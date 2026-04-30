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

    # Search both brand and generic names to improve match rate.
    search_query = (
        f'openfda.brand_name:"{clean_name}"'
        f'+openfda.generic_name:"{clean_name}"'
    )
    url = "https://api.fda.gov/drug/label.json"
    
    try:
        response = requests.get(
            url,
            params={"search": search_query, "limit": 3},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            return data["results"]
        return []
    except requests.exceptions.RequestException as e:
        print(f"FDA API Request failed for drug {drug_name}: {e}")
        return []
