import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

DB_PATH = os.environ.get("DB_PATH", "/data/pdf_fanout.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable WAL mode for high concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # 1. Documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        gcs_uri TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'PENDING',
        page_count INTEGER DEFAULT 0,
        institution TEXT,
        doc_date TEXT,
        account_numbers TEXT,
        raw_metadata_uri TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. SQLite FTS5 Virtual Table for full-text search with BM25 ranking
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
        doc_id UNINDEXED,
        filename,
        institution,
        account_numbers,
        searchable_text,
        tokenize = 'porter unicode61'
    );
    """)

    # 3. Ingest Errors table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingest_errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT,
        gcs_uri TEXT NOT NULL,
        error_message TEXT NOT NULL,
        traceback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Analysis Results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT NOT NULL UNIQUE,
        summary TEXT,
        structured_json TEXT NOT NULL,
        report_gcs_uri TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(doc_id) REFERENCES documents(id)
    );
    """)

    # 5. Analysis Errors table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis_errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT NOT NULL,
        error_message TEXT NOT NULL,
        traceback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(doc_id) REFERENCES documents(id)
    );
    """)

    conn.commit()
    conn.close()

def upsert_document_ingest(
    doc_id: str,
    filename: str,
    gcs_uri: str,
    page_count: int,
    institution: Optional[str],
    doc_date: Optional[str],
    account_numbers: Optional[str],
    raw_metadata_uri: str,
    searchable_text: str
):
    conn = get_db_connection()
    cursor = conn.cursor()
    from datetime import timezone
    now = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("""
    INSERT INTO documents (
        id, filename, gcs_uri, status, page_count, institution, doc_date, account_numbers, raw_metadata_uri, updated_at
    ) VALUES (?, ?, ?, 'INGESTED', ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        filename = excluded.filename,
        gcs_uri = excluded.gcs_uri,
        status = 'INGESTED',
        page_count = excluded.page_count,
        institution = excluded.institution,
        doc_date = excluded.doc_date,
        account_numbers = excluded.account_numbers,
        raw_metadata_uri = excluded.raw_metadata_uri,
        updated_at = excluded.updated_at;
    """, (doc_id, filename, gcs_uri, page_count, institution, doc_date, account_numbers, raw_metadata_uri, now))
    
    cursor.execute("DELETE FROM documents_fts WHERE doc_id = ?", (doc_id,))
    cursor.execute("""
    INSERT INTO documents_fts (doc_id, filename, institution, account_numbers, searchable_text)
    VALUES (?, ?, ?, ?, ?);
    """, (doc_id, filename, institution or "", account_numbers or "", searchable_text))
    
    conn.commit()
    conn.close()

def record_ingest_error(doc_id: Optional[str], gcs_uri: str, error_message: str, traceback: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO ingest_errors (doc_id, gcs_uri, error_message, traceback)
    VALUES (?, ?, ?, ?);
    """, (doc_id, gcs_uri, error_message, traceback))
    
    if doc_id:
        cursor.execute("UPDATE documents SET status = 'ERROR', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (doc_id,))
    
    conn.commit()
    conn.close()

def search_documents_bm25(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cleaned_query = " ".join([f'"{token}"' for token in query.replace('"', '').split() if token])
    if not cleaned_query:
        return list_recent_documents(limit=limit)
        
    try:
        cursor.execute("""
        SELECT 
            d.id, d.filename, d.gcs_uri, d.status, d.page_count, d.institution, d.doc_date, d.account_numbers, d.created_at,
            snippet(documents_fts, 4, '<mark>', '</mark>', '...', 20) AS match_snippet,
            bm25(documents_fts) AS rank_score
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.doc_id
        WHERE documents_fts MATCH ?
        ORDER BY rank_score ASC
        LIMIT ?;
        """, (cleaned_query, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.OperationalError:
        cursor.execute("""
        SELECT id, filename, gcs_uri, status, page_count, institution, doc_date, account_numbers, created_at,
               '' AS match_snippet, 0 AS rank_score
        FROM documents
        WHERE filename LIKE ? OR institution LIKE ? OR account_numbers LIKE ?
        ORDER BY created_at DESC
        LIMIT ?;
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def list_recent_documents(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, filename, gcs_uri, status, page_count, institution, doc_date, account_numbers, created_at,
           '' AS match_snippet, 0 AS rank_score
    FROM documents
    ORDER BY created_at DESC
    LIMIT ?;
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        return None
    
    doc_dict = dict(doc)
    
    cursor.execute("SELECT * FROM analysis_results WHERE doc_id = ?", (doc_id,))
    analysis = cursor.fetchone()
    doc_dict["analysis"] = dict(analysis) if analysis else None
    
    cursor.execute("SELECT * FROM ingest_errors WHERE doc_id = ? ORDER BY created_at DESC", (doc_id,))
    doc_dict["ingest_errors"] = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM analysis_errors WHERE doc_id = ? ORDER BY created_at DESC", (doc_id,))
    doc_dict["analysis_errors"] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return doc_dict

def set_document_status(doc_id: str, status: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE documents SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, doc_id))
    conn.commit()
    conn.close()

def record_analysis_result(doc_id: str, summary: str, structured_json: str, report_gcs_uri: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO analysis_results (doc_id, summary, structured_json, report_gcs_uri)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(doc_id) DO UPDATE SET
        summary = excluded.summary,
        structured_json = excluded.structured_json,
        report_gcs_uri = excluded.report_gcs_uri,
        created_at = CURRENT_TIMESTAMP;
    """, (doc_id, summary, structured_json, report_gcs_uri))
    
    cursor.execute("UPDATE documents SET status = 'ANALYZED', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

def record_analysis_error(doc_id: str, error_message: str, traceback: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO analysis_errors (doc_id, error_message, traceback)
    VALUES (?, ?, ?);
    """, (doc_id, error_message, traceback))
    
    cursor.execute("UPDATE documents SET status = 'ERROR', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
