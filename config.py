"""
Configuration file for BMSCE Assistant
Adjust these parameters to optimize performance and accuracy
"""

# ============================================
# VECTOR DATABASE SETTINGS
# ============================================

# Distance threshold for relevance filtering
# Lower value = stricter matching (only very similar results)
# Higher value = more lenient matching (allows less similar results)
# Recommended range: 0.8 - 1.5
# Start with 1.2 and adjust based on your testing
VECTOR_DISTANCE_THRESHOLD = 1.2  # Stricter matching to avoid irrelevant chunks

# Number of chunks to retrieve from vector database
# More chunks = more context but slower response
# Recommended: 3-5
VECTOR_N_RESULTS = 3  # Get more chunks but filter strictly by threshold

# Chunk size for splitting documents
# Larger chunks = more context per chunk but fewer chunks
# Smaller chunks = more precise matching but may lose context
# Recommended: 600-1000
VECTOR_CHUNK_SIZE = 600  # Smaller chunks for more precise matching

# Overlap between chunks
# Higher overlap = better context continuity but more chunks
# Recommended: 10-20% of chunk size
VECTOR_CHUNK_OVERLAP = 60

# Batch size for adding documents to vector DB
# Higher = faster initial indexing but more memory
VECTOR_BATCH_SIZE = 100

# ============================================
# LLM GENERATION SETTINGS
# ============================================

# Model to use (ensure it's installed in Ollama)
LLM_MODEL = "mistral:7b"

# Temperature for tool selection (lower = more deterministic)
# Recommended: 0.05 - 0.1
TOOL_SELECTION_TEMPERATURE = 0.05

# Temperature for natural responses (higher = more creative)
# Recommended: 0.6 - 0.8
RESPONSE_TEMPERATURE = 0.2

# Temperature for casual chat (higher = more natural)
# Recommended: 0.7 - 0.9
CHAT_TEMPERATURE = 0.7

# Maximum tokens for tool selection
# Lower = faster tool selection
TOOL_SELECTION_MAX_TOKENS = 50

# Maximum tokens for natural responses
# Lower = faster but potentially cut-off responses
RESPONSE_MAX_TOKENS = 1000  # Increased for complete answers

# Maximum tokens for casual chat
# Lower = faster, more concise chat
CHAT_MAX_TOKENS = 150

# Top-p sampling for generation
# Lower = more focused responses
# Recommended: 0.5 - 0.9
TOP_P = 0.9

# ============================================
# STREAMING SETTINGS
# ============================================

# Enable streaming responses (word-by-word vs all at once)
# True = Streaming enabled (text appears as it's generated)
# False = Non-streaming (wait for complete response)
# Recommended: True for better user experience
ENABLE_STREAMING = True

# ============================================
# WEB SCRAPING SETTINGS
# ============================================

# Timeout for web requests (seconds)
WEB_REQUEST_TIMEOUT = 10

# ============================================
# PERFORMANCE TUNING NOTES
# ============================================

"""
CURRENT CONFIGURATION EXPLANATION:

VECTOR_DISTANCE_THRESHOLD = 0.6
- Very strict matching
- Only returns highly relevant chunks
- Prevents mixing of unrelated information
- Lower values = more precise results

VECTOR_N_RESULTS = 5
- Retrieves more chunks initially
- But threshold filters to only relevant ones
- Better than retrieving fewer chunks

VECTOR_CHUNK_SIZE = 600
- Smaller chunks for better precision
- Each chunk focuses on specific topic
- Reduces mixing of different subjects

RESPONSE_MAX_TOKENS = 400
- Allows for complete, detailed answers
- Gives LLM space to extract relevant info

WHY THESE SETTINGS?

Problem: User asks about "ACM Club" but gets info about other clubs too
Solution:
1. Stricter threshold (0.6) ensures only ACM-related chunks
2. Better prompt tells LLM to focus only on user's question
3. Smaller chunks (600) prevent mixing topics in one chunk
4. More tokens (400) allow LLM to properly filter and respond

TESTING YOUR CONFIGURATION:

Run this to see distance values:
    python vector_db.py

Then test with queries like:
- "Tell me about ACM Club"
- "What is IEEE chapter?"
- "Information about NSS"

Each should return ONLY information about that specific topic.

If you see mixed results:
- Lower VECTOR_DISTANCE_THRESHOLD (try 0.5 or 0.4)
- Reduce VECTOR_CHUNK_SIZE (try 500)
- The prompt in client.py is already optimized to filter

ALTERNATIVE CONFIGURATIONS:

For Maximum Precision:
    VECTOR_DISTANCE_THRESHOLD = 0.5
    VECTOR_N_RESULTS = 7
    VECTOR_CHUNK_SIZE = 500
    RESPONSE_MAX_TOKENS = 400

For Balanced (More Context):
    VECTOR_DISTANCE_THRESHOLD = 0.8
    VECTOR_N_RESULTS = 4
    VECTOR_CHUNK_SIZE = 700
    RESPONSE_MAX_TOKENS = 350

For Speed (Less Precise):
    VECTOR_DISTANCE_THRESHOLD = 1.0
    VECTOR_N_RESULTS = 2
    VECTOR_CHUNK_SIZE = 800
    RESPONSE_MAX_TOKENS = 250
"""