#!/bin/bash
# Post-Tool-Use Tracker Hook
# Tracks file edits (Edit, Write, MultiEdit operations) for automated testing/checks

TOOL_NAME=$1
FILE_PATH=$2
LOG_FILE=".claude/.edit-log.json"

# Only track Edit, Write, MultiEdit operations
if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "MultiEdit" ]]; then
  exit 0
fi

# Skip if no file path provided
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Initialize log file if doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  echo "[]" > "$LOG_FILE"
fi

# Get timestamp
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
else
  # Linux
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
fi

# Create edit record
RECORD=$(cat <<EOF
{
  "tool": "$TOOL_NAME",
  "file": "$FILE_PATH",
  "timestamp": "$TIMESTAMP"
}
EOF
)

# Append to log using Python (more reliable than jq on all systems)
python3 << 'PYTHON_SCRIPT'
import json
import sys

log_file = ".claude/.edit-log.json"
record = {
    "tool": sys.argv[1],
    "file": sys.argv[2],
    "timestamp": sys.argv[3]
}

try:
    with open(log_file, 'r') as f:
        logs = json.load(f)
except:
    logs = []

logs.append(record)

with open(log_file, 'w') as f:
    json.dump(logs, f, indent=2)

PYTHON_SCRIPT "$TOOL_NAME" "$FILE_PATH" "$TIMESTAMP"

exit 0
