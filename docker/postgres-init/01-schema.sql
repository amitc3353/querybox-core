-- QueryBox Core Database Schema
-- Based on PipesHub's MongoDB patterns adapted for PostgreSQL 15
-- Includes pgvector extension for embeddings support

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ========================================
-- ENUMS AND TYPES
-- ========================================

-- Storage provider options (based on PipesHub's storageVendor)
CREATE TYPE storage_provider_enum AS ENUM (
    'local',        -- Local filesystem storage
    's3',           -- Amazon S3 or S3-compatible (MinIO)
    'azure_blob'    -- Azure Blob Storage
);

-- Document processing status (based on PipesHub's IndexingStatus)
CREATE TYPE document_status_enum AS ENUM (
    'pending',      -- Document uploaded, waiting for processing
    'uploading',    -- File upload in progress
    'processing',   -- Extraction and embedding generation in progress
    'completed',    -- Fully processed and ready for search
    'failed'        -- Processing failed
);

-- Processing stage types for detailed tracking
CREATE TYPE processing_stage_enum AS ENUM (
    'upload',           -- File upload stage
    'validation',       -- File validation (MIME type, size, etc.)
    'extraction',       -- Text extraction from document
    'chunking',         -- Document chunking for embeddings
    'embedding',        -- Embedding generation
    'indexing',         -- Vector indexing
    'completion'        -- Final processing completion
);

-- Processing stage status
CREATE TYPE stage_status_enum AS ENUM (
    'not_started',
    'in_progress', 
    'completed',
    'failed',
    'skipped'
);

-- ========================================
-- MAIN DOCUMENTS TABLE
-- ========================================

CREATE TABLE documents (
    -- Primary identifier (UUID for scalability and security)
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Document naming (based on PipesHub's documentName/alternateDocumentName)
    document_name VARCHAR(255) NOT NULL,           -- Display name for the document
    original_name VARCHAR(255) NOT NULL,           -- Original filename as uploaded
    alternate_name VARCHAR(255),                   -- Optional alternate display name
    
    -- File metadata (adapted from PipesHub's extension/mimeType/sizeInBytes)
    mime_type VARCHAR(100) NOT NULL,               -- MIME type (e.g., 'application/pdf')
    file_extension VARCHAR(10) NOT NULL,           -- File extension (e.g., '.pdf', '.docx')
    file_size BIGINT NOT NULL,                     -- File size in bytes
    checksum VARCHAR(64) NOT NULL,                 -- SHA-256 checksum for integrity
    
    -- Storage configuration (based on PipesHub's multi-storage pattern)
    storage_provider storage_provider_enum NOT NULL DEFAULT 'local',
    storage_path TEXT NOT NULL,                    -- Full path to file in storage system
    storage_bucket VARCHAR(100),                   -- S3 bucket name or Azure container
    storage_region VARCHAR(50),                    -- Storage region for S3/Azure
    
    -- Document status and lifecycle (adapted from PipesHub's indexingStatus)
    status document_status_enum NOT NULL DEFAULT 'pending',
    
    -- Versioning (based on PipesHub's version management)
    is_versioned_file BOOLEAN NOT NULL DEFAULT false,
    current_version INTEGER NOT NULL DEFAULT 1,
    mutation_count INTEGER NOT NULL DEFAULT 1,    -- Total number of changes
    
    -- Flexible metadata storage (JSON for extensibility like PipesHub's customMetadata)
    metadata JSONB DEFAULT '{}',                   -- Custom metadata as key-value pairs
    tags TEXT[],                                   -- Document tags for categorization
    
    -- Processing timestamps (based on PipesHub's timestamp pattern)
    last_extraction_at TIMESTAMP WITH TIME ZONE,  -- When text extraction completed
    last_embedding_at TIMESTAMP WITH TIME ZONE,   -- When embeddings were generated
    last_indexed_at TIMESTAMP WITH TIME ZONE,     -- When document was indexed
    
    -- Audit trail (based on PipesHub's createdAt/updatedAt pattern)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Soft delete pattern (based on PipesHub's isDeleted/deletedByUserId)
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by_user_id UUID,                      -- Reference to user who deleted (if applicable)
    
    -- Additional PipesHub-inspired fields
    is_dirty BOOLEAN NOT NULL DEFAULT false,      -- Indicates need for re-processing
    processing_reason TEXT,                       -- Reason for current status (e.g., error message)
    
    -- Constraints
    CONSTRAINT documents_checksum_unique UNIQUE (checksum),
    CONSTRAINT documents_storage_path_unique UNIQUE (storage_provider, storage_path),
    CONSTRAINT documents_deleted_check CHECK (
        (is_deleted = false AND deleted_at IS NULL) OR 
        (is_deleted = true AND deleted_at IS NOT NULL)
    )
);

-- ========================================
-- DOCUMENT VERSIONS TABLE
-- ========================================

CREATE TABLE document_versions (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reference to parent document
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Version information (based on PipesHub's DocumentVersion schema)
    version_number INTEGER NOT NULL,
    user_assigned_label VARCHAR(100),              -- Custom version label (e.g., "v2.0", "draft")
    version_note TEXT,                             -- Optional note about this version
    
    -- File metadata for this version
    file_size BIGINT NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_extension VARCHAR(10) NOT NULL,
    
    -- Storage for this specific version
    storage_provider storage_provider_enum NOT NULL,
    storage_path TEXT NOT NULL,
    storage_bucket VARCHAR(100),
    storage_region VARCHAR(50),
    
    -- Version-specific metadata
    metadata JSONB DEFAULT '{}',
    
    -- Version lifecycle
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_user_id UUID,                      -- User who created this version
    is_latest_version BOOLEAN NOT NULL DEFAULT false,
    
    -- Constraints
    CONSTRAINT document_versions_unique_version UNIQUE (document_id, version_number),
    CONSTRAINT document_versions_checksum_unique UNIQUE (checksum),
    CONSTRAINT document_versions_storage_unique UNIQUE (storage_provider, storage_path)
);

-- ========================================
-- PROCESSING STATUS TABLE
-- ========================================

CREATE TABLE processing_status (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reference to document being processed
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Processing stage information
    stage processing_stage_enum NOT NULL,
    status stage_status_enum NOT NULL DEFAULT 'not_started',
    
    -- Timing information
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,                           -- Processing duration in milliseconds
    
    -- Progress tracking
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    
    -- Results and error handling
    result_data JSONB DEFAULT '{}',                -- Stage-specific results (e.g., extracted text length)
    error_message TEXT,                            -- Error details if status = 'failed'
    error_code VARCHAR(50),                        -- Structured error code for handling
    
    -- Retry tracking
    attempt_number INTEGER NOT NULL DEFAULT 1,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',                   -- Stage-specific metadata
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT processing_status_unique_stage UNIQUE (document_id, stage, attempt_number),
    CONSTRAINT processing_status_duration_check CHECK (
        (completed_at IS NULL AND duration_ms IS NULL) OR
        (completed_at IS NOT NULL AND duration_ms IS NOT NULL)
    )
);

-- ========================================
-- EMBEDDINGS TABLE (for vector search)
-- ========================================

CREATE TABLE embeddings (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reference to source document
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Chunk information
    chunk_index INTEGER NOT NULL,                 -- Order of chunk within document
    chunk_text TEXT NOT NULL,                     -- The actual text content
    chunk_tokens INTEGER,                         -- Token count for this chunk
    
    -- Embedding vector (using pgvector extension)
    embedding vector(1024),                       -- BGE-M3 embedding dimension (1024), OpenAI ada-002 uses 1536

    -- Chunk metadata
    start_position INTEGER,                       -- Character position in original document
    end_position INTEGER,                         -- End character position
    page_number INTEGER,                          -- Page number if applicable

    -- Enhanced metadata (Step 9.1)
    section_heading VARCHAR(500),                 -- Section heading for context
    subsection_heading VARCHAR(500),              -- Subsection heading
    chunk_type VARCHAR(50) DEFAULT 'paragraph',   -- paragraph, list, table, code, heading
    paragraph_index INTEGER,                      -- Paragraph index within section
    semantic_density FLOAT,                       -- Ratio of content words to total words
    contains_table BOOLEAN DEFAULT false,         -- Contains table data
    contains_list BOOLEAN DEFAULT false,          -- Contains list items
    contains_code BOOLEAN DEFAULT false,          -- Contains code blocks
    contains_equation BOOLEAN DEFAULT false,      -- Contains mathematical equations
    contains_figure BOOLEAN DEFAULT false,        -- Contains figure references
    language VARCHAR(10) DEFAULT 'en',            -- Language code
    chunk_metadata JSONB DEFAULT '{}',            -- Additional metadata

    -- Processing metadata
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'BAAI/bge-m3',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT embeddings_unique_chunk UNIQUE (document_id, chunk_index)
);

-- ========================================
-- PERFORMANCE INDEXES
-- ========================================

-- Documents table indexes
CREATE INDEX idx_documents_status ON documents(status) WHERE is_deleted = false;
CREATE INDEX idx_documents_created_at ON documents(created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_documents_updated_at ON documents(updated_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_documents_storage_provider ON documents(storage_provider) WHERE is_deleted = false;
CREATE INDEX idx_documents_mime_type ON documents(mime_type) WHERE is_deleted = false;
CREATE INDEX idx_documents_tags ON documents USING GIN(tags) WHERE is_deleted = false;
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata) WHERE is_deleted = false;
CREATE INDEX idx_documents_checksum ON documents(checksum);
CREATE INDEX idx_documents_is_dirty ON documents(is_dirty) WHERE is_dirty = true;

-- Document versions indexes
CREATE INDEX idx_document_versions_document_id ON document_versions(document_id);
CREATE INDEX idx_document_versions_latest ON document_versions(document_id, is_latest_version) WHERE is_latest_version = true;
CREATE INDEX idx_document_versions_created_at ON document_versions(created_at DESC);

-- Processing status indexes
CREATE INDEX idx_processing_status_document_id ON processing_status(document_id);
CREATE INDEX idx_processing_status_stage_status ON processing_status(stage, status);
CREATE INDEX idx_processing_status_created_at ON processing_status(created_at DESC);
CREATE INDEX idx_processing_status_active ON processing_status(document_id, stage) WHERE status = 'in_progress';

-- Embeddings indexes (for vector similarity search)
CREATE INDEX idx_embeddings_document_id ON embeddings(document_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_embeddings_chunk_index ON embeddings(document_id, chunk_index);

-- ========================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_status_updated_at BEFORE UPDATE ON processing_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_embeddings_updated_at BEFORE UPDATE ON embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to manage document version flags
CREATE OR REPLACE FUNCTION manage_latest_version()
RETURNS TRIGGER AS $$
BEGIN
    -- If this version is marked as latest, unmark all others for this document
    IF NEW.is_latest_version = true THEN
        UPDATE document_versions 
        SET is_latest_version = false 
        WHERE document_id = NEW.document_id AND id != NEW.id;
        
        -- Update parent document's current_version
        UPDATE documents 
        SET current_version = NEW.version_number,
            updated_at = NOW()
        WHERE id = NEW.document_id;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for version management
CREATE TRIGGER manage_document_versions AFTER INSERT OR UPDATE ON document_versions
    FOR EACH ROW EXECUTE FUNCTION manage_latest_version();

-- ========================================
-- VIEWS FOR COMMON QUERIES
-- ========================================

-- View for active documents with latest version info
CREATE VIEW active_documents_with_versions AS
SELECT 
    d.*,
    dv.version_number as latest_version_number,
    dv.user_assigned_label as latest_version_label,
    dv.created_at as latest_version_created_at
FROM documents d
LEFT JOIN document_versions dv ON d.id = dv.document_id AND dv.is_latest_version = true
WHERE d.is_deleted = false;

-- View for document processing summary
CREATE VIEW document_processing_summary AS
SELECT 
    d.id,
    d.document_name,
    d.status as overall_status,
    COUNT(ps.id) as total_stages,
    COUNT(CASE WHEN ps.status = 'completed' THEN 1 END) as completed_stages,
    COUNT(CASE WHEN ps.status = 'failed' THEN 1 END) as failed_stages,
    COUNT(CASE WHEN ps.status = 'in_progress' THEN 1 END) as active_stages,
    MAX(ps.updated_at) as last_processing_update
FROM documents d
LEFT JOIN processing_status ps ON d.id = ps.document_id
WHERE d.is_deleted = false
GROUP BY d.id, d.document_name, d.status;

-- ========================================
-- INITIAL DATA / SEED VALUES
-- ========================================

-- Example: Insert a test document status entry
-- This would typically be done via application code
/*
INSERT INTO documents (
    document_name, 
    original_name, 
    mime_type, 
    file_extension, 
    file_size, 
    checksum, 
    storage_provider, 
    storage_path
) VALUES (
    'Sample Document',
    'sample.pdf',
    'application/pdf',
    '.pdf',
    1024000,
    'abc123def456...',
    'local',
    '/uploads/documents/sample.pdf'
);
*/

-- ========================================
-- COMMENTS AND DOCUMENTATION
-- ========================================

COMMENT ON TABLE documents IS 'Main documents table storing document metadata and status, based on PipesHub MongoDB schema patterns';
COMMENT ON COLUMN documents.id IS 'Primary UUID identifier for the document';
COMMENT ON COLUMN documents.document_name IS 'Display name for the document (equivalent to PipesHub documentName)';
COMMENT ON COLUMN documents.original_name IS 'Original filename as uploaded by user';
COMMENT ON COLUMN documents.storage_provider IS 'Storage backend (local/s3/azure_blob) following PipesHub multi-storage pattern';
COMMENT ON COLUMN documents.storage_path IS 'Full path to file in the storage system';
COMMENT ON COLUMN documents.checksum IS 'SHA-256 checksum for file integrity verification';
COMMENT ON COLUMN documents.status IS 'Processing status following PipesHub IndexingStatus pattern';
COMMENT ON COLUMN documents.metadata IS 'Flexible JSONB field for custom metadata (equivalent to PipesHub customMetadata)';
COMMENT ON COLUMN documents.is_dirty IS 'Flag indicating document needs re-processing (PipesHub pattern)';
COMMENT ON COLUMN documents.is_deleted IS 'Soft delete flag following PipesHub pattern';

COMMENT ON TABLE document_versions IS 'Version history for documents, based on PipesHub DocumentVersion schema';
COMMENT ON COLUMN document_versions.version_number IS 'Numeric version identifier';
COMMENT ON COLUMN document_versions.user_assigned_label IS 'Custom version label (e.g., "v2.0", "draft")';
COMMENT ON COLUMN document_versions.is_latest_version IS 'Flag indicating if this is the current version';

COMMENT ON TABLE processing_status IS 'Detailed processing stage tracking for documents';
COMMENT ON COLUMN processing_status.stage IS 'Specific processing stage (upload, extraction, embedding, etc.)';
COMMENT ON COLUMN processing_status.status IS 'Status of this processing stage';
COMMENT ON COLUMN processing_status.attempt_number IS 'Retry attempt number for failed stages';

COMMENT ON TABLE embeddings IS 'Vector embeddings for document chunks, supporting semantic search';
COMMENT ON COLUMN embeddings.embedding IS 'Vector embedding (1024 dimensions for BGE-M3)';
COMMENT ON COLUMN embeddings.chunk_index IS 'Order of this chunk within the document';
COMMENT ON COLUMN embeddings.chunk_text IS 'The actual text content for this chunk';