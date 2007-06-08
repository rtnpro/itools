# -*- coding: UTF-8 -*-
# Copyright (C) 2006 Hervé Cauwelier <herve@itaapy.com>
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# Import from the Standard Library
import mimetypes
from zipfile import ZipFile
from tarfile import TarFile
from cStringIO import StringIO

# Import from itools
from file import File
from registry import register_handler_class


class ZipArchive(File):

    class_mimetypes = ['application/zip']

    def get_contents(self):
        archive = StringIO(self.to_str())
        zip = ZipFile(archive)
        contents = zip.namelist()
        zip.close()
        return contents
    
    
    def get_file(self, filename):
        archive = StringIO(self.to_str())
        zip = ZipFile(archive)
        contents = zip.read(filename)
        zip.close()
        return contents
   


class TarArchive(File):

    class_mimetypes = ['application/x-tar']

    def get_contents(self):
        name = self.name
        archive = StringIO(self.to_str())
        tar = TarFile.open(name=name, fileobj=archive)
        contents = tar.getnames()
        tar.close()

        return contents



# Register
register_handler_class(ZipArchive)
register_handler_class(TarArchive)

# Mimetypes BZip2 support
mimetypes.suffix_map['.tbz2'] = '.tar.bz2'
mimetypes.encodings_map['.bz2'] = 'bzip2'
mimetypes.add_type('application/x-tar', '.tar.bz2')
