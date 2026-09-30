from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from models import Document
from extensions import db
import os, uuid

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        u = current_user
        u.name = request.form.get('name') or u.name
        u.age = request.form.get('age') or u.age
        u.gender = request.form.get('gender') or u.gender
        u.blood_group = request.form.get('blood_group') or u.blood_group
        h = request.form.get('height')
        w = request.form.get('weight')
        u.height = float(h) if h else u.height
        u.weight = float(w) if w else u.weight
        u.allergies = request.form.get('allergies', u.allergies)
        u.chronic_conditions = request.form.get('chronic_conditions', u.chronic_conditions)
        u.emergency_contact = request.form.get('emergency_contact', u.emergency_contact)
        u.emergency_phone = request.form.get('emergency_phone', u.emergency_phone)
        u.caregiver_email = request.form.get('caregiver_email', u.caregiver_email)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.profile'))

    documents = Document.query.filter_by(user_id=current_user.id)\
        .order_by(Document.uploaded_at.desc()).all()
    return render_template('profile.html', documents=documents)

@profile_bp.route('/api/documents/upload', methods=['POST'])
@login_required
def upload_document():
    if 'document' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})
    file = request.files['document']
    if not file.filename:
        return jsonify({'success': False, 'error': 'No file selected'})
    filename = f"{uuid.uuid4()}_{file.filename}"
    upload_path = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_path, exist_ok=True)
    file.save(os.path.join(upload_path, filename))
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        original_name=file.filename,
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
    try:
        file_path = os.path.join(current_app.root_path, 'uploads', doc.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'success': True})