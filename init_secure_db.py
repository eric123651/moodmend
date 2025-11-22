import sqlite3
import os

DB_NAME = 'moodmend.db'

def init_secure_db():
    print(f"Initializing secure database: {DB_NAME}")
    
    # Remove existing database if it exists (optional, maybe dangerous for production?)
    # For now, we'll just connect and create if not exists.
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Enable Write-Ahead Logging (WAL) for better concurrency
    cursor.execute('PRAGMA journal_mode=WAL;')
    
    # Enable foreign key constraints
    cursor.execute('PRAGMA foreign_keys=ON;')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            user_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            log_id TEXT PRIMARY KEY,
            user_id TEXT,
            email TEXT,
            time TEXT,
            emotion TEXT,
            task TEXT,
            nft TEXT,
            completed BOOLEAN,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create user_emotions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_emotions (
            user_id TEXT PRIMARY KEY,
            last_emotion TEXT,
            last_update TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Secure database initialized successfully.")

if __name__ == '__main__':
    init_secure_db()
