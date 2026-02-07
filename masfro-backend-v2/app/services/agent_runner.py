
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentRunner:
    """
    Background service that periodically executes the `step()` method of registered agents.
    
    This ensures that agents process their message queues and perform their internal
    logic (fusion, reasoning, etc.) even when no external API request is active.
    
    This replaces the passive "dormant agent" model with an active execution loop.
    """
    
    def __init__(self, interval_seconds: float = 1.0):
        """
        Initialize the AgentRunner.
        
        Args:
            interval_seconds: Frequency of agent execution (default: 1.0s)
        """
        self.interval_seconds = interval_seconds
        self.agents: List[Any] = []
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self._last_run_time = {}
        
    def register_agent(self, agent: Any) -> None:
        """Register an agent to be run."""
        if agent not in self.agents:
            self.agents.append(agent)
            logger.info(f"Agent {getattr(agent, 'agent_id', 'unknown')} registered with AgentRunner")
            
    def unregister_agent(self, agent: Any) -> None:
        """Unregister an agent."""
        if agent in self.agents:
            self.agents.remove(agent)
            
    async def _run_loop(self):
        """Main execution loop."""
        logger.info(f"AgentRunner started (interval={self.interval_seconds}s)")
        
        while self.is_running:
            start_time = time.time()
            
            # Execute step() for all agents
            for agent in self.agents:
                try:
                    agent_id = getattr(agent, 'agent_id', 'unknown')
                    
                    # Run step (synchronous or async)
                    if hasattr(agent, 'step'):
                        if asyncio.iscoroutinefunction(agent.step):
                            await agent.step()
                        else:
                            # Run synchronous step in thread pool to avoid blocking
                            await asyncio.to_thread(agent.step)
                    else:
                        logger.warning(f"Agent {agent_id} has no step() method")
                        
                except Exception as e:
                    logger.error(f"Error running agent {agent_id}: {e}", exc_info=True)
            
            # Calculate sleep time to maintain interval
            elapsed = time.time() - start_time
            sleep_time = max(0.1, self.interval_seconds - elapsed)
            
            if elapsed > self.interval_seconds:
                logger.warning(f"Agent execution took {elapsed:.2f}s, exceeding interval {self.interval_seconds}s")
            
            await asyncio.sleep(sleep_time)
            
        logger.info("AgentRunner stopped")

    async def start(self):
        """Start the runner background task."""
        if self.is_running:
            return
            
        self.is_running = True
        self.task = asyncio.create_task(self._run_loop())
        
    async def stop(self):
        """Stop the runner."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self.task.cancel()
            self.task = None
            
# Global instance
agent_runner: Optional[AgentRunner] = None

def get_agent_runner() -> Optional[AgentRunner]:
    return agent_runner

def set_agent_runner(runner: AgentRunner):
    global agent_runner
    agent_runner = runner
