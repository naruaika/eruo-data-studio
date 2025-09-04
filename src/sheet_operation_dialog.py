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


from gi.repository import Adw, GLib, GObject, Gtk, Pango
import threading

from . import utils
from .window import Window

class SheetOperationArg(GObject.Object):
    __gtype_name__ = 'SheetOperationArg'

    value = GObject.Property(type=str, default='')
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

        n_main_widgets = 0

        for item in layout:
            operation_arg = SheetOperationArg()
            self.operation_args.append(operation_arg)

            title, dtype = item[0], item[1]
            if utils.is_iterable(title):
                title, description = item[0][0], item[0][1]
            else:
                description = None
            if len(item) > 2:
                options = item[2]

            match dtype:
                case 'entry':
                    self.create_entry_row(title, description, operation_arg)
                    n_main_widgets += 1
                case 'spin':
                    self.create_spin_row(title, description, operation_arg)
                    n_main_widgets += 1
                case 'switch':
                    self.create_switch_row(title, description, operation_arg)
                    n_main_widgets += 1
                case 'combo':
                    self.create_combo_row(title, description, options, operation_arg)
                    n_main_widgets += 1
                case 'list-check':
                    self.create_list_check(title, description, options, operation_arg)

        if 'match_case' in self.kwargs:
            self.create_match_case_switch()
        if 'use_regexp' in self.kwargs:
            self.create_use_regexp_switch()
        if 'on_column' in self.kwargs:
            self.create_on_column_switch()
        if 'new_worksheet' in self.kwargs:
            self.create_new_worksheet_switch()
        if 'live_previewer' in self.kwargs:
            self.preview_container.set_visible(True)
            self.live_preview(use_thread=False) # update on startup

        if n_main_widgets == 0:
            self.content_container.unparent()
        if 'live_previewer' not in self.kwargs:
            self.preview_container.unparent()

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

    def create_combo_row(self,
                         title:   str,
                         description: str,
                         options: list[str],
                         oarg:    SheetOperationArg) -> None:
        combo = Adw.ComboRow()
        combo.set_title(title)
        if description is not None:
            combo.set_subtitle(description)
        combo_model = Gtk.StringList()
        for option in options:
            combo_model.append(option)
        combo.set_model(combo_model)
        combo.bind_property('selected-item', oarg,
                            'value', GObject.BindingFlags.SYNC_CREATE,
                            transform_to=lambda _, val: val.get_string())
        combo.connect('notify::selected-item', self.on_input_changed)
        self.content_container.add(combo)

    def create_entry_row(self,
                         title: str,
                         description: str,
                         oarg:  SheetOperationArg) -> None:
        entry = Adw.EntryRow()
        entry.set_title(title)
        if description is not None:
            entry.set_subtitle(description)
        entry.bind_property('text', oarg,
                            'value', GObject.BindingFlags.SYNC_CREATE)
        entry.connect('entry-activated', self.on_input_activated)
        entry.connect('notify::text', self.on_input_changed)
        self.content_container.add(entry)

    def create_list_check(self,
                          title:       str,
                          description: str,
                          options:     list[str],
                          oarg:        SheetOperationArg) -> None:

        def setup_factory(list_item_factory: Gtk.SignalListItemFactory,
                          list_item:         Gtk.ListItem) -> None:
            check_button = Gtk.CheckButton()
            list_item.set_child(check_button)

            label = Gtk.Label(halign=Gtk.Align.START,
                              hexpand=True,
                              ellipsize=Pango.EllipsizeMode.END)
            check_button.set_child(label)

            list_item.check_button = check_button
            list_item.label = label
            list_item.bind_toggled = None

        def bind_factory(list_item_factory: Gtk.SignalListItemFactory,
                         list_item:         Gtk.ListItem) -> None:
            item_data = list_item.get_item()

            def on_toggled(button:    Gtk.Button,
                           item_data: Gtk.StringObject) -> None:
                if oarg.value == '':
                    selected_columns = []
                else:
                    selected_columns = oarg.value.split('$')
                target_column = item_data.get_string()
                if button.get_active():
                    selected_columns.append(target_column)
                else:
                    selected_columns.remove(target_column)
                oarg.value = '$'.join(selected_columns)

            if list_item.bind_toggled is not None:
                list_item.check_button.disconnect(list_item.bind_toggled)

            label = item_data.get_string()
            list_item.label.set_label(label)

            if len(options) <= 10: # TODO: find optimal behaviour
                list_item.check_button.set_active(True)

            list_item.bind_toggled = list_item.check_button.connect('toggled',
                                                                    on_toggled,
                                                                    item_data)

        def teardown_factory(list_item_factory: Gtk.SignalListItemFactory,
                             list_item:         Gtk.ListItem) -> None:
            list_item.label = None
            list_item.check_button = None
            list_item.bind_toggled = None

        group = Adw.PreferencesGroup()
        group.set_title(title)
        if description is not None:
            group.set_description(description)

        row = Adw.PreferencesRow()
        row.set_activatable(False)
        group.add(row)

        list_view = Gtk.ListView()
        list_view.set_single_click_activate(True)
        list_view.add_css_class('sheet-ops-list-view')
        row.set_child(list_view)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', setup_factory)
        factory.connect('bind', bind_factory)
        factory.connect('teardown', teardown_factory)
        list_view.set_factory(factory)

        selection = Gtk.SingleSelection()
        list_view.set_model(selection)

        string_list = Gtk.StringList()
        for option in options:
            string_list.append(option)
        selection.set_model(string_list)

        self.preferences_page.add(group)

        oarg.type = 'strv'

    def create_spin_row(self,
                        title: str,
                        description: str,
                        oarg:  SheetOperationArg) -> None:
        spin = Adw.SpinRow()
        spin.set_title(title)
        if description is not None:
            spin.set_subtitle(description)
        spin.set_range(0, 1_000_000_000)
        spin.get_adjustment().set_page_increment(5)
        spin.get_adjustment().set_step_increment(1)
        spin.bind_property('text', oarg,
                           'value', GObject.BindingFlags.SYNC_CREATE)
        spin.connect('notify::value', self.on_input_changed)
        self.content_container.add(spin)
        oarg.type = 'int'

    def create_switch_row(self,
                          title: str,
                          description: str,
                          oarg:  SheetOperationArg) -> None:
        switch = Adw.SwitchRow()
        switch.set_title(title)
        if description is not None:
            switch.set_subtitle(description)
        switch.bind_property('active', oarg,
                             'value', GObject.BindingFlags.SYNC_CREATE)
        switch.connect('notify::active', self.on_input_changed)
        self.content_container.add(switch)
        oarg.type = 'bool'

    def create_match_case_switch(self):
        self.match_case = Adw.SwitchRow()
        self.match_case.set_active(self.kwargs['match_case'])
        self.match_case.set_title('Case Sensitive (Match Case)')
        self.match_case.set_subtitle('Distinguish between uppercase and lowercase')
        self.content_container.add(self.match_case)

    def create_new_worksheet_switch(self):
        self.new_worksheet = Adw.SwitchRow()
        self.new_worksheet.set_active(self.kwargs['new_worksheet'])
        self.new_worksheet.set_title('Create a New Worksheet')
        self.new_worksheet.set_subtitle('Send the result into a new worksheet')
        self.content_container.add(self.new_worksheet)

    def create_on_column_switch(self):
        self.on_column = Adw.SwitchRow()
        self.on_column.set_active(self.kwargs['on_column'])
        self.on_column.set_title('Apply on Entire Rows')
        self.on_column.set_subtitle('Disable to apply on selection only')
        self.content_container.add(self.on_column)

    def create_use_regexp_switch(self):
        self.use_regexp = Adw.SwitchRow()
        self.use_regexp.set_active(self.kwargs['use_regexp'])
        self.use_regexp.set_title('Use Regular Expression')
        self.use_regexp.set_subtitle('Learn more about <a href="https://regexlearn.com/">'
                                     'Regular Expression</a>')
        self.content_container.add(self.use_regexp)

    def on_input_changed(self,
                         widget: Gtk.Widget,
                         pspec:  GObject.ParamSpec) -> None:
        self.live_preview()

    def on_input_activated(self, widget: Gtk.Widget) -> None:
        self.on_apply_button_clicked(self.apply_button)

    def live_preview(self, use_thread: bool = True) -> None:
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

        if not use_thread:
            update_search_list()
        else:
            threading.Thread(target=update_search_list, daemon=True).start()

    def get_callback_args(self) -> list:
        args = []

        for operation_arg in self.operation_args:
            arg = operation_arg.value

            # Cast the argument value if needed
            if operation_arg.type == 'int':
                arg = int(arg if arg.isnumeric() else 0)
            if operation_arg.type == 'bool':
                arg = utils.cast_to_boolean(arg)
            if operation_arg.type == 'strv':
                if arg == '':
                    arg = []
                else:
                    arg = arg.split('$')

            args.append(arg)

        return args