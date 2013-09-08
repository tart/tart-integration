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
    def __init__(self, address, username = None, password = None, token = None, syslog = False, application = None):
        self.__address = address
        self.__username = username
        self.__password = password
        self.__token = token
        self.__syslog = syslog
        self.application = application

    def __encodeParameters(self, **parameters):
        from urllib.parse import quote_plus
        for key, value in list(parameters.items()):
            if isinstance(value, list):
                for item in value:
                    yield (key + '[]', quote_plus(item))
            else:
                yield (key, quote_plus(str(value)))

    def __request(self, *arguments, **parameters):
        from urllib.request import Request
        address = self.__address + '/'.join(arguments)
        if parameters:
            address += '?' + '&'.join(key + '=' + value for key, value in self.__encodeParameters(**parameters))
        request = Request(address)
        if self.__username:
            from base64 import urlsafe_b64encode
            authenticationString = self.__username + ':' + self.__password
            authenticationString = urlsafe_b64encode(authenticationString.encode('ascii')).decode('ascii')
            request.add_header('Authorization', 'Basic ' + authenticationString)
        elif self.__token:
            request.add_header('Authorization', 'Token token=' + self.__token)
        request.add_header('Content-type', 'application/json')
        return request

    def __requestWithData(self, *arguments, **parameters):
        '''Create a normal request object with arguments, add parameters to the body instead of the URL.'''
        request = self.__request(*arguments)
        request.add_data(json.dumps(parameters).encode('utf-8'))
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
            print(request.get_method() + ' ' + request.get_full_url() + '\n')
            print(response.info())
            if request.has_data():
                print(request.get_data().decode('utf-8') + '\n')
            print(response.read().decode('utf-8'))
            print(('\n' * 2) + ('=' * 50) + '\n')
            raise
        finally:
            if self.__syslog:
                message = request.get_method() + ' ' + request.get_full_url()
                if response:
                    message += ' response: ' + str(response.getcode())
                message += ' seconds: ' + str(time.time() - startedAt)
                import syslog
                if self.application:
                    syslog.openlog(self.application)
                syslog.syslog(message)

        with response:
            try:
                return json.loads(response.readall().decode('utf-8'))
            except ValueError: pass

    def get(self, *arguments, **parameters):
        return self.__makeRequest(self.__request(*arguments, **parameters))

    def post(self, *arguments, **parameters):
        return self.__makeRequest(self.__requestWithData(*arguments, **parameters))

    def put(self, *arguments, **parameters):
        request = self.__requestWithData(*arguments, **parameters)
        request.get_method = lambda: 'PUT'
        return self.__makeRequest(request)

