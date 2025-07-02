# sheet_column_menu.py
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

from gi.repository import Gtk

from ..dbms import DBMS

@Gtk.Template(resource_path='/com/macipra/Eruo/gtk/sheet-column-menu.ui')
class SheetColumnMenu(Gtk.PopoverMenu):
    __gtype_name__ = 'SheetColumnMenu'

    filter_scrolledwindow = Gtk.Template.Child()
    filter_listbox = Gtk.Template.Child()

    _colid: str
    _dbms: DBMS

    def __init__(self, colid: int, dbms: DBMS, **kwargs) -> None:
        """Creates a new SheetColumnMenu."""
        super().__init__(**kwargs)

        self._colid = str(colid)
        self._dbms = dbms

    def set_colid(self, colid: int) -> None:
        """Sets the colid for the SheetColumnMenu."""
        self._colid = str(colid)

    def set_filter_options(self, options: list[any]) -> None:
        """
        Sets the filter options for the SheetColumnMenu.

        This function resets the existing filter options and adds the new options to the SheetColumnMenu.

        Args:
            options (list[str]): A list of filter options.
        """
        def on_check_button_toggled(widget: Gtk.Widget, is_meta: bool) -> None:
            """
            Callback function for when a check button is toggled.

            Args:
                check_button (Gtk.CheckButton): The check button that was toggled.
            """

            is_active = widget.get_active()
            select_all = self.filter_listbox.get_row_at_index(0).get_first_child()

            def post_process() -> None:
                """Post-processes the SheetColumnMenu after the check button is toggled."""
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

            if is_meta and widget.get_label() == 'Select All':
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

            elif is_meta and widget.get_label() == '(Blanks)':
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

        def add_check_button(value: any, is_active: bool = False, is_meta: bool = False) -> None:
            """
            Adds a check button to the SheetColumnMenu.

            This function adds a check button to the SheetColumnMenu with the given label and active state.
            The label is truncated if it is too long. The check button is appended to the filter listbox.
            The check button is disabled if the label starts with 'eruo-data-studio:truncated', as it is used
            as a placeholder indicating that more options are available.

            Args:
                label (str): The label of the check button.
                active (bool, optional): Whether the check button is active. Defaults to False.
            """
            filter_value = value
            value = str(value)
            if len(value) > 80:
                value = value[:77] + '...' # truncate to optimize UI rendering
            check_button = Gtk.CheckButton.new_with_label(value)
            check_button.filter_value = filter_value
            if value == 'eruo-data-studio:truncated':
                check_button.set_label(f'Use search to find more items...')
                check_button.set_active(False)
                check_button.set_sensitive(False)
                check_button.add_css_class('truncated')
                check_button.is_placeholder = True
            else:
                check_button.set_active(is_active)
                check_button.set_can_focus(False)
                check_button.connect('toggled', on_check_button_toggled, is_meta)
            self.filter_listbox.append(check_button)

        self.filter_listbox.remove_all()
        add_check_button('Select All', True, True)
        if any(option in [None, ''] for option in options):
            add_check_button('(Blanks)', True, True)
        for option in options:
            if option in [None, '']:
                continue
            add_check_button(option, is_active=True)

        # TODO: read from the current applied filters if any
        self.filter_scrolledwindow.get_vadjustment().set_value(0)
        self._dbms.pending_values_to_show = ['meta:all']
        self._dbms.pending_values_to_hide = []
        self.action_set_enabled('app.sheet.column.apply-filter', True)
