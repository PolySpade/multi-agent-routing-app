# filename: app/agents/base_agent.py

"""
Base agent class for MAS-FRO multi-agent system.

Provides common functionality and interface for all agents including
MessageQueue registration and message processing utilities.
"""

from typing import Optional, Dict, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from ..communication.message_queue import MessageQueue


class BaseAgent:
    """
    A base class for all agents in the MAS-FRO simulation.

    Provides common attributes like an ID and a reference to the environment,
    MessageQueue registration, a reusable message drain loop, and defines
    a common interface ('step') for the simulation loop.
    """

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        message_queue: Optional["MessageQueue"] = None,
    ) -> None:
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent
            environment: Reference to the DynamicGraphEnvironment instance
            message_queue: Optional MessageQueue for MAS communication
        """
        from ..core.logging_config import get_logger

        self.agent_id = agent_id
        self.environment = environment
        self.message_queue = message_queue
        self.logger = get_logger(f"app.agents.{agent_id}")

        # Register with message queue if provided
        if self.message_queue:
            try:
                self.message_queue.register_agent(self.agent_id)
                self.logger.info(f"{self.agent_id} registered with MessageQueue")
            except ValueError:
                self.logger.debug(f"{self.agent_id} already registered with MQ")

        self.logger.info(f"Agent {self.agent_id} created")

    def _drain_mq_requests(
        self,
        handlers: Dict[str, Callable],
    ) -> None:
        """
        Drain all pending REQUEST messages from the MQ and dispatch to handlers.

        Polls the message queue in a non-blocking loop, dispatching each
        REQUEST message to the matching handler based on its ``action`` field.
        Non-REQUEST performatives are logged and skipped.

        Args:
            handlers: Mapping of action name -> callable(msg, data).
                      Each handler receives the full ACLMessage and the
                      ``content["data"]`` dict.
        """
        if not self.message_queue:
            return

        from ..communication.acl_protocol import Performative

        while True:
            msg = self.message_queue.receive_message(
                agent_id=self.agent_id, timeout=0.0, block=False
            )
            if msg is None:
                break

            if msg.performative == Performative.REQUEST:
                action = msg.content.get("action")
                data = msg.content.get("data", {})
                handler = handlers.get(action)
                if handler:
                    handler(msg, data)
                else:
                    self.logger.warning(
                        f"{self.agent_id}: unknown REQUEST action '{action}' "
                        f"from {msg.sender}"
                    )
            else:
                self.logger.debug(
                    f"{self.agent_id}: ignoring {msg.performative} from {msg.sender}"
                )

    def shutdown(self) -> None:
        """
        Gracefully shut down the agent.

        Subclasses should override to flush caches or close connections.
        """
        self.logger.info(f"{self.agent_id} shutting down")

    def step(self) -> None:
        """
        Represents a single time-step of action for the agent.
        This method must be implemented by each child agent.

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Each agent must implement its own step() method.")