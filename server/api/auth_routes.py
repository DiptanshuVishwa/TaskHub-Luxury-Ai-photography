from flask import Blueprint, request, make_response
import jwt
import datetime
from config import Config
from db import supabase
from functools import wraps
from api.utils import api_response, log_audit

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def generate_jwt(user):
    payload = {
        'sub': user['id'],
        'email': user['email'],
        'role': user['role'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return api_response(False, "Token is missing", error="unauthorized", status=401)
        try:
            data = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            user_res = supabase.table('users').select('*').eq('id', data['sub']).execute()
            if not user_res.data:
                return api_response(False, "User not found", error="unauthorized", status=401)
            current_user = user_res.data[0]
        except Exception as e:
            return api_response(False, "Token is invalid or expired", error=str(e), status=401)
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user['role'] != 'admin':
            return api_response(False, "Admin privilege required", error="forbidden", status=403)
        return f(current_user, *args, **kwargs)
    return decorated

@bp.route('/oauth/callback', methods=['POST'])
def oauth_callback():
    try:
        data = request.json
        if not data or not data.get('email'):
            return api_response(False, "Email is required", status=400)
            
        email = data.get('email')
        name = data.get('name', 'Unknown')
        avatar_url = data.get('avatar_url')
        provider = data.get('provider', 'oauth')
        user_id = data.get('id')

        # Robust user resolution and account linking to prevent duplicate key or email violations
        user = None
        user_by_id = None
        if user_id:
            id_res = supabase.table('users').select('*').eq('id', user_id).execute()
            if id_res.data:
                user_by_id = id_res.data[0]

        email_res = supabase.table('users').select('*').eq('email', email).execute()
        user_by_email = email_res.data[0] if email_res.data else None

        if user_by_id:
            # User exists by ID. Update their profile details
            user = user_by_id
            updates = {}
            if user.get('email') != email:
                updates['email'] = email
            if user.get('name') != name:
                updates['name'] = name
            if avatar_url and user.get('avatar_url') != avatar_url:
                updates['avatar_url'] = avatar_url
            if provider and user.get('oauth_provider') != provider:
                updates['oauth_provider'] = provider
            
            if updates:
                user = supabase.table('users').update(updates).eq('id', user['id']).execute().data[0]
        elif user_by_email:
            # User exists by email. To avoid foreign key violations, keep existing ID but link details
            user = user_by_email
            updates = {}
            if user.get('name') != name:
                updates['name'] = name
            if avatar_url and user.get('avatar_url') != avatar_url:
                updates['avatar_url'] = avatar_url
            if provider and user.get('oauth_provider') != provider:
                updates['oauth_provider'] = provider
            
            if updates:
                user = supabase.table('users').update(updates).eq('id', user['id']).execute().data[0]
        else:
            # Brand new user
            new_user = {
                'email': email,
                'name': name,
                'avatar_url': avatar_url,
                'oauth_provider': provider,
                'role': 'admin' if 'admin' in email.lower() else 'user'
            }
            if user_id:
                new_user['id'] = user_id
                
            user = supabase.table('users').insert(new_user).execute().data[0]
            log_audit(user['id'], "user_created", "users", user['id'])

        # Auto-seed a luxury watch campaign for the user if they don't have any tasks assigned
        try:
            tasks_res = supabase.table('tasks').select('id').eq('assigned_to', user['id']).execute()
            if not tasks_res.data:
                # Find admin to act as created_by
                admin_res = supabase.table('users').select('*').eq('role', 'admin').limit(1).execute()
                admin_id = admin_res.data[0]['id'] if admin_res.data else user['id']
                
                # Create Task
                task_data = {
                    "title": "Luxury Watch Campaign",
                    "description": "Generate high-quality luxury photos of this gold watch.",
                    "product_image_url": "/generated_samples/01-white-background.png",
                    "status": "in_progress",
                    "created_by": admin_id,
                    "assigned_to": user['id']
                }
                task = supabase.table('tasks').insert(task_data).execute().data[0]
                
                # Insert 8 Seeded Images
                seeded_images = [
                    {"file": "01-white-background.png", "type": "white_background", "angle": "white_background_1"},
                    {"file": "02-marble-luxury.png", "type": "theme", "angle": "theme_1"},
                    {"file": "03-velvet-luxury.png", "type": "theme", "angle": "theme_2"},
                    {"file": "04-beach-luxury.png", "type": "creative", "angle": "creative_1"},
                    {"file": "05-cinematic-editorial.png", "type": "creative", "angle": "creative_2"},
                    {"file": "06-model-front.png", "type": "model", "angle": "front"},
                    {"file": "07-model-side.png", "type": "model", "angle": "side_45"},
                    {"file": "08-model-closeup.png", "type": "model", "angle": "closeup"},
                ]
                
                for img in seeded_images:
                    supabase.table('generated_images').insert({
                        "task_id": task['id'],
                        "image_type": img['type'],
                        "image_url": f"/generated_samples/{img['file']}",
                        "prompt_used": f"Seeded demo generation for {img['type']}",
                        "metadata": {"source": "demo_seed"},
                        "angle": img['angle'],
                        "is_final": True
                    }).execute()
                
                print(f"Successfully auto-seeded luxury watch campaign for user {user['id']}")
        except Exception as e:
            print(f"Failed to auto-seed user campaign: {e}")

        token = generate_jwt(user)
        log_audit(user['id'], "user_login", "users", user['id'])
        
        resp_data, status = api_response(True, "Login successful", data={"user": user})
        resp = make_response(resp_data)
        resp.status_code = status
        resp.set_cookie('token', token, httponly=True, samesite='Lax', secure=False, max_age=7*24*60*60)
        return resp
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("OAuth Exception traceback:")
        print(tb)
        return api_response(False, "OAuth failed", error=tb, status=500)

@bp.route('/me', methods=['GET'])
@token_required
def get_me(current_user):
    return api_response(True, "Current user retrieved", data={"user": current_user})

@bp.route('/logout', methods=['POST'])
def logout():
    resp_data, status = api_response(True, "Logout successful")
    resp = make_response(resp_data)
    resp.status_code = status
    resp.delete_cookie('token')
    return resp

@bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    try:
        users = supabase.table('users').select('id, email, name, avatar_url, role').execute().data
        return api_response(True, "Users retrieved", data=users)
    except Exception as e:
        return api_response(False, "Failed to retrieve users", error=str(e), status=500)

@bp.route('/demo-login', methods=['POST'])
def demo_login():
    try:
        role = request.json.get('role', 'user')
        email = f"demo_{role}@taskhub.com"
        user_res = supabase.table('users').select('*').eq('email', email).execute()
        if len(user_res.data) == 0:
            return api_response(False, "Demo user not found. Please run seed script.", status=404)
            
        user = user_res.data[0]
        token = generate_jwt(user)
        log_audit(user['id'], "demo_login", "users", user['id'])
        
        resp_data, status = api_response(True, "Demo Login successful", data={"user": user})
        resp = make_response(resp_data)
        resp.status_code = status
        resp.set_cookie('token', token, httponly=True, samesite='Lax', secure=False, max_age=7*24*60*60)
        return resp
    except Exception as e:
        return api_response(False, "Login failed", error=str(e), status=500)
