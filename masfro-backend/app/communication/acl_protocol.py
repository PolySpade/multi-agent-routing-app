# filename: app/communication/acl_protocol.py

"""
Agent Communication Language (ACL) Protocol for MAS-FRO

This module implements a standardized communication protocol based on FIPA-ACL
(Foundation for Intelligent Physical Agents - Agent Communication Language)
for message exchange between agents in the Multi-Agent System for Flood Route
Optimization (MAS-FRO).

Reference: FIPA ACL Message Structure Specification
"""

from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json


class Performative(str, Enum):
    """
    ACL message performatives (speech acts).

    Defines the intent or purpose of the message being communicated
    between agents.
    """
    REQUEST = "REQUEST"  # Request an action to be performed
    INFORM = "INFORM"  # Provide information
    QUERY = "QUERY"  # Query for information
    CONFIRM = "CONFIRM"  # Confirm truth of a proposition
    REFUSE = "REFUSE"  # Refuse to perform action
    AGREE = "AGREE"  # Agree to perform action
    FAILURE = "FAILURE"  # Notification of action failure
    PROPOSE = "PROPOSE"  # Submit proposal
    CFP = "CFP"  # Call for proposals


@dataclass
class ACLMessage:
    """
    Agent Communication Language Message.

    Represents a standardized message for inter-agent communication in the
    MAS-FRO system. Follows FIPA-ACL specifications with extensions for
    flood routing domain.

    Attributes:
        performative: The communicative act type (REQUEST, INFORM, etc.)
        sender: Unique identifier of the sending agent
        receiver: Unique identifier of the receiving agent
        content: The actual message payload (typically a dict)
        language: Content representation language (default: "json")
        ontology: Domain ontology identifier (default: "routing")
        conversation_id: Optional identifier for conversation tracking
        reply_with: Optional identifier for this message for tracking replies
        in_reply_to: Optional identifier of message being replied to
        timestamp: Message creation timestamp

    Example:
        >>> msg = ACLMessage(
        ...     performative=Performative.REQUEST,
        ...     sender="flood_agent_001",
        ...     receiver="hazard_agent_001",
        ...     content={
        ...         "action": "update_risk",
        ...         "data": {"location": "Nangka", "flood_depth": 1.5}
        ...     }
        ... )
    """
    performative: Performative
    sender: str
    receiver: str
    content: Dict[str, Any]
    language: str = "json"
    ontology: str = "routing"
    conversation_id: Optional[str] = None
    reply_with: Optional[str] = None
    in_reply_to: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ACL message to dictionary representation.

        Returns:
            Dict containing all message fields with serializable values
        """
        return {
            "performative": self.performative.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "language": self.language,
            "ontology": self.ontology,
            "conversation_id": self.conversation_id,
            "reply_with": self.reply_with,
            "in_reply_to": self.in_reply_to,
            "timestamp": self.timestamp.isoformat()
        }

    def to_json(self) -> str:
        """
        Convert ACL message to JSON string.

        Returns:
            JSON string representation of the message
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ACLMessage":
        """
        Create ACL message from dictionary.

        Args:
            data: Dictionary containing message fields

        Returns:
            ACLMessage instance
        """
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data.get("performative"), str):
            data["performative"] = Performative(data["performative"])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "ACLMessage":
        """
        Create ACL message from JSON string.

        Args:
            json_str: JSON string representation of message

        Returns:
            ACLMessage instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


def create_request_message(
    sender: str,
    receiver: str,
    action: str,
    data: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None
) -> ACLMessage:
    """
    Helper function to create a REQUEST message.

    Args:
        sender: Sender agent ID
        receiver: Receiver agent ID
        action: The requested action
        data: Optional data payload for the request
        conversation_id: Optional conversation tracking ID

    Returns:
        ACLMessage with REQUEST performative
    """
    content = {"action": action}
    if data:
        content["data"] = data

    return ACLMessage(
        performative=Performative.REQUEST,
        sender=sender,
        receiver=receiver,
        content=content,
        conversation_id=conversation_id
    )


def create_inform_message(
    sender: str,
    receiver: str,
    info_type: str,
    data: Dict[str, Any],
    conversation_id: Optional[str] = None,
    in_reply_to: Optional[str] = None
) -> ACLMessage:
    """
    Helper function to create an INFORM message.

    Args:
        sender: Sender agent ID
        receiver: Receiver agent ID
        info_type: Type of information being provided
        data: Information payload
        conversation_id: Optional conversation tracking ID
        in_reply_to: Optional ID of message being replied to

    Returns:
        ACLMessage with INFORM performative
    """
    content = {"info_type": info_type, "data": data}

    return ACLMessage(
        performative=Performative.INFORM,
        sender=sender,
        receiver=receiver,
        content=content,
        conversation_id=conversation_id,
        in_reply_to=in_reply_to
    )


def create_query_message(
    sender: str,
    receiver: str,
    query_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None
) -> ACLMessage:
    """
    Helper function to create a QUERY message.

    Args:
        sender: Sender agent ID
        receiver: Receiver agent ID
        query_type: Type of query being made
        parameters: Optional query parameters
        conversation_id: Optional conversation tracking ID

    Returns:
        ACLMessage with QUERY performative
    """
    content = {"query_type": query_type}
    if parameters:
        content["parameters"] = parameters

    return ACLMessage(
        performative=Performative.QUERY,
        sender=sender,
        receiver=receiver,
        content=content,
        conversation_id=conversation_id
    )
