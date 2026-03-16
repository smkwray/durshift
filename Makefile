PYTHON ?= python

.PHONY: install verify-seed qa sample clean

install:
	$(PYTHON) -m pip install -e ".[dev]"

verify-seed:
	$(PYTHON) scripts/verify_repo_readiness.py

qa:
	$(PYTHON) -m pytest -q

sample:
	bash scripts/run_pipeline.sh

clean:
	rm -f data/processed/*.csv
	rm -f outputs/tables/*.csv
	rm -f outputs/figures/*.png
