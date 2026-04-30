import json
import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List

load_dotenv()

PROMPTS = {
    "prescription": """You are MediSimplify. Explain this prescription in simple language. Never diagnose. Always include a disclaimer to consult a doctor.
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "Medicines": ["List of extracted medicine names"],
      "Dosage": "Simplified dosage instructions",
      "Purpose": "What the medicines are for",
      "Warnings": ["List of key warnings or side effects"],
      "Disclaimer": "This is an AI generated summary. Please consult a doctor."
    }}""",
    
    "lab": """You are MediSimplify. Explain this lab report in simple language. Extract the test results, their values, units, and reference ranges (min and max). Never diagnose.
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "Summary": "A brief, simple summary of what these tests are generally for.",
      "Lab Results": [
        {{
          "test_name": "Name of the test",
          "value": "numeric value if available, else string",
          "unit": "unit of measurement",
          "min_range": "minimum normal value (numeric) if available, else null",
          "max_range": "maximum normal value (numeric) if available, else null",
          "explanation": "Simple explanation of what this test measures"
        }}
      ],
      "Disclaimer": "This is an AI generated summary. Please consult a doctor."
    }}""",
    
    "ecg": """You are MediSimplify. Explain this ECG/EKG report in simple language. Never diagnose.
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "Summary": "Simple explanation of the overall ECG findings",
      "Heart Rate": "Heart rate if mentioned",
      "Rhythm": "Rhythm description if mentioned",
      "Key Findings": ["List of key observations in simple terms"],
      "Disclaimer": "This is an AI generated summary. Please consult a doctor."
    }}""",

    "eeg": """You are MediSimplify. Explain this EEG report in simple language. Never diagnose.
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "Summary": "Simple explanation of the overall EEG findings",
      "Brain Wave Activity": "Simple description of brain wave activity",
      "Key Findings": ["List of key observations in simple terms"],
      "Disclaimer": "This is an AI generated summary. Please consult a doctor."
    }}""",

    "pulmonary": """You are MediSimplify. Explain this Pulmonary Function Test report in simple language. Never diagnose.
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "Summary": "Simple explanation of the overall lung function findings",
      "Key Measurements": ["List of key lung capacity/flow measurements in simple terms"],
      "Interpretation": "Simple explanation of the test interpretation",
      "Disclaimer": "This is an AI generated summary. Please consult a doctor."
    }}""",

    "procedure": """You are MediSimplify. Explain this Procedure/Surgery report in simple language. Never diagnose.
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "Procedure Name": "Name of the procedure performed",
      "Summary": "Simple summary of what was done",
      "Key Findings": ["List of key findings during the procedure"],
      "Post-Procedure Instructions": ["Any extracted post-procedure or recovery instructions"],
      "Disclaimer": "This is an AI generated summary. Please consult a doctor."
    }}""",

    "general": """You are MediSimplify. Explain this general medical diagnosis report in simple language. Never diagnose.
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "Summary": "Simple explanation of the report",
      "Key Findings": ["List of key observations or diagnoses mentioned"],
      "Recommendations": ["Any extracted next steps or recommendations"],
      "Disclaimer": "This is an AI generated summary. Please consult a doctor."
    }}"""
}

def run_rag_pipeline(fda_data_list: List[Dict[str, Any]], ocr_text: str, report_type: str = "prescription") -> Dict[str, Any]:
    """
    Conditionally chunks FDA text, retrieves context if available, and uses a modular prompt routing
    system to process various types of medical reports.
    """
    context = "No additional context."
    
    if report_type == "prescription" and fda_data_list:
        # 1. Prepare FDA text to embed
        fda_text_content = ""
        for fda_data in fda_data_list:
            if fda_data:
                brand_name = fda_data.get('openfda', {}).get('brand_name', ['Unknown Drug'])[0]
                fda_text_content += f"--- DRUG: {brand_name} ---\n"
                for key in ["warnings", "dosage_and_administration", "indications_and_usage", "purpose"]:
                    if key in fda_data:
                        fda_text_content += f"{key.upper()}:\n{fda_data[key][0]}\n\n"
        
        # 2. Chunk FDA text
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name="gpt-4o",
            chunk_size=500, 
            chunk_overlap=50
        )
        chunks = text_splitter.split_text(fda_text_content)
        if not chunks:
            chunks = ["No relevant FDA information found."]

        # 3. Create Vector Store
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = FAISS.from_texts(chunks, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        
        # 4. Retrieve context using the OCR text as the query
        retrieved_docs = retriever.invoke(ocr_text)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
    
    # 5. Call GPT-4o for structured output
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    system_prompt = PROMPTS.get(report_type, PROMPTS["general"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Context:\n{context}\n\nReport (OCR Text):\n{ocr_text}")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "context": context,
        "ocr_text": ocr_text
    })
    
    raw_content = response.content.strip()
    
    # Clean up markdown if present
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:]
    elif raw_content.startswith("```"):
        raw_content = raw_content[3:]
    if raw_content.endswith("```"):
        raw_content = raw_content[:-3]
        
    try:
        structured_data = json.loads(raw_content)
    except json.JSONDecodeError:
        print("Failed to parse JSON from LLM. Raw content:", raw_content)
        structured_data = {
            "Summary": "Error extracting data.",
            "Disclaimer": "This is an AI generated summary. Please consult a doctor."
        }
        
    # 6. Safety check for Lab Reports (Calculate High/Low/Normal in Python)
    if report_type == "lab" and "Lab Results" in structured_data:
        for result in structured_data["Lab Results"]:
            val = result.get("value")
            min_val = result.get("min_range")
            max_val = result.get("max_range")
            status = "Normal"
            if val is not None and min_val is not None and max_val is not None:
                try:
                    v = float(val)
                    min_v = float(min_val)
                    max_v = float(max_val)
                    if v < min_v:
                        status = "Low"
                    elif v > max_v:
                        status = "High"
                except (ValueError, TypeError):
                    status = "Unknown"
            result["status"] = status
            
    return structured_data

def extract_drug_names_from_ocr(ocr_text: str) -> List[str]:
    """
    Uses GPT-4o to identify potential drug names from raw OCR text to query OpenFDA.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    system_prompt = """
    Extract a list of drug/medicine names from the following OCR'd medical text.
    Return ONLY a JSON list of strings. Example: ["Aspirin", "Lisinopril"].
    Do not wrap in markdown.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{ocr_text}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"ocr_text": ocr_text})
    raw_content = response.content.strip()
    
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:]
    elif raw_content.startswith("```"):
        raw_content = raw_content[3:]
    if raw_content.endswith("```"):
        raw_content = raw_content[:-3]
        
    try:
        drugs = json.loads(raw_content)
        if isinstance(drugs, list):
            return drugs
    except json.JSONDecodeError:
        pass
        
    return []
