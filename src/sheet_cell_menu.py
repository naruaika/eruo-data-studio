# sheet_cell_menu.py
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

from gi.repository import Gio, Gtk

from .sheet_selection import SheetCell, SheetCornerLocatorCell, SheetTopLocatorCell, SheetLeftLocatorCell

class SheetCellMenu(Gtk.PopoverMenu):
    __gtype_name__ = 'SheetCellMenu'

    def __init__(self,
                 start_column:         str,       start_row: str,
                 end_column:           str,       end_row:   str,
                 column_span:          int,       row_span:  int,
                 n_hidden_columns:     int,
                 n_all_hidden_columns: int,
                 ctype:                SheetCell,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        main_menu = Gio.Menu.new()

        self.create_cut_copy_paste_section(main_menu)
        self.create_insert_duplicate_delete_section(main_menu,
                                                    start_column, start_row,
                                                    end_column,   end_row,
                                                    column_span,  row_span,
                                                    ctype)
        self.create_hide_autofit_section(main_menu,
                                         start_column, end_column,
                                         n_hidden_columns,
                                         n_all_hidden_columns,
                                         ctype)
        self.create_filter_sort_section(main_menu, ctype)
        self.create_convert_section(main_menu, ctype)

        self.set_menu_model(main_menu)

    def create_cut_copy_paste_section(self, main_menu: Gio.Menu) -> None:
        cut_copy_paste_section = Gio.Menu.new()
        cut_copy_paste_section.append(_('Cut'), 'app.cut')
        cut_copy_paste_section.append(_('Copy'), 'app.copy')
        cut_copy_paste_section.append(_('Paste'), 'app.paste')
        main_menu.append_section(None, cut_copy_paste_section)

    def create_insert_duplicate_delete_section(self,
                                               main_menu:    Gio.Menu,
                                               start_column: str,       start_row: str,
                                               end_column:   str,       end_row:   str,
                                               column_span:  int,       row_span:  int,
                                               ctype:        SheetCell) -> None:
        row_name = start_row
        if start_row != end_row:
            row_name = f'{start_row}–{end_row}'

        column_name = start_column
        if start_column != end_column:
            column_name = f'{start_column}–{end_column}'

        insert_duplicate_delete_section = Gio.Menu.new()

        if ctype not in [SheetCornerLocatorCell, SheetTopLocatorCell, SheetLeftLocatorCell]:
            # Insert Section
            insert_menu = Gio.Menu.new()

            insert_section_1 = Gio.Menu.new()
            if int(start_row) > 1:
                insert_section_1.append(_('{:,} Row(s) _Above').format(row_span), 'app.insert-row-above')
            insert_section_1.append(_('{:,} Row(s) _Below').format(row_span), 'app.insert-row-below')

            insert_section_2 = Gio.Menu.new()
            insert_section_2.append(_('{:,} Column(s) _Left').format(column_span), 'app.insert-column-left')
            insert_section_2.append(_('{:,} Column(s) _Right').format(column_span), 'app.insert-column-right')

            insert_menu.append_section(None, insert_section_1)
            insert_menu.append_section(None, insert_section_2)

            insert_menu_item = Gio.MenuItem.new(_('_Insert'), None)
            insert_menu_item.set_submenu(insert_menu)

            insert_duplicate_delete_section.append_item(insert_menu_item)

            # Duplicate Section
            duplicate_menu = Gio.Menu.new()

            if int(start_row) > 1:
                duplicate_section_1 = Gio.Menu.new()
                duplicate_section_1.append(_('{:,} Row(s) _Above').format(row_span), 'app.duplicate-to-above')
                duplicate_section_1.append(_('{:,} Row(s) _Below').format(row_span), 'app.duplicate-to-below')
                duplicate_menu.append_section(None, duplicate_section_1)

            duplicate_section_2 = Gio.Menu.new()
            duplicate_section_2.append(_('{:,} Column(s) _Left').format(column_span), 'app.duplicate-to-left')
            duplicate_section_2.append(_('{:,} Column(s) _Right').format(column_span), 'app.duplicate-to-right')
            duplicate_menu.append_section(None, duplicate_section_2)

            duplicate_menu_item = Gio.MenuItem.new(_('_Duplicate'), None)
            duplicate_menu_item.set_submenu(duplicate_menu)

            insert_duplicate_delete_section.append_item(duplicate_menu_item)

            # Delete Section
            delete_menu = Gio.Menu.new()

            if int(start_row) > 1:
                delete_menu.append(_('Delete _Row {}').format(row_name), 'app.delete-row')
            delete_menu.append(_('Delete _Column {}').format(column_name), 'app.delete-column')

            delete_menu_item = Gio.MenuItem.new(_('_Delete'), None)
            delete_menu_item.set_submenu(delete_menu)

            insert_duplicate_delete_section.append_item(delete_menu_item)

            # Clear Contents
            clear_contents_item = Gio.MenuItem.new(_('_Clear Content(s)'), 'app.clear-contents')
            insert_duplicate_delete_section.append_item(clear_contents_item)

            main_menu.append_section(None, insert_duplicate_delete_section)

        if ctype is SheetTopLocatorCell:
            insert_duplicate_section = Gio.Menu.new()
            delete_clear_section = Gio.Menu.new()

            # Insert Section
            insert_duplicate_section.append(_('Insert {:,} Column(s) _Left').format(column_span), 'app.insert-column-left')
            insert_duplicate_section.append(_('Insert {:,} Column(s) _Right').format(column_span), 'app.insert-column-right')

            # Duplicate Section
            insert_duplicate_section.append(_('Duplicate {:,} Column(s) _Left').format(column_span), 'app.duplicate-to-left')
            insert_duplicate_section.append(_('Duplicate {:,} Column(s) _Right').format(column_span), 'app.duplicate-to-right')

            # Delete Section
            delete_clear_section.append(_('Delete {:,} Column(s)').format(column_span), 'app.delete-column')

            # Clear Contents
            delete_clear_section.append(_('_Clear Content(s)'), 'app.clear-contents')

            main_menu.append_section(None, insert_duplicate_section)
            main_menu.append_section(None, delete_clear_section)

        if ctype is SheetLeftLocatorCell:
            insert_duplicate_section = Gio.Menu.new()
            delete_clear_section = Gio.Menu.new()

            # Insert Section
            insert_duplicate_section.append(_('Insert {:,} Row(s) _Above').format(row_span), 'app.insert-row-above')
            insert_duplicate_section.append(_('Insert {:,} Row(s) _Below').format(row_span), 'app.insert-row-below')

            # Duplication Section
            insert_duplicate_section.append(_('Duplicate {:,} Row(s) _Above').format(row_span), 'app.duplicate-to-above')
            insert_duplicate_section.append(_('Duplicate {:,} Row(s) _Below').format(row_span), 'app.duplicate-to-below')

            # Delete Section
            delete_clear_section.append(_('Delete {:,} Row(s)').format(row_span), 'app.delete-row')

            # Clear Contents
            delete_clear_section.append(_('_Clear Content(s)'), 'app.clear-contents')

            main_menu.append_section(None, insert_duplicate_section)
            main_menu.append_section(None, delete_clear_section)

    def create_hide_autofit_section(self,
                                    main_menu:            Gio.Menu,
                                    start_column:         str,
                                    end_column:           str,
                                    n_hidden_columns:     int,
                                    n_all_hidden_columns: int,
                                    ctype:                SheetCell) -> None:
        if ctype is not SheetTopLocatorCell:
            return

        column_name = start_column
        if start_column != end_column:
            column_name = f'{start_column}–{end_column}'

        hide_section = Gio.Menu.new()

        hide_section.append(_('Hide Column {}').format(column_name), 'app.hide-column')

        main_menu.append_section(None, hide_section)

        if 0 < n_hidden_columns:
            main_menu.append(_('Unhide {:,} Column(s)').format(n_hidden_columns), 'app.unhide-column')

        if 0 < n_all_hidden_columns:
            main_menu.append(_('Unhide All Columns'), 'app.unhide-all-columns')

    def create_filter_sort_section(self,
                                   main_menu: Gio.Menu,
                                   ctype:     SheetCell) -> None:
        if ctype in [SheetCornerLocatorCell, SheetTopLocatorCell, SheetLeftLocatorCell]:
            return

        filter_sort_section = Gio.Menu.new()
        main_menu.append_section(None, filter_sort_section)

        filter_menu = Gio.Menu.new()
        filter_menu.append(_('By Cell _Value'), 'app.filter-cell-value')
        filter_menu.append(_('By Cell _Color'), 'app.filter-cell-color')
        filter_menu.append(_('By _Font Color'), 'app.filter-font-color')

        filter_menu_item = Gio.MenuItem.new(_('_Filter'), None)
        filter_menu_item.set_submenu(filter_menu)
        filter_sort_section.append_item(filter_menu_item)

        sort_menu = Gio.Menu.new()
        sort_menu.append(_('By Ascending'), 'app.sort-by-ascending')
        sort_menu.append(_('By Descending'), 'app.sort-by-descending')

        sort_menu_item = Gio.MenuItem.new(_('_Sort'), None)
        sort_menu_item.set_submenu(sort_menu)
        filter_sort_section.append_item(sort_menu_item)

    def create_convert_section(self,
                               main_menu: Gio.Menu,
                               ctype:     SheetCell) -> None:
        if ctype in [SheetCornerLocatorCell, SheetLeftLocatorCell]:
            return

        convert_section = Gio.Menu.new()

        # TODO: wondering that we need to simplify this to fewer options as possible?
        convert_int_section = Gio.Menu.new()
        convert_int_section.append(_('Integer _8'), 'app.convert-to-int8')
        convert_int_section.append(_('Integer _16'), 'app.convert-to-int16')
        convert_int_section.append(_('Integer _32'), 'app.convert-to-int32')
        convert_int_section.append(_('Integer _64'), 'app.convert-to-int64')

        convert_uint_section = Gio.Menu.new()
        convert_uint_section.append(_('Unsigned Integer _8'), 'app.convert-to-uint8')
        convert_uint_section.append(_('Unsigned Integer _16'), 'app.convert-to-uint16')
        convert_uint_section.append(_('Unsigned Integer _32'), 'app.convert-to-uint32')
        convert_uint_section.append(_('Unsigned Integer _64'), 'app.convert-to-uint64')

        convert_float_section = Gio.Menu.new()
        convert_float_section.append(_('Float _32'), 'app.convert-to-float32')
        convert_float_section.append(_('Float _64'), 'app.convert-to-float64')
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

        convert_menu_item = Gio.MenuItem.new(_('_Change Type'), None)
        convert_menu_item.set_submenu(convert_menu)

        convert_section.append_item(convert_menu_item)

        main_menu.append_section(None, convert_section)