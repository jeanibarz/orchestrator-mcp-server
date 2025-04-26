#!/bin/bash
# Script to run tests using uv

# Set default arguments if none provided
if [ $# -eq 0 ]; then
    ARGS="tests/"
else
    ARGS="$@"
fi

# Run pytest with uv
uv run pytest $ARGS

# Exit with the same status code as pytest
exit $?
