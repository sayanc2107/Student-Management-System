"""
T5 ERP SYSTEM - Safe, Repeatable Demo Data CLI

Usage:
    python seed.py              # Seeds fictional demo data idempotently
    python seed.py --seed       # Explicitly seeds fictional demo data
    python seed.py --remove     # Safely removes all demo records (isDemo: True)
    python seed.py --status     # Reports counts of demo vs production records
"""
import sys
import asyncio
import argparse
from app.config import settings
from app.database import db_manager, get_database
from app.seed_data import seed_demo_data, remove_demo_data, get_demo_status

async def main():
    parser = argparse.ArgumentParser(description="T5 ERP SYSTEM - Demo Data Management CLI")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--seed", action="store_true", help="Idempotently seed fictional demo records")
    group.add_argument("--remove", "--clean", dest="remove", action="store_true", help="Safely remove all demo records without touching production data")
    group.add_argument("--status", action="store_true", help="Check status of demo records across collections")

    args = parser.parse_args()

    print("=================================================================")
    print("T5 ERP SYSTEM - DATABASE UTILITY")
    print("=================================================================")
    print(f"Environment: {settings.APP_ENV} | Target Database: {settings.DATABASE_NAME}")

    await db_manager.connect()
    db = get_database()

    try:
        if args.remove:
            print("\n[ACTION] Removing all fictional demo records (isDemo: True)...")
            res = await remove_demo_data(db)
            print("\n[SUCCESS] Cleanup complete:")
            for k, v in res.items():
                print(f"  - {k}: {v}")
            print("\nReal production records and custom accounts remain untouched.")
        elif args.status:
            print("\n[ACTION] Inspecting database records...")
            stats = await get_demo_status(db)
            print("\nCollection Breakdown:")
            print(f"{'Collection':<15} | {'Total':<8} | {'Demo':<8} | {'Production':<10}")
            print("-" * 50)
            for col, count_dict in stats.items():
                print(f"{col:<15} | {count_dict['total']:<8} | {count_dict['demo']:<8} | {count_dict['production']:<10}")
        else:
            # Default action: seed idempotently
            print("\n[ACTION] Seeding fictional demo records (idempotent, safe)...")
            await seed_demo_data(db)
            print("\n[SUCCESS] Fictional demo dataset ready.")
            print("Demo accounts available for testing:")
            print("  - Teacher: teacher@example.com (or username 'teacher') | Password: Teacher@123")
            print("  - Student: student1@example.com (or username 'aarav')   | Password: Student@123")
            print("  - Student: student2@example.com (or username 'diya')    | Password: Student@123")
            print("\nNote: In production (APP_ENV=production), demo data is never seeded automatically.")
            print("To remove demo records at any time, run: python seed.py --remove")
    finally:
        await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
