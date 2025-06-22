# db_connection.py
from pymongo import MongoClient
import ssl
import config
import os

def get_db_connection():
    """Get MongoDB connection with proper SSL configuration for different environments"""
    try:
        # Detect if we're on Render
        is_render = os.environ.get('RENDER') == 'true'
        
        print(f"Connecting to MongoDB... (Render environment: {is_render})")
        
        # Different connection options based on environment
        if is_render:
            # Render-specific connection options with modified SSL settings
            client = MongoClient(
                config.MONGODB_URI,
                ssl=True,
                ssl_cert_reqs=ssl.CERT_NONE,  # Disable certificate validation for Render
                tlsAllowInvalidCertificates=True,  # Allow invalid certificates
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                serverSelectionTimeoutMS=30000
            )
        else:
            # Local development connection options
            client = MongoClient(
                config.MONGODB_URI,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                serverSelectionTimeoutMS=30000
            )
        
        # Test the connection
        client.admin.command('ping')
        print("MongoDB connection successful!")
        
        # Return the database
        db = client[config.MONGODB_DB_NAME]
        return db
        
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        # For development, use mock DB. For production, we might want to fail
        if os.environ.get('ENVIRONMENT') == 'production':
            raise e
        else:
            print("Using mock database for development")
            return MockDB()

class MockDB:
    """Mock DB for testing when MongoDB is unavailable"""
    def __getattr__(self, name):
        print(f"Using mock collection: {name}")
        return MockCollection(name)

class MockCollection:
    """Mock Collection that simulates basic MongoDB operations"""
    def __init__(self, name):
        self.name = name
        self.data = {}
    
    def find_one(self, query=None, *args, **kwargs):
        print(f"Mock DB - find_one in {self.name} with query: {query}")
        if query and '_id' in query and str(query['_id']) == 'mock_id':
            return {
                "_id": "mock_id", 
                "email": "test@hy.ly", 
                "name": "Test User", 
                "google_id": "12345",
                "course_progress": {},
                "completed_chapters": [],
                "total_time_spent": 0,
                "created_at": "2025-06-22"
            }
        return None
    
    def insert_one(self, document, *args, **kwargs):
        print(f"Mock DB - insert_one in {self.name}: {document}")
        class MockResult:
            @property
            def inserted_id(self):
                return "mock_id"
        return MockResult()
    
    def update_one(self, query, update, *args, **kwargs):
        print(f"Mock DB - update_one in {self.name}: {query} → {update}")
        return None
    
    def find(self, query=None, *args, **kwargs):
        print(f"Mock DB - find in {self.name} with query: {query}")
        return []
