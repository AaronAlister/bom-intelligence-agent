import httpx

from backend.app.agents.retry import (
    RetryClassification,
    RetryPolicy,
)


def test_retry_policy_classifies_timeout_as_transient() -> None:
    policy = RetryPolicy()

    assert (
        policy.classify(
            TimeoutError("Temporary timeout.")
        )
        == RetryClassification.TRANSIENT
    )


def test_retry_policy_classifies_connection_error_as_transient() -> None:
    policy = RetryPolicy()

    assert (
        policy.classify(
            ConnectionError("Connection dropped.")
        )
        == RetryClassification.TRANSIENT
    )


def test_retry_policy_classifies_httpx_timeout_as_transient() -> None:
    policy = RetryPolicy()

    assert (
        policy.classify(
            httpx.TimeoutException(
                "Request timed out."
            )
        )
        == RetryClassification.TRANSIENT
    )


def test_retry_policy_classifies_httpx_connect_error_as_transient() -> None:
    policy = RetryPolicy()

    assert (
        policy.classify(
            httpx.ConnectError(
                "Connection failed."
            )
        )
        == RetryClassification.TRANSIENT
    )


def test_retry_policy_classifies_http_429_as_transient() -> None:
    policy = RetryPolicy()

    response = httpx.Response(
        status_code=429,
        request=httpx.Request(
            "GET",
            "https://example.com",
        ),
    )

    exception = httpx.HTTPStatusError(
        "Rate limited.",
        request=response.request,
        response=response,
    )

    assert (
        policy.classify(exception)
        == RetryClassification.TRANSIENT
    )


def test_retry_policy_classifies_http_500_as_transient() -> None:
    policy = RetryPolicy()

    response = httpx.Response(
        status_code=500,
        request=httpx.Request(
            "GET",
            "https://example.com",
        ),
    )

    exception = httpx.HTTPStatusError(
        "Server error.",
        request=response.request,
        response=response,
    )

    assert (
        policy.classify(exception)
        == RetryClassification.TRANSIENT
    )


def test_retry_policy_classifies_http_401_as_permanent() -> None:
    policy = RetryPolicy()

    response = httpx.Response(
        status_code=401,
        request=httpx.Request(
            "GET",
            "https://example.com",
        ),
    )

    exception = httpx.HTTPStatusError(
        "Unauthorized.",
        request=response.request,
        response=response,
    )

    assert (
        policy.classify(exception)
        == RetryClassification.PERMANENT
    )


def test_retry_policy_classifies_http_404_as_permanent() -> None:
    policy = RetryPolicy()

    response = httpx.Response(
        status_code=404,
        request=httpx.Request(
            "GET",
            "https://example.com",
        ),
    )

    exception = httpx.HTTPStatusError(
        "Not found.",
        request=response.request,
        response=response,
    )

    assert (
        policy.classify(exception)
        == RetryClassification.PERMANENT
    )


def test_retry_policy_classifies_runtime_error_as_permanent() -> None:
    policy = RetryPolicy()

    assert (
        policy.classify(
            RuntimeError("Permanent failure.")
        )
        == RetryClassification.PERMANENT
    )


def test_retry_policy_stops_at_max_attempts() -> None:
    policy = RetryPolicy(
        max_attempts=2,
    )

    exception = TimeoutError(
        "Temporary timeout."
    )

    assert policy.should_retry(
        exception,
        attempt=1,
    )

    assert not policy.should_retry(
        exception,
        attempt=2,
    )