# auth.py
import os
import json
from datetime import datetime
from flask import Blueprint, redirect, url_for, session, request, jsonify, flash
from authlib.integrations.flask_client import OAuth
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import config
import ssl

# Initialize MongoDB with multiple connection methods
try:
    # Check if we're on Render
    is_render = os.environ.get('RENDER', 'false').lower() == 'true'
    
    if is_render:
        print("Running on Render - trying multiple MongoDB connection methods")
        
        # Try multiple connection methods
        connection_options = [
            # Method 1: Standard SRV connection with TLS options
            {
                "name": "Standard SRV with TLS options",
                "options": {
                    "tls": True,
                    "tlsAllowInvalidCertificates": True,
                    "retryWrites": True,
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "serverSelectionTimeoutMS": 30000
                }
            },
            # Method 2: Direct connection without SRV
            {
                "name": "Direct connection without SRV",
                "options": {
                    "tls": True,
                    "tlsAllowInvalidCertificates": True,
                    "retryWrites": True,
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "serverSelectionTimeoutMS": 30000
                },
                "uri_modifier": lambda uri: uri.replace("mongodb+srv://", "mongodb://")
            },
            # Method 3: SSL with certificate requirements disabled
            {
                "name": "SSL with cert requirements disabled",
                "options": {
                    "ssl": True,
                    "ssl_cert_reqs": ssl.CERT_NONE,
                    "retryWrites": False,
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "serverSelectionTimeoutMS": 30000
                }
            }
        ]
        
        # Try each method until one works
        last_error = None
        for method in connection_options:
            try:
                print(f"Trying MongoDB connection method: {method['name']}")
                
                # Apply URI modifier if specified
                if "uri_modifier" in method:
                    uri = method["uri_modifier"](config.MONGODB_URI)
                    print(f"Modified URI: {uri.split('@')[0]}@***")
                else:
                    uri = config.MONGODB_URI
                
                # Create client with options
                client = MongoClient(uri, **method["options"])
                
                # Test connection
                client.admin.command('ping')
                print(f"MongoDB connection successful with method: {method['name']}")
                
                # Get database
                db = client[config.MONGODB_DB_NAME]
                users_collection = db.users
                
                # Exit the loop if connection works
                break
                
            except Exception as e:
                print(f"Connection method failed: {method['name']} - {e}")
                last_error = e
                continue
        
        # If we've tried all methods and still have an error, raise it
        if last_error and 'users_collection' not in locals():
            raise last_error
    else:
        # Standard connection for local development
        print("Local environment - using standard MongoDB connection")
        client = MongoClient(config.MONGODB_URI)
        db = client[config.MONGODB_DB_NAME]
        users_collection = db.users
        
except Exception as e:
    print(f"MongoDB connection error in auth.py: {e}")
    
    # Define a mock collection for development/testing
    class MockCollection:
        def find_one(self, query=None, *args, **kwargs):
            print(f"Mock DB - find_one with query: {query}")
            # Return a mock user for development
            return {
                "_id": "mock_id", 
                "email": "test@hy.ly", 
                "name": "Test User", 
                "google_id": "12345",
                "course_progress": {},
                "completed_chapters": [],
                "total_time_spent": 0,
                "created_at": datetime.utcnow()
            }
        
        def insert_one(self, document, *args, **kwargs):
            print(f"Mock DB - insert_one: {document}")
            class MockResult:
                @property
                def inserted_id(self):
                    return "mock_id"
            return MockResult()
        
        def update_one(self, query, update, *args, **kwargs):
            print(f"Mock DB - update_one: {query} → {update}")
            return None
    
    # Use mock database if MongoDB connection fails
    print("Using mock database for development/testing")
    class MockDB:
        def __getattr__(self, name):
            return MockCollection()
    
    db = MockDB()
    users_collection = db.users

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with Flask app"""
    oauth.init_app(app)
    
    # Configure Google OAuth
    google = oauth.register(
        name='google',
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        },
    )
    return google

@auth_bp.route('/login')
def login():
    """Initiate Google OAuth login"""
    try:
        google = oauth.google
        redirect_uri = url_for('auth.callback', _external=True)
        print(f"Redirect URI: {redirect_uri}")
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"Login error: {e}")
        flash('Authentication service unavailable. Please try again.', 'error')
        return redirect(url_for('auth.login_page'))

@auth_bp.route('/callback')
def callback():
    """Handle OAuth callback"""
    try:
        google = oauth.google
        token = google.authorize_access_token()
        
        # Get user info from token
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback: get user info from Google API
            resp = google.parse_id_token(token)
            user_info = resp
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name')
            picture = user_info.get('picture')
            google_id = user_info.get('sub')
            
            print(f"=== DEBUG INFO ===")
            print(f"Google sent email: {email}")
            print(f"User name: {name}")
            print(f"Google ID: {google_id}")
            print(f"Profile picture: {picture}")
            print(f"Email ends with @hy.ly: {email.endswith('@hy.ly') if email else False}")
            print(f"==================")
            
            # Check if email is from hy.ly domain
            if not email or not any(email.endswith(domain) for domain in config.ALLOWED_DOMAINS):
                print(f"Access denied for: {email}")
                # Store the email in session for display on error page
                session['debug_email'] = email or "No email received"
                session['debug_name'] = name or "No name received"
                return redirect(url_for('auth.login_failed'))
            
            print(f"Access granted for: {email}")
            
            # Check if user exists in database
            user = users_collection.find_one({'email': email})
            
            if not user:
                # Create new user
                user_data = {
                    'email': email,
                    'name': name,
                    'google_id': google_id,
                    'picture': picture,
                    'created_at': datetime.utcnow(),
                    'last_login': datetime.utcnow(),
                    'course_progress': {},
                    'total_time_spent': 0,
                    'completed_chapters': [],
                    'bookmarks': []
                }
                result = users_collection.insert_one(user_data)
                user_data['_id'] = result.inserted_id
                user = user_data
                print(f"Created new user: {email}")
            else:
                # Update last login
                users_collection.update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.utcnow()}}
                )
                print(f"Updated existing user: {email}")
            
            # Store user info in session
            session['user'] = {
                'id': str(user['_id']),
                'email': user['email'],
                'name': user['name'],
                'picture': user.get('picture'),
                'is_authenticated': True
            }
            
            print(f"Session created for: {email}")
            return redirect('/')
        else:
            session['debug_email'] = "No user info received from Google"
            session['debug_name'] = "Unknown"
            return redirect(url_for('auth.login_failed'))
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        session['debug_email'] = f"Error: {str(e)}"
        session['debug_name'] = "Error occurred"
        return redirect(url_for('auth.login_failed'))

@auth_bp.route('/logout')
def logout():
    """Log out user"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login_page'))

@auth_bp.route('/login-page')
def login_page():
    """Display login page"""
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    debug_info = f"Client ID configured: {'Yes' if client_id else 'No'}"
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hyly Course Platform - Login</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #26BBED, #1a9bd8);
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .login-container {{
                background: white;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 450px;
                width: 90%;
            }}
            .logo {{
                width: 80px;
                height: 80px;
                background: #26BBED;
                border-radius: 50%;
                margin: 0 auto 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2rem;
                color: white;
            }}
            h1 {{
                color: #333;
                margin-bottom: 10px;
                font-size: 1.8rem;
            }}
            .subtitle {{
                color: #666;
                margin-bottom: 30px;
                font-size: 1rem;
            }}
            .google-login-btn {{
                background: #4285f4;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 10px;
                transition: background 0.2s;
                margin-bottom: 20px;
            }}
            .google-login-btn:hover {{
                background: #3367d6;
            }}
            .restriction-note {{
                margin-top: 20px;
                padding: 20px;
                background: #f0f8ff;
                border-left: 4px solid #26BBED;
                border-radius: 4px;
                color: #333;
                font-size: 0.9rem;
                text-align: left;
            }}
            .debug-info {{
                margin-top: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
                font-size: 0.8rem;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">🎓</div>
            <h1>Hylee's Course Platform</h1>
            <p class="subtitle">Sign in with your Hyly account</p>
            
            <a href="/auth/login" class="google-login-btn">
                <svg width="20" height="20" viewBox="0 0 24 24">
                    <path fill="white" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="white" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="white" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="white" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Sign in with Google
            </a>
            
            <div class="restriction-note">
                <strong>📋 Required:</strong> @hy.ly emails only<br>
                <strong>Valid:</strong> daniyal@hy.ly, munish@hy.ly
            </div>
            
            <div class="debug-info">
                Debug: {debug_info}
            </div>
        </div>
    </body>
    </html>
    '''

@auth_bp.route('/login-failed')
def login_failed():
    """Display login failed page with the actual email received"""
    debug_email = session.get('debug_email', 'Unknown email')
    debug_name = session.get('debug_name', 'Unknown name')
    
    # Clear debug info from session
    session.pop('debug_email', None)
    session.pop('debug_name', None)
    
    # Create the solution content based on the email received
    if debug_email == 'daniyal@hy.ly':
        solution_content = '''
        <p><strong>Great news!</strong> You're signed into the correct account (daniyal@hy.ly).</p>
        <p>The issue might be that the @hy.ly email isn't properly set up as a Google account yet.</p>
        <p><strong>Next steps:</strong></p>
        <ol>
            <li>Go to <a href="https://accounts.google.com/signup" target="_blank">accounts.google.com/signup</a></li>
            <li>Create a Google account using daniyal@hy.ly as the email</li>
            <li>Verify the email (you'll need access to daniyal@hy.ly mailbox)</li>
            <li>Return here and try signing in again</li>
        </ol>
        '''
    else:
        solution_content = f'''
        <p>Google sent us: <strong>{debug_email}</strong></p>
        <p>We need: <strong>daniyal@hy.ly</strong> or <strong>munish@hy.ly</strong></p>
        <p><strong>To fix this:</strong></p>
        <ol>
            <li>Sign out of all Google accounts</li>
            <li>Sign in with the @hy.ly Google account</li>
            <li>If @hy.ly account doesn't exist, create it first</li>
            <li>Return here and try again</li>
        </ol>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Access Denied - Hyly Course Platform</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px; 
                background: #f5f5f5; 
            }}
            .container {{ 
                background: white; 
                padding: 40px; 
                border-radius: 8px; 
                max-width: 600px; 
                margin: 0 auto; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .error {{ 
                color: #d32f2f; 
                font-size: 1.1rem; 
                margin-bottom: 20px; 
                padding: 15px;
                background: #ffebee;
                border-radius: 4px;
            }}
            .debug-result {{
                background: #e3f2fd;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: left;
                font-size: 0.95rem;
                border-left: 4px solid #2196f3;
            }}
            .retry-btn {{ 
                background: #26BBED; 
                color: white; 
                padding: 12px 24px; 
                text-decoration: none; 
                border-radius: 4px; 
                display: inline-block;
                margin-top: 20px;
            }}
            .solution {{
                background: #f1f8e9;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: left;
                border-left: 4px solid #4caf50;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚫 Access Denied</h1>
            
            <div class="error">
                Only @hy.ly email addresses are allowed to access this platform.
            </div>
            
            <div class="debug-result">
                <h3>🔍 Debug Results:</h3>
                <strong>Email Google sent us:</strong> {debug_email}<br>
                <strong>Name:</strong> {debug_name}<br>
                <strong>Required:</strong> Must end with @hy.ly
            </div>
            
            <div class="solution">
                <h3>✅ Solution:</h3>
                {solution_content}
            </div>
            
            <a href="/auth/login-page" class="retry-btn">Try Again</a>
        </div>
    </body>
    </html>
    '''

# Helper function to check if user is authenticated
def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user', {}).get('is_authenticated'):
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to get current user
def get_current_user():
    """Get current user from session"""
    user_session = session.get('user')
    if user_session and user_session.get('is_authenticated'):
        return users_collection.find_one({'_id': ObjectId(user_session['id'])})
    return None
