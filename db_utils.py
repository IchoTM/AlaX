#!/usr/bin/env python3
"""
Database utilities for AlaX bot
Simple functions for common database operations
"""

import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
import logging

DB_PATH = 'alax.db'

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logging.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def ensure_user_exists(user_id, username=None, name=None):
    """Ensure user exists in database, create if not"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            # Update last active time
            cursor.execute(
                'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?',
                (user_id,)
            )
        else:
            # Create new user
            cursor.execute('''
                INSERT INTO users (user_id, username, name)
                VALUES (?, ?, ?)
            ''', (user_id, username, name))
            
            # Create default settings
            cursor.execute('''
                INSERT INTO user_settings (user_id)
                VALUES (?)
            ''', (user_id,))
        
        conn.commit()

def add_reminder(user_id, message, remind_at, recurring=None):
    """Add a new reminder"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reminders (user_id, message, remind_at, recurring)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message, remind_at, recurring))
        conn.commit()
        return cursor.lastrowid

def get_pending_reminders():
    """Get all pending reminders that should be sent"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.username 
            FROM reminders r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.completed = FALSE AND r.remind_at <= datetime('now')
            ORDER BY r.remind_at
        ''')
        return cursor.fetchall()

def mark_reminder_completed(reminder_id):
    """Mark a reminder as completed"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE reminders 
            SET completed = TRUE, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (reminder_id,))
        conn.commit()

def add_note(user_id, content, tags=None, category='general'):
    """Add a new note"""
    tags_json = json.dumps(tags) if tags else None
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notes (user_id, content, tags, category)
            VALUES (?, ?, ?, ?)
        ''', (user_id, content, tags_json, category))
        conn.commit()
        return cursor.lastrowid

def get_user_notes(user_id, limit=10, search_term=None):
    """Get user's notes, optionally filtered by search term"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if search_term:
            cursor.execute('''
                SELECT content, created_at FROM notes
                WHERE user_id = ? AND content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, f'%{search_term}%', limit))
        else:
            cursor.execute('''
                SELECT content, created_at FROM notes
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
        return cursor.fetchall()

def delete_note(user_id, note_id):
    """Delete a user's note"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM notes 
            WHERE id = ? AND user_id = ?
        ''', (note_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def get_user_settings(user_id):
    """Get user settings"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT us.* 
            FROM user_settings us
            JOIN users u ON us.user_id = u.user_id
            WHERE us.user_id = ?
        ''', (user_id,))
        return cursor.fetchone()

def update_user_setting(user_id, setting_name, value):
    """Update a specific user setting"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if setting_name == 'timezone':
            cursor.execute('UPDATE users SET timezone = ? WHERE user_id = ?', (value, user_id))
        else:
            cursor.execute(f'UPDATE user_settings SET {setting_name} = ? WHERE user_id = ?', (value, user_id))
        
        conn.commit()
        return cursor.rowcount > 0

def add_conversation_context(user_id, message_text, message_type='user', context_data=None):
    """Add conversation context for AI memory"""
    context_json = json.dumps(context_data) if context_data else None
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO conversation_context (user_id, message_text, message_type, context_data)
            VALUES (?, ?, ?, ?)
        ''', (user_id, message_text, message_type, context_json))
        conn.commit()
        
        # Keep only last 100 messages per user to avoid bloat
        cursor.execute('''
            DELETE FROM conversation_context 
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM conversation_context 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 100
            )
        ''', (user_id, user_id))
        conn.commit()

def get_conversation_history(user_id, limit=20):
    """Get recent conversation history for context"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT message_text, message_type, timestamp
            FROM conversation_context
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        return list(reversed(cursor.fetchall()))  # Return chronological order

def cleanup_old_data(days_to_keep=30):
    """Clean up old data to prevent database bloat"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Clean up completed reminders older than specified days
        cursor.execute('''
            DELETE FROM reminders 
            WHERE completed = TRUE 
            AND completed_at < datetime('now', '-{} days')
        '''.format(days_to_keep))
        
        # Clean up old conversation context (keep last 100 per user)
        cursor.execute('''
            DELETE FROM conversation_context 
            WHERE timestamp < datetime('now', '-{} days')
        '''.format(days_to_keep))
        
        conn.commit()
        
        logging.info(f"Cleaned up data older than {days_to_keep} days")

def get_database_stats():
    """Get database statistics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        tables = ['users', 'reminders', 'notes', 'habits', 'events', 'bookmarks']
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        
        return stats

# Health check function
def check_database_health():
    """Check if database is accessible and has correct structure"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if main tables exist
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('users', 'reminders', 'notes', 'user_settings')
            ''')
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['users', 'reminders', 'notes', 'user_settings']
            missing_tables = set(required_tables) - set(tables)
            
            if missing_tables:
                return False, f"Missing tables: {missing_tables}"
            
            return True, "Database is healthy"
    
    except Exception as e:
        return False, f"Database error: {e}"