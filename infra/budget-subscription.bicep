// Subscription-level budget deployment - deploy this separately

targetScope = 'subscription'

@description('Resource Group name to filter budget for')
param resourceGroupName string

@description('Budget name')
param budgetName string

@description('Budget amount in USD')
param budgetAmount int = 500

@description('Email addresses to receive budget alerts')
param alertEmails array = []

@description('Budget category')
@allowed(['Cost', 'Usage'])
param budgetCategory string = 'Cost'

@description('Time grain for the budget')
@allowed(['Monthly', 'Quarterly', 'Annually'])
param timeGrain string = 'Monthly'

@description('Start date for the budget (YYYY-MM-DD format)')
param startDate string = utcNow('yyyy-MM-01')

@description('End date for the budget (YYYY-MM-DD format) - optional')
param endDate string = ''

resource budget 'Microsoft.Consumption/budgets@2021-10-01' = {
  name: budgetName
  properties: {
    timePeriod: {
      startDate: startDate
      endDate: !empty(endDate) ? endDate : null
    }
    timeGrain: timeGrain
    amount: budgetAmount
    category: budgetCategory
    notifications: {
      // Alert at 80% of budget
      Alert80: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        contactEmails: alertEmails
        contactRoles: [
          'Owner'
          'Contributor'
        ]
        thresholdType: 'Percentage'
      }
      // Alert at 90% of budget
      Alert90: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 90
        contactEmails: alertEmails
        contactRoles: [
          'Owner'
          'Contributor'
        ]
        thresholdType: 'Percentage'
      }
      // Alert at 100% of budget
      Alert100: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        contactEmails: alertEmails
        contactRoles: [
          'Owner'
          'Contributor'
        ]
        thresholdType: 'Percentage'
      }
      // Forecast alert at 120% (projected overspend)
      ForecastAlert120: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 120
        contactEmails: alertEmails
        contactRoles: [
          'Owner'
          'Contributor'
        ]
        thresholdType: 'Forecasted'
      }
    }
    filter: {
      and: [
        {
          dimensions: {
            name: 'ResourceGroupName'
            operator: 'In'
            values: [
              resourceGroupName
            ]
          }
        }
      ]
    }
  }
}

output budgetId string = budget.id
output budgetName string = budget.name
