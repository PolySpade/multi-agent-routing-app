
import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock
import json

# Setup path and logging
sys.path.append(str(Path(__file__).parent))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestRSS")

from app.agents.flood_agent import FloodAgent

def main():
    # 1. Setup minimal agent
    mock_env = MagicMock()
    mock_mq = MagicMock()
    
    agent = FloodAgent(
        agent_id="test_rss_agent",
        environment=mock_env,
        message_queue=mock_mq,
        use_real_apis=True, # Needs requests
        enable_llm=True
    )
    
    queries = ["Marikina River Flood", "Marikina Red Warning"]
    
    print("\n" + "="*50)
    print(" TESTING GOOGLE NEWS RSS SCRAPER")
    print("="*50)
    
    all_results = []
    
    for query in queries:
        print(f"\n🔍 Querying: '{query}'...")
        try:
            # Call the service method
            # Now returns list of dicts: {'text': ..., 'pub_date': ..., 'link': ...}
            if not agent.advisory_scraper:
                print("   ❌ AdvisoryScraperService not initialized on agent!")
                continue
                
            items = agent.advisory_scraper.scrape_google_news_rss(query)
            
            print(f"   Found {len(items)} articles (Filtered by Date).")
            
            # Limit to first 10 items
            for i, item in enumerate(items[:10]):
                text = item['text']
                pub_date = item['pub_date']
                link = item.get('link', '')
                
                print(f"   --- Article {i+1} ---")
                print(f"   Date: {pub_date}")
                print(f"   Title/Snippet: {text[:150]}...") # Show snippet
                
                # Parse it
                print("   > Parsing with Agent...")
                parsed = agent.parse_text_advisory(text)
                
                result_summary = {
                    "query": query,
                    "date": pub_date,
                    "text_snippet": text[:100],
                    "parsed_result": parsed
                }
                all_results.append(result_summary)
                
                # Show key extracted warnings if found
                if parsed.get('warning_level'):
                    print(f"   🔴 DETECTED WARNING: {parsed.get('warning_level')}")
                if parsed.get('affected_areas'):
                    print(f"   📍 AFFECTED: {parsed.get('affected_areas')}")
                    
        except Exception as e:
            logger.error(f"Test failed for {query}: {e}")

    print("\n" + "="*50)
    print(" FINAL PARSED RESULTS SUMMARY")
    print("="*50)
    print(json.dumps(all_results, indent=2, default=str))

if __name__ == "__main__":
    main()
