from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import Medication, MedicationLog
from app import db
from datetime import datetime, timedelta, date
import json

medications_bp = Blueprint('medications', __name__)

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

@medications_bp.route('/medications')
@login_required
def medications():
    active_meds = Medication.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    inactive_meds = Medication.query.filter_by(
        user_id=current_user.id,
        is_active=False
    ).all()

    today = (datetime.utcnow() + timedelta(hours=5, minutes=30)).date()

    start_of_day = datetime.combine(
        today,
        datetime.min.time()
    ) - timedelta(hours=5, minutes=30)

    end_of_day = start_of_day + timedelta(days=1)

    today_logs = MedicationLog.query.filter(
        MedicationLog.user_id == current_user.id,
        MedicationLog.logged_at >= start_of_day,
        MedicationLog.logged_at < end_of_day
    ).all()

    logged_today = {}
    for log in today_logs:
        if log.medication_id not in logged_today:
            logged_today[log.medication_id] = {}
        dose = log.scheduled_time or 'Daily'
        logged_today[log.medication_id][dose] = log.status

    # Adherence stats (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    all_logs = MedicationLog.query.filter(
        MedicationLog.user_id == current_user.id,
        MedicationLog.logged_at >= thirty_days_ago
    ).all()

    adherence_rate = 0
    if all_logs:
        taken = sum(1 for log in all_logs if log.status == 'taken')
        adherence_rate = round((taken / len(all_logs)) * 100, 1)

    # Weekly chart data
    week_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_logs = [log for log in all_logs if log.logged_at.date() == day]

        taken = sum(1 for log in day_logs if log.status == 'taken')
        missed = sum(1 for log in day_logs if log.status == 'missed')

        week_data.append({
            'date': day.strftime('%a'),
            'taken': taken,
            'missed': missed
        })

    return render_template(
        'medications.html',
        active_meds=active_meds,
        inactive_meds=inactive_meds,
        logged_today=logged_today,
        adherence_rate=adherence_rate,
        week_data=json.dumps(week_data),
        get_dose_labels=get_dose_labels
    )

@medications_bp.route('/api/medications/add', methods=['POST'])
@login_required
def add_medication():
    data = request.get_json()

    med = Medication(
        user_id=current_user.id,
        name=data.get('name'),
        dosage=data.get('dosage'),
        frequency=data.get('frequency'),
        timing=data.get('timing'),
        notes=data.get('notes', '')
    )

    if data.get('start_date'):
        med.start_date = datetime.strptime(
            data['start_date'],
            '%Y-%m-%d'
        ).date()

    if data.get('end_date'):
        med.end_date = datetime.strptime(
            data['end_date'],
            '%Y-%m-%d'
        ).date()

    db.session.add(med)
    db.session.commit()

    return jsonify({
        'success': True,
        'id': med.id,
        'name': med.name
    })

@medications_bp.route('/api/medications/<int:med_id>/log', methods=['POST'])
@login_required
def log_medication(med_id):
    data = request.get_json()
    status = data.get('status', 'taken')
    dose = data.get('dose', 'Daily')

    med = Medication.query.filter_by(
        id=med_id,
        user_id=current_user.id,
        is_active=True
    ).first_or_404()

    today = (datetime.utcnow() + timedelta(hours=5, minutes=30)).date()

    start_of_day = datetime.combine(
        today,
        datetime.min.time()
    ) - timedelta(hours=5, minutes=30)

    end_of_day = start_of_day + timedelta(days=1)

    existing_log = MedicationLog.query.filter(
        MedicationLog.medication_id == med.id,
        MedicationLog.user_id == current_user.id,
        MedicationLog.scheduled_time == dose,
        MedicationLog.logged_at >= start_of_day,
        MedicationLog.logged_at < end_of_day
    ).first()

    if existing_log:
        existing_log.status = status
        existing_log.logged_at = datetime.utcnow()
    else:
        log = MedicationLog(
            medication_id=med.id,
            user_id=current_user.id,
            status=status,
            scheduled_time=dose,
            notes=data.get('notes', '')
        )
        db.session.add(log)

    db.session.commit()

    return jsonify({
        'success': True,
        'status': status,
        'dose': dose
    })

@medications_bp.route('/api/medications/<int:med_id>/delete', methods=['DELETE'])
@login_required
def delete_medication(med_id):
    med = Medication.query.filter_by(
        id=med_id,
        user_id=current_user.id
    ).first_or_404()

    med.is_active = False
    db.session.commit()

    return jsonify({'success': True})