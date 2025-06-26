# display.py
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

from gi.repository import GObject

class Display(GObject.Object):
    __gtype_name__ = 'Display'

    ROW_HEADER_WIDTH: int = 40
    CELL_DEFAULT_HEIGHT: int = 20
    CELL_DEFAULT_WIDTH: int = 60
    SCROLL_VERTICAL_POSITION: int = 0
    SCROLL_HORIZONTAL_POSITION: int = 0

    def __init__(self) -> None:
        """
        Initializes the Display class.

        This class is responsible for managing the display settings of the Eruo Data Studio.
        It defines constants for row header width, cell dimensions, scroll positions, and other
        display-related properties.
        """
        super().__init__()