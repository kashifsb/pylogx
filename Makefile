.PHONY: test install example clean

## Install in dev mode
install:
	pip install -e ".[dev]"

## Run all tests
test:
	python -m pytest tests/ -v

## Run the example
example:
	python examples/demo.py

## Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
