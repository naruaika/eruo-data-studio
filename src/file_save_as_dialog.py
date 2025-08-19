# file_save_as_dialog.py
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
import os

from .file_save_as_csv_view import FileSaveAsCsvView
from .file_save_as_erbook_view import FileSaveAsErbookView
from .file_save_as_json_view import FileSaveAsJsonView
from .file_save_as_parquet_view import FileSaveAsParquetView
from .window import Window

@Gtk.Template(resource_path='/com/macipra/eruo/ui/file-save-as-dialog.ui')
class FileSaveAsDialog(Adw.Dialog):
    __gtype_name__ = 'FileSaveAsDialog'

    view_stack = Gtk.Template.Child()

    warning_banner = Gtk.Template.Child()

    def __init__(self,
                 window:   Window,
                 callback: callable,
                 **kwargs) -> None:
        super().__init__(**kwargs)

        self.window = window
        self.callback = callback

        file_name = 'Book1'
        folder_path = str(Path.home())

        if window.file is not None:
            file_path = window.file.get_path()
            file_name = os.path.basename(file_path).split('.')[0]
            folder_path = os.path.dirname(file_path)

        view = FileSaveAsErbookView(file_name, folder_path)
        self.view_stack.add_titled(view, 'erbook', 'Erbook')

        view = FileSaveAsCsvView(file_name, folder_path)
        self.view_stack.add_titled(view, 'csv', 'CSV')

        view = FileSaveAsJsonView(file_name, folder_path)
        self.view_stack.add_titled(view, 'json', 'JSON')

        view = FileSaveAsParquetView(file_name, folder_path)
        self.view_stack.add_titled(view, 'parquet', 'Parquet')

        self.visible_view = self.view_stack.get_visible_child()
        self.view_stack.connect('notify::visible-child', self.on_visible_child_changed)

    def on_visible_child_changed(self,
                                 stack: Adw.ViewStack,
                                 pspec: GObject.ParamSpec) -> None:
        view = self.view_stack.get_visible_child()

        save_as_value = self.visible_view.save_as.get_text()
        save_to_value = self.visible_view.save_to.get_subtitle()

        # Copy the text and subtitle from the previous view
        view.save_as.set_text(save_as_value)
        view.save_to.set_subtitle(save_to_value)

        self.visible_view = view

        self.warning_banner.set_revealed(not isinstance(view, FileSaveAsErbookView))

    @Gtk.Template.Callback()
    def on_warning_banner_button_clicked(self, button: Gtk.Button) -> None:
        self.view_stack.set_visible_child_name('erbook')
        self.warning_banner.set_revealed(False)

    @Gtk.Template.Callback()
    def on_save_button_clicked(self, button: Gtk.Button) -> None:
        view = self.view_stack.get_visible_child()

        file_format = ''
        match view:
            case FileSaveAsErbookView():
                file_format = '.erbook'
            case FileSaveAsCsvView():
                file_format = '.csv'
            case FileSaveAsJsonView():
                file_format = '.json'
            case FileSaveAsParquetView():
                file_format = '.parquet'

        file_name = view.save_as.get_text()
        folder_path = view.save_to.get_subtitle()

        file_path = f'{folder_path}/{file_name}{file_format}'
        file_path = file_path.replace('~', str(Path.home()))

        if self.check_file_exists(file_path):
            return

        match view:
            case FileSaveAsErbookView():
                self.save_as_erbook(view)
            case FileSaveAsCsvView():
                self.save_as_csv(view)
            case FileSaveAsJsonView():
                self.save_as_json(view)
            case FileSaveAsParquetView():
                self.save_as_parquet(view)

    def save_as_erbook(self, view: FileSaveAsErbookView) -> None:
        file_name = view.save_as.get_text()
        folder_path = view.save_to.get_subtitle()
        file_path = f'{folder_path}/{file_name}.erbook'
        self.write_file(file_path)

    def save_as_csv(self, view: FileSaveAsCsvView) -> None:
        file_name = view.save_as.get_text()
        folder_path = view.save_to.get_subtitle()
        file_path = f'{folder_path}/{file_name}.csv'

        include_header = view.include_header.get_active()

        separator = view.separator.get_text()
        line_terminator = view.line_terminator.get_text()
        quote_char = view.quote_character.get_text()

        datetime_format = view.datetime_format.get_text()
        date_format = view.date_format.get_text()
        time_format = view.time_format.get_text()

        # Escape special characters
        separator = separator.encode().decode('unicode_escape')
        line_terminator = line_terminator.encode().decode('unicode_escape')
        quote_char = quote_char.encode().decode('unicode_escape')

        # Convert empty string to None
        if datetime_format == '':
            datetime_format = None
        if date_format == '':
            date_format = None
        if time_format == '':
            time_format = None

        parameters = {
            'include_header': include_header,
            'separator': separator,
            'line_terminator': line_terminator,
            'quote_char': quote_char,
            'datetime_format': datetime_format,
            'date_format': date_format,
            'time_format': time_format
        }

        self.write_file(file_path, **parameters)

    def save_as_json(self, view: FileSaveAsJsonView) -> None:
        file_name = view.save_as.get_text()
        folder_path = view.save_to.get_subtitle()
        file_path = f'{folder_path}/{file_name}.json'
        self.write_file(file_path)

    def save_as_parquet(self, view: FileSaveAsParquetView) -> None:
        file_name = view.save_as.get_text()
        folder_path = view.save_to.get_subtitle()
        file_path = f'{folder_path}/{file_name}.parquet'

        statistics = view.statistics.get_active()
        compression = view.compression.get_selected_item().get_string()
        compression_level = int(view.compression_level.get_value())

        parameters = {
            'statistics': statistics,
            'compression': compression,
            'compression_level': compression_level
        }

        self.write_file(file_path, **parameters)

    def check_file_exists(self, file_path: str) -> bool:
        if not Gio.File.new_for_path(file_path).query_exists(None):
            return False

        file_basename = os.path.basename(file_path)

        alert_dialog = Adw.AlertDialog()

        alert_dialog.set_heading(_('Replace File?'))
        alert_dialog.set_body(_('A file named "{}" already exists. '
                                'Do you want to replace it?').format(file_basename))

        alert_dialog.add_response('cancel', _('_Cancel'))
        alert_dialog.add_response('replace', _('_Replace'))

        alert_dialog.set_response_appearance('replace', Adw.ResponseAppearance.DESTRUCTIVE)
        alert_dialog.set_default_response('replace')
        alert_dialog.set_close_response('cancel')

        alert_dialog.choose(self.get_root(), None, self.on_alert_dialog_dismissed)

        return True

    def on_alert_dialog_dismissed(self,
                                  dialog: Adw.AlertDialog,
                                  result: Gio.Task) -> None:
        if result.had_error():
            return

        if dialog.choose_finish(result) != 'replace':
            return

        view = self.view_stack.get_visible_child()

        match view:
            case FileSaveAsErbookView():
                self.save_as_erbook(view)
            case FileSaveAsCsvView():
                self.save_as_csv(view)
            case FileSaveAsJsonView():
                self.save_as_json(view)
            case FileSaveAsParquetView():
                self.save_as_parquet(view)

    def write_file(self,
                   file_path: str,
                   **kwargs) -> None:
        self.callback(self.window, file_path, **kwargs)
        self.close()