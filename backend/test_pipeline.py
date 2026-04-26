import json
from dotenv import load_dotenv
from fda_api import get_fda_drug_data
from rag_engine import run_rag_pipeline, extract_drug_names_from_ocr

load_dotenv()

def main():
    sample_ocr_text = """
    Patient Name: John Doe
    Date: 2023-10-26
    
    Rx:
    Lisinopril 10mg
    Take one tablet daily for blood pressure.
    
    Metformin 500mg
    Take twice daily with meals.
    
    Doctor: Dr. Smith
    """
    
    print("1. Extracting drug names from OCR text...")
    drug_names = extract_drug_names_from_ocr(sample_ocr_text)
    print(f"Extracted drugs: {drug_names}")
    
    fda_data_list = []
    print("\n2. Fetching OpenFDA data for extracted drugs...")
    for drug in drug_names:
        print(f"Fetching data for {drug}...")
        drug_data = get_fda_drug_data(drug)
        if drug_data:
            print(f"Found {len(drug_data)} results for {drug}.")
            fda_data_list.extend(drug_data)
        else:
            print(f"No data found for {drug}.")
            
    print("\n3. Running RAG Pipeline...")
    try:
        structured_data = run_rag_pipeline(fda_data_list, sample_ocr_text)
        print("\n--- Final Structured Output ---")
        print(json.dumps(structured_data, indent=2))
    except Exception as e:
        print(f"Error during RAG pipeline: {e}")

if __name__ == "__main__":
    main()
