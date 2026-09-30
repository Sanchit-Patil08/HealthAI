from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models import SymptomLog, MedicationLog, Medication, HealthScore, ReportLog, Appointment, ChatLog
from extensions import db
from services.health_insights import generate_health_insights
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)

def get_dose_labels(med):
    if med.frequency == 'Once daily':
        return [med.timing or 'Daily']
    if med.frequency == 'Twice daily':
        if med.timing == 'Morning & Night':
            return ['Morning', 'Night']
        if med.timing == 'Morning & Evening':
            return ['Morning', 'Evening']
        return ['Dose 1', 'Dose 2']
    if med.frequency == 'Three times daily':
        if med.timing == 'Morning, Afternoon & Night':
            return ['Morning', 'Afternoon', 'Night']
        return ['Dose 1', 'Dose 2', 'Dose 3']
    if med.frequency == 'Every 8 hours':
        return ['Dose 1', 'Dose 2', 'Dose 3']
    if med.frequency == 'Weekly':
        return ['Weekly']
    return ['As needed']

def compute_health_score(user):
    score = 75.0
    factors = []
    week_ago = datetime.utcnow() - timedelta(days=7)

    # Medication adherence
    med_logs = MedicationLog.query.filter(
        MedicationLog.user_id == user.id,
        MedicationLog.logged_at >= week_ago
    ).all()

    if med_logs:
        taken = sum(1 for log in med_logs if log.status == 'taken')
        missed = sum(1 for log in med_logs if log.status == 'missed')
        total = taken + missed

        if total > 0:
            adherence = taken / total

            if adherence >= 0.8:
                score += 10
                status = 'good'
            elif adherence >= 0.5:
                status = 'warning'
            else:
                score -= 10
                status = 'danger'

            factors.append({
                'label': 'Medication Adherence',
                'value': f'{int(adherence * 100)}%',
                'status': status
            })

    # BMI
    bmi = user.bmi

    if bmi:
        if 18.5 <= bmi <= 24.9:
            status = 'good'
        elif 25 <= bmi <= 29.9:
            score -= 5
            status = 'warning'
        else:
            score -= 10
            status = 'danger'

        factors.append({
            'label': 'BMI',
            'value': str(bmi),
            'status': status
        })

    # Recent symptoms
    recent_symptoms = SymptomLog.query.filter(
        SymptomLog.user_id == user.id,
        SymptomLog.logged_at >= week_ago
    ).all()

    symptom_count = len(recent_symptoms)
    high_severity = sum(
        1 for symptom in recent_symptoms
        if symptom.severity and symptom.severity >= 7
    )

    if high_severity > 0:
        score -= 10
        factors.append({
            'label': 'Symptom Severity',
            'value': f'{high_severity} high-severity log(s)',
            'status': 'danger'
        })
    elif symptom_count >= 3:
        score -= 5
        factors.append({
            'label': 'Recent Symptoms',
            'value': f'{symptom_count} logs',
            'status': 'warning'
        })
    elif symptom_count > 0:
        factors.append({
            'label': 'Recent Symptoms',
            'value': f'{symptom_count} log(s)',
            'status': 'good'
        })

    score = max(10, min(100, round(score, 1)))

    # Save only one health score per day
    today = datetime.utcnow().date()
    existing_score = HealthScore.query.filter(
        HealthScore.user_id == user.id,
        db.func.date(HealthScore.computed_at) == today
    ).first()

    if existing_score:
        existing_score.score = score
        existing_score.factors = json.dumps(factors)
    else:
        hs = HealthScore(
            user_id=user.id,
            score=score,
            factors=json.dumps(factors)
        )
        db.session.add(hs)

    db.session.commit()

    return score, factors

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    # Health score
    score, factors = compute_health_score(current_user)

    # Data-driven health insights
    health_insights = generate_health_insights(current_user)

    # Recent symptoms
    recent_symptoms = SymptomLog.query.filter_by(user_id=current_user.id)\
        .order_by(SymptomLog.logged_at.desc()).limit(5).all()

    # Active medications
    active_meds = Medication.query.filter_by(user_id=current_user.id, is_active=True).all()

    # Today's medication status
    today = (datetime.utcnow() + timedelta(hours=5, minutes=30)).date()

    start_of_day = datetime.combine(today, datetime.min.time()) - timedelta(hours=5, minutes=30)
    end_of_day = start_of_day + timedelta(days=1)

    today_logs = MedicationLog.query.filter(
        MedicationLog.user_id == current_user.id,
        MedicationLog.logged_at >= start_of_day,
        MedicationLog.logged_at < end_of_day
    ).all()

    logged_med_ids = {}

    for log in today_logs:
        if log.medication_id not in logged_med_ids:
            logged_med_ids[log.medication_id] = {}

        dose = log.scheduled_time or 'Daily'
        logged_med_ids[log.medication_id][dose] = log.status

    # Recent reports
    recent_reports = ReportLog.query.filter_by(user_id=current_user.id)\
        .order_by(ReportLog.logged_at.desc()).limit(3).all()

    # Upcoming appointments
    upcoming = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.appointment_date >= datetime.utcnow(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date).limit(3).all()

    # Health score trend
    raw_history = HealthScore.query.filter_by(user_id=current_user.id)\
        .order_by(HealthScore.computed_at.desc()).limit(7).all()
    raw_history.reverse()

    score_history = [
        {
            "score": s.score,
            "date": s.computed_at.isoformat() if s.computed_at else None
        }
        for s in raw_history
    ]   

    # Alerts
    alerts = []
    missed_today = [m for m in active_meds if m.id not in logged_med_ids]
    if missed_today:
        alerts.append({
            'type': 'warning',
            'icon': 'capsule',
            'title': 'Medications Due',
            'message': f'{len(missed_today)} medication(s) not logged today',
            'action': 'medications'
        })

    high_severity = [s for s in recent_symptoms if s.severity and s.severity >= 7]
    if high_severity:
        alerts.append({
            'type': 'danger',
            'icon': 'activity',
            'title': 'High Severity Symptoms',
            'message': f'You logged high-severity symptoms recently. Consider consulting a doctor.',
            'action': 'emergency'
        })

    if score < 50:
        alerts.append({
            'type': 'danger',
            'icon': 'heart-pulse',
            'title': 'Low Health Score',
            'message': 'Your health score needs attention. Review your trends.',
            'action': 'dashboard'
        })

    return render_template('dashboard.html',
        score=score,
        factors=factors,
        recent_symptoms=recent_symptoms,
        active_meds=active_meds,
        logged_med_ids=logged_med_ids,
        recent_reports=recent_reports,
        upcoming=upcoming,
        score_history=score_history,
        alerts=alerts,
        health_insights=health_insights,
        get_dose_labels=get_dose_labels
    )
    