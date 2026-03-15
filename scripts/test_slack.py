import os
import sys

# Ensure src is in PYTHONPATH to import Consigliere modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dotenv import load_dotenv
load_dotenv()

from core.notify.slack import SlackSender

def test_slack_sending():
    print("🚀 Initializing SlackSender...")
    sender = SlackSender()
    
    print("📨 Sending test message...")
    response = sender.send("Hello from Consigliere! 🤖 This is a test message to confirm your Slack configuration.")
    
    if response.get("status") == "success":
        print("✅ Message sent successfully!")
        print("Response data:", response.get("data"))
    else:
        print("❌ Failed to send message.")
        print("Error:", response.get("error"))

if __name__ == "__main__":
    test_slack_sending()
