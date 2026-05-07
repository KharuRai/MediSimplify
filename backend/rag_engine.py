import json
import os
import re
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List
from clinical_ranges import (
    convert_value_to_unit,
    detect_units_in_text,
    format_range,
    get_clinical_range,
    normalize_unit,
    normalize_test_name,
)

load_dotenv()


PROMPTS = {
    "prescription": """You are MediSimplify.

STRICT SAFETY RULES:
- Do NOT diagnose any condition
- Do NOT suggest diseases
- Only explain what is written in the prescription
- If unclear, say "Not clearly mentioned"

Explain this prescription in simple language.
Use Context (OpenFDA) to provide FDA information for each medicine.
For each medicine, extract and summarize key FDA details like indications, warnings, and dosage from the context.
If FDA context is available, populate fda_validation with a concise summary of the FDA information.
.

Respond ONLY with valid JSON in the exact following structure:
{
  "Summary": "Simple summary of what this prescription is for and key care instructions, or 'Not clearly mentioned' if unclear.",
  "Medicines": [
    {
      "name": "",
      "dosage": "",
      "frequency": "",
      "purpose": "",
      "warnings": "",
      "fda_validation": ""
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

def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(',', '.').replace('\u2013', '-').replace('\u2014', '-')
        match = re.search(r"[-+]?[0-9]*\.?[0-9]+", cleaned)
        if not match:
            return None
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def parse_range_value(raw_value: Any, prefer_last: bool = False) -> float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    text = str(raw_value)
    numbers = re.findall(r"[-+]?[0-9]*\.?[0-9]+", text)
    if not numbers:
        return None
    return float(numbers[-1] if prefer_last else numbers[0])


def extract_value_unit(raw_value: Any) -> dict[str, Any] | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return {"value": float(raw_value), "unit": None}
    text = str(raw_value)
    match = re.search(
        r"([-+]?[0-9]*\.?[0-9]+)\s*(g/dL|mg/dL|mmol/L|µmol/L|umol/L|x10\^3/uL|10\^3/uL|K/µL|cells/mm3|/cmm|%)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return {
            "value": match.group(1),
            "unit": normalize_unit(match.group(2)),
        }
    match = re.search(r"([-+]?[0-9]*\.?[0-9]+)", text)
    if match:
        return {"value": match.group(1), "unit": None}
    return None


def derive_status(value: float | None, min_value: float | None, max_value: float | None) -> str:
    if value is None or min_value is None or max_value is None:
        return "Unknown"
    if min_value >= max_value:
        return "Unknown"
    if value < min_value:
        return "Low"
    if value > max_value:
        return "High"
    return "Normal"


def format_range_string(min_value: float | None, max_value: float | None, unit: str | None) -> str | None:
    if min_value is None or max_value is None:
        return None
    if unit:
        return f"{min_value:g} - {max_value:g} {unit}"
    return f"{min_value:g} - {max_value:g}"


def compute_confidence(
    value: float | None,
    unit: str | None,
    report_min: float | None,
    report_max: float | None,
    range_valid: bool,
    has_clinical: bool,
    discrepancy: bool,
) -> str:
    score = 5
    if value is None:
        score -= 2
    if not unit:
        score -= 1
    if report_min is None or report_max is None:
        score -= 1
    if not range_valid:
        score -= 1
    if discrepancy:
        score -= 1
    if score >= 5 and has_clinical:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def analyze_lab_results(lab_results: List[Dict[str, Any]], ocr_text: str) -> List[Dict[str, Any]]:
    analyzed = []
    text_units = detect_units_in_text(ocr_text)
    for result in lab_results:
        test_name = str(result.get("test_name", "")).strip()
        raw_value = result.get("value")
        raw_unit = str(result.get("unit", "")).strip() if result.get("unit") is not None else ""
        parsed = extract_value_unit(raw_value)
        if parsed:
            if parsed["unit"] and not raw_unit:
                raw_unit = parsed["unit"]
            raw_value = parsed["value"]

        unit = normalize_unit(raw_unit) if raw_unit else None
        if not unit and len(text_units) == 1:
            unit = normalize_unit(next(iter(text_units)))

        value = safe_float(raw_value)
        report_min = parse_range_value(result.get("min_range"))
        report_max = parse_range_value(result.get("max_range"), prefer_last=True)
        range_valid = report_min is not None and report_max is not None and report_min < report_max
        status_report = derive_status(value, report_min, report_max)
        report_range = format_range_string(report_min, report_max, unit)

        clinical_data = get_clinical_range(test_name, unit)
        clinical_range = None
        status_clinical = "Unknown"
        if clinical_data:
            clinical_range = format_range(
                clinical_data["min_value"],
                clinical_data["max_value"],
                clinical_data["unit"],
            )
            if value is not None:
                comparison_value = value
                if unit and clinical_data["unit"] != unit:
                    converted = convert_value_to_unit(value, unit, clinical_data["unit"], test_name)
                    if converted is not None:
                        comparison_value = converted
                    else:
                        comparison_value = None
                status_clinical = derive_status(
                    comparison_value,
                    clinical_data["min_value"],
                    clinical_data["max_value"],
                )

        discrepancy_flag = False
        if status_report != "Unknown" and status_clinical != "Unknown" and status_report != status_clinical:
            discrepancy_flag = True
        if report_range and clinical_range and report_range != clinical_range:
            discrepancy_flag = True

        warning = None
        if discrepancy_flag:
            warning = "⚠ Report range differs from standard clinical reference."

        confidence = compute_confidence(
            value,
            unit,
            report_min,
            report_max,
            range_valid,
            clinical_data is not None,
            discrepancy_flag,
        )

        enriched_result = {
            **result,
            "value": value if value is not None else result.get("value"),
            "unit": unit or result.get("unit"),
            "report_range": report_range,
            "clinical_range": clinical_range,
            "status_report_based": status_report,
            "status_clinical": status_clinical,
            "discrepancy_flag": discrepancy_flag,
            "confidence": confidence,
            "warning": warning,
            "status": status_report,
        }
        analyzed.append(enriched_result)

    return analyzed


def _get_first_list_text(data: Dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    if isinstance(value, str):
        return value.strip()
    return None


def _shorten_text(text: str, max_len: int = 220) -> str:
    if not text:
        return ""
    normalized = " ".join(text.replace("\n", " ").split())
    if len(normalized) <= max_len:
        return normalized
    sentences = re.split(r'(?<=[.!?])\s+', normalized)
    snippet = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(snippet) + len(sentence) + 1 <= max_len:
            snippet = f"{snippet} {sentence}".strip()
        else:
            break
    if not snippet:
        snippet = normalized[:max_len]
    return snippet.rstrip() + ("..." if len(snippet) < len(normalized) else "")


def _summarize_fda_label(fda_data: Dict[str, Any]) -> str:
    openfda = fda_data.get("openfda", {}) or {}
    brand_name = _get_first_list_text(openfda, "brand_name")
    generic_name = _get_first_list_text(openfda, "generic_name")
    title = generic_name or brand_name or "This drug"

    indications = _shorten_text(_get_first_list_text(fda_data, "indications_and_usage") or "")
    warnings = _shorten_text(_get_first_list_text(fda_data, "warnings") or _get_first_list_text(fda_data, "boxed_warning") or "")
    dosage = _shorten_text(_get_first_list_text(fda_data, "dosage_and_administration") or "")

    pieces = [f"FDA label for {title}."]
    if indications:
        pieces.append(f"Indications: {indications}")
    if warnings:
        pieces.append(f"Warnings: {warnings}")
    if dosage:
        pieces.append(f"Dosage guidance: {dosage}")
    if len(pieces) == 1:
        return "No FDA information available"
    return " ".join(pieces)


def enrich_prescription_with_fda(structured_data: Dict[str, Any], fda_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not fda_data_list or not structured_data or "Medicines" not in structured_data:
        return structured_data

    def match_label(name: str, label: Dict[str, Any]) -> bool:
        if not name:
            return False
        name_lower = name.lower()
        openfda = label.get("openfda", {}) or {}
        for key in ["brand_name", "generic_name", "substance_name"]:
            entries = openfda.get(key, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, str):
                    continue
                entry_lower = entry.lower()
                if name_lower == entry_lower or name_lower in entry_lower or entry_lower in name_lower:
                    return True
        return False

    for medicine in structured_data.get("Medicines", []):
        if not isinstance(medicine, dict):
            continue
        name = str(medicine.get("name", "")).strip()
        current_validation = str(medicine.get("fda_validation", "")).strip()
        if current_validation and current_validation.lower() != "not clearly mentioned":
            continue

        matched_labels = [label for label in fda_data_list if match_label(name, label)]
        medicine["fda_validation"] = _summarize_fda_label(matched_labels[0]) if matched_labels else "No FDA information available"
    return structured_data


def ensure_prescription_fields(structured_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize prescription output so frontend always has at least one
    user-visible section even when medicine extraction fails.
    """
    if not isinstance(structured_data, dict):
        return {
            "Summary": "Could not extract structured prescription details from this document.",
            "Medicines": [],
        }

    medicines = structured_data.get("Medicines")
    if not isinstance(medicines, list):
        structured_data["Medicines"] = []
        medicines = structured_data["Medicines"]

    summary = structured_data.get("Summary")
    if not isinstance(summary, str) or not summary.strip():
        if medicines:
            med_names = [
                str(med.get("name", "")).strip()
                for med in medicines
                if isinstance(med, dict) and str(med.get("name", "")).strip()
            ]
            if med_names:
                structured_data["Summary"] = f"Prescription includes: {', '.join(med_names[:5])}."
            else:
                structured_data["Summary"] = "Prescription detected. Review medicine details below."
        else:
            structured_data["Summary"] = "Could not extract medicine details clearly from this prescription. Try a clearer scan."

    return structured_data

def run_rag_pipeline(fda_data_list: List[Dict[str, Any]], ocr_text: str, report_type: str = "prescription") -> Dict[str, Any]:
    """
    Conditionally chunks FDA text, retrieves context if available, and uses a modular prompt routing
    system to process various types of medical reports.
    """
    context = "No additional context."
    fda_text_content = ""
    
    if report_type == "prescription" and fda_data_list:
        # 1. Prepare FDA text to embed
        fda_text_content = ""
        for fda_data in fda_data_list:
            if fda_data:
                brand_name = fda_data.get('openfda', {}).get('brand_name', ['Unknown Drug'])[0]
                generic_name = fda_data.get('openfda', {}).get('generic_name', [''])[0]
                substance_names = fda_data.get('openfda', {}).get('substance_name', [])
                fda_text_content += f"--- DRUG: {brand_name} ---\n"
                if generic_name:
                    fda_text_content += f"GENERIC NAME: {generic_name}\n"
                if substance_names:
                    fda_text_content += f"SUBSTANCE: {', '.join(substance_names)}\n"
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

    if report_type == "prescription" and fda_text_content:
        # Always give the LLM direct access to the OpenFDA label context.
        context = f"{context}\n\nOpenFDA Context:\n{fda_text_content}" if context else fda_text_content
    
    # 5. Call GPT-4o for structured output
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    system_prompt = PROMPTS.get(report_type, PROMPTS["general"])
    # Escape literal JSON braces in system prompt so LangChain template parsing
    # does not treat them as replacement fields.
    escaped_system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", escaped_system_prompt),
        ("user", "Context:\n{context}\n\nReport (OCR Text):\n{ocr_text}")
    ])
    
    chain = prompt | llm
    
    # If OCR text is empty, provide context about the image being analyzed visually
    ocr_or_note = ocr_text if ocr_text.strip() else "[Image analyzed visually due to complex layout]"
    
    response = chain.invoke({
        "context": context,
        "ocr_text": ocr_or_note
    })
    
    raw_content = response.content.strip()
    
    # Clean up markdown if present
    if raw_content.startswith("```json"):
        raw_content = raw_content[7:]
    elif raw_content.startswith("```"):
        raw_content = raw_content[3:]
    if raw_content.endswith("```"):
        raw_content = raw_content[:-3]
    
    raw_content = raw_content.strip()
    
    print(f"DEBUG: LLM Response type: {type(response)}")
    print(f"DEBUG: Raw content (first 500 chars): {raw_content[:500]}")
        
    try:
        structured_data = json.loads(raw_content)
        print(f"DEBUG: Successfully parsed JSON for {report_type}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON from LLM. Error: {e}")
        print(f"DEBUG: Raw content that failed to parse: {raw_content}")
        structured_data = {
            "Summary": "Error extracting data.",
            "Disclaimer": "This interpretation is based on extracted report data and may not reflect clinically verified ranges. Consult a healthcare professional."
        }
        
    # 6. Safety check for Lab Reports (Calculate High/Low/Normal in Python)
    if report_type == "lab" and "Lab Results" in structured_data:
        structured_data["Lab Results"] = analyze_lab_results(structured_data["Lab Results"], ocr_text)
        structured_data["Disclaimer"] = (
            "This interpretation is based on extracted report data and may not reflect clinically verified ranges. "
            "Consult a healthcare professional."
        )

    if "Disclaimer" not in structured_data:
        structured_data["Disclaimer"] = (
            "This interpretation is based on extracted report data and may not reflect clinically verified ranges. "
            "Consult a healthcare professional."
        )
    if report_type == "prescription":
        structured_data = enrich_prescription_with_fda(structured_data, fda_data_list)
        structured_data = ensure_prescription_fields(structured_data)

    return structured_data

def extract_drug_names_from_ocr(ocr_text: str) -> List[str]:
    """
    Uses GPT-4o to identify potential drug names from raw OCR text to query OpenFDA.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    system_prompt = """
    Extract a list of drug/medicine names from the following OCR'd medical text.
    Prioritize medicine tokens appearing after labels like "Medication", "Medicine", "Drug", "Rx", or "Tab".
    Keep only medicine names (remove strength like 500mg, dosage instructions, and quantity counts).
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
