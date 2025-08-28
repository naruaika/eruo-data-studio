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

        # The default flags make the menu width too large
        self.set_flags(Gtk.PopoverMenuFlags.NESTED)

        main_menu = Gio.Menu.new()

        self.create_cut_copy_paste_section(main_menu)

        if dfi >= 0:
            self.create_filter_sort_section(main_menu)
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

        other_section = Gio.Menu.new()
        other_section.append(_('Command Palette...'), 'app.open-command-palette')
        main_menu.append_section(None, other_section)

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

    def create_filter_sort_section(self, main_menu: Gio.Menu) -> None:
        filter_sort_section = Gio.Menu.new()
        main_menu.append_section(None, filter_sort_section)

        keep_only_section_1 = Gio.Menu.new()
        keep_only_section_1.append(_('Keep Only Including the Selection'), 'app.keep-rows-only-including-selection')
        keep_only_section_1.append(_('Keep Only Including a String (Case Insensitive)...'), 'app.keep-rows-only-including-case-insensitive-string')
        keep_only_section_1.append(_('Keep Only Including a String (Case Sensitive)...'), 'app.keep-rows-only-including-case-sensitive-string')
        keep_only_section_1.append(_('Keep Only Matching a Regex (Case Insensitive)...'), 'app.keep-rows-only-matching-regex-case-insensitive')
        keep_only_section_1.append(_('Keep Only Matching a Regex (Case Sensitive)...'), 'app.keep-rows-only-matching-regex-case-sensitive')

        keep_only_section_2 = Gio.Menu.new()
        keep_only_section_2.append(_('Keep Only Including the Selection Into a New Worksheet'), 'app.keep-rows-only-including-selection-into-new-worksheet')
        keep_only_section_2.append(_('Keep Only Including a String Into a New Worksheet (Case Insensitive)...'), 'app.keep-rows-only-including-insensitive-string-into-new-worksheet')
        keep_only_section_2.append(_('Keep Only Including a String Into a New Worksheet (Case Sensitive)...'), 'app.keep-rows-only-including-sensitive-string-into-new-worksheet')
        keep_only_section_2.append(_('Keep Only Matching a Regex Into a New Worksheet (Case Insensitive)...'), 'app.keep-rows-only-matching-regex-insensitive-into-new-worksheet')
        keep_only_section_2.append(_('Keep Only Matching a Regex Into a New Worksheet (Case Sensitive)...'), 'app.keep-rows-only-matching-regex-sensitive-into-new-worksheet')

        remove_rows_section_1 = Gio.Menu.new()
        remove_rows_section_1.append(_('Remove Including the Selection'), 'app.remove-rows-including-selection')
        remove_rows_section_1.append(_('Remove Including a String (Case Insensitive)...'), 'app.remove-rows-including-case-insensitive-string')
        remove_rows_section_1.append(_('Remove Including a String (Case Sensitive)...'), 'app.remove-rows-including-case-sensitive-string')
        remove_rows_section_1.append(_('Remove Matching a Regex (Case Insensitive)...'), 'app.remove-rows-matching-regex-case-insensitive')
        remove_rows_section_1.append(_('Remove Matching a Regex (Case Sensitive)...'), 'app.remove-rows-matching-regex-case-sensitive')

        remove_rows_section_2 = Gio.Menu.new()
        remove_rows_section_2.append(_('Remove Including the Selection Into a New Worksheet'), 'app.remove-rows-including-selection-into-new-worksheet')
        remove_rows_section_2.append(_('Remove Including a String Into a New Worksheet (Case Insensitive)...'), 'app.remove-rows-including-insensitive-string-into-new-worksheet')
        remove_rows_section_2.append(_('Remove Including a String Into a New Worksheet (Case Sensitive)...'), 'app.remove-rows-including-sensitive-string-into-new-worksheet')
        remove_rows_section_2.append(_('Remove Matching a Regex Into a New Worksheet (Case Insensitive)...'), 'app.remove-rows-matching-regex-insensitive-into-new-worksheet')
        remove_rows_section_2.append(_('Remove Matching a Regex Into a New Worksheet (Case Sensitive)...'), 'app.remove-rows-matching-regex-sensitive-into-new-worksheet')

        other_rows_section = Gio.Menu.new()
        other_rows_section.append(_('Custom Filter...'), 'app.open-sort-filter')
        other_rows_section.append(_('Reset All Filters'), 'app.reset-all-filters')

        filter_menu = Gio.Menu.new()
        filter_menu.append_section(None, keep_only_section_1)
        filter_menu.append_section(None, keep_only_section_2)
        filter_menu.append_section(None, remove_rows_section_1)
        filter_menu.append_section(None, remove_rows_section_2)
        filter_menu.append_section(None, other_rows_section)

        filter_menu_item = Gio.MenuItem.new(_('_Filter'), None)
        filter_menu_item.set_submenu(filter_menu)
        filter_sort_section.append_item(filter_menu_item)

        sort_menu = Gio.Menu.new()
        sort_menu.append(_('Sort By Ascending'), 'app.sort-by-ascending')
        sort_menu.append(_('Sort By Descending'), 'app.sort-by-descending')

        sort_menu_item = Gio.MenuItem.new(_('_Sort'), None)
        sort_menu_item.set_submenu(sort_menu)
        filter_sort_section.append_item(sort_menu_item)

    def create_convert_transform_section(self,
                                         main_menu: Gio.Menu,
                                         ctype:     SheetCell) -> None:
        convert_transform_section = Gio.Menu.new()
        main_menu.append_section(None, convert_transform_section)

        # TODO: wondering that we need to simplify this to fewer options as possible?

        convert_basic_section = Gio.Menu.new()
        convert_basic_section.append(_('Change To _Categorical'), 'app.convert-to-categorical')
        convert_basic_section.append(_('Change To _Whole Number'), 'app.convert-to-whole-number')
        convert_basic_section.append(_('Change To _Decimal'), 'app.convert-to-decimal')
        convert_basic_section.append(_('Change To _Text'), 'app.convert-to-text')
        convert_basic_section.append(_('Change To _Boolean'), 'app.convert-to-boolean')

        convert_int_section = Gio.Menu.new()
        convert_int_section.append(_('Change To Integer _8'), 'app.convert-to-int8')
        convert_int_section.append(_('Change To Integer _16'), 'app.convert-to-int16')
        convert_int_section.append(_('Change To Integer _32'), 'app.convert-to-int32')
        convert_int_section.append(_('Change To Integer _64'), 'app.convert-to-int64')

        convert_uint_section = Gio.Menu.new()
        convert_uint_section.append(_('Change To Unsigned Integer _8'), 'app.convert-to-uint8')
        convert_uint_section.append(_('Change To Unsigned Integer _16'), 'app.convert-to-uint16')
        convert_uint_section.append(_('Change To Unsigned Integer _32'), 'app.convert-to-uint32')
        convert_uint_section.append(_('Change To Unsigned Integer _64'), 'app.convert-to-uint64')

        convert_float_section = Gio.Menu.new()
        convert_float_section.append(_('Change To Float _32'), 'app.convert-to-float32')
        convert_float_section.append(_('Change To Float _64'), 'app.convert-to-float64')

        convert_date_time_menu = Gio.Menu.new()
        convert_date_time_menu.append(_('Change To _Date'), 'app.convert-to-date')
        convert_date_time_menu.append(_('Change To _Time'), 'app.convert-to-time')
        convert_date_time_menu.append(_('Change To D_atetime'), 'app.convert-to-datetime')

        convert_menu = Gio.Menu.new()
        convert_menu.append_section(None, convert_basic_section)
        convert_menu.append_section(None, convert_date_time_menu)
        convert_menu.append_section(None, convert_int_section)
        convert_menu.append_section(None, convert_uint_section)
        convert_menu.append_section(None, convert_float_section)

        convert_menu_item = Gio.MenuItem.new(_('_Change Type'), None)
        convert_menu_item.set_submenu(convert_menu)
        convert_transform_section.append_item(convert_menu_item)

        transform_cell_menu = Gio.Menu.new()

        transform_cell_menu.append(_('Append Text Prefix...'), 'app.append-prefix-to-cell')
        transform_cell_menu.append(_('Append Text Suffix...'), 'app.append-suffix-to-cell')
        transform_cell_menu.append(_('Change Case to Camel Case (camelCase)'), 'app.change-cell-case-to-camel-case')
        transform_cell_menu.append(_('Change Case to Constant Case (CONSTANT_CASE)'), 'app.change-cell-case-to-constant-case')
        transform_cell_menu.append(_('Change Case to Dot Case (dot.case)'), 'app.change-cell-case-to-dot-case')
        transform_cell_menu.append(_('Change Case to Kebab Case (kebab-case)'), 'app.change-cell-case-to-kebab-case')
        transform_cell_menu.append(_('Change Case to Lowercase'), 'app.change-cell-case-to-lowercase')
        transform_cell_menu.append(_('Change Case to Pascal Case (PascalCase)'), 'app.change-cell-case-to-pascal-case')
        transform_cell_menu.append(_('Change Case to Snake Case (snake_case)'), 'app.change-cell-case-to-snake-case')
        transform_cell_menu.append(_('Change Case to Sentence Case (Sentence case)'), 'app.change-cell-case-to-sentence-case')
        transform_cell_menu.append(_('Change Case to Sponge Case (RANdoM CAPiTAlizAtiON)'), 'app.change-cell-case-to-sponge-case')
        transform_cell_menu.append(_('Change Case to Title Case (Capitalize Each Word)'), 'app.change-cell-case-to-title-case')
        transform_cell_menu.append(_('Change Case to Uppercase'), 'app.change-cell-case-to-uppercase')
        transform_cell_menu.append(_('Convert to NFC Unicode Normalization Form'), 'app.convert-cell-to-unicode-normalization-nfc')
        transform_cell_menu.append(_('Convert to NFD Unicode Normalization Form'), 'app.convert-cell-to-unicode-normalization-nfd')
        transform_cell_menu.append(_('Convert to NFKC Unicode Normalization Form'), 'app.convert-cell-to-unicode-normalization-nfkc')
        transform_cell_menu.append(_('Convert to NFKD Unicode Normalization Form'), 'app.convert-cell-to-unicode-normalization-nfkd')
        transform_cell_menu.append(_('Decode Base64 Text'), 'app.decode-base64-cell-text')
        transform_cell_menu.append(_('Decode Hexadecimal Text'), 'app.decode-hexadecimal-cell-text')
        transform_cell_menu.append(_('Decode URL Text'), 'app.decode-url-cell-text')
        transform_cell_menu.append(_('Encode Base64 Text'), 'app.encode-base64-cell-text')
        transform_cell_menu.append(_('Encode Hexadecimal Text'), 'app.encode-hexadecimal-cell-text')
        transform_cell_menu.append(_('Encode URL Text'), 'app.encode-url-cell-text')
        transform_cell_menu.append(_('Pad End (Right) with Custom Character...'), 'app.pad-end-cell-with-custom-string')
        transform_cell_menu.append(_('Pad End (Right) with Whitespace'), 'app.pad-end-cell')
        transform_cell_menu.append(_('Pad Start (Left) with Custom Character...'), 'app.pad-start-cell-with-custom-string')
        transform_cell_menu.append(_('Pad Start (Left) with Whitespace'), 'app.pad-start-cell')
        transform_cell_menu.append(_('Pig Latinnify'), 'app.pig-latinnify-cell')
        transform_cell_menu.append(_('Remove Prefix (Case Insensitive)...'), 'app.remove-prefix-from-cell-case-insensitive')
        transform_cell_menu.append(_('Remove Prefix (Case Sensitive)...'), 'app.remove-prefix-from-cell-case-sensitive')
        transform_cell_menu.append(_('Remove Suffix (Case Insensitive)...'), 'app.remove-suffix-from-cell-case-insensitive')
        transform_cell_menu.append(_('Remove Suffix (Case Sensitive)...'), 'app.remove-suffix-from-cell-case-sensitive')
        transform_cell_menu.append(_('Remove New-Lines Characters'), 'app.remove-cell-new-lines-characters')
        transform_cell_menu.append(_('Remove Whitespace Characters'), 'app.remove-cell-whitespace-characters')
        transform_cell_menu.append(_('Replace Text Value (Case Insensitive)...'), 'app.replace-cell-values-case-insensitive')
        transform_cell_menu.append(_('Replace Text Value with Regex (Case Insensitive)...'), 'app.replace-cell-values-case-insensitive-with-regex')
        transform_cell_menu.append(_('Replace Text Value (Case Sensitive)...'), 'app.replace-cell-values-case-sensitive')
        transform_cell_menu.append(_('Replace Text Value with Regex (Case Sensitive)...'), 'app.replace-cell-values-case-sensitive-with-regex')
        transform_cell_menu.append(_('Replace Whitespace with a Single Space'), 'app.replace-cell-whitespace-with-a-single-space')
        transform_cell_menu.append(_('Replace Whitespace & New-Lines with a Single Space'), 'app.replace-cell-whitespace-and-new-lines-with-a-single-space')
        transform_cell_menu.append(_('Reverse Text'), 'app.reverse-text-cell')
        transform_cell_menu.append(_('Slugify'), 'app.slugify-cell')
        transform_cell_menu.append(_('Split Text by Comma & Collect Into New Worksheet'), 'app.split-cell-by-comma-into-new-worksheet')
        transform_cell_menu.append(_('Split Text by a Set of Characters & Collect Into New Worksheet...'), 'app.split-cell-by-characters-into-new-worksheet')
        transform_cell_menu.append(_('Split Text by Pipe & Collect Into New Worksheet'), 'app.split-cell-by-pipe-into-new-worksheet')
        transform_cell_menu.append(_('Split Text by Semicolon & Collect Into New Worksheet'), 'app.split-cell-by-semicolon-into-new-worksheet')
        transform_cell_menu.append(_('Split Text by Whitespace & Collect Into New Worksheet'), 'app.split-cell-by-space-into-new-worksheet')
        transform_cell_menu.append(_('Swap Text Case'), 'app.swap-cell-text-case')
        transform_cell_menu.append(_('Trim Leading & Trailing Whitespace'), 'app.trim-cell-whitespace')
        transform_cell_menu.append(_('Trim Whitespace & Remove Newlines'), 'app.trim-cell-whitespace-and-remove-new-lines')
        transform_cell_menu.append(_('Trim Leading Whitespace'), 'app.trim-cell-start-whitespace')
        transform_cell_menu.append(_('Trim Trailing Whitespace'), 'app.trim-cell-end-whitespace')
        transform_cell_menu.append(_('Wrap with Text (Different Prefix and Suffix)...'), 'app.wrap-cell-with-text-different')
        transform_cell_menu.append(_('Wrap with Text (Same Prefix and Suffix)...'), 'app.wrap-cell-with-text-same')

        transform_column_menu = Gio.Menu.new()

        transform_column_menu.append(_('Append Text Prefix...'), 'app.append-prefix-to-column')
        transform_column_menu.append(_('Append Text Suffix...'), 'app.append-suffix-to-column')
        transform_column_menu.append(_('Change Case to Camel Case (camelCase)'), 'app.change-column-case-to-camel-case')
        transform_column_menu.append(_('Change Case to Constant Case (CONSTANT_CASE)'), 'app.change-column-case-to-constant-case')
        transform_column_menu.append(_('Change Case to Dot Case (dot.case)'), 'app.change-column-case-to-dot-case')
        transform_column_menu.append(_('Change Case to Kebab Case (kebab-case)'), 'app.change-column-case-to-kebab-case')
        transform_column_menu.append(_('Change Case to Lowercase'), 'app.change-column-case-to-lowercase')
        transform_column_menu.append(_('Change Case to Pascal Case (PascalCase)'), 'app.change-column-case-to-pascal-case')
        transform_column_menu.append(_('Change Case to Snake Case (snake_case)'), 'app.change-column-case-to-snake-case')
        transform_column_menu.append(_('Change Case to Sentence Case (Sentence case)'), 'app.change-column-case-to-sentence-case')
        transform_column_menu.append(_('Change Case to Sponge Case (RANdoM CAPiTAlizAtiON)'), 'app.change-column-case-to-sponge-case')
        transform_column_menu.append(_('Change Case to Title Case (Capitalize Each Word)'), 'app.change-column-case-to-title-case')
        transform_column_menu.append(_('Change Case to Uppercase'), 'app.change-column-case-to-uppercase')
        transform_column_menu.append(_('Convert to NFC Unicode Normalization Form'), 'app.convert-column-to-unicode-normalization-nfc')
        transform_column_menu.append(_('Convert to NFD Unicode Normalization Form'), 'app.convert-column-to-unicode-normalization-nfd')
        transform_column_menu.append(_('Convert to NFKC Unicode Normalization Form'), 'app.convert-column-to-unicode-normalization-nfkc')
        transform_column_menu.append(_('Convert to NFKD Unicode Normalization Form'), 'app.convert-column-to-unicode-normalization-nfkd')
        transform_column_menu.append(_('Decode Base64 Text'), 'app.decode-base64-column-text')
        transform_column_menu.append(_('Decode Hexadecimal Text'), 'app.decode-hexadecimal-column-text')
        transform_column_menu.append(_('Decode URL Text'), 'app.decode-url-column-text')
        transform_column_menu.append(_('Encode Base64 Text'), 'app.encode-base64-column-text')
        transform_column_menu.append(_('Encode Hexadecimal Text'), 'app.encode-hexadecimal-column-text')
        transform_column_menu.append(_('Encode URL Text'), 'app.encode-url-column-text')
        transform_column_menu.append(_('Pad End (Right) with Custom Character...'), 'app.pad-end-column-with-custom-string')
        transform_column_menu.append(_('Pad End (Right) with Whitespace'), 'app.pad-end-column')
        transform_column_menu.append(_('Pad Start (Left) with Custom Character...'), 'app.pad-start-column-with-custom-string')
        transform_column_menu.append(_('Pad Start (Left) with Whitespace'), 'app.pad-start-column')
        transform_column_menu.append(_('Pig Latinnify'), 'app.pig-latinnify-column')
        transform_column_menu.append(_('Remove Prefix (Case Insensitive)...'), 'app.remove-prefix-from-column-case-insensitive')
        transform_column_menu.append(_('Remove Prefix (Case Sensitive)...'), 'app.remove-prefix-from-column-case-sensitive')
        transform_column_menu.append(_('Remove Suffix (Case Insensitive)...'), 'app.remove-suffix-from-column-case-insensitive')
        transform_column_menu.append(_('Remove Suffix (Case Sensitive)...'), 'app.remove-suffix-from-column-case-sensitive')
        transform_column_menu.append(_('Remove New-Lines Characters'), 'app.remove-column-new-lines-characters')
        transform_column_menu.append(_('Remove Whitespace Characters'), 'app.remove-column-whitespace-characters')
        transform_column_menu.append(_('Replace Text Value (Case Insensitive)...'), 'app.replace-column-values-case-insensitive')
        transform_column_menu.append(_('Replace Text Value with Regex (Case Insensitive)...'), 'app.replace-column-values-case-insensitive-with-regex')
        transform_column_menu.append(_('Replace Text Value (Case Sensitive)...'), 'app.replace-column-values-case-sensitive')
        transform_column_menu.append(_('Replace Text Value with Regex (Case Sensitive)...'), 'app.replace-column-values-case-sensitive-with-regex')
        transform_column_menu.append(_('Replace Whitespace with a Single Space'), 'app.replace-column-whitespace-with-a-single-space')
        transform_column_menu.append(_('Replace Whitespace & New-Lines with a Single Space'), 'app.replace-column-whitespace-and-new-lines-with-a-single-space')
        transform_column_menu.append(_('Reverse Text'), 'app.reverse-text-column')
        transform_column_menu.append(_('Slugify'), 'app.slugify-column')
        transform_column_menu.append(_('Split Text by Comma & Collect Into New Worksheet'), 'app.split-column-by-comma-into-new-worksheet')
        transform_column_menu.append(_('Split Text by a Set of Characters & Collect Into New Worksheet...'), 'app.split-column-by-characters-into-new-worksheet')
        transform_column_menu.append(_('Split Text by Pipe & Collect Into New Worksheet'), 'app.split-column-by-pipe-into-new-worksheet')
        transform_column_menu.append(_('Split Text by Semicolon & Collect Into New Worksheet'), 'app.split-column-by-semicolon-into-new-worksheet')
        transform_column_menu.append(_('Split Text by Whitespace & Collect Into New Worksheet'), 'app.split-column-by-space-into-new-worksheet')
        transform_column_menu.append(_('Swap Text Case'), 'app.swap-column-text-case')
        transform_column_menu.append(_('Trim Leading & Trailing Whitespace'), 'app.trim-column-whitespace')
        transform_column_menu.append(_('Trim Whitespace & Remove Newlines'), 'app.trim-column-whitespace-and-remove-new-lines')
        transform_column_menu.append(_('Trim Leading Whitespace'), 'app.trim-column-start-whitespace')
        transform_column_menu.append(_('Trim Trailing Whitespace'), 'app.trim-column-end-whitespace')
        transform_column_menu.append(_('Wrap with Text (Different Prefix and Suffix)...'), 'app.wrap-column-with-text-different')
        transform_column_menu.append(_('Wrap with Text (Same Prefix and Suffix)...'), 'app.wrap-column-with-text-same')

        transform_menu_item = Gio.MenuItem.new(_('_Transform'), None)
        if ctype in [SheetCornerLocatorCell, SheetTopLocatorCell]:
            transform_menu_item.set_submenu(transform_column_menu)
        else:
            transform_menu_item.set_submenu(transform_cell_menu)
        convert_transform_section.append_item(transform_menu_item)