#!/usr/bin/env python
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

class Incident(dict):
    def __str__(self):
        return '#' + str(self['incident_number'])

class LogEntry(dict):
    def __str__(self):
        return str(self['id'])

    def incident(self):
        return Incident(self['incident'])

class PagerDutyClient(JSONAPI):
    def logEntries(self, since):
        '''Get log entries. Return them reverse ordered as they come with right descending order.'''
        logEntries = self.get('log_entries', since=since, include=['incident', 'channel', 'service'])['log_entries']
        return (LogEntry(item) for item in reversed(logEntries) if item['created_at'] > since)

