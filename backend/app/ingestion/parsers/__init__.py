from .csv_parser import CSVBOMParser
from .excel_parser import ExcelBOMParser
from .json_parser import JSONBOMParser
from .xml_parser import XMLBOMParser


PARSERS = [
    CSVBOMParser(),
    ExcelBOMParser(),
    XMLBOMParser(),
    JSONBOMParser(),
]


def get_parser(extension: str):

    extension = extension.lower()

    for parser in PARSERS:

        if parser.supports(extension):
            return parser

    raise ValueError(
        f"Unsupported BOM file format: {extension}"
    )