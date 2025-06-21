# routes/progress_routes.py
from flask import Blueprint, jsonify, request
from auth import require_auth, get_current_user
from services import notion_service, user_service
import config
from utils.error_handler import handle_error, ApiError

# Create blueprint
progress_bp = Blueprint('progress', __name__, url_prefix='/progress')

@progress_bp.route('/complete-chapter', methods=['POST'])
@require_auth
def complete_chapter():
    """Mark a chapter as completed and unlock the next one"""
    try:
        data = request.get_json()
        completed_chapter = data.get('chapter_title')
        
        # Get current user
        current_user = get_current_user()
        if not current_user:
            raise ApiError("User not found", 401)
        
        if not completed_chapter:
            raise ApiError("Chapter title is required", 400)
            
        # Extract chapter number using notion_service
        chapter_number = notion_service.extract_chapter_number(completed_chapter)
        if not chapter_number:
            raise ApiError("Invalid chapter format", 400)
        
        # Update user's completed chapters using the user service
        success = user_service.complete_chapter(current_user['_id'], completed_chapter)
        if not success:
            raise ApiError("Failed to update chapter completion status", 500)
        
        # Get all chapters again to determine next chapter using notion_service
        course_map = notion_service.build_course_map(config.NOTION_DATABASE_ID)
        all_chapters = []
        for title in sorted(course_map.keys()):
            if "Chapter" in title and title != "Table of contents":
                chapter_num = notion_service.extract_chapter_number(title)
                if chapter_num:
                    all_chapters.append({
                        "title": title,
                        "number": chapter_num,
                        "locked": chapter_num > (chapter_number + 1)  # Unlock up to next chapter
                    })
        
        all_chapters.sort(key=lambda x: x["number"])
        next_chapter = next((ch for ch in all_chapters if ch["number"] == chapter_number + 1), None)
        
        return jsonify({
            "success": True,
            "unlockedChapters": all_chapters,
            "nextChapter": next_chapter
        })
        
    except ApiError as e:
        return handle_error(e, e.status_code)
    except Exception as e:
        return handle_error(e)

@progress_bp.route('/user', methods=['GET'])
@require_auth
def get_user_progress():
    """Get current user's progress"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "User not found"}), 401
        
        progress = user_service.get_user_progress(current_user['_id'])
        if not progress:
            return jsonify({"error": "Could not retrieve user progress"}), 500
        
        return jsonify({"user": progress})
    except Exception as e:
        print(f"Error getting user progress: {e}")
        return jsonify({"error": str(e)}), 500

@progress_bp.route('/save', methods=['POST'])
@require_auth
def save_progress():
    """Save user's current progress"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "User not found"}), 401
        
        data = request.get_json()
        chapter_title = data.get('chapter_title')
        section_index = data.get('section_index', 0)
        time_spent = data.get('time_spent', 0)
        
        success = user_service.update_user_progress(
            current_user['_id'], 
            chapter_title, 
            section_index, 
            time_spent
        )
        
        if not success:
            return jsonify({"error": "Failed to update progress"}), 500
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error saving progress: {e}")
        return jsonify({"error": str(e)}), 500