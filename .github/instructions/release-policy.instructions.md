---
description: "Use when committing, pushing, tagging, or deciding whether a change needs a release. Covers release policy, versioning decisions, and when to push directly vs. cut a release tag."
---
# Hermes Release Policy

## Push Directly to `main` (no release required)

These changes should be committed and pushed without a version bump or release tag:

- **Documentation fixes** — typos, formatting, broken links, missing Jekyll front matter, incorrect examples
- **Config/syntax corrections** — YAML, TOML, JSON, workflow files with no behavioral change
- **Comment or whitespace changes** — no logic impact
- **Test-only changes** — adding, fixing, or improving tests without touching `src/`
- **Dependency patch bumps** — automated Renovate PRs for patch-level updates with no API changes
- **CI/CD workflow tweaks** — pipeline config that doesn't affect the application itself

## Cut a Release (version bump + tag required)

These changes require a new version in `CHANGELOG.md`, a semver bump, and a `v*` tag to trigger the GHCR publish workflow:

- **New features** — any user-visible functionality added to `src/`
- **Bug fixes in application code** — behavioral corrections in `src/`
- **Breaking changes** — API, config schema, or CLI changes that affect users
- **Dependency minor/major bumps** — library updates that change behavior or APIs
- **Docker / deployment changes** — `Dockerfile`, `docker-compose.yml` changes that affect how the image runs
- **Security patches** — any fix addressing a vulnerability

## Decision Rule

> **If the change only affects what users *read* or how the project is *built/tested*, push directly.  
> If the change affects what users *run*, cut a release.**

## Versioning

Use [Semantic Versioning](https://semver.org):

- `PATCH` (x.x.**1**) — bug fixes, no new features
- `MINOR` (x.**1**.0) — new features, backward-compatible
- `MAJOR` (**1**.0.0) — breaking changes

## Release Steps (when a release IS needed)

1. Update `CHANGELOG.md` with the new version and date
2. Bump the version in relevant files (e.g. `pyproject.toml`, `package.json`)
3. Commit: `git commit -m "chore: release vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push both: `git push origin main --tags`
   - This triggers the GHCR publish workflow automatically
