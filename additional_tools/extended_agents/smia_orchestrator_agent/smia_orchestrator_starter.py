"""
smia_orchestrator_starter.py
==============================
Custom Docker entrypoint for the orchestrator SMIA instance.

WHY THIS FILE EXISTS:
----------------------
Same reason as smia_machine_starter.py: the default Docker starter creates a plain
`SMIAAgent` without extension hooks. We need `ExtensibleSMIAAgent` to add the
`OrchestratorDispatchBehaviour` as a SPADE behaviour via `add_new_agent_capability()`.

This file is mounted over the default starter inside the container:
    - ../additional_tools/extended_agents/smia_orchestrator_agent/smia_orchestrator_starter.py
      → /usr/local/lib/python3.12/site-packages/smia/launchers/smia_docker_starter.py

ROLE OF THE ORCHESTRATOR:
--------------------------
The orchestrator sits between the operator and the machines:
  - Operator sends CSSRequest with {color: "red"} to orchestrator
  - Orchestrator discovers machines, filters by color, runs FIPA-CNP, dispatches execution
  - Result is forwarded back to operator

The orchestrator's AASX declares AgentCapability (PickPiece, PlacePiece) so it appears
in the operator GUI as a selectable SMIA. The actual execution logic is entirely in
OrchestratorDispatchBehaviour — the AASX capabilities serve as AAS documentation.

VOLUME MOUNTS IN DOCKER-COMPOSE:
----------------------------------
    smia_orchestrator_starter.py          → .../smia/launchers/smia_docker_starter.py
    orchestrator_dispatch_behaviour.py    → .../smia/launchers/orchestrator_dispatch_behaviour.py
"""

import logging
import os
import sys

import smia
from smia.agents.extensible_smia_agent import ExtensibleSMIAAgent
from smia.utilities.general_utils import DockerUtils

# Add the launcher directory to sys.path so we can import orchestrator_dispatch_behaviour,
# which is mounted in the same directory inside the container.
sys.path.insert(0, os.path.dirname(__file__))

from orchestrator_dispatch_behaviour import OrchestratorDispatchBehaviour

_logger = logging.getLogger(__name__)


def main():
    # ----------------------------------------------------------------
    # Step 1: Initial self-configuration
    # ----------------------------------------------------------------
    # Reads smia-initialization.properties from the AASX or config folder.
    # Must be called before any other smia operation.
    smia.initial_self_configuration()
    _logger.info("Orchestrator SMIA: initial self-configuration complete.")

    # ----------------------------------------------------------------
    # Step 2: Load the AAS model
    # ----------------------------------------------------------------
    # AAS_MODEL_NAME env var → /smia_archive/config/aas/Orchestrator_case0.aasx
    # The orchestrator AASX declares AgentCapability for PickPiece and PlacePiece,
    # making the orchestrator visible in the operator GUI as an available SMIA.
    aas_model_path = DockerUtils.get_aas_model_from_env_var()
    _logger.info(f"Orchestrator SMIA: loading AAS model from {aas_model_path}")
    smia.load_aas_model(aas_model_path)

    # ----------------------------------------------------------------
    # Step 3: Read XMPP credentials
    # ----------------------------------------------------------------
    # AGENT_ID=smia_orch@ejabberd, AGENT_PASSWD=password
    smia_jid = os.environ.get('AGENT_ID')
    smia_passwd = os.environ.get('AGENT_PASSWD')

    # ----------------------------------------------------------------
    # Step 4: Create extensible agent
    # ----------------------------------------------------------------
    smia_agent = ExtensibleSMIAAgent(smia_jid, smia_passwd)

    # ----------------------------------------------------------------
    # Step 5: Add the orchestration behaviour
    # ----------------------------------------------------------------
    # OrchestratorDispatchBehaviour is a CyclicBehaviour that:
    #   - Intercepts CSSRequests from the operator (thread-reservation pattern)
    #   - Discovers machines from AAS folder, filters by color
    #   - Broadcasts FIPA-CNP CFP to eligible machines
    #   - Receives winner INFORM, sends execution CSSRequest to winner
    #   - Forwards execution result back to operator
    #
    # add_new_agent_capability() accepts a SPADE behaviour INSTANCE (not the class).
    # The instance is appended to extended_agent_capabilities and started alongside
    # the base SMIA behaviours (ACLHandlingBehaviour, NegotiatingBehaviour, etc.)
    # when smia.run() is called.
    orch_behaviour = OrchestratorDispatchBehaviour()
    smia_agent.add_new_agent_capability(orch_behaviour)
    _logger.info("Orchestrator SMIA: registered OrchestratorDispatchBehaviour.")

    # ----------------------------------------------------------------
    # Step 6: Start the agent
    # ----------------------------------------------------------------
    # After booting (InitAASModelBehaviour CSS self-configuration), the agent enters
    # StateRunning. All registered behaviours — including OrchestratorDispatchBehaviour
    # and the base ACLHandlingBehaviour — run concurrently in SPADE's asyncio event loop.
    smia.run(smia_agent)


if __name__ == '__main__':
    main()
