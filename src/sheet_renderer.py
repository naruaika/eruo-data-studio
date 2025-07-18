# sheet_renderer.py
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


from gi.repository import Adw, GObject, Gtk, Pango, PangoCairo
import cairo

from . import globals
from .sheet_document import SheetDocument
from .sheet_data import SheetData
from .sheet_display import SheetDisplay
from .sheet_selection import SheetSelection

class SheetRenderer(GObject.Object):
    __gtype_name__ = 'SheetRenderer'

    prefers_dark: bool = False
    color_accent: tuple[float, float, float, float]
    render_caches: dict[str, cairo.ImageSurface]

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document
        self.render_caches = {}

    def render(self, canvas: Gtk.DrawingArea, context: cairo.Context, width: int, height: int) -> None:
        display = self.document.display
        data = self.document.data
        selection = self.document.selection

        # We may not want to change the order of these calls as it can causes
        # unoptimal rendering results :)
        self.setup_cairo_context(context)
        self.draw_headers_backgrounds(context, width, height, display)
        self.draw_selection_backgrounds(context, width, height, display, selection)
        self.draw_cells_borders(context, width, height, display)
        self.draw_headers_contents(canvas, context, width, height, display, data)
        self.draw_cells_contents(canvas, context, width, height, display, data)
        self.draw_selection_borders(context, width, height, display, selection)

    def setup_cairo_context(self, context: cairo.Context) -> None:
        # We want that the canvas color scheme respects the system color scheme
        if (prefers_dark := Adw.StyleManager().get_dark()) != self.prefers_dark:
            self.prefers_dark = prefers_dark
            self.render_caches = {}

        # self.color_accent = (0.20, 0.51, 0.89, 1.00)
        self.color_accent = Adw.StyleManager().get_accent_color_rgba()

        # I don't actually see any difference between the default and good antialiasing,
        # but I'll leave it here for now
        font_options = cairo.FontOptions()
        font_options.set_antialias(cairo.Antialias.GOOD)

        # I assume this is mandatory for drawing hairline type lines,
        # I might be cannot remember correctly though :/
        context.set_font_options(font_options)
        context.set_antialias(cairo.Antialias.NONE)

    def draw_headers_backgrounds(self, context: cairo.Context, width: int, height: int, display: SheetDisplay) -> None:
        context.save()

        # The only reason is because we want to separate the headers from the contents.
        # I do agree that it's not always good to hardcode like this, so let's flag it
        # as a TODO for now.
        if self.prefers_dark:
            context.set_source_rgb(0.11, 0.11, 0.13)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

        context.rectangle(0, 0, width, display.column_header_height)
        context.rectangle(0, display.column_header_height, display.row_header_width, height)
        context.fill()

        context.restore()

    def draw_selection_backgrounds(self, context: cairo.Context, width: int, height: int, display: SheetDisplay, selection: SheetSelection) -> None:
        context.save()

        # range_x and range_y were adjusted by the sheet document, so now they are relative to the top
        # of the viewport, meaning they'll be negative if the user scrolled down. The calculations below
        # is only for optimization purposes or to handle the case where the selection size is too big so
        # that it can only be partially drawn.
        range = selection.current_active_range
        range_x = range.x
        range_y = range.y
        range_width = range.width
        range_height = range.height

        # Hide the top of the selection if it is exceeded by the scroll viewport
        if range_y < 0:
            range_height += range_y
            range_y = 0
        # Hide the entire selection if it is exceeded by the scroll viewport
        if range_height < 0:
            range_height = 0
        # Hide the entire selection if the viewport has not reached it yet
        if height < range_y:
            range_y = height
            range_height = 0
        # Hide the bottom of the selection if it is not yet in the viewport
        if height < range_y + range_height:
            range_height = height - range_y

        # Hide the left of the selection if it is exceeded by the scroll viewport
        if range_x < 0:
            range_width += range_x
            range_x = 0
        # Hide the entire selection if it is exceeded by the scroll viewport
        if range_width < 0:
            range_width = 0
        # Hide the entire selection if the viewport has not reached it yet
        if width < range_x:
            range_x = width
            range_width = 0
        # Hide the right of the selection if it is not yet in the viewport
        if width < range_x + range_width:
            range_width = width - range_x

        # Clipping for when the user selects the entire row(s). You may notice that
        # I didn't adjust the width and height as it's not worth the complexity.
        if range.column == 0:
            context.rectangle(-1, display.column_header_height - 1, width, height)
            context.clip()
        # Clipping for when the user selects the entire column(s)
        if range.row == 0:
            context.rectangle(display.row_header_width - 1, -1, width, height)
            context.clip()
        # Clipping for general use cases
        if range.column > 0 and range.row > 0:
            context.rectangle(display.row_header_width - 1, display.column_header_height - 1, width, height)
            context.clip()

        # Reduces the opacity of the accent color so that it doesn't look too bright,
        # we try to imitate the behavior of other applications.
        accent_rgba = list(self.color_accent)
        accent_rgba[3] = 0.2
        context.set_source_rgba(*accent_rgba)

        # Draw the selection only if it's perceivable
        if range_width > 0 and range_height > 0:
            context.rectangle(range_x, range_y, range_width, range_height)
            context.fill()

        # Indicates that the user has selected the entire column(s) by highlighting all the row headers
        if range.column > 0 and range.row == 0:
            context.reset_clip()
            context.rectangle(0, display.column_header_height, display.row_header_width, height)
            context.fill()

        # Indicates that the user has selected the entire row(s) by highlighting all the column headers
        if range.column == 0 and range.row > 0:
            context.reset_clip()
            context.rectangle(display.row_header_width, 0, width, display.column_header_height)
            context.fill()

        # Indicates that the user has a selection by highlighting the row and column header(s)
        if range.column > 0 and range.row > 0:
            context.reset_clip()
            context.rectangle(display.row_header_width - 1, 0, width, height)
            context.clip()
            context.rectangle(range_x, 0, range_width, display.column_header_height)
            context.fill()

            context.reset_clip()
            context.rectangle(0, display.column_header_height - 1, width, height)
            context.clip()
            context.rectangle(0, range_y, display.row_header_width, range_height)
            context.fill()

        # We want more emphasis for when the user has selected column(s), row(s), or even the entire sheet,
        # so we'll increase the opacity again
        accent_rgba[3] = 1.0
        context.set_source_rgba(*accent_rgba)

        # Bold highlight all the column headers if the user has selected the entire sheet
        if range.column == 0 and range.row == 0:
            context.reset_clip()
            context.rectangle(display.row_header_width, range_y, width, display.column_header_height)
            context.rectangle(range_x, display.column_header_height, display.row_header_width, range_height)
            context.fill()

        # Bold highlight the selected column(s) header
        if range.column > 0 and range.row == 0:
            context.reset_clip()
            context.rectangle(display.row_header_width -1, -1, width, height)
            context.clip()
            context.rectangle(range_x, range_y, range_width, display.column_header_height)
            context.fill()

        # Bold highlight the selected row(s) header
        if range.column == 0 and range.row > 0:
            context.reset_clip()
            context.rectangle(-1, display.column_header_height - 1, width, height)
            context.clip()
            context.rectangle(range_x, range_y, display.row_header_width, range_height)
            context.fill()

        # It's important to differentiate between the active cell and the selection range
        # because the active cell is the only one that its data is appearing in the input bar.
        # Here we reset the color of the drawing context back to the canvas background color.
        if self.prefers_dark:
            context.set_source_rgb(0.13, 0.13, 0.15)
        else:
            context.set_source_rgb(0.98, 0.98, 0.98)

        # Highlight the active cell if the user is currently editing it
        if globals.is_editing_cells:
            accent_rgba[3] = 0.2
            context.set_source_rgba(*accent_rgba)

        cell = selection.current_active_cell

        context.reset_clip()
        context.rectangle(display.row_header_width - 1, display.column_header_height - 1, width, height)
        context.clip()
        context.rectangle(cell.x, cell.y, cell.width, cell.height)
        context.fill()

        context.restore()

    def draw_cells_borders(self, context: cairo.Context, width: int, height: int, display: SheetDisplay) -> None:
        context.save()

        # We need to make sure that the cell borders are contrast enough to the canvas background
        if self.prefers_dark:
            context.set_source_rgb(0.25, 0.25, 0.25)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)

        x_start = display.row_header_width
        y_start = display.column_header_height
        cell_width = display.DEFAULT_CELL_WIDTH
        cell_height = display.DEFAULT_CELL_HEIGHT

        # Draw separator line between headers and contents
        context.move_to(0, y_start)
        context.line_to(width, y_start)
        context.move_to(x_start, 0)
        context.line_to(x_start, height)
        context.stroke()

        # I bet this is better than a thick line!
        context.set_hairline(True)

        # Draw horizontal lines
        y = y_start

        nrow_index = int((y - display.column_header_height) // cell_height + display.get_starting_row())
        prow_index = nrow_index

        context.reset_clip()
        context.rectangle(0, display.column_header_height, width, height)
        context.clip()

        # TODO: add support for custom row heights
        while y < height:
            context.move_to(x_start, y)
            context.line_to(width, y)

            # Skipping rows that are hidden will result in double lines
            double_lines = False
            if nrow_index < len(display.row_visible_series):
                vrow_index = display.row_visible_series[nrow_index]
                if vrow_index != prow_index:
                    double_lines = True
                    prow_index = vrow_index

            # Handle edge cases where the last row(s) are hidden
            elif nrow_index == len(display.row_visible_series) and \
                    len(display.row_visible_series) and \
                    display.row_visible_series[-1] + 1 < len(display.row_visibility_flags) and \
                    not display.row_visibility_flags[display.row_visible_series[-1] + 1]:
                double_lines = True

            if double_lines:
                context.move_to(0, y - 2)
                context.line_to(x_start, y - 2)
                context.move_to(0, y + 2)
                context.line_to(x_start, y + 2)
            else:
                context.move_to(0, y)
                context.line_to(x_start, y)

            y += cell_height
            nrow_index += 1
            prow_index += 1

        context.stroke()

        # Draw vertical lines
        ncol_index = display.get_starting_column()
        pcol_index = ncol_index

        context.reset_clip()
        context.rectangle(display.row_header_width, 0, width, height)
        context.clip()

        x = x_start
        x_offset = 0
        while x < width:
            # Skipping columns that are hidden will result in double lines
            double_lines = False
            if ncol_index < len(display.column_visible_series):
                vcol_index = display.column_visible_series[ncol_index]
                if vcol_index != pcol_index:
                    double_lines = True
                    pcol_index = vcol_index

            # Handle edge cases where the last column(s) are hidden
            elif ncol_index == len(display.column_visible_series) and \
                    len(display.column_visible_series) and \
                    display.column_visible_series[-1] + 1 < len(display.column_visibility_flags) and \
                    not display.column_visibility_flags[display.column_visible_series[-1] + 1]:
                double_lines = True

            # Get the width of the next appearing column
            cell_width = display.DEFAULT_CELL_WIDTH
            if ncol_index < len(display.column_widths):
                cell_width = display.column_widths[ncol_index]

            # Offset the first appearing column to account for the scroll position if necessary
            if x == x_start and 0 < display.scroll_x_position and len(display.cumulative_column_widths):
                x_offset = display.scroll_x_position
                if 0 < ncol_index <= len(display.cumulative_column_widths):
                    x_offset -= display.cumulative_column_widths[ncol_index - 1]
                elif len(display.cumulative_column_widths) < ncol_index:
                    x_offset = (x_offset - display.cumulative_column_widths[-1]) % display.DEFAULT_CELL_WIDTH
                x -= x_offset

            # Draw line(s) in the locator area
            if double_lines:
                context.move_to(x - 2, 0)
                context.line_to(x - 2, y_start)
                context.move_to(x + 2, 0)
                context.line_to(x + 2, y_start)
            else:
                context.move_to(x, 0)
                context.line_to(x, y_start)

            # Draw line in the content area
            context.move_to(x, y_start)
            context.line_to(x, height)

            x += cell_width
            ncol_index += 1
            pcol_index += 1

        context.stroke()

        context.restore()

    def draw_headers_contents(self, canvas: Gtk.DrawingArea, context: cairo.Context, width: int, height: int, display: SheetDisplay, data: SheetData) -> None:
        context.save()

        # Monospace is the best in my opinion for the headers, especially when it comes to the row headers
        # which are numbers so that it can be easier to read because of the good visual alignment.
        header_font_desc = Pango.font_description_from_string(f'Monospace Normal Bold {display.FONT_SIZE}px')
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(header_font_desc)

        # Use system default font family for drawing text
        body_font_desc = Gtk.Widget.create_pango_context(canvas).get_font_description()
        font_family = body_font_desc.get_family() if body_font_desc else 'Sans'
        body_font_desc = Pango.font_description_from_string(f'{font_family} Normal Bold {display.FONT_SIZE}px')

        # We should achieve the high contrast between the text and the canvas background, though I'm aware
        # of the potential problems with using the pure black and white colors. Let's decide that later.
        text_color = (0.0, 0.0, 0.0)
        if self.prefers_dark:
            text_color = (1.0, 1.0, 1.0)
        context.set_source_rgb(*text_color)

        # Determine the starting column label
        col_index = display.get_starting_column() + 1

        context.save()
        context.rectangle(display.row_header_width, 0, width, height)
        context.clip()

        # Draw column headers texts (centered)
        # It's so rare to see a worksheet go beyond Z*9 columns, but it's better to be prepared for it anyway
        # by having defining the clip region to prevent the text from overflowing to the next cells. TODO: maybe
        # it's better to automatically adjust the cell widths to fit the text width if the text is overflowing?
        x_start = display.row_header_width
        x = x_start
        x_offset = 0
        while x < width:
            # Handle edge cases where the last column(s) are hidden
            if col_index - 1 == len(display.column_visible_series) and \
                    len(display.column_visible_series) and \
                    display.column_visible_series[-1] + 1 < len(display.column_visibility_flags) and \
                    not display.column_visibility_flags[display.column_visible_series[-1] + 1]:
                col_index += (len(display.column_visibility_flags) - 1) - (display.column_visible_series[-1] - 1) - 1

            # Get the width of the next appearing column
            cell_width = display.DEFAULT_CELL_WIDTH
            if col_index - 1 < len(display.column_widths):
                cell_width = display.column_widths[col_index - 1]

            # Offset the first appearing column to account for the scroll position if necessary
            if x == x_start and 0 < display.scroll_x_position and len(display.cumulative_column_widths):
                x_offset = display.scroll_x_position
                if 0 < col_index - 1 <= len(display.cumulative_column_widths):
                    x_offset -= display.cumulative_column_widths[col_index - 2]
                elif len(display.cumulative_column_widths) < col_index - 1:
                    x_offset = (x_offset - display.cumulative_column_widths[-1]) % display.DEFAULT_CELL_WIDTH
                x -= x_offset

            vcol_index = display.get_vcolumn_from_column(col_index)

            # Draw dataframe header
            if len(data.bbs) and 0 < display.scroll_y_position and col_index <= data.bbs[0].column_span:
                cname = data.dfs[0].columns[vcol_index - 1]
                dtype = display.get_dtype_symbol(data.dfs[0].dtypes[vcol_index - 1])
                layout.set_font_description(body_font_desc)
                layout.set_text(f'{cname} ({dtype})', -1)
                x_text = x + display.DEFAULT_CELL_PADDING

            # Draw column name
            else:
                cell_text = display.get_column_name_from_column(vcol_index)
                layout.set_font_description(header_font_desc)
                layout.set_text(cell_text, -1)
                text_width = layout.get_size()[0] / Pango.SCALE
                x_text = x + (cell_width - text_width) / 2

            context.save()
            context.rectangle(x, 0, cell_width - 1, display.column_header_height)
            context.clip()
            context.move_to(x_text, 2)
            PangoCairo.show_layout(context, layout)
            context.restore()

            x += cell_width
            col_index += 1

        context.restore()

        layout.set_font_description(header_font_desc)

        # Determine the starting row number
        row_index = display.get_starting_row() + 1

        # Draw row headers texts (right-aligned)
        # Here we don't necessarily need the clip region because the row headers are usually if not always
        # readjusted before even moving to the rendering process.
        y = display.column_header_height
        while y < height:
            # Handle edge cases where the last row(s) are hidden
            if row_index - 1 == len(display.row_visible_series) and \
                    len(display.row_visible_series) and \
                    display.row_visible_series[-1] + 1 < len(display.row_visibility_flags) and \
                    not display.row_visibility_flags[display.row_visible_series[-1] + 1]:
                row_index += (len(display.row_visibility_flags) - 1) - (display.row_visible_series[-1] - 1) - 1

            cell_text = display.get_vrow_from_row(row_index)
            layout.set_text(str(cell_text), -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            x = display.row_header_width - text_width - display.DEFAULT_CELL_PADDING

            context.move_to(x, 2 + y)
            PangoCairo.show_layout(context, layout)

            row_index += 1
            y += display.DEFAULT_CELL_HEIGHT

        context.restore()

    def draw_cells_contents(self, canvas: Gtk.DrawingArea, context: cairo.Context, width: int, height: int, display: SheetDisplay, data: SheetData) -> None:
        if len(data.dfs) == 0:
            return

        # Drawing loop boundaries
        x_start = display.row_header_width
        y_start = display.column_header_height
        x_end = width
        y_end = height

        # Boundaries for non-cached area
        nx_start = x_start
        ny_start = y_start
        nx_end = x_end
        ny_end = y_end

        use_cache = True

        # Create the cache if it doesn't exist
        if 'content' not in self.render_caches:
            self.render_caches['content'] = {
                'surface': cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height),
                'x_pos': display.scroll_x_position,
                'y_pos': display.scroll_y_position,
            }
            use_cache = False

        rcache = self.render_caches['content']
        ccontext = cairo.Context(rcache['surface'])

        if use_cache:
            # Calculate the scroll position offset
            x_offset = display.scroll_x_position - rcache['x_pos']
            y_offset = display.scroll_y_position - rcache['y_pos']

            # Prevent the canvas from being re-drawn when the scroll isn't changed
            if x_offset == 0 and y_offset == 0:
                context.set_source_surface(rcache['surface'], 0, 0)
                context.paint()
                return

            nsurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            ncontext = cairo.Context(nsurface)

            # Use cache if only the cache area will be visible in the viewport
            # and the canvas movement is not diagonal.
            if abs(x_offset) < width and abs(y_offset) < height and \
                    (abs(x_offset) > 0 and y_offset == 0) or \
                    (abs(y_offset) > 0 and x_offset == 0):
                if x_offset > 0:
                    nx_start = display.get_cell_x_from_point(width - x_offset)
                    cwidth = nx_start - x_start
                    ncontext.rectangle(x_start, y_start, cwidth, y_end)
                elif x_offset < 0:
                    nx_end = display.get_cell_x_from_point(x_start - x_offset)
                    cwidth = display.get_cell_width_from_point(x_start - x_offset)
                    ncontext.rectangle(nx_end + cwidth, y_start, x_end, y_end)

                if y_offset > 0:
                    ny_start = display.get_cell_y_from_point(height - y_offset)
                    cheight = ny_start - y_start
                    ncontext.rectangle(x_start, y_start, x_end, cheight)
                elif y_offset < 0:
                    ny_end = display.get_cell_y_from_point(y_start - y_offset)
                    cheight = display.get_cell_height_from_point(y_start - y_offset)
                    ncontext.rectangle(x_start, ny_end + cheight, x_end, y_end)

                ncontext.clip()
                ncontext.set_source_surface(rcache['surface'], -x_offset, -y_offset)
                ncontext.paint()
                ncontext.reset_clip()

            ccontext = ncontext
            rcache['surface'] = nsurface
            rcache['x_pos'] = display.scroll_x_position
            rcache['y_pos'] = display.scroll_y_position

        self.setup_cairo_context(ccontext)

        # Use system default font family for drawing text
        font_desc = Gtk.Widget.create_pango_context(canvas).get_font_description()
        font_family = font_desc.get_family() if font_desc else 'Sans'
        header_font_desc = Pango.font_description_from_string(f'{font_family} Normal Bold {display.FONT_SIZE}px')
        body_font_desc = Pango.font_description_from_string(f'{font_family} Normal Regular {display.FONT_SIZE}px')

        layout = PangoCairo.create_layout(ccontext)

        ccontext.save()
        ccontext.rectangle(x_start, y_start, x_end, y_end)
        ccontext.clip()

        # We use the same color scheme as the headers
        if self.prefers_dark:
            ccontext.set_source_rgb(1.0, 1.0, 1.0)
        else:
            ccontext.set_source_rgb(0.0, 0.0, 0.0)

        cell_width = display.DEFAULT_CELL_WIDTH
        cell_height = display.DEFAULT_CELL_HEIGHT

        # TODO: support multiple dataframes?
        x = x_start
        x_offset = 0
        col_index = display.get_starting_column()
        while x < x_end:
            if data.bbs[0].column_span <= col_index:
                width = x # prevent iteration over empty cells
                break

            y = y_start
            row_index = int((y - display.column_header_height) // cell_height + display.get_starting_row())

            # Get the width of the next appearing column
            cell_width = display.DEFAULT_CELL_WIDTH
            if col_index < len(display.column_widths):
                cell_width = display.column_widths[col_index]

            # Offset the first appearing column to account for the scroll position if necessary
            if x == x_start and 0 < display.scroll_x_position and len(display.cumulative_column_widths):
                x_offset = display.scroll_x_position
                if 0 < col_index <= len(display.cumulative_column_widths):
                    x_offset -= display.cumulative_column_widths[col_index - 1]
                elif len(display.cumulative_column_widths) < col_index:
                    x_offset = (x_offset - display.cumulative_column_widths[-1]) % display.DEFAULT_CELL_WIDTH
                x -= x_offset
                if nx_start == x_start:
                    nx_start -= x_offset

            ccontext.save()
            ccontext.rectangle(x, display.column_header_height, cell_width - 1, height)
            ccontext.clip()

            while y < y_end:
                if y < ny_start or ny_end < y or x < nx_start or nx_end < x:
                    y += cell_height
                    row_index += 1
                    continue # skip cached area

                if data.bbs[0].row_span <= row_index:
                    height = y
                    break # prevent iteration over empty cells

                # Draw dataframe header
                if row_index == 0:
                    layout.set_font_description(header_font_desc)
                    if col_index < len(display.column_visible_series):
                        vcol_index = display.column_visible_series[col_index]
                    else:
                        vcol_index = col_index
                    cname = data.dfs[0].columns[vcol_index]
                    dtype = display.get_dtype_symbol(data.dfs[0].dtypes[vcol_index])
                    cell_text = f'{cname} ({dtype})'

                # Draw dataframe content
                else:
                    layout.set_font_description(body_font_desc)
                    if row_index < len(display.row_visible_series):
                        vrow_index = display.row_visible_series[row_index]
                    else:
                        vrow_index = row_index
                    if col_index < len(display.column_visible_series):
                        vcol_index = display.column_visible_series[col_index]
                    else:
                        vcol_index = col_index
                    cell_text = data.dfs[0][vrow_index - 1, vcol_index]

                if cell_text in ['', None]:
                    y += cell_height
                    row_index += 1
                    continue # skip empty cells

                # Truncate before the first line break to prevent overflow
                cell_text = str(cell_text).split('\n', 1)[0]
                # Truncate the contents for performance reasons
                cell_text = cell_text[:int(cell_width * 0.2)] # TODO: 0.2 is a magic number

                ccontext.move_to(x + display.DEFAULT_CELL_PADDING, y + 2)
                layout.set_text(cell_text, -1)
                PangoCairo.show_layout(ccontext, layout)

                # TODO: add support for custom row heights
                y += cell_height
                row_index += 1

            ccontext.restore()
            x += cell_width
            col_index += 1

        ccontext.restore()

        context.set_source_surface(rcache['surface'], 0, 0)
        context.paint()

    def draw_selection_borders(self, context: cairo.Context, width: int, height: int, display: SheetDisplay, selection: SheetSelection) -> None:
        context.save()

        def auto_adjust_selection_range(range_x: int, range_y: int, range_width: int, range_height: int) -> tuple[int, int, int, int]:
            # Hide the top of the selection if it is exceeded by the scroll viewport
            if range_y < 0:
                range_height += range_y
                range_y = display.column_header_height
                range_height -= display.column_header_height
            # Hide the entire selection if it is exceeded by the scroll viewport
            if range_height < 0:
                range_height = 0
            # Hide the entire selection if the viewport has not reached it yet
            if height < range_y:
                range_y = height + 1
                range_height = 0
            # Hide the bottom of the selection if it is not yet in the viewport
            if height < range_y + range_height:
                range_height = height + 1 - range_y

            # Hide the left of the selection if it is exceeded by the scroll viewport
            if range_x < 0:
                range_width += range_x
                range_x = display.row_header_width
                range_width -= display.row_header_width
            # Hide the entire selection if it is exceeded by the scroll viewport
            if range_width < 0:
                range_width = 0
            # Hide the entire selection if the viewport has not reached it yet
            if width < range_x:
                range_x = width + 1
                range_width = 0
            # Hide the right of the selection if it is not yet in the viewport
            if width < range_x + range_width:
                range_width = width + 1 - range_x

            return range_x, range_y, range_width, range_height

        range = selection.current_active_range
        range_x, range_y, range_width, range_height = auto_adjust_selection_range(range.x, range.y, range.width, range.height)

        search_range = selection.current_search_range
        if search_range is not None:
            search_range_x, search_range_y, search_range_width, search_range_height = auto_adjust_selection_range(search_range.x, search_range.y,
                                                                                                                  search_range.width, search_range.height)

        # Clipping for when the user selects the entire row(s). You may notice that
        # I didn't adjust the width and height as it's not worth the complexity.
        if range.column == 0:
            context.rectangle(-1, display.column_header_height - 1, width, height)
            context.clip()
        # Clipping for when the user selects the entire column(s)
        if range.row == 0:
            context.rectangle(display.row_header_width - 1, -1, width, height)
            context.clip()
        # Clipping for general use cases
        if range.column > 0 and range.row > 0:
            context.rectangle(display.row_header_width - 1, display.column_header_height - 1, width, height)
            context.clip()

        # We use a bold style here
        context.set_source_rgba(*self.color_accent)
        context.set_line_width(2)

        # Don't render the active selection when the user selects the entire sheet
        if not (range_x == 0 and range_y == 0) and not globals.is_editing_cells:
            context.rectangle(range_x, range_y, range_width, range_height)
            context.stroke()

            # Render the search range
            if search_range is not None:
                context.save()
                context.set_line_width(1)
                context.set_dash([4, 4], 0)
                context.rectangle(search_range_x, search_range_y, search_range_width, search_range_height)
                context.stroke()
                context.restore()

        # Indicates that the user has selected the entire column(s) by drawing a vertical line
        # next to the row headers
        if range.column > 0 and range.row == 0:
            context.move_to(display.row_header_width, display.column_header_height - 1)
            context.line_to(display.row_header_width, height)
            context.stroke()

        # Indicates that the user has selected the entire row(s) by drawing a horizontal line
        # next to the column headers
        if range.column == 0 and range.row > 0:
            context.move_to(display.row_header_width - 1, display.column_header_height)
            context.line_to(width, display.column_header_height)
            context.stroke()

        # Indicates that the user has a selection by drawing a line next to the row and column header(s)
        if range.column > 0 and range.row > 0:
            context.move_to(range_x, display.column_header_height)
            context.line_to(range_x + range_width, display.column_header_height)
            context.move_to(display.row_header_width, range_y)
            context.line_to(display.row_header_width, range_y + range_height)
            context.stroke()

        context.restore()