// Creates an Azure AI Foundry resource for unified AI services

@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('AI Foundry resource name')
param aiFoundryName string

@description('AI Foundry display name')
param aiFoundryFriendlyName string = aiFoundryName

@description('AI Foundry description')
param aiFoundryDescription string

@description('The SKU name for the AI Foundry resource')
@allowed(['S0'])
param skuName string = 'S0'

@description('Whether public network access is allowed')
@allowed(['Enabled', 'Disabled'])
param publicNetworkAccess string = 'Enabled'

@description('Custom subdomain name for the AI Foundry resource')
param customSubDomainName string = ''

@description('Whether to disable local authentication')
param disableLocalAuth bool = false

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: aiFoundryName
  location: location
  tags: union(tags, {
    displayName: aiFoundryFriendlyName
    description: aiFoundryDescription
  })
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: skuName
  }
  properties: {
    customSubDomainName: !empty(customSubDomainName) ? customSubDomainName : aiFoundryName
    publicNetworkAccess: publicNetworkAccess
    disableLocalAuth: disableLocalAuth
    apiProperties: {
      // API properties can be extended here for specific requirements
    }
    networkAcls: {
      defaultAction: 'Allow'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

output aiFoundryId string = aiFoundry.id
output aiFoundryName string = aiFoundry.name
output aiFoundryEndpoint string = aiFoundry.properties.endpoint
output aiFoundryPrincipalId string = aiFoundry.identity.principalId
