# sheet_notebook.py
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
import duckdb

from .clipboard_manager import ClipboardManager
from .sheet_functions import register_sql_functions

class SheetNotebook(GObject.Object):
    __gtype_name__ = 'SheetNotebook'

    document_id = GObject.Property(type=str, default='sheet_1')
    title = GObject.Property(type=str, default='Sheet 1')

    def __init__(self,
                 sheet_manager,
                 document_id: str,
                 title:       str) -> None:
        super().__init__()

        self.sheet_manager = sheet_manager

        self.document_id = document_id
        self.title = title

        from .sheet_notebook_view import SheetNotebookView
        self.view = SheetNotebookView(self)

        from .sheet_data import SheetData
        self.data = SheetData(self, None)

        # See the explanation in SheetDocument
        self.is_searching_cells: bool = False
        self.search_range_performer: str = ''

        # We don't use all objects below, they're just placeholders
        # so that it doesn't break the current design. Let's flag
        # this as TODO.

        from .sheet_widget import SheetWidget
        self.widgets: list[SheetWidget] = []

        from .history_manager import HistoryManager
        self.history = HistoryManager(self)

        from .sheet_display import SheetDisplay
        from .sheet_renderer import SheetRenderer
        from .sheet_selection import SheetSelection

        self.display = SheetDisplay(self)
        self.renderer = SheetRenderer(self)
        self.selection = SheetSelection(self)

    def run_sql_query(self, query: str) -> Any:
        connection = duckdb.connect()

        # Register all the main dataframes
        # FIXME: this process takes 0.2-0.3 seconds
        for sheet in self.sheet_manager.sheets.values():
            if sheet.data.has_main_dataframe:
                connection.register(sheet.title, sheet.data.dfs[0])

        register_sql_functions(connection)

        try:
            dataframe = connection.sql(query).pl()
            connection.close()
            return dataframe
        except Exception as e:
            print(e)
            message = str(e)
        connection.close()
        return message

    def cut_from_current_selection(self, clipboard: ClipboardManager) -> None:
        pass

    def copy_from_current_selection(self, clipboard: ClipboardManager) -> None:
        pass

    def paste_into_current_selection(self,
                                     clipboard: ClipboardManager,
                                     content:   Any) -> None:
        pass

    # We don't use all functions below, they're just placeholders
    # so that it doesn't break the current design. Let's flag
    # this as TODO.

    def update_current_cells(self, new_value: Any) -> bool:
        pass

    def find_in_current_cells(self,
                              text_value:       str,
                              match_case:       bool,
                              match_cell:       bool,
                              within_selection: bool,
                              use_regexp:       bool) -> int:
        pass

    def find_replace_in_current_cells(self,
                                      replace_with:   str,
                                      search_pattern: str,
                                      match_case:     bool) -> bool:
        pass

    def find_replace_all_in_current_cells(self,
                                          search_pattern: str,
                                          replace_with: str,
                                          match_case: bool,
                                          match_cell: bool,
                                          within_selection: bool,
                                          use_regexp: bool) -> None:
        pass

    def notify_selection_changed(self, column: int, row: int, metadata) -> None:
        pass

    def notify_selected_table_changed(self, force: bool = False) -> None:
        pass

    def repopulate_auto_filter_widgets(self) -> None:
        pass

    def auto_adjust_scrollbars_by_selection(self,
                                            follow_cursor: bool = True,
                                            scroll_axis:   str = 'both',
                                            with_offset:   bool = False,
                                            smooth_scroll: bool = False) -> None:
        pass

    def auto_adjust_locators_size_by_scroll(self) -> None:
        pass

    def auto_adjust_selections_by_scroll(self) -> None:
        pass