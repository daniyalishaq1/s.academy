@app.route('/diagnose/mongodb', methods=['GET'])
def diagnose_mongodb():
    """Diagnostic endpoint for MongoDB connection"""
    import ssl
    import pymongo
    import urllib.parse
    import json
    import platform
    
    result = {
        "status": "checking",
        "python_version": platform.python_version(),
        "pymongo_version": pymongo.__version__,
        "openssl_version": ssl.OPENSSL_VERSION,
        "environment": os.environ.get('RENDER', 'false'),
        "tests": []
    }
    
    # Get MongoDB URI from config
    mongo_uri = config.MONGODB_URI
    
    # Try different connection methods
    connection_methods = [
        {
            "name": "Standard connection",
            "options": {}
        },
        {
            "name": "TLS connection with certificate validation disabled",
            "options": {
                "tls": True,
                "tlsAllowInvalidCertificates": True
            }
        },
        {
            "name": "Direct connection with TLS disabled",
            "options": {
                "directConnection": True,
                "ssl": False
            }
        },
        {
            "name": "Connection with SRV resolution and TLS",
            "options": {
                "tls": True,
                "retryWrites": True,
                "connectTimeoutMS": 5000,
                "socketTimeoutMS": 5000,
                "serverSelectionTimeoutMS": 5000
            }
        }
    ]
    
    for method in connection_methods:
        test_result = {
            "method": method["name"],
            "success": False,
            "error": None
        }
        
        try:
            # Create client with the specified options
            client = pymongo.MongoClient(mongo_uri, **method["options"])
            
            # Test the connection with a small timeout
            client.admin.command('ping', socketTimeoutMS=5000)
            
            test_result["success"] = True
            test_result["message"] = "Connection successful"
        except Exception as e:
            test_result["error"] = str(e)
        
        result["tests"].append(test_result)
    
    # Check overall status
    if any(test["success"] for test in result["tests"]):
        result["status"] = "success"
        result["message"] = "At least one connection method works"
    else:
        result["status"] = "failure"
        result["message"] = "All connection methods failed"
    
    return jsonify(result)
