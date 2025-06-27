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

    def next_column_label(self, label: str) -> str:
        """
        Returns the next column label in alphabetical order.

        The pattern starts with a single character ('A'), then increments the last character ('B', 'C', ...),
        wrapping around to 'A' when it reaches 'Z' and prepending a new character ('AA', 'AB', ...). In other
        words, following this pattern: A ^ B ^ C ... Z ^ AA ... AZ ^ BA ... ZZ ^ AAA ...

        Args:
            label: The current column label.

        Returns:
            The next column label in alphabetical order.
        """
        i = len(label) - 1
        while i >= 0 and label[i] == 'Z':
            i -= 1
        if i == -1:
            return 'A' * (len(label) + 1)
        return label[:i] + chr(ord(label[i]) + 1) + 'A' * (len(label) - i - 1)

    def draw_headers_backgrounds(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws the backgrounds of the row and column headers.

        This method draws the backgrounds of the row and column headers of the main canvas.
        It uses the accent color with reduced opacity to draw the backgrounds within the selected cell range.

        Args:
            area: The area that is being drawn.
            context: The Cairo context to draw with.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        context.save()

        if self._prefer_dark:
            context.set_source_rgb(0.15, 0.15, 0.15)
        else:
            context.set_source_rgb(0.9, 0.9, 0.9)

        # Draw column header background
        context.rectangle(0, 0, width, self._display.COLUMN_HEADER_HEIGHT)
        context.fill()

        # Draw row header background
        context.rectangle(0, self._display.COLUMN_HEADER_HEIGHT, self._display.ROW_HEADER_WIDTH, height)
        context.fill()

        # Get the selected cell range
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()

        # Set the accent color with reduced opacity for selected column header
        accent_rgba = list(self._color_accent)
        accent_rgba[3] = 0.25
        context.set_source_rgba(*accent_rgba)

        # Draw column headers background within the selected cell range
        context.save()
        context.rectangle(self._display.ROW_HEADER_WIDTH, 0, width, self._display.COLUMN_HEADER_HEIGHT)
        context.clip()
        col_min, col_max = min(start_col, end_col), max(start_col, end_col)
        num_cols = col_max - col_min + 1
        x_start = self._display.ROW_HEADER_WIDTH + col_min * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        context.rectangle(x_start, 0, num_cols * self._display.CELL_DEFAULT_WIDTH, self._display.COLUMN_HEADER_HEIGHT)
        context.fill()
        context.restore()

        # Draw row headers background within the selected cell range
        context.save()
        context.rectangle(0, self._display.COLUMN_HEADER_HEIGHT, self._display.ROW_HEADER_WIDTH, height)
        context.clip()
        row_min, row_max = min(start_row, end_row), max(start_row, end_row)
        num_rows = row_max - row_min + 1
        y_start = self._display.COLUMN_HEADER_HEIGHT + row_min * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        context.rectangle(0, y_start, self._display.ROW_HEADER_WIDTH, num_rows * self._display.CELL_DEFAULT_HEIGHT)
        context.fill()
        context.restore()

        context.restore()

    def draw_selection_background(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws the background for the selected cell range and the active cell.

        This method highlights the selected cell range in the drawing area with a translucent
        accent color, and the active cell with a different color to differentiate it from the
        rest of the selected cells. The drawing takes into account the current scroll position
        and display settings.

        Args:
            area: The Gtk.DrawingArea where the selection background is drawn.
            context: The Cairo context used for drawing operations.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        context.save()

        context.rectangle(self._display.ROW_HEADER_WIDTH, self._display.COLUMN_HEADER_HEIGHT, width, height)
        context.clip()

        # Set the accent color with reduced opacity for selected column header
        accent_rgba = list(self._color_accent)
        accent_rgba[3] = 0.25
        context.set_source_rgba(*accent_rgba)

        # Calculate the position and size of the selection rectangle
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()
        x_start = self._display.ROW_HEADER_WIDTH + min(start_col, end_col) * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        y_start = self._display.COLUMN_HEADER_HEIGHT + min(start_row, end_row) * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        width_sel = (abs(end_col - start_col) + 1) * self._display.CELL_DEFAULT_WIDTH
        height_sel = (abs(end_row - start_row) + 1) * self._display.CELL_DEFAULT_HEIGHT

        # Draw selection box around the selected cell range
        context.rectangle(x_start, y_start, width_sel, height_sel)
        context.fill()

        if self._prefer_dark:
            context.set_source_rgb(0.1, 0.1, 0.1)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

        # Calculate the position and size of the active cell
        active_row, active_col = self._selection.get_active_cell()
        x = self._display.ROW_HEADER_WIDTH + active_col * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        y = self._display.COLUMN_HEADER_HEIGHT + active_row * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT

        # Draw active cell background with a different color
        context.rectangle(x, y, cell_width, cell_height)
        context.fill()

        context.restore()

    def draw_cells_lines(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws the lines separating the cells in the main canvas.

        This method draws the lines separating the cells in the main canvas using a light gray
        color. The lines are drawn on top of the headers and the selection background.

        Args:
            area: The Gtk.DrawingArea where the cells are drawn.
            context: The Cairo context used for drawing operations.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        context.save()

        if self._prefer_dark:
            context.set_source_rgb(0.25, 0.25, 0.25)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)

        x_start = self._display.ROW_HEADER_WIDTH
        y_start = self._display.COLUMN_HEADER_HEIGHT
        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT

        # Draw separator line between column header and the worksheet cells
        context.move_to(0, y_start)
        context.line_to(width, y_start)
        context.move_to(x_start, 0)
        context.line_to(x_start, height)
        context.stroke()

        # Draw vertical and horizontal lines
        context.set_hairline(True)
        for y in range(y_start, height, cell_height):
            context.move_to(0, y)
            context.line_to(width, y)
        for x in range(x_start, width, cell_width):
            context.move_to(x, 0)
            context.line_to(x, height)
        context.stroke()

        # Draw separator line between the worksheet column header and the data frame column header
        if not self._dbms.data_frame.is_empty():
            context.move_to(x_start, cell_height)
            context.line_to(width, cell_height)
            context.stroke()

        context.restore()

    def draw_selection_border(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws a border around the currently selected cell range in the main canvas.

        This method draws a border around the currently selected cell range in the main canvas.
        The border is drawn using the accent color. The position and size of the border are
        calculated based on the selected cell range and the scroll position of the main canvas.
        The method also draws a decoration on the column and row headers of the selected cell range.

        Args:
            area: The Gtk.DrawingArea where the cells are drawn.
            context: The Cairo context used for drawing operations.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        context.save()

        context.rectangle(self._display.ROW_HEADER_WIDTH - 1, self._display.COLUMN_HEADER_HEIGHT - 1, width, height)
        context.clip()

        context.set_source_rgba(*self._color_accent)

        # Calculate the position and size of the selection rectangle
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()
        x_start = self._display.ROW_HEADER_WIDTH + min(start_col, end_col) * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        y_start = self._display.COLUMN_HEADER_HEIGHT + min(start_row, end_row) * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        width_sel = (abs(end_col - start_col) + 1) * self._display.CELL_DEFAULT_WIDTH
        height_sel = (abs(end_row - start_row) + 1) * self._display.CELL_DEFAULT_HEIGHT

        # Draw selection box around the selected cell range
        context.rectangle(x_start, y_start, width_sel, height_sel)
        context.stroke()

        # Draw column header decoration
        context.move_to(x_start, self._display.COLUMN_HEADER_HEIGHT)
        context.rel_line_to(width_sel, 0)
        context.stroke()

        # Draw row header decoration
        context.move_to(self._display.ROW_HEADER_WIDTH, y_start)
        context.rel_line_to(0, height_sel)
        context.stroke()

        context.restore()

    def draw_headers_texts(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws the text labels for the column and row headers in the main canvas.

        This method draws the text labels for the column and row headers in the main canvas.
        The text labels are drawn using a bold font with a size of 12 points. The method also
        handles the drawing of the text labels for the selected cell range using the current system
        accent color. The method also draws the column and row headers texts centered and right-aligned
        respectively.

        Args:
            area: The Gtk.DrawingArea where the cells are drawn.
            context: The Cairo context used for drawing operations.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        context.save()

        # Use monospace font family for drawing text
        context.select_font_face('Monospace', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(12)

        # Get the selected cell range
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()
        col_min = min(start_col, end_col) - self._display.scroll_horizontal_position // self._display.CELL_DEFAULT_WIDTH
        col_max = max(start_col, end_col) - self._display.scroll_horizontal_position // self._display.CELL_DEFAULT_WIDTH
        row_min = min(start_row, end_row) - self._display.scroll_vertical_position // self._display.CELL_DEFAULT_HEIGHT
        row_max = max(start_row, end_row) - self._display.scroll_vertical_position // self._display.CELL_DEFAULT_HEIGHT

        x_start = self._display.ROW_HEADER_WIDTH
        y_start = 0
        cell_width = self._display.CELL_DEFAULT_WIDTH

        # Determine the starting column label based on the scroll position
        # TODO: I think this algorithm is not very efficient for large tables with thousands of columns,
        #       but it just works for now, so I'll leave it for now
        initial_col = self._display.scroll_horizontal_position // self._display.CELL_DEFAULT_WIDTH + 1
        cell_text = ''
        while initial_col > 0:
            cell_text = self.next_column_label(cell_text) if cell_text else 'A'
            initial_col -= 1

        text_color = (0.0, 0.0, 0.0)
        if self._prefer_dark:
            text_color = (1.0, 1.0, 1.0)
        *accent_color, _ = self._color_accent

        # Draw column headers texts (centered)
        for col, x in enumerate(range(x_start, width, cell_width)):
            xbearing, ybearing, text_width, text_height, xadvance, yadvance = context.text_extents(cell_text)
            x = x + (cell_width - text_width) / 2 - xbearing

            # If the current column header is within the selected cell range, use the current system accent color
            if col_min <= col <= col_max:
                context.set_source_rgb(*accent_color)
            else:
                context.set_source_rgb(*text_color)

            context.move_to(x, 14 + y_start)
            context.show_text(cell_text)
            cell_text = self.next_column_label(cell_text)

        x_start = 0
        y_start = self._display.COLUMN_HEADER_HEIGHT
        cell_width = self._display.ROW_HEADER_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT

        # Adjust the starting row label based on the scroll position
        cell_text = self._display.scroll_vertical_position // self._display.CELL_DEFAULT_HEIGHT + 1

        # Draw row headers texts (right-aligned)
        for row, y in enumerate(range(y_start, height, cell_height)):
            xbearing, ybearing, text_width, text_height, xadvance, yadvance = context.text_extents(str(cell_text))
            x = x_start + cell_width - text_width - xbearing - 6

            # If the current row header is within the selected cell range, use the current system accent color
            if row_min <= row <= row_max:
                context.set_source_rgb(*accent_color)
            else:
                context.set_source_rgb(*text_color)

            context.move_to(x, 14 + y)
            context.show_text(str(cell_text))
            cell_text += 1

        # Use system default font family for drawing text
        font_desc = Gtk.Widget.create_pango_context(area).get_font_description()
        font_family = font_desc.get_family() if font_desc else 'Sans'
        context.select_font_face(font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(12)

        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        horizontal_offset = self._display.scroll_horizontal_position
        df_shape = self._dbms.data_frame.shape

        # Draw data frame header texts (centered)
        x = self._display.ROW_HEADER_WIDTH
        while x < width:
            col = (x - self._display.ROW_HEADER_WIDTH) // cell_width + horizontal_offset // cell_width
            if df_shape[1] <= col:
                width = x # prevent iteration over empty cells
                break

            # If the current column header is within the selected cell range, use the current system accent color
            if col_min <= (col - horizontal_offset // cell_width) <= col_max:
                context.set_source_rgb(*accent_color)
            else:
                context.set_source_rgb(*text_color)

            context.save()
            context.rectangle(x, cell_height, cell_width, cell_height * 2)
            context.clip()

            # Align text to the center, or back to the left if the column name is too long
            xbearing, ybearing, text_width, text_height, xadvance, yadvance = context.text_extents(str(self._dbms.data_frame.columns[col]))
            if (text_width + 6 * 2) > cell_width:
                context.move_to(6 + x, 14 + self._display.CELL_DEFAULT_HEIGHT + 2)
            else:
                context.move_to(x + (cell_width - text_width) / 2 - xbearing, 14 + self._display.CELL_DEFAULT_HEIGHT + 2)
            context.show_text(str(self._dbms.data_frame.columns[col]))

            # Always align text to the center for the column data type
            context.select_font_face(font_family, cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_NORMAL)
            context.set_font_size(11)
            xbearing, ybearing, text_width, text_height, xadvance, yadvance = context.text_extents(str(self._dbms.data_frame.dtypes[col]))
            context.move_to(x + (cell_width - text_width) / 2 - xbearing, 14 + self._display.CELL_DEFAULT_HEIGHT * 2 - 2)
            context.show_text(str(self._dbms.data_frame.dtypes[col]))

            context.restore()
            x += cell_width

        context.restore()

    def draw_cells_texts(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws the text contents of the cells within the visible area of the main canvas.

        This method iterates over the cells within the current view, extracts their data from the
        data frame, and renders the text within the specified drawing area. It adjusts the text color
        based on the display mode (dark or light) and uses the system's default font settings. The
        drawing takes into account the current scroll position to determine which cells are visible.

        Args:
            area: The Gtk.DrawingArea where the cell texts are drawn.
            context: The Cairo context used for drawing operations.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
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
        vertical_offset = self._display.scroll_vertical_position
        horizontal_offset = self._display.scroll_horizontal_position
        df_shape = self._dbms.data_frame.shape

        x = self._display.ROW_HEADER_WIDTH
        while x < width:
            y = self._display.COLUMN_HEADER_HEIGHT
            while y < height:
                row = (y - self._display.COLUMN_HEADER_HEIGHT) // cell_height + vertical_offset // cell_height
                col = (x - self._display.ROW_HEADER_WIDTH) // cell_width + horizontal_offset // cell_width
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

    def setup_cairo_context(self, area: Gtk.DrawingArea, context: cairo.Context, height: int, width: int) -> None:
        """
        Sets up global Cairo context settings for drawing operations.

        Args:
            area: The Gtk.DrawingArea where the drawing operations are performed.
            context: The Cairo context used for drawing operations.
            height: The height of the drawing area.
            width: The width of the drawing area.
        """
        self._prefer_dark = Adw.StyleManager().get_dark()
        self._color_accent = Adw.StyleManager().get_accent_color_rgba()
        font_options = cairo.FontOptions()
        font_options.set_antialias(cairo.Antialias.FAST)
        context.set_font_options(font_options)
        context.set_antialias(cairo.Antialias.NONE)

    def adjust_row_header_width(self, area: Gtk.DrawingArea, context: cairo.Context, height: int, width: int) -> None:
        """
        Adjusts the width of the row header to fit the maximum row number.

        Args:
            area: The Gtk.DrawingArea where the row header is drawn.
            context: The Cairo context used for drawing operations.
            height: The height of the drawing area.
            width: The width of the drawing area.
        """
        context.save()
        context.select_font_face('Monospace', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(12)
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        y_start = self._display.COLUMN_HEADER_HEIGHT
        max_row_number = (self._display.scroll_vertical_position // cell_height) + 1 + ((height - y_start) // cell_height)
        text_metrics = context.text_extents(str(max_row_number))
        self._display.ROW_HEADER_WIDTH = max(40, int(text_metrics[2] + 2 * 6 + 0.5))
        context.restore()

    def draw(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws the main canvas by calling all the necessary draw methods.

        The draw process starts by setting the style manager properties for the dark theme
        and accent color. It then sets the font options to FAST antialiasing and disables
        antialiasing for the context.

        Args:
            area: The Gtk.DrawingArea where the drawing is done.
            context: The Cairo context used for drawing.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        self.setup_cairo_context(area, context, width, height)
        self.adjust_row_header_width(area, context, width, height)
        self.draw_headers_backgrounds(area, context, width, height)
        self.draw_selection_background(area, context, width, height)
        self.draw_cells_lines(area, context, width, height)
        self.draw_headers_texts(area, context, width, height)
        self.draw_cells_texts(area, context, width, height)
        self.draw_selection_border(area, context, width, height)