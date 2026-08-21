from pathlib import Path
from typing import Any

import pandas as pd

from .base import BaseBOMParser


class ExcelBOMParser(BaseBOMParser):

    supported_extensions = {
        ".xlsx",
        ".xls",
    }

    def parse(
        self,
        file_path: Path
    ) -> list[dict[str, Any]]:

        dataframe = pd.read_excel(
            file_path
        )

        dataframe = dataframe.where(
            dataframe.notna(),
            None
        )

        records = dataframe.to_dict(
            orient="records"
        )

        return [
            {
                str(key): value
                for key, value in record.items()
            }
            for record in records
        ]