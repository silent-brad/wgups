# WGUPS Routing Program — C950 Task 2

set shell := ["bash", "-cu"]

# Default recipe: show available commands
default:
    @just --list

# Run the main program with CPython
run:
    python src/main.py

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

# Compile Python source to bytecode with PyPy
build:
    pypy3 -m compileall -f src/

# Run the compiled .pyc directly (bypassing source re-read)
run-compiled:
    #!/usr/bin/env bash
    pyc=$(ls src/__pycache__/main.*.pyc 2>/dev/null | head -n1)
    if [ -z "$pyc" ]; then
        echo "No compiled .pyc found. Run 'just build' first."
        exit 1
    fi
    echo "Running $pyc"
    PYTHONPATH=src pypy3 "$pyc"

# Run all validation steps (lint, format check, typecheck, build)
validate: check typecheck build
