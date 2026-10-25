"""Evidence pack builder (hackathon MVP; PRD FR-PACK-01 to FR-PACK-06, reduced scope).

Writes a ZIP of Markdown and JSON documents plus the case's original evidence files, with a
SHA-256 manifest. Pure: it receives already-loaded data and a callback that returns each
evidence file's original bytes; it does no database or filesystem access.

Safety rules enforced here:
- every ZIP entry name is generated from fixed templates (never from user-supplied filenames)
  and validated: relative, forward slashes, no `..`, no duplicates, limited character set;
- evidence bytes are written exactly as read; nothing is converted or re-encoded;
- no internal storage keys or paths appear in any document.

Not included, by design: a Section 63 certificate draft. No counsel-reviewed template exists
(DECISIONS.md LR-16), and PaySetu must not fabricate legal certifications.
"""

import hashlib
import json
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import IO, Any

from app.domain.rules import RuleMeta
from app.schemas import cases as out

PACK_FORMAT = "paysetu-demo-evidence-pack-1"
DEMO_BANNER = "SYNTHETIC DEMO DATA. NOT LEGALLY CERTIFIED. NOT LEGAL ADVICE."

_SAFE_ENTRY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*$")
_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/heic": ".heic",
    "message/rfc822": ".eml",
    "text/plain": ".txt",
}


class UnsafeEntryNameError(ValueError):
    """A ZIP entry name that is not a plain, relative, unique path."""


@dataclass(frozen=True)
class PackVerification:
    passed: bool
    checked_files: int
    checked_events: int
    head_hash: str | None
    checked_at: datetime


@dataclass(frozen=True)
class PackData:
    generated_at: datetime  # timezone-aware
    supplier: out.SupplierOut
    case: out.CaseOut
    evidence: list[out.EvidenceOut]  # non-excluded items only
    responses: list[out.ResponseOut]
    timeline: list[out.TimelineEventOut]
    checklist: out.ChecklistOut
    interest: out.InterestOut
    rules_relied_on: list[RuleMeta]
    verification: PackVerification
    case_id: str


@dataclass(frozen=True)
class PackResult:
    manifest_sha256: str
    manifest: dict[str, Any]
    entry_names: list[str]


def safe_entry_name(name: str) -> str:
    """Return `name` if it is a safe ZIP path; raise `UnsafeEntryNameError` otherwise."""
    if (
        not _SAFE_ENTRY.fullmatch(name)
        or ".." in name.split("/")
        or "//" in name
        or len(name) > 120
    ):
        raise UnsafeEntryNameError(f"Unsafe ZIP entry name: {name!r}")
    return name


def evidence_entry_name(index: int, item: out.EvidenceOut) -> str:
    """`evidence/01_invoice_ab12cd34.pdf`: built from our own fields, never the user's filename."""
    extension = _EXTENSIONS.get(item.mime_type, ".bin")
    return safe_entry_name(f"evidence/{index:02d}_{item.kind}_{item.sha256[:8]}{extension}")


def cell(value: object) -> str:
    """Make a value safe inside a Markdown table cell."""
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("`", "'") or "-"


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    """A Markdown table, or `empty` text when there are no rows. Cells must be pre-escaped."""
    if not rows:
        return empty
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_pack(
    target: IO[bytes], data: PackData, read_evidence: Callable[[out.EvidenceOut], bytes]
) -> PackResult:
    """Write the pack ZIP to `target`. `read_evidence` returns an item's original bytes."""
    generated = data.generated_at.astimezone(UTC)
    stamp = (
        generated.year,
        generated.month,
        generated.day,
        generated.hour,
        generated.minute,
        generated.second,
    )
    names: list[str] = []
    entries: list[dict[str, Any]] = []

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:

        def add(name: str, content: bytes, role: str, **extra: Any) -> None:
            safe = safe_entry_name(name)
            if safe in names:
                raise UnsafeEntryNameError(f"Duplicate ZIP entry name: {safe!r}")
            info = zipfile.ZipInfo(safe, date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16  # regular file, no execute bit
            archive.writestr(info, content)
            names.append(safe)
            entries.append(
                {
                    "path": safe,
                    "role": role,
                    "size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    **extra,
                }
            )

        documents = [
            ("README_FIRST.md", "readme", _readme(data)),
            ("01_case_summary.md", "document", _case_summary(data)),
            ("02_deemed_clock_and_interest.md", "document", _clock_and_interest(data)),
            ("03_timeline.md", "document", _timeline_md(data)),
            ("04_case_strength_checklist.md", "document", _checklist_md(data)),
            ("05_verification_report.md", "document", _verification_md(data)),
        ]
        for name, role, text in documents:
            add(name, text.encode("utf-8"), role)
        add("timeline.json", _timeline_json(data), "timeline_data")

        for index, item in enumerate(data.evidence, start=1):
            add(
                evidence_entry_name(index, item),
                read_evidence(item),
                "evidence",
                evidence_id=item.id,
                kind=item.kind,
                original_filename=item.original_filename,
                mime_type=item.mime_type,
                recorded_sha256=item.sha256,
            )

        manifest = {
            "pack_format": PACK_FORMAT,
            "demo": True,
            "legally_certified": False,
            "notice": DEMO_BANNER,
            "generated_at": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "case_reference": data.case.reference,
            "rule_set_version": data.case.rule_set_version,
            "timeline_events": data.verification.checked_events,
            "timeline_head_hash": data.verification.head_hash,
            "unconfirmed_rules": data.case.clock.unconfirmed_rules,
            "pending_reviews": data.case.clock.pending_reviews,
            "files": entries,
            "manifest_note": "manifest.json lists every other file; its own SHA-256 is the pack ID.",
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        info = zipfile.ZipInfo("manifest.json", date_time=stamp)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, manifest_bytes)
        names.append("manifest.json")

    return PackResult(hashlib.sha256(manifest_bytes).hexdigest(), manifest, names)


# ----------------------------------------------------------------------------- documents


def _readme(d: PackData) -> str:
    c = d.case
    return f"""# PaySetu evidence pack: {cell(c.reference)}

**{DEMO_BANNER}**

Generated {d.generated_at.astimezone(UTC):%Y-%m-%d %H:%M} UTC from the PaySetu demo build
(rule set `{c.rule_set_version}`). The supplier and buyer in this pack are synthetic samples.
PaySetu prepares and organises evidence. It is not a law firm, does not file claims and does not
certify anything. Dates and amounts are illustrative until reviewed by an advocate.

## What is in this pack

| File | What it is |
| --- | --- |
| `01_case_summary.md` | Supplier, buyer, invoice, delivery, evidence list and buyer responses |
| `02_deemed_clock_and_interest.md` | Acceptance, due date and interest start, the rules relied on, interest |
| `03_timeline.md` / `timeline.json` | Every recorded action in order, with the hash chain |
| `04_case_strength_checklist.md` | What is present or missing in the file (not a prediction) |
| `05_verification_report.md` | Re-check of every evidence file and the timeline chain at export time |
| `evidence/` | The original uploaded files, byte for byte as received |
| `manifest.json` | SHA-256 and size of every other file in this pack |

## How to verify this pack

1. For each entry in `manifest.json`, compute the file's SHA-256 (for example
   `shasum -a 256 <file>`) and compare it with the listed value.
2. The pack ID is the SHA-256 of `manifest.json` itself. PaySetu also returns it in the
   `X-PaySetu-Pack-SHA256` response header when the pack is downloaded.
3. To re-check the timeline, recompute each event's `event_hash`: the SHA-256 of the canonical
   JSON (keys sorted, no extra whitespace, UTF-8) of `case_id`, `seq`, `event_type`,
   `occurred_on`, `recorded_at`, `actor_type`, `actor_id`, `payload` and `prev_hash`. The first
   event's `prev_hash` is 64 zeros, and each later `prev_hash` equals the previous `event_hash`.

A matching hash shows that a file has not changed since it was recorded. It does not show that
the file was genuine when it was uploaded, and it does not by itself make evidence admissible.

## What is not included

- **No Section 63 (Bharatiya Sakshya Adhiniyam) certificate.** No counsel-reviewed template
  exists yet (open item LR-16), so none is generated. No signature, certification or legal
  validity is claimed anywhere in this pack.
- **No filing.** If the buyer does not pay, the supplier files on the official MSME ODR portal
  or instructs an advocate; PaySetu does not do either.

## Open legal review

Rules and readings this pack relies on that an advocate has not confirmed:
{_bullets(c.clock.unconfirmed_rules)}

Open questions (see `docs/DECISIONS.md`): {", ".join(c.clock.pending_reviews)}.
"""


def _case_summary(d: PackData) -> str:
    c, s = d.case, d.supplier
    terms = (
        "Verbal or no written terms"
        if c.deal_type == "verbal"
        else f"Written terms: {c.agreed_payment_days or c.agreed_due_date} "
        f"{'days' if c.agreed_payment_days is not None else '(agreed date)'}"
    )
    reasons = "\n".join(f"- {cell(r['message'])} ({r['status']})" for r in s.eligibility_reasons)
    evidence_table = _table(
        ["File", "Kind", "Original filename", "Bytes", "SHA-256", "Recorded (UTC)", "Note"],
        [
            [
                evidence_entry_name(i, e),
                e.kind,
                cell(e.original_filename),
                str(e.size_bytes),
                f"`{e.sha256}`",
                e.received_at,
                cell(e.note),
            ]
            for i, e in enumerate(d.evidence, start=1)
        ],
        "No evidence files have been uploaded for this case.",
    )
    response_table = _table(
        ["Received", "Kind", "Channel", "Summary", "Objection removed", "PaySetu's reading"],
        [
            [
                str(r.received_on),
                r.kind,
                r.channel,
                cell(r.summary),
                str(r.objection_removed_on or "-"),
                cell(r.note),
            ]
            for r in d.responses
        ],
        "No buyer responses have been recorded.",
    )
    return f"""# Case summary: {cell(c.reference)}

**{DEMO_BANNER}**

## Supplier (synthetic demo supplier)

| Field | Value |
| --- | --- |
| Name | {cell(s.legal_name)} |
| Udyam number | {cell(s.udyam_number)} (verification: {s.udyam_verification_status}) |
| Enterprise class / activity | {cell(s.enterprise_class)} / {cell(s.major_activity)} |
| Udyam registration date | {cell(s.udyam_registration_date)} |
| Eligibility (profile only, not a legal determination) | {s.eligibility_verdict} |

{reasons}

## Buyer

| Field | Value |
| --- | --- |
| Name | {cell(c.buyer.legal_name)} |
| GSTIN | {cell(c.buyer.gstin)} |

## Invoice and delivery

| Field | Value |
| --- | --- |
| Invoice number | {cell(c.invoice_number)} |
| Invoice date | {c.invoice_date} |
| Invoice amount | Rs {c.invoice_amount} |
| Goods or services | {cell(c.description)} |
| Delivery date | {c.delivery_date} |
| Delivery location | {cell(c.delivery_location)} |
| Payment terms | {terms} |
| Recorded in PaySetu | {c.recorded_late_days} day(s) after delivery |
| Payments recorded | None (payments are not part of the demo build) |

## Evidence in this pack

{evidence_table}

## Buyer responses

{response_table}
"""


def _clock_and_interest(d: PackData) -> str:
    k, i = d.case.clock, d.interest
    explanations = "\n".join(
        f"- **{e.field.replace('_', ' ')}** ({', '.join(e.rule_ids)}): {cell(e.text)}"
        for e in k.explanations
    )
    rules = "\n".join(
        f"| {r.rule_id} | {cell(r.title)} | {cell(r.explanation)} | {r.verification_status.value} |"
        for r in d.rules_relied_on
    )
    if i.status == "computed":
        rows = "\n".join(
            f"| {p.start} to {p.end} | {p.days} | {p.annual_rate_percent}% "
            f"{'(UNVERIFIED rate)' if not p.rate_verified else ''} | {p.opening_balance} | {p.interest} |"
            for p in i.periods
        )
        interest = f"""Interest accrued to {i.as_of}: **Rs {i.interest_accrued}** (illustrative).
Total outstanding including interest: **Rs {i.total_outstanding}** (illustrative).

| Period | Days | Rate (3 x bank rate) | Opening balance (Rs) | Interest (Rs) |
| --- | --- | --- | --- | --- |
{rows}

{"**The bank rate used has NOT been verified against an RBI notification.** " if i.uses_unverified_rates else ""}Method: provisional simulation defaults (monthly rests at rate/12 for full months, actual days/365 for part periods, rounded half-up to the paisa, principal-first part payments). These are not validated legal rules."""
    else:
        interest = f"Interest is **not calculated**: {cell(i.message)} (status: `{i.status}`)."
    return f"""# DeemedClock, assumptions and interest

**{DEMO_BANNER}**

Computed as of {k.as_of} (India date) under rule set `{k.rule_set_version}`.

## Result

| Item | Value |
| --- | --- |
| Acceptance state | {k.acceptance_state} (basis: {cell(k.acceptance_basis)}) |
| Last day for the buyer to object in writing | {k.window_end} |
| Acceptance date | {cell(k.acceptance_date)} |
| Payment due | {cell(k.due_date)} |
| Interest from | {cell(k.interest_start)} |
| Indicative limitation date | {cell(k.indicative_limitation_date)} (indicative only) |
| Payment state | {cell(k.payment_state)}{f" ({k.days_overdue} days overdue)" if k.days_overdue else ""} |
| Agreed terms capped at 45 days | {"yes" if k.terms_capped_at_45 else "no"} |

## Why these dates

{explanations or "No dates are fixed yet."}

## Rules and assumptions relied on

Status `text_checked` means the statute wording was compared with the Act as enacted;
`pending_counsel` and `provisional_default` mean an advocate has not confirmed the reading.
The MSMED (Amendment) Act 2026 does not amend the sections used for these dates, but its text
and commencement still need confirmation (LR-21).

| Rule | Title | What it says | Status |
| --- | --- | --- | --- |
{rules}

Open legal questions: {", ".join(k.pending_reviews)}.

## Interest (illustrative)

{interest}
"""


def _timeline_md(d: PackData) -> str:
    rows = "\n".join(
        f"| {e.seq} | {e.recorded_at} | {cell(e.actor_type)} | {e.event_type} | "
        f"{e.occurred_on or '-'} | `{e.event_hash[:16]}` |"
        for e in d.timeline
    )
    return f"""# Timeline

**{DEMO_BANNER}**

Each entry's hash includes the entry before it, so a later change to history can be detected.
Full hashes and payloads are in `timeline.json`.

| # | Recorded (UTC) | Actor | Event | Refers to date | Event hash (first 16) |
| --- | --- | --- | --- | --- | --- |
{rows}
"""


def _timeline_json(d: PackData) -> bytes:
    document = {
        "notice": DEMO_BANNER,
        "case_id": d.case_id,
        "events": [
            {
                "seq": e.seq,
                "event_type": e.event_type,
                "occurred_on": e.occurred_on.isoformat() if e.occurred_on else None,
                "recorded_at": e.recorded_at,
                "actor_type": e.actor_type,
                "actor_id": None,
                "payload": e.payload,
                "prev_hash": e.prev_hash,
                "event_hash": e.event_hash,
            }
            for e in d.timeline
        ],
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _checklist_md(d: PackData) -> str:
    k = d.checklist
    rows = "\n".join(
        f"| {i.item_id} | {cell(i.title)} | {i.level} | {i.status} | {cell(i.action)} |"
        for i in k.items
    )
    return f"""# Case Strength checklist

**{DEMO_BANNER}**

{k.required_met} of {k.required_total} required items complete. This list shows what is present
or missing in the file. It does not score the case or predict any outcome.

| Item | What | Level | Status | What to do |
| --- | --- | --- | --- | --- |
{rows}

Rules awaiting legal confirmation: {", ".join(k.unconfirmed_rules) or "none"}.
"""


def _verification_md(d: PackData) -> str:
    v = d.verification
    files_table = _table(
        ["File in pack", "Recorded and recomputed SHA-256", "Result"],
        [
            [evidence_entry_name(i, e), f"`{e.sha256}`", "match"]
            for i, e in enumerate(d.evidence, start=1)
        ],
        "No evidence files.",
    )
    return f"""# Verification report

**{DEMO_BANNER}**

Performed at {v.checked_at.astimezone(UTC):%Y-%m-%d %H:%M:%S} UTC, immediately before this pack
was built. The export is refused if any check fails, so this report only exists for a passing case.

| Check | Result |
| --- | --- |
| Evidence files re-hashed | {v.checked_files} checked, all match the hash recorded at upload |
| Timeline hash chain | {v.checked_events} events checked, links and hashes consistent |
| Timeline head hash | `{v.head_hash or "(no events)"}` |
| Overall | {"PASS" if v.passed else "FAIL"} |

## Evidence files

{files_table}

## What this does and does not show

A match shows a file has not changed since PaySetu recorded it. It does not show who created
the file, that its contents are true, or that a court will accept it. Admissibility of
electronic evidence needs a Section 63 certificate and the judgement of the forum; none is
provided here.
"""


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in items) or "- none"
