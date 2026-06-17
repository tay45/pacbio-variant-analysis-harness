# Contributing

## Development Setup

Use Python 3.10 or newer and install the package locally with `python -m pip install -e .`.

## Coding Style

Prefer small, testable modules, safe subprocess argument lists, explicit configuration, and manifest-driven workflows.

## Tests

Run `python scripts/run_tests.py -q` before submitting changes. Standard tests must be hermetic: no network, no private data, no real patient data, no real caller execution, no containers, and no Slurm requirement.

## Caller Contracts

Caller-facing changes must preserve or update committed contract fixtures and tests where relevant.

## Phase Plans

Major features should include a phase plan under `docs/development_history/phase_plans/`.

## Documentation

Update README, docs, schemas, examples, and validation boundaries when behavior changes.

## Pull Request Checklist

- Tests pass.
- Hermetic suite passes.
- No network in standard tests.
- No patient data, credentials, institution-private data, or private paths.
- No unsupported clinical claims.
- Docs and schemas updated where relevant.
- Caller contracts verified where relevant.
