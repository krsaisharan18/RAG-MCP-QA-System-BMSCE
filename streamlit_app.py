import streamlit as st
import asyncio
import json
import ollama
from typing import Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import (
    LLM_MODEL, TOOL_SELECTION_TEMPERATURE, RESPONSE_TEMPERATURE,
    CHAT_TEMPERATURE, TOOL_SELECTION_MAX_TOKENS, RESPONSE_MAX_TOKENS,
    CHAT_MAX_TOKENS, TOP_P, ENABLE_STREAMING
)

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="BMSCE Assistant",
    page_icon="🎓",
    layout="centered"
)

# --- Custom CSS for Chat Interface ---
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #f0f2f6;
    }
    .stChatMessage[data-testid="stChatMessageAssistant"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# --- MCP Client Class (Adapted for Streamlit) ---
class StreamlitMCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.available_tools = []
        self.client_context = None
        self.session_context = None
        # Map tools for validation
        self.tool_arg_map = {
            'query_knowledge_base': ['query_text'],
            'get_professor_details': ['name'],
            'get_syllabus_info': ['query_type', 'search_term']
        }

    async def connect_to_server(self, server_script_path: str):
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None
        )
        self.client_context = stdio_client(server_params)
        self.stdio, self.write = await self.client_context.__aenter__()
        self.session_context = ClientSession(self.stdio, self.write)
        self.session = await self.session_context.__aenter__()
        await self.session.initialize()
        response = await self.session.list_tools()
        self.available_tools = response.tools
        # print(f"✅ Connected to MCP Server")

    async def process_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.call_tool(tool_name, tool_args)
        return result.content[0].text

    async def generate_response(self, prompt: str, temperature: float, max_tokens: int):
        # Use streaming with Ollama
        stream = ollama.generate(
            model=LLM_MODEL, prompt=prompt, stream=ENABLE_STREAMING,
            options={"temperature": temperature, "top_p": TOP_P, "num_predict": max_tokens}
        )
        for chunk in stream:
            if 'response' in chunk:
                yield chunk['response']

    async def make_natural_response(self, user_query: str, raw_data: str):
        # --- UNIVERSAL STRICT FILTERING PROMPT ---
        prompt = f"""You are a precise information assistant for BMSCE.

USER QUESTION: "{user_query}"

RETRIEVED KNOWLEDGE BASE DATA:
{raw_data}

--- INSTRUCTIONS ---
0. Use only common nouns and gender-neutral language. Do not use gendered pronouns such as he or she; use they, the person, the individual, or similar terms.
1. FILTER STRICTLY: The data above may contain lists of multiple items.
2. SELECT ONLY: Extract *only* the specific information that answers the User Question.
3. IGNORE OTHERS: If the data lists "Item A, Item B" and the user asked about "Item B", DO NOT mention A.
4. FORMAT: Present the answer cleanly. Use bullet points only for details regarding the *specific* topic requested.
5. UNKNOWN: If the retrieved data does not contain the answer, say "I couldn't find specific details about that in my database."
6. HOD of CSE is Dr. Kavitha Sooda 

Your Response:"""
        
        # Return the generator directly
        return self.generate_response(prompt, RESPONSE_TEMPERATURE, RESPONSE_MAX_TOKENS)

    async def _handle_chat_fallback(self, user_message: str, error_message: str = None):
        # If error is just "No results", be helpful.
        if error_message and "found" in error_message.lower():
             async def simple_gen():
                 yield "I checked my database, but I couldn't find that specific information."
             return simple_gen()

        chat_prompt = f"""You are BMSCE Assistant.
    User: {user_message}
    Respond warmly and concisely. No markdown unless necessary.
    Response:"""
        return self.generate_response(chat_prompt, CHAT_TEMPERATURE, CHAT_MAX_TOKENS)

    def _sanitize_tool_args(self, tool_name: str, tool_args: dict, user_message: str) -> dict:
        """
        Fixes common LLM mistakes in argument generation.
        """
        # Fix 1: get_syllabus_info missing query_type
        if tool_name == 'get_syllabus_info':
            if 'query_type' not in tool_args:
                # Default to subject_detail if implied
                tool_args['query_type'] = 'subject_detail'
            
            if 'search_term' not in tool_args:
                # Fallback: Use the whole user message as search term if missing
                clean_term = user_message.lower().replace("is there", "").replace("any", "").replace("subject", "").strip()
                tool_args['search_term'] = clean_term

        # Fix 2: get_professor_details missing name
        if tool_name == 'get_professor_details':
            if 'name' not in tool_args:
                 # Try to grab the name from the query
                 clean_name = user_message.lower().replace("who is", "").replace("professor", "").replace("email", "").strip()
                 tool_args['name'] = clean_name

        return tool_args

    def _extract_tool_call(self, text: str) -> Optional[dict]:
        try:
            text = text.replace('```json', '').replace('```', '').strip()
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
        except:
            pass
        return None

    async def process_message(self, user_message: str):
        # Decision prompt 
        decision_prompt = f"""Analyze the user's question and select the BEST tool.

Tools:
1. get_latest_news - news, events
2. get_college_notifications - official notices
3. query_knowledge_base - generic search (placements,recruiting companies,clubs, rules, history, campus, hostels). Usage: {{"tool": "query_knowledge_base", "arguments": {{"query_text": "search query"}}}}
4. get_professor_details - email/phone of profs (requires "name")
5. get_syllabus_info - syllabus/subjects. Usage:
   - "subjects in 5th sem" -> {{"tool": "get_syllabus_info", "arguments": {{"query_type": "semester_list", "search_term": "5"}}}}
   - "is there any software engineering subject" -> {{"tool": "get_syllabus_info", "arguments": {{"query_type": "subject_detail", "search_term": "software engineering"}}}}
   - "details of DBMS" -> {{"tool": "get_syllabus_info", "arguments": {{"query_type": "subject_detail", "search_term": "DBMS"}}}}
6. none - greetings, casual chat

Question: "{user_message}"

Respond ONLY with a JSON object: {{"tool": "tool_name", "arguments": {{...}}}}
JSON:"""

        decision_response = ollama.generate(
            model=LLM_MODEL, prompt=decision_prompt,
            options={"temperature": TOOL_SELECTION_TEMPERATURE, "top_p": 0.5, "num_predict": TOOL_SELECTION_MAX_TOKENS}
        )

        tool_call = self._extract_tool_call(decision_response['response'])
        
        if not tool_call or tool_call.get('tool') == 'none':
            return await self._handle_chat_fallback(user_message)

        tool_name = tool_call.get('tool')
        tool_args = tool_call.get('arguments', {})

        # Sanitize Arguments
        tool_args = self._sanitize_tool_args(tool_name, tool_args, user_message)

        # Strict Validation
        required_args = self.tool_arg_map.get(tool_name)
        if required_args and not all(arg in tool_args and tool_args[arg] for arg in required_args):
            return await self._handle_chat_fallback(user_message, "Missing args")

        try:
            # st.info(f"Using tool: {tool_name}") # Optional: Show tool usage
            raw_data = await self.process_tool_call(tool_name, tool_args)
            
            # Basic error checking
            is_error = False
            try:
                data_json = json.loads(raw_data)
                if isinstance(data_json, dict) and ('error' in data_json):
                    is_error = True
                    if "ambiguous" in str(data_json.get('error')).lower() or "tip" in str(data_json): 
                        is_error = False 
                elif isinstance(data_json, list) and len(data_json) == 0:
                    is_error = True
            except:
                pass
            
            if is_error:
                return await self._handle_chat_fallback(user_message, raw_data)

            return await self.make_natural_response(user_message, raw_data)

        except Exception as e:
            async def error_gen():
                yield f"Error: {e}"
            return error_gen()

    async def close(self):
        if self.session_context: await self.session_context.__aexit__(None, None, None)
        if self.client_context: await self.client_context.__aexit__(None, None, None)


# --- Main App Logic ---

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("🎓 BMSCE Assistant")
st.caption("Ask me about syllabus, professors, news, or campus details!")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle input
if prompt := st.chat_input("How can I help you?"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        # Placeholder for streaming
        response_placeholder = st.empty()
        
        async def run_chat():
            client = StreamlitMCPClient()
            try:
                await client.connect_to_server("main.py")
                # process_message now returns an async generator
                response_gen = await client.process_message(prompt)
                
                # st.write_stream consumes the generator
                # Note: st.write_stream works with sync generators or iterables. 
                # For async generators, we need to bridge it or collect chunks.
                # Streamlit's write_stream supports async generators in newer versions, 
                # but to be safe and simple, let's iterate and update.
                
                full_response = ""
                # We need to iterate the async generator
                async for chunk in response_gen:
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                return full_response

            finally:
                await client.close()
        
        response_text = asyncio.run(run_chat())
    
    # Add assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response_text})
