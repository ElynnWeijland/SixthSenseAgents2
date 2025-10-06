<div align="center">
    <img src="../media/image-infra2.png" width="100%" alt="Azure AI Foundry">
</div>

# Azure AI Foundry Infrastructure

This directory contains the infrastructure components and deployment scripts for the Azure AI Foundry project.

## 🔐 Cost Control Policies

### HackathonPolicies.ps1

The `policies/HackathonPolicies.ps1` script is a comprehensive PowerShell solution designed to prevent expensive Azure resource deployments in hackathon and development environments. This script helps organizations maintain budget control while still enabling productive development.

#### What It Does

The script creates and deploys an **Azure Policy Initiative** that automatically blocks the deployment of expensive services including:

- **Expensive VM SKUs**: GPU instances (NC, ND, NV series), high-memory VMs (M, GS series), and large compute instances
- **Premium App Service Plans**: Premium and Isolated tier app services
- **Premium Storage**: Premium storage account SKUs that significantly increase costs
- **Expensive Database SKUs**: Premium SQL Database tiers and multi-region Cosmos DB configurations
- **High-Cost AKS Nodes**: Expensive Kubernetes node pool SKUs
- **Regional Restrictions**: Limits deployments to cost-effective Azure regions
- **Resource Count Limits**: Monitors resource count per resource group

#### Key Benefits

✅ **Proactive Cost Control**: Prevents expensive resources before they're deployed  
✅ **Hackathon Ready**: Perfect for time-boxed events with budget constraints  
✅ **Flexible Deployment**: Works at subscription, management group, or resource group scope  
✅ **Dry Run Capability**: Test policies without making actual changes  
✅ **Comprehensive Coverage**: Covers major Azure services that drive high costs  

#### Quick Start

1. **Prerequisites**
   ```powershell
   # Install required Azure PowerShell modules
   Install-Module -Name Az -Force -Scope CurrentUser
   
   # Authenticate with Azure
   Connect-AzAccount
   ```

2. **Basic Deployment**
   ```powershell
   # Navigate to the policies directory
   cd infra/policies
   
   # Deploy to your subscription
   .\HackathonPolicies.ps1 -SubscriptionId "your-subscription-id"
   ```

3. **Test First (Recommended)**
   ```powershell
   # Dry run to validate without deploying
   .\HackathonPolicies.ps1 -SubscriptionId "your-subscription-id" -DryRun
   ```

#### Deployment Options

| Scope | Command | Use Case |
|-------|---------|----------|
| **Subscription** | `.\HackathonPolicies.ps1 -SubscriptionId "sub-id"` | Single subscription control |
| **Management Group** | `.\HackathonPolicies.ps1 -SubscriptionId "sub-id" -ManagementGroupId "mg-id"` | Multi-subscription governance |
| **Resource Group** | `.\HackathonPolicies.ps1 -SubscriptionId "sub-id" -ResourceGroupName "rg-name"` | Limited scope testing |

#### What Gets Created

The script creates:
- **7 Custom Policy Definitions** targeting expensive services
- **1 Policy Initiative** combining all policies
- **1 Policy Assignment** applying the initiative to your chosen scope

#### Cost Impact

Typical cost savings in hackathon environments:
- **60-80% reduction** in compute costs by blocking expensive VM SKUs
- **40-60% reduction** in storage costs by preventing premium storage
- **50-70% reduction** in database costs by restricting premium tiers
- **Regional optimization** can save 20-30% based on location

#### Monitoring and Compliance

After deployment, monitor policy effectiveness through:
- **Azure Portal**: Policy → Compliance dashboard
- **Cost Management**: Track spending patterns and denied deployments
- **Activity Log**: Review blocked deployment attempts

#### Advanced Usage

```powershell
# Deploy to specific region with custom location
.\HackathonPolicies.ps1 -SubscriptionId "sub-id" -Location "West US 2"

# Management group deployment for enterprise
.\HackathonPolicies.ps1 -SubscriptionId "sub-id" -ManagementGroupId "hackathon-mg"
```

#### Troubleshooting

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| **Module not found** | `Install-Module -Name Az -Force -Scope CurrentUser` |
| **Authentication failed** | `Connect-AzAccount` and verify subscription access |
| **Permission denied** | Ensure **Policy Contributor** role is assigned |
| **Policy creation failed** | Check Azure service availability in target region |

#### Important Notes

⚠️ **Before Deployment**: Test with `-DryRun` parameter first  
⚠️ **Permissions Required**: Policy Contributor role at deployment scope  
⚠️ **Impact**: Policies take effect immediately after assignment  
⚠️ **Scope**: Carefully choose deployment scope to avoid affecting production workloads  

#### Getting Help

For detailed documentation, examples, and troubleshooting, see:
- [`policies/README.md`](policies/README.md) - Complete documentation
- [Azure Policy Documentation](https://docs.microsoft.com/en-us/azure/governance/policy/)
- [Azure Cost Management](https://docs.microsoft.com/en-us/azure/cost-management-billing/)

---

## Other Infrastructure Components

*Additional infrastructure components and deployment scripts will be documented here as they are added to the project.*
