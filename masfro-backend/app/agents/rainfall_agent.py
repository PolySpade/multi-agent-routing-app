# filename: app/agents/rainfall_agent.py
from .base_agent import BaseAgent

class RainfallAgent(BaseAgent):
    """
    A specific agent that scrapes rainfall data and updates the environment.
    It inherits the common structure from BaseAgent.
    """
    def __init__(self, agent_id: str, environment):
        # Call the parent class's constructor to set up the id and environment.
        super().__init__(agent_id, environment)
        # Add attributes specific to this agent.
        self.api_url = "http://pagasa.dost.gov.ph/..."

    def step(self):
        """
        The specific logic for the rainfall agent's turn.
        """
        print(f"RainfallAgent '{self.agent_id}' is performing its step: scraping data.")
        # --- Your Selenium or data scraping logic would go here ---
        # scraped_data = self.scrape_data()
        # self.environment.update_risks_from_rainfall(scraped_data)