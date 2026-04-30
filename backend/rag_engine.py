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
    "prescription": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Only explain what is written in the prescription
- If unclear, say "Not clearly mentioned"

Explain this prescription in simple language.

Respond ONLY with valid JSON in the exact following structure:
{
  "Medicines": [
    {
      "name": "",
      "dosage": "",
      "frequency": "",
      "purpose": "",
      "warnings": ""
    }
  ],
  "Disclaimer": "This is an AI generated summary. Please consult a doctor."
}
""",

    "lab": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Do NOT assume normal ranges
- Only extract values and ranges exactly as written
- Do NOT calculate High/Low
- If range is missing, set min_range and max_range as null
- Only explain what the test measures
- If unclear, say "Not clearly mentioned"

Explain this lab report in simple language.

Respond ONLY with valid JSON in the exact following structure:
{
  "Summary": "A brief, simple summary of what these tests are generally for.",
  "Lab Results": [
    {
      "test_name": "",
      "value": "",
      "unit": "",
      "min_range": null,
      "max_range": null,
      "explanation": ""
    }
  ],
  "Disclaimer": "This is an AI generated summary. Please consult a doctor."
}
""",

    "ecg": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Only use explicitly mentioned findings
- Do NOT interpret waveform data
- Do NOT infer abnormalities unless clearly written
- If unclear, say "Not clearly mentioned"

Explain this ECG/EKG report in simple language.

Respond ONLY with valid JSON in the exact following structure:
{
  "Summary": "Simple explanation of the overall ECG findings",
  "Heart Rate": "",
  "Rhythm": "",
  "Key Findings": [],
  "Disclaimer": "This is an AI generated summary. Please consult a doctor."
}
""",

    "eeg": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Only summarize what is written
- Do NOT infer neurological conditions
- If unclear, say "Not clearly mentioned"

Explain this EEG report in simple language.

Respond ONLY with valid JSON in the exact following structure:
{
  "Summary": "Simple explanation of the overall EEG findings",
  "Brain Wave Activity": "",
  "Key Findings": [],
  "Disclaimer": "This is an AI generated summary. Please consult a doctor."
}
""",

    "pulmonary": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Do NOT assume ranges if not provided
- Only explain values mentioned in the report
- If unclear, say "Not clearly mentioned"

Explain this Pulmonary Function Test report in simple language.

Respond ONLY with valid JSON in the exact following structure:
{
  "Summary": "Simple explanation of the overall lung function findings",
  "Key Measurements": [],
  "Observation": "Simple description of what the report states",
  "Disclaimer": "This is an AI generated summary. Please consult a doctor."
}
""",

    "procedure": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Only describe what was done and found
- Do NOT interpret findings beyond what is written
- If unclear, say "Not clearly mentioned"

Explain this Procedure/Surgery report in simple language.

Respond ONLY with valid JSON in the exact following structure:
{
  "Procedure Name": "",
  "Summary": "Simple summary of what was done",
  "Key Findings": [],
  "Post-Procedure Instructions": [],
  "Disclaimer": "This is an AI generated summary. Please consult a doctor."
}
""",

    "general": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Do NOT infer missing information
- Only extract clearly stated details
- If unclear, say "Not clearly mentioned"

Explain this general medical report in simple language.

Respond ONLY with valid JSON in the exact following structure:
{
  "Summary": "Simple explanation of the report",
  "Key Findings": [],
  "Recommendations": [],
  "Disclaimer": "This is an AI generated summary. Please consult a doctor."
}
"""
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
