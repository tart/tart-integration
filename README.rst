Currently only PagerDuty and Jira integration supported. The script
will check both PagerDuty and Jira based on the configurations.
Configurations explained below.


Dependencies
------------

* Python 3


Usage
-----

Configure PagerDuty:

* Generate an API key or create an user if you want incidents to
  be updated.

* Modify the API configuration file explained below.


Configure Jira:

* Create an user with required privileges.

* Add the user credentials to the API configuration file explained
  below.


Configure Jira to trigger incidents with email (optional):

* Create a generic email system service on the PagerDuty.

* Give the same email address to the user on the Jira.

* Set the Jira email type to plain text on the user preferences.

* Make sure "Do not notify me" choosed for "My changes" option
  on the user preferences to avoid recursion.

* Add email filters to the service to match the project name,
  the issue type and the assignee.

* Add the service to the service configuration explained below
  to integrate them both ways.


Execute the script:

$ ./integrate.py

$ python3.2 integrate.py

The script must be run on the same directory with the configuration
files.


Add it to the cron like this:

$ cd tart-integration && ./integrate.py


API Configuration
-----------------

Configuration file named api.conf defines API connections. Section names
should match the required applications names. Currently, Jira and
PagerDuty are the supported sections. See the example configuration.

address
    Root address of the RESTful API (required)

username
    Username for HTTP basic authentication (optional)

password
    Password for HTTP basic authentication (required with username)

token
    Token for HTTP authentication (optional)

syslog
    Log the API requests to syslog (default: no)

application
    Application type to use on remote links on the Jira (required to
    find back incidents), also ident for syslog

Application type can also used for Issue Link Renderer Plugin Module [1]
of the Jira.

"DEFAULT" is the special section. Parameters can be set as default
in this section of all configuration files.

[1] https://developer.atlassian.com/display/JIRADEV/Issue+Link+Renderer+Plugin+Module


Action Configuration
--------------------

Configuration file named action.conf defines the actions of the script.
Section names should match the the action names on the source API.
Currently the source API is PagerDuty. The actions on PagerDuty are listed
as Log Entry Types on their API documentation [1].

Current action configuration will probably fit to your usecase. See the
default configuration.

link
    Action to create issue if not found (default: no)

transition
    Transition for the found issues (optional)

link
    Action to add application link to the found issues, issue links are
    used to find incidents, incidents will be updated if they can be
    found so it is is required to this on the "trigger" action
    (default: no)

assign
    Action to assign the found issues (default: no)

comment
    Action to add comment to the found issues, comments will be added
    with transitions independently (default: no)

match-status
    Issue status or statuses to update the incidents (optional)

match-priority
    Issue priority or priorities to update the incidents (optional)

Parameters starting with "match-" are to update incidents on PagerDuty.
They would only work with "acknowledge", "resolve" and "reassign"
actions as they are the only methods [1] on the PagerDuty REST API.
A user should be created on PagerDuty, username and password must be
set on the API configuration for this functionality.

[1] http://developer.pagerduty.com/documentation/rest/log_entries/show


Service Configuration
---------------------

Configuration file named service.conf defines the relation of services.
Section names should match the the service names on the source API. 

project
    Key of the project for the issues (required)

type
    Name of the issue type for the issues (required)

create-priority
    Name of the issue priority to create issues (optional)


License
-------

This tool is released under the ISC License, whose text is included to the
source file. The ISC License is registered with and approved by the
Open Source Initiative [1].

[1] http://opensource.org/licenses/isc-license.txt

