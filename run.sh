#!/bin/bash
# FinMatcher - Production Run Script
# Sets up environment and runs the application

# Set script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Set PYTHONPATH to include project root
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}"

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "finmatcher-py3.11" ]; then
    source finmatcher-py3.11/bin/activate
fi

# Create necessary directories
mkdir -p logs output reports temp_attachments attachments

# Run the application
echo "Starting FinMatcher..."
echo "Working directory: $(pwd)"
echo "PYTHONPATH: $PYTHONPATH"
echo

python main.py "$@"
