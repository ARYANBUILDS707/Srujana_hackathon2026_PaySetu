"""Evidence pack export for the demo (read-only; PRD FR-PACK-04).

Reuses the existing case services for every figure, so the pack can never disagree with what
the API and UI show. Nothing is written to the database: no timeline event, no evidence change.
The export is refused (409 `integrity_failed`) if any stored file or the timeline chain fails
verification, and again if a file's bytes differ from its recorded hash at the moment it is read.
"""

import hashlib
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from sqlalchemy.orm import Session

from app.clock import Clock
from app.documents.pack import PackData, PackVerification, build_pack
from app.errors import Conflict, FieldError, IntegrityFailed
from app.rules.loader import load_rule_set
from app.schemas import cases as out
from app.services import cases as cases_service
from app.storage.evidence_store import EvidenceStore

MAX_REPORTED_MISMATCHES = 20
_REFERENCE = re.compile(r"^PS-\d{4}-\d{4}$")


@dataclass
class PackExport:
    """A built pack in an anonymous temp file, positioned at the start."""

    file: IO[bytes]
    size_bytes: int
    filename: str
    pack_sha256: str


def export_pack(session: Session, clock: Clock, store: EvidenceStore, case_id: str) -> PackExport:
    verification = cases_service.verify_case(session, store, case_id)  # 404 if not found
    if not verification.passed:
        raise IntegrityFailed(
            "Evidence integrity verification failed, so no pack was created. A stored file or "
            "timeline entry no longer matches its recorded hash.",
            errors=[
                FieldError(f"{m.type}:{m.reference}", "integrity_mismatch", m.detail)
                for m in verification.mismatches[:MAX_REPORTED_MISMATCHES]
            ],
        )

    now = clock.now_utc()
    case = cases_service.get_case(session, clock, case_id)
    timeline = cases_service.list_timeline(session, case_id)
    interest = cases_service.get_interest(session, clock, case_id, None)
    rule_set = load_rule_set(case.rule_set_version)
    relied_on = list(dict.fromkeys([*case.clock.unconfirmed_rules, *interest.unconfirmed_rules]))
    data = PackData(
        generated_at=now,
        supplier=cases_service.get_supplier(session),
        case=case,
        evidence=[e for e in cases_service.list_evidence(session, case_id) if not e.excluded],
        responses=cases_service.list_responses(session, clock, case_id),
        timeline=timeline,
        checklist=cases_service.get_checklist(session, clock, case_id),
        interest=interest,
        rules_relied_on=[rule_set.rule(rule_id) for rule_id in relied_on],
        verification=PackVerification(
            passed=True,
            checked_files=verification.checked_files,
            checked_events=verification.checked_events,
            head_hash=verification.head_hash,
            checked_at=now,
        ),
        case_id=case_id,
    )

    def read_evidence(item: out.EvidenceOut) -> bytes:
        _, path = cases_service.evidence_file(session, store, item.id)
        content = Path(path).read_bytes()
        if _sha256(content) != item.sha256:
            raise IntegrityFailed(
                "A stored file changed while the pack was being built, so no pack was created.",
                errors=[FieldError(f"file:{item.id}", "integrity_mismatch", "hash does not match")],
            )
        return content

    # Anonymous temp file: never listed on disk. It outlives this function on purpose; the
    # streaming response closes it, and it is closed here if building fails.
    target = tempfile.TemporaryFile()  # noqa: SIM115
    try:
        result = build_pack(target, data, read_evidence)
        # A new event during the build would make the pack disagree with the case.
        after = cases_service.list_timeline(session, case_id)
        if [e.event_hash for e in after] != [e.event_hash for e in timeline]:
            raise Conflict("The case changed while the pack was being built. Please try again.")
        size = target.tell()
        target.seek(0)
    except BaseException:
        target.close()
        raise
    reference = case.reference if _REFERENCE.fullmatch(case.reference) else "case"
    return PackExport(
        target, size, f"PaySetu-evidence-pack-{reference}.zip", result.manifest_sha256
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
