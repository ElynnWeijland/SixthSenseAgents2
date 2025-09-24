#!/bin/bash

# Post-deployment script to create Grounding with Bing Search connection
# This script should be run after the main deployment is complete

set -e

# Parameters
RESOURCE_GROUP_NAME=${1:-""}
AI_FOUNDRY_NAME=${2:-""}
BING_GROUNDING_SEARCH_NAME=${3:-""}
CONNECTION_NAME=${4:-"BingGroundingSearchConnection"}

if [ -z "$RESOURCE_GROUP_NAME" ] || [ -z "$AI_FOUNDRY_NAME" ] || [ -z "$BING_GROUNDING_SEARCH_NAME" ]; then
    echo "Usage: $0 <resource-group-name> <ai-foundry-name> <bing-grounding-search-name> [connection-name]"
    echo ""
    echo "Example:"
    echo "  $0 my-rg aif-demo-1234 bgs-demo-1234"
    exit 1
fi

echo "Creating Grounding with Bing Search connection..."
echo "Resource Group: $RESOURCE_GROUP_NAME"
echo "AI Foundry: $AI_FOUNDRY_NAME" 
echo "Bing Grounding Search: $BING_GROUNDING_SEARCH_NAME"
echo "Connection Name: $CONNECTION_NAME"

# Get the AI project name (assuming it follows the naming convention)
PROJECT_NAME=$(echo $AI_FOUNDRY_NAME | sed 's/aif-/prj-/')

# Get Bing Grounding Search resource ID and access key
BING_RESOURCE_ID=$(az resource show --resource-group $RESOURCE_GROUP_NAME --name $BING_GROUNDING_SEARCH_NAME --resource-type "Microsoft.Bing/accounts" --query id -o tsv)
BING_ACCESS_KEY=$(az resource invoke-action --resource-group $RESOURCE_GROUP_NAME --name $BING_GROUNDING_SEARCH_NAME --resource-type "Microsoft.Bing/accounts" --action listKeys --query key1 -o tsv)

echo "Bing Resource ID: $BING_RESOURCE_ID"

# Create the connection using Azure CLI (this may require preview extension)
# Note: This command may not work until the preview CLI extension supports this resource type
echo "Creating connection (may require manual setup in Azure AI Foundry portal)..."

cat << EOF

To manually create the connection in Azure AI Foundry portal:
1. Navigate to https://ai.azure.com
2. Open your project: $PROJECT_NAME
3. Go to Settings > Connections
4. Click "Add connection"
5. Select "Grounding with Bing Search"
6. Use Resource ID: $BING_RESOURCE_ID
7. Name the connection: $CONNECTION_NAME

Or use this information in your application:
- Resource ID: $BING_RESOURCE_ID
- Connection Name: $CONNECTION_NAME

EOF

echo "Script completed. Connection may need to be created manually in the portal."