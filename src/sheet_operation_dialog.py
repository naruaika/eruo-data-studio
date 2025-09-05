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
import json

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
    options_container = Gtk.Template.Child()

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

        n_content = 0
        n_options = 0

        for item in layout:
            operation_arg = SheetOperationArg()
            self.operation_args.append(operation_arg)

            title, dtype = item[0], item[1]
            description = None
            contents = []

            if utils.is_iterable(title):
                title, description = item[0][0], item[0][1]
            if len(item) > 2:
                contents = item[2]

            match dtype:
                case 'entry':
                    self.create_entry_row(title, operation_arg)
                    n_content += 1
                case 'spin':
                    self.create_spin_row(title, description, operation_arg)
                    n_content += 1
                case 'switch':
                    self.create_switch_row(title, description, operation_arg)
                    n_content += 1
                case 'combo':
                    self.create_combo_row(title, description, contents, operation_arg)
                    n_content += 1
                case 'list-check':
                    self.create_list_check(title, description, contents, operation_arg)
                    n_content += 1
                case 'list-entry':
                    self.create_list_entry(title, contents, operation_arg)
                    # this widget needs a separate AdwPreferencesGroup

        if 'match_case' in self.kwargs:
            self.create_match_case_switch()
            n_options += 1
        if 'use_regexp' in self.kwargs:
            self.create_use_regexp_switch()
            n_options += 1
        if 'on_column' in self.kwargs:
            self.create_on_column_switch()
            n_options += 1
        if 'new_worksheet' in self.kwargs:
            self.create_new_worksheet_switch()
            n_options += 1
        if 'live_previewer' in self.kwargs:
            self.preview_container.set_visible(True)
            self.live_preview(use_thread=False) # update on startup

        # Remove or re-position to the end
        if n_content == 0:
            self.content_container.unparent()
        self.preferences_page.remove(self.options_container)
        self.preferences_page.remove(self.preview_container)
        if n_options > 0:
            self.preferences_page.add(self.options_container)
        if 'live_previewer' in self.kwargs:
            self.preferences_page.add(self.preview_container)

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
                         title:       str,
                         description: str,
                         options:     list[str],
                         ops_arg:     SheetOperationArg) -> None:
        combo = Adw.ComboRow()
        combo.set_title(title)
        if description is not None:
            combo.set_subtitle(description)
        combo_model = Gtk.StringList()
        for option in options:
            combo_model.append(option)
        combo.set_model(combo_model)
        combo.bind_property('selected-item', ops_arg,
                            'value', GObject.BindingFlags.SYNC_CREATE,
                            transform_to=lambda _, val: val.get_string())
        combo.connect('notify::selected-item', self.on_input_changed)
        self.content_container.add(combo)

    def create_entry_row(self,
                         title:   str,
                         ops_arg: SheetOperationArg) -> None:
        entry = Adw.EntryRow()
        entry.set_title(title)
        entry.bind_property('text', ops_arg,
                            'value', GObject.BindingFlags.SYNC_CREATE)
        entry.connect('entry-activated', self.on_input_activated)
        entry.connect('notify::text', self.on_input_changed)
        self.content_container.add(entry)

    def create_list_entry(self,
                          title:      str,
                          contents:   list,
                          ops_arg:    SheetOperationArg,
                          group:      Adw.PreferencesGroup = None,
                          add_button: Adw.ButtonRow = None) -> None:
        # Initialize the operation arguments with an empty string
        # where each argument correspond to a child input widget.
        ops_arg.value = json.dumps([''] * (1 + len(contents)))

        def on_entry_changed(widget: Gtk.Widget,
                             pspec:  GObject.ParamSpec) -> None:
            arg = ops_arg.value
            args = json.loads(arg) if arg else []
            args[0] = widget.get_text()
            ops_arg.value = json.dumps(args)
            self.on_input_changed(widget, pspec)

        if create_new_group := group is None:
            group = Adw.PreferencesGroup()
            self.preferences_page.add(group)

        entry = Adw.EntryRow()
        entry.set_title(title)
        entry.add_css_class('list-entry-item')
        entry.connect('notify::text', on_entry_changed)
        group.add(entry)

        box = entry.get_first_child()
        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_spacing(10)

        suffix = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        suffix.set_spacing(6)
        suffix.set_homogeneous(True)
        suffix.set_visible(len(contents) > 0)
        entry.add_suffix(suffix)

        chindex = 1 # the first index (or zero) is already taken
                    # by the entry widget, so we start from one.
        for dtype, options in contents:
            match dtype:
                case 'dropdown':
                    self.create_suffix_dropdown(options, suffix, chindex, ops_arg)
            chindex += 1

        def on_add_button_clicked(button: Gtk.Button) -> None:
            new_ops_arg = SheetOperationArg()
            self.operation_args.append(new_ops_arg)
            self.create_list_entry(title, contents, new_ops_arg, group, button)

        def on_delete_button_clicked(button: Gtk.Button) -> None:
            group.remove(entry)
            ops_index = self.operation_args.index(ops_arg)
            del self.operation_args[ops_index]

        delete_button = Gtk.Button()
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.add_css_class('flat')
        delete_button.connect('clicked', on_delete_button_clicked)
        entry.add_suffix(delete_button)

        if create_new_group:
            add_button = Adw.ButtonRow()
            add_button.set_title(_('Add') + ' ' + title)
            add_button.set_start_icon_name('list-add-symbolic')
            add_button.connect('activated', on_add_button_clicked)
            group.add(add_button)
        else:
            # Re-position to the end
            group.remove(add_button)
            group.add(add_button)

        ops_arg.type = 'strv'

    def create_list_check(self,
                          title:       str,
                          description: str,
                          options:     list[str],
                          ops_arg:     SheetOperationArg) -> None:

        def on_check_toggled(button: Gtk.CheckButton,
                             value:  str) -> None:
            args = json.loads(ops_arg.value) \
                   if ops_arg.value else []
            args.append(value) if button.get_active() \
                               else args.remove(value)
            ops_arg.value = json.dumps(args)

        row = Adw.PreferencesRow()
        row.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.set_child(box)

        box.get_parent().set_activatable(False)

        subbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        subbox.set_margin_top(6)
        subbox.set_margin_bottom(6)
        subbox.set_margin_start(10)
        subbox.set_margin_end(10)
        subbox.add_css_class('title')
        box.append(subbox)

        label_title = Gtk.Label()
        label_title.set_halign(Gtk.Align.START)
        label_title.set_ellipsize(Pango.EllipsizeMode.END)
        label_title.add_css_class('title')
        label_title.set_label(title)
        subbox.append(label_title)

        if description is not None:
            label_description = Gtk.Label()
            label_description.set_halign(Gtk.Align.START)
            label_description.set_wrap_mode(Gtk.WrapMode.WORD)
            label_description.add_css_class('subtitle')
            label_description.set_label(description)
            subbox.append(label_description)

        list_view = Gtk.FlowBox()
        list_view.set_selection_mode(Gtk.SelectionMode.NONE)
        list_view.set_min_children_per_line(2)
        list_view.set_homogeneous(True)
        list_view.add_css_class('sheet-ops-list-view')
        box.append(list_view)

        for option in options:
            label = Gtk.Label()
            label.set_halign(Gtk.Align.START)
            label.set_valign(Gtk.Align.CENTER)
            label.set_hexpand(True)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_label(option)
            check_button = Gtk.CheckButton()
            check_button.set_child(label)
            check_button.connect('toggled', on_check_toggled, option)
            list_view.append(check_button)

        self.content_container.add(row)

        ops_arg.type = 'strv'

    def create_spin_row(self,
                        title:       str,
                        description: str,
                        ops_arg:     SheetOperationArg) -> None:
        spin = Adw.SpinRow()
        spin.set_title(title)
        if description is not None:
            spin.set_subtitle(description)
        spin.set_range(0, 1_000_000_000)
        spin.get_adjustment().set_page_increment(5)
        spin.get_adjustment().set_step_increment(1)
        spin.bind_property('text', ops_arg,
                           'value', GObject.BindingFlags.SYNC_CREATE)
        spin.connect('notify::value', self.on_input_changed)
        self.content_container.add(spin)
        ops_arg.type = 'int'

    def create_switch_row(self,
                          title:       str,
                          description: str,
                          ops_arg:     SheetOperationArg) -> None:
        switch = Adw.SwitchRow()
        switch.set_title(title)
        if description is not None:
            switch.set_subtitle(description)
        switch.bind_property('active', ops_arg,
                             'value', GObject.BindingFlags.SYNC_CREATE)
        switch.connect('notify::active', self.on_input_changed)
        self.content_container.add(switch)
        ops_arg.type = 'bool'

    def create_suffix_dropdown(self,
                               options: list,
                               parent:  Gtk.Widget,
                               chindex: int,
                               ops_arg: SheetOperationArg) -> None:
        dropdown = Gtk.DropDown.new()
        dropdown.set_hexpand(True)
        dropdown.set_valign(Gtk.Align.CENTER)

        def setup_factory_dropdown(list_item_factory: Gtk.SignalListItemFactory,
                                   list_item:         Gtk.ListItem) -> None:
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
            list_item.bind_item = None

        def bind_factory_dropdown(list_item_factory: Gtk.SignalListItemFactory,
                                  list_item:         Gtk.ListItem) -> None:
            item_data = list_item.get_item()
            label = item_data.get_string()

            def on_list_item_selected(*args) -> None:
                is_selected = list_item.get_selected()
                list_item.image.set_opacity(is_selected)
                if not is_selected:
                    return
                arg = ops_arg.value
                args = json.loads(arg) if arg else []
                args[chindex] = label
                ops_arg.value = json.dumps(args)
                self.on_input_changed()

            list_item.label.set_label(label)

            if list_item.bind_item is not None:
                list_item.disconnect(list_item.bind_item)

            list_item.bind_item = dropdown.connect('notify::selected-item', on_list_item_selected)
            on_list_item_selected()

        def teardown_factory_dropdown(list_item_factory: Gtk.SignalListItemFactory,
                                      list_item:         Gtk.ListItem) -> None:
            list_item.label = None
            list_item.image = None
            list_item.bind_item = None

        dropdown_model = Gtk.StringList()
        for option in options:
            dropdown_model.append(option)
        dropdown.set_model(dropdown_model)

        dropdown_list_factory = Gtk.SignalListItemFactory()
        dropdown_list_factory.connect('setup', setup_factory_dropdown)
        dropdown_list_factory.connect('bind', bind_factory_dropdown)
        dropdown_list_factory.connect('teardown', teardown_factory_dropdown)
        dropdown.set_list_factory(dropdown_list_factory)

        dropdown_factory = Gtk.BuilderListItemFactory.new_from_bytes(None, GLib.Bytes.new(bytes(
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
        dropdown.set_factory(dropdown_factory)

        parent.append(dropdown)

    def create_match_case_switch(self):
        self.match_case = Adw.SwitchRow()
        self.match_case.set_active(self.kwargs['match_case'])
        self.match_case.set_title('Case Sensitive (Match Case)')
        self.match_case.set_subtitle('Distinguish between uppercase and lowercase')
        self.options_container.add(self.match_case)

    def create_new_worksheet_switch(self):
        self.new_worksheet = Adw.SwitchRow()
        self.new_worksheet.set_active(self.kwargs['new_worksheet'])
        self.new_worksheet.set_title('Create a New Worksheet')
        self.new_worksheet.set_subtitle('Send the result into a new worksheet')
        self.options_container.add(self.new_worksheet)

    def create_on_column_switch(self):
        self.on_column = Adw.SwitchRow()
        self.on_column.set_active(self.kwargs['on_column'])
        self.on_column.set_title('Apply on Entire Rows')
        self.on_column.set_subtitle('Disable to apply on selection only')
        self.options_container.add(self.on_column)

    def create_use_regexp_switch(self):
        self.use_regexp = Adw.SwitchRow()
        self.use_regexp.set_active(self.kwargs['use_regexp'])
        self.use_regexp.set_title('Use Regular Expression')
        self.use_regexp.set_subtitle('Learn more about <a href="https://regexlearn.com/">'
                                     'Regular Expression</a>')
        self.options_container.add(self.use_regexp)

    def on_input_changed(self, *args) -> None:
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

            GLib.idle_add(self.preview_list_store.remove_all)
            GLib.idle_add(self.preview_list_store.splice, 0, 0, list_items_to_add)

        if not use_thread:
            update_search_list()
            return
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
                arg = json.loads(arg) if arg else []

            args.append(arg)

        return args