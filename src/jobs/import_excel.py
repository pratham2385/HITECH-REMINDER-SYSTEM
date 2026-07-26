"""CLI job for importing an Excel workbook into the dashboard database."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.config.settings import load_settings
from src.db.session import db_session, init_database
from src.services.excel_importer import ExcelImportService
from src.utils.logger import setup_logging


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(description="Import an Excel workbook into dashboard modules.")
    parser.add_argument(
        "workbook",
        nargs="?",
        help="Path to the workbook. Defaults to EXCEL_PATH or data/Accountant_TODO.xlsx.",
    )
    parser.add_argument(
        "--skip-activities",
        action="store_true",
        help="Import sheets as modules only, without creating reminder activities.",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    """Import a workbook into the dashboard database."""

    settings = load_settings()
    logger = setup_logging(settings.log_dir)
    args = build_parser().parse_args(argv)
    workbook_path = Path(args.workbook).expanduser() if args.workbook else settings.excel_path

    logger.info("Excel import started | workbook=%s", workbook_path)
    try:
        if not workbook_path.exists() or not workbook_path.is_file():
            logger.error("Workbook not found: %s", workbook_path)
            return 1

        init_database(settings)
        importer = ExcelImportService(settings.upload_dir)
        stored_path = importer.save_uploaded_file(workbook_path.name, workbook_path)

        with db_session(settings) as session:
            pending = importer.create_pending_import(session, workbook_path.name, stored_path, None)
            importer.import_workbook(
                session,
                pending,
                import_activity_sheets=not args.skip_activities,
            )
            logger.info(
                "Excel import finished | import_id=%s | sheets=%s | rows=%s",
                pending.id,
                pending.sheet_count,
                pending.row_count,
            )
        return 0
    except Exception:
        logger.exception("Excel import failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())

