# -*- coding: UTF-8 -*-
# Copyright (C) 2006-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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
from context import HTTPContext, get_context, set_context
from entities import Entity
from exceptions import HTTPError, ClientError, ServerError
from exceptions import HTTP_OK, NotModified
from exceptions import BadRequest, Unauthorized, Forbidden, NotFound
from exceptions import InternalServerError, NotImplemented, BadGateway
from exceptions import ServiceUnavailable, MethodNotAllowed, Conflict
from headers import get_type
from headers import Cookie, SetCookieDataType
from server import HTTPServer
from mounts import HTTPMount, StaticMount
from utils import set_response


__all__ = [
    'SoupMessage',
    'HTTPServer',
    'HTTPContext',
    'Entity',
    'get_type',
    'set_response',
    'get_context',
    'set_context',
    # Cookies
    'Cookie',
    'SetCookieDataType',
    # Mounts
    'HTTPMount',
    'StaticMount',
    # Exceptions
    'BadGateway',
    'BadRequest',
    'ClientError',
    'Conflict',
    'Forbidden',
    'HTTP_OK',
    'HTTPError',
    'InternalServerError',
    'MethodNotAllowed',
    'NotFound',
    'NotImplemented',
    'NotModified',
    'ServerError',
    'ServiceUnavailable',
    'Unauthorized',
    ]
