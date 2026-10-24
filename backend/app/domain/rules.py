"""Versioned legal rule set (T2.1; PRD Section 4; ADR-013).

`parse_rule_set` validates an already-decoded document (e.g. from TOML) into typed objects.
It performs no I/O; reading the file is done by `app.rules.loader`.

Every legal reading the engine depends on is a named parameter or policy. A policy value the
engine does not implement is rejected with `RuleSetError`, never silently replaced by another
reading.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from app.domain.errors import DomainValidationError, RuleSetError


class Tier(StrEnum):
    STATUTE = "S"
    INTERPRETATION = "I"
    CONFIGURABLE = "C"


class VerificationStatus(StrEnum):
    TEXT_CHECKED = "text_checked"
    PENDING_COUNSEL = "pending_counsel"
    PROVISIONAL_DEFAULT = "provisional_default"
    COUNSEL_CONFIRMED = "counsel_confirmed"


class AgreedTermsOverMax(StrEnum):
    CAP = "cap"  # R6a


class MultipleObjections(StrEnum):
    LATEST_REMOVAL = "latest_removal"  # R21


class AgreedDaysBase(StrEnum):
    ACCEPTANCE = "acceptance"  # A9


class PaymentAllocation(StrEnum):
    PRINCIPAL_FIRST = "principal_first"  # A4


class RateSelection(StrEnum):
    PERIOD_START = "period_start"  # A3


class LimitationLeapDay(StrEnum):
    FEB_28 = "feb_28"  # A11


@dataclass(frozen=True)
class RuleMeta:
    rule_id: str
    tier: Tier
    title: str
    explanation: str
    source: str
    effective_from: date
    verification_status: VerificationStatus
    decision_refs: tuple[str, ...]

    @property
    def counsel_confirmed(self) -> bool:
        return self.verification_status is VerificationStatus.COUNSEL_CONFIRMED


@dataclass(frozen=True)
class RuleParameters:
    # Periods (R2–R6, R4a)
    objection_window_days: int
    appointed_day_period_days: int
    max_agreed_payment_days: int
    # Interest (R8, A1, A2, A10)
    interest_multiplier: Decimal
    months_per_year: int
    day_count_basis_days: int
    # Limitation (R12, A7, A11)
    limitation_years: int
    limitation_warning_days: int
    # Readings of the statute (tier I / C)
    phone_note_counts_as_written: bool  # R19
    other_channel_counts_as_written: bool  # A6
    acknowledgement_ends_window: bool  # R20
    holiday_adjustment: bool  # R4b
    agreed_terms_over_max: AgreedTermsOverMax  # R6a
    multiple_objections: MultipleObjections  # R21
    agreed_days_base: AgreedDaysBase  # A9
    payment_allocation: PaymentAllocation  # A4
    rate_selection: RateSelection  # A3
    limitation_leap_day: LimitationLeapDay  # A11


@dataclass(frozen=True)
class RuleSet:
    version: str
    title: str
    legal_basis: str
    effective_from: date
    effective_until: date | None
    parameters: RuleParameters
    rules: tuple[RuleMeta, ...]
    pending_reviews: tuple[str, ...]

    def rule(self, rule_id: str) -> RuleMeta:
        for meta in self.rules:
            if meta.rule_id == rule_id:
                return meta
        raise RuleSetError(f"Rule set {self.version} has no rule {rule_id!r}.")

    def unconfirmed(self, rule_ids: Iterable[str]) -> tuple[str, ...]:
        """Return the given rule IDs that are not counsel-confirmed, in input order."""
        return tuple(dict.fromkeys(r for r in rule_ids if not self.rule(r).counsel_confirmed))

    def check_applies_to(self, delivery_date: date) -> None:
        """Reject a delivery date outside the period this rule set is declared to govern."""
        if delivery_date < self.effective_from:
            raise DomainValidationError(
                f"Rule set {self.version} applies from {self.effective_from.isoformat()}; "
                f"delivery date {delivery_date.isoformat()} is earlier."
            )
        if self.effective_until is not None and delivery_date >= self.effective_until:
            raise DomainValidationError(
                f"Rule set {self.version} does not apply on or after "
                f"{self.effective_until.isoformat()}."
            )


_SECTIONS = {"rule_set", "parameters", "rules"}
_RULE_SET_KEYS = {
    "version",
    "title",
    "legal_basis",
    "effective_from",
    "effective_until",
    "pending_reviews",
}
_RULE_KEYS = {
    "id",
    "tier",
    "title",
    "explanation",
    "source",
    "effective_from",
    "verification_status",
    "decision_refs",
}
_INT_PARAMS = {
    "objection_window_days": (1, 90),
    "appointed_day_period_days": (1, 90),
    "max_agreed_payment_days": (1, 365),
    "months_per_year": (12, 12),
    "day_count_basis_days": (360, 366),
    "limitation_years": (1, 30),
    "limitation_warning_days": (0, 3650),
}
_BOOL_PARAMS = {
    "phone_note_counts_as_written",
    "other_channel_counts_as_written",
    "acknowledgement_ends_window",
    "holiday_adjustment",
}
_ENUM_PARAMS: dict[str, type[StrEnum]] = {
    "agreed_terms_over_max": AgreedTermsOverMax,
    "multiple_objections": MultipleObjections,
    "agreed_days_base": AgreedDaysBase,
    "payment_allocation": PaymentAllocation,
    "rate_selection": RateSelection,
    "limitation_leap_day": LimitationLeapDay,
}
_DECIMAL_PARAMS = {"interest_multiplier"}
_PARAM_KEYS = set(_INT_PARAMS) | _BOOL_PARAMS | set(_ENUM_PARAMS) | _DECIMAL_PARAMS


def parse_rule_set(document: Mapping[str, Any]) -> RuleSet:
    """Validate a decoded rule-set document. Unknown or missing keys raise `RuleSetError`."""
    _check_keys("document", document, required=_SECTIONS, allowed=_SECTIONS)
    head = _mapping("rule_set", document["rule_set"])
    _check_keys(
        "rule_set", head, required=_RULE_SET_KEYS - {"effective_until"}, allowed=_RULE_SET_KEYS
    )
    params = _parse_parameters(_mapping("parameters", document["parameters"]))

    raw_rules = document["rules"]
    if not isinstance(raw_rules, list) or not raw_rules:
        raise RuleSetError("'rules' must be a non-empty list.")
    rules = tuple(_parse_rule(i, _mapping(f"rules[{i}]", r)) for i, r in enumerate(raw_rules))
    ids = [r.rule_id for r in rules]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise RuleSetError(f"Duplicate rule IDs: {', '.join(duplicates)}.")

    effective_from = _date("rule_set.effective_from", head["effective_from"])
    effective_until = (
        _date("rule_set.effective_until", head["effective_until"])
        if "effective_until" in head
        else None
    )
    if effective_until is not None and effective_until <= effective_from:
        raise RuleSetError("rule_set.effective_until must be after effective_from.")

    return RuleSet(
        version=_str("rule_set.version", head["version"]),
        title=_str("rule_set.title", head["title"]),
        legal_basis=_str("rule_set.legal_basis", head["legal_basis"]),
        effective_from=effective_from,
        effective_until=effective_until,
        parameters=params,
        rules=rules,
        pending_reviews=_str_tuple("rule_set.pending_reviews", head["pending_reviews"]),
    )


def _parse_parameters(raw: Mapping[str, Any]) -> RuleParameters:
    _check_keys("parameters", raw, required=_PARAM_KEYS, allowed=_PARAM_KEYS)
    values: dict[str, Any] = {}
    for key, (low, high) in _INT_PARAMS.items():
        value = raw[key]
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            raise RuleSetError(f"parameters.{key} must be an integer in [{low}, {high}].")
        values[key] = value
    for key in _BOOL_PARAMS:
        if not isinstance(raw[key], bool):
            raise RuleSetError(f"parameters.{key} must be true or false.")
        values[key] = raw[key]
    for key, enum_type in _ENUM_PARAMS.items():
        try:
            values[key] = enum_type(raw[key])
        except ValueError:
            supported = ", ".join(m.value for m in enum_type)
            raise RuleSetError(
                f"parameters.{key}={raw[key]!r} is not supported by this engine "
                f"(supported: {supported})."
            ) from None
    for key in _DECIMAL_PARAMS:
        if not isinstance(raw[key], str):
            raise RuleSetError(f'parameters.{key} must be a decimal string, e.g. "3".')
        try:
            number = Decimal(raw[key])
        except InvalidOperation:
            raise RuleSetError(f"parameters.{key} is not a valid decimal.") from None
        if not number.is_finite() or number <= 0:
            raise RuleSetError(f"parameters.{key} must be a positive decimal.")
        values[key] = number
    if values["holiday_adjustment"]:
        raise RuleSetError("parameters.holiday_adjustment=true is not supported (R4b).")
    return RuleParameters(**values)


def _parse_rule(index: int, raw: Mapping[str, Any]) -> RuleMeta:
    where = f"rules[{index}]"
    _check_keys(where, raw, required=_RULE_KEYS, allowed=_RULE_KEYS)
    try:
        tier = Tier(raw["tier"])
        status = VerificationStatus(raw["verification_status"])
    except ValueError as exc:
        raise RuleSetError(f"{where}: {exc}") from None
    if tier is Tier.STATUTE and status is VerificationStatus.PROVISIONAL_DEFAULT:
        raise RuleSetError(f"{where}: a statute-text rule cannot be a provisional default.")
    if tier is not Tier.STATUTE and status is VerificationStatus.TEXT_CHECKED:
        raise RuleSetError(f"{where}: only statute-text rules can be 'text_checked'.")
    return RuleMeta(
        rule_id=_str(f"{where}.id", raw["id"]),
        tier=tier,
        title=_str(f"{where}.title", raw["title"]),
        explanation=_str(f"{where}.explanation", raw["explanation"]),
        source=_str(f"{where}.source", raw["source"]),
        effective_from=_date(f"{where}.effective_from", raw["effective_from"]),
        verification_status=status,
        decision_refs=_str_tuple(f"{where}.decision_refs", raw["decision_refs"]),
    )


def _check_keys(
    where: str, raw: Mapping[str, Any], *, required: set[str], allowed: set[str]
) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise RuleSetError(f"{where}: unknown keys {', '.join(unknown)}.")
    missing = sorted(required - set(raw))
    if missing:
        raise RuleSetError(f"{where}: missing keys {', '.join(missing)}.")


def _mapping(where: str, value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuleSetError(f"{where} must be a table.")
    return value


def _str(where: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleSetError(f"{where} must be a non-empty string.")
    return value


def _str_tuple(where: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise RuleSetError(f"{where} must be a list of non-empty strings.")
    return tuple(value)


def _date(where: str, value: object) -> date:
    # TOML local dates decode to `date`; a datetime (which subclasses date) is rejected.
    if not isinstance(value, date) or hasattr(value, "hour"):
        raise RuleSetError(f"{where} must be a TOML local date (YYYY-MM-DD).")
    return value
