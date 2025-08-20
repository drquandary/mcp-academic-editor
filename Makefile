.PHONY: install test lint format clean docs run

# Installation
install:
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm

install-dev: install
	pip install -e .

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

# Documentation
docs:
	cd docs && make html

# Running
run-cli:
	python cli.py --help

run-ui:
	streamlit run ui/app.py

# Example usage
demo:
	python cli.py process examples/sample_manuscript.md examples/sample_comments.json examples/vision_brief.json -o output/revised.md -i

# Docker
docker-build:
	docker build -t mcp-academic-editor .

docker-run:
	docker run -v $(PWD):/workspace mcp-academic-editor

# Cleaning
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf .coverage htmlcov/

# Development setup
setup-dev: install-dev
	pre-commit install

# Release
release-patch:
	bump2version patch

release-minor:
	bump2version minor

release-major:
	bump2version major