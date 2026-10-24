"""Case Strength checklist (C01–C17) and next-action rules (DESIGN.md 9.4)."""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.domain.checklist import (
    ChecklistInputs,
    IntegrityStatus,
    InvoiceDetails,
    ItemLevel,
    ItemStatus,
    evaluate_checklist,
)
from app.domain.deemed_clock import BuyerResponseFact, CaseFacts, ClockResult, compute_clock
from app.domain.eligibility import SupplierProfileFacts
from app.domain.next_action import NextActionCode, decide_next_action
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

DELIVERY = date(2026, 11, 1)
OVERDUE_DAY = date(2026, 12, 1)
PROFILE = SupplierProfileFacts(
    udyam_number="UDYAM-TS-02-0001234",
    enterprise_class=EnterpriseClass.MICRO,
    major_activity=MajorActivity.MANUFACTURING,
    udyam_registration_date=date(2024, 6, 12),
    verification_status=UdyamVerificationStatus.CERTIFICATE_UPLOADED,
)
INVOICE = InvoiceDetails("RF/26-27/118", DELIVERY, True, "Apex Auto Components", "36ABCDE1234F1Z5")
FULL_EVIDENCE = frozenset(
    {EvidenceKind.INVOICE, EvidenceKind.DELIVERY_CHALLAN, EvidenceKind.CHAT_EXPORT}
)


def _clock(
    rule_set: RuleSet,
    today: date = OVERDUE_DAY,
    deal: DealType = DealType.VERBAL,
    responses: tuple[BuyerResponseFact, ...] = (),
    settled: bool = False,
) -> ClockResult:
    facts = CaseFacts(
        DELIVERY,
        deal,
        agreed_payment_days=30 if deal is DealType.WRITTEN else None,
        responses=responses,
    )
    return compute_clock(facts, today, rule_set, is_settled=settled)


def _inputs(rule_set: RuleSet, **changes: object) -> ChecklistInputs:
    base = ChecklistInputs(
        profile=PROFILE,
        delivery_date=DELIVERY,
        deal_type=DealType.VERBAL,
        invoice=INVOICE,
        evidence_kinds=FULL_EVIDENCE,
        intimation_done=True,
        demand_done=True,
        clock=_clock(
            rule_set,
            responses=(
                BuyerResponseFact(
                    ResponseKind.ACKNOWLEDGEMENT, date(2026, 11, 3), ResponseChannel.EMAIL
                ),
            ),
        ),
        integrity=IntegrityStatus.PASSED_CURRENT,
        has_simulated_items=False,
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def _status(rule_set: RuleSet, item_id: str, **changes: object) -> ItemStatus:
    return evaluate_checklist(_inputs(rule_set, **changes), rule_set).item(item_id).status


def test_complete_case_meets_every_applicable_item(rule_set: RuleSet) -> None:
    result = evaluate_checklist(_inputs(rule_set), rule_set)
    assert [i.item_id for i in result.items] == [f"C{n:02d}" for n in range(1, 18)]
    assert result.required_met == result.required_total
    assert result.warnings == 0
    assert all(i.action is None for i in result.items)
    assert result.item("C10").status is ItemStatus.NOT_APPLICABLE  # verbal deal


def test_result_has_counts_but_no_score_or_prediction(rule_set: RuleSet) -> None:
    result = evaluate_checklist(_inputs(rule_set), rule_set)
    fields = set(result.__dataclass_fields__)
    assert fields == {"items", "required_met", "required_total", "warnings", "unconfirmed_rules"}


def test_unknown_item_raises_key_error(rule_set: RuleSet) -> None:
    with pytest.raises(KeyError):
        evaluate_checklist(_inputs(rule_set), rule_set).item("C99")


@pytest.mark.parametrize(
    ("item_id", "changes", "expected"),
    [
        ("C01", {"profile": replace(PROFILE, udyam_number=None)}, ItemStatus.MISSING),
        ("C01", {"profile": replace(PROFILE, udyam_number="UDYAM-1")}, ItemStatus.MISSING),
        (
            "C02",
            {
                "profile": replace(
                    PROFILE, verification_status=UdyamVerificationStatus.SELF_DECLARED
                )
            },
            ItemStatus.MISSING,
        ),
        (
            "C02",
            {
                "profile": replace(
                    PROFILE, verification_status=UdyamVerificationStatus.SELF_DECLARED
                ),
                "evidence_kinds": FULL_EVIDENCE | {EvidenceKind.UDYAM_CERTIFICATE},
            },
            ItemStatus.MET,
        ),
        (
            "C02",
            {
                "profile": replace(
                    PROFILE, verification_status=UdyamVerificationStatus.PROVIDER_VERIFIED_SANDBOX
                )
            },
            ItemStatus.WARNING,
        ),
        ("C03", {"profile": replace(PROFILE, enterprise_class=None)}, ItemStatus.MISSING),
        (
            "C03",
            {"profile": replace(PROFILE, enterprise_class=EnterpriseClass.MEDIUM)},
            ItemStatus.WARNING,
        ),
        ("C04", {"profile": replace(PROFILE, major_activity=None)}, ItemStatus.MISSING),
        (
            "C04",
            {"profile": replace(PROFILE, major_activity=MajorActivity.TRADING)},
            ItemStatus.WARNING,
        ),
        ("C05", {"profile": replace(PROFILE, udyam_registration_date=None)}, ItemStatus.MISSING),
        (
            "C05",
            {"profile": replace(PROFILE, udyam_registration_date=date(2026, 11, 2))},
            ItemStatus.WARNING,
        ),
        ("C06", {"evidence_kinds": FULL_EVIDENCE - {EvidenceKind.INVOICE}}, ItemStatus.MISSING),
        ("C07", {"invoice": replace(INVOICE, invoice_number=" ")}, ItemStatus.MISSING),
        ("C07", {"invoice": replace(INVOICE, invoice_date=None)}, ItemStatus.MISSING),
        ("C07", {"invoice": replace(INVOICE, has_invoice_amount=False)}, ItemStatus.MISSING),
        ("C07", {"invoice": replace(INVOICE, buyer_name=None)}, ItemStatus.MISSING),
        ("C07", {"invoice": replace(INVOICE, buyer_gstin=None)}, ItemStatus.MISSING),
        (
            "C07",
            {"invoice": replace(INVOICE, buyer_gstin=None, buyer_gstin_unavailable=True)},
            ItemStatus.MET,
        ),
        (
            "C08",
            {"evidence_kinds": FULL_EVIDENCE - {EvidenceKind.DELIVERY_CHALLAN}},
            ItemStatus.MISSING,
        ),
        (
            "C08",
            {"evidence_kinds": frozenset({EvidenceKind.INVOICE, EvidenceKind.TRACKING_RECORD})},
            ItemStatus.MET,
        ),
        ("C09", {"evidence_kinds": FULL_EVIDENCE - {EvidenceKind.CHAT_EXPORT}}, ItemStatus.MISSING),
        ("C11", {"intimation_done": False}, ItemStatus.MISSING),
        ("C13", {"demand_done": False}, ItemStatus.MISSING),
        ("C16", {"integrity": IntegrityStatus.NEVER_RUN}, ItemStatus.MISSING),
        ("C16", {"integrity": IntegrityStatus.PASSED_STALE}, ItemStatus.MISSING),
        ("C16", {"integrity": IntegrityStatus.FAILED}, ItemStatus.WARNING),
        ("C17", {"has_simulated_items": True}, ItemStatus.WARNING),
    ],
)
def test_item_status(
    item_id: str, changes: dict[str, object], expected: ItemStatus, rule_set: RuleSet
) -> None:
    item = evaluate_checklist(_inputs(rule_set, **changes), rule_set).item(item_id)
    assert item.status is expected
    if expected in (ItemStatus.MISSING, ItemStatus.WARNING):
        assert item.action, f"{item_id} must give a one-line action"


def test_written_deal_needs_terms_evidence(rule_set: RuleSet) -> None:
    clock = _clock(rule_set, deal=DealType.WRITTEN)
    missing = _status(rule_set, "C10", deal_type=DealType.WRITTEN, clock=clock)
    assert missing is ItemStatus.MISSING
    met = _status(
        rule_set,
        "C10",
        deal_type=DealType.WRITTEN,
        clock=clock,
        evidence_kinds=FULL_EVIDENCE | {EvidenceKind.PURCHASE_ORDER},
    )
    assert met is ItemStatus.MET


def test_open_objection_is_a_warning(rule_set: RuleSet) -> None:
    objection = BuyerResponseFact(ResponseKind.OBJECTION, date(2026, 11, 4), ResponseChannel.EMAIL)
    assert (
        _status(rule_set, "C12", clock=_clock(rule_set, responses=(objection,)))
        is ItemStatus.WARNING
    )


def test_demand_not_applicable_until_overdue_and_acknowledgement_missing(rule_set: RuleSet) -> None:
    early = _clock(rule_set, today=date(2026, 11, 10))
    result = evaluate_checklist(_inputs(rule_set, clock=early, demand_done=False), rule_set)
    assert result.item("C13").status is ItemStatus.NOT_APPLICABLE
    assert result.item("C14").status is ItemStatus.MISSING
    assert result.item("C15").status is ItemStatus.NOT_APPLICABLE  # no limitation date yet


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2029, 5, 20), ItemStatus.MET),  # 181 days left: more than 180 (PRD C15)
        (date(2029, 5, 21), ItemStatus.WARNING),  # exactly 180 days left
        (date(2029, 11, 17), ItemStatus.WARNING),
        (date(2029, 11, 18), ItemStatus.WARNING),  # may have passed
    ],
)
def test_limitation_warning_boundaries(
    today: date, expected: ItemStatus, rule_set: RuleSet
) -> None:
    clock = _clock(rule_set, today=today)
    assert clock.indicative_limitation_date == date(2029, 11, 17)
    item = evaluate_checklist(_inputs(rule_set, clock=clock), rule_set).item("C15")
    assert item.status is expected
    if today > date(2029, 11, 17):
        assert item.action is not None and "passed" in item.action


def test_required_counts_exclude_not_applicable_items(rule_set: RuleSet) -> None:
    result = evaluate_checklist(
        _inputs(rule_set, evidence_kinds=frozenset(), integrity=IntegrityStatus.NEVER_RUN), rule_set
    )
    required = [
        i
        for i in result.items
        if i.level is ItemLevel.REQUIRED and i.status is not ItemStatus.NOT_APPLICABLE
    ]
    assert result.required_total == len(required)
    assert result.required_met == len(required) - 3  # C06, C08, C16 missing


# ------------------------------------------------------------------ next action


def _next(
    rule_set: RuleSet,
    clock: ClockResult | None = None,
    *,
    pack_exists: bool = False,
    **changes: object,
) -> NextActionCode:
    inputs = _inputs(rule_set, clock=clock or _clock(rule_set), **changes)
    return decide_next_action(
        inputs.clock,
        evaluate_checklist(inputs, rule_set),
        integrity=inputs.integrity,
        intimation_done=inputs.intimation_done,
        demand_done=inputs.demand_done,
        pack_exists=pack_exists,
    ).code


def test_next_action_priority_order(rule_set: RuleSet) -> None:
    objection = BuyerResponseFact(ResponseKind.OBJECTION, date(2026, 11, 4), ResponseChannel.EMAIL)
    window_open = _clock(rule_set, today=date(2026, 11, 5))
    not_due = _clock(rule_set, today=date(2026, 11, 20), deal=DealType.WRITTEN)  # due 1 Dec

    assert _next(rule_set, integrity=IntegrityStatus.FAILED) is NextActionCode.REVIEW_INTEGRITY
    assert (
        _next(rule_set, _clock(rule_set, responses=(objection,)))
        is NextActionCode.RESOLVE_OBJECTION
    )
    assert _next(rule_set, window_open, intimation_done=False) is NextActionCode.SEND_INTIMATION
    assert (
        _next(rule_set, evidence_kinds=FULL_EVIDENCE - {EvidenceKind.INVOICE})
        is NextActionCode.COMPLETE_EVIDENCE
    )
    assert _next(rule_set, demand_done=False) is NextActionCode.SEND_DEMAND
    assert _next(rule_set) is NextActionCode.GENERATE_PACK
    assert _next(rule_set, pack_exists=True) is NextActionCode.SHARE_OR_FILE
    assert _next(rule_set, _clock(rule_set, settled=True)) is NextActionCode.CLOSE_CASE
    assert _next(rule_set, not_due) is NextActionCode.WAIT
    assert _next(rule_set, window_open) is NextActionCode.WAIT


def test_next_action_details(rule_set: RuleSet) -> None:
    inputs = _inputs(rule_set)
    checklist = evaluate_checklist(inputs, rule_set)
    shared = decide_next_action(
        inputs.clock,
        checklist,
        integrity=inputs.integrity,
        intimation_done=True,
        demand_done=True,
        pack_exists=True,
    )
    assert shared.code is NextActionCode.SHARE_OR_FILE

    missing = _inputs(rule_set, evidence_kinds=FULL_EVIDENCE - {EvidenceKind.DELIVERY_CHALLAN})
    action = decide_next_action(
        missing.clock,
        evaluate_checklist(missing, rule_set),
        integrity=missing.integrity,
        intimation_done=True,
        demand_done=True,
        pack_exists=False,
    )
    assert action.code is NextActionCode.COMPLETE_EVIDENCE and action.checklist_item == "C08"

    window_open = _inputs(rule_set, clock=_clock(rule_set, today=date(2026, 11, 5)))
    wait = decide_next_action(
        window_open.clock,
        evaluate_checklist(window_open, rule_set),
        integrity=window_open.integrity,
        intimation_done=True,
        demand_done=True,
        pack_exists=False,
    )
    assert wait.code is NextActionCode.WAIT and wait.until == DELIVERY + timedelta(days=15)
