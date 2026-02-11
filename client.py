import asyncio
import json
import sys
import time
from typing import Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama

from config import (
    LLM_MODEL, TOOL_SELECTION_TEMPERATURE, RESPONSE_TEMPERATURE,
    CHAT_TEMPERATURE, TOOL_SELECTION_MAX_TOKENS, RESPONSE_MAX_TOKENS,
    CHAT_MAX_TOKENS, TOP_P, ENABLE_STREAMING
)

class MCPClient:
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
        print(f"✅ Connected to MCP Server\n")

    async def process_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        if not self.session:
            raise RuntimeError("Not connected to server")
        result = await self.session.call_tool(tool_name, tool_args)
        return result.content[0].text

    async def generate_response(self, prompt: str, temperature: float, max_tokens: int):
        if ENABLE_STREAMING:
            try:
                stream = ollama.generate(
                    model=LLM_MODEL, prompt=prompt, stream=True,
                    options={"temperature": temperature, "top_p": TOP_P, "num_predict": max_tokens}
                )
                for chunk in stream:
                    if 'response' in chunk:
                        print(chunk['response'], end='', flush=True)
                print("\n")
            except Exception as e:
                print(f"Streaming error: {e}. Fallback to non-streaming.")
                response = ollama.generate(
                    model=LLM_MODEL, prompt=prompt,
                    options={"temperature": temperature, "top_p": TOP_P, "num_predict": max_tokens}
                )
                print(f"{response['response'].strip()}\n")
        else:
            response = ollama.generate(
                model=LLM_MODEL, prompt=prompt,
                options={"temperature": temperature, "top_p": TOP_P, "num_predict": max_tokens}
            )
            print(f"{response['response'].strip()}\n")

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
        
        await self.generate_response(prompt, 0.2, RESPONSE_MAX_TOKENS)

    async def _handle_chat_fallback(self, user_message: str, error_message: str = None):
        # If error is just "No results", be helpful.
        if error_message and "found" in error_message.lower():
             print("I checked my database, but I couldn't find that specific information.\n")
             return

        chat_prompt = f"""You are BMSCE Assistant.
    User: {user_message}
    Respond warmly and concisely. No markdown unless necessary.
    Response:"""
        await self.generate_response(chat_prompt, CHAT_TEMPERATURE, CHAT_MAX_TOKENS)

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
                # This captures "Software Engineering" from "Is there software engineering"
                # removing common stop words roughly
                clean_term = user_message.lower().replace("is there", "").replace("any", "").replace("subject", "").strip()
                tool_args['search_term'] = clean_term

        # Fix 2: get_professor_details missing name
        if tool_name == 'get_professor_details':
            if 'name' not in tool_args:
                 # Try to grab the name from the query
                 clean_name = user_message.lower().replace("who is", "").replace("professor", "").replace("email", "").strip()
                 tool_args['name'] = clean_name

        return tool_args

    async def chat_with_mistral(self, user_message: str):
        # Decision prompt 
        decision_prompt = f"""Analyze the user's question and select the BEST tool.

Tools:
1. get_latest_news - news, events
2. get_college_notifications - official notices
3. query_knowledge_base - generic search (clubs, rules, history, campus, hostels). Usage: {{"tool": "query_knowledge_base", "arguments": {{"query_text": "search query"}}}}
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
            await self._handle_chat_fallback(user_message)
            return

        tool_name = tool_call.get('tool')
        tool_args = tool_call.get('arguments', {})

        # --- NEW STEP: Sanitize Arguments ---
        # This fixes the "Missing arguments" crash by auto-filling missing keys
        tool_args = self._sanitize_tool_args(tool_name, tool_args, user_message)

        # Strict Validation (Last Line of Defense)
        required_args = self.tool_arg_map.get(tool_name)
        if required_args and not all(arg in tool_args and tool_args[arg] for arg in required_args):
            print(f"⚠️ Missing arguments for {tool_name} even after sanitization. Fallback to chat.\n")
            await self._handle_chat_fallback(user_message, "Missing args")
            return

        try:
            print("🔍 Searching...", end='', flush=True)
            raw_data = await self.process_tool_call(tool_name, tool_args)
            print("\r" + " " * 20 + "\r", end='', flush=True)
            
            # Basic error checking
            is_error = False
            try:
                data_json = json.loads(raw_data)
                if isinstance(data_json, dict) and ('error' in data_json):
                    is_error = True
                    # If "ambiguous" or "tips", it's not a hard error, let LLM explain
                    if "ambiguous" in str(data_json.get('error')).lower() or "tip" in str(data_json): 
                        is_error = False 
                elif isinstance(data_json, list) and len(data_json) == 0:
                    is_error = True
            except:
                pass
            
            if is_error:
                print(f"🤔 The search didn't return a result.")
                await self._handle_chat_fallback(user_message, raw_data)
                return

            await self.make_natural_response(user_message, raw_data)

        except Exception as e:
            print(f"Oops! Trouble getting info. {e}\n")
            await self.make_natural_response(user_message, f"Error: {e}")

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

    async def close(self):
        if self.session_context: await self.session_context.__aexit__(None, None, None)
        if self.client_context: await self.client_context.__aexit__(None, None, None)

async def main():
    client = MCPClient()
    print("\n🎓 BMSCE Assistant (Robust & Universal) 🤖\n")
    try:
        await client.connect_to_server("main.py")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit']: break
            if not user_input: continue
            print()
            await client.chat_with_mistral(user_input)
            print("─" * 60 + "\n")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())