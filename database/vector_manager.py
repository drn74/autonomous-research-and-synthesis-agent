import os
from pathlib import Path
from langchain_chroma import Chroma
from core.llm import get_gemini_embeddings
from core.config import console

CHROMA_PATH = "data/chroma_db"

class VectorManager:
    def __init__(self, collection_name: str = "arsa_knowledge"):
        self.embeddings = get_gemini_embeddings()
        self.collection_name = collection_name
        self.persist_directory = CHROMA_PATH
        
        # Ensure the directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
        console.print(f"[dim]VectorStore initialized in {self.persist_directory}[/dim]")

    def add_chunks(self, session_id: str, url: str, chunks: list[str], metadatas: list[dict]):
        """
        Adds multiple chunks to the vector store with session filtering.
        """
        # Enhance metadatas with session_id and source_url for filtering
        for meta in metadatas:
            meta["session_id"] = session_id
            meta["source_url"] = url
            
        try:
            self.vector_store.add_texts(texts=chunks, metadatas=metadatas)
            # We don't need a loud message here as it happens for every file
        except Exception as e:
            console.print(f"[bold red]Vector DB Error (add_chunks): {e}[/bold red]")

    def query(self, session_id: str, query_text: str, n_results: int = 5):
        """
        Searches the vector store for relevant chunks within a specific session.
        """
        try:
            results = self.vector_store.similarity_search(
                query_text,
                k=n_results,
                filter={"session_id": session_id}
            )
            return results
        except Exception as e:
            console.print(f"[bold red]Vector DB Error (query): {e}[/bold red]")
            return []
