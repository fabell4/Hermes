---
layout: default
title: "Release Process"
---

# Release Process

## Overview

This document outlines the complete release process for Hermes to prevent incomplete or broken releases.

## Release Architecture

```
Hermes-dev (GitHub) → Forgejo CI → Public Hermes (GitHub)
                          ↓
                    Docker Registries (GHCR + Private)
```

## Pre-Release Checklist

### 1. Code Validation (Local)

Run all checks locally before committing:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Format code
ruff format src tests

# Lint code
ruff check src tests

# Type checking
mypy src

# Run tests
pytest --cov=src -v

# Security scan (optional)
bandit -r src
```

**All checks must pass** before proceeding.

### 2. Version Update

Update version in all required files:

- [ ] `CHANGELOG.md` - Add new version entry with changes
- [ ] `frontend/package.json` - Update `"version"` field
- [ ] Verify version format: `X.Y.Z` or `X.Y.Z-beta`

```powershell
# Example for v0.3.7-beta
# Edit CHANGELOG.md to add:
## [0.3.7-beta] - YYYY-MM-DD
### Fixed
- ...

# Edit frontend/package.json:
"version": "0.3.7"

# Commit changes
git add CHANGELOG.md frontend/package.json
git commit -m "Bump to v0.3.7-beta"
```

### 3. Pre-Release Validation (CI)

Trigger the pre-release check workflow:

1. Go to GitHub Actions on Hermes-dev repo
2. Select "Pre-Release Check" workflow
3. Click "Run workflow"
4. Enter version number (e.g., `0.3.7-beta`)
5. Wait for all checks to complete

**Do not proceed if any checks fail.**

### 4. Create and Push Tag

Only after pre-release validation passes:

```powershell
# Create annotated tag
git tag -a v0.3.7-beta -m "Release v0.3.7-beta: Brief description of changes"

# Push commit and tag
git push origin main
git push origin v0.3.7-beta
```

### 5. Monitor Forgejo Pipeline

Watch the Forgejo release workflow:

- [ ] All CI checks pass (ruff, mypy, pytest, bandit, semgrep)
- [ ] SonarQube Quality Gate: PASSED
- [ ] Docker image built successfully
- [ ] Image pushed to GHCR and private registry
- [ ] Internal CI files stripped (.forgejo/, renovate.json, etc.)
- [ ] Force-pushed to public Hermes repo
- [ ] GitHub release created with tag

### 6. Verify Public Release

Check the public Hermes repository:

- [ ] Tag `v0.3.7-beta` exists and points to correct commit
- [ ] GitHub Actions workflow passes on public repo
- [ ] Release created with proper description
- [ ] Docker images available:
  - `ghcr.io/.../hermes:0.3.7-beta`
  - `ghcr.io/.../hermes:latest`
  - `registry.greenflametech.net/hermes:0.3.7-beta`
  - `registry.greenflametech.net/hermes:latest`

## Rollback Procedure

If a release fails or has critical issues:

### Option 1: Create Patch Version (Recommended)

```powershell
# Fix issues locally
# Update version to next patch (e.g., 0.3.7 → 0.3.8)
git add .
git commit -m "Fix: Critical issue in v0.3.7"
# Follow release process from step 2
```

### Option 2: Delete Failed Release

**Only for releases that never completed successfully:**

```powershell
# Delete local tag
git tag -d v0.3.7-beta

# Delete remote tags
git push origin --delete v0.3.7-beta
git push forgejo --delete v0.3.7-beta

# Manually delete GitHub/Forgejo releases via UI
# Manually delete Docker images if pushed
```

**⚠️ Warning**: Public repo may have protection rules preventing tag deletion.

## Common Issues

### Issue: Tag Created Before Final Fixes

**Symptom**: Release workflow uses old commit, tests fail  
**Cause**: Tag created before pushing all commits  
**Solution**:

- Delete tag and recreate at correct commit, OR
- Create new patch version with fixes

### Issue: SonarQube Quality Gate Failed

**Symptom**: Pipeline stops at SonarQube analysis  
**Cause**: Code quality issues, security vulnerabilities, or unused suppressions  
**Solution**:

- Check SonarQube dashboard for specific issues
- Fix locally and re-test
- Do not disable quality gates to force release

### Issue: GitHub Actions Fail on Public Repo

**Symptom**: Public repo CI fails but Forgejo CI passed  
**Cause**: Environment differences, missing configuration files  
**Solution**:

- Ensure `mypy.ini`, `pytest.ini`, etc. are not in `.forgejo/` (would be stripped)
- Keep CI config files at repo root
- Test on fresh checkout to simulate public repo state

### Issue: Version Mismatch

**Symptom**: Pre-release check fails on version consistency  
**Cause**: Forgot to update CHANGELOG.md or frontend/package.json  
**Solution**: Update all version files before tagging

## Best Practices

1. **Never skip local validation** - Run full test suite before committing
2. **Use pre-release workflow** - Always trigger pre-release check before tagging
3. **One commit, one tag** - Don't push multiple commits after creating tag
4. **Meaningful release notes** - Document changes clearly in CHANGELOG.md
5. **Monitor the full pipeline** - Watch Forgejo workflow to completion
6. **Verify public release** - Check public repo and Docker registries
7. **Keep history clean** - Delete tags for failed releases that never completed

## Release Cadence

- **Beta releases**: As needed for testing and validation
- **Stable releases**: After beta testing period with no critical issues
- **Hotfixes**: Immediate for critical bugs in production

## Contact

For questions about the release process, refer to:

- `.forgejo/workflows/release.yml` - Forgejo CI pipeline
- `.github/workflows/` - GitHub Actions configuration
- `docs/RELEASE-SETUP.md` - Infrastructure setup documentation
