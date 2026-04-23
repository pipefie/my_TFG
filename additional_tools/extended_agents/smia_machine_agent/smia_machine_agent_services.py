"""
smia_machine_agent_services.py
================================
Agent service functions for the machine SMIA instances (machine0, machine1, machine2).

WHAT IS AN AGENT SERVICE IN SMIA?
-----------------------------------
In the SMIA framework, an "agent service" is a Python function registered under a specific
identifier (matching an AAS element idShort) that SMIA calls automatically when that element
is referenced via `accessibleThroughAgentService` in the CSS SemanticRelationships submodel.

Agent services allow the SMIA to compute dynamic values from Python logic, as opposed to
"asset services" which make HTTP calls to an external asset (Node-RED, OPC-UA, etc.).

HOW THIS FILE IS USED:
-----------------------
1. `smia_machine_starter.py` imports this module and registers `get_machine_availability`
   as the agent service with id 'machineAvailValue' via:
       smia_agent.add_new_agent_service('machineAvailValue', get_machine_availability)

2. When the orchestrator sends a FIPA-CNP CFP with:
       negCriterion = "http://www.w3id.org/upv-ehu/gcis/css-smia#Skill_NegAvailability"
   SMIA's HandleNegotiationBehaviour resolves this IRI to the OWL instance Skill_NegAvailability,
   finds its associated SkillInterface (machineAvailValue via accessibleThroughAgentService),
   checks that the parent submodel is NOT the AssetInterfacesDescription (AID), and therefore
   calls: agent_services.execute_agent_service_by_id('machineAvailValue')
   which ultimately calls: await get_machine_availability()

3. The returned float is used as the machine's negotiation score (negValue):
       1.0 = machine is free and ready
       0.0 = machine is currently executing a task (busy)
   SMIA normalizes values: if value > 1.0 it is divided by 100.0 (see services_utils.py).

WHY THIS APPROACH (AGENT SERVICE vs ASSET SERVICE)?
----------------------------------------------------
We could put an HTTP GET endpoint in the AID submodel and use `accessibleThroughAssetService`.
We chose agent service instead because:
  - The availability state is tracked by Node-RED (the same process that executes tasks)
  - Python's aiohttp can make the GET call asynchronously within SMIA's asyncio event loop
  - No new AID elements needed — the AID stays clean (only POST actions for pick/place)
  - The agent service function is simpler to test and modify

IMPORTANT — HOW EXTERNAL FUNCTIONS ARE REGISTERED:
----------------------------------------------------
SMIA's save_agent_service() (agent_services.py:66) uses types.MethodType to bind the function
to the AgentServices class instance. For plain functions (no class, no self), the binding
results in the original function being stored. When called, it is invoked as:
    await get_machine_availability(**adapted_params)
with NO implicit 'self'. Therefore this function is written WITHOUT a self parameter.
"""

import logging
import os

import aiohttp  # available in the SMIA alpine image (installed as a smia dependency)

_logger = logging.getLogger(__name__)

# Base URL of the Node-RED instance.
# Read from the NODERED_URL environment variable so the deployment target
# (containerized Node-RED vs. external DIDA-Central host) can be changed
# without rebuilding the image. Default falls back to the Docker service name.
NODE_RED_BASE = os.environ.get('NODERED_URL', 'http://nodered:1880')
# Local part of the XMPP JID (e.g. "smia_machine1" from "smia_machine1@ejabberd").
# Used as the per-machine key in Node-RED's machine_busy_<machineId> flags so that
# multiple machines sharing the same Node-RED instance track availability independently.
MACHINE_ID = os.environ.get('AGENT_ID', 'machine').split('@')[0]


async def get_machine_availability():
    """
    Agent service registered under id 'machineAvailValue'.

    Queries the Node-RED availability endpoint to determine whether the physical machine
    is currently free to accept a new task.

    The endpoint GET /smia/lego/availability is implemented in Node-RED as follows:
      - A global variable 'machine_busy' is set to true when a pick/place POST request
        arrives and cleared to false after the MQTT command is published.
      - This endpoint reads that variable and returns '1.0' (free) or '0.0' (busy)
        as plain text (not JSON) so that SMIA can directly parse it as float.

    The value is used by HandleNegotiationBehaviour as the machine's negotiation score
    (negValue). When multiple machines of the same color exist, the one with the higher
    score wins the FIPA-CNP and executes the task.

    Returns:
        float: 1.0 if the machine is available, 0.0 if currently busy.
               Returns 0.0 on connection error (treats unreachable Node-RED as unavailable).
    """
    url = f"{NODE_RED_BASE}/smia/lego/availability?machine={MACHINE_ID}"
    try:
        # aiohttp is used instead of requests because SMIA runs in an asyncio event loop.
        # Using synchronous requests.get() here would block the entire event loop,
        # preventing other SMIA behaviours (like ACLHandlingBehaviour) from running.
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                text = await resp.text()
                value = float(text.strip())
                _logger.info(f"[machineAvailValue] Node-RED availability for {MACHINE_ID}: {value}")
                return value
    except aiohttp.ClientConnectorError:
        _logger.warning(f"[machineAvailValue] Cannot connect to Node-RED at {url} ({MACHINE_ID}) — returning 0.0 (busy)")
        return 0.0
    except ValueError:
        _logger.warning(f"[machineAvailValue] Node-RED returned non-float response ({MACHINE_ID}) — returning 0.0")
        return 0.0
    except Exception as e:
        _logger.error(f"[machineAvailValue] Unexpected error ({MACHINE_ID}): {e} — returning 0.0")
        return 0.0
