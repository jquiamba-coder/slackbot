import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import string

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'],'/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']
message_counts = {}
welcome_messages = {}

KEY_WORDS1 = ['2fa', '2fa reset', '2fa in okta']
KEY_WORDS2 = ['okta password', 'lockout', 'password reset']
KEY_WORDS3 = ['jira', 'confluence', 'board', 'project']

class WelcomeMessage:
    START_TEXT = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': (
                ':tada: Welcome to the #IT-Support channel! :tada: \n\n'
                ' This is your Paxful IT SlackBot at your Service :paxbot:'
            )
        }
    }

    DIVIDER = {'type': 'divider'}

    def __init__(self, channel, user):
        self.channel = channel
        self.user = user
        self.icon_emoji = ':paxbot:'
        self.timestamp = ''
        self.completed = False


    def get_message(self):
        return {
            'ts': self.timestamp,
            'channel': self.channel,
            'username': 'Welcome Robot!',
            'icon_emoji': self.icon_emoji,
            'blocks': [
                self.START_TEXT,
                self.DIVIDER,
                self._get_reaction_task()
            ]
        }
    
    def _get_reaction_task(self):
        checkmark = ':white_check_mark:'
        if not self.completed:
            checkmark = ':white_large_square:'

        text = f'{checkmark} *React to this message so we know you are not a Bot!*'

        return {'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}

def send_welcome_message(channel, user,):
        if channel not in welcome_messages:
            welcome_messages[channel] = {}

        if user in welcome_messages[channel]:
            return

        welcome = WelcomeMessage(channel, user)
        message = welcome.get_message()
        response = client.chat_postMessage(**message)
        welcome.timestamp = response['ts']

        welcome_messages[channel][user] = welcome

def check_if_key_words1(message):
    msg = message.lower()
    msg = msg.translate(str.maketrans('', '', string.punctuation))

    return any(word in msg for word in KEY_WORDS1)

def check_if_key_words2(message):
    msg = message.lower()
    msg = msg.translate(str.maketrans('', '', string.punctuation))

    return any(word in msg for word in KEY_WORDS2)

def check_if_key_words3(message):
    msg = message.lower()
    msg = msg.translate(str.maketrans('', '', string.punctuation))

    return any(word in msg for word in KEY_WORDS3)


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if user_id != None and BOT_ID != user_id:
        if user_id in message_counts:
            message_counts[user_id] += 1
        else:
            message_counts[user_id] = 1

        if check_if_key_words1(text):
            ts=event.get('ts')
            client.chat_postMessage(
                channel=channel_id, thread_ts=ts, text ="Do you need help with 2fa?" )

        elif check_if_key_words2(text):
            ts=event.get('ts')
            client.chat_postMessage(
                channel=channel_id, thread_ts=ts, text ="Ok, hang on a minute while I get an associate to help you" )
        
        elif check_if_key_words3(text):
            ts=event.get('ts')
            client.chat_postMessage(
            channel=channel_id, thread_ts=ts, text ="Do you need help with any Atlassian Products?")
        else:
            print(text)

@slack_event_adapter.on('reaction_added')
def reaction(payload):
    event = payload.get('event', {})
    channel_id = event.get('item', {}).get('channel')
    user_id = event.get('user')

    if f'@{user_id}' not in welcome_messages:
        return
    
    welcome = welcome_messages[f'@{user_id}'][user_id]
    welcome.completed = True
    welcome.channel = channel_id
    message = welcome.get_message()
    updated_message = client.chat_update(**message)
    welcome.timestamp = updated_message['ts']

@app.route('/message-count', methods=['POST'])
def message_count():
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    message_count = message_counts.get(user_id, 0)

    client.chat_postMessage(channel=channel_id, text=f"message: {message_count}")
    return Response(), 200

if __name__ == "__main__":
    app.run(debug=True)    
