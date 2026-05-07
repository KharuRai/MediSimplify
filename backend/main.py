import os
import uuid
import json
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

from pdf_processor import extract_text_from_pdf, extract_images_from_pdf, extract_text_from_image
from fda_api import get_fda_drug_data
from rag_engine import run_rag_pipeline, extract_drug_names_from_ocr
from pdf_generator import generate_simplified_pdf
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

app = FastAPI(title="MediSimplify API")
security = HTTPBearer(auto_error=False)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def get_cors_origins() -> list[str]:
    """
    Parse CORS origins from FRONTEND_ORIGINS (comma-separated) or FRONTEND_ORIGIN.
    """
    origins = os.getenv("FRONTEND_ORIGINS", "").strip()
    single_origin = os.getenv("FRONTEND_ORIGIN", "").strip()

    raw_values = origins or single_origin
    allowed = [origin.strip() for origin in raw_values.split(",") if origin.strip()]

    # Always allow local development host for local frontend testing
    for dev_origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]:
        if dev_origin not in allowed:
            allowed.append(dev_origin)

    if not allowed:
        return ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]

    return allowed

supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def normalize_signed_url(url_response) -> str:
    """
    Handle Supabase signed URL response shape differences across client versions.
    Always return an absolute URL string.
    """
    candidate = None

    if isinstance(url_response, str):
        candidate = url_response
    elif isinstance(url_response, dict):
        # Common keys observed across supabase-py versions
        candidate = (
            url_response.get("signedURL")
            or url_response.get("signedUrl")
            or url_response.get("signed_url")
        )
        if candidate is None and isinstance(url_response.get("data"), dict):
            data = url_response["data"]
            candidate = (
                data.get("signedURL")
                or data.get("signedUrl")
                or data.get("signed_url")
            )
    elif hasattr(url_response, "signed_url"):
        candidate = getattr(url_response, "signed_url")

    if not candidate or not isinstance(candidate, str):
        raise ValueError(f"Invalid signed URL response: {url_response}")

    # Some SDK versions return a relative path like /storage/v1/object/sign/...
    if candidate.startswith("/") and SUPABASE_URL:
        return f"{SUPABASE_URL.rstrip('/')}{candidate}"
    return candidate

def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Allow OPTIONS (preflight) requests without authentication
    if request.method == "OPTIONS":
        return None
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = credentials.credentials
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.user.id
    except Exception as e:
        print(f"Supabase auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"Configured CORS origins: {get_cors_origins()}")


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...), 
    report_type: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    valid_types = ["prescription", "lab", "ecg", "general"]
    if report_type not in valid_types:
        raise HTTPException(status_code=400, detail="Invalid report type.")

    valid_exts = ['.pdf']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in valid_exts:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    is_pdf = True

    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured.")
        
    file_id = str(uuid.uuid4())
    input_file_path = os.path.join(UPLOAD_DIR, f"{file_id}_input{ext}")
    output_pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}_output.pdf")
    
    # 1. Read and save locally + upload to Supabase Storage
    try:
        content = await file.read()
        original_path = f"{user_id}/{file_id}_original{ext}"
        supabase.storage.from_("medical_reports").upload(original_path, content)
        
        with open(input_file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # 2. Create DB Record
    try:
        db_response = supabase.table("reports").insert({
            "user_id": user_id,
            "original_filename": file.filename,
            "original_file_path": original_path,
            "status": "processing"
        }).execute()
        report_record_id = db_response.data[0]["id"]
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
         
    try:
        source_image_paths = []
        image_signed_urls = []

        if is_pdf:
            # 3. Extract Text (OCR or pdfplumber)
            try:
                ocr_text = extract_text_from_pdf(input_file_path)
                if not ocr_text:
                    raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")
            except HTTPException:
                raise
            except Exception as pdf_error:
                print(f"PDF extraction error: {str(pdf_error)}")
                raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(pdf_error)}")
                
            # 3.5 Extract Images and upload
            try:
                local_image_paths = extract_images_from_pdf(input_file_path, UPLOAD_DIR, file_id)
            except Exception as img_extract_error:
                print(f"Image extraction from PDF error: {str(img_extract_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to extract images from PDF: {str(img_extract_error)}")
            
            for i, img_path in enumerate(local_image_paths):
                storage_path = f"{user_id}/{file_id}_page_{i}.jpg"
                with open(img_path, "rb") as img_file:
                    supabase.storage.from_("medical_reports").upload(storage_path, img_file.read())
                source_image_paths.append(storage_path)
                
                # Generate signed URL
                url_res = supabase.storage.from_("medical_reports").create_signed_url(storage_path, 3600)
                image_signed_urls.append(normalize_signed_url(url_res))
                
                # Clean up local image
                if os.path.exists(img_path):
                    os.remove(img_path)
        else:
            # This should not happen now since we only accept PDFs
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
            
        fda_data_list = []
        if report_type == "prescription":
            # 4. Extract drug names to query FDA
            drug_names = extract_drug_names_from_ocr(ocr_text)
            
            # 5. Fetch FDA Data
            for drug in drug_names:
                drug_data = get_fda_drug_data(drug)
                if drug_data:
                    fda_data_list.extend(drug_data)
                else:
                    print(f"Warning: No FDA data found for drug '{drug}'")
                    
        # 6. Run RAG Pipeline
        structured_data = run_rag_pipeline(fda_data_list, ocr_text, report_type)
        
        if source_image_paths:
            structured_data["source_image_paths"] = source_image_paths
            
        # 7. Generate Output PDF
        generate_simplified_pdf(structured_data, output_pdf_path)
        
        # 8. Upload Result to Storage
        simplified_path = f"{user_id}/{file_id}_simplified.pdf"
        with open(output_pdf_path, "rb") as f:
            supabase.storage.from_("medical_reports").upload(simplified_path, f.read())
            
        # 9. Update DB Record
        supabase.table("reports").update({
            "status": "completed",
            "simplified_file_path": simplified_path,
            "extracted_data": structured_data
        }).eq("id", report_record_id).execute()
        
    except Exception as e:
        # Mark as failed
        supabase.table("reports").update({
            "status": "failed",
            "error_message": str(e)
        }).eq("id", report_record_id).execute()
        raise HTTPException(status_code=500, detail=f"Error in pipeline: {str(e)}")
        
    finally:
        # Clean up input and output PDF to save space
        if os.path.exists(input_file_path):
            os.remove(input_file_path)
        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
            
    return JSONResponse(content={
        "id": report_record_id,
        "data": structured_data,
        "report_type": report_type,
        "image_urls": image_signed_urls,
        "message": "Report processed successfully."
    })

@app.get("/reports")
async def get_reports(user_id: str = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured.")
        
    try:
        db_response = supabase.table("reports").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"reports": db_response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reports: {str(e)}")

@app.get("/reports/{report_id}/download")
async def download_report(report_id: str, user_id: str = Depends(get_current_user)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured.")
        
    try:
        # Verify ownership
        db_response = supabase.table("reports").select("user_id, simplified_file_path").eq("id", report_id).execute()
        if not db_response.data or db_response.data[0]["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized access to report")
            
        simplified_file_path = db_response.data[0]["simplified_file_path"]
        if not simplified_file_path:
             raise HTTPException(status_code=404, detail="PDF not generated yet")
             
        # Generate signed URL
        url_response = supabase.storage.from_("medical_reports").create_signed_url(simplified_file_path, 3600)
        return {"signed_url": normalize_signed_url(url_response)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating download link: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
