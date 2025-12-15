#!/usr/bin/env python3
"""
MoodMend Database Restore Script
Restores database from a backup file
"""

import shutil
import os
import sys
from pathlib import Path

# Configuration
DB_PATH = os.getenv('DATABASE_PATH', 'src/backend/moodmend.db')
BACKUP_DIR = os.getenv('DATABASE_BACKUP_PATH', 'backups')

def list_backups():
    """List all available backups"""
    if not os.path.exists(BACKUP_DIR):
        print(f"No backups found in {BACKUP_DIR}")
        return []
    
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith('moodmend_') and f.endswith('.db')],
        reverse=True
    )
    
    if not backups:
        print("No backups available")
        return []
    
    print("\nAvailable backups:")
    print("=" * 60)
    for i, backup in enumerate(backups, 1):
        backup_path = os.path.join(BACKUP_DIR, backup)
        size = os.path.getsize(backup_path)
        print(f"{i}. {backup} ({size:,} bytes)")
    
    return backups

def restore_database(backup_file):
    """Restore database from backup"""
    backup_path = os.path.join(BACKUP_DIR, backup_file)
    
    if not os.path.exists(backup_path):
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    try:
        # Create backup of current database before restoring
        if os.path.exists(DB_PATH):
            current_backup = DB_PATH + '.before_restore'
            shutil.copy2(DB_PATH, current_backup)
            print(f"📦 Current database backed up to: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_path, DB_PATH)
        print(f"✅ Database restored successfully from: {backup_file}")
        return True
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

if __name__ == '__main__':
    print("MoodMend Database Restore")
    print("=" * 60)
    
    backups = list_backups()
    
    if not backups:
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # Backup file specified as argument
        backup_file = sys.argv[1]
    else:
        # Interactive selection
        print("\nEnter backup number to restore (or 'q' to quit): ", end='')
        choice = input().strip()
        
        if choice.lower() == 'q':
            print("Cancelled")
            sys.exit(0)
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_file = backups[index]
            else:
                print("Invalid selection")
                sys.exit(1)
        except ValueError:
            print("Invalid input")
            sys.exit(1)
    
    print(f"\n⚠️  WARNING: This will replace the current database!")
    print(f"Restore from: {backup_file}")
    print("Continue? (yes/no): ", end='')
    confirm = input().strip().lower()
    
    if confirm == 'yes':
        restore_database(backup_file)
    else:
        print("Cancelled")
