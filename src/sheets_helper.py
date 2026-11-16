import json
import os
from typing import Any

import gspread


class SheetsHelper:
    def __init__(
        self,
        credentials_json: str | None = None,
        sheet_id: str | None = None,
        worksheet_name: str | None = None,
    ) -> None:
        credentials = json.loads(
            credentials_json or os.environ["GOOGLE_CREDENTIALS_JSON"]
        )
        client = gspread.service_account_from_dict(credentials)
        spreadsheet = client.open_by_key(sheet_id or os.environ["GOOGLE_SHEET_ID"])
        worksheet_name = (
            worksheet_name
            if worksheet_name is not None
            else os.getenv("GOOGLE_SHEET_WORKSHEET", "").strip()
        )
        self.worksheet = (
            spreadsheet.worksheet(worksheet_name)
            if worksheet_name
            else spreadsheet.sheet1
        )

    def append_expense(self, expense: dict[str, Any], sender: str) -> None:
        row = [
            expense.get("date", ""),
            expense.get("property", ""),
            expense.get("description", ""),
            expense.get("category", ""),
            expense.get("amount", ""),
            expense.get("currency", "BRL"),
            sender,
        ]
        self.worksheet.append_row(row, value_input_option="USER_ENTERED")
