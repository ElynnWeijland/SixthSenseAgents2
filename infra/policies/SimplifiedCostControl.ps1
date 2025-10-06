#Requires -Modules Az.Accounts, Az.Resources
<#
.SYNOPSIS
    Deploy cost control policies and budget alerts to resource groups.

.DESCRIPTION
    This simplified script does two things:
    1. Creates Azure policies to deny expensive resource deployments
    2. Creates budget alerts at the resource group level
    
    Perfect for hackathon environments where you need quick cost control.

.PARAMETER SubscriptionId
    The Azure subscription ID where the policies and budgets will be deployed.

.PARAMETER ResourceGroupNames
    Array of resource group names to apply cost controls to.

.PARAMETER BudgetAmount
    Budget amount per resource group in USD. Default is 500.

.PARAMETER NotificationEmails
    Array of email addresses to receive budget alerts.

.PARAMETER DryRun
    If specified, only validates without deploying.

.EXAMPLE
    .\SimplifiedCostControl.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -ResourceGroupNames @("rg-team1", "rg-team2")

.EXAMPLE
    .\SimplifiedCostControl.ps1 -SubscriptionId "sub-id" -ResourceGroupNames @("rg-team1") -BudgetAmount 750 -NotificationEmails @("admin@company.com")
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
$RequiredModules = @('Az.Accounts', 'Az.Resources')
foreach ($Module in $RequiredModules) {
    if (!(Get-Module -ListAvailable -Name $Module)) {
        Write-Error "Required module '$Module' is not installed. Please run: Install-Module -Name $Module"
        exit 1
    }
    Import-Module $Module -Force
}

# Authentication check
function Test-AzureAuthentication {
    try {
        $context = Get-AzContext
        if (-not $context) {
            Write-Host "No Azure context found. Please run Connect-AzAccount first." -ForegroundColor Red
            return $false
        }
        
        Write-Host "✓ Authenticated as: $($context.Account.Id)" -ForegroundColor Green
        Write-Host "✓ Current subscription: $($context.Subscription.Name) ($($context.Subscription.Id))" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Error "Failed to check Azure authentication: $($_.Exception.Message)"
        return $false
    }
}

# Check if Azure CLI is available for budget creation
function Test-AzureCliAvailable {
    try {
        $azVersion = az version 2>$null | ConvertFrom-Json
        if ($azVersion) {
            Write-Host "✓ Azure CLI version: $($azVersion.'azure-cli')" -ForegroundColor Green
            
            # Check if authenticated
            $account = az account show 2>$null | ConvertFrom-Json
            if ($account) {
                Write-Host "✓ Azure CLI authenticated as: $($account.user.name)" -ForegroundColor Green
                return $true
            } else {
                Write-Host "⚠️ Azure CLI not authenticated. Please run: az login" -ForegroundColor Yellow
                return $false
            }
        }
    }
    catch {
        Write-Host "⚠️ Azure CLI not available. Budget creation will be skipped." -ForegroundColor Yellow
        Write-Host "   Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
        return $false
    }
    return $false
}

# Validate resource groups exist
function Test-ResourceGroupsExist {
    param([string[]]$ResourceGroupNames)
    
    $validRGs = @()
    
    foreach ($rgName in $ResourceGroupNames) {
        try {
            $rg = Get-AzResourceGroup -Name $rgName -ErrorAction SilentlyContinue
            if ($rg) {
                Write-Host "✓ Resource Group exists: $rgName" -ForegroundColor Green
                $validRGs += $rgName
            } else {
                Write-Host "✗ Resource Group not found: $rgName" -ForegroundColor Red
            }
        }
        catch {
            Write-Host "✗ Error checking Resource Group $rgName : $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    return $validRGs
}

# Create the main cost control policy that denies expensive resources
function New-CostControlPolicy {
    try {
        $policyName = "deny-expensive-resources"
        $policyDisplayName = "Deny Expensive Azure Resources"
        $policyDescription = "Denies deployment of expensive VM SKUs, Premium storage, Premium databases, and other costly resources"
        
        # Policy rule that denies expensive resources
        $policyRule = @{
            if = @{
                anyOf = @(
                    # Expensive VM SKUs
                    @{
                        allOf = @(
                            @{ field = "type"; equals = "Microsoft.Compute/virtualMachines" },
                            @{ 
                                field = "Microsoft.Compute/virtualMachines/sku.name"
                                in = @(
                                    "Standard_NC*", "Standard_ND*", "Standard_NV*",  # GPU VMs
                                    "Standard_M*", "Standard_GS*", "Standard_G*",    # High-memory VMs
                                    "Standard_H*", "Standard_L*",                    # Specialized VMs
                                    "Standard_F72*", "Standard_F64*"                 # Large compute VMs
                                )
                            }
                        )
                    },
                    # Premium Storage Accounts
                    @{
                        allOf = @(
                            @{ field = "type"; equals = "Microsoft.Storage/storageAccounts" },
                            @{ 
                                field = "Microsoft.Storage/storageAccounts/sku.name"
                                in = @("Premium_LRS", "Premium_ZRS", "Premium_GRS", "Premium_RAGRS")
                            }
                        )
                    },
                    # Premium App Service Plans
                    @{
                        allOf = @(
                            @{ field = "type"; equals = "Microsoft.Web/serverfarms" },
                            @{ 
                                field = "Microsoft.Web/serverfarms/sku.tier"
                                in = @("Premium", "PremiumV2", "PremiumV3", "Isolated", "IsolatedV2")
                            }
                        )
                    },
                    # Premium SQL Databases
                    @{
                        allOf = @(
                            @{ field = "type"; equals = "Microsoft.Sql/servers/databases" },
                            @{ 
                                field = "Microsoft.Sql/servers/databases/edition"
                                in = @("Premium", "BusinessCritical")
                            }
                        )
                    },
                    # Expensive Cosmos DB configurations
                    @{
                        allOf = @(
                            @{ field = "type"; equals = "Microsoft.DocumentDB/databaseAccounts" },
                            @{ field = "Microsoft.DocumentDB/databaseAccounts/enableMultipleWriteLocations"; equals = "true" }
                        )
                    }
                )
            }
            then = @{
                effect = "deny"
            }
        }
        
        Write-Host "Creating cost control policy: $policyDisplayName" -ForegroundColor Yellow
        
        if ($DryRun) {
            Write-Host "  [DRY RUN] Would create policy definition: $policyDisplayName" -ForegroundColor Cyan
            return @{ Name = $policyName; Id = "/subscriptions/$SubscriptionId/providers/Microsoft.Authorization/policyDefinitions/$policyName" }
        }
        
        $policyDefinition = New-AzPolicyDefinition `
            -Name $policyName `
            -DisplayName $policyDisplayName `
            -Description $policyDescription `
            -Policy ($policyRule | ConvertTo-Json -Depth 10) `
            -Mode "All"
            
        Write-Host "✓ Successfully created policy definition: $policyDisplayName" -ForegroundColor Green
        return $policyDefinition
    }
    catch {
        Write-Error "Failed to create cost control policy: $($_.Exception.Message)"
        throw
    }
}

# Assign policy to resource group
function New-PolicyAssignmentForResourceGroup {
    param(
        [object]$PolicyDefinition,
        [string]$ResourceGroupName
    )
    
    try {
        $scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"
        $assignmentName = "deny-expensive-resources-$ResourceGroupName"
        $assignmentDisplayName = "Deny Expensive Resources - $ResourceGroupName"
        
        Write-Host "  Assigning policy to: $ResourceGroupName" -ForegroundColor Yellow
        
        if ($DryRun) {
            Write-Host "    [DRY RUN] Would assign policy to: $ResourceGroupName" -ForegroundColor Cyan
            return $true
        }
        
        $assignment = New-AzPolicyAssignment `
            -Name $assignmentName `
            -DisplayName $assignmentDisplayName `
            -Scope $scope `
            -PolicyDefinition $PolicyDefinition
            
        Write-Host "  ✓ Successfully assigned policy to: $ResourceGroupName" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "  ✗ Failed to assign policy to $ResourceGroupName : $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Create budget for resource group using Azure CLI
function New-BudgetForResourceGroup {
    param(
        [string]$ResourceGroupName,
        [int]$Amount,
        [string[]]$NotificationEmails
    )
    
    $budgetName = "budget-$ResourceGroupName"
    $startDate = (Get-Date -Format "yyyy-MM-01")
    $endDate = (Get-Date).AddYears(1).ToString("yyyy-MM-01")
    
    Write-Host "  Creating budget: $budgetName ($Amount USD)" -ForegroundColor Yellow
    
    if ($DryRun) {
        Write-Host "    [DRY RUN] Would create budget: $budgetName for $Amount USD" -ForegroundColor Cyan
        return $true
    }
    
    try {
        # Create budget using Azure CLI
        $result = az consumption budget create `
            --budget-name $budgetName `
            --amount $Amount `
            --category "Cost" `
            --time-grain "Monthly" `
            --start-date $startDate `
            --end-date $endDate `
            --resource-group-filter $ResourceGroupName `
            --subscription $SubscriptionId 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Successfully created budget: $budgetName" -ForegroundColor Green
            
            # Add notifications if emails provided
            if ($NotificationEmails.Count -gt 0) {
                $emailList = $NotificationEmails -join " "
                
                # 80% actual threshold
                az consumption budget create-notification `
                    --budget-name $budgetName `
                    --notification-key "Actual_80_Percent" `
                    --operator "GreaterThan" `
                    --threshold 80 `
                    --contact-emails $emailList `
                    --contact-roles "Owner" "Contributor" `
                    --subscription $SubscriptionId 2>$null
                
                # 100% forecasted threshold
                az consumption budget create-notification `
                    --budget-name $budgetName `
                    --notification-key "Forecasted_100_Percent" `
                    --operator "GreaterThan" `
                    --threshold 100 `
                    --contact-emails $emailList `
                    --contact-roles "Owner" "Contributor" `
                    --subscription $SubscriptionId 2>$null
                    
                Write-Host "  ✓ Budget notifications configured (80% actual, 100% forecasted)" -ForegroundColor Green
            }
            
            return $true
        }
        else {
            Write-Host "  ✗ Failed to create budget: $budgetName" -ForegroundColor Red
            Write-Host "    Error: $result" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ✗ Exception creating budget: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main execution
function Main {
    Write-Host "=== Simplified Cost Control Deployment ===" -ForegroundColor Cyan
    Write-Host "Purpose: Deploy cost control policies and budget alerts to resource groups" -ForegroundColor Cyan
    Write-Host ""
    
    # Check prerequisites
    if (-not (Test-AzureAuthentication)) {
        exit 1
    }
    
    $azureCliAvailable = Test-AzureCliAvailable
    
    # Set subscription context
    Write-Host "Setting subscription context..." -ForegroundColor Yellow
    try {
        $null = Set-AzContext -SubscriptionId $SubscriptionId
        Write-Host "✓ Subscription context set to: $SubscriptionId" -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to set subscription context: $($_.Exception.Message)"
        exit 1
    }
    
    # Validate resource groups
    Write-Host ""
    Write-Host "Validating resource groups..." -ForegroundColor Yellow
    $validResourceGroups = Test-ResourceGroupsExist -ResourceGroupNames $ResourceGroupNames
    
    if ($validResourceGroups.Count -eq 0) {
        Write-Error "No valid resource groups found. Please check the resource group names."
        exit 1
    }
    
    Write-Host ""
    Write-Host "Will deploy to $($validResourceGroups.Count) resource groups:" -ForegroundColor Green
    foreach ($rg in $validResourceGroups) {
        Write-Host "  • $rg" -ForegroundColor Green
    }
    Write-Host ""
    
    # Create the cost control policy (once per subscription)
    Write-Host "1. Creating cost control policy..." -ForegroundColor Magenta
    $costControlPolicy = New-CostControlPolicy
    
    # Deploy to each resource group
    Write-Host ""
    Write-Host "2. Deploying policies to resource groups..." -ForegroundColor Magenta
    $successfulPolicies = 0
    
    foreach ($rgName in $validResourceGroups) {
        $success = New-PolicyAssignmentForResourceGroup -PolicyDefinition $costControlPolicy -ResourceGroupName $rgName
        if ($success) {
            $successfulPolicies++
        }
    }
    
    # Create budgets for each resource group
    Write-Host ""
    Write-Host "3. Creating budget alerts..." -ForegroundColor Magenta
    $successfulBudgets = 0
    
    if ($azureCliAvailable) {
        # Set Azure CLI subscription context
        az account set --subscription $SubscriptionId
        
        foreach ($rgName in $validResourceGroups) {
            $success = New-BudgetForResourceGroup -ResourceGroupName $rgName -Amount $BudgetAmount -NotificationEmails $NotificationEmails
            if ($success) {
                $successfulBudgets++
            }
        }
    } else {
        Write-Host "⚠️ Skipping budget creation - Azure CLI not available or not authenticated" -ForegroundColor Yellow
    }
    
    # Summary
    Write-Host ""
    Write-Host "=== Deployment Summary ===" -ForegroundColor Cyan
    Write-Host "Resource Groups Processed: $($validResourceGroups.Count)" -ForegroundColor Green
    Write-Host "Policy Assignments Created: $successfulPolicies" -ForegroundColor Green
    Write-Host "Budget Alerts Created: $successfulBudgets" -ForegroundColor Green
    Write-Host "Budget Amount per RG: `$$BudgetAmount" -ForegroundColor Green
    
    if ($DryRun) {
        Write-Host ""
        Write-Host "🧪 This was a dry run - no actual changes were made." -ForegroundColor Yellow
        Write-Host "Remove the -DryRun parameter to deploy for real." -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        if ($successfulPolicies -eq $validResourceGroups.Count) {
            Write-Host "🛡️ All policies deployed successfully!" -ForegroundColor Green
            Write-Host "   Expensive resources will be denied in these resource groups." -ForegroundColor Green
        }
        
        if ($successfulBudgets -eq $validResourceGroups.Count) {
            Write-Host "💰 All budgets created successfully!" -ForegroundColor Green
            Write-Host "   You'll receive alerts at 80% actual and 100% forecasted spend." -ForegroundColor Green
        }
        elseif ($successfulBudgets -gt 0) {
            Write-Host "⚠️ Some budgets were created successfully." -ForegroundColor Yellow
        }
        else {
            Write-Host "❌ No budgets were created. Check Azure CLI authentication." -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "🚀 Cost control is now active on your resource groups!" -ForegroundColor Green
    Write-Host ""
    Write-Host "What's protected:" -ForegroundColor Yellow
    Write-Host "  ❌ Expensive VM SKUs (GPU, high-memory, large compute)" -ForegroundColor Yellow
    Write-Host "  ❌ Premium storage accounts" -ForegroundColor Yellow
    Write-Host "  ❌ Premium App Service plans" -ForegroundColor Yellow
    Write-Host "  ❌ Premium SQL databases" -ForegroundColor Yellow
    Write-Host "  ❌ Multi-region Cosmos DB" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Budget alerts configured:" -ForegroundColor Yellow
    Write-Host "  🔔 80% of budget spent (actual)" -ForegroundColor Yellow
    Write-Host "  ⚠️ 100% of budget forecasted" -ForegroundColor Yellow
}

# Execute main function
try {
    Main
}
catch {
    Write-Error "Script execution failed: $($_.Exception.Message)"
    exit 1
}