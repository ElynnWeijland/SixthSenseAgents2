import os
import time
import asyncio
import logging
from typing import Tuple

from azure.ai.agents.models import MessageRole
from azure.storage.blob import BlobServiceClient

from utils import (
    project_client,
    API_DEPLOYMENT_NAME,
    add_agent_tools,
    async_reboot_vm,
    toolset,
    INSTRUCTIONS_FILE,
    cleanup,
    AZURE_RESOURCE_GROUP_NAME,
    AZURE_SUBSCRIPTION_ID,
)
import re

logger = logging.getLogger(__name__)

    url = "https://mystorageaccount.blob.core.windows.net"
    container = "fileshare"
    blob = "AvailabilityLogs.log"
    sas = "<INSERT SAS TOKEN>"
    
    result = search_responsetime_in_log(url, container, blob, sas)
    for line in result:
        print(line)

async def search_responsetime_in_log(storage_account_url: str, container_name: str, blob_name: str, sas_token: str):
    """
    Search for the text 'responsetime' in a blob file.

    Parameters:
    - storage_account_url: URL of the Azure Storage Account (without SAS-token)
    - container_name: name of the container containing the blob
    - blob_name: name of the blob (e.g., 'availability.log')
    - sas_token: SAS-token for access to the blob (do NOT hardcode secrets in source)

    Returns:
    - List of lines containing 'responsetime'
    """
    # Create a client using the SAS token
    blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=sas_token)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    # Download blob contents
    download_stream = blob_client.download_blob()
    content = download_stream.readall().decode("utf-8")

    # Search for lines containing 'responsetime' (case-insensitive)
    matches = [line for line in content.splitlines() if "responsetime" in line.lower()]

    return matches


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
    """Create an Azure AI Agent using a plain prompt (no tools, no DB).

    Args:
        prompt_path: optional path to the prompt file. If omitted, looks for
            ../instructions/monitor_agent_prompt.txt relative to this file.

    Returns:
        (agent, thread)
    """
    # Default path: reuse INSTRUCTIONS_FILE logic from utils.py (honors ENVIRONMENT)
    if not prompt_path:
        env = os.getenv("ENVIRONMENT", "local")
        prompt_path = f"{'src/workshop/' if env == 'container' else ''}{INSTRUCTIONS_FILE}"

    if not os.path.isfile(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8", errors="ignore") as f:
        instructions = f.read()

    # Add tools configured in utils (e.g., reboot tool). If this fails, continue.
    try:
        await add_agent_tools()
    except Exception:
        logger.debug("add_agent_tools failed or not applicable; continuing without additional tools", exc_info=True)

    # Note: not registering an AsyncFunctionTool here since the exact API
    # and desired behavior need confirmation. Keep a local async_llm_decide fallback.

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
