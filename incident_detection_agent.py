import importlib.util
import os
from types import ModuleType

# Load the actual agent implementation from src/workshop/incident_detection_agent.py
_impl_path = os.path.join(os.path.dirname(__file__), "src", "workshop", "incident_detection_agent.py")
_spec = importlib.util.spec_from_file_location("sixthsense_incident_detection_agent_impl", _impl_path)
_impl = ModuleType("sixthsense_incident_detection_agent_impl")
if _spec and _spec.loader:
    _spec.loader.exec_module(_impl)  # type: ignore

# Re-export expected symbols for tests and other imports
try:
    create_incident_ticket = getattr(_impl, "create_incident_ticket")
except AttributeError:
    create_incident_ticket = None

try:
    raise_incident_in_slack = getattr(_impl, "raise_incident_in_slack")
except AttributeError:
    raise_incident_in_slack = None

__all__ = ["create_incident_ticket", "raise_incident_in_slack"]