from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import Medication, HealthScore, ChatLog, SymptomLog
from extensions import db
from services.chatbot import ask_chatbot_structured
import random
import re

api_bp = Blueprint('api', __name__)


# ---------------------------------------------------------------------------
# Cheap local checks (no Gemini)
# ---------------------------------------------------------------------------

def normalize(text):
    return text.lower().replace('’', "'").strip()


def first_name(user):
    parts = (user.name or '').split()
    return parts[0] if parts else 'there'


# A message made ONLY of these words is treated as basic chat.
BASIC_WORDS = {
    'hi', 'hello', 'hey', 'good', 'morning', 'afternoon', 'evening', 'night',
    'thanks', 'thank', 'thx', 'you', 'so', 'much', 'thats', 'helpful',
    'great', 'awesome', 'nice', 'cool', 'ok', 'okay',
    'bye', 'goodbye', 'see', 'later'
}
BYE_WORDS = {'bye', 'goodbye', 'night', 'later'}
THANKS_WORDS = {'thanks', 'thank', 'thx', 'helpful', 'great', 'awesome',
                'nice', 'cool', 'ok', 'okay', 'thats'}


def basic_reply(message, user):
    """Local reply for greetings / thanks / acknowledgements / bye, else None."""
    words = re.sub(r"[^\w\s]", "", normalize(message)).split()

    if not words or len(words) > 5 or not set(words) <= BASIC_WORDS:
        return None

    name = first_name(user)

    if BYE_WORDS & set(words):
        return f"Take care, {name}! 👋 I'm here whenever you need me."

    if THANKS_WORDS & set(words):
        return f"You're welcome, {name}! 😊 I'm always here to support your health journey."

    return f"Hello {name}! 👋 How can I help you today?"


EMERGENCY_KEYWORDS = [
    'chest pain',
    'chest pressure',
    'difficulty breathing',
    'shortness of breath',
    'cannot breathe',
    "can't breathe",
    'unconscious',
    'fainting',
    'severe bleeding',
    'ambulance',
    'medical emergency',
    'heart attack',
    'stroke'
]

# Matched keywords that are not symptoms and should not be saved as one.
NON_SYMPTOM_EMERGENCY = {'ambulance', 'medical emergency', 'heart attack', 'stroke'}

FIRST_PERSON = re.compile(
    r"\b(i have|i've|i am|i'm|im|i feel|i'm having|i'm experiencing|i am having|i am experiencing)\b"
)

EMERGENCY_RESPONSE = (
    "🚨 This could be a medical emergency. Please call 112 or go to the nearest "
    "emergency department right now. Do not wait to see if it passes. "
    "If you can, ask someone nearby to stay with you until help arrives."
)


def emergency_matches(text):
    return [k for k in EMERGENCY_KEYWORDS if k in text]


# Questions answered from the user's own HealthAI data (existing handlers).
DATA_KEYWORDS = [
    'my health score',
    'my medications',
    'my medication',
    'my medicine',
    'my appointment',
    'my bmi',
    'what am i taking',
    'what medicine am i taking'
]


def is_app_data_question(text):
    return any(k in text for k in DATA_KEYWORDS)


def build_symptom_log(user_id, message, symptoms, duration, severity, urgency):
    return SymptomLog(
        user_id=user_id,
        symptoms=symptoms,
        duration=duration,
        severity=severity,
        urgency_level=urgency,
        notes=f"Reported via chatbot: {message}"[:1000]
    )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@api_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({
            'response': 'Please enter a message so I can help you.'
        }), 400

    text = normalize(message)
    symptom_log = None

    matched = emergency_matches(text)
    local = None if matched else basic_reply(message, current_user)

    if matched:
        # Emergency: deterministic, never waits for Gemini
        intent = 'emergency'
        response = EMERGENCY_RESPONSE

        if FIRST_PERSON.search(text):
            symptoms = [k for k in matched if k not in NON_SYMPTOM_EMERGENCY]
            if symptoms:
                symptom_log = build_symptom_log(
                    current_user.id, message, ', '.join(symptoms),
                    None, None, 'emergency'
                )

    elif local:
        # Basic conversation: no Gemini call
        intent = 'basic'
        response = local

    elif is_app_data_question(text):
        # Existing health score / medications / BMI / appointment handlers
        intent = 'data'
        response = generate_response(text, current_user, intent)

    else:
        # Meaningful message: ONE Gemini call (reply + personal-health extraction)
        intent = 'general'
        try:
            result = ask_chatbot_structured(message[:1000])
            response = result['response']

            health = result['health_data']
            if result['is_personal_health'] and health:
                intent = 'personal'
                symptom_log = build_symptom_log(
                    current_user.id, message,
                    health['symptoms'], health['duration'],
                    health['severity'], health['urgency_level']
                )
        except Exception as e:
            # Gemini disabled / failed: fall back to the old canned answers
            print("CHATBOT GEMINI ERROR:", e)
            response = generate_response(text, current_user, intent)

    print("CHAT INTENT:", intent)

    user_log = ChatLog(
        user_id=current_user.id,
        message=message,
        role='user'
    )

    bot_log = ChatLog(
        user_id=current_user.id,
        message=response,
        response=response,
        role='assistant'
    )

    try:
        db.session.add_all([user_log, bot_log])
        if symptom_log:
            db.session.add(symptom_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("CHAT LOG SAVE ERROR:", e)

    return jsonify({
        'response': response,
        'intent': intent
    })


# ---------------------------------------------------------------------------
# Existing rule-based responses (unchanged). Now used for the data questions
# above and as the fallback when Gemini is unavailable.
# ---------------------------------------------------------------------------

def generate_response(msg, user, intent):

    # Greeting
    if any(k in msg for k in ['hello', 'hi ', 'hey', 'good morning', 'good evening']):
        return f"Hello {user.name.split()[0]}! 👋 I'm your AI health assistant. I can help with symptoms, medications, health tips, and more. What's on your mind?"

    # Emergency — check before general symptom keywords
    if any(k in msg for k in [
        'emergency',
        'ambulance',
        'urgent',
        '112',
        '108',
        'heart attack',
        'stroke',
        'chest pain',
        'chest pressure',
        'difficulty breathing',
        'shortness of breath',
        'cannot breathe',
        "can't breathe",
        'unconscious',
        'fainting',
        'severe bleeding'
    ]):
        return "🚨 If you are experiencing a medical emergency such as severe chest pain, difficulty breathing, or loss of consciousness, call 112 immediately or seek emergency medical care."

    # General health questions
    if 'what is fever' in msg or 'what are fever' in msg:
        return "Fever is a temporary increase in body temperature, often caused by an infection or illness. It is a symptom rather than a disease itself."

    if 'what causes fever' in msg:
        return "Fever can occur when the body responds to infections such as viral or bacterial infections. Other causes are also possible."

    if 'what is bmi' in msg:
        return "BMI is a measure calculated from height and weight that is commonly used as a general indicator of weight status."

    # Medications
    if any(k in msg for k in [
        'medication',
        'medicine',
        'pill',
        'tablet',
        'capsule',
        'dose'
    ]):
        meds = Medication.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()

        if meds:
            med_list = ', '.join(
                [f"{m.name} ({m.dosage})" for m in meds[:5]]
            )

            return f"You have {len(meds)} active medication(s): {med_list}. Remember to log them daily for adherence tracking! Head to the Medications page to mark today's doses."

        return "You have no active medications logged yet. Add them in the Medications section to start tracking your adherence."

    # Personal symptoms
    if any(k in msg for k in [
        'symptom',
        'pain',
        'fever',
        'sick',
        'ill',
        'hurt',
        'ache',
        'cough',
        'headache',
        'nausea'
    ]):
        return "Sounds like you're not feeling well. Please use the Health Check tool for a detailed analysis of your symptoms. If your symptoms are severe or become an emergency, seek medical care immediately."

    # Health score
    if any(k in msg for k in [
        'score',
        'health score',
        'wellness score'
    ]):
        latest = HealthScore.query.filter_by(
            user_id=user.id
        ).order_by(
            HealthScore.computed_at.desc()
        ).first()

        if latest:
            level = (
                'Excellent'
                if latest.score >= 80
                else (
                    'Good'
                    if latest.score >= 65
                    else (
                        'Fair'
                        if latest.score >= 50
                        else 'Needs Attention'
                    )
                )
            )

            return f"Your current health score is {latest.score}/100 — {level}. {'Keep maintaining your healthy habits! 🌟' if latest.score >= 75 else 'Check your dashboard for specific recommendations to improve it.'}"

        return "Your health score is computed from medication adherence, BMI, and symptom history. Log your daily medications and complete your profile for an accurate score!"

    # Appointments
    if any(k in msg for k in [
        'appointment',
        'doctor',
        'book',
        'schedule',
        'consult'
    ]):
        return "You can book a doctor appointment in the Emergency & Quick Actions section. For help choosing an appropriate specialist, please consult a qualified healthcare professional."

    # BMI
    if any(k in msg for k in [
        'bmi',
        'weight',
        'overweight',
        'obesity'
    ]):
        bmi = user.bmi

        if bmi:
            if bmi < 18.5:
                return f"Your BMI is {bmi} (Underweight). Consider consulting a nutritionist to reach a healthy weight with a balanced diet."

            if bmi <= 24.9:
                return f"Your BMI is {bmi} — that's in the Normal range. Keep maintaining healthy habits."

            if bmi <= 29.9:
                return f"Your BMI is {bmi} (Overweight). Regular physical activity and balanced nutrition can support healthy weight management."

            return f"Your BMI is {bmi} (Obese). Consider discussing your health and weight-management options with a qualified healthcare professional."

        return "I can't calculate your BMI yet. Please update your height and weight in Profile Settings."

    # Diet and nutrition
    if any(k in msg for k in [
        'diet',
        'food',
        'nutrition',
        'eat',
        'meal'
    ]):
        tips = [
            "🥗 Aim for a varied diet with plenty of vegetables, fruits, whole grains, and suitable protein sources.",
            "🌾 Whole grains such as brown rice and oats can be part of a balanced diet.",
            "🥚 Include suitable protein sources such as lentils, eggs, fish, or chicken according to your dietary preferences.",
            "💧 Staying hydrated throughout the day supports normal body functions."
        ]

        return random.choice(tips)

    # Exercise
    if any(k in msg for k in [
        'exercise',
        'workout',
        'fitness',
        'physical activity',
        'steps'
    ]):
        return "🏃 Regular physical activity can support cardiovascular health, mood, and sleep. Start with manageable activities such as walking and gradually build consistency."

    # Sleep
    if any(k in msg for k in [
        'sleep',
        'insomnia',
        'rest',
        'tired',
        'fatigue'
    ]):
        return "😴 Most adults need around 7–9 hours of sleep. A consistent sleep schedule, a comfortable sleep environment, and limiting screens before bed can support better sleep."

    # Stress and mental wellbeing
    if any(k in msg for k in [
        'stress',
        'anxiety',
        'mental health',
        'depressed',
        'worry',
        'overwhelm'
    ]):
        return "🧘 Mental wellbeing is an important part of overall health. Activities such as deep breathing, journaling, regular movement, and talking with someone you trust may help. If you're consistently struggling, consider speaking with a qualified mental health professional."

    # Blood pressure
    if any(k in msg for k in [
        'blood pressure',
        'bp',
        'hypertension'
    ]):
        return "Blood pressure is typically recorded using two numbers, such as systolic and diastolic pressure. Regular monitoring and discussing persistent abnormal readings with a healthcare professional can help manage blood pressure."

    # Diabetes
    if any(k in msg for k in [
        'diabetes',
        'sugar',
        'glucose',
        'insulin'
    ]):
        return "For diabetes management, follow your healthcare professional's advice, monitor blood glucose as recommended, maintain a balanced diet, stay active, and take prescribed medications as directed."

    # Thanks
    if any(k in msg for k in [
        'thank',
        'thanks',
        'awesome',
        'great',
        'helpful'
    ]):
        return f"You're welcome, {user.name.split()[0]}! 😊 I'm always here to support your health journey."

    # General tips
    if any(k in msg for k in [
        'tip',
        'advice',
        'suggest',
        'recommend'
    ]):
        tips = [
            "💧 Stay hydrated throughout the day.",
            "🚶 Regular walking or other enjoyable physical activity can support overall health.",
            "😴 Keep a consistent sleep and wake schedule when possible.",
            "🥗 Include a variety of fruits and vegetables in your meals.",
            "🧘 Taking a few minutes for slow breathing or relaxation can help manage everyday stress."
        ]

        return random.choice(tips)

    # Fallback
    return "I'm your AI health assistant! I can help with symptom information, medications, health score insights, wellness tips, and emergency guidance. Try asking something like 'What is fever?', 'What is my health score?', or 'Give me a health tip!'"