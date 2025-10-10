# QueryBox Document Storage

## Directory Structure:
- uploads/     : Temporary upload storage
- processing/  : Documents being processed
- completed/   : Successfully processed documents
- failed/      : Failed processing (for debugging)

## File Naming:
{org_id}/{year}/{month}/{document_id}/{filename}

Example: 
a1b2c3d4/2024/11/doc_uuid_here/report.pdf

## Storage Strategy (From CLAUDE.md):

### Hybrid Approach
- **Local for processing**: Temporary staging during document processing
- **Cloud for permanent**: S3/MinIO for scalable storage
- **Cache layer**: Frequently accessed files for performance

### Processing Flow
```
Upload → Local Processing → Cloud Storage → Delete Local
```

### Directory Usage

#### uploads/
- Temporary storage for files during upload
- Files move here first before processing starts
- Cleaned up after successful processing

#### processing/
- Documents currently being processed
- Includes extraction, chunking, embedding stages
- Files remain here until all processing completes

#### completed/
- Backup copies of successfully processed documents
- Used for reprocessing if needed
- Can be cleaned up based on retention policy

#### failed/
- Documents that failed processing
- Kept for debugging and retry attempts
- Include error logs and stack traces

## Implementation Notes

Based on PROJECT.md architecture:
- Each workspace gets its own subdirectory
- Year/month organization prevents filesystem limitations
- Document IDs are UUIDs for uniqueness
- Original filenames preserved for user experience

## Enterprise Considerations

For production deployments:
- This local storage is for processing only
- Permanent storage should use S3/MinIO
- Consider retention policies for cleanup
- Monitor disk usage and set alerts