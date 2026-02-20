# Branch Merge Design: Consolidate All Branches into low_ram_build_environment

**Date:** 2026-02-20
**Status:** Approved
**Target Branch:** `low_ram_build_environment`

## Context

The repository has 9 branches that need to be consolidated into `low_ram_build_environment`. Analysis revealed branch containment relationships that simplify the merge:

- `low_ram_build_environment` already contains: `routing_agent`, `Presented`, `Refactor`
- `DEM-File` already contains: `Mock-APIs`, `Indiv-Agents`

Only 3 branches have unique commits to merge: `master` (1 commit), `New-Method` (2 commits), `DEM-File` (29 commits).

## Strategy: Sequential Merge — Clean First, Then Big

### Merge Order

1. **`origin/master`** → 1 unique commit (`.gitignore` fix). Conflicts: `.gitignore`, `.claude/settings.local.json` — combine both.
2. **`origin/New-Method`** → 2 unique commits (cleanup). Clean merge expected.
3. **`origin/DEM-File`** → 29 unique commits (covers Mock-APIs + Indiv-Agents). ~40 file conflicts.

### Conflict Resolution Rules

| File Category | Winner | Rationale |
|--------------|--------|-----------|
| `masfro-backend/app/**` | DEM-File | Newest feature code |
| `masfro-frontend/src/**` | DEM-File | Newest UI code |
| `.github/`, CI configs | low_ram | CI pipeline is low_ram's contribution |
| `scripts/`, `config/`, systemd | low_ram | Deployment tooling |
| `tests/` | Combine both | Functional + CI tests |
| `.gitignore`, `.devcontainer/` | Combine both | Union of entries |
| `masfro-backend-old/**` | DEM-File | Legacy code, accept as-is |

### Rollback

```bash
git tag backup/pre-merge-low-ram  # Created before any merge
git reset --hard backup/pre-merge-low-ram  # If anything goes wrong
```

## Preserved Work

- **From low_ram:** CI pipeline, low-RAM configs, lazy imports, systemd/lifecycle scripts, test infrastructure
- **From DEM-File:** All 5 agents, DEM integration, orchestrator chat, mock server, map visualization
- **From master:** Updated .gitignore
- **From New-Method:** Cleanup fixes

## Verification

After all merges:
1. Backend starts without import errors
2. Frontend builds successfully
3. Existing tests pass (unit + integration)
4. No orphaned merge conflict markers in codebase
