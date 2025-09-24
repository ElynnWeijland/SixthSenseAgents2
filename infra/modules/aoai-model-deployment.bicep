@description('Resource ID of an Azure AI Foundry resource (kind=AIServices) or Azure OpenAI account (kind=OpenAI).')
param openAIAccountId string

@description('Deployment name.')
param deploymentName string = 'gpt41'

@description('Model name.')
param modelName string = 'gpt-4.1'

@minValue(1)
param capacity int = 30

var openAIAccountName = last(split(openAIAccountId, '/'))

resource openAI 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openAIAccountName
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: deploymentName
  parent: openAI
  sku: {
    name: 'GlobalStandard'
    capacity: capacity
  }
  properties: {
    model: {
      name: modelName
      format: 'OpenAI'
    }
    // Optional: versionUpgradeOption: 'OnceCurrentVersionExpired' | 'NoAutoUpgrade'
    // Optional: raiPolicyName: 'Microsoft.Default'
  }
}

output deploymentName string = deploymentName
output modelNameOut string = modelName
output endpoint string = openAI.properties.endpoint
