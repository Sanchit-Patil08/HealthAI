import os
import json
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

CHATBOT_GEMINI_ENABLED = os.getenv(
    "CHATBOT_GEMINI_ENABLED",
    "false"
).lower() == "true"

client = None

if CHATBOT_GEMINI_ENABLED:
    api_key = os.getenv("CHATBOT_GEMINI_API_KEY")

    if api_key:
        client = genai.Client(api_key=api_key)


CHATBOT_SYSTEM_INSTRUCTION = """
You are the AI health assistant inside HealthAI, a healthcare application.

Your role is to provide clear, educational, patient-friendly health information.

Important rules:
- Do not diagnose diseases.
- Do not prescribe medicines.
- Do not tell users to start, stop, or change medication.
- Do not present possibilities as confirmed diagnoses.
- Encourage consultation with a qualified healthcare professional when appropriate.
- For potentially serious symptoms, advise appropriate medical attention.
- Keep responses concise and easy to understand.
- Do not claim to have examined the user.
- Do not invent personal health information.
"""


# Used only by the structured chat call below.
CHATBOT_STRUCTURED_INSTRUCTION = CHATBOT_SYSTEM_INSTRUCTION + """

Also fill in the JSON fields as follows:
- response: your reply to the user.
- is_personal_health: true ONLY if the user describes their OWN current or recent
  symptoms or health condition (e.g. "I've had a fever since yesterday").
  false for general questions ("What is fever?", "What causes headaches?"),
  questions about other people, or hypotheticals.
- health_data: null when is_personal_health is false. Otherwise:
  - symptoms: short comma-separated list in the user's own words. No diagnoses.
  - duration: exactly what the user said (e.g. "since yesterday", "past week"),
    or null if they did not say.
  - severity: an integer 1-10 ONLY if the user explicitly gave a number,
    otherwise null. Never guess it.
  - urgency_level: one of low, medium, high, emergency, based on the symptoms described.
- If urgency_level is high or emergency, the response must advise seeking
  medical care promptly.
"""

VALID_URGENCY = {"low", "medium", "high", "emergency"}


class HealthData(BaseModel):
    symptoms: str
    duration: Optional[str]
    severity: Optional[int]
    urgency_level: str


class ChatbotReply(BaseModel):
    response: str
    is_personal_health: bool
    health_data: Optional[HealthData]


def ask_gemini(message):
    if not CHATBOT_GEMINI_ENABLED or client is None:
        raise RuntimeError("Chatbot Gemini AI is disabled or not configured")

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=CHATBOT_SYSTEM_INSTRUCTION,
            temperature=0.4,
            max_output_tokens=500
        )
    )

    return response.text.strip()


def ask_chatbot_structured(message):
    """
    ONE Gemini call returning the reply plus personal-health extraction.

    Returns:
        {
          'response': str,
          'is_personal_health': bool,
          'health_data': {symptoms, duration, severity, urgency_level} or None
        }
    Raises on any failure so the caller can fall back.
    """
    if not CHATBOT_GEMINI_ENABLED or client is None:
        raise RuntimeError("Chatbot Gemini AI is disabled or not configured")

    result = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=CHATBOT_STRUCTURED_INSTRUCTION,
            temperature=0.4,
            max_output_tokens=800,
            response_mime_type="application/json",
            response_schema=ChatbotReply
        )
    )

    data = json.loads(result.text)

    reply = (data.get("response") or "").strip()
    if not reply:
        raise ValueError("Empty chatbot response")

    health = data.get("health_data") if data.get("is_personal_health") else None
    cleaned = None

    if isinstance(health, dict):
        symptoms = (health.get("symptoms") or "").strip()

        if symptoms:
            severity = health.get("severity")
            if isinstance(severity, bool) or not isinstance(severity, int) or not 1 <= severity <= 10:
                severity = None

            duration = (health.get("duration") or "").strip()[:50] or None

            urgency = health.get("urgency_level")
            if urgency not in VALID_URGENCY:
                urgency = None

            cleaned = {
                "symptoms": symptoms,
                "duration": duration,
                "severity": severity,
                "urgency_level": urgency
            }

    return {
        "response": reply,
        "is_personal_health": cleaned is not None,
        "health_data": cleaned
    }