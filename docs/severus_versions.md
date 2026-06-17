# Severus Versions

Phase 2F.1 uses a fixture-backed compatibility registry pinned to official Severus tag `1.7`, commit `3dc316d6a3c1711d51782b597699979e329df523`. Unknown or mismatched versions fail by default. A permissive unknown-version policy may allow inventory-only review, but executable command generation still requires a verified contract.

Any future registry expansion must be checked against current official Severus documentation before coding.
