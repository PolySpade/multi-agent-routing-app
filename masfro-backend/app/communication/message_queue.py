# filename: app/communication/message_queue.py

"""
Message Queue System for MAS-FRO Agent Communication

This module implements a centralized message queue system for asynchronous
communication between agents in the Multi-Agent System for Flood Route
Optimization (MAS-FRO). Uses thread-safe queues for concurrent agent operations.
"""

from typing import Dict, Optional
from queue import Queue, Empty
from threading import Lock
import logging

from .acl_protocol import ACLMessage

logger = logging.getLogger(__name__)


class MessageQueue:
    """
    Centralized message queue system for inter-agent communication.

    Manages individual message queues for each agent and provides thread-safe
    message routing between agents. Supports asynchronous message passing for
    decoupled agent interactions.

    Attributes:
        queues: Dictionary mapping agent IDs to their message queues
        lock: Thread lock for safe concurrent access

    Example:
        >>> mq = MessageQueue()
        >>> mq.register_agent("flood_agent_001")
        >>> mq.register_agent("hazard_agent_001")
        >>> msg = ACLMessage(...)
        >>> mq.send_message(msg)
        >>> received_msg = mq.receive_message("hazard_agent_001", timeout=1.0)
    """

    def __init__(self):
        """Initialize the message queue system."""
        self.queues: Dict[str, Queue] = {}
        self.lock = Lock()
        logger.info("MessageQueue system initialized")

    def register_agent(self, agent_id: str) -> None:
        """
        Register a new agent and create its message queue.

        Args:
            agent_id: Unique identifier for the agent

        Raises:
            ValueError: If agent is already registered
        """
        with self.lock:
            if agent_id in self.queues:
                raise ValueError(f"Agent {agent_id} is already registered")
            self.queues[agent_id] = Queue()
            logger.info(f"Agent {agent_id} registered with message queue")

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent and remove its message queue.

        Args:
            agent_id: Unique identifier for the agent

        Raises:
            ValueError: If agent is not registered
        """
        with self.lock:
            if agent_id not in self.queues:
                raise ValueError(f"Agent {agent_id} is not registered")
            del self.queues[agent_id]
            logger.info(f"Agent {agent_id} unregistered from message queue")

    def send_message(self, message: ACLMessage) -> None:
        """
        Send a message to the receiver agent's queue.

        Args:
            message: ACLMessage to be sent

        Raises:
            ValueError: If receiver agent is not registered
        """
        receiver = message.receiver
        with self.lock:
            if receiver not in self.queues:
                logger.error(
                    f"Cannot send message: receiver {receiver} not registered"
                )
                raise ValueError(f"Receiver agent {receiver} is not registered")

            self.queues[receiver].put(message)
            logger.debug(
                f"Message sent from {message.sender} to {receiver} "
                f"(performative: {message.performative})"
            )

    def receive_message(
        self,
        agent_id: str,
        timeout: Optional[float] = None,
        block: bool = True
    ) -> Optional[ACLMessage]:
        """
        Receive a message from the agent's queue.

        Args:
            agent_id: ID of the agent receiving the message
            timeout: Maximum time to wait for a message (seconds)
            block: Whether to block waiting for a message

        Returns:
            ACLMessage if available, None if timeout or queue empty

        Raises:
            ValueError: If agent is not registered
        """
        with self.lock:
            if agent_id not in self.queues:
                raise ValueError(f"Agent {agent_id} is not registered")
            agent_queue = self.queues[agent_id]

        try:
            message = agent_queue.get(block=block, timeout=timeout)
            logger.debug(
                f"Message received by {agent_id} from {message.sender} "
                f"(performative: {message.performative})"
            )
            return message
        except Empty:
            return None

    def get_queue_size(self, agent_id: str) -> int:
        """
        Get the number of pending messages for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Number of messages in the agent's queue

        Raises:
            ValueError: If agent is not registered
        """
        with self.lock:
            if agent_id not in self.queues:
                raise ValueError(f"Agent {agent_id} is not registered")
            return self.queues[agent_id].qsize()

