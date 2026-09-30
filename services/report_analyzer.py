import os
import re
import pymupdf

PARAMETERS = [
    "Hemoglobin",
    "RBC Count",
    "WBC Count",
    "Platelet Count",
    "Glucose (Fasting)",
    "Creatinine",
    "Urea",
    "Total Cholesterol",
    "HDL Cholesterol",
    "LDL Cholesterol",
    "Triglycerides",
    "ALT (SGPT)",
    "AST (SGOT)",
    "Total Bilirubin"
]

def extract_report_text(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError("Report file not found")

    document = pymupdf.open(file_path)
    text = []

    for page in document:
        text.append(page.get_text())

    document.close()

    return "\n".join(text).strip()

def extract_parameters(text):
    results = []
    lines = text.splitlines()
    normalized_lines = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if (
            line.endswith("-")
            and i + 1 < len(lines)
            and re.match(r'^\d', lines[i + 1].strip())
        ):
            line = line + " " + lines[i + 1].strip()
            i += 1

        normalized_lines.append(line)
        i += 1

    number = r'[-+]?\d[\d,]*(?:\.\d+)?'

    for line in normalized_lines:
        for parameter in PARAMETERS:
            if line.lower().startswith(parameter.lower()):
                match = re.search(
                    rf'({number})\s*([a-zA-Z/%µ]+(?:/[a-zA-Z]+)?)?.*?Reference Range:\s*({number})\s*-\s*({number})',
                    line,
                    re.IGNORECASE
                )

                if match:
                    value = float(match.group(1).replace(',', ''))
                    unit = match.group(2) or ""
                    low = float(match.group(3).replace(',', ''))
                    high = float(match.group(4).replace(',', ''))

                    if value < low:
                        status = "Low"
                    elif value > high:
                        status = "High"
                    else:
                        status = "Normal"

                    results.append({
                        "parameter": parameter,
                        "value": value,
                        "unit": unit,
                        "reference_low": low,
                        "reference_high": high,
                        "status": status
                    })

                break

    return results

def analyze_report(file_path):
    text = extract_report_text(file_path)
    parameters = extract_parameters(text)

    if not parameters:
        return {
            "summary": "No supported medical parameters were detected in this report.",
            "key_metrics": [],
            "flags": []
        }

    normal_count = sum(
        1 for item in parameters
        if item["status"] == "Normal"
    )

    high_count = sum(
        1 for item in parameters
        if item["status"] == "High"
    )

    low_count = sum(
        1 for item in parameters
        if item["status"] == "Low"
    )

    flags = [
        item for item in parameters
        if item["status"] in ["High", "Low"]
    ]

    summary = (
        f"{len(parameters)} parameters were analyzed. "
        f"{normal_count} are within the stated reference ranges, "
        f"{high_count} are above range, and "
        f"{low_count} are below range."
    )

    return {
        "summary": summary,
        "key_metrics": parameters,
        "flags": flags
    }