# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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

# Import from the Standard Library
from base64 import decodestring
from types import GeneratorType
from urllib import unquote

# Import from itools
from itools.handlers import BaseDatabase
from itools.html import stream_to_str_as_html
from itools.http import HTTPError, HTTPMount
from context import WebContext


# These are the values that 'WebApplication.find_resource' may return
MOVED = 301
REDIRECT = 307 # 302 in HTTP 1.0
UNAUTHORIZED = 401
FORBIDDEN = 403
NOT_FOUND = 404
GONE = 410 # Not available in HTTP 1.0

status2name = {
    401: 'http_unauthorized',
    403: 'http_forbidden',
    404: 'http_not_found',
    405: 'http_method_not_allowed',
    409: 'http_conflict'}



class WebApplication(HTTPMount):

    context_class = WebContext
    database = BaseDatabase()


    def handle_request(self, context):
        try:
            context.access
            method = self.known_methods[context.method]
            method = getattr(self, method)
            method(context)
        except HTTPError, exception:
            status = exception.code
            context.status = status
            context.resource = context.host
            del context.view
            context.view_name = status2name[status]
            context.access = True
            self.handle_request(context)
        else:
            if context.status is None:
                context.status = 200
            context.set_status(context.status)


    def get_host(self, context):
        return None


    def get_user(self, credentials):
        return None


    #######################################################################
    # Request handlers
    #######################################################################
    known_methods = {
        'OPTIONS': 'http_options',
        'GET': 'http_get',
        'HEAD': 'http_get',
        'POST': 'http_post'}


    def get_allowed_methods(self, context):
        obj = context.view or context.resource

        methods = [
            x for x in self.known_methods
            if getattr(obj, self.known_methods[x], None) ]
        methods = set(methods)
        methods.add('OPTIONS')
        return methods


    def http_options(self, context):
        methods = self.get_allowed_methods(context.resource)
        context.set_status(200)
        context.set_header('Allow', ','.join(methods))


    def http_get(self, context):
        view = context.view
        body = view.http_get(context.resource, context)
        if type(body) is GeneratorType:
            body = stream_to_str_as_html(body)
        context.set_body('text/html', body)


    def http_post(self, context):
        resource = context.resource
        resource.http_post(context)
