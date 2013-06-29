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

    def __issue(self, incident):
        key = incident.issueKey()
        if key:
            return Issue({'key': key})
        return self.__jira.lastIssueBySummary(incident.summary().split(' - ')[0])

    def __process(self, logEntry):
        '''Process incidents with the log entry and the incident related to the log entry.'''
        incident = logEntry.incident()
        issue = self.__issue(incident)

        if not self.__actionConfig.filter(logEntry['type'], 'status', incident['status']):
            if not issue:
                if self.__actionConfig.check(logEntry['type'], 'create'):
                    if self.__serviceConfig.has_section(logEntry['service']['name']):
                        projectKey = self.__serviceConfig.get(logEntry['service']['name'], 'project')
                        issueTypeName = self.__serviceConfig.get(logEntry['service']['name'], 'type')
                        self.__jira.createIssue(project = {'key': projectKey},
                                                issuetype = self.__jira.issueType(issueTypeName),
                                                summary = incident.summary(),
                                                description = logEntry.description())
            else:
                if self.__actionConfig.has_option(logEntry['type'], 'transition'):
                    transition = self.__jira.transition(issue, self.__actionConfig.get(logEntry['type'], 'transition'))
                    if transition:
                        self.__jira.transit(issue, transition, logEntry.comment())

                if self.__actionConfig.check(logEntry['type'], 'assign'):
                    self.__jira.updateAssignee(issue, logEntry.username('assigned_user'))

                if self.__actionConfig.check(logEntry['type'], 'comment'):
                    self.__jira.addComment(issue, logEntry.comment())

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

