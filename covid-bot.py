import os
import re
import logging
import certifi
import time
import pygsheets
import pandas as pd
import ssl as ssl_lib
from flask import Flask
from fuzzywuzzy import fuzz
from slack import WebClient
from nltk.corpus import stopwords
from slackeventsapi import SlackEventAdapter
import requests

r = requests.get('https://api.covid19india.org/data.json')
body = r.json()

# The bot id, so we can remove this from the response text
bot_id = '<@U012HNV5J2D>'

# Initialize a Flask app to host the events adapter
app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ["SLACK_SIGNING_SECRET"], "/slack/events", app)

# Initialize a Web API client
slack_web_client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

def get_message_payload(channel_id, welcome_block):
    return {
        "channel": channel_id,
        "blocks": [
            welcome_block,
        ],
    }


def prepareAllAnswer(body, index, statename):
    statewise = body['statewise']
    statedata = statewise[index]
    data = statename
    data += "\nConfirmed: " + statedata['confirmed']
    if int(statedata['deltaconfirmed']) > 0 :
        if int(statedata['deltaconfirmed']) > 1:
            data += ' (' + statedata['deltaconfirmed'] + ' new cases)'
        else:
            data += ' (' + statedata['deltaconfirmed'] + ' new case)'

    data += "\nActive: " + statedata['active']
    data += "\nRecovered: " + statedata['recovered']
    if int(statedata['deltarecovered']) > 0:
        if int(statedata['deltarecovered']) > 1:
            data += ' (' + statedata['deltarecovered'] + ' new recoveries)'
        else:
            data += ' (' + statedata['deltarecovered'] + ' new recovery)'

    data += "\nDeaths: " + statedata['deaths']
    if int(statedata['deltadeaths']) > 0 :
        if int(statedata['deltadeaths']) > 1 :
             data += ' (' + statedata['deltadeaths'] + ' new deaths)'
        else:
            data += ' (' + statedata['deltadeaths'] + ' new death)'
    return data


def prepareStatesData(body):
    statewise = body['statewise']
    index = 0
    #data = "My"
    data = 'Top 15 states with most cases'
    for object in statewise:
        if index > 15:
            break
        else:
            data += '\n' + object['state'] + ': ' + object['confirmed']
            #print(data)
        if int(object['deltaconfirmed']) > 0:
            data += ' (+' + object['deltaconfirmed'] + ') '
            #print(data)
        index = index + 1
    return data


# Post message to slack using WebClient
def post_message_to_slack(channel: str, slack_message):
    response = slack_web_client.chat_postMessage(channel=channel, text=slack_message)

def preprocess_raw_text(text):
    stop_words = [bot_id]
    # Remove stopword and punctuation
    text = ' '.join([word for word in text.split() if word not in stop_words])
    text = ' '.join([re.sub(r'[^A-Za-z0-9]+', "", word) for word in text.split()])
    # print("Processed text in fun" + text)
    return text


# Subscribe to only the message events that mention your app or bot eg. @covid-bot all/states
@slack_events_adapter.on("app_mention")
def message(payload):
    global company_index
    # Extract the payload contents
    start_time = time.time()
    event = payload.get("event", {})
    print(event)
    channel_id = event.get("channel")
    command = preprocess_raw_text(event.get("text"))
    if command.lower() == "all":
        allData = prepareAllAnswer(body, 0, "All States in India")
        print(allData)
        post_message_to_slack(channel_id, allData)
    elif command.lower() == "states":
        stateData = prepareStatesData(body)
        print(stateData)
        post_message_to_slack(channel_id, stateData)
    else:
        print("Please enter 'all' or 'states'")
        post_message_to_slack(channel_id, "Please enter 'all' or 'states'")

if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
    app.run(port=3000)