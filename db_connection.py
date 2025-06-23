# db_connection.py
import os
import ssl
from pymongo import MongoClient
import config
from datetime import datetime

def get_mongodb_connection():
    """Get a MongoDB connection using the best method for the environment"""
    
    # Check if we're on Render
    is_render = os.environ.get('RENDER', 'false').lower() == 'true'
    
    if is_render:
        print("Running on Render - using MongoDB connection method for Render")
        
        # For Render, we need to modify the URI and use special connection options
        mongo_uri = config.MONGODB_URI
        
        # Convert URI format if using SRV format
        if mongo_uri.startswith('mongodb+srv://'):
            # Extract username, password, host and database
            srv_parts = mongo_uri.split('@')
            credentials = srv_parts[0].replace('mongodb+srv://', '')
            host_and_options = srv_parts[1]
            
            # Split host and options if present
            if '?' in host_and_options:
                host_part, options_part = host_and_options.split('?', 1)
                options = f"?{options_part}"
            else:
                host_part = host_and_options
                options = ""
            
            # Convert to standard format with specific servers
            # This is a workaround for Render's SSL/TLS issues
            mongo_uri = f"mongodb://{credentials}@{host_part.replace('.mongodb.net', '-shard-00-00.mongodb.net:27017,')}{host_part.replace('.mongodb.net', '-shard-00-01.mongodb.net:27017,')}{host_part.replace('.mongodb.net', '-shard-00-02.mongodb.net:27017')}/admin?ssl=true&replicaSet=atlas-lv2bm9-shard-0&authSource=admin&retryWrites=true"
        
        # Create client with special options for Render
        client = MongoClient(
            mongo_uri,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_NONE,  # This is key for Render
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            serverSelectionTimeoutMS=30000
        )
    else:
        print("Local environment - using standard MongoDB connection")
        client = MongoClient(config.MONGODB_URI)
    
    # Test the connection
    client.admin.command('ping')
    print("MongoDB connection successful!")
    
    # Return the database
    return client[config.MONGODB_DB_NAME]
