#!/usr/bin/env python3

import requests
from requests.auth import HTTPBasicAuth
import json
import os
import sys
import argparse

ENV_ARGS_MAP = {

}

ISSUE_TYPE_TO_ID_MAP = {
    "EPIC": 10085,
    "STORY": 10086,
    "TASK": 10083,
    "SUBTASK": 10084
}

url = "https://devops-workspace.atlassian.net/rest/api/3/issue"

PARSER = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter
    )

PARSER.add_argument('-j','--jiraProject', required=True, help='Jira Project Key where new issues to be created')
PARSER.add_argument('-e','--jiraEpic', required=True, help='Jira Epic Key where new issues to be created')

ARGUMENTS = PARSER.parse_args()
PROJ_KEY=ARGUMENTS.jiraProject
EPIC=ARGUMENTS.jiraEpic

try:
    api_token=os.environ['JIRA_TOKEN']
    email_address=os.environ['JIRA_EMAIL']
except KeyError:
    print("At least one of the following environment variables JIRA_TOKEN, JIRA_EMAIL is not defined. Set `JIRA_EMAIL` with Jira login email address and `JIRA_TOKEN` with actual Jira API Token value and run again")
    exit(1)
except:
    print("Unexpected error:", sys.exc_info()[0])
    raise

auth = HTTPBasicAuth(email_address, api_token)

headers = {
  "Accept": "application/json",
  "Content-Type": "application/json"
}

# payload = json.dumps( {
#   "fields": {
#     "issuetype": {
#       "id": "10086"
#     },
#     "parent": {
#       "key": EPIC
#     },
#     "project": {
#       "key": PROJ_KEY
#     },
#     "summary": "Hello from python script",
#   },
#   "update": {}
# } )

# response = requests.request(
#    "POST",
#    url,
#    data=payload,
#    headers=headers,
#    auth=auth
# )

#print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
#print(response.text["key"])
# print(json.loads(response.text)["key"])



# payload = json.dumps( {
#   "fields": {
#     "assignee": {
#       "id": "5b109f2e9729b51b54dc274d"
#     },
#     "components": [
#       {
#         "id": "10000"
#       }
#     ],
#     "customfield_10000": "09/Jun/19",
#     "customfield_20000": "06/Jul/19 3:25 PM",
#     "customfield_30000": [
#       "10000",
#       "10002"
#     ],
#     "customfield_40000": {
#       "content": [
#         {
#           "content": [
#             {
#               "text": "Occurs on all orders",
#               "type": "text"
#             }
#           ],
#           "type": "paragraph"
#         }
#       ],
#       "type": "doc",
#       "version": 1
#     },
#     "customfield_50000": {
#       "content": [
#         {
#           "content": [
#             {
#               "text": "Could impact day-to-day work.",
#               "type": "text"
#             }
#           ],
#           "type": "paragraph"
#         }
#       ],
#       "type": "doc",
#       "version": 1
#     },
#     "customfield_60000": "jira-software-users",
#     "customfield_70000": [
#       "jira-administrators",
#       "jira-software-users"
#     ],
#     "customfield_80000": {
#       "value": "red"
#     },
#     "description": {
#       "content": [
#         {
#           "content": [
#             {
#               "text": "Order entry fails when selecting supplier.",
#               "type": "text"
#             }
#           ],
#           "type": "paragraph"
#         }
#       ],
#       "type": "doc",
#       "version": 1
#     },
#     "duedate": "2019-05-11",
#     "environment": {
#       "content": [
#         {
#           "content": [
#             {
#               "text": "UAT",
#               "type": "text"
#             }
#           ],
#           "type": "paragraph"
#         }
#       ],
#       "type": "doc",
#       "version": 1
#     },
#     "fixVersions": [
#       {
#         "id": "10001"
#       }
#     ],
#     "issuetype": {
#       "id": "10000"
#     },
#     "labels": [
#       "bugfix",
#       "blitz_test"
#     ],
#     "parent": {
#       "key": "PROJ-123"
#     },
#     "priority": {
#       "id": "20000"
#     },
#     "project": {
#       "id": "10000"
#     },
#     "reporter": {
#       "id": "5b10a2844c20165700ede21g"
#     },
#     "security": {
#       "id": "10000"
#     },
#     "summary": "Main order flow broken",
#     "timetracking": {
#       "originalEstimate": "10",
#       "remainingEstimate": "5"
#     },
#     "versions": [
#       {
#         "id": "10000"
#       }
#     ]
#   },
#   "update": {}
# } )


# def get_issue_types(auth, project_id):
#     issue_types_url =  "https://devops-workspace.atlassian.net/rest/api/3/project/{}".format(project_id)
#     response = requests.request(
#         "GET",
#         issue_types_url,
#         headers=headers,
#         auth=auth
#     )
#     print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))


def main():
    # auth = HTTPBasicAuth(email_address, api_token)
    from jira import get_issue_types
    issueTypes = get_issue_types(auth, PROJ_KEY)
    print(json.dumps(issueTypes, sort_keys=True, indent=4, separators=(",", ": ")))


if __name__ == "__main__":
    main()