![alt text](image.png)

# Azure Policy Initiative for Cost Control

This directory contains PowerShell scripts for deploying Azure Policy Initiatives designed to prevent expensive services in hackathon and development environments.

## Overview

The `HackathonPolicies.ps1` script creates and deploys a comprehensive Azure Policy Initiative that restricts the use of expensive Azure services and SKUs. It's specifically designed to control costs in hackathon or development environments while still allowing productive development with cost-effective resources.

## 🔒 Policy Definitions Included

The script creates the following policy definitions to prevent expensive resource deployments:

### 1. **Expensive VM SKUs**
- **Purpose**: Blocks GPU, high-memory, and premium compute instances
- **Restricted SKUs**: 
  - GPU instances: `Standard_NC*`, `Standard_ND*`, `Standard_NV*`
  - High-memory: `Standard_GS*`, `Standard_G*`, `Standard_M*`
  - Large compute: `Standard_E64*`, `Standard_E96*`, `Standard_F72*`
  - Specialized: `Standard_H*`, `Standard_L*`

### 2. **Premium App Service Plans**
- **Purpose**: Prevents Premium and Isolated tier App Service plans
- **Restricted Tiers**: 
  - Premium (P1, P2, P3, PV2, PV3)
  - Isolated (I1, I2, I3, IsolatedV2)

### 3. **Expensive Storage SKUs**
- **Purpose**: Blocks Premium storage account types
- **Restricted SKUs**: 
  - Premium_LRS, Premium_ZRS
  - Premium_GRS, Premium_RAGRS

### 4. **Expensive Database SKUs**
- **Purpose**: Restricts Premium SQL Database and multi-region Cosmos DB
- **Restrictions**:
  - SQL Database: Premium and BusinessCritical tiers
  - Cosmos DB: Multi-write locations and failover configurations

### 5. **Expensive AKS Node SKUs**
- **Purpose**: Prevents costly Kubernetes node pool SKUs
- **Restricted SKUs**: Same as VM restrictions for AKS agent pools

### 6. **Resource Count Limits**
- **Purpose**: Audits resource count per resource group
- **Default Limit**: 50 resources per resource group
- **Effect**: Audit (logs violations without blocking)

### 7. **Region Restrictions**
- **Purpose**: Limits deployment to cost-effective regions
- **Default Allowed Regions**: 
  - East US, East US 2, West US 2, Central US
- **Benefit**: Prevents deployment to expensive regions

## 🛠 Script Capabilities

### **Flexible Deployment Scope**
- **Subscription**: Deploy policies to an entire subscription
- **Management Group**: Deploy across multiple subscriptions
- **Resource Group**: Limit scope to specific resource groups

### **Dry Run Mode**
- Test the deployment without making actual changes
- Validate policy definitions and configurations
- Perfect for testing and verification

### **Comprehensive Error Handling**
- Validates Azure authentication before proceeding
- Handles individual policy creation failures gracefully
- Provides detailed error messages and warnings

### **Modular Design**
- Easy to customize and extend with additional policies
- Well-structured functions for maintainability
- Clear separation of concerns

## 📋 Usage Examples

### Basic Deployment
Deploy to a subscription with default settings:
```powershell
.\HackathonPolicies.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012"
```

### Dry Run Testing
Test the deployment without making changes:
```powershell
.\HackathonPolicies.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -DryRun
```

### Management Group Deployment
Deploy to a management group for broader scope:
```powershell
.\HackathonPolicies.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -ManagementGroupId "mg-hackathon"
```

### Resource Group Scoped Deployment
Deploy to a specific resource group:
```powershell
.\HackathonPolicies.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -ResourceGroupName "rg-hackathon"
```

### Custom Location
Specify a different Azure region for metadata storage:
```powershell
.\HackathonPolicies.ps1 -SubscriptionId "12345678-1234-1234-1234-123456789012" -Location "West US 2"
```

## 🔧 Prerequisites

### PowerShell Requirements
- **PowerShell Version**: 5.1 or later
- **Execution Policy**: Set to allow script execution

### Required Azure PowerShell Modules
The script requires the following modules:
- `Az.Accounts` - Azure authentication and context management
- `Az.Policy` - Azure Policy management
- `Az.Resources` - Azure resource management

### Azure Authentication
- Valid Azure account with appropriate permissions
- Authenticated session using `Connect-AzAccount`

## 🚀 Installation and Setup

### 1. Install Required Modules
If the Azure PowerShell modules are not installed:
```powershell
Install-Module -Name Az.Accounts, Az.Policy, Az.Resources -Force -Scope CurrentUser
```

### 2. Authenticate with Azure
```powershell
Connect-AzAccount
```

### 3. Verify Subscription Access
```powershell
Get-AzSubscription
```

### 4. Run the Script
```powershell
# Navigate to the policies directory
cd /path/to/Azure-AI-Foundry/infra/policies

# Execute the script
.\HackathonPolicies.ps1 -SubscriptionId "your-subscription-id"
```

## 📊 Script Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `SubscriptionId` | String | Yes | Azure subscription ID for deployment | - |
| `ManagementGroupId` | String | No | Management Group ID for broader scope | - |
| `ResourceGroupName` | String | No | Resource Group name for limited scope | - |
| `Location` | String | No | Azure region for metadata storage | "East US" |
| `DryRun` | Switch | No | Test mode without actual deployment | False |

## 🔐 Required Permissions

To deploy the policies, you need the following Azure RBAC permissions:

### At Subscription Level
- **Policy Contributor** or **Owner** role
- Permissions to create policy definitions and assignments

### At Management Group Level
- **Management Group Contributor** or **Owner** role
- Policy permissions across multiple subscriptions

### At Resource Group Level
- **Policy Contributor** role on the target resource group
- Limited scope for resource-specific policies

## 📈 Monitoring and Compliance

### Policy Compliance
After deployment, monitor policy compliance through:
- **Azure Portal**: Policy > Compliance dashboard
- **Azure CLI**: `az policy state list`
- **PowerShell**: `Get-AzPolicyState`

### Cost Impact Analysis
Track cost savings by monitoring:
- Denied resource deployments
- Resource type distribution
- Regional deployment patterns

### Reporting
Generate compliance reports to track:
- Policy violation attempts
- Resource deployment patterns
- Cost control effectiveness

## 🔄 Maintenance and Updates

### Updating Policies
To modify existing policies:
1. Update the policy definitions in the script
2. Re-run the script to update deployed policies
3. Monitor compliance for any affected resources

### Adding New Policies
To add new cost control policies:
1. Add new policy definition to `Get-PolicyDefinitions` function
2. Test with `-DryRun` parameter
3. Deploy to production environment

### Removing Policies
To remove specific policies:
```powershell
# Remove policy assignment
Remove-AzPolicyAssignment -Name "hackathon-cost-control-initiative-assignment"

# Remove policy initiative
Remove-AzPolicySetDefinition -Name "hackathon-cost-control-initiative"

# Remove individual policy definitions
Remove-AzPolicyDefinition -Name "restrictExpensiveVmSkus"
```

## 🏗 Architecture and Design Principles

### Security Best Practices
- ✅ **Secure Authentication**: Uses Azure managed identity patterns
- ✅ **Least Privilege**: Implements minimal required permissions
- ✅ **Error Handling**: Comprehensive error management
- ✅ **Audit Trail**: Maintains detailed deployment logs

### Performance Optimization
- ✅ **Efficient Deployment**: Batch policy creation where possible
- ✅ **Resource Management**: Proper cleanup and resource handling
- ✅ **Scalable Design**: Supports large-scale deployments

### Maintainability
- ✅ **Modular Code**: Clear function separation
- ✅ **Documentation**: Comprehensive inline documentation
- ✅ **Extensibility**: Easy to add new policies
- ✅ **Version Control**: Git-friendly configuration

## 🎯 Cost Control Benefits

### Immediate Impact
- Prevents accidental deployment of expensive resources
- Enforces cost-conscious development practices
- Reduces cloud spend variability

### Long-term Benefits
- Builds cost awareness among development teams
- Establishes governance best practices
- Provides baseline for cost optimization strategies

### Hackathon Specific Advantages
- Enables innovation within budget constraints
- Prevents cost overruns during events
- Allows focus on development rather than cost management

## 🆘 Troubleshooting

### Common Issues

#### Authentication Errors
```powershell
# Check current context
Get-AzContext

# Re-authenticate if needed
Connect-AzAccount -Force
```

#### Module Not Found
```powershell
# Install missing modules
Install-Module -Name Az.Policy -Force
Import-Module Az.Policy
```

#### Permission Denied
- Verify RBAC permissions at the deployment scope
- Check if subscription/management group access is available
- Ensure Policy Contributor role is assigned

#### Policy Creation Failures
- Review Azure Resource Provider registrations
- Validate JSON syntax in policy definitions
- Check Azure service availability in target region

### Debugging Tips
1. Use `-DryRun` parameter to test without deployment
2. Enable verbose logging: `$VerbosePreference = "Continue"`
3. Check Azure Activity Log for detailed error messages
4. Validate policy JSON using Azure Policy validator tools

## 📚 Additional Resources

### Azure Policy Documentation
- [Azure Policy Overview](https://docs.microsoft.com/en-us/azure/governance/policy/overview)
- [Policy Definition Structure](https://docs.microsoft.com/en-us/azure/governance/policy/concepts/definition-structure)
- [Policy Assignment Structure](https://docs.microsoft.com/en-us/azure/governance/policy/concepts/assignment-structure)

### Cost Management
- [Azure Cost Management](https://docs.microsoft.com/en-us/azure/cost-management-billing/)
- [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)
- [Azure Budgets](https://docs.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)

### PowerShell Resources
- [Azure PowerShell Documentation](https://docs.microsoft.com/en-us/powershell/azure/)
- [Az.Policy Module Reference](https://docs.microsoft.com/en-us/powershell/module/az.policy/)

---

## 📝 Notes

- This script follows Azure best practices for policy deployment
- Designed specifically for hackathon and development environments
- Regular updates recommended to align with Azure service changes
- Consider testing in non-production environments first

**Author**: Azure AI Foundry Team  
**Version**: 1.0  
**Last Updated**: October 2025