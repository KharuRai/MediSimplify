import os
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from typing import List
from PIL import Image

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

def extract_images_from_pdf(pdf_path: str, output_dir: str, file_prefix: str) -> List[str]:
    """
    Extracts pages of a PDF as JPEG images and saves them to the output directory.
    Returns a list of local file paths.
    """
    image_paths = []
    try:
        images = convert_from_path(pdf_path)
        os.makedirs(output_dir, exist_ok=True)
        for i, image in enumerate(images):
            img_path = os.path.join(output_dir, f"{file_prefix}_page_{i}.jpg")
            image.save(img_path, "JPEG")
            image_paths.append(img_path)
    except Exception as e:
        print(f"Error extracting images from PDF: {e}")
    return image_paths

def extract_text_from_image(image_path: str) -> str:
    """
    Extracts text directly from an image file using pytesseract.
    """
    text = ""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        print(f"Error extracting text from image: {e}")
    return text.strip()
