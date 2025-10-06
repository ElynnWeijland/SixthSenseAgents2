#Requires -Modules Az.Resources, Az.Accounts
<#
.SYNOPSIS
    Deploy Azure Policy Initiative to prevent expensive services for hackathon environments.

.DESCRIPTION
    This script creates and deploys a comprehensive Azure Policy Initiative that restricts
    the use of expensive Azure services and SKUs. It's designed to control costs in
    hackathon or development environments while still allowing productive development.

.PARAMETER SubscriptionId
    The Azure subscription ID where the policies will be deployed.

.PARAMETER ManagementGroupId
    Optional. Management Group ID for broader scope deployment.

.PARAMETER ResourceGroupName
    Optional. Resource Group name for resource-level scope.

.PARAMETER Location
    Azure region for metadata storage. Default is 'East US'.

.PARAMETER DryRun
    If specified, only validates the policy definitions without deploying them.

.EXAMPLE
    .\HackathonPolicies.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012"

.EXAMPLE
    .\HackathonPolicies.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -DryRun

.NOTES
    Author: Azure AI Foundry Team
    Version: 1.0
    Requires: PowerShell 5.1 or later, Az PowerShell modules
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory = $false)]
    [string]$ManagementGroupId,
    
    [Parameter(Mandatory = $false)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory = $false)]
    [string]$Location = "East US",
    
    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

# Import required modules
$RequiredModules = @('Az.Accounts', 'Az.Resources')
foreach ($Module in $RequiredModules) {
    if (!(Get-Module -ListAvailable -Name $Module)) {
        Write-Error "Required module '$Module' is not installed. Please run: Install-Module -Name $Module"
        exit 1
    }
    Import-Module $Module -Force
}

# Global variables
$PolicyInitiativeName = "hackathon-cost-control-initiative"
$PolicyInitiativeDisplayName = "Hackathon Cost Control Initiative"
$PolicyInitiativeDescription = "Comprehensive policy initiative to prevent expensive Azure services in hackathon environments"

# Authentication check
function Test-AzureAuthentication {
    try {
        $context = Get-AzContext
        if (-not $context) {
            Write-Host "No Azure context found. Please run Connect-AzAccount first." -ForegroundColor Red
            return $false
        }
        
        Write-Host "Authenticated as: $($context.Account.Id)" -ForegroundColor Green
        Write-Host "Current subscription: $($context.Subscription.Name) ($($context.Subscription.Id))" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Error "Failed to check Azure authentication: $($_.Exception.Message)"
        return $false
    }
}

# Set the subscription context
function Set-AzureSubscription {
    param([string]$SubscriptionId)
    
    try {
        Write-Host "Setting subscription context to: $SubscriptionId" -ForegroundColor Yellow
        $null = Set-AzContext -SubscriptionId $SubscriptionId
        Write-Host "Successfully set subscription context" -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to set subscription context: $($_.Exception.Message)"
        exit 1
    }
}

# Define policy definitions for expensive services
function Get-PolicyDefinitions {
    return @{
        "restrictExpensiveVmSkus" = @{
            displayName = "Restrict Expensive VM SKUs"
            description = "Prevents deployment of expensive VM SKUs like GPU, high-memory, and premium compute instances"
            mode = "All"
            policyRule = @{
                if = @{
                    allOf = @(
                        @{
                            field = "type"
                            equals = "Microsoft.Compute/virtualMachines"
                        },
                        @{
                            anyOf = @(
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_NC*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_ND*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_NV*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_GS*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_G*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_M*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_E64*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_E96*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_F72*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_H*" },
                                @{ field = "Microsoft.Compute/virtualMachines/sku.name"; like = "Standard_L*" }
                            )
                        }
                    )
                }
                then = @{
                    effect = "deny"
                }
            }
        }
        
        "restrictPremiumAppServicePlans" = @{
            displayName = "Restrict Premium App Service Plans"
            description = "Prevents deployment of Premium and Isolated App Service Plans"
            mode = "All"
            policyRule = @{
                if = @{
                    allOf = @(
                        @{
                            field = "type"
                            equals = "Microsoft.Web/serverfarms"
                        },
                        @{
                            anyOf = @(
                                @{ field = "Microsoft.Web/serverfarms/sku.tier"; like = "Premium*" },
                                @{ field = "Microsoft.Web/serverfarms/sku.tier"; equals = "Isolated" },
                                @{ field = "Microsoft.Web/serverfarms/sku.tier"; equals = "IsolatedV2" },
                                @{ field = "Microsoft.Web/serverfarms/sku.name"; like = "P*" },
                                @{ field = "Microsoft.Web/serverfarms/sku.name"; like = "I*" }
                            )
                        }
                    )
                }
                then = @{
                    effect = "deny"
                }
            }
        }
        
        "restrictExpensiveStorageSkus" = @{
            displayName = "Restrict Expensive Storage SKUs"
            description = "Prevents deployment of Premium and Ultra SSD storage"
            mode = "All"
            policyRule = @{
                if = @{
                    allOf = @(
                        @{
                            field = "type"
                            equals = "Microsoft.Storage/storageAccounts"
                        },
                        @{
                            anyOf = @(
                                @{ field = "Microsoft.Storage/storageAccounts/sku.name"; equals = "Premium_LRS" },
                                @{ field = "Microsoft.Storage/storageAccounts/sku.name"; equals = "Premium_ZRS" },
                                @{ field = "Microsoft.Storage/storageAccounts/sku.name"; equals = "Premium_GRS" },
                                @{ field = "Microsoft.Storage/storageAccounts/sku.name"; equals = "Premium_RAGRS" }
                            )
                        }
                    )
                }
                then = @{
                    effect = "deny"
                }
            }
        }
        
        "restrictExpensiveDatabaseSkus" = @{
            displayName = "Restrict Expensive Database SKUs"
            description = "Prevents deployment of expensive SQL Database and Cosmos DB SKUs"
            mode = "All"
            policyRule = @{
                if = @{
                    anyOf = @(
                        @{
                            allOf = @(
                                @{
                                    field = "type"
                                    equals = "Microsoft.Sql/servers/databases"
                                },
                                @{
                                    anyOf = @(
                                        @{ field = "Microsoft.Sql/servers/databases/sku.tier"; equals = "Premium" },
                                        @{ field = "Microsoft.Sql/servers/databases/sku.tier"; equals = "BusinessCritical" },
                                        @{ field = "Microsoft.Sql/servers/databases/sku.name"; like = "P*" },
                                        @{ field = "Microsoft.Sql/servers/databases/sku.name"; like = "BC_*" }
                                    )
                                }
                            )
                        },
                        @{
                            allOf = @(
                                @{
                                    field = "type"
                                    equals = "Microsoft.DocumentDB/databaseAccounts"
                                },
                                @{
                                    anyOf = @(
                                        @{ field = "Microsoft.DocumentDB/databaseAccounts/enableMultipleWriteLocations"; equals = "true" },
                                        @{ field = "Microsoft.DocumentDB/databaseAccounts/locations[*].failoverPriority"; greater = 0 }
                                    )
                                }
                            )
                        }
                    )
                }
                then = @{
                    effect = "deny"
                }
            }
        }
        
        "restrictExpensiveAKSNodes" = @{
            displayName = "Restrict Expensive AKS Node SKUs"
            description = "Prevents deployment of expensive AKS node pool SKUs"
            mode = "All"
            policyRule = @{
                if = @{
                    allOf = @(
                        @{
                            field = "type"
                            equals = "Microsoft.ContainerService/managedClusters/agentPools"
                        },
                        @{
                            anyOf = @(
                                @{ field = "Microsoft.ContainerService/managedClusters/agentPools/vmSize"; like = "Standard_NC*" },
                                @{ field = "Microsoft.ContainerService/managedClusters/agentPools/vmSize"; like = "Standard_ND*" },
                                @{ field = "Microsoft.ContainerService/managedClusters/agentPools/vmSize"; like = "Standard_NV*" },
                                @{ field = "Microsoft.ContainerService/managedClusters/agentPools/vmSize"; like = "Standard_GS*" },
                                @{ field = "Microsoft.ContainerService/managedClusters/agentPools/vmSize"; like = "Standard_M*" },
                                @{ field = "Microsoft.ContainerService/managedClusters/agentPools/vmSize"; like = "Standard_E64*" },
                                @{ field = "Microsoft.ContainerService/managedClusters/agentPools/vmSize"; like = "Standard_F72*" }
                            )
                        }
                    )
                }
                then = @{
                    effect = "deny"
                }
            }
        }
        
        "limitResourceCount" = @{
            displayName = "Limit Resource Count per Resource Group"
            description = "Limits the number of resources that can be created in a resource group"
            mode = "All"
            policyRule = @{
                if = @{
                    allOf = @(
                        @{
                            field = "type"
                            notIn = @(
                                "Microsoft.Resources/subscriptions/resourceGroups",
                                "Microsoft.Authorization/roleAssignments",
                                "Microsoft.Authorization/policyAssignments"
                            )
                        }
                    )
                }
                then = @{
                    effect = "audit"
                }
            }
            parameters = @{
                maxResourceCount = @{
                    type = "Integer"
                    metadata = @{
                        displayName = "Maximum Resource Count"
                        description = "Maximum number of resources allowed per resource group"
                    }
                    defaultValue = 50
                }
            }
        }
        
        "restrictRegions" = @{
            displayName = "Restrict Deployment Regions"
            description = "Restricts resource deployment to specific Azure regions to control costs"
            mode = "All"
            policyRule = @{
                if = @{
                    allOf = @(
                        @{
                            field = "location"
                            exists = "true"
                        },
                        @{
                            field = "location"
                            notIn = "[parameters('allowedLocations')]"
                        }
                    )
                }
                then = @{
                    effect = "deny"
                }
            }
            parameters = @{
                allowedLocations = @{
                    type = "Array"
                    metadata = @{
                        displayName = "Allowed Locations"
                        description = "List of allowed Azure regions for resource deployment"
                        strongType = "location"
                    }
                    defaultValue = @("eastus", "eastus2", "westus2", "centralus")
                }
            }
        }
    }
}

# Create or update policy definition
function New-CustomPolicyDefinition {
    param(
        [string]$Name,
        [hashtable]$Definition,
        [string]$Scope
    )
    
    try {
        Write-Host "Creating policy definition: $($Definition.displayName)" -ForegroundColor Yellow
        
        $policyDefinition = @{
            Name = $Name
            DisplayName = $Definition.displayName
            Description = $Definition.description
            Policy = ($Definition.policyRule | ConvertTo-Json -Depth 10)
            Mode = $Definition.mode
        }
        
        if ($Definition.parameters) {
            $policyDefinition.Parameter = ($Definition.parameters | ConvertTo-Json -Depth 10)
        }
        
        if ($Scope) {
            $policyDefinition.ManagementGroupName = $Scope
        }
        
        if ($DryRun) {
            Write-Host "DRY RUN: Would create policy definition: $($Definition.displayName)" -ForegroundColor Cyan
            return $null
        }
        
        $result = New-AzPolicyDefinition @policyDefinition
        Write-Host "Successfully created policy definition: $($Definition.displayName)" -ForegroundColor Green
        return $result
    }
    catch {
        Write-Error "Failed to create policy definition '$($Definition.displayName)': $($_.Exception.Message)"
        throw
    }
}

# Create policy initiative
function New-PolicyInitiative {
    param(
        [array]$PolicyDefinitions,
        [string]$Scope
    )
    
    try {
        Write-Host "Creating policy initiative: $PolicyInitiativeDisplayName" -ForegroundColor Yellow
        
        # Build policy definitions array for the initiative
        $policyDefArray = @()
        foreach ($policy in $PolicyDefinitions) {
            if ($policy) {
                $policyDefArray += @{
                    policyDefinitionId = $policy.PolicyDefinitionId
                }
            }
        }
        
        $initiativeDefinition = @{
            Name = $PolicyInitiativeName
            DisplayName = $PolicyInitiativeDisplayName
            Description = $PolicyInitiativeDescription
            PolicyDefinition = ($policyDefArray | ConvertTo-Json -Depth 5)
        }
        
        if ($Scope) {
            $initiativeDefinition.ManagementGroupName = $Scope
        }
        
        if ($DryRun) {
            Write-Host "DRY RUN: Would create policy initiative: $PolicyInitiativeDisplayName" -ForegroundColor Cyan
            return $null
        }
        
        $result = New-AzPolicySetDefinition @initiativeDefinition
        Write-Host "Successfully created policy initiative: $PolicyInitiativeDisplayName" -ForegroundColor Green
        return $result
    }
    catch {
        Write-Error "Failed to create policy initiative: $($_.Exception.Message)"
        throw
    }
}

# Assign policy initiative
function New-PolicyAssignment {
    param(
        [object]$PolicyInitiative,
        [string]$Scope
    )
    
    try {
        Write-Host "Assigning policy initiative to scope: $Scope" -ForegroundColor Yellow
        
        $assignmentName = "$PolicyInitiativeName-assignment"
        $assignmentDisplayName = "$PolicyInitiativeDisplayName Assignment"
        
        if ($DryRun) {
            Write-Host "DRY RUN: Would assign policy initiative to scope: $Scope" -ForegroundColor Cyan
            return $null
        }
        
        $assignment = New-AzPolicyAssignment `
            -Name $assignmentName `
            -DisplayName $assignmentDisplayName `
            -Description "Assignment of $PolicyInitiativeDisplayName to control costs" `
            -PolicySetDefinition $PolicyInitiative `
            -Scope $Scope
            
        Write-Host "Successfully assigned policy initiative" -ForegroundColor Green
        return $assignment
    }
    catch {
        Write-Error "Failed to assign policy initiative: $($_.Exception.Message)"
        throw
    }
}

# Determine deployment scope
function Get-DeploymentScope {
    if ($ManagementGroupId) {
        return "/providers/Microsoft.Management/managementGroups/$ManagementGroupId"
    }
    elseif ($ResourceGroupName) {
        return "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"
    }
    else {
        return "/subscriptions/$SubscriptionId"
    }
}

# Main execution
function Main {
    Write-Host "=== Azure Policy Initiative Deployment Script ===" -ForegroundColor Cyan
    Write-Host "Purpose: Deploy cost control policies for hackathon environments" -ForegroundColor Cyan
    Write-Host ""
    
    # Validate authentication
    if (-not (Test-AzureAuthentication)) {
        Write-Host "Please authenticate with Azure first using: Connect-AzAccount" -ForegroundColor Red
        exit 1
    }
    
    # Set subscription context
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    # Determine scope
    $deploymentScope = Get-DeploymentScope
    Write-Host "Deployment scope: $deploymentScope" -ForegroundColor Yellow
    
    # Get policy definitions
    $policyDefinitions = Get-PolicyDefinitions
    
    # Create individual policy definitions
    $createdPolicies = @()
    foreach ($policyName in $policyDefinitions.Keys) {
        try {
            $policy = New-CustomPolicyDefinition -Name $policyName -Definition $policyDefinitions[$policyName] -Scope $ManagementGroupId
            if ($policy) {
                $createdPolicies += $policy
            }
        }
        catch {
            Write-Warning "Failed to create policy '$policyName', continuing with others..."
        }
    }
    
    if ($createdPolicies.Count -eq 0 -and -not $DryRun) {
        Write-Error "No policies were created successfully. Aborting initiative creation."
        exit 1
    }
    
    # Create policy initiative
    if ($createdPolicies.Count -gt 0 -or $DryRun) {
        $initiative = New-PolicyInitiative -PolicyDefinitions $createdPolicies -Scope $ManagementGroupId
        
        # Assign policy initiative
        if ($initiative -or $DryRun) {
            $assignment = New-PolicyAssignment -PolicyInitiative $initiative -Scope $deploymentScope
        }
    }
    
    Write-Host ""
    Write-Host "=== Deployment Summary ===" -ForegroundColor Cyan
    Write-Host "Policy definitions created: $($createdPolicies.Count)" -ForegroundColor Green
    Write-Host "Initiative created: $(if ($initiative -or $DryRun) { 'Yes' } else { 'No' })" -ForegroundColor Green
    Write-Host "Assignment created: $(if ($assignment -or $DryRun) { 'Yes' } else { 'No' })" -ForegroundColor Green
    
    if ($DryRun) {
        Write-Host ""
        Write-Host "This was a dry run. No actual changes were made." -ForegroundColor Yellow
        Write-Host "Remove the -DryRun parameter to deploy the policies." -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        Write-Host "Cost control policies have been successfully deployed!" -ForegroundColor Green
        Write-Host "These policies will help prevent expensive resource deployments." -ForegroundColor Green
    }
}

# Execute main function
try {
    Main
}
catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    exit 1
}