---
name: deps-audit
description: Dependency Audit & Offline Package — audit project dependencies, lock versions, generate offline wheel packages, verify offline installation, and produce deployment-ready artifacts.
---

# Dependency Audit & Offline Package

## When to Use

Use this skill whenever the task involves:

- adding, removing, or updating dependencies
- auditing requirements.txt or pyproject.toml
- resolving dependency conflicts
- generating uv.lock
- building offline wheel packages
- preparing for deployment to air-gapped environments
- project release dependency review

## Principles

### 1. Declare only direct dependencies

If project code directly imports a package, it MUST be in pyproject.toml dependencies.

### 2. Do not declare transitive dependencies

Packages only needed by third-party libraries should NOT be declared unless imported directly.

### 3. pyproject.toml is the single source of truth

Use >= for minimum version. Never use == in pyproject.toml. Version locking belongs in uv.lock.

### 4. uv.lock is regenerated, never hand-edited

---

## Workflow (10 Steps)

### Step 1: Audit project imports
Scan all Python files. Identify direct imports, optional imports, test-only imports.

### Step 2: Audit requirements.txt
Check for missing, unused, duplicate, conflicting, or invalid packages.

### Step 3: Audit pyproject.toml
Ensure correct names, reasonable ranges, dev deps separated, no == pins.

### Step 4: Generate lock file
uv lock

### Step 5: Export locked requirements
uv export --format requirements-txt --no-dev --no-hashes -o requirements_lock.txt

### Step 6: Detect environment
Determine OS, arch, Python version. Name: offline_{os}_{arch}_py{version}

### Step 7: Generate wheel packages
python3 -m pip wheel -r requirements_lock.txt -w offline_linux_x86_64_py312/wheels

### Step 8: Verify offline installation
python3 -m pip install --no-index --find-links=offline_linux_x86_64_py312/wheels --dry-run -r requirements.txt

### Step 9: Package for delivery
tar czf offline_linux_x86_64_py312.tar.gz offline_linux_x86_64_py312/

### Step 10: Generate audit report
Include added/removed/updated packages, risks, offline package summary.

---

## Version Consistency Chain

pyproject.toml -> uv lock -> uv.lock -> uv export -> requirements_lock.txt -> pip wheel -> *.whl

## Git

Commit: pyproject.toml, requirements.txt, uv.lock, .gitignore
Ignore: requirements_lock.txt, offline_*/

## Release Checklist

[ ] imports audited
[ ] requirements.txt updated
[ ] pyproject.toml updated
[ ] uv.lock regenerated
[ ] wheel packages generated
[ ] offline installation verified
[ ] compressed archive generated
[ ] dependency report completed

## Common Issues

See dependency-management.md for Chinese-language troubleshooting.
