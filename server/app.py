from flask import Flask, jsonify, request
from flask_cors import CORS
from db import supabase

from config import Config

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[Config.FRONTEND_URL, "http://localhost:3000"])

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

# Import routes
from api import auth_routes, task_routes, ai_routes

app.register_blueprint(auth_routes.bp, url_prefix="/api/auth")
app.register_blueprint(task_routes.bp, url_prefix="/api/tasks")
app.register_blueprint(ai_routes.bp)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
