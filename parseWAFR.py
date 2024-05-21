#!/usr/bin/env python3

import json
import logging
import sys
import os

import argparse
import botocore
import boto3
from jira import create_issue, transit_issue, get_transition_id_by_name, move_issues_to_board
from parseAwsDocWebPages import parse_web_page
from pkg_resources import packaging

response = ""


# Setup Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger()
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
PARSER = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    )

DEFAULT_LENS_ALIAS="wellarchitected"

try:
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID']
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    aws_session_token=os.environ['AWS_SESSION_TOKEN']
    api_token=os.environ['JIRA_TOKEN']
    email_address=os.environ['JIRA_EMAIL']
except KeyError:
    print("""At least one of the following environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, JIRA_TOKEN, JIRA_EMAIL is not defined.
          Set `JIRA_EMAIL` with Jira login email address, `JIRA_TOKEN` with actual Jira API Token value, and AWS-based ones with appropriate values, then run again""")
    exit(1)
except:
    print("Unexpected error:", sys.exc_info()[0])
    raise

PARSER = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter
    )

PARSER.add_argument('-p','--profile', required=False, default="default", help='AWS CLI Profile Name')
PARSER.add_argument('-r','--region', required=False, default="eu-central-1", help='From Region Name. Example: us-east-1')
PARSER.add_argument('-w','--workloadId', required=True, help='Workload Id to use instead of creating a TEMP workload')
PARSER.add_argument('-m','--milestoneNumber', required=False, default=1, help='Milestone number to take answers from')
#PARSER.add_argument('-a','--lensAlias', required=False, default=DEFAULT_LENS_ALIAS, help='Lense alias which questions to take from') #do we need it? page parsing won't work for other lenses 
PARSER.add_argument('-l','--lensVersion', required=False, default="latest", help='Lense version which questions to take from and appropriately for builing link to documentation')
PARSER.add_argument('-j','--jiraProject', required=True, help='Jira Project Key where new issues to be created')
PARSER.add_argument('-e','--jiraEpic', required=True, help='Jira Epic Key where new issues to be created')
PARSER.add_argument('-b','--jiraBoard', required=False, default="15", help='Jira board ID where to move created tasks')
PARSER.add_argument('-v','--debug', action='store_true', help='print debug messages to stderr')
PARSER.add_argument('-n','--doNotMoveToBoard', action='store_true', help='do not move tasks to board')

ARGUMENTS = PARSER.parse_args()
PROFILE=ARGUMENTS.profile
REGION=ARGUMENTS.region
WORKLOAD_ID=ARGUMENTS.workloadId
MILESTONE_NUMBER=ARGUMENTS.milestoneNumber
#LENS_ALIAS=ARGUMENTS.lensAlias
LENS_ALIAS=DEFAULT_LENS_ALIAS
LENS_VERSION=ARGUMENTS.lensVersion
PROJ_KEY=ARGUMENTS.jiraProject
EPIC=ARGUMENTS.jiraEpic
BOARD_ID=ARGUMENTS.jiraBoard

if ARGUMENTS.debug:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

#JIRA_WAS_DONE_TRANSITION_ID = 11    # WTB
#JIRA_WAS_DONE_TRANSITION_ID = 10     # WL
global JIRA_WAS_DONE_TRANSITION_ID    # to find by name (JIRA_WAS_DONE_TRANSITION_NAME)
JIRA_WAS_DONE_TRANSITION_NAME = "was selected"

PILLAR_PARSE_MAP = {
                    "operationalExcellence": "OPS",
                    "security": "SEC",
                    "reliability": "REL",
                    "performance": "PERF",
                    "costOptimization": "COST",
                    "sustainability": "SUS"
                    }

def generate_question_page_name(code: str, index: int):
    return "{}-{}".format(code.lower(), index if index > 9 else "0{}".format(index))

def is_choice_applied(choice_id: str, choice_answer_summaries: list):
    if len(choice_answer_summaries) == 0:
        return True
    for summary in choice_answer_summaries:
        if summary["ChoiceId"] == choice_id:
            return summary["Status"] != "NOT_APPLICABLE"
    return True


def get_hri_choises(answer):
    logger.debug("%s" % json.dumps(answer, indent = 4))
    logger.debug("%s" % answer["ChoiceAnswerSummaries"])
    hri_choices = []
    choice_id_risk_level_map = {}
    choices = answer["Choices"]
    for i, choice in enumerate(choices):
        logger.debug("%s" % json.dumps(choice, indent = 4))
        if choice["Title"] == "None of these":
            continue
        choice_id = choice["ChoiceId"]
        url = "https://docs.aws.amazon.com/wellarchitected/{}/framework/{}.html".format(LENS_VERSION, choice_id)
        risk_level = parse_web_page(url)
        # logger.info("Q: %s\nChoice: %s\nDetected risk: %s\nLink: %s\n" % (answer["QuestionTitle"],
        #                                                                 choice["Title"],
        #                                                                 risk_level,
        #                                                                 url))
        logger.info("Detected risk: %s\nLink: %s\n" % (risk_level, url))
        if risk_level is None:
            # Exception?
            logger.error("Could not find risk level on page: %s" % url)
        # Check if the statement (choice) has a high risk level and is not selected as done (and not marked as `not applied`) 
        else:
            choice_answer_summaries = answer["ChoiceAnswerSummaries"]
            if risk_level == 'High' and is_choice_applied(choice_id, choice_answer_summaries):
                choice["RiskLevel"] = risk_level
                choice["Selected"] = choice_id in answer["SelectedChoices"]
                choice["Documention"] = url
                hri_choices.append(choice)
        choice_id_risk_level_map[choice_id] = risk_level
    return hri_choices


def create_tasks(
        waclient,
        workloadId,
        lensAlias
):
    JIRA_WAS_DONE_TRANSITION_ID = None
    tasks = []
    for pillar in PILLAR_PARSE_MAP:
        answers = []
        logger.debug("Grabbing answers for %s %s" % (lensAlias, pillar))
        # Find a questionID using the questionTitle
        try:
            response=waclient.list_answers(
                WorkloadId=workloadId,
                LensAlias=lensAlias,
                PillarId=pillar
            )
        except botocore.exceptions.ParamValidationError as e:
            logger.error("ERROR - Parameter validation error: %s" % e)
        except botocore.exceptions.ClientError as e:
            logger.error("ERROR - Unexpected error: %s" % e)

        logger.debug("%s" % json.dumps(response, indent = 4))
        answers.extend(response["AnswerSummaries"])
        while "NextToken" in response:
            try:
                response = waclient.list_answers(WorkloadId=workloadId,
                                                 LensAlias=lensAlias,
                                                 PillarId=pillar,
                                                 NextToken=response["NextToken"])
            except botocore.exceptions.ParamValidationError as e:
                logger.error("ERROR - Parameter validation error: %s" % e)
            except botocore.exceptions.ClientError as e:
                logger.error("ERROR - Unexpected error: %s" % e)
            answers.extend(response["AnswerSummaries"])
            logger.debug("response: %s" % json.dumps(response, indent = 4))
            logger.debug("answers: %s" % json.dumps(answers, indent = 4))
        applicable_answers=[]
        for i, answer in enumerate(answers, start=1):
            logger.debug("%s: %s's risk is %s" % (pillar, answer["QuestionId"], answer["Risk"]))
            if answer["Risk"] != "NOT_APPLICABLE":
                answer["Index"] = i
                applicable_answers.append(answer)
        logger.debug("%s" % json.dumps(applicable_answers, indent = 4))
        for answer in applicable_answers:
            logger.debug("%s: %s: %s" % (pillar, answer["QuestionId"], answer["Risk"]))
            question_url = "https://docs.aws.amazon.com/wellarchitected/{}/framework/{}.html".format(
                                                                LENS_VERSION,
                                                                generate_question_page_name(
                                                                                            PILLAR_PARSE_MAP[pillar],
                                                                                            answer["Index"]
                                                                                        )
                                                            )
            task_id=create_issue(email_address,
                                 api_token,
                                 "TASK",
                                 "{}_pillar".format(pillar),
                                 EPIC,
                                 PROJ_KEY,
                                 answer["QuestionTitle"],
                                 question_url
            )
            logger.debug("issue_id=create_issue(%s, %s, %s, %s, %s, %s)" % (email_address,
                                                                            api_token,
                                                                            "TASK",
                                                                            EPIC,
                                                                            PROJ_KEY,
                                                                            answer["QuestionTitle"]))
            logger.debug("%s created" % task_id)
            logger.debug("creating issues")
            if JIRA_WAS_DONE_TRANSITION_ID is None:
                logger.info("JIRA_WAS_DONE_TRANSITION_ID is not defined, requesting transition id")
                JIRA_WAS_DONE_TRANSITION_ID = get_transition_id_by_name(
                    email_address,
                    api_token,
                    task_id,
                    JIRA_WAS_DONE_TRANSITION_NAME
                )
                logger.info("JIRA_WAS_DONE_TRANSITION_ID = %s" % JIRA_WAS_DONE_TRANSITION_ID)
                if JIRA_WAS_DONE_TRANSITION_ID is None:
                    logger.error("Could not find transition with name '%s' for %s" % (JIRA_WAS_DONE_TRANSITION_NAME,
                                                                                      task_id))
            logger.info("Applicable answer id = %s, task id = %s, risk level = %s" % (answer["QuestionId"],
                                                                                      task_id,
                                                                                      answer["Risk"]))
            if answer["Risk"] != "HIGH":
                logger.info("Transiting %s since all HRI choices of `%s` were selected" % (task_id,
                                                                                           answer["QuestionId"]))
                status_code = transit_issue(email_address,
                                            api_token,
                                            task_id,
                                            JIRA_WAS_DONE_TRANSITION_ID
                )
                logger.info("Transiting %s: status code is %s" % (task_id, status_code))
            tasks.append(task_id)
            if len(tasks) == 50 and not ARGUMENTS.doNotMoveToBoard:
                status_code = move_issues_to_board(
                              email_address,
                              api_token,
                              BOARD_ID,
                              tasks
                )
                logger.info("Moving 50 issues to the Jira Board with ID==%s: status code is %s" % (BOARD_ID, status_code))
                tasks = []
            hri_choices = get_hri_choises(answer)
            logger.debug("%s (%s), choices:\n%s\n\nHRI choices:\n%s\n\n" % (answer["QuestionTitle"],
                                                                           task_id,
                                                                           json.dumps(answer["Choices"], indent = 4),
                                                                           json.dumps(hri_choices, indent = 4)
                                                                           ))
            for choice in hri_choices:
                subtask_id=create_issue(email_address,
                                        api_token,
                                        "SUBTASK",
                                        "{}_pillar".format(pillar),
                                        task_id,
                                        PROJ_KEY,
                                        choice["Title"],
                                        choice["Documention"]
                )
                logger.debug("%s created" % subtask_id)
                if choice["Selected"]:
                    status_code = transit_issue(email_address,
                                                api_token,
                                                subtask_id,
                                                JIRA_WAS_DONE_TRANSITION_ID
                    )
                    logger.debug("Transiting %s: status code is %s" % (subtask_id, status_code))
        
        # logger.debug("%s" % (json.dumps(applicable_answers, indent = 4)))

    if not ARGUMENTS.doNotMoveToBoard:
        status_code = move_issues_to_board(
                        email_address,
                        api_token,
                        BOARD_ID,
                        tasks
        )
        logger.info("Moving remaining %s tasks to the Jira Board with ID==%s: status code is %s" % (len(tasks),
                                                                                                   BOARD_ID,
                                                                                                   status_code))

def main():
    """ Main program run """

    boto3_min_version = "1.16.38"
    # Verify if the version of Boto3 we are running has the wellarchitected APIs included
    if packaging.version.parse(boto3.__version__) < packaging.version.parse(boto3_min_version):
        logger.error("Your Boto3 version (%s) is less than %s. You must ugprade to run this script (pip3 upgrade boto3)" % (boto3.__version__, boto3_min_version))
        sys.exit()

    logger.info("Starting Boto %s Session" % boto3.__version__)

    # Create a new boto3 session
    SESSION1 = boto3.session.Session(aws_access_key_id=aws_access_key_id,
                                     aws_secret_access_key=aws_secret_access_key,
                                     aws_session_token=aws_session_token)
    WACLIENT = SESSION1.client(
        service_name='wellarchitected',
        region_name=REGION
    )
    create_tasks(WACLIENT, WORKLOAD_ID, LENS_ALIAS)
    logger.info("All applicable HRI answers and choices imported to Jira tasks and subtasks.")



if __name__ == "__main__":
    main()