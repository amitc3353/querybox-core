# Step 12 - Database Migration Fix

**Date**: 2025-11-05
**Type**: Infrastructure Fix
**Duration**: ~1 hour
**Status**: ✅ Complete

---

## Problem

Running `alembic upgrade head` failed with multiple errors:

1. **Authentication failure**: Password mismatch between `.env`, `alembic.ini`, and `docker-compose.yml`
2. **Backwards migration**: Generated migration was trying to ALTER/DROP tables instead of CREATE
3. **Missing pgvector**: PostgreSQL container didn't have pgvector extension installed

---

## Root Causes

### 1. Credential Mismatch
- **docker-compose.yml**: `querybox:querybox_dev_2024@localhost:5432/querybox_core`
- **.env file**: `querybox:password@localhost:5432/querybox`
- **alembic.ini**: `postgres:postgres@localhost:5432/querybox`

### 2. Backwards Migration
The migration file `20251103_1812_initial_schema.py` had `upgrade()` and `downgrade()` swapped - likely generated from an existing schema instead of empty database.

### 3. Missing Extension
`postgres:15-alpine` image doesn't include pgvector extension, which is required for the `embeddings.embedding` column.

---

## Solutions Implemented

### Fix 1: Standardize Database Credentials

**Updated `backend/.env`** (lines 7, 221):
```bash
# Before
DATABASE_URL=postgresql://querybox:password@localhost:5432/querybox
TEST_DATABASE_URL=postgresql://querybox:password@localhost:5432/querybox_test

# After
DATABASE_URL=postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_core
TEST_DATABASE_URL=postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_test
```

**Note**: `alembic.ini` default is overridden by `DATABASE_URL` env var in `alembic/env.py:98-101`, so no changes needed there.

### Fix 2: Regenerate Migration

**Deleted broken migration**:
```bash
rm backend/alembic/versions/20251103_1812_initial_schema.py
```

**Generated fresh migration**:
```bash
DATABASE_URL=postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_core \
  alembic revision --autogenerate -m "initial_schema"
```

**Fixed imports** in `20251105_1527_initial_schema.py` (lines 8-17):
```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy
import sys
import os

# Add parent directory to path to import custom types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.models import types as app_types
```

**Replaced references**:
```bash
sed -i '' 's/app\.models\.types\./app_types./g' \
  alembic/versions/20251105_1527_initial_schema.py
```

### Fix 3: Install pgvector Extension

**Updated docker-compose.yml** (line 34):
```yaml
# Before
postgres:
  image: postgres:15-alpine

# After
postgres:
  image: pgvector/pgvector:pg15
```

**Recreated container**:
```bash
docker-compose up -d postgres
```

**Enabled extension**:
```bash
PGPASSWORD=querybox_dev_2024 psql -h localhost -U querybox -d querybox_core \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Fix 4: Run Migration

```bash
DATABASE_URL=postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_core \
  alembic upgrade head
```

**Output**:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 6e71b3dac76f, initial_schema
```

---

## Verification

**Confirmed all tables created**:
```sql
\dt
```

**Result**:
```
 public | alembic_version   | table | querybox
 public | document_texts    | table | querybox
 public | document_versions | table | querybox
 public | documents         | table | querybox
 public | embeddings        | table | querybox
 public | processing_queue  | table | querybox
 public | processing_status | table | querybox
```

✅ All 6 application tables + 1 Alembic version table created successfully.

---

## Files Modified

### Configuration Files
- `backend/.env` (lines 7, 221) - Updated database credentials
- `docker-compose.yml` (line 34) - Changed to pgvector image

### Migration Files
- `backend/alembic/versions/20251103_1812_initial_schema.py` - **Deleted** (broken)
- `backend/alembic/versions/20251105_1527_initial_schema.py` - **Created** (correct)

### No Code Changes
- All application code (`app/models/*.py`) remained unchanged
- Migration was purely infrastructure/configuration fix

---

## Key Learnings

### 1. Credential Management
**Best Practice**: Use environment variables consistently
- `alembic/env.py` already reads `DATABASE_URL` from environment
- No need to hardcode in `alembic.ini`
- Always match `docker-compose.yml` credentials in `.env`

### 2. PostgreSQL + pgvector
**Lesson**: Always use `pgvector/pgvector:pg*` images for vector workloads
- `postgres:*-alpine` images don't include pgvector
- Installing pgvector manually in Alpine is complex (clang-19 missing)
- Official pgvector images are production-ready

### 3. Migration Generation
**Warning**: Running `alembic revision --autogenerate` against existing schema creates backwards migrations
- Always start with empty database for initial migration
- Or manually verify `upgrade()` creates tables (not drops them)

---

## Future Considerations

### Environment Variables
Consider using `python-dotenv` to auto-load `.env` in Alembic:

**alembic/env.py** (add before line 96):
```python
from dotenv import load_dotenv
load_dotenv()  # Auto-loads .env file
```

Then simplify commands to just:
```bash
alembic upgrade head  # No DATABASE_URL= prefix needed
```

### Docker Volume Persistence
Current setup preserves data across container restarts via `postgres_data` volume. To reset database completely:
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d
alembic upgrade head
```

---

## Next Steps (Step 12 Remaining Tasks)

- [ ] Create demo data seed script (`backend/scripts/seed_demo.py`)
- [ ] Add health check script (`backend/scripts/health_check.py`)
- [ ] Document one-command deployment workflow
- [ ] Update README with database setup instructions

---

## Quick Reference

### Run Migrations
```bash
# From backend/ directory
export $(cat .env | xargs)  # Load env vars
alembic upgrade head
```

### Check Migration Status
```bash
alembic current
alembic history
```

### Create New Migration
```bash
alembic revision --autogenerate -m "description"
```

### Rollback Migration
```bash
alembic downgrade -1  # Go back one version
alembic downgrade base  # Reset to empty database
```

### Verify Database
```bash
PGPASSWORD=querybox_dev_2024 psql -h localhost -U querybox -d querybox_core
\dt  # List tables
\d+ documents  # Describe table schema
```

---

**Completion**: All database migration infrastructure is now working correctly. Ready to proceed with demo data seeding and one-command deployment setup.
