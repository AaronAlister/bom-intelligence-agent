import re


def clean_extracted_text(text: str) -> str:
    """
    Conservatively clean text extracted from an engineering PDF.

    Cleaning is intentionally limited to extraction noise.

    The function:
    - normalizes line endings
    - removes null characters
    - removes zero-width spaces
    - converts non-breaking spaces to regular spaces
    - removes trailing whitespace from lines
    - removes leading/trailing whitespace from the document
    - collapses repeated blank lines

    Technical content, numbers, units, punctuation, and
    internal line spacing are otherwise preserved.
    """

    if not text:
        return ""

    cleaned = text.replace(
        "\r\n",
        "\n",
    )

    cleaned = cleaned.replace(
        "\r",
        "\n",
    )

    cleaned = cleaned.replace(
        "\x00",
        "",
    )

    cleaned = cleaned.replace(
        "\u200b",
        "",
    )

    cleaned = cleaned.replace(
        "\u00a0",
        " ",
    )

    lines = cleaned.split("\n")

    normalized_lines = [
        line.rstrip()
        for line in lines
    ]

    cleaned = "\n".join(
        normalized_lines
    )

    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned,
    )

    return cleaned.strip()