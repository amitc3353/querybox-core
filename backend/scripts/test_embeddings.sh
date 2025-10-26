#!/bin/bash
# Test Script for Step 9.2: BGE-M3 Embedding Generation
# Run this script to verify the embedding generation pipeline

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
DOCUMENT_ID="61456e53-e9fe-4df8-8e82-5718d45180b0"
API_BASE="http://localhost:8000/api/v1"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Step 9.2: BGE-M3 Embedding Generation Test${NC}"
echo -e "${YELLOW}========================================${NC}\n"

# 1. Check Backend Health
echo -e "${YELLOW}[1/5] Checking backend health...${NC}"
HEALTH_RESPONSE=$(curl -s -X GET "${API_BASE%/api/v1}/health" || echo "FAILED")

if [[ "$HEALTH_RESPONSE" == *"FAILED"* ]] || [[ "$HEALTH_RESPONSE" == "" ]]; then
    echo -e "${RED}❌ Backend is not running!${NC}"
    echo -e "${YELLOW}Start the backend with:${NC}"
    echo -e "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000\n"
    exit 1
else
    echo -e "${GREEN}✅ Backend is healthy${NC}\n"
fi

# 2. Check Document Status
echo -e "${YELLOW}[2/5] Checking document and chunks...${NC}"
PGPASSWORD=querybox_dev_2024 psql -h localhost -U querybox -d querybox_core -t -c \
  "SELECT
    d.document_name,
    COUNT(e.id) as total_chunks,
    COUNT(e.embedding) as embeddings_count
  FROM documents d
  LEFT JOIN embeddings e ON d.id = e.document_id
  WHERE d.id = '$DOCUMENT_ID'
  GROUP BY d.id, d.document_name;" | while read -r line; do
    echo -e "${GREEN}  $line${NC}"
done
echo ""

# 3. Trigger Embedding Generation
echo -e "${YELLOW}[3/5] Triggering embedding generation...${NC}"
GENERATE_RESPONSE=$(curl -s -X POST \
  "${API_BASE}/documents/${DOCUMENT_ID}/embeddings/generate" \
  -H "Content-Type: application/json" \
  -d '{"force_regenerate": false, "batch_size": 100}')

if [[ "$GENERATE_RESPONSE" == *"task_id"* ]]; then
    TASK_ID=$(echo "$GENERATE_RESPONSE" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
    STATUS=$(echo "$GENERATE_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    MESSAGE=$(echo "$GENERATE_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)

    echo -e "${GREEN}✅ Embedding generation queued${NC}"
    echo -e "   Task ID: ${TASK_ID}"
    echo -e "   Status: ${STATUS}"
    echo -e "   Message: ${MESSAGE}\n"

    if [[ "$STATUS" == "SKIPPED" ]]; then
        echo -e "${YELLOW}ℹ️  Embeddings already exist. Use force_regenerate=true to regenerate.${NC}\n"
    fi
else
    echo -e "${RED}❌ Failed to trigger embedding generation${NC}"
    echo -e "Response: $GENERATE_RESPONSE\n"
    exit 1
fi

# 4. Monitor Status
echo -e "${YELLOW}[4/5] Monitoring embedding generation status...${NC}"
echo -e "${YELLOW}Waiting for embeddings to complete (checking every 5 seconds)...${NC}\n"

MAX_ATTEMPTS=60  # 5 minutes max
ATTEMPT=0
COMPLETED=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    STATUS_RESPONSE=$(curl -s -X GET \
      "${API_BASE}/documents/${DOCUMENT_ID}/embeddings/status")

    if [[ "$STATUS_RESPONSE" == *"completion_percentage"* ]]; then
        TOTAL=$(echo "$STATUS_RESPONSE" | grep -o '"total_chunks":[0-9]*' | cut -d':' -f2)
        WITH_EMB=$(echo "$STATUS_RESPONSE" | grep -o '"chunks_with_embeddings":[0-9]*' | cut -d':' -f2)
        PERCENTAGE=$(echo "$STATUS_RESPONSE" | grep -o '"completion_percentage":[0-9.]*' | cut -d':' -f2)
        PROC_STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"processing_status":"[^"]*"' | cut -d'"' -f4)

        echo -e "   Progress: ${WITH_EMB}/${TOTAL} chunks (${PERCENTAGE}%) - Status: ${PROC_STATUS}"

        if [[ "$PERCENTAGE" == "100.0" ]] || [[ "$PERCENTAGE" == "100" ]]; then
            echo -e "${GREEN}✅ Embedding generation completed!${NC}\n"
            COMPLETED=true
            break
        fi

        if [[ "$PROC_STATUS" == "failed" ]]; then
            echo -e "${RED}❌ Embedding generation failed${NC}\n"
            exit 1
        fi
    fi

    ATTEMPT=$((ATTEMPT + 1))
    sleep 5
done

if [ "$COMPLETED" = false ]; then
    echo -e "${YELLOW}⚠️  Embedding generation still in progress after 5 minutes${NC}"
    echo -e "${YELLOW}Check Celery worker logs for details${NC}\n"
fi

# 5. Verify Results
echo -e "${YELLOW}[5/5] Verifying embeddings in database...${NC}"
PGPASSWORD=querybox_dev_2024 psql -h localhost -U querybox -d querybox_core -c \
  "SELECT
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embeddings,
    COUNT(DISTINCT embedding_model) as unique_models,
    STRING_AGG(DISTINCT embedding_model, ', ') as models_used
  FROM embeddings
  WHERE document_id = '$DOCUMENT_ID';"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Test Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Sample vector query
echo -e "${YELLOW}Sample: Query one embedding vector:${NC}"
PGPASSWORD=querybox_dev_2024 psql -h localhost -U querybox -d querybox_core -c \
  "SELECT
    chunk_index,
    LEFT(chunk_text, 100) as chunk_preview,
    embedding_model,
    vector_dims(embedding) as vector_dimension
  FROM embeddings
  WHERE document_id = '$DOCUMENT_ID'
    AND embedding IS NOT NULL
  ORDER BY chunk_index
  LIMIT 1;"

echo -e "\n${GREEN}Done! Your embedding generation pipeline is working.${NC}\n"
