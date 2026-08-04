import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.request import SocketModeRequest
from agent.bedrock_agent import invoke_agent

load_dotenv()

AGENT_ID    = os.environ["BEDROCK_AGENT_ID"]
AGENT_ALIAS = os.environ["BEDROCK_AGENT_ALIAS_ID"]

slack_web   = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
slack_socket = SocketModeClient(
    app_token=os.environ["SLACK_APP_TOKEN"],
    web_client=slack_web,
)


def handle_message(client: SocketModeClient, req: SocketModeRequest):
    if req.type != "events_api":
        return
    client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

    event = req.payload.get("event", {})
    if event.get("type") != "app_mention" or event.get("bot_id"):
        return

    user    = event["user"]
    text    = event["text"]
    channel = event["channel"]
    ts      = event["ts"]

    slack_web.reactions_add(channel=channel, timestamp=ts, name="thinking_face")

    response = invoke_agent(
        agent_id=AGENT_ID,
        alias_id=AGENT_ALIAS,
        message=text,
        session_id=f"{user}-{channel}",
    )

    slack_web.reactions_remove(channel=channel, timestamp=ts, name="thinking_face")
    slack_web.chat_postMessage(channel=channel, thread_ts=ts, text=response)


slack_socket.socket_mode_request_listeners.append(handle_message)
slack_socket.connect()

print("IT Support Agent is online. Listening for mentions...")

import signal
signal.pause()
