# sheet_header_menu.py
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

from gi.repository import GLib, GObject, Gtk, Pango
import copy
import polars
import threading

from .window import Window

class BasicFilterListItem(GObject.Object):
    __gtype_name__ = 'BasicFilterListItem'

    cvalue = GObject.Property(type=str, default='[Blank]')
    active = GObject.Property(type=bool, default=False)
    inconsistent = GObject.Property(type=bool, default=False)
    mvalue = GObject.Property(type=str, default='')

    def __init__(self,
                 cvalue:       str,
                 active:       bool,
                 inconsistent: bool = False,
                 mvalue:       str = '') -> None:
        super().__init__()

        self.cvalue = cvalue
        self.active = active
        self.inconsistent = inconsistent
        self.mvalue = mvalue



_MAX_NO_UNIQUE_ITEMS = 20_000

_basic_filter_list_items_pool = []

for i in range(_MAX_NO_UNIQUE_ITEMS):
    _basic_filter_list_items_pool.append(BasicFilterListItem('[Blank]', False))



@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-header-menu.ui')
class SheetHeaderMenu(Gtk.PopoverMenu):
    __gtype_name__ = 'SheetHeaderMenu'

    filter_search_box = Gtk.Template.Child()
    filter_search_entry = Gtk.Template.Child()
    filter_use_regexp = Gtk.Template.Child()

    filter_status = Gtk.Template.Child()
    filter_continue = Gtk.Template.Child()

    filter_list_view = Gtk.Template.Child()
    filter_list_store = Gtk.Template.Child()

    def __init__(self,
                 window:      Window,
                 column:      int,
                 dfi:         int,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window
        self.column = column
        self.dfi = dfi

        sheet_document = self.window.get_current_active_document()

        column_name = sheet_document.data.dfs[dfi].columns[self.column]

        self.cvalues_to_show: list[str] = ['$all']
        self.cvalues_to_hide: list[str] = []

        # Get the current active filters if any, otherwise initialize the default filters
        for cfilter in sheet_document.current_filters:
            if cfilter['qtype'] != 'primitive':
                continue

            condition = cfilter['query-builder']['conditions'][0]

            if condition['field'] == column_name:
                if condition['operator'] == 'in':
                    self.cvalues_to_show = copy.deepcopy(condition['value'])
                    self.cvalues_to_hide = ['$all']

                if condition['operator'] == 'not in':
                    self.cvalues_to_show = ['$all']
                    self.cvalues_to_hide = copy.deepcopy(condition['value'])

                if condition['operator'] == '=':
                    self.cvalues_to_show = [condition['value']]
                    self.cvalues_to_hide = ['$all']

                if condition['operator'] == '!=':
                    self.cvalues_to_show = ['$all']
                    self.cvalues_to_hide = [condition['value']]

                break

        self.all_unique_values_hash = polars.Series([])
        self.current_unique_values_hash = polars.Series([])

        self.is_manually_toggling = False

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory_check_button)
        factory.connect('bind', self.bind_factory_check_button)
        factory.connect('teardown', self.teardown_factory_check_button)
        self.filter_list_view.set_factory(factory)

        self.populate_filter_list()

    def setup_factory_check_button(self,
                                   list_item_factory: Gtk.SignalListItemFactory,
                                   list_item:         Gtk.ListItem) -> None:
        check_button = Gtk.CheckButton()
        list_item.set_child(check_button)

        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        check_button.set_child(label)

        list_item.check_button = check_button
        list_item.label = label

        list_item.bind_active = None
        list_item.bind_inconsistent = None
        list_item.bind_toggled = None

    def bind_factory_check_button(self,
                                  list_item_factory: Gtk.SignalListItemFactory,
                                  list_item:         Gtk.ListItem) -> None:
        item_data = list_item.get_item()

        if list_item.bind_active is not None:
            list_item.bind_active.unbind()

        if list_item.bind_inconsistent is not None:
            list_item.bind_inconsistent.unbind()

        if list_item.bind_toggled is not None:
            list_item.check_button.disconnect(list_item.bind_toggled)

        list_item.bind_active = item_data.bind_property('active', list_item.check_button,
                                                        'active', GObject.BindingFlags.SYNC_CREATE)

        list_item.bind_inconsistent = item_data.bind_property('inconsistent', list_item.check_button,
                                                              'inconsistent', GObject.BindingFlags.SYNC_CREATE)

        list_item.bind_toggled = list_item.check_button.connect('toggled', self.on_filter_list_item_check_button_toggled,
                                                                item_data)

        list_item.label.set_label(item_data.cvalue[:40])

    def teardown_factory_check_button(self,
                                      list_item_factory: Gtk.SignalListItemFactory,
                                      list_item: Gtk.ListItem) -> None:
        list_item.bind_active = None
        list_item.bind_inconsistent = None
        list_item.bind_toggled = None

        list_item.check_button = None
        list_item.label = None

    def on_filter_list_item_check_button_toggled(self,
                                                 button:    Gtk.Button,
                                                 item_data: BasicFilterListItem) -> None:
        if self.is_manually_toggling:
            return
        self.is_manually_toggling = True

        # Update the active flag
        item_data.active = button.get_active()

        # Update the cvalues flags
        if item_data.mvalue == '$all':
            if item_data.active:
                self.cvalues_to_show = ['$all']
                self.cvalues_to_hide = []
            else:
                self.cvalues_to_show = []
                self.cvalues_to_hide = ['$all']
            for idata in self.filter_list_store:
                if idata.mvalue == '$all':
                    continue
                idata.active = item_data.active
            item_data.inconsistent = False

        elif item_data.mvalue == '$results':
            for idata in self.filter_list_store:
                if idata.mvalue in ['$all', '$results']:
                    continue
                if item_data.active:
                    self.cvalues_to_show.append(idata.cvalue)
                    if idata.cvalue in self.cvalues_to_hide:
                        self.cvalues_to_hide.remove(idata.cvalue)
                else:
                    self.cvalues_to_hide.append(idata.cvalue)
                    if idata.cvalue in self.cvalues_to_show:
                        self.cvalues_to_show.remove(idata.cvalue)
                idata.active = item_data.active

        elif item_data.mvalue == '$blanks':
            if item_data.active:
                if '$blanks' in self.cvalues_to_hide:
                    self.cvalues_to_hide.remove('$blanks')
                if '$all' not in self.cvalues_to_show:
                    self.cvalues_to_show.append('$blanks')
            else:
                if '$blanks' in self.cvalues_to_show:
                    self.cvalues_to_show.remove('$blanks')
                if '$all' not in self.cvalues_to_hide:
                    self.cvalues_to_hide.append('$blanks')

        else:
            if item_data.active:
                if item_data.cvalue in self.cvalues_to_hide:
                    self.cvalues_to_hide.remove(item_data.cvalue)
                if '$all' not in self.cvalues_to_show:
                    self.cvalues_to_show.append(item_data.cvalue)
            else:
                if item_data.cvalue in self.cvalues_to_show:
                    self.cvalues_to_show.remove(item_data.cvalue)
                if '$all' not in self.cvalues_to_hide:
                    self.cvalues_to_hide.append(item_data.cvalue)

        # Try to clean up the cvalues flags. This won't be very accurate especially
        # when there are too many of unique values in which we decided not to track
        # all of them for memory efficiency reasons. But hey, after all the user is
        # discouraged from using this feature to filter the dataframe in that case.
        if '$all' in self.cvalues_to_show and len(self.cvalues_to_hide) == 0:
            self.cvalues_to_show = ['$all']
            self.cvalues_to_hide = []
            self.filter_list_store.get_item(0).active = True
            self.filter_list_store.get_item(0).inconsistent = False

        elif '$all' in self.cvalues_to_hide and len(self.cvalues_to_show) == 0:
            self.cvalues_to_show = []
            self.cvalues_to_hide = ['$all']
            self.filter_list_store.get_item(0).active = False
            self.filter_list_store.get_item(0).inconsistent = False

        else:
            cvalues_to_show = list(set(self.cvalues_to_show) - {'$blanks'})
            cvalues_to_hide = list(set(self.cvalues_to_hide) - {'$blanks'})
            cvalues_to_show_hash = polars.Series(cvalues_to_show).sort().hash()
            cvalues_to_hide_hash = polars.Series(cvalues_to_hide).sort().hash()

            if '$all' in cvalues_to_show and cvalues_to_hide_hash.equals(self.all_unique_values_hash):
                self.cvalues_to_show = []
                self.cvalues_to_hide = ['$all']
                self.filter_list_store.get_item(0).active = False
                self.filter_list_store.get_item(0).inconsistent = False

            elif '$all' in cvalues_to_hide and cvalues_to_show_hash.equals(self.all_unique_values_hash):
                self.cvalues_to_show = ['$all']
                self.cvalues_to_hide = []
                self.filter_list_store.get_item(0).active = True
                self.filter_list_store.get_item(0).inconsistent = False

            else:
                self.filter_list_store.get_item(0).inconsistent = True

        # Update the 'Select All Results' state. For simplicity, we don't play with
        # the 'inconsistent' flag for this item.
        if self.filter_list_store.get_item(1).mvalue == '$results':
            if '$all' in self.cvalues_to_show and len(self.cvalues_to_hide) == 0:
                self.filter_list_store.get_item(1).active = True

            elif '$all' in self.cvalues_to_hide and len(self.cvalues_to_show) == 0:
                self.filter_list_store.get_item(1).active = False

            elif cvalues_to_show_hash.equals(self.current_unique_values_hash):
                self.filter_list_store.get_item(1).active = True

            elif cvalues_to_hide_hash.equals(self.current_unique_values_hash):
                self.filter_list_store.get_item(1).active = False

        sheet_document = self.window.get_current_active_document()
        column_name = sheet_document.data.dfs[self.dfi].columns[self.column]
        column_index = sheet_document.data.dfs[self.dfi].columns.index(column_name)
        column_dtype = sheet_document.data.dfs[self.dfi].schema[column_name]

        # Build the query blocks
        operator = 'not in'
        value = copy.deepcopy(self.cvalues_to_hide)

        if '$all' in self.cvalues_to_hide:
            operator = 'in'
            value = copy.deepcopy(self.cvalues_to_show)

        if '$blanks' in value:
            value.remove('$blanks')
            value.append(None)

        if len(value) == 1:
            if operator == 'in':
                operator = '='
            else:
                operator = '!='
            value = value[0]

        query_builder = {
            'operator': 'and',
            'conditions': [{
                'findex': column_index,
                'fdtype': column_dtype,
                'field': column_name,
                'operator': operator,
                'value': value,
            }],
        }

        if not isinstance(value, list):
            value = [value]

        value = copy.deepcopy(value)
        value = polars.Series(value).cast(column_dtype, strict=False)

        expression = polars.col(column_name).is_in(value)
        if operator in ['not in', '!=']:
            expression = expression.not_()

        # Update the document's active filters
        sheet_document.pending_filters = [{
            'qhash': hash((column_name, 'array')),
            'qtype': 'primitive',
            'operator': 'and',
            'query-builder': query_builder,
            'expression': expression,
        }]

        self.is_manually_toggling = False

    @Gtk.Template.Callback()
    def on_filter_search_entry_activated(self, entry: Gtk.Entry) -> None:
        self.find_unique_values(search_query=entry.get_text())

    @Gtk.Template.Callback()
    def on_filter_continue_button_clicked(self, button: Gtk.Button) -> None:
        self.filter_continue.set_visible(False)
        self.find_unique_values(sample_only=True)

    def populate_filter_list(self) -> None:
        sheet_document = self.window.get_current_active_document()

        col_dtype = sheet_document.data.dfs[self.dfi].dtypes[self.column]

        if col_dtype != polars.String:
            self.filter_search_entry.set_placeholder_text("This isn't a text column.")
            self.filter_search_box.set_sensitive(False)

        n_unique_approx = sheet_document.data.read_cell_data_n_unique_approx_from_metadata(self.column, self.dfi)

        if _MAX_NO_UNIQUE_ITEMS < n_unique_approx \
                and not sheet_document.data.check_cell_data_unique_cache(self.column, self.dfi):
            self.filter_status.set_text('Found approximately {:,} unique values. '
                                        'Continue anyway?'.format(n_unique_approx))

            if col_dtype == polars.String:
                self.filter_status.set_text(f'{self.filter_status.get_text()} '
                                            f'Or use the search box to narrow down the result set.')
            else:
                self.filter_status.set_text(f'{self.filter_status.get_text()} '
                                            f'Or use the custom filter to narrow down the result set.')

            self.filter_continue.set_visible(True)

            return

        self.find_unique_values()

    def find_unique_values(self,
                           sample_only: bool = False,
                           search_query: str = None) -> None:
        if search_query == '':
            search_query = None

        use_regexp = self.filter_use_regexp.get_active()

        sheet_document = self.window.get_current_active_document()

        n_unique = sheet_document.data.read_cell_data_n_unique_from_metadata(self.column,
                                                                             0,
                                                                             search_query,
                                                                             use_regexp)
        self.filter_status.set_text('Found {:,} unique values'.format(n_unique))

        self.filter_continue.set_visible(False)

        if _MAX_NO_UNIQUE_ITEMS < n_unique:
            self.filter_status.set_text(f'{self.filter_status.get_text()}. '
                                        'The result set only contains a subset of the unique values.')
            sample_only = True # force sampling

        def show_filter_list() -> None:
            list_items_to_add = []

            # Add the "Select All" option
            active = '$all' in self.cvalues_to_show or len(self.cvalues_to_show) > 0
            consistent = ('$all' in self.cvalues_to_show and len(self.cvalues_to_hide) == 0) or \
                         ('$all' in self.cvalues_to_hide and len(self.cvalues_to_show) == 0)
            list_item = BasicFilterListItem('Select All', active, not consistent, '$all')
            list_items_to_add.append(list_item)

            unique_values = sheet_document.data.read_cell_data_unique_from_metadata(self.column,
                                                                                    0,
                                                                                    sample_only,
                                                                                    search_query,
                                                                                    use_regexp)

            # Store the unique values hash for tracking changes
            if search_query is None or self.all_unique_values_hash.shape[0] == 0:
                self.all_unique_values_hash = unique_values.hash()
            self.current_unique_values_hash = unique_values.hash()

            item_counter = 0
            blank_option_added = False
            all_results_actived = True

            cvalues_to_hide = set(self.cvalues_to_hide)
            cvalues_to_show = set(self.cvalues_to_show)

            for cvalue in unique_values:
                if item_counter == _MAX_NO_UNIQUE_ITEMS:
                    break

                if cvalue in [None, '']:
                    if blank_option_added:
                        continue # in case we have already added the same item
                    active = ('$blanks' in cvalues_to_show and '$all' in cvalues_to_hide) or \
                             ('$blanks' not in cvalues_to_hide and '$all' in cvalues_to_show)
                    all_results_actived &= active
                    list_item = BasicFilterListItem('(Blanks)', active, mvalue='$blanks')
                    list_items_to_add.insert(1, list_item)
                    continue

                cvalue = str(cvalue)
                active = (cvalue in cvalues_to_show and '$all' in cvalues_to_hide) or \
                         (cvalue not in cvalues_to_hide and '$all' in cvalues_to_show)
                all_results_actived &= active
                list_item = _basic_filter_list_items_pool[item_counter]
                list_item.set_property('cvalue', cvalue)
                list_item.set_property('active', active)
                list_items_to_add.append(list_item)
                item_counter += 1

            # Add the "Select All Results" option if necessary
            if search_query is not None:
                list_item = BasicFilterListItem('Select All Results', all_results_actived, mvalue='$results')
                list_items_to_add.insert(1, list_item)

            GLib.idle_add(self.filter_list_store.splice, 0, 0, list_items_to_add)

        # TODO: show a loading indicator
        self.filter_list_store.remove_all()
        if n_unique > 0:
            threading.Thread(target=show_filter_list, daemon=True).start()