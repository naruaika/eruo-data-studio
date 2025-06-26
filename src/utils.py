# utils.py
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

from enum import Enum
import os

class Log(Enum):
    EMERGENCY = 1
    ALERT = 2
    CRITICAL = 3
    ERROR = 4
    WARNING = 5
    NOTICE = 6
    INFO = 7
    DEBUG = 8

_DEBUG_MODE_ENABLED = None
_DEBUG_LEVEL = None

def is_debug_mode_enabled() -> bool:
    """Check if debug mode is enabled"""
    global _DEBUG_MODE_ENABLED
    if _DEBUG_MODE_ENABLED is None:
        _DEBUG_MODE_ENABLED = int(os.environ.get('DEBUG_MODE', '0')) == 1
    return _DEBUG_MODE_ENABLED

def get_debug_level() -> int:
    """Get the debug level

    Returns:
        int: debug level
    """
    global _DEBUG_LEVEL
    if _DEBUG_LEVEL is None:
        _DEBUG_LEVEL = int(os.environ.get('DEBUG_LEVEL', '4'))
    return _DEBUG_LEVEL

def print_log(message: str, type: Log = Log.INFO, context: str = '') -> None:
    """Print info or warning message

    Args:
        message (str): message
        type (str, optional): log type. Defaults to Log.INFO.
        context (str, optional): log context. Defaults to ''.
    """
    if not is_debug_mode_enabled():
        return
    if get_debug_level() < type.value:
        return
    if type == Log.EMERGENCY:
        color = '\033[91m'
        msg_type = 'EMERGENCY'
    elif type == Log.ALERT:
        color = '\033[91m'
        msg_type = 'ALERT'
    elif type == Log.CRITICAL:
        color = '\033[91m'
        msg_type = 'CRITICAL'
    elif type == Log.ERROR:
        color = '\033[91m'
        msg_type = 'ERROR'
    elif type == Log.WARNING:
        color = '\033[93m'
        msg_type = 'WARNING'
    elif type == Log.NOTICE:
        color = '\033[96m'
        msg_type = 'NOTICE'
    elif type == Log.INFO:
        color = '\033[94m'
        msg_type = 'INFO'
    else:
        color = '\033[95m'
        msg_type = 'DEBUG'
    if context:
        context = f'({context}): '
    print(f'{context}{color}{msg_type}\033[0m: {message}')
