# clipboard_manager.py
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


from gi.repository import Gdk, GObject

class ClipboardManager(GObject.Object):
    __gtype_name__ = 'ClipboardManager'

    def __init__(self) -> None:
        super().__init__()

        display = Gdk.Display.get_default()
        self.clipboard = display.get_clipboard()

        from .sheet_selection import SheetCell
        self.range: SheetCell = None

    def set_text(self, text: str) -> None:
        self.clipboard.set(GObject.Value(str, text))

    def read_text_async(self, callback: callable) -> None:
        self.clipboard.read_text_async(None, callback)

    def clear(self) -> None:
        self.clipboard.set_content(None)
        self.range = None