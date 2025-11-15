#!/usr/bin/env python3
"""
Database Reset Script

Completely resets the database by:
1. Dropping all tables
2. Running Alembic migrations from scratch
3. Optionally seeding demo data

Usage:
    python backend/scripts/reset_database.py [--with-demo-data]
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import argparse
import subprocess
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
import structlog

logger = structlog.get_logger()


def drop_all_tables(engine):
    """Drop all tables in the database"""
    print("\n🗑️  Dropping all tables...")

    with engine.connect() as conn:
        # Get all table names
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:
            print("   ✅ No tables to drop")
            return

        print(f"   Found {len(tables)} tables to drop:")
        for table in tables:
            print(f"      - {table}")

        # Drop all tables (CASCADE to handle foreign keys)
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO querybox"))
        conn.commit()

        print("   ✅ All tables dropped successfully")


def drop_alembic_version(engine):
    """Drop the alembic_version table to reset migration state"""
    print("\n🔄 Resetting Alembic migration state...")

    with engine.connect() as conn:
        try:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
            print("   ✅ Alembic version table dropped")
        except Exception as e:
            print(f"   ⚠️  Warning: {e}")


def install_pgvector_extension(engine):
    """Install pgvector extension for vector operations"""
    print("\n📦 Installing pgvector extension...")

    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("   ✅ pgvector extension installed")
        except Exception as e:
            print(f"   ❌ Failed to install pgvector: {e}")
            print("   Make sure pgvector is installed on your PostgreSQL server")
            raise


def run_migrations():
    """Run Alembic migrations from scratch"""
    print("\n📝 Running Alembic migrations...")

    try:
        # Change to backend directory where alembic.ini is located
        backend_dir = Path(__file__).parent.parent

        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            check=True
        )

        print("   ✅ Migrations completed successfully")
        if result.stdout:
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"      {line}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Migration failed!")
        print(f"   Error: {e.stderr}")
        return False


def seed_demo_data():
    """Seed demo data"""
    print("\n🌱 Seeding demo data...")

    try:
        backend_dir = Path(__file__).parent.parent
        seed_script = backend_dir / "scripts" / "seed_demo.py"

        if not seed_script.exists():
            print(f"   ⚠️  Demo seed script not found: {seed_script}")
            return False

        result = subprocess.run(
            ["python", str(seed_script)],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            check=True
        )

        print("   ✅ Demo data seeded successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Seeding failed!")
        print(f"   Error: {e.stderr}")
        return False


def verify_database_state(engine):
    """Verify the database is in a good state"""
    print("\n✅ Verifying database state...")

    with engine.connect() as conn:
        # Get table count
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"   📊 Tables in database: {len(tables)}")
        for table in sorted(tables):
            # Count rows in each table
            try:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                print(f"      - {table}: {count} rows")
            except Exception as e:
                print(f"      - {table}: Error counting rows - {e}")


def clear_redis_cache():
    """Clear Redis cache"""
    print("\n🧹 Clearing Redis cache...")

    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.flushdb()
        print("   ✅ Redis cache cleared")
        return True
    except Exception as e:
        print(f"   ⚠️  Could not clear Redis: {e}")
        return False


def clear_minio_storage():
    """Clear MinIO/S3 storage"""
    print("\n🧹 Clearing MinIO storage...")

    try:
        from minio import Minio
        from minio.error import S3Error

        # Parse endpoint URL
        endpoint = settings.S3_ENDPOINT.replace('http://', '').replace('https://', '')

        client = Minio(
            endpoint,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            secure=False
        )

        bucket_name = settings.S3_BUCKET_NAME

        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            print(f"   ✅ Bucket '{bucket_name}' doesn't exist (nothing to clear)")
            return True

        # List and delete all objects
        objects = client.list_objects(bucket_name, recursive=True)
        objects_list = list(objects)

        if not objects_list:
            print(f"   ✅ Bucket '{bucket_name}' is already empty")
            return True

        print(f"   Found {len(objects_list)} objects to delete")

        for obj in objects_list:
            client.remove_object(bucket_name, obj.object_name)

        print(f"   ✅ Cleared {len(objects_list)} objects from MinIO")
        return True

    except S3Error as e:
        print(f"   ⚠️  MinIO error: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  Could not clear MinIO: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Reset the database completely",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--with-demo-data',
        action='store_true',
        help='Seed demo data after resetting'
    )
    parser.add_argument(
        '--skip-storage',
        action='store_true',
        help='Skip clearing MinIO storage'
    )
    parser.add_argument(
        '--skip-cache',
        action='store_true',
        help='Skip clearing Redis cache'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🔄 DATABASE RESET SCRIPT")
    print("=" * 60)
    print(f"\nDatabase: {settings.DATABASE_URL.split('@')[1]}")
    print(f"This will:")
    print("  1. Drop ALL tables and data")
    print("  2. Reset Alembic migration state")
    print("  3. Install pgvector extension")
    print("  4. Run migrations from scratch")
    if not args.skip_cache:
        print("  5. Clear Redis cache")
    if not args.skip_storage:
        print("  6. Clear MinIO storage")
    if args.with_demo_data:
        print("  7. Seed demo data")

    print("\n⚠️  WARNING: This action is IRREVERSIBLE!")
    print("⚠️  All data will be permanently deleted!")

    if not args.yes:
        confirmation = input("\nType 'yes' to continue: ")
        if confirmation.lower() != 'yes':
            print("\n❌ Reset cancelled")
            return 1

    # Create database engine
    engine = create_engine(settings.DATABASE_URL)

    try:
        # Step 1: Drop all tables
        drop_all_tables(engine)

        # Step 2: Drop alembic version
        drop_alembic_version(engine)

        # Step 3: Install pgvector extension
        install_pgvector_extension(engine)

        # Step 4: Run migrations
        if not run_migrations():
            print("\n❌ Reset failed during migrations")
            return 1

        # Step 5: Clear Redis cache
        if not args.skip_cache:
            clear_redis_cache()

        # Step 6: Clear MinIO storage
        if not args.skip_storage:
            clear_minio_storage()

        # Step 7: Seed demo data (optional)
        if args.with_demo_data:
            if not seed_demo_data():
                print("\n⚠️  Reset completed but demo data seeding failed")

        # Verify final state
        verify_database_state(engine)

        print("\n" + "=" * 60)
        print("✅ DATABASE RESET COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Restart backend services if running")
        if not args.with_demo_data:
            print("  2. Upload documents via the UI or API")
            print("  3. Test end-to-end functionality")
        else:
            print("  2. Demo data is ready to use!")
            print("  3. Test with sample documents")

        return 0

    except Exception as e:
        print(f"\n❌ Reset failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
