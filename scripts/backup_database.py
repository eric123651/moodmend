#!/usr/bin/env python3
"""
MoodMend Database Backup Script
Automatically backs up the SQLite database with timestamp
"""

import shutil
import os
from datetime import datetime
from pathlib import Path

# Configuration
DB_PATH = os.getenv('DATABASE_PATH', 'src/backend/moodmend.db')
BACKUP_DIR = os.getenv('DATABASE_BACKUP_PATH', 'backups')
MAX_BACKUPS = 30  # Keep last 30 backups

def backup_database():
    """Create a timestamped backup of the database"""
    # Create backup directory if it doesn't exist
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'moodmend_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # Copy database file
        shutil.copy2(DB_PATH, backup_path)
        file_size = os.path.getsize(backup_path)
        print(f"✅ Backup created successfully: {backup_path}")
        print(f"   Size: {file_size:,} bytes")
        
        # Clean up old backups
        cleanup_old_backups()
        
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def cleanup_old_backups():
    """Remove old backups, keeping only the most recent MAX_BACKUPS"""
    try:
        # Get all backup files
        backup_files = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.startswith('moodmend_') and f.endswith('.db')],
            reverse=True
        )
        
        # Remove old backups
        if len(backup_files) > MAX_BACKUPS:
            for old_backup in backup_files[MAX_BACKUPS:]:
                old_path = os.path.join(BACKUP_DIR, old_backup)
                os.remove(old_path)
                print(f"   Removed old backup: {old_backup}")
                
        print(f"   Total backups: {min(len(backup_files), MAX_BACKUPS)}")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

if __name__ == '__main__':
    print("MoodMend Database Backup")
    print("=" * 50)
    backup_database()
