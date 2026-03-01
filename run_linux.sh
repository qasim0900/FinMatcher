#!/bin/bash
# FinMatcher - Linux Run Script

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the application
echo "Starting FinMatcher..."
python main.py "$@"
