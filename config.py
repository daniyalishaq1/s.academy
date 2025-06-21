# config.py
import os
from dotenv import load_dotenv

# Load environment variables if .env file exists
if os.path.exists('.env'):
    load_dotenv()

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
PORT = int(os.getenv('PORT', 5000))

# API Keys
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'course_platform')

# Application Settings
ALLOWED_DOMAINS = os.getenv('ALLOWED_DOMAINS', '@hy.ly').split(',')
COURSE_NAME = os.getenv('COURSE_NAME', "Hylees Intro to Multifamily")

# Validate required configuration
def validate_config():
    """Validate that all required configuration values are set"""
    required_vars = [
        'NOTION_API_KEY', 
        'NOTION_DATABASE_ID', 
        'OPENAI_API_KEY',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'MONGODB_URI'
    ]
    
    missing_vars = [var for var in required_vars if not globals().get(var)]
    
    if missing_vars:
        missing_list = ', '.join(missing_vars)
        print(f"ERROR: Missing required environment variables: {missing_list}")
        return False
    
    return True

# Config is valid if this is true
CONFIG_VALID = validate_config()