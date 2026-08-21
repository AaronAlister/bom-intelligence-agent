import re
from dataclasses import dataclass
from typing import Optional


COLUMN_ALIASES = {
    "mpn": {
        "mpn",
        "part number",
        "part no",
        "part",
        "part #",
        "part number #",
        "manufacturer part number",
        "manufacturer part no",
        "manufacturer part #",
        "mfr part number",
        "mfr part no",
        "mfr part #",
        "mfr p n",
        "mfr p/n",
        "mfg part number",
        "mfg part no",
        "mfg part #",
        "mfg p n",
        "mfg p/n",
        "item code",
        "item number",
        "item no",
    },

    "manufacturer": {
        "manufacturer",
        "mfr",
        "mfg",
        "maker",
        "brand",
        "vendor",
    },

    "description": {
        "description",
        "desc",
        "part description",
        "component description",
        "item description",
        "component desc",
    },

    "category": {
        "category",
        "component category",
        "part category",
        "component type",
        "part type",
        "type",
    },

    "package": {
        "package",
        "package type",
        "package name",
        "case",
        "case style",
        "footprint",
    },

    "quantity": {
        "quantity",
        "qty",
        "count",
        "required quantity",
        "required qty",
        "req qty",
        "number required",
    },

    "reference_designators": {
        "reference",
        "references",
        "ref",
        "refdes",
        "ref des",
        "reference designator",
        "reference designators",
        "component reference",
        "component references",
    },
}

@dataclass
class ColumnCandidate:
    field: str
    column: str
    score: float


@dataclass
class ColumnDetection:
    field: str
    column: Optional[str]
    confidence: float
    ambiguous: bool
    candidates: list[ColumnCandidate]

def score_column(
    column: str,
    field: str,
) -> float:
    """
    Calculate how strongly a source column matches
    a canonical BOM field.
    """

    normalized_column = normalize_column_name(
        column
    )

    aliases = {
        normalize_column_name(alias)
        for alias in COLUMN_ALIASES[field]
    }

    if normalized_column in aliases:
        return 1.0

    # Partial token overlap.
    column_tokens = set(
        normalized_column.split()
    )

    best_score = 0.0

    for alias in aliases:

        alias_tokens = set(
            alias.split()
        )

        if not alias_tokens:
            continue

        overlap = (
            len(column_tokens & alias_tokens)
            / len(alias_tokens)
        )

        best_score = max(
            best_score,
            overlap,
        )

    return best_score

def detect_columns_with_confidence(
    columns: list[str],
    confidence_threshold: float = 0.75,
    ambiguity_margin: float = 0.10,
) -> dict[str, ColumnDetection]:
    """
    Detect BOM columns with confidence and ambiguity information.

    Each source column can normally be assigned to only one
    canonical BOM field.
    """

    results: dict[str, ColumnDetection] = {}

    used_columns: set[str] = set()

    for field in COLUMN_ALIASES:

        candidates: list[ColumnCandidate] = []

        for column in columns:

            score = score_column(
                column,
                field,
            )

            if score > 0:
                candidates.append(
                    ColumnCandidate(
                        field=field,
                        column=column,
                        score=score,
                    )
                )

        candidates.sort(
            key=lambda candidate: candidate.score,
            reverse=True,
        )

        # No candidates found.
        if not candidates:

            results[field] = ColumnDetection(
                field=field,
                column=None,
                confidence=0.0,
                ambiguous=False,
                candidates=[],
            )

            continue

        # Remove columns that have already been assigned
        # to another canonical field.
        available_candidates = [
            candidate
            for candidate in candidates
            if candidate.column not in used_columns
        ]

        if not available_candidates:

            results[field] = ColumnDetection(
                field=field,
                column=None,
                confidence=0.0,
                ambiguous=False,
                candidates=candidates,
            )

            continue

        best = available_candidates[0]

        ambiguous = False

        if len(available_candidates) > 1:

            second = available_candidates[1]

            if (
                best.score >= confidence_threshold
                and (
                    best.score - second.score
                    < ambiguity_margin
                )
            ):
                ambiguous = True

        if best.score < confidence_threshold:

            results[field] = ColumnDetection(
                field=field,
                column=None,
                confidence=best.score,
                ambiguous=False,
                candidates=candidates,
            )

            continue

        results[field] = ColumnDetection(
            field=field,
            column=best.column,
            confidence=best.score,
            ambiguous=ambiguous,
            candidates=candidates,
        )

        used_columns.add(
            best.column
        )

    return results

def normalize_column_name(name: str) -> str:
    """
    Normalize a column name so that variations in
    capitalization, punctuation and spacing don't
    prevent matching.
    """

    name = str(name).lower().strip()

    name = name.replace("/", " ")
    name = name.replace("#", " number ")

    name = re.sub(
        r"[^a-z0-9]+",
        " ",
        name,
    )

    return " ".join(name.split())


def detect_columns(
    columns: list[str],
) -> dict[str, Optional[str]]:
    """
    Map canonical BOM fields to the original column names.
    """

    detected: dict[str, Optional[str]] = {
        field: None
        for field in COLUMN_ALIASES
    }

    normalized_columns = {
        column: normalize_column_name(column)
        for column in columns
    }

    normalized_aliases = {
        field: {
            normalize_column_name(alias)
            for alias in aliases
        }
        for field, aliases in COLUMN_ALIASES.items()
    }

    for original_column, normalized_column in normalized_columns.items():

        for field, aliases in normalized_aliases.items():

            if normalized_column in aliases:
                detected[field] = original_column
                break

    return detected