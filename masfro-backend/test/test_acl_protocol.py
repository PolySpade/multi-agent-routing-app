# filename: test/test_acl_protocol.py

"""
Tests for ACL Protocol and Message Queue
"""

import pytest
from datetime import datetime
from app.communication.acl_protocol import (
    ACLMessage,
    Performative,
    create_request_message,
    create_inform_message,
    create_query_message
)
from app.communication.message_queue import MessageQueue


class TestACLMessage:
    """Test ACL message creation and serialization."""

    def test_create_message(self):
        """Test creating a basic ACL message."""
        msg = ACLMessage(
            performative=Performative.REQUEST,
            sender="agent1",
            receiver="agent2",
            content={"action": "test"}
        )

        assert msg.performative == Performative.REQUEST
        assert msg.sender == "agent1"
        assert msg.receiver == "agent2"
        assert msg.content["action"] == "test"

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = ACLMessage(
            performative=Performative.INFORM,
            sender="agent1",
            receiver="agent2",
            content={"info": "test"}
        )

        msg_dict = msg.to_dict()

        assert msg_dict["performative"] == "INFORM"
        assert msg_dict["sender"] == "agent1"
        assert msg_dict["receiver"] == "agent2"
        assert "timestamp" in msg_dict

    def test_message_to_json(self):
        """Test JSON serialization."""
        msg = ACLMessage(
            performative=Performative.QUERY,
            sender="agent1",
            receiver="agent2",
            content={"query": "test"}
        )

        json_str = msg.to_json()
        assert isinstance(json_str, str)
        assert "QUERY" in json_str

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "performative": "REQUEST",
            "sender": "agent1",
            "receiver": "agent2",
            "content": {"action": "test"},
            "timestamp": datetime.now().isoformat()
        }

        msg = ACLMessage.from_dict(data)

        assert msg.performative == Performative.REQUEST
        assert msg.sender == "agent1"

    def test_create_request_helper(self):
        """Test request message helper."""
        msg = create_request_message(
            sender="agent1",
            receiver="agent2",
            action="calculate_route",
            data={"start": "A", "end": "B"}
        )

        assert msg.performative == Performative.REQUEST
        assert msg.content["action"] == "calculate_route"
        assert msg.content["data"]["start"] == "A"

    def test_create_inform_helper(self):
        """Test inform message helper."""
        msg = create_inform_message(
            sender="agent1",
            receiver="agent2",
            info_type="flood_data",
            data={"depth": 0.5}
        )

        assert msg.performative == Performative.INFORM
        assert msg.content["info_type"] == "flood_data"

    def test_create_query_helper(self):
        """Test query message helper."""
        msg = create_query_message(
            sender="agent1",
            receiver="agent2",
            query_type="risk_score",
            parameters={"location": "Nangka"}
        )

        assert msg.performative == Performative.QUERY
        assert msg.content["query_type"] == "risk_score"


class TestMessageQueue:
    """Test message queue functionality."""

    def test_register_agent(self):
        """Test agent registration."""
        mq = MessageQueue()
        mq.register_agent("agent1")

        assert "agent1" in mq.queues

    def test_register_duplicate_agent(self):
        """Test duplicate registration raises error."""
        mq = MessageQueue()
        mq.register_agent("agent1")

        with pytest.raises(ValueError):
            mq.register_agent("agent1")

    def test_send_message(self):
        """Test sending message."""
        mq = MessageQueue()
        mq.register_agent("agent1")
        mq.register_agent("agent2")

        msg = ACLMessage(
            performative=Performative.REQUEST,
            sender="agent1",
            receiver="agent2",
            content={"test": "data"}
        )

        success = mq.send_message(msg)
        assert success is True

    def test_send_to_unregistered_agent(self):
        """Test sending to unregistered agent raises error."""
        mq = MessageQueue()
        mq.register_agent("agent1")

        msg = ACLMessage(
            performative=Performative.REQUEST,
            sender="agent1",
            receiver="agent_unknown",
            content={"test": "data"}
        )

        with pytest.raises(ValueError):
            mq.send_message(msg)

    def test_receive_message(self):
        """Test receiving message."""
        mq = MessageQueue()
        mq.register_agent("agent1")
        mq.register_agent("agent2")

        msg = ACLMessage(
            performative=Performative.REQUEST,
            sender="agent1",
            receiver="agent2",
            content={"test": "data"}
        )

        mq.send_message(msg)
        received = mq.receive_message("agent2", block=False)

        assert received is not None
        assert received.sender == "agent1"
        assert received.content["test"] == "data"

    def test_receive_empty_queue(self):
        """Test receiving from empty queue."""
        mq = MessageQueue()
        mq.register_agent("agent1")

        received = mq.receive_message("agent1", block=False)
        assert received is None

    def test_queue_size(self):
        """Test getting queue size."""
        mq = MessageQueue()
        mq.register_agent("agent1")
        mq.register_agent("agent2")

        msg = ACLMessage(
            performative=Performative.REQUEST,
            sender="agent1",
            receiver="agent2",
            content={"test": "data"}
        )

        mq.send_message(msg)
        size = mq.get_queue_size("agent2")

        assert size == 1

    def test_clear_queue(self):
        """Test clearing queue."""
        mq = MessageQueue()
        mq.register_agent("agent1")
        mq.register_agent("agent2")

        # Send multiple messages
        for i in range(3):
            msg = ACLMessage(
                performative=Performative.REQUEST,
                sender="agent1",
                receiver="agent2",
                content={"test": i}
            )
            mq.send_message(msg)

        count = mq.clear_queue("agent2")
        assert count == 3
        assert mq.get_queue_size("agent2") == 0

    def test_broadcast_message(self):
        """Test broadcasting message."""
        mq = MessageQueue()
        mq.register_agent("agent1")
        mq.register_agent("agent2")
        mq.register_agent("agent3")

        msg = ACLMessage(
            performative=Performative.INFORM,
            sender="agent1",
            receiver="broadcast",
            content={"alert": "test"}
        )

        count = mq.broadcast_message(msg, exclude_sender=True)

        # Should send to agent2 and agent3 (not agent1)
        assert count == 2
        assert mq.get_queue_size("agent2") == 1
        assert mq.get_queue_size("agent3") == 1
        assert mq.get_queue_size("agent1") == 0
