"""Reads rule-set TOML files shipped in this package.

File reading lives here, outside `app.domain`, so the domain stays free of I/O (AGENTS.md
Section 2). Validation is done by `app.domain.rules.parse_rule_set`.
"""

import re
import tomllib
from functools import cache
from importlib.resources import files

from app.domain.errors import RuleSetError
from app.domain.rules import RuleSet, parse_rule_set

CURRENT_RULE_SET_VERSION = "msmed-v1"
_VERSION_PATTERN = re.compile(r"^msmed-v[0-9]+$")


@cache
def load_rule_set(version: str = CURRENT_RULE_SET_VERSION) -> RuleSet:
    """Load and validate a packaged rule set by version, e.g. ``"msmed-v1"``."""
    if not _VERSION_PATTERN.fullmatch(version):
        raise RuleSetError(f"Invalid rule-set version {version!r}.")
    resource = files("app.rules").joinpath(f"{version}.toml")
    if not resource.is_file():
        raise RuleSetError(f"Rule set {version!r} not found.")
    try:
        document = tomllib.loads(resource.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise RuleSetError(f"Rule set {version!r} is not valid TOML: {exc}") from None
    rule_set = parse_rule_set(document)
    if rule_set.version != version:
        raise RuleSetError(
            f"File {version}.toml declares version {rule_set.version!r}; they must match."
        )
    return rule_set
