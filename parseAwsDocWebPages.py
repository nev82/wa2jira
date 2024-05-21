#!/usr/bin/env python3

import requests
import json
import re
from bs4 import BeautifulSoup

risk_levels = ["High", "Medium", "Low"]

# Function to parse the web pages and extract the required information
def parse_web_page(url):
    response = requests.get(url)

    soup = BeautifulSoup(response.content, "html.parser")
    risk_elements = soup.find_all('p')
    for i, element in enumerate(risk_elements):
        if "established:" in element.get_text():
            # risk_value = element.get_text().split(": ")[-1].strip()
            candidate = element.get_text().split(": ")[-1].strip()
            risks = {}
            # risk_value = None
            for risk in risk_levels:
                risks[risk] = risk in candidate
                # risk_value = risk
            if list(risks.values()).count(True) == 1:
                return list(risks.keys())[list(risks.values()).index(True)]
                # return risk_value
            elif list(risks.values()).count(True) > 1:
                print("More than 1 risk level indicator found in:\n{}".format(element))
            else:
                print("No risk level indicators found in:\n{}".format(element))
    return None

def get_implementation_steps(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    ul = None
    b_element = soup.find('b', string = re.compile("Implementation steps"))
    if b_element:
        p_element = b_element.parent
        ul = p_element.find_next('ul')
    else:
        h2_element = soup.find('h2', string = re.compile("Implementation guidance"))
        if h2_element:
            ul = h2_element.find_next('ul')
        else:
            raise ValueError("No Implementation guidance found on the page {}".format(url))
    lis = ul.find_all('li')
    implementation_steps = []
    for li in lis:
        step = li.find('p')
        implementation_steps.append(step)
    return implementation_steps

def parse_web_pages(urls):
    results = {}  # Dictionary to store the results

    for url, expected_result in urls.items():
        risk_value = parse_web_page(url)

        # Compare the extracted value with the expected result and store the comparison result
        is_correct = risk_value == expected_result
        results[url] = {"Extracted Value": risk_value, "Expected Result": expected_result, "Result": is_correct}

    return results



def main():
    # Call the function and print the results
    from riskLevelMap import CHOICE_ID_RISK_LEVEL_MAP
    # Dictionary containing URLs and expected results
    url_to_expected_result = {}
    for choice in CHOICE_ID_RISK_LEVEL_MAP:
        url = "https://docs.aws.amazon.com/wellarchitected/latest/framework/{}.html".format(choice)
        url_to_expected_result[url] = CHOICE_ID_RISK_LEVEL_MAP[choice]

    results = parse_web_pages(url_to_expected_result)

    # Print the results
    for url, data in results.items():
        print(f"URL: {url}")
        print(f"Extracted Value: {data['Extracted Value']}")
        print(f"Expected Result: {data['Expected Result']}")
        print(f"Result: {'Correct' if data['Result'] else 'Incorrect'}")
        print("-" * 50)

if __name__ == "__main__":
    main()