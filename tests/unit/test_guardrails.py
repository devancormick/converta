import pytest
from services.generation.guardrails import run_pre_guardrails, run_post_guardrails, scrub_pii
from data.schemas.config import Settings


def test_pre_guardrails_passes_clean_text():
    result = run_pre_guardrails("Your loan application is under review.")
    assert result.ok


def test_pre_guardrails_blocks_ssn():
    result = run_pre_guardrails("Please provide your SSN: 123-45-6789")
    assert not result.ok
    assert "PII" in result.reason


def test_post_guardrails_blocks_guaranteed():
    result = run_post_guardrails("Guaranteed approval for everyone!")
    assert not result.ok


def test_post_guardrails_blocks_no_credit_check():
    result = run_post_guardrails("Apply now — no credit check required!")
    assert not result.ok


def test_post_guardrails_passes_clean():
    result = run_post_guardrails("Complete your application to see your rate.")
    assert result.ok


def test_scrub_pii_redacts_ssn():
    scrubbed = scrub_pii("My SSN is 123-45-6789 please process")
    assert "123-45-6789" not in scrubbed
    assert "[REDACTED]" in scrubbed
