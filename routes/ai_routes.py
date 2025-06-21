# routes/ai_routes.py
from flask import Blueprint, jsonify, request, Response
import json
from auth import require_auth
from services import ai_service
from utils.error_handler import handle_error, ApiError

# Create blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

@ai_bp.route('/classify-intent', methods=['POST'])
@require_auth
def classify_intent():
    """Endpoint that determines if user wants to continue or ask a question"""
    try:
        data = request.get_json()
        user_input = data.get('user_input', '').strip()
        current_section = data.get('current_section_title', '')
        next_section = data.get('next_section_title', '')
        
        if not user_input:
            raise ApiError("User input is required", 400)
            
        intent = ai_service.classify_user_intent(user_input, current_section, next_section)
        return jsonify({"intent": intent})
        
    except ApiError as e:
        return handle_error(e, e.status_code)
    except Exception as e:
        # Safe fallback for this specific endpoint
        return jsonify({"intent": "QUESTION"})

@ai_bp.route('/quick-actions', methods=['POST'])
@require_auth
def generate_quick_actions():
    """Endpoint that generates contextual quick action buttons"""
    try:
        data = request.get_json()
        section_content = data.get('section_content', '').strip()
        
        if not section_content:
            raise ApiError("Section content is required", 400)
            
        actions = ai_service.generate_quick_actions(section_content)
        return jsonify({"actions": actions})
        
    except ApiError as e:
        return handle_error(e, e.status_code)
    except Exception as e:
        print(f"Error in generate_quick_actions: {e}")
        # Safe fallback - still specific
        return jsonify({"actions": ["What is the main topic?", "How does this work?", "What are the steps?"]})

@ai_bp.route('/ask', methods=['POST'])
@require_auth
def ask_question():
    """Non-streaming AI tutoring endpoint (fallback) with empathetic responses"""
    try:
        data = request.get_json()
        question = data.get('question')
        context = data.get('context')
        current_chapter_title = data.get('current_chapter_title', '')
        
        if not question or not context: 
            raise ApiError("Question and context required.", 400)

        answer = ai_service.ask_question(question, context, current_chapter_title)
        return jsonify({"answer": answer})
    except ApiError as e:
        return handle_error(e, e.status_code)
    except Exception as e:
        print(f"Error in ask_question: {e}")
        return jsonify({"answer": "I'm sorry, I encountered an issue. Could you try rephrasing?"})

@ai_bp.route('/ask-stream', methods=['POST'])
@require_auth
def ask_question_stream():
    """Streaming AI tutoring endpoint for real-time empathetic responses"""
    try:
        data = request.get_json()
        question = data.get('question')
        context = data.get('context')
        current_chapter_title = data.get('current_chapter_title', '')
        
        print(f"Streaming endpoint called - Question: {question[:50]}...")
        
        if not question or not context: 
            raise ApiError("Question and context required.", 400)

        def generate_streaming_response():
            """Generator function for streaming OpenAI responses"""
            try:
                # Get streaming response from AI service
                response = ai_service.stream_response(question, context, current_chapter_title)
                
                print("OpenAI API call successful, starting stream...")
                
                # Stream the response
                for chunk in response:
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            content = delta['content']
                            print(f"Received chunk: {content}")
                            # Send each chunk as Server-Sent Event
                            yield f"data: {json.dumps({'content': content})}\n\n"
                
                print("Streaming complete")
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
    except ApiError as e:
        return handle_error(e, e.status_code)
    except Exception as e:
        print(f"Error setting up streaming: {e}")
        return jsonify({"error": "Failed to set up streaming response"}), 500

@ai_bp.route('/test', methods=['GET'])
def test_openai():
    """Test OpenAI connectivity"""
    try:
        success, result = ai_service.test_connection()
        if success:
            return f"""
            <html>
                <body>
                    <h1>OpenAI API Test</h1>
                    <p><strong>Status:</strong> Success</p>
                    <p><strong>Response:</strong> {result}</p>
                    <p><a href="/">Return to course</a></p>
                </body>
            </html>
            """
        else:
            return f"""
            <html>
                <body>
                    <h1>OpenAI API Test</h1>
                    <p><strong>Status:</strong> Error</p>
                    <p><strong>Error:</strong> {result}</p>
                    <p><a href="/">Return to course</a></p>
                </body>
            </html>
            """
    except Exception as e:
        return handle_error(e)