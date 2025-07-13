# sheet_cell_menu.py
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

from gi.repository import Gio, Gtk

from .sheet_selection import SheetCell, SheetTopLocatorCell, SheetLeftLocatorCell

class SheetCellMenu(Gtk.PopoverMenu):
    __gtype_name__ = 'SheetCellMenu'

    def __init__(self, start_column: str, start_row: str, end_column: str, end_row: str, ctype: SheetCell, **kwargs) -> None:
        super().__init__(**kwargs)

        # self.set_flags(Gtk.PopoverMenuFlags.NESTED)
        # self.set_has_arrow(False)
        self.add_css_class('context-menu')

        main_menu = Gio.Menu.new()

        # Cut/Copy/Paste Section
        cut_copy_paste_section = Gio.Menu.new()
        cut_copy_paste_section.append(_('Cut'), 'app.cut')
        cut_copy_paste_section.append(_('Copy'), 'app.copy')
        cut_copy_paste_section.append(_('Paste'), 'app.paste')
        main_menu.append_section(None, cut_copy_paste_section)

        # Insert Section
        insert_menu = Gio.Menu.new()

        ## Insert Row Section
        if ctype is not SheetTopLocatorCell:
            row_span = int(end_row) - int(start_row) + 1
            insert_section_1 = Gio.Menu.new()
            if int(start_row) > 1:
                insert_section_1.append(_('{} Row(s) _Above').format(row_span), 'app.insert-row-above')
            insert_section_1.append(_('{} Row(s) _Below').format(row_span), 'app.insert-row-below')
            insert_menu.append_section(None, insert_section_1)

        ## Insert Column Section
        if ctype is not SheetLeftLocatorCell:
            column_span = ord(end_column) - ord(start_column) + 1
            insert_section_2 = Gio.Menu.new()
            insert_section_2.append(_('{} Column(s) _Left').format(column_span), 'app.insert-column-left')
            insert_section_2.append(_('{} Column(s) _Right').format(column_span), 'app.insert-column-right')
            insert_menu.append_section(None, insert_section_2)

        insert_menu_item = Gio.MenuItem.new(_('_Insert'), None)
        insert_menu_item.set_submenu(insert_menu)

        # Duplicate Section
        duplicate_menu = Gio.Menu.new()

        ## Duplicate Row Section
        if ctype is not SheetTopLocatorCell and int(start_row) > 1:
            duplicate_section_1 = Gio.Menu.new()
            duplicate_section_1.append(_('To Row(s) _Above'), 'app.duplicate-to-above')
            duplicate_section_1.append(_('To Row(s) _Below'), 'app.duplicate-to-below')
            duplicate_menu.append_section(None, duplicate_section_1)

        ## Duplicate Column Section
        if ctype is not SheetLeftLocatorCell:
            duplicate_section_2 = Gio.Menu.new()
            duplicate_section_2.append(_('To Column(s) _Left'), 'app.duplicate-to-left')
            duplicate_section_2.append(_('To Column(s) _Right'), 'app.duplicate-to-right')
            duplicate_menu.append_section(None, duplicate_section_2)

        duplicate_menu_item = Gio.MenuItem.new(_('_Duplicate'), None)
        duplicate_menu_item.set_submenu(duplicate_menu)

        # Delete Section
        delete_menu = Gio.Menu.new()

        ## Delete Row Item
        if ctype is not SheetTopLocatorCell and int(start_row) > 1:
            row_name = start_row
            if start_row != end_row:
                row_name = f'{start_row}–{end_row}'
            delete_menu.append(_('Delete _Row {}').format(row_name), 'app.delete-row')

        ## Delete Column Item
        if ctype is not SheetLeftLocatorCell:
            column_name = start_column
            if start_column != end_column:
                column_name = f'{start_column}–{end_column}'
            delete_menu.append(_('Delete _Column {}').format(column_name), 'app.delete-column')

        delete_menu_item = Gio.MenuItem.new(_('_Delete'), None)
        delete_menu_item.set_submenu(delete_menu)

        # Clear Contents
        insert_duplicate_delete_section = Gio.Menu.new()
        insert_duplicate_delete_section.append_item(insert_menu_item)
        if not(ctype is SheetLeftLocatorCell and int(start_row) == 1):
            insert_duplicate_delete_section.append_item(duplicate_menu_item)
            insert_duplicate_delete_section.append_item(delete_menu_item)

        clear_contents_item = Gio.MenuItem.new(_('_Clear Contents'), 'app.clear-contents')
        insert_duplicate_delete_section.append_item(clear_contents_item)

        main_menu.append_item(Gio.MenuItem.new_section(None, insert_duplicate_delete_section))

        # Filter/Sort Section
        filter_sort_section = Gio.Menu.new()

        ## Filter Section
        filter_menu = Gio.Menu.new()
        filter_menu.append(_('Cell _Value'), 'app.filter-cell-value')
        filter_menu.append(_('Cell _Color'), 'app.filter-cell-color')
        filter_menu.append(_('_Font Color'), 'app.filter-font-color')

        filter_menu_item = Gio.MenuItem.new(_('_Filter'), None)
        filter_menu_item.set_submenu(filter_menu)

        ## Sort Section
        sort_menu = Gio.Menu.new()
        sort_menu.append(_('A-Z (Smallest to Largest)'), 'app.sort-smallest-to-largest')
        sort_menu.append(_('Z-A (Largest to Smallest)'), 'app.sort-largest-to-smallest')

        sort_menu_item = Gio.MenuItem.new(_('_Sort'), None)
        sort_menu_item.set_submenu(sort_menu)

        filter_sort_section.append_item(filter_menu_item)
        filter_sort_section.append_item(sort_menu_item)

        main_menu.append_item(Gio.MenuItem.new_section(None, filter_sort_section))

        # Convert Section
        convert_section = Gio.Menu.new()

        convert_int_section = Gio.Menu.new()
        convert_int_section.append(_('Integer_8'), 'app.convert-to-int8')
        convert_int_section.append(_('Integer_16'), 'app.convert-to-int16')
        convert_int_section.append(_('Integer_32'), 'app.convert-to-int32')
        convert_int_section.append(_('Integer_64'), 'app.convert-to-int64')

        convert_uint_section = Gio.Menu.new()
        convert_uint_section.append(_('Unsigned Integer_8'), 'app.convert-to-uint8')
        convert_uint_section.append(_('Unsigned Integer_16'), 'app.convert-to-uint16')
        convert_uint_section.append(_('Unsigned Integer_32'), 'app.convert-to-uint32')
        convert_uint_section.append(_('Unsigned Integer_64'), 'app.convert-to-uint64')

        convert_float_section = Gio.Menu.new()
        convert_float_section.append(_('Float_32'), 'app.convert-to-float32')
        convert_float_section.append(_('Float_64'), 'app.convert-to-float64')
        convert_float_section.append(_('_Decimal'), 'app.convert-to-decimal')

        convert_number_menu = Gio.Menu.new()
        convert_number_menu.append_section(None, convert_int_section)
        convert_number_menu.append_section(None, convert_uint_section)
        convert_number_menu.append_section(None, convert_float_section)

        convert_number_menu_item = Gio.MenuItem.new(_('To _Number'), None)
        convert_number_menu_item.set_submenu(convert_number_menu)

        convert_date_time_menu = Gio.Menu.new()
        convert_date_time_menu.append(_('_Date'), 'app.convert-to-date')
        convert_date_time_menu.append(_('_Time'), 'app.convert-to-time')
        convert_date_time_menu.append(_('D_atetime'), 'app.convert-to-datetime')

        convert_date_time_menu_item = Gio.MenuItem.new(_('To _Date/Time'), None)
        convert_date_time_menu_item.set_submenu(convert_date_time_menu)

        convert_menu = Gio.Menu.new()
        convert_menu.append(_('To _Categorical'), 'app.convert-to-categorical')
        convert_menu.append_item(convert_number_menu_item)
        convert_menu.append_item(convert_date_time_menu_item)
        convert_menu.append(_('To _Boolean'), 'app.convert-to-boolean')
        convert_menu.append(_('To _Text'), 'app.convert-to-text')

        convert_menu_item = Gio.MenuItem.new(_('_Convert'), None)
        convert_menu_item.set_submenu(convert_menu)

        convert_section.append_item(convert_menu_item)

        main_menu.append_item(Gio.MenuItem.new_section(None, convert_section))

        self.set_menu_model(main_menu)
