@description('Resource ID of the Azure OpenAI account (Microsoft.CognitiveServices/accounts with kind OpenAI).')
param openAIAccountId string

@description('Deployment name (no spaces).')
param deploymentName string = 'gpt41'

@description('Model name (e.g. gpt-4.1, gpt-4.1-mini, gpt-4o, etc.)')
param modelName string = 'gpt-4.1'

@description('Model version or `latest` if supported in your region.')
param modelVersion string = 'latest'

@description('Throughput / capacity units (depends on quota & model).')
@minValue(1)
param capacity int = 30

// Derive account name from full resource ID
var openAIAccountName = last(split(openAIAccountId, '/'))

// Reference existing Azure OpenAI account
resource openAI 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: openAIAccountName
}

// Model deployment
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAI
  name: deploymentName
  sku: {
    name: 'Standard'
    capacity: capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    scaleSettings: {
      capacity: capacity
    }
    // Uncomment if you must specify a RAI policy that exists in the account
    // raiPolicyName: 'Microsoft.Default'
  }
}

output deploymentName string = deploymentName
output modelNameOut string = modelName
output endpoint string = openAI.properties.endpoint
