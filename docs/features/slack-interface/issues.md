# Issue Log: Slack Interactive Interface

## 1. Cloudflare Tunnel URL Volatility
- **Problem**: Using the account-less `cloudflared tunnel --url` command generates a random URL that expires if the process restarts or the connection idles too long.
- **Impact**: Requires manual updating of "Request URL" in Slack API settings frequently during development.
- **Recommendation**: Consider a persistent named tunnel (requires Cloudflare account) or ngrok with a fixed domain.

## 2. n8n Production Webhook 404 Errors
- **Problem**: Requests to production webhook URLs (e.g., `/webhook/slack-events`) frequently return 404, even when the workflow is "Published" (Active).
- **Observation**: n8n v2.9.4 seems to handle production routing differently. Webhooks that work in "Test" mode (`/webhook-test/...`) fail in production mode.
- **Status**: Investigating if n8n requires a specific URL structure (e.g., including the Workflow ID) or if there's a delay in registration.

## 3. Slack URL Verification Challenge Failure
- **Problem**: Slack's "Event Subscriptions" verification sends a POST with a `challenge` parameter. Our n8n workflow must return this exact string.
- **Blocker**: Because of the 404 issue (Issue #2), Slack cannot reach the endpoint to verify it.
- **Workaround Attempted**: Used `Webhook` + `Respond to Webhook` nodes, but registration remains unstable.

## 4. Tunnel Connection Timeouts
- **Problem**: The tunnel often disconnects during long-running browser subagent tasks or when the system is under high load.
- **Impact**: Interrupts the feedback loop between Slack and the local server.
