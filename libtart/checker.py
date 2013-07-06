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

from .jira import JiraClient, Issue
from .pagerduty import PagerDutyClient
from .configuration import ConfigParser
from .database import SingleUserDatabase

class PagerDutyToJira:
    def __init__(self):
        config = ConfigParser('api.conf')
        self.__jira = JiraClient(**dict(config.items('Jira')))
        self.__pagerDuty = PagerDutyClient(**dict(config.items('PagerDuty')))
        self.__actionConfig = ConfigParser('action.conf')
        self.__serviceConfig = ConfigParser('service.conf')
        self.__userConfig = ConfigParser('user.conf')

    def __username(self, email):
        for section in self.__userConfig.sections():
            if self.__userConfig.has_option(section, 'email'):
                if self.__userConfig.get(section, 'email') == email:
                    return section
        return email.split('@')[0]

    def __description(self, channel):
        body = ''
        if channel['type'] == 'nagios':
            if channel['details']['HOSTALIAS']:
                body += 'Host alias: ' + channel['details']['HOSTALIAS'] + '\n'
            body += 'Host address: ' + channel['details']['HOSTADDRESS'] + '\n'
            body += 'Host output: ' + channel['details']['HOSTOUTPUT'] + '\n'
            if channel['details']['SERVICEDISPLAYNAME']:
                body += 'Service name: ' + channel['details']['SERVICEDISPLAYNAME'] + '\n'
            if channel['details']['SERVICEOUTPUT']:
                body += 'Service output: ' + channel['details']['SERVICEOUTPUT'] + '\n'
            if channel['details']['SERVICENOTES']:
                body += 'Note: ' + channel['details']['SERVICENOTES'] + '\n'
            elif channel['details']['HOSTNOTES']:
                body += 'Note: ' + channel['details']['HOSTNOTES'] + '\n'
        return body

    def __comment(self, logEntry):
        '''Subject:'''
        if logEntry['type'] == 'notify':
            body = '[~' + self.__username(logEntry['user']['email']) + ']'
        else:
            body = 'Incident ' + str(logEntry.incident())

        '''Auxiliary:'''
        body += ' has'
        if 'channel' in logEntry and logEntry['channel']['type'] == 'auto' and 'assigned_user' not in logEntry:
            '''Automatically adverb does not added if assigned user exists because the verb changed to escalated
            if it is automatically assigned.'''
            body += ' automatically'
        elif 'notification' in logEntry:
            if logEntry['notification']['status'] == 'success':
                body += ' successfully'
            elif logEntry['notification']['status'] == 'in_progress':
                '''Exception raised to buy time.'''
                raise Exception('Notification in progress.')
            elif logEntry['notification']['status'] != 'no_answer':
                '''Log entries include only the current status of the notifiations which is not enough to say
                something for certain.'''
                body += ' possibly'

        '''Predicate:'''
        body += ' been'
        if logEntry['type'] == 'reach_trigger_limit':
            body += ' reached the log entry trigger limit and will not create any more'
        elif logEntry['type'] == 'repeat_escalation_path':
            body += ' reached the end of its escalation policy and will restart'
        elif logEntry['type'] == 'exhaust_escalation_path':
            body += ' cycled through its escalation policy the max allowed number of times'
        elif logEntry['type'][-1:] == 'y':
            body += ' ' + logEntry['type'][:-1] + 'ied'
        elif logEntry['type'][-1:] == 'e':
            body += ' ' + logEntry['type'] + 'd'
        else:
            body += ' ' + logEntry['type'] + 'ed'

        '''Prepositional Phrase:'''
        if 'agent' in logEntry:
            if logEntry['agent']['type'] == 'user':
                body += ' by [~' + self.__username(logEntry['agent']['email']) + ']'
        if 'channel' in logEntry:
            if logEntry['channel']['type'] == 'timeout':
                body += ' due to timeout'
            elif logEntry['channel']['type'] == 'api':
                body += ' through the API'
            elif logEntry['channel']['type'] == 'website':
                body += ' on the website'
            elif logEntry['channel']['type'] == 'nagios':
                body += ' by the Nagios'
            elif logEntry['channel']['type'] != 'auto':
                body += ' by ' + logEntry['channel']['type']
        if 'notification' in logEntry:
            if 'push_notification' in logEntry['notification']['type']:
                body += ' via push notification'
            else:
                body += ' via ' + logEntry['notification']['type']
            body += ' at ' + logEntry['notification']['address']
            if logEntry['notification']['status'] == 'no_answer':
                    body += ' but nobody answered'
        if 'assigned_user' in logEntry:
            body += ' to [~' + self.__username(logEntry['assigned_user']['email']) + ']'
        if 'note' in logEntry and logEntry['note']:
            body += ' with note: ' + logEntry['note']

        return body + '.'

    def __process(self, logEntry):
        '''Process incidents with the log entry and the incident related to the log entry.'''
        if not self.__serviceConfig.has_section(logEntry['service']['name']):
            return

        if not self.__actionConfig.has_section(logEntry['type']):
            return

        incident = logEntry.incident()
        projectKey = self.__serviceConfig.get(logEntry['service']['name'], 'project')
        issuetypeName = self.__serviceConfig.get(logEntry['service']['name'], 'type')

        if self.__actionConfig.filter(logEntry['type'], 'status', incident['status']):
            return

        if incident.issueKey():
            issue = Issue({'key': incident.issueKey()})
        else:
            issue = self.__jira.searchIssue(incident.summary().split(' - ')[0],
                                            project = projectKey,
                                            issuetype = issuetypeName)

        if not issue:
            if self.__actionConfig.check(logEntry['type'], 'create'):
                self.__jira.createIssue(project = {'key': projectKey},
                                        issuetype = self.__jira.issuetype(issuetypeName),
                                        summary = incident.summary(),
                                        description = self.__description(logEntry['channel']))
        else:
            if self.__actionConfig.has_option(logEntry['type'], 'transition'):
                transition = self.__jira.transition(issue, self.__actionConfig.get(logEntry['type'], 'transition'))
                if transition:
                    self.__jira.transit(issue, transition, self.__comment(logEntry))

            if self.__actionConfig.check(logEntry['type'], 'assign'):
                self.__jira.updateAssignee(issue, self.__username(logEntry['assigned_user']['email']))

            if self.__actionConfig.check(logEntry['type'], 'comment'):
                self.__jira.addComment(issue, self.__comment(logEntry))

            if self.__actionConfig.check(logEntry['type'], 'link'):
                self.__jira.remotelink(issue, str(incident),
                                       url = incident['html_url'],
                                       title = 'Incident ' + str(incident),
                                       status = {'resolved': incident['status'] == 'resolved'})

    databaseFile = '/tmp/tart-integration'

    def check(self):
        with SingleUserDatabase(self.databaseFile) as database:
            if not database.read():
                from datetime import datetime
                database.write(datetime.utcnow().isoformat())
            for logEntry in self.__pagerDuty.logEntries(database.read()):
                self.__process(logEntry)
                database.write(logEntry['created_at'])

