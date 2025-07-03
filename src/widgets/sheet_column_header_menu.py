# sheet_column_header_menu.py
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

import polars
import threading

from gi.repository import Adw, Gdk, GLib, Gtk

from ..dbms import DBMS
from ..utils import print_log, Log

@Gtk.Template(resource_path='/com/macipra/Eruo/gtk/sheet-column-header-menu.ui')
class SheetColumnHeaderMenu(Gtk.PopoverMenu):
    __gtype_name__ = 'SheetColumnHeaderMenu'

    quick_statistics = Gtk.Template.Child()
    filter_placeholder = Gtk.Template.Child()
    filter_searchentry = Gtk.Template.Child()
    filter_scrolledwindow = Gtk.Template.Child()
    filter_spinner = Gtk.Template.Child()
    filter_listbox = Gtk.Template.Child()

    _colid: str
    _dbms: DBMS

    _is_filter_ready: bool = False

    def __init__(self, colid: int, dbms: DBMS, **kwargs) -> None:
        """Creates a new SheetColumnHeaderMenu."""
        super().__init__(**kwargs)

        self._colid = str(colid)
        self._dbms = dbms

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_filter_searchentry_key_pressed)
        self.filter_searchentry.add_controller(key_event_controller)

    def do_hide(self) -> None:
        """Callback function for when the popover menu is hidden."""
        self._colid = -1
        return Gtk.PopoverMenu.do_hide(self)

    def on_filter_searchentry_key_pressed(self, event: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> None:
        if keyval == Gdk.KEY_Escape:
            self.filter_listbox.grab_focus()

    @Gtk.Template.Callback()
    def on_filter_searchentry_changed(self, widget: Gtk.Widget) -> None:
        """Updates the filter options when the filter search entry is changed."""
        # Prevent the callback from being called when the first time the popover menu is shown
        if not self._is_filter_ready:
            self._is_filter_ready = True
            return

        self.filter_scrolledwindow.get_vadjustment().set_value(0)
        self.filter_listbox.remove_all()
        self.filter_spinner.show()

        col_name = self._dbms.get_column(int(self._colid))
        query = widget.get_text()
        print_log(f'Searching for \'{query}\' in column {col_name}...', Log.DEBUG)
        threading.Thread(target=self.populate_filters, args=(query,), daemon=True).start()

    def set_colid(self, colid: int) -> None:
        """Sets the colid for the SheetColumnHeaderMenu."""
        self._colid = str(colid)

    def prepare_ui(self) -> None:
        """Prepares the UI for the SheetColumnHeaderMenu."""
        self.filter_searchentry.set_text('')
        self.filter_searchentry.set_placeholder_text('Loading...')
        self.filter_scrolledwindow.get_vadjustment().set_value(0)
        self.filter_listbox.remove_all()
        self._dbms.pending_values_to_show = ['meta:all']
        self._dbms.pending_values_to_hide = []

        col_dtype = self._dbms.get_dtype(int(self._colid))
        if col_dtype not in [polars.Boolean, polars.Int8, polars.Int16, polars.Int32, polars.Int64, polars.UInt8,
                             polars.UInt16, polars.UInt32, polars.UInt64, polars.Float32, polars.Float64, polars.Decimal,
                             polars.Utf8, polars.Categorical, polars.Date,polars.Time, polars.Datetime]:
            self.action_set_enabled('app.sheet.column.apply-filter', False)
            self.filter_placeholder.show()
            self.filter_spinner.hide()
            return

        self.filter_placeholder.hide()
        self.filter_spinner.show()
        threading.Thread(target=self.populate_filters, daemon=True).start()

        green_color = '#008000'
        orange_color = '#FF8000'
        if Adw.StyleManager().get_dark():
            green_color = '#00B300'
            orange_color = '#E66000'
        col_name = self._dbms.get_column(int(self._colid))
        fill_count = self._dbms.fill_counts[int(self._colid)]

        # Show quick statistics
        if self._dbms.data_frame[col_name].dtype.is_numeric():
            description = self._dbms.data_frame[col_name].describe()
            str_format = ',.2f'
            if self._dbms.data_frame[col_name].dtype.is_integer():
                description = description.with_columns(polars.col('value').cast(polars.Int16))
                str_format = ',d'
            self.quick_statistics.set_label(f'<span color="{green_color}" weight="bold">Count:</span> {format(fill_count, ",d")}\n'
                                            f'<span color="{orange_color}" weight="bold">Missing:</span> {format(self._dbms.data_frame.shape[0] - fill_count, ",d")}\n'
                                            f'<b>Minimum:</b> {format(description[4, "value"], str_format)}\n'
                                            f'<b>Median:</b> {format(description[6, "value"], str_format)}\n'
                                            f'<b>Maximum:</b> {format(description[8, "value"], str_format)} ')
            print_log(f'Quick preview of the column {col_name}: {description}', Log.DEBUG)
        else:
            self.quick_statistics.set_label(f'<span color="{green_color}" weight="bold">Count:</span> {format(fill_count, ",d")}\n'
                                            f'<span color="{orange_color}" weight="bold">Missing:</span> {format(self._dbms.data_frame.shape[0] - fill_count, ",d")}')

    def populate_filters(self, query: str | None = None) -> None:
        """Populates the filter options for the SheetColumnHeaderMenu."""
        def on_check_button_toggled(widget: Gtk.Widget, is_meta: bool) -> None:
            """
            Callback function for when a check button is toggled.

            Args:
                check_button (Gtk.CheckButton): The check button that was toggled.
            """
            is_active = widget.get_active()
            select_all = self.filter_listbox.get_row_at_index(0).get_first_child()

            def post_process() -> None:
                """Post-processes the SheetColumnHeaderMenu after the check button is toggled."""
                is_consistent = False

                select_all.handler_block_by_func(on_check_button_toggled)
                if 'meta:all' in self._dbms.pending_values_to_show and len(self._dbms.pending_values_to_hide) == 0:
                    self._dbms.pending_values_to_show = ['meta:all']
                    self._dbms.pending_values_to_hide = []
                    select_all.set_active(True)
                    is_consistent = True
                elif 'meta:all' in self._dbms.pending_values_to_hide and len(self._dbms.pending_values_to_show) == 0:
                    self._dbms.pending_values_to_show = []
                    self._dbms.pending_values_to_hide = ['meta:all']
                    select_all.set_active(False)
                    is_consistent = True
                else:
                    values_to_show = list(set(self._dbms.pending_values_to_show) - {'meta:blank'})
                    values_to_hide = list(set(self._dbms.pending_values_to_hide) - {'meta:blank'})
                    values_to_show_hash = polars.Series(values_to_show).sort().hash()
                    values_to_hide_hash = polars.Series(values_to_hide).sort().hash()
                    if 'meta:all' in values_to_show and values_to_hide_hash.equals(self._dbms.current_unique_values_hash):
                        self._dbms.pending_values_to_show = []
                        self._dbms.pending_values_to_hide = ['meta:all']
                        select_all.set_active(False)
                        is_consistent = True
                    elif 'meta:all' in values_to_hide and values_to_show_hash.equals(self._dbms.current_unique_values_hash):
                        self._dbms.pending_values_to_show = ['meta:all']
                        self._dbms.pending_values_to_hide = []
                        select_all.set_active(True)
                        is_consistent = True
                select_all.handler_unblock_by_func(on_check_button_toggled)

                if len(self._dbms.pending_values_to_show) == 0:
                    self.action_set_enabled('app.sheet.column.apply-filter', False)
                else:
                    self.action_set_enabled('app.sheet.column.apply-filter', True)
                select_all.set_inconsistent(not is_consistent)

            if is_meta and widget.filter_value == 'meta:all':
                if is_active:
                    self._dbms.pending_values_to_show = ['meta:all']
                    self._dbms.pending_values_to_hide = []
                else:
                    self._dbms.pending_values_to_show = []
                    self._dbms.pending_values_to_hide = ['meta:all']

                index = 1
                widget = self.filter_listbox.get_row_at_index(index).get_first_child()
                while widget:
                    if hasattr(widget, 'is_placeholder'):
                        break
                    widget.handler_block_by_func(on_check_button_toggled)
                    widget.set_active(is_active)
                    widget.handler_unblock_by_func(on_check_button_toggled)
                    index += 1
                    listboxrow = self.filter_listbox.get_row_at_index(index)
                    widget = listboxrow.get_first_child() if listboxrow else None

                select_all.set_inconsistent(False)
                self.action_set_enabled('app.sheet.column.apply-filter', is_active)

            elif is_meta and widget.filter_value == 'meta:all-result':
                index = 1
                widget = self.filter_listbox.get_row_at_index(index).get_first_child()
                while widget:
                    if hasattr(widget, 'is_placeholder'):
                        break
                    if is_active:
                        self._dbms.pending_values_to_show.append(widget.filter_value)
                        if widget.filter_value in self._dbms.pending_values_to_hide:
                            self._dbms.pending_values_to_hide.remove(widget.filter_value)
                    else:
                        self._dbms.pending_values_to_hide.append(widget.filter_value)
                        if widget.filter_value in self._dbms.pending_values_to_show:
                            self._dbms.pending_values_to_show.remove(widget.filter_value)
                    widget.handler_block_by_func(on_check_button_toggled)
                    widget.set_active(is_active)
                    widget.handler_unblock_by_func(on_check_button_toggled)
                    index += 1
                    listboxrow = self.filter_listbox.get_row_at_index(index)
                    widget = listboxrow.get_first_child() if listboxrow else None
                post_process()

            elif is_meta and widget.filter_value == 'meta:blank':
                if is_active:
                    if 'meta:blank' in self._dbms.pending_values_to_hide:
                        self._dbms.pending_values_to_hide.remove('meta:blank')
                    if 'meta:all' not in self._dbms.pending_values_to_show:
                        self._dbms.pending_values_to_show.append('meta:blank')
                else:
                    if 'meta:blank' in self._dbms.pending_values_to_show:
                        self._dbms.pending_values_to_show.remove('meta:blank')
                    if 'meta:all' not in self._dbms.pending_values_to_hide:
                        self._dbms.pending_values_to_hide.append('meta:blank')
                post_process()

            else:
                if is_active:
                    if widget.filter_value in self._dbms.pending_values_to_hide:
                        self._dbms.pending_values_to_hide.remove(widget.filter_value)
                    if 'meta:all' not in self._dbms.pending_values_to_show:
                        self._dbms.pending_values_to_show.append(widget.filter_value)
                else:
                    if widget.filter_value in self._dbms.pending_values_to_show:
                        self._dbms.pending_values_to_show.remove(widget.filter_value)
                    if 'meta:all' not in self._dbms.pending_values_to_hide:
                        self._dbms.pending_values_to_hide.append(widget.filter_value)
                post_process()

        def add_check_button(value: any, is_active: bool = False, is_meta: bool = False) -> Gtk.CheckButton:
            """
            Adds a check button to the SheetColumnHeaderMenu.

            This function adds a check button to the SheetColumnHeaderMenu with the given label and active state.
            The label is truncated if it is too long. The check button is appended to the filter listbox.
            The check button is disabled if the label starts with 'eruo-data-studio:*', as it is used as a placeholder.

            Args:
                label (str): The label of the check button.
                active (bool, optional): Whether the check button is active. Defaults to False.
            """
            filter_value = value
            value = str(value)
            if len(value) > 80:
                value = value[:77] + '...' # truncate to optimize UI rendering

            check_button = Gtk.CheckButton()

            if is_meta and filter_value == 'Select All':
                filter_value = 'meta:all'
                check_button.set_active(filter_value in self._dbms.pending_values_to_show or len(self._dbms.pending_values_to_show) > 0)
                is_consistent = (filter_value in self._dbms.pending_values_to_show and len(self._dbms.pending_values_to_hide) == 0) \
                                or (filter_value in self._dbms.pending_values_to_hide and len(self._dbms.pending_values_to_show) == 0)
                check_button.set_inconsistent(not is_consistent)
            elif is_meta and filter_value == '(Select All)':
                filter_value = 'meta:all-result'
            elif is_meta and filter_value == '(Blanks)':
                filter_value = 'meta:blank'
            elif filter_value == 'eruo-data-studio:truncated':
                value = _('Use search to uncover more items')
            elif filter_value == 'eruo-data-studio:empty':
                value = _('No items found')

            if filter_value != 'meta:all':
                is_active = (filter_value in self._dbms.pending_values_to_show and 'meta:all' in self._dbms.pending_values_to_hide) \
                            or (filter_value not in self._dbms.pending_values_to_hide and 'meta:all' in self._dbms.pending_values_to_show)
                check_button.set_active(is_active)

            if filter_value.startswith('eruo-data-studio:'):
                check_button.set_active(False)
                check_button.set_sensitive(False)
                check_button.add_css_class('search-placeholder')
                check_button.is_placeholder = True
            else:
                check_button.set_can_focus(False)
                check_button.connect('toggled', on_check_button_toggled, is_meta)

            check_button.set_label(value)
            check_button.filter_value = filter_value
            return check_button

        def update_listbox(checkboxes: list[Gtk.CheckButton]) -> None:
            for checkbox in checkboxes:
                self.filter_listbox.append(checkbox)
            self.filter_spinner.hide()

        colid = int(self._colid)
        col_name = self._dbms.get_column(colid)

        if query is not None:
            is_approx = False
            n_unique, options = self._dbms.find_unique_values(colid, query)
        else:
            for index, return_value in enumerate(self._dbms.scan_unique_values(colid)):
                if index == 0:
                    n_unique, is_approx = return_value
                else:
                    options = return_value

        if len(options) == 1_000 and n_unique > 1_000: # 1_000 is used in scan_unique_values()
            options += ['eruo-data-studio:truncated']
        elif len(options) == 0:
            options += ['eruo-data-studio:empty']

        if colid != int(self._colid):
            print_log(f'Interrupted from showing filter options for column {col_name}', Log.DEBUG)
            return

        if query in [None, '']:
            checkboxes = [add_check_button(_('Select All'), True, True)]
        elif len(options) > 0:
            checkboxes = [add_check_button('(Select All)', False, True)]
        else:
            checkboxes = []
        if any(option in [None, ''] for option in options):
            checkboxes.append(add_check_button(_('(Blanks)'), True, True))
        for option in options:
            if option in [None, '']:
                continue
            checkboxes.append(add_check_button(option, True))

        GLib.idle_add(self.filter_searchentry.set_placeholder_text, f'Search in {"approx. " if is_approx else ""}{format(n_unique, ",d")} item(s)...')
        GLib.idle_add(update_listbox, checkboxes)
        self.action_set_enabled('app.sheet.column.apply-filter', True)
        print_log(f'Showing filter options for column {col_name}...', Log.DEBUG)
