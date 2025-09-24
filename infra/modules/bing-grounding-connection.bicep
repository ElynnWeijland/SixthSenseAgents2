// Creates a Grounding with Bing Search connection for Azure AI Foundry projects

@description('AI Project resource ID')
param aiProjectId string

@description('Grounding with Bing Search resource ID')  
param bingGroundingSearchId string

@description('Connection name')
param connectionName string = 'BingGroundingSearchConnection'

@description('Whether to create the connection')
param createConnection bool = true

// Extract project information from resource ID
var projectResourceParts = split(aiProjectId, '/')
var aiFoundryAccountName = projectResourceParts[8]
var aiProjectName = projectResourceParts[10]

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: aiFoundryAccountName
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  name: aiProjectName
  parent: aiFoundry
}

// Create Bing Grounding Search connection
resource bingGroundingConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = if (createConnection) {
  name: connectionName
  parent: aiProject
  properties: {
    category: 'BingGroundingSearch'
    target: bingGroundingSearchId
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: listKeys(bingGroundingSearchId, '2025-05-01-preview').key1
    }
    metadata: {
      ResourceId: bingGroundingSearchId
    }
  }
}

output connectionId string = createConnection ? bingGroundingConnection.id : ''
output connectionName string = createConnection ? bingGroundingConnection.name : ''
