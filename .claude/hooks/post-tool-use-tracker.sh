#!/bin/bash
# Post-Tool-Use Tracker Hook
# Tracks file edits (Edit, Write, MultiEdit operations) for automated testing/checks

TOOL_NAME=$1
FILE_PATH=$2

# Only track Edit, Write, MultiEdit operations
if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "MultiEdit" ]]; then
  exit 0
fi

# Skip if no file path provided
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Find project root by looking for .claude directory
PROJECT_ROOT=$(pwd)
while [ "$PROJECT_ROOT" != "/" ]; do
  if [ -d "$PROJECT_ROOT/.claude" ]; then
    break
  fi
  PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
done

# If .claude not found, exit silently
if [ ! -d "$PROJECT_ROOT/.claude" ]; then
  exit 0
fi

LOG_FILE="$PROJECT_ROOT/.claude/.edit-log.json"

# Initialize log file if doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  echo "[]" > "$LOG_FILE"
fi

# Get timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Append to log using Python
python3 -c "
import json
import sys

log_file = '$LOG_FILE'
record = {
    'tool': '$TOOL_NAME',
    'file': '$FILE_PATH',
    'timestamp': '$TIMESTAMP'
}

try:
    with open(log_file, 'r') as f:
        logs = json.load(f)
except:
    logs = []

logs.append(record)

with open(log_file, 'w') as f:
    json.dump(logs, f, indent=2)
"

exit 0
