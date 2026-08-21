from pathlib import Path

from backend.app.ingestion.pipeline import ingest_bom


FIXTURE_DIR = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "boms"
)

def test_ingest_valid_csv(tmp_path: Path):

    bom_file = tmp_path / "test_bom.csv"

    bom_file.write_text(
        'Mfr P/N,Mfg,Description,Qty,RefDes\n'
        'LM358DR,Texas Instruments,Dual op amp,2,"U1,U2"\n',
        encoding="utf-8",
    )

    result = ingest_bom(
        bom_file
    )

    assert result.source_format == "csv"

    assert result.total_rows == 1

    assert result.valid_rows == 1

    assert result.invalid_rows == 0

    assert len(result.components) == 1

    assert result.components[0].mpn == "LM358DR"

    assert result.components[0].quantity == 2

    assert result.components[0].reference_designators == [
        "U1",
        "U2",
    ]

def test_ingest_invalid_component(tmp_path: Path):

    bom_file = tmp_path / "invalid_bom.csv"

    bom_file.write_text(
        "MPN,Manufacturer,Quantity\n"
        "LM358DR,Texas Instruments,4\n"
        ",Texas Instruments,2\n"
        "STM32F401,STMicroelectronics,-1\n",
        encoding="utf-8",
    )

    result = ingest_bom(
        bom_file
    )

    assert result.total_rows == 3

    assert result.valid_rows == 1

    assert result.invalid_rows == 2

    assert len(result.components) == 1

    assert result.components[0].mpn == "LM358DR"

    assert len(result.validation_issues) == 2

def test_pipeline_extracts_filename_metadata():

    file_path = FIXTURE_DIR / "sample.xlsx"

    result = ingest_bom(
        file_path,
    )

    assert result.metadata is not None

    assert result.metadata.bom_id == result.bom_id

    assert (
        result.metadata.source_file
        == "sample.xlsx"
    )

    assert (
        result.metadata.source_format
        == "xlsx"
    )

    assert result.metadata.ingested_at is not None


def test_ingest_bom_missing_required_column(
    tmp_path: Path,
):

    bom_file = tmp_path / "invalid_structure.csv"

    bom_file.write_text(
        "Manufacturer,Description,Package\n"
        "Texas Instruments,Dual op amp,SOIC-8\n",
        encoding="utf-8",
    )

    result = ingest_bom(
        bom_file
    )

    assert result.total_rows == 1

    assert result.valid_rows == 0

    assert result.invalid_rows == 1

    assert result.components == []

    assert len(result.validation_issues) == 2

    assert {
        issue.field
        for issue in result.validation_issues
    } == {
        "mpn",
        "quantity",
    }

    assert all(
        issue.severity == "error"
        for issue in result.validation_issues
    )

def test_ingest_empty_bom(
    tmp_path: Path,
):

    bom_file = tmp_path / "empty_bom.csv"

    bom_file.write_text(
        "",
        encoding="utf-8",
    )

    result = ingest_bom(
        bom_file
    )

    assert result.total_rows == 0

    assert result.valid_rows == 0

    assert result.invalid_rows == 0

    assert result.components == []

    assert result.validation_issues == []

def test_ingest_bom_ambiguous_required_column(
    tmp_path: Path,
):

    bom_file = tmp_path / "ambiguous_bom.csv"

    bom_file.write_text(
        "Part Number,Manufacturer Part Number,Quantity\n"
        "LM358DR,LM358DR,4\n",
        encoding="utf-8",
    )

    result = ingest_bom(
        bom_file
    )

    assert result.total_rows == 1

    assert result.valid_rows == 0

    assert result.invalid_rows == 1

    assert result.components == []

    assert len(result.validation_issues) == 1

    issue = result.validation_issues[0]

    assert issue.field == "mpn"

    assert issue.severity == "error"

    assert "ambiguous" in issue.message.lower()

def test_ingest_bom_invalid_quantity_values(
    tmp_path: Path,
):

    bom_file = tmp_path / "invalid_quantities.csv"

    bom_file.write_text(
        "MPN,Quantity\n"
        "LM358DR,4.5\n"
        "STM32F401,abc\n"
        "GRM188R71C104KA01D,0\n"
        "RC0603FR-0710KL,-5\n",
        encoding="utf-8",
    )

    result = ingest_bom(
        bom_file
    )

    assert result.total_rows == 4

    assert result.valid_rows == 0

    assert result.invalid_rows == 4

    assert result.components == []

    quantity_issues = [
        issue
        for issue in result.validation_issues
        if issue.field == "quantity"
    ]

    assert len(quantity_issues) == 4

    assert all(
        issue.severity == "error"
        for issue in quantity_issues
    )

def test_ingest_bom_blank_required_header(
    tmp_path: Path,
):

    bom_file = tmp_path / "blank_header.csv"

    bom_file.write_text(
        ",Quantity,Manufacturer\n"
        "LM358DR,4,Texas Instruments\n",
        encoding="utf-8",
    )

    result = ingest_bom(
        bom_file
    )

    assert result.total_rows == 1

    assert result.valid_rows == 0

    assert result.invalid_rows == 1

    assert result.components == []

    assert len(result.validation_issues) == 1

    issue = result.validation_issues[0]

    assert issue.field == "mpn"

    assert issue.severity == "error"