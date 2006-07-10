# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2004-2006 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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

# Import from the future
from __future__ import with_statement

# Import from itools
from itools import vfs
from itools.handlers.base import Handler
from IO import (decode_byte, encode_byte, decode_link, encode_link,
                decode_string, encode_string, decode_uint32, encode_uint32,
                NULL)



class Document(object):
    
    def __init__(self, *args):
        self.values = {}
        for field_number, value in enumerate(args):
            self.values[field_number] = value



class Documents(Handler):

    __slots__ = ['uri', 'timestamp', 'documents', 'n_documents',
                 'added_documents', 'removed_documents']


    def new(self):
        # State
        self.documents = {}
        self.n_documents = 0
        # Changes
        self.added_documents = []
        self.removed_documents = []


    ######################################################################
    # Load/Save
    ######################################################################
    def load_state(self):
        base = vfs.open(self.uri)
        with base.open('index') as index_file:
            self.documents = {}
            index_file.seek(0, 2)
            self.n_documents = index_file.tell() / 8
        # Nothing changed yet
        self.added_documents = []
        self.removed_documents = []


    def _save_state(self, uri):
        base = vfs.open(uri)
        index_file = base.open('index')
        docs_file = base.open('documents')
        try:
            # Removed documents
            for doc_n in self.removed_documents:
                index_file.seek(doc_n * 8)
                index_file.write(NULL)
                # Update data structure
                if doc_n in self.documents:
                    del self.documents[doc_n]
            # Added documents
            docs_file.seek(0, 2)
            index_file.seek(0, 2)
            for doc_n in self.added_documents:
                document = self.documents[doc_n]
                # Append the new document to the documents file
                buffer = []
                keys = document.values.keys()
                keys.sort()
                for field_number in keys:
                    value = document.values[field_number]
                    buffer.append(encode_byte(field_number))
                    buffer.append(encode_string(value))
                position = docs_file.tell()
                data = ''.join(buffer)
                docs_file.write(data)
                # Update the index file
                size = len(data)
                index_file.write(encode_link(position) + encode_uint32(size))
            # Clean the data structure
            self.added_documents = []
            self.removed_documents = []
        finally:
            index_file.close()
            docs_file.close()


    def save_state(self):
        self._save_state(self.uri)


    def save_state_to(self, uri):
        # Create the index folder
        vfs.make_folder(uri) 
        base = vfs.open(uri)
        # Initialize the tree file
        base.make_file('documents')
        base.make_file('index')
        # XXX Remains to save the data in "self._documents"
        # Save changes
        self._save_state(uri)


    ######################################################################
    # API
    ######################################################################
    def index_document(self, document):
        doc_n = self.n_documents
        self.n_documents += 1
        self.documents[doc_n] = document
        self.added_documents.append(doc_n)
        return doc_n


    def unindex_document(self, doc_n):
        self.removed_documents.append(doc_n)


    def get_document(self, doc_n):
        if doc_n not in self.documents:
            document = Document()
            # Load document from the documents file
            base = vfs.open(self.uri)
            index_file = base.open('index', 'r')
            docs_file = base.open('documents', 'r')
            try:
                # Read the index entry
                index_file.seek(doc_n * 8)
                data = index_file.read(8)
                pointer = decode_link(data[0:4])
                if pointer is None:
                    raise LookupError, 'document "%d" is not indexed' % doc_n
                size = decode_uint32(data[4:8])
                # Read the document data
                docs_file.seek(pointer)
                data = docs_file.read(size)
                # Load the document data
                while data:
                    field_n = decode_byte(data[0])
                    value, data = decode_string(data[1:])
                    document.values[field_n] = value
                self.documents[doc_n] = document
            finally:
                index_file.close()
                docs_file.close()

        return self.documents[doc_n]






