# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2004 Juan David Ib��ez Palomar <jdavid@itaapy.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA


# Import from Python
import csv

# Import from itools
from Text import Text



class CSV(Text):

    class_mimetypes = ['text/comma-separated-values', 'text/csv']


    #########################################################################
    # Parsing
    #########################################################################
    def _load(self, resource):
        Text._load(self, resource)

        data = self._data
        del self._data

        # csv.reader expects an iterator
        data = [ x.strip() for x in data.split('\n') ]
        data = [ x.encode(self._encoding) for x in data if x ]

        if data:
            # Sniff the dialect
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff('\n'.join(data))

            # Parse
            self.lines = []
            for line in csv.reader(data, dialect):
                line = [ unicode(x, self._encoding) for x in line ]
                self.lines.append(line)
        else:
            self.lines = []


    #########################################################################
    # API
    #########################################################################
    def to_unicode(self, encoding=None):
        s = u''
        for line in self.lines:
            line = [ '"%s"' % x for x in line ]
            s += ','.join(line) + '\n'
        return s


CSV.register_handler_class(Text)
