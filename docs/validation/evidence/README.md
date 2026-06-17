# Validation Evidence

These artifacts document software behavior, packaging checks, and public-release verification. They do not establish biological accuracy, clinical readiness, or production validation. Synthetic scale tests do not mean real samples were processed.

| Evidence category | Purpose | Latest artifact | Scope | Interpretation |
| --- | --- | --- | --- | --- |
| Full hermetic tests | Verify the standard mocked test suite | [TEST_RESULTS.txt](test_summaries/TEST_RESULTS.txt) | Software behavior | Unit, integration, contract, and synthetic tests pass. |
| Clean-exit verification | Confirm pytest exits cleanly | [PYTEST_EXIT_VERIFICATION.txt](test_summaries/PYTEST_EXIT_VERIFICATION.txt) | Test infrastructure | Detects hangs or missing summaries. |
| Full clean-exit verification | Confirm full suite exits cleanly | [PYTEST_FULL_EXIT_VERIFICATION.txt](test_summaries/PYTEST_FULL_EXIT_VERIFICATION.txt) | Test infrastructure | Confirms full-suite clean exit. |
| Pytest resolution | Confirm official pytest is used | [PYTEST_RESOLUTION_CHECK.txt](test_summaries/PYTEST_RESOLUTION_CHECK.txt) | Test infrastructure | Guards against local pytest shadowing. |
| Network isolation | Confirm standard tests avoid network | [NETWORK_ISOLATION_TEST.txt](public_release/NETWORK_ISOLATION_TEST.txt) | Public packaging | Standard tests remain hermetic. |
| Portability | Check active source for prohibited environment assumptions | [PORTABILITY_SCAN.txt](public_release/PORTABILITY_SCAN.txt) | Public packaging | Does not validate deployment portability. |
| Public package audit | Check root, identity, evidence, privacy, links, and forbidden files | [PUBLIC_PACKAGE_AUDIT.txt](public_release/PUBLIC_PACKAGE_AUDIT.txt) | Public packaging | Repository presentation and hygiene check. |
| Documentation-link audit | Check Markdown links | [DOCUMENTATION_LINK_AUDIT.txt](public_release/DOCUMENTATION_LINK_AUDIT.txt) | Documentation | Relative links resolve. |
| Public privacy/IP audit | Check publishable files for sensitive markers | [PUBLIC_RELEASE_AUDIT.txt](public_release/PUBLIC_RELEASE_AUDIT.txt) | Public packaging | Redacted pattern categories only. |
| 3,000-sample planning | Preserve synthetic cohort scale summary | [SCALE_TEST_RESULTS.txt](scale_tests/SCALE_TEST_RESULTS.txt) | Synthetic planning | Not real cohort processing. |
| Joint 3,000-sample planning | Preserve synthetic joint scale summary | [JOINT_SCALE_TEST_RESULTS.txt](scale_tests/JOINT_SCALE_TEST_RESULTS.txt) | Synthetic planning | Not real joint calling. |
| DeepSomatic mocked integration | Evidence in full test summaries | [TEST_RESULTS.txt](test_summaries/TEST_RESULTS.txt) | Mocked execution | No real DeepSomatic execution. |
| Severus official-contract verification | Evidence in contract tests and full summaries | [TEST_RESULTS.txt](test_summaries/TEST_RESULTS.txt) | Contract fixtures | No real Severus execution required. |
| Integrated somatic reporting | Evidence in full and selector summaries | [TEST_RESULTS.txt](test_summaries/TEST_RESULTS.txt) | Mocked/synthetic reporting | Technical reporting only. |
| Repository identity audit | Confirm PacBio public repository identity | [PUBLIC_PACKAGE_AUDIT.txt](public_release/PUBLIC_PACKAGE_AUDIT.txt) | Public packaging | Ensures current owner, slug, URL, and title. |
