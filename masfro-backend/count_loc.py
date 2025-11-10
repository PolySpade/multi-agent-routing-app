#!/usr/bin/env python3
"""
Script to count actual lines of code for each agent file.
Counts non-empty, non-comment lines.
"""
import re
from pathlib import Path

def count_loc(file_path: Path) -> dict:
    """Count lines of code in a file."""
    if not file_path.exists():
        return {"total": 0, "code": 0, "comments": 0, "empty": 0, "error": "File not found"}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total = len(lines)
        code = 0
        comments = 0
        empty = 0
        in_multiline_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                empty += 1
                continue
            
            # Check for multiline comments (docstrings)
            if '"""' in stripped or "'''" in stripped:
                # Toggle multiline comment state
                count = stripped.count('"""') + stripped.count("'''")
                if count % 2 == 1:
                    in_multiline_comment = not in_multiline_comment
                comments += 1
                continue
            
            if in_multiline_comment:
                comments += 1
                continue
            
            # Check for single-line comments
            if stripped.startswith('#'):
                comments += 1
                continue
            
            # Check for inline comments (but count the line as code)
            if '#' in stripped:
                code += 1
                continue
            
            # Everything else is code
            code += 1
        
        return {
            "total": total,
            "code": code,
            "comments": comments,
            "empty": empty
        }
    except Exception as e:
        return {"total": 0, "code": 0, "error": str(e)}

# Agent files to check
agents = {
    "FloodAgent": "app/agents/flood_agent.py",
    "ScoutAgent": "app/agents/scout_agent.py",
    "HazardAgent": "app/agents/hazard_agent.py",
    "RoutingAgent": "app/agents/routing_agent.py",
    "EvacuationMgr": "app/agents/evacuation_manager_agent.py"
}

# Expected LOC from slides
expected = {
    "FloodAgent": 960,
    "ScoutAgent": 486,
    "HazardAgent": 594,
    "RoutingAgent": 459,
    "EvacuationMgr": 430
}

print("=== Agent LOC Count Verification ===\n")

base_path = Path(__file__).parent
results = {}

for agent_name, rel_path in agents.items():
    file_path = base_path / rel_path
    stats = count_loc(file_path)
    results[agent_name] = stats
    
    print(f"{agent_name} ({rel_path}):")
    if "error" in stats:
        print(f"  ERROR: {stats['error']}")
    else:
        print(f"  Total lines: {stats['total']}")
        print(f"  Code lines: {stats['code']}")
        print(f"  Comment lines: {stats['comments']}")
        print(f"  Empty lines: {stats['empty']}")
        print(f"  Expected (from slides): {expected.get(agent_name, 'N/A')}")
        
        if agent_name in expected:
            diff = stats['code'] - expected[agent_name]
            pct_diff = (diff / expected[agent_name]) * 100 if expected[agent_name] > 0 else 0
            print(f"  Difference: {diff:+,} ({pct_diff:+.1f}%)")
    print()

print("=== Summary ===")
print(f"{'Agent':<20} {'Actual LOC':<12} {'Expected LOC':<12} {'Difference':<12} {'Status'}")
print("-" * 70)
for agent_name in agents.keys():
    if agent_name in results and "error" not in results[agent_name]:
        actual = results[agent_name]['code']
        exp = expected.get(agent_name, 0)
        diff = actual - exp
        status = "✅ MATCH" if abs(diff) < 10 else "⚠️ DIFFERENT"
        print(f"{agent_name:<20} {actual:<12} {exp:<12} {diff:+<12} {status}")

