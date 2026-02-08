"""Mock data server for MAS-FRO simulation testing."""

# Module-level configuration set by run.py before uvicorn starts.
# The startup handler in main.py reads this to know which scenario to load.
_initial_scenario: str = "light"
