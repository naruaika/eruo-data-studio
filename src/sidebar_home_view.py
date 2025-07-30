# sidebar_home_view.py
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


from gi.repository import Adw, Gio, GLib, GObject, Gtk, Pango
from datetime import datetime, timedelta
import polars

from . import utils
from .window import Window

class FieldListItem(GObject.Object):
    __gtype_name__ = 'FieldListItem'

    cindex = GObject.Property(type=int, default=1)
    cname = GObject.Property(type=str, default='column_1')
    dtype = GObject.Property(type=str, default='text')
    active = GObject.Property(type=bool, default=True)

    def __init__(self, cindex: int, cname: str, dtype: str, active: bool) -> None:
        super().__init__()

        self.cindex = cindex
        self.cname = cname
        self.dtype = dtype
        self.active = active



class SortListItem(GObject.Object):
    __gtype_name__ = 'SortListItem'

    cindex = GObject.Property(type=int, default=0)
    cname = GObject.Property(type=str, default='column_1')
    order = GObject.Property(type=str, default='Ascending')

    def __init__(self, cindex: int, cname: str, order: str) -> None:
        super().__init__()

        self.cindex = cindex
        self.cname = cname
        self.order = order



class FilterListItem(GObject.Object):
    __gtype_name__ = 'FilterListItem'

    # TODO: support for nested conditions?
    qtype = GObject.Property(type=str, default='basic')
    query = GObject.Property(type=str, default='')
    findex = GObject.Property(type=int, default=0)
    fdtype = GObject.Property(type=str, default='text')
    field = GObject.Property(type=str, default='column_1')
    operator = GObject.Property(type=str, default='equals')
    value: dict = {}

    def __init__(self, qtype: str, query: str, findex: int, fdtype: str, field: str, operator: str, value: dict) -> None:
        super().__init__()

        self.qtype = qtype
        self.query = query
        self.findex = findex
        self.fdtype = fdtype
        self.field = field
        self.operator = operator
        self.value = value



FILTER_BASIC_SCHEMA = {
    # GENERIC
    '='                           : [['$field', '$operator'], # row 1
                                     ['$value']],          # row 2, etc.
    '!='                          : [['$field', '$operator'],
                                     ['$value']],
    '<>'                          : [['$field', '$operator'],
                                     ['$value']],
    'equals'                      : [['$field', '$operator'],
                                     ['$value']],
    'does not equal'              : [['$field', '$operator'],
                                     ['$value']],
    'is null'                     : [['$field', '$operator']],
    'is not null'                 : [['$field', '$operator']],

    # TEXT
    'begins with'                 : [['$field', '$operator'],
                                     ['$value']],
    'does not begin with'         : [['$field', '$operator'],
                                     ['$value']],
    'ends with'                   : [['$field', '$operator'],
                                     ['$value']],
    'does not end with'           : [['$field', '$operator'],
                                     ['$value']],
    'contains'                    : [['$field', '$operator'],
                                     ['$value']],
    'does not contain'            : [['$field', '$operator'],
                                     ['$value']],

    # NUMERIC
    '>'                           : [['$field', '$operator'],
                                     ['$value']],
    '>='                          : [['$field', '$operator'],
                                     ['$value']],
    '<'                           : [['$field', '$operator'],
                                     ['$value']],
    '<='                          : [['$field', '$operator'],
                                     ['$value']],
    'is greater than'             : [['$field', '$operator'],
                                     ['$value']],
    'is greater than or equal to' : [['$field', '$operator'],
                                     ['$value']],
    'is less than'                : [['$field', '$operator'],
                                     ['$value']],
    'is less than or equal to'    : [['$field', '$operator'],
                                     ['$value']],
    'is between'                  : [['$field', '$operator'],
                                     ['$value', '$value']],
    'is not between'              : [['$field', '$operator'],
                                     ['$value', '$value']],
    'above average'               : [['$field', '$operator']],
    'below average'               : [['$field', '$operator']],

    # TEMPORAL
    'before'                      : [['$field', '$operator'],
                                     ['$value']],
    'after'                       : [['$field', '$operator'],
                                     ['$value']],
    'between'                     : [['$field', '$operator'],
                                     ['$value', '$value']],
    'tomorrow'                    : [['$field', '$operator']],
    'today'                       : [['$field', '$operator']],
    'yesterday'                   : [['$field', '$operator']],
    'next week'                   : [['$field', '$operator']],
    'this week'                   : [['$field', '$operator']],
    'last week'                   : [['$field', '$operator']],
    'next month'                  : [['$field', '$operator']],
    'this month'                  : [['$field', '$operator']],
    'last month'                  : [['$field', '$operator']],
    'next quarter'                : [['$field', '$operator']],
    'this quarter'                : [['$field', '$operator']],
    'last quarter'                : [['$field', '$operator']],
    'next year'                   : [['$field', '$operator']],
    'this year'                   : [['$field', '$operator']],
    'last year'                   : [['$field', '$operator']],
    'quarter 1'                   : [['$field', '$operator']],
    'quarter 2'                   : [['$field', '$operator']],
    'quarter 3'                   : [['$field', '$operator']],
    'quarter 4'                   : [['$field', '$operator']],
    'january'                     : [['$field', '$operator']],
    'february'                    : [['$field', '$operator']],
    'march'                       : [['$field', '$operator']],
    'april'                       : [['$field', '$operator']],
    'may'                         : [['$field', '$operator']],
    'june'                        : [['$field', '$operator']],
    'july'                        : [['$field', '$operator']],
    'august'                      : [['$field', '$operator']],
    'september'                   : [['$field', '$operator']],
    'october'                     : [['$field', '$operator']],
    'november'                    : [['$field', '$operator']],
    'december'                    : [['$field', '$operator']],

    # CUSTOM (SQL)
    'custom'                      : [['$operator'],
                                     ['$custom']],
}



FILTER_BASIC_OPTION = {
    'generic' : [
        'equals',
        'does not equal',
        'is null',
        'is not null',
    ],
    'text': [
        'begins with',
        'does not begin with',
        'ends with',
        'does not end with',
        'contains',
        'does not contain',
    ],
    'numeric': [
        'is greater than',
        'is greater than or equal to',
        'is less than',
        'is less than or equal to',
        'is between',
        'is not between',
        'above average',
        'below average',
    ],
    'temporal': [
        'before',
        'after',
        'between',
        'tomorrow',
        'today',
        'yesterday',
        'next week',
        'this week',
        'last week',
        'next month',
        'this month',
        'last month',
        'next quarter',
        'this quarter',
        'last quarter',
        'next year',
        'this year',
        'last year',
        'quarter 1',
        'quarter 2',
        'quarter 3',
        'quarter 4',
        'january',
        'february',
        'march',
        'april',
        'may',
        'june',
        'july',
        'august',
        'september',
        'october',
        'november',
        'december',
    ],
}



def get_filter_basic_expression(item_data: FilterListItem, cvalues: list) -> polars.Expr:
    query = item_data.query
    field = item_data.field
    fdtype = item_data.fdtype
    operator = item_data.operator

    # Get the current date
    today = datetime.today().date()

    def get_quarter_start_end(date):
        year = date.year
        if 1 <= date.month <= 3:
            quarter_start = datetime(year, 1, 1).date()
            quarter_end = datetime(year, 3, 31).date()
        elif 4 <= date.month <= 6:
            quarter_start = datetime(year, 4, 1).date()
            quarter_end = datetime(year, 6, 30).date()
        elif 7 <= date.month <= 9:
            quarter_start = datetime(year, 7, 1).date()
            quarter_end = datetime(year, 9, 30).date()
        else: # 10 <= date.month <= 12
            quarter_start = datetime(year, 10, 1).date()
            quarter_end = datetime(year, 12, 31).date()
        return quarter_start, quarter_end

    # Calculate the start and end of the current quarter
    current_quarter_start, current_quarter_end = get_quarter_start_end(today)

    # Calculate the start and end of the next quarter
    next_month_for_quarter = (current_quarter_end + timedelta(days=1)).replace(day=1) + timedelta(days=60)
    next_quarter_start, next_quarter_end = get_quarter_start_end(next_month_for_quarter)

    # Calculate the start and end of the last quarter
    last_month_for_quarter = (current_quarter_start - timedelta(days=1)).replace(day=1) - timedelta(days=60)
    last_quarter_start, last_quarter_end = get_quarter_start_end(last_month_for_quarter)

    # Get the start and end of the current year
    this_year_start = datetime(today.year, 1, 1).date()
    this_year_end = datetime(today.year, 12, 31).date()

    # Get the start and end of the next year
    next_year_start = datetime(today.year + 1, 1, 1).date()
    next_year_end = datetime(today.year + 1, 12, 31).date()

    # Get the start and end of the last year
    last_year_start = datetime(today.year - 1, 1, 1).date()
    last_year_end = datetime(today.year - 1, 12, 31).date()

    # Calculate the start of the current week (Monday)
    this_week_start = today - timedelta(days=today.isoweekday() - 1)
    this_week_end = this_week_start + timedelta(days=6)

    # Calculate next week
    next_week_start = this_week_start + timedelta(weeks=1)
    next_week_end = this_week_end + timedelta(weeks=1)

    # Calculate last week
    last_week_start = this_week_start - timedelta(weeks=1)
    last_week_end = this_week_end - timedelta(weeks=1)

    # Calculate this month
    this_month_start = today.replace(day=1)
    if this_month_start.month == 12:
        this_month_end = datetime(this_month_start.year, 12, 31).date()
    else:
        this_month_end = this_month_start.replace(month=this_month_start.month + 1) - timedelta(days=1)

    # Calculate next month
    if this_month_start.month == 12:
        next_month_start = datetime(this_month_start.year + 1, 1, 1).date()
    else:
        next_month_start = this_month_start.replace(month=this_month_start.month + 1)
    if next_month_start.month == 12:
        next_month_end = datetime(next_month_start.year, 12, 31).date()
    else:
        next_month_end = next_month_start.replace(month=next_month_start.month + 1) - timedelta(days=1)

    # Calculate last month
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    match operator:
        # GENERIC
        case 'equals'                      : return polars.col(field).eq(cvalues[0]) if fdtype != 'text' else polars.col(field).str.to_lowercase().eq(cvalues[0].lower())
        case 'does not equal'              : return polars.col(field).ne(cvalues[0]) if fdtype != 'text' else polars.col(field).str.to_lowercase().ne(cvalues[0].lower())
        case 'is null'                     : return polars.col(field).is_null()
        case 'is not null'                 : return polars.col(field).is_not_null()

        # TEXT
        case 'begins with'                 : return polars.col(field).str.to_lowercase().str.starts_with(cvalues[0].lower())
        case 'does not begin with'         : return polars.col(field).str.to_lowercase().str.starts_with(cvalues[0].lower()).not_()
        case 'ends with'                   : return polars.col(field).str.to_lowercase().str.ends_with(cvalues[0].lower())
        case 'does not end with'           : return polars.col(field).str.to_lowercase().str.ends_with(cvalues[0].lower()).not_()
        case 'contains'                    : return polars.col(field).str.contains_any([cvalues[0]], ascii_case_insensitive=True)
        case 'does not contain'            : return polars.col(field).str.contains_any([cvalues[0]], ascii_case_insensitive=True).not_()

        # NUMERIC
        case 'is greater than'             : return polars.col(field).gt(cvalues[0])
        case 'is greater than or equal to' : return polars.col(field).ge(cvalues[0])
        case 'is less than'                : return polars.col(field).lt(cvalues[0])
        case 'is less than or equal to'    : return polars.col(field).le(cvalues[0])
        case 'is between'                  : return polars.col(field).ge(cvalues[0]).and_(polars.col(field).le(cvalues[1]))
        case 'is not between'              : return polars.col(field).lt(cvalues[0]).or_(polars.col(field).gt(cvalues[1]))
        case 'above average'               : return polars.col(field).gt(polars.col(field).mean())
        case 'below average'               : return polars.col(field).lt(polars.col(field).mean())

        # TEMPORAL
        case 'before'                      : return polars.col(field).dt.date().lt(cvalues[0])
        case 'after'                       : return polars.col(field).dt.date().gt(cvalues[0])
        case 'between'                     : return polars.col(field).dt.date().ge(cvalues[0]).and_(polars.col(field).dt.date().le(cvalues[1]))
        case 'tomorrow'                    : return polars.col(field).dt.date().eq(today + timedelta(days=1))
        case 'today'                       : return polars.col(field).dt.date().eq(today)
        case 'yesterday'                   : return polars.col(field).dt.date().eq(today - timedelta(days=1))
        case 'next week'                   : return polars.col(field).dt.date().ge(next_week_start).and_(polars.col(field).dt.date().le(next_week_end))
        case 'this week'                   : return polars.col(field).dt.date().ge(this_week_start).and_(polars.col(field).dt.date().le(this_week_end))
        case 'last week'                   : return polars.col(field).dt.date().ge(last_week_start).and_(polars.col(field).dt.date().le(last_week_end))
        case 'next month'                  : return polars.col(field).dt.date().ge(next_month_start).and_(polars.col(field).dt.date().le(next_month_end))
        case 'this month'                  : return polars.col(field).dt.date().ge(this_month_start).and_(polars.col(field).dt.date().le(this_month_end))
        case 'last month'                  : return polars.col(field).dt.date().ge(last_month_start).and_(polars.col(field).dt.date().le(last_month_end))
        case 'next quarter'                : return polars.col(field).dt.date().ge(next_quarter_start).and_(polars.col(field).dt.date().le(next_quarter_end))
        case 'this quarter'                : return polars.col(field).dt.date().ge(current_quarter_start).and_(polars.col(field).dt.date().le(current_quarter_end))
        case 'last quarter'                : return polars.col(field).dt.date().ge(last_quarter_start).and_(polars.col(field).dt.date().le(last_quarter_end))
        case 'next year'                   : return polars.col(field).dt.date().ge(next_year_start).and_(polars.col(field).dt.date().le(next_year_end))
        case 'this year'                   : return polars.col(field).dt.date().ge(this_year_start).and_(polars.col(field).dt.date().le(this_year_end))
        case 'last year'                   : return polars.col(field).dt.date().ge(last_year_start).and_(polars.col(field).dt.date().le(last_year_end))
        case 'quarter 1'                   : return polars.col(field).dt.month().is_in([ 1,  2,  3])
        case 'quarter 2'                   : return polars.col(field).dt.month().is_in([ 4,  5,  6])
        case 'quarter 3'                   : return polars.col(field).dt.month().is_in([ 7,  8,  9])
        case 'quarter 4'                   : return polars.col(field).dt.month().is_in([10, 11, 12])
        case 'january'                     : return polars.col(field).dt.month().eq(1)
        case 'february'                    : return polars.col(field).dt.month().eq(2)
        case 'march'                       : return polars.col(field).dt.month().eq(3)
        case 'april'                       : return polars.col(field).dt.month().eq(4)
        case 'may'                         : return polars.col(field).dt.month().eq(5)
        case 'june'                        : return polars.col(field).dt.month().eq(6)
        case 'july'                        : return polars.col(field).dt.month().eq(7)
        case 'august'                      : return polars.col(field).dt.month().eq(8)
        case 'september'                   : return polars.col(field).dt.month().eq(9)
        case 'october'                     : return polars.col(field).dt.month().eq(10)
        case 'november'                    : return polars.col(field).dt.month().eq(11)
        case 'december'                    : return polars.col(field).dt.month().eq(12)

        # CUSTOM
        case 'custom'                      : return polars.sql_expr(query)

    return polars.lit(True)



@Gtk.Template(resource_path='/com/macipra/eruo/ui/sidebar-home-view.ui')
class SidebarHomeView(Adw.Bin):
    __gtype_name__ = 'SidebarHomeView'

    field_list_status = Gtk.Template.Child()
    field_list_view = Gtk.Template.Child()
    field_list_store = Gtk.Template.Child()

    sort_list_view_box = Gtk.Template.Child()
    sort_list_status = Gtk.Template.Child()
    sort_list_view = Gtk.Template.Child()
    sort_list_status_label = Gtk.Template.Child()
    sort_list_status_add_button = Gtk.Template.Child()
    sort_list_store = Gtk.Template.Child()

    filter_list_view_box = Gtk.Template.Child()
    filter_list_status = Gtk.Template.Child()
    filter_list_view = Gtk.Template.Child()
    filter_list_status_label = Gtk.Template.Child()
    filter_list_status_add_button = Gtk.Template.Child()
    filter_list_store = Gtk.Template.Child()

    def __init__(self, window: Window, **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window


        # Setup the field section
        self.field_list_status.get_parent().set_activatable(False)
        self.field_list_view.get_parent().set_activatable(False)
        self.field_list_view.get_parent().set_visible(False)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory_field)
        factory.connect('bind', self.bind_factory_field)
        factory.connect('teardown', self.teardown_factory_field)
        self.field_list_view.set_factory(factory)


        # Setup the sort section
        self.sort_list_view_box.get_parent().set_activatable(False)
        self.sort_list_view_box.get_parent().set_visible(False)
        self.sort_list_status.get_parent().set_activatable(False)

        header_factory = Gtk.SignalListItemFactory()
        header_factory.connect('setup', self.setup_header_factory_sort)
        self.sort_list_view.set_header_factory(header_factory)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory_sort)
        factory.connect('bind', self.bind_factory_sort)
        factory.connect('teardown', self.teardown_factory_sort)
        self.sort_list_view.set_factory(factory)


        # Setup the filter section
        self.filter_list_view_box.get_parent().set_activatable(False)
        self.filter_list_view_box.get_parent().set_visible(False)
        self.filter_list_status.get_parent().set_activatable(False)

        header_factory = Gtk.SignalListItemFactory()
        header_factory.connect('setup', self.setup_header_factory_filter)
        self.filter_list_view.set_header_factory(header_factory)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory_filter)
        factory.connect('bind', self.bind_factory_filter)
        factory.connect('teardown', self.teardown_factory_filter)
        self.filter_list_view.set_factory(factory)

    #
    # Field section
    #

    def setup_factory_field(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        check_button = Gtk.CheckButton()
        list_item.set_child(check_button)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label_name = Gtk.Label()
        label_name.set_halign(Gtk.Align.START)
        label_name.set_hexpand(True)
        label_name.set_ellipsize(Pango.EllipsizeMode.END)

        label_type = Gtk.Label()
        label_type.set_halign(Gtk.Align.END)
        label_type.add_css_class('sidebar-list-item-badge')

        box.append(label_name)
        box.append(label_type)
        check_button.set_child(box)

        list_item.check_button = check_button
        list_item.label_name = label_name
        list_item.label_type = label_type

    def bind_factory_field(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        item_data = list_item.get_item()
        list_item.check_button.set_active(item_data.active)
        list_item.label_name.set_label(item_data.cname)
        list_item.label_type.set_label(item_data.dtype)

        def on_check_button_toggled(button: Gtk.Button, item_data: FieldListItem) -> None:
            item_data.active = button.get_active()

            sheet_document = self.window.get_current_active_document()
            sheet_document.is_refreshing_uis = True
            sheet_document.toggle_column_visibility(item_data.cindex, button.get_active())
            sheet_document.is_refreshing_uis = False

        list_item.check_button.connect('toggled', on_check_button_toggled, item_data)

    def teardown_factory_field(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        list_item.check_button = None
        list_item.label_name = None
        list_item.label_type = None

    def repopulate_field_list(self, dfi: int = 0) -> None:
        self.field_list_store.remove_all()

        sheet_document = self.window.get_current_active_document()

        if dfi < 0 or len(sheet_document.data.dfs) <= dfi:
            self.field_list_view.get_parent().set_visible(False)
            self.field_list_status.get_parent().set_visible(True)
            self.field_list_status.set_text('No table selected')
            return

        schema = sheet_document.data.dfs[dfi].schema
        bboxes = sheet_document.data.bbs[dfi]
        vflags = sheet_document.display.column_visibility_flags

        for cindex, cname in enumerate(schema):
            dtype = utils.get_dtype_symbol(schema[cname])
            active = vflags[bboxes.column + cindex - 1] if len(vflags) else True
            self.field_list_store.append(FieldListItem(cindex + 1, cname, dtype, active))

        self.repopulate_sort_list(dfi)

        is_empty = self.field_list_store.get_n_items() == 0
        self.field_list_view.get_parent().set_visible(not is_empty)
        self.field_list_status.get_parent().set_visible(is_empty)

        if self.field_list_store.get_n_items() == 0:
            self.field_list_status.set_text('No fields found')

    #
    # Sort section
    #

    def setup_header_factory_sort(self, list_item_factory: Gtk.SignalListItemFactory, list_header: Gtk.ListHeader) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(6)
        list_header.set_child(box)

        subbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        subbox.set_homogeneous(True)
        box.append(subbox)

        # Setup field label
        label = Gtk.Label()
        label.set_margin_start(6)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_label('Field')
        subbox.append(label)

        # Setup order label
        label = Gtk.Label()
        label.set_margin_start(6)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_label('Order')
        subbox.append(label)

        # Add a spacer to the right
        spacer = Gtk.Box()
        spacer.set_margin_end(28)
        box.append(spacer)

    def setup_factory_sort(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        list_item.set_focusable(False)
        list_item.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_bottom(3)
        box.set_spacing(6)
        list_item.set_child(box)

        subbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        subbox.set_homogeneous(True)
        subbox.add_css_class('linked')
        box.append(subbox)

        field_dropdown = self.create_field_dropdown()
        subbox.append(field_dropdown)

        order_dropdown = self.create_order_dropdown()
        subbox.append(order_dropdown)

        delete_button = self.create_delete_button()
        box.append(delete_button)

        list_item.field_dropdown = field_dropdown
        list_item.order_dropdown = order_dropdown
        list_item.delete_button = delete_button

    def bind_factory_sort(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:

        def on_field_selected(dropdown: Gtk.DropDown, pspec: GObject.ParamSpec, item_data: SortListItem) -> None:
            item_data.cindex = dropdown.get_selected_item().cindex
            item_data.cname = dropdown.get_selected_item().cname

        def on_order_selected(dropdown: Gtk.DropDown, pspec: GObject.ParamSpec, item_data: SortListItem) -> None:
            item_data.order = dropdown.get_selected_item().get_string()

        item_data = list_item.get_item()

        list_item.field_dropdown.set_selected(item_data.cindex)
        list_item.field_dropdown.connect('notify::selected-item', on_field_selected, item_data)

        order_position = 0 if item_data.order == 'Ascending' else 1
        list_item.order_dropdown.set_selected(order_position)
        list_item.order_dropdown.connect('notify::selected-item', on_order_selected, item_data)

        def on_delete_sort_button_clicked(button: Gtk.Button) -> None:
            self.on_delete_sort_button_clicked(button, list_item.get_position())

        list_item.delete_button.connect('clicked', on_delete_sort_button_clicked)

    def teardown_factory_sort(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        list_item.field_dropdown = None
        list_item.order_dropdown = None
        list_item.delete_button = None

    def on_delete_sort_button_clicked(self, button: Gtk.Button, position: int) -> None:
        self.sort_list_store.remove(position)

        if self.sort_list_store.get_n_items() == 0:
            self.sort_list_view_box.get_parent().set_visible(False)
            self.sort_list_status.get_parent().set_visible(True)
            self.sort_list_status_label.set_text('No sorts found')

    @Gtk.Template.Callback()
    def on_add_sort_button_clicked(self, button: Gtk.Button) -> None:
        selected_item = self.field_list_store.get_item(0)
        self.sort_list_store.append(SortListItem(selected_item.cindex - 1, selected_item.cname, 'Ascending'))

        self.sort_list_view_box.get_parent().set_visible(True)
        self.sort_list_status.get_parent().set_visible(False)

    @Gtk.Template.Callback()
    def on_delete_all_sort_button_clicked(self, button: Gtk.Button) -> None:
        self.sort_list_store.remove_all()

        self.sort_list_view_box.get_parent().set_visible(False)
        self.sort_list_status.get_parent().set_visible(True)
        self.sort_list_status_label.set_text('No sorts found')

    @Gtk.Template.Callback()
    def on_apply_sort_button_clicked(self, button: Gtk.Button) -> None:
        document = self.window.get_current_active_document()

        document.pending_sorts = {}
        for sort_item in self.sort_list_store:
            descending = sort_item.order == 'Descending'
            document.pending_sorts[sort_item.cname] = {'cindex': sort_item.cindex,
                                                       'descending': descending}

        document.is_refreshing_uis = True
        document.sort_current_rows(multiple=True)
        document.is_refreshing_uis = False

    def repopulate_sort_list(self, dfi: int = 0) -> None:
        self.sort_list_store.remove_all()

        sheet_document = self.window.get_current_active_document()

        if dfi < 0 or len(sheet_document.data.dfs) <= dfi:
            self.sort_list_view.get_parent().set_visible(False)
            self.sort_list_status.get_parent().set_visible(True)
            self.sort_list_status_label.set_text('No table selected')
            return

        column_names = sheet_document.data.dfs[dfi].columns

        for cname in sheet_document.current_sorts:
            cindex = column_names.index(cname)
            descending = sheet_document.current_sorts[cname]['descending']
            order = 'Descending' if descending else 'Ascending'
            self.sort_list_store.append(SortListItem(cindex, cname, order))

        is_empty = self.sort_list_store.get_n_items() == 0
        self.sort_list_view_box.get_parent().set_visible(not is_empty)
        self.sort_list_status.get_parent().set_visible(is_empty)

        if self.sort_list_store.get_n_items() == 0:
            self.sort_list_status_label.set_text('No sorts found')

    #
    # Filter section
    #

    def setup_header_factory_filter(self, list_item_factory: Gtk.SignalListItemFactory, list_header: Gtk.ListHeader) -> None:
        label = Gtk.Label()
        label.set_margin_start(6)
        label.set_margin_end(34)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_label('Condition')
        list_header.set_child(label)

    def setup_factory_filter(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        list_item.set_focusable(False)
        list_item.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_bottom(3)
        box.set_spacing(6)
        list_item.set_child(box)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.set_spacing(3)
        box.append(container)

        delete_button = self.create_delete_button()
        delete_button.set_valign(Gtk.Align.START)
        delete_button.set_size_request(-1, 28)
        box.append(delete_button)

        list_item.container = container
        list_item.delete_button = delete_button

    def bind_factory_filter(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:

        def on_filter_field_selected(dropdown: Gtk.DropDown, pspec: GObject.ParamSpec, item_data: FilterListItem) -> None:
            pstate = { 'findex': item_data.findex, }
            _, position = self.filter_list_store.find(item_data)
            item_data.findex = dropdown.get_selected_item().cindex - 1
            item_data.fdtype = dropdown.get_selected_item().dtype
            item_data.field = dropdown.get_selected_item().cname
            self.refresh_filter_list_item(position, pstate)

        def on_filter_value_changed(entry: Gtk.Entry, item_data: FilterListItem, value_index: int) -> None:
            item_data.value[value_index] = entry.get_text()

        def on_filter_operator_selected(dropdown: Gtk.DropDown, pspec: GObject.ParamSpec, item_data: FilterListItem) -> None:
            pstate = { 'operator': item_data.operator, }
            _, position = self.filter_list_store.find(item_data)
            item_data.operator = dropdown.get_selected_item().get_string()
            self.refresh_filter_list_item(position, pstate)

        item_data = list_item.get_item()

        if item_data.qtype == 'primitive':
            text_view = self.create_general_text_view(item_data.query)
            text_view.add_css_class('dimmed')
            text_view.set_editable(False)
            list_item.container.append(text_view)

        else:
            fdtype = item_data.fdtype
            if isinstance(fdtype, polars.DataType):
                fdtype = utils.get_dtype_class(fdtype)
                item_data.fdtype = fdtype

            value_index = 0

            # Generate a form input
            if item_data.operator in FILTER_BASIC_SCHEMA:
                for row in FILTER_BASIC_SCHEMA[item_data.operator]:
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                    box.set_homogeneous(True)
                    box.set_spacing(3)

                    for row_item in row:
                        # Field selector
                        if row_item == '$field':
                            fdropdown = self.create_field_dropdown()
                            fdropdown.set_selected(item_data.findex)
                            fdropdown.connect('notify::selected-item', on_filter_field_selected, item_data)
                            box.append(fdropdown)

                        # Value input
                        elif row_item == '$value':
                            entry = Gtk.Entry()
                            entry.set_hexpand(True)
                            if value_index < len(item_data.value):
                                entry.set_text(str(item_data.value[value_index]))
                            else:
                                item_data.value[value_index] = ''
                            entry.connect('changed', on_filter_value_changed, item_data, value_index)
                            box.append(entry)
                            value_index += 1

                        # Custom input
                        elif row_item == '$custom':
                            text_view = self.create_general_text_view(item_data.query)
                            text_view.get_buffer().bind_property('text', item_data, 'query', GObject.BindingFlags.DEFAULT)
                            box.append(text_view)

                        # Operator selector
                        elif row_item == '$operator':
                            fdropdown = self.create_operator_dropdown(fdtype)
                            model = fdropdown.get_model()
                            position = model.find(item_data.operator)
                            if position < model.get_n_items():
                                fdropdown.set_selected(position)
                            fdropdown.connect('notify::selected-item', on_filter_operator_selected, item_data)
                            box.append(fdropdown)

                    list_item.container.append(box)

            # Fallback for unsupported queries
            else:
                text_view = self.create_general_text_view(item_data.query)
                list_item.container.append(text_view)

        def on_delete_filter_button_clicked(button: Gtk.Button) -> None:
            self.on_delete_filter_button_clicked(button, list_item.get_position())

        list_item.delete_button.connect('clicked', on_delete_filter_button_clicked)

    def teardown_factory_filter(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        # I fear by commenting this out, there'll be memory leaks. But we can't access these variables anymore
        # after splicing the filter_list_store when calling the refresh_filter_list_item() function.
        # list_item.condition_box = None
        # list_item.delete_button = None
        pass

    def on_delete_filter_button_clicked(self, button: Gtk.Button, position: int) -> None:
        self.filter_list_store.remove(position)

        if self.filter_list_store.get_n_items() == 0:
            self.filter_list_view_box.get_parent().set_visible(False)
            self.filter_list_status.get_parent().set_visible(True)
            self.filter_list_status_label.set_text('No filters found')

            self.apply_pending_filter() # force apply filter

    @Gtk.Template.Callback()
    def on_add_filter_button_clicked(self, button: Gtk.Button) -> None:
        findex = 0
        field = self.field_list_store.get_item(findex).cname
        fdtype = self.field_list_store.get_item(findex).dtype
        operator = 'is not null'

        qtype = 'basic'
        query = f'{field} {operator}'
        value = {}

        self.filter_list_store.append(FilterListItem(qtype, query, findex, fdtype, field, operator, value))

        self.filter_list_view_box.get_parent().set_visible(True)
        self.filter_list_status.get_parent().set_visible(False)

    @Gtk.Template.Callback()
    def on_delete_all_filter_button_clicked(self, button: Gtk.Button) -> None:
        self.filter_list_store.remove_all()

        self.filter_list_view_box.get_parent().set_visible(False)
        self.filter_list_status.get_parent().set_visible(True)
        self.filter_list_status_label.set_text('No filters found')

        self.apply_pending_filter() # force apply filter

    @Gtk.Template.Callback()
    def on_apply_filter_button_clicked(self, button: Gtk.Button) -> None:
        self.apply_pending_filter()

    def repopulate_filter_list(self, dfi: int = 0) -> None:
        self.filter_list_store.remove_all()

        sheet_document = self.window.get_current_active_document()

        if dfi < 0 or len(sheet_document.data.dfs) <= dfi:
            self.filter_list_view.get_parent().set_visible(False)
            self.filter_list_status.get_parent().set_visible(True)
            self.filter_list_status_label.set_text('No table selected')
            return

        for afilter in sheet_document.current_filters:
            builder = afilter['query-builder']
            condition = builder['conditions'][0]

            qtype = afilter['qtype']
            query = self.parse_query(builder)
            findex = condition['findex']
            fdtype = condition['fdtype']
            field = condition['field']
            operator = condition['operator']
            value = condition['value']

            if not isinstance(value, list):
                value = [value]
            value = {x: v for x, v in enumerate(condition['value'])}

            query = query.strip()
            if query.startswith('and'):
                query = query[3:].strip()
            if query.startswith('('):
                query = query[1:].strip()
            if query.endswith(')'):
                query = query[:-1].strip()

            self.filter_list_store.append(FilterListItem(qtype, query, findex, fdtype, field, operator, value))

        is_empty = self.filter_list_store.get_n_items() == 0
        self.filter_list_view_box.get_parent().set_visible(not is_empty)
        self.filter_list_status.get_parent().set_visible(is_empty)

        if self.filter_list_store.get_n_items() == 0:
            self.filter_list_status_label.set_text('No filters found')

    def refresh_filter_list_item(self, position: int, pstate: dict) -> None:
        item = self.filter_list_store.get_item(position)

        # TODO: support multiple dataframes?
        document = self.window.get_current_active_document()
        dtypes = document.data.dfs[0].dtypes

        qtype = item.qtype
        query = '' # to always reset
        findex = item.findex
        fdtype = item.fdtype
        field = item.field
        operator = item.operator
        value = item.value

        # Reset states to manage compatibility
        for skey, svalue in pstate.items():
            if skey == 'findex':
                # Reset the value if the new and old field aren't naively compatible
                old_dclass = utils.get_dtype_class(dtypes[svalue])
                new_dclass = utils.get_dtype_class(dtypes[item.findex])
                if old_dclass != new_dclass:
                    operator = 'equals'
                    value = {}

                # Convert the field data type to data type class, since field_list_store
                # always stores the data type from the dataframe schema. To make sure all
                # the available operators are shown.
                fdtype = utils.get_dtype_class(dtypes[item.findex])

            if skey == 'operator':
                # Prevent from showing non-generic operators
                if item.operator == 'custom':
                    fdtype = 'undefined'

                # Force update the field data type to show the available operators
                if svalue == 'custom':
                    fdtype = utils.get_dtype_class(dtypes[item.findex])

                # Switching from/to custom always resets the value
                if svalue == 'custom' or item.operator == 'custom':
                    value = {}
                    continue

                # Reset the value if the new and old operator aren't naively compatible
                old_schema = FILTER_BASIC_SCHEMA[svalue]
                old_n_values = len([item for row in old_schema for item in row if item == '$value'])
                new_schema = FILTER_BASIC_SCHEMA[item.operator]
                new_n_values = len([item for row in new_schema for item in row if item == '$value'])
                if old_n_values != new_n_values:
                    value = {}

        new_item = FilterListItem(qtype, query, findex, fdtype, field, operator, value)

        self.filter_list_store.splice(position, 1, [new_item])

    def parse_query(self, builder: dict, query: str = '') -> str:
        if 'conditions' in builder:
            query += f' {builder['operator']} '
            for condition in builder['conditions']:
                return self.parse_query(condition, query)

        value = builder['value']

        if value == '':
            query += f'({builder['field']} {builder['operator']})'
            return query

        if value is None:
            value = 'null'

        if isinstance(value, str):
            value = f"'{value}'"

        if isinstance(value, list):
            value_list = []
            for v in value:
                if v is None:
                    value_list.append('null')
                elif isinstance(v, str):
                    value_list.append(f"'{v}'")
                else:
                    value_list.append(str(v))
            value = f'({", ".join(value_list)})'

        query += f'({builder['field']} {builder['operator']} {value})'

        return query

    def apply_pending_filter(self) -> None:
        # TODO: support multiple dataframes?
        document = self.window.get_current_active_document()
        dtypes = document.data.dfs[0].dtypes

        if len(document.current_filters) == 0 and self.filter_list_store.get_n_items() == 0:
            return # skip to prevent from saving new history item

        document.current_filters = []
        document.pending_filters = []

        for filter_item in self.filter_list_store:
            qtype = filter_item.qtype
            findex = filter_item.findex
            fdtype = filter_item.fdtype
            field = filter_item.field
            operator = filter_item.operator
            value = list(filter_item.value.values())
            expression = polars.lit(True)

            # Try to cast the value to the right type
            try:
                value = polars.Series(value).cast(dtypes[findex]).to_list()
            except Exception:
                continue # skip invalid filters, FIXME: show a warning to user

            try:
                expression = get_filter_basic_expression(filter_item, value)
            except Exception:
                continue # skip invalid filters, FIXME: show a warning to user

            # TODO: add support for OR operator?
            metadata = {
                'qhash': None,
                'qtype': qtype,
                'operator': 'and',
                'query-builder': {
                    'operator': 'and',
                    'conditions': [{
                        'findex': findex,
                        'fdtype': fdtype,
                        'field': field,
                        'operator': operator,
                        'value': value,
                    }],
                },
                'expression': expression,
            }

            document.pending_filters.append(metadata)

        document.is_refreshing_uis = True
        document.filter_current_rows(multiple=True)
        document.is_refreshing_uis = False



    def create_field_dropdown(self) -> Gtk.DropDown:
        field_dropdown = Gtk.DropDown.new()
        field_dropdown.set_hexpand(True)

        def setup_factory_field_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.set_hexpand(True)
            list_item.set_child(box)

            label = Gtk.Label()
            box.append(label)

            image = Gtk.Image()
            image.set_from_icon_name('object-select-symbolic')
            image.set_opacity(0)
            box.append(image)

            list_item.label = label
            list_item.image = image

        def bind_factory_field_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            item_data = list_item.get_item()
            list_item.label.set_label(item_data.cname)

            def on_list_item_selected(*_) -> None:
                list_item.image.set_opacity(0)
                if list_item.get_selected():
                    list_item.image.set_opacity(1)

            field_dropdown.connect('notify::selected-item', on_list_item_selected)
            on_list_item_selected()

        def teardown_factory_field_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            # I fear by commenting this out, there'll be memory leaks. But we can't access these variables anymore
            # after splicing the filter_list_store when calling the refresh_filter_list_item() function.
            # list_item.label = None
            # list_item.image = None
            pass

        field_dropdown_list_factory = Gtk.SignalListItemFactory()
        field_dropdown_list_factory.connect('setup', setup_factory_field_dropdown)
        field_dropdown_list_factory.connect('bind', bind_factory_field_dropdown)
        field_dropdown_list_factory.connect('teardown', teardown_factory_field_dropdown)
        field_dropdown.set_list_factory(field_dropdown_list_factory)

        field_dropdown_model = Gio.ListStore()
        for cindex in range(self.field_list_store.get_n_items()):
            field_dropdown_model.append(self.field_list_store.get_item(cindex))
        field_dropdown.set_model(field_dropdown_model)

        field_dropdown_factory = Gtk.BuilderListItemFactory.new_from_bytes(None, GLib.Bytes.new(bytes(
"""
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <template class="GtkListItem">
    <property name="child">
      <object class="GtkLabel">
        <property name="halign">start</property>
        <property name="hexpand">true</property>
        <property name="ellipsize">end</property>
        <binding name="label">
          <lookup name="cname" type="FieldListItem">
            <lookup name="item">GtkListItem</lookup>
          </lookup>
        </binding>
      </object>
    </property>
  </template>
</interface>
""", 'utf-8')))
        field_dropdown.set_factory(field_dropdown_factory)

        return field_dropdown

    def create_order_dropdown(self) -> Gtk.DropDown:
        order_dropdown = Gtk.DropDown.new()
        order_dropdown.set_hexpand(True)

        def setup_factory_order_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.set_hexpand(True)
            list_item.set_child(box)

            label = Gtk.Label()
            box.append(label)

            image = Gtk.Image()
            image.set_from_icon_name('object-select-symbolic')
            image.set_opacity(0)
            box.append(image)

            list_item.label = label
            list_item.image = image

        def bind_factory_order_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            item_data = list_item.get_item()
            list_item.label.set_label(item_data.get_string())

            def on_list_item_selected(*_) -> None:
                list_item.image.set_opacity(0)
                if list_item.get_selected():
                    list_item.image.set_opacity(1)

            order_dropdown.connect('notify::selected-item', on_list_item_selected)
            on_list_item_selected()

        def teardown_factory_order_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            list_item.label = None
            list_item.image = None

        order_dropdown_list_factory = Gtk.SignalListItemFactory()
        order_dropdown_list_factory.connect('setup', setup_factory_order_dropdown)
        order_dropdown_list_factory.connect('bind', bind_factory_order_dropdown)
        order_dropdown_list_factory.connect('teardown', teardown_factory_order_dropdown)
        order_dropdown.set_list_factory(order_dropdown_list_factory)

        order_dropdown_model = Gtk.StringList()
        order_dropdown_model.append('Ascending')
        order_dropdown_model.append('Descending')
        order_dropdown.set_model(order_dropdown_model)

        order_dropdown_factory = Gtk.BuilderListItemFactory.new_from_bytes(None, GLib.Bytes.new(bytes(
"""
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <template class="GtkListItem">
    <property name="child">
      <object class="GtkLabel">
        <property name="halign">start</property>
        <property name="hexpand">true</property>
        <property name="ellipsize">end</property>
        <binding name="label">
          <lookup name="string" type="GtkStringObject">
            <lookup name="item">GtkListItem</lookup>
          </lookup>
        </binding>
      </object>
    </property>
  </template>
</interface>
""", 'utf-8')))
        order_dropdown.set_factory(order_dropdown_factory)

        return order_dropdown

    def create_operator_dropdown(self, dtype: str) -> Gtk.DropDown:
        basic_filter_dropdown = Gtk.DropDown.new()
        basic_filter_dropdown.set_hexpand(True)

        def setup_factory_basic_filter_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.set_hexpand(True)
            list_item.set_child(box)

            label = Gtk.Label()
            box.append(label)

            image = Gtk.Image()
            image.set_from_icon_name('object-select-symbolic')
            image.set_opacity(0)
            box.append(image)

            list_item.label = label
            list_item.image = image

        def bind_factory_basic_filter_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            item_data = list_item.get_item()
            list_item.label.set_label(item_data.get_string())

            def on_list_item_selected(*_) -> None:
                list_item.image.set_opacity(0)
                if list_item.get_selected():
                    list_item.image.set_opacity(1)

            basic_filter_dropdown.connect('notify::selected-item', on_list_item_selected)
            on_list_item_selected()

        def teardown_factory_basic_filter_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            # I fear by commenting this out, there'll be memory leaks. But we can't access these variables anymore
            # after splicing the filter_list_store when calling the refresh_filter_list_item() function.
            # list_item.label = None
            # list_item.image = None
            pass

        basic_filter_dropdown_list_factory = Gtk.SignalListItemFactory()
        basic_filter_dropdown_list_factory.connect('setup', setup_factory_basic_filter_dropdown)
        basic_filter_dropdown_list_factory.connect('bind', bind_factory_basic_filter_dropdown)
        basic_filter_dropdown_list_factory.connect('teardown', teardown_factory_basic_filter_dropdown)
        basic_filter_dropdown.set_list_factory(basic_filter_dropdown_list_factory)

        # TODO: this can potentially causes confusion for the users, since they need
        #       to switch to any generic operator before they can see non-generic ones
        #       after when they want to make a switch from custom input.
        basic_filter_dropdown_model = Gtk.StringList()
        for option in FILTER_BASIC_OPTION['generic']:
            basic_filter_dropdown_model.append(option)
        if dtype in FILTER_BASIC_OPTION:
            for option in FILTER_BASIC_OPTION[dtype]:
                basic_filter_dropdown_model.append(option)
        basic_filter_dropdown_model.append('custom')
        basic_filter_dropdown.set_model(basic_filter_dropdown_model)

        basic_filter_dropdown_factory = Gtk.BuilderListItemFactory.new_from_bytes(None, GLib.Bytes.new(bytes(
"""
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <template class="GtkListItem">
    <property name="child">
      <object class="GtkLabel">
        <property name="halign">start</property>
        <property name="hexpand">true</property>
        <property name="ellipsize">end</property>
        <binding name="label">
          <lookup name="string" type="GtkStringObject">
            <lookup name="item">GtkListItem</lookup>
          </lookup>
        </binding>
      </object>
    </property>
  </template>
</interface>
""", 'utf-8')))
        basic_filter_dropdown.set_factory(basic_filter_dropdown_factory)

        return basic_filter_dropdown

    def create_general_text_view(self, text: str = '') -> Gtk.TextView:
        text_view = Gtk.TextView()
        text_view.set_hexpand(True)
        text_view.set_size_request(-1, 28)

        buffer = Gtk.TextBuffer()
        buffer.set_text(text)
        text_view.set_buffer(buffer)

        def on_text_view_focus_received(event: Gtk.EventControllerFocus) -> None:
            # I actually want it to wrap words when it's created,
            # but unfortunately it seems to always glitch much.
            event.get_widget().set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('enter', on_text_view_focus_received)
        text_view.add_controller(focus_event_controller)

        return text_view

    def create_delete_button(self) -> Gtk.Button:
        delete_button = Gtk.Button()
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.set_tooltip_text('Delete item')
        delete_button.add_css_class('flat')
        delete_button.set_margin_end(2)
        return delete_button

    def open_home_view(self) -> None:
        self.window.split_view.set_collapsed(False)
        self.window.toggle_sidebar.set_active(True)

        tab_page = self.window.sidebar_home_page
        self.window.sidebar_tab_view.set_selected_page(tab_page)