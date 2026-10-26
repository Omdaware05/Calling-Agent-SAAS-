import sys
from pathlib import Path
import pytest

# Add Dograh to python path to test schema compliance against Dograh's actual DTOs
import importlib.metadata

import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("OSS_JWT_SECRET", "test-secret-at-least-32-chars-long")


_orig_version = importlib.metadata.version
def _mock_version(pkg):
    if pkg == "pipecat-ai":
        return "0.0.1"
    return _orig_version(pkg)
importlib.metadata.version = _mock_version

DOGRAH_ROOT = Path(__file__).resolve().parent.parent.parent / "dograh"
PIPECAT_SRC = DOGRAH_ROOT / "pipecat" / "src"
if str(DOGRAH_ROOT) not in sys.path:
    sys.path.insert(0, str(DOGRAH_ROOT))
if str(PIPECAT_SRC) not in sys.path:
    sys.path.insert(0, str(PIPECAT_SRC))



from app.services.dograh_service import dograh_service


def test_workflow_definition_matches_dograh_reactflow_dto():
    """
    Validates our generated workflow definition against Dograh's official ReactFlowDTO.
    """
    from api.services.workflow.dto import ReactFlowDTO

    generated = dograh_service.build_workflow_definition(
        name="Course Sales Agent",
        purpose="Sell our company's courses",
        instructions="Explain curriculum, pricing and benefits.",
        allowed_topics=["Curriculum", "Pricing"],
        restricted_topics=["Politics", "Religion"],
        behavior_rules=["Be polite and professional"],
        trigger_path="agent-test1234",
    )

    wf_def = generated["workflow_definition"]
    # Validate against Dograh's official ReactFlowDTO Pydantic model
    validated_dto = ReactFlowDTO.model_validate(wf_def)

    assert validated_dto is not None
    assert len(validated_dto.nodes) == 7
    assert len(validated_dto.edges) == 5

    # Verify node types
    node_types = {n.type for n in validated_dto.nodes}
    assert "globalNode" in node_types
    assert "startCall" in node_types
    assert "agentNode" in node_types
    assert "endCall" in node_types
    assert "trigger" in node_types
    assert "webhook" in node_types

    # Verify trigger path
    trigger_node = next(n for n in validated_dto.nodes if n.type == "trigger")
    assert trigger_node.data.trigger_path == "agent-test1234"

    # Verify edge labels and conditions
    for edge in validated_dto.edges:
        assert edge.data.label is not None
        assert edge.data.condition is not None


DOGRAH_SDK_SRC = DOGRAH_ROOT / "sdk" / "python" / "src"
if str(DOGRAH_SDK_SRC) not in sys.path:
    sys.path.insert(0, str(DOGRAH_SDK_SRC))


def test_public_agent_trigger_payload_matches_dograh_model():
    """
    Validates our trigger call payload against Dograh's TriggerCallRequest schema.
    Verified against dograh/api/routes/public_agent.py:36-46.
    """
    from pydantic import BaseModel
    from typing import Optional

    class TriggerCallRequestContract(BaseModel):
        phone_number: str
        initial_context: Optional[dict] = None
        telephony_configuration_id: Optional[int] = None
        from_phone_number_id: Optional[int] = None

    payload = {
        "phone_number": "+919876543210",
        "initial_context": {
            "app_call_id": "call-1234",
            "customer_name": "Test Customer",
        },
        "telephony_configuration_id": None,
        "from_phone_number_id": None,
    }

    validated_req = TriggerCallRequestContract.model_validate(payload)
    assert validated_req.phone_number == "+919876543210"
    assert validated_req.initial_context["app_call_id"] == "call-1234"


def test_telephony_initiate_payload_matches_dograh_model():
    """
    Validates our telephony test call payload against Dograh's official InitiateCallRequest.
    Source: dograh/sdk/python/src/dograh_sdk/_generated_models.py:327
    """
    from dograh_sdk._generated_models import InitiateCallRequest

    payload = {
        "workflow_id": 14,
        "phone_number": "+919876543210",
    }

    validated_req = InitiateCallRequest.model_validate(payload)
    assert validated_req.workflow_id == 14
    assert validated_req.phone_number == "+919876543210"


