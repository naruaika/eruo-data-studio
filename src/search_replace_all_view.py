# search_replace_all_view.py
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

        def update_search_list() -> None:
            globals.is_changing_state = True

            item_counter = 0
            has_more_items = False

            MAX_SEARCH_RESULT_ITEMS = 10_000

            # Update the search results
            for row in range(search_results.height):
                if item_counter == MAX_SEARCH_RESULT_ITEMS:
                    has_more_items = True
                    break

                for column_name in search_results.columns:
                    if item_counter == MAX_SEARCH_RESULT_ITEMS:
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

                    list_item = SearchResultListItem(cname, cvalue)

                    if item_counter == 0:
                        first_list_item = list_item
                        def update_selection():
                            search_range = sheet_document.selection.current_search_range
                            sheet_document.update_selection_from_name(first_list_item.cname)
                            sheet_document.selection.current_search_range = search_range
                        GLib.idle_add(update_selection)
                    item_counter += 1

                    GLib.idle_add(self.search_list_store.append, list_item)

            if has_more_items:
                # TODO: should we really show all the results? If so, we can process it in a different thread,
                #       and append it to the store using GLib.idle_add(), maybe?
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

        sheet_document.replace_all_in_current_cells(search_pattern,
                                                    replace_with,
                                                    match_case,
                                                    match_cell,
                                                    within_selection,
                                                    use_regexp)

        self.search_status.set_visible(False)

    def close_search_view(self) -> None:
        self.window.toggle_search_all.set_active(False)

        sheet_document = self.window.get_current_active_document()
        sheet_document.is_searching_cells = False