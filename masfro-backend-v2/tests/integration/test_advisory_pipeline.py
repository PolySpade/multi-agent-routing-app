
import sys
import logging
import argparse
from pathlib import Path
from unittest.mock import MagicMock

# Setup path and logging
sys.path.append(str(Path(__file__).parents[2]))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestPipeline")

from app.agents.flood_agent import FloodAgent
from app.services.llm_service import get_llm_service

def main():
    parser = argparse.ArgumentParser(description="Test Flood Agent Advisory Processing Pipeline")
    parser.add_argument("--file", type=str, default="sample_advisory.txt", help="Path to text file containing advisory")
    parser.add_argument("--text", type=str, help="Direct text input (overrides file)")
    parser.add_argument("--no-llm", action="store_true", help="Force disable LLM to test rule-based fallback")
    args = parser.parse_args()

    # 1. Load Advisory Text
    if args.text:
        advisory_text = args.text
        source = "Command Line Input"
    else:
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return
        with open(file_path, "r", encoding="utf-8") as f:
            advisory_text = f.read()
        source = str(file_path)

    logger.info(f"Loaded advisory text from {source} ({len(advisory_text)} chars)")
    print("-" * 50)
    print(advisory_text)
    print("-" * 50)

    # 2. Setup Agent (Mocking dependencies)
    mock_env = MagicMock()
    mock_mq = MagicMock()
    
    # Check if LLM is actually available before initializing
    llm_available = False
    if not args.no_llm:
        try:
            llm_service = get_llm_service()
            if llm_service.is_available():
                llm_available = True
                logger.info(f"LLM Service Available: {llm_service.text_model}")
            else:
                logger.warning("LLM Service unavailable (Ollama running?), using rule-based fallback")
        except Exception as e:
            logger.warning(f"Error checking LLM service: {e}")

    agent = FloodAgent(
        agent_id="test_flood_agent",
        environment=mock_env,
        message_queue=mock_mq,
        use_simulated=True,
        use_real_apis=False,
        enable_llm=(not args.no_llm)
    )

    # 3. Run Pipeline
    logger.info("Running parse_text_advisory()...")
    result = agent.parse_text_advisory(advisory_text)

    # 4. Display Results
    print("\n" + "="*20 + " PIPELINE RESULT " + "="*20)
    import json
    print(json.dumps(result, indent=2))
    print("="*57)

    if result.get("parsing_method") in ["qwen3_llm", "configured_llm"]:
        logger.info("✅ Successfully processed using LLM")
    else:
        logger.info("⚠️ Processed using Rule-Based Fallback")

if __name__ == "__main__":
    main()
