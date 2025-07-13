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
import polars
import re

from .sheet_document import SheetDocument
from .sheet_view import SheetView

class SheetManager(GObject.Object):
    __gtype_name__ = 'SheetManager'

    def __init__(self) -> None:
        super().__init__()

        self.sheets: dict[int, SheetDocument] = {}
        self.sheet_counter: int = 0

    def get_sheet_names(self) -> list[str]:
        return [sheet.title for sheet in self.sheets.values()]

    def create_sheet(self, dataframe: polars.DataFrame, title: str = None) -> SheetView:
        if title is None:
            sheet_number = 1
            for sheet_name in self.get_sheet_names():
                if match := re.match(r'Sheet\s+(\d+)', sheet_name):
                    sheet_number = max(sheet_number, int(match.group(1)) + 1)
            title = f'Sheet {sheet_number}'

        did = self.sheet_counter
        self.sheet_counter += 1

        sheet = SheetDocument(did, title, dataframe)
        self.sheets[did] = sheet

        return sheet.view

    def delete_sheet(self, sheet_view: SheetView) -> None:
        self.sheets.pop(sheet_view.document.did)