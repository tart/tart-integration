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
        parameters = {}
        parameters['jql'] = 'project = "' + project + '" and issuetype = "' + issuetype + '" and '
        parameters['jql'] += 'summary ~ "' + summary + '" and status != Closed order by updated'
        parameters['maxResults'] = 1
        parameters['fields'] = 'key'

        result = self.get('search', parameters)
        if result['issues']:
            return Issue(self, result['issues'][0])

    maxUpdatedIssues = 100

    def updatedIssues(self, projectIssuetypeTuples, since):
        parameters = {}
        parameters['jql'] = '(' + ' or '.join('(project = "' + project + '" and issuetype = "' + issuetype + '")'
                for project, issuetype in projectIssuetypeTuples)
        parameters['jql'] += ') and updated > "' + since.replace('T', ' ')[:16] + '" order by updated asc'
        parameters['maxResults'] = self.maxUpdatedIssues
        parameters['fields'] = 'key,updated,status,priority'

        return (Issue(self, r) for r in self.get('search', parameters)['issues'])

    def issuetype(self, name):
        for issuetype in self.get('issuetype'):
            if name == issuetype['name']:
                return issuetype

    def priority(self, name):
        for priority in self.get('priority'):
            if name == priority['name']:
                return priority

    def createIssue(self, fields):
        return Issue(self, self.post('issue', {'fields': fields}))

    def getUser(self, name):
        '''According to Jira 6.1 REST API documentation users can be searched by username, name or email.'''
        users = self.get('user/search', {'username': name, 'maxResults': 1})
        if users:
            return users[0]

class Issue(dict):
    def __init__(self, client, properties):
        self.__client = client
        dict.__init__(self, properties)

    def __str__(self):
        return self['key']

    def getUnresolvedRemotelinks(self):
        for remoteLink in self.__client.get('issue/' + self['key'] + '/remotelink'):
            if 'application' in remoteLink:
                if 'type' in remoteLink['application']:
                    if remoteLink['application']['type'] == self.__client.application:
                        if not remoteLink['object']['status']['resolved']:
                            yield remoteLink

    def postRemotelink(self, globalId, **kwargs):
        parameters = {}
        parameters['globalId'] = globalId
        parameters['application'] = {'type': self.__client.application}
        parameters['object'] = kwargs

        return self.__client.post('issue/' + self['key'] + '/remotelink', parameters)

    def getTransition(self, name):
        for transition in self.__client.get('issue/' + self['key'] + '/transitions')['transitions']:
            if transition['name'] == name:
                return Transition(transition)

    def postTransition(self, transition, commentBody):
        parameters = {}
        parameters['transition'] = transition
        parameters['update'] = {'comment': [{'add': {'body': commentBody}}]}

        return self.__client.post('issue/' + self['key'] + '/transitions', parameters)

    def postComment(self, body):
        return self.__client.post('issue/' + self['key'] + '/comment', {'body': body})

    def putAssignee(self, user):
        self.__client.put('issue/' + self['key'] + '/assignee', user)

class Transition(dict):
    def __str__(self):
        return self['name']

