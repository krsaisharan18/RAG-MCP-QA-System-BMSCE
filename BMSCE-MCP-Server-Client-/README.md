# 🎓 BMSCE Assistant

A friendly AI-powered chatbot for BMS College of Engineering students, built using the Model Context Protocol (MCP) and Mistral 7B. Get real-time updates on college events, notifications, and query academic documents—all through a natural conversational interface.

## ✨ Features

- 📰 **Latest News & Events**: Stay updated with college events, workshops, festivals, and happenings
- 📢 **College Notifications**: Access official notices, circulars, announcements, and deadlines
- 🔍 **Knowledge Base Query**: Search through uploaded PDF documents (syllabus, resumes, academic content)
- 💬 **Natural Conversation**: Friendly, student-oriented chat interface powered by Mistral 7B
- 🚀 **MCP Architecture**: Built on Model Context Protocol for extensible tool integration

## 🏗️ Architecture

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  client.py      │  ◄── Mistral 7B LLM (via Ollama)
│  (MCP Client)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   main.py       │
│  (MCP Server)   │
│                 │
│  Tools:         │
│  • get_latest_news
│  • get_college_notifications
│  • query_knowledge_base
└────────┬────────┘
         │
    ┌────┴────┬──────────────┐
    ▼         ▼              ▼
┌────────┐ ┌──────┐ ┌────────────────┐
│Web     │ │Web   │ │ChromaDB        │
│Scraper │ │Scraper│ │Vector Store    │
│(News)  │ │(Notif)│ │(PDF Documents) │
└────────┘ └──────┘ └────────────────┘
```

## 📋 Prerequisites

- **Python 3.8+**
- **Ollama** with the following models:
  - `mistral:7b` (LLM)
  - `nomic-embed-text:v1.5` (Embeddings)

### Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download
```

### Pull Required Models

```bash
ollama pull mistral:7b
ollama pull nomic-embed-text:v1.5
```

## 🚀 Installation

1. **Clone the repository**

```bash
git clone <your-repo-url>
cd bmsce-assistant
```

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

3. **Set up the vector database** (optional, for PDF querying)

If you want to add PDF documents to the knowledge base:

```bash
# Edit vector_db.py and add your PDF files to the pdf_files list
python vector_db.py
```

This will create a `chroma_storage` directory with indexed documents.

## 💻 Usage

### Running the Assistant

Start the chatbot with:

```bash
python client.py
```

You'll see a welcome screen:

```
🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓

   Welcome to BMSCE Assistant! 🤖
   Your friendly AI helper for all things BMS College

🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓 🎓

✅ Connected to MCP Server

💬 Hey there! Ask me about college events, notifications, or anything else!
   Type 'quit' or 'exit' when you're done.

────────────────────────────────────────────────────────────────

You: 
```

### Example Queries

**News & Events:**
```
You: What events are happening this month?
You: Tell me about upcoming workshops
You: Any festivals coming up?
```

**Notifications:**
```
You: What are the latest notifications?
You: Show me recent announcements
You: Any important deadlines?
```

**Knowledge Base:**
```
You: Search for syllabus information
You: Find details about [specific topic]
You: What does the document say about [query]?
```

**General Chat:**
```
You: Hi!
You: Thank you
You: How are you?
```

### Exiting

Type any of the following to exit:
- `quit`
- `exit`
- `bye`
- `goodbye`
- Or press `Ctrl+C`

## 📁 Project Structure

```
bmsce-assistant/
│
├── client.py              # MCP client with Mistral integration
├── main.py                # MCP server with tool definitions
├── web_scrap.py           # Web scrapers for BMSCE website
├── vector_db.py           # ChromaDB setup and PDF indexing
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore file
│
├── chroma_storage/        # ChromaDB persistent storage (auto-created)
└── *.pdf                  # Your PDF documents to index
```

## 🛠️ Components

### 1. MCP Server (`main.py`)

Defines three tools:

- **`get_latest_news()`**: Scrapes news and events from BMSCE website
- **`get_college_notifications()`**: Scrapes college notifications
- **`query_knowledge_base(query_text, n_results=3)`**: Queries ChromaDB vector store

### 2. MCP Client (`client.py`)

- Connects to the MCP server
- Uses Mistral 7B to:
  - Interpret user queries
  - Select appropriate tools
  - Generate natural, friendly responses
- Provides a conversational interface

### 3. Web Scraper (`web_scrap.py`)

- Scrapes the BMSCE website (https://bmsce.ac.in)
- Extracts structured data from:
  - News & Events section
  - College Notifications section
- Returns data in JSON format

### 4. Vector Database (`vector_db.py`)

- Uses ChromaDB for semantic search
- Indexes PDF documents with Nomic embeddings
- Supports chunked document retrieval

## 🔧 Configuration

### Adding PDF Documents

Edit `vector_db.py`:

```python
if __name__ == "__main__":
    pdf_files = [
        "syllabus.pdf",
        "handbook.pdf",
        "your_document.pdf"
    ]
    for pdf in pdf_files:
        add_pdf_to_vectordb(pdf)
```

Then run:

```bash
python vector_db.py
```

### Customizing LLM Behavior

In `client.py`, you can modify:

- **Temperature**: Controls randomness (0.1 = focused, 0.9 = creative)
- **Model**: Change `mistral:7b` to other Ollama models
- **Prompts**: Edit system prompts for different personalities

### Adjusting Chunk Size

In `vector_db.py`:

```python
chunks = split_text(pdf_text, chunk_size=1000, overlap=100)
```

## 🤝 How It Works

1. **User asks a question** → Sent to `client.py`
2. **Mistral analyzes** the query and decides which tool to use
3. **Client calls the tool** on the MCP server (`main.py`)
4. **Server executes** the tool:
   - Web scraping for news/notifications
   - Vector search for knowledge base queries
5. **Raw data returned** to client
6. **Mistral formats** the data into a natural response
7. **User sees friendly answer** 🎉

## 🐛 Troubleshooting

### "Not connected to server" error

- Make sure both `client.py` and `main.py` are in the same directory
- Check that Python can execute `main.py` as a subprocess

### Ollama model not found

```bash
# Pull the models
ollama pull mistral:7b
ollama pull nomic-embed-text:v1.5

# Verify installation
ollama list
```

### ChromaDB errors

- Delete `chroma_storage` folder and re-run `vector_db.py`
- Ensure PDF files exist in the project directory

### Web scraping fails

- Check your internet connection
- Verify the BMSCE website is accessible
- Website structure may have changed (update selectors in `web_scrap.py`)

## 📝 Dependencies

Key libraries:
- `fastmcp` - MCP server framework
- `mcp` - MCP client SDK
- `ollama` - Ollama Python client
- `chromadb` - Vector database
- `beautifulsoup4` - Web scraping
- `PyPDF2` - PDF text extraction

See `requirements.txt` for complete list.

## 🚧 Future Enhancements

- [ ] Add caching for web scraping results
- [ ] Support for more document formats (DOCX, TXT)
- [ ] Database for persistent conversation history
- [ ] Voice input/output
- [ ] Web interface (Gradio/Streamlit)
- [ ] Multi-language support
- [ ] Integration with college calendar
- [ ] Student authentication system



**Made with ❤️ for BMSCE students**

