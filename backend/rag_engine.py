import json
import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List

load_dotenv()

def run_rag_pipeline(fda_data_list: List[Dict[str, Any]], ocr_text: str) -> Dict[str, Any]:
    """
    Chunks the FDA text using token splitting, embeds it, stores in FAISS, retrieves relevant info using OCR text,
    and calls GPT-4o to output structured JSON.
    """
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
    # The requirement: 500-token chunks with 50-token overlap
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
    
    system_prompt = """You are MediSimplify. Explain this prescription in simple language. Never diagnose. Always include a disclaimer to consult a doctor.
    
    Respond ONLY with valid JSON in the exact following structure:
    {{
      "medicines": ["List of extracted medicine names"],
      "dosage": "Simplified dosage instructions",
      "purpose": "What the medicines are for",
      "warnings": ["List of key warnings or side effects"],
      "disclaimer": "A standard medical disclaimer stating this is AI generated and not medical advice."
    }}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Context (FDA Data):\n{context}\n\nPrescription (OCR Text):\n{ocr_text}")
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
            "medicines": [],
            "dosage": "Error extracting data.",
            "purpose": "Error extracting data.",
            "warnings": [],
            "disclaimer": "This is an AI generated summary. Please consult a doctor."
        }
        
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
