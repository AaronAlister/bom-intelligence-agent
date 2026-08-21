import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .base import BaseBOMParser


class XMLBOMParser(BaseBOMParser):

    supported_extensions = {
        ".xml",
    }

    def parse(
        self,
        file_path: Path
    ) -> list[dict[str, Any]]:

        tree = ET.parse(file_path)
        root = tree.getroot()

        records = []

        for element in root.iter():

            tag = element.tag.split("}")[-1]

            if tag.lower() != "component":
                continue

            record = {}

            for child in element:

                if child.text is None:
                    continue

                value = child.text.strip()

                if not value:
                    continue

                child_tag = child.tag.split("}")[-1]

                record[child_tag] = value

            if record:
                records.append(record)

        return records