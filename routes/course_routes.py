# routes/course_routes.py
from flask import Blueprint, jsonify, request
from auth import require_auth
from services import notion_service
import config
from utils.error_handler import handle_error, ApiError

# Create blueprint
course_bp = Blueprint('course', __name__, url_prefix='/course')

@course_bp.route('/content', methods=['GET'])
@require_auth
def get_table_of_contents():
    """Get table of contents and preload first chapter"""
    try:
        # Use notion_service
        course_map = notion_service.build_course_map(config.NOTION_DATABASE_ID)
        toc_page_id = course_map.get("Table of contents")
        
        if not toc_page_id:
            raise ApiError("Table of contents not found", 404)
        
        # Get all chapters in order
        all_chapters = []
        for title in sorted(course_map.keys()):
            if "Chapter" in title and title != "Table of contents":
                chapter_number = notion_service.extract_chapter_number(title)
                if chapter_number:
                    all_chapters.append({
                        "title": title,
                        "number": chapter_number,
                        "locked": chapter_number > 1  # Only Chapter 1 is unlocked initially
                    })
        
        # Sort by chapter number
        all_chapters.sort(key=lambda x: x["number"])
        first_chapter_title = all_chapters[0]["title"] if all_chapters else None
        
        # Get table of contents content
        toc_blocks = notion_service.get_all_blocks_from_id(toc_page_id)
        content = "\n\n".join(filter(None, [notion_service.convert_block_to_markdown(b) for b in toc_blocks]))
        
        # Preload first chapter content for performance
        first_chapter_content = None
        if first_chapter_title:
            try:
                print(f"Preloading first chapter: {first_chapter_title}")
                first_chapter_content = notion_service.get_chapter_content(course_map, first_chapter_title)
                print("First chapter preloaded successfully!")
            except Exception as preload_error:
                print(f"Preload error (not critical): {preload_error}")
                first_chapter_content = None
        
        return jsonify({
            "content": content, 
            "firstChapterTitle": first_chapter_title,
            "firstChapterContent": first_chapter_content,
            "allChapters": all_chapters
        })
    except ApiError as e:
        return handle_error(e, e.status_code)
    except Exception as e: 
        return handle_error(e)

@course_bp.route('/chapter', methods=['POST'])
@require_auth
def get_chapter_content():
    """Get content for a specific chapter"""
    try:
        # Use notion_service
        course_map = notion_service.build_course_map(config.NOTION_DATABASE_ID)
        data = request.get_json()
        chapter_title = data.get('title')
        
        if not chapter_title:
            raise ApiError("Chapter title is required", 400)
            
        try:
            content = notion_service.get_chapter_content(course_map, chapter_title)
            return jsonify({"content": content})
        except ValueError as e:
            raise ApiError(str(e), 404)
            
    except ApiError as e:
        return handle_error(e, e.status_code)
    except Exception as e: 
        return handle_error(e)