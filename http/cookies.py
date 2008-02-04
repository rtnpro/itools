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
from itools.datatypes import DataType
from parsing import (read_char, read_parameter, read_parameters,
    read_white_space)


"""
Partial implementation of an "HTTP State Management Mechanism", also known
as cookies.

Related documents:

 - RFC 2109, http://www.ietf.org/rfc/rfc2109.txt

 - RFC 2965, http://www.ietf.org/rfc/rfc2965.txt

 - http://en.wikipedia.org/wiki/HTTP_cookie
"""



class Cookie(object):

    def __init__(self, value, comment=None, domain=None, max_age=None,
                 path=None, secure=None, version=None, commenturl=None,
                 discard=None, port=None, expires=None):
        self.value = value
        # Parameters (RFC 2109)
        self.comment = comment
        self.domain = domain
        self.max_age = max_age
        self.path = path
        self.secure = secure
        self.version = version
        # Parameters (RFC 2965)
        self.commenturl = commenturl
        self.discard = discard
        self.port = port
        # Not standard
        self.expires = expires


    def __eq__(self, other):
        names = ['value', 'comment', 'domain', 'max_age', 'path', 'secure',
                 'version', 'commenturl', 'discard', 'port', 'expires']
        for name in names:
            if getattr(self, name) != getattr(other, name):
                return False
        return True


    def __str__(self):
        output = ['"%s"' % self.value]
        if self.path is not None:
            output.append('$Path="%s"' % self.path)
        if self.domain is not None:
            output.append('$Domain="%s"' % self.domain)
        return '; '.join(output)



class CookieDataType(DataType):

    @staticmethod
    def decode(data):
        # Version (old clients do not send "$Version")
        first, rest = read_parameter(data)
        if first[0] == '$version':
            version = first[1]
            if version != '1':
                raise ValueError, 'unexpected cookie version "%s"' % version
            data = rest
            # ;
            white, data = read_white_space(data)
            data = read_char(';', data)
            white, data = read_white_space(data)
        else:
            version = None

        # Cookies
        cookies = {}
        while data:
            cookie, data = read_parameter(data)
            cookie_name, cookie_value = cookie
            path = domain = None
            # White Space
            white, data = read_white_space(data)
            # Parameters
            if data:
                # Seperator (;)
                data = read_char(';', data)
                white, data = read_white_space(data)
                # Parameter
                value, rest = read_parameter(data)
                name, value = value
                if name == '$path':
                    path = value
                    white, data = read_white_space(rest)
                    if data:
                        # Separator (;)
                        data = read_char(';', data)
                        white, data = read_white_space(data)
                        # Parameter
                        value, rest = read_parameter(data)
                        if name == '$domain':
                            domain = value
                            white, data = read_white_space(rest)
                            if data:
                                # Separator (;)
                                data = read_char(';', data)
                                white, data = read_white_space(data)
                elif name == '$domain':
                    domain = value
                    white, data = read_white_space(rest)
                    if data:
                        # Separator (;)
                        data = read_char(';', data)
                        white, data = read_white_space(data)
            # Set
            cookies[cookie_name] = Cookie(cookie_value, path=path,
                                          domain=domain, version=version)

        return cookies


    @staticmethod
    def encode(cookies):
        output = []
        # Version
        output.append('$Version="1"')
        # Cookies
        for name in cookies:
            cookie = cookies[name]
            version = cookie.version
            if version is not None and version != '1':
                raise ValueError, 'unexpected cookie version "%s"' % version

            output.append('%s=%s' % (name, cookie))

        return '; '.join(output)



class SetCookieDataType(DataType):

    @staticmethod
    def decode(data):
        cookies = {}
        # Cookie
        cookie, data = read_parameter(data)
        name, value = cookie
        # White Space
        white, data = read_white_space(data)
        # Parameters
        parameters, data = read_parameters(data)

        # FIXME There may be more cookies (comma separated)
        cookies[name] = Cookie(value, **parameters)
        if data:
            raise ValueError, 'unexpected string "%s"' % data

        return cookies


    @staticmethod
    def encode(cookies):
        output = []
        for name in cookies:
            cookie = cookies[name]
            aux = []
            aux.append('%s="%s"' % (name, cookie.value))
            # The parameters
            if cookie.version is not None:
                aux.append('version="%s"' % cookie.version)
            if cookie.expires is not None:
                aux.append('expires="%s"' % cookie.expires)
            if cookie.domain is not None:
                aux.append('domain="%s"' % cookie.domain)
            if cookie.path is not None:
                aux.append('path="%s"' % cookie.path)
            else:
                aux.append('path="/"')
            if cookie.max_age is not None:
                aux.append('max-age="%s"' % cookie.max_age)
            if cookie.comment is not None:
                aux.append('comment="%s"' % cookie.comment)
            if cookie.secure is not None:
                aux.append('secure="%s"' % cookie.secure)
            # The value
            output.append('; '.join(aux))
        return ', '.join(output)

