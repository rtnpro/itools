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
from time import strftime
from datetime import timedelta

# Import from itools
from app import Application
from exceptions import HTTPError
from message import HTTPMessage
from soup import SoupServer
from itools.log import Logger, register_logger, log_info



class HTTPServer(SoupServer):

    # The default application says "hello"
    app = Application()
    message_class = HTTPMessage


    def __init__(self, access_log=None):
        SoupServer.__init__(self)

        # The logger
        logger = AccessLogger(log_file=access_log)
        logger.launch_rotate(timedelta(weeks=3))
        register_logger(logger, 'itools.web_access')


    def log_access(self, host, request_line, status_code, body_length):
        now = strftime('%d/%b/%Y:%H:%M:%S')
        message = '%s - - [%s] "%s" %d %d\n' % (host, now, request_line,
                                                status_code, body_length)
        log_info(message, domain='itools.web_access')


    def listen(self, address, port):
        SoupServer.listen(self, address, port)
        address = address if address is not None else '*'
        print 'Listen %s:%d' % (address, port)


    def stop(self):
        SoupServer.stop(self)
        if self.access_log:
            self.access_log_file.close()


    #######################################################################
    # Callbacks
    #######################################################################
    def star_callback(self, soup_message, path):
        """This method is called for the special "*" request URI, which means
        the request concerns the server itself, and not any particular
        resource.

        Currently this feature is only supported for the OPTIONS request
        method:

          OPTIONS * HTTP/1.1
        """
        method = soup_message.get_method()
        if method != 'OPTIONS':
            soup_message.set_status(405)
            soup_message.set_header('Allow', 'OPTIONS')
            return

        methods = self._get_server_methods()
        soup_message.set_status(200)
        soup_message.set_header('Allow', ','.join(methods))


    def path_callback(self, soup_message, path):
        # 501 Not Implemented
        method = soup_message.get_method()
        method = method.lower()
        method = getattr(self, 'http_%s' % method, None)
        if method is None:
            soup_message.set_status(501)
            soup_message.set_response('text/plain', '501 Not Implemented')
            return

        try:
            self._path_callback(soup_message, path)
        except Exception:
            self.log_error()
            soup_message.set_status(500)
            soup_message.set_body('text/plain', '500 Internal Server Error')


    def _path_callback(self, soup_message, path):
        message = self.message_class(soup_message, path)

        # 501 Not Implemented
        method = message.get_method()
        method = method.lower()
        method = getattr(self, 'http_%s' % method, None)
        if method is None:
            return message.set_response(501)

        # Step 1: Host
        app = self.app
        app.get_host(message)

        # Step 2: Resource
        resource = app.get_resource(message)
        if resource is None:
            # 404 Not Found
            return message.set_response(404)
        if type(resource) is str:
            # 307 Temporary redirect
            message.set_status(307)
            message.set_header('Location', resource)
            return

        # Continue
        message.resource = resource
        try:
            method(message)
        except HTTPError, exception:
            self.log_error()
            status = exception.code
            message.set_response(status)


    #######################################################################
    # Request methods
    def _get_server_methods(self):
        return [ x[5:].upper() for x in dir(self) if x[:5] == 'http_' ]


    def http_options(self, context):
        resource = message.resource

        # Methods supported by the server
        methods = self._get_server_methods()

        # Test capabilities of a resource
        resource_methods = resource._get_resource_methods()
        methods = set(methods) & set(resource_methods)
        # Special cases
        methods.add('OPTIONS')
        if 'GET' in methods:
            methods.add('HEAD')
        # DELETE is unsupported at the root
        if context.path == '/':
            methods.discard('DELETE')

        # Ok
        context.soup_message.set_status(200)
        context.set_header('Allow', ','.join(methods))


    def http_get(self, message):
        resource = message.resource

        # 405 Method Not Allowed
        method = getattr(resource, 'http_get', None)
        if method is None:
            message.set_status(405)
            server_methods = set(self._get_server_methods())
            resource_methods = set(resource._get_reource_methods)
            methods = server_methods & resource_methods
            message.set_header('allow', ','.join(methods))
            return

        # Continue
        return method(message)


    def http_post(self, message):
        resource = message.resource

        # 405 Method Not Allowed
        method = getattr(resource, 'http_post', None)
        if method is None:
            message.set_status(405)
            server_methods = set(self._get_server_methods())
            resource_methods = set(resource._get_reource_methods)
            methods = server_methods & resource_methods
            message.set_header('allow', ','.join(methods))
            return

        # Continue
        return method(message)


    http_head = http_get



class AccessLogger(Logger):
    def format(self, domain, level, message):
        return message


###########################################################################
# For testing purposes
###########################################################################
if __name__ == '__main__':
    server = HTTPServer()
    print 'Start server..'
    server.start()
