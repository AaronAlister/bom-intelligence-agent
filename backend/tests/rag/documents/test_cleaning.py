from backend.app.rag.documents.cleaning import (
    clean_extracted_text,
)


def test_empty_text_returns_empty_string() -> None:
    assert clean_extracted_text("") == ""


def test_normal_text_is_preserved() -> None:
    text = (
        "TPS7A4901\n"
        "Input Voltage: 3 V to 36 V\n"
        "Output Current: 300 mA"
    )

    assert clean_extracted_text(text) == text


def test_windows_line_endings_are_normalized() -> None:
    text = (
        "Line one\r\n"
        "Line two\r\n"
        "Line three"
    )

    assert clean_extracted_text(text) == (
        "Line one\n"
        "Line two\n"
        "Line three"
    )


def test_old_mac_line_endings_are_normalized() -> None:
    text = (
        "Line one\r"
        "Line two\r"
        "Line three"
    )

    assert clean_extracted_text(text) == (
        "Line one\n"
        "Line two\n"
        "Line three"
    )


def test_null_characters_are_removed() -> None:
    text = "Input\x00 Voltage: 3 V"

    assert clean_extracted_text(text) == (
        "Input Voltage: 3 V"
    )


def test_zero_width_spaces_are_removed() -> None:
    text = "TPS7A\u200b4901"

    assert clean_extracted_text(text) == (
        "TPS7A4901"
    )


def test_non_breaking_spaces_are_normalized() -> None:
    text = "Input\u00a0Voltage: 3 V"

    assert clean_extracted_text(text) == (
        "Input Voltage: 3 V"
    )


def test_trailing_line_whitespace_is_removed() -> None:
    text = (
        "Input Voltage: 3 V   \n"
        "Output Voltage: 5 V\t\n"
        "Current: 300 mA"
    )

    assert clean_extracted_text(text) == (
        "Input Voltage: 3 V\n"
        "Output Voltage: 5 V\n"
        "Current: 300 mA"
    )


def test_repeated_blank_lines_are_collapsed() -> None:
    text = (
        "Section one\n"
        "\n"
        "\n"
        "\n"
        "Section two"
    )

    assert clean_extracted_text(text) == (
        "Section one\n\n"
        "Section two"
    )


def test_leading_and_trailing_whitespace_is_removed() -> None:
    text = (
        "  \n"
        "Input Voltage: 3 V\n"
        "Output Voltage: 5 V\n"
        "  "
    )

    assert clean_extracted_text(text) == (
        "Input Voltage: 3 V\n"
        "Output Voltage: 5 V"
    )


def test_internal_spaces_are_preserved() -> None:
    text = (
        "Parameter        Min        Typ        Max"
    )

    assert clean_extracted_text(text) == text


def test_engineering_values_are_preserved() -> None:
    text = (
        "Input Voltage: 3 V to 36 V\n"
        "Output Current: 300 mA\n"
        "Temperature: -40 C to 125 C\n"
        "Tolerance: ±2%"
    )

    assert clean_extracted_text(text) == text