# mongodb_diagnostic.py
import os
import ssl
import pymongo
import json
from urllib.parse import quote_plus
from datetime import datetime

def test_mongodb_connections(uri=None):
    """Test multiple MongoDB connection methods and return results"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "python_ssl": ssl.OPENSSL_VERSION,
        "pymongo_version": pymongo.__version__,
        "methods_tested": [],
        "successful_methods": []
    }
    
    # Use provided URI or get from environment
    if not uri:
        uri = os.environ.get('MONGODB_URI', '')
    
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
            "name": "TLS disabled connection",
            "options": {"tls": False},
            "uri_modifier": lambda u: u.replace('mongodb+srv://', 'mongodb://')
        },
        {
            "name": "TLS with validation disabled",
            "options": {"tls": True, "tlsAllowInvalidCertificates": True},
            "uri_modifier": None
        },
        {
            "name": "Connection with all TLS options disabled",
            "options": {
                "tls": False,
                "ssl": False,
                "tlsAllowInvalidCertificates": True,
                "retryWrites": False
            },
            "uri_modifier": lambda u: u.replace('mongodb+srv://', 'mongodb://')
        },
        {
            "name": "Direct connection to replica set",
            "options": {
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "replicaSet": "atlas-lv2bm9-shard-0",
                "authSource": "admin",
                "retryWrites": True
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
    
    return results

if __name__ == "__main__":
    # Run as standalone script
    print(json.dumps(test_mongodb_connections(), indent=2))
