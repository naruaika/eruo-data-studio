# sheet_manager.py
#
# Copyright (c) 2025 Naufan Rusyda Faikar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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