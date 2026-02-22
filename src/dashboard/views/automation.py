import streamlit as st
import pandas as pd
from dashboard.api_client import DashboardClient

def show_automation():
    st.title("⚙️ Operations: Automation Workflows")
    st.markdown("Manage and manually execute background AI automations running on the n8n engine.")

    # 1. Fetch current status of workflows
    with st.spinner("Loading workflows..."):
        workflows = DashboardClient.get_workflows()

    if not workflows:
        st.info("No workflows found in the connected n8n instance.")
        return

    st.subheader("Active Agents & Triggers")

    # 2. Render each workflow as an expandable card
    for wf in workflows:
        name = wf.get("name", "Unnamed Workflow")
        active = wf.get("active", False)
        wf_id = wf.get("id")
        created_at = wf.get("createdAt", "Unknown")
        updated_at = wf.get("updatedAt", "Unknown")

        # Color-coded status indicator
        status_icon = "🟢" if active else "⚫"
        
        with st.expander(f"{status_icon} **{name}** (ID: `{wf_id}`)", expanded=False):
            st.markdown(f"""
            - **Status:** {'Active' if active else 'Inactive'}
            - **Created:** {created_at}
            - **Last Updated:** {updated_at}
            """)
            
            # Action button to trigger workflow manually
            col1, col2 = st.columns([1, 4])
            with col1:
                # n8n workflows cannot be externally triggered without a Webhook node.
                # Direct users to the native n8n editor for manual testing.
                n8n_url = f"http://localhost:5678/workflow/{wf_id}"
                st.link_button("🛠️ Open in n8n Editor", n8n_url)
            with col2:
                # Reserved for future usage (e.g., viewing run history)
                pass

    st.divider()
    st.caption("Note: n8n restricts external API execution of workflows unless they contain a Webhook or Execute Workflow trigger node.")
