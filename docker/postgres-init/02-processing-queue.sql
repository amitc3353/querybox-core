-- Additional tables for processing queue management
-- Complements the main schema with queue functionality from the provided schema

-- Processing queue table (adapted from provided schema)
CREATE TABLE IF NOT EXISTS processing_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Queue management
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10), -- 1=highest, 10=lowest
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    
    -- Worker tracking
    processor_id VARCHAR(255),  -- Celery worker ID
    locked_at TIMESTAMP WITH TIME ZONE, -- When worker claimed the task
    
    -- Retry management
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    
    -- Timing
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB DEFAULT '{}',
    error_code VARCHAR(50),
    
    -- Metadata
    task_params JSONB DEFAULT '{}', -- Task-specific parameters
    result_data JSONB DEFAULT '{}',  -- Task results
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for queue performance
CREATE INDEX idx_queue_pending ON processing_queue(priority DESC, scheduled_at ASC) 
    WHERE status = 'pending' AND (next_retry_at IS NULL OR next_retry_at <= NOW());
CREATE INDEX idx_queue_processing ON processing_queue(processor_id, locked_at) 
    WHERE status = 'processing';
CREATE INDEX idx_queue_document ON processing_queue(document_id);
CREATE INDEX idx_queue_status ON processing_queue(status, created_at DESC);

-- Trigger for queue updates
CREATE TRIGGER update_queue_updated_at BEFORE UPDATE ON processing_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to claim a queue item (for Celery workers)
CREATE OR REPLACE FUNCTION claim_queue_item(worker_id VARCHAR(255))
RETURNS UUID AS $$
DECLARE
    queue_item_id UUID;
BEGIN
    SELECT id INTO queue_item_id
    FROM processing_queue
    WHERE status = 'pending' 
        AND (next_retry_at IS NULL OR next_retry_at <= NOW())
    ORDER BY priority ASC, scheduled_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;
    
    IF queue_item_id IS NOT NULL THEN
        UPDATE processing_queue
        SET status = 'processing',
            processor_id = worker_id,
            locked_at = NOW(),
            started_at = NOW(),
            attempts = attempts + 1
        WHERE id = queue_item_id;
    END IF;
    
    RETURN queue_item_id;
END;
$$ LANGUAGE plpgsql;

-- View for queue monitoring
CREATE VIEW queue_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_age_seconds,
    MIN(created_at) as oldest_item
FROM processing_queue
GROUP BY status;

COMMENT ON TABLE processing_queue IS 'Queue for document processing tasks, integrated with Celery';
COMMENT ON FUNCTION claim_queue_item IS 'Atomic function for Celery workers to claim queue items';