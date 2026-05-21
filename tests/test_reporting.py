from io import StringIO

from cac.reporting import Event, EventType, Phase, PlainReporter, scrub_sensitive_text


def test_scrub_sensitive_text_redacts_common_secret_shapes() -> None:
    message = (
        "api_key=sk-live token:abcd password=hunter2 "
        "Authorization: Bearer secret-token x-api-key: gemini-key "
        "https://example.test/path?key=secret-value&other=1"
    )

    scrubbed = scrub_sensitive_text(message)

    assert "sk-live" not in scrubbed
    assert "abcd" not in scrubbed
    assert "hunter2" not in scrubbed
    assert "secret-token" not in scrubbed
    assert "gemini-key" not in scrubbed
    assert "secret-value" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_plain_reporter_scrubs_failure_errors() -> None:
    stream = StringIO()
    reporter = PlainReporter(stream=stream)

    reporter.on_event(
        Event(
            phase=Phase.TEST,
            event_type=EventType.FAIL,
            index=1,
            total=1,
            question_id="q-001",
            error="Request failed: https://example.test?key=secret-value",
        )
    )

    content = stream.getvalue()
    assert "secret-value" not in content
    assert "key=[REDACTED]" in content
