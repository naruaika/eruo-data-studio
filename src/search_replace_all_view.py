# search_replace_all_view.py
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


from gi.repository import GLib, GObject, Gtk
import polars
import threading

from . import globals
from .window import Window

class SearchResultListItem(GObject.Object):
    __gtype_name__ = 'SearchResultListItem'

    cname = GObject.Property(type=str, default='A1')
    cvalue = GObject.Property(type=str, default='[Blank]')

    def __init__(self, cname: str, cvalue: str):
        super().__init__()

        self.cname = cname
        self.cvalue = cvalue



_MAX_SEARCH_RESULT_ITEMS = 20_000

_search_result_list_items_pool = []

for i in range(_MAX_SEARCH_RESULT_ITEMS):
    _search_result_list_items_pool.append(SearchResultListItem('A1', '[Blank]'))



@Gtk.Template(resource_path='/com/macipra/eruo/ui/search-replace-all-view.ui')
class SearchReplaceAllView(Gtk.Box):
    __gtype_name__ = 'SearchReplaceAllView'

    search_entry = Gtk.Template.Child()
    search_status = Gtk.Template.Child()

    search_list_view = Gtk.Template.Child()
    search_list_store = Gtk.Template.Child()

    search_options = Gtk.Template.Child()

    search_match_case = Gtk.Template.Child()
    search_match_cell = Gtk.Template.Child()
    search_within_selection = Gtk.Template.Child()
    search_use_regexp = Gtk.Template.Child()

    toggle_replace = Gtk.Template.Child()
    replace_section = Gtk.Template.Child()
    replace_entry = Gtk.Template.Child()

    search_results = polars.DataFrame()
    search_results_length: int = 0

    def __init__(self, window: Window, **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window

        self.search_list_view.connect('activate', self.on_search_list_view_item_activated)

    def on_search_list_view_item_activated(self,
                                           list_view: Gtk.ListView,
                                           position:  int) -> None:
        sheet_document = self.window.get_current_active_document()

        search_range = sheet_document.selection.current_search_range

        cname = self.search_list_store.get_item(position).cname
        sheet_document.renderer.render_caches = {}
        sheet_document.update_selection_from_name(cname)

        sheet_document.selection.current_search_range = search_range

    @Gtk.Template.Callback()
    def on_search_entry_activated(self, entry: Gtk.Entry) -> None:
        text_value = self.search_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        sheet_document = self.window.get_current_active_document()

        # Reset the current search range
        if not within_selection:
            sheet_document.selection.current_search_range = None

        # Initialize the current search range
        elif sheet_document.selection.current_search_range is None:
            arange = sheet_document.selection.current_active_range
            sheet_document.selection.current_search_range = arange

        self.search_status.set_visible(True)

        if text_value == '':
            self.search_status.set_text('No results found')
            return # prevent empty search

        # Get the search results
        search_results, self.search_results_length = sheet_document.find_in_current_cells(text_value,
                                                                                          match_case,
                                                                                          match_cell,
                                                                                          within_selection,
                                                                                          use_regexp)

        if self.search_results_length == 0:
            self.search_list_store.remove_all()
            self.search_status.set_text('No results found')
            return # prevent empty search

        self.search_status.set_text(f'Found {format(self.search_results_length, ',d')} results')
        self.search_status.set_visible(True)

        if within_selection:
            sheet_document.search_range_performer = 'search-all'

        def update_search_list() -> None:
            globals.is_changing_state = True

            list_items_to_add = []
            item_counter = 0
            has_more_items = False

            # Update the search results
            for row in range(search_results.height):
                if item_counter == _MAX_SEARCH_RESULT_ITEMS:
                    has_more_items = True
                    break

                for column_name in search_results.columns:
                    if item_counter == _MAX_SEARCH_RESULT_ITEMS:
                        has_more_items = True
                        break
                    if column_name == '$ridx':
                        continue
                    if search_results[column_name][row] is False:
                        continue

                    # TODO: support multiple dataframes?
                    col_index = sheet_document.data.dfs[0].columns.index(column_name) + 1 # +1 for the $ridx column
                    row_index = search_results['$ridx'][row] + 2 # +2 for the locator and the header

                    cname = sheet_document.display.get_cell_name_from_position(col_index, row_index)
                    cvalue = str(sheet_document.data.dfs[0][column_name][row_index - 2])[:40]

                    list_item = _search_result_list_items_pool[item_counter]
                    list_item.cname = cname
                    list_item.cvalue = cvalue
                    list_items_to_add.append(list_item)

                    if item_counter == 0:
                        first_list_item = list_item
                        def update_selection():
                            search_range = sheet_document.selection.current_search_range
                            sheet_document.update_selection_from_name(first_list_item.cname)
                            sheet_document.selection.current_search_range = search_range
                        GLib.idle_add(update_selection)

                    item_counter += 1

            GLib.idle_add(self.search_list_store.splice, 0, 0, list_items_to_add)

            if has_more_items:
                GLib.idle_add(self.search_status.set_text, f'{self.search_status.get_text()}. '
                                                           f'The result set only contains a subset of all matches.')

            globals.is_changing_state = False

        self.search_list_store.remove_all()
        threading.Thread(target=update_search_list, daemon=True).start()

    @Gtk.Template.Callback()
    def on_replace_entry_activated(self, entry: Gtk.Entry) -> None:
        self.replace_all_search_occurences()

    @Gtk.Template.Callback()
    def on_search_options_toggled(self, button: Gtk.Button) -> None:
        is_active = button.get_active()
        self.search_options.set_visible(is_active)

    def open_search_view(self) -> None:
        self.window.split_view.set_collapsed(False)
        self.window.toggle_search_all.set_active(True)
        self.window.toggle_sidebar.set_active(True)

        if self.search_results_length == 0:
            self.search_status.set_visible(False)

        tab_page = self.window.search_replace_all_page
        self.window.sidebar_tab_view.set_selected_page(tab_page)

        sheet_document = self.window.get_current_active_document()

        if sheet_document is None:
            return

        sheet_document.is_searching_cells = True

        self.search_entry.grab_focus()

    def toggle_replace_section(self) -> None:
        sidebar_is_collapsed = self.window.split_view.get_collapsed()
        selected_page = self.window.sidebar_tab_view.get_selected_page()
        target_page = self.window.search_replace_all_page

        view_is_visible = not sidebar_is_collapsed and selected_page == target_page
        view_is_in_focus = self.get_focus_child()
        search_entry_in_focus = self.search_entry.get_focus_child()
        replace_section_visible = self.replace_section.get_visible()

        # Open the search view
        if not view_is_visible:
            self.open_search_view()

        # In case the user wants to jump between the search and replace entry
        if view_is_visible \
                and replace_section_visible \
                and view_is_in_focus \
                and search_entry_in_focus:
            self.toggle_replace.set_icon_name('go-down-symbolic')
            self.replace_section.set_visible(True)

            # Selects all text on the replace entry
            text_length = len(self.replace_entry.get_text())
            self.replace_entry.select_region(0, text_length)
            self.replace_entry.get_first_child().set_focus_on_click(True)
            self.replace_entry.get_first_child().grab_focus()

            self.replace_entry.grab_focus()

        # Hide the replace section and grab focus on the search entry
        elif view_is_visible \
                and replace_section_visible \
                and view_is_in_focus:
            self.toggle_replace.set_icon_name('go-next-symbolic')
            self.replace_section.set_visible(False)

            self.search_entry.grab_focus()

        # Show and grab focus on the replace entry
        else:
            self.toggle_replace.set_icon_name('go-down-symbolic')
            self.replace_section.set_visible(True)

            # Selects all text on the replace entry
            text_length = len(self.replace_entry.get_text())
            self.replace_entry.select_region(0, text_length)
            self.replace_entry.get_first_child().set_focus_on_click(True)
            self.replace_entry.get_first_child().grab_focus()

            self.replace_entry.grab_focus()

    def replace_all_search_occurences(self) -> None:
        search_pattern = self.search_entry.get_text()
        replace_with = self.replace_entry.get_text()

        match_case = self.search_match_case.get_active()
        match_cell = self.search_match_cell.get_active()
        within_selection = self.search_within_selection.get_active()
        use_regexp = self.search_use_regexp.get_active()

        sheet_document = self.window.get_current_active_document()

        # Reset the current search range
        if not within_selection:
            sheet_document.selection.current_search_range = None

        # Initialize the current search range
        elif sheet_document.selection.current_search_range is None:
            arange = sheet_document.selection.current_active_range
            sheet_document.selection.current_search_range = arange

        sheet_document.find_replace_all_in_current_cells(search_pattern,
                                                         replace_with,
                                                         match_case,
                                                         match_cell,
                                                         within_selection,
                                                         use_regexp)

        self.search_status.set_visible(False)

    def close_search_view(self) -> None:
        self.window.toggle_search_all.set_active(False)

        sheet_document = self.window.get_current_active_document()

        if sheet_document is None:
            return

        sheet_document.is_searching_cells = False

        if self.search_within_selection.get_active():
            sheet_document.search_range_performer = ''