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
import time

from gi.repository import Adw, GObject, Gtk, Pango, PangoCairo

from .utils import Log, print_log
from .dbms import DBMS
from .display import Display
from .selection import Selection

class Renderer(GObject.Object):
    __gtype_name__ = 'Renderer'

    FONT_SIZE: float = 9

    _dbms: DBMS
    _display: Display
    _selection: Selection

    _prefer_dark = Adw.StyleManager().get_dark()
    _color_accent = Adw.StyleManager().get_accent_color_rgba()
    _cell_contents_snapshot = None

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

    def invalidate_cache(self) -> None:
        print_log('Invalidating main canvas drawing cache...', Log.DEBUG)
        self._cell_contents_snapshot = None

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
        print_log(f'Re-drawing main canvas content...', Log.DEBUG)
        start_time = time.perf_counter()

        self.setup_cairo_context(area, context, width, height)
        self.adjust_row_header_width(area, context, width, height)
        self.draw_headers_backgrounds(area, context, width, height)
        self.draw_selection_backgrounds(area, context, width, height)
        self.draw_headers_contents(area, context, width, height)

        # Draw the cell contents
        if self._cell_contents_snapshot is None:
            self._cell_contents_snapshot = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            context_snapshot = cairo.Context(self._cell_contents_snapshot)
            self.draw_cells_contents(area, context_snapshot, width, height)
        context.set_source_surface(self._cell_contents_snapshot, 0, 0)
        context.paint()

        self.draw_cells_borders(area, context, width, height)
        self.draw_selection_borders(area, context, width, height)

        end_time = time.perf_counter()
        print_log(f'Time to finish drawing: {end_time - start_time:.6f} sec', Log.DEBUG)

    def setup_cairo_context(self, area: Gtk.DrawingArea, context: cairo.Context, height: int, width: int) -> None:
        """
        Sets up global Cairo context settings for drawing operations.

        Args:
            area: The Gtk.DrawingArea where the drawing operations are performed.
            context: The Cairo context used for drawing operations.
            height: The height of the drawing area.
            width: The width of the drawing area.
        """
        if (prefer_dark := Adw.StyleManager().get_dark()) != self._prefer_dark:
            self._prefer_dark = prefer_dark
            self.invalidate_cache()
        self._color_accent = Adw.StyleManager().get_accent_color_rgba()
        font_options = cairo.FontOptions()
        font_options.set_antialias(cairo.Antialias.GOOD)
        context.set_font_options(font_options)
        context.set_antialias(cairo.Antialias.NONE)

    def adjust_row_header_width(self, area: Gtk.DrawingArea, context: cairo.Context, height: int, width: int) -> None:
        """
        Adjusts the width of the row header to fit the maximum row number.

        Args:
            area: The Gtk.DrawingArea where the drawing operations are performed.
            context: The Cairo context used for drawing operations.
            height: The height of the drawing area.
            width: The width of the drawing area.
        """
        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0))
        font_desc = Pango.font_description_from_string(f'Monospace Normal Bold {self.FONT_SIZE}')
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        y_start = self._display.COLUMN_HEADER_HEIGHT
        max_row_number = (self._display.scroll_vertical_position // cell_height) + 1 + ((height - y_start) // cell_height)
        layout = PangoCairo.create_layout(context)
        layout.set_text(str(max_row_number), -1)
        layout.set_font_description(font_desc)
        text_width = layout.get_size()[0] / Pango.SCALE
        self._display.ROW_HEADER_WIDTH = max(40, int(text_width + 2 * self._display.CELL_DEFAULT_PADDING + 0.5))

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

        # Set the background color
        if self._prefer_dark:
            context.set_source_rgb(0.15, 0.15, 0.15)
        else:
            context.set_source_rgb(0.9, 0.9, 0.9)

        # Draw header backgrounds
        context.rectangle(0, 0, width, self._display.COLUMN_HEADER_HEIGHT)
        context.rectangle(0, self._display.COLUMN_HEADER_HEIGHT, self._display.ROW_HEADER_WIDTH, height)
        context.fill()

        # Set the accent color with reduced opacity for selected column header
        accent_rgba = list(self._color_accent)
        accent_rgba[3] = 0.25
        context.set_source_rgba(*accent_rgba)

        # Get the selected cell range
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()
        x_start = self._display.ROW_HEADER_WIDTH + start_col * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        y_start = self._display.COLUMN_HEADER_HEIGHT + start_row * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        width_sel = (end_col - start_col + 1) * self._display.CELL_DEFAULT_WIDTH
        height_sel = (end_row - start_row + 1) * self._display.CELL_DEFAULT_HEIGHT

        if not self._display.cumulative_column_widths.is_empty():
            x_start = self._display.get_column_position(start_col) + self._display.ROW_HEADER_WIDTH - self._display.scroll_horizontal_position
            if start_col == end_col:
                width_sel = self._display.get_column_width(start_col)
            else:
                width_sel = self._display.get_column_position(end_col + 1) - self._display.get_column_position(start_col)

        # Draw column headers background within the selected cell range
        context.rectangle(self._display.ROW_HEADER_WIDTH, 0, width, self._display.COLUMN_HEADER_HEIGHT)
        context.clip()
        context.rectangle(x_start, 0, width_sel, self._display.COLUMN_HEADER_HEIGHT)
        context.fill()

        # Draw row headers background within the selected cell range
        context.reset_clip()
        context.rectangle(0, self._display.COLUMN_HEADER_HEIGHT, self._display.ROW_HEADER_WIDTH, height)
        context.clip()
        context.rectangle(0, y_start, self._display.ROW_HEADER_WIDTH, height_sel)
        context.fill()

        context.restore()

    def draw_selection_backgrounds(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
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
        x_start = self._display.ROW_HEADER_WIDTH + start_col * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        y_start = self._display.COLUMN_HEADER_HEIGHT + start_row * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        width_sel = ((end_col - start_col) + 1) * self._display.CELL_DEFAULT_WIDTH
        height_sel = ((end_row - start_row) + 1) * self._display.CELL_DEFAULT_HEIGHT

        if not self._display.cumulative_column_widths.is_empty():
            x_start = self._display.get_column_position(start_col) + self._display.ROW_HEADER_WIDTH - self._display.scroll_horizontal_position
            if start_col == end_col:
                width_sel = self._display.get_column_width(start_col)
            else:
                width_sel = self._display.get_column_position(end_col + 1) - self._display.get_column_position(start_col)

        # Draw selection box around the selected cell range
        context.rectangle(x_start, y_start, width_sel, height_sel)
        context.fill()

        if self._prefer_dark:
            context.set_source_rgb(0.1, 0.1, 0.1)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

        # Calculate the position and size of the active cell
        row, col = self._selection.get_active_cell()
        x = self._display.ROW_HEADER_WIDTH + col * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        y = self._display.COLUMN_HEADER_HEIGHT + row * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        width_sel = self._display.CELL_DEFAULT_WIDTH
        height_sel = self._display.CELL_DEFAULT_HEIGHT

        if not self._display.cumulative_column_widths.is_empty():
            x = self._display.get_column_position(col) + self._display.ROW_HEADER_WIDTH - self._display.scroll_horizontal_position
            width_sel = self._display.get_column_width(col)

        # Draw active cell background with a different color
        context.rectangle(x, y, width_sel, height_sel)
        context.fill()

        context.restore()

    def draw_headers_contents(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        """
        Draws the header content for the column and row headers in the main canvas.

        This method draws the column and row headers in the main canvas, including the column headers
        and row headers. The drawing takes into account the current scroll position and display settings.

        Args:
            area: The Gtk.DrawingArea where the cells are drawn.
            context: The Cairo context used for drawing operations.
            width: The width of the drawing area.
            height: The height of the drawing area.
        """
        def next_column_label(label: str) -> str:
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

        context.save()

        # Get system default font family for drawing text
        font_desc = Gtk.Widget.create_pango_context(area).get_font_description()
        system_font = font_desc.get_family() if font_desc else 'Sans'
        index_font_desc = Pango.font_description_from_string(f'Monospace Normal Bold {self.FONT_SIZE}')
        name_font_desc = Pango.font_description_from_string(f'{system_font} Normal Bold {self.FONT_SIZE}')
        type_font_desc = Pango.font_description_from_string(f'{system_font} Normal Regular {self.FONT_SIZE - 1}')

        text_color = (0.0, 0.0, 0.0)
        if self._prefer_dark:
            text_color = (1.0, 1.0, 1.0)
        *accent_color, _ = self._color_accent

        # Get the selected cell range
        (start_row, start_col), (end_row, end_col) = self._selection.get_selected_cells()

        # Determine the starting column label based on the scroll position
        col_index = self._display.coordinate_to_column(self._display.scroll_horizontal_position)
        text_index = col_index
        cell_text = ''
        while text_index >= 0:
            cell_text = chr(65 + text_index % 26) + cell_text
            text_index = text_index // 26 - 1

        # Calculate the starting column width and offset
        x_offset = 0
        cell_width = self._display.CELL_DEFAULT_WIDTH
        if not self._display.cumulative_column_widths.is_empty():
            if 0 <= col_index - 1 < self._display.cumulative_column_widths.shape[0]:
                x_offset = self._display.cumulative_column_widths[col_index - 1]
            x_offset -= self._display.scroll_horizontal_position
            if col_index < self._display.column_widths.shape[0]:
                cell_width = self._display.column_widths[col_index] + x_offset
            else:
                scroll_position = self._display.scroll_horizontal_position - self._display.cumulative_column_widths[-1]
                x_offset = scroll_position % self._display.CELL_DEFAULT_WIDTH
                cell_width = self._display.CELL_DEFAULT_WIDTH - x_offset

        # Draw column headers texts
        x = self._display.ROW_HEADER_WIDTH
        layout = PangoCairo.create_layout(context)
        while x < width:
            # Use the current system accent color, if the current column header is within the selected cell range
            if start_col <= col_index <= end_col:
                context.set_source_rgb(*accent_color)
            else:
                context.set_source_rgb(*text_color)

            context.save()
            context.rectangle(x, 0, cell_width, self._display.COLUMN_HEADER_HEIGHT)
            context.clip()

            layout.set_text(cell_text, -1)
            layout.set_font_description(index_font_desc)

            cell_actual_width = self._display.CELL_DEFAULT_WIDTH
            if col_index < self._display.column_widths.shape[0]:
                cell_actual_width = self._display.column_widths[col_index]

            x_offset = 0
            if x == self._display.ROW_HEADER_WIDTH:
                x_offset = cell_actual_width - cell_width

            # Draw the column index
            text_width = layout.get_size()[0] / Pango.SCALE
            x_text = x + (cell_actual_width - text_width) / 2 - x_offset
            context.move_to(x_text, 2)
            PangoCairo.show_layout(context, layout)
            cell_text = next_column_label(cell_text)

            # Draw the column name
            if col_index < self._dbms.get_shape()[1]:
                cell_text_2 = str(self._dbms.get_columns()[col_index])
                layout.set_text(cell_text_2, -1)
                layout.set_font_description(name_font_desc)
                x_text = x + self._display.CELL_DEFAULT_PADDING - x_offset
                context.move_to(x_text, 2 + self._display.CELL_DEFAULT_HEIGHT + 2)
                PangoCairo.show_layout(context, layout)

            # Draw the column type
            if col_index < self._dbms.get_shape()[1]:
                cell_text_2 = str(self._dbms.get_dtypes()[col_index])
                if cell_text_2.startswith('Categorical'):
                    cell_text_2 = 'Categor.'
                layout.set_text(cell_text_2, -1)
                layout.set_font_description(type_font_desc)
                x_text = x + self._display.CELL_DEFAULT_PADDING - x_offset
                context.move_to(x_text, self._display.CELL_DEFAULT_HEIGHT * 2)
                PangoCairo.show_layout(context, layout)

            # Draw the filter icon
            if col_index < self._dbms.get_shape()[1]:
                context.set_hairline(True)
                x_text = x + cell_actual_width - self._display.ICON_DEFAULT_SIZE - self._display.CELL_DEFAULT_PADDING - x_offset
                y_text = self._display.CELL_DEFAULT_HEIGHT * 2 + self._display.ICON_DEFAULT_SIZE / 2
                context.move_to(x_text, y_text + 2)
                context.line_to(x_text + self._display.ICON_DEFAULT_SIZE / 2, y_text + self._display.ICON_DEFAULT_SIZE - 2)
                context.line_to(x_text + self._display.ICON_DEFAULT_SIZE, y_text + 2)
                context.stroke()

            context.restore()

            x += cell_width
            col_index += 1
            if col_index < self._display.column_widths.shape[0]:
                cell_width = self._display.column_widths[col_index]
            else:
                cell_width = self._display.CELL_DEFAULT_WIDTH

        # Determine the starting row label based on the scroll position
        cell_text = self._display.scroll_vertical_position // self._display.CELL_DEFAULT_HEIGHT + 1

        # Draw row headers texts (right-aligned)
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(index_font_desc)
        for y in range(self._display.COLUMN_HEADER_HEIGHT, height, self._display.CELL_DEFAULT_HEIGHT):
            # Align the text to the right of the cell
            layout.set_text(str(cell_text), -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            x = self._display.ROW_HEADER_WIDTH - text_width - self._display.CELL_DEFAULT_PADDING

            # Use the current system accent color, if the current row header is within the selected cell range
            if start_row <= cell_text - 1 <= end_row:
                context.set_source_rgb(*accent_color)
            else:
                context.set_source_rgb(*text_color)

            context.move_to(x, 2 + y)
            PangoCairo.show_layout(context, layout)
            cell_text += 1

        context.restore()

    def draw_cells_contents(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
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
        if self._display.cumulative_column_widths.is_empty():
            return # TODO

        context.save()

        if self._prefer_dark:
            context.set_source_rgb(1.0, 1.0, 1.0)
        else:
            context.set_source_rgb(0.0, 0.0, 0.0)

        # Use system default font family for drawing text
        font_desc = Gtk.Widget.create_pango_context(area).get_font_description()
        font_family = font_desc.get_family() if font_desc else 'Sans'
        font_desc = Pango.font_description_from_string(f'{font_family} Normal Regular {self.FONT_SIZE}')

        x_start = self._display.ROW_HEADER_WIDTH
        cell_width = self._display.CELL_DEFAULT_WIDTH
        cell_height = self._display.CELL_DEFAULT_HEIGHT
        df_shape = self._dbms.get_shape()

        col_index = self._display.coordinate_to_column(self._display.scroll_horizontal_position)
        x_offset = 0
        if 0 <= col_index - 1 < self._display.cumulative_column_widths.shape[0]:
            x_offset = self._display.cumulative_column_widths[col_index - 1]
        x_offset -= self._display.scroll_horizontal_position
        if col_index < self._display.column_widths.shape[0]:
            cell_width = self._display.column_widths[col_index] + x_offset
        else:
            scroll_position = self._display.scroll_horizontal_position - self._display.cumulative_column_widths[-1]
            x_offset = scroll_position % self._display.CELL_DEFAULT_WIDTH
            cell_width = self._display.CELL_DEFAULT_WIDTH - x_offset

        x = x_start
        while x < width:
            y = self._display.COLUMN_HEADER_HEIGHT
            row_index = 0
            while y < height:
                row_index = (y - self._display.COLUMN_HEADER_HEIGHT) // cell_height + self._display.scroll_vertical_position // cell_height
                if df_shape[0] <= row_index:
                    height = y # prevent iteration over empty cells
                    break
                if df_shape[1] <= col_index:
                    width = x # prevent iteration over empty cells
                    break
                cell_actual_width = self._display.CELL_DEFAULT_WIDTH
                if col_index < self._display.column_widths.shape[0]:
                    cell_actual_width = self._display.column_widths[col_index]
                x_offset = 0
                if x == self._display.ROW_HEADER_WIDTH:
                    x_offset = cell_actual_width - cell_width
                x_text = x + self._display.CELL_DEFAULT_PADDING - x_offset
                cell_text = str(self._dbms.get_data(row_index, col_index))[:int(cell_actual_width * 1.25)] # 1.25 is a magic number
                context.save()
                context.rectangle(x, y, cell_width, cell_height)
                context.clip()
                context.move_to(x_text, 2 + y)
                layout = PangoCairo.create_layout(context)
                layout.set_text(cell_text, -1)
                layout.set_font_description(font_desc)
                PangoCairo.show_layout(context, layout)
                context.restore()
                y += cell_height
            x += cell_width
            col_index += 1
            if col_index < self._display.column_widths.shape[0]:
                cell_width = self._display.column_widths[col_index]
            else:
                cell_width = self._display.CELL_DEFAULT_WIDTH

        context.restore()

    def draw_cells_borders(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
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

        # Draw separator line between column header and the worksheet content
        context.move_to(0, y_start)
        context.line_to(width, y_start)
        context.move_to(x_start, 0)
        context.line_to(x_start, height)
        context.stroke()

        context.set_hairline(True)

        # Draw horizontal lines
        for y in range(y_start, height, cell_height):
            context.move_to(0, y)
            context.line_to(width, y)

        # Draw vertical lines
        if self._display.cumulative_column_widths.is_empty():
            for x in range(x_start, width, cell_width):
                context.move_to(x, 0)
                context.line_to(x, height)
        else:
            col_index = self._display.coordinate_to_column(self._display.scroll_horizontal_position)
            x_offset = 0
            if 0 <= col_index - 1 < self._display.cumulative_column_widths.shape[0]:
                x_offset = self._display.cumulative_column_widths[col_index - 1]
            x_offset -= self._display.scroll_horizontal_position
            cell_width = self._display.CELL_DEFAULT_WIDTH
            if col_index < self._display.column_widths.shape[0]:
                cell_width = self._display.column_widths[col_index] + x_offset
            else:
                scroll_position = self._display.scroll_horizontal_position - self._display.cumulative_column_widths[-1]
                x_offset = scroll_position % self._display.CELL_DEFAULT_WIDTH
                cell_width = self._display.CELL_DEFAULT_WIDTH - x_offset
            x = x_start
            while x < width:
                context.move_to(x, 0)
                context.line_to(x, height)
                x += cell_width
                col_index += 1
                if col_index < self._display.column_widths.shape[0]:
                    cell_width = self._display.column_widths[col_index]
                else:
                    cell_width = self._display.CELL_DEFAULT_WIDTH

        # Draw separator line between the worksheet column header and the data frame column header
        if not self._display.cumulative_column_widths.is_empty():
            context.move_to(x_start, cell_height)
            context.line_to(width, cell_height)

        context.stroke()
        context.restore()

    def draw_selection_borders(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
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
        x_start = self._display.ROW_HEADER_WIDTH + start_col * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
        y_start = self._display.COLUMN_HEADER_HEIGHT + start_row * self._display.CELL_DEFAULT_HEIGHT - self._display.scroll_vertical_position
        width_sel = (end_col - start_col + 1) * self._display.CELL_DEFAULT_WIDTH
        height_sel = (end_row - start_row + 1) * self._display.CELL_DEFAULT_HEIGHT

        if not self._display.cumulative_column_widths.is_empty():
            x_start = self._display.get_column_position(start_col) + self._display.ROW_HEADER_WIDTH - self._display.scroll_horizontal_position
            if start_col == end_col:
                width_sel = self._display.get_column_width(start_col)
            else:
                width_sel = self._display.get_column_position(end_col + 1) - self._display.get_column_position(start_col)

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

        if (col_index := self._selection.get_selected_column()) > -1:
            if self._prefer_dark:
                context.set_source_rgb(1.0, 1.0, 1.0)
            else:
                context.set_source_rgb(0.1, 0.1, 0.1)

            x_start = self._display.ROW_HEADER_WIDTH + col_index * self._display.CELL_DEFAULT_WIDTH - self._display.scroll_horizontal_position
            width_sel = (end_col - col_index + 1) * self._display.CELL_DEFAULT_WIDTH
            if not self._display.cumulative_column_widths.is_empty():
                x_start = self._display.get_column_position(col_index) + self._display.ROW_HEADER_WIDTH - self._display.scroll_horizontal_position
                width_sel = self._display.get_column_width(col_index)

            # Draw selection border around the selected column
            context.reset_clip()
            context.rectangle(self._display.ROW_HEADER_WIDTH - 1, self._display.CELL_DEFAULT_HEIGHT - 1, width, self._display.COLUMN_HEADER_HEIGHT)
            context.clip()
            context.rectangle(x_start, self._display.CELL_DEFAULT_HEIGHT, width_sel, self._display.CELL_DEFAULT_HEIGHT * 2)
            context.stroke()

        context.restore()
