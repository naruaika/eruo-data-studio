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


from gi.repository import Adw, GLib, GObject, Gtk, Pango

from . import globals
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



@Gtk.Template(resource_path='/com/macipra/eruo/ui/sidebar-home-view.ui')
class SidebarHomeView(Adw.Bin):
    __gtype_name__ = 'SidebarHomeView'

    field_list_status = Gtk.Template.Child()
    field_list_view = Gtk.Template.Child()
    field_list_store = Gtk.Template.Child()

    sort_list_view_box = Gtk.Template.Child()
    sort_list_status = Gtk.Template.Child()
    sort_list_view = Gtk.Template.Child()
    sort_list_store = Gtk.Template.Child()

    filter_list_status = Gtk.Template.Child()

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
        header_factory.connect('setup', self.setup_factory_header)
        self.sort_list_view.set_header_factory(header_factory)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory_sort)
        factory.connect('bind', self.bind_factory_sort)
        factory.connect('teardown', self.teardown_factory_sort)
        self.sort_list_view.set_factory(factory)

        # Setup the filter section
        self.filter_list_status.get_parent().set_activatable(False)

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
            globals.is_refreshing_uis = True
            sheet_document = self.window.get_current_active_document()
            sheet_document.toggle_column_visibility(item_data.cindex, button.get_active())
            globals.is_refreshing_uis = False

        list_item.check_button.connect('toggled', on_check_button_toggled, item_data)

    def teardown_factory_field(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        list_item.check_button = None
        list_item.label_name = None
        list_item.label_type = None

    def repopulate_field_list(self, dfi: int = 0) -> None:
        self.field_list_store.remove_all()

        sheet_document = self.window.get_current_active_document()

        if dfi < 0 or len(sheet_document.data.dfs) <= dfi:
            self.field_list_status.get_parent().set_visible(True)
            self.field_list_view.get_parent().set_visible(False)
            return

        self.field_list_status.get_parent().set_visible(False)
        self.field_list_view.get_parent().set_visible(True)

        schema = sheet_document.data.dfs[dfi].schema
        bboxes = sheet_document.data.bbs[dfi]
        vflags = sheet_document.display.column_visibility_flags

        for cindex, cname in enumerate(schema):
            dtype = utils.get_dtype_symbol(schema[cname])
            active = vflags[bboxes.column + cindex - 1] if len(vflags) else True
            self.field_list_store.append(FieldListItem(cindex + 1, cname, dtype, active))

        self.repopulate_sort_list(dfi)

    def setup_factory_header(self, list_item_factory: Gtk.SignalListItemFactory, list_header: Gtk.ListHeader) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(6)
        list_header.set_child(box)

        subbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        subbox.set_homogeneous(True)
        subbox.add_css_class('linked')
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
        list_item.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(6)
        list_item.set_child(box)

        subbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        subbox.set_homogeneous(True)
        subbox.add_css_class('linked')
        box.append(subbox)

        # Setup field dropdown
        field_dropdown = Gtk.DropDown.new()
        field_dropdown.set_hexpand(True)
        subbox.append(field_dropdown)

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
            list_item.label.set_label(item_data.get_string())

            def on_list_item_selected(*_) -> None:
                list_item.image.set_opacity(0)
                if list_item.get_selected():
                    list_item.image.set_opacity(1)

            field_dropdown.connect('notify::selected-item', on_list_item_selected)
            on_list_item_selected()

        def teardown_factory_field_dropdown(list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
            list_item.label = None
            list_item.image = None

        field_dropdown_list_factory = Gtk.SignalListItemFactory()
        field_dropdown_list_factory.connect('setup', setup_factory_field_dropdown)
        field_dropdown_list_factory.connect('bind', bind_factory_field_dropdown)
        field_dropdown_list_factory.connect('teardown', teardown_factory_field_dropdown)
        field_dropdown.set_list_factory(field_dropdown_list_factory)

        field_dropdown_model = Gtk.StringList()
        for cindex in range(self.field_list_store.get_n_items()):
            field_dropdown_model.append(self.field_list_store.get_item(cindex).cname)
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
          <lookup name="string" type="GtkStringObject">
            <lookup name="item">GtkListItem</lookup>
          </lookup>
        </binding>
      </object>
    </property>
  </template>
</interface>
""", 'utf-8')))
        field_dropdown.set_factory(field_dropdown_factory)

        # Setup order dropdown
        order_dropdown = Gtk.DropDown.new()
        order_dropdown.set_hexpand(True)
        subbox.append(order_dropdown)

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

        # Setup delete button
        delete_button = Gtk.Button()
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.set_tooltip_text('Delete sort')
        delete_button.add_css_class('flat')
        delete_button.set_margin_end(2)
        box.append(delete_button)

        list_item.field_dropdown = field_dropdown
        list_item.order_dropdown = order_dropdown
        list_item.delete_button = delete_button

    def bind_factory_sort(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        item_data = list_item.get_item()

        list_item.field_dropdown.set_selected(item_data.cindex)

        order_position = 0 if item_data.order == 'Ascending' else 1
        list_item.order_dropdown.set_selected(order_position)

        def get_string_from_sobject(binding: GObject.Binding, value: any) -> str:
            if isinstance(value, Gtk.StringObject):
                return value.get_string()
            return ''

        list_item.field_dropdown.bind_property('selected', item_data, 'cindex', GObject.BindingFlags.DEFAULT)
        list_item.field_dropdown.bind_property('selected-item', item_data, 'cname', GObject.BindingFlags.DEFAULT, transform_to=get_string_from_sobject)
        list_item.order_dropdown.bind_property('selected-item', item_data, 'order', GObject.BindingFlags.DEFAULT, transform_to=get_string_from_sobject)

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

    @Gtk.Template.Callback()
    def on_add_sort_button_clicked(self, button: Gtk.Button) -> None:
        selected_item = self.field_list_store.get_item(0)
        self.sort_list_store.append(SortListItem(selected_item.cindex - 1, selected_item.cname, 'Ascending'))

        self.sort_list_view_box.get_parent().set_visible(True)
        self.sort_list_status.get_parent().set_visible(False)

    @Gtk.Template.Callback()
    def on_apply_sort_button_clicked(self, button: Gtk.Button) -> None:
        document = self.window.get_current_active_document()

        document.pending_sorts = {}
        for sort_item in self.sort_list_store:
            descending = sort_item.order == 'Descending'
            document.pending_sorts[sort_item.cname] = {'cindex': sort_item.cindex,
                                                       'descending': descending}

        globals.is_refreshing_uis = True
        document.sort_current_rows(multiple=True)
        globals.is_refreshing_uis = False

    def repopulate_sort_list(self, dfi: int = 0) -> None:
        self.sort_list_store.remove_all()

        document = self.window.get_current_active_document()
        column_names = document.data.dfs[dfi].columns

        for cname in document.current_sorts:
            cindex = column_names.index(cname)
            descending = document.current_sorts[cname]['descending']
            order = 'Descending' if descending else 'Ascending'
            self.sort_list_store.append(SortListItem(cindex, cname, order))

        is_empty = self.sort_list_store.get_n_items() == 0
        self.sort_list_view_box.get_parent().set_visible(not is_empty)
        self.sort_list_status.get_parent().set_visible(is_empty)

    def open_home_view(self) -> None:
        self.window.split_view.set_collapsed(False)
        self.window.toggle_sidebar.set_active(True)

        tab_page = self.window.sidebar_home_page
        self.window.sidebar_tab_view.set_selected_page(tab_page)