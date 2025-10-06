#Requires -Modules Az.Accounts, Az.Resources
<#
.SYNOPSIS
    Create individual budgets for multiple resource groups using Azure CLI.

.DESCRIPTION
    This script creates $500 budgets for each specified resource group using Azure CLI commands.
    It's designed to work alongside the policy deployment script for complete cost control.

.PARAMETER SubscriptionId
    The Azure subscription ID where budgets will be created.

.PARAMETER ResourceGroupNames
    Array of resource group names to create budgets for.

.PARAMETER BudgetAmount
    Budget amount per resource group in USD. Default is 500.

.PARAMETER NotificationEmails
    Array of email addresses to receive budget alerts.

.EXAMPLE
    .\CreateBudgets.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -ResourceGroupNames @("rg-team1", "rg-team2", "rg-team3")

.EXAMPLE
    .\CreateBudgets.ps1 -SubscriptionId "sub-id" -ResourceGroupNames @("rg-team1", "rg-team2") -BudgetAmount 750 -NotificationEmails @("admin@company.com", "manager@company.com")
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
    [string[]]$NotificationEmails = @()
)

function Test-AzureCliInstalled {
    try {
        $azVersion = az version 2>$null | ConvertFrom-Json
        if ($azVersion) {
            Write-Host "Azure CLI version: $($azVersion.'azure-cli')" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "Azure CLI is not installed or not in PATH" -ForegroundColor Red
        Write-Host "Please install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
        return $false
    }
    return $false
}

function Test-AzureCliAuthentication {
    try {
        $account = az account show 2>$null | ConvertFrom-Json
        if ($account) {
            Write-Host "Authenticated as: $($account.user.name)" -ForegroundColor Green
            Write-Host "Current subscription: $($account.name) ($($account.id))" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "Not authenticated with Azure CLI" -ForegroundColor Red
        Write-Host "Please run: az login" -ForegroundColor Yellow
        return $false
    }
    return $false
}

function New-ResourceGroupBudget {
    param(
        [string]$SubscriptionId,
        [string]$ResourceGroupName,
        [int]$Amount,
        [string[]]$NotificationEmails
    )
    
    $budgetName = "budget-$ResourceGroupName"
    $startDate = (Get-Date -Format "yyyy-MM-01")
    $endDate = (Get-Date).AddYears(1).ToString("yyyy-MM-01")
    
    Write-Host "Creating budget: $budgetName for Resource Group: $ResourceGroupName" -ForegroundColor Yellow
    
    # Create the budget JSON
    $budgetJson = @{
        properties = @{
            category = "Cost"
            amount = $Amount
            timeGrain = "Monthly"
            timePeriod = @{
                startDate = $startDate
                endDate = $endDate
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
    
    # Add notifications if emails provided
    if ($NotificationEmails.Count -gt 0) {
        $emailList = $NotificationEmails -join ","
        
        $budgetJson.properties.notifications["Actual_GreaterThan_80_Percent"] = @{
            enabled = $true
            operator = "GreaterThan"
            threshold = 80
            contactEmails = $NotificationEmails
            contactRoles = @("Owner", "Contributor")
            thresholdType = "Actual"
        }
        
        $budgetJson.properties.notifications["Forecasted_GreaterThan_100_Percent"] = @{
            enabled = $true
            operator = "GreaterThan"
            threshold = 100
            contactEmails = $NotificationEmails
            contactRoles = @("Owner", "Contributor")
            thresholdType = "Forecasted"
        }
    }
    
    # Convert to JSON and save to temp file
    $tempFile = [System.IO.Path]::GetTempFileName() + ".json"
    $budgetJson | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding utf8
    
    try {
        # Create budget using Azure CLI
        $scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"
        
        Write-Host "  Executing: az consumption budget create" -ForegroundColor Gray
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
                    --notification-key "Actual_GreaterThan_80_Percent" `
                    --operator "GreaterThan" `
                    --threshold 80 `
                    --contact-emails $emailList `
                    --contact-roles "Owner" "Contributor" `
                    --subscription $SubscriptionId 2>$null
                
                # 100% forecasted threshold
                az consumption budget create-notification `
                    --budget-name $budgetName `
                    --notification-key "Forecasted_GreaterThan_100_Percent" `
                    --operator "GreaterThan" `
                    --threshold 100 `
                    --contact-emails $emailList `
                    --contact-roles "Owner" "Contributor" `
                    --subscription $SubscriptionId 2>$null
                    
                Write-Host "  ✓ Budget notifications configured" -ForegroundColor Green
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
    finally {
        # Clean up temp file
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force
        }
    }
}

# Main execution
Write-Host "=== Azure Budget Creation Script ===" -ForegroundColor Cyan
Write-Host "Purpose: Create individual budgets for multiple resource groups" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
if (-not (Test-AzureCliInstalled)) {
    exit 1
}

if (-not (Test-AzureCliAuthentication)) {
    exit 1
}

# Set subscription
Write-Host "Setting subscription context..." -ForegroundColor Yellow
az account set --subscription $SubscriptionId

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set subscription context"
    exit 1
}

Write-Host "✓ Subscription context set to: $SubscriptionId" -ForegroundColor Green
Write-Host ""

# Create budgets for each resource group
$successCount = 0
$totalCount = $ResourceGroupNames.Count

Write-Host "Creating budgets for $totalCount resource groups..." -ForegroundColor Yellow
Write-Host "Budget amount per resource group: `$$BudgetAmount" -ForegroundColor Yellow

if ($NotificationEmails.Count -gt 0) {
    Write-Host "Notification emails: $($NotificationEmails -join ', ')" -ForegroundColor Yellow
}

Write-Host ""

foreach ($rgName in $ResourceGroupNames) {
    $success = New-ResourceGroupBudget -SubscriptionId $SubscriptionId -ResourceGroupName $rgName -Amount $BudgetAmount -NotificationEmails $NotificationEmails
    if ($success) {
        $successCount++
    }
    Write-Host ""
}

# Summary
Write-Host "=== Budget Creation Summary ===" -ForegroundColor Cyan
Write-Host "Total Resource Groups: $totalCount" -ForegroundColor Green
Write-Host "Successful Budget Creations: $successCount" -ForegroundColor Green
Write-Host "Failed Budget Creations: $($totalCount - $successCount)" -ForegroundColor $(if ($totalCount - $successCount -eq 0) { "Green" } else { "Red" })

if ($successCount -eq $totalCount) {
    Write-Host ""
    Write-Host "🎉 All budgets created successfully!" -ForegroundColor Green
    Write-Host "Each resource group now has a `$$BudgetAmount monthly budget with alerts." -ForegroundColor Green
}
elseif ($successCount -gt 0) {
    Write-Host ""
    Write-Host "⚠️ Some budgets were created successfully." -ForegroundColor Yellow
    Write-Host "Check the output above for any failures and retry if needed." -ForegroundColor Yellow
}
else {
    Write-Host ""
    Write-Host "❌ No budgets were created successfully." -ForegroundColor Red
    Write-Host "Please check your permissions and try again." -ForegroundColor Red
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Verify budgets in Azure Portal > Cost Management + Billing > Budgets" -ForegroundColor Yellow
Write-Host "2. Monitor spending and alerts" -ForegroundColor Yellow
Write-Host "3. Adjust thresholds if needed" -ForegroundColor Yellow