# services/ai_service.py
from openai import OpenAI
import config
import re

# Initialize the OpenAI client
client = OpenAI(api_key=config.OPENAI_API_KEY)

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
        response = client.chat.completions.create(
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
        response = client.chat.completions.create(
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

def ask_question(question, context, current_chapter_title=''):
    """Non-streaming AI tutoring endpoint with empathetic responses"""
    if not question or not context: 
        raise ValueError("Question and context required.")

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
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=120,
            temperature=0.7,
            top_p=0.9,
            frequency_penalty=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in ask_question: {e}")
        return "I'm sorry, I encountered an issue. Could you try rephrasing?"

def stream_response(question, context, current_chapter_title=''):
    """Streaming AI tutoring endpoint for real-time empathetic responses"""
    if not question or not context: 
        raise ValueError("Question and context required.")

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

    print("Making OpenAI API call...")
    # Create streaming completion
    return client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=120,
        temperature=0.7,
        top_p=0.9,
        frequency_penalty=0.1,
        stream=True  # Enable streaming
    )

def test_connection():
    """Test OpenAI connectivity"""
    try:
        # Simple test query
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=10
        )
        return True, response.choices[0].message.content
    except Exception as e:
        return False, str(e)
