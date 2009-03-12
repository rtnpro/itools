# -*- coding: UTF-8 -*-
# Copyright (C) 2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from itools
from cache import LRUCache
from freeze import freeze, frozendict, frozenlist
from utils import add_type, guess_all_extensions, guess_extension, guess_type
from utils import has_encoding, has_extension
from utils import get_abspath, merge_dicts, get_pipe
from sys import platform

if platform[:3] == 'win':
    from _win import become_daemon, fork, get_time_spent, vmsize
else:
    from _unix import become_daemon, fork, get_time_spent, vmsize



__all__ = [
    # Frozen types
    'freeze',
    'frozendict',
    'frozenlist',
    # Caching
    'LRUCache',
    # Mimetypes
    'add_type',
    'guess_all_extensions',
    'guess_extension',
    'guess_type',
    'has_encoding',
    'has_extension',
    # Utility functions
    'get_abspath',
    'merge_dicts',
    'get_pipe',
    # System specific functions
    'become_daemon',
    'fork',
    'get_time_spent',
    'vmsize',
   ]
