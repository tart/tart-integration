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

import re

from .jira import JiraClient, Issue
from .pagerduty import PagerDutyClient
from .configuration import ConfigParser
from .database import TimestampDatabase

class PagerDutyJira:
    def __init__(self):
        config = ConfigParser('api.conf')
        self.__jira = JiraClient(**dict(config.items('Jira')))
        self.__pagerDuty = PagerDutyClient(**dict(config.items('PagerDuty')))
        self.__actionConfig = ConfigParser('action.conf')
        self.__serviceConfig = ConfigParser('service.conf')

    checkPagerDutyTimestampFile = '/tmp/tart-integration.pagerduty.ts'

    def checkPagerDuty(self):
        with TimestampDatabase(self.checkPagerDutyTimestampFile) as database:
            for logEntry in self.__pagerDuty.logEntries(database.read()):
                if 'notification' in logEntry and logEntry['notification']['status'] == 'in_progress':
                    '''Stop progress for now to buy time.'''
                    break
                self.__processLogEntry(logEntry)
                database.write(logEntry['created_at'])

    checkJiraTimestampFile = '/tmp/tart-integration.jira.ts'

    def checkJira(self):
        with TimestampDatabase(self.checkJiraTimestampFile) as database:
            for issue in self.__jira.updatedIssues(self.__serviceConfig.sectionValues('project', 'type'),
                                                   database.read()):
                for remotelink in issue.getUnresolvedRemotelinks():
                    for action in self.__actionConfig.sections():
                        if self.__matchAction(action, issue):
                            incident = self.__pagerDuty.getIncident(remotelink['globalId'])

                            if incident['status'] != self.__incidentStatus(action):
                                incident.put(action)

                database.write(issue['fields']['updated'])

    def __matchAction(self, action, issue):
        if self.__actionConfig.filter(action, 'match-status', issue['fields']['status']['name']):
            return True
        if self.__actionConfig.filter(action, 'match-priority', issue['fields']['priority']['name']):
            return True
        return False

    def __incidentStatus(self, action):
        if action == 'resolve':
            return 'resolved'
        if action == 'acknowledge':
            return 'acknowledged'
        return 'triggered'

    def __processLogEntry(self, logEntry):
        '''Process incidents with the log entry and the incident related to the log entry.'''
        if not self.__serviceConfig.has_section(logEntry['service']['name']):
            return

        if not self.__actionConfig.has_section(logEntry['type']):
            return

        projectKey = self.__serviceConfig.get(logEntry['service']['name'], 'project')
        issuetypeName = self.__serviceConfig.get(logEntry['service']['name'], 'type')
        incident = logEntry.incident()
        issue = self.__findIssue(projectKey, issuetypeName, incident['trigger_summary_data'])

        if not issue and incident['status'] != 'resolved':
            '''Do not create issues for incidents already resolved on the PagerDuty. It is too late for them.'''

            if self.__actionConfig.check(logEntry['type'], 'create'):
                fields = {}
                fields['project'] = {'key': projectKey}
                fields['issuetype'] = self.__jira.issuetype(issuetypeName)
                fields['summary'] = self.__issueSummary(incident['trigger_summary_data'])
                fields['description'] = self.__description(logEntry['channel'])

                jiraUser = self.__jira.getUser(incident['assigned_to_user']['email'])
                if jiraUser:
                    fields['assignee'] = jiraUser

                if self.__serviceConfig.has_option(logEntry['service']['name'], 'create-priority'):
                    priorityName = self.__serviceConfig.get(logEntry['service']['name'], 'create-priority')
                    fields['priority'] = self.__jira.priority(priorityName)

                issue = self.__jira.createIssue(fields)

        if issue:
            if self.__actionConfig.has_option(logEntry['type'], 'transition'):
                transition = issue.transition(self.__actionConfig.get(logEntry['type'], 'transition'))
                if transition:
                    issue.transit(transition, self.__generateComment(logEntry))

            if self.__actionConfig.check(logEntry['type'], 'assign'):
                jiraUser = self.__jira.getUser(logEntry['assigned_user']['email'])
                if jiraUser:
                    issue.updateAssignee(jiraUser)

            if self.__actionConfig.check(logEntry['type'], 'comment'):
                issue.addComment(self.__generateComment(logEntry))

            if self.__actionConfig.check(logEntry['type'], 'link'):
                issue.addRemotelink(str(incident), url = incident['html_url'],
                        title = 'Incident #' + str(incident['incident_number']),
                        status = {'resolved': incident['status'] == 'resolved'})

    issueSummarySplitters = ['\t', ' - ']

    def __findIssue(self, projectKey, issuetypeName, summary):
        issueSummary = self.__issueSummary(summary)
        for splitter in self.issueSummarySplitters:
            issueSummary = issueSummary.split(splitter, 1)[0]

        '''First, search by the issue key on the subject. It is usefull for incidents created by Jira emails.
        Issue type does not matter.'''
        issueKeys = re.findall(projectKey + '-[0-9]{1,6}', issueSummary)
        if issueKeys:
            return Issue(self.__jira, {'key': issueKeys[0]})
        return self.__jira.searchIssue(projectKey, issuetypeName, issueSummary)

    def __issueSummary(self, summary):
        if 'SERVICESTATE' in summary and summary['SERVICESTATE']:
            return summary['HOSTNAME'] + ' ' + summary['SERVICEDESC'] + ' ' + summary['SERVICESTATE']
        if 'HOSTSTATE' in summary and summary['HOSTSTATE']:
            return summary['HOSTNAME'] + ' ' + summary['HOSTSTATE']
        return summary['subject']

    descriptionDetails = ('HOSTDISPLAYNAME', 'HOSTALIAS', 'HOSTADDRESS', 'HOSTOUTPUT',
            'SERVICEDISPLAYNAME', 'SERVICEOUTPUT', 'SERVICECHECKTYPE', 'SERVICEATTEMPT',
            'SERVICECHECKCOMMAND', 'TOTALSERVICEPROBLEMS', 'SERVICELATENCY',
            'SERVICENOTES', 'HOSTNOTES')

    def __description(self, channel):
        body = ''
        for detail in self.descriptionDetails:
            if detail in channel['details'] and channel['details'][detail]:
                body += ' '.join(self.__wordsOfDetail(detail.strip('_ ').lower())).capitalize() + ': '
                body += channel['details'][detail] + '\n'
        return body

    detailWords = 'host', 'service', 'display', 'check', 'total'

    def __wordsOfDetail(self, detail):
        for word in self.detailWords:
            if detail[:len(word)] == word:
                return [word] + self.__wordsOfDetail(detail[len(word):])
        return [detail]

    def __generateComment(self, logEntry):
        '''Subject:'''
        if logEntry['type'] == 'notify':
            body = self.__annotation(logEntry['user'])
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
                body += ' by ' + self.__annotation(logEntry['agent'])
        if 'channel' in logEntry:
            if logEntry['channel']['type'] == 'timeout':
                body += ' due to timeout'
            elif logEntry['channel']['type'] == 'api':
                body += ' through the API'
            elif logEntry['channel']['type'] == 'website':
                body += ' on the website'
            elif logEntry['channel']['type'] == 'nagios':
                body += ' by the Nagios'
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
            body += ' to ' + self.__annotation(logEntry['assigned_user'])

        if 'channel' in logEntry and logEntry['channel']['type'] == 'note':
            return body + ': ' + logEntry['channel']['content']
        return body + '.'

    def __annotation(self, user):
        jiraUser = self.__jira.getUser(user['email'])
        if jiraUser:
            return '[~' + jiraUser['name'] + ']'
        return user['name'] + ' <' + user['email'] + '>'

