# services/notion_service.py
import os
import config
from notion_client import Client

# Initialize Notion client
notion = Client(auth=config.NOTION_API_KEY)
course_map = None

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

def build_course_map(database_id, course_name=config.COURSE_NAME):
    """Build a map of all course content from Notion database"""
    global course_map
    if course_map is not None: return course_map
    
    print("Building course map...")
    db_response = notion.databases.query(
        database_id=database_id, 
        filter={"property": "Course Name", "title": {"equals": course_name}}
    )
    pages = db_response.get("results", [])
    if not pages: raise Exception(f"Could not find '{course_name}' page.")
    
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
    return course_map

def get_chapter_content(course_map, chapter_title):
    """Get content for a specific chapter"""
    chapter_page_id = course_map.get(chapter_title)
    if not chapter_page_id: 
        raise ValueError(f"Chapter '{chapter_title}' not found in course map.")
        
    chapter_blocks = get_all_blocks_from_id(chapter_page_id)
    content = "\n\n".join(filter(None, [convert_block_to_markdown(b) for b in chapter_blocks]))
    
    return content

def extract_chapter_number(title):
    """Extract chapter number from title like 'Chapter 1: Introduction'"""
    import re
    match = re.search(r'Chapter\s+(\d+)', title, re.IGNORECASE)
    return int(match.group(1)) if match else None