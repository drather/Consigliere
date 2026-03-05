# Feature Spec: Slack Interactive Interface (Chat-Ops)

## Overview
This feature introduces Slack as a bidirectional interface for Project Consigliere. It starts with establishing a robust, one-way notification channel (Slack Sender) and will eventually expand to allow users to trigger internal workflows directly from Slack using interactive buttons and webhooks.

## Goals
1.  **Sender Abstraction**: Create a generic `Sender` interface in `src/core/notify/sender.py` to decouple notification logic from core business logic, enabling easy addition of future channels (e.g., Email, Discord).
2.  **Slack Implementation**: Implement `SlackSender` using a Slack Bot Token and the `chat.postMessage` API to send formatted messages to a designated channel.
3.  **Local Tunneling**: Set up Cloudflare Tunnel (or ngrok) to expose the local Fast API/n8n instance so it can receive incoming webhooks from Slack (Phase 2).
4.  **Verification**: Confirm successful delivery of a test message from the local Consigliere API to the user's smartphone Slack app.

## Architecture

1.  **Notification Layer**:
    *   `src/core/notify/sender.py`: Abstract Base Class defining `send(message: str, **kwargs)`.
    *   `src/core/notify/slack.py`: Concrete implementation using `requests` and Slack API.
    *   `src/main.py`: New `/notify/slack` endpoint that delegates to `SlackSender`.

2.  **Configuration**:
    *   `.env` will store `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID`.

## Required User Setup
The user must manually create a Slack App, install it to their workspace, enable Bot permissions (`chat:write`), and provide the resulting OAuth Token and Channel ID to the `.env` file.
