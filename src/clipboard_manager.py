# clipboard_manager.py
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