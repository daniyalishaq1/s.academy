import os
import json
from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS
from notion_client import Client
import openai
from dotenv import load_dotenv

# Load environment variables only in development
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__, static_folder='.')

# CORS configuration for production
CORS(app, origins=['*'])  # In production, you might want to restrict this

# Environment variables
NOTION_API_KEY = os.getenv('NOTION_API_KEY')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not all([NOTION_API_KEY, NOTION_DATABASE_ID, OPENAI_API_KEY]):
    raise Exception("ERROR: Make sure all API keys and IDs are set in your environment variables")

notion = Client(auth=NOTION_API_KEY)
openai.api_key = OPENAI_API_KEY
course_map = None

# --- Serve static files ---
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# --- Helper Functions ---
def convert_rich_text_to_markdown(rich_text_array):
    """Convert Notion rich text to markdown format"""
    markdown_parts = []
    for item in rich_text_array:
        text_content = item.get("text", {}).get("content", "")
        annotations = item.get("annotations", {})
        if annotations.get("bold"): text_content = f"**{text_content}**"
        if annotations.get("italic"): text_content = f"*{text_content}*"
        if annotations.get("strikethrough"): text_content = f"~~{text_content}~~"
        if annotations.get("code"): text_content = f"`{text_content}`"
        markdown_parts.append(text_content)
    return "".join(markdown_parts)

def get_all_blocks_from_id(block_id):
    """Fetch all blocks from a Notion page/block"""
    try:
        return notion.blocks.children.list(block_id=block_id).get("results", [])
    except Exception as e:
        print(f"Error fetching blocks for ID {block_id}: {e}")
        return []

def convert_block_to_markdown(block):
    """Convert different Notion block types to markdown"""
    block_type = block.get("type")
    content = block.get(block_type, {})
    
    if block_type == "image":
        image_data = content.get("file") or content.get("external")
        if image_data and image_data.get("url"):
            return f"![Notion Image]({image_data.get('url')})"
        return ""
    
    elif block_type == "table":
        table_rows = get_all_blocks_from_id(block['id'])
        if not table_rows: return ""
        
        num_columns = len(table_rows[0].get('table_row', {}).get('cells', []))
        header_cells = table_rows[0].get('table_row', {}).get('cells', [])
        header_md = "| " + " | ".join([convert_rich_text_to_markdown(cell) for cell in header_cells]) + " |"
        separator_md = "| " + " | ".join(["---"] * num_columns) + " |"
        markdown_table = [header_md, separator_md]
        
        for row_block in table_rows[1:]:
            data_cells = row_block.get('table_row', {}).get('cells', [])
            markdown_table.append("| " + " | ".join([convert_rich_text_to_markdown(cell) for cell in data_cells]) + " |")
        return "\n".join(markdown_table)
    
    if "rich_text" in content:
        processed_text = convert_rich_text_to_markdown(content["rich_text"])
        if not processed_text: return ""
        
        if block_type == "heading_1": return f"# {processed_text}"
        if block_type == "heading_2": return f"## {processed_text}"
        if block_type == "heading_3": return f"### {processed_text}"
        if block_type == "bulleted_list_item": return f"* {processed_text}"
        if block_type == "numbered_list_item": return f"1. {processed_text}"
        if block_type == "paragraph": return processed_text
    
    return ""

def build_course_map():
    """Build a map of all course content from Notion database"""
    global course_map
    if course_map is not None: return
    
    print("Building course map...")
    db_response = notion.databases.query(
        database_id=NOTION_DATABASE_ID, 
        filter={"property": "Course Name", "title": {"equals": "Hylees Intro to Multifamily"}}
    )
    pages = db_response.get("results", [])
    if not pages: raise Exception("Could not find 'Hylees Intro to Multifamily' page.")
    
    main_page_blocks = get_all_blocks_from_id(pages[0]["id"])
    course_material_block_id = None
    
    for block in main_page_blocks:
        if block.get("type") == "heading_3" and block.get("heading_3", {}).get("is_toggleable"):
            if "Course Material" in convert_rich_text_to_markdown(block.get('heading_3', {}).get('rich_text', [])):
                course_material_block_id = block["id"]
                break
    
    if not course_material_block_id: 
        raise Exception("Could not find 'Course Material' toggleable heading.")
    
    temp_map = {}
    blocks_inside_heading = get_all_blocks_from_id(course_material_block_id)
    for block in blocks_inside_heading:
        if block.get("type") == "child_page":
            title = block.get("child_page", {}).get("title")
            page_id = block["id"]
            if title:
                temp_map[title] = page_id
    
    course_map = temp_map
    print(f"Course map built with {len(course_map)} items.")

def extract_chapter_number(title):
    """Extract chapter number from title like 'Chapter 1: Introduction'"""
    import re
    match = re.search(r'Chapter\s+(\d+)', title, re.IGNORECASE)
    return int(match.group(1)) if match else None

# --- OPTIMIZED AI Functions ---
def classify_user_intent(user_input, current_section_title, next_section_title):
    """Faster intent classification with shorter prompt"""
    intent_prompt = f"""
Determine user intent: CONTINUE (wants next section) or QUESTION (has question about current content).

User said: "{user_input}"

CONTINUE examples: next, continue, move on, yes, ok, got it
QUESTION examples: what, how, explain, clarify, don't understand

Respond: CONTINUE or QUESTION
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": intent_prompt}],
            max_tokens=5,  # Just need one word
            temperature=0,  # Deterministic for speed
        )
        
        result = response.choices[0].message.content.strip().upper()
        return result if result in ['CONTINUE', 'QUESTION'] else 'QUESTION'
    except Exception as e:
        print(f"Intent classification error: {e}")
        return 'QUESTION'

def generate_quick_actions(section_content):
    """Generate specific, content-based quick actions - exactly 3 actions"""
    
    # Truncate content for faster processing
    max_content_length = 1200
    if len(section_content) > max_content_length:
        section_content = section_content[:max_content_length] + "..."
    
    quick_actions_prompt = f"""
Based on this content, create exactly 3 specific questions about actual terms, numbers, concepts, or facts mentioned.

Content: {section_content}

Requirements:
- Extract specific terms, numbers, or concepts from the content
- Format as questions like "What is [specific term]?", "How many [specific number/data]?", "When was [specific event]?"
- Use ONLY information that actually appears in the content
- Each question must be different and specific
- Keep questions under 6 words
- NO generic questions like "give examples", "elaborate", "define key terms"

Example good questions:
- "What is Lease-up Phase?"
- "How many units converted?"
- "What is Cap Rate?"

Generate exactly 3 specific questions:
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": quick_actions_prompt}],
            max_tokens=100,
            temperature=0.2,  # Low temperature for consistency
        )
        
        result = response.choices[0].message.content.strip()
        print(f"Raw AI response: {result}")
        
        # Extract questions from the response
        actions = []
        lines = result.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Clean up the line - remove numbers, bullets, quotes
            cleaned = line
            # Remove leading numbers and bullets
            cleaned = cleaned.lstrip('123456789.- ')
            # Remove quotes
            cleaned = cleaned.strip('"\'')
            
            # Only keep lines that look like questions or contain specific terms
            if cleaned and (cleaned.endswith('?') or any(word in cleaned.lower() for word in ['what', 'how', 'when', 'where', 'why'])):
                if len(cleaned) <= 60 and cleaned not in actions:
                    actions.append(cleaned)
        
        # If we don't have enough specific actions, try to extract specific terms from content
        if len(actions) < 3:
            # Try to find specific terms in the content
            import re
            
            # Look for capitalized terms, numbers, percentages
            specific_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', section_content)
            numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?%?\b', section_content)
            
            # Create questions from found terms
            for term in specific_terms[:2]:
                if len(actions) >= 3:
                    break
                question = f"What is {term}?"
                if question not in actions and len(question) <= 60:
                    actions.append(question)
            
            for number in numbers[:1]:
                if len(actions) >= 3:
                    break
                question = f"What about {number}?"
                if question not in actions and len(question) <= 60:
                    actions.append(question)
        
        # Ensure we have exactly 3 actions
        specific_fallbacks = [
            "What is the main topic?",
            "How does this work?", 
            "What are the steps?"
        ]
        
        while len(actions) < 3:
            for fallback in specific_fallbacks:
                if len(actions) >= 3:
                    break
                if fallback not in actions:
                    actions.append(fallback)
        
        final_actions = actions[:3]  # Limit to exactly 3
        print(f"Final 3 actions: {final_actions}")
        return final_actions
            
    except Exception as e:
        print(f"Quick actions generation error: {e}")
        return ["What is the main topic?", "How does this work?", "What are the steps?"]

# --- API Endpoints ---
@app.route('/get-course-content', methods=['GET'])
def get_table_of_contents():
    """Get table of contents and preload first chapter"""
    try:
        build_course_map()
        toc_page_id = course_map.get("Table of contents")
        
        # Get all chapters in order
        all_chapters = []
        for title in sorted(course_map.keys()):
            if "Chapter" in title and title != "Table of contents":
                chapter_number = extract_chapter_number(title)
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
        toc_blocks = get_all_blocks_from_id(toc_page_id)
        content = "\n\n".join(filter(None, [convert_block_to_markdown(b) for b in toc_blocks]))
        
        # Preload first chapter content for performance
        first_chapter_content = None
        if first_chapter_title:
            try:
                print(f"Preloading first chapter: {first_chapter_title}")
                chapter_page_id = course_map.get(first_chapter_title)
                if chapter_page_id:
                    chapter_blocks = get_all_blocks_from_id(chapter_page_id)
                    first_chapter_content = "\n\n".join(filter(None, [convert_block_to_markdown(b) for b in chapter_blocks]))
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
    except Exception as e: 
        print(f"Error in get_table_of_contents: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-chapter-content', methods=['POST'])
def get_chapter_content():
    """Get content for a specific chapter"""
    try:
        build_course_map()
        data = request.get_json()
        chapter_title = data.get('title')
        
        if not chapter_title:
            return jsonify({"error": "Chapter title is required"}), 400
            
        chapter_page_id = course_map.get(chapter_title)
        if not chapter_page_id: 
            return jsonify({"error": f"Chapter '{chapter_title}' not found in course map."}), 404
            
        chapter_blocks = get_all_blocks_from_id(chapter_page_id)
        content = "\n\n".join(filter(None, [convert_block_to_markdown(b) for b in chapter_blocks]))
        
        return jsonify({"content": content})
    except Exception as e: 
        print(f"Error in get_chapter_content: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/complete-chapter', methods=['POST'])
def complete_chapter():
    """Mark a chapter as completed and unlock the next one"""
    try:
        data = request.get_json()
        completed_chapter = data.get('chapter_title')
        
        if not completed_chapter:
            return jsonify({"error": "Chapter title is required"}), 400
            
        # Extract chapter number
        chapter_number = extract_chapter_number(completed_chapter)
        if not chapter_number:
            return jsonify({"error": "Invalid chapter format"}), 400
            
        # Get all chapters again to determine next chapter
        build_course_map()
        all_chapters = []
        for title in sorted(course_map.keys()):
            if "Chapter" in title and title != "Table of contents":
                chapter_num = extract_chapter_number(title)
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
        
    except Exception as e:
        print(f"Error in complete_chapter: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/classify-intent', methods=['POST'])
def classify_intent():
    """Endpoint that determines if user wants to continue or ask a question"""
    try:
        data = request.get_json()
        user_input = data.get('user_input', '').strip()
        current_section = data.get('current_section_title', '')
        next_section = data.get('next_section_title', '')
        
        if not user_input:
            return jsonify({"error": "User input is required"}), 400
            
        intent = classify_user_intent(user_input, current_section, next_section)
        return jsonify({"intent": intent})
        
    except Exception as e:
        print(f"Error in classify_intent: {e}")
        return jsonify({"intent": "QUESTION"})  # Safe fallback

@app.route('/generate-quick-actions', methods=['POST'])
def generate_quick_actions_endpoint():
    """Endpoint that generates contextual quick action buttons"""
    try:
        data = request.get_json()
        section_content = data.get('section_content', '').strip()
        
        if not section_content:
            return jsonify({"error": "Section content is required"}), 400
            
        actions = generate_quick_actions(section_content)
        return jsonify({"actions": actions})
        
    except Exception as e:
        print(f"Error in generate_quick_actions_endpoint: {e}")
        # Safe fallback - still specific
        return jsonify({"actions": ["What is the main topic?", "How does this work?", "What are the steps?"]})

@app.route('/ask-question', methods=['POST'])
def ask_question():
    """Non-streaming AI tutoring endpoint (fallback) with empathetic responses"""
    data = request.get_json()
    question = data.get('question')
    context = data.get('context')
    current_chapter_title = data.get('current_chapter_title', '')
    
    if not question or not context: 
        return jsonify({"error": "Question and context required."}), 400

    # Updated system prompt for better responses
    system_prompt = (
        "You are Hylee, a friendly and empathetic multifamily real estate tutor. "
        "Always be warm, understanding, and helpful. "
        
        "Rules: "
        "1) Answer in 1-2 sentences max using only the provided context. "
        "2) For chapter completion time questions: Give realistic estimates based on content length (typically 10-15 minutes per chapter). "
        "3) For off-topic questions, be understanding and try to connect to course content when possible. "
        "4) Always maintain a warm, encouraging tone. Never sound robotic or dismissive. "
        "5) Be conversational and show genuine interest in helping them learn. "
        "6) Don't mention future chapters unless specifically asked about course progression."
    )
    
    # Truncate context if too long to speed up processing
    max_context_length = 2000
    if len(context) > max_context_length:
        context = context[:max_context_length] + "..."
    
    user_message = f"Current Chapter: {current_chapter_title}\nContext: {context}\n\nQ: {question}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=120,  # Slightly increased for more empathetic responses
            temperature=0.7,  # Increased for more natural, human-like responses
            top_p=0.9,
            frequency_penalty=0.1,
            stream=False
        )
        return jsonify({"answer": response.choices[0].message.content})
    except Exception as e:
        print(f"Error in ask_question: {e}")
        return jsonify({"answer": "I'm sorry, I encountered an issue. Could you try rephrasing?"})

# --- Streaming AI Response Endpoint with Empathetic Responses ---
@app.route('/ask-question-stream', methods=['POST'])
def ask_question_stream():
    """Streaming AI tutoring endpoint for real-time empathetic responses"""
    data = request.get_json()
    question = data.get('question')
    context = data.get('context')
    current_chapter_title = data.get('current_chapter_title', '')
    
    if not question or not context: 
        return jsonify({"error": "Question and context required."}), 400

    def generate_streaming_response():
        """Generator function for streaming OpenAI responses"""
        # Updated system prompt
        system_prompt = (
            "You are Hylee, a friendly and empathetic multifamily real estate tutor. "
            "Always be warm, understanding, and helpful. "
            
            "Rules: "
            "1) Answer in 1-2 sentences max using only the provided context. "
            "2) For chapter completion time questions: Give realistic estimates based on content length (typically 10-15 minutes per chapter). "
            "3) For off-topic questions, be understanding and try to connect to course content when possible. "
            "4) Always maintain a warm, encouraging tone. Never sound robotic or dismissive. "
            "5) Be conversational and show genuine interest in helping them learn. "
            "6) Don't mention future chapters unless specifically asked about course progression."
        )
        
        # Truncate context if too long
        max_context_length = 2000
        truncated_context = context[:max_context_length] + "..." if len(context) > max_context_length else context
        
        user_message = f"Current Chapter: {current_chapter_title}\nContext: {truncated_context}\n\nQ: {question}"

        try:
            # Create streaming completion
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=120,  # Slightly increased for more empathetic responses
                temperature=0.7,  # Increased for more natural, human-like responses
                top_p=0.9,
                frequency_penalty=0.1,
                stream=True  # Enable streaming
            )
            
            # Stream the response
            for chunk in response:
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta:
                        content = delta['content']
                        # Send each chunk as Server-Sent Event
                        yield f"data: {json.dumps({'content': content})}\n\n"
            
            # Send completion signal
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            print(f"Error in streaming: {e}")
            yield f"data: {json.dumps({'error': 'Sorry, I encountered an issue.'})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(
        generate_streaming_response(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "message": "Course API is running"})

if __name__ == '__main__':
    # Use environment port for production, 5001 for development
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
