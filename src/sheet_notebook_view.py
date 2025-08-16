# sheet_notebook_view.py
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


from gi.repository import Gdk, GObject, Gtk, GtkSource
import polars

from .sheet_notebook import SheetNotebook

class CellListItem(GObject.Object):
    __gtype_name__ = 'ListItem'

    ctype = GObject.Property(type=str, default='sql')
    query = GObject.Property(type=str, default='')
    status = GObject.Property(type=str, default='')

    def __init__(self,
                 ctype:  str = '',
                 query:  str = '',
                 status: str = '') -> None:
        super().__init__()

        self.ctype = ctype
        self.query = query
        self.status = status



@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-notebook-view.ui')
class SheetNotebookView(Gtk.Box):
    __gtype_name__ = 'SheetNotebookView'

    scrolled_window = Gtk.Template.Child()

    list_view = Gtk.Template.Child()
    list_store = Gtk.Template.Child()

    def __init__(self, document: SheetNotebook, **kwargs) -> None:
        super().__init__(**kwargs)

        self.document = document

        # Disable scroll to focus behavior of the Gtk.Viewport
        self.scrolled_window.get_first_child().set_scroll_to_focus(False)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory)
        factory.connect('bind', self.bind_factory)
        factory.connect('teardown', self.teardown_factory)
        self.list_view.set_factory(factory)

        # We don't use all objects below, they're just placeholders
        # so that it doesn't break the current design. Let's flag
        # this as TODO.

        self.main_canvas = Gtk.DrawingArea()
        self.horizontal_scrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.HORIZONTAL)
        self.vertical_scrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)

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
        source_view.set_auto_indent(True)
        source_view.set_monospace(True)
        source_view.set_tab_width(4)
        source_view.add_css_class('notebook-source-view')
        source_view.add_css_class('card')
        source_view.set_size_request(-1, 68)
        content_container.append(source_view)

        status_text = Gtk.TextView()
        status_text.set_halign(Gtk.Align.FILL)
        status_text.set_hexpand(True)
        status_text.set_editable(False)
        status_text.set_cursor_visible(False)
        status_text.set_wrap_mode(Gtk.WrapMode.WORD)
        status_text.add_css_class('notebook-status')
        status_text.add_css_class('error')
        status_text.add_css_class('frame')
        status_text.remove_css_class('view')
        status_text.set_visible(False)
        content_container.append(status_text)

        from .sheet_document import SheetDocument
        sheet_document = SheetDocument(configs={'show-auto-filters'    : False,
                                                'ctrl-wheel-to-scroll' : True})

        sheet_document.view.add_css_class('notebook-output')
        sheet_document.view.add_css_class('frame')
        sheet_document.view.set_visible(False)
        content_container.append(sheet_document.view)

        delete_button = Gtk.Button()
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.set_valign(Gtk.Align.START)
        delete_button.add_css_class('flat')
        main_container.append(delete_button)

        list_item.run_button = run_button
        list_item.source_view = source_view
        list_item.status_text = status_text
        list_item.sheet_document = sheet_document
        list_item.delete_button = delete_button

    def bind_factory(self,
                     list_item_factory: Gtk.SignalListItemFactory,
                     list_item:         Gtk.ListItem) -> None:
        position = list_item.get_position()
        item_data = list_item.get_item()

        def auto_resize_sheet_view(sheet_view: Gtk.Widget, n_rows: int) -> None:
            MAX_VIEW_HEIGHT = 600 + 16 + 2
            new_view_height = (n_rows + 3) * 20 + 16 + 2
            new_view_height = min(new_view_height, MAX_VIEW_HEIGHT)
            sheet_view.set_size_request(-1, new_view_height)

        def on_run_button_clicked(button: Gtk.Button) -> None:
            result = self.document.run_sql_query(item_data.query)

            if not isinstance(result, polars.DataFrame):
                list_item.sheet_document.view.set_visible(False)

                list_item.status_text.get_buffer().set_text(result)
                list_item.status_text.set_visible(True)

                self.document.data.dfs[position] = polars.DataFrame()

                item_data.status = result

                return

            auto_resize_sheet_view(list_item.sheet_document.view, result.height)

            list_item.sheet_document.view.set_visible(True)
            list_item.status_text.set_visible(False)

            list_item.sheet_document.data.setup_main_dataframe(result)
            list_item.sheet_document.setup_document()
            list_item.sheet_document.renderer.render_caches = {}
            list_item.sheet_document.view.main_canvas.queue_draw()

            self.document.data.dfs[position] = result

            item_data.status = ''

        def on_source_view_changed(text_buffer: Gtk.TextBuffer) -> None:
            start_iter = text_buffer.get_start_iter()
            end_iter = text_buffer.get_end_iter()
            text = text_buffer.get_text(start_iter, end_iter, True)
            item_data.query = text

        def on_source_view_key_pressed(event_controller: Gtk.EventControllerKey,
                                       keyval:           int,
                                       keycode:          int,
                                       state:            Gdk.ModifierType) -> bool:
            # Ctrl+Return to execute the query
            if keyval == Gdk.KEY_Return:
                if state != Gdk.ModifierType.CONTROL_MASK:
                    return False
                list_item.run_button.emit('clicked')
                return True

        def on_delete_button_clicked(button: Gtk.Button) -> None:
            self.list_store.remove(position)
            self.document.data.dfs.pop(position)
            self.document.data.bbs.pop(position)
            if self.list_store.get_n_items() == 0:
                self.list_view.set_visible(False)

        dataframe = self.document.data.dfs[position]

        auto_resize_sheet_view(list_item.sheet_document.view, dataframe.height)

        list_item.sheet_document.view.set_visible(dataframe.width > 0 and
                                                  dataframe.height > 0)

        list_item.sheet_document.data.setup_main_dataframe(dataframe)
        list_item.sheet_document.setup_document()
        list_item.sheet_document.view.main_canvas.queue_draw()

        list_item.status_text.get_buffer().set_text(item_data.status)
        list_item.status_text.set_visible(item_data.status != '')

        list_item.source_view.get_buffer().set_text(item_data.query)

        list_item.run_button.connect('clicked', on_run_button_clicked)
        list_item.source_view.get_buffer().connect('changed', on_source_view_changed)
        list_item.delete_button.connect('clicked', on_delete_button_clicked)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', on_source_view_key_pressed)
        list_item.source_view.add_controller(key_event_controller)

    def teardown_factory(self,
                         list_item_factory: Gtk.SignalListItemFactory,
                         list_item:         Gtk.ListItem) -> None:
        # list_item.run_button = None
        # list_item.source_view = None
        # list_item.status_text = None
        # list_item.sheet_document = None
        # list_item.delete_button = None
        pass

    @Gtk.Template.Callback()
    def on_run_all_clicked(self, button: Gtk.Button) -> None:
        # Try to execute all cells
        for cindex in range(self.list_store.get_n_items()):
            list_item = self.list_store.get_item(cindex)
            result = self.document.run_sql_query(list_item.query)
            if not isinstance(result, polars.DataFrame):
                self.document.data.dfs[cindex] = polars.DataFrame()
                list_item.status = result
                break
            self.document.data.dfs[cindex] = result
            list_item.status = ''

        # Force the list view to re-bind the factory
        old_model = self.list_view.get_model()
        self.list_view.set_model(None)
        self.list_view.set_model(old_model)

    @Gtk.Template.Callback()
    def on_add_sql_query_clicked(self, button: Gtk.Button) -> None:
        self.document.data.insert_blank_dataframe()

        list_item = CellListItem('sql')
        self.list_store.append(list_item)
        self.list_view.set_visible(True)

    @Gtk.Template.Callback()
    def on_add_markdown_clicked(self, button: Gtk.Button) -> None:
        pass