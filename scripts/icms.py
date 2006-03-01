#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2006 Juan David Ib��ez Palomar <jdavid@itaapy.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Import from itools
import itools



if __name__ == '__main__':
    print 'Welcome to: itools %s' % itools.__version__
    print
    print 'Type:'
    print
    print '  icms-init TARGET'
    print '  - To create a new instance (of itools.cms).'
    print
    print '  icms-start TARGET'
    print '  - To start a web server (it will publish your instance to the world).'
    print
    print '  icms-stop TARGET'
    print '  - To stop the web server.'
    print
    print '  icms-update TARGET'
    print '  - To update your instance (to be used after a software upgrade).'
    print
    print '  icms-restore TARGET'
    print '  - To recover your instance (to be used after a crash).'
    print
    print 'For more help on any command type: "icms-<command> --help"'
    print
