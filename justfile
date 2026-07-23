# Run the test suite
test:
    uv run pytest -v --cov=src --cov-report=term-missing

# Lint the code
lint:
    uv run ruff check --fix src tests

# Auto-format the code
format:
    uv run ruff format src tests

# Run all quality checks
check: lint test

# run:
#    uv run python -m streamlit run src/app.py
