# sheet_notebook.py
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
import duckdb

from . import globals
from .clipboard_manager import ClipboardManager
from .sheet_functions import register_sql_functions

class SheetNotebook(GObject.Object):
    __gtype_name__ = 'SheetNotebook'

    document_id = GObject.Property(type=str, default='sheet_1')
    title = GObject.Property(type=str, default='Sheet 1')

    def __init__(self,
                 sheet_manager       = None,
                 document_id:   str  = '',
                 title:         str  = '',
                 configs:       dict = {}) -> None:
        super().__init__()

        self.sheet_manager = sheet_manager

        self.document_id = document_id
        self.title = title

        from .history_manager import HistoryManager
        self.history = HistoryManager(self)

        from .sheet_notebook_view import SheetNotebookView
        self.view = SheetNotebookView(self)

        # See the explanation in SheetDocument
        self.is_searching_cells: bool = False
        self.search_range_performer: str = ''

    def run_sql_query(self, query: str) -> Any:
        connection = duckdb.connect()

        # Register all the data sources
        connection_strings = globals.register_connection(connection)
        query = connection_strings + query

        register_sql_functions(connection)

        try:
            result = connection.sql(query)

            if result is not None:
                result = result.pl()
            else:
                result = 'Query executed successfully'

            connection.close()
            return result

        except Exception as e:
            print(e)
            message = str(e).strip('\n')

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