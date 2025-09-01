# file_save_as_csv_view.py
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


from gi.repository import Adw, Gio, Gtk
from pathlib import Path

@Gtk.Template(resource_path='/com/macipra/eruo/ui/file-save-as-csv-view.ui')
class FileSaveAsCsvView(Adw.PreferencesPage):
    __gtype_name__ = 'FileSaveAsCsvView'

    save_as = Gtk.Template.Child()
    save_to = Gtk.Template.Child()

    include_header = Gtk.Template.Child()

    separator = Gtk.Template.Child()
    line_terminator = Gtk.Template.Child()
    quote_character = Gtk.Template.Child()

    datetime_format = Gtk.Template.Child()
    date_format = Gtk.Template.Child()
    time_format = Gtk.Template.Child()

    def __init__(self,
                 file_name: str,
                 folder_path: str,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        if file_name is not None:
            self.save_as.set_text(file_name)

        if folder_path is not None:
            self.save_to.set_text(folder_path)

    @Gtk.Template.Callback()
    def on_save_to_clicked(self, button: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title('Save To')
        dialog.set_initial_folder(Gio.File.new_for_path(str(Path.home())))
        dialog.set_modal(True)

        dialog.select_folder(self.get_root(),
                             None,
                             self.on_save_to_dialog_dismissed)

    def on_save_to_dialog_dismissed(self,
                                    dialog: Gtk.FileDialog,
                                    result: Gio.Task) -> None:
        if result.had_error():
            return
        folder = dialog.select_folder_finish(result)
        self.save_to.set_text(folder.get_path())

    @Gtk.Template.Callback()
    def on_reset_default_clicked(self, button: Gtk.Button) -> None:
        self.include_header.set_active(True)

        self.separator.set_text(',')
        self.line_terminator.set_text('\\n')
        self.quote_character.set_text('"')

        self.datetime_format.set_text('%Y-%m-%d %H:%M:%S')
        self.date_format.set_text('%Y-%m-%d')
        self.time_format.set_text('%H:%M:%S')