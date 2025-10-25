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


def transform_monitoring_to_incident_format(monitoring_output: dict) -> dict:
    """
    Transform monitoring agent output to the format expected by incident detection agent.

    Monitoring output format:
    {
        "status": "abnormalities_detected",
        "application_name": "AppName",
        "abnormal_lines": [...],
        "analysis_summary": "...",
        "timestamp": "..."
    }

    Incident detection expected format:
    {
        "status": "abnormality_detected",
        "title": "...",
        "short_description": "...",
        "detection_time": "...",
        "application_name": "...",
        "related_log_lines": [...],
        "timestamp_detected": "..."
    }
    """
    if monitoring_output.get("status") != "abnormalities_detected":
        return monitoring_output  # Return as-is if not abnormalities

    # Extract detection_time - use timestamp_detected which has the actual log timestamp
    detection_time = monitoring_output.get("timestamp_detected") or monitoring_output.get("detection_time") or monitoring_output.get("timestamp") or ""

    return {
        "status": "abnormality_detected",
        "title": f"Performance Issue Detected in {monitoring_output.get('application_name', 'Unknown')}",
        "short_description": monitoring_output.get("analysis_summary", "Abnormalities detected in application logs"),
        "detection_time": detection_time,
        "application_name": monitoring_output.get("application_name", "Unknown"),
        "related_log_lines": monitoring_output.get("related_log_lines", []) or monitoring_output.get("abnormal_lines", []),
        "timestamp_detected": monitoring_output.get("timestamp_detected", "")
    }


async def main() -> None:
    """Integrated multi-agent workflow: Monitoring → Incident Detection → Resolution → Report → Benefits.

    This workflow:
    1. Monitoring Agent: Analyzes logs for abnormalities
    2. Incident Detection Agent: Processes abnormalities and creates incident tickets (only if abnormalities detected)
    3. Resolution Agent: Diagnoses and resolves the incident (only if incident created)
    4. Report Agent: Creates a ticket with resolution details and sends to Slack
    5. Benefits Agent: Calculates financial impact and sends analysis to Slack (with ticket ID)
    """

    # Use the project client within a context manager for the entire session
    with project_client:
        print("\n" + "="*80)
        print("INTEGRATED WORKFLOW: Monitoring → Detection → Resolution → Report → Benefits")
        print("="*80 + "\n")

        monitoring_output = None
        incident_result = None
        resolution_result = None
        ticket_id = None
        slack_thread_ts = None  # Thread timestamp for Slack threading

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

                # Require storage account configuration
                if not storage_account_name:
                    raise EnvironmentError(
                        f"STORAGE_ACCOUNT_NAME environment variable is not set.\n"
                        f"Please configure your Azure Storage account:\n"
                        f"  export STORAGE_ACCOUNT_NAME=\"your-storage-account\"\n"
                        f"  export CONTAINER_NAME=\"logs\"  (default: logs)\n"
                        f"  export BLOB_NAME=\"AvailabilityLogs.log\"  (default: AvailabilityLogs.log)"
                    )

                # Create monitoring agent
                monitor_agent, monitor_thread = await create_monitor_agent()

                try:
                    # Retrieve logs from Azure Storage using existing session
                    print(f"{tc.CYAN}Retrieving logs from Azure Storage ({storage_account_name})...{tc.RESET}\n")
                    log_content = await get_logs_from_azure_with_auth(
                        storage_account_name=storage_account_name,
                        container_name=container_name,
                        blob_name=blob_name
                    )

                    # Analyze logs for abnormalities
                    print(f"{tc.CYAN}Analyzing logs for abnormalities...{tc.RESET}\n")
                    analysis_result = await check_for_abnormalities(
                        log_content=log_content,
                        agent_id=monitor_agent.id,
                        thread_id=monitor_thread.id
                    )

                    # Collect and format output
                    monitoring_output = collect_abnormalities_output(analysis_result)

                    # Transform to incident detection format if abnormalities detected
                    if monitoring_output.get("status") == "abnormalities_detected":
                        monitoring_output = transform_monitoring_to_incident_format(monitoring_output)

                    print(f"{tc.CYAN}Monitoring Agent Output:{tc.RESET}")
                    print(f"  Status: {monitoring_output.get('status')}")
                    if monitoring_output.get('status') == 'abnormality_detected':
                        print(f"  Title: {monitoring_output.get('title')}")
                        print(f"  Application: {monitoring_output.get('application_name')}")
                        print(f"  Description: {monitoring_output.get('short_description')}\n")
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
            and monitoring_output.get("status") == "abnormality_detected"):

            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 2: INCIDENT DETECTION AGENT - Processing abnormalities{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                print(f"{tc.CYAN}Processing monitoring data as incident...{tc.RESET}\n")

                # Transform monitoring output to incident detection expected format
                transformed_data = transform_monitoring_to_incident_format(monitoring_output)

                # Process the transformed monitoring data through incident detection
                incident_result = await process_monitoring_incident(transformed_data)

                print(f"{tc.CYAN}Incident Detection Output:{tc.RESET}")
                print(f"  Status: {incident_result.get('status')}")
                if incident_result.get('status') == 'success':
                    print(f"  Ticket ID: {incident_result.get('ticket_id')}")
                    print(f"  Title: {incident_result.get('title')}")
                    print(f"  Severity: {incident_result.get('severity')}")
                    print(f"  Application: {incident_result.get('application_name')}")
                    print(f"  VM Name: {incident_result.get('vm_name')}")

                    # Show metrics information
                    metrics = incident_result.get('metrics', {})
                    if metrics:
                        metrics_status = metrics.get('status', 'unknown')
                        print(f"  Azure Metrics Status: {metrics_status}")

                        if metrics_status == 'success':
                            print(f"  Azure Metrics:")
                            if metrics.get('cpu_max') is not None:
                                print(f"    - CPU: {metrics.get('cpu_max')}%")
                            else:
                                print(f"    - CPU: No data (None)")
                            if metrics.get('memory_max') is not None:
                                mem_gb = metrics.get('memory_max') / (1024**3)
                                print(f"    - Memory: {mem_gb:.2f}GB")
                            else:
                                print(f"    - Memory: No data (None)")
                            print(f"  Raw Metrics Data Points: {metrics.get('raw_data', [])}")
                        else:
                            # Show error details if metrics fetch failed
                            if metrics.get('error'):
                                print(f"  Metrics Error: {metrics.get('error')}")
                            print(f"  Raw Metrics: {metrics}")

                    ticket_id = incident_result.get('ticket_id')
                    slack_thread_ts = incident_result.get('slack_thread_ts')  # Capture thread timestamp

                    # Show Slack delivery status
                    if incident_result.get('slack_delivery'):
                        slack_status = incident_result['slack_delivery'].get('status')
                        print(f"  Slack Delivery: {slack_status}")
                        if slack_thread_ts:
                            print(f"  Slack Thread ID: {slack_thread_ts}\n")
                        else:
                            print()
                else:
                    print(f"  Message: {incident_result.get('message')}\n")

            except Exception as e:
                print(f"{tc.RED}Error in Incident Detection Agent: {e}{tc.RESET}\n")
                incident_result = {"status": "error", "message": str(e)}

        elif monitoring_output and monitoring_output.get("status") != "abnormality_detected":
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
                # Extract VM name and metrics for Resolution Agent
                vm_name = incident_result.get('vm_name', 'VirtualMachine')
                metrics = incident_result.get('metrics', {})

                # Construct incident description with all details for resolution agent
                incident_description = f"""
                Ticket ID: {ticket_id}
                Title: {incident_result.get('title')}
                Application: {incident_result.get('application_name')}
                VM Name: {vm_name}
                Severity: {incident_result.get('severity')}
                Description: {incident_result.get('description')}
                Detection Time: {incident_result.get('detection_time')}

                Azure Monitor Metrics:
                """

                # Add metrics details to help Resolution Agent make decisions
                if metrics and metrics.get('status') == 'success':
                    if metrics.get('cpu_max') is not None:
                        cpu_value = metrics.get('cpu_max')
                        incident_description += f"\n- CPU Usage: {cpu_value}%"
                        if cpu_value > 80:
                            incident_description += " (HIGH - requires immediate action)"
                    if metrics.get('memory_max') is not None:
                        mem_gb = metrics.get('memory_max') / (1024**3)
                        incident_description += f"\n- Memory: {mem_gb:.2f}GB"
                        if mem_gb > 8:
                            incident_description += " (HIGH)"
                else:
                    incident_description += "\nNo metrics available"

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
        # STEP 4: REPORT AGENT - Create ticket and send to Slack
        # ============================================================================
        if (HAS_REPORT_AGENT and incident_result
            and incident_result.get("status") == "success"):

            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 4: REPORT AGENT - Creating Ticket with Resolution & Sending to Slack{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                # Extract incident details for the report
                incident_description = incident_result.get("description", "")
                application_name = incident_result.get("application_name", "Unknown")
                severity = incident_result.get("severity", "High")

                report_agent, report_thread = await create_report_agent()

                try:
                    # Determine if resolution should be broadcast to channel
                    # Broadcast if: escalated, critical severity, or resolution failed
                    should_broadcast = (
                        "escalate" in resolution_result.lower() or
                        severity == "Critical" or
                        "failed" in resolution_result.lower() or
                        "error" in resolution_result.lower()
                    )

                    # Construct the ticket creation request with the unified ticket ID
                    ticket_query = f"""
                    Create a ticket for the following incident with Ticket ID: {ticket_id}

                    Incident: {incident_description}
                    Application: {application_name}
                    Severity: {severity}
                    Resolution: {resolution_result}

                    IMPORTANT: Use the provided Ticket ID: {ticket_id}

                    SLACK THREADING INSTRUCTIONS:
                    - Thread timestamp (thread_ts): {slack_thread_ts}
                    - Post this message as a reply to the Slack thread using the thread_ts above
                    - Broadcast to channel: {"YES - This requires attention!" if should_broadcast else "NO - Keep in thread only"}
                    - Set reply_broadcast parameter to: {str(should_broadcast).lower()}

                    Please:
                    1. Use the provided ticket ID: {ticket_id}
                    2. Create a clear ticket title
                    3. Include the full resolution details
                    4. Extract and organize all relevant incident details
                    5. Format the ticket for Slack delivery with Ticket ID: {ticket_id}
                    6. Send the ticket to Slack immediately with threading parameters (thread_ts={slack_thread_ts}, reply_broadcast={str(should_broadcast).lower()})
                    """

                    ticket_result = await post_to_report_agent(
                        thread_id=report_thread.id,
                        content=ticket_query,
                        agent=report_agent,
                        thread=report_thread
                    )

                    print(f"\n{tc.CYAN}Report Agent Output:{tc.RESET}")
                    print(f"{ticket_result}\n")

                    print(f"{tc.GREEN}Report Agent processed with Ticket ID: {ticket_id}{tc.RESET}\n")

                finally:
                    # Cleanup report agent
                    try:
                        project_client.agents.delete_agent(report_agent.id)
                        print(f"Deleted report agent: {report_agent.id}\n")
                    except Exception as e:
                        print(f"Error deleting report agent: {e}\n")

            except Exception as e:
                print(f"{tc.RED}Error in Report Agent: {e}{tc.RESET}\n")
                ticket_id = "INC-ERROR-001"
        elif HAS_REPORT_AGENT and incident_result and incident_result.get("status") != "success":
            print(f"{tc.YELLOW}Incident was not successfully created. Skipping report agent.{tc.RESET}\n")
        elif not HAS_REPORT_AGENT:
            print(f"{tc.YELLOW}Report agent not available. Skipping ticket creation.{tc.RESET}\n")

        # ============================================================================
        # STEP 5: BENEFITS AGENT - Calculate financial impact and send to Slack
        # ============================================================================
        if (HAS_BENEFITS_AGENT and incident_result
            and incident_result.get("status") == "success" and ticket_id):

            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 5: BENEFITS AGENT - Calculating Financial Impact & Sending to Slack{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                # Extract incident details for benefits analysis
                incident_description = incident_result.get("description", "")
                application_name = incident_result.get("application_name", "Unknown")

                benefits_agent, benefits_thread = await create_benefits_agent()

                try:
                    # Construct the benefits analysis request
                    benefits_query = f"""
                    Please calculate the financial benefits of the following prevented issue:

                    Ticket ID: {ticket_id}
                    Application: {application_name}
                    Original Problem: {incident_description}
                    Resolution: {resolution_result}

                    Please provide:
                    1. Direct cost savings (developer time, infrastructure)
                    2. Indirect benefits (preserved revenue, customer satisfaction)
                    3. Total financial impact with explanation

                    IMPORTANT INSTRUCTIONS:
                    - Reference the Application as "{application_name}" (NOT "VM Name")
                    - Include the Ticket ID "{ticket_id}" in your Slack message so it's clear this benefits analysis is related to the ticket that was just sent.

                    SLACK THREADING INSTRUCTIONS:
                    - Thread timestamp (thread_ts): {slack_thread_ts}
                    - Post this message as a reply to the Slack thread using the thread_ts above
                    - DO NOT broadcast to channel - keep this informational message in the thread only

                    - After completing your analysis, send the results to the Slack incident channel with thread_ts={slack_thread_ts}
                    """

                    benefits_result = await post_to_benefits_agent(
                        thread_id=benefits_thread.id,
                        content=benefits_query,
                        agent=benefits_agent,
                        thread=benefits_thread
                    )

                    print(f"\n{tc.CYAN}Benefits Agent Analysis:{tc.RESET}")
                    print(f"{benefits_result}\n")

                finally:
                    # Cleanup benefits agent
                    try:
                        project_client.agents.delete_agent(benefits_agent.id)
                        print(f"Deleted benefits agent: {benefits_agent.id}\n")
                    except Exception as e:
                        print(f"Error deleting benefits agent: {e}\n")

            except Exception as e:
                print(f"{tc.RED}Error in Benefits Agent: {e}{tc.RESET}\n")
        elif HAS_BENEFITS_AGENT and (not incident_result or incident_result.get("status") != "success"):
            print(f"{tc.YELLOW}Incident was not successfully created. Skipping benefits analysis.{tc.RESET}\n")
        elif HAS_BENEFITS_AGENT and not ticket_id:
            print(f"{tc.YELLOW}Ticket ID not available. Skipping benefits analysis.{tc.RESET}\n")
        elif not HAS_BENEFITS_AGENT:
            print(f"{tc.YELLOW}Benefits agent not available. Skipping benefits analysis.{tc.RESET}\n")

        # ============================================================================
        # SUMMARY
        # ============================================================================
        print(f"{tc.GREEN}{'='*80}{tc.RESET}")
        print(f"{tc.GREEN}INTEGRATED WORKFLOW COMPLETED{tc.RESET}")
        print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

        print(f"{tc.CYAN}Workflow Summary:{tc.RESET}")
        print(f"  Step 1 - Monitoring: {monitoring_output.get('status') if monitoring_output else 'Skipped'}")
        print(f"  Step 2 - Incident Detection: {incident_result.get('status') if incident_result else 'Not created'}")
        print(f"  Step 3 - Resolution: {resolution_result if resolution_result else 'Not attempted'}")
        if ticket_id:
            print(f"  Step 4 - Report: Ticket ID {ticket_id} created")
        else:
            print(f"  Step 4 - Report: Not executed")
        print(f"  Step 5 - Benefits: Analysis sent to Slack (if ticket created)")
        print()


if __name__ == "__main__":
    print("Starting multi-agent system...")
    asyncio.run(main())
    print("Program finished.")

