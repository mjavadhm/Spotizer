"""Add yt_id column to tables

Usage:
    python migrate_yt_id.py
"""

import asyncio
from sqlalchemy import text
from database.session import async_session_maker

async def migrate():
    """Run the database migration"""
    print("Starting database migration to add yt_id...")
    
    async with async_session_maker() as session:
        try:
            # Add yt_id to user_downloads
            print("Adding yt_id to user_downloads...")
            await session.execute(text("""
                ALTER TABLE user_downloads 
                ADD COLUMN IF NOT EXISTS yt_id TEXT
            """))
            print("✓ yt_id added to user_downloads")
            
            # Add yt_id to playlist_tracks
            print("Adding yt_id to playlist_tracks...")
            await session.execute(text("""
                ALTER TABLE playlist_tracks 
                ADD COLUMN IF NOT EXISTS yt_id TEXT
            """))
            print("✓ yt_id added to playlist_tracks")
            
            await session.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            await session.rollback()
            raise

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration Script: Add yt_id")
    print("=" * 50)
    print()
    
    confirm = input("This will modify the database. Continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Migration cancelled.")
        exit(0)
    
    print()
    asyncio.run(migrate())
    print()
    print("=" * 50)
