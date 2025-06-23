# app.py
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import openai
from auth import auth_bp, init_oauth
from routes import register_blueprints
import config
from utils.error_handler import setup_error_handlers

# Create Flask application
app = Flask(__name__, static_folder='static')
app.secret_key = config.SECRET_KEY

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Register other blueprints
register_blueprints(app)

# Initialize OAuth
google = init_oauth(app)

# Setup error handlers
setup_error_handlers(app)

# CORS configuration
CORS(app, origins=['*'])  # In production, you might want to restrict this

# Initialize OpenAI
openai.api_key = config.OPENAI_API_KEY

@app.route('/diagnose/mongodb')
def diagnose_mongodb():
    """Diagnostic endpoint for MongoDB connections"""
    from mongodb_diagnostic import test_mongodb_connections
    return jsonify(test_mongodb_connections())

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "message": "Course API is running"})

# --- Legacy routes for backward compatibility ---
@app.route('/get-course-content', methods=['GET'])
def legacy_get_course_content():
    """Redirect to new course content endpoint"""
    from routes.course_routes import get_table_of_contents
    return get_table_of_contents()

@app.route('/get-chapter-content', methods=['POST'])
def legacy_get_chapter_content():
    """Redirect to new chapter content endpoint"""  
    from routes.course_routes import get_chapter_content
    return get_chapter_content()

@app.route('/complete-chapter', methods=['POST'])
def legacy_complete_chapter():
    """Redirect to new complete chapter endpoint"""
    from routes.progress_routes import complete_chapter
    return complete_chapter()

@app.route('/classify-intent', methods=['POST'])
def legacy_classify_intent():
    """Redirect to new classify intent endpoint"""
    from routes.ai_routes import classify_intent
    return classify_intent()

@app.route('/generate-quick-actions', methods=['POST'])
def legacy_generate_quick_actions():
    """Redirect to new generate quick actions endpoint"""
    from routes.ai_routes import generate_quick_actions
    return generate_quick_actions()

@app.route('/ask-question', methods=['POST'])
def legacy_ask_question():
    """Redirect to new ask question endpoint"""
    from routes.ai_routes import ask_question
    return ask_question()

@app.route('/ask-question-stream', methods=['POST'])
def legacy_ask_question_stream():
    """Redirect to new ask question stream endpoint"""
    from routes.ai_routes import ask_question_stream
    return ask_question_stream()

@app.route('/get-user-progress', methods=['GET'])
def legacy_get_user_progress():
    """Redirect to new user progress endpoint"""
    from routes.progress_routes import get_user_progress
    return get_user_progress()

@app.route('/save-progress', methods=['POST'])
def legacy_save_progress():
    """Redirect to new save progress endpoint"""
    from routes.progress_routes import save_progress
    return save_progress()

@app.route('/test-openai')
def legacy_test_openai():
    """Redirect to new test openai endpoint"""
    from routes.ai_routes import test_openai
    return test_openai()

if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)
