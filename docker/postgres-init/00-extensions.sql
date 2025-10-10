-- Enable required extensions for QueryBox Core
-- This runs before the main schema creation

-- UUID generation functions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions for checksums
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Vector similarity search (pgvector extension)
CREATE EXTENSION IF NOT EXISTS "vector";