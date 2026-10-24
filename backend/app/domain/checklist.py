"""Case Strength readiness checklist C01–C17 (T2.6; PRD FR-CHK-02).

The checklist lists what is present or missing in the case file. It never scores, ranks or
predicts an outcome (FR-CHK-01).
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.deemed_clock import AcceptanceState, ClockResult, PaymentState
from app.domain.eligibility import (
    ReasonStatus,
    SupplierProfileFacts,
    assess_registration_timing,
    is_valid_udyam_number,
)
from app.domain.rules import RuleSet
from app.domain.types import (
    DealType,
    EnterpriseClass,
    EvidenceKind,
    MajorActivity,
    ResponseKind,
    UdyamVerificationStatus,
)

DELIVERY_PROOF = frozenset(
    {EvidenceKind.DELIVERY_CHALLAN, EvidenceKind.DELIVERY_PHOTO, EvidenceKind.TRACKING_RECORD}
)
ORDER_PROOF = frozenset(
    {
        EvidenceKind.PURCHASE_ORDER,
        EvidenceKind.WRITTEN_TERMS,
        EvidenceKind.CHAT_EXPORT,
        EvidenceKind.EMAIL,
    }
)
TERMS_PROOF = frozenset({EvidenceKind.WRITTEN_TERMS, EvidenceKind.PURCHASE_ORDER})


class ItemLevel(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"


class ItemStatus(StrEnum):
    MET = "met"
    MISSING = "missing"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class IntegrityStatus(StrEnum):
    NEVER_RUN = "never_run"
    PASSED_CURRENT = "passed_current"  # last check passed and nothing changed since
    PASSED_STALE = "passed_stale"  # last check passed but the case changed afterwards
    FAILED = "failed"


@dataclass(frozen=True)
class InvoiceDetails:
    invoice_number: str | None
    invoice_date: date | None
    has_invoice_amount: bool
    buyer_name: str | None
    buyer_gstin: str | None
    buyer_gstin_unavailable: bool = False


@dataclass(frozen=True)
class ChecklistInputs:
    profile: SupplierProfileFacts
    delivery_date: date
    deal_type: DealType
    invoice: InvoiceDetails
    evidence_kinds: frozenset[EvidenceKind]  # non-excluded case and supplier-level evidence
    intimation_done: bool  # sent, or recorded as sent manually
    demand_done: bool
    clock: ClockResult
    integrity: IntegrityStatus
    has_simulated_items: bool


@dataclass(frozen=True)
class ChecklistItem:
    item_id: str
    title: str
    level: ItemLevel
    status: ItemStatus
    action: str | None  # one-line next step when not met
    rule_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChecklistResult:
    items: tuple[ChecklistItem, ...]
    required_met: int
    required_total: int
    warnings: int
    unconfirmed_rules: tuple[str, ...]

    def item(self, item_id: str) -> ChecklistItem:
        for entry in self.items:
            if entry.item_id == item_id:
                return entry
        raise KeyError(item_id)


def evaluate_checklist(inputs: ChecklistInputs, rule_set: RuleSet) -> ChecklistResult:
    """Evaluate C01–C17 as of `inputs.clock.as_of`."""
    items = (
        _c01(inputs),
        _c02(inputs),
        _c03(inputs),
        _c04(inputs),
        _c05(inputs),
        _require_kinds(
            "C06", "Invoice file", inputs, {EvidenceKind.INVOICE}, "Upload the invoice."
        ),
        _c07(inputs),
        _require_kinds(
            "C08",
            "Proof of delivery",
            inputs,
            DELIVERY_PROOF,
            "Upload the signed challan or a delivery photo.",
        ),
        _require_kinds(
            "C09",
            "Proof of order",
            inputs,
            ORDER_PROOF,
            "Upload the order message or purchase order.",
            level=ItemLevel.RECOMMENDED,
        ),
        _c10(inputs),
        _flag(
            "C11",
            "Delivery intimation",
            ItemLevel.RECOMMENDED,
            inputs.intimation_done,
            "Send the delivery intimation.",
        ),
        _c12(inputs),
        _c13(inputs),
        _c14(inputs),
        _c15(inputs, rule_set),
        _c16(inputs),
        _c17(inputs),
    )
    required = [i for i in items if i.level is ItemLevel.REQUIRED]
    applicable = [i for i in required if i.status is not ItemStatus.NOT_APPLICABLE]
    rule_ids = tuple(dict.fromkeys(r for i in items for r in i.rule_ids))
    return ChecklistResult(
        items=items,
        required_met=sum(1 for i in applicable if i.status is ItemStatus.MET),
        required_total=len(applicable),
        warnings=sum(1 for i in items if i.status is ItemStatus.WARNING),
        unconfirmed_rules=rule_set.unconfirmed(rule_ids),
    )


def _item(
    item_id: str,
    title: str,
    level: ItemLevel,
    status: ItemStatus,
    action: str | None,
    rule_ids: tuple[str, ...] = (),
) -> ChecklistItem:
    return ChecklistItem(
        item_id,
        title,
        level,
        status,
        None if status in (ItemStatus.MET, ItemStatus.NOT_APPLICABLE) else action,
        rule_ids,
    )


def _flag(item_id: str, title: str, level: ItemLevel, ok: bool, action: str) -> ChecklistItem:
    return _item(item_id, title, level, ItemStatus.MET if ok else ItemStatus.MISSING, action)


def _require_kinds(
    item_id: str,
    title: str,
    inputs: ChecklistInputs,
    kinds: frozenset[EvidenceKind] | set[EvidenceKind],
    action: str,
    level: ItemLevel = ItemLevel.REQUIRED,
) -> ChecklistItem:
    return _flag(item_id, title, level, bool(inputs.evidence_kinds & kinds), action)


def _c01(inputs: ChecklistInputs) -> ChecklistItem:
    number = inputs.profile.udyam_number
    if number and is_valid_udyam_number(number):
        status, action = ItemStatus.MET, None
    elif number:
        status, action = ItemStatus.MISSING, "Correct the Udyam number (UDYAM-XX-00-0000000)."
    else:
        status, action = ItemStatus.MISSING, "Add your Udyam number in Profile."
    return _item("C01", "Udyam number recorded", ItemLevel.REQUIRED, status, action, ("R9", "R9a"))


def _c02(inputs: ChecklistInputs) -> ChecklistItem:
    verification = inputs.profile.verification_status
    if (
        verification
        in (
            UdyamVerificationStatus.CERTIFICATE_UPLOADED,
            UdyamVerificationStatus.PROVIDER_VERIFIED_LIVE,
        )
        or EvidenceKind.UDYAM_CERTIFICATE in inputs.evidence_kinds
    ):
        status = ItemStatus.MET
    elif verification is UdyamVerificationStatus.PROVIDER_VERIFIED_SANDBOX:
        status = ItemStatus.WARNING
    else:
        status = ItemStatus.MISSING
    return _item(
        "C02",
        "Udyam proof",
        ItemLevel.RECOMMENDED,
        status,
        "Upload your Udyam certificate.",
        ("R9a",),
    )


def _c03(inputs: ChecklistInputs) -> ChecklistItem:
    value = inputs.profile.enterprise_class
    if value is None:
        status, action = ItemStatus.MISSING, "Add your enterprise class in Profile."
    elif value is EnterpriseClass.MEDIUM:
        status = ItemStatus.WARNING
        action = "Medium enterprises are not covered by ss.15–24."
    else:
        status, action = ItemStatus.MET, None
    return _item("C03", "Eligible class", ItemLevel.REQUIRED, status, action, ("R9",))


def _c04(inputs: ChecklistInputs) -> ChecklistItem:
    value = inputs.profile.major_activity
    if value is None:
        status, action = ItemStatus.MISSING, "Add your major activity in Profile."
    elif value is MajorActivity.TRADING:
        status = ItemStatus.WARNING
        action = "Trading registrations may not be covered. Ask counsel."
    else:
        status, action = ItemStatus.MET, None
    return _item("C04", "Activity eligibility", ItemLevel.REQUIRED, status, action, ("R11",))


def _c05(inputs: ChecklistInputs) -> ChecklistItem:
    reason = assess_registration_timing(
        inputs.profile.udyam_registration_date, inputs.delivery_date
    )
    status = {
        ReasonStatus.MET: ItemStatus.MET,
        ReasonStatus.WARNING: ItemStatus.WARNING,
        ReasonStatus.MISSING: ItemStatus.MISSING,
        ReasonStatus.FAILED: ItemStatus.WARNING,
    }[reason.status]
    action = (
        "Add your Udyam registration date in Profile."
        if status is ItemStatus.MISSING
        else "Registration after supply may limit your claim. Ask counsel."
    )
    return _item("C05", "Registered before supply", ItemLevel.REQUIRED, status, action, ("R10",))


def _c07(inputs: ChecklistInputs) -> ChecklistItem:
    invoice = inputs.invoice
    complete = (
        bool(invoice.invoice_number and invoice.invoice_number.strip())
        and invoice.invoice_date is not None
        and invoice.has_invoice_amount
        and bool(invoice.buyer_name and invoice.buyer_name.strip())
        and (bool(invoice.buyer_gstin) or invoice.buyer_gstin_unavailable)
    )
    return _flag(
        "C07", "Invoice details", ItemLevel.REQUIRED, complete, "Complete invoice details."
    )


def _c10(inputs: ChecklistInputs) -> ChecklistItem:
    if inputs.deal_type is DealType.VERBAL:
        return _item(
            "C10", "Written terms evidence", ItemLevel.REQUIRED, ItemStatus.NOT_APPLICABLE, None
        )
    return _require_kinds(
        "C10",
        "Written terms evidence",
        inputs,
        TERMS_PROOF,
        "Upload the document showing the agreed terms.",
    )


def _c12(inputs: ChecklistInputs) -> ChecklistItem:
    raised = inputs.clock.acceptance_state is AcceptanceState.OBJECTION_RAISED
    return _item(
        "C12",
        "No open objection",
        ItemLevel.REQUIRED,
        ItemStatus.WARNING if raised else ItemStatus.MET,
        "Resolve the objection and record the date it was removed.",
        ("R2",),
    )


def _c13(inputs: ChecklistInputs) -> ChecklistItem:
    if inputs.clock.payment_state is not PaymentState.OVERDUE:
        return _item("C13", "Demand served", ItemLevel.RECOMMENDED, ItemStatus.NOT_APPLICABLE, None)
    return _flag(
        "C13", "Demand served", ItemLevel.RECOMMENDED, inputs.demand_done, "Send a demand letter."
    )


def _c14(inputs: ChecklistInputs) -> ChecklistItem:
    acknowledged = any(r.kind is ResponseKind.ACKNOWLEDGEMENT for r in inputs.clock.responses)
    return _flag(
        "C14",
        "Buyer acknowledgement",
        ItemLevel.RECOMMENDED,
        acknowledged,
        "Save any message where the buyer confirmed receipt or the amount.",
    )


def _c15(inputs: ChecklistInputs, rule_set: RuleSet) -> ChecklistItem:
    limitation = inputs.clock.indicative_limitation_date
    rules = ("R12", "A7")
    if limitation is None:
        return _item(
            "C15", "Limitation window", ItemLevel.REQUIRED, ItemStatus.NOT_APPLICABLE, None, rules
        )
    days_left = (limitation - inputs.clock.as_of).days
    if days_left > rule_set.parameters.limitation_warning_days:
        status, action = ItemStatus.MET, None
    elif days_left >= 0:
        status, action = ItemStatus.WARNING, "Limitation may be close. Consult counsel now."
    else:
        status, action = ItemStatus.WARNING, "Limitation may have passed. Consult counsel now."
    return _item("C15", "Limitation window", ItemLevel.REQUIRED, status, action, rules)


def _c16(inputs: ChecklistInputs) -> ChecklistItem:
    status = {
        IntegrityStatus.PASSED_CURRENT: ItemStatus.MET,
        IntegrityStatus.PASSED_STALE: ItemStatus.MISSING,
        IntegrityStatus.NEVER_RUN: ItemStatus.MISSING,
        IntegrityStatus.FAILED: ItemStatus.WARNING,
    }[inputs.integrity]
    action = (
        "Review the integrity problem before filing."
        if status is ItemStatus.WARNING
        else "Run Verify integrity."
    )
    return _item("C16", "Integrity", ItemLevel.REQUIRED, status, action)


def _c17(inputs: ChecklistInputs) -> ChecklistItem:
    return _item(
        "C17",
        "No simulated data",
        ItemLevel.REQUIRED,
        ItemStatus.WARNING if inputs.has_simulated_items else ItemStatus.MET,
        "Replace simulated items with real ones before filing.",
    )
