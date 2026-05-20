from flask import Blueprint, request, jsonify
from api.auth_routes import token_required
from api.utils import api_response, log_audit
from db import supabase
from tasks.worker import generate_image_task
from celery.result import AsyncResult
from api.rate_limit import limit_api_rate, limit_ai_rate

bp = Blueprint('ai', __name__, url_prefix='/api')

@bp.route('/tasks/<task_id>/generate', methods=['POST'])
@token_required
@limit_api_rate()
@limit_ai_rate()
def generate_image(current_user, task_id):
    try:
        data = request.json
        if not data or not data.get('image_type') or not data.get('prompt'):
            return api_response(False, "Missing required fields", status=400)
            
        image_type = data['image_type']
        prompt = data['prompt']
        angle = data.get('angle')
        
        task_res = supabase.table('tasks').select('*').eq('id', task_id).execute().data
        if not task_res:
            return api_response(False, "Task not found", status=404)
        task = task_res[0]
        
        job = generate_image_task.delay(task_id, image_type, prompt, task['product_image_url'], angle)
        log_audit(current_user['id'], "image_generation_started", "tasks", task_id, {"job_id": job.id, "image_type": image_type, "angle": angle})
        
        return api_response(True, "Job queued", data={"job_id": job.id, "status": "processing"})
    except Exception as e:
        return api_response(False, "Failed to start generation", error=str(e), status=500)

@bp.route('/jobs/<job_id>/status', methods=['GET'])
@token_required
@limit_api_rate()
def job_status(current_user, job_id):
    try:
        res = AsyncResult(job_id)
        if res.ready():
            if res.successful():
                return api_response(True, "Job completed", data={"status": "completed", "result": res.result})
            else:
                return api_response(True, "Job failed", data={"status": "failed", "error": str(res.result)})
        else:
            return api_response(True, "Job processing", data={"status": "processing"})
    except Exception as e:
        return api_response(False, "Failed to check status", error=str(e), status=500)

@bp.route('/tasks/<task_id>/generations', methods=['GET'])
@token_required
@limit_api_rate()
def get_generations(current_user, task_id):
    try:
        gens = supabase.table('generated_images').select('*').eq('task_id', task_id).order('created_at', desc=True).execute().data
        return api_response(True, "Generations retrieved", data=gens)
    except Exception as e:
        return api_response(False, "Failed to fetch generations", error=str(e), status=500)

@bp.route('/generations/<gen_id>', methods=['DELETE'])
@token_required
@limit_api_rate()
def delete_generation(current_user, gen_id):
    try:
        supabase.table('generated_images').delete().eq('id', gen_id).execute()
        log_audit(current_user['id'], "generation_deleted", "generated_images", gen_id)
        return api_response(True, "Generation deleted")
    except Exception as e:
        return api_response(False, "Failed to delete generation", error=str(e), status=500)

@bp.route('/tasks/<task_id>/fallback', methods=['POST'])
@token_required
@limit_api_rate()
def fallback_generation(current_user, task_id):
    try:
        data = request.json
        if not data or not data.get('image_type') or not data.get('file_name'):
            return api_response(False, "Missing required fields", status=400)
            
        image_type = data['image_type']
        angle = data.get('angle')
        file_name = data['file_name']
        
        gen = supabase.table('generated_images').insert({
            "task_id": task_id,
            "image_type": image_type,
            "image_url": f"/generated_samples/{file_name}",
            "prompt_used": f"Fallback demo generation for {image_type}",
            "metadata": {"source": "demo_seed"},
            "angle": angle,
            "is_final": True
        }).execute().data[0]
        
        log_audit(current_user['id'], "fallback_generation_used", "tasks", task_id, {"image_type": image_type})
        
        return api_response(True, "Fallback generated", data=gen)
    except Exception as e:
        return api_response(False, "Failed to create fallback", error=str(e), status=500)
