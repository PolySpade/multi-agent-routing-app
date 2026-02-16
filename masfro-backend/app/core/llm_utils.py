# filename: app/core/llm_utils.py

"""
Shared LLM utility functions for MAS-FRO agents.

Extracted from orchestrator_agent.py and evacuation_manager_agent.py
to avoid duplication.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks and truncation.

    Handles common LLM output issues:
    - Markdown code fences (```json ... ```)
    - Preamble text before the JSON object
    - Truncated closing braces
    - Incomplete trailing key-value pairs

    Args:
        text: Raw LLM response text

    Returns:
        Parsed dict or None if no valid JSON found
    """
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    start = text.find("{")
    if start < 0:
        return None

    # Try parsing from the start brace
    candidate = text[start:]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # LLM often truncates the closing brace - try appending them
    open_braces = candidate.count("{") - candidate.count("}")
    if open_braces > 0:
        candidate_fixed = candidate + "}" * open_braces
        try:
            return json.loads(candidate_fixed)
        except json.JSONDecodeError:
            pass

        # Also try trimming trailing incomplete string + closing
        last_quote = candidate.rfind('"')
        if last_quote > 0:
            trimmed = candidate[: last_quote + 1]
            trimmed += "}" * (trimmed.count("{") - trimmed.count("}"))
            try:
                return json.loads(trimmed)
            except json.JSONDecodeError:
                pass

        # Drop the last incomplete key-value pair (trim to last comma)
        last_comma = candidate.rfind(",")
        if last_comma > 0:
            trimmed = candidate[:last_comma].rstrip()
            trimmed += "}" * (trimmed.count("{") - trimmed.count("}"))
            try:
                return json.loads(trimmed)
            except json.JSONDecodeError:
                pass

    logger.debug(f"parse_llm_json failed to parse: {text[:200]}")
    return None
