import re
import requests
from typing import Dict, Any, List

def get_fda_drug_data(drug_name: str) -> List[Dict[str, Any]]:
    """
    Queries the OpenFDA API for a given drug name.
    Returns a list of label data results if found, or an empty list if not found or on error.
    """
    clean_name = (drug_name or "").strip()
    if not clean_name:
        return []

    # Remove dosage, strength, and form words that may appear in OCR-extracted names.
    clean_name = re.sub(
        r"\b(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|tablet|tab|capsule|cap|drop|spray|unit|IU|tabs|caps))\b",
        "",
        clean_name,
        flags=re.IGNORECASE,
    ).strip()
    clean_name = re.sub(r"\b(hcl|hydrochloride)\b", "", clean_name, flags=re.IGNORECASE).strip()
    clean_name = re.sub(r"\s+", " ", clean_name)
    if not clean_name:
        return []

    # Search brand name, generic name, and substance name sequentially.
    search_fields = [
        f'openfda.generic_name:"{clean_name}"',
        f'openfda.brand_name:"{clean_name}"',
        f'openfda.substance_name:"{clean_name}"',
    ]
    url = "https://api.fda.gov/drug/label.json"
    results = []
    for query in search_fields:
        try:
            response = requests.get(
                url,
                params={"search": query, "limit": 3},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            if "results" in data and data["results"]:
                return data["results"]
        except requests.exceptions.HTTPError as e:
            # If no results found, OpenFDA returns 404; try next query field.
            if response.status_code == 404:
                continue
            print(f"FDA API Request failed for drug {drug_name}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"FDA API Request failed for drug {drug_name}: {e}")
            return []
    return []
