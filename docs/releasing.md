# Windows release security checks

Updating `master` or `uv.lock` does not update an existing executable. The public
v0.3.0 release (2026-08-20) was built from a tag whose lock selects certifi
2026.7.22. Its actual embedded Python, OpenSSL and CA bundle have not been
inspected; that artifact remains unverified and needs a separately authorized
replacement release. Do not rebuild or overwrite the old tag to imply it changed.

Before a maintainer authorizes a new release:

1. Start from a reviewed commit containing the current `pyproject.toml`, `uv.lock`
   and `.python-version`. Review Python, OpenSSL, uv, PyInstaller and dependency
   advisories again; a reproducible lock can still become stale. Update the runtime
   pin and lock deliberately, and record the source SHA and tool versions.
2. Use the Python version in `.python-version` for both CI and the release build.
   The current pin is 3.13.17, an October 21 security release. This is a build
   baseline, not a claim that all Python vulnerabilities are fixed. Source users
   still manage their own supported Python runtime (the package supports 3.11+).
3. In a fresh Windows environment run `uv lock --check`, `uv sync --frozen`,
   `uv run --no-sync pytest -m "not integration"`, Ruff, Mypy and `uv build`.
   `tests/test_build_security.py` checks the installed certifi floor, package
   dependency metadata and loadable CA bundle. This does not assert that every
   emSign-named root is absent or that all CA risks are resolved. The release
   workflow runs these trust checks before PyInstaller and uses `--no-sync` so
   packaging cannot silently resolve a different environment.
4. Build a candidate with the exact PyInstaller command in `release.yml`. Check
   `--help`, offline station lookup and MCP stdio initialization. Inspect the
   resulting archive's embedded Python/OpenSSL and `certifi/cacert.pem`, compare
   the CA bundle to the validated build environment, and test HTTPS against JMA
   from the candidate. A source-environment test or offline smoke test alone
   does not verify the executable's TLS trust.
   `scripts/verify_windows_bundle.py` now gates publication on matching embedded
   Python/OpenSSL/CA bytes and package version metadata, `--version`, help, station
   lookup and MCP stdio checks. The release job also requires live JMA HTTPS via
   the candidate (`--https`), verifies tag/package version agreement, and publishes
   `build-verification.json` beside the EXE/checksum. CI runs the offline checks.
5. Retain the source SHA, runtime/dependency versions, CI results and candidate
   SHA256 for review. Only after explicit release approval create a new version
   tag/release. The `v*` tag push triggers publication and uploads the EXE and
   checksum; ordinary branch pushes and PRs run CI without publishing.

The certifi lower bound also applies to fresh source/wheel installs, which do not
use this repository's lock. Existing source environments must be reinstalled or
synced; existing EXEs must be replaced. Review installer-bundled pip/uv trust and
OS/custom CA stores separately, including `SSL_CERT_FILE` / `SSL_CERT_DIR` or other
trust overrides. Updating application certifi cannot repair those stores.

For the nonbreaking v0.3.1 security release, package metadata and `__version__`
must both read 0.3.1. Download the new EXE from its new release, verify it against
`SHA256SUMS.txt` and `build-verification.json`, and check `--version`. The standalone
EXE has no separate installer or signing step in the established workflow; its
checksum verifies integrity, not publisher identity. Leave v0.3.0 assets unchanged.

References:

- [certifi emSign advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
- [Python October 21 security releases](https://blog.python.org/2026/10/python-3151-3149-31317/)

CPython's tar_filter CVE-2026-114583 fix landed October 22, after those Python
releases; no stable fixed release was established in this review. No direct tar
extraction path was found here. Track the upstream fix separately; no speculative
tar extraction change is included.
