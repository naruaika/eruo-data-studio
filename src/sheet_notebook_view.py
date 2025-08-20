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


from gi.repository import Adw, Gdk, GLib, GObject, Gtk, GtkSource
import polars
import threading

from . import utils
from .sheet_notebook import SheetNotebook

@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-notebook-view.ui')
class SheetNotebookView(Gtk.Box):
    __gtype_name__ = 'SheetNotebookView'

    run_all_button = Gtk.Template.Child()

    scrolled_window = Gtk.Template.Child()
    list_view = Gtk.Template.Child()

    def __init__(self,
                 document: SheetNotebook,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.document = document

        # Disable scroll to focus behavior of the Gtk.Viewport
        self.scrolled_window.get_first_child().set_scroll_to_focus(False)

        self.list_items: list[dict[str, GObject.Object]] = []

        self.run_queue: list[int] = []
        self.is_running_queue = False

        settings = Gtk.Settings.get_default()
        settings.connect('notify::gtk-application-prefer-dark-theme',
                         self.on_prefer_dark_theme_changed)

        # We don't use all objects below, they're just placeholders
        # so that it doesn't break the current design. Let's flag
        # this as TODO.

        self.main_canvas = Gtk.DrawingArea()
        self.horizontal_scrollbar = Gtk.Scrollbar()
        self.vertical_scrollbar = Gtk.Scrollbar()

    def on_prefer_dark_theme_changed(self,
                                     settings:     Gtk.Settings,
                                     gparamstring: str) -> None:
        scheme_manager = GtkSource.StyleSchemeManager.get_default()
        prefers_dark = Adw.StyleManager().get_dark()
        color_scheme = 'Adwaita-dark' if prefers_dark else 'Adwaita'
        style_scheme = scheme_manager.get_scheme(color_scheme)

        for list_item in self.list_items:
            if 'source_view' not in list_item:
                continue
            source_buffer = list_item['source_view'].get_buffer()
            source_buffer.set_style_scheme(style_scheme)

    def add_new_sql_cell(self,
                         query:    str = None,
                         position: int = -1) -> None:
        main_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_container.set_spacing(6)

        run_button = Gtk.Button()
        run_button.set_margin_top(34)
        run_button.set_valign(Gtk.Align.START)
        run_button.set_icon_name('media-playback-start-symbolic')
        run_button.add_css_class('flat')
        main_container.append(run_button)

        content_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_container.set_spacing(6)
        main_container.append(content_container)

        toolbar_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toolbar_container.set_spacing(3)
        toolbar_container.set_hexpand(True)
        toolbar_container.set_halign(Gtk.Align.FILL)
        toolbar_container.add_css_class('notebook-cell-toolbar')
        content_container.append(toolbar_container)

        add_sql_button = Gtk.Button()
        add_sql_button.set_valign(Gtk.Align.START)
        add_sql_button.add_css_class('flat')
        add_sql_content_button = Adw.ButtonContent()
        add_sql_content_button.set_icon_name('list-add-symbolic')
        add_sql_content_button.set_label('SQL')
        add_sql_button.set_child(add_sql_content_button)
        toolbar_container.append(add_sql_button)

        add_markdown_button = Gtk.Button()
        add_markdown_button.set_valign(Gtk.Align.START)
        add_markdown_button.add_css_class('flat')
        add_markdown_content_button = Adw.ButtonContent()
        add_markdown_content_button.set_icon_name('list-add-symbolic')
        add_markdown_content_button.set_label('Markdown')
        add_markdown_button.set_child(add_markdown_content_button)
        toolbar_container.append(add_markdown_button)

        run_above_button = Gtk.Button()
        run_above_button.set_valign(Gtk.Align.START)
        run_above_button.add_css_class('flat')
        run_above_content_button = Adw.ButtonContent()
        run_above_content_button.set_icon_name('media-playback-start-symbolic')
        run_above_content_button.set_label('All Above Cells')
        run_above_button.set_child(run_above_content_button)
        toolbar_container.append(run_above_button)

        run_below_button = Gtk.Button()
        run_below_button.set_valign(Gtk.Align.START)
        run_below_button.add_css_class('flat')
        run_below_content_button = Adw.ButtonContent()
        run_below_content_button.set_icon_name('media-playback-start-symbolic')
        run_below_content_button.set_label('This and All Below Cells')
        run_below_button.set_child(run_below_content_button)
        toolbar_container.append(run_below_button)

        delete_button = Gtk.Button()
        delete_button.set_valign(Gtk.Align.START)
        delete_button.add_css_class('flat')
        delete_content_button = Adw.ButtonContent()
        delete_content_button.set_icon_name('user-trash-symbolic')
        delete_content_button.set_label('Delete')
        delete_button.set_child(delete_content_button)
        toolbar_container.append(delete_button)

        source_buffer = GtkSource.Buffer()
        source_buffer.set_highlight_syntax(True)

        language_manager = GtkSource.LanguageManager.get_default()
        sql_language = language_manager.get_language('sql')
        source_buffer.set_language(sql_language)

        scheme_manager = GtkSource.StyleSchemeManager.get_default()
        prefers_dark = Adw.StyleManager().get_dark()
        color_scheme = 'Adwaita-dark' if prefers_dark else 'Adwaita'
        style_scheme = scheme_manager.get_scheme(color_scheme)
        source_buffer.set_style_scheme(style_scheme)

        source_view = GtkSource.View.new_with_buffer(source_buffer)

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

        sheet_document.view.set_vexpand(False)
        sheet_document.view.add_css_class('notebook-output')
        sheet_document.view.add_css_class('frame')
        sheet_document.view.set_visible(False)
        output_container.append(sheet_document.view)

        if position == 0:
            self.list_view.prepend(main_container)
        if position == -1:
            self.list_view.append(main_container)
        if position > 0:
            target_list_item = self.list_items[position - 1]['main_container']
            self.list_view.insert_child_after(main_container, target_list_item)

        cell_id = utils.generate_ulid()

        def on_run_button_clicked(button: Gtk.Button) -> None:
            # TODO: implement undo/redo?

            status_text.get_buffer().set_text('Running...')
            status_text.remove_css_class('error')
            status_text.set_visible(True)

            sheet_document.view.set_visible(False)

            output_container.set_visible(True)

            button.set_sensitive(False)

            # Remove the item from the queue
            if self.is_running_queue:
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

            def show_output_message(message: str) -> None:
                status_text.get_buffer().set_text(message)
                if message == 'Query executed successfully':
                    status_text.add_css_class('success')
                    status_text.remove_css_class('error')
                else:
                    status_text.add_css_class('error')
                    status_text.remove_css_class('success')
                status_text.set_visible(True)

                sheet_document.data.setup_main_dataframe(polars.DataFrame())
                sheet_document.view.set_visible(False)

            def run_next_query(is_success: bool) -> None:
                if self.is_running_queue:
                    if not is_success:
                        self.run_all_cells_finish()
                        return

                    if len(self.run_queue) == 0:
                        self.run_all_cells_finish()
                        return

                    # Trigger the next query in queue
                    lidx = self.run_queue[0]
                    list_item = self.list_items[lidx]
                    list_item['run_button'].emit('clicked')

            def run_query_in_thread() -> None:
                text_buffer = source_view.get_buffer()
                start_iter = text_buffer.get_start_iter()
                end_iter = text_buffer.get_end_iter()

                query = text_buffer.get_text(start_iter, end_iter, True)
                query = query.strip()

                if query == '':
                    status_text.set_visible(False)
                    run_next_query(True)
                    return

                result = self.document.run_sql_query(query)
                is_success = isinstance(result, polars.DataFrame)

                if is_success:
                    GLib.idle_add(show_query_result, result)
                else:
                    GLib.idle_add(show_output_message, result)

                button.set_sensitive(True)

                run_next_query(is_success)

            threading.Thread(target=run_query_in_thread, daemon=True).start()

        def on_run_above_button_clicked(button: Gtk.Button) -> None:
            position = self.get_cell_position_by_id(cell_id)
            self.run_all_cells(end=position)

        def on_run_below_button_clicked(button: Gtk.Button) -> None:
            position = self.get_cell_position_by_id(cell_id)
            self.run_all_cells(start=position)

        def on_add_sql_button_clicked(button: Gtk.Button) -> None:
            position = self.get_cell_position_by_id(cell_id)
            self.add_new_sql_cell(position=position)

        def on_add_markdown_button_clicked(button: Gtk.Button) -> None:
            pass

        def on_delete_button_clicked(button: Gtk.Button) -> None:
            position = self.get_cell_position_by_id(cell_id)
            list_item = self.list_items[position]
            list_item['main_container'].unparent()
            self.list_items.pop(position)

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

        run_button.connect('clicked', on_run_button_clicked)
        run_above_button.connect('clicked', on_run_above_button_clicked)
        run_below_button.connect('clicked', on_run_below_button_clicked)
        add_sql_button.connect('clicked', on_add_sql_button_clicked)
        add_markdown_button.connect('clicked', on_add_markdown_button_clicked)
        delete_button.connect('clicked', on_delete_button_clicked)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', on_source_view_key_pressed)
        source_view.add_controller(key_event_controller)

        self.list_items.insert(position, {
            'cell_id'             : cell_id,
            'ctype'               : 'sql',
            'sheet_document'      : sheet_document,
            'main_container'      : main_container,
            'toolbar_container'   : toolbar_container,
            'content_container'   : content_container,
            'output_container'    : output_container,
            'source_view'         : source_view,
            'status_text'         : status_text,
            'run_button'          : run_button,
            'run_above_button'    : run_above_button,
            'run_below_button'    : run_below_button,
            'add_sql_button'      : add_sql_button,
            'add_markdown_button' : add_markdown_button,
            'delete_button'       : delete_button,
        })

    @Gtk.Template.Callback()
    def on_run_all_clicked(self, button: Gtk.Button) -> None:
        self.run_all_cells()

    def run_all_cells(self,
                      start: int = 0,
                      end:   int = None) -> None:
        if end is None:
            end = len(self.list_items)

        self.is_running_queue = True

        self.run_all_button.set_sensitive(False)

        self.run_queue = []

        for lidx, list_item in enumerate(self.list_items):
            if lidx < start:
                continue
            if lidx >= end:
                break
            if list_item['ctype'] not in {'sql'}:
                continue

            list_item['output_container'].set_visible(False)
            list_item['run_button'].set_sensitive(False)

            self.run_queue.append(lidx)

        if len(self.run_queue) == 0:
            self.run_all_cells_finish()
            return

        # Trigger the first query execution
        lidx = self.run_queue[0]
        list_item = self.list_items[lidx]
        list_item['run_button'].emit('clicked')

    def run_all_cells_finish(self) -> None:
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
        pass # TODO

    def get_cell_position_by_id(self, cell_id: int) -> int:
        for lidx, list_item in enumerate(self.list_items):
            if list_item['cell_id'] == cell_id:
                return lidx
        return -1