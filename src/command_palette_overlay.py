# command_palette_overlay.py
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


from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from .window import Window

class CommandListItem(GObject.Object):
    __gtype_name__ = 'CommandListItem'

    action_name = GObject.Property(type=str, default='')
    title = GObject.Property(type=str, default='Command')
    shortcuts: list[str] = []

    def __init__(self,
                 action_name: str,
                 title:       str,
                 shortcuts:   list[str]) -> None:
        super().__init__()

        self.action_name = action_name
        self.title = title
        self.shortcuts = shortcuts or []



@Gtk.Template(resource_path='/com/macipra/eruo/ui/command-palette-overlay.ui')
class CommandPaletteOverlay(Adw.Bin):
    __gtype_name__ = 'CommandPaletteOverlay'

    command_overlay = Gtk.Template.Child()
    command_entry = Gtk.Template.Child()

    list_view = Gtk.Template.Child()
    list_store = Gtk.Template.Child()
    selection = Gtk.Template.Child()

    def __init__(self,
                 window:   Window,
                 commands: list[dict],
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window

        self.is_animating_uis: bool = False

        self.list_view.set_single_click_activate(False)

        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_factory)
        factory.connect('bind', self.bind_factory)
        factory.connect('teardown', self.teardown_factory)
        self.list_view.set_factory(factory)

        self.command_entry.connect('changed', self.on_command_entry_changed)
        self.command_entry.connect('delete-text', self.on_command_entry_deleted)
        self.command_entry.connect('activate', self.on_command_entry_activated)

        self.list_view.connect('activate', self.on_list_view_activated)
        self.selection.connect('selection-changed', self.on_selection_changed)

        key_event_controller = Gtk.EventControllerKey()
        key_event_controller.connect('key-pressed', self.on_key_pressed)
        self.add_controller(key_event_controller)

        focus_event_controller = Gtk.EventControllerFocus()
        focus_event_controller.connect('leave', self.on_unfocused)
        self.add_controller(focus_event_controller)

        motion_event_controller = Gtk.EventControllerMotion()
        motion_event_controller.connect('motion', self.on_motion)
        self.add_controller(motion_event_controller)

        self.command_titles = [] # for faster subsequence search

        for command in commands:
            list_item = CommandListItem(command['action-name'],
                                        command['title'],
                                        command['shortcuts'])
            self.command_titles.append(list_item.title)
            self.list_store.append(list_item)

    def setup_factory(self,
                      list_item_factory: Gtk.SignalListItemFactory,
                      list_item:         Gtk.ListItem) -> None:
        list_item.set_focusable(False)

        box = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL)
        list_item.set_child(box)

        ctitle = Gtk.Label()
        ctitle.set_halign(Gtk.Align.START)
        ctitle.set_ellipsize(Pango.EllipsizeMode.END)
        box.set_start_widget(ctitle)

        shortcut = Gtk.Label()
        shortcut.set_halign(Gtk.Align.END)
        shortcut.add_css_class('command-shortcut')
        shortcut.add_css_class('dimmed')
        box.set_end_widget(shortcut)

        list_item.ctitle = ctitle
        list_item.shortcut = shortcut

    def bind_factory(self,
                     list_item_factory: Gtk.SignalListItemFactory,
                     list_item:         Gtk.ListItem) -> None:
        item_data = list_item.get_item()

        list_item.ctitle.set_label(item_data.title)
        list_item.shortcut.set_visible(False)

        if len(item_data.shortcuts) > 0:
            shortcut_string = item_data.shortcuts[0]
            is_parsed, accel_key, accel_mods = Gtk.accelerator_parse(shortcut_string)

            if is_parsed:
                label = Gtk.accelerator_get_label(accel_key, accel_mods)
                list_item.shortcut.set_label(label)
                list_item.shortcut.set_visible(True)

    def teardown_factory(self,
                         list_item_factory: Gtk.SignalListItemFactory,
                         list_item:         Gtk.ListItem) -> None:
        list_item.ctitle = None
        list_item.shortcut = None

    def on_command_entry_deleted(self,
                                 entry:     Gtk.Entry,
                                 start_pos: int,
                                 end_pos:   int) -> None:
        self.on_command_entry_changed(entry)

    def on_command_entry_changed(self, entry: Gtk.Entry) -> None:
        query = entry.get_text()

        # Show all items if the query is empty
        if query == '':
            self.selection.set_model(self.list_store)
            self.list_view.scroll_to(0, Gtk.ListScrollFlags.SELECT, None)
            return

        new_list_store = Gio.ListStore()

        # Get all the items that match the query
        for iidx in range(self.list_store.get_n_items()):
            current_item = self.list_store.get_item(iidx)
            if self.is_subsequence(query, current_item.title):
                new_list_store.append(current_item)

        self.selection.set_model(new_list_store)

        if new_list_store.get_n_items() == 0:
            return

        self.list_view.set_single_click_activate(False)
        self.list_view.scroll_to(0, Gtk.ListScrollFlags.SELECT, None)

    def on_command_entry_activated(self, entry: Gtk.Entry) -> None:
        action_name = self.selection.get_selected_item().action_name
        self.window.get_application().activate_action(action_name, None)
        self.close_command_overlay()

    def on_list_view_activated(self,
                               list_view: Gtk.ListView,
                               position:  int) -> None:
        self.on_command_entry_activated(self.command_entry)

    def on_selection_changed(self,
                             selection: Gtk.SelectionModel,
                             position:  int,
                             n_items:   int) -> None:
        pass

    def on_key_pressed(self,
                       event:   Gtk.EventControllerKey,
                       keyval:  int,
                       keycode: int,
                       state:   Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close_command_overlay()
            return False

        # Cycle through the commands and keep the focus on the entry box
        if keyval in {Gdk.KEY_Up, Gdk.KEY_Down}:
            position = self.selection.get_selected()
            position += 1 if keyval == Gdk.KEY_Down else -1
            position %= self.selection.get_model().get_n_items()

            # Prevent the mouse cursor from interrupting the selection,
            # it'll be enabled back when the user moves the mouse again
            self.list_view.set_single_click_activate(False)

            self.list_view.scroll_to(position, Gtk.ListScrollFlags.SELECT, None)
            return True

        return False

    def on_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        self.close_command_overlay()

    def on_motion(self,
                  event: Gtk.EventControllerMotion,
                  x:     float,
                  y:     float) -> None:
        if self.is_animating_uis:
            return
        self.list_view.set_single_click_activate(True)

    def open_command_overlay(self) -> None:
        self.list_view.set_single_click_activate(False)
        self.set_visible(True)

        self.command_entry.set_text('')
        self.command_entry.grab_focus()

        self.is_animating_uis = True
        def stop_animating_uis() -> None:
            self.is_animating_uis = False

        self.command_overlay.add_css_class('slide-up-dialog')
        GLib.timeout_add(200, self.command_overlay.remove_css_class, 'slide-up-dialog')
        GLib.timeout_add(200, stop_animating_uis)

    def close_command_overlay(self) -> None:
        self.command_overlay.add_css_class('slide-down-dialog')
        GLib.timeout_add(200, self.set_visible, False)
        GLib.timeout_add(200, self.command_overlay.remove_css_class, 'slide-down-dialog')

        sheet_view = self.window.get_current_active_view()

        if sheet_view is None:
            return

        # Focus on the main canvas
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    def is_subsequence(self,
                       query:  str,
                       target: str) -> bool:
        query = query.lower()
        target = target.lower()

        qidx = 0
        tidx = 0

        while qidx < len(query) and \
              tidx < len(target):
            if query[qidx] == target[tidx]:
                qidx += 1
            tidx += 1

        return qidx == len(query)