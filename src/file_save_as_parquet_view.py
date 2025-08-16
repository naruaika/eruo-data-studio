# file_save_as_parquet_view.py
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


from gi.repository import Adw, Gio, GObject, Gtk
from pathlib import Path

@Gtk.Template(resource_path='/com/macipra/eruo/ui/file-save-as-parquet-view.ui')
class FileSaveAsParquetView(Adw.PreferencesPage):
    __gtype_name__ = 'FileSaveAsParquetView'

    save_as = Gtk.Template.Child()
    save_to = Gtk.Template.Child()

    statistics = Gtk.Template.Child()

    compression = Gtk.Template.Child()
    compression_level = Gtk.Template.Child()

    def __init__(self,
                 file_name:   str,
                 folder_path: str,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        if file_name is not None:
            self.save_as.set_text(file_name)

        if folder_path is not None:
            self.save_to.set_subtitle(folder_path)

    @Gtk.Template.Callback()
    def on_save_to_activated(self, button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title('Save To')
        dialog.set_modal(True)

        home_path = Gio.File.new_for_path(str(Path.home()))
        dialog.set_initial_folder(home_path)

        dialog.select_folder(self.get_root(),
                             None,
                             self.on_save_to_dialog_dismissed)

    def on_save_to_dialog_dismissed(self,
                                    dialog: Gtk.FileDialog,
                                    result: Gio.Task) -> None:
        if result.had_error():
            return

        folder = dialog.select_folder_finish(result)
        self.save_to.set_subtitle(folder.get_path())

    @Gtk.Template.Callback()
    def on_compression_selected(self,
                                combo_box: Adw.ComboRow,
                                pspec:     GObject.ParamSpec) -> None:
        compression_map = {
            'zstd': (1, 22),
            'brotli': (0, 11),
            'uncompressed': (0, 0),
        }
        default_range = (1, 9)

        selected = combo_box.get_selected_item().get_string()
        start, end = compression_map.get(selected, default_range)
        self.compression_level.set_range(start, end)

        level = self.compression_level.get_value()
        level = max(min(level, end), start)
        self.compression_level.set_value(level)

    @Gtk.Template.Callback()
    def on_reset_default_clicked(self, button: Gtk.Button) -> None:
        self.statistics.set_active(True)

        self.compression.set_selected_item('zstd')
        self.compression_level.set_value(1)