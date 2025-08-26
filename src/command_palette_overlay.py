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
from typing import Any
import html

from . import utils
from .window import Window

class CommandListItem(GObject.Object):
    __gtype_name__ = 'CommandListItem'

    action_name = GObject.Property(type=str, default='')
    title = GObject.Property(type=str, default='Command')
    label = GObject.Property(type=str, default='Command')

    is_separator = GObject.Property(type=bool, default=False)
    is_recent_item = GObject.Property(type=bool, default=False)

    shortcuts: list[str] = []
    steal_focus: bool = False
    will_prompt: bool = False

    def __init__(self,
                 action_name:    str = '',
                 title:          str = '',
                 shortcuts:      list[str] = [],
                 steal_focus:    bool = False,
                 will_prompt:    bool = False,
                 is_separator:   bool = False,
                 is_recent_item: bool = False) -> None:
        super().__init__()

        self.action_name = action_name
        self.title = title
        self.label = title

        self.is_separator = is_separator
        self.is_recent_item = is_recent_item

        self.shortcuts = shortcuts or []
        self.steal_focus = steal_focus
        self.will_prompt = will_prompt



@Gtk.Template(resource_path='/com/macipra/eruo/ui/command-palette-overlay.ui')
class CommandPaletteOverlay(Adw.Bin):
    __gtype_name__ = 'CommandPaletteOverlay'

    command_overlay = Gtk.Template.Child()
    command_entry = Gtk.Template.Child()

    prompt_text = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()

    list_view = Gtk.Template.Child()
    list_store = Gtk.Template.Child()
    selection = Gtk.Template.Child()

    MAX_RECENT_COMMANDS = 10

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

        self.mouse_x = -1
        self.mouse_y = -1

        self.command_titles = [] # for faster subsequence search

        self.list_separator = CommandListItem(is_separator=True)

        for command in commands:
            list_item = CommandListItem(command['action-name'],
                                        command['title'],
                                        command['shortcuts'],
                                        command['steal-focus'],
                                        command['will-prompt'])
            self.command_titles.append(list_item.title)
            self.list_store.append(list_item)

        self.recent_command_titles = []

        self.is_prompting = False
        self.prompt_callback = None
        self.prompt_arguments = []
        self.will_prompt_again = False

    def setup_factory(self,
                      list_item_factory: Gtk.SignalListItemFactory,
                      list_item:         Gtk.ListItem) -> None:
        list_item.set_focusable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_item.set_child(box)

        content = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(content)

        label = Gtk.Label(halign=Gtk.Align.START,
                          ellipsize=Pango.EllipsizeMode.END,
                          use_markup=True)
        content.set_start_widget(label)

        shortcut = Gtk.Label(halign=Gtk.Align.END)
        shortcut.add_css_class('command-shortcut')
        shortcut.add_css_class('dimmed')
        content.set_end_widget(shortcut)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL,
                                  visible=False)
        box.append(separator)

        list_item.content = content
        list_item.label = label
        list_item.shortcut = shortcut
        list_item.separator = separator

    def bind_factory(self,
                     list_item_factory: Gtk.SignalListItemFactory,
                     list_item:         Gtk.ListItem) -> None:
        item_data = list_item.get_item()

        if item_data.is_separator:
            list_item.set_focusable(False)
            list_item.set_selectable(False)
            list_item.set_activatable(False)
            list_item.content.set_visible(False)
            list_item.separator.set_visible(True)
            return

        list_item.label.set_label(item_data.label)
        list_item.shortcut.set_visible(False)

        item_data.bind_property('label', list_item.label,
                                'label', GObject.BindingFlags.SYNC_CREATE)

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
        list_item.content = None
        list_item.label = None
        list_item.shortcut = None
        list_item.separator = None

    def on_command_entry_deleted(self,
                                 entry:     Gtk.Entry,
                                 start_pos: int,
                                 end_pos:   int) -> None:
        self.on_command_entry_changed(entry)

    def on_command_entry_changed(self, entry: Gtk.Entry) -> None:
        if self.is_prompting:
            return

        query = entry.get_text()

        if query == '':
            # Reset all the labels
            for iidx in range(self.list_store.get_n_items()):
                current_item = self.list_store.get_item(iidx)
                current_item.label = current_item.title

            # Show all items if the query is empty
            self.selection.set_model(self.list_store)
            self.list_view.scroll_to(0, Gtk.ListScrollFlags.SELECT, None)
            return

        new_list_store = Gio.ListStore()

        # Get all the items that match the query
        for iidx in range(self.list_store.get_n_items()):
            current_item = self.list_store.get_item(iidx)

            # Skip recent and separator items
            if current_item.is_recent_item or current_item.is_separator:
                continue

            # Get the highlighted string for the current item
            highlighted_title = self.get_highlighted_string(query, current_item.title)

            # If a match was found, update the item with the highlighted title
            # and append it to the new list store.
            if highlighted_title is not None:
                current_item.label = highlighted_title
                new_list_store.append(current_item)

        self.selection.set_model(new_list_store)

        n_list_items = new_list_store.get_n_items()

        self.scrolled_window.get_vscrollbar().set_visible(n_list_items > 3)
        self.scrolled_window.set_visible(n_list_items > 0)

        self.prompt_text.set_label('No matching commands')
        self.prompt_text.set_visible(n_list_items == 0)

        if n_list_items == 0:
            return

        self.list_view.set_single_click_activate(False)
        self.list_view.scroll_to(0, Gtk.ListScrollFlags.SELECT, None)

    def on_command_entry_activated(self, entry: Gtk.Entry) -> None:
        if self.is_prompting:
            will_prompt = self.will_prompt_again
            if not utils.is_iterable(self.prompt_arguments):
                self.prompt_arguments = [self.prompt_arguments]
            self.prompt_callback(entry.get_text(), *self.prompt_arguments)
            self.close_command_overlay(steal_focus=False, will_prompt=will_prompt)
            return

        selected_item = self.selection.get_selected_item()
        action_name = selected_item.action_name

        if len(self.recent_command_titles) == 0:
            self.list_store.insert(0, self.list_separator)

        # Add the selected item to the recently used commands
        selected_item = CommandListItem(action_name,
                                        selected_item.title,
                                        selected_item.shortcuts,
                                        selected_item.steal_focus,
                                        selected_item.will_prompt,
                                        is_recent_item=True)

        if selected_item.title in self.recent_command_titles:
            list_item_index = self.recent_command_titles.index(selected_item.title)
            self.list_store.remove(list_item_index)
            self.recent_command_titles.remove(selected_item.title)

        self.list_store.insert(0, selected_item)
        self.recent_command_titles.insert(0, selected_item.title)

        if len(self.recent_command_titles) > self.MAX_RECENT_COMMANDS:
            self.list_store.remove(self.MAX_RECENT_COMMANDS)
            self.recent_command_titles.pop()

        self.window.get_application().activate_action(action_name, None)
        self.close_command_overlay(selected_item.steal_focus,
                                   selected_item.will_prompt)

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
            n_items = self.selection.get_model().get_n_items()

            position = self.selection.get_selected()
            position += 1 if keyval == Gdk.KEY_Down else -1
            position %= n_items

            # Prevent the mouse cursor from interrupting the selection,
            # it'll be enabled back when the user moves the mouse again
            self.list_view.set_single_click_activate(False)

            if len(self.recent_command_titles) > 0 \
                    and position == len(self.recent_command_titles) \
                    and self.command_entry.get_text() == '':
                if keyval == Gdk.KEY_Up:
                    position -= 1
                if keyval == Gdk.KEY_Down:
                    position += 1
                position %= n_items

            self.list_view.scroll_to(position, Gtk.ListScrollFlags.SELECT, None)
            return True

        return False

    def on_unfocused(self, event: Gtk.EventControllerFocus) -> None:
        if self.is_animating_uis:
            return
        self.close_command_overlay()

    def on_motion(self,
                  event: Gtk.EventControllerMotion,
                  x:     float,
                  y:     float) -> None:
        if self.is_animating_uis:
            return
        if self.mouse_x == x and self.mouse_y == y:
            return
        self.mouse_x = x
        self.mouse_y = y
        self.list_view.set_single_click_activate(True)

    def open_command_overlay(self,
                             as_prompt:   bool = False,
                             prompt_text: str = '',
                             callback:    callable = None,
                             user_data:   Any = [],
                             more_prompt: bool = False) -> None:
        self.is_prompting = as_prompt
        self.prompt_callback = callback
        self.prompt_arguments = user_data
        self.will_prompt_again = more_prompt

        self.prompt_text.set_label(f"{prompt_text} (Press 'Enter' to confirm or 'Escape' to cancel)")
        self.prompt_text.set_visible(as_prompt)

        self.scrolled_window.set_visible(not as_prompt)
        self.list_view.set_single_click_activate(False)

        self.set_visible(True)

        self.command_entry.set_text('')
        self.command_entry.grab_focus()

        if as_prompt:
            return

        self.prompt_text.set_visible(False)
        self.scrolled_window.set_visible(True)

        self.is_animating_uis = True
        def stop_animating_uis() -> None:
            self.is_animating_uis = False

        self.command_overlay.add_css_class('slide-up-dialog')
        GLib.timeout_add(200, self.command_overlay.remove_css_class, 'slide-up-dialog')
        GLib.timeout_add(200, stop_animating_uis)

    def close_command_overlay(self,
                              steal_focus: bool = False,
                              will_prompt: bool = False) -> None:
        if will_prompt:
            return

        self.is_prompting = False
        self.prompt_callback = None
        self.prompt_arguments = []
        self.will_prompt_again = False

        self.command_overlay.add_css_class('slide-down-dialog')
        GLib.timeout_add(200, self.set_visible, False)
        GLib.timeout_add(200, self.command_overlay.remove_css_class, 'slide-down-dialog')

        if steal_focus:
            return

        sheet_view = self.window.get_current_active_view()

        if sheet_view is None:
            return

        # Focus on the main canvas
        sheet_view.main_canvas.set_focusable(True)
        sheet_view.main_canvas.grab_focus()

    def find_subsequence_indices(self,
                                 query:  str,
                                 target: str) -> list[int]:
        """
        Finds the indices of the characters in `target` that form the `query` subsequence.

        Returns a list of indices if found, otherwise None.
        """
        qlower = query.lower()
        tlower = target.lower()

        query_index = 0
        target_index = 0
        matched_indices = []

        while query_index < len(qlower) and target_index < len(tlower):
            if qlower[query_index] == tlower[target_index]:
                matched_indices.append(target_index)
                query_index += 1
            target_index += 1

        # If we matched every character in the query, return the indices
        if query_index == len(qlower):
            return matched_indices
        return None

    def get_highlighted_string(self,
                               query:  str,
                               target: str) -> str:
        """
        Generates an HTML string with `<b>` tags around the matched subsequence.

        Returns the highlighted string if a match is found, otherwise None.
        """
        # Unescape the target string for the subsequence search
        plain_target = html.unescape(target)
        matched_indices = self.find_subsequence_indices(query, plain_target)

        if matched_indices is None:
            return None

        is_matched_at_index = {idx for idx in matched_indices}

        parts = []
        orig_target_cursor = 0
        plain_cursor = 0

        # Iterate through the original target string
        while orig_target_cursor < len(target):
            is_bold = plain_cursor in is_matched_at_index

            # Determine if we need to start a new bold tag
            if is_bold and (plain_cursor == 0 or
                            plain_cursor - 1 not in is_matched_at_index):
                parts.append('<u>')

            # Check for HTML entities in the original string
            if target[orig_target_cursor] == '&':
                end_entity_index = target.find(';', orig_target_cursor)
                if end_entity_index != -1:
                    entity_str = target[orig_target_cursor:end_entity_index + 1]
                    parts.append(entity_str)
                    orig_target_cursor = end_entity_index + 1
                else: # Malformed entity, treat '&' as a regular character
                    parts.append('&')
                    orig_target_cursor += 1
            else:
                # Handle regular characters
                parts.append(target[orig_target_cursor])
                orig_target_cursor += 1

            # Determine if we need to close the bold tag
            if is_bold and (plain_cursor + 1 not in is_matched_at_index):
                parts.append('</u>')

            plain_cursor += 1

        return ''.join(parts)