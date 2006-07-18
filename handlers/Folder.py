# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2003-2006 Juan David Ib��ez Palomar <jdavid@itaapy.com>
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

# Import from the Standard Library
from datetime import datetime

# Import from itools
from itools.uri import Path
from itools.vfs import api as vfs
from itools.handlers.Handler import Handler
from itools.handlers import registry



class Context(object):
    """Used by 'traverse2' to control the traversal."""

    def __init__(self):
        self.skip = False



class Folder(Handler):
    """
    This is the base handler class for any folder handler. It is also used
    as the default handler class for any folder resource that has not a more
    specific handler.
    """

    class_resource_type = 'folder'
    class_mimetypes = ['application/x-not-regular-file']

    
    __slots__ = ['cache', 'added_handlers', 'removed_handlers']


    def new(self, **kw):
        self.cache = {}
        self.added_handlers = set()
        self.removed_handlers = set()


    def _load_state(self, uri):
        # XXX This code may be optimized just checking wether there is
        # already an up-to-date handler in the cache, then it should
        # not be touched.
        cache = {}
        for name in vfs.get_names(uri):
            cache[name] = None
        self.cache = cache

        # Keep differential
        self.added_handlers = set()
        self.removed_handlers = set()


    def _deep_load(self):
        self.load_state()
        for name in self.cache:
            handler = self.get_handler(name)
            handler._deep_load()


    def _save_state(self, resource):
        cache = self.cache
        # Remove
        for name in self.removed_handlers:
            resource.del_resource(name)
        self.removed_handlers = set()

        # Add
        base = self.uri
        for name in self.added_handlers:
            ref = base.resolve2(name)
            # First remove the resource if it exists
            if vfs.exists(ref):
                vfs.remove(ref)
            # Add a dummy resource
            handler = cache[name]
            if isinstance(handler, Folder):
                vfs.make_folder(ref)
            else:
                vfs.make_file(ref)
            # Save state to the dummy resource
            handler.uri = ref
            with vfs.open(ref) as new_resource:
                handler._save_state(new_resource)
        self.added_handlers = set()


    def _save_state_to(self, resource):
        # Clean the target
        for name in resource.get_names():
            resource.del_resource(name)

        # Add the resources
        cache = self.cache
        for name in cache:
            ref = base.resolve2(name)
            # Add a dummy resource
            handler = cache[name]
            if isinstance(handler, Folder):
                vfs.make_folder(ref)
            else:
                vfs.make_file(ref)
            # Save state to the dummy resource
            new_resource = resource.get_resource(name)
            handler.save_state_to(new_resource)


    #########################################################################
    # API (private)
    #########################################################################
    def _get_handler_names(self):
        return self.cache.keys()


    def get_handler_class(self, segment, resource):
        return registry.get_handler_class(resource)


    def _get_virtual_handler(self, segment):
        """
        This method must return a handler for the given segment, or raise
        the exception LookupError. We know there is not a resource with
        the given name, this method is used to return 'virtual' handlers.
        """
        raise LookupError, 'the resource "%s" does not exist' % segment.name


    #########################################################################
    # API (public)
    #########################################################################
    def load_state(self):
        self._load_state(self.uri)
        self.timestamp = vfs.get_mtime(self.uri)


    def load_state_from(self, uri):
        get_transaction().add(self)
        self._load_state(uri)
        self.timestamp = datetime.now()


    def get_handler(self, path):
        # Be sure path is a Path
        if not isinstance(path, Path):
            path = Path(path)

        if path.is_absolute():
            root = self.get_root()
            path = str(path)[1:]
            return root.get_handler(path)

        if len(path) == 0:
            return self

        if path[0].name == '..':
            if self.parent is None:
                raise ValueError, 'this handler is the root handler'
            return self.parent.get_handler(path[1:])

        here = self
        for segment in path:
            name = segment.name

            # Check wether it is a folder or not
            if not isinstance(here, Folder):
                raise LookupError, u'the resource "%s" does not exist' % name

            # Check wether the resource exists or not
            if name not in here.cache:
                # Virtual handler
                handler = self._get_virtual_handler(segment)
                handler = build_virtual_handler(handler)
                # Set parent and name
                handler.parent = here
                handler.name = name

                here = handler
                continue

            # Check if it is a new handler (avoid cache)
            if name in here.added_handlers:
                here = here.cache[name]
                continue

            # Get the handler from the cache
            handler = here.cache[name]
            if handler is None:
                # Miss
                resource = here.resource.get_resource(name)
                handler_class = here.get_handler_class(segment, resource)
                handler = handler_class(resource)
                # Update the cache
                here.cache[name] = handler
            else:
                # Hit, reload the handler if needed
                if handler.is_outdated():
                    handler.load_state()
        return here


    def has_handler(self, path):
        # Be sure path is a Path
        if not isinstance(path, Path):
            path = Path(path)

        # Get the container
        path, segment = path[:-1], path[-1]
        container = self.get_handler(path)

        # Check wether the container has the handler or not
        return segment.name in container.cache


    def get_handler_names(self, path='.'):
        container = self.get_handler(path)
        return container.cache.keys()


    def get_handlers(self, path='.'):
        handler = self.get_handler(path)
        for name in handler.get_handler_names(path):
            yield handler.get_handler(name)


    def set_handler(self, path, handler, **kw):
        if not isinstance(path, Path):
            path = Path(path)

        path, segment = path[:-1], path[-1]
        name = segment.name

        container = self.get_handler(path)
        # Check if there is already a handler with that name
        if name in container.get_handler_names():
            raise LookupError, 'there is already a handler named "%s"' % name

        # Store the container in the transaction
        container.set_changed()
        # Clean the 'removed_handlers' data structure if needed
        if name in container.removed_handlers:
            container.removed_handlers.remove(name)
        # Event: before set handler
        container.before_set_handler(segment, handler, **kw)
        # Make a copy of the handler
        handler = handler.copy_handler()
        handler.parent = container
        handler.name = name
        # Add the handler
        container.added_handlers.add(name)
        container.cache[name] = handler
        # Event: after set handler
        container.after_set_handler(segment, handler, **kw)
        return handler


    def del_handler(self, path):
        if not isinstance(path, Path):
            path = Path(path)

        path, segment = path[:-1], path[-1]
        name = segment.name

        container = self.get_handler(path)
        # Check wether the handler really exists
        if name not in container.get_handler_names():
            raise LookupError, 'there is not any handler named "%s"' % name

        # Store the container in the transaction
        container.set_changed()
        # Event, on del handler
        if hasattr(container, 'on_del_handler'):
            container.on_del_handler(segment)
        # Clean the 'added_handlers' data structure if needed
        if name in container.added_handlers:
            container.added_handlers.remove(name)
        # Mark the handler as deleted
        container.removed_handlers.add(name)
        del container.cache[name]


    ########################################################################
    # Other methods
    def before_set_handler(self, segment, handler, **kw):
        pass


    def after_set_handler(self, segment, handler, **kw):
        pass


    ########################################################################
    # Tree
    def traverse(self):
        yield self
        for name in self.get_handler_names():
            handler = self.get_handler(name)
            if isinstance(handler, Folder):
                for x in handler.traverse():
                    yield x
            else:
                yield handler


    def traverse2(self, context=None):
        if context is None:
            context = Context()

        yield self, context
        if context.skip is True:
            context.skip = False
        else:
            for name in self.get_handler_names():
                handler = self.get_handler(name)
                if isinstance(handler, Folder):
                    for x, context in handler.traverse2(context):
                        yield x, context
                else:
                    yield handler, context
                    if context.skip is True:
                        context.skip = False



def build_virtual_handler(handler):
    virtual_handler = Handler.__new__(handler.__class__)

    # XXX Use __slots__ instead of "state"
    virtual_handler.resource = handler.resource
    virtual_handler.state = handler.state
    virtual_handler.timestamp = handler.timestamp

    # Keep a reference to the real handler
    virtual_handler.real_handler = handler

    return virtual_handler
    

registry.register_handler_class(Folder)
