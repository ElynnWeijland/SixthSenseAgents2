// Creates an Azure AI Foundry project as a child resource

@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object = {}

@description('Project name')
param aiProjectName string

@description('Project display name')
param aiProjectFriendlyName string = aiProjectName

@description('Project description')
param aiProjectDescription string = 'Azure AI Foundry project'

@description('Resource ID of the parent AI Foundry resource')
param aiFoundryId string

// Extract the AI Foundry account name from the resource ID
var aiFoundryAccountName = last(split(aiFoundryId, '/'))

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiFoundryAccountName
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  name: aiProjectName
  parent: aiFoundry
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: aiProjectFriendlyName
    description: aiProjectDescription
  }
}

output aiProjectId string = aiProject.id
output aiProjectName string = aiProject.name
