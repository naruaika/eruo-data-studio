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
                     stype:     str = 'worksheet') -> SheetView:

        # Automatically generate the sheet title when not provided
        if title is None:
            title = self.generate_sheet_name()

        # Generate a new column name if needed
        if title in self.get_sheet_names():
            title = self.generate_sheet_name(title)

        document_id = f'{self.sheet_id}_{self.sheet_counter}'
        self.sheet_counter += 1

        if stype == 'notebook':
            sheet = SheetNotebook(self, document_id, title)
        if stype == 'worksheet':
            sheet = SheetDocument(self, document_id, title, dataframe)

        self.sheets[document_id] = sheet
        return sheet.view

    def duplicate_sheet(self, document_id: str) -> SheetView:
        target_sheet = self.get_sheet(document_id)

        title = target_sheet.title
        title = self.generate_sheet_name(title)

        document_id = f'{self.sheet_id}_{self.sheet_counter}'
        self.sheet_counter += 1

        if isinstance(target_sheet, SheetNotebook):
            new_sheet = SheetNotebook(self, document_id, title)

            new_sheet.is_searching_cells     = target_sheet.is_searching_cells
            new_sheet.search_range_performer = target_sheet.search_range_performer

            for list_item in target_sheet.view.list_items:
                source_view = list_item['source_view']

                text_buffer = source_view.get_buffer()
                start_iter = text_buffer.get_start_iter()
                end_iter = text_buffer.get_end_iter()
                query = text_buffer.get_text(start_iter, end_iter, True)

                new_sheet.view.add_new_sql_cell(query)

        if isinstance(target_sheet, SheetDocument):
            dataframe = target_sheet.data.dfs[0]
            configs = target_sheet.configs

            new_sheet = SheetDocument(self, document_id, title, dataframe, configs)

            new_sheet.is_searching_cells      = target_sheet.is_searching_cells
            new_sheet.search_range_performer  = target_sheet.search_range_performer
            new_sheet.current_dfi             = target_sheet.current_dfi
            new_sheet.pending_sorts           = target_sheet.pending_sorts
            new_sheet.current_sorts           = target_sheet.current_sorts
            new_sheet.pending_filters         = target_sheet.pending_filters
            new_sheet.current_filters         = target_sheet.current_filters

            new_sheet.data.bbs                = target_sheet.data.bbs
            new_sheet.data.dfs                = target_sheet.data.dfs
            new_sheet.data.has_main_dataframe = target_sheet.data.has_main_dataframe

            new_sheet.renderer.render_caches  = target_sheet.renderer.render_caches

            new_sheet.display.left_locator_width       = target_sheet.display.left_locator_width
            new_sheet.display.top_locator_height       = target_sheet.display.top_locator_height
            new_sheet.display.scroll_increment         = target_sheet.display.scroll_increment
            new_sheet.display.page_increment           = target_sheet.display.page_increment
            new_sheet.display.scroll_y_position        = target_sheet.display.scroll_y_position
            new_sheet.display.scroll_x_position        = target_sheet.display.scroll_x_position
            new_sheet.display.row_visibility_flags     = target_sheet.display.row_visibility_flags
            new_sheet.display.column_visibility_flags  = target_sheet.display.column_visibility_flags
            new_sheet.display.row_visible_series       = target_sheet.display.row_visible_series
            new_sheet.display.column_visible_series    = target_sheet.display.column_visible_series
            new_sheet.display.row_heights              = target_sheet.display.row_heights
            new_sheet.display.column_widths            = target_sheet.display.column_widths
            new_sheet.display.cumulative_row_heights   = target_sheet.display.cumulative_row_heights
            new_sheet.display.cumulative_column_widths = target_sheet.display.cumulative_column_widths

            new_sheet.selection.cell_name              = target_sheet.selection.cell_name
            new_sheet.selection.cell_data              = target_sheet.selection.cell_data
            new_sheet.selection.cell_dtype             = target_sheet.selection.cell_dtype
            new_sheet.selection.current_active_range   = target_sheet.selection.current_active_range
            new_sheet.selection.previous_active_range  = target_sheet.selection.previous_active_range
            new_sheet.selection.current_active_cell    = target_sheet.selection.current_active_cell
            new_sheet.selection.current_cursor_cell    = target_sheet.selection.current_cursor_cell
            new_sheet.selection.current_search_range   = target_sheet.selection.current_search_range

            new_sheet.setup_document()

        self.sheets[document_id] = new_sheet
        return new_sheet.view

    def delete_sheet(self, sheet_view: SheetView) -> None:
        self.sheets.pop(sheet_view.document.document_id, None)

    def generate_sheet_name(self, sheet_name: str = None) -> str:
        # Use the default sheet name if needed
        if sheet_name is None:
            sheet_name = 'Sheet'

        # Remove the number suffix if present
        new_name = re.sub(r'\s+(\d+)$', '', sheet_name)

        # Determine a new sheet name
        sheet_number = 1
        for sheet_name in self.get_sheet_names():
            if match := re.match(new_name + r'\s+(\d+)', sheet_name):
                sheet_number = max(sheet_number, int(match.group(1)) + 1)

        return f'{new_name} {sheet_number}'