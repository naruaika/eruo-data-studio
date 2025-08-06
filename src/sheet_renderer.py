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
from time import time
import cairo

from . import globals
from . import utils
from .sheet_document import SheetDocument
from .sheet_data import SheetData
from .sheet_display import SheetDisplay
from .sheet_selection import SheetSelection
from .sheet_widget import SheetWidget

class SheetRenderer(GObject.Object):
    __gtype_name__ = 'SheetRenderer'

    prefers_dark: bool = False
    color_accent: tuple[float, float, float, float]
    render_caches: dict[str, cairo.ImageSurface]

    def __init__(self, document: SheetDocument) -> None:
        super().__init__()

        self.document = document
        self.render_caches = {}

    def render(self,
               canvas:  Gtk.DrawingArea,
               context: cairo.Context,
               width:   int,
               height:  int) -> None:
        display = self.document.display
        data = self.document.data
        selection = self.document.selection
        widgets = self.document.widgets

        # We may not want to change the order of these calls as it can causes
        # unoptimal rendering results :)
        self.setup_cairo_context(context)
        self.draw_headers_backgrounds(context, width, height, display)
        self.draw_selection_backgrounds(context, width, height, display, selection)
        self.draw_headers_contents(canvas, context, width, height, display, data)
        self.draw_cells_contents(canvas, context, width, height, display, data)
        self.draw_selection_overlay(context, width, height, display, selection)
        self.draw_cells_borders(context, width, height, display)
        self.draw_selection_borders(context, width, height, display, selection)
        self.draw_virtual_widgets(context, width, height, display, widgets)

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

    def draw_headers_backgrounds(self,
                                 context: cairo.Context,
                                 width:   int,
                                 height:  int,
                                 display: SheetDisplay) -> None:
        context.save()

        # The only reason is because we want to separate the headers from the contents.
        # I do agree that it's not always good to hardcode like this, so let's flag it
        # as a TODO for now.
        if self.prefers_dark:
            context.set_source_rgb(0.11, 0.11, 0.13)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

        context.rectangle(0, 0, width, display.top_locator_height)
        context.rectangle(0, display.top_locator_height, display.left_locator_width, height)
        context.fill()

        context.restore()

    def draw_selection_backgrounds(self,
                                   context:   cairo.Context,
                                   width:     int,
                                   height:    int,
                                   display:   SheetDisplay,
                                   selection: SheetSelection) -> None:
        context.save()

        # range_x and range_y were adjusted by the sheet document, so now they are relative to the top
        # of the viewport, meaning they'll be negative if the user scrolled down. The calculations below
        # is only for optimization purposes or to handle the case where the selection size is too big so
        # that it can only be partially drawn.
        arange = selection.current_active_range
        range_x, range_y, range_width, range_height = self.auto_adjust_selection_range(arange.x,
                                                                                       arange.y,
                                                                                       arange.width,
                                                                                       arange.height,
                                                                                       width,
                                                                                       height,
                                                                                       display)

        # Clipping for when the user selects the entire row(s). You may notice that
        # I didn't adjust the width and height as it's not worth the complexity.
        if arange.column == 0:
            context.rectangle(-1, display.top_locator_height - 1, width, height)
            context.clip()
        # Clipping for when the user selects the entire column(s)
        if arange.row == 0:
            context.rectangle(display.left_locator_width - 1, -1, width, height)
            context.clip()
        # Clipping for general use cases
        if arange.column > 0 and arange.row > 0:
            context.rectangle(display.left_locator_width - 1, display.top_locator_height - 1, width, height)
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
        if arange.column > 0 and arange.row == 0:
            context.reset_clip()
            context.rectangle(0, display.top_locator_height, display.left_locator_width, height)
            context.fill()

        # Indicates that the user has selected the entire row(s) by highlighting all the column headers
        if arange.column == 0 and arange.row > 0:
            context.reset_clip()
            context.rectangle(display.left_locator_width, 0, width, display.top_locator_height)
            context.fill()

        # Indicates that the user has a selection by highlighting the row and column header(s)
        if arange.column > 0 and arange.row > 0:
            context.reset_clip()
            context.rectangle(display.left_locator_width - 1, 0, width, height)
            context.clip()
            context.rectangle(range_x, 0, range_width, display.top_locator_height)
            context.fill()

            context.reset_clip()
            context.rectangle(0, display.top_locator_height - 1, width, height)
            context.clip()
            context.rectangle(0, range_y, display.left_locator_width, range_height)
            context.fill()

        # We want more emphasis for when the user has selected column(s), row(s), or even the entire sheet,
        # so we'll increase the opacity again
        accent_rgba[3] = 1.0
        context.set_source_rgba(*accent_rgba)

        # Bold highlight all the headers if the user has selected the entire sheet
        if arange.column == 0 and arange.row == 0:
            context.reset_clip()
            context.rectangle(display.left_locator_width, range_y, width, display.top_locator_height)
            context.rectangle(range_x, display.top_locator_height, display.left_locator_width, range_height)
            context.fill()

        # Bold highlight the selected column(s) header
        if arange.column > 0 and arange.row == 0:
            context.reset_clip()
            context.rectangle(display.left_locator_width - 1, -1, width, height)
            context.clip()
            context.rectangle(range_x, range_y, range_width, display.top_locator_height)
            context.fill()

        # Bold highlight the selected row(s) header
        if arange.column == 0 and arange.row > 0:
            context.reset_clip()
            context.rectangle(-1, display.top_locator_height - 1, width, height)
            context.clip()
            context.rectangle(range_x, range_y, display.left_locator_width, range_height)
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
        context.rectangle(display.left_locator_width - 1, display.top_locator_height - 1, width, height)
        context.clip()
        context.rectangle(cell.x, cell.y, cell.width, cell.height)
        context.fill()

        context.restore()

    def draw_headers_contents(self,
                              canvas:  Gtk.DrawingArea,
                              context: cairo.Context,
                              width:   int,
                              height:  int,
                              display: SheetDisplay,
                              data:    SheetData) -> None:
        context.save()

        # Monospace is the best in my opinion for the headers, especially when it comes to the row headers
        # which are numbers so that it can be easier to read because of the good visual alignment.
        header_font_desc = Pango.font_description_from_string(f'Monospace Normal Bold {display.FONT_SIZE}px')
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(header_font_desc)

        # Use system default font family for drawing text
        body_font_desc = Gtk.Widget.create_pango_context(canvas).get_font_description()
        body_font_family = body_font_desc.get_family() if body_font_desc else 'Sans'
        body_font_desc = Pango.font_description_from_string(f'{body_font_family} Normal Bold {display.FONT_SIZE}px')

        # We should achieve the high contrast between the text and the canvas background, though I'm aware
        # of the potential problems with using the pure black and white colors. Let's decide that later.
        text_color = (0.0, 0.0, 0.0)
        if self.prefers_dark:
            text_color = (1.0, 1.0, 1.0)
        context.set_source_rgb(*text_color)

        context.save()
        context.rectangle(display.left_locator_width, 0, width, height)
        context.clip()

        # Draw column headers texts (centered)
        # It's so rare to see a worksheet go beyond Z*9 columns, but it's better to be prepared for it anyway
        # by having defining the clip region to prevent the text from overflowing to the next cells. TODO: maybe
        # it's better to automatically adjust the cell widths to fit the text width if the text is overflowing?
        col_index = display.get_starting_column()
        x = display.get_cell_x_from_column(col_index)

        while x < width:
            vcol_index = display.get_vcolumn_from_column(col_index)
            cell_width = display.get_cell_width_from_column(col_index)

            # Draw dataframe header
            # TODO: support multiple dataframes?
            if len(data.bbs) \
                    and 0 < display.scroll_y_position \
                    and col_index <= data.bbs[0].column_span:
                cname = data.dfs[0].columns[vcol_index - 1]
                dtype = utils.get_dtype_symbol(data.dfs[0].dtypes[vcol_index - 1])
                layout.set_font_description(body_font_desc)
                layout.set_text(f'{cname} [{dtype}]', -1)
                x_text = x + display.DEFAULT_CELL_PADDING

            # Draw column name
            else:
                cell_text = display.get_column_name_from_column(vcol_index)
                layout.set_font_description(header_font_desc)
                layout.set_text(cell_text, -1)
                text_width = layout.get_size()[0] / Pango.SCALE
                x_text = x + (cell_width - text_width) / 2

            context.save()
            context.rectangle(x, 0, cell_width - 1, display.top_locator_height)
            context.clip()
            context.move_to(x_text, 2)
            PangoCairo.show_layout(context, layout)
            context.restore()

            x += cell_width
            col_index += 1

        context.restore()

        layout.set_font_description(header_font_desc)

        # Draw row headers texts (right-aligned)
        # Here we don't necessarily need the clip region because the row headers are usually if not always
        # readjusted before even moving to the rendering process.
        row_index = display.get_starting_row()
        y = display.get_cell_y_from_row(row_index)

        while y < height:
            cell_text = display.get_vrow_from_row(row_index)
            layout.set_text(str(cell_text), -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            x = display.left_locator_width - text_width - display.DEFAULT_CELL_PADDING

            context.move_to(x, 2 + y)
            PangoCairo.show_layout(context, layout)

            y += display.get_cell_height_from_row(row_index)
            row_index += 1

        context.restore()

    def draw_cells_contents(self,
                            canvas:  Gtk.DrawingArea,
                            context: cairo.Context,
                            width:   int,
                            height:  int,
                            display: SheetDisplay,
                            data:    SheetData) -> None:
        if len(data.dfs) == 0:
            return

        # Drawing loop boundaries
        x_start = display.left_locator_width
        y_start = display.top_locator_height
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
                'x_trans': 0,
                'y_trans': 0,
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
            if abs(x_offset) < width and \
                    abs(y_offset) < height and \
                    (abs(x_offset) > 0 and y_offset == 0) or \
                    (abs(y_offset) > 0 and x_offset == 0):
                # When the user scrolls the canvas to the right
                if x_offset > 0:
                    nx_start = display.get_cell_x_from_point(width - x_offset)
                    cwidth = nx_start - x_start
                    ncontext.rectangle(x_start, y_start, cwidth, y_end)

                # When the user scrolls the canvas to the left
                elif x_offset < 0:
                    nx_end = display.get_cell_x_from_point(x_start - x_offset)
                    cwidth = display.get_cell_width_from_point(x_start - x_offset)
                    ncontext.rectangle(nx_end + cwidth, y_start, x_end, y_end)

                    col_index = display.get_starting_column()
                    x = display.get_cell_x_from_column(col_index)
                    nx_start = x

                # When the user scrolls the canvas down
                if y_offset > 0:
                    ny_start = display.get_cell_y_from_point(height - y_offset)
                    cheight = ny_start - y_start
                    ncontext.rectangle(x_start, y_start, x_end, cheight)

                # When the user scrolls the canvas up
                elif y_offset < 0:
                    ny_end = display.get_cell_y_from_point(y_start - y_offset, -1)
                    cheight = display.get_cell_height_from_point(y_start - y_offset)
                    ncontext.rectangle(x_start, ny_end + cheight, x_end, y_end)

                    row_index = display.get_starting_row()
                    y = display.get_cell_y_from_row(row_index)
                    ny_start = y

                ncontext.translate(rcache['x_trans'], rcache['y_trans'])
                ncontext.clip()
                ncontext.set_source_surface(rcache['surface'], -x_offset, -y_offset)
                ncontext.paint()
                ncontext.reset_clip()
                ncontext.translate(-rcache['x_trans'], -rcache['y_trans'])

                rcache['x_trans'] = 0
                rcache['y_trans'] = 0

            ccontext = ncontext
            rcache['surface'] = nsurface
            rcache['x_pos'] = display.scroll_x_position
            rcache['y_pos'] = display.scroll_y_position

        self.setup_cairo_context(ccontext)

        # Use system default font family for drawing text
        font_desc = Gtk.Widget.create_pango_context(canvas).get_font_description()
        font_family = font_desc.get_family() if font_desc else 'Sans'
        header_font_desc = Pango.font_description_from_string(f'{font_family} Normal Bold {display.FONT_SIZE}px #tnum=1')
        body_font_desc = Pango.font_description_from_string(f'{font_family} Normal Regular {display.FONT_SIZE}px #tnum=1')

        layout = PangoCairo.create_layout(ccontext)

        ccontext.save()
        ccontext.rectangle(x_start, y_start, x_end, y_end)
        ccontext.clip()

        # We use the same color scheme as the headers
        if self.prefers_dark:
            ccontext.set_source_rgb(1.0, 1.0, 1.0)
        else:
            ccontext.set_source_rgb(0.0, 0.0, 0.0)

        col_index = display.get_starting_column()
        x = display.get_cell_x_from_column(col_index)

        if not use_cache:
            nx_start = x

        # TODO: support multiple dataframes?
        while x < x_end:
            if data.bbs[0].column_span < col_index:
                width = x # prevent iteration over empty cells
                break

            vcol_index = display.get_vcolumn_from_column(col_index)
            cell_width = display.get_cell_width_from_column(col_index)

            ccontext.save()
            ccontext.rectangle(x, display.top_locator_height, cell_width - 1, height)
            ccontext.clip()

            row_index = display.get_starting_row()
            y = display.get_cell_y_from_row(row_index)

            while y < y_end:
                vrow_index = display.get_vrow_from_row(row_index)
                cell_height = display.get_cell_height_from_row(row_index)

                if y < ny_start \
                        or ny_end < y \
                        or x < nx_start \
                        or nx_end < x:
                    y += cell_height
                    row_index += 1
                    continue # skip cached area

                if data.bbs[0].row_span < row_index:
                    height = y
                    break # prevent iteration over empty cells

                x_text = x + display.DEFAULT_CELL_PADDING

                # Draw dataframe header
                if vrow_index == 1:
                    layout.set_font_description(header_font_desc)
                    cname = data.dfs[0].columns[vcol_index - 1]
                    dtype = utils.get_dtype_symbol(data.dfs[0].dtypes[vcol_index - 1])
                    cell_text = f'{cname} [{dtype}]'
                    layout.set_text(cell_text, -1)

                # Draw dataframe content
                else:
                    layout.set_font_description(body_font_desc)
                    cell_text = data.dfs[0][vrow_index - 2, vcol_index - 1]
                    col_dtype = data.dfs[0].dtypes[vcol_index - 1]

                    if cell_text in ['', None]:
                        y += cell_height
                        row_index += 1
                        continue # skip empty cells

                    # Right-align numeric and temporal values
                    if col_dtype.is_numeric() or col_dtype.is_temporal():
                        cell_text = str(cell_text)
                        layout.set_text(cell_text, -1)
                        text_width = layout.get_size()[0] / Pango.SCALE
                        x_text = x + cell_width - text_width - display.DEFAULT_CELL_PADDING

                    # Otherwise keep it left-aligned
                    else:
                        # Truncate before the first line break to prevent overflow
                        cell_text = str(cell_text).split('\n', 1)[0]
                        # Truncate the contents for performance reasons
                        cell_text = cell_text[:int(cell_width * 0.2)] # TODO: 0.2 is a magic number
                        layout.set_text(cell_text, -1)

                ccontext.move_to(x_text, y + 2)
                PangoCairo.show_layout(ccontext, layout)

                y += cell_height
                row_index += 1

            x += cell_width
            col_index += 1

            ccontext.restore()

        ccontext.restore()

        context.set_source_surface(rcache['surface'], 0, 0)
        context.paint()

    def draw_cells_borders(self,
                           context: cairo.Context,
                           width:   int,
                           height:  int,
                           display: SheetDisplay) -> None:
        context.save()

        # We need to make sure that the cell borders are contrast enough to the canvas background
        if self.prefers_dark:
            context.set_source_rgb(0.25, 0.25, 0.25)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)

        # I bet this is better than a thick line!
        context.set_hairline(True)

        x_start = display.left_locator_width
        y_start = display.top_locator_height

        # Draw separator line between headers and contents
        context.move_to(0, y_start)
        context.line_to(width, y_start)
        context.move_to(x_start, 0)
        context.line_to(x_start, height)
        context.stroke()

        # Draw horizontal lines
        context.reset_clip()
        context.rectangle(0, display.top_locator_height, width, height)
        context.clip()

        nrow_index = display.get_starting_row()
        prow_index = nrow_index

        y = display.get_cell_y_from_row(nrow_index)

        # Prevent showing double lines at the first row when the logical cell
        # right above it is visible
        if nrow_index > 1:
            vrow_index = display.get_vrow_from_row(nrow_index)
            if display.check_cell_visibility_from_position(vrow_index - 1, -1):
                prow_index = vrow_index

        while y < width:
            vrow_index = display.get_vrow_from_row(nrow_index)
            hidden_row_exists = prow_index != vrow_index

            if hidden_row_exists:
                prow_index = vrow_index

            double_lines = hidden_row_exists

            # Draw line(s) in the locator area
            if double_lines:
                context.move_to(0, y - 2)
                context.line_to(x_start, y - 2)
                context.move_to(0, y + 2)
                context.line_to(x_start, y + 2)
            else:
                context.move_to(0, y)
                context.line_to(x_start, y)

            # Draw line in the content area
            context.move_to(x_start, y)
            context.line_to(width, y)

            y += display.get_cell_height_from_row(nrow_index)
            nrow_index += 1
            prow_index += 1

        context.stroke()

        # Draw vertical lines
        context.reset_clip()
        context.rectangle(display.left_locator_width, 0, width, height)
        context.clip()

        ncol_index = display.get_starting_column()
        pcol_index = ncol_index

        x = display.get_cell_x_from_column(ncol_index)

        # Prevent showing double lines at the first column when the logical cell
        # right before it is visible
        if ncol_index > 1:
            vcol_index = display.get_vcolumn_from_column(ncol_index)
            if display.check_cell_visibility_from_position(vcol_index - 1, -1):
                pcol_index = vcol_index

        while x < width:
            vcol_index = display.get_vcolumn_from_column(ncol_index)
            hidden_column_exists = pcol_index != vcol_index

            if hidden_column_exists:
                pcol_index = vcol_index

            double_lines = hidden_column_exists

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

            x += display.get_cell_width_from_column(ncol_index)
            ncol_index += 1
            pcol_index += 1

        context.stroke()

        context.restore()

    def draw_selection_overlay(self,
                               context:   cairo.Context,
                               width:     int,
                               height:    int,
                               display:   SheetDisplay,
                               selection: SheetSelection) -> None:
        context.save()

        cutcopy_range = selection.current_cutcopy_range
        if cutcopy_range is not None \
                and (display.document.is_cutting_cells or
                     display.document.is_copying_cells):
            cutcopy_range_x, \
            cutcopy_range_y, \
            cutcopy_range_width, \
            cutcopy_range_height = self.auto_adjust_selection_range(cutcopy_range.x,
                                                                    cutcopy_range.y,
                                                                    cutcopy_range.width,
                                                                    cutcopy_range.height,
                                                                    width,
                                                                    height,
                                                                    display)

        # Render the cut frontground
        if display.document.is_cutting_cells and cutcopy_range is not None:
            context.save()
            if self.prefers_dark:
                context.set_source_rgba(0.13, 0.13, 0.15, 0.5)
            else:
                context.set_source_rgba(0.98, 0.98, 0.98, 0.5)
            context.rectangle(cutcopy_range_x, cutcopy_range_y, cutcopy_range_width, cutcopy_range_height)
            context.fill()
            context.restore()

        context.restore()

    def draw_selection_borders(self,
                               context:   cairo.Context,
                               width:     int,
                               height:    int,
                               display:   SheetDisplay,
                               selection: SheetSelection) -> None:
        context.save()

        arange = selection.current_active_range
        range_x, range_y, range_width, range_height = self.auto_adjust_selection_range(arange.x,
                                                                                       arange.y,
                                                                                       arange.width,
                                                                                       arange.height,
                                                                                       width,
                                                                                       height,
                                                                                       display)

        search_range = selection.current_search_range
        if display.document.is_searching_cells and search_range is not None:
            search_range_x, \
            search_range_y, \
            search_range_width, \
            search_range_height = self.auto_adjust_selection_range(search_range.x,
                                                                   search_range.y,
                                                                   search_range.width,
                                                                   search_range.height,
                                                                   width,
                                                                   height,
                                                                   display)

        cutcopy_range = selection.current_cutcopy_range
        if (display.document.is_cutting_cells or display.document.is_copying_cells) and cutcopy_range is not None:
            cutcopy_range_x, \
            cutcopy_range_y, \
            cutcopy_range_width, \
            cutcopy_range_height = self.auto_adjust_selection_range(cutcopy_range.x,
                                                                    cutcopy_range.y,
                                                                    cutcopy_range.width,
                                                                    cutcopy_range.height,
                                                                    width,
                                                                    height,
                                                                    display)

        # Clipping for when the user selects the entire row(s). You may notice that
        # I didn't adjust the width and height as it's not worth the complexity.
        if arange.column == 0:
            context.rectangle(0, display.top_locator_height - 1, width, height)
            context.clip()
        # Clipping for when the user selects the entire column(s)
        if arange.row == 0:
            context.rectangle(display.left_locator_width - 1, 0, width, height)
            context.clip()
        # Clipping for general use cases
        if arange.column > 0 and arange.row > 0:
            context.rectangle(display.left_locator_width - 1, display.top_locator_height - 1, width, height)
            context.clip()

        # We use a bold style here
        context.set_source_rgba(*self.color_accent)
        context.set_line_width(2)

        # Indicates that the user has selected the entire column(s) by drawing a vertical line
        # next to the row headers
        if arange.column > 0 and arange.row == 0:
            context.move_to(display.left_locator_width, display.top_locator_height - 1)
            context.line_to(display.left_locator_width, height)
            context.stroke()

        # Indicates that the user has selected the entire row(s) by drawing a horizontal line
        # next to the column headers
        if arange.column == 0 and arange.row > 0:
            context.move_to(display.left_locator_width - 1, display.top_locator_height)
            context.line_to(width, display.top_locator_height)
            context.stroke()

        # Indicates that the user has a selection by drawing a line next to the row and column header(s)
        if arange.column > 0 and arange.row > 0:
            context.move_to(range_x, display.top_locator_height)
            context.line_to(range_x + range_width, display.top_locator_height)
            context.move_to(display.left_locator_width, range_y)
            context.line_to(display.left_locator_width, range_y + range_height)
            context.stroke()

        # Don't render the active selection when the user selects the entire sheet
        if not (range_x == 0 and range_y == 0) and not globals.is_editing_cells:
            context.rectangle(range_x, range_y, range_width - 1, range_height - 1)
            context.stroke()

        context.reset_clip()
        context.rectangle(display.left_locator_width - 1, 0, width, height)
        context.clip()

        context.set_line_width(1)

        # Render the search range
        if display.document.is_searching_cells and search_range is not None:
            context.save()
            context.rectangle(search_range_x, search_range_y, search_range_width, search_range_height)
            context.stroke()
            if self.prefers_dark:
                context.set_source_rgb(0.13, 0.13, 0.15)
            else:
                context.set_source_rgb(0.98, 0.98, 0.98)
            context.set_dash([4, 4], 0)
            if search_range_width > 0 and search_range_height > 0:
                context.rectangle(search_range_x, search_range_y, search_range_width, search_range_height)
                context.stroke()
            context.restore()

        # Render the cut/copy range
        if (display.document.is_cutting_cells or display.document.is_copying_cells) and cutcopy_range is not None:
            context.save()
            context.rectangle(cutcopy_range_x, cutcopy_range_y, cutcopy_range_width, cutcopy_range_height)
            context.stroke()
            if self.prefers_dark:
                context.set_source_rgb(0.13, 0.13, 0.15)
            else:
                context.set_source_rgb(0.98, 0.98, 0.98)
            context.set_dash([4, 4], time() * 30)
            if cutcopy_range_width > 0 and cutcopy_range_height > 0:
                context.rectangle(cutcopy_range_x, cutcopy_range_y, cutcopy_range_width, cutcopy_range_height)
                context.stroke()
            context.restore()

        context.restore()

    def draw_virtual_widgets(self,
                             context: cairo.Context,
                             width:   int,
                             height:  int,
                             display: SheetDisplay,
                             widgets: list[SheetWidget]) -> None:
        context.save()

        context.set_antialias(cairo.Antialias.DEFAULT)

        for widget in widgets:
            # Check if the widget will be visible, otherwise skip it
            if widget.get_x() + widget.get_width() < display.scroll_x_position \
                    or widget.get_y() + widget.get_height() < display.scroll_y_position \
                    or display.scroll_x_position + width < widget.get_x() \
                    or display.scroll_y_position + height < widget.get_y():
                continue

            context.save()
            widget.do_render(context, width, height, self.prefers_dark, self.color_accent)
            context.restore()

        context.restore()

    def auto_adjust_selection_range(self,
                                    range_x:      int,
                                    range_y:      int,
                                    range_width:  int,
                                    range_height: int,
                                    width:        int,
                                    height:       int,
                                    display:      SheetDisplay) -> tuple[int, int, int, int]:
            # Hide the top of the selection if it is exceeded by the scroll viewport
            if range_y < 0:
                range_height += range_y
                range_y = display.top_locator_height
                range_height -= display.top_locator_height
            # Hide the entire selection if it is exceeded by the scroll viewport
            if range_height < 0:
                range_height = 0
            # Hide the entire selection if the viewport has not reached it yet
            if height < range_y:
                range_y = height + 1
                range_height = 0
            # Hide the bottom of the selection if it is not yet in the viewport
            if height < range_y + range_height:
                range_height = height - range_y

            # Hide the left of the selection if it is exceeded by the scroll viewport
            if range_x < 0:
                range_width += range_x
                range_x = display.left_locator_width
                range_width -= display.left_locator_width
            # Hide the entire selection if it is exceeded by the scroll viewport
            if range_width < 0:
                range_width = 0
            # Hide the entire selection if the viewport has not reached it yet
            if width < range_x:
                range_x = width + 1
                range_width = 0
            # Hide the right of the selection if it is not yet in the viewport
            if width < range_x + range_width:
                range_width = width - range_x

            return range_x, range_y, range_width, range_height