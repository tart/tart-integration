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

class JiraClient(JSONAPI):
    def searchIssue(self, project, issuetype, summary):
        '''Search for name in the issue summaries which are not closed, return the one updated last.'''
        result = self.get('search', jql = 'project = "' + project + '" and issuetype = "' + issuetype + '" and ' +
                'summary ~ "' + summary + '" and status != Closed order by updated', maxResults = '1', fields = 'key')
        if result['issues']:
            return Issue(self, result['issues'][0])

    maxUpdatedIssues = 100

    def updatedIssues(self, projectIssuetypeTuples, since):
        jql = ' and '.join('(project = "' + project + '" and issuetype = "' + issuetype + '")'
                for project, issuetype in projectIssuetypeTuples)
        jql += ' and updated > "' + since.replace('T', ' ')[:16] + '" order by updated asc'

        return (Issue(self, r) for r in self.get('search', jql = jql, maxResults = self.maxUpdatedIssues,
                                                 fields = 'key,updated,status,priority')['issues'])

    def issuetype(self, name):
        for issuetype in self.get('issuetype'):
            if name == issuetype['name']:
                return issuetype

    def createIssue(self, **fields):
        return self.post('issue', fields = fields)

class Issue(dict):
    def __init__(self, client, properties):
        self.__client = client
        dict.__init__(self, properties)

    def __str__(self):
        return self['key']

    def remotelinks(self):
        return self.__client.get('issue', self['key'], 'remotelink')

    def transition(self, name):
        for transition in self.__client.get('issue', self['key'], 'transitions')['transitions']:
            if transition['name'] == name:
                return Transition(transition)

    def transit(self, transition, commentBody):
        return self.__client.post('issue', self['key'], 'transitions', transition = transition,
                        update = {'comment': [{'add': {'body': commentBody}}]})

    def addRemotelink(self, globalId, **parameters):
        return self.__client.post('issue', self['key'], 'remotelink', globalId = globalId, object = parameters)

    def addComment(self, body):
        return self.__client.post('issue', self['key'], 'comment', body = body)

    def updateAssignee(self, name):
        return self.__client.put('issue', self['key'], 'assignee', name = name)

class Transition(dict):
    def __str__(self):
        return self['name']

