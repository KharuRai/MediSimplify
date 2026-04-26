import requests
import urllib.parse
from typing import Dict, Any, List

def get_fda_drug_data(drug_name: str) -> List[Dict[str, Any]]:
    """
    Queries the OpenFDA API for a given drug name.
    Returns a list of label data results if found, or an empty list if not found or on error.
    """
    # Clean the drug name for search
    encoded_name = urllib.parse.quote(drug_name)
    url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:\"{encoded_name}\"&limit=3"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            return data["results"]
        return []
    except requests.exceptions.RequestException as e:
        print(f"FDA API Request failed for drug {drug_name}: {e}")
        return []
