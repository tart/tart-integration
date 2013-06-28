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

    def issueKey(self):
        if 'trigger_summary_data' in self:
            summary = self['trigger_summary_data']
            if 'subject' in summary and summary['subject']:
                issueKeys = re.findall('\([A-Z]{3,6}-[0-9]{1,6}\)', summary['subject'])
                if issueKeys:
                    return issueKeys[0][1:-1]

    def summary(self):
        if 'trigger_summary_data' in self:
            summary = self['trigger_summary_data']
            if 'subject' in summary and summary['subject']:
                return summary['subject']
            if 'SERVICESTATE' in summary and summary['SERVICESTATE']:
                return summary['HOSTNAME'] + ' ' + summary['SERVICEDESC'] + ' ' + summary['SERVICESTATE']
            if 'HOSTSTATE' in summary and summary['HOSTSTATE']:
                return summary['HOSTNAME'] + ' ' + summary['HOSTSTATE']
        return self['incident_key']

class LogEntry(dict):
    def __str__(self):
        return str(self['id'])

    def username(self, key='user'):
        if self[key]:
            email = self[key]['email']
            return email.split('@')[0]

    def incident(self):
        return Incident(self['incident'])

    def description(self):
        body = ''
        if 'channel' in self:
            if self['channel']['type'] == 'nagios':
                if self['channel']['details']['HOSTALIAS']:
                    body += 'Host alias: ' + self['channel']['details']['HOSTALIAS'] + '\n'
                body += 'Host address: ' + self['channel']['details']['HOSTADDRESS'] + '\n'
                body += 'Host output: ' + self['channel']['details']['HOSTOUTPUT'] + '\n'
                if self['channel']['details']['SERVICEDISPLAYNAME']:
                    body += 'Service name: ' + self['channel']['details']['SERVICEDISPLAYNAME'] + '\n'
                if self['channel']['details']['SERVICEOUTPUT']:
                    body += 'Service output: ' + self['channel']['details']['SERVICEOUTPUT'] + '\n'
                if self['channel']['details']['SERVICENOTES']:
                    body += 'Note: ' + self['channel']['details']['SERVICENOTES'] + '\n'
                elif self['channel']['details']['HOSTNOTES']:
                    body += 'Note: ' + self['channel']['details']['HOSTNOTES'] + '\n'
        return body

    def comment(self):
        '''Subject:'''
        if self['type'] == 'notify':
            body = '[~' + self.username() + ']'
        else:
            body = 'Incident ' + str(self.incident())

        '''Auxiliary:'''
        body += ' has'
        if 'channel' in self and self['channel']['type'] == 'auto' and 'assigned_user' not in self:
            '''Automatically adverb does not added if assigned user exists because the verb changed to escalated
            if it is automatically assigned.'''
            body += ' automatically'
        elif 'notification' in self:
            if self['notification']['status'] == 'success':
                body += ' successfully'
            elif self['notification']['status'] == 'in_progress':
                '''Exception raised to buy time.'''
                raise Exception('Notification in progress.')
            elif self['notification']['status'] != 'no_answer':
                '''Log entries include only the current status of the notifiations which is not enough to say
                something for certain.'''
                body += ' possibly'

        '''Predicate:'''
        body += ' been'
        if self['type'] == 'reach_trigger_limit':
            body += ' reached the log entry trigger limit and will not create any more'
        elif self['type'] == 'repeat_escalation_path':
            body += ' reached the end of its escalation policy and will restart'
        elif self['type'] == 'exhaust_escalation_path':
            body += ' cycled through its escalation policy the max allowed number of times'
        elif self['type'][-1:] == 'y':
            body += ' ' + self['type'][:-1] + 'ied'
        elif self['type'][-1:] == 'e':
            body += ' ' + self['type'] + 'd'
        else:
            body += ' ' + self['type'] + 'ed'

        '''Prepositional Phrase:'''
        if 'agent' in self:
            if self['agent']['type'] == 'user':
                body += ' by [~' + self.username('agent') + ']'
        if 'channel' in self:
            if self['channel']['type'] == 'timeout':
                body += ' due to timeout'
            elif self['channel']['type'] == 'api':
                body += ' through the API'
            elif self['channel']['type'] == 'website':
                body += ' on the website'
            elif self['channel']['type'] == 'nagios':
                body += ' by the Nagios'
            elif self['channel']['type'] != 'auto':
                body += ' by ' + self['channel']['type']
        if 'notification' in self:
            if 'push_notification' in self['notification']['type']:
                body += ' via push notification'
            else:
                body += ' via ' + self['notification']['type']
            body += ' at ' + self['notification']['address']
            if self['notification']['status'] == 'no_answer':
                    body += ' but nobody answered'
        if 'assigned_user' in self:
            body += ' to [~' + self.username('assigned_user') + ']'
        if 'note' in self and self['note']:
            body += ' with note: ' + self['note']

        return body + '.'

class PagerDutyClient(JSONAPI):
    def logEntries(self, since):
        '''Get log entries. Return them reverse ordered as they come with right descending order.'''
        logEntries = self.get('log_entries', since=since, include=['incident', 'channel', 'service'])['log_entries']
        return (LogEntry(item) for item in reversed(logEntries) if item['created_at'] > since)

