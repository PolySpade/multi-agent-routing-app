# Agent Team Test Prompt for MAS-FRO Backend

Copy the prompt below into a new Claude Code session to launch a full agent-team test of the backend.

---

## Prompt

```
The MAS-FRO backend server is running at http://127.0.0.1:8000. This is a multi-agent flood routing system for Marikina City built with FastAPI. It has 6 agents (scout, flood, hazard, routing, evacuation_manager, orchestrator) scm-history-item:c%3A%5CUsers%5CClinton%5CDocuments%5CCoding%20Project%5Cthesis%5Cmulti-agent-routing-app?%7B%22repositoryId%22%3A%22scm0%22%2C%22historyItemId%22%3A%229da87dc1cfb72b4baeae37708dbbf04fa9dcac31%22%2C%22historyItemParentId%22%3A%223a2cb086db3b66213dbe1eb8d18492acea133e00%22%2C%22historyItemDisplayId%22%3A%229da87dc%22%7Dthat communicate via FIPA-ACL MessageQueue.

Create an agent team with 4 teammates to comprehensively test this backend. Each teammate should use curl to hit the API and report pass/fail results. The server is already running — do NOT start it.

Write all test results to `tests/backend_test_report.md` at the end, consolidated from all teammates.

---
```
