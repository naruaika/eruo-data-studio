# sheet_column_locator_menu.py
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

from gi.repository import Gtk

from ..dbms import DBMS

@Gtk.Template(resource_path='/com/macipra/Eruo/gtk/sheet-column-locator-menu.ui')
class SheetColumnLocatorMenu(Gtk.PopoverMenu):
    __gtype_name__ = 'SheetColumnLocatorMenu'

    _colid: str
    _dbms: DBMS

    def __init__(self, colid: int, dbms: DBMS, **kwargs) -> None:
        """Creates a new SheetColumnLocatorMenu."""
        super().__init__(**kwargs)

        self._colid = str(colid)
        self._dbms = dbms

    def set_colid(self, colid: int) -> None:
        """Sets the colid for the SheetColumnLocatorMenu."""
        self._colid = str(colid)
