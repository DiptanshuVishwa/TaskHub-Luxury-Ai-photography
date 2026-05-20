from flask import Blueprint, request, jsonify
from api.auth_routes import token_required, admin_required
from api.utils import api_response, log_audit
from db import supabase
from tasks.worker import send_email_task
from api.email_templates import (
    get_task_assigned_email,
    get_task_submitted_email,
    get_task_accepted_email,
    get_task_revision_email
)
import datetime
from api.rate_limit import limit_api_rate

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@bp.route('', methods=['POST'])
@admin_required
@limit_api_rate()
def create_task(current_user):
    try:
        data = request.json
        if not data or not data.get('title') or not data.get('product_image_url'):
            return api_response(False, "Missing required fields", status=400)
            
        new_task = {
            'title': data['title'],
            'description': data.get('description', ''),
            'product_image_url': data['product_image_url'],
            'created_by': current_user['id'],
            'status': 'pending'
        }
        task = supabase.table('tasks').insert(new_task).execute().data[0]
        log_audit(current_user['id'], "task_created", "tasks", task['id'])
        return api_response(True, "Task created", data=task)
    except Exception as e:
        return api_response(False, "Failed to create task", error=str(e), status=500)

@bp.route('', methods=['GET'])
@admin_required
@limit_api_rate()
def get_all_tasks(current_user):
    try:
        tasks = supabase.table('tasks').select('*, users!assigned_to(name, email)').order('created_at', desc=True).execute().data
        return api_response(True, "Tasks retrieved", data=tasks)
    except Exception as e:
        return api_response(False, "Failed to fetch tasks", error=str(e), status=500)

@bp.route('/<task_id>', methods=['GET'])
@token_required
@limit_api_rate()
def get_task(current_user, task_id):
    try:
        task = supabase.table('tasks').select('*, users!assigned_to(name, email)').eq('id', task_id).execute().data
        if not task:
            return api_response(False, "Task not found", status=404)
            
        task_data = task[0]
        
        if current_user['role'] != 'admin' and task_data['assigned_to'] != current_user['id'] and task_data['created_by'] != current_user['id']:
            return api_response(False, "Forbidden", status=403)
            
        return api_response(True, "Task retrieved", data=task_data)
    except Exception as e:
        return api_response(False, "Failed to fetch task", error=str(e), status=500)

@bp.route('/<task_id>/assign', methods=['POST'])
@admin_required
@limit_api_rate()
def assign_task(current_user, task_id):
    try:
        data = request.json
        assigned_to = data.get('user_id')
        if not assigned_to:
            return api_response(False, "User ID is required", status=400)
            
        task = supabase.table('tasks').update({'assigned_to': assigned_to, 'status': 'assigned', 'updated_at': datetime.datetime.utcnow().isoformat()}).eq('id', task_id).execute().data[0]
        log_audit(current_user['id'], "task_assigned", "tasks", task_id, {"assigned_to": assigned_to})
        
        # Trigger email
        user = supabase.table('users').select('email, name').eq('id', assigned_to).execute().data[0]
        html_content = get_task_assigned_email(task['title'], task.get('description'), task['product_image_url'], task['id'])
        send_email_task.delay(user['email'], f"New Task Assigned: {task['title']}", html_content)
        
        return api_response(True, "Task assigned", data=task)
    except Exception as e:
        return api_response(False, "Failed to assign task", error=str(e), status=500)

@bp.route('/my-tasks', methods=['GET'])
@token_required
@limit_api_rate()
def get_my_tasks(current_user):
    try:
        tasks = supabase.table('tasks').select('*').eq('assigned_to', current_user['id']).order('created_at', desc=True).execute().data
        return api_response(True, "Tasks retrieved", data=tasks)
    except Exception as e:
        return api_response(False, "Failed to fetch tasks", error=str(e), status=500)

@bp.route('/<task_id>/start', methods=['PUT'])
@token_required
@limit_api_rate()
def start_task(current_user, task_id):
    try:
        task = supabase.table('tasks').update({'status': 'in_progress', 'updated_at': datetime.datetime.utcnow().isoformat()}).eq('id', task_id).eq('assigned_to', current_user['id']).execute().data
        if not task:
            return api_response(False, "Forbidden or Not found", status=403)
        return api_response(True, "Task started", data=task[0])
    except Exception as e:
        return api_response(False, "Failed to start task", error=str(e), status=500)

@bp.route('/<task_id>/submit', methods=['POST'])
@token_required
@limit_api_rate()
def submit_task(current_user, task_id):
    try:
        images = supabase.table('generated_images').select('image_type, angle').eq('task_id', task_id).execute().data
        
        # Build set of present slots in the format (image_type, angle)
        present_slots = {(img['image_type'], img.get('angle')) for img in images}
        
        required_slots = {
            ('white_background', 'white_background_1'),
            ('theme', 'theme_1'),
            ('theme', 'theme_2'),
            ('creative', 'creative_1'),
            ('creative', 'creative_2'),
            ('model', 'front'),
            ('model', 'side_45'),
            ('model', 'closeup')
        }
        
        missing = required_slots - present_slots
        if missing:
            missing_descriptions = [f"{t.replace('_', ' ')} ({a.replace('_', ' ') if a else 'standard'})" for t, a in missing]
            return api_response(False, f"Fulfillment incomplete. Missing required slots: {', '.join(missing_descriptions)}", status=400)
            
        task = supabase.table('tasks').update({'status': 'submitted', 'updated_at': datetime.datetime.utcnow().isoformat()}).eq('id', task_id).eq('assigned_to', current_user['id']).execute().data[0]
        log_audit(current_user['id'], "task_submitted", "tasks", task_id)
        
        # Trigger email to admin
        admin = supabase.table('users').select('email').eq('role', 'admin').limit(1).execute().data[0]
        html = get_task_submitted_email(task['title'], current_user['name'], task_id)
        send_email_task.delay(admin['email'], f"Task Completed: {task['title']} by {current_user['name']}", html)
        
        return api_response(True, "Task submitted", data=task)
    except Exception as e:
        return api_response(False, "Failed to submit task", error=str(e), status=500)

@bp.route('/<task_id>/accept', methods=['PUT'])
@admin_required
@limit_api_rate()
def accept_task(current_user, task_id):
    try:
        feedback = request.json.get('feedback', 'Great job! All images meet photography standard.') if request.json else 'Great job! All images meet photography standard.'
        task = supabase.table('tasks').update({'status': 'accepted', 'updated_at': datetime.datetime.utcnow().isoformat()}).eq('id', task_id).execute().data[0]
        log_audit(current_user['id'], "task_accepted", "tasks", task_id)
        
        user = supabase.table('users').select('email').eq('id', task['assigned_to']).execute().data[0]
        html = get_task_accepted_email(task['title'], feedback)
        send_email_task.delay(user['email'], f"Task Accepted: {task['title']}", html)
        
        return api_response(True, "Task accepted", data=task)
    except Exception as e:
        return api_response(False, "Failed to accept task", error=str(e), status=500)

@bp.route('/<task_id>/request-revision', methods=['PUT'])
@admin_required
@limit_api_rate()
def request_revision(current_user, task_id):
    try:
        notes = request.json.get('notes', 'Please regenerate incorrect assets.') if request.json else 'Please regenerate incorrect assets.'
        task = supabase.table('tasks').update({'status': 'revision_requested', 'revision_notes': notes, 'updated_at': datetime.datetime.utcnow().isoformat()}).eq('id', task_id).execute().data[0]
        log_audit(current_user['id'], "revision_requested", "tasks", task_id, {"notes": notes})
        
        user = supabase.table('users').select('email').eq('id', task['assigned_to']).execute().data[0]
        html = get_task_revision_email(task['title'], notes)
        send_email_task.delay(user['email'], f"Revision Requested: {task['title']}", html)
        
        return api_response(True, "Revision requested", data=task)
    except Exception as e:
        return api_response(False, "Failed to request revision", error=str(e), status=500)

@bp.route('/<task_id>', methods=['DELETE'])
@admin_required
@limit_api_rate()
def delete_task(current_user, task_id):
    try:
        supabase.table('tasks').delete().eq('id', task_id).execute()
        log_audit(current_user['id'], "task_deleted", "tasks", task_id)
        return api_response(True, "Task deleted")
    except Exception as e:
        return api_response(False, "Failed to delete task", error=str(e), status=500)
