# routes/__init__.py
from flask import Flask

def register_blueprints(app: Flask):
    """Register all blueprints with the Flask app"""
    from .course_routes import course_bp
    from .progress_routes import progress_bp
    from .ai_routes import ai_bp
    from .admin_routes import admin_bp
    from .static_routes import static_bp
    
    # Register blueprints
    app.register_blueprint(course_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(static_bp)
    
    # Return the app for chaining
    return app