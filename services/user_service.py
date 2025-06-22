# services/user_service.py
import os
import ssl
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import config

# Initialize MongoDB connection with SSL configuration that works on Render
try:
    # Check if we're on Render
    is_render = os.environ.get('RENDER', 'false').lower() == 'true'
    
    if is_render:
        print("Running on Render - using special MongoDB connection options")
        # Render-specific connection with relaxed SSL settings
        client = MongoClient(
            config.MONGODB_URI,
            ssl=True, 
            ssl_cert_reqs=ssl.CERT_NONE,  # Disable certificate validation
            tlsAllowInvalidCertificates=True,  # Allow invalid certificates
            retryWrites=True,
            w='majority',
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            serverSelectionTimeoutMS=30000
        )
    else:
        # Standard connection for local development
        print("Local environment - using standard MongoDB connection")
        client = MongoClient(config.MONGODB_URI)
    
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful in user_service.py")
    db = client[config.MONGODB_DB_NAME]
    users_collection = db.users
except Exception as e:
    print(f"MongoDB connection error in user_service.py: {e}")
    
    # Define a mock collection for development/testing
    class MockCollection:
        def find_one(self, query=None, *args, **kwargs):
            print(f"Mock DB - find_one in users with query: {query}")
            if query and '_id' in query:
                return {
                    "_id": query['_id'], 
                    "email": "test@hy.ly", 
                    "name": "Test User", 
                    "course_progress": {},
                    "completed_chapters": [],
                    "total_time_spent": 0
                }
            return None
            
        def update_one(self, query, update, *args, **kwargs):
            print(f"Mock DB - update_one in users: {query} → {update}")
            return True
            
        def find(self, *args, **kwargs):
            print(f"Mock DB - find in users")
            return []
    
    # Use mock database if MongoDB connection fails
    print("Using mock database for development/testing")
    class MockDB:
        def __getattr__(self, name):
            return MockCollection()
    
    db = MockDB()
    users_collection = db.users

def get_user_by_id(user_id):
    """Get user by ID"""
    if not user_id:
        return None
    
    try:
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        return user
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

def get_all_users():
    """Get all users from the database"""
    try:
        users = list(users_collection.find())
        
        # Convert ObjectId to string and datetime objects to strings for JSON serialization
        for user in users:
            user['_id'] = str(user['_id'])
            if 'created_at' in user:
                user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if 'last_login' in user:
                user['last_login'] = user['last_login'].strftime('%Y-%m-%d %H:%M:%S')
        
        return users
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []

def update_user_progress(user_id, chapter_title, section_index, time_spent=0):
    """Update user's progress for a specific chapter"""
    if not user_id or not chapter_title:
        return False
    
    try:
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    f'course_progress.{chapter_title}': {
                        'section_index': section_index,
                        'last_updated': datetime.utcnow()
                    },
                    'last_activity': datetime.utcnow()
                },
                '$inc': {'total_time_spent': time_spent}
            }
        )
        return True
    except Exception as e:
        print(f"Error updating user progress: {e}")
        return False

def complete_chapter(user_id, completed_chapter):
    """Mark a chapter as completed for a user"""
    if not user_id or not completed_chapter:
        return False
    
    try:
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$addToSet': {'completed_chapters': completed_chapter},
                '$set': {'last_activity': datetime.utcnow()}
            }
        )
        return True
    except Exception as e:
        print(f"Error completing chapter: {e}")
        return False

def get_user_progress(user_id):
    """Get user's progress details"""
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    return {
        "name": user.get('name'),
        "email": user.get('email'),
        "completed_chapters": user.get('completed_chapters', []),
        "course_progress": user.get('course_progress', {}),
        "total_time_spent": user.get('total_time_spent', 0)
    }
