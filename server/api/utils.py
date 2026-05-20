from flask import jsonify
from db import supabase
from functools import wraps
from flask import request

def api_response(success=True, message="", data=None, error=None, status=200):
    return jsonify({
        "success": success,
        "message": message,
        "data": data,
        "error": error
    }), status

def log_audit(user_id, action, table_name, record_id, changes=None):
    try:
        supabase.table('audit_logs').insert({
            "user_id": user_id,
            "action": action,
            "table_name": table_name,
            "record_id": record_id,
            "changes": changes or {}
        }).execute()
    except Exception as e:
        print(f"Failed to log audit: {e}")
