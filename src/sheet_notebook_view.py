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


from gi.repository import Gdk, GLib, GObject, Gtk, GtkSource
import polars
import threading

from .sheet_notebook import SheetNotebook

@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-notebook-view.ui')
class SheetNotebookView(Gtk.Box):
    __gtype_name__ = 'SheetNotebookView'

    run_all_button = Gtk.Template.Child()

    scrolled_window = Gtk.Template.Child()
    list_view = Gtk.Template.Child()

    def __init__(self, document: SheetNotebook, **kwargs) -> None:
        super().__init__(**kwargs)

        self.document = document

        # Disable scroll to focus behavior of the Gtk.Viewport
        self.scrolled_window.get_first_child().set_scroll_to_focus(False)

        self.list_items: list[dict[str, GObject.Object]] = []

        self.run_queue: list[int] = []
        self.is_running_queue = False

        # We don't use all objects below, they're just placeholders
        # so that it doesn't break the current design. Let's flag
        # this as TODO.

        self.main_canvas = Gtk.DrawingArea()
        self.horizontal_scrollbar = Gtk.Scrollbar()
        self.vertical_scrollbar = Gtk.Scrollbar()

    def add_new_sql_cell(self, query: str = None) -> None:
        main_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_container.set_spacing(6)

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

        if query is not None:
            source_view.get_buffer().set_text(query)

        output_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        output_container.set_spacing(6)
        content_container.append(output_container)

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
        output_container.append(status_text)

        from .sheet_document import SheetDocument
        sheet_document = SheetDocument(configs={'show-auto-filters'    : False,
                                                'ctrl-wheel-to-scroll' : True})

        sheet_document.view.add_css_class('notebook-output')
        sheet_document.view.add_css_class('frame')
        sheet_document.view.set_visible(False)
        output_container.append(sheet_document.view)

        delete_button = Gtk.Button()
        delete_button.set_valign(Gtk.Align.START)
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.add_css_class('flat')
        main_container.append(delete_button)

        self.list_view.append(main_container)

        position = len(self.list_items)

        def on_run_button_clicked(button: Gtk.Button) -> None:
            status_text.get_buffer().set_text('Running...')
            status_text.remove_css_class('error')
            status_text.set_visible(True)

            sheet_document.view.set_visible(False)

            output_container.set_visible(True)

            button.set_sensitive(False)

            # Remove the item from the queue
            if self.is_running_queue \
                    and self.run_queue[0] == position:
                self.run_queue.pop(0)

            def show_query_result(dataframe: polars.DataFrame) -> None:
                MAX_VIEW_HEIGHT = 600 + 16 + 2
                new_view_height = (dataframe.height + 3) * 20 + 16 + 2
                new_view_height = min(new_view_height, MAX_VIEW_HEIGHT)
                sheet_document.view.set_size_request(-1, new_view_height)

                sheet_document.view.set_visible(True)
                status_text.set_visible(False)

                sheet_document.data.setup_main_dataframe(dataframe)
                sheet_document.setup_document()
                sheet_document.renderer.render_caches = {}

            def show_error_message(message: str) -> None:
                status_text.get_buffer().set_text(message)
                status_text.add_css_class('error')
                status_text.set_visible(True)

                sheet_document.data.setup_main_dataframe(polars.DataFrame())
                sheet_document.view.set_visible(False)

            def run_query_in_thread() -> None:
                text_buffer = source_view.get_buffer()
                start_iter = text_buffer.get_start_iter()
                end_iter = text_buffer.get_end_iter()
                query = text_buffer.get_text(start_iter, end_iter, True)

                result = self.document.run_sql_query(query)
                is_success = isinstance(result, polars.DataFrame)

                if is_success:
                    GLib.idle_add(show_query_result, result)
                else:
                    GLib.idle_add(show_error_message, result)

                button.set_sensitive(True)

                if self.is_running_queue:
                    if is_success \
                            and len(self.run_queue) > 0:
                        # Trigger the next query in queue
                        lidx = self.run_queue[0]
                        list_item = self.list_items[lidx]
                        list_item['run_button'].emit('clicked')
                    else:
                        self.run_all_finish()

            threading.Thread(target=run_query_in_thread, daemon=True).start()

        def on_source_view_key_pressed(event_controller: Gtk.EventControllerKey,
                                       keyval:           int,
                                       keycode:          int,
                                       state:            Gdk.ModifierType) -> bool:
            # Ctrl+Return to execute the query
            if keyval == Gdk.KEY_Return:
                if state != Gdk.ModifierType.CONTROL_MASK:
                    return False
                on_run_button_clicked(run_button)
                return True

        def on_delete_button_clicked(button: Gtk.Button) -> None:
            list_item = self.list_items[position]
            list_item['main_container'].unparent()
            self.list_items.pop(position)

        run_button.connect('clicked', on_run_button_clicked)
        delete_button.connect('clicked', on_delete_button_clicked)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', on_source_view_key_pressed)
        source_view.add_controller(key_event_controller)

        self.list_items.append({
            'type'              : 'sql',
            'sheet_document'    : sheet_document,
            'main_container'    : main_container,
            'content_container' : content_container,
            'output_container'  : output_container,
            'source_view'       : source_view,
            'status_text'       : status_text,
            'run_button'        : run_button,
            'delete_button'     : delete_button,
        })

    @Gtk.Template.Callback()
    def on_run_all_clicked(self, button: Gtk.Button) -> None:
        self.is_running_queue = True

        button.set_sensitive(False)

        self.run_queue = []

        for lidx, list_item in enumerate(self.list_items):
            if list_item['type'] not in {'sql'}:
                continue
            list_item['output_container'].set_visible(False)
            list_item['run_button'].set_sensitive(False)
            self.run_queue.append(lidx)

        # Trigger the first query execution
        lidx = self.run_queue[0]
        list_item = self.list_items[lidx]
        list_item['run_button'].emit('clicked')

    def run_all_finish(self) -> None:
        self.is_running_queue = False

        self.run_all_button.set_sensitive(True)

        self.run_queue = []

        for list_item in self.list_items:
            list_item['run_button'].set_sensitive(True)

    @Gtk.Template.Callback()
    def on_add_sql_query_clicked(self, button: Gtk.Button) -> None:
        self.add_new_sql_cell()

    @Gtk.Template.Callback()
    def on_add_markdown_clicked(self, button: Gtk.Button) -> None:
        pass