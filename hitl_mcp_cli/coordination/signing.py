"""Message signing and verification for integrity and non-repudiation."""

import hashlib
import hmac
import json
from typing import Any


class MessageSigner:
    """Sign and verify coordination messages using HMAC-SHA256."""

    def __init__(self, secret_key: str | None = None):
        """Initialize message signer.

        Args:
            secret_key: Server secret key for HMAC (auto-generated if None)
        """
        if secret_key is None:
            import secrets

            secret_key = secrets.token_urlsafe(32)

        self.secret_key = secret_key.encode()

    def sign_message(self, message_dict: dict[str, Any], agent_secret: str) -> str:
        """Sign a message using agent's secret key.

        Args:
            message_dict: Message dictionary (without signature)
            agent_secret: Agent's secret key

        Returns:
            HMAC signature (hex)
        """
        # Canonical JSON representation
        message_json = json.dumps(message_dict, sort_keys=True, separators=(",", ":"))

        # Combine server secret + agent secret for signing
        combined_key = self.secret_key + agent_secret.encode()

        # HMAC-SHA256
        signature = hmac.new(combined_key, message_json.encode(), hashlib.sha256).hexdigest()

        return signature

    def verify_message(self, message_dict: dict[str, Any], signature: str, agent_secret: str) -> bool:
        """Verify message signature.

        Args:
            message_dict: Message dictionary (without signature)
            signature: HMAC signature to verify
            agent_secret: Agent's secret key

        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = self.sign_message(message_dict, agent_secret)
        return hmac.compare_digest(signature, expected_signature)

    def sign_payload(self, payload: str, agent_secret: str) -> str:
        """Sign arbitrary payload.

        Args:
            payload: String payload to sign
            agent_secret: Agent's secret key

        Returns:
            HMAC signature (hex)
        """
        combined_key = self.secret_key + agent_secret.encode()
        signature = hmac.new(combined_key, payload.encode(), hashlib.sha256).hexdigest()
        return signature

    def verify_payload(self, payload: str, signature: str, agent_secret: str) -> bool:
        """Verify payload signature.

        Args:
            payload: String payload
            signature: HMAC signature
            agent_secret: Agent's secret key

        Returns:
            True if valid
        """
        expected_signature = self.sign_payload(payload, agent_secret)
        return hmac.compare_digest(signature, expected_signature)
