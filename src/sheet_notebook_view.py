# sheet_notebook_view.py
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


from gi.repository import GObject, Gtk, GtkSource

from .sheet_notebook import SheetNotebook

class CellListItem(GObject.Object):
    __gtype_name__ = 'ListItem'

    ctype = GObject.Property(type=str, default='sql')
    query = GObject.Property(type=str, default='')
    result = GObject.Property(type=str, default='')

    def __init__(self,
                 ctype: str,
                 query: str = '',
                 result: str = '') -> None:
        super().__init__()

        self.ctype = ctype
        self.query = query
        self.result = result



@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-notebook-view.ui')
class SheetNotebookView(Gtk.Box):
    __gtype_name__ = 'SheetNotebookView'

    list_view = Gtk.Template.Child()
    list_store = Gtk.Template.Child()

    def __init__(self, document: SheetNotebook, **kwargs) -> None:
        super().__init__(**kwargs)

        self.document = document

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory)
        factory.connect('bind', self.bind_factory)
        factory.connect('teardown', self.teardown_factory)
        self.list_view.set_factory(factory)

        # We don't use all objects below, they're just placeholders
        # so that it doesn't break the current design. Let's flag
        # this as TODO.

        self.main_canvas = Gtk.DrawingArea()

    def setup_factory(self,
                      list_item_factory: Gtk.SignalListItemFactory,
                      list_item:         Gtk.ListItem) -> None:
        list_item.set_focusable(False)
        list_item.set_activatable(False)

        main_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_container.set_spacing(6)
        list_item.set_child(main_container)

        run_button = Gtk.Button()
        run_button.set_icon_name('media-playback-start-symbolic')
        run_button.set_valign(Gtk.Align.START)
        main_container.append(run_button)

        content_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_container.set_spacing(6)
        main_container.append(content_container)

        source_view = GtkSource.View()
        source_view.set_hexpand(True)
        source_view.set_show_line_numbers(True)
        source_view.set_monospace(True)
        source_view.set_tab_width(4)
        source_view.add_css_class('notebook-source-view')
        source_view.add_css_class('card')
        source_view.set_size_request(-1, 68)
        content_container.append(source_view)

        text_view = Gtk.TextView()
        text_view.set_hexpand(True)
        text_view.set_editable(False)
        text_view.add_css_class('notebook-output')
        text_view.set_visible(False)
        content_container.append(text_view)

        delete_button = Gtk.Button()
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.set_valign(Gtk.Align.START)
        delete_button.add_css_class('flat')
        main_container.append(delete_button)

        list_item.run_button = run_button
        list_item.source_view = source_view
        list_item.output_view = text_view
        list_item.delete_button = delete_button

    def bind_factory(self,
                     list_item_factory: Gtk.SignalListItemFactory,
                     list_item:         Gtk.ListItem) -> None:

        def on_run_button_clicked(button:    Gtk.Button,
                                  item_data: CellListItem) -> None:
            output = self.document.run_sql_query(item_data.query)
            list_item.output_view.get_buffer().set_text(output)
            list_item.output_view.set_visible(True)
            item_data.result = output

        def on_source_view_changed(text_buffer: Gtk.TextBuffer,
                                   item_data:   CellListItem) -> None:
            start_iter = text_buffer.get_start_iter()
            end_iter = text_buffer.get_end_iter()
            text = text_buffer.get_text(start_iter, end_iter, True)
            item_data.query = text

        def on_delete_button_clicked(button:    Gtk.Button,
                                     item_data: CellListItem) -> None:
            _, position = self.list_store.find(item_data)
            self.list_store.remove(position)

            if self.list_store.get_n_items() == 0:
                self.list_view.set_visible(False)

        item_data = list_item.get_item()

        list_item.source_view.get_buffer().set_text(item_data.query)

        if item_data.result:
            list_item.output_view.get_buffer().set_text(item_data.result)
            list_item.output_view.set_visible(True)

        list_item.run_button.connect('clicked', on_run_button_clicked, item_data)
        list_item.source_view.get_buffer().connect('changed', on_source_view_changed, item_data)
        list_item.delete_button.connect('clicked', on_delete_button_clicked, item_data)

    def teardown_factory(self,
                         list_item_factory: Gtk.SignalListItemFactory,
                         list_item:         Gtk.ListItem) -> None:
        # list_item.run_button = None
        # list_item.source_view = None
        # list_item.output_view = None
        # list_item.delete_button = None
        pass

    @Gtk.Template.Callback()
    def on_run_all_clicked(self, button: Gtk.Button) -> None:
        pass

    @Gtk.Template.Callback()
    def on_add_sql_query_clicked(self, button: Gtk.Button) -> None:
        list_item = CellListItem('sql')
        self.list_store.append(list_item)

        self.list_view.set_visible(True)

    @Gtk.Template.Callback()
    def on_add_markdown_clicked(self, button: Gtk.Button) -> None:
        list_item = CellListItem('markdown')
        self.list_store.append(list_item)

        self.list_view.set_visible(True)