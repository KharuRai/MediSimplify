import os
import uuid
import json
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

from pdf_processor import extract_text_from_pdf
from fda_api import get_fda_drug_data
from rag_engine import run_rag_pipeline, extract_drug_names_from_ocr
from pdf_generator import generate_simplified_pdf
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

app = FastAPI(title="MediSimplify API")
security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
    allow_origins=["*"], # In production, restrict to actual frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured.")
        
    file_id = str(uuid.uuid4())
    input_pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}_input.pdf")
    output_pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}_output.pdf")
    
    # 1. Read and save locally + upload to Supabase Storage
    try:
        content = await file.read()
        original_path = f"{user_id}/{file_id}_original.pdf"
        supabase.storage.from_("medical_reports").upload(original_path, content)
        
        with open(input_pdf_path, "wb") as f:
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
        # 3. Extract Text (OCR or pdfplumber)
        ocr_text = extract_text_from_pdf(input_pdf_path)
        
        if not ocr_text:
            raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")
            
        # 4. Extract drug names to query FDA
        drug_names = extract_drug_names_from_ocr(ocr_text)
        
        # 5. Fetch FDA Data
        fda_data_list = []
        for drug in drug_names:
            drug_data = get_fda_drug_data(drug)
            if drug_data:
                fda_data_list.extend(drug_data)
            else:
                print(f"Warning: No FDA data found for drug '{drug}'")
                
        # 6. Run RAG Pipeline
        structured_data = run_rag_pipeline(fda_data_list, ocr_text)
            
        # 7. Generate Output PDF
        mapped_data = {
            "Medicines": structured_data.get("medicines", []),
            "Dosage": structured_data.get("dosage", "Not specified."),
            "Purpose": structured_data.get("purpose", "Not specified."),
            "Warnings": structured_data.get("warnings", []),
            "Disclaimer": structured_data.get("disclaimer", "This is an AI generated summary. Please consult a doctor.")
        }
        generate_simplified_pdf(mapped_data, output_pdf_path)
        
        # 8. Upload Result to Storage
        simplified_path = f"{user_id}/{file_id}_simplified.pdf"
        with open(output_pdf_path, "rb") as f:
            supabase.storage.from_("medical_reports").upload(simplified_path, f.read())
            
        # 9. Update DB Record
        supabase.table("reports").update({
            "status": "completed",
            "simplified_file_path": simplified_path,
            "extracted_data": mapped_data
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
        if os.path.exists(input_pdf_path):
            os.remove(input_pdf_path)
        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
            
    return JSONResponse(content={
        "id": report_record_id,
        "data": mapped_data,
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
        
        # Check if the response contains the signedURL string (depends on supabase-py version)
        if isinstance(url_response, dict) and "signedURL" in url_response:
            return {"signed_url": url_response["signedURL"]}
        elif hasattr(url_response, "signed_url"):
            return {"signed_url": url_response.signed_url}
        else:
            return {"signed_url": url_response} # Sometimes it returns the string directly
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating download link: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
