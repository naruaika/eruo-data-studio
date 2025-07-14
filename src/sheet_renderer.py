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
        self.draw_headers_contents(context, width, height, display)
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
            context.set_source_rgb(0.15, 0.15, 0.15)
        else:
            context.set_source_rgb(0.9, 0.9, 0.9)

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
            context.set_source_rgb(0.1, 0.1, 0.1)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

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

        while y < height:
            # TODO: add support for custom row heights
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
                    0 < len(display.row_visible_series) and \
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
        x_offset = display.scroll_x_position % display.DEFAULT_CELL_WIDTH
        cell_width = display.DEFAULT_CELL_WIDTH - x_offset
        x = x_start

        context.reset_clip()
        context.rectangle(display.row_header_width, 0, width, height)
        context.clip()

        while x < width:
            # TODO: add indicator for hidden column(s)
            # TODO: add support for custom column widths
            x_offset = 0
            if x == display.row_header_width:
                x_offset = display.DEFAULT_CELL_WIDTH - cell_width
            x_line = x - x_offset
            context.move_to(x_line, 0)
            context.line_to(x_line, height)
            x += cell_width
            cell_width = display.DEFAULT_CELL_WIDTH

        context.stroke()

        context.restore()

    def draw_headers_contents(self, context: cairo.Context, width: int, height: int, display: SheetDisplay) -> None:
        context.save()

        # Monospace is the best in my opinion for the headers, especially when it comes to the row headers
        # which are numbers so that it can be easier to read because of the good visual alignment.
        font_description = Pango.font_description_from_string(f'Monospace Normal Bold {display.FONT_SIZE}px')
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(font_description)

        # We should achieve the high contrast between the text and the canvas background, though I'm aware
        # of the potential problems with using the pure black and white colors. Let's decide that later.
        text_color = (0.0, 0.0, 0.0)
        if self.prefers_dark:
            text_color = (1.0, 1.0, 1.0)
        context.set_source_rgb(*text_color)

        col_index = display.get_starting_column()
        x_offset = display.scroll_x_position % display.DEFAULT_CELL_WIDTH
        cell_width = display.DEFAULT_CELL_WIDTH - x_offset

        # Determine the starting column label
        text_index = col_index
        cell_text = ''
        while text_index >= 0:
            cell_text = chr(65 + text_index % 26) + cell_text
            text_index = text_index // 26 - 1

        # Draw column headers texts (centered)
        # It's so rare to see a worksheet go beyond Z*9 columns, but it's better to be prepared for it anyway
        # by having defining the clip region.
        x = display.row_header_width
        while x < width:
            x_offset = 0
            if x == display.row_header_width:
                x_offset = display.DEFAULT_CELL_WIDTH - cell_width
            layout.set_text(cell_text, -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            x_text = x + (display.DEFAULT_CELL_WIDTH - text_width) / 2 - x_offset

            context.save()
            context.rectangle(x, 0, cell_width, display.column_header_height)
            context.clip()
            context.move_to(x_text, 2)
            PangoCairo.show_layout(context, layout)
            context.restore()

            x += cell_width
            col_index += 1
            cell_width = display.DEFAULT_CELL_WIDTH
            # TODO: add support for skipping hidden column(s)
            cell_text = display.get_right_cell_name(cell_text)

        # Determine the starting row number
        row_index = display.get_starting_row() + 1
        cell_text = display.get_vrow_from_row(row_index)

        # Draw row headers texts (right-aligned)
        # Here we don't necessarily need the clip region because the row headers are usually if not always
        # readjusted before even moving to the rendering process.
        y = display.column_header_height
        while y < height:
            # Handle edge cases where the last row(s) are hidden
            if row_index - 1 == len(display.row_visible_series) and \
                    0 < len(display.row_visible_series) and \
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

        if 'content' not in self.render_caches:
            self.render_caches['content'] = {
                'surface': cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height),
                'width': width,
                'height': height,
                'x_pos': display.scroll_x_position,
                'y_pos': display.scroll_y_position,
                'blank': True,
            }

        # Use system default font family for drawing text
        font_desc = Gtk.Widget.create_pango_context(canvas).get_font_description()
        font_family = font_desc.get_family() if font_desc else 'Sans'
        font_desc = Pango.font_description_from_string(f'{font_family} Normal Regular {display.FONT_SIZE}px')

        x_start = display.row_header_width
        y_start = display.column_header_height
        x_end = width
        y_end = height

        rcache = self.render_caches['content']
        ccontext = cairo.Context(rcache['surface'])

        if not rcache['blank']:
            scroll_x_offset = display.scroll_x_position - rcache['x_pos']
            scroll_y_offset = display.scroll_y_position - rcache['y_pos']

            # Prevent the canvas from being drawn when the scroll isn't changed
            if scroll_x_offset == 0 and scroll_y_offset == 0:
                x_end = 0

            if not (scroll_x_offset == 0 and scroll_y_offset == 0):
                nsurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                ncontext = cairo.Context(nsurface)

                if abs(scroll_y_offset) < height or abs(scroll_x_offset) < width:
                    clip_x = display.row_header_width
                    clip_y = display.column_header_height

                    if scroll_x_offset > 0:
                        # Basically we want to minimize the glitches when scrolling to the right or bottom where cells
                        # near the right/bottom edges are getting bolder when scrolling due to getting multiple redraws.
                        # TODO: this should be taken care as we'll add support for non-uniform column sizes
                        # TODO: remember that we currently don't have support for continuous scrolling too
                        clip_width = width - display.row_header_width
                        clip_width = clip_width - (display.DEFAULT_CELL_WIDTH * scroll_x_offset / display.DEFAULT_CELL_WIDTH)
                        clip_width = clip_width - (width - display.row_header_width) % display.DEFAULT_CELL_WIDTH
                        clip_height = height - display.column_header_height
                    elif scroll_y_offset > 0:
                        clip_width = width - display.row_header_width
                        clip_height = height - display.column_header_height
                        clip_height = clip_height - (display.DEFAULT_CELL_HEIGHT * scroll_y_offset / display.DEFAULT_CELL_HEIGHT)
                        clip_height = clip_height - (height - display.column_header_height) % display.DEFAULT_CELL_HEIGHT
                    else:
                        clip_width = width - display.row_header_width
                        clip_height = height - display.column_header_height

                    ncontext.save()
                    ncontext.rectangle(clip_x, clip_y, clip_width, clip_height)
                    ncontext.clip()
                    ncontext.set_source_surface(rcache['surface'], -scroll_x_offset, -scroll_y_offset)
                    ncontext.paint()
                    ncontext.restore()

                ccontext = ncontext
                rcache['surface'] = nsurface
                rcache['x_pos'] = display.scroll_x_position
                rcache['y_pos'] = display.scroll_y_position

                if scroll_x_offset > 0:
                    x_start = x_end - scroll_x_offset
                    x_start = x_start - (x_start - display.row_header_width) % display.DEFAULT_CELL_WIDTH
                    x_start = max(x_start, display.row_header_width)
                elif scroll_x_offset < 0:
                    x_end = x_start - scroll_x_offset
                    x_end = min(x_end, width)

                if scroll_y_offset > 0:
                    y_start = y_end - scroll_y_offset
                    y_start = y_start - (y_start - display.column_header_height) % display.DEFAULT_CELL_HEIGHT
                    y_start = max(y_start, display.column_header_height)
                elif scroll_y_offset < 0:
                    y_end = y_start - scroll_y_offset
                    y_end = min(y_end, height)

        self.setup_cairo_context(ccontext)

        # We use the same color scheme as the headers
        if self.prefers_dark:
            ccontext.set_source_rgb(1.0, 1.0, 1.0)
        else:
            ccontext.set_source_rgb(0.0, 0.0, 0.0)

        layout = PangoCairo.create_layout(ccontext)
        layout.set_font_description(font_desc)

        cell_width = display.DEFAULT_CELL_WIDTH
        cell_height = display.DEFAULT_CELL_HEIGHT

        # TODO: support multiple dataframes?
        x = x_start
        col_index = int((x - display.row_header_width) // cell_width + display.get_starting_column())
        while x < x_end:
            if data.bbs[0].column_span <= col_index:
                width = x # prevent iteration over empty cells
                break
            ccontext.save()
            ccontext.rectangle(x, display.column_header_height, cell_width - 1, height)
            ccontext.clip()
            y = y_start
            row_index = int((y - display.column_header_height) // cell_height + display.get_starting_row())
            while y < y_end:
                if data.bbs[0].row_span <= row_index:
                    height = y # prevent iteration over empty cells
                    break
                if row_index == 0: # dataframe header
                    cname = data.dfs[0].columns[col_index]
                    dtype = display.get_dtype_symbol(data.dfs[0].dtypes[col_index])
                    cell_text = f'{cname} ({dtype})'
                else: # dataframe content
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
                    y += cell_height # skip empty cells
                    row_index += 1
                    continue
                # Truncate before the first line break to prevent overflow
                cell_text = str(cell_text).split('\n', 1)[0]
                # Truncate the contents for performance reasons
                cell_text = cell_text[:int(cell_width * 0.2)] # FIXME: 0.2 is a magic number
                ccontext.move_to(x + display.DEFAULT_CELL_PADDING, y + 2)
                layout.set_text(cell_text, -1)
                PangoCairo.show_layout(ccontext, layout)
                y += cell_height
                row_index += 1
            ccontext.restore()
            x += cell_width
            col_index += 1

        context.set_source_surface(self.render_caches['content']['surface'], 0, 0)
        context.paint()

        self.render_caches['content']['blank'] = False

    def draw_selection_borders(self, context: cairo.Context, width: int, height: int, display: SheetDisplay, selection: SheetSelection) -> None:
        context.save()

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
            range_y = height + 1
            range_height = 0
        # Hide the bottom of the selection if it is not yet in the viewport
        if height < range_y + range_height:
            range_height = height + 1 - range_y

        # Hide the left of the selection if it is exceeded by the scroll viewport
        if range_x < 0:
            range_width += range_x
            range_x = 0
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