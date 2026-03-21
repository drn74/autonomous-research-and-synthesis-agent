import sqlite3
import hashlib
from typing import List
from core.config import console

DB_PATH = "research.db"

def get_wsl_host_ip() -> str:
    """Returns localhost since we verified Ollama listens there."""
    return "127.0.0.1"

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
