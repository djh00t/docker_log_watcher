.PHONY: install format lint test clean

install:
	poetry install

format:
	poetry run black .

lint:
	poetry run flake8 .

test:
	poetry run pytest

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -r {} +
