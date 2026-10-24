"""Evidence integrity: SHA-256 hashing, hash-chained timeline, verification (T2.5; ADR-008).

A matching hash shows that bytes have not changed since they were hashed. It does not show
that a file was genuine when recorded, and it does not by itself make evidence admissible
(R15; BSA 2023 s.63 certificate pending counsel review, LR-16).

Event hashing follows DATABASE.md Section 3.11: SHA-256 over the canonical JSON of
{case_id, seq, event_type, occurred_on, recorded_at, actor_type, actor_id, payload, prev_hash}.
Canonical JSON = sorted keys, no insignificant whitespace, UTF-8, no floats.
"""

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from app.domain.errors import DomainValidationError

GENESIS_HASH = "0" * 64
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_RECORDED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")


class ActorType(StrEnum):
    SUPPLIER_USER = "supplier_user"
    SYSTEM = "system"
    ADVOCATE_LINK = "advocate_link"
    BUYER_LINK = "buyer_link"


class CheckResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class TimelineEvent:
    case_id: str
    seq: int
    event_type: str
    occurred_on: date | None
    recorded_at: str  # ISO-8601 UTC with "Z", set by the server
    actor_type: ActorType
    actor_id: str | None
    payload: Mapping[str, Any]
    prev_hash: str
    event_hash: str


@dataclass(frozen=True)
class ChainMismatch:
    position: int
    seq: int | None
    reason: str


@dataclass(frozen=True)
class ChainVerification:
    result: CheckResult
    checked_events: int
    head_hash: str | None
    mismatches: tuple[ChainMismatch, ...]


@dataclass(frozen=True)
class FileRecord:
    evidence_id: str
    expected_sha256: str


@dataclass(frozen=True)
class FileMismatch:
    evidence_id: str
    expected: str
    actual: str | None  # None when the stored file could not be found


@dataclass(frozen=True)
class FileVerification:
    result: CheckResult
    checked_files: int
    mismatches: tuple[FileMismatch, ...]


# ----------------------------------------------------------------------------- hashing


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_chunks(chunks: Iterable[bytes]) -> str:
    """Hash a stream of byte chunks (e.g. an upload read in blocks) without joining them."""
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk)
    return digest.hexdigest()


def is_sha256_hex(value: str) -> bool:
    return _HEX64.fullmatch(value) is not None


def canonical_json(value: Any) -> bytes:
    """Deterministic JSON bytes. Floats are rejected to avoid representation differences."""
    _check_canonical(value, "value")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _check_canonical(value: Any, path: str) -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        raise DomainValidationError(f"{path}: floats are not allowed; use strings for decimals.")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise DomainValidationError(f"{path}: object keys must be strings.")
            _check_canonical(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _check_canonical(item, f"{path}[{index}]")
        return
    raise DomainValidationError(f"{path}: unsupported type {type(value).__name__}.")


# --------------------------------------------------------------------------- the chain


def compute_event_hash(
    *,
    case_id: str,
    seq: int,
    event_type: str,
    occurred_on: date | None,
    recorded_at: str,
    actor_type: ActorType,
    actor_id: str | None,
    payload: Mapping[str, Any],
    prev_hash: str,
) -> str:
    body = {
        "case_id": case_id,
        "seq": seq,
        "event_type": event_type,
        "occurred_on": occurred_on.isoformat() if occurred_on else None,
        "recorded_at": recorded_at,
        "actor_type": actor_type.value,
        "actor_id": actor_id,
        "payload": dict(payload),
        "prev_hash": prev_hash,
    }
    return sha256_hex(canonical_json(body))


def append_event(
    previous: TimelineEvent | None,
    *,
    case_id: str,
    event_type: str,
    occurred_on: date | None,
    recorded_at: str,
    actor_type: ActorType,
    actor_id: str | None,
    payload: Mapping[str, Any],
) -> TimelineEvent:
    """Build the next event in a case's chain (seq 1 links to GENESIS_HASH)."""
    if not case_id or not event_type:
        raise DomainValidationError("case_id and event_type are required.")
    if _RECORDED_AT.fullmatch(recorded_at) is None:
        raise DomainValidationError("recorded_at must be ISO-8601 UTC ending in 'Z'.")
    if previous is not None and previous.case_id != case_id:
        raise DomainValidationError("An event cannot follow an event from another case.")
    seq = 1 if previous is None else previous.seq + 1
    prev_hash = GENESIS_HASH if previous is None else previous.event_hash
    event_hash = compute_event_hash(
        case_id=case_id,
        seq=seq,
        event_type=event_type,
        occurred_on=occurred_on,
        recorded_at=recorded_at,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        prev_hash=prev_hash,
    )
    return TimelineEvent(
        case_id=case_id,
        seq=seq,
        event_type=event_type,
        occurred_on=occurred_on,
        recorded_at=recorded_at,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        prev_hash=prev_hash,
        event_hash=event_hash,
    )


def verify_chain(events: Sequence[TimelineEvent]) -> ChainVerification:
    """Check a case's events in stored order: single case, seq 1..n, links and hashes."""
    mismatches: list[ChainMismatch] = []
    case_ids = {e.case_id for e in events}
    if len(case_ids) > 1:
        mismatches.append(ChainMismatch(0, None, "Events belong to more than one case."))

    expected_prev = GENESIS_HASH
    for position, event in enumerate(events):
        expected_seq = position + 1
        if event.seq != expected_seq:
            mismatches.append(
                ChainMismatch(
                    position, event.seq, f"Expected seq {expected_seq}, found {event.seq}."
                )
            )
        if event.prev_hash != expected_prev:
            mismatches.append(
                ChainMismatch(position, event.seq, "prev_hash does not match the previous event.")
            )
        recomputed = compute_event_hash(
            case_id=event.case_id,
            seq=event.seq,
            event_type=event.event_type,
            occurred_on=event.occurred_on,
            recorded_at=event.recorded_at,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            payload=event.payload,
            prev_hash=event.prev_hash,
        )
        if recomputed != event.event_hash:
            mismatches.append(
                ChainMismatch(position, event.seq, "event_hash does not match the event content.")
            )
        expected_prev = event.event_hash

    return ChainVerification(
        result=CheckResult.FAIL if mismatches else CheckResult.PASS,
        checked_events=len(events),
        head_hash=events[-1].event_hash if events else None,
        mismatches=tuple(mismatches),
    )


def verify_files(
    records: Sequence[FileRecord], actual_hashes: Mapping[str, str | None]
) -> FileVerification:
    """Compare recorded hashes with freshly computed ones (`None` = file missing)."""
    mismatches: list[FileMismatch] = []
    for record in records:
        if not is_sha256_hex(record.expected_sha256):
            raise DomainValidationError(
                f"Recorded hash for {record.evidence_id} is not a SHA-256 hex digest."
            )
        actual = actual_hashes.get(record.evidence_id)
        if actual != record.expected_sha256:
            mismatches.append(FileMismatch(record.evidence_id, record.expected_sha256, actual))
    return FileVerification(
        result=CheckResult.FAIL if mismatches else CheckResult.PASS,
        checked_files=len(records),
        mismatches=tuple(mismatches),
    )
