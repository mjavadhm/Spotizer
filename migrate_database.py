"""Add quality to user_content_unique constraint

This migration updates the UniqueConstraint on user_downloads table
to include the quality field, allowing users to download the same
content in different qualities.

Usage:
    python migrate_database.py
"""

import asyncio
from sqlalchemy import text
from database.session import async_session_maker, engine

async def migrate():
    """Run the database migration"""
    print("Starting database migration...")
    
    async with async_session_maker() as session:
        try:
            # Check if old constraint exists
            print("Checking for existing constraint...")
            check_query = text("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'user_downloads'::regclass 
                AND conname = 'user_content_unique'
            """)
            result = await session.execute(check_query)
            constraint_exists = result.scalar() is not None
            
            if constraint_exists:
                print("Dropping old constraint 'user_content_unique'...")
                drop_query = text("""
                    ALTER TABLE user_downloads 
                    DROP CONSTRAINT user_content_unique
                """)
                await session.execute(drop_query)
                print("✓ Old constraint dropped successfully")
            else:
                print("Old constraint not found, skipping drop")
            
            # Add new constraint with quality field
            print("Adding new constraint with quality field...")
            add_query = text("""
                ALTER TABLE user_downloads 
                ADD CONSTRAINT user_content_unique 
                UNIQUE (user_id, deezer_id, content_type, quality)
            """)
            await session.execute(add_query)
            await session.commit()
            print("✓ New constraint added successfully")
            
            # Verify the new constraint
            print("\nVerifying new constraint...")
            verify_query = text("""
                SELECT pg_get_constraintdef(oid) as definition
                FROM pg_constraint 
                WHERE conrelid = 'user_downloads'::regclass 
                AND conname = 'user_content_unique'
            """)
            result = await session.execute(verify_query)
            definition = result.scalar()
            print(f"✓ Constraint definition: {definition}")
            
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            await session.rollback()
            raise

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration Script")
    print("=" * 50)
    print()
    
    # Confirm before proceeding
    confirm = input("This will modify the database. Continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Migration cancelled.")
        exit(0)
    
    print()
    asyncio.run(migrate())
    print()
    print("=" * 50)
