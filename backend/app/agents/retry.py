from dataclasses import dataclass
from enum import StrEnum
from typing import Type

import httpx


class RetryClassification(StrEnum):
    """Classification used to determine retry behavior."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"


@dataclass(frozen=True)
class RetryPolicy:
    """
    Configuration for bounded agent tool retries.

    Retry decisions are based on explicitly classified
    exception types. Deterministic ToolResult failures
    are not retried by the executor.
    """

    max_attempts: int = 2

    retryable_exceptions: tuple[
        Type[BaseException],
        ...,
    ] = (
        TimeoutError,
        ConnectionError,
        httpx.TimeoutException,
        httpx.ConnectError,
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(
                "max_attempts must be at least 1."
            )

    def classify(
        self,
        exception: BaseException,
    ) -> RetryClassification:
        """
        Classify an exception as transient or permanent.
        """
        if isinstance(
            exception,
            self.retryable_exceptions,
        ):
            return RetryClassification.TRANSIENT

        if isinstance(
            exception,
            httpx.HTTPStatusError,
        ):
            status_code = exception.response.status_code

            if status_code == 429 or 500 <= status_code <= 599:
                return RetryClassification.TRANSIENT

        return RetryClassification.PERMANENT

    def should_retry(
        self,
        exception: BaseException,
        attempt: int,
    ) -> bool:
        """
        Return whether another attempt should be made.

        `attempt` is the current one-based attempt number.
        """
        if attempt >= self.max_attempts:
            return False

        return (
            self.classify(exception)
            == RetryClassification.TRANSIENT
        )