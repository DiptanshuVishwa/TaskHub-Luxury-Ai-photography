from flask import Blueprint, request, jsonify
from api.auth_routes import token_required
from api.utils import api_response, log_audit
from db import supabase
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
        
        job_id = None
        is_simulated = False
        
        from config import Config
        if Config.REDIS_URL:
            try:
                from tasks.worker import generate_image_task
                job = generate_image_task.delay(task_id, image_type, prompt, task['product_image_url'], angle)
                job_id = job.id
            except Exception as queue_err:
                print(f"Warning: Failed to queue task via Celery: {queue_err}")
                is_simulated = True
        else:
            is_simulated = True
            
        if is_simulated:
            import base64
            import json
            import time
            import uuid
            
            job_data = {
                "image_type": image_type,
                "angle": angle,
                "task_id": task_id,
                "created_at": time.time()
            }
            job_id = "sim_" + base64.urlsafe_b64encode(json.dumps(job_data).encode()).decode()
            
        log_audit(current_user['id'], "image_generation_started", "tasks", task_id, {
            "job_id": job_id,
            "image_type": image_type,
            "angle": angle,
            "is_simulated": is_simulated
        })
        
        return api_response(True, "Job queued", data={"job_id": job_id, "status": "processing"})
    except Exception as e:
        return api_response(False, "Failed to start generation", error=str(e), status=500)

@bp.route('/jobs/<job_id>/status', methods=['GET'])
@token_required
@limit_api_rate()
def job_status(current_user, job_id):
    try:
        if job_id.startswith("sim_"):
            import base64
            import json
            import time
            
            try:
                encoded_data = job_id[4:]
                padding = len(encoded_data) % 4
                if padding:
                    encoded_data += '=' * (4 - padding)
                job_data = json.loads(base64.urlsafe_b64decode(encoded_data.encode()).decode())
                image_type = job_data["image_type"]
                angle = job_data["angle"]
                task_id = job_data["task_id"]
                created_at = job_data["created_at"]
            except Exception as decode_err:
                return api_response(False, "Invalid simulated job ID", error=str(decode_err), status=400)
                
            elapsed = time.time() - created_at
            if elapsed < 6.0:
                return api_response(True, "Job processing", data={"status": "processing"})
                
            try:
                existing = supabase.table('generated_images').select('*').eq('task_id', task_id).eq('image_type', image_type).eq('angle', angle).execute().data
                if existing:
                    gen_record = existing[0]
                else:
                    def map_to_fallback_file(img_type, ang):
                        if img_type == 'white_background' or ang == 'white_background_1':
                            return '01-white-background.png'
                        elif ang == 'theme_1':
                            return '02-marble-luxury.png'
                        elif ang == 'theme_2':
                            return '03-velvet-luxury.png'
                        elif ang == 'creative_1':
                            return '04-beach-luxury.png'
                        elif ang == 'creative_2':
                            return '05-cinematic-editorial.png'
                        elif ang == 'front' or ang == 'model_1':
                            return '06-model-front.png'
                        elif ang == 'side_45' or ang == 'model_2':
                            return '07-model-side.png'
                        elif ang == 'closeup' or ang == 'model_3':
                            return '08-model-closeup.png'
                        return '01-white-background.png'
                        
                    file_name = map_to_fallback_file(image_type, angle)
                    image_url = f"/generated_samples/{file_name}"
                    prompt_used = f"High-fidelity AI photo of jewelry, {image_type} background, {angle or 'default'} view"
                    
                    res_insert = supabase.table('generated_images').insert({
                        "task_id": task_id,
                        "image_type": image_type,
                        "image_url": image_url,
                        "prompt_used": prompt_used,
                        "metadata": {"source": "simulated_worker"},
                        "angle": angle,
                        "is_final": True
                    }).execute()
                    
                    gen_record = res_insert.data[0] if (res_insert and hasattr(res_insert, 'data') and res_insert.data) else {"image_url": image_url}
                    
                return api_response(True, "Job completed", data={
                    "status": "completed",
                    "result": {"status": "success", "url": gen_record.get("image_url", f"/generated_samples/01-white-background.png")}
                })
            except Exception as db_err:
                return api_response(False, "Database execution error during simulation", error=str(db_err), status=500)
        else:
            try:
                from celery.result import AsyncResult
                res = AsyncResult(job_id)
                if res.ready():
                    if res.successful():
                        return api_response(True, "Job completed", data={"status": "completed", "result": res.result})
                    else:
                        return api_response(True, "Job failed", data={"status": "failed", "error": str(res.result)})
                else:
                    return api_response(True, "Job processing", data={"status": "processing"})
            except Exception as celery_err:
                print(f"Warning: Celery/Redis exception during status check: {celery_err}")
                return api_response(True, "Job failed", data={
                    "status": "failed",
                    "error": f"Celery broker is unavailable: {str(celery_err)}"
                })
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
