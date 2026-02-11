import os
import chromadb
from chromadb.utils import embedding_functions
from PyPDF2 import PdfReader
from config import (
    VECTOR_CHUNK_SIZE,
    VECTOR_CHUNK_OVERLAP,
    VECTOR_BATCH_SIZE,
    VECTOR_N_RESULTS,
    VECTOR_DISTANCE_THRESHOLD
)

# -----------------------------
# PDF Text Extraction
# -----------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""  # handle None pages
    return text

# -----------------------------
# Split text into chunks
# -----------------------------
def split_text(text: str, chunk_size: int = VECTOR_CHUNK_SIZE, overlap: int = VECTOR_CHUNK_OVERLAP) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

# -----------------------------
# Persistent ChromaDB Setup
# -----------------------------
PERSIST_DIR = "chroma_storage"
os.makedirs(PERSIST_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=PERSIST_DIR)

# Embedding function
ollama_ef = embedding_functions.OllamaEmbeddingFunction(model_name="nomic-embed-text:v1.5")

# Create or load collection
collection = client.get_or_create_collection(
    name="docs",
    embedding_function=ollama_ef
)

# -----------------------------
# Add PDF to VectorDB
# -----------------------------
def add_pdf_to_vectordb(pdf_path: str):
    # Extract text
    pdf_text = extract_text_from_pdf(pdf_path)
    
    # Split into chunks using config parameters
    chunks = split_text(pdf_text)
    
    # Generate unique IDs to avoid collisions
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    ids = [f"{base_name}_chunk_{i}" for i in range(len(chunks))]
    
    # Add to collection in batches
    batch_size = VECTOR_BATCH_SIZE
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        
        collection.add(
            documents=batch_chunks,
            ids=batch_ids
        )
        print(f"✅ Added batch {i//batch_size + 1}: {len(batch_chunks)} chunks")
    
    print(f"✅ Total: Added {len(chunks)} chunks from {pdf_path} to collection.")

# -----------------------------
# Query VectorDB
# -----------------------------
def query_vectordb(query_text: str, n_results: int = VECTOR_N_RESULTS):
    """
    Query the vector database and return relevant chunks.
    Filters results based on distance threshold from config.
    """
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    # Filter results by distance threshold
    filtered_documents = []
    filtered_distances = []
    
    if results['distances'] and results['documents']:
        for doc, distance in zip(results['documents'][0], results['distances'][0]):
            if distance <= VECTOR_DISTANCE_THRESHOLD:
                filtered_documents.append(doc)
                filtered_distances.append(distance)
    
    return {
        'documents': filtered_documents,
        'distances': filtered_distances,
        'total_found': len(filtered_documents)
    }

# -----------------------------
# Example Usage & Testing
# -----------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("BMSCE Assistant - Vector Database Setup")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Chunk Size: {VECTOR_CHUNK_SIZE}")
    print(f"  Chunk Overlap: {VECTOR_CHUNK_OVERLAP}")
    print(f"  Batch Size: {VECTOR_BATCH_SIZE}")
    print(f"  Distance Threshold: {VECTOR_DISTANCE_THRESHOLD}")
    print(f"  N Results: {VECTOR_N_RESULTS}")
    print("\n" + "=" * 60)
    
    # Add PDFs to vector database
    pdf_files = ["Data/hostel_rule.pdf"]
    for pdf in pdf_files:
        if os.path.exists(pdf):
            add_pdf_to_vectordb(pdf)
        else:
            print(f"⚠️  Warning: {pdf} not found")
 