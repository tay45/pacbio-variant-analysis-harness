.PHONY: help test test-fast test-full verify-exit lint-docs portability-scan package-audit clean

help:
	@echo "Targets: test test-fast test-full verify-exit lint-docs portability-scan package-audit clean"

test:
	python scripts/run_tests.py -q

test-fast:
	python scripts/run_tests.py -q -k "not scale"

test-full:
	python scripts/run_tests.py -q
	python scripts/run_tests.py --durations=30

verify-exit:
	python scripts/verify_pytest_exit.py
	python scripts/verify_pytest_exit.py --full

lint-docs:
	python scripts/audit_public_repository.py --links-only

portability-scan:
	python scripts/audit_public_repository.py --privacy-only

package-audit:
	python scripts/audit_public_repository.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage tmp scratch results
