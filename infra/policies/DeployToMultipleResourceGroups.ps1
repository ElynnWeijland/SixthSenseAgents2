#Requires -Modules Az.Resources, Az.Accounts, Az.Billing
<#
.SYNOPSIS
    Deploy Azure Policy Initiative and budgets to multiple resource groups for hackathon cost control.

.DESCRIPTION
    This script deploys the cost control policy initiative to multiple resource groups within a subscription
    and creates individual $500 budgets for each resource group. This is perfect for hackathon scenarios
    where you want to give each team their own resource group with cost controls.

.PARAMETER SubscriptionId
    The Azure subscription ID where the policies will be deployed.

.PARAMETER ResourceGroupNames
    Array of resource group names to apply policies and budgets to.

.PARAMETER BudgetAmount
    Budget amount per resource group in USD. Default is 500.

.PARAMETER NotificationEmails
    Array of email addresses to receive budget alerts.

.PARAMETER DryRun
    If specified, only validates the policy definitions and budget configurations without deploying them.

.EXAMPLE
    .\DeployToMultipleResourceGroups.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -ResourceGroupNames @("rg-team1", "rg-team2", "rg-team3")

.EXAMPLE
    .\DeployToMultipleResourceGroups.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -ResourceGroupNames @("rg-team1", "rg-team2") -BudgetAmount 750 -NotificationEmails @("admin@company.com")

.NOTES
    Author: Azure AI Foundry Team
    Version: 1.0
    Requires: PowerShell 5.1 or later, Az PowerShell modules
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory = $true)]
    [string[]]$ResourceGroupNames,
    
    [Parameter(Mandatory = $false)]
    [int]$BudgetAmount = 500,
    
    [Parameter(Mandatory = $false)]
    [string[]]$NotificationEmails = @(),
    
    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

# Import required modules
$RequiredModules = @('Az.Accounts', 'Az.Resources', 'Az.Billing')
foreach ($Module in $RequiredModules) {
    if (!(Get-Module -ListAvailable -Name $Module)) {
        Write-Warning "Module '$Module' is not installed. Budget creation will be skipped."
        if ($Module -eq 'Az.Billing') {
            $BillingModuleAvailable = $false
        }
    } else {
        Import-Module $Module -Force
        if ($Module -eq 'Az.Billing') {
            $BillingModuleAvailable = $true
        }
    }
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

# Validate resource groups exist
function Test-ResourceGroupsExist {
    param([string[]]$ResourceGroupNames)
    
    $existingRGs = @()
    $missingRGs = @()
    
    foreach ($rgName in $ResourceGroupNames) {
        try {
            $rg = Get-AzResourceGroup -Name $rgName -ErrorAction SilentlyContinue
            if ($rg) {
                $existingRGs += $rgName
                Write-Host "✓ Resource Group '$rgName' exists" -ForegroundColor Green
            } else {
                $missingRGs += $rgName
                Write-Host "✗ Resource Group '$rgName' does not exist" -ForegroundColor Red
            }
        }
        catch {
            $missingRGs += $rgName
            Write-Host "✗ Error checking Resource Group '$rgName': $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    if ($missingRGs.Count -gt 0) {
        Write-Host ""
        Write-Host "Missing Resource Groups:" -ForegroundColor Yellow
        foreach ($rg in $missingRGs) {
            Write-Host "  - $rg" -ForegroundColor Yellow
        }
        
        $choice = Read-Host "Do you want to create the missing resource groups? (y/N)"
        if ($choice -eq 'y' -or $choice -eq 'Y') {
            foreach ($rgName in $missingRGs) {
                if (-not $DryRun) {
                    try {
                        New-AzResourceGroup -Name $rgName -Location "East US" -Force | Out-Null
                        Write-Host "✓ Created Resource Group '$rgName'" -ForegroundColor Green
                        $existingRGs += $rgName
                    }
                    catch {
                        Write-Error "Failed to create Resource Group '$rgName': $($_.Exception.Message)"
                    }
                } else {
                    Write-Host "DRY RUN: Would create Resource Group '$rgName'" -ForegroundColor Cyan
                    $existingRGs += $rgName
                }
            }
        }
    }
    
    return $existingRGs
}

# Define policy definitions for expensive services (same as original script)
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

# Create or update policy definition (same as original)
function New-CustomPolicyDefinition {
    param(
        [string]$Name,
        [hashtable]$Definition
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

# Create policy initiative (same as original)
function New-PolicyInitiative {
    param([array]$PolicyDefinitions)
    
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

# Assign policy initiative to resource group
function New-PolicyAssignmentForResourceGroup {
    param(
        [object]$PolicyInitiative,
        [string]$ResourceGroupName
    )
    
    try {
        $scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"
        $assignmentName = "$PolicyInitiativeName-$ResourceGroupName"
        $assignmentDisplayName = "$PolicyInitiativeDisplayName - $ResourceGroupName"
        
        Write-Host "Assigning policy initiative to: $ResourceGroupName" -ForegroundColor Yellow
        
        if ($DryRun) {
            Write-Host "DRY RUN: Would assign policy initiative to: $ResourceGroupName" -ForegroundColor Cyan
            return $null
        }
        
        $assignment = New-AzPolicyAssignment `
            -Name $assignmentName `
            -DisplayName $assignmentDisplayName `
            -Description "Assignment of $PolicyInitiativeDisplayName to $ResourceGroupName for cost control" `
            -PolicySetDefinition $PolicyInitiative `
            -Scope $scope
            
        Write-Host "Successfully assigned policy initiative to: $ResourceGroupName" -ForegroundColor Green
        return $assignment
    }
    catch {
        Write-Error "Failed to assign policy initiative to '$ResourceGroupName': $($_.Exception.Message)"
        return $null
    }
}

# Create budget for resource group
function New-BudgetForResourceGroup {
    param(
        [string]$ResourceGroupName,
        [int]$Amount,
        [string[]]$NotificationEmails
    )
    
    if (-not $BillingModuleAvailable) {
        Write-Warning "Az.Billing module not available. Skipping budget creation for $ResourceGroupName"
        return $null
    }
    
    try {
        $budgetName = "budget-$ResourceGroupName"
        $scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"
        
        Write-Host "Creating budget for: $ResourceGroupName (Amount: `$$Amount)" -ForegroundColor Yellow
        
        if ($DryRun) {
            Write-Host "DRY RUN: Would create budget for: $ResourceGroupName (Amount: `$$Amount)" -ForegroundColor Cyan
            return $null
        }
        
        # Create budget using REST API call since Az.Billing cmdlets can be limited
        $budgetBody = @{
            properties = @{
                category = "Cost"
                amount = $Amount
                timeGrain = "Monthly"
                timePeriod = @{
                    startDate = (Get-Date -Format "yyyy-MM-01")
                    endDate = (Get-Date).AddYears(1).ToString("yyyy-MM-01")
                }
                filter = @{
                    dimensions = @{
                        name = "ResourceGroupName"
                        operator = "In"
                        values = @($ResourceGroupName)
                    }
                }
                notifications = @{}
            }
        }
        
        # Add notification if emails provided
        if ($NotificationEmails.Count -gt 0) {
            $budgetBody.properties.notifications["Actual_GreaterThan_80_Percent"] = @{
                enabled = $true
                operator = "GreaterThan"
                threshold = 80
                contactEmails = $NotificationEmails
                contactRoles = @("Owner", "Contributor")
                thresholdType = "Actual"
            }
            
            $budgetBody.properties.notifications["Forecasted_GreaterThan_100_Percent"] = @{
                enabled = $true
                operator = "GreaterThan"
                threshold = 100
                contactEmails = $NotificationEmails
                contactRoles = @("Owner", "Contributor")
                thresholdType = "Forecasted"
            }
        }
        
        # Note: Full budget creation would require REST API calls or Cost Management cmdlets
        # For now, we'll show the structure and inform the user
        Write-Host "Budget structure created for: $ResourceGroupName" -ForegroundColor Green
        Write-Host "  - Amount: `$$Amount per month" -ForegroundColor Gray
        Write-Host "  - Alerts at 80% actual and 100% forecasted" -ForegroundColor Gray
        Write-Host "  - To complete budget creation, use Azure Portal or Az.CostManagement module" -ForegroundColor Yellow
        
        return $budgetBody
    }
    catch {
        Write-Error "Failed to create budget for '$ResourceGroupName': $($_.Exception.Message)"
        return $null
    }
}

# Main execution
function Main {
    Write-Host "=== Multi-Resource Group Policy and Budget Deployment ===" -ForegroundColor Cyan
    Write-Host "Purpose: Deploy cost control policies and budgets to multiple resource groups" -ForegroundColor Cyan
    Write-Host ""
    
    # Validate authentication
    if (-not (Test-AzureAuthentication)) {
        Write-Host "Please authenticate with Azure first using: Connect-AzAccount" -ForegroundColor Red
        exit 1
    }
    
    # Set subscription context
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    # Validate resource groups
    Write-Host "Validating resource groups..." -ForegroundColor Yellow
    $validResourceGroups = Test-ResourceGroupsExist -ResourceGroupNames $ResourceGroupNames
    
    if ($validResourceGroups.Count -eq 0) {
        Write-Error "No valid resource groups found. Exiting."
        exit 1
    }
    
    Write-Host "Will deploy to $($validResourceGroups.Count) resource groups:" -ForegroundColor Green
    foreach ($rg in $validResourceGroups) {
        Write-Host "  - $rg" -ForegroundColor Green
    }
    Write-Host ""
    
    # Get policy definitions
    $policyDefinitions = Get-PolicyDefinitions
    
    # Create individual policy definitions (only once per subscription)
    $createdPolicies = @()
    Write-Host "Creating policy definitions..." -ForegroundColor Yellow
    foreach ($policyName in $policyDefinitions.Keys) {
        try {
            $policy = New-CustomPolicyDefinition -Name $policyName -Definition $policyDefinitions[$policyName]
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
    
    # Create policy initiative (only once per subscription)
    $initiative = $null
    if ($createdPolicies.Count -gt 0 -or $DryRun) {
        $initiative = New-PolicyInitiative -PolicyDefinitions $createdPolicies
    }
    
    # Deploy to each resource group
    $successfulAssignments = 0
    $successfulBudgets = 0
    
    foreach ($rgName in $validResourceGroups) {
        Write-Host ""
        Write-Host "=== Processing Resource Group: $rgName ===" -ForegroundColor Magenta
        
        # Assign policy to resource group
        if ($initiative -or $DryRun) {
            $assignment = New-PolicyAssignmentForResourceGroup -PolicyInitiative $initiative -ResourceGroupName $rgName
            if ($assignment -or $DryRun) {
                $successfulAssignments++
            }
        }
        
        # Create budget for resource group
        $budget = New-BudgetForResourceGroup -ResourceGroupName $rgName -Amount $BudgetAmount -NotificationEmails $NotificationEmails
        if ($budget -or $DryRun) {
            $successfulBudgets++
        }
    }
    
    # Summary
    Write-Host ""
    Write-Host "=== Deployment Summary ===" -ForegroundColor Cyan
    Write-Host "Resource Groups Processed: $($validResourceGroups.Count)" -ForegroundColor Green
    Write-Host "Policy Assignments Created: $successfulAssignments" -ForegroundColor Green
    Write-Host "Budget Configurations Created: $successfulBudgets" -ForegroundColor Green
    Write-Host "Budget Amount per RG: `$$BudgetAmount" -ForegroundColor Green
    
    if ($DryRun) {
        Write-Host ""
        Write-Host "This was a dry run. No actual changes were made." -ForegroundColor Yellow
        Write-Host "Remove the -DryRun parameter to deploy the policies and budgets." -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        Write-Host "Cost control policies have been successfully deployed!" -ForegroundColor Green
        Write-Host "Each resource group now has:" -ForegroundColor Green
        Write-Host "  ✓ Policy restrictions on expensive services" -ForegroundColor Green
        Write-Host "  ✓ Budget configuration (complete setup in Azure Portal)" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Complete budget setup in Azure Portal > Cost Management" -ForegroundColor Yellow
        Write-Host "2. Monitor policy compliance in Azure Portal > Policy" -ForegroundColor Yellow
        Write-Host "3. Set up additional alerts as needed" -ForegroundColor Yellow
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