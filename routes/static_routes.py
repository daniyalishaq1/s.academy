# routes/static_routes.py
from flask import Blueprint, send_from_directory
from auth import require_auth

# Create blueprint
static_bp = Blueprint('static', __name__)

@static_bp.route('/')
@require_auth
def serve_index():
    """Serve the main index.html file"""
    return send_from_directory('static', 'index.html')

@static_bp.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@static_bp.route('/static/images/<path:filename>')
def serve_images(filename):
    """Serve static image files"""
    return send_from_directory('static/images', filename)