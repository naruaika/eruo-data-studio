# globals.py
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


# TODO: I don't think this pattern is a good idea in general.
# We should use a singleton maybe? Note that we'll need
# to find an easy way to make communication between sheets
# and windows can happen in the near future, e.g. for the
# vlookup feature or some other similar things. Anyway, I think
# it's more ideal to setup any kind of inter-process communication
# (IPC) between windows.


from .history_manager import HistoryManager

# The history state for the current active window to help with undo/redo.
history: HistoryManager = None
is_changing_state: bool = False


# The idea is to make the current active window to behave in a
# certain way, e.g. when editing cells and the user wants to do
# a vlookup to another window, the current window should show
# the current editing formula in the input bar. For that specific
# case, we may also need another global variable to track any
# changes in the input bar.
is_editing_cells: bool = False
docid_being_edited: str = ''


# This is supposed to be set by any current window to enable any module
# to send notifications, e.g. error messages when something goes wrong.
# It may will appear a bit technical to common users, but could somehow
# be useful especially when asking in a community forum.
send_notification: callable = lambda *_: None