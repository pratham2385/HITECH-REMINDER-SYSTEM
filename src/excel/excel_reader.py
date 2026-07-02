"""Excel reader for activity workbooks."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

from src.models import Activity
from src.utils.helpers import clean_string


REQUIRED_COLUMNS: Final[set[str]] = {"Activity", "Frequency", "Date"}


class ExcelReaderError(Exception):
    """Raised when the Excel workbook cannot be loaded or validated."""


class ExcelActivityReader:
    """Loads and validates reminder activities from an Excel workbook."""

    def __init__(self, excel_path: Path, logger: logging.Logger) -> None:
        self.excel_path = excel_path
        self.logger = logger

    def load_activities(self) -> list[Activity]:
        """Read the workbook and return cleaned activity records."""

        if pd is None:
            raise ExcelReaderError(
                "Missing required dependency: pandas. Run `pip install -r requirements.txt`."
            )

        if not self.excel_path.exists():
            raise ExcelReaderError(f"Excel file not found: {self.excel_path}")

        if not self.excel_path.is_file():
            raise ExcelReaderError(f"Excel path is not a file: {self.excel_path}")

        try:
            dataframe = pd.read_excel(self.excel_path, engine="openpyxl")
        except PermissionError as exc:
            raise ExcelReaderError(
                f"Permission denied while reading Excel file: {self.excel_path}"
            ) from exc
        except ValueError as exc:
            raise ExcelReaderError(f"Invalid or unsupported Excel file: {exc}") from exc
        except Exception as exc:
            raise ExcelReaderError(f"Unable to read Excel file: {exc}") from exc

        missing_columns = REQUIRED_COLUMNS.difference(dataframe.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ExcelReaderError(f"Missing required Excel columns: {missing}")

        activities: list[Activity] = []
        for index, row in dataframe.iterrows():
            row_number = int(index) + 2
            activity_name = clean_string(row.get("Activity"))
            frequency = clean_string(row.get("Frequency"))
            date_value = row.get("Date")

            if not activity_name and not frequency and clean_string(date_value) == "":
                self.logger.warning("Skipping blank row %s", row_number)
                continue

            if not activity_name:
                self.logger.warning("Skipping row %s because Activity is blank", row_number)
                continue

            if not frequency:
                self.logger.warning("Skipping row %s because Frequency is blank", row_number)
                continue

            activities.append(
                Activity(
                    activity=activity_name,
                    frequency=frequency,
                    date_value=date_value,
                    row_number=row_number,
                )
            )

        self.logger.info("Excel Loaded | rows=%s | valid_activities=%s", len(dataframe), len(activities))
        return activities
