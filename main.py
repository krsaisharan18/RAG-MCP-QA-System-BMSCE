import json
import difflib
import re
from fastmcp import FastMCP
from web_scrap import get_news_events, get_notifications
from vector_db import collection

# --- IMPORT DATA ---
from professor_resources import PROFESSOR_DATA

# Load Syllabus Data
try:
    with open('resources.json', 'r') as f:
        SYLLABUS_DATA = json.load(f)
except FileNotFoundError:
    SYLLABUS_DATA = []
    print("Warning: resources.json not found. Syllabus tool will be empty.")

mcp = FastMCP("MCP for BMS College of Engineering")

# --- HELPER CONFIGURATIONS & FUNCTIONS ---

# Common abbreviations mapping for BMSCE subjects
# This maps what users type -> to what is in the syllabus JSON
SUBJECT_ALIASES = {
    "dbms": "database management systems",
    "daa": "analysis and design of algorithms",
    "ada": "analysis and design of algorithms",
    "aiml": "artificial intelligence",
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "dl": "deep learning",
    "cn": "computer networks",
    "os": "operating systems",
    "coa": "computer organization",
    "oops": "object oriented",
    "java": "object oriented java",
    "dsa": "data structures",
    "rpa": "robot process automation",
    "hpc": "high performance computing",
    "nlp": "natural language processing",
    "iot": "internet of things",
    "uipath": "robot process automation",
    "web dev": "full stack web development"
}

def fuzzy_match(query: str, target: str, threshold: float = 0.6) -> bool:
    """
    Returns True if the query is similar enough to the target.
    Handles substring matches and typo tolerance.
    """
    if not query or not target:
        return False
        
    query = query.lower().strip()
    target = target.lower().strip()
    
    # 1. Direct Substring Match (Fastest & Most Reliable for exact phrases)
    if query in target:
        return True
        
    # 2. Sequence Matching (for typos like 'mashine' -> 'machine')
    # ratio() returns a float between 0 and 1 indicating similarity
    similarity = difflib.SequenceMatcher(None, query, target).ratio()
    return similarity >= threshold

# --- TOOLS ---

@mcp.tool()
def get_latest_news():
    """
    Extracts the 'News & Events' Website,
    and returns the data as a JSON string.
    """ 
    return get_news_events()


@mcp.tool()
def get_college_notifications():
    """
    Extracts 'College Notifications' from the Website,
    and returns the data as a JSON string.
    """
    return get_notifications()


@mcp.tool()
def query_knowledge_base(query_text: str, n_results: int = 3) -> str:
    """
    Queries the ChromaDB vector store to find the most relevant document chunks.
    """
    if not collection:
        return json.dumps({"error": "Cannot query. ChromaDB collection is not available."})
    
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        # Check if we actually got results
        if not results['documents'] or not results['documents'][0]:
             return json.dumps({"message": "No relevant documents found in knowledge base."})

        return json.dumps(results['documents'][0], indent=2)
    except Exception as e:
        return json.dumps({"error": f"An error occurred during the query: {e}"})


@mcp.tool()
def get_professor_details(name: str) -> str:
    """
    Searches for details (email, phone, department) for a specific professor.
    """
    search_name = name.lower().strip()
    found_professors = []
    
    for prof in PROFESSOR_DATA:
        # Use fuzzy match for names (handles "Kavita" vs "Kavitha")
        # Threshold 0.7 prevents matching "Smith" with "Smit" too loosely if names are short
        if fuzzy_match(search_name, prof["name"], threshold=0.7):
            found_professors.append(prof)
    
    if len(found_professors) == 1:
        return json.dumps(found_professors[0], indent=2)
    elif len(found_professors) > 1:
        matches = [p['name'] for p in found_professors]
        return json.dumps({
            "error": "Ambiguous query. Multiple professors found.",
            "matches": matches,
            "details": found_professors # Returning details so LLM can choose if needed
        })
    else:
        # Provide suggestions if no exact/fuzzy match found
        all_names = [p["name"] for p in PROFESSOR_DATA]
        suggestions = difflib.get_close_matches(name, all_names, n=3, cutoff=0.5)
        msg = f"Professor '{name}' not found."
        if suggestions:
            msg += f" Did you mean: {', '.join(suggestions)}?"
        return json.dumps({"error": msg})


@mcp.tool()
def get_syllabus_info(query_type: str, search_term: str) -> str:
    """
    Retrieves syllabus and subject information.
    
    Args:
        query_type: "semester_list" (list all subjects) OR "subject_detail" (search specific subject).
        search_term: The semester number (e.g. "5") OR the subject name (e.g. "Machine Learning", "DBMS").
    """
    data = SYLLABUS_DATA
    raw_search_term = str(search_term).strip().lower()
    
    # --- LOGIC 1: LIST ALL SUBJECTS IN A SEMESTER ---
    if query_type == "semester_list":
        # Extract digits only (e.g., "5th" -> 5, "sem 3" -> 3)
        digit_match = re.search(r'\d+', raw_search_term)
        target_sem = int(digit_match.group()) if digit_match else 0
        
        found_data = None
        
        # Handle First Year (Sem 1 & 2 grouped as year 1)
        if target_sem in [1, 2]:
            found_data = next((item for item in data if item.get("year") == 1), None)
        else:
            found_data = next((item for item in data if item.get("semester") == target_sem), None)
            
        if found_data:
            subjects = found_data.get("all_subjects", [])
            return json.dumps({
                "semester": target_sem,
                "total_subjects": len(subjects),
                "subjects": subjects
            }, indent=2)
        else:
            return json.dumps({"error": f"No syllabus data found for Semester {target_sem}."})

    # --- LOGIC 2: SUBJECT DETAILS / SEARCH ---
    elif query_type == "subject_detail":
        matches = []
        
        # Check if the user used an alias (e.g., "DBMS") and map it to full name
        actual_search_term = SUBJECT_ALIASES.get(raw_search_term, raw_search_term)
        
        for entry in data:
            sem_label = f"Semester {entry.get('semester')}" if 'semester' in entry else "1st Year"
            
            # Check detailed syllabus first
            if "detailed_syllabus" in entry:
                for subject in entry["detailed_syllabus"]:
                    t = subject["course_title"]
                    c = subject["course_code"]
                    
                    # Use fuzzy matching on Title OR Code
                    if fuzzy_match(actual_search_term, t) or fuzzy_match(actual_search_term, c):
                        subject_info = subject.copy()
                        subject_info["found_in"] = sem_label
                        matches.append(subject_info)
            
            # Check simple list if details not found
            elif "all_subjects" in entry:
                for subject in entry["all_subjects"]:
                     # Fuzzy match on Title
                     if fuzzy_match(actual_search_term, subject["title"]):
                        matches.append({
                            "title": subject["title"],
                            "code": subject["code"],
                            "found_in": sem_label,
                            "note": "Detailed syllabus modules not available."
                        })

        if len(matches) >= 1:
            # Return matches (Limit to top 5 to avoid token overflow)
            return json.dumps({
                "message": f"Found {len(matches)} subjects matching '{search_term}' (mapped to '{actual_search_term}').",
                "matches": matches[:5]
            }, indent=2)
        else:
            # Try to offer a helpful error message
            return json.dumps({
                "error": f"No subject found matching '{search_term}' (or '{actual_search_term}').",
                "tip": "Try using the full subject name or checking the semester list."
            })

    return json.dumps({"error": "Invalid query_type."})


if __name__ == "__main__":
    mcp.run()