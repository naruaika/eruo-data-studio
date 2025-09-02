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

from .sheet_selection import SheetCell, SheetCornerLocatorCell, \
                             SheetTopLocatorCell, SheetLeftLocatorCell

class SheetCellMenu(Gtk.PopoverMenu):
    __gtype_name__ = 'SheetCellMenu'

    def __init__(self,
                 start_column:         str,       start_row: str,
                 end_column:           str,       end_row:   str,
                 column_span:          int,       row_span:  int,
                 n_hidden_columns:     int,
                 n_all_hidden_columns: int,
                 ctype:                SheetCell, dfi:       int,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        # The default flags make the menu width too large and buggy
        # for a big menu with smaller submenu.
        self.set_flags(Gtk.PopoverMenuFlags.NESTED)

        main_menu = Gio.Menu.new()

        self.create_cut_copy_paste_section(main_menu)

        if dfi >= 0:
            self.create_filter_sort_section(main_menu, ctype)
            self.create_convert_transform_section(main_menu, ctype)
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
            self.create_table_section(main_menu, ctype)

        # General section
        other_section = Gio.Menu.new()
        other_section.append(_('Command Palette...'), 'app.open-command-palette')
        main_menu.append_section(None, other_section)

        self.set_menu_model(main_menu)

    def create_cut_copy_paste_section(self, main_menu: Gio.Menu) -> None:
        cut_copy_paste_section = Gio.Menu.new()
        cut_copy_paste_section.append(_('_Cut'), 'app.cut')
        cut_copy_paste_section.append(_('C_opy'), 'app.copy')
        cut_copy_paste_section.append(_('_Paste'), 'app.paste')
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
                insert_section_1.append(_('Insert {:,} Row(s) _Above').format(row_span), 'app.insert-row-above')
            insert_section_1.append(_('Insert {:,} Row(s) _Below').format(row_span), 'app.insert-row-below')

            insert_section_2 = Gio.Menu.new()
            insert_section_2.append(_('Insert {:,} Column(s) _Left').format(column_span), 'app.insert-column-left')
            insert_section_2.append(_('Insert {:,} Column(s) _Right').format(column_span), 'app.insert-column-right')

            insert_menu.append_section(None, insert_section_1)
            insert_menu.append_section(None, insert_section_2)

            insert_menu_item = Gio.MenuItem.new(_('_Insert'), None)
            insert_menu_item.set_submenu(insert_menu)

            insert_duplicate_delete_section.append_item(insert_menu_item)

            # Duplicate Section
            duplicate_menu = Gio.Menu.new()

            if int(start_row) > 1:
                duplicate_section_1 = Gio.Menu.new()
                duplicate_section_1.append(_('Duplicate {:,} Row(s) _Above').format(row_span), 'app.duplicate-to-above')
                duplicate_section_1.append(_('Duplicate {:,} Row(s) _Below').format(row_span), 'app.duplicate-to-below')
                duplicate_menu.append_section(None, duplicate_section_1)

            duplicate_section_2 = Gio.Menu.new()
            duplicate_section_2.append(_('Duplicate {:,} Column(s) _Left').format(column_span), 'app.duplicate-to-left')
            duplicate_section_2.append(_('Duplicate {:,} Column(s) _Right').format(column_span), 'app.duplicate-to-right')
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
        if ctype in [SheetCornerLocatorCell, SheetLeftLocatorCell]:
            return

        filter_sort_section = Gio.Menu.new()
        main_menu.append_section(None, filter_sort_section)

        keep_only_section_1 = Gio.Menu.new()
        keep_only_section_1.append(_('Including the Selection'), 'app.keep-rows-only-including-selection')
        keep_only_section_1.append(_('Including String (Case Insensitive)...'), 'app.keep-rows-only-including-case-insensitive-string')
        keep_only_section_1.append(_('Including String (Case Sensitive)...'), 'app.keep-rows-only-including-case-sensitive-string')
        keep_only_section_1.append(_('Matching Regex (Case Insensitive)...'), 'app.keep-rows-only-matching-regex-case-insensitive')
        keep_only_section_1.append(_('Matching Regex (Case Sensitive)...'), 'app.keep-rows-only-matching-regex-case-sensitive')

        keep_only_section_2 = Gio.Menu.new()
        keep_only_section_2.append(_('Including the Selection'), 'app.keep-rows-only-including-selection-into-new-worksheet')
        keep_only_section_2.append(_('Including String (Case Insensitive)...'), 'app.keep-rows-only-including-insensitive-string-into-new-worksheet')
        keep_only_section_2.append(_('Including String (Case Sensitive)...'), 'app.keep-rows-only-including-sensitive-string-into-new-worksheet')
        keep_only_section_2.append(_('Matching Regex (Case Insensitive)...'), 'app.keep-rows-only-matching-regex-insensitive-into-new-worksheet')
        keep_only_section_2.append(_('Matching Regex (Case Sensitive)...'), 'app.keep-rows-only-matching-regex-sensitive-into-new-worksheet')

        remove_rows_section_1 = Gio.Menu.new()
        remove_rows_section_1.append(_('Including the Selection'), 'app.remove-rows-including-selection')
        remove_rows_section_1.append(_('Including String (Case Insensitive)...'), 'app.remove-rows-including-case-insensitive-string')
        remove_rows_section_1.append(_('Including String (Case Sensitive)...'), 'app.remove-rows-including-case-sensitive-string')
        remove_rows_section_1.append(_('Matching Regex (Case Insensitive)...'), 'app.remove-rows-matching-regex-case-insensitive')
        remove_rows_section_1.append(_('Matching Regex (Case Sensitive)...'), 'app.remove-rows-matching-regex-case-sensitive')

        remove_rows_section_2 = Gio.Menu.new()
        remove_rows_section_2.append(_('Including the Selection'), 'app.remove-rows-including-selection-into-new-worksheet')
        remove_rows_section_2.append(_('Including String (Case Insensitive)...'), 'app.remove-rows-including-insensitive-string-into-new-worksheet')
        remove_rows_section_2.append(_('Including String (Case Sensitive)...'), 'app.remove-rows-including-sensitive-string-into-new-worksheet')
        remove_rows_section_2.append(_('Matching Regex (Case Insensitive)...'), 'app.remove-rows-matching-regex-insensitive-into-new-worksheet')
        remove_rows_section_2.append(_('Matching Regex (Case Sensitive)...'), 'app.remove-rows-matching-regex-sensitive-into-new-worksheet')

        other_rows_section = Gio.Menu.new()
        other_rows_section.append(_('Custom Filter...'), 'app.open-sort-filter')
        other_rows_section.append(_('Reset All Filters'), 'app.reset-all-filters')

        filter_menu = Gio.Menu.new()
        filter_menu.append_section('Keep Rows Only', keep_only_section_1)
        filter_menu.append_section('Keep Rows Only Into New Worksheet', keep_only_section_2)
        filter_menu.append_section('Remove Rows', remove_rows_section_1)
        filter_menu.append_section('Remove Rows Into New Worksheet', remove_rows_section_2)
        filter_menu.append_section(None, other_rows_section)

        filter_menu_item = Gio.MenuItem.new(_('_Filter'), None)
        filter_menu_item.set_submenu(filter_menu)
        filter_sort_section.append_item(filter_menu_item)

        sort_menu = Gio.Menu.new()
        sort_menu.append(_('Sort by Ascending'), 'app.sort-by-ascending')
        sort_menu.append(_('Sort by Descending'), 'app.sort-by-descending')
        sort_menu.append(_('Custom Sort...'), 'app.open-sort-filter')

        sort_menu_item = Gio.MenuItem.new(_('_Sort'), None)
        sort_menu_item.set_submenu(sort_menu)
        filter_sort_section.append_item(sort_menu_item)

    def create_convert_transform_section(self,
                                         main_menu: Gio.Menu,
                                         ctype:     SheetCell) -> None:
        if ctype in [SheetCornerLocatorCell, SheetLeftLocatorCell]:
            return

        convert_transform_section = Gio.Menu.new()
        main_menu.append_section(None, convert_transform_section)

        # TODO: wondering that we need to simplify this to fewer options as possible?

        convert_basic_section = Gio.Menu.new()
        convert_basic_section.append(_('Change to _Categorical'), 'app.convert-to-categorical')
        convert_basic_section.append(_('Change to _Whole Number'), 'app.convert-to-whole-number')
        convert_basic_section.append(_('Change to _Decimal Number'), 'app.convert-to-decimal')
        convert_basic_section.append(_('Change to _Text (String)'), 'app.convert-to-text')
        convert_basic_section.append(_('Change to _Boolean'), 'app.convert-to-boolean')

        convert_int_section = Gio.Menu.new()
        convert_int_section.append(_('Change to Integer _8'), 'app.convert-to-int8')
        convert_int_section.append(_('Change to Integer _16'), 'app.convert-to-int16')
        convert_int_section.append(_('Change to Integer _32'), 'app.convert-to-int32')
        convert_int_section.append(_('Change to Integer _64'), 'app.convert-to-int64')

        convert_uint_section = Gio.Menu.new()
        convert_uint_section.append(_('Change to Unsigned Integer _8'), 'app.convert-to-uint8')
        convert_uint_section.append(_('Change to Unsigned Integer _16'), 'app.convert-to-uint16')
        convert_uint_section.append(_('Change to Unsigned Integer _32'), 'app.convert-to-uint32')
        convert_uint_section.append(_('Change to Unsigned Integer _64'), 'app.convert-to-uint64')

        convert_float_section = Gio.Menu.new()
        convert_float_section.append(_('Change to Float _32'), 'app.convert-to-float32')
        convert_float_section.append(_('Change to Float _64'), 'app.convert-to-float64')

        convert_date_time_menu = Gio.Menu.new()
        convert_date_time_menu.append(_('Change to _Date'), 'app.convert-to-date')
        convert_date_time_menu.append(_('Change to _Time'), 'app.convert-to-time')
        convert_date_time_menu.append(_('Change to D_atetime'), 'app.convert-to-datetime')

        convert_menu = Gio.Menu.new()
        convert_menu.append_section(None, convert_basic_section)
        convert_menu.append_section(None, convert_date_time_menu)
        convert_menu.append_section(None, convert_int_section)
        convert_menu.append_section(None, convert_uint_section)
        convert_menu.append_section(None, convert_float_section)

        convert_menu_item = Gio.MenuItem.new(_('_Change Type'), None)
        convert_menu_item.set_submenu(convert_menu)
        convert_transform_section.append_item(convert_menu_item)

        operand = 'cell'
        if ctype in [SheetTopLocatorCell]:
            operand = 'column'

        transform_section_1 = Gio.Menu.new()
        transform_section_1.append(_('Append Prefix...'), f'app.append-prefix-to-{operand}')
        transform_section_1.append(_('Append Suffix...'), f'app.append-suffix-to-{operand}')
        transform_section_1.append(_('Wrap with Different Affixes...'), f'app.wrap-{operand}-with-text-different')
        transform_section_1.append(_('Wrap with Same Affixes...'), f'app.wrap-{operand}-with-text-same')

        transform_section_2 = Gio.Menu.new()
        transform_section_2.append(_('Remove Prefix (Case Insensitive)...'), f'app.remove-prefix-from-{operand}-case-insensitive')
        transform_section_2.append(_('Remove Prefix (Case Sensitive)...'), f'app.remove-prefix-from-{operand}-case-sensitive')
        transform_section_2.append(_('Remove Suffix (Case Insensitive)...'), f'app.remove-suffix-from-{operand}-case-insensitive')
        transform_section_2.append(_('Remove Suffix (Case Sensitive)...'), f'app.remove-suffix-from-{operand}-case-sensitive')

        transform_section_3 = Gio.Menu.new()
        transform_section_3.append(_('Pad End (Right) with Character...'), f'app.pad-end-{operand}-with-custom-string')
        transform_section_3.append(_('Pad End (Right) with Whitespace'), f'app.pad-end-{operand}')
        transform_section_3.append(_('Pad Start (Left) with Character...'), f'app.pad-start-{operand}-with-custom-string')
        transform_section_3.append(_('Pad Start (Left) with Whitespace'), f'app.pad-start-{operand}')

        transform_section_4 = Gio.Menu.new()
        transform_section_4.append(_('Trim Leading Whitespace'), f'app.trim-{operand}-start-whitespace')
        transform_section_4.append(_('Trim Trailing Whitespace'), f'app.trim-{operand}-end-whitespace')
        transform_section_4.append(_('Trim Leading and Trailing Whitespace'), f'app.trim-{operand}-whitespace')
        transform_section_4.append(_('Trim Whitespace and Remove Newlines'), f'app.trim-{operand}-whitespace-and-remove-new-lines')

        transform_section_5 = Gio.Menu.new()
        transform_section_5.append(_('To Camel Case (camelCase)'), f'app.change-{operand}-case-to-camel-case')
        transform_section_5.append(_('To Constant Case (CONSTANT__CASE)'), f'app.change-{operand}-case-to-constant-case')
        transform_section_5.append(_('To Dot Case (dot.case)'), f'app.change-{operand}-case-to-dot-case')
        transform_section_5.append(_('To Kebab Case (kebab-case)'), f'app.change-{operand}-case-to-kebab-case')
        transform_section_5.append(_('To Lowercase'), f'app.change-{operand}-case-to-lowercase')
        transform_section_5.append(_('To Pascal Case (PascalCase)'), f'app.change-{operand}-case-to-pascal-case')
        transform_section_5.append(_('To Sentence Case (Sentence case)'), f'app.change-{operand}-case-to-sentence-case')
        transform_section_5.append(_('To Snake Case (snake__case)'), f'app.change-{operand}-case-to-snake-case')
        transform_section_5.append(_('To Sponge Case (RANdoM CAPiTAlizAtiON)'), f'app.change-{operand}-case-to-sponge-case')
        transform_section_5.append(_('To Title Case (Capitalize Each Word)'), f'app.change-{operand}-case-to-title-case')
        transform_section_5.append(_('To Uppercase'), f'app.change-{operand}-case-to-uppercase')
        transform_section_5.append(_('Slugify Text'), f'app.slugify-{operand}')
        transform_section_5.append(_('Swap Case'), f'app.swap-{operand}-text-case')

        transform_section_6 = Gio.Menu.new()
        transform_section_6.append(_('Convert to NFC'), f'app.convert-{operand}-to-unicode-normalization-nfc')
        transform_section_6.append(_('Convert to NFD'), f'app.convert-{operand}-to-unicode-normalization-nfd')
        transform_section_6.append(_('Convert to NFKC'), f'app.convert-{operand}-to-unicode-normalization-nfkc')
        transform_section_6.append(_('Convert to NFKD'), f'app.convert-{operand}-to-unicode-normalization-nfkd')

        transform_section_7 = Gio.Menu.new()
        transform_section_7.append(_('Decode Base64'), f'app.decode-base64-{operand}-text')
        transform_section_7.append(_('Decode Hexadecimal'), f'app.decode-hexadecimal-{operand}-text')
        transform_section_7.append(_('Decode URL'), f'app.decode-url-{operand}-text')
        transform_section_7.append(_('Encode Base64'), f'app.encode-base64-{operand}-text')
        transform_section_7.append(_('Encode Hexadecimal'), f'app.encode-hexadecimal-{operand}-text')
        transform_section_7.append(_('Encode URL'), f'app.encode-url-{operand}-text')
        transform_section_7.append(_('Reverse Text'), f'app.reverse-text-{operand}')

        transform_section_8 = Gio.Menu.new()
        transform_section_8.append(_('Replace Value (Case Insensitive)...'), f'app.replace-{operand}-values-case-insensitive')
        transform_section_8.append(_('Replace Value with Regex (Case Insensitive)...'), f'app.replace-{operand}-values-case-insensitive-with-regex')
        transform_section_8.append(_('Replace Value (Case Sensitive)...'), f'app.replace-{operand}-values-case-sensitive')
        transform_section_8.append(_('Replace Value with Regex (Case Sensitive)...'), f'app.replace-{operand}-values-case-sensitive-with-regex')
        transform_section_8.append(_('Replace Whitespace with Single Space'), f'app.replace-{operand}-whitespace-with-a-single-space')
        transform_section_8.append(_('Replace Whitespace and Newlines with Single Space'), f'app.replace-{operand}-whitespace-and-new-lines-with-a-single-space')
        transform_section_8.append(_('Remove Newlines Characters'), f'app.remove-{operand}-new-lines-characters')
        transform_section_8.append(_('Remove Whitespace Characters'), f'app.remove-{operand}-whitespace-characters')

        transform_section_9 = Gio.Menu.new()
        transform_section_9.append(_('Split by Comma'), f'app.split-{operand}-by-comma-into-new-worksheet')
        transform_section_9.append(_('Split by Pipe'), f'app.split-{operand}-by-pipe-into-new-worksheet')
        transform_section_9.append(_('Split by Semicolon'), f'app.split-{operand}-by-semicolon-into-new-worksheet')
        transform_section_9.append(_('Split by Whitespace'), f'app.split-{operand}-by-space-into-new-worksheet')
        transform_section_9.append(_('Split by Character Set...'), f'app.split-{operand}-by-characters-into-new-worksheet')

        transform_menu = Gio.Menu.new()
        transform_menu.append_section('Append Affixes', transform_section_1)
        transform_menu.append_section('Remove Affixes', transform_section_2)
        transform_menu.append_section('Append Padding', transform_section_3)
        transform_menu.append_section('Trim Whitespaces', transform_section_4)
        transform_menu.append_section('Transform Case', transform_section_5)
        transform_menu.append_section('Unicode Normalization', transform_section_6)
        transform_menu.append_section('Decode and Encode', transform_section_7)
        transform_menu.append_section('Replace Value', transform_section_8)
        transform_menu.append_section('Split Into New Worksheet', transform_section_9)

        transform_menu_item = Gio.MenuItem.new(_('_Transform'), None)
        transform_menu_item.set_submenu(transform_menu)
        convert_transform_section.append_item(transform_menu_item)

    def create_table_section(self,
                             main_menu: Gio.Menu,
                             ctype:     SheetCell) -> None:
        if ctype in [SheetCornerLocatorCell]:
            header_section_1 = Gio.Menu.new()
            header_section_1.append(_('Use First Row as Headers'), 'app.use-first-row-as-headers')
            header_section_1.append(_('Use Headers as First Row'), 'app.use-headers-as-first-row')
            main_menu.append_section(None, header_section_1)

        if ctype in [SheetCornerLocatorCell]:
            header_section_2 = Gio.Menu.new()
            header_section_2.append(_('Choose Columns...'), 'app.open-field-selector')
            main_menu.append_section(None, header_section_2)

        if ctype in [SheetCornerLocatorCell]:
            keep_only_section = Gio.Menu.new()
            keep_only_section.append(_('Keep Top (First) Rows Only...'), 'app.keep-first-rows')
            keep_only_section.append(_('Keep Bottom (Last) Rows Only...'), 'app.keep-last-rows')
            keep_only_section.append(_('Keep Range of Rows Only...'), 'app.keep-range-rows')
            main_menu.append_section(None, keep_only_section)

            remove_rows_section = Gio.Menu.new()
            remove_rows_section.append(_('Remove Top (First) Rows...'), 'app.remove-first-rows')
            remove_rows_section.append(_('Remove Bottom (Last) Rows...'), 'app.remove-last-rows')
            remove_rows_section.append(_('Remove Alternate Rows...'), 'app.remove-alternate-rows')
            main_menu.append_section(None, remove_rows_section)