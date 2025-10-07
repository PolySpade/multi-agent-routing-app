# filename: app/agents/base_agent.py

class BaseAgent:
    """
    A base class for all agents in the MAS-FRO simulation.

    Provides common attributes like an ID and a reference to the environment,
    and defines a common interface ('step') for the simulation loop.
    """
    def __init__(self, agent_id: str, environment):
        # All agents must have an ID and access to the environment.
        self.agent_id = agent_id
        self.environment = environment
        print(f"Agent {self.agent_id} created.")

    def step(self):
        """
        Represents a single time-step of action for the agent.
        This method must be implemented by each child agent.
        """
        raise NotImplementedError("Each agent must implement its own step() method.")