#!/usr/bin/env python3
"""
AlaX Database Setup Script
Run this script once to initialize the database structure.

Usage: python setup_db.py
"""

import sqlite3
import os
import sys
from datetime import datetime

def create_database(db_path='alax.db'):
    """Create the database and all required tables"""
    
    print(f"Setting up database at: {os.path.abspath(db_path)}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')
        
        print("Creating tables...")
        
        # Users table - store basic user info
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                timezone TEXT DEFAULT 'UTC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ Users table created")
        
        # User settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                weather_location TEXT,
                notification_enabled BOOLEAN DEFAULT TRUE,
                daily_summary_time TEXT DEFAULT '08:00',
                language TEXT DEFAULT 'en',
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ User settings table created")
        
        # Reminders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                recurring TEXT DEFAULT NULL,  -- 'daily', 'weekly', 'monthly', etc.
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ Reminders table created")
        
        # Notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT NULL,  -- JSON array of tags
                category TEXT DEFAULT 'general',
                is_pinned BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ Notes table created")
        
        # Habits table for habit tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                target_frequency INTEGER DEFAULT 1,  -- times per day
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ Habits table created")
        
        # Habit logs for tracking completion
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT NULL,
                FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ Habit logs table created")
        
        # Events/Calendar table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                location TEXT,
                reminder_minutes INTEGER DEFAULT 15,
                is_all_day BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ Events table created")
        
        # Bookmarks/Links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                description TEXT,
                tags TEXT,  -- JSON array
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ Bookmarks table created")
        
        # Conversation context for AI memory
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                message_type TEXT DEFAULT 'user',  -- 'user' or 'bot'
                context_data TEXT,  -- JSON for additional context
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        print("✓ Conversation context table created")
        
        # Create indexes for better performance
        print("Creating indexes...")
        
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_reminders_user_time ON reminders(user_id, remind_at)',
            'CREATE INDEX IF NOT EXISTS idx_reminders_pending ON reminders(remind_at, completed)',
            'CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id, created_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_notes_search ON notes(content)',
            'CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id, is_active)',
            'CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON habit_logs(habit_id, completed_at)',
            'CREATE INDEX IF NOT EXISTS idx_events_user_time ON events(user_id, start_time)',
            'CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id, created_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_conversation_user_time ON conversation_context(user_id, timestamp DESC)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("✓ Indexes created")
        
        # Create some sample data if requested
        if '--with-sample-data' in sys.argv:
            print("Adding sample data...")
            add_sample_data(cursor)
        
        # Commit all changes
        conn.commit()
        print(f"\n✅ Database setup completed successfully!")
        print(f"Database file: {os.path.abspath(db_path)}")
        
        # Show table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Created {len(tables)} tables: {', '.join([t[0] for t in tables])}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def add_sample_data(cursor):
    """Add some sample data for testing"""
    sample_user_id = 123456789
    
    # Sample user
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, timezone)
        VALUES (?, ?, ?, ?)
    ''', (sample_user_id, 'testuser', 'Test User', 'America/New_York'))
    
    # Sample settings
    cursor.execute('''
        INSERT OR REPLACE INTO user_settings (user_id, weather_location)
        VALUES (?, ?)
    ''', (sample_user_id, 'New York, NY'))
    
    # Sample reminder
    cursor.execute('''
        INSERT INTO reminders (user_id, message, remind_at)
        VALUES (?, ?, datetime('now', '+1 hour'))
    ''', (sample_user_id, 'Sample reminder - check the weather'))
    
    # Sample note
    cursor.execute('''
        INSERT INTO notes (user_id, content, category)
        VALUES (?, ?, ?)
    ''', (sample_user_id, 'This is a sample note to test the system', 'test'))
    
    print("✓ Sample data added")

def check_database_exists(db_path='alax.db'):
    """Check if database already exists"""
    return os.path.exists(db_path)

def backup_existing_database(db_path='alax.db'):
    """Create a backup of existing database"""
    if check_database_exists(db_path):
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(db_path, backup_path)
        print(f"📦 Existing database backed up to: {backup_path}")

def main():
    """Main setup function"""
    print("🚀 AlaX Database Setup")
    print("=" * 30)
    
    db_path = 'alax.db'
    
    # Check if database exists
    if check_database_exists(db_path):
        response = input(f"\nDatabase '{db_path}' already exists. What would you like to do?\n"
                        "1. Backup existing and create new (b)\n"
                        "2. Skip setup (s)\n"
                        "3. Force recreate - WARNING: Will lose data! (f)\n"
                        "Choice [b/s/f]: ").lower().strip()
        
        if response in ['s', 'skip']:
            print("Skipping database setup.")
            return
        elif response in ['f', 'force']:
            os.remove(db_path)
            print("🗑️  Existing database removed")
        elif response in ['b', 'backup', '']:
            backup_existing_database(db_path)
        else:
            print("Invalid choice. Exiting.")
            return
    
    # Create the database
    create_database(db_path)
    
    print("\n🎉 Setup complete! You can now run your AlaX bot.")
    print("\nNext steps:")
    print("1. Update your bot token in the main script")
    print("2. Get API keys for weather service")
    print("3. Run your main bot script: python alax_bot.py")

if __name__ == '__main__':
    main()