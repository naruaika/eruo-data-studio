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


from gi.repository import Adw, GObject, Gtk, Pango

from . import utils
from .window import Window

class FieldListItem(GObject.Object):
    __gtype_name__ = 'FieldListItem'

    ccolumn = GObject.Property(type=int, default=0)
    cname = GObject.Property(type=str, default='[Blank]')
    dtype = GObject.Property(type=str, default='text')
    active = GObject.Property(type=bool, default=True)

    def __init__(self, ccolumn: int, cname: str, dtype: str, active: bool) -> None:
        super().__init__()

        self.ccolumn = ccolumn
        self.cname = cname
        self.dtype = dtype
        self.active = active



@Gtk.Template(resource_path='/com/macipra/eruo/ui/sidebar-home-view.ui')
class SidebarHomeView(Adw.Bin):
    __gtype_name__ = 'SidebarHomeView'

    field_section = Gtk.Template.Child()
    field_list_status = Gtk.Template.Child()
    field_list_view = Gtk.Template.Child()
    field_list_store = Gtk.Template.Child()

    def __init__(self, window: Window, **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window

        self.field_list_view.get_parent().set_activatable(False)
        self.field_list_view.get_parent().set_visible(False)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory_check_button)
        factory.connect('bind', self.bind_factory_check_button)
        factory.connect('teardown', self.teardown_factory_check_button)
        self.field_list_view.set_factory(factory)

    def setup_factory_check_button(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
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

    def bind_factory_check_button(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        item_data = list_item.get_item()
        list_item.check_button.set_active(item_data.active)
        list_item.check_button.connect('toggled', self.on_field_list_item_check_button_toggled, item_data)
        list_item.label_name.set_label(item_data.cname)
        list_item.label_type.set_label(item_data.dtype)

    def teardown_factory_check_button(self, list_item_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        list_item.check_button = None
        list_item.label_name = None
        list_item.label_type = None

    def on_field_list_item_check_button_toggled(self, button: Gtk.Button, item_data: FieldListItem) -> None:
        sheet_document = self.window.get_current_active_document()
        sheet_document.toggle_column_visibility(item_data.ccolumn, button.get_active())

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

    def open_home_view(self) -> None:
        self.window.split_view.set_collapsed(False)
        self.window.toggle_sidebar.set_active(True)

        tab_page = self.window.sidebar_home_page
        self.window.sidebar_tab_view.set_selected_page(tab_page)