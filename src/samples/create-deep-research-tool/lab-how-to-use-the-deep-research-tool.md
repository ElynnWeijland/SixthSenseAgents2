<div align="center">
    <img src="../../../media/image-deepresearch1.png" width="100%" alt="Azure AI Foundry workshop / lab / sample">
</div>

# Deep Research Introduction
Before diving into the Deep Research tool, it's important to understand its capabilities, prerequisites, and how to effectively utilize it within your Azure AI Foundry projects. 

## Model Details
- **Model Name**: o3-deep-research  
- **Deployment Type**: Global Standard  
- **Available Regions**: West US, Norway East  
- **Quotas and Limits**:  
    - **Enterprise**: 30K RPS / 30M TPM  
    - **Default**: 3K RPS / 3M TPM  

## Research Tool Prerequisites
- If you already have access to the Azure OpenAI o3 model, no request is required to access the o3-deep-research model. Otherwise, fill out the request form.
- An Azure subscription with the ability to create the following resources:  
    - AI Foundry project  
    - Grounding with Bing Search  
    - Deep research model  
    - GPT model resources  
- Set up your environment in the **West US** and **Norway East** regions.
- Grounding with Bing Search tool resource for connecting to your Azure AI Foundry project. 
- Capgemini network limitations: The **Bing Grounding API is blocked on the Capgemini network via Zscaler** (at this moment). To use the Deep Research tool, you will need to connect to a different compute environment that allows access to the Bing Search API. Using Codespaces or another non-Capgemini device is recommended.

> IMPORTANT !!! This means that in order to use the Deep Research tool, you need to have access to the o3-deep-research model and set up the necessary Azure resources in one of the supported regions. As the default region for the workshop is East US, you might need to create a new Azure AI Foundry project in West US or Norway East to use the Deep Research tool. In addition, to make use of the Deep Research tool, the request access form must be filled out if you do not already have access to the o3 model. Please check with your instructor if the model access request has been submitted and approved before proceeding!

## Model Deployments
- **o3-deep-research**:  
    - Version: 2025-06-26  
    - Available Regions: West US, Norway East  
- **gpt-4o**:  
    - Purpose: Intent clarification  
    - Deployment: Same region as the o3-deep-research model  

## Integrated with Grounding with Bing Search
The deep research tool is tightly integrated with Grounding with Bing Search and only supports web-based research. Once the task is scoped, the agent using the Deep Research tool invokes the Grounding with Bing Search tool to gather a curated set of recent web data designed to provide the research model with a foundation of authoritative, high quality, up-to-date sources.

> IMPORTANT !!!
> 
> 1. Your usage of Grounding with Bing Search can incur costs. See the pricing page for details.
> 2. By creating and using a Grounding with Bing Search resource through code-first experience, such as Azure CLI, or deploying through deployment template, you agree to be bound by and comply with the terms available at https://www.microsoft.com/en-us/bing/apis/grounding-legal, which may be updated from time to time.
> 3. When you use Grounding with Bing Search, your customer data is transferred outside of the Azure compliance boundary to the Grounding with Bing Search service. Grounding with Bing Search is not subject to the same data processing terms (including location of processing) and does not have the same compliance standards and certifications as the Azure AI Foundry Agent Service, as described in the Grounding with Bing Search Terms of Use: https://www.microsoft.com/en-us/bing/apis/grounding-legal. It is your responsibility to assess whether use of Grounding with Bing Search in your agent meets your needs and requirements.

# Deployment Steps
## Model Deployment

1. Navigate to the Azure AI Foundry portal: https://portal.azure.com/#view/Microsoft_AiFoundry/AIProjectsMenuBlade/~/Overview and select your project in either West US or Norway East. Copy the project endpoint connection string and project key from the Keys + Endpoint tab.

Save this endpoint to an environment file (.env) as **PROJECT_ENDPOINT**.

1. Navigate to the Models + Endpoints tab.

![alt text](../../../media/image-deepresearch2.png)

Deploy the o3-deep-research-model and GPT-4o model. For the o3-deep-research model, select version 2025-06-26 and choose a deployment name. You can leave the other settings as default.

![alt text](../../../media/image-deepresearch3.png)

Deploy an Azure OpenAI GPT model that is supported for Deep Research, such as gpt-4o, in the same region as the o3-deep-research model. 

> NOTE !!! 
> Other GPT-series models including GPT-4o-mini and the GPT-4.1 series are not supported for scope clarification in Deep Research.

![alt text](../../../media/image-deepresearch4.png)

## Connect Bing Grounding to your project
To use the Deep Research tool, you need to connect a Bing Grounding resource to your Azure AI Foundry project. If you haven't done this yet, follow the instructions in this lab: [Create a Bing Grounding connection](../create-a-bing-grounding-connection/lab-create-a-bing-grounding-connection.md).

# Create an agent with the Deep Research tool
Assuming a new Azure AI Foundry project has been created in either West US or Norway East, follow the steps below to create an agent with the Deep Research tool.

## Setup the Python environment
The Deep Research tool requires the latest prerelease versions of the azure-ai-projects library. First we recommend creating a virtual environment to work in. If you haven't done already create one:

```python
python -m venv env
# after creating the virtual environment, activate it with:
.\env\Scripts\activate
```
You can install the package with the following command:

```python
pip install --pre azure-ai-projects
pip install azure-identity
```

Make sure you have a .env file with the right environment variables. If you don't have this already have a look at the Getting Started manual: [Getting Started](../../docs/docs/getting-started.md) to create yours.

## Create the Deep Research script 
Create a new file named `create_deep_research_agent.py` and add the following code:

```python
import os, time
from typing import Optional
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import DeepResearchTool, MessageRole, ThreadMessage
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def fetch_and_print_new_agent_response(
    thread_id: str,
    agents_client: AgentsClient,
    last_message_id: Optional[str] = None,
    show_details: bool = True,
    show_thinking: bool = False,
) -> Optional[str]:
    response = agents_client.messages.get_last_message_by_role(
        thread_id=thread_id,
        role=MessageRole.AGENT,
    )
    if not response or response.id == last_message_id:
        return last_message_id  # No new content

    if show_details:
        content = "\n".join(t.text.value for t in response.text_messages)
        
        if show_thinking:
            # Show the agent's thinking/reasoning process
            print("\n" + "="*60)
            print("🧠 AGENT THINKING & REASONING:")
            print("="*60)
            
            # Show content in chunks to understand the reasoning
            if len(content) > 500:
                print(f"📝 Response Content ({len(content)} characters):")
                print("-" * 40)
                # Show first part for reasoning
                print(content[:800] + "..." if len(content) > 800 else content)
                print("-" * 40)
            else:
                print("📝 Response Content:")
                print(content)
        else:
            print("\nAgent response:")
            print(content)

        # Show URL citations with more detail
        if response.url_citation_annotations:
            print("\n🔗 SOURCES BEING REFERENCED:")
            print("-" * 40)
            for i, ann in enumerate(response.url_citation_annotations, 1):
                title = ann.url_citation.title or "Untitled Source"
                url = ann.url_citation.url
                print(f"{i}. 📄 {title}")
                print(f"   🌐 {url}")
                print()

    return response.id


def monitor_research_progress(
    thread_id: str,
    agents_client: AgentsClient,
    last_message_id: Optional[str] = None,
) -> Optional[str]:
    """
    Monitor research progress and show detailed information about sources and reasoning
    """
    response = agents_client.messages.get_last_message_by_role(
        thread_id=thread_id,
        role=MessageRole.AGENT,
    )
    
    if not response or response.id == last_message_id:
        return last_message_id  # No new content

    content = "\n".join(t.text.value for t in response.text_messages)
    
    # Analyze the content to show what's happening
    print("\n" + "="*70)
    print("🔍 RESEARCH PROGRESS UPDATE")
    print("="*70)
    
    # Show content analysis
    if "start_research_task(" in content:
        print("📋 RESEARCH TASK SETUP:")
        # Extract and show the research parameters
        lines = content.split('\n')
        for line in lines:
            if 'title=' in line:
                title = line.split('title=')[1].strip(' ",')
                print(f"   📌 Research Title: {title}")
            elif 'response=' in line:
                response_text = line.split('response=')[1].strip(' ",')[:200]
                print(f"   💭 Agent's Plan: {response_text}...")
        print()
    
    # Show reasoning and progress
    if len(content) > 100:
        print(f"📊 Content Generated: {len(content):,} characters")
        
        # Look for thinking patterns
        content_lower = content.lower()
        if any(phrase in content_lower for phrase in ["analyzing", "researching", "investigating", "examining"]):
            print("🧠 Agent is actively analyzing sources...")
        
        if any(phrase in content_lower for phrase in ["found", "discovered", "according to", "based on"]):
            print("📖 Agent is synthesizing information from sources...")
        
        if any(phrase in content_lower for phrase in ["conclusion", "summary", "key findings"]):
            print("📝 Agent is compiling final findings...")
    
    # Show sources being referenced
    if response.url_citation_annotations:
        print(f"\n🌐 ONLINE RESOURCES REFERENCED ({len(response.url_citation_annotations)} sources):")
        print("-" * 50)
        
        for i, ann in enumerate(response.url_citation_annotations, 1):
            title = ann.url_citation.title or f"Source {i}"
            url = ann.url_citation.url
            
            # Try to identify the type of source
            source_type = "📄 Document"
            if "arxiv.org" in url:
                source_type = "📚 Academic Paper"
            elif "nature.com" in url or "science.org" in url:
                source_type = "🔬 Scientific Journal"
            elif "github.com" in url:
                source_type = "💻 Code Repository"
            elif "news" in url or "press" in url:
                source_type = "📰 News Article"
            elif ".edu" in url:
                source_type = "🎓 Academic Institution"
            elif ".gov" in url:
                source_type = "🏛️ Government Source"
            
            print(f"{i:2d}. {source_type}")
            print(f"     📌 {title}")
            print(f"     🌐 {url}")
            print()
    
    print("="*70)
    
    return response.id


def is_refinement_question(message_content: str) -> bool:
    """
    Detect if the agent is in refinement mode.
    Everything before start_research_task() is considered refinement and should be interactive.
    """
    # If the message contains start_research_task(), refinement is done
    if "start_research_task(" in message_content:
        return False
    
    # Everything else is refinement and should be interactive
    return True


def is_research_starting(message_content: str) -> bool:
    """
    Detect when actual research is starting by looking for the start_research_task() function call
    """
    return "start_research_task(" in message_content


def is_research_complete(message_content: str, research_started_flag: bool) -> bool:
    """
    Determines if the research is complete using a flag-based approach:
    - If research_started_flag is True AND start_research_task() is NOT in the message, research is complete
    - If research_started_flag is False, research hasn't started yet
    """
    if not research_started_flag:
        return False  # Research hasn't started yet
    
    # If research started but start_research_task() is no longer in the message, research is complete
    research_still_running = "start_research_task(" in message_content
    
    return not research_still_running


def conduct_interactive_refinement(
    agents_client: AgentsClient,
    thread_id: str,
    agent_id: str
) -> int:
    """
    Conducts interactive refinement session with the agent using a deterministic approach.
    Returns the number of refinements made.
    """
    print("\n" + "="*60)
    print("🔍 INTERACTIVE REFINEMENT SESSION")
    print("="*60)
    print("The agent will ask clarifying questions to improve research quality.")
    print("Answer each question or type 'done' to start the research.")
    print("="*60)
    
    refinement_count = 0
    max_refinements = 5  # Limit to 5 refinements for better control
    
    # Start by explicitly asking the agent to ask a clarifying question
    clarification_request = """
    Before starting your research, please ask me ONE specific clarifying question about my research request. 
    This should help you understand exactly what aspect, timeframe, scope, or focus I'm most interested in.
    
    Ask only ONE clear question. Do not start the research yet.
    """
    
    agents_client.messages.create(
        thread_id=thread_id,
        role="user",
        content=clarification_request,
    )
    
    while refinement_count < max_refinements:
        print(f"\n⏳ Getting clarifying question #{refinement_count + 1}...")
        
        # Create a run to get agent response
        run = agents_client.runs.create(thread_id=thread_id, agent_id=agent_id)
        
        # Wait for the run to complete
        while run.status in ("queued", "in_progress"):
            time.sleep(1)
            run = agents_client.runs.get(thread_id=thread_id, run_id=run.id)
        
        if run.status == "failed":
            print(f"❌ Run failed: {run.last_error}")
            break
        
        # Get the agent's response
        agent_response = agents_client.messages.get_last_message_by_role(
            thread_id=thread_id, role=MessageRole.AGENT
        )
        
        if not agent_response:
            print("No response from agent.")
            break
        
        response_content = "\n".join(t.text.value for t in agent_response.text_messages)
        
        # DETERMINISTIC CHECK: Look for the agent saying it has enough info
        if "sufficient information" in response_content.lower() or "enough information" in response_content.lower():
            print("\n✅ Agent indicates it has sufficient information to proceed.")
            print("🚀 Starting research...")
            break
        
        # Show the agent's question/response
        print(f"\n🤖 Agent Response #{refinement_count + 1}:")
        print("-" * 50)
        print(response_content)
        print("-" * 50)
        
        # Get user input
        user_answer = input("\n💬 Your answer (or 'done' to start research): ").strip()
        
        if user_answer.lower() in ['done', 'start', 'proceed', 'go', 'research']:
            print("\n✅ User requested to start research.")
            break
        
        if user_answer:
            # Add user's answer and explicitly control the next step
            if refinement_count < max_refinements - 1:
                follow_up_prompt = f"""
                Thank you for that clarification: "{user_answer}"
                
                Do you have ONE more specific clarifying question that would help you conduct better research? 
                If yes, ask it now. If you have enough information to proceed, respond with "I have sufficient information to proceed with the research."
                """
            else:
                follow_up_prompt = f"""
                Thank you for that clarification: "{user_answer}"
                
                I have sufficient information to proceed with the research.
                """
            
            agents_client.messages.create(
                thread_id=thread_id,
                role="user",
                content=follow_up_prompt,
            )
            refinement_count += 1
            print(f"✅ Refinement {refinement_count} added.")
            
            # Check if we've reached the limit
            if refinement_count >= max_refinements:
                print(f"\n⚠️ Maximum refinements ({max_refinements}) reached. Starting research...")
                break
        else:
            print("No answer provided. Starting research...")
            break
    
    return refinement_count


def wait_for_research_completion(
    agents_client: AgentsClient,
    thread_id: str,
    agent_id: str,
    max_wait_minutes: int = 25
) -> Optional[ThreadMessage]:
    """
    Wait for the deep research to complete using flag-based detection:
    - Flag enabled when start_research_task() appears
    - Research complete when flag is enabled but start_research_task() no longer appears
    """
    print(f"\n⏳ Monitoring research progress for up to {max_wait_minutes} minutes...")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    research_started_flag = False
    last_message_id = None
    check_interval = 5  # Check every 5 seconds for more responsive detection
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # Check for new messages
            current_message = agents_client.messages.get_last_message_by_role(
                thread_id=thread_id, role=MessageRole.AGENT
            )
            
            if current_message and current_message.id != last_message_id:
                content = "\n".join(t.text.value for t in current_message.text_messages)
                
                # Check if research is starting (enable flag)
                if not research_started_flag and is_research_starting(content):
                    print("🚀 Deep Research Task initialized - research is now starting...")
                    research_started_flag = True
                    # Show detailed setup information
                    monitor_research_progress(thread_id, agents_client, last_message_id)
                
                # Check if research is complete (flag enabled but start_research_task no longer running)
                elif is_research_complete(content, research_started_flag):
                    elapsed_minutes = (time.time() - start_time) / 60
                    print(f"✅ Research completed after {elapsed_minutes:.1f} minutes!")
                    print(f"📊 Final content length: {len(content):,} characters")
                    # Show final detailed information
                    monitor_research_progress(thread_id, agents_client, last_message_id)
                    return current_message
                
                # Show detailed progress during research
                elif research_started_flag:
                    monitor_research_progress(thread_id, agents_client, last_message_id)
                
                last_message_id = current_message.id
            
            # Show elapsed time periodically
            elapsed_minutes = (time.time() - start_time) / 60
            if int(elapsed_minutes * 4) % 4 == 0:  # Every 30 seconds (4 times per minute)
                if research_started_flag:
                    print(f"⏱️  Research in progress - Elapsed: {elapsed_minutes:.1f}/{max_wait_minutes} minutes")
                else:
                    print(f"⏱️  Waiting for research to start - Elapsed: {elapsed_minutes:.1f}/{max_wait_minutes} minutes")
                
        except Exception as e:
            print(f"Error checking research status: {e}")
        
        time.sleep(check_interval)
    
    elapsed_minutes = (time.time() - start_time) / 60
    print(f"\n⚠️  Timeout after {elapsed_minutes:.1f} minutes.")
    
    if research_started_flag:
        print("   Research was started but may not have completed.")
    else:
        print("   Research never started - check if there were any errors.")
    
    # Return the latest message even if not complete
    return agents_client.messages.get_last_message_by_role(
        thread_id=thread_id, role=MessageRole.AGENT
    )


def create_research_summary(
        message: ThreadMessage,
        filepath: str = "research_summary.md"
) -> None:
    if not message:
        print("No message content provided, cannot create research summary.")
        return

    with open(filepath, "w", encoding="utf-8") as fp:
        # Add header with timestamp
        fp.write(f"# Research Report\n")
        fp.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write text summary
        text_summary = "\n\n".join([t.text.value.strip() for t in message.text_messages])
        fp.write(text_summary)

        # Write unique URL citations, if present
        if message.url_citation_annotations:
            fp.write("\n\n## References\n")
            seen_urls = set()
            for ann in message.url_citation_annotations:
                url = ann.url_citation.url
                title = ann.url_citation.title or url
                if url not in seen_urls:
                    fp.write(f"- [{title}]({url})\n")
                    seen_urls.add(url)

    print(f"Research summary written to '{filepath}'.")


project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

conn_id = project_client.connections.get(name=os.environ["BING_RESOURCE_NAME"]).id


# Initialize a Deep Research tool with Bing Connection ID and Deep Research model deployment name
deep_research_tool = DeepResearchTool(
    bing_grounding_connection_id=conn_id,
    deep_research_model=os.environ["DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME"],
)

# Create Agent with the Deep Research tool and process Agent run
with project_client:

    with project_client.agents as agents_client:

        # Create a new agent that has the Deep Research tool attached.
        # NOTE: To add Deep Research to an existing agent, fetch it with `get_agent(agent_id)` and then,
        # update the agent with the Deep Research tool.
        agent = agents_client.create_agent(
            model=os.environ["AGENT_MODEL_DEPLOYMENT_NAME"],
            name="my-agent",
            instructions="You are a helpful Agent that assists in researching scientific topics.",
            tools=deep_research_tool.definitions,
        )

        # [END create_agent_with_deep_research_tool]
        print(f"Created agent, ID: {agent.id}")

        # Create thread for communication
        thread = agents_client.threads.create()
        print(f"Created thread, ID: {thread.id}")

        # Ask user what they want to research
        print("\n" + "="*60)
        print("🔬 DEEP RESEARCH ASSISTANT")
        print("="*60)
        print("What would you like to research?")
        print("\nExamples:")
        print("• Latest developments in quantum computing")
        print("• Climate change impact on renewable energy")
        print("• AI breakthroughs in medical diagnosis")
        print("• Recent advances in space exploration")
        print("="*60)
        
        research_topic = input("\n📝 Enter your research topic: ").strip()
        
        while not research_topic:
            print("❌ Please enter a valid research topic.")
            research_topic = input("📝 Enter your research topic: ").strip()
        
        print(f"\n✅ Research topic: {research_topic}")

        # Create initial message to thread
        message = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=research_topic,
        )
        print(f"Created message, ID: {message.id}")

        # Conduct interactive refinement session
        print("\n📋 Starting refinement process...")
        refinement_count = conduct_interactive_refinement(
            agents_client, thread.id, agent.id
        )
        
        print(f"\n✅ Refinement completed with {refinement_count} refinement(s).")

        # Now instruct the agent to start the actual research
        research_instruction = """
        Now please conduct comprehensive deep research on this topic using the Deep Research tool. 
        Gather information from multiple reliable sources and provide a detailed, well-structured report.
        """
        
        agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=research_instruction,
        )

        print("\n" + "="*60)
        print("🔍 STARTING DEEP RESEARCH")
        print("="*60)
        print("The agent is now conducting comprehensive research...")
        print("This may take several minutes. Please be patient.")
        print("="*60)

        # Start the research run
        run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
        last_message_id = None
        
        # Monitor the research run
        while run.status in ("queued", "in_progress"):
            time.sleep(2)
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            
            # Check for new messages (but don't print everything to avoid clutter)
            current_message = agents_client.messages.get_last_message_by_role(
                thread_id=thread.id, role=MessageRole.AGENT
            )
            
            if current_message and current_message.id != last_message_id:
                content = "\n".join(t.text.value for t in current_message.text_messages)
                
                if is_research_starting(content):
                    print("🚀 Deep Research Tool activated - searching sources...")
                elif len(content) > 100:
                    print(f"📝 Research in progress... ({len(content)} characters generated)")
                
                last_message_id = current_message.id
            
            print(f"⏱️  Run status: {run.status}")

        print(f"\n📋 Research run completed with status: {run.status}")

        if run.status == "failed":
            print(f"❌ Run failed: {run.last_error}")
        else:
            # Wait for the complete research results
            print("\n⏳ Waiting for complete research results...")
            final_message = wait_for_research_completion(
                agents_client, thread.id, agent.id, max_wait_minutes=25
            )
            
            if final_message:
                content = "\n".join(t.text.value for t in final_message.text_messages)
                
                # Check if research started and completed using our flag-based approach
                research_started = is_research_starting(content)
                research_complete = is_research_complete(content, research_started)
                
                if research_complete:
                    print("\n✅ RESEARCH COMPLETED SUCCESSFULLY!")
                    print("📄 Creating comprehensive research report...")
                    
                    # Create the research summary
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"research_report_{timestamp}.md"
                    create_research_summary(final_message, filename)
                    
                    # Show summary statistics
                    print(f"\n📊 Research Statistics:")
                    print(f"   • Report length: {len(content):,} characters")
                    print(f"   • File saved as: {filename}")
                    
                    if final_message.url_citation_annotations:
                        print(f"   • Sources cited: {len(final_message.url_citation_annotations)}")
                        print("   • Key sources:")
                        for i, ann in enumerate(final_message.url_citation_annotations[:5], 1):
                            title = ann.url_citation.title or "Untitled"
                            print(f"     {i}. {title}")
                        
                        if len(final_message.url_citation_annotations) > 5:
                            remaining = len(final_message.url_citation_annotations) - 5
                            print(f"     ... and {remaining} more sources")
                    
                    print(f"\n🎉 Research complete! Check '{filename}' for the full report.")
                else:
                    print("\n⚠️  Research may not be fully complete.")
                    print("📄 Saving current progress...")
                    create_research_summary(final_message, "partial_research_report.md")
                    print("💡 You may need to wait longer or try again.")
            else:
                print("\n❌ No research results found.")
                print("   The research may have failed or taken too long.")

        # Clean-up and delete the agent once the run is finished.
        # NOTE: Comment out this line if you plan to reuse the agent later.
        agents_client.delete_agent(agent.id)
        print("Deleted agent")
```

Run the script from your terminal:

```python
python create_deep_research_agent.py
```

After a while the LLM will respond with an initial response asking for some refinement. You must provide additional instructions to refine the research or just press Enter to skip this step. The agent will then perform deep research and provide a final response.

In our case this was the initial response:

```prompt
📋 Starting refinement process...

============================================================
🔍 INTERACTIVE REFINEMENT SESSION
============================================================
The agent will ask clarifying questions to improve research quality.
Answer each question or type 'done' to start the research.
============================================================

⏳ Getting clarifying question #1...

🤖 Agent Response #1:
--------------------------------------------------
Great! Could you please specify whether you’re most interested in recent breakthroughs in hardware, software algorithms, commercial applications, or theoretical advances in quantum computing?
--------------------------------------------------

💬 Your answer (or 'done' to start research): hardware
✅ Refinement 1 added.

⏳ Getting clarifying question #2...

🤖 Agent Response #2:
--------------------------------------------------
Would you like the research to focus on advances in specific quantum hardware platforms (such as superconducting qubits, trapped ions, photonics, etc.), or should I cover all major approaches in quantum computing hardware?
--------------------------------------------------

💬 Your answer (or 'done' to start research): all
✅ Refinement 2 added.

⏳ Getting clarifying question #3...

✅ Agent indicates it has sufficient information to proceed.
🚀 Starting research...

✅ Refinement completed with 2 refinement(s).

============================================================
🔍 STARTING DEEP RESEARCH
============================================================
```

You can then provide refinement instructions or you just simply say "done" to start the research.

The Deep Research tool will then perform the research.

The research can take several minutes (25 minutes in our case!) to complete so make sure to be patient. Once done, a research summary will be created in the file `final_research_summary.md`. 

![alt text](../../../media/image-deepresearch11.png)
![alt text](../../../media/image-deepresearch12.png)

# Optional: Use vibe coding to modify the script to output a Word Document
You can use vibe coding to modify the script to output a Word document instead of a markdown file. 

Go to Github Copilot and make sure Agent mode is enabled. In the prompt input section, add the following prompt:

```prompt
Modify the create_research_summary function to output a Word document instead of a markdown file. Use the python-docx library to create the Word document. The document should have a title "Research Summary", a timestamp, the text summary, and a references section with unique URL citations. Save the document as research_summary.docx.
```

While Github Copilot Agent is running it will ask for user input every now and then. Review each Human in the Loop suggestion and accept, reject or answer the questions.

In our case several iterations were needed to get the desired changes. The final version of the script is able to output both a markdown file and a Word documents:

![alt text](../../../media/image-deepresearch13.png)