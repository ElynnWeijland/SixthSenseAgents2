import os
import time
import asyncio
import logging
from typing import Tuple
from datetime import datetime

from azure.ai.agents.models import MessageRole
from azure.storage.blob import BlobServiceClient

from utils import (
    project_client,
    API_DEPLOYMENT_NAME,
    add_agent_tools,
    async_reboot_vm,
    toolset,
    cleanup,
    AZURE_RESOURCE_GROUP_NAME,
    AZURE_SUBSCRIPTION_ID,
)
import re
import json

logger = logging.getLogger(__name__)

async def get_log_from_azure_storage(
    storage_account_url: str,
    container_name: str,
    blob_name: str,
    sas_token: str
) -> str:
    """
    Retrieve log file from Azure Storage Account.

    Parameters:
    - storage_account_url: URL of the Azure Storage Account (without SAS-token)
    - container_name: name of the container containing the blob
    - blob_name: name of the blob (e.g., 'AvailabilityLogs.log')
    - sas_token: SAS-token for access to the blob (do NOT hardcode secrets in source)

    Returns:
    - Full contents of the log file as a string
    """
    try:
        # Create a client using the SAS token
        blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=sas_token)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Download blob contents
        download_stream = blob_client.download_blob()
        content = download_stream.readall().decode("utf-8")

        logger.info(f"Successfully retrieved log file: {blob_name} from container: {container_name}")
        return content
    except Exception as e:
        logger.error(f"Error retrieving log file from Azure Storage: {e}")
        raise


async def check_for_abnormalities(log_content: str, agent_id: str, thread_id: str) -> dict:
    """
    Use LLM to analyze log content for abnormalities.

    Parameters:
    - log_content: The full log file content
    - agent_id: The monitor agent ID
    - thread_id: The thread ID for the conversation

    Returns:
    - Dictionary with keys:
        - 'abnormalities_found': bool
        - 'analysis': str (LLM analysis result)
        - 'abnormal_lines': list of problematic log lines (if any)
        - 'application_name': str (extracted app name)
    """
    try:
        logger.info("Analyzing log content for abnormalities using LLM...")

        # Create a message with the log content for analysis
        user_message = f"""Please analyze the following log file for abnormalities, specifically looking for increased response times (response times > 1000ms are considered abnormal).

Log Content:
---
{log_content}
---

Provide your analysis in the following JSON format:
{{
    "abnormalities_found": boolean,
    "application_name": "name of application from logs (if identifiable)",
    "abnormal_lines": ["line1", "line2", ...],
    "summary": "brief summary of findings"
}}"""

        message = project_client.agents.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message,
        )
        logger.info(f"Message created for analysis: {message.id}")

        # Create run for analysis
        run = project_client.agents.runs.create(
            thread_id=thread_id,
            agent_id=agent_id,
        )
        logger.info(f"Analysis run created: {run.id}")

        # Poll for completion
        max_iterations = 120
        iteration = 0
        while run.status in ("queued", "in_progress", "requires_action") and iteration < max_iterations:
            time.sleep(2)
            iteration += 1
            run = project_client.agents.runs.get(thread_id=thread_id, run_id=run.id)
            logger.debug(f"Run status: {run.status} (iteration {iteration})")

        if run.status == "completed":
            response = project_client.agents.messages.get_last_message_by_role(
                thread_id=thread_id,
                role=MessageRole.AGENT,
            )

            if response:
                analysis_text = "\n".join(t.text.value for t in response.text_messages)
                logger.info(f"LLM analysis completed")

                # Try to parse JSON from response
                try:
                    # Extract JSON from response if wrapped in markdown code blocks
                    json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        result = json.loads(analysis_text)

                    return {
                        'abnormalities_found': result.get('abnormalities_found', False),
                        'application_name': result.get('application_name', 'Unknown'),
                        'abnormal_lines': result.get('abnormal_lines', []),
                        'analysis': result.get('summary', analysis_text)
                    }
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON from LLM response, returning raw analysis")
                    return {
                        'abnormalities_found': 'abnormalities found' in analysis_text.lower() or 'response time' in analysis_text.lower(),
                        'application_name': 'Unknown',
                        'abnormal_lines': [],
                        'analysis': analysis_text
                    }
            else:
                logger.warning("No response from LLM analysis")
                return {
                    'abnormalities_found': False,
                    'analysis': 'Unable to complete analysis',
                    'abnormal_lines': [],
                    'application_name': 'Unknown'
                }
        else:
            logger.error(f"Analysis run failed with status: {run.status}")
            return {
                'abnormalities_found': False,
                'analysis': f'Analysis failed with status: {run.status}',
                'abnormal_lines': [],
                'application_name': 'Unknown'
            }
    except Exception as e:
        logger.error(f"Error checking for abnormalities: {e}")
        return {
            'abnormalities_found': False,
            'analysis': f'Error during analysis: {str(e)}',
            'abnormal_lines': [],
            'application_name': 'Unknown'
        }


def collect_abnormalities_output(analysis_result: dict) -> dict:
    """
    Collect and format the abnormalities output.

    Parameters:
    - analysis_result: Dictionary from check_for_abnormalities

    Returns:
    - Formatted output with application name and abnormal log lines
    """
    if not analysis_result.get('abnormalities_found'):
        return {
            'status': 'healthy',
            'message': 'No abnormalities detected in logs. All response times appear normal.',
            'application_name': None,
            'abnormal_lines': []
        }

    # Extract detection time from the first abnormal line
    abnormal_lines = analysis_result.get('abnormal_lines', [])
    detection_time = None
    if abnormal_lines and isinstance(abnormal_lines, list):
        for line in abnormal_lines:
            if isinstance(line, str) and line.strip():
                # Extract timestamp from beginning of line (ISO 8601 format)
                parts = line.split()
                if parts:
                    detection_time = parts[0]
                    break

    # Fallback to current time only if no timestamp found in abnormal lines
    if not detection_time:
        logger.warning("No detection time found in abnormal lines, using current time")
        detection_time = datetime.now().isoformat()

    return {
        'status': 'abnormalities_detected',
        'application_name': analysis_result.get('application_name', 'Unknown'),
        'abnormal_lines': abnormal_lines,
        'analysis_summary': analysis_result.get('analysis', ''),
        'timestamp': detection_time
    }


async def async_llm_decide(user_input: str) -> str:
    """Decide whether to 'solve' or 'escalate' based on the input.

    NOTE: Intentionally simple keyword-based fallback. Replace with a real LLM call if desired.
    """
    # Simulate async LLM latency
    await asyncio.sleep(0.05)
    text = (user_input or "").lower()
    # crude heuristic: if CPU or high cpu load mentioned -> solve
    if "cpu" in text and ("high" in text or "high cpu" in text or "high cpu load" in text or "cpu usage" in text):
        logger.debug("async_llm_decide: returning 'solve'")
        return "solve"
    logger.debug("async_llm_decide: returning 'escalate'")
    return "escalate"


async def create_agent_from_prompt(prompt_path: str | None = None) -> Tuple[object, object]:
    """Create an Azure AI Agent using monitor agent instructions.

    Args:
        prompt_path: optional path to the prompt file. If omitted, looks for
            instructions/monitor_agent_instructions.txt relative to this file.

    Returns:
        (agent, thread)
    """
    # Default path for monitor agent instructions
    if not prompt_path:
        env = os.getenv("ENVIRONMENT", "local")
        prompt_path = f"{'src/workshop/' if env == 'container' else ''}instructions/monitor_agent_instructions.txt"

    if not os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
        instructions = f.read()

    # Note: Monitor agent doesn't need additional tools (sales data, reboot, etc.)
    # These are only used by other agents (resolution agent, etc.)
    # Skipping add_agent_tools() to keep the monitor agent lightweight

    logger.info("Creating monitor agent...")
    agent = project_client.agents.create_agent(
        model=API_DEPLOYMENT_NAME,
        name="Monitor Agent",
        instructions=instructions,
        temperature=0.0,
        toolset=toolset,
        headers={"x-ms-enable-preview": "true"},
    )
    logger.info("Created monitor agent: %s", getattr(agent, "id", "<no-id>"))

    logger.info("Creating thread for monitor agent...")
    thread = project_client.agents.threads.create()
    logger.info("Created thread: %s", getattr(thread, "id", "<no-id>"))

    return agent, thread


async def run_monitor_workflow(
    storage_account_url: str,
    container_name: str,
    blob_name: str,
    sas_token: str
) -> dict:
    """
    Execute the complete monitoring workflow:
    1. Get log file from Azure Storage
    2. Check for abnormalities using LLM
    3. Collect and output results if abnormalities found

    Parameters:
    - storage_account_url: URL of Azure Storage Account
    - container_name: Name of storage container
    - blob_name: Name of log blob file
    - sas_token: SAS token for storage access

    Returns:
    - Dictionary with monitoring results
    """
    try:
        logger.info("Starting monitor workflow...")

        # Step 1: Get log file from Azure Storage
        logger.info("Step 1: Retrieving log file from Azure Storage...")
        log_content = await get_log_from_azure_storage(
            storage_account_url,
            container_name,
            blob_name,
            sas_token
        )
        logger.info(f"Log file retrieved successfully ({len(log_content)} bytes)")

        # Create agent and thread for analysis
        agent, thread = await create_agent_from_prompt()

        # Step 2: Check for abnormalities
        logger.info("Step 2: Analyzing logs for abnormalities...")
        analysis_result = await check_for_abnormalities(
            log_content,
            agent.id,
            thread.id
        )

        # Step 2.1 & 2.2: Handle results based on abnormality detection
        if analysis_result.get('abnormalities_found'):
            logger.info("Step 3: Abnormalities detected, collecting output...")
            output = collect_abnormalities_output(analysis_result)
            logger.info(f"Monitor workflow completed with abnormalities detected for application: {output['application_name']}")
        else:
            logger.info("Step 2.2: No abnormalities detected, ending flow...")
            output = collect_abnormalities_output(analysis_result)
            logger.info("Monitor workflow completed - system is healthy")

        # Cleanup
        await cleanup(agent, thread)

        return output

    except Exception as e:
        logger.error(f"Monitor workflow failed: {e}", exc_info=True)
        raise
