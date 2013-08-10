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

class PagerDutyJira:
    def __init__(self):
        config = ConfigParser('api.conf')
        self.__jira = JiraClient(**dict(config.items('Jira')))
        self.__pagerDuty = PagerDutyClient(**dict(config.items('PagerDuty')))
        self.__actionConfig = ConfigParser('action.conf')
        self.__serviceConfig = ConfigParser('service.conf')
        self.__userConfig = ConfigParser('user.conf')

    databaseFile = '/tmp/tart-integration'

    def check(self):
        with SingleUserDatabase(self.databaseFile) as database:
            if not database.read():
                from datetime import datetime
                database.write(datetime.utcnow().isoformat())
            since = database.read()

            for logEntry in self.__pagerDuty.logEntries(since):
                if 'notification' in logEntry and logEntry['notification']['status'] == 'in_progress':
                    '''Stop progress for now to buy time.'''
                    break
                self.__processLogEntry(logEntry)
                database.write(logEntry['created_at'])

            self.__checkUpdatedIssues(since)

    def __checkUpdatedIssues(self, since):
        incidentsToUpdate = []

        for issue in self.__jira.updatedIssues(self.__serviceConfig.sectionValues('project', 'type'), since):
            for remotelink in issue.remotelinks():
                for action in self.__actionConfig.sections():
                    if self.__actionConfig.filter(action, 'issuestatus', issue['fields']['status']['name']):
                        status = self.__actionConfig.get(action, 'status')
                        incident = self.__pagerDuty.getIncident(remotelink['globalId'])

                        if incident['status'] not in (status, 'resolved'):
                            incidentsToUpdate.append({'id': incident['id'], 'status': status})

        if incidentsToUpdate:
            self.__pagerDuty.putIncidents(incidents = incidentsToUpdate)

    def __processLogEntry(self, logEntry):
        '''Process incidents with the log entry and the incident related to the log entry.'''
        if not self.__serviceConfig.has_section(logEntry['service']['name']):
            return

        if not self.__actionConfig.has_section(logEntry['type']):
            return

        incident = logEntry.incident()

        if not self.__actionConfig.filter(logEntry['type'], 'status', incident['status']):
            return

        projectKey = self.__serviceConfig.get(logEntry['service']['name'], 'project')
        issuetypeName = self.__serviceConfig.get(logEntry['service']['name'], 'type')
        issue = self.__findIssue(projectKey, issuetypeName, incident['trigger_summary_data'])

        if not issue:
            if self.__actionConfig.check(logEntry['type'], 'create'):
                self.__jira.createIssue(project = {'key': projectKey},
                                        issuetype = self.__jira.issuetype(issuetypeName),
                                        summary = self.__issueSummary(incident['trigger_summary_data']),
                                        description = self.__description(logEntry['channel']),
                                        assignee = {'name': self.__usernameFromEmail(incident['assigned_to_user']['email'])})
        else:
            if self.__actionConfig.has_option(logEntry['type'], 'transition'):
                transition = issue.transition(self.__actionConfig.get(logEntry['type'], 'transition'))
                if transition:
                    issue.transit(transition, self.__generateComment(logEntry))

            if self.__actionConfig.check(logEntry['type'], 'assign'):
                issue.updateAssignee(self.__usernameFromEmail(logEntry['assigned_user']['email']))

            if self.__actionConfig.check(logEntry['type'], 'comment'):
                issue.addComment(self.__generateComment(logEntry))

            if self.__actionConfig.check(logEntry['type'], 'link'):
                issue.addRemotelink(str(incident), url = incident['html_url'],
                                    title = 'Incident #' + str(incident['incident_number']),
                                    status = {'resolved': incident['status'] == 'resolved'})

    def __findIssue(self, projectKey, issuetypeName, summary):
        '''Search by the hostname:'''
        if 'HOSTNAME' in summary and summary['HOSTNAME']:
            return self.__jira.searchIssue(projectKey, issuetypeName, summary['HOSTNAME'])

        '''Search by the issue key on the subject:'''
        '''It is usefull for incidents created by Jira emails.'''
        import re
        issueKeys = re.findall('\([A-Z]{3,6}-[0-9]{1,6}\)', summary['subject'])
        if issueKeys:
            return Issue(self.__jira, {'key': issueKeys[0][1:-1]})

        '''Search by the subject:'''
        return self.__jira.searchIssue(projectKey, issuetypeName, summary['subject'])

    def __issueSummary(self, summary):
        if 'SERVICESTATE' in summary and summary['SERVICESTATE']:
            return summary['HOSTNAME'] + ' ' + summary['SERVICEDESC'] + ' ' + summary['SERVICESTATE']
        if 'HOSTSTATE' in summary and summary['HOSTSTATE']:
            return summary['HOSTNAME'] + ' ' + summary['HOSTSTATE']
        return summary['subject']

    def __usernameFromEmail(self, email):
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

    def __generateComment(self, logEntry):
        '''Subject:'''
        if logEntry['type'] == 'notify':
            body = '[~' + self.__usernameFromEmail(logEntry['user']['email']) + ']'
        else:
            body = 'Incident #' + str(logEntry.incident()['incident_number'])

        '''Auxiliary:'''
        body += ' has'
        if 'channel' in logEntry and logEntry['channel']['type'] == 'auto' and 'assigned_user' not in logEntry:
            '''Automatically adverb does not added if assigned user exists because the verb changed to escalated
            if it is automatically assigned.'''
            body += ' automatically'
        elif 'notification' in logEntry:
            if logEntry['notification']['status'] == 'success':
                body += ' successfully'
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
                body += ' by [~' + self.__usernameFromEmail(logEntry['agent']['email']) + ']'
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
            elif logEntry['notification']['type'] == 'sms':
                body += ' via SMS'
            else:
                body += ' via ' + logEntry['notification']['type']
            body += ' at ' + logEntry['notification']['address']
            if logEntry['notification']['status'] == 'no_answer':
                    body += ' but nobody answered'
        if 'assigned_user' in logEntry:
            body += ' to [~' + self.__usernameFromEmail(logEntry['assigned_user']['email']) + ']'
        if 'note' in logEntry and logEntry['note']:
            body += ' with note: ' + logEntry['note']

        return body + '.'

