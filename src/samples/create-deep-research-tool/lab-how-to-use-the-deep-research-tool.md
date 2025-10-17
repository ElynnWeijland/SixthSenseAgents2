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
The Deep Research tool requires the latest prerelease versions of the azure-ai-projects library. First we recommend creating a virtual environment to work in. Open the file src/samples/deep-research-tool.py and run it.

Run the script from your terminal:

```python
python src/samples/deep-research-tool.py
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