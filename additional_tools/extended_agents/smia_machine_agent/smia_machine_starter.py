"""
smia_machine_starter.py
========================
Custom Docker entrypoint for all three machine SMIA instances (machine0, machine1, machine2).

WHY THIS FILE EXISTS:
----------------------
The SMIA Docker image (`ekhurtado/smia:latest-alpine`) runs the following command at startup:
    python3 -m smia.launchers.smia_docker_starter

The default `smia_docker_starter.py` creates a plain `SMIAAgent`, which does NOT support
the extension hooks (`add_new_agent_service`, `add_new_agent_capability`, etc.).

To register a custom agent service (`machineAvailValue`), we need `ExtensibleSMIAAgent`.
This file is COPY'd into the container by `my_models/docker/smia-machine/Dockerfile`:
    COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /smia_machine_starter.py
    CMD ["python3", "-u", "smia_machine_starter.py"]

The Dockerfile CMD overrides the default SMIA launcher — no Python path manipulation required.

HOW IT DIFFERS FROM THE DEFAULT STARTER:
-----------------------------------------
Default starter:
    agent = SMIAAgent(jid, password)       # no extension hooks
    smia.run(agent)

This starter:
    agent = ExtensibleSMIAAgent(jid, password)               # supports extension hooks
    agent.add_new_agent_service('machineAvailValue', fn)      # register availability service
    smia.run(agent)

Everything else (initial_self_configuration, load_aas_model, CSS self-configuration,
AID interface setup, FIPA-CNP capability handling) is handled by the SMIA framework
identically — we only add the custom service registration before run().

DOCKERFILE DEPLOYMENT:
-----------------------
Both files are COPY'd to / in the container so Python can import them:
    smia_machine_starter.py        → /smia_machine_starter.py
    smia_machine_agent_services.py → /smia_machine_agent_services.py
WORKDIR / puts / on sys.path, making `import smia_machine_agent_services` resolve correctly.

SHARED ACROSS ALL MACHINES:
-----------------------------
machine0 (red), machine1 (blue), machine2 (white) all use this same starter file.
The difference between machines is entirely in the AASX model and environment variables
(AAS_MODEL_NAME, AAS_ID, AGENT_ID, AGENT_PASSWD) — not in the Python code.
"""

import logging
import os
import sys

import smia
from smia.agents.extensible_smia_agent import ExtensibleSMIAAgent
from smia.utilities.general_utils import DockerUtils

# Ensure the launcher directory is on sys.path so we can import our services module,
# which is mounted in the same directory as this file inside the container.
sys.path.insert(0, os.path.dirname(__file__))

import smia_machine_agent_services as machine_svc

_logger = logging.getLogger(__name__)


def main():
    # ----------------------------------------------------------------
    # Step 1: Initial self-configuration
    # ----------------------------------------------------------------
    # Reads smia-initialization.properties (embedded in the AASX or in the config folder),
    # sets up logging, loads framework configuration (XMPP server address, CSS ontology
    # loading mode, etc.). Must be called before any other smia operation.
    smia.initial_self_configuration()
    _logger.info("Machine SMIA: initial self-configuration complete.")

    # ----------------------------------------------------------------
    # Step 2: Load the AAS model
    # ----------------------------------------------------------------
    # DockerUtils.get_aas_model_from_env_var() reads the AAS_MODEL_NAME environment
    # variable and prepends the configured AAS folder path (/smia_archive/config/aas/).
    # The result is the absolute path to the .aasx file inside the container.
    # smia.load_aas_model() parses the AASX using the BaSyx Python SDK and stores
    # the object store in memory for later CSS self-configuration.
    aas_model_path = DockerUtils.get_aas_model_from_env_var()
    _logger.info(f"Machine SMIA: loading AAS model from {aas_model_path}")
    smia.load_aas_model(aas_model_path)

    # ----------------------------------------------------------------
    # Step 3: Read XMPP credentials from environment variables
    # ----------------------------------------------------------------
    # AGENT_ID   → full XMPP JID, e.g. "SMIA_agent@ejabberd"
    # AGENT_PASSWD → password for this ejabberd account
    # These are set per-container in docker-compose.yml, allowing the same Docker image
    # and the same AASX to represent multiple distinct agents on the XMPP network.
    smia_jid = os.environ.get('AGENT_ID')
    smia_passwd = os.environ.get('AGENT_PASSWD')

    # ----------------------------------------------------------------
    # Step 4: Create the extensible agent
    # ----------------------------------------------------------------
    # ExtensibleSMIAAgent inherits from SMIAAgent and adds three official extension hooks:
    #   - add_new_agent_capability(behaviour): add a SPADE behaviour instance
    #   - add_new_agent_service(id, fn):       register a Python function as agent service
    #   - add_new_asset_connection(id, conn):  add a custom asset protocol handler
    # The agent is not yet started at this point — we configure extensions first.
    smia_agent = ExtensibleSMIAAgent(smia_jid, smia_passwd)

    # ----------------------------------------------------------------
    # Step 5: Register the negotiation availability service
    # ----------------------------------------------------------------
    # 'machineAvailValue' is the idShort of the SkillInterface AAS element in the
    # CapabilitiesAndSkills submodel. It is linked to Skill_NegAvailability via an
    # accessibleThroughAgentService SemanticRelationship in the AASX.
    #
    # When the orchestrator sends a FIPA-CNP CFP with negCriterion pointing to
    # Skill_NegAvailability, SMIA's HandleNegotiationBehaviour:
    #   1. Resolves Skill_NegAvailability → SkillInterface machineAvailValue (via ontology)
    #   2. Finds that the parent submodel is NOT the AID (AssetInterfacesDescription)
    #   3. Calls: agent_services.execute_agent_service_by_id('machineAvailValue')
    #   4. The registered function get_machine_availability() runs and returns 1.0 or 0.0
    #   5. This becomes the machine's negValue for the FIPA-CNP negotiation round
    smia_agent.add_new_agent_service('machineAvailValue', machine_svc.get_machine_availability)
    _logger.info("Machine SMIA: registered 'machineAvailValue' agent service.")

    # ----------------------------------------------------------------
    # Step 6: Start the agent
    # ----------------------------------------------------------------
    # smia.run() starts the SPADE agent, which triggers the SMIA lifecycle:
    #   Booting:  InitAASModelBehaviour runs 3 tracks of CSS self-configuration:
    #             Track 1 — AID: reads AssetInterfacesDescription, creates HTTP asset connection
    #             Track 2 — CSS: reads CapabilitiesAndSkills, builds OWL instances in css_ontology
    #             Track 3 — Rel: reads SemanticRelationships, wires isRealizedBy and accessibleThrough*
    #   Running:  ACLHandlingBehaviour listens for incoming FIPA-ACL messages on XMPP
    #             NegotiatingBehaviour dispatches FIPA-CNP messages to HandleNegotiationBehaviour
    #             HandleCapabilityBehaviour handles direct CSSRequest from operator/orchestrator
    smia.run(smia_agent)


if __name__ == '__main__':
    main()
