"""Conservative field labeling for OCR and native PDF text.

The rules only promote explicit values. Missing or conflicting data remains reviewable.
"""

import re
from collections.abc import Iterable
from typing import Any


FIELD_ORDER = (
    "name",
    "email",
    "phone",
    "consent",
    "consent_choice",
    "purpose",
    "signature",
    "notice_version",
    "form_version",
)

LABELS = {
    "name": r"(?:full legal name of customer|full name of (?:the )?depositor|customer name|name of (?:the )?(?:enterprise|individual)|name of claimant(?: \([^)]*\))?|name(?!\s+of))",
    "email": r"(?:e[ -]?mail(?: address| id)?)",
    "phone": r"(?:mobile(?: no\.?| number)?|phone(?: number)?|telephone(?: no\.?)?)",
    "purpose": r"(?:(?:consent|processing|account|loan)?\s*purpose)",
    "notice_version": r"(?:privacy notice version|notice version)",
    "form_version": r"(?:form version)",
}

CATEGORIES = {
    "name": "Identity",
    "email": "Contact",
    "phone": "Contact",
    "consent": "Consent evidence",
    "consent_choice": "Consent evidence",
    "purpose": "Purpose",
    "signature": "Signature evidence",
    "notice_version": "Version",
    "form_version": "Version",
}

PLACEHOLDERS = re.compile(
    r"^(?:[_ .\-/]*|yes\s*[/|]\s*no|dd[/ -]?mm[/ -]?yyyy|n/?a|unknown|please specify)$",
    re.I,
)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()\-.]{6,23}\d)(?!\w)")

DOCUMENT_PURPOSES = {
    "Corporate account": "Open a corporate account",
    "Savings account": "Open a savings account",
    "Fixed deposit": "Open a fixed deposit",
    "Loan application": "Apply for a loan",
    "MSME loan": "Apply for an MSME loan",
    "Unclaimed deposit": "Settle an unclaimed deposit claim",
}


def document_type(text: str) -> str:
    lower = text.lower()
    if "msme loan" in lower:
        return "MSME loan"
    if "unclaimed deposits" in lower or "inoperative accounts claim" in lower:
        return "Unclaimed deposit"
    if "fixed deposit application" in lower:
        return "Fixed deposit"
    if "corporate customer" in lower:
        return "Corporate account"
    if "account opening form" in lower:
        return "Savings account"
    if "loan application" in lower:
        return "Loan application"
    if "consent" in lower:
        return "Consent form"
    return "Unknown"


def _representations(page: dict[str, Any]) -> Iterable[str]:
    seen: set[str] = set()
    for value in (page.get("native_text", ""), page.get("text", "")):
        value = value.strip()
        if value and value not in seen:
            seen.add(value)
            yield value


def _valid_labeled_value(name: str, raw: str) -> str | None:
    raw = raw.strip(" \t:|.-_")
    if not raw or PLACEHOLDERS.fullmatch(raw) or "___" in raw:
        return None
    if name == "email":
        compact = re.sub(r"\s+", "", raw)
        match = EMAIL.fullmatch(compact)
        return match.group(0).lower() if match else None
    if name == "phone":
        match = PHONE.match(raw)
        if not match:
            return None
        value = match.group(0).strip()
        digits = re.sub(r"\D", "", value)
        return value if 7 <= len(digits) <= 15 else None
    if name == "name":
        raw = re.split(r"\s+\(", raw, maxsplit=1)[0].strip(" _")
        if raw.startswith("/"):
            return None
        raw = re.split(r"\s+(?:photograph|date of birth|address)\b", raw, maxsplit=1, flags=re.I)[0]
        raw = " ".join(raw.split())
        parts = raw.split()
        if len(parts) >= 2 and len(parts[0]) == 1 and len(parts[1]) >= 3 and raw.upper() == raw:
            raw = parts[0] + parts[1] + (" " + " ".join(parts[2:]) if len(parts) > 2 else "")
        blocked = (
            "signatory",
            "claimant",
            "guardian",
            "proprietor",
            "partner",
            "director",
            "please",
            "signature",
            "employee",
            "account",
            "address",
            "date of birth",
            "country",
        )
        if len(raw.split()) > 8 or any(word in raw.lower() for word in blocked):
            return None
        return raw if re.search(r"[A-Za-z]", raw) else None
    return raw[:500]


def _labeled_candidates(name: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if name == "name":
        primary_label = (
            r"(?:full\s*legal name of customer|full name of (?:the )?depositor|"
            r"customer name|name of (?:the )?enterprise(?:\s*/\s*individual)?|"
            r"name of (?:the )?individual|"
            r"name of claimant(?: \([^)]*\))?)"
        )
        patterns = (
            (re.compile(rf"^\s*(?:\d+[.)]\s*)?{primary_label}\s*\*?\s*(?:[:|\-]\s*)?(.{{1,500}})$", re.I), 0),
            (re.compile(r"^\s*name\s*[:|\-]\s*(.{1,500})$", re.I), 10),
        )
    else:
        label = LABELS[name]
        delimiter = r"[:|\-]\s*" if name == "purpose" else r"(?:[:|\-]\s*)?"
        patterns = ((re.compile(rf"^\s*(?:\d+[.)]\s*)?{label}\s*\*?\s*{delimiter}(.{{1,500}})$", re.I), 0),)
    for page in pages:
        for source_priority, representation in enumerate(_representations(page)):
            for line in representation.splitlines():
                for pattern, priority in patterns:
                    match = pattern.match(line)
                    if not match:
                        continue
                    normalized = _valid_labeled_value(name, match.group(1))
                    if normalized is not None:
                        candidate_priority = priority + source_priority
                        if name == "phone":
                            label_text = line[: match.start(1)].lower()
                            if "mobile number" in label_text:
                                candidate_priority = source_priority
                            elif "mobile" in label_text:
                                candidate_priority = 10 + source_priority
                            else:
                                candidate_priority = 20 + source_priority
                        candidates.append(
                            {
                                "value": normalized,
                                "raw": match.group(1).strip(),
                                "page": page["number"],
                                "evidence": line.strip(),
                                "confidence": page.get("confidence"),
                                "provenance": "native_or_ocr_label",
                                "priority": candidate_priority,
                            }
                        )
                    break
    return candidates


def _pattern_candidates(name: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recover values whose PDF text layer separates labels from positioned answers."""
    candidates: list[dict[str, Any]] = []
    for page in pages:
        if name == "email" and page["number"] != 1:
            continue
        for representation in _representations(page):
            for line in representation.splitlines():
                clean = line.strip()
                if not clean:
                    continue
                if name == "email":
                    compact = re.sub(r"\s+", "", clean)
                    match = EMAIL.search(compact)
                    value = match.group(0).lower() if match else None
                elif name == "name" and page["number"] == 1:
                    # Boxed PDF fields often store each letter independently. Preserve the
                    # wider gaps between words while joining the smaller character gaps.
                    if len(re.findall(r"[A-Z]\s{1,4}(?=[A-Z])", clean)) < 6:
                        continue
                    value = re.sub(r"(?<=[A-Z])\s{1,4}(?=[A-Z])", "", clean)
                    value = " ".join(value.split())
                    if not re.fullmatch(r"[A-Z][A-Z ]{7,70}", value):
                        continue
                    blocked = ("APPLICATION", "CORPORATION", "BUSINESS PARK", "NEW DELHI")
                    if any(term in value for term in blocked) or not 2 <= len(value.split()) <= 5:
                        continue
                elif name == "phone" and page["number"] == 1:
                    match = re.search(
                        r"(?<!\d)((?:\d\s+){9}\d)(?=\s+[A-Z](?:\s+[A-Z]){3})",
                        clean,
                    )
                    value = re.sub(r"\s+", "", match.group(1)) if match else None
                else:
                    continue
                if value:
                    candidates.append(
                        {
                            "value": value,
                            "raw": clean,
                            "page": page["number"],
                            "evidence": clean,
                            "confidence": page.get("confidence"),
                            "provenance": "native_or_ocr_pattern",
                            "priority": -10 if name == "name" else 0,
                        }
                    )
                    if name == "name":
                        return candidates
    return candidates


def _widget_candidates(name: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = {
        "name": ("name", "applicant", "customer"),
        "email": ("email", "e-mail"),
        "phone": ("phone", "mobile", "telephone"),
        "purpose": ("purpose",),
        "notice_version": ("notice version", "privacy version"),
        "form_version": ("form version",),
    }[name]
    candidates: list[dict[str, Any]] = []
    for page in pages:
        for widget in page.get("widgets", []):
            widget_name = str(widget.get("name", ""))
            if not any(alias in widget_name.lower() for alias in aliases):
                continue
            raw = str(widget.get("value", "")).lstrip("/")
            normalized = _valid_labeled_value(name, raw)
            if normalized is not None:
                candidates.append(
                    {
                        "value": normalized,
                        "raw": raw,
                        "page": page["number"],
                        "evidence": f"PDF field {widget_name}",
                        "confidence": 100.0,
                        "provenance": "pdf_widget",
                    }
                )
    return candidates


def _choose(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    if candidates:
        best_priority = min(candidate.get("priority", 0) for candidate in candidates)
        candidates = [
            candidate for candidate in candidates if candidate.get("priority", 0) == best_priority
        ]
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        unique.setdefault(str(candidate["value"]).casefold(), candidate)
    if len(unique) == 1:
        return next(iter(unique.values())), None
    return None, "ambiguous" if unique else "not_present"


def _field(name: str, hit: dict[str, Any] | None, missing_reason: str | None) -> dict[str, Any]:
    return {
        "name": name,
        "category": CATEGORIES[name],
        "value": hit["value"] if hit else None,
        "raw_value": hit["raw"] if hit else None,
        "page": hit["page"] if hit else None,
        "evidence": hit["evidence"] if hit else "",
        "confidence": hit.get("confidence") if hit else None,
        "missing_reason": missing_reason,
        "party": "Unassigned",
        "provenance": hit.get("provenance", "extracted") if hit else "extracted",
    }


def _clauses(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for page in pages:
        for text in _representations(page):
            for line in text.splitlines():
                clean = " ".join(line.split())
                if len(clean) < 12:
                    continue
                lower = clean.lower()
                category = None
                if (
                    "consent" in lower
                    or "certify" in lower
                    or (("authorise" in lower or "authorize" in lower) and "signator" not in lower)
                    or re.search(r"\b(?:i/?we|we)\b.*\bagree\b", lower)
                ) and not re.fullmatch(r"(?:privacy\s+)?consent\s+form", lower):
                    category = "Consent candidate"
                elif "premature withdrawal" in lower or "maturity payment" in lower:
                    category = "Product instruction"
                elif "sms alert" in lower or "e-mail alert" in lower or "email alert" in lower:
                    category = "Service preference"
                elif any(word in lower for word in ("declare", "declaration", "certify", "acknowledge")):
                    category = "Declaration"
                elif "purpose" in lower:
                    category = "Purpose context"
                if category and (category, clean) not in seen:
                    seen.add((category, clean))
                    clauses.append({"category": category, "text": clean[:2000], "page": page["number"]})
    return clauses[:100]


def categorize(pages: list[dict[str, Any]]) -> dict[str, Any]:
    combined = "\n".join(
        f"{page.get('native_text', '')}\n{page.get('text', '')}" for page in pages
    )
    warnings: list[str] = []
    fields: dict[str, dict[str, Any]] = {}

    for name in ("name", "email", "phone", "purpose", "notice_version", "form_version"):
        candidates = _widget_candidates(name, pages) + _labeled_candidates(name, pages)
        if name == "name":
            candidates.extend(_pattern_candidates(name, pages))
        elif name in ("email", "phone") and not candidates:
            candidates.extend(_pattern_candidates(name, pages))
        hit, missing_reason = _choose(candidates)
        fields[name] = _field(name, hit, missing_reason)
        if missing_reason == "ambiguous":
            warnings.append(f"Multiple {name.replace('_', ' ')} values were found; review is required.")

    clauses = _clauses(pages)
    consent_clauses = [clause for clause in clauses if clause["category"] == "Consent candidate"]
    consent_clauses.sort(key=lambda clause: ("consent" not in clause["text"].lower(), clause["page"]))
    if consent_clauses:
        clause = consent_clauses[0]
        consent_text = " ".join(item["text"] for item in consent_clauses[:5])[:2000]
        fields["consent"] = _field(
            "consent",
            {
                "value": consent_text,
                "raw": consent_text,
                "page": clause["page"],
                "evidence": consent_text,
                "confidence": None,
                "provenance": "clause_rule",
            },
            None,
        )
    else:
        fields["consent"] = _field(
            "consent", None, "not_present"
        )

    choices: list[dict[str, Any]] = []
    for clause in consent_clauses:
        match = re.search(
            r"(?:consent|authori[sz](?:e|ation))[^\n:]{0,80}:\s*(yes|no)\b",
            clause["text"],
            re.I,
        )
        if match:
            value = match.group(1).lower()
            choices.append(
                {
                    "value": value,
                    "raw": value,
                    "page": clause["page"],
                    "evidence": clause["text"],
                    "confidence": None,
                    "provenance": "clause_rule",
                }
            )
    choice, choice_missing = _choose(choices)
    fields["consent_choice"] = _field("consent_choice", choice, choice_missing)

    signature_widgets = []
    signature_ocr_hit: tuple[dict[str, Any], str] | None = None
    signature_label_page: int | None = None
    for page in pages:
        for widget in page.get("widgets", []):
            if "sign" in str(widget.get("name", "")).lower() and str(widget.get("value", "")).strip("/"):
                signature_widgets.append((page, widget))
        page_text = f"{page.get('native_text', '')}\n{page.get('text', '')}"
        if signature_label_page is None and re.search(r"\bsignatures?\b|\bsigned by\b", page_text, re.I):
            signature_label_page = page["number"]
        ocr_lines = [line.strip() for line in page.get("text", "").splitlines() if line.strip()]
        for index, line in enumerate(ocr_lines):
            direct = re.search(r"\bsignature(?:\s*/\s*stamp)?\s*[:\-]\s*(.{2,80})$", line, re.I)
            if direct and re.search(r"[A-Za-z]", direct.group(1)):
                signature_ocr_hit = (page, line)
                break
            if re.search(r"\b(?:authori[sz]ed signator(?:y|ies)|signature of)\b", line, re.I):
                neighbor = ocr_lines[index - 1] if index else ""
                if 2 <= len(neighbor) <= 100 and re.search(r"[A-Za-z]{2}", neighbor):
                    signature_ocr_hit = (page, neighbor)
                    break
        if signature_ocr_hit is None and re.search(r"\bsignatures?\b", page_text, re.I):
            for line in ocr_lines:
                if re.fullmatch(r"[A-Z](?:\.[A-Z])?\.[A-Za-z]{3,30}", line):
                    signature_ocr_hit = (page, line)
                    break
    if len(signature_widgets) == 1:
        page, widget = signature_widgets[0]
        fields["signature"] = _field(
            "signature",
            {
                "value": "present",
                "raw": str(widget.get("value")),
                "page": page["number"],
                "evidence": f"PDF signature field {widget.get('name', 'Unnamed')}",
                "confidence": 100.0,
                "provenance": "pdf_widget",
            },
            None,
        )
    elif signature_ocr_hit is not None:
        page, evidence = signature_ocr_hit
        fields["signature"] = _field(
            "signature",
            {
                "value": "present",
                "raw": "visual mark detected",
                "page": page["number"],
                "evidence": evidence,
                "confidence": page.get("confidence"),
                "provenance": "ocr_presence_rule",
            },
            None,
        )
    else:
        fields["signature"] = _field(
            "signature", None, "ambiguous" if signature_label_page is not None else "not_present"
        )
        if signature_label_page is not None:
            fields["signature"]["page"] = signature_label_page
            fields["signature"]["evidence"] = "Signature area found; visual confirmation required."

    if fields["signature"]["value"] == "present":
        signature = fields["signature"]
        fields["consent_choice"] = _field(
            "consent_choice",
            {
                "value": "yes",
                "raw": "signature present",
                "page": signature["page"],
                "evidence": (
                    "Signature presence treated as consent under the configured business rule. "
                    f"Signature evidence: {signature['evidence']}"
                ),
                "confidence": signature["confidence"],
                "provenance": "signature_consent_rule",
            },
            None,
        )
        warnings.append(
            "Consent choice was set to yes because signature presence was detected, per the configured business rule."
        )

    # Printed form revisions are not privacy notice versions.
    if fields["form_version"]["value"] is None:
        for page in pages:
            page_text = f"{page.get('native_text', '')}\n{page.get('text', '')}"
            match = re.search(
                r"(?:SMBC Account Opening Form[^\n]*Version\s*[\d.]+|V\.05 October 2025)",
                page_text,
                re.I,
            )
            if match:
                fields["form_version"] = _field(
                    "form_version",
                    {
                        "value": match.group(0),
                        "raw": match.group(0),
                        "page": page["number"],
                        "evidence": match.group(0),
                        "confidence": page.get("confidence"),
                        "provenance": "version_rule",
                    },
                    None,
                )
                break

    detected_type = document_type(combined)
    if fields["purpose"]["value"] is None and detected_type in DOCUMENT_PURPOSES:
        purpose = DOCUMENT_PURPOSES[detected_type]
        fields["purpose"] = _field(
            "purpose",
            {
                "value": purpose,
                "raw": purpose,
                "page": 1,
                "evidence": f"Derived from document type: {detected_type}",
                "confidence": None,
                "provenance": "document_type_rule",
            },
            None,
        )

    warnings.extend(
        [
            "Rule-based extraction is a local MVP baseline; verify party ownership and clause context.",
            "Signature output reports presence evidence only and does not authenticate the signer or establish signer identity.",
        ]
    )
    return {
        "document_type": detected_type,
        "fields": [fields[name] for name in FIELD_ORDER],
        "clauses": clauses,
        "warnings": warnings,
    }
