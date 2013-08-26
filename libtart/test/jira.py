from libtart.jira import JiraClient
from configparser import SafeConfigParser
from datetime import date

configParser = SafeConfigParser()
configParser.read('api.conf')

jira = JiraClient(**dict(configParser.items('Jira')))
jira.searchIssue('TSS', 'System Problem', 'loadbalancer.tart.local')
jira.updatedIssues([('TSS', 'System Problem')], date.today().isoformat())

