install:
	poetry install

tests: install
	poetry run pytest --cov=./ --cov-report=xml

export:
	poetry export -f requirements.txt -o requirements.txt --without-hashes

update_index:
	cp README.md docs/index.md
