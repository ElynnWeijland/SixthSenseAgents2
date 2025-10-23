# Benefits Agent - Data Sources

The Benefits Agent uses real business data from the following documents to calculate financial impact:

## Data Sources

### 1. Action_Webshopdata_Business_Case.docx
**Location**: `/src/Action_Webshopdata_Business_Case.docx`

**Contains**:
- Webshop visitor and revenue data per hour
- Daily revenue: ~€246,000
- Weekly revenue: ~€1.7 million
- Conversion rates by time of day
- Peak hours: 12:00-18:00 (€18,667/hour)

**Hourly Revenue Breakdown**:
| Time Period | Revenue/Hour |
|-------------|--------------|
| 00:00-06:00 | €2,667       |
| 06:00-09:00 | €3,333       |
| 09:00-12:00 | €12,000      |
| 12:00-15:00 | €18,667      |
| 15:00-18:00 | €18,667      |
| 18:00-21:00 | €16,000      |
| 21:00-00:00 | €8,000       |

### 2. VM_Kostenoverzicht_Azure.docx
**Location**: `/src/VM_Kostenoverzicht_Azure.docx`

**Contains**:
- Azure VM pricing for West-Europa region
- CPU, RAM, and disk costs
- Scalability information

**VM Costs Used**:
| VM Type | vCPU | RAM | Cost/Hour | Usage |
|---------|------|-----|-----------|-------|
| B2s | 2 | 8 GiB | €0.0832 | Test/Dev |
| B4as_v2 | 4 | 16 GiB | €0.1500 | Production |
| B16s_v2 | 16 | 64 GiB | €0.6660 | Heavy Compute |
| D4s_v3 | 4 | 16 GiB | €0.2500 | General Purpose |

## How the Data is Used

### In benefits_agent.py

1. **CONTEXTUAL_DATA Dictionary**:
   - Stores all business case and VM cost data
   - Updated from hardcoded values to real document data

2. **get_revenue_per_hour_by_time()**:
   - Returns accurate revenue/hour based on incident time
   - Uses time-specific data from business case

3. **get_vm_cost_per_hour()**:
   - Infers VM type from VM name
   - Returns actual Azure costs from cost overview

4. **async_calculate_benefits()**:
   - Main calculation function
   - Uses revenue data to calculate prevented losses
   - Includes VM infrastructure costs
   - Adds business context to results

5. **async_send_benefits_to_slack()**:
   - Sends financial analysis to Slack incident channel
   - Formats benefits in a clear, visual Slack message
   - Includes revenue preserved, cost savings, and total benefit
   - Automatically called after benefit calculations

## Calculation Methodology

When an incident is prevented, the benefits agent calculates:

1. **Direct Cost Savings**:
   - Developer time saved (€75/hour × hours saved)
   - Based on manual resolution time vs automated

2. **Revenue Preserved**:
   - Uses time-specific revenue data
   - Calculates: `downtime_minutes × revenue_per_minute`
   - Example: 30 min downtime at 15:00 = 30 × €311.11 = €9,333

3. **Infrastructure Context**:
   - Shows VM hourly cost
   - Indicates operational cost during incident

4. **Customer Impact**:
   - €500 base cost for customer dissatisfaction
   - Full value if automated, 50% if escalated

## Example Output

For a 30-minute CPU issue on "webshop-prod-01" at 15:00:

```json
{
  "calculations": {
    "developer_cost_saved_eur": 150,
    "revenue_per_hour_at_incident_time_eur": 18667,
    "revenue_per_minute_eur": 311.11,
    "revenue_preserved_eur": 9333.33,
    "vm_hourly_cost_eur": 0.15,
    "customer_satisfaction_value_eur": 500,
    "total_benefit_eur": 9983.33
  },
  "business_context": {
    "webshop_daily_revenue_eur": 246000,
    "webshop_weekly_revenue_eur": 1700000,
    "peak_revenue_hours": "12:00-18:00 (€18,667/hour)"
  }
}
```

## Slack Integration

### Configuration

The benefits agent automatically sends financial analysis to Slack after completing calculations. Configure the following environment variables in your `.env` file:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL=#incidents
```

### Slack Message Format

The benefits agent sends a formatted message to the Slack incident channel with:

- **Header**: Financial Benefits Analysis
- **Incident Description**: Summary of the resolved issue
- **Resolution Method**: How the incident was resolved
- **Downtime Prevented**: Minutes of downtime prevented
- **Affected System**: VM name
- **Financial Impact**:
  - Revenue Preserved
  - Developer Cost Saved
  - Total Benefit (highlighted)
- **Context**: Data source reference and timestamp

### Workflow

1. Resolution agent fixes the incident
2. Benefits agent calculates financial impact
3. Benefits agent automatically sends analysis to Slack
4. Team is immediately informed of the value created

## Maintenance

To update the business data:
1. Update the .docx source files in `/src/`
2. Extract new values using python-docx
3. Update `CONTEXTUAL_DATA` in `benefits_agent.py`
4. Update this documentation file

To modify Slack integration:
1. Update `async_send_benefits_to_slack()` in `benefits_agent.py`
2. Modify the Slack Block Kit formatting as needed
3. Ensure SLACK_BOT_TOKEN has proper permissions
