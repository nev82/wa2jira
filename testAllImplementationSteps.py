#!/usr/bin/env python3

import json
import logging
import sys
import os

import argparse
import botocore
import boto3
from parseAwsDocWebPages import get_implementation_steps
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
except KeyError:
    print("""At least one of the following environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN is not defined.
          Set AWS-based variables with appropriate values, then run again""")
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
PARSER.add_argument('-v','--debug', action='store_true', help='print debug messages to stderr')

ARGUMENTS = PARSER.parse_args()
PROFILE=ARGUMENTS.profile
REGION=ARGUMENTS.region
WORKLOAD_ID=ARGUMENTS.workloadId
MILESTONE_NUMBER=ARGUMENTS.milestoneNumber
LENS_ALIAS=DEFAULT_LENS_ALIAS
LENS_VERSION=ARGUMENTS.lensVersion

if ARGUMENTS.debug:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# PILLAR_PARSE_MAP = {
#                     "operationalExcellence": "OPS",
#                     "security": "SEC",
#                     "reliability": "REL",
#                     "performance": "PERF",
#                     "costOptimization": "COST",
#                     "sustainability": "SUS"
#                     }

PILLAR_PARSE_MAP = {
                    "operationalExcellence": "OPS"
                    }



# def generate_question_page_name(code: str, index: int):
#     return "{}-{}".format(code.lower(), index if index > 9 else "0{}".format(index))



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

    for pillar in PILLAR_PARSE_MAP:
        answers = []
        choices = []
        choiceIds = []
        logger.debug("Grabbing answers for %s %s" % (LENS_ALIAS, pillar))
        # Find a questionID using the questionTitle
        try:
            response = WACLIENT.list_answers(
                WorkloadId=WORKLOAD_ID,
                LensAlias=LENS_ALIAS,
                PillarId=pillar
            )
        except botocore.exceptions.ParamValidationError as e:
            logger.error("ERROR - Parameter validation error: %s" % e)
        except botocore.exceptions.ClientError as e:
            logger.error("ERROR - Unexpected error: %s" % e)

        # logger.debug("%s" % json.dumps(response, indent = 4))
        # choiceIds.extend(response["AnswerSummaries"]["Choices"]["ChoiceId"])
        answers.extend(response["AnswerSummaries"])
        while "NextToken" in response:
            try:
                response = WACLIENT.list_answers(WorkloadId=WORKLOAD_ID,
                                                 LensAlias=LENS_ALIAS,
                                                 PillarId=pillar,
                                                 NextToken=response["NextToken"])
            except botocore.exceptions.ParamValidationError as e:
                logger.error("ERROR - Parameter validation error: %s" % e)
            except botocore.exceptions.ClientError as e:
                logger.error("ERROR - Unexpected error: %s" % e)
            answers.extend(response["AnswerSummaries"])
        for answer in answers:
            logger.debug("choices:\n%s" % (answer["Choices"]))
            choices.extend(answer["Choices"])
        for choice in choices:
            logger.debug("ChoiceId:\t%s" % (choice["ChoiceId"]))
            if choice['Title'] != "None of these":
                choiceIds.append(choice["ChoiceId"])
        logger.debug("choiceIds:\t%s" % choiceIds)
        for choiceId in choiceIds:
            url = "https://docs.aws.amazon.com/wellarchitected/{}/framework/{}.html".format(LENS_VERSION, choiceId)
            try:
                steps = get_implementation_steps(url)
            except ValueError as e:
                logger.error("ERROR - Value error: %s" % e)
            else:
                print("\n\n{}".format(url))
                for step in steps:
                    print(" * {}".format(step))



if __name__ == "__main__":
    main()