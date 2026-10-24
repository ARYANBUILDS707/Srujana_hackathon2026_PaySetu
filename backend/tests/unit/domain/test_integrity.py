import hashlib
from dataclasses import replace
from datetime import date
from typing import Any

import pytest

from app.domain.errors import DomainValidationError
from app.domain.integrity import (
    GENESIS_HASH,
    ActorType,
    CheckResult,
    FileRecord,
    TimelineEvent,
    append_event,
    canonical_json,
    compute_event_hash,
    is_sha256_hex,
    sha256_chunks,
    sha256_hex,
    verify_chain,
    verify_files,
)

CASE = "c-0001"
SAMPLE = b"SAMPLE delivery challan bytes (test data, not real evidence)"


def _chain(n: int, case_id: str = CASE) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for i in range(n):
        events.append(
            append_event(
                events[-1] if events else None,
                case_id=case_id,
                event_type="evidence_added",
                occurred_on=date(2026, 11, 1),
                recorded_at=f"2026-11-01T09:0{i}:00.000Z",
                actor_type=ActorType.SUPPLIER_USER,
                actor_id="u-1",
                payload={"evidence_id": f"e-{i}", "sha256": sha256_hex(SAMPLE + bytes([i]))},
            )
        )
    return events


# ------------------------------------------------------------------- hashing


def test_sha256_matches_hashlib_and_streaming_matches_whole() -> None:
    expected = hashlib.sha256(SAMPLE).hexdigest()
    assert sha256_hex(SAMPLE) == expected
    assert sha256_chunks([SAMPLE[:10], SAMPLE[10:], b""]) == expected
    assert is_sha256_hex(expected) and not is_sha256_hex(expected.upper())


def test_canonical_json_is_order_independent_and_compact() -> None:
    assert canonical_json({"b": 1, "a": [True, None, "₹"]}) == canonical_json(
        {"a": [True, None, "₹"], "b": 1}
    )
    assert canonical_json({"a": 1, "b": "x"}) == b'{"a":1,"b":"x"}'


@pytest.mark.parametrize("value", [{"x": 1.5}, {1: "x"}, {"d": date(2026, 1, 1)}, [object()]])
def test_canonical_json_rejects_non_deterministic_values(value: Any) -> None:
    with pytest.raises(DomainValidationError):
        canonical_json(value)


# --------------------------------------------------------------------- files


def test_file_verification_passes_before_and_fails_after_tampering() -> None:
    record = FileRecord("e-1", sha256_hex(SAMPLE))
    assert verify_files([record], {"e-1": sha256_hex(SAMPLE)}).result is CheckResult.PASS

    tampered = bytearray(SAMPLE)
    tampered[0] ^= 0x01  # flip one bit
    report = verify_files([record], {"e-1": sha256_hex(bytes(tampered))})
    assert report.result is CheckResult.FAIL
    assert report.mismatches[0].evidence_id == "e-1"


def test_missing_file_is_reported_as_mismatch() -> None:
    report = verify_files([FileRecord("e-1", sha256_hex(SAMPLE))], {"e-1": None})
    assert report.result is CheckResult.FAIL and report.mismatches[0].actual is None


def test_malformed_recorded_hash_is_rejected() -> None:
    with pytest.raises(DomainValidationError):
        verify_files([FileRecord("e-1", "not-a-hash")], {})


# --------------------------------------------------------------------- chain


def test_chain_links_from_genesis_and_verifies() -> None:
    events = _chain(4)
    assert events[0].seq == 1 and events[0].prev_hash == GENESIS_HASH
    assert all(b.prev_hash == a.event_hash for a, b in zip(events, events[1:], strict=False))
    report = verify_chain(events)
    assert report.result is CheckResult.PASS
    assert report.checked_events == 4 and report.head_hash == events[-1].event_hash


def test_event_hash_is_deterministic() -> None:
    first, again = _chain(1)[0], _chain(1)[0]
    assert first.event_hash == again.event_hash


def test_empty_chain_passes() -> None:
    report = verify_chain([])
    assert report.result is CheckResult.PASS and report.head_hash is None


def test_payload_change_is_detected() -> None:
    events = _chain(3)
    events[1] = replace(events[1], payload={**events[1].payload, "sha256": "0" * 64})
    report = verify_chain(events)
    assert report.result is CheckResult.FAIL
    assert any(m.seq == 2 and "content" in m.reason for m in report.mismatches)


def test_reordering_is_detected() -> None:
    events = _chain(3)
    events[1], events[2] = events[2], events[1]
    report = verify_chain(events)
    assert report.result is CheckResult.FAIL
    assert any("Expected seq" in m.reason for m in report.mismatches)


def test_missing_event_is_detected() -> None:
    events = _chain(4)
    del events[1]
    assert verify_chain(events).result is CheckResult.FAIL


def test_rehashed_forgery_still_breaks_the_next_link() -> None:
    events = _chain(3)
    forged_payload = {"evidence_id": "e-1", "sha256": "f" * 64}
    forged_hash = compute_event_hash(
        case_id=CASE,
        seq=2,
        event_type="evidence_added",
        occurred_on=events[1].occurred_on,
        recorded_at=events[1].recorded_at,
        actor_type=events[1].actor_type,
        actor_id=events[1].actor_id,
        payload=forged_payload,
        prev_hash=events[1].prev_hash,
    )
    events[1] = replace(events[1], payload=forged_payload, event_hash=forged_hash)
    report = verify_chain(events)
    assert [m.seq for m in report.mismatches] == [3]


def test_mixed_cases_are_detected() -> None:
    events = _chain(1) + [replace(_chain(2, "c-0002")[1])]
    assert verify_chain(events).result is CheckResult.FAIL


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"case_id": ""}, "required"),
        ({"event_type": ""}, "required"),
        ({"recorded_at": "2026-11-01 09:00:00"}, "ISO-8601"),
        ({"recorded_at": "2026-11-01T09:00:00+05:30"}, "ISO-8601"),
    ],
)
def test_append_event_validates_inputs(kwargs: dict[str, str], message: str) -> None:
    base: dict[str, Any] = {
        "case_id": CASE,
        "event_type": "case_created",
        "occurred_on": None,
        "recorded_at": "2026-11-01T09:00:00Z",
        "actor_type": ActorType.SYSTEM,
        "actor_id": None,
        "payload": {},
    }
    with pytest.raises(DomainValidationError, match=message):
        append_event(None, **{**base, **kwargs})


def test_cannot_append_to_another_cases_chain() -> None:
    with pytest.raises(DomainValidationError, match="another case"):
        append_event(
            _chain(1)[0],
            case_id="c-0002",
            event_type="case_created",
            occurred_on=None,
            recorded_at="2026-11-01T09:00:00Z",
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            payload={},
        )
