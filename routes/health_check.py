from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import SymptomLog, ReportLog
from app import db
from datetime import datetime
from services.report_analyzer import analyze_report
from services.report_ai import interpret_report_with_ai, generate_fallback_interpretation
import os, uuid, json
import joblib

health_check_bp = Blueprint('health_check', __name__)

UPLOAD_FOLDER = 'uploads'

def load_symptom_model():
    model_path = os.path.join(current_app.root_path, 'ml', 'symptom_model.pkl')
    vectorizer_path = os.path.join(current_app.root_path, 'ml', 'tfidf_vectorizer.pkl')

    model = joblib.load(model_path)
    vectorizer = joblib.load(vectorizer_path)

    return model, vectorizer

def get_recommendations(condition, symptoms, severity, urgency):
    """Generate general guidance based on condition, symptoms and severity."""

    recommendations = []
    condition_lower = condition.lower()
    symptoms_lower = symptoms.lower()

    if urgency == 'emergency':
        recommendations.append(
            'Seek emergency medical attention immediately.'
        )
        return recommendations

    if urgency == 'high':
        recommendations.append(
            'Seek medical attention promptly, especially if your symptoms worsen.'
        )

    if 'dengue' in condition_lower:
        recommendations.append(
            'Stay well hydrated and get adequate rest.'
        )
        recommendations.append(
            'Monitor your fever and other symptoms closely and consult a healthcare professional.'
        )

    elif 'gastroesophageal reflux' in condition_lower or 'gerd' in condition_lower:
        recommendations.append(
            'Avoid meals that appear to trigger your symptoms and avoid lying down immediately after eating.'
        )
        recommendations.append(
            'Consider discussing persistent or recurring symptoms with a healthcare professional.'
        )

    elif 'migraine' in condition_lower:
        recommendations.append(
            'Rest in a quiet environment and maintain adequate fluid intake.'
        )
        recommendations.append(
            'Consult a healthcare professional if headaches are severe, frequent, or worsening.'
        )

    elif 'urinary tract infection' in condition_lower or 'uti' in condition_lower:
        recommendations.append(
            'Maintain adequate fluid intake and monitor your symptoms.'
        )
        recommendations.append(
            'Consult a healthcare professional for appropriate evaluation, especially if symptoms persist or worsen.'
        )

    elif 'common cold' in condition_lower:
        recommendations.append(
            'Get adequate rest and maintain good fluid intake.'
        )
        recommendations.append(
            'Seek medical advice if symptoms become severe or do not improve.'
        )

    elif 'allergy' in condition_lower:
        recommendations.append(
            'Try to identify and avoid possible triggers that worsen your symptoms.'
        )
        recommendations.append(
            'Consult a healthcare professional if symptoms are persistent or severe.'
        )

    elif 'pneumonia' in condition_lower:
        recommendations.append(
            'Monitor your breathing, fever, and overall condition closely.'
        )
        recommendations.append(
            'Seek medical evaluation, particularly if symptoms are worsening.'
        )

    elif 'asthma' in condition_lower:
        recommendations.append(
            'Avoid known triggers and monitor your breathing closely.'
        )
        recommendations.append(
            'Seek medical attention if breathing difficulty increases.'
        )

    elif 'hypertension' in condition_lower:
        recommendations.append(
            'Monitor your blood pressure regularly and discuss persistent high readings with a healthcare professional.'
        )

    elif 'diabetes' in condition_lower:
        recommendations.append(
            'Monitor your symptoms and maintain regular health check-ups.'
        )
        recommendations.append(
            'Discuss persistent or concerning symptoms with a healthcare professional.'
        )

    elif 'psoriasis' in condition_lower:
        recommendations.append(
            'Avoid scratching irritated skin and monitor changes in the affected areas.'
        )
        recommendations.append(
            'Consult a healthcare professional if the skin condition persists or worsens.'
        )

    elif 'peptic ulcer' in condition_lower:
        recommendations.append(
            'Monitor for worsening abdominal pain or other concerning symptoms.'
        )
        recommendations.append(
            'Consult a healthcare professional for persistent or recurring symptoms.'
        )

    elif 'uncertain classification' in condition_lower:
        matched_category = False

    # Headache-related symptoms
        if any(keyword in symptoms_lower for keyword in [
            'headache',
            'head pain',
            'throbbing head'
        ]):
            matched_category = True

            recommendations.append(
                'Rest in a quiet environment and maintain adequate fluid intake.'
            )
            recommendations.append(
                'Monitor the headache and seek medical evaluation if it becomes severe, persistent, or worsens.'
            )

        # Fever-related symptoms
        if any(keyword in symptoms_lower for keyword in [
            'fever',
            'high temperature',
            'chills'
        ]):
            matched_category = True

            recommendations.append(
                'Monitor your temperature, get adequate rest, and maintain good fluid intake.'
            )
            recommendations.append(
                'Seek medical evaluation if the fever is persistent, very high, or accompanied by worsening symptoms.'
            )

        # Cough / respiratory symptoms
        if any(keyword in symptoms_lower for keyword in [
            'cough',
            'sore throat',
            'runny nose',
            'congestion',
            'wheezing'
        ]):
            matched_category = True

            recommendations.append(
                'Get adequate rest and maintain good fluid intake while monitoring your symptoms.'
            )
            recommendations.append(
                'Consult a healthcare professional if breathing difficulty develops or symptoms worsen.'
            )

        # Stomach / digestive symptoms
        if any(keyword in symptoms_lower for keyword in [
            'stomach pain',
            'abdominal pain',
            'nausea',
            'vomiting',
            'diarrhea',
            'indigestion',
            'stomach discomfort'
        ]):
            matched_category = True

            recommendations.append(
                'Stay hydrated and monitor your digestive symptoms closely.'
            )
            recommendations.append(
                'Consult a healthcare professional if symptoms persist, become severe, or worsen.'
            )

        # Skin symptoms
        if any(keyword in symptoms_lower for keyword in [
            'rash',
            'itchy skin',
            'red patches',
            'skin irritation',
            'dry skin',
            'scales'
        ]):
            matched_category = True

            recommendations.append(
                'Avoid scratching or irritating the affected skin and monitor any changes.'
            )
            recommendations.append(
                'Consider consulting a healthcare professional if the skin changes persist or worsen.'
            )

        # Urinary symptoms
        if any(keyword in symptoms_lower for keyword in [
            'burning urination',
            'burning when urinating',
            'painful urination',
            'pain when urinating',
            'frequent urination',
            'urinate frequently',
            'urinating frequently',
            'urine'
        ]):
            matched_category = True

            recommendations.append(
                'Maintain adequate fluid intake and monitor your symptoms.'
            )
            recommendations.append(
                'Consult a healthcare professional if urinary symptoms persist or worsen.'
            )

    # General uncertain case
        if not matched_category:
            recommendations.append(
                'Monitor your symptoms and keep track of any changes.'
            )
            recommendations.append(
                'Consult a healthcare professional if your symptoms persist or worsen.'
            )

    return recommendations


def ai_analyze_symptoms(symptoms, duration, severity):
    """ML-based symptom analysis with rule-based safety checks."""

    model, vectorizer = load_symptom_model()
    symptoms_tfidf = vectorizer.transform([symptoms])
    prediction = model.predict(symptoms_tfidf)[0]
    probabilities = model.predict_proba(symptoms_tfidf)[0]
    confidence = probabilities.max()
    symptoms_lower = symptoms.lower()
    conditions = []
    urgency = 'low'

    # Convert severity safely
    try:
        severity = int(severity)
    except (ValueError, TypeError):
        severity = 0

    if confidence >= 0.30:
        conditions.append({
            'name': prediction,
            'probability': f'{confidence:.0%}',
            'type': 'ml_prediction'
        })

        predicted_condition = prediction

    else:
        conditions.append({
            'name': 'Uncertain classification',
            'probability': f'{confidence:.0%}',
            'type': 'uncertain'
        })

        predicted_condition = 'Uncertain classification'

    if any(keyword in symptoms_lower for keyword in [
        'chest pain',
        'chest pressure',
        'left arm pain',
        'jaw pain'
    ]):
        urgency = 'emergency'

    elif any(keyword in symptoms_lower for keyword in [
        'shortness of breath',
        'difficulty breathing',
        'breathless'
    ]):
        urgency = 'high'

    elif any(keyword in symptoms_lower for keyword in [
        'sudden severe headache',
        'worst headache',
        'thunderclap headache'
    ]):
        urgency = 'high'

    if severity >= 9 and urgency == 'low':
        urgency = 'high'

    elif severity >= 7 and urgency == 'low':
        urgency = 'medium'

    recommendations = get_recommendations(
        predicted_condition,
        symptoms,
        severity,
        urgency
    )

    summary = (
        f"Based on your reported symptoms ({symptoms[:100]}...) "
        f"with severity {severity}/10 lasting {duration}, "
        f"the ML model identified {len(conditions)} possible condition(s)."
    )

    return {
        'conditions': conditions,
        'urgency': urgency,
        'recommendations': recommendations,
        'summary': summary,
        'disclaimer': (
            'This analysis is AI-generated and not a medical diagnosis. '
            'Always consult a qualified healthcare professional.'
        )
    }

@health_check_bp.route('/health-check')
@login_required
def health_check():
    from models import SymptomLog, ReportLog

    symptom_history = SymptomLog.query.filter_by(user_id=current_user.id)\
        .order_by(SymptomLog.logged_at.desc()).limit(15).all()
    report_history = ReportLog.query.filter_by(user_id=current_user.id)\
        .order_by(ReportLog.logged_at.desc()).limit(10).all()
    return render_template(
        'health_check.html',
        symptom_history=symptom_history,
        report_history=report_history
    )

@health_check_bp.route('/api/analyze-symptoms', methods=['POST'])
@login_required
def analyze_symptoms():
    data = request.get_json()
    symptoms = data.get('symptoms', '')
    duration = data.get('duration', '')
    severity = data.get('severity', 5)
    subject = data.get('subject', 'me')

    if subject not in ('me', 'other'):
        subject = 'me'
    
    result = ai_analyze_symptoms(symptoms, duration, severity)
    
    log_id = None

    if subject == 'me':
        log = SymptomLog(
            user_id=current_user.id,
            symptoms=symptoms,
            duration=duration,
            severity=int(severity),
            ai_analysis=result['summary'],
            possible_conditions=json.dumps(result['conditions']),
            urgency_level=result['urgency']
        )
        db.session.add(log)
        db.session.commit()
        log_id = log.id
    
    return jsonify({'success': True, 'result': result, 'log_id': log.id})

@health_check_bp.route('/api/analyze-report', methods=['POST'])
@login_required
def analyze_report_route():
    if 'report' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})

    file = request.files['report']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})

    filename = f"{uuid.uuid4()}_{file.filename}"
    upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
    os.makedirs(upload_path, exist_ok=True)

    report_path = os.path.join(upload_path, filename)
    file.save(report_path)

    result = analyze_report(report_path)

    try:
        ai_result = interpret_report_with_ai(result['key_metrics'])
        analysis_source = 'gemini'
    except Exception:
        ai_result = generate_fallback_interpretation(result['key_metrics'])
        analysis_source = 'fallback'

    ai_by_parameter = {
        item['parameter']: item
        for item in ai_result['interpretations']
    }

    enriched_metrics = []

    for metric in result['key_metrics']:
        interpretation = ai_by_parameter.get(metric['parameter'], {})

        enriched_metric = {
            **metric,
            'ai_explanation': interpretation.get('explanation', ''),
            'recommendations': interpretation.get('recommendations', [])
        }

        enriched_metrics.append(enriched_metric)

    result['summary'] = ai_result['summary']
    result['key_metrics'] = enriched_metrics
    result['ai_recommendations'] = ai_result['recommendations']
    result['analysis_source'] = analysis_source

    log = ReportLog(
        user_id=current_user.id,
        filename=filename,
        report_type=request.form.get('report_type', 'General'),
        ai_summary=result['summary'],
        key_metrics=json.dumps(result['key_metrics']),
        flags=json.dumps(result['flags'])
    )

    db.session.add(log)
    db.session.commit()

    return jsonify({
        'success': True,
        'result': result,
        'log_id': log.id
    })