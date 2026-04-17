import sqlite3
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List
from core.config import console, APP_CONFIG

DB_PATH = "research.db"

def initialize_db():
    """Initializes the database with the complete schema."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Crawled URLs table with all necessary columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawled_urls (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                session_id TEXT,
                depth INTEGER DEFAULT 0,
                content_hash TEXT,
                relevance_score FLOAT,
                status TEXT DEFAULT 'pending_analysis',
                local_path TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        # Entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                name TEXT NOT NULL,
                entity_type TEXT,
                frequency INTEGER DEFAULT 1,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                UNIQUE(session_id, name)
            )
        ''')
        
        # Knowledge chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_url TEXT,
                content TEXT,
                content_type TEXT,
                content_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                UNIQUE(session_id, content_hash)
            )
        ''')
        
        conn.commit()
        conn.close()
        console.print("[dim]Database initialized with complete schema.[/dim]")
    except Exception as e:
        console.print(f"[bold red]DB Error (initialize_db): {e}[/bold red]")

def save_session(session_id: str, topic: str, goal: str):
    """Saves session info to the sessions table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO sessions (session_id, topic, purpose)
            VALUES (?, ?, ?)
        ''', (session_id, topic, goal))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (save_session): {e}[/bold red]")

def get_last_session() -> dict:
    """Retrieves the last active session from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, topic, purpose as goal FROM sessions ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as e:
        console.print(f"[bold red]DB Error (get_last_session): {e}[/bold red]")
        return {}

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

def get_ollama_host() -> str:
    """Returns the Ollama host from config."""
    return APP_CONFIG.get("ollama", {}).get("host", "127.0.0.1")

def get_ollama_port() -> int:
    """Returns the Ollama port from config."""
    return APP_CONFIG.get("ollama", {}).get("port", 11434)

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
    """Saves a specific piece of technical knowledge (code, recipe, snippet) with deduplication."""
    try:
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO knowledge_chunks (session_id, source_url, content, content_type, content_hash)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, url, content, content_type, content_hash))
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

def is_url_crawled(url: str, session_id: str) -> bool:
    url_hash = get_url_hash(url)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM crawled_urls WHERE url_hash = ? AND session_id = ?", (url_hash, session_id))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        console.print(f"[bold red]DB Error (is_url_crawled): {e}[/bold red]")
        return False

def add_seed_url(session_id: str, url: str):
    """Adds an initial URL to the crawl queue with status 'pending_crawl'."""
    url_hash = get_url_hash(url)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if already exists
        cursor.execute("SELECT 1 FROM crawled_urls WHERE url_hash = ?", (url_hash,))
        if cursor.fetchone() is None:
            cursor.execute('''
                INSERT INTO crawled_urls (url_hash, url, session_id, status, depth)
                VALUES (?, ?, ?, 'pending_crawl', 0)
            ''', (url_hash, url, session_id))
            conn.commit()
            console.print(f"[dim]Seed URL added: {url}[/dim]")
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (add_seed_url): {e}[/bold red]")

def get_pending_crawl_urls(session_id: str) -> List[tuple]:
    """Returns a list of (url, depth) for URLs with status 'pending_crawl'."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT url, depth FROM crawled_urls WHERE session_id = ? AND status = 'pending_crawl'", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        console.print(f"[bold red]DB Error (get_pending_crawl_urls): {e}[/bold red]")
        return []

def add_pending_urls(session_id: str, urls: List[str], depth: int):
    """Adds a list of discovered URLs to the queue with status 'pending_crawl'."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for url in urls:
            url_hash = get_url_hash(url)
            cursor.execute("SELECT 1 FROM crawled_urls WHERE url_hash = ?", (url_hash,))
            if cursor.fetchone() is None:
                cursor.execute('''
                    INSERT INTO crawled_urls (url_hash, url, session_id, status, depth)
                    VALUES (?, ?, ?, 'pending_crawl', ?)
                ''', (url_hash, url, session_id, depth))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (add_pending_urls): {e}[/bold red]")

def save_crawled_url(url: str, session_id: str, local_path: str):
    url_hash = get_url_hash(url)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
            
        # Bug 4 fix: Use INSERT OR IGNORE and targeted UPDATE
        cursor.execute('''
            INSERT OR IGNORE INTO crawled_urls (url_hash, url, session_id, status, depth)
            VALUES (?, ?, ?, 'pending_crawl', 0)
        ''', (url_hash, url, session_id))
        
        cursor.execute('''
            UPDATE crawled_urls 
            SET local_path = ?, session_id = ?, status = 'pending_analysis' 
            WHERE url_hash = ? AND local_path IS NULL
        ''', (str(local_path), session_id, url_hash))
            
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
        
def count_crawled_urls_for_domain(session_id: str, domain: str) -> int:
    """Counts how many URLs have been successfully crawled for a specific domain in this session."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # We check URLs that contain the domain name and have a local_path (meaning they were downloaded)
        # A more robust way would be to store the domain explicitly, but this works for now.
        cursor.execute('''
            SELECT COUNT(*) FROM crawled_urls 
            WHERE session_id = ? AND url LIKE ? AND local_path IS NOT NULL
        ''', (session_id, f"%{domain}%"))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        console.print(f"[bold red]DB Error (count_crawled_urls_for_domain): {e}[/bold red]")
        return 0

def mark_file_analyzed(url_hash: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE crawled_urls SET status = 'analyzed' WHERE url_hash = ?", (url_hash,))
        conn.commit()
        conn.close()
    except Exception as e:
        console.print(f"[bold red]DB Error (mark_file_analyzed): {e}[/bold red]")
