# utils/error_handler.py
import traceback
import logging
import json
from flask import jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Create a logger
logger = logging.getLogger('course_platform')

class ApiError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message, status_code=500, details=None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

def handle_error(error, status_code=500, log_exception=True):
    """Handle errors consistently across the application"""
    if log_exception:
        logger.error(f"Error: {str(error)}")
        logger.error(traceback.format_exc())
    
    response = {
        "error": str(error),
        "status": "error"
    }
    
    return jsonify(response), status_code

def handle_api_error(error):
    """Handle ApiError exceptions"""
    logger.error(f"API Error: {error.message}")
    
    response = {
        "error": error.message,
        "status": "error"
    }
    
    if error.details:
        response["details"] = error.details
    
    return jsonify(response), error.status_code

def setup_error_handlers(app):
    """Set up error handlers for the Flask app"""
    @app.errorhandler(404)
    def not_found(error):
        return handle_error("Resource not found", 404, log_exception=False)
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return handle_error("Internal server error", 500)
    
    @app.errorhandler(ApiError)
    def handle_custom_api_error(error):
        return handle_api_error(error)
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        return handle_error(error, 500)