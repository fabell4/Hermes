# Quick Release Checklist

Use this checklist for every release. See [docs/RELEASE-PROCESS.md](../docs/RELEASE-PROCESS.md) for detailed instructions.

## Pre-Release

- [ ] All code changes committed and tested locally
- [ ] Run `ruff format src tests` - no changes needed
- [ ] Run `ruff check src tests` - all checks pass
- [ ] Run `mypy src` - no errors
- [ ] Run `pytest --cov=src -v` - all 297+ tests pass

## Version Update

- [ ] Update `CHANGELOG.md` with new version and changes
- [ ] Update `frontend/package.json` version field
- [ ] Commit: `git commit -m "Bump to vX.Y.Z-beta"`

## Validation

- [ ] Trigger "Pre-Release Check" workflow on GitHub Actions
- [ ] Enter version number (e.g., `0.3.7-beta`)
- [ ] Wait for ✅ All checks passed

## Release

- [ ] Create tag: `git tag -a vX.Y.Z-beta -m "Release vX.Y.Z-beta: ..."`
- [ ] Push: `git push origin main`
- [ ] Push tag: `git push origin vX.Y.Z-beta`

## Monitor

- [ ] Forgejo workflow completes successfully
- [ ] SonarQube Quality Gate: PASSED
- [ ] Docker images pushed to registries
- [ ] Public Hermes repo updated with tag
- [ ] GitHub Actions pass on public repo

## Verify

- [ ] GitHub release created
- [ ] Docker images available: `ghcr.io/.../hermes:X.Y.Z-beta` and `:latest`
- [ ] Docker images available on private registry

---

**⚠️ STOP if any step fails. Do not proceed to next step until issue is resolved.**
