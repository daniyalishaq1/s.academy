# services/user_service.py
import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import config

# Initialize MongoDB connection
try:
    client = MongoClient(config.MONGODB_URI)
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful in user_service.py")
    db = client[config.MONGODB_DB_NAME]
    users_collection = db.users
except Exception as e:
    print(f"MongoDB connection error in user_service.py: {e}")
    # For development, you might want to raise the error to see it clearly
    raise e

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