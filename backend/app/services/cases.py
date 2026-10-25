"""Demo vertical slice services: cases, buyer responses, evidence, integrity, interest.

All legal results come from `app.domain` (DeemedClock, interest, eligibility, checklist,
next action, integrity). This module only gathers stored facts, calls the domain and records
timeline events. Every public function takes the caller's `supplier_id`, which routes take from
the authenticated session (never from request data); every query is scoped by it, so another
supplier's case looks exactly like a missing one (404).
"""

import functools
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import Clock, format_utc_timestamp
from app.config import Settings
from app.domain.checklist import (
    ChecklistInputs,
    ChecklistResult,
    IntegrityStatus,
    InvoiceDetails,
    evaluate_checklist,
)
from app.domain.deemed_clock import BuyerResponseFact, CaseFacts, ClockResult, compute_clock
from app.domain.eligibility import SupplierProfileFacts, assess_eligibility
from app.domain.errors import MissingRateError
from app.domain.integrity import (
    ActorType,
    CheckResult,
    FileRecord,
    TimelineEvent,
    append_event,
    canonical_json,
    verify_chain,
    verify_files,
)
from app.domain.interest import BankRatePeriod, InterestResult, compute_interest
from app.domain.next_action import decide_next_action
from app.domain.rules import RuleSet
from app.domain.types import (
    DealType,
    EnterpriseClass,
    EvidenceKind,
    MajorActivity,
    ResponseChannel,
    ResponseKind,
    UdyamVerificationStatus,
)
from app.errors import Conflict, NotFound, PayloadTooLarge
from app.models import Buyer, BuyerResponse, Case, EvidenceItem, Supplier, TimelineEventRow
from app.repositories import cases as repo
from app.rules.loader import CURRENT_RULE_SET_VERSION, load_rule_set
from app.schemas import cases as out
from app.security.body_limit import MIB
from app.storage.evidence_store import EvidenceStore, StoredFile

LATE_RECORD_THRESHOLD_DAYS = 2


# ------------------------------------------------------------------------- helpers


def _uuid() -> str:
    return str(uuid.uuid4())


def _money(paise: int) -> str:
    return f"{Decimal(paise) / 100:.2f}"


def _dec(value: Decimal) -> str:
    return f"{value:.2f}"


def _supplier(session: Session, supplier_id: str) -> Supplier:
    supplier = session.get(Supplier, supplier_id)
    if supplier is None:  # the session resolved it moments ago; only a deleted row lands here
        raise NotFound("Supplier profile not found.")
    return supplier


def _case(session: Session, supplier: Supplier, case_id: str) -> Case:
    case = repo.get_case(session, supplier.id, case_id)
    if case is None:
        raise NotFound("Case not found or you don't have access.")
    return case


def _profile(supplier: Supplier) -> SupplierProfileFacts:
    return SupplierProfileFacts(
        udyam_number=supplier.udyam_number,
        enterprise_class=EnterpriseClass(supplier.enterprise_class)
        if supplier.enterprise_class
        else None,
        major_activity=MajorActivity(supplier.major_activity) if supplier.major_activity else None,
        udyam_registration_date=supplier.udyam_registration_date,
        verification_status=UdyamVerificationStatus(supplier.udyam_verification_status),
    )


def _facts(case: Case, responses: list[BuyerResponse]) -> CaseFacts:
    return CaseFacts(
        delivery_date=case.delivery_date,
        deal_type=DealType(case.deal_type),
        agreed_payment_days=case.agreed_payment_days,
        agreed_due_date=case.agreed_due_date,
        responses=tuple(
            BuyerResponseFact(
                kind=ResponseKind(r.kind),
                received_on=r.received_on,
                channel=ResponseChannel(r.channel),
                objection_removed_on=r.objection_removed_on,
                response_id=r.id,
            )
            for r in responses
        ),
    )


def _to_domain_event(row: TimelineEventRow) -> TimelineEvent:
    return TimelineEvent(
        case_id=row.case_id,
        seq=row.seq,
        event_type=row.event_type,
        occurred_on=row.occurred_on,
        recorded_at=row.recorded_at,
        actor_type=ActorType(row.actor_type),
        actor_id=row.actor_id,
        payload=json.loads(row.payload),
        prev_hash=row.prev_hash,
        event_hash=row.event_hash,
    )


def _append(
    session: Session,
    clock: Clock,
    case_id: str,
    event_type: str,
    payload: dict[str, Any],
    occurred_on: date | None = None,
    actor_type: ActorType = ActorType.SUPPLIER_USER,
) -> TimelineEventRow:
    rows = repo.list_timeline(session, case_id)
    previous = _to_domain_event(rows[-1]) if rows else None
    event = append_event(
        previous,
        case_id=case_id,
        event_type=event_type,
        occurred_on=occurred_on,
        recorded_at=format_utc_timestamp(clock.now_utc()),
        actor_type=actor_type,
        actor_id=None,
        payload=payload,
    )
    row = TimelineEventRow(
        id=_uuid(),
        case_id=case_id,
        seq=event.seq,
        event_type=event.event_type,
        occurred_on=event.occurred_on,
        recorded_at=event.recorded_at,
        actor_type=event.actor_type.value,
        actor_id=None,
        payload=canonical_json(payload).decode("utf-8"),
        prev_hash=event.prev_hash,
        event_hash=event.event_hash,
    )
    session.add(row)
    session.flush()
    return row


def _integrity_status(rows: list[TimelineEventRow]) -> IntegrityStatus:
    checks = [r for r in rows if r.event_type in ("integrity_verified", "integrity_failed")]
    if not checks:
        return IntegrityStatus.NEVER_RUN
    last = checks[-1]
    if last.event_type == "integrity_failed":
        return IntegrityStatus.FAILED
    return (
        IntegrityStatus.PASSED_CURRENT if last.seq == rows[-1].seq else IntegrityStatus.PASSED_STALE
    )


def _rates(session: Session) -> list[BankRatePeriod]:
    return [
        BankRatePeriod(
            effective_from=r.effective_from,
            rate_percent=Decimal(r.rate_bps) / 100,
            source=r.source,
            verified=r.verified,
            verified_by=r.verified_by,
        )
        for r in repo.list_bank_rates(session)
    ]


def _interest(
    case: Case,
    clock_result: ClockResult,
    as_of: date,
    rates: list[BankRatePeriod],
    rule_set: RuleSet,
) -> tuple[str, InterestResult | None, str]:
    """Return (status, result, message). Never invents a rate."""
    start = clock_result.interest_start
    if start is None:
        return "not_applicable", None, "The acceptance date is not fixed yet, so no interest start."
    if as_of < start:
        return "not_yet_due", None, f"Interest would start on {start.isoformat()}."
    if not rates:
        return (
            "rate_data_unavailable",
            None,
            "No RBI bank-rate data is recorded; interest not computed.",
        )
    try:
        result = compute_interest(
            principal=Decimal(case.invoice_amount_paise) / 100,
            interest_start=start,
            as_of=as_of,
            payments=(),
            rate_table=rates,
            rule_set=rule_set,
        )
    except MissingRateError as exc:
        return "rate_data_unavailable", None, f"{exc} Interest not computed."
    note = (
        "Illustrative. Uses a bank rate that PaySetu has NOT verified against RBI sources."
        if result.uses_unverified_rates
        else "Illustrative. Confirm with counsel."
    )
    return "computed", result, note


def _buyer_out(buyer: Buyer) -> out.BuyerOut:
    return out.BuyerOut(
        id=buyer.id,
        legal_name=buyer.legal_name,
        gstin=buyer.gstin,
        contact_name=buyer.contact_name,
        email=buyer.email,
    )


def _summary(case: Case, buyer: Buyer, clock_result: ClockResult) -> out.CaseSummaryOut:
    return out.CaseSummaryOut(
        id=case.id,
        reference=case.reference,
        buyer=_buyer_out(buyer),
        invoice_number=case.invoice_number,
        invoice_amount=_money(case.invoice_amount_paise),
        delivery_date=case.delivery_date,
        acceptance_state=clock_result.acceptance_state.value,
        payment_state=clock_result.payment_state.value if clock_result.payment_state else None,
        due_date=clock_result.due_date,
    )


def _clock_out(result: ClockResult) -> out.ClockOut:
    return out.ClockOut(
        as_of=result.as_of,
        rule_set_version=result.rule_set_version,
        acceptance_state=result.acceptance_state.value,
        acceptance_basis=result.acceptance_basis.value if result.acceptance_basis else None,
        window_end=result.window_end,
        window_day=result.window_day,
        window_days_remaining=result.window_days_remaining,
        acceptance_date=result.acceptance_date,
        due_date=result.due_date,
        interest_start=result.interest_start,
        indicative_limitation_date=result.indicative_limitation_date,
        payment_state=result.payment_state.value if result.payment_state else None,
        days_overdue=result.days_overdue,
        terms_capped_at_45=result.terms_capped_at_max,
        explanations=[
            out.ExplanationOut(field=e.field, rule_ids=list(e.rule_ids), text=e.text)
            for e in result.explanations
        ],
        unconfirmed_rules=list(result.unconfirmed_rules),
        pending_reviews=list(result.pending_reviews),
    )


def _checklist(
    supplier: Supplier,
    case: Case,
    buyer: Buyer,
    evidence: list[EvidenceItem],
    clock_result: ClockResult,
    integrity: IntegrityStatus,
    rule_set: RuleSet,
) -> ChecklistResult:
    return evaluate_checklist(
        ChecklistInputs(
            profile=_profile(supplier),
            delivery_date=case.delivery_date,
            deal_type=DealType(case.deal_type),
            invoice=InvoiceDetails(
                invoice_number=case.invoice_number,
                invoice_date=case.invoice_date,
                has_invoice_amount=case.invoice_amount_paise > 0,
                buyer_name=buyer.legal_name,
                buyer_gstin=buyer.gstin,
            ),
            evidence_kinds=frozenset(
                EvidenceKind(e.kind) for e in evidence if e.excluded_at is None
            ),
            # Letters (intimation, demand) are not built in the demo slice: reported as missing.
            intimation_done=False,
            demand_done=False,
            clock=clock_result,
            integrity=integrity,
            has_simulated_items=False,
        ),
        rule_set,
    )


# ------------------------------------------------------------- allocation conflicts

# Case references and timeline sequence numbers are allocated by reading the current maximum.
# Two requests can read the same value before either commits; the database's unique constraint
# then rejects the second insert. The loser re-reads in a fresh transaction and tries again.
_ALLOCATION_CONSTRAINTS = (
    "cases.supplier_id, cases.reference",
    "timeline_events.case_id, timeline_events.seq",
)
_MAX_ALLOCATION_ATTEMPTS = 5


def _is_allocation_conflict(error: IntegrityError) -> bool:
    return any(name in str(error.orig) for name in _ALLOCATION_CONSTRAINTS)


def _retry_allocation_conflict[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Retry a whole service transaction when it loses a reference/sequence allocation race.

    Only for functions whose database work is one `with session.begin():` block (a rollback
    leaves the session clean) and that do not consume one-shot inputs such as upload streams.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        for _ in range(_MAX_ALLOCATION_ATTEMPTS - 1):
            try:
                return func(*args, **kwargs)
            except IntegrityError as error:
                if not _is_allocation_conflict(error):
                    raise
        return func(*args, **kwargs)  # last attempt: any error propagates

    return wrapper


# ------------------------------------------------------------------------ supplier


def get_supplier(session: Session, supplier_id: str) -> out.SupplierOut:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        rule_set = load_rule_set(CURRENT_RULE_SET_VERSION)
        eligibility = assess_eligibility(_profile(supplier), rule_set)
        return out.SupplierOut(
            id=supplier.id,
            legal_name=supplier.legal_name,
            udyam_number=supplier.udyam_number,
            enterprise_class=_profile(supplier).enterprise_class,
            major_activity=_profile(supplier).major_activity,
            udyam_registration_date=supplier.udyam_registration_date,
            udyam_verification_status=UdyamVerificationStatus(supplier.udyam_verification_status),
            eligibility_verdict=eligibility.verdict.value,
            eligibility_reasons=[
                {"code": r.code, "status": r.status.value, "message": r.message}
                for r in eligibility.reasons
            ],
        )


# -------------------------------------------------------------------------- buyers


def list_buyers(session: Session, supplier_id: str) -> list[out.BuyerOut]:
    with session.begin():
        return [
            _buyer_out(b) for b in repo.list_buyers(session, _supplier(session, supplier_id).id)
        ]


def create_buyer(
    session: Session, supplier_id: str, clock: Clock, data: out.BuyerCreate
) -> out.BuyerOut:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        now = format_utc_timestamp(clock.now_utc())
        buyer = Buyer(
            id=_uuid(),
            supplier_id=supplier.id,
            legal_name=data.legal_name,
            gstin=data.gstin,
            contact_name=data.contact_name,
            email=data.email,
            created_at=now,
            updated_at=now,
        )
        session.add(buyer)
        return _buyer_out(buyer)


# --------------------------------------------------------------------------- cases


@_retry_allocation_conflict
def create_case(
    session: Session, supplier_id: str, clock: Clock, data: out.CaseCreate
) -> out.CaseOut:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        buyer = repo.get_buyer(session, supplier.id, data.buyer_id)
        if buyer is None:
            raise NotFound("Buyer not found.")
        today = clock.today()
        rule_set = load_rule_set(CURRENT_RULE_SET_VERSION)
        case = Case(
            id=_uuid(),
            supplier_id=supplier.id,
            buyer_id=buyer.id,
            reference="",
            rule_set_version=rule_set.version,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            invoice_amount_paise=int(data.invoice_amount * 100),
            description=data.description,
            delivery_date=data.delivery_date,
            delivery_location=data.delivery_location,
            deal_type=data.deal_type.value,
            agreed_payment_days=data.agreed_payment_days,
            agreed_due_date=data.agreed_due_date,
            lifecycle="open",
            created_at=format_utc_timestamp(clock.now_utc()),
            updated_at=format_utc_timestamp(clock.now_utc()),
        )
        # Validates dates and terms with the domain rules (raises DomainValidationError -> 422).
        compute_clock(_facts(case, []), today, rule_set)
        prefix = f"PS-{today.year}-"
        case.reference = (
            f"{prefix}{repo.count_cases_with_prefix(session, supplier.id, prefix) + 1:04d}"
        )
        session.add(case)
        session.flush()
        _append(
            session,
            clock,
            case.id,
            "case_created",
            {
                "reference": case.reference,
                "invoice_number": case.invoice_number,
                "invoice_amount_paise": case.invoice_amount_paise,
                "delivery_date": case.delivery_date.isoformat(),
                "deal_type": case.deal_type,
                "recorded_late_days": (today - case.delivery_date).days,
            },
            occurred_on=case.delivery_date,
        )
        return _case_out(session, clock, supplier, case, buyer)


def list_cases(
    session: Session, supplier_id: str, clock: Clock, limit: int
) -> list[out.CaseSummaryOut]:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        today = clock.today()
        summaries = []
        for case in repo.list_cases(session, supplier.id, limit):
            buyer = repo.get_buyer(session, supplier.id, case.buyer_id)
            assert buyer is not None  # composite FK guarantees it
            rule_set = load_rule_set(case.rule_set_version)
            result = compute_clock(
                _facts(case, repo.list_responses(session, case.id)), today, rule_set
            )
            summaries.append(_summary(case, buyer, result))
        return summaries


def get_case(session: Session, supplier_id: str, clock: Clock, case_id: str) -> out.CaseOut:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        case = _case(session, supplier, case_id)
        buyer = repo.get_buyer(session, supplier.id, case.buyer_id)
        assert buyer is not None
        return _case_out(session, clock, supplier, case, buyer)


def _case_out(
    session: Session, clock: Clock, supplier: Supplier, case: Case, buyer: Buyer
) -> out.CaseOut:
    today = clock.today()
    rule_set = load_rule_set(case.rule_set_version)
    responses = repo.list_responses(session, case.id)
    clock_result = compute_clock(_facts(case, responses), today, rule_set)
    evidence = repo.list_evidence(session, case.id)
    timeline = repo.list_timeline(session, case.id)
    integrity = _integrity_status(timeline)
    checklist = _checklist(supplier, case, buyer, evidence, clock_result, integrity, rule_set)
    action = decide_next_action(
        clock_result,
        checklist,
        integrity=integrity,
        intimation_done=False,
        demand_done=False,
        pack_exists=False,
    )
    status, interest, _message = _interest(case, clock_result, today, _rates(session), rule_set)
    principal = _money(case.invoice_amount_paise)
    created = date.fromisoformat(case.created_at[:10])
    summary = _summary(case, buyer, clock_result)
    return out.CaseOut(
        **summary.model_dump(),
        lifecycle=case.lifecycle,
        invoice_date=case.invoice_date,
        description=case.description,
        delivery_location=case.delivery_location,
        deal_type=DealType(case.deal_type),
        agreed_payment_days=case.agreed_payment_days,
        agreed_due_date=case.agreed_due_date,
        recorded_late_days=max(0, (created - case.delivery_date).days),
        rule_set_version=case.rule_set_version,
        clock=_clock_out(clock_result),
        amounts=out.AmountsOut(
            as_of=today,
            principal=principal,
            paid="0.00",
            outstanding_principal=principal,
            interest=_dec(interest.interest_accrued) if interest else None,
            total_claimable=_dec(interest.total_outstanding) if interest else None,
            interest_status=status,
            uses_unverified_rates=bool(interest and interest.uses_unverified_rates),
        ),
        checklist_summary={
            "required_met": checklist.required_met,
            "required_total": checklist.required_total,
            "warnings": checklist.warnings,
        },
        next_action=out.NextActionOut(
            code=action.code.value, checklist_item=action.checklist_item, until=action.until
        ),
        has_simulated_items=False,
    )


def get_checklist(
    session: Session, supplier_id: str, clock: Clock, case_id: str
) -> out.ChecklistOut:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        case = _case(session, supplier, case_id)
        buyer = repo.get_buyer(session, supplier.id, case.buyer_id)
        assert buyer is not None
        rule_set = load_rule_set(case.rule_set_version)
        clock_result = compute_clock(
            _facts(case, repo.list_responses(session, case.id)), clock.today(), rule_set
        )
        result = _checklist(
            supplier,
            case,
            buyer,
            repo.list_evidence(session, case.id),
            clock_result,
            _integrity_status(repo.list_timeline(session, case.id)),
            rule_set,
        )
        return out.ChecklistOut(
            required_met=result.required_met,
            required_total=result.required_total,
            warnings=result.warnings,
            items=[
                out.ChecklistItemOut(
                    item_id=i.item_id,
                    title=i.title,
                    level=i.level.value,
                    status=i.status.value,
                    action=i.action,
                )
                for i in result.items
            ],
            unconfirmed_rules=list(result.unconfirmed_rules),
        )


def get_interest(
    session: Session, supplier_id: str, clock: Clock, case_id: str, as_of: date | None
) -> out.InterestOut:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        case = _case(session, supplier, case_id)
        rule_set = load_rule_set(case.rule_set_version)
        today = clock.today()
        clock_result = compute_clock(
            _facts(case, repo.list_responses(session, case.id)), today, rule_set
        )
        effective = as_of or today
        status, result, message = _interest(
            case, clock_result, effective, _rates(session), rule_set
        )
        return out.InterestOut(
            status=status,
            as_of=effective,
            interest_start=clock_result.interest_start,
            principal=_money(case.invoice_amount_paise),
            interest_accrued=_dec(result.interest_accrued) if result else None,
            total_outstanding=_dec(result.total_outstanding) if result else None,
            uses_unverified_rates=bool(result and result.uses_unverified_rates),
            periods=[
                out.InterestPeriodOut(
                    start=p.start,
                    end=p.end,
                    days=p.days,
                    kind=p.kind.value,
                    bank_rate_percent=_dec(p.bank_rate_percent),
                    annual_rate_percent=_dec(p.annual_rate_percent),
                    rate_verified=p.rate_verified,
                    opening_balance=_dec(p.opening_balance),
                    interest=_dec(p.interest),
                    closing_principal=_dec(p.closing_principal),
                    closing_interest=_dec(p.closing_interest),
                )
                for p in (result.periods if result else ())
            ],
            unconfirmed_rules=list(
                result.unconfirmed_rules if result else clock_result.unconfirmed_rules
            ),
            pending_reviews=list(rule_set.pending_reviews),
            message=message,
        )


# ---------------------------------------------------------------- buyer responses


def _response_outs(case: Case, rows: list[BuyerResponse], today: date) -> list[out.ResponseOut]:
    result = compute_clock(_facts(case, rows), today, load_rule_set(case.rule_set_version))
    by_id = {a.response_id: a for a in result.responses}
    outputs = []
    for row in rows:
        assessment = by_id[row.id]
        outputs.append(
            out.ResponseOut(
                id=row.id,
                kind=ResponseKind(row.kind),
                received_on=row.received_on,
                channel=ResponseChannel(row.channel),
                summary=row.summary,
                evidence_item_id=row.evidence_item_id,
                objection_removed_on=row.objection_removed_on,
                within_window=assessment.within_window,
                counts_as_written=assessment.counts_as_written,
                affects_acceptance=assessment.affects_acceptance,
                note=assessment.note,
            )
        )
    return outputs


def list_responses(
    session: Session, supplier_id: str, clock: Clock, case_id: str
) -> list[out.ResponseOut]:
    with session.begin():
        case = _case(session, _supplier(session, supplier_id), case_id)
        return _response_outs(case, repo.list_responses(session, case.id), clock.today())


@_retry_allocation_conflict
def record_response(
    session: Session, supplier_id: str, clock: Clock, case_id: str, data: out.ResponseCreate
) -> list[out.ResponseOut]:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        case = _case(session, supplier, case_id)
        if data.evidence_item_id is not None:
            item = repo.get_evidence(session, supplier.id, data.evidence_item_id)
            if item is None or item.case_id != case.id:
                raise NotFound("Evidence item not found in this case.")
        now = format_utc_timestamp(clock.now_utc())
        row = BuyerResponse(
            id=_uuid(),
            case_id=case.id,
            kind=data.kind.value,
            received_on=data.received_on,
            channel=data.channel.value,
            summary=data.summary,
            evidence_item_id=data.evidence_item_id,
            objection_removed_on=None,
            created_at=now,
            updated_at=now,
        )
        rows = [*repo.list_responses(session, case.id), row]
        # Validates the response date against delivery date and today (-> 422 if invalid).
        compute_clock(_facts(case, rows), clock.today(), load_rule_set(case.rule_set_version))
        session.add(row)
        _append(
            session,
            clock,
            case.id,
            "response_recorded",
            {"response_id": row.id, "kind": row.kind, "channel": row.channel},
            occurred_on=row.received_on,
        )
        return _response_outs(case, rows, clock.today())


@_retry_allocation_conflict
def remove_objection(
    session: Session,
    supplier_id: str,
    clock: Clock,
    case_id: str,
    response_id: str,
    removed_on: date,
) -> list[out.ResponseOut]:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        case = _case(session, supplier, case_id)
        row = repo.get_response(session, case.id, response_id)
        if row is None:
            raise NotFound("Response not found.")
        if row.kind != ResponseKind.OBJECTION.value or row.objection_removed_on is not None:
            raise Conflict("Only an open objection can be marked as removed.", code="invalid_state")
        row.objection_removed_on = removed_on
        rows = repo.list_responses(session, case.id)
        compute_clock(_facts(case, rows), clock.today(), load_rule_set(case.rule_set_version))
        row.updated_at = format_utc_timestamp(clock.now_utc())
        _append(
            session,
            clock,
            case.id,
            "objection_removed",
            {"response_id": row.id},
            occurred_on=removed_on,
        )
        return _response_outs(case, rows, clock.today())


# ------------------------------------------------------------------------ evidence


def _evidence_out(item: EvidenceItem) -> out.EvidenceOut:
    return out.EvidenceOut(
        id=item.id,
        kind=EvidenceKind(item.kind),
        original_filename=item.original_filename,
        mime_type=item.mime_type,
        size_bytes=item.size_bytes,
        sha256=item.sha256,
        received_at=item.received_at,
        note=item.note,
        excluded=item.excluded_at is not None,
    )


def upload_evidence(
    session: Session,
    supplier_id: str,
    clock: Clock,
    settings: Settings,
    store: EvidenceStore,
    case_id: str,
    *,
    kind: EvidenceKind,
    filename: str,
    chunks: Any,
    note: str | None,
) -> out.EvidenceOut:
    # The upload stream can only be read once, so the file is stored before the (retryable)
    # database step. A stored file without a row is harmless: content-addressed, never exposed.
    with session.begin():
        _case(session, _supplier(session, supplier_id), case_id)  # access check before any bytes
    stored = store.save(supplier_id, chunks, max_bytes=settings.max_upload_mb * MIB)
    return _record_evidence(
        session, supplier_id, clock, settings, case_id, stored, kind, filename, note
    )


@_retry_allocation_conflict
def _record_evidence(
    session: Session,
    supplier_id: str,
    clock: Clock,
    settings: Settings,
    case_id: str,
    stored: StoredFile,
    kind: EvidenceKind,
    filename: str,
    note: str | None,
) -> out.EvidenceOut:
    with session.begin():
        supplier = _supplier(session, supplier_id)
        case = _case(session, supplier, case_id)
        if (
            repo.case_storage_bytes(session, case.id) + stored.size_bytes
            > settings.max_case_storage_mb * MIB
        ):
            raise PayloadTooLarge(
                "This case has reached its storage limit.", code="case_storage_full"
            )
        existing = next(
            (e for e in repo.list_evidence(session, case.id) if e.sha256 == stored.sha256), None
        )
        if existing is not None:
            raise Conflict(
                f"Already in this case (uploaded {existing.received_at}).",
                code="duplicate_evidence",
            )
        now = format_utc_timestamp(clock.now_utc())
        item = EvidenceItem(
            id=_uuid(),
            case_id=case.id,
            supplier_id=supplier.id,
            kind=kind.value,
            original_filename=_display_filename(filename),
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            storage_key=stored.storage_key,
            received_at=now,
            note=note,
            excluded_at=None,
            excluded_reason=None,
            created_at=now,
        )
        session.add(item)
        session.flush()
        _append(
            session,
            clock,
            case.id,
            "evidence_added",
            {
                "evidence_id": item.id,
                "kind": item.kind,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            },
        )
        return _evidence_out(item)


def _display_filename(filename: str) -> str:
    """Display only; never used in storage paths."""
    cleaned = "".join(ch for ch in filename.replace("\\", "/").split("/")[-1] if ch.isprintable())
    return (cleaned or "upload")[:255]


def list_evidence(session: Session, supplier_id: str, case_id: str) -> list[out.EvidenceOut]:
    with session.begin():
        case = _case(session, _supplier(session, supplier_id), case_id)
        return [_evidence_out(e) for e in repo.list_evidence(session, case.id)]


def evidence_file(
    session: Session, supplier_id: str, store: EvidenceStore, evidence_id: str
) -> tuple[EvidenceItem, str]:
    with session.begin():
        item = repo.get_evidence(session, _supplier(session, supplier_id).id, evidence_id)
        if item is None:
            raise NotFound("Evidence not found or you don't have access.")
        return item, str(store.path_for(item.storage_key))


@dataclass(frozen=True)
class Verification:
    """Result of re-hashing stored evidence and re-walking the timeline chain (read-only)."""

    passed: bool
    checked_files: int
    checked_events: int
    head_hash: str | None
    mismatches: list[out.MismatchOut]


def _verify_case(session: Session, store: EvidenceStore, case: Case) -> Verification:
    evidence = repo.list_evidence(session, case.id)
    files = verify_files(
        [FileRecord(e.id, e.sha256) for e in evidence],
        {e.id: store.current_sha256(e.storage_key) for e in evidence},
    )
    chain = verify_chain([_to_domain_event(r) for r in repo.list_timeline(session, case.id)])
    mismatches = [
        out.MismatchOut(
            type="file",
            reference=m.evidence_id,
            detail="missing" if m.actual is None else "hash does not match the recorded hash",
        )
        for m in files.mismatches
    ] + [
        out.MismatchOut(type="timeline", reference=f"seq {m.seq}", detail=m.reason)
        for m in chain.mismatches
    ]
    return Verification(
        passed=files.result is CheckResult.PASS and chain.result is CheckResult.PASS,
        checked_files=files.checked_files,
        checked_events=chain.checked_events,
        head_hash=chain.head_hash,
        mismatches=mismatches,
    )


def verify_case(
    session: Session, supplier_id: str, store: EvidenceStore, case_id: str
) -> Verification:
    """Verify a case without recording anything (used by the evidence-pack export)."""
    with session.begin():
        return _verify_case(
            session, store, _case(session, _supplier(session, supplier_id), case_id)
        )


@_retry_allocation_conflict
def check_integrity(
    session: Session, supplier_id: str, clock: Clock, store: EvidenceStore, case_id: str
) -> out.IntegrityOut:
    with session.begin():
        case = _case(session, _supplier(session, supplier_id), case_id)
        result = _verify_case(session, store, case)
        row = _append(
            session,
            clock,
            case.id,
            "integrity_verified" if result.passed else "integrity_failed",
            {
                "result": "pass" if result.passed else "fail",
                "checked_files": result.checked_files,
                "checked_events": result.checked_events,
                "head_hash": result.head_hash,
            },
            actor_type=ActorType.SYSTEM,
        )
        return out.IntegrityOut(
            result="pass" if result.passed else "fail",
            checked_files=result.checked_files,
            checked_events=result.checked_events,
            mismatches=result.mismatches,
            timeline_head_hash=result.head_hash,
            recorded_event_seq=row.seq,
        )


def list_timeline(session: Session, supplier_id: str, case_id: str) -> list[out.TimelineEventOut]:
    with session.begin():
        case = _case(session, _supplier(session, supplier_id), case_id)
        return [
            out.TimelineEventOut(
                seq=r.seq,
                event_type=r.event_type,
                occurred_on=r.occurred_on,
                recorded_at=r.recorded_at,
                actor_type=r.actor_type,
                payload=json.loads(r.payload),
                prev_hash=r.prev_hash,
                event_hash=r.event_hash,
            )
            for r in repo.list_timeline(session, case.id)
        ]
