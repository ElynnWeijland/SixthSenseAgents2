// Creates a Grounding with Bing Search resource for Azure AI Foundry agents

@description('Tags to add to the resources')
param tags object

@description('Grounding with Bing Search resource name')
param bingGroundingSearchName string

@description('Grounding with Bing Search display name')
param bingGroundingSearchFriendlyName string = bingGroundingSearchName

@description('Grounding with Bing Search description')
param bingGroundingSearchDescription string = 'Grounding with Bing Search for AI agents'

@description('The SKU name for the Grounding with Bing Search resource')
@allowed(['S1'])
param skuName string = 'S1'

@description('Whether public network access is allowed')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Whether to disable local authentication')
param disableLocalAuth bool = false

resource bingGroundingSearch 'Microsoft.Bing/accounts@2025-05-01-preview' = {
  name: bingGroundingSearchName
  location: 'global'
  tags: union(tags, {
    displayName: bingGroundingSearchFriendlyName
    description: bingGroundingSearchDescription
  })
  kind: 'BingGroundingSearch'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: skuName
  }
  properties: {
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: disableLocalAuth
    networkAcls: {
      defaultAction: 'Allow'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

output bingGroundingSearchId string = bingGroundingSearch.id
output bingGroundingSearchName string = bingGroundingSearch.name
output bingGroundingSearchEndpoint string = bingGroundingSearch.properties.endpoint
output bingGroundingSearchPrincipalId string = bingGroundingSearch.identity.principalId
// Note: Access keys should be retrieved securely in the consuming module when needed
