# Celeritas Development Commands

# Default: list available commands
default:
    @just --list

# ─────────────────────────────────────────────────────────────────────────────
# Development Servers
# ─────────────────────────────────────────────────────────────────────────────

# Run backend development server
backend:
    uv run fastapi dev app/main.py

# Run frontend development server
frontend:
    cd frontend && npm run dev

# Run both frontend and backend (requires terminal multiplexer or two terminals)
dev:
    @echo "Run 'just backend' and 'just frontend' in separate terminals"

# ─────────────────────────────────────────────────────────────────────────────
# Backend (Python)
# ─────────────────────────────────────────────────────────────────────────────

# Format Python code with ruff
format:
    uv run ruff format .

# Check Python code with ruff
lint:
    uv run ruff check .

# Fix Python linting issues automatically
lint-fix:
    uv run ruff check . --fix

# Run Python type checking with pyright
typecheck:
    uv run ty check

# Run all Python checks (format check, lint, typecheck)
check: lint typecheck
    uv run ruff format . --check

# Run Python tests
test *args:
    uv run pytest {{args}}

# ─────────────────────────────────────────────────────────────────────────────
# Frontend (TypeScript/React)
# ─────────────────────────────────────────────────────────────────────────────

# Lint frontend code
frontend-lint:
    cd frontend && npm run lint

# Build frontend for production
frontend-build:
    cd frontend && npm run build

# Type check frontend
frontend-typecheck:
    cd frontend && npx tsc --noEmit

# ─────────────────────────────────────────────────────────────────────────────
# All
# ─────────────────────────────────────────────────────────────────────────────

# Run all checks (backend + frontend)
check-all: check frontend-lint frontend-typecheck

# Format and fix all code
fix: format lint-fix

# Install all dependencies
install:
    uv sync
    cd frontend && npm install
