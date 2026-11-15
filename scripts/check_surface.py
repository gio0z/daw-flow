"""Surface-session validation (`validate.py verify`).

Implements the enforceable half of `daw-verify` Rule 8: a UI-affecting change
must carry a recorded role-based session whose write leg, read-back leg, wire
outcome, and operator-visible message are all present. Read-only; owns no
workflow rules of its own.
"""

from __future__ import annotations

import re
from typing import Any

try:
    from scripts.daw_common import make_error as _error, make_warning as _warning
except ImportError:
    from daw_common import make_error as _error, make_warning as _warning  # type: ignore[import-not-found]

SURFACE_UI = "ui"
SURFACE_NON_UI = "non-ui"
SURFACES = (SURFACE_UI, SURFACE_NON_UI)

REQUIRED_LEG_KINDS = ("write", "read_back")
OPTIONAL_LEG_KINDS = ("non_staff",)
LEG_KINDS = REQUIRED_LEG_KINDS + OPTIONAL_LEG_KINDS
LEG_STATUSES = ("passed", "failing", "unexercised")

PHONE_MAX_WIDTH = 480
DESKTOP_MIN_WIDTH = 1024

# A wire outcome must name a concrete result: an HTTP status following a method
# (or an explicit -> N), or a process exit code. A bare number proves nothing.
_WIRE_OUTCOME = re.compile(
    r"(\b(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+\S+\s+[1-5]\d\d\b)"
    r"|(\bexit\s+\d+\b)"
    r"|(->\s*\d+)"
)

_UI_SCOPE_PREFIXES = (
    "frontend/",
    "web/",
    "ui/",
    "app/",
    "public/",
    "src/components/",
    "src/pages/",
    "src/routes/",
    "src/views/",
)
_UI_EXTENSIONS = (".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss", ".html", ".astro")

SURFACE_LIMITATIONS = [
    "Structural only: verifies that a session is recorded and complete, never that it was walked against the real product.",
    "Cannot prove the message shown to the operator matches the wire outcome; a fabricated pass is undetectable here.",
    "Viewport pairing is width-based (phone <= 480 px, desktop >= 1024 px); other form factors are not judged.",
]


def infer_ui_scope(scope: Any) -> bool:
    """Return True when the declared write scope looks like a rendered surface."""
    if not isinstance(scope, list):
        return False
    for entry in scope:
        if not isinstance(entry, str):
            continue
        rel = entry.strip().replace("\\", "/").lower()
        if not rel:
            continue
        if rel.startswith(_UI_SCOPE_PREFIXES):
            return True
        if rel.endswith(_UI_EXTENSIONS):
            return True
    return False


def _check_viewports(session: dict[str, Any], prefix: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    viewports = session.get("viewports")
    if not isinstance(viewports, list) or not viewports:
        return [
            _error(
                "surface_viewport_missing",
                f"{prefix}.viewports",
                "A UI session records both a phone (<= 480 px) and a desktop (>= 1024 px) viewport.",
            )
        ]
    widths: list[int] = []
    for index, viewport in enumerate(viewports):
        location = f"{prefix}.viewports[{index}]"
        if not isinstance(viewport, dict):
            findings.append(_error("surface_viewport_invalid", location, "Viewport entry must be an object."))
            continue
        width = viewport.get("width")
        height = viewport.get("height")
        if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
            findings.append(_error("surface_viewport_invalid", f"{location}.width", "width must be a positive integer."))
            continue
        if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
            findings.append(_error("surface_viewport_invalid", f"{location}.height", "height must be a positive integer."))
            continue
        widths.append(width)
    if len(widths) < 2:
        findings.append(
            _error(
                "surface_viewport_missing",
                f"{prefix}.viewports",
                "At least two viewports are required for a UI change.",
            )
        )
        return findings
    has_phone = any(width <= PHONE_MAX_WIDTH for width in widths)
    has_desktop = any(width >= DESKTOP_MIN_WIDTH for width in widths)
    if not (has_phone and has_desktop):
        findings.append(
            _error(
                "surface_viewport_pair_missing",
                f"{prefix}.viewports",
                "Record both a phone viewport (<= 480 px) and a desktop viewport (>= 1024 px).",
            )
        )
    return findings


def _check_legs(session: dict[str, Any], prefix: str, enforce_passed: bool) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    legs = session.get("legs")
    if not isinstance(legs, list) or not legs:
        return [
            _error(
                "surface_legs_missing",
                f"{prefix}.legs",
                "The session records at least one write leg and one read-back leg.",
            )
        ]

    seen_kinds: set[str] = set()
    for index, leg in enumerate(legs):
        location = f"{prefix}.legs[{index}]"
        if not isinstance(leg, dict):
            findings.append(_error("surface_leg_invalid", location, "Leg entry must be an object."))
            continue
        kind = leg.get("kind")
        if isinstance(kind, str) and kind in LEG_KINDS:
            seen_kinds.add(kind)
        else:
            findings.append(
                _error(
                    "surface_leg_kind_invalid",
                    f"{location}.kind",
                    f"kind must be one of {list(LEG_KINDS)}.",
                )
            )
        for field in ("name", "interaction", "message"):
            value = leg.get(field)
            if not isinstance(value, str) or not value.strip():
                findings.append(
                    _error(
                        "surface_leg_field_missing",
                        f"{location}.{field}",
                        f"{field} must be a non-blank string.",
                    )
                )
        wire = leg.get("wire")
        if not isinstance(wire, str) or not wire.strip():
            findings.append(
                _error(
                    "surface_leg_field_missing",
                    f"{location}.wire",
                    "wire must state the observed outcome, e.g. 'POST /api/v1/x -> 201'.",
                )
            )
        elif not _WIRE_OUTCOME.search(wire):
            findings.append(
                _error(
                    "surface_leg_wire_undetermined",
                    f"{location}.wire",
                    "wire names no HTTP status, exit code, or '-> N' outcome.",
                )
            )
        status = leg.get("status")
        if status is None:
            if enforce_passed:
                findings.append(
                    _error(
                        "surface_leg_not_passed",
                        f"{location}.status",
                        "status is required at completion: passed, failing, or unexercised.",
                    )
                )
        elif status not in LEG_STATUSES:
            findings.append(
                _error(
                    "surface_leg_status_invalid",
                    f"{location}.status",
                    f"status must be one of {list(LEG_STATUSES)}.",
                )
            )
        elif enforce_passed and status != "passed":
            findings.append(
                _error(
                    "surface_leg_not_passed",
                    f"{location}.status",
                    "a leg that is not passed cannot certify a UI criterion as verified.",
                )
            )

    for kind in REQUIRED_LEG_KINDS:
        if kind not in seen_kinds:
            findings.append(
                _error(
                    "surface_leg_kind_missing",
                    f"{prefix}.legs",
                    f"the session has no '{kind}' leg; both write and read_back are required.",
                )
            )
    return findings


def validate_surface_session(
    session: Any,
    *,
    prefix: str = "surface_session",
    enforce_passed: bool = True,
    required: bool = True,
) -> list[dict[str, str]]:
    """Validate one recorded role-based session.

    enforce_passed=False is the in-flight stage (`execute`): shape only, so a
    partially walked session can be recorded without failing the run.
    """
    if session is None:
        if required:
            return [
                _error(
                    "surface_session_missing",
                    prefix,
                    "A UI-affecting task must record its role-based surface session before completion.",
                )
            ]
        return []
    if not isinstance(session, dict):
        return [_error("surface_session_invalid", prefix, "Surface session must be an object.")]

    findings: list[dict[str, str]] = []
    role = session.get("role")
    if not isinstance(role, str) or not role.strip():
        findings.append(_error("surface_role_missing", f"{prefix}.role", "role must name the operator who walked the flow."))
    findings.extend(_check_viewports(session, prefix))
    findings.extend(_check_legs(session, prefix, enforce_passed))
    return findings


def validate_surface_declaration(
    declared: Any, scope: Any
) -> list[dict[str, str]]:
    """Validate the contract's optional `surface` declaration."""
    findings: list[dict[str, str]] = []
    if declared is None:
        if infer_ui_scope(scope):
            findings.append(
                _warning(
                    "surface_declaration_inferred",
                    "surface",
                    "The write scope looks like a rendered surface; declare `surface: \"ui\"` so the session is enforced.",
                )
            )
        return findings
    if not isinstance(declared, str) or declared not in SURFACES:
        findings.append(
            _error("surface_declaration_invalid", "surface", f"surface must be one of {list(SURFACES)}.")
        )
    elif declared == SURFACE_NON_UI and infer_ui_scope(scope):
        findings.append(
            _error(
                "surface_declaration_mismatch",
                "surface",
                "The write scope looks like a rendered surface but `surface` is \"non-ui\"; declare \"ui\" and record the surface session, or narrow the scope.",
            )
        )
    return findings
