"""
SQLite database module for tracking processed JIRA tickets
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging


class TicketTracker:
    """Manages SQLite database for tracking processed JIRA tickets"""
    
    def __init__(self, db_path: str = "ticket_processing.db"):
        """Initialize the ticket tracker with database connection
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create tickets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT NOT NULL,
                    user TEXT NOT NULL DEFAULT 'default',
                    processed_at TIMESTAMP NOT NULL,
                    success BOOLEAN NOT NULL,
                    execution_time_seconds REAL,
                    pr_urls TEXT,
                    error_message TEXT,
                    deepseek_analysis TEXT,
                    claude_analysis_path TEXT,
                    jira_comment_added BOOLEAN DEFAULT FALSE,
                    labels_added TEXT,
                    UNIQUE(ticket_id, processed_at)
                )
            """)
            
            # Create index on ticket_id for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticket_id 
                ON processed_tickets(ticket_id)
            """)
            
            # Create index on user for user-specific queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user 
                ON processed_tickets(user)
            """)
            
            conn.commit()
            self.logger.info(f"Database initialized at {self.db_path}")
    
    def log_ticket_processing(self, 
                             ticket_id: str,
                             user: str,
                             success: bool,
                             execution_time: Optional[float] = None,
                             pr_urls: Optional[List[str]] = None,
                             error_message: Optional[str] = None,
                             deepseek_analysis: Optional[str] = None,
                             claude_analysis_path: Optional[str] = None,
                             jira_comment_added: bool = False,
                             labels_added: Optional[List[str]] = None) -> int:
        """Log a processed ticket to the database
        
        Args:
            ticket_id: JIRA ticket ID
            user: User who processed the ticket (e.g., 'default', 'yassa')
            success: Whether processing was successful
            execution_time: Time taken to process in seconds
            pr_urls: List of PR URLs created
            error_message: Error message if processing failed
            deepseek_analysis: DeepSeek analysis result
            claude_analysis_path: Path to Claude analysis log file
            jira_comment_added: Whether comment was added to JIRA
            labels_added: List of labels added to the ticket
            
        Returns:
            The ID of the inserted record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Convert lists to JSON strings for storage
            pr_urls_json = json.dumps(pr_urls) if pr_urls else None
            labels_json = json.dumps(labels_added) if labels_added else None
            
            cursor.execute("""
                INSERT INTO processed_tickets (
                    ticket_id, user, processed_at, success, 
                    execution_time_seconds, pr_urls, error_message,
                    deepseek_analysis, claude_analysis_path,
                    jira_comment_added, labels_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_id,
                user,
                datetime.now(),
                success,
                execution_time,
                pr_urls_json,
                error_message,
                deepseek_analysis,
                claude_analysis_path,
                jira_comment_added,
                labels_json
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            
            self.logger.info(f"Logged ticket {ticket_id} processing (ID: {record_id}, Success: {success})")
            return record_id
    
    def get_ticket_history(self, ticket_id: str) -> List[Dict[str, Any]]:
        """Get processing history for a specific ticket
        
        Args:
            ticket_id: JIRA ticket ID
            
        Returns:
            List of processing records for the ticket
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM processed_tickets 
                WHERE ticket_id = ? 
                ORDER BY processed_at DESC
            """, (ticket_id,))
            
            rows = cursor.fetchall()
            
            # Convert to list of dicts and parse JSON fields
            results = []
            for row in rows:
                record = dict(row)
                if record['pr_urls']:
                    record['pr_urls'] = json.loads(record['pr_urls'])
                if record['labels_added']:
                    record['labels_added'] = json.loads(record['labels_added'])
                results.append(record)
            
            return results
    
    def get_user_statistics(self, user: str) -> Dict[str, Any]:
        """Get processing statistics for a specific user
        
        Args:
            user: Username (e.g., 'default', 'yassa')
            
        Returns:
            Dictionary with user statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total tickets processed
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_processed,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    AVG(execution_time_seconds) as avg_execution_time,
                    COUNT(DISTINCT ticket_id) as unique_tickets
                FROM processed_tickets
                WHERE user = ?
            """, (user,))
            
            stats = cursor.fetchone()
            
            # Get PR creation stats
            cursor.execute("""
                SELECT COUNT(*) as tickets_with_prs
                FROM processed_tickets
                WHERE user = ? AND pr_urls IS NOT NULL
            """, (user,))
            
            pr_stats = cursor.fetchone()
            
            return {
                'user': user,
                'total_processed': stats[0] or 0,
                'successful': stats[1] or 0,
                'failed': stats[2] or 0,
                'avg_execution_time_seconds': stats[3] or 0,
                'unique_tickets': stats[4] or 0,
                'tickets_with_prs': pr_stats[0] or 0
            }
    
    def get_recent_tickets(self, limit: int = 10, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recently processed tickets
        
        Args:
            limit: Maximum number of records to return
            user: Optional user filter
            
        Returns:
            List of recent ticket processing records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if user:
                cursor.execute("""
                    SELECT * FROM processed_tickets 
                    WHERE user = ?
                    ORDER BY processed_at DESC 
                    LIMIT ?
                """, (user, limit))
            else:
                cursor.execute("""
                    SELECT * FROM processed_tickets 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            
            # Convert to list of dicts and parse JSON fields
            results = []
            for row in rows:
                record = dict(row)
                if record['pr_urls']:
                    record['pr_urls'] = json.loads(record['pr_urls'])
                if record['labels_added']:
                    record['labels_added'] = json.loads(record['labels_added'])
                results.append(record)
            
            return results