import sqlite3
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List
from core.config import console

DB_PATH = "research.db"

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^\w\-_\. ]', '_', name)

def save_markdown_to_raw(url: str, content: str, session_id: str) -> str:
    """
    Saves markdown content to data/raw/ and records it in the database.
    Returns the filepath of the saved file.
    """
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = sanitize_filename(url.split('//')[-1][:40])
    filename = f"{timestamp}_{slug}.md"
    filepath = raw_dir / filename
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"---\nurl: {url}\ntimestamp: {timestamp}\n---\n\n")
            f.write(content)
            
        save_crawled_url(url, session_id, str(filepath))
        return str(filepath)
    except Exception as e:
        console.print(f"[bold red]Error saving markdown for {url}: {e}[/bold red]")
        return ""

def get_wsl_host_ip() -> str:
    """Returns localhost since we verified Ollama listens there."""
    return "127.0.0.1"

def clear_session(session_id: str):
    """Clears all data associated with a session to start fresh."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM crawled_urls WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM entities WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM knowledge_chunks WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        console.print(f"[dim]Database cleared for session: {session_id}[/dim]")
    except Exception as e:
        console.print(f"[bold red]DB Error (clear_session): {e}[/bold red]")

def save_knowledge_chunk(session_id: str, url: str, content: str, content_type: str):
    """Saves a specific piece of technical knowledge (code, recipe, snippet)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Create table if not exists (migration)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_url TEXT,
                content TEXT,
                content_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO knowledge_chunks (session_id, source_url, content, content_type)
            VALUES (?, ?, ?, ?)
        ''', (session_id, url, content, content_type))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (save_knowledge_chunk): {e}[/bold red]")

def get_knowledge_chunks(session_id: str) -> List[dict]:
    """Retrieves all extracted knowledge snippets for the current session."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT content, content_type, source_url FROM knowledge_chunks WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        console.print(f"[bold red]DB Error (get_knowledge_chunks): {e}[/bold red]")
        return []

def get_url_hash(url: str) -> str:
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def get_entities_from_db(session_id: str) -> List[str]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM entities WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        console.print(f"[bold red]DB Error (get_entities): {e}[/bold red]")
        return []

def save_entities_to_db(session_id: str, entities: List[str]):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for entity in entities:
            cursor.execute('''
                INSERT OR IGNORE INTO entities (session_id, name, entity_type) 
                VALUES (?, ?, 'Concept')
            ''', (session_id, entity))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (save_entities): {e}[/bold red]")

def is_url_crawled(url: str) -> bool:
    url_hash = get_url_hash(url)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM crawled_urls WHERE url_hash = ?", (url_hash,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        console.print(f"[bold red]DB Error (is_url_crawled): {e}[/bold red]")
        return False

def save_crawled_url(url: str, session_id: str, local_path: str):
    url_hash = get_url_hash(url)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE crawled_urls ADD COLUMN status TEXT DEFAULT 'pending_analysis'")
            cursor.execute("ALTER TABLE crawled_urls ADD COLUMN local_path TEXT")
        except sqlite3.OperationalError:
            pass # Columns already exist
            
        cursor.execute('''
            INSERT OR REPLACE INTO crawled_urls (url_hash, url, session_id, status, local_path)
            VALUES (?, ?, ?, 'pending_analysis', ?)
        ''', (url_hash, url, session_id, str(local_path)))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (save_crawled_url): {e}[/bold red]")

def get_pending_files(session_id: str) -> List[tuple]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT url_hash, local_path FROM crawled_urls WHERE session_id = ? AND status = 'pending_analysis'", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        console.print(f"[bold red]DB Error (get_pending_files): {e}[/bold red]")
        return []
        
def mark_file_analyzed(url_hash: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE crawled_urls SET status = 'analyzed' WHERE url_hash = ?", (url_hash,))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (mark_file_analyzed): {e}[/bold red]")
