# sheet_manager.py
#
# Copyright 2025 Naufan Rusyda Faikar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later


from gi.repository import GObject
from typing import Any
import polars
import re

from .sheet_document import SheetDocument
from .sheet_notebook import SheetNotebook
from .sheet_view import SheetView

class SheetManager(GObject.Object):
    __gtype_name__ = 'SheetManager'

    def __init__(self) -> None:
        super().__init__()

        from time import time
        # SheetManager is highly coupled to the main window. Because we can
        # have multiple instances of the main window, we need to identify
        # each window with a unique id.
        self.sheet_id = str(int(time()))

        self.sheets: dict[int, SheetDocument | SheetNotebook] = {}
        self.sheet_counter: int = 0

    def get_sheet_names(self) -> list[str]:
        return [sheet.title for sheet in self.sheets.values()]

    def get_sheet(self, document_id: str) -> Any:
        return self.sheets.get(document_id, None)

    def create_sheet(self,
                     # The initial dataframe to display in the newly created sheet,
                     # the remaining dataframe should be loaded progressively.
                     dataframe: polars.DataFrame,
                     title:     str = None,
                     stype:     str = 'default') -> SheetView:

        def generate_new_title(title: str = None) -> str:
            if title is None:
                title = 'Sheet'
            sheet_number = 1
            for sheet_name in self.get_sheet_names():
                if match := re.match(title + r'\s+(\d+)', sheet_name):
                    sheet_number = max(sheet_number, int(match.group(1)) + 1)
            return f'{title} {sheet_number}'

        # Automatically generate the sheet title when not provided
        if title is None:
            title = generate_new_title()

        # Generate a new column name if needed
        if title in self.get_sheet_names():
            title = generate_new_title(title)

        document_id = f'{self.sheet_id}_{self.sheet_counter}'
        self.sheet_counter += 1

        if stype == 'notebook':
            sheet = SheetNotebook(self, document_id, title)
            self.sheets[document_id] = sheet
            return sheet.view

        sheet = SheetDocument(self, document_id, title, dataframe)
        self.sheets[document_id] = sheet
        return sheet.view

    def delete_sheet(self, sheet_view: SheetView) -> None:
        self.sheets.pop(sheet_view.document.document_id, None)