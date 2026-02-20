# Branch Merge Consolidation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge all 9 repository branches into `low_ram_build_environment` with zero breaking changes, using sequential merges with DEM-File winning on application code conflicts.

**Architecture:** Three sequential merges (master → New-Method → DEM-File) into a local `low_ram_build_environment` tracking branch. Branches already contained in low_ram or DEM-File are skipped. A backup tag enables instant rollback.

**Tech Stack:** Git (merge, conflict resolution), Python (backend verification), Node.js/npm (frontend verification), pytest (test verification)

---

### Task 1: Setup — Create Local Tracking Branch and Backup Tag

**Files:**
- No files modified — git operations only

**Step 1: Fetch all remote branches**

```bash
git fetch --all
```

Expected: All remote branches up to date.

**Step 2: Create local tracking branch for low_ram_build_environment**

```bash
git checkout -b low_ram_build_environment origin/low_ram_build_environment
```

Expected: `Switched to a new branch 'low_ram_build_environment'` tracking origin.

**Step 3: Create backup tag for rollback safety**

```bash
git tag backup/pre-merge-low-ram
```

Expected: Tag created silently. Verify with `git tag -l 'backup/*'`.

**Step 4: Verify starting state is clean**

```bash
git status
git log --oneline -3
```

Expected: Clean working tree. Top commit is `051bf13 fix: mark pre-existing broken tests as xfail and fix smoke test`.

---

### Task 2: Merge origin/master (1 commit — .gitignore fix)

**Files:**
- Conflict: `.gitignore` — combine both versions (union of ignore rules)
- Conflict: `.claude/settings.local.json` — keep low_ram version (local config)

**Step 1: Start the merge**

```bash
git merge origin/master --no-ff -m "merge: integrate master branch (.gitignore update)"
```

Expected: CONFLICT in `.gitignore` and `.claude/settings.local.json`.

**Step 2: Resolve .gitignore — combine both versions**

Open `.gitignore`. The conflict will be between master's updated ignore rules and low_ram's version. Combine both sets of ignore rules — take the union. Remove conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).

**Step 3: Resolve .claude/settings.local.json — keep low_ram version**

This is a local config file. Accept low_ram's version:

```bash
git checkout --ours .claude/settings.local.json
```

**Step 4: Complete the merge**

```bash
git add .gitignore .claude/settings.local.json
git commit --no-edit
```

Expected: Merge commit created.

**Step 5: Verify merge succeeded**

```bash
git log --oneline -3
```

Expected: Merge commit at top, then low_ram's previous commits.

---

### Task 3: Merge origin/New-Method (2 commits — cleanup)

**Files:**
- No conflicts expected (clean merge from dry-run analysis)

**Step 1: Execute the merge**

```bash
git merge origin/New-Method --no-ff -m "merge: integrate New-Method branch (cleanup fixes)"
```

Expected: Clean merge, no conflicts.

**Step 2: Verify merge succeeded**

```bash
git log --oneline -5
```

Expected: New merge commit at top.

---

### Task 4: Merge origin/DEM-File (29 commits — major feature merge)

This is the largest merge. ~40 files will conflict. DEM-File wins for application code; low_ram wins for CI/deployment.

**Files with conflicts (from dry-run analysis):**
- `.devcontainer/docker-compose.yml` — combine both
- `.gitignore` — combine both
- `masfro-backend/app/agents/*.py` (6 files) — **DEM-File wins**
- `masfro-backend/app/algorithms/*.py` (2 files) — **DEM-File wins**
- `masfro-backend/app/communication/message_queue.py` — **DEM-File wins**
- `masfro-backend/app/core/agent_config.py` — **DEM-File wins**
- `masfro-backend/app/core/config.py` — **DEM-File wins**
- `masfro-backend/app/core/llm_utils.py` — **DEM-File wins**
- `masfro-backend/app/database/*.py` (2 files) — **DEM-File wins**
- `masfro-backend/app/environment/graph_manager.py` — **DEM-File wins**
- `masfro-backend/app/main.py` — **DEM-File wins**
- `masfro-backend/app/ml_models/location_geocoder.py` — **DEM-File wins**
- `masfro-backend/app/ml_models/locations/location.csv` — **DEM-File wins**
- `masfro-backend/app/data/evacuation_centers.csv` — **DEM-File wins**
- `masfro-backend/app/services/*.py` (3 files) — **DEM-File wins**
- `masfro-backend/app/static/agent_viewer/index.html` — **DEM-File wins**
- `masfro-backend/config/agents.yaml` — **DEM-File wins**
- `masfro-backend/mock_server/*.py` (5 files) — **DEM-File wins**
- `masfro-backend/tests/conftest.py` — **Combine both** (low_ram's fixtures + DEM-File's fixtures)
- `masfro-backend/tests/unit/test_evacuation_nlp.py` — **Combine both**
- `masfro-backend/tests/unit/test_orchestrator.py` — **Combine both**
- `masfro-frontend/src/app/api/places/autocomplete/route.js` — **DEM-File wins**
- `masfro-frontend/src/components/*.js` (4 files) — **DEM-File wins**
- `masfro-backend-old/**` (many files) — **DEM-File wins** (accept all as-is)

**Step 1: Start the merge**

```bash
git merge origin/DEM-File --no-ff -m "merge: integrate DEM-File branch (all features + DEM integration)"
```

Expected: CONFLICT in ~40 files.

**Step 2: Resolve DEM-File-wins conflicts in bulk**

For all backend app code, frontend code, and backend-old files — accept DEM-File's version:

```bash
# Backend application code — DEM-File wins
git checkout --theirs masfro-backend/app/agents/base_agent.py
git checkout --theirs masfro-backend/app/agents/evacuation_manager_agent.py
git checkout --theirs masfro-backend/app/agents/flood_agent.py
git checkout --theirs masfro-backend/app/agents/hazard_agent.py
git checkout --theirs masfro-backend/app/agents/orchestrator_agent.py
git checkout --theirs masfro-backend/app/agents/routing_agent.py
git checkout --theirs masfro-backend/app/agents/scout_agent.py
git checkout --theirs masfro-backend/app/algorithms/path_optimizer.py
git checkout --theirs masfro-backend/app/algorithms/risk_aware_astar.py
git checkout --theirs masfro-backend/app/communication/message_queue.py
git checkout --theirs masfro-backend/app/core/agent_config.py
git checkout --theirs masfro-backend/app/core/config.py
git checkout --theirs masfro-backend/app/core/llm_utils.py
git checkout --theirs masfro-backend/app/database/connection.py
git checkout --theirs masfro-backend/app/database/repository.py
git checkout --theirs masfro-backend/app/environment/graph_manager.py
git checkout --theirs masfro-backend/app/main.py
git checkout --theirs masfro-backend/app/ml_models/location_geocoder.py
git checkout --theirs masfro-backend/app/ml_models/locations/location.csv
git checkout --theirs masfro-backend/app/data/evacuation_centers.csv
git checkout --theirs masfro-backend/app/services/agent_lifecycle_manager.py
git checkout --theirs masfro-backend/app/services/agent_viewer_service.py
git checkout --theirs masfro-backend/app/services/dam_water_scraper_service.py
git checkout --theirs masfro-backend/app/services/llm_service.py
git checkout --theirs masfro-backend/app/static/agent_viewer/index.html
git checkout --theirs masfro-backend/config/agents.yaml

# Mock server — DEM-File wins
git checkout --theirs masfro-backend/mock_server/data_store.py
git checkout --theirs masfro-backend/mock_server/main.py
git checkout --theirs masfro-backend/mock_server/routers/admin_router.py
git checkout --theirs masfro-backend/mock_server/routers/social_router.py
git checkout --theirs masfro-backend/mock_server/scenarios.py

# Frontend — DEM-File wins
git checkout --theirs masfro-frontend/src/app/api/places/autocomplete/route.js
git checkout --theirs masfro-frontend/src/components/AgentDataPanel.js
git checkout --theirs masfro-frontend/src/components/LocationSearch.js
git checkout --theirs masfro-frontend/src/components/MapboxMap.js
git checkout --theirs masfro-frontend/src/components/OrchestratorChat.js
```

**Step 3: Resolve combine-both conflicts manually**

For `.gitignore`, `.devcontainer/docker-compose.yml`, and test files — open each, combine both sides, remove conflict markers.

Files to manually review:
- `.gitignore` — union of both sets of ignore rules
- `.devcontainer/docker-compose.yml` — combine container configs
- `masfro-backend/tests/conftest.py` — keep low_ram's path fixtures AND DEM-File's test fixtures
- `masfro-backend/tests/unit/test_evacuation_nlp.py` — combine test cases from both
- `masfro-backend/tests/unit/test_orchestrator.py` — combine test cases from both

**Step 4: Resolve masfro-backend-old conflicts**

All `masfro-backend-old/**` files — accept DEM-File's version:

```bash
git checkout --theirs -- $(git diff --name-only --diff-filter=U | grep 'masfro-backend-old/')
```

**Step 5: Stage all resolved files and commit**

```bash
git add -A
git commit --no-edit
```

Expected: Merge commit created.

**Step 6: Verify no leftover conflict markers**

```bash
grep -rn '<<<<<<< ' --include='*.py' --include='*.js' --include='*.yml' --include='*.yaml' --include='*.json' --include='*.md' masfro-backend/ masfro-frontend/ .devcontainer/ .github/ || echo "CLEAN — no conflict markers found"
```

Expected: `CLEAN — no conflict markers found`

---

### Task 5: Verify — No Breaking Changes

**Step 1: Check for Python import errors in backend**

```bash
cd masfro-backend
python -c "import app.main" 2>&1 || echo "IMPORT ERROR — needs fixing"
cd ..
```

Expected: No import errors (or expected errors about missing env vars/DB connection — those are runtime, not structural).

**Step 2: Check frontend builds**

```bash
cd masfro-frontend
npm install 2>&1 | tail -5
npm run build 2>&1 | tail -10
cd ..
```

Expected: Build succeeds (or warns about missing env vars for Mapbox token — that's expected).

**Step 3: Run backend tests**

```bash
cd masfro-backend
python -m pytest tests/unit/ -v --timeout=30 2>&1 | tail -20
cd ..
```

Expected: Tests pass (some may be xfail from low_ram's pre-existing markers).

**Step 4: Final diff summary**

```bash
git log --oneline backup/pre-merge-low-ram..HEAD
git diff --stat backup/pre-merge-low-ram..HEAD | tail -5
```

Expected: 3 merge commits. Summary of all files changed.

---

### Task 6: Cleanup and Summary

**Step 1: Verify branch state**

```bash
git branch -v
git log --oneline --graph -10
```

**Step 2: Report merge summary**

List what was merged, what was skipped, any issues found during verification.

**Step 3 (Optional): Remove backup tag when satisfied**

```bash
git tag -d backup/pre-merge-low-ram
```

Only do this after confirming everything is working.

---

## Branches Skipped (Already Contained)

| Branch | Reason |
|--------|--------|
| `routing_agent` | Already in low_ram (ancestor) |
| `Presented` | Already in low_ram (ancestor) |
| `Refactor` | Already in low_ram (ancestor) |
| `Indiv-Agents` | Already in DEM-File (ancestor) |
| `Mock-APIs` | Already in DEM-File (ancestor) |

## Rollback Procedure

If anything goes wrong at any step:

```bash
git merge --abort          # If mid-merge
git reset --hard backup/pre-merge-low-ram  # Nuclear option — back to start
```
