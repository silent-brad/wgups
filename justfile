# WGUPS Routing Program — C950

# Default recipe: show available commands
default:
    @just --list

# Run the compiled .pyc (builds first if none exists).
# Requires pypy3 to be installed and on PATH.
run *ARGS:
    #!/usr/bin/env bash
    if ! command -v pypy3 >/dev/null 2>&1; then
        echo "pypy3 not found. Install it or run 'nix develop' to enter the dev shell."
        exit 1
    fi
    pyc=$(ls -t src/__pycache__/main.*.pyc 2>/dev/null | head -n1)
    if [ -z "$pyc" ]; then
        echo "No compiled .pyc found. Building now..."
        rm -rf src/__pycache__
        pypy3 -m compileall -f src/
        pyc=$(ls -t src/__pycache__/main.*.pyc 2>/dev/null | head -n1)
    fi
    PYTHONPATH=src pypy3 "$pyc" {{ARGS}}

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

# Compile Python source to bytecode with pypy3.
# The __pycache__ directory is wiped first so old .pyc files from a
# different interpreter cannot be picked up.
build:
    rm -rf src/__pycache__
    pypy3 -m compileall -f src/

# Run unit tests for hash table and distance table
test:
    python3 -m unittest discover -s tests -v

# Run all validation steps (lint, format check, typecheck, test, build)
validate: check typecheck test build
