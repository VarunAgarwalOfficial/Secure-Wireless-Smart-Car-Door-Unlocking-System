.PHONY: check lint

check:
	python3 -m compileall -q .
	python3 -c "import glob, json; [json.load(open(f)) for f in glob.glob('**/*.ipynb', recursive=True)]"

lint:
	ruff check .
	ruff format --check .
