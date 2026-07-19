# Run the test suite
test:
    uv run pytest -v --cov=src --cov-report=term-missing

# Lint the code
lint:
    uv run ruff check src tests

# Auto-format the code
format:
    uv run ruff format src tests

# Run all quality checks
check: lint test