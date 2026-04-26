import os
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text from a PDF file.
    Uses a two-stage logic:
    1. Try pdfplumber for digital PDFs.
    2. If text is too short (likely scanned), fallback to OCR using pdf2image + pytesseract.
    """
    text = ""
    
    # Stage 1: Try digital extraction
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF with pdfplumber: {e}")

    # Heuristic: If extracted text is less than 50 characters, it might be a scanned image
    if len(text.strip()) < 50:
        print("Text is too short, falling back to OCR...")
        text = "" # Reset text
        # Stage 2: Fallback to OCR
        try:
            images = convert_from_path(pdf_path)
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
        except Exception as e:
            print(f"Error during OCR extraction: {e}")

    return text.strip()
