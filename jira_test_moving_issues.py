#!/usr/bin/env python3

from jira import move_issues_to_board
import os
import sys

board_id = 15
issues = ["WL-318", "WL-315", "WL-313", "WL-306", "WL-265", "WL-229"]
try:
    api_token=os.environ['JIRA_TOKEN']
    email_address=os.environ['JIRA_EMAIL']
except KeyError:
    print("""At least one of the following environment variables: JIRA_TOKEN, JIRA_EMAIL is not defined.
        Set `JIRA_EMAIL` with Jira login email address, `JIRA_TOKEN` with actual Jira API Token value, then run again""")
    exit(1)
except:
    print("Unexpected error:", sys.exc_info()[0])
    raise

def main():
    for i in range(333, 337):
        issues.append("WL-{}".format(i))
    for i in range(321, 323):
        issues.append("WL-{}".format(i))
    for i in range(242, 245):
        issues.append("WL-{}".format(i))
    response = move_issues_to_board(
            email_address,
            api_token,
            board_id,
            issues
    )
    print(response)

if __name__ == "__main__":
    main()