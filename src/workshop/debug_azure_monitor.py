"""
Debug script to investigate Azure Monitor API responses
"""

import os
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

try:
    from azure.mgmt.monitor import MonitorManagementClient
    from azure.identity import ChainedTokenCredential, EnvironmentCredential, InteractiveBrowserCredential
except ImportError as e:
    print(f"Error importing Azure modules: {e}")
    exit(1)

load_dotenv()


def get_credential():
    """Get Azure credentials"""
    try:
        credential = ChainedTokenCredential(
            EnvironmentCredential(),
            InteractiveBrowserCredential(),
        )
        return credential
    except Exception as e:
        print(f"Failed to get credentials: {e}")
        return None


def construct_resource_id(vm_name: str) -> str:
    """Construct Azure VM resource ID"""
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP_NAME")

    if not subscription_id or not resource_group:
        print(f"Missing env vars: subscription_id={subscription_id}, resource_group={resource_group}")
        return None

    resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}"
    return resource_id


async def debug_metrics():
    """Debug Azure Monitor metrics"""

    vm_name = "VirtualMachine"
    print(f"\n🔍 Debugging Azure Monitor metrics for VM: {vm_name}\n")

    # Get credentials
    credential = get_credential()
    if not credential:
        print("❌ Failed to get Azure credentials")
        return

    # Get subscription ID
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        print("❌ AZURE_SUBSCRIPTION_ID not set")
        return

    print(f"✓ Subscription ID: {subscription_id}")

    # Construct resource ID
    resource_id = construct_resource_id(vm_name)
    if not resource_id:
        print("❌ Failed to construct resource ID")
        return

    print(f"✓ Resource ID: {resource_id}")

    # Create client
    try:
        client = MonitorManagementClient(credential, subscription_id)
        print("✓ MonitorManagementClient created")
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        return

    # Set time range
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(minutes=10)

    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    timespan_str = f"{start_str}/{end_str}"

    print(f"✓ Time range: {timespan_str}")
    print(f"  Start: {start_str}")
    print(f"  End:   {end_str}")

    # Test a single metric
    metric_name = "Percentage CPU"

    print(f"\n📊 Querying metric: {metric_name}")
    print("-" * 80)

    try:
        response = client.metrics.list(
            resource_uri=resource_id,
            timespan=timespan_str,
            interval="PT1M",
            aggregation="Maximum",
            metricnames=[metric_name],
        )

        print(f"✓ API call succeeded")
        print(f"  Response type: {type(response)}")
        print(f"  Response: {response}")

        # Debug response structure
        print(f"\n  Has 'value' attribute: {hasattr(response, 'value')}")
        if hasattr(response, 'value'):
            print(f"  response.value type: {type(response.value)}")
            print(f"  response.value length: {len(response.value) if response.value else 0}")
            print(f"  response.value: {response.value}")

            if response.value:
                for i, metric in enumerate(response.value):
                    print(f"\n  Metric #{i}:")
                    print(f"    Type: {type(metric)}")
                    print(f"    Dir: {[attr for attr in dir(metric) if not attr.startswith('_')]}")

                    # Try to access common attributes
                    if hasattr(metric, 'name'):
                        print(f"    name: {metric.name}")
                        if hasattr(metric.name, 'value'):
                            print(f"    name.value: {metric.name.value}")

                    if hasattr(metric, 'unit'):
                        print(f"    unit: {metric.unit}")

                    if hasattr(metric, 'timeseries'):
                        print(f"    timeseries type: {type(metric.timeseries)}")
                        print(f"    timeseries length: {len(metric.timeseries) if metric.timeseries else 0}")

                        if metric.timeseries:
                            for j, ts in enumerate(metric.timeseries):
                                print(f"      Timeseries #{j}:")
                                print(f"        Type: {type(ts)}")
                                print(f"        Dir: {[attr for attr in dir(ts) if not attr.startswith('_')]}")

                                if hasattr(ts, 'data'):
                                    print(f"        data type: {type(ts.data)}")
                                    print(f"        data length: {len(ts.data) if ts.data else 0}")

                                    if ts.data:
                                        print(f"        First 3 data points:")
                                        for k, dp in enumerate(ts.data[:3]):
                                            print(f"          Data point #{k}:")
                                            print(f"            Type: {type(dp)}")
                                            print(f"            Dir: {[attr for attr in dir(dp) if not attr.startswith('_')]}")

                                            if hasattr(dp, 'maximum'):
                                                print(f"            maximum: {dp.maximum}")
                                            if hasattr(dp, 'minimum'):
                                                print(f"            minimum: {dp.minimum}")
                                            if hasattr(dp, 'average'):
                                                print(f"            average: {dp.average}")
                                            if hasattr(dp, 'total'):
                                                print(f"            total: {dp.total}")
                                            if hasattr(dp, 'count'):
                                                print(f"            count: {dp.count}")
                                            if hasattr(dp, 'time_stamp'):
                                                print(f"            time_stamp: {dp.time_stamp}")
            else:
                print(f"\n  ⚠️  response.value is empty or None")

        # Try to access other attributes
        print(f"\n  Other attributes on response:")
        for attr in dir(response):
            if not attr.startswith('_') and attr != 'value':
                try:
                    val = getattr(response, attr)
                    if not callable(val):
                        print(f"    {attr}: {val}")
                except:
                    pass

    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Azure Monitor Debug Script")
    print("   Investigating Azure Monitor metrics response structure\n")

    asyncio.run(debug_metrics())

    print("\n✨ Debug complete!")
