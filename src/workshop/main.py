import asyncio
import sys
import os
import json

# Add the workshop directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import project_client, tc
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

# Import Monitoring Agent functions
try:
    from monitor_agent import (
        get_log_from_azure_storage,
        check_for_abnormalities,
        collect_abnormalities_output,
        create_agent_from_prompt as create_monitor_agent,
    )
    HAS_MONITOR_AGENT = True
except ImportError:
    HAS_MONITOR_AGENT = False
    print("Warning: monitor_agent.py not found. Monitor agent will not be available.")

# Import Incident Detection Agent functions
try:
    from incident_detection_agent import (
        process_monitoring_incident,
        raise_incident_in_slack,
    )
    HAS_INCIDENT_DETECTION_AGENT = True
except ImportError:
    HAS_INCIDENT_DETECTION_AGENT = False
    print("Warning: incident_detection_agent.py not found. Incident detection agent will not be available.")

# Import Resolution Agent functions
try:
    from resolution_agent import create_agent_from_prompt as create_resolution_agent
    from resolution_agent import post_message as post_to_resolution_agent
    HAS_RESOLUTION_AGENT = True
except ImportError:
    HAS_RESOLUTION_AGENT = False
    print("Warning: resolution_agent.py not found. Resolution agent will not be available.")

try:
    from benefits_agent import create_agent_from_prompt as create_benefits_agent
    from benefits_agent import post_message as post_to_benefits_agent
    HAS_BENEFITS_AGENT = True
except ImportError:
    HAS_BENEFITS_AGENT = False
    print("Warning: benefits_agent.py not found. Benefits agent will not be available.")

try:
    from report_agent import create_agent_from_prompt as create_report_agent
    from report_agent import post_message as post_to_report_agent
    HAS_REPORT_AGENT = True
except ImportError:
    HAS_REPORT_AGENT = False
    print("Warning: report_agent.py not found. Report agent will not be available.")


async def get_logs_from_azure_with_auth(
    storage_account_name: str,
    container_name: str,
    blob_name: str
) -> str:
    """
    Retrieve logs from Azure Storage using the current Azure session credentials.

    This uses DefaultAzureCredential which picks up your existing Azure CLI/SDK authentication.
    """
    try:
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        credential = DefaultAzureCredential()

        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        download_stream = blob_client.download_blob()
        content = download_stream.readall().decode("utf-8")

        print(f"{tc.CYAN}Successfully retrieved logs from Azure Storage ({blob_name}){tc.RESET}\n")
        return content
    except Exception as e:
        print(f"{tc.YELLOW}Note: Could not retrieve logs from Azure Storage: {e}{tc.RESET}")
        print(f"{tc.YELLOW}Make sure you're authenticated with: az login{tc.RESET}\n")
        raise


async def main() -> None:
    """Integrated multi-agent workflow: Monitoring → Incident Detection → Resolution.

    This workflow:
    1. Monitoring Agent: Analyzes logs for abnormalities
    2. Incident Detection Agent: Processes abnormalities and creates incident tickets (only if abnormalities detected)
    3. Resolution Agent: Diagnoses and resolves the incident (only if incident created)
    """

    # Use the project client within a context manager for the entire session
    with project_client:
        print("\n" + "="*80)
        print("INTEGRATED WORKFLOW: Monitoring → Incident Detection → Resolution")
        print("="*80 + "\n")

        monitoring_output = None
        incident_result = None
        resolution_result = None
        ticket_id = None

        # ============================================================================
        # STEP 1: MONITORING AGENT - Analyze logs for abnormalities
        # ============================================================================
        if HAS_MONITOR_AGENT:
            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 1: MONITORING AGENT - Analyzing logs for abnormalities{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                # Get monitoring parameters from environment variables
                storage_account_name = os.getenv("STORAGE_ACCOUNT_NAME", "")
                container_name = os.getenv("CONTAINER_NAME", "logs")
                blob_name = os.getenv("BLOB_NAME", "AvailabilityLogs.log")

                # Create monitoring agent
                monitor_agent, monitor_thread = await create_monitor_agent()

                try:
                    log_content = None

                    if storage_account_name:
                        # Attempt to retrieve logs from Azure Storage using existing session
                        try:
                            print(f"{tc.CYAN}Retrieving logs from Azure Storage ({storage_account_name})...{tc.RESET}\n")
                            log_content = await get_logs_from_azure_with_auth(
                                storage_account_name=storage_account_name,
                                container_name=container_name,
                                blob_name=blob_name
                            )
                        except Exception as e:
                            print(f"{tc.YELLOW}Could not retrieve logs: {e}{tc.RESET}")
                            print(f"{tc.YELLOW}Using sample data instead.{tc.RESET}\n")
                            log_content = None

                    if log_content:
                        # Analyze real logs for abnormalities
                        print(f"{tc.CYAN}Analyzing logs for abnormalities...{tc.RESET}\n")
                        analysis_result = await check_for_abnormalities(
                            log_content=log_content,
                            agent_id=monitor_agent.id,
                            thread_id=monitor_thread.id
                        )

                        # Collect and format output
                        monitoring_output = collect_abnormalities_output(analysis_result)

                    else:
                        print(f"{tc.YELLOW}Using sample data for demonstration.{tc.RESET}")
                        print(f"{tc.YELLOW}To use real data, set STORAGE_ACCOUNT_NAME environment variable.{tc.RESET}\n")
                        # Use sample monitoring output for demonstration
                        monitoring_output = {
                            "status": "abnormalities_detected",
                            "application_name": "WebShop-Service",
                            "abnormal_lines": [
                                "2025-10-24T10:15:00 - Response time: 1250ms",
                                "2025-10-24T10:20:00 - Response time: 1450ms",
                                "2025-10-24T10:25:00 - Response time: 1680ms"
                            ],
                            "analysis_summary": "Gradually increasing response times detected",
                            "timestamp": "2025-10-24T10:25:00"
                        }

                    print(f"{tc.CYAN}Monitoring Agent Output:{tc.RESET}")
                    print(f"  Status: {monitoring_output.get('status')}")
                    if monitoring_output.get('status') == 'abnormalities_detected':
                        print(f"  Application: {monitoring_output.get('application_name')}")
                        print(f"  Summary: {monitoring_output.get('analysis_summary')}\n")
                    else:
                        print(f"  Message: {monitoring_output.get('message')}\n")

                finally:
                    # Cleanup monitoring agent
                    try:
                        project_client.agents.delete_agent(monitor_agent.id)
                        print(f"Deleted monitoring agent: {monitor_agent.id}\n")
                    except Exception as e:
                        print(f"Error deleting monitoring agent: {e}\n")

            except Exception as e:
                print(f"{tc.RED}Error in Monitoring Agent: {e}{tc.RESET}\n")
                monitoring_output = {"status": "error", "message": str(e)}
        else:
            print(f"{tc.YELLOW}Monitoring agent not available. Skipping monitoring step.{tc.RESET}\n")
            monitoring_output = {"status": "healthy", "message": "Monitoring agent not available"}

        # ============================================================================
        # STEP 2: INCIDENT DETECTION AGENT - Only run if abnormalities detected
        # ============================================================================
        if (HAS_INCIDENT_DETECTION_AGENT and monitoring_output
            and monitoring_output.get("status") == "abnormalities_detected"):

            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 2: INCIDENT DETECTION AGENT - Processing abnormalities{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                print(f"{tc.CYAN}Processing monitoring data as incident...{tc.RESET}\n")

                # Process the monitoring output through incident detection
                incident_result = await process_monitoring_incident(monitoring_output)

                print(f"{tc.CYAN}Incident Detection Output:{tc.RESET}")
                print(f"  Status: {incident_result.get('status')}")
                if incident_result.get('status') == 'success':
                    print(f"  Incident ID: {incident_result.get('incident_id')}")
                    print(f"  Title: {incident_result.get('title')}")
                    print(f"  Severity: {incident_result.get('severity')}")
                    print(f"  Application: {incident_result.get('application_name')}")
                    ticket_id = incident_result.get('incident_id')

                    # Show Slack delivery status
                    if incident_result.get('slack_delivery'):
                        slack_status = incident_result['slack_delivery'].get('status')
                        print(f"  Slack Delivery: {slack_status}\n")
                else:
                    print(f"  Message: {incident_result.get('message')}\n")

            except Exception as e:
                print(f"{tc.RED}Error in Incident Detection Agent: {e}{tc.RESET}\n")
                incident_result = {"status": "error", "message": str(e)}

        elif monitoring_output and monitoring_output.get("status") != "abnormalities_detected":
            print(f"{tc.YELLOW}{'='*80}{tc.RESET}")
            print(f"{tc.YELLOW}No abnormalities detected. Skipping incident detection and resolution.{tc.RESET}")
            print(f"{tc.YELLOW}{'='*80}{tc.RESET}\n")
        elif not HAS_INCIDENT_DETECTION_AGENT:
            print(f"{tc.YELLOW}Incident detection agent not available. Skipping incident detection.{tc.RESET}\n")

        # ============================================================================
        # STEP 3: RESOLUTION AGENT - Only run if incident was created
        # ============================================================================
        if (HAS_RESOLUTION_AGENT and incident_result
            and incident_result.get("status") == "success"):

            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 3: RESOLUTION AGENT - Diagnosing and Resolving Incident{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                # Construct incident description for resolution agent
                incident_description = f"""
                Incident ID: {incident_result.get('incident_id')}
                Title: {incident_result.get('title')}
                Application: {incident_result.get('application_name')}
                Severity: {incident_result.get('severity')}
                Description: {incident_result.get('description')}
                Detection Time: {incident_result.get('detection_time')}
                """

                resolution_agent, resolution_thread = await create_resolution_agent()

                try:
                    resolution_result = await post_to_resolution_agent(
                        thread_id=resolution_thread.id,
                        content=incident_description,
                        agent=resolution_agent,
                        thread=resolution_thread
                    )

                    print(f"{tc.CYAN}Resolution Agent Output:{tc.RESET}")
                    print(f"  {resolution_result}\n")

                finally:
                    # Cleanup resolution agent
                    try:
                        project_client.agents.delete_agent(resolution_agent.id)
                        print(f"Deleted resolution agent: {resolution_agent.id}\n")
                    except Exception as e:
                        print(f"Error deleting resolution agent: {e}\n")

            except Exception as e:
                print(f"{tc.RED}Error in Resolution Agent: {e}{tc.RESET}\n")
                resolution_result = "Unable to resolve issue automatically"
        elif HAS_RESOLUTION_AGENT and incident_result and incident_result.get("status") != "success":
            print(f"{tc.YELLOW}Incident creation failed. Skipping resolution agent.{tc.RESET}\n")
        elif not HAS_RESOLUTION_AGENT:
            print(f"{tc.YELLOW}Resolution agent not available. Skipping resolution step.{tc.RESET}\n")

        # ============================================================================
        # SUMMARY
        # ============================================================================
        print(f"{tc.GREEN}{'='*80}{tc.RESET}")
        print(f"{tc.GREEN}INTEGRATED WORKFLOW COMPLETED{tc.RESET}")
        print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

        print(f"{tc.CYAN}Workflow Summary:{tc.RESET}")
        print(f"  Monitoring Result: {monitoring_output.get('status') if monitoring_output else 'Skipped'}")
        print(f"  Incident Result: {incident_result.get('status') if incident_result else 'Not created'}")
        print(f"  Resolution Result: {resolution_result if resolution_result else 'Not attempted'}")
        if ticket_id:
            print(f"  Ticket ID: {ticket_id}")
        print()


if __name__ == "__main__":
    print("Starting multi-agent system...")
    asyncio.run(main())
    print("Program finished.")

