# Testing Guide for MAS-FRO

Quick reference for testing the multi-agent system components.

---

## 🚀 Quick Start

### Run All Agent Tests
```bash
cd masfro-backend
uv run pytest app/agents/ -v
```

### Run HazardAgent Tests Only
```bash
uv run pytest app/agents/test_hazard_agent.py -v
```

### Run Specific Test
```bash
uv run pytest app/agents/test_hazard_agent.py::TestDataFusion::test_fusion_with_both_sources -v
```

---

## 📊 Current Test Coverage

| Agent | Test File | Status | Tests |
|-------|-----------|--------|-------|
| **HazardAgent** | `test_hazard_agent.py` | ✅ PASS | 27/27 |
| FloodAgent | TBD | ⏳ Pending | - |
| RoutingAgent | TBD | ⏳ Pending | - |
| ScoutAgent | TBD | ⏳ Pending | - |
| EvacuationManager | TBD | ⏳ Pending | - |

---

## 🎯 Testing Best Practices

### 1. Test File Location
Place test files next to the code they test:
```
app/agents/
├── hazard_agent.py
├── test_hazard_agent.py  ← Test file
├── flood_agent.py
└── test_flood_agent.py   ← Future test
```

### 2. Test File Naming
- Use prefix `test_` for test files
- Match the module name: `hazard_agent.py` → `test_hazard_agent.py`

### 3. Test Organization
```python
class TestFeatureName:
    """Group related tests together."""

    def test_happy_path(self):
        """Test normal operation."""
        pass

    def test_edge_case(self):
        """Test edge case."""
        pass

    def test_error_handling(self):
        """Test error handling."""
        pass
```

---

## 🔍 Common Test Commands

### Verbose Output
```bash
uv run pytest -v
```

### Show Print Statements
```bash
uv run pytest -s
```

### Stop at First Failure
```bash
uv run pytest -x
```

### Run Only Failed Tests
```bash
uv run pytest --lf
```

---

**Last Updated:** November 5, 2025
**Maintained By:** MAS-FRO Development Team
