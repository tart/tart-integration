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

from .api import JSONAPI

class PagerDutyClient(JSONAPI):
    includeWithLogEntry = ['incident', 'channel', 'service', 'note']

    def logEntries(self, since):
        '''Get log entries. Return them reverse ordered as they come with right descending order.'''
        logEntries = self.get('log_entries', {'since': since, 'include': self.includeWithLogEntry})['log_entries']
        return (LogEntry(self, item) for item in reversed(logEntries) if item['created_at'] > since)

    def getIncident(self, incidentId):
        assert len(incidentId) > 6
        return Incident(self, self.get('incidents' + '/' + incidentId))

class Incident(dict):
    def __init__(self, client, properties):
        self.__client = client
        dict.__init__(self, properties)

    def __str__(self):
        return str(self['id'])

    def put(self, action):
        self.__client.put('incidents/' + self['id'] + '/' + action)

class LogEntry(dict):
    def __init__(self, client, properties):
        self.__client = client
        dict.__init__(self, properties)

    def __str__(self):
        return str(self['id'])

    def incident(self):
        return Incident(self.__client, self['incident'])

