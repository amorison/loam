# check style, typing, and run tests
check-all: lint typecheck test

# check style and format
lint:
    uv run -- ruff check --extend-select I .
    uv run -- ruff format --check .

# format code and sort imports
format:
    uv run -- ruff check --select I --fix .
    uv run -- ruff format .

# check static typing annotations
typecheck:
    uv run -- mypy loam/ tests/

# run test suite
test:
    uv run -- pytest --cov=./loam --cov-report term-missing

# invoke mkdocs with appropriate dependencies
mkdocs *FLAGS:
    uv run --with-requirements=docs/requirements.txt -- mkdocs {{FLAGS}}
