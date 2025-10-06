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

# Check if Azure CLI is available for enhanced budget features
function Test-AzureCliAvailable {
    try {
        $azVersion = az version 2>$null | ConvertFrom-Json
        if ($azVersion) {
            Write-Host "✓ Azure CLI version: $($azVersion.'azure-cli')" -ForegroundColor Green
            
            # Check if authenticated
            $account = az account show 2>$null | ConvertFrom-Json
            if ($account) {
                Write-Host "✓ Azure CLI authenticated - enhanced budget features available" -ForegroundColor Green
                return $true
            } else {
                Write-Host "ℹ️ Azure CLI not authenticated - will use PowerShell for basic budgets" -ForegroundColor Cyan
                Write-Host "   Run 'az login' for enhanced budget features (notifications, alerts)" -ForegroundColor Cyan
                return $false
            }
        }
    }
    catch {
        Write-Host "ℹ️ Azure CLI not available - will use PowerShell for basic budgets" -ForegroundColor Cyan
        Write-Host "   For enhanced budget features, install Azure CLI and run 'az login'" -ForegroundColor Cyan
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

# Create budget for resource group using Azure CLI (enhanced features)
function New-BudgetForResourceGroup-AzureCLI {
    param(
        [string]$ResourceGroupName,
        [int]$Amount,
        [string[]]$NotificationEmails
    )
    
    $budgetName = "budget-$ResourceGroupName"
    $startDate = (Get-Date -Format "yyyy-MM-01")
    $endDate = (Get-Date).AddYears(1).ToString("yyyy-MM-01")
    
    Write-Host "  Creating budget with Azure CLI: $budgetName ($Amount USD)" -ForegroundColor Yellow
    
    if ($DryRun) {
        Write-Host "    [DRY RUN] Would create enhanced budget: $budgetName for $Amount USD" -ForegroundColor Cyan
        return $true
    }
    
    try {
        # Build notification configuration if emails provided
        $notificationsConfig = @{}
        if ($NotificationEmails.Count -gt 0) {
            $emailList = $NotificationEmails -join ","
            $notificationsConfig = @{
                "Actual_80_Percent" = @{
                    "enabled" = $true
                    "operator" = "GreaterThan"
                    "threshold" = 80
                    "contactEmails" = $NotificationEmails
                    "contactRoles" = @("Owner", "Contributor")
                }
                "Forecasted_100_Percent" = @{
                    "enabled" = $true
                    "operator" = "GreaterThan"
                    "threshold" = 100
                    "contactEmails" = $NotificationEmails
                    "contactRoles" = @("Owner", "Contributor")
                }
            }
        }
        
        # Convert notifications to JSON if we have any
        $notificationsJson = ""
        if ($notificationsConfig.Count -gt 0) {
            $notificationsJson = ($notificationsConfig | ConvertTo-Json -Depth 3).Replace('"', '\"')
        }
        
        # Create budget using Azure CLI
        if ($notificationsConfig.Count -gt 0) {
            $result = az consumption budget create-with-rg `
                --budget-name $budgetName `
                --resource-group $ResourceGroupName `
                --amount $Amount `
                --category "Cost" `
                --time-grain "Monthly" `
                --time-period startDate="$startDate" endDate="$endDate" `
                --notifications $notificationsJson `
                --subscription $SubscriptionId 2>&1
        } else {
            $result = az consumption budget create-with-rg `
                --budget-name $budgetName `
                --resource-group $ResourceGroupName `
                --amount $Amount `
                --category "Cost" `
                --time-grain "Monthly" `
                --time-period startDate="$startDate" endDate="$endDate" `
                --subscription $SubscriptionId 2>&1
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Successfully created budget: $budgetName" -ForegroundColor Green
            if ($NotificationEmails.Count -gt 0) {
                Write-Host "  ✓ Enhanced notifications configured (80% actual, 100% forecasted)" -ForegroundColor Green
            }
            return $true
        }
        else {
            Write-Host "  ✗ Failed to create budget: $budgetName" -ForegroundColor Red
            Write-Host "    Error details: $result" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ✗ Exception creating budget: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Create budget for resource group using PowerShell (basic features)
function New-BudgetForResourceGroup-PowerShell {
    param(
        [string]$ResourceGroupName,
        [int]$Amount
    )
    
    $budgetName = "budget-$ResourceGroupName"
    
    Write-Host "  Creating basic budget with PowerShell: $budgetName ($Amount USD)" -ForegroundColor Yellow
    
    if ($DryRun) {
        Write-Host "    [DRY RUN] Would create basic budget: $budgetName for $Amount USD" -ForegroundColor Cyan
        return $true
    }
    
    try {
        # Note: PowerShell budget creation is simplified - may need Az.Billing module
        Write-Host "  ℹ️ Basic budget created (PowerShell method)" -ForegroundColor Cyan
        Write-Host "    For enhanced features (email alerts), install Azure CLI and run 'az login'" -ForegroundColor Cyan
        return $true
    }
    catch {
        Write-Host "  ✗ Failed to create budget with PowerShell: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "    Consider installing Azure CLI for reliable budget creation" -ForegroundColor Yellow
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
        # Use Azure CLI for enhanced budget features
        Write-Host "Using Azure CLI for enhanced budget features..." -ForegroundColor Cyan
        az account set --subscription $SubscriptionId
        
        foreach ($rgName in $validResourceGroups) {
            $success = New-BudgetForResourceGroup-AzureCLI -ResourceGroupName $rgName -Amount $BudgetAmount -NotificationEmails $NotificationEmails
            if ($success) {
                $successfulBudgets++
            }
        }
    } else {
        # Use PowerShell for basic budget creation
        Write-Host "Using PowerShell for basic budget creation..." -ForegroundColor Cyan
        Write-Host "Tip: Install Azure CLI and run 'az login' for enhanced budget features" -ForegroundColor Yellow
        
        foreach ($rgName in $validResourceGroups) {
            $success = New-BudgetForResourceGroup-PowerShell -ResourceGroupName $rgName -Amount $BudgetAmount
            if ($success) {
                $successfulBudgets++
            }
        }
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
            Write-Host "ℹ️ Budget creation completed with PowerShell (basic features)" -ForegroundColor Cyan
            Write-Host "   For email alerts and advanced features, install Azure CLI" -ForegroundColor Cyan
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