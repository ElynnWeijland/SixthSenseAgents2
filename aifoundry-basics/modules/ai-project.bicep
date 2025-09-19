@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object = {}

@description('Project workspace name')
param aiProjectName string

@description('Project display name')
param aiProjectFriendlyName string = aiProjectName

@description('Project description')
param aiProjectDescription string = 'Sample project'

@description('Resource ID of the hub (kind=hub) workspace')
param hubId string

// NOTE: The linking property name can vary in previews.
// Commonly it is one of: hubId or hub.
// Keep only the correct property after verifying with:
// az bicep types show --resource-type Microsoft.MachineLearningServices/workspaces --api-version 2023-08-01-preview | grep -i hub
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2023-08-01-preview' = {
  name: aiProjectName
  location: location
  tags: tags
  kind: 'project'
  properties: {
    friendlyName: aiProjectFriendlyName
    description: aiProjectDescription

    // Try hubId first; if validation fails, swap to 'hub'
    hubId: hubId
    // hub: hubId
  }
}

output aiProjectId string = aiProject.id
