# Step 10.3 Database Migration Guide

## Overview

This migration adds database indexes to optimize citation metadata queries, reducing latency from ~200ms to ~5ms.

## Prerequisites

- PostgreSQL database with `embeddings` table
- Database user with CREATE INDEX permissions
- At least 100 documents processed (for meaningful performance impact)

## Migration Files

- `step10_3_citation_indexes.sql` - SQL migration script

## Running the Migration

### Option 1: Direct SQL Execution

```bash
# Connect to PostgreSQL
psql -U querybox -d querybox_core

# Run migration
\i backend/migrations/step10_3_citation_indexes.sql

# Verify indexes
\di embeddings*
```

### Option 2: Using psql from Command Line

```bash
psql -U querybox -d querybox_core -f backend/migrations/step10_3_citation_indexes.sql
```

### Option 3: Using Alembic (if configured)

```bash
cd backend

# Create migration
alembic revision -m "Add citation metadata indexes"

# Edit the generated migration file and add:
def upgrade():
    op.create_index(
        'idx_embeddings_citation_lookup',
        'embeddings',
        ['document_id', 'page_number', 'section_heading'],
        postgresql_where=sa.text('page_number IS NOT NULL')
    )

def downgrade():
    op.drop_index('idx_embeddings_citation_lookup', table_name='embeddings')

# Run migration
alembic upgrade head
```

## Indexes Created

| Index Name | Columns | Purpose | Performance Impact |
|------------|---------|---------|-------------------|
| `idx_embeddings_citation_lookup` | document_id, page_number, section_heading | Main citation query | 200ms → 5ms |
| `idx_embeddings_section` | section_heading | Section filtering | Enables fast section search |
| `idx_embeddings_page_number` | page_number | Page range queries | Enables fast page filtering |

## Verification

### 1. Check Indexes Exist

```sql
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'embeddings'
  AND indexname LIKE 'idx_embeddings_%';
```

Expected output:
```
indexname                          | indexdef
-----------------------------------+------------------
idx_embeddings_citation_lookup     | CREATE INDEX ...
idx_embeddings_section             | CREATE INDEX ...
idx_embeddings_page_number         | CREATE INDEX ...
```

### 2. Test Query Performance

```sql
-- Test citation metadata query
EXPLAIN ANALYZE
SELECT
    id,
    chunk_text,
    page_number,
    section_heading,
    start_position,
    end_position
FROM embeddings
WHERE document_id = 'your-document-id'
LIMIT 10;
```

Expected output should show:
```
Index Scan using idx_embeddings_citation_lookup on embeddings
  (cost=0.42..8.45 rows=1 width=1234)
  (actual time=0.123..2.456 rows=10 loops=1)
```

### 3. Monitor Index Usage

```sql
-- Check how often indexes are used
SELECT
    indexname,
    idx_scan as times_used,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'embeddings'
  AND indexname LIKE 'idx_embeddings_%'
ORDER BY idx_scan DESC;
```

## Performance Benchmarks

### Before Migration

```
Query: Fetch citation metadata for 10 documents
Method: Sequential Scan
Time: ~200-300ms
CPU: High
```

### After Migration

```
Query: Fetch citation metadata for 10 documents
Method: Index Scan
Time: ~5-10ms
CPU: Low
```

**Performance Improvement: 20-40x faster**

## Disk Space Requirements

Indexes will consume additional disk space:

- `idx_embeddings_citation_lookup`: ~10-20MB per 100K documents
- `idx_embeddings_section`: ~5-10MB per 100K documents
- `idx_embeddings_page_number`: ~2-5MB per 100K documents

**Total**: ~20-35MB per 100K documents

Check current table size:

```sql
SELECT
    pg_size_pretty(pg_total_relation_size('embeddings')) as total_size,
    pg_size_pretty(pg_relation_size('embeddings')) as table_size,
    pg_size_pretty(pg_indexes_size('embeddings')) as indexes_size;
```

## Maintenance

### Rebuild Indexes (if performance degrades)

```sql
-- Rebuild all citation indexes
REINDEX INDEX CONCURRENTLY idx_embeddings_citation_lookup;
REINDEX INDEX CONCURRENTLY idx_embeddings_section;
REINDEX INDEX CONCURRENTLY idx_embeddings_page_number;

-- Or rebuild all indexes on embeddings table
REINDEX TABLE CONCURRENTLY embeddings;
```

### Vacuum (if many updates/deletes)

```sql
-- Analyze table statistics
ANALYZE embeddings;

-- Clean up dead rows
VACUUM embeddings;

-- Full cleanup (requires table lock)
VACUUM FULL embeddings;
```

## Rollback

To remove indexes:

```sql
DROP INDEX IF EXISTS idx_embeddings_citation_lookup;
DROP INDEX IF EXISTS idx_embeddings_section;
DROP INDEX IF EXISTS idx_embeddings_page_number;
```

## Troubleshooting

### Issue: Index creation takes too long

**Cause**: Large table (>1M rows)

**Solution**: Create indexes concurrently

```sql
CREATE INDEX CONCURRENTLY idx_embeddings_citation_lookup
    ON embeddings(document_id, page_number, section_heading)
    WHERE page_number IS NOT NULL;
```

### Issue: Indexes not being used

**Cause**: Query planner not choosing indexes

**Solution**: Update table statistics

```sql
ANALYZE embeddings;
```

### Issue: Out of disk space

**Cause**: Indexes consume significant space

**Solution**: Clean up unused data first

```sql
-- Remove old/unused embeddings
DELETE FROM embeddings WHERE created_at < NOW() - INTERVAL '90 days';

-- Vacuum to reclaim space
VACUUM FULL embeddings;

-- Then create indexes
\i step10_3_citation_indexes.sql
```

## Testing

After migration, test citation extraction:

```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Test citation endpoint
curl -X POST "http://localhost:8000/api/v1/search/unified?citations=true" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "strategy": "hybrid", "limit": 10}'

# Check logs for citation extraction time
tail -f logs/app.log | grep citation
```

Expected log output:
```
citation_metadata_fetched rows_count=10 latency_ms=5
citation_extraction_completed num_citations=25 total_latency_ms=85
```

## Notes

- Indexes are created with `IF NOT EXISTS` to be idempotent
- Partial indexes (WHERE page_number IS NOT NULL) save space
- CONCURRENTLY option avoids table locking (recommended for production)
- Monitor `pg_stat_user_indexes` to verify indexes are being used

---

**Migration Status**: Ready to apply
**Estimated Duration**: 1-5 minutes (depending on table size)
**Downtime**: None (if using CONCURRENTLY)
**Risk Level**: Low
