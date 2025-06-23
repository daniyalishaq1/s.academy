# app.py
import os
import ssl
from flask import Flask, jsonify, request
from flask_cors import CORS
import openai
from auth import auth_bp, init_oauth
from routes import register_blueprints
import config
from utils.error_handler import setup_error_handlers
from datetime import datetime
import pymongo

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
    results = {
        "timestamp": datetime.now().isoformat(),
        "python_ssl": ssl.OPENSSL_VERSION,
        "pymongo_version": pymongo.__version__,
        "render_env": os.environ.get('RENDER', 'false'),
        "methods_tested": [],
        "successful_methods": []
    }
    
    # Get MongoDB URI
    uri = config.MONGODB_URI
    
    # Make sure we don't log the password
    safe_uri = uri
    if '@' in uri:
        prefix, suffix = uri.split('@', 1)
        if ':' in prefix:
            user_part = prefix.split(':', 1)[0]
            safe_uri = f"{user_part}:***@{suffix}"
    
    results["uri_format"] = safe_uri
    
    # Test methods
    connection_methods = [
        {
            "name": "Standard connection",
            "options": {},
            "uri_modifier": None
        },
        {
            "name": "TLS with validation disabled",
            "options": {"tls": True, "tlsAllowInvalidCertificates": True},
            "uri_modifier": None
        },
        {
            "name": "Direct connection without SRV",
            "options": {
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "retryWrites": False
            },
            "uri_modifier": lambda u: u.replace('mongodb+srv://', 'mongodb://')
        },
        {
            "name": "SSL with cert requirements disabled",
            "options": {
                "ssl": True,
                "ssl_cert_reqs": ssl.CERT_NONE,
                "retryWrites": False
            },
            "uri_modifier": None
        },
        {
            "name": "Connection with all options",
            "options": {
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "ssl": True,
                "ssl_cert_reqs": ssl.CERT_NONE,
                "retryWrites": True,
                "connectTimeoutMS": 30000,
                "socketTimeoutMS": 30000,
                "serverSelectionTimeoutMS": 30000
            },
            "uri_modifier": None
        }
    ]
    
    # Test each method
    for method in connection_methods:
        result = {
            "method": method["name"],
            "success": False,
            "error": None,
            "connection_options": str(method["options"])
        }
        
        try:
            # Apply URI modifier if specified
            test_uri = uri
            if method["uri_modifier"]:
                test_uri = method["uri_modifier"](uri)
                result["modified_uri"] = test_uri.replace(uri.split('@', 1)[0], "[REDACTED]") if '@' in uri else test_uri
            
            # Create client with timeout
            client = pymongo.MongoClient(
                test_uri, 
                serverSelectionTimeoutMS=5000,
                **method["options"]
            )
            
            # Test the connection
            client.admin.command('ping')
            
            # If we get here, connection was successful
            result["success"] = True
            results["successful_methods"].append(method["name"])
            
            # Try to list database names
            try:
                db_names = client.list_database_names()
                result["databases"] = db_names
            except Exception as db_err:
                result["db_list_error"] = str(db_err)
                
        except Exception as e:
            result["error"] = str(e)
        
        results["methods_tested"].append(result)
    
    # Add summary
    results["success_count"] = len(results["successful_methods"])
    results["total_tested"] = len(connection_methods)
    
    return jsonify(results)

# --- Enhanced Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    try:
        is_render = os.environ.get('RENDER', 'false').lower() == 'true'
        health_info = {
            "status": "healthy",
            "message": "Course API is running",
            "timestamp": datetime.now().isoformat(),
            "environment": "Render" if is_render else "Local",
            "python_version": pymongo.__version__,
            "mock_db": "users_collection" not in dir()
        }
        return jsonify(health_info)
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

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
