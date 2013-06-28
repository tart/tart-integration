from ..jira import JiraClient

configParser = SafeConfigParser()
configParser.read('service.conf')

jira = JiraClient(**dict(configParser.items('Jira')))
jira.lastIssueBySummary('loadbalancer.tart.local HTTP CRITICAL')

