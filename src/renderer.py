# renderer.py
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

import cairo

from gi.repository import Adw, GObject, Gtk

from .dbms import DBMS
from .display import Display
from .selection import Selection

class Renderer(GObject.Object):
    __gtype_name__ = 'Renderer'

    _dbms: DBMS
    _display: Display
    _selection: Selection

    def __init__(self, display: Display, selection: Selection, dbms: DBMS) -> None:
        """
        Initializes the Renderer class.

        This class is responsible for rendering the main canvas of the Eruo Data Studio.
        It uses Cairo for drawing operations and GTK for handling the drawing area.

        Args:
            display: An instance of the Display class that provides display settings and dimensions.
            selection: An instance of the Selection class that manages cell selection and active cell.
        """
        super().__init__()

        self._dbms = dbms
        self._display = display
        self._selection = selection

    def draw_headers_backgrounds(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        context.save()

        if self._prefer_dark:
            context.set_source_rgb(0.15, 0.15, 0.15)
        else:
            context.set_source_rgb(0.9, 0.9, 0.9)

        # Draw column header background
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        context.rectangle(0, 0, width, cell_height)
        context.fill()

        # Draw row header background
        cell_width = self._display.ROW_HEADER_WIDTH
        context.rectangle(0, cell_height, cell_width, height)
        context.fill()

        # Get the selected cell range
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()

        # Set the accent color with reduced opacity for selected column header
        accent_rgba = list(self._color_accent)
        accent_rgba[3] = 0.25
        context.set_source_rgba(*accent_rgba)

        # TODO: limit the rectangle to the size of the drawing area
        # Draw column headers background within the selected cell range
        col_min, col_max = min(start_col, end_col), max(start_col, end_col)
        num_cols = col_max - col_min + 1
        context.rectangle(
            self._display.ROW_HEADER_WIDTH + col_min * self._display.CELL_DEFAULT_WIDTH,
            0,
            num_cols * self._display.CELL_DEFAULT_WIDTH,
            cell_height,
        )
        context.fill()

        # TODO: limit the rectangle to the size of the drawing area
        # Draw row headers background within the selected cell range
        row_min, row_max = min(start_row, end_row), max(start_row, end_row)
        num_rows = row_max - row_min + 1
        context.rectangle(
            0,
            self._display.CELL_DEFAULT_HEIGHT + row_min * self._display.CELL_DEFAULT_HEIGHT,
            self._display.ROW_HEADER_WIDTH,
            num_rows * self._display.CELL_DEFAULT_HEIGHT,
        )
        context.fill()

        context.restore()

    def draw_selection_background(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        context.save()

        # Set the accent color with reduced opacity for selected column header
        accent_rgba = list(self._color_accent)
        accent_rgba[3] = 0.25
        context.set_source_rgba(*accent_rgba)

        # Calculate the position and size of the selection rectangle
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()
        x_start = self._display.ROW_HEADER_WIDTH + min(start_col, end_col) * self._display.CELL_DEFAULT_WIDTH
        y_start = self._display.CELL_DEFAULT_HEIGHT + min(start_row, end_row) * self._display.CELL_DEFAULT_HEIGHT
        width_sel = (abs(end_col - start_col) + 1) * self._display.CELL_DEFAULT_WIDTH
        height_sel = (abs(end_row - start_row) + 1) * self._display.CELL_DEFAULT_HEIGHT

        # TODO: limit the rectangle to the size of the drawing area
        # Draw selection box around the selected cell range
        context.rectangle(x_start, y_start, width_sel, height_sel)
        context.fill()

        if self._prefer_dark:
            context.set_source_rgb(0.1, 0.1, 0.1)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

        # Calculate the position and size of the active cell
        active_row, active_col = self._selection.get_active_cell()
        x = self._display.ROW_HEADER_WIDTH + active_col * self._display.CELL_DEFAULT_WIDTH
        y = self._display.CELL_DEFAULT_HEIGHT + active_row * self._display.CELL_DEFAULT_HEIGHT
        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT

        # TODO: limit the rectangle to the size of the drawing area
        # Draw active cell background with a different color
        context.rectangle(x, y, cell_width, cell_height)
        context.fill()

        context.restore()

    def draw_headers_lines(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        context.save()

        if self._prefer_dark:
            context.set_source_rgb(0.25, 0.25, 0.25)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)
        context.set_hairline(True)

        x_start = 0
        y_start = 0
        cell_width = self._display.ROW_HEADER_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT

        # Draw column header lines
        context.move_to(x_start, cell_height)
        context.rel_line_to(width, 0)
        context.stroke()

        # Draw row header lines
        context.move_to(cell_width, y_start)
        context.rel_line_to(0, height)
        context.stroke()

        context.restore()

    def draw_cells_lines(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        context.save()

        if self._prefer_dark:
            context.set_source_rgb(0.25, 0.25, 0.25)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)
        context.set_hairline(True)

        x_start = self._display.ROW_HEADER_WIDTH
        y_start = self._display.CELL_DEFAULT_HEIGHT
        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT

        for y in range(y_start, height, cell_height):
            context.move_to(0, y)
            context.line_to(width, y)
        for x in range(x_start, width, cell_width):
            context.move_to(x, 0)
            context.line_to(x, height)
        context.stroke()

        context.restore()

    def draw_selection_border(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        context.save()

        context.set_source_rgba(*self._color_accent)

        # Calculate the position and size of the selection rectangle
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()
        x_start = self._display.ROW_HEADER_WIDTH + min(start_col, end_col) * self._display.CELL_DEFAULT_WIDTH
        y_start = self._display.CELL_DEFAULT_HEIGHT + min(start_row, end_row) * self._display.CELL_DEFAULT_HEIGHT
        width_sel = (abs(end_col - start_col) + 1) * self._display.CELL_DEFAULT_WIDTH
        height_sel = (abs(end_row - start_row) + 1) * self._display.CELL_DEFAULT_HEIGHT

        # TODO: limit the rectangle to the size of the drawing area,
        #       don't forget to take the stroke width into account
        # Draw selection box around the selected cell range
        context.rectangle(x_start, y_start, width_sel, height_sel)
        context.stroke()

        cell_width = self._display.ROW_HEADER_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT

        # Draw column header lines
        context.move_to(x_start, cell_height)
        context.rel_line_to(width_sel, 0)
        context.stroke()

        # Draw row header lines
        context.move_to(cell_width, y_start)
        context.rel_line_to(0, height_sel)
        context.stroke()

        context.restore()

    def draw_headers_texts(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        context.save()

        # Use system default font family for drawing text (monospace)
        context.select_font_face('Monospace', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(12)

        # Get the selected cell range
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()
        col_min, col_max = min(start_col, end_col), max(start_col, end_col)
        row_min, row_max = min(start_row, end_row), max(start_row, end_row)

        x_start = self._display.ROW_HEADER_WIDTH
        y_start = 0
        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        cell_text = 'A'

        text_color = (0.0, 0.0, 0.0)
        if self._prefer_dark:
            text_color = (1.0, 1.0, 1.0)
        *accent_color, _ = self._color_accent

        # Draw column headers texts (centered)
        for col, x in enumerate(range(x_start, width, cell_width)):
            xbearing, ybearing, text_width, text_height, xadvance, yadvance = context.text_extents(cell_text)
            x = x + (cell_width - text_width) / 2 - xbearing

            # If the current column header is within the selected cell range,
            # use the current system accent color
            if col_min <= col <= col_max:
                context.set_source_rgb(*accent_color)
            else:
                context.set_source_rgb(*text_color)

            context.move_to(x, 14 + y_start)
            context.show_text(cell_text)

            # Increment column label according to this pattern:
            # A ^ B ^ C ... Z ^ AA ... AZ ^ BA ... ZZ ^ AAA ...
            def next_col_label(label):
                i = len(label) - 1
                while i >= 0 and label[i] == 'Z':
                    i -= 1
                if i == -1:
                    return 'A' * (len(label) + 1)
                return label[:i] + chr(ord(label[i]) + 1) + 'A' * (len(label) - i - 1)
            cell_text = next_col_label(cell_text)

        x_start = 0
        y_start = self._display.CELL_DEFAULT_HEIGHT
        cell_width = self._display.ROW_HEADER_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        cell_text = '1'

        # Draw row headers texts (right-aligned)
        for row, y in enumerate(range(y_start, height, cell_height)):
            xbearing, ybearing, text_width, text_height, xadvance, yadvance = context.text_extents(cell_text)
            x = x_start + cell_width - text_width - xbearing - 6

            # If the current row header is within the selected cell range,
            # use the current system accent color
            if row_min <= row <= row_max:
                context.set_source_rgb(*accent_color)
            else:
                context.set_source_rgb(*text_color)

            context.move_to(x, 14 + y)
            context.show_text(cell_text)
            cell_text = str(int(cell_text) + 1)

        context.restore()

    def draw_cells_texts(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        if self._dbms.data_frame.is_empty():
            return

        context.save()

        if self._prefer_dark:
            context.set_source_rgb(1.0, 1.0, 1.0)
        else:
            context.set_source_rgb(0.0, 0.0, 0.0)

        # Use system default font family for drawing text
        font_desc = Gtk.Widget.create_pango_context(area).get_font_description()
        font_family = font_desc.get_family() if font_desc else 'Sans'
        context.select_font_face(font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(12)

        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        df_shape = self._dbms.data_frame.shape

        x = self._display.ROW_HEADER_WIDTH
        while x < width:
            y = self._display.CELL_DEFAULT_HEIGHT
            while y < height:
                row = (y - self._display.CELL_DEFAULT_HEIGHT) // cell_height
                col = (x - self._display.ROW_HEADER_WIDTH) // cell_width
                if df_shape[0] <= row:
                    height = y # prevent iteration over empty cells
                    break
                if df_shape[1] <= col:
                    width = x # prevent iteration over empty cells
                    break
                context.save()
                context.rectangle(x, y, cell_width, cell_height)
                context.clip()
                context.move_to(6 + x, 14 + y)
                text = str(self._dbms.data_frame[row, col])
                context.show_text(text)
                context.restore()
                y += cell_height
            x += cell_width

        context.restore()

    def draw(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        self._prefer_dark = Adw.StyleManager().get_dark()
        self._color_accent = Adw.StyleManager().get_accent_color_rgba()
        font_options = cairo.FontOptions()
        font_options.set_antialias(cairo.Antialias.FAST)
        context.set_font_options(font_options)
        context.set_antialias(cairo.Antialias.NONE)

        self.draw_headers_backgrounds(area, context, width, height)
        self.draw_selection_background(area, context, width, height)
        self.draw_headers_lines(area, context, width, height)
        self.draw_cells_lines(area, context, width, height)
        self.draw_headers_texts(area, context, width, height)
        self.draw_cells_texts(area, context, width, height)
        self.draw_selection_border(area, context, width, height)