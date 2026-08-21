"""Worker / cloud error classification for Pub/Sub ACK behavior."""

from __future__ import annotations


class RetryableWorkerError(Exception):
    """Return HTTP 5xx so Pub/Sub retries delivery."""

    def __init__(self, message: str, *, correlation_id: str | None = None) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
        self.retryable = True


class TerminalWorkerError(Exception):
    """Non-retryable — ACK the message (2xx) after recording failure metadata."""

    def __init__(
        self,
        message: str,
        *,
        correlation_id: str | None = None,
        dead_letter_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.correlation_id = correlation_id
        self.dead_letter_reason = dead_letter_reason or message
        self.retryable = False
