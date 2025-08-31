# sheet_widget.py
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

from gi.repository import Gdk, GObject, Gtk, Pango, PangoCairo
import cairo

from . import utils
from .sheet_data import SheetData
from .sheet_display import SheetDisplay

class SheetWidget(GObject.Object):
    __gtype_name__ = 'SheetWidget'

    def __init__(self,
                 x:       int,
                 y:       int,
                 width:   int,
                 height:  int,
                 display: SheetDisplay) -> None:
        super().__init__()

        self.x = x
        self.y = y

        self.width = width
        self.height = height

        self.display = display

        self.position: str = 'relative'

        self.cursor: Gdk.Cursor = Gdk.Cursor.new_from_name('default')

    def get_x(self) -> int:
        if self.position == 'absolute':
            return self.x + self.display.scroll_x_position
        return self.x

    def get_y(self) -> int:
        if self.position == 'absolute':
            return self.y + self.display.scroll_y_position
        return self.y

    def get_rx(self) -> int:
        return self.x

    def get_ry(self) -> int:
        return self.y

    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height

    def contains(self, x: int, y: int) -> bool:
        return self.get_rx() <= x <= self.get_rx() + self.width and \
               self.get_ry() <= y <= self.get_ry() + self.height

    def do_on_enter(self, x: int, y: int) -> bool:
        return False # should interrupt mouse event

    def do_on_leave(self, x: int, y: int) -> bool:
        return False # should interrupt mouse event

    def do_on_pressed(self, x: int, y: int) -> bool:
        return False # should interrupt mouse event

    def do_on_released(self, x: int, y: int) -> bool:
        return False # should interrupt mouse event

    def do_on_dragged(self, x: int, y: int) -> bool:
        return False # should interrupt mouse event

    def do_render(self,
                  context:      cairo.Context,
                  width:        int,
                  height:       int,
                  prefers_dark: bool,
                  color_accent: tuple[float, float, float, float]) -> None:
        if self.position == 'relative':
            context.translate(-self.display.scroll_x_position, -self.display.scroll_y_position)



class SheetAutoFilter(SheetWidget):
    __gtype_name__ = 'SheetAutoFilter'

    def __init__(self,
                 x:          int,
                 y:          int,
                 width:      int,
                 height:     int,
                 display:    SheetDisplay,
                 on_clicked: callable) -> None:
        super().__init__(x, y, width, height, display)

        self.on_clicked = on_clicked

        self.position = 'absolute'

        self.cursor = Gdk.Cursor.new_from_name('pointer', Gdk.Cursor.new_from_name('default'))

    def get_x(self) -> int:
        return self.x

    def get_rx(self) -> int:
        return self.x - self.display.scroll_x_position

    def get_ry(self) -> int:
        if self.display.scroll_y_position > 0:
            return self.y - self.display.top_locator_height
        return self.y

    def contains(self, x: int, y: int) -> bool:
        if x < self.display.left_locator_width:
            return False
        return self.get_rx() <= x <= self.get_rx() + self.width and \
               self.get_ry() <= y <= self.get_ry() + self.height

    def do_on_pressed(self, x: int, y: int) -> bool:
        self.on_clicked(x, y)
        return False

    def do_render(self,
                  context:      cairo.Context,
                  width:        int,
                  height:       int,
                  prefers_dark: bool,
                  color_accent: tuple[float, float, float, float]) -> None:
        context.rectangle(self.display.left_locator_width, 0, width, height)
        context.clip()

        x = self.get_rx()
        y = self.get_ry()

        background_color = (1.0, 1.0, 1.0)
        if prefers_dark:
            background_color = (0.13, 0.13, 0.15)

        context.set_source_rgb(*background_color)

        # Draw the background fill
        context.rectangle(x, y, self.width, self.height)
        context.fill()

        stroke_color = (0.0, 0.0, 0.0)
        if prefers_dark:
            stroke_color = (1.0, 1.0, 1.0)

        context.set_source_rgb(*stroke_color)
        context.set_hairline(True)

        # Draw the left diagonal line
        start_x = x + 5
        start_y = y + 7
        end_x = x + self.width / 2
        end_y = y + self.height - 7
        context.move_to(start_x, start_y)
        context.line_to(end_x, end_y)

        # Draw the right diagonal line
        start_x = x + self.width / 2
        start_y = y + self.height - 7
        end_x = x + self.width - 5
        end_y = y + 7
        context.move_to(start_x, start_y)
        context.line_to(end_x, end_y)

        context.stroke()

        # stroke_color = (0.75, 0.75, 0.75)
        # if prefers_dark:
        #     stroke_color = (0.25, 0.25, 0.25)

        # context.set_source_rgb(*stroke_color)
        # context.set_antialias(cairo.Antialias.NONE)

        # # Draw the border line
        # context.rectangle(x, y, self.width, self.height)
        # context.stroke()



class SheetColumnResizer(SheetWidget):
    __gtype_name__ = 'SheetColumnResizer'

    def __init__(self,
                 x:           int,
                 y:           int,
                 width:       int,
                 height:      int,
                 display:     SheetDisplay,
                 data:        SheetData,
                 on_hovered:  callable,
                 on_released: callable) -> None:
        super().__init__(x, y, width, height, display)

        self.data = data

        self.on_hovered = on_hovered
        self.on_released = on_released

        self.position = 'absolute'

        self.cursor = Gdk.Cursor.new_from_name('ew-resize')

        self.is_hovered = False
        self.is_clicked = False

        self.target_cell_x = 0
        self.target_cell_width = 0
        self.target_column = 0
        self.new_cell_width = 0
        self.handler_x = 0
        self.x_offset = 0

    def contains(self, x: int, y: int) -> bool:
        cell_x = self.display.get_cell_x_from_point(x)
        cell_width = self.display.get_cell_width_from_point(x)

        left_1 = cell_x
        left_2 = cell_x + (self.width / 2)

        right_1 = cell_x + cell_width - (self.width / 2)
        right_2 = cell_x + cell_width

        left_hovered = left_1 <= x <= left_2
        right_hovered = right_1 <= x <= right_2

        if x <= self.display.left_locator_width \
                or (left_hovered and cell_x <= self.display.left_locator_width):
            return False

        # Move the widget to around the left/right edge of the current cell
        self.x = cell_x if left_hovered else cell_x + cell_width

        # Store the x coordinate of the current cell to set the left boundary of
        # the handle, so that it always appears to the right of the current cell.
        self.target_column = self.display.get_starting_column(x) - 1
        self.target_cell_x = cell_x

        # Re-calculating the left boundary for the handle. When left_hovered is True,
        # it means that the cursor is around the left edge of the cell. We assume that
        # that the user wants to resize the cell on the left of the current cell. Thus
        # we need to get the x coordinate of the left sibling cell instead.
        if left_hovered:
            previous_cell_x = self.display.get_cell_x_from_column(self.target_column)
            self.target_cell_x = previous_cell_x

        self.target_cell_width = self.display.get_cell_width_from_column(self.target_column)
        self.handler_x = self.target_cell_x + self.target_cell_width

        return (left_hovered or right_hovered) and \
               0 <= y <= self.display.top_locator_height

    def do_on_enter(self, x: int, y: int) -> bool:
        if self.is_clicked:
            return False

        self.is_hovered = True
        self.on_hovered()

        self.new_cell_width = self.handler_x - self.target_cell_x
        self.x_offset = self.new_cell_width - self.target_cell_width

        return False

    def do_on_leave(self, x: int, y: int) -> bool:
        self.is_hovered = False

        if self.is_clicked:
            return False

        self.on_hovered()
        return False

    def do_on_pressed(self, x: int, y: int) -> bool:
        self.is_hovered = False
        self.is_clicked = True
        self.on_hovered()
        return True

    def do_on_released(self, x: int, y: int) -> bool:
        self.is_clicked = False
        self.on_released(self.target_column, self.new_cell_width)
        return True

    def do_on_dragged(self, x: int, y: int) -> bool:
        self.x = x
        self.on_hovered()

        self.handler_x = max(max(self.x, self.target_cell_x), self.display.left_locator_width)
        self.new_cell_width = self.handler_x - self.target_cell_x
        self.x_offset = self.new_cell_width - self.target_cell_width

        return True

    def do_render(self,
                  context:      cairo.Context,
                  width:        int,
                  height:       int,
                  prefers_dark: bool,
                  color_accent: tuple[float, float, float, float]) -> None:
        if not self.is_hovered and not self.is_clicked:
            return # skip if not hovered

        context.set_antialias(cairo.Antialias.NONE)

        if self.is_clicked:
            # We want to re-draw the top locator to show how it'll look if the user resizes the current cell.
            # This approach is already quite efficient and doesn't seem too complicated, maybe?
            new_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, self.display.top_locator_height + 1)
            new_context = cairo.Context(new_surface)
            new_context.set_source_surface(context.get_target(), self.x_offset, 0)
            new_context.paint()

            # We copied some part of the code below from sheet_renderer.py
            self.draw_headers_backgrounds(context, width, prefers_dark)
            self.draw_selection_backgrounds(context, width, height, color_accent)
            self.draw_headers_contents(context, width, prefers_dark)
            self.draw_cells_borders(context, width, prefers_dark)
            self.draw_selection_borders(context, width, color_accent)

            context.save()
            context.rectangle(self.handler_x - 1,
                              0,
                              width - self.handler_x + 1,
                              self.display.top_locator_height + 1)
            context.clip()
            context.set_source_surface(new_surface, 0, 0)
            context.paint()
            context.restore()

            # TODO: should we manually render the autofilter widget for the target column
            #       if it's applicable? Currently, it's being overdrawn by the previous steps.

            self.draw_vertical_line(context, height, color_accent)

        self.draw_resize_handler(context, prefers_dark)

        context.set_antialias(cairo.Antialias.DEFAULT)

        if self.x_offset < 0:
            self.draw_diagonal_lines_pattern(context, width, prefers_dark)

    def draw_resize_handler(self,
                            context: cairo.Context,
                            prefers_dark: bool) -> None:
        context.save()

        x = self.handler_x
        y = self.get_ry()

        background_color = (0.0, 0.0, 0.0)
        if prefers_dark:
            background_color = (1.0, 1.0, 1.0)

        context.set_source_rgb(*background_color)

        # Draw the handle fill
        context.rectangle(x - self.width / 2,
                          y,
                          self.width,
                          self.height)
        context.fill()

        stroke_color = (1.0, 1.0, 1.0)
        if prefers_dark:
            stroke_color = (0.0, 0.0, 0.0)

        context.set_source_rgb(*stroke_color)
        context.set_hairline(True)

        # Draw a line in the middle
        context.move_to(x, y + 2)
        context.line_to(x, y + self.height - 2)
        context.stroke()

        context.restore()

    def draw_vertical_line(self,
                           context:      cairo.Context,
                           height:       int,
                           color_accent: tuple[float, float, float, float]) -> None:
        context.save()

        x = self.handler_x

        context.set_source_rgba(*color_accent)
        context.set_line_width(2)
        context.set_dash([4, 4], 0)

        context.move_to(x, 0)
        context.line_to(x, height)
        context.stroke()

        context.restore()

    def draw_headers_backgrounds(self,
                                 context:      cairo.Context,
                                 width:        int,
                                 prefers_dark: bool) -> None:
        context.save()

        # I don't want this class to access the data directly,
        # but well I have no alternative solution right now.
        selection = self.display.document.selection
        arange = selection.current_active_range

        # Flag this as a TODO for now following the sheet_renderer,
        # as this code is copied from there.
        if prefers_dark:
            context.set_source_rgb(0.13, 0.13, 0.15)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

        x = max(self.target_cell_x, self.display.left_locator_width)

        rcolumn_span = arange.column_span

        mdfi = arange.metadata.dfi
        bbox = self.data.bbs[mdfi]

        if arange.column_span < 0:
            rcolumn_span = bbox.column_span + 1

        # Take hidden column(s) into account
        start_vcolumn = self.display.get_vcolumn_from_column(arange.column)
        end_vcolumn = self.display.get_vcolumn_from_column(arange.column + rcolumn_span - 1)
        rcolumn_span = end_vcolumn - start_vcolumn + 1

        if arange.column_span < 0:
            rcolumn_span -= 1

        # Adjust the rectangle position for the specific condition
        # based on pixel perfect calculation
        if arange.column + rcolumn_span - 1 < self.target_column \
                or arange.x <= self.display.left_locator_width:
            x += 1

        context.rectangle(x,
                          0,
                          width - x,
                          self.display.top_locator_height - 1)
        context.fill()

        context.restore()

    def draw_selection_backgrounds(self,
                                   context:      cairo.Context,
                                   width:        int,
                                   height:       int,
                                   color_accent: tuple[float, float, float, float]) -> None:
        context.save()

        # I don't want this class to access the data directly,
        # but well I have no alternative solution right now.
        selection = self.display.document.selection

        # range_x and range_y were adjusted by the sheet document, so now they are relative to the top
        # of the viewport, meaning they'll be negative if the user scrolled down. The calculations below
        # is only for optimization purposes or to handle the case where the selection size is too big so
        # that it can only be partially drawn.
        arange = selection.current_active_range

        range_x = arange.x
        range_y = arange.y

        range_width = arange.width

        range_row = arange.row
        range_column = arange.column
        rcolumn_span = arange.column_span

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

        mdfi = arange.metadata.dfi
        bbox = self.data.bbs[mdfi]

        if arange.column_span < 0:
            rcolumn_span = bbox.column_span + 1

        # Take hidden column(s) into account
        start_vcolumn = self.display.get_vcolumn_from_column(range_column)
        end_vcolumn = self.display.get_vcolumn_from_column(range_column + rcolumn_span - 1)
        rcolumn_span = end_vcolumn - start_vcolumn + 1

        if arange.column_span < 0:
            rcolumn_span -= 1

        # Only draw the selection if the target column is within the selection
        if 0 < rcolumn_span and \
                (range_column + rcolumn_span <= self.target_column or
                 self.target_column < range_column):
            return

        # Adjust the range if necessary to prevent from drawing over translucent cells
        column_in_range = range_column <= self.target_column <= range_column + rcolumn_span - 1
        if column_in_range or rcolumn_span == -1:
            range_x = max(range_x, self.target_cell_x)
            range_width = max(range_width, self.new_cell_width)

        # Reduces the opacity of the accent color so that it doesn't look too bright,
        # we try to imitate the behavior of other applications.
        accent_rgba = list(color_accent)
        accent_rgba[3] = 0.2
        context.set_source_rgba(*accent_rgba)

        # Indicates that the user has selected the entire row(s) by highlighting all the column headers
        if range_column == 0:
            context.reset_clip()
            context.rectangle(range_x, 0, width, self.display.top_locator_height - 1)
            context.fill()

        # Indicates that the user has a selection by highlighting the column header(s)
        if range_column > 0:
            context.reset_clip()
            context.rectangle(self.display.left_locator_width, 0, width, height)
            context.clip()
            context.rectangle(range_x, 0, range_width, self.display.top_locator_height - 1)
            context.fill()

        # We want more emphasis for when the user has selected column(s), row(s), or even the entire sheet,
        # so we'll increase the opacity again
        accent_rgba[3] = 1.0
        context.set_source_rgba(*accent_rgba)

        # Bold highlight all the column headers if the user has selected the entire sheet
        if range_column == 0 and range_row == 0:
            context.reset_clip()
            context.rectangle(range_x, range_y, width, self.display.top_locator_height - 1)
            context.fill()

        # Bold highlight the selected column(s) header
        if range_column > 0 and range_row == 0:
            context.reset_clip()
            context.rectangle(self.display.left_locator_width, -1, width, height)
            context.clip()
            context.rectangle(range_x, range_y, range_width, self.display.top_locator_height - 1)
            context.fill()

        context.restore()

    def draw_cells_borders(self,
                           context:      cairo.Context,
                           width:        int,
                           prefers_dark: bool) -> None:
        context.save()

        # I don't want this class to access the data directly,
        # but well I have no alternative solution right now.
        selection = self.display.document.selection
        arange = selection.current_active_range

        # We need to make sure that the cell borders are contrast enough to the canvas background
        if prefers_dark:
            context.set_source_rgb(0.25, 0.25, 0.25)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)

        context.set_hairline(True)

        x_start = self.display.left_locator_width
        y_start = self.display.top_locator_height

        # Draw separator line between headers and contents for the specific condition
        # based on pixel perfect calculation
        if arange.column > 0 and arange.row > 0:
            context.move_to(x_start, 0)
            context.line_to(x_start, y_start - 1)

        x_start = max(self.target_cell_x, self.display.left_locator_width)

        context.move_to(x_start + 1, y_start)
        context.line_to(width, y_start)

        context.stroke()

        context.restore()

    def draw_headers_contents(self,
                              context:      cairo.Context,
                              width:        int,
                              prefers_dark: bool) -> None:
        context.save()

        # I don't want this class to access the data directly,
        # but well I have no alternative solution right now.
        data = self.display.document.data

        # Monospace is the best in my opinion for the headers, especially when it comes to the row headers
        # which are numbers so that it can be easier to read because of the good visual alignment.
        header_font_desc = Pango.font_description_from_string(f'Monospace Normal Bold {self.display.FONT_SIZE}px')
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(header_font_desc)

        # Use system default font family for drawing text
        canvas = self.display.document.view.main_canvas
        body_font_desc = Gtk.Widget.create_pango_context(canvas).get_font_description()
        body_font_family = body_font_desc.get_family() if body_font_desc else 'Sans'
        body_font_desc = Pango.font_description_from_string(f'{body_font_family} Normal Bold {self.display.FONT_SIZE}px')

        # We should achieve the high contrast between the text and the canvas background, though I'm aware
        # of the potential problems with using the pure black and white colors. Let's decide that later.
        text_color = (0.0, 0.0, 0.0)
        if prefers_dark:
            text_color = (1.0, 1.0, 1.0)
        context.set_source_rgb(*text_color)

        # Determine the starting column label
        col_index = self.target_column

        context.rectangle(self.display.left_locator_width,
                          0,
                          width,
                          self.display.top_locator_height)
        context.clip()

        # Draw column headers texts (centered)
        # It's so rare to see a worksheet go beyond Z*9 columns, but it's better to be prepared for it anyway
        # by having defining the clip region to prevent the text from overflowing to the next cells. TODO: maybe
        # it's better to automatically adjust the cell widths to fit the text width if the text is overflowing?
        vcol_index = self.display.get_vcolumn_from_column(col_index)

        # Draw dataframe header
        if len(data.bbs) \
                and 0 < self.display.scroll_y_position \
                and col_index <= data.bbs[0].column_span:
            cname = data.dfs[0].columns[vcol_index - 1]
            dtype = utils.get_dtype_symbol(data.dfs[0].dtypes[vcol_index - 1])
            layout.set_font_description(body_font_desc)
            layout.set_text(f'{cname} [{dtype}]', -1)
            x_text = self.target_cell_x + self.display.DEFAULT_CELL_PADDING

        # Draw column name
        else:
            cell_text = self.display.get_column_name_from_column(vcol_index)
            layout.set_font_description(header_font_desc)
            layout.set_text(cell_text, -1)
            text_width = layout.get_size()[0] / Pango.SCALE
            x_text = self.target_cell_x + (self.new_cell_width - text_width) / 2

        context.rectangle(self.target_cell_x,
                          0,
                          self.new_cell_width - 1,
                          self.display.top_locator_height)
        context.clip()

        context.move_to(x_text, 2)
        PangoCairo.show_layout(context, layout)

        context.restore()

    def draw_selection_borders(self,
                               context:      cairo.Context,
                               width:        int,
                               color_accent: tuple[float, float, float, float]) -> None:
        context.save()

        # I don't want this class to access the data directly,
        # but well I have no alternative solution right now.
        selection = self.display.document.selection

        # range_x and range_y were adjusted by the sheet document, so now they are relative to the top
        # of the viewport, meaning they'll be negative if the user scrolled down. The calculations below
        # is only for optimization purposes or to handle the case where the selection size is too big so
        # that it can only be partially drawn.
        arange = selection.current_active_range

        range_x = arange.x
        range_width = arange.width

        range_row = arange.row
        range_column = arange.column
        rcolumn_span = arange.column_span

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

        mdfi = arange.metadata.dfi
        bbox = self.data.bbs[mdfi]

        if arange.column_span < 0:
            rcolumn_span = bbox.column_span + 1

        # Take hidden column(s) into account
        start_vcolumn = self.display.get_vcolumn_from_column(range_column)
        end_vcolumn = self.display.get_vcolumn_from_column(range_column + rcolumn_span - 1)
        rcolumn_span = end_vcolumn - start_vcolumn + 1

        if arange.column_span < 0:
            rcolumn_span -= 1

        # Only draw the selection if the target column is within the selection
        if 0 < rcolumn_span and \
                (range_column + rcolumn_span <= self.target_column or
                 self.target_column < range_column):
            return

        # Adjust the range if necessary to prevent from drawing over translucent cells
        if range_column <= self.target_column <= range_column + rcolumn_span - 1:
            range_x = max(range_x, self.target_cell_x)
            range_width = max(self.target_cell_width, self.new_cell_width)

        # We use a bold style here
        context.set_source_rgba(*color_accent)
        context.set_line_width(2)

        context.rectangle(self.display.left_locator_width,
                          0,
                          width,
                          self.display.top_locator_height + 1)
        context.clip()

        # Indicates that the user has a selection by drawing a line next to the row and column header(s)
        if range_column > 0 and range_row > 0:
            context.move_to(range_x, self.display.top_locator_height)
            context.line_to(range_x + range_width, self.display.top_locator_height)
            context.stroke()

        context.restore()

    def draw_diagonal_lines_pattern(self,
                                    context:      cairo.Context,
                                    width:        int,
                                    prefers_dark: bool) -> None:
        context.save()

        if prefers_dark:
            context.set_source_rgb(0.25, 0.25, 0.25)
        else:
            context.set_source_rgb(0.75, 0.75, 0.75)

        context.set_hairline(True)

        height = self.display.top_locator_height

        context.rectangle(width + self.x_offset, 0, width, height)
        context.clip()

        for c in range(width + self.x_offset, width + height, 5):
            x1 = c
            y1 = 0

            x2 = 0
            y2 = c

            x3 = width
            y3 = c - width

            x4 = c - height
            y4 = height

            points = []
            if 0 <= x1 <= width  and 0 <= y1 <= height: points.append((x1, y1))
            if 0 <= x2 <= width  and 0 <= y2 <= height: points.append((x2, y2))
            if 0 <= x3 <= width  and 0 <= y3 <= height: points.append((x3, y3))
            if 0 <= y4 <= height and 0 <= x4 <= width : points.append((x4, y4))

            unique_points = []
            for p in points:
                if p not in unique_points:
                    unique_points.append(p)

            if len(unique_points) >= 2:
                start_point = unique_points[0]
                end_point   = unique_points[-1]
                context.move_to(start_point[0], start_point[1])
                context.line_to(end_point[0], end_point[1])

        context.stroke()

        context.restore()