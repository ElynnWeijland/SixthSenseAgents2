import asyncio
import sys
import os

# Add the workshop directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import project_client, tc

# Import the agent modules
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


async def main() -> None:
    """Multi-agent workflow demonstrating resolution and benefits agents working together.

    This workflow:
    1. Resolution Agent: Diagnoses and resolves technical incidents
    2. Benefits Agent: Calculates the financial impact of the resolution
    """

    # Use the project client within a context manager for the entire session
    with project_client:
        print("\n" + "="*80)
        print("MULTI-AGENT WORKFLOW: Resolution + Benefits Analysis")
        print("="*80 + "\n")

        # Example incident scenario
        print(f"{tc.CYAN}Simulating an incident scenario...{tc.RESET}\n")

        incident_description = "VM 'webshop-prod-01' is experiencing high CPU usage at 95% for the past 30 minutes, affecting customer experience"

        print(f"{tc.YELLOW}Incident Report:{tc.RESET}")
        print(f"  {incident_description}\n")

        resolution_result = None

        # Step 1: Resolution Agent handles the incident
        if HAS_RESOLUTION_AGENT:
            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 1: RESOLUTION AGENT - Diagnosing and Resolving Issue{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                resolution_agent, resolution_thread = await create_resolution_agent()

                try:
                    resolution_result = await post_to_resolution_agent(
                        thread_id=resolution_thread.id,
                        content=incident_description,
                        agent=resolution_agent,
                        thread=resolution_thread
                    )

                    print(f"\n{tc.CYAN}Resolution Agent Output:{tc.RESET}")
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
        else:
            print(f"{tc.YELLOW}Resolution agent not available. Skipping resolution step.{tc.RESET}\n")
            resolution_result = "Issue resolved via automated reboot"

        # Step 2: Benefits Agent calculates financial impact
        if HAS_BENEFITS_AGENT:
            print(f"{tc.GREEN}{'='*80}{tc.RESET}")
            print(f"{tc.GREEN}STEP 2: BENEFITS AGENT - Calculating Financial Impact{tc.RESET}")
            print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")

            try:
                benefits_agent, benefits_thread = await create_benefits_agent()

                try:
                    # Construct the benefits analysis request
                    benefits_query = f"""
                    Please calculate the financial benefits of the following prevented issue:

                    Original Problem: {incident_description}
                    Resolution: {resolution_result}

                    Context:
                    - VM Name: webshop-prod-01
                    - Downtime prevented: 30 minutes
                    - Issue type: High CPU usage
                    - Resolution method: {"Automated reboot" if "solved" in resolution_result.lower() or "rebooted" in resolution_result.lower() else "Escalated to support team"}

                    Please provide:
                    1. Direct cost savings (developer time, infrastructure)
                    2. Indirect benefits (preserved revenue, customer satisfaction)
                    3. Total financial impact with explanation
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
        else:
            print(f"{tc.YELLOW}Benefits agent not available. Skipping benefits analysis.{tc.RESET}\n")

        print(f"{tc.GREEN}{'='*80}{tc.RESET}")
        print(f"{tc.GREEN}MULTI-AGENT WORKFLOW COMPLETED{tc.RESET}")
        print(f"{tc.GREEN}{'='*80}{tc.RESET}\n")


if __name__ == "__main__":
    print("Starting multi-agent system...")
    asyncio.run(main())
    print("Program finished.")

