from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from models import Appointment, Document, SymptomLog, Medication, MedicationLog, ReportLog
from extensions import db
from datetime import datetime
import os, uuid, json

emergency_bp = Blueprint('emergency', __name__)
profile_bp = Blueprint('profile', __name__)
api_bp = Blueprint('api', __name__)

# ─── EMERGENCY ────────────────────────────────────────────────────────────────

@emergency_bp.route('/emergency')
@login_required
def emergency():
    appointments = Appointment.query.filter_by(user_id=current_user.id)\
        .order_by(Appointment.appointment_date.desc()).all()
    return render_template('emergency.html', appointments=appointments)

@emergency_bp.route('/api/appointments/book', methods=['POST'])
@login_required
def book_appointment():
    data = request.get_json(silent=True) or {}

    doctor_name = data.get('doctor_name', '').strip()
    specialty = data.get('specialty', '').strip()
    location = data.get('location', '').strip()
    appointment_date = data.get('appointment_date', '').strip()

    if not appointment_date:
        return jsonify({
            'success': False,
            'error': 'Appointment date is required'
        }), 400

    try:
        appointment_datetime = datetime.strptime(
            appointment_date,
            '%Y-%m-%dT%H:%M'
        )
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid appointment date'
        }), 400

    if appointment_datetime < datetime.now():
        return jsonify({
            'success': False,
            'error': 'Appointment date cannot be in the past'
        }), 400

    appt = Appointment(
        user_id=current_user.id,
        doctor_name=doctor_name or 'Available Doctor',
        specialty=specialty or 'General',
        location=location or 'Not specified',
        notes=data.get('notes', '').strip(),
        appointment_date=appointment_datetime
    )

    db.session.add(appt)
    db.session.commit()

    return jsonify({
        'success': True,
        'id': appt.id
    })

@emergency_bp.route('/api/appointments/<int:appt_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appt_id):
    appt = Appointment.query.filter_by(id=appt_id, user_id=current_user.id).first_or_404()
    appt.status = 'cancelled'
    db.session.commit()
    return jsonify({'success': True})

@emergency_bp.route('/api/health-summary')
@login_required
def health_summary():
    user = current_user
    recent_symptoms = SymptomLog.query.filter_by(user_id=user.id).order_by(SymptomLog.logged_at.desc()).limit(3).all()
    active_meds = Medication.query.filter_by(user_id=user.id, is_active=True).all()
    
    summary = {
        'name': user.name,
        'age': user.age,
        'blood_group': user.blood_group,
        'allergies': user.allergies,
        'chronic_conditions': user.chronic_conditions,
        'emergency_contact': user.emergency_contact,
        'emergency_phone': user.emergency_phone,
        'bmi': user.bmi,
        'active_medications': [{'name': m.name, 'dosage': m.dosage, 'frequency': m.frequency} for m in active_meds],
        'recent_symptoms': [{'symptoms': s.symptoms, 'severity': s.severity, 'date': s.logged_at.strftime('%Y-%m-%d')} for s in recent_symptoms]
    }
    return jsonify(summary)

# ─── PROFILE ──────────────────────────────────────────────────────────────────

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        user = current_user
        user.name = request.form.get('name', user.name)
        user.age = request.form.get('age', user.age)
        user.gender = request.form.get('gender', user.gender)
        user.blood_group = request.form.get('blood_group', user.blood_group)
        user.height = request.form.get('height', user.height) or None
        user.weight = request.form.get('weight', user.weight) or None
        user.allergies = request.form.get('allergies', user.allergies)
        user.chronic_conditions = request.form.get('chronic_conditions', user.chronic_conditions)
        user.emergency_contact = request.form.get('emergency_contact', user.emergency_contact)
        user.emergency_phone = request.form.get('emergency_phone', user.emergency_phone)
        user.caregiver_email = request.form.get('caregiver_email', user.caregiver_email)
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile.profile'))

    documents = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.uploaded_at.desc()).all()
    return render_template('profile.html', documents=documents)

@profile_bp.route('/api/documents/upload', methods=['POST'])
@login_required
def upload_document():
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': 'No file'})
    file = request.files['document']
    original_name = secure_filename(file.filename)
    filename = f"{uuid.uuid4()}_{original_name}"
    upload_path = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_path, exist_ok=True)
    file.save(os.path.join(upload_path, filename))
    
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        original_name=original_name,
        doc_type=request.form.get('doc_type', 'Other'),
        notes=request.form.get('notes', '')
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify({'success': True, 'id': doc.id, 'name': file.filename})

@profile_bp.route('/api/documents/<int:doc_id>/delete', methods=['DELETE'])
@login_required
def delete_document(doc_id):
    doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first_or_404()
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'success': True})
