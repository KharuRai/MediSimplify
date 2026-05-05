import re
from typing import Dict, Optional, Tuple

UNIT_ALIASES = {
    "g/dl": "g/dL",
    "mg/dl": "mg/dL",
    "mmol/l": "mmol/L",
    "µmol/l": "µmol/L",
    "umol/l": "µmol/L",
    "x10^3/ul": "10^3/uL",
    "10^3/ul": "10^3/uL",
    "k/ul": "10^3/uL",
    "10^3/μl": "10^3/uL",
    "cells/mm3": "cells/mm3",
    "/cmm": "cells/mm3",
    "%": "%"
}

COMMON_LAB_RANGES = {
    "hemoglobin": {
        "g/dL": (13.0, 17.0),
        "g/L": (130.0, 170.0),
    },
    "wbc": {
        "10^3/uL": (4.0, 11.0),
        "cells/mm3": (4000.0, 11000.0),
    },
    "platelets": {
        "10^3/uL": (150.0, 450.0),
        "cells/mm3": (150000.0, 450000.0),
    },
    "glucose": {
        "mg/dL": (70.0, 100.0),
        "mmol/L": (3.9, 5.6),
    },
    "creatinine": {
        "mg/dL": (0.6, 1.3),
    },
}

UNIT_CONVERSIONS = {
    ("mg/dL", "mmol/L", "glucose"): lambda v: v / 18.0,
    ("mmol/L", "mg/dL", "glucose"): lambda v: v * 18.0,
}

UNIT_PATTERN = re.compile(r"\b(?:g/dL|mg/dL|mmol/L|µmol/L|umol/L|x10\^3/uL|10\^3/uL|K/µL|cells/mm3|/cmm|%)\b", re.IGNORECASE)


def normalize_unit(unit: str) -> Optional[str]:
    if not unit:
        return None
    normalized = unit.strip().lower().replace("μ", "u")
    normalized = normalized.replace("µ", "u")
    normalized = normalized.replace("micro", "u")
    normalized = normalized.replace("µl", "uL")
    normalized = normalized.replace("μl", "uL")
    normalized = re.sub(r"\s+", "", normalized)
    return UNIT_ALIASES.get(normalized, unit.strip())


def normalize_test_name(test_name: str) -> Optional[str]:
    if not test_name:
        return None
    name = test_name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    name = name.strip()
    if "hemoglobin" in name or "hb" == name:
        return "hemoglobin"
    if "white blood cell" in name or "wbc" in name:
        return "wbc"
    if "platelet" in name:
        return "platelets"
    if "glucose" in name or "blood sugar" in name:
        return "glucose"
    if "creatinine" in name:
        return "creatinine"
    return None


def get_clinical_range(test_name: str, unit: Optional[str] = None) -> Optional[Dict[str, Tuple[float, float]]]:
    canonical = normalize_test_name(test_name)
    if not canonical:
        return None

    ranges = COMMON_LAB_RANGES.get(canonical)
    if not ranges:
        return None

    if unit:
        unit_normalized = normalize_unit(unit)
        if unit_normalized in ranges:
            min_val, max_val = ranges[unit_normalized]
            return {
                "test_name": canonical,
                "unit": unit_normalized,
                "min_value": min_val,
                "max_value": max_val,
            }

    # Fall back to the first known unit if none matched.
    default_unit, (min_val, max_val) = next(iter(ranges.items()))
    return {
        "test_name": canonical,
        "unit": default_unit,
        "min_value": min_val,
        "max_value": max_val,
    }


def convert_value_to_unit(value: float, from_unit: str, to_unit: str, test_name: str) -> Optional[float]:
    normalized_from = normalize_unit(from_unit)
    normalized_to = normalize_unit(to_unit)
    if normalized_from == normalized_to:
        return value

    converter = UNIT_CONVERSIONS.get((normalized_from, normalized_to, normalize_test_name(test_name)))
    if converter:
        try:
            return converter(value)
        except Exception:
            return None
    return None


def format_range(min_value: float, max_value: float, unit: Optional[str] = None) -> str:
    if unit:
        return f"{min_value:g} - {max_value:g} {unit}"
    return f"{min_value:g} - {max_value:g}"


def detect_units_in_text(text: str) -> Dict[str, str]:
    matches = UNIT_PATTERN.findall(text or "")
    return {match.strip(): match.strip() for match in matches}
