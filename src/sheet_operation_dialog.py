# sheet_operation_dialog.py
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


from gi.repository import Adw, GLib, GObject, Gtk
import threading

from . import utils
from .window import Window

class SheetOperationArg(GObject.Object):
    __gtype_name__ = 'SheetOperationArg'

    text = GObject.Property(type=str, default='')
    type = GObject.Property(type=str, default='str')



class PreviewListItem(GObject.Object):
    __gtype_name__ = 'PreviewListItem'

    before = GObject.Property(type=str, default='')
    after = GObject.Property(type=str, default='')

    def __init__(self,
                 before: str,
                 after:  str):
        super().__init__()

        self.before = before
        self.after = after



@Gtk.Template(resource_path='/com/macipra/eruo/ui/sheet-operation-dialog.ui')
class SheetOperationDialog(Adw.Dialog):
    __gtype_name__ = 'SheetOperationDialog'

    preferences_page = Gtk.Template.Child()
    content_container = Gtk.Template.Child()

    preview_container = Gtk.Template.Child()
    preview_list_view = Gtk.Template.Child()
    preview_list_store = Gtk.Template.Child()

    apply_button = Gtk.Template.Child()

    def __init__(self,
                 title:    str,
                 layout:   list[tuple],
                 callback: callable,
                 window:   Window,
                 **kwargs) -> None:
        super().__init__()

        self.set_title(title)

        # Disable scroll to focus behavior of the Gtk.Viewport
        scrolled_window = self.preferences_page.get_first_child()
        viewport = scrolled_window.get_first_child()
        viewport.set_scroll_to_focus(False)

        self.callback = callback
        self.window = window
        self.kwargs = kwargs

        self.operation_args = []

        def on_input_changed(stack, pspec) -> None:
            self.live_preview()

        def on_input_activated(widget) -> None:
            self.on_apply_button_clicked(self.apply_button)

        for item in layout:
            operation_arg = SheetOperationArg()
            self.operation_args.append(operation_arg)

            title, dtype = item[0], item[1]
            if len(item) > 2:
                options = item[2]

            match dtype:
                case 'entry':
                    entry = Adw.EntryRow()
                    entry.set_title(title)
                    entry.bind_property('text', operation_arg,
                                        'text', GObject.BindingFlags.SYNC_CREATE)
                    entry.connect('entry-activated', on_input_activated)
                    entry.connect('notify::text', on_input_changed)
                    self.content_container.add(entry)

                case 'spin':
                    spin = Adw.SpinRow()
                    spin.set_title(title)
                    spin.set_range(0, 1_000_000_000)
                    spin.get_adjustment().set_page_increment(5)
                    spin.get_adjustment().set_step_increment(1)
                    spin.bind_property('text', operation_arg,
                                       'text', GObject.BindingFlags.SYNC_CREATE)
                    spin.connect('notify::value', on_input_changed)
                    self.content_container.add(spin)
                    operation_arg.type = 'int'

                case 'switch':
                    switch = Adw.SwitchRow()
                    switch.set_title(title)
                    switch.bind_property('active', operation_arg,
                                         'text', GObject.BindingFlags.SYNC_CREATE)
                    spin.connect('notify::active', on_input_changed)
                    self.content_container.add(switch)
                    operation_arg.type = 'bool'

                case 'combo':
                    combo = Adw.ComboRow()
                    combo.set_title(title)
                    combo_model = Gtk.StringList()
                    for option in options:
                        combo_model.append(option)
                    combo.set_model(combo_model)
                    combo.bind_property('selected-item', operation_arg,
                                        'text', GObject.BindingFlags.SYNC_CREATE,
                                        transform_to=lambda _, val: val.get_string())
                    combo.connect('notify::selected-item', on_input_changed)
                    self.content_container.add(combo)

        if 'match_case' in self.kwargs:
            self.match_case = Adw.SwitchRow()
            self.match_case.set_active(self.kwargs['match_case'])
            self.match_case.set_title('Case Sensitive (Match Case)')
            self.match_case.set_subtitle('Distinguish between uppercase and lowercase')
            self.content_container.add(self.match_case)

        if 'use_regexp' in self.kwargs:
            self.use_regexp = Adw.SwitchRow()
            self.use_regexp.set_active(self.kwargs['use_regexp'])
            self.use_regexp.set_title('Use Regular Expression')
            self.use_regexp.set_subtitle('Learn at https://docs.rs/regex/latest/regex/')
            self.content_container.add(self.use_regexp)

        if 'on_column' in self.kwargs:
            self.on_column = Adw.SwitchRow()
            self.on_column.set_active(self.kwargs['on_column'])
            self.on_column.set_title('Apply on Entire Rows')
            self.on_column.set_subtitle('Disable to apply on selection only')
            self.content_container.add(self.on_column)

        if 'new_worksheet' in self.kwargs:
            self.new_worksheet = Adw.SwitchRow()
            self.new_worksheet.set_active(self.kwargs['new_worksheet'])
            self.new_worksheet.set_title('Create a New Worksheet')
            self.new_worksheet.set_subtitle('Send the result into a new worksheet')
            # self.new_worksheet.set_subtitle_selectable(True)
            self.content_container.add(self.new_worksheet)

        if 'live_previewer' in self.kwargs:
            self.preview_container.set_visible(True)
            self.live_preview() # update on startup

    def do_closed(self) -> None:
        application = self.window.get_application()
        if hasattr(application, '_return_focus_back'):
            application._return_focus_back()

    @Gtk.Template.Callback()
    def on_apply_button_clicked(self, button: Gtk.Button) -> None:
        if 'match_case' in self.kwargs:
            self.kwargs['match_case'] = self.match_case.get_active()
        if 'use_regexp' in self.kwargs:
            self.kwargs['use_regexp'] = self.use_regexp.get_active()
        if 'on_column' in self.kwargs:
            self.kwargs['on_column'] = self.on_column.get_active()
        if 'new_worksheet' in self.kwargs:
            self.kwargs['new_worksheet'] = self.new_worksheet.get_active()

        self.close() # close first to properly handle the focus
        self.callback(self.get_callback_args(), **self.kwargs)

    def live_preview(self) -> None:
        if 'live_previewer' not in self.kwargs:
            return

        def update_search_list() -> None:
            args = self.get_callback_args()
            dataframe = self.kwargs['live_previewer'](args)

            list_items_to_add = []

            for row_index in range(dataframe.height):
                list_item = PreviewListItem(dataframe[row_index, 'before'],
                                            dataframe[row_index, 'after'])
                list_items_to_add.append(list_item)

            GLib.idle_add(self.preview_list_store.splice, 0, 0, list_items_to_add)

        self.preview_list_store.remove_all()
        threading.Thread(target=update_search_list, daemon=True).start()

    def get_callback_args(self) -> list:
        args = []

        for operation_arg in self.operation_args:
            arg = operation_arg.text

            # Cast the argument value if needed
            if operation_arg.type == 'int':
                arg = int(arg if arg.isnumeric() else 0)
            if operation_arg.type == 'bool':
                arg = utils.cast_to_boolean(arg)

            args.append(arg)

        return args