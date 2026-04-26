import os
import uuid
import json
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pdf_processor import extract_text_from_pdf
from fda_api import get_fda_drug_data
from rag_engine import run_rag_pipeline, extract_drug_names_from_ocr
from pdf_generator import generate_simplified_pdf

load_dotenv()

app = FastAPI(title="MediSimplify API")

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
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    file_id = str(uuid.uuid4())
    input_pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}_input.pdf")
    output_pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}_output.pdf")
    
    # 1. Save uploaded file
    try:
        with open(input_pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # 2. Extract Text (OCR or pdfplumber)
    ocr_text = extract_text_from_pdf(input_pdf_path)
    
    if not ocr_text:
        raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")
        
    # 3. Extract drug names to query FDA
    drug_names = extract_drug_names_from_ocr(ocr_text)
    
    # 4. Fetch FDA Data
    fda_data_list = []
    for drug in drug_names:
        # get_fda_drug_data returns a list of results (up to 3 limits)
        drug_data = get_fda_drug_data(drug)
        if drug_data:
            fda_data_list.extend(drug_data)
        else:
            print(f"Warning: No FDA data found for drug '{drug}'")
            
    # 5. Run RAG Pipeline
    try:
        structured_data = run_rag_pipeline(fda_data_list, ocr_text)
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error in RAG pipeline: {str(e)}")
        
    # 6. Generate Output PDF
    try:
        # Capitalize keys back to match what pdf_generator expects
        # pdf_generator expects: Medicines, Purpose, Dosage, Warnings, Disclaimer
        mapped_data = {
            "Medicines": structured_data.get("medicines", []),
            "Dosage": structured_data.get("dosage", "Not specified."),
            "Purpose": structured_data.get("purpose", "Not specified."),
            "Warnings": structured_data.get("warnings", []),
            "Disclaimer": structured_data.get("disclaimer", "This is an AI generated summary. Please consult a doctor.")
        }
        generate_simplified_pdf(mapped_data, output_pdf_path)
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
         
    # Clean up input PDF to save space
    if os.path.exists(input_pdf_path):
        os.remove(input_pdf_path)
        
    # The frontend expects 'data' object with capitalized keys (Medicines, Purpose, etc.)
    # Since we mapped them, let's return mapped_data to not break the frontend.
    return JSONResponse(content={
        "id": file_id,
        "data": mapped_data,
        "message": "Report processed successfully."
    })

@app.get("/result/{file_id}")
async def get_result_pdf(file_id: str):
    output_pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}_output.pdf")
    if not os.path.exists(output_pdf_path):
        raise HTTPException(status_code=404, detail="Result PDF not found.")
        
    return FileResponse(
        path=output_pdf_path,
        filename=f"Simplified_Report_{file_id}.pdf",
        media_type="application/pdf"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
