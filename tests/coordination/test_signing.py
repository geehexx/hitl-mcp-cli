"""Tests for message signing and verification."""

from hitl_mcp_cli.coordination.signing import MessageSigner


def test_sign_message():
    """Test signing a message."""
    signer = MessageSigner(secret_key="server-secret")
    message = {"id": "msg-1", "from": "agent-a", "content": "Hello"}

    signature = signer.sign_message(message, "agent-secret")

    assert len(signature) == 64  # SHA256 hex = 64 chars
    assert signature.isalnum()


def test_verify_valid_signature():
    """Test verifying valid signature."""
    signer = MessageSigner(secret_key="server-secret")
    message = {"id": "msg-1", "from": "agent-a", "content": "Hello"}

    signature = signer.sign_message(message, "agent-secret")
    valid = signer.verify_message(message, signature, "agent-secret")

    assert valid is True


def test_verify_invalid_signature():
    """Test detecting tampered message."""
    signer = MessageSigner(secret_key="server-secret")
    message = {"id": "msg-1", "from": "agent-a", "content": "Hello"}

    signature = signer.sign_message(message, "agent-secret")

    # Tamper with message
    message["content"] = "Tampered"

    valid = signer.verify_message(message, signature, "agent-secret")

    assert valid is False


def test_verify_wrong_agent_secret():
    """Test detecting wrong agent secret."""
    signer = MessageSigner(secret_key="server-secret")
    message = {"id": "msg-1", "from": "agent-a", "content": "Hello"}

    signature = signer.sign_message(message, "agent-secret")

    # Try to verify with different agent secret
    valid = signer.verify_message(message, signature, "wrong-secret")

    assert valid is False


def test_canonical_json():
    """Test canonical JSON representation."""
    signer = MessageSigner(secret_key="server-secret")

    # Different key order, same content
    message1 = {"id": "msg-1", "from": "agent-a", "content": "Hello"}
    message2 = {"from": "agent-a", "content": "Hello", "id": "msg-1"}

    sig1 = signer.sign_message(message1, "agent-secret")
    sig2 = signer.sign_message(message2, "agent-secret")

    # Should produce same signature
    assert sig1 == sig2


def test_sign_payload():
    """Test signing arbitrary payload."""
    signer = MessageSigner(secret_key="server-secret")
    payload = "Important data"

    signature = signer.sign_payload(payload, "agent-secret")

    assert len(signature) == 64


def test_verify_payload():
    """Test verifying payload signature."""
    signer = MessageSigner(secret_key="server-secret")
    payload = "Important data"

    signature = signer.sign_payload(payload, "agent-secret")
    valid = signer.verify_payload(payload, signature, "agent-secret")

    assert valid is True


def test_verify_tampered_payload():
    """Test detecting tampered payload."""
    signer = MessageSigner(secret_key="server-secret")
    payload = "Important data"

    signature = signer.sign_payload(payload, "agent-secret")

    # Tamper
    tampered = "Tampered data"

    valid = signer.verify_payload(tampered, signature, "agent-secret")

    assert valid is False


def test_different_server_secrets():
    """Test that different server secrets produce different signatures."""
    signer1 = MessageSigner(secret_key="server-secret-1")
    signer2 = MessageSigner(secret_key="server-secret-2")

    message = {"id": "msg-1", "from": "agent-a", "content": "Hello"}

    sig1 = signer1.sign_message(message, "agent-secret")
    sig2 = signer2.sign_message(message, "agent-secret")

    # Different server secrets = different signatures
    assert sig1 != sig2

    # Each can verify their own
    assert signer1.verify_message(message, sig1, "agent-secret")
    assert signer2.verify_message(message, sig2, "agent-secret")

    # But cannot verify each other's
    assert not signer1.verify_message(message, sig2, "agent-secret")
    assert not signer2.verify_message(message, sig1, "agent-secret")
