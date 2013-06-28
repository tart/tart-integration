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

class Issue(dict):
    def __str__(self):
        return self['key']

class Transition(dict):
    def __str__(self):
        return self['name']

class JiraClient(JSONAPI):
    def lastIssueBySummary(self, name):
        '''Search for host name in the issue summaries which are not closed, return the one updated last.'''
        issues = self.get('search', jql = 'summary~"' + name + '" and status!=Closed order by updatedDate',
                maxResults = '1', fields= 'key,assignee')['issues']
        if issues:
            return Issue(issues[0])

    def transition(self, issue, name):
        for transition in self.get('issue', issue['key'], 'transitions')['transitions']:
            if transition['name'] == name:
                return Transition(transition)

    def transit(self, issue, transition, commentBody):
        return self.post('issue', issue['key'], 'transitions', transition = transition,
                        update = {'comment': [{'add': {'body': commentBody}}]})

    def issueType(self, name):
        for issueType in self.get('issuetype'):
            if name == issueType['name']:
                return issueType

    def createIssue(self, **fields):
        return self.post('issue', fields = fields)

    def remotelink(self, issue, globalId, **parameters):
        return self.post('issue', issue['key'], 'remotelink', globalId = globalId, object = parameters)

    def addComment(self, issue, body):
        return self.post('issue', issue['key'], 'comment', body = body)

    def updateAssignee(self, issue, name):
        return self.put('issue', issue['key'], 'assignee', name = name)

