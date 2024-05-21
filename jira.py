# it'd be better to implement object-orientated approach, and create auth object and issue_name_to_id map in the init method

import requests
from requests.auth import HTTPBasicAuth
import json
import re
# import os
# import sys
# import argparse

ENV_ARGS_MAP = {

}

# WTB:
# ISSUE_TYPE_TO_ID_MAP = {
#     "EPIC": 10085,
#     "STORY": 10086,
#     "TASK": 10083,
#     "SUBTASK": 10084
# }

# WL:
# ISSUE_TYPE_TO_ID_MAP = {
#     "EPIC": 10099,
#     "STORY": 10096,
#     "TASK": 10097,
#     "SUBTASK": 10100
# }

base_url = "https://devops-workspace.atlassian.net/rest"
issues_path = "/api/3/issue"
issues_url = "{}{}".format(base_url, issues_path)
boards_path = "/agile/1.0/board"
boards_url = "{}{}".format(base_url, boards_path)


# PARSER = argparse.ArgumentParser(
#     formatter_class=argparse.RawDescriptionHelpFormatter
#     )

# PARSER.add_argument('-j','--jiraProject', required=True, help='Jira Project Key where new issues to be created')
# PARSER.add_argument('-e','--jiraEpic', required=True, help='Jira Epic Key where new issues to be created')

# ARGUMENTS = PARSER.parse_args()
# PROJ_KEY=ARGUMENTS.jiraProject
# EPIC=ARGUMENTS.jiraEpic

# try:
#     api_token=os.environ['JIRA_TOKEN']
#     email_address=os.environ['JIRA_EMAIL']
# except KeyError:
#     print("At least one of the following environment variables JIRA_TOKEN, JIRA_EMAIL is not defined. Set `JIRA_EMAIL` with Jira login email address and `JIRA_TOKEN` with actual Jira API Token value and run again")
#     exit(1)
# except:
#     print("Unexpected error:", sys.exc_info()[0])
#     raise

headers = {
  "Accept": "application/json",
  "Content-Type": "application/json"
}

def unify_issue_name(name: str):
    return re.sub('[^A-Za-z0-9]+', '', name).upper()

def get_issue_type_id(auth, project_id, issue_type):
    issue_types_url =  "https://devops-workspace.atlassian.net/rest/api/3/project/{}".format(project_id)
    response = requests.request(
        "GET",
        issue_types_url,
        headers=headers,
        auth=auth
    )
    issue_types = {}
    # print(json.loads(response.text))
    for it in json.loads(response.text)["issueTypes"]:
        # issue_types[it["name"]] = it["id"]
        issue_types[unify_issue_name(it["name"])] = it["id"]
    return issue_types[unify_issue_name(issue_type)]

# def get_transition_id():

def create_issue(
        email_address,
        api_token,
        issue_type,
        pillar_label,
        parent,
        proj_key,
        summary,
        link
):

    auth = HTTPBasicAuth(email_address, api_token)
    payload = json.dumps( {
        "fields": {
            "description": {
            "version": 1,
            "type": "doc",
            "content": [
                {
                "type": "paragraph",
                "content": [
                    {
                    "type": "text",
                    "text": summary,
                    "marks": [
                        {
                        "type": "link",
                        "attrs": {
                            "href": link
                        }
                        }
                    ]
                    }
                ]
                }
            ]
            },
            "issuetype": {
            "id": get_issue_type_id(auth, proj_key, issue_type)
            },
            "labels": [
            pillar_label
            ],
            "parent": {
            "key": parent
            },
            "project": {
            "key": proj_key
            },
            "summary": summary.replace("\n", ""),
        },
        "update": {}
    } )

    response = requests.request(
        "POST",
        issues_url,
        data=payload,
        headers=headers,
        auth=auth
    )

    # print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
    return json.loads(response.text)["key"]

def get_transition_id_by_name(
        email_address,
        api_token,
        issue_key,
        transition_name  
):
    url = "{}/{}/transitions".format(issues_url, issue_key)
    auth = HTTPBasicAuth(email_address, api_token)
    response = requests.request(
        "GET",
        url,
        headers=headers,
        auth=auth
    )
    for tr in json.loads(response.text)["transitions"]:
        if tr["name"].upper() == transition_name.upper():
            return tr["id"]
    return None

def transit_issue(
        email_address,
        api_token,
        issue_key,
        transition_id
):

    url = "{}/{}/transitions".format(issues_url, issue_key)
    auth = HTTPBasicAuth(email_address, api_token)

    payload = json.dumps( {
        "transition": {
            "id": transition_id
        },
        "update": {
            "comment": [
            {
                "add": {
                "body": {
                    "content": [
                    {
                        "content": [
                        {
                            "text": "Updated with Python script",
                            "type": "text"
                        }
                        ],
                        "type": "paragraph"
                    }
                    ],
                    "type": "doc",
                    "version": 1
                }
                }
            }
            ]
        }
    } )

    response = requests.request(
        "POST",
        url,
        data=payload,
        headers=headers,
        auth=auth
    )

    #print(json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": ")))
    return response.status_code

def move_issues_to_board(
        email_address,
        api_token,
        board_id,
        issues: list
):
    url = "{}/{}/issue".format(boards_url, board_id)
    auth = HTTPBasicAuth(email_address, api_token)
    headers["Authorization"] = "Bearer {}:{}".format(email_address, api_token)
    payload = json.dumps( {
        "issues": issues
    } )
    # print(payload)

    response = requests.request(
        "POST",
        url,
        data=payload,
        headers=headers,
        auth=auth
    )
    return response.status_code