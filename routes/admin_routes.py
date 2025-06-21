# routes/admin_routes.py
from flask import Blueprint, jsonify
from services import user_service
from datetime import datetime
import json

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
def view_users():
    """Admin route to view all users - REMOVE IN PRODUCTION"""
    try:
        # Get all users from MongoDB
        users = user_service.get_all_users()
        
        # Create HTML to display users
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Users Data - Admin View</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .user-card {{ background: #f8f9fa; padding: 20px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #26BBED; }}
                .user-email {{ font-size: 1.2rem; font-weight: bold; color: #26BBED; margin-bottom: 10px; }}
                .user-details {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; }}
                .detail-item {{ background: white; padding: 10px; border-radius: 4px; }}
                .detail-label {{ font-weight: bold; color: #666; font-size: 0.9rem; }}
                .detail-value {{ color: #333; }}
                .stats {{ background: #e8f5e8; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center; }}
                .json-view {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin-top: 10px; overflow-x: auto; }}
                .json-toggle {{ background: #6c757d; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 0.8rem; }}
                .nav-links {{ margin-bottom: 20px; }}
                .nav-links a {{ background: #26BBED; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; margin-right: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="nav-links">
                    <a href="/">← Back to Course</a>
                    <a href="/admin/users">Refresh Users</a>
                </div>
                
                <h1>🎓 Course Platform - Users Data</h1>
                
                <div class="stats">
                    <h3>📊 Statistics</h3>
                    <p><strong>Total Users:</strong> {len(users)}</p>
                    <p><strong>Database:</strong> course_platform.users</p>
                    <p><strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
        '''
        
        if not users:
            html += '''
                <div class="user-card">
                    <p>No users found in the database yet.</p>
                    <p>Users will appear here after they log in for the first time.</p>
                </div>
            '''
        else:
            for i, user in enumerate(users):
                completed_count = len(user.get('completed_chapters', []))
                total_time = user.get('total_time_spent', 0)
                
                html += f'''
                <div class="user-card">
                    <div class="user-email">👤 {user.get('email', 'No email')}</div>
                    
                    <div class="user-details">
                        <div class="detail-item">
                            <div class="detail-label">Name</div>
                            <div class="detail-value">{user.get('name', 'Not provided')}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Google ID</div>
                            <div class="detail-value">{user.get('google_id', 'Not available')[:20]}...</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Created At</div>
                            <div class="detail-value">{user.get('created_at', 'Unknown')}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Last Login</div>
                            <div class="detail-value">{user.get('last_login', 'Never')}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Completed Chapters</div>
                            <div class="detail-value">{completed_count} chapters</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Time Spent</div>
                            <div class="detail-value">{total_time} minutes</div>
                        </div>
                    </div>
                    
                    <button class="json-toggle" onclick="toggleJson({i})">Show Full Data</button>
                    <div id="json-{i}" class="json-view" style="display: none;">
                        <pre>{json.dumps(user, indent=2)}</pre>
                    </div>
                </div>
                '''
        
        html += '''
                <div style="margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 6px;">
                    <h4>⚠️ Security Note</h4>
                    <p>This admin route shows sensitive user data. In production:</p>
                    <ul>
                        <li>Remove this route or add proper admin authentication</li>
                        <li>Use MongoDB Atlas interface for user management</li>
                        <li>Implement proper admin permissions</li>
                    </ul>
                </div>
            </div>
            
            <script>
                function toggleJson(index) {
                    const element = document.getElementById('json-' + index);
                    const button = event.target;
                    if (element.style.display === 'none') {
                        element.style.display = 'block';
                        button.textContent = 'Hide Full Data';
                    } else {
                        element.style.display = 'none';
                        button.textContent = 'Show Full Data';
                    }
                }
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f'''
        <h1>Error loading users</h1>
        <p>Error: {str(e)}</p>
        <p><a href="/">Return to Course</a></p>
        '''