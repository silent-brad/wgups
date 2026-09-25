# WGUPS Routing Program — C950 Task 2

# Default recipe: show available commands
default:
    @just --list

# Run the main program directly (uses whichever interpreter was detected)
run:
    python3 src/main.py

# Check code formatting and lint with ruff
check:
    ruff check src/
    ruff format --check src/

# Auto-format all Python files in src/
fmt:
    ruff format src/
    ruff check --fix src/

# Run static type checking with pyright
typecheck:
    pyright src/

# Compile Python source to bytecode with the detected interpreter.
# The __pycache__ directory is wiped first so old .pyc files from a
# different interpreter cannot be picked up by run-compiled.
build:
    rm -rf src/__pycache__
    pypy3 -m compileall -f src/

# Run the compiled .pyc directly (bypassing source re-read).
# Uses `ls -t` to select the most recently created .pyc so that
# even if multiple interpreters have compiled main.py we always
# execute the one produced by the latest `just build`.
run-compiled:
    #!/usr/bin/env bash
    pyc=$(ls -t src/__pycache__/main.*.pyc 2>/dev/null | head -n1)
    if [ -z "$pyc" ]; then
        echo "No compiled .pyc found. Run 'just build' first."
        exit 1
    fi
    PYTHONPATH=src pypy3 "$pyc"

# Run unit tests for hash table and distance table
test:
    python3 -m unittest discover -s tests -v

# Run all validation steps (lint, format check, typecheck, test, build)
validate: check typecheck test build
