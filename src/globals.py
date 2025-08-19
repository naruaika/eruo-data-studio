# globals.py
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
current_document_id: str = ''


# This is supposed to be set by any current window to enable any module
# to send notifications, e.g. error messages when something goes wrong.
# It may will appear a bit technical to common users, but could somehow
# be useful especially when asking in a community forum.
send_notification: callable = lambda *_: None
pending_action_data: dict = {}


# The purpose is to register all the connections for target DuckDB connection
# to the dataframes across all windows and sheets as well as getting all the
# active connection strings to the supported databases by DuckDB, which are:
# MySQL, PostgreSQL, and SQLite.
register_connection: callable = lambda *_: None