import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_ENABLED = os.getenv("GEMINI_ENABLED", "false").lower() == "true"
client = None
if GEMINI_ENABLED :
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "A concise overall explanation of the report findings."
        },
        "interpretations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "parameter": {
                        "type": "string"
                    },
                    "explanation": {
                        "type": "string"
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "parameter",
                    "explanation",
                    "recommendations"
                ]
            }
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "summary",
        "interpretations",
        "recommendations"
    ]
}


def interpret_report_with_ai(key_metrics):
    if not GEMINI_ENABLED:
        raise RuntimeError("Gemini AI is disabled")

    prompt = f"""
You are assisting a healthcare application with educational interpretation of
laboratory report results.

The application has already extracted the laboratory parameters and compared
each value with the reference range stated in the report.

Your job is ONLY to explain the findings in clear, patient-friendly language.

IMPORTANT:
- Do not diagnose diseases.
- Do not prescribe medicines.
- Do not recommend starting, stopping, or changing medication.
- Do not invent reference ranges.
- Do not contradict the supplied status.
- Treat the supplied laboratory reference ranges as authoritative for this report.
- Explain what an abnormal parameter generally represents and why the user may
  want to discuss it with a qualified healthcare professional.
- Recommendations must be general follow-up guidance, not treatment advice.
- If a result is normal, do not unnecessarily create a concerning interpretation.
- Keep explanations concise.

Report findings:
{json.dumps(key_metrics, indent=2)}

Return the requested JSON structure.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=REPORT_SCHEMA
        )
    )

    return json.loads(response.text)

def generate_fallback_interpretation(key_metrics):
    interpretations = []
    abnormal = []

    fallback_guidance = {
        "hemoglobin": {
            "low": [
                "Discuss the low hemoglobin result with a healthcare professional.",
                "Review your dietary iron and overall nutritional intake with a professional if appropriate.",
                "Ask whether repeat testing or additional evaluation is needed."
            ],
            "high": [
                "Discuss the elevated hemoglobin result with a healthcare professional.",
                "Review the result together with your hydration status and other health information.",
                "Ask whether repeat testing or further evaluation is appropriate."
            ]
        },
        "glucose (fasting)": {
            "high": [
                "Discuss the elevated fasting glucose result with a healthcare professional.",
                "Review your recent blood glucose results and overall health history with them.",
                "Maintain balanced nutrition and regular physical activity as appropriate for you."
            ],
            "low": [
                "Discuss the low fasting glucose result with a healthcare professional.",
                "Review any symptoms or circumstances around the test with them.",
                "Ask whether repeat testing or further evaluation is appropriate."
            ]
        },
        "total cholesterol": {
            "high": [
                "Discuss the elevated cholesterol result with a healthcare professional.",
                "Review your overall lipid profile rather than considering this value alone.",
                "Discuss dietary habits and regular physical activity with a healthcare professional."
            ]
        },
        "ldl cholesterol": {
            "high": [
                "Discuss the elevated LDL result with a healthcare professional.",
                "Review the complete lipid profile and relevant health factors with them.",
                "Discuss appropriate nutrition and physical activity habits with a professional."
            ]
        },
        "triglycerides": {
            "high": [
                "Discuss the elevated triglyceride result with a healthcare professional.",
                "Review the complete lipid profile and relevant health factors with them.",
                "Discuss appropriate dietary and lifestyle habits with a professional."
            ]
        },
        "creatinine": {
            "high": [
                "Discuss the elevated creatinine result with a healthcare professional.",
                "Review this result together with your other kidney-related test results.",
                "Ask whether repeat testing or additional evaluation is appropriate."
            ],
            "low": [
                "Discuss the low creatinine result with a healthcare professional if it persists.",
                "Review the result together with your overall health and nutritional status.",
                "Ask whether any follow-up testing is appropriate."
            ]
        },
        "wbc count": {
            "high": [
                "Discuss the elevated WBC count with a healthcare professional.",
                "Review the result together with your symptoms and other blood test findings.",
                "Ask whether repeat testing or further evaluation is appropriate."
            ],
            "low": [
                "Discuss the low WBC count with a healthcare professional.",
                "Review the result together with your symptoms and other blood test findings.",
                "Ask whether repeat testing or further evaluation is appropriate."
            ]
        },
        "platelet count": {
            "high": [
                "Discuss the elevated platelet count with a healthcare professional.",
                "Review the result together with your other blood test findings.",
                "Ask whether repeat testing or further evaluation is appropriate."
            ],
            "low": [
                "Discuss the low platelet count with a healthcare professional.",
                "Review the result together with your other blood test findings.",
                "Ask whether repeat testing or further evaluation is appropriate."
            ]
        }
    }

    for metric in key_metrics:
        parameter = metric["parameter"]
        status = metric["status"]

        explanation = (
            f"{parameter} is {status.lower()} compared with the "
            f"reference range stated in the uploaded report."
        )

        recommendations = []

        if status in ["High", "Low"]:
            abnormal.append(parameter)

            parameter_key = parameter.lower()
            status_key = status.lower()

            recommendations = fallback_guidance.get(
                parameter_key, {}
            ).get(status_key, [
                f"Discuss the {status.lower()} {parameter} result with a healthcare professional.",
                "Review this result together with your other report findings and relevant health information.",
                "Ask whether repeat testing or further evaluation is appropriate."
            ])

            explanation += (
                " A result outside the stated reference range can have "
                "different possible causes and should be interpreted in "
                "the context of the person's overall health."
            )

        interpretations.append({
            "parameter": parameter,
            "explanation": explanation,
            "recommendations": recommendations
        })

    if abnormal:
        summary = (
            f"The report contains {len(abnormal)} parameter(s) outside "
            f"the reference ranges stated in the report: "
            f"{', '.join(abnormal)}."
        )
        overall_recommendations = [
            "Discuss the abnormal findings with a qualified healthcare professional.",
            "Consider the results together with your symptoms, medical history, and other test findings.",
            "Ask whether repeat testing or further evaluation is appropriate."
        ]
    else:
        summary = (
            "The analyzed parameters are within the reference ranges "
            "stated in the uploaded report."
        )
        overall_recommendations = [
            "Continue routine health monitoring as appropriate.",
            "Discuss any persistent symptoms or concerns with a healthcare professional."
        ]

    return {
        "summary": summary,
        "interpretations": interpretations,
        "recommendations": overall_recommendations
    }