# -*- coding: utf-8 -*-
##
# Tart Integration
#
# Copyright (c) 2013, Tart İnternet Teknolojileri Ticaret AŞ
#
# Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby
# granted, provided that the above copyright notice and this permission notice appear in all copies.
#
# The software is provided "as is" and the author disclaims all warranties with regard to the software including all
# implied warranties of merchantability and fitness. In no event shall the author be liable for any special, direct,
# indirect, or consequential damages or any damages whatsoever resulting from loss of use, data or profits, whether
# in an action of contract, negligence or other tortious action, arising out of or in connection with the use or
# performance of this software.
##

import json
import time

class JSONAPI:
    def __init__(self, address, username=None, password=None, token=None, syslog=False, application=None):
        self.address = address
        self.username = username
        self.password = password
        self.token = token
        self.syslog = syslog
        self.application = application

    def __encodeParameters(self, parameters):
        from urllib.parse import quote_plus
        for key, value in list(parameters.items()):
            if isinstance(value, list):
                for item in value:
                    yield (key + '[]', quote_plus(item))
            else:
                yield (key, quote_plus(str(value)))

    def __request(self, uri, getParameters=None, postParameters=None):
        from urllib.request import Request
        address = self.address + uri
        if getParameters:
            address += '?' + '&'.join(key + '=' + value for key, value in self.__encodeParameters(getParameters))
        request = Request(address)
        if postParameters is not None:
            request.add_data(json.dumps(postParameters).encode('utf-8'))

        if self.username:
            from base64 import urlsafe_b64encode
            authenticationString = self.username + ':' + self.password
            authenticationString = urlsafe_b64encode(authenticationString.encode('ascii')).decode('ascii')
            request.add_header('Authorization', 'Basic ' + authenticationString)
        elif self.token:
            request.add_header('Authorization', 'Token token=' + self.token)
        request.add_header('Content-type', 'application/json')
        return request

    def __makeRequest(self, request):
        from urllib.request import urlopen
        from urllib.error import HTTPError

        response = None
        startedAt = time.time()
        try:
            response = urlopen(request)
        except HTTPError as error:
            response = error
        finally:
            if self.syslog:
                message = request.get_method() + ' ' + request.get_full_url()
                if response:
                    message += ' response: ' + str(response.getcode())
                message += ' seconds: ' + str(time.time() - startedAt)
                import syslog
                if self.application:
                    syslog.openlog(self.application)
                syslog.syslog(message)

        return JSONResponse(response)

    def get(self, uri, parameters=None):
        response = self.__makeRequest(self.__request(uri, parameters))
        if response.successful():
            return response.body()
        response.raiseAsError()

    def post(self, uri, parameters):
        response = self.__makeRequest(self.__request(uri, postParameters=parameters))
        if response.successful():
            return response.body()
        response.raiseAsError()

    def put(self, uri, parameters={}):
        request = self.__request(uri, postParameters=parameters)
        request.get_method = lambda: 'PUT'
        response = self.__makeRequest(request)
        if response.successful():
            return response.body()
        if response.clientError():
            return False
        response.raiseAsError()

class JSONResponse:
    debug = True

    def __init__(self, message):
        self.__message = message

    def body(self):
        with self.__message:
            try:
                return json.loads(self.__message.read().decode('utf-8'))
            except ValueError: pass

    def raiseAsError(self):
        if self.debug:
            print('\n=== Response ===\n')
            print(str(self.__message.info()))
            print(str(self.body()))
            print(('\n' * 2) + ('=' * 50) + '\n')
        raise self.__message

    def code(self):
        return self.__message.getcode()

    def __str__(self):
        return str(self.__message)

    def information(self):
        return 100 <= self.code() < 200

    def successful(self):
        return 200 <= self.code() < 300

    def redirect(self):
        return 300 <= self.code() < 400

    def clientError(self):
        return 400 <= self.code() < 500

    def serverError(self):
        return 500 <= self.code() < 600

