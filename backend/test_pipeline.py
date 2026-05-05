import json
from dotenv import load_dotenv
from fda_api import get_fda_drug_data
from rag_engine import analyze_lab_results, run_rag_pipeline, extract_drug_names_from_ocr

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

    print("\n4. Running lab validation logic tests...")
    lab_test_samples = [
        {
            "test_name": "Hemoglobin",
            "value": "10.2",
            "unit": "g/dL",
            "min_range": "12",
            "max_range": "16",
            "explanation": "Measures oxygen-carrying protein.",
        },
        {
            "test_name": "Glucose",
            "value": "5.5 mmol/L",
            "unit": "",
            "min_range": "3.9",
            "max_range": "5.6",
            "explanation": "Blood sugar level.",
        },
        {
            "test_name": "WBC",
            "value": "10570 /cmm",
            "unit": "",
            "min_range": "4000",
            "max_range": "11000",
            "explanation": "White blood cell count.",
        },
        {
            "test_name": "Platelets",
            "value": "150",
            "unit": "x10^3/uL",
            "min_range": "150",
            "max_range": "450",
            "explanation": "Platelet count.",
        },
    ]
    validated_lab_results = analyze_lab_results(lab_test_samples, sample_ocr_text)
    print(json.dumps(validated_lab_results, indent=2))

if __name__ == "__main__":
    main()
