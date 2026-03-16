"""
orchestrator_dispatch_behaviour.py
====================================
FIPA-CNP Initiator + Result Forwarding for the SMIA Orchestrator.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH CONTRIBUTION — WHY THIS FILE EXISTS
═══════════════════════════════════════════════════════════════════════════════
The SMIA framework (Hurtado et al., 2025) implements the FIPA-CNP (Contract Net Protocol)
RESPONDER/PROPOSER side: when a machine SMIA receives a CFP (Call For Proposals), it
computes its negValue (availability score) and sends a PROPOSE to all other participants.
The machine with the highest negValue determines itself the winner and sends INFORM(winner=True)
to the `negRequester`.

What is NOT implemented in the base SMIA is the INITIATOR side:
  - Who sends the initial CFP?
  - Who discovers which agents can handle the request?
  - Who routes by color constraint?
  - Who sends the actual capability execution request to the winner?
  - Who forwards the result back to the operator?

THIS CLASS implements all of that. It is the orchestration layer that turns the SMIA
multi-agent system into a truly flexible, autonomous manufacturing pipeline.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE — MESSAGE FLOW
═══════════════════════════════════════════════════════════════════════════════

PHASE 1 — Routing by color constraint:
    Operator → Orchestrator: REQUEST (ontology=css-service)
                             body: {capabilityIRI, skillParams: {color: "red"}}

    OrchestratorDispatchBehaviour:
      1. Scans AAS folder → reads each .aasx → finds SMIA JID + capability color
      2. Filters: only machines whose Capability/color == "red"
      3. Maps color → position: "red" → "0" (hardcoded warehouse slot)
      4. Sends CFP to matching machines

PHASE 2 — FIPA-CNP negotiation (handled entirely by machine SMIAs):
    Orchestrator → Machines: CFP (protocol=fipa-contract-net)
                             body: {capabilityIRI, negCriterion=Skill_NegAvailability,
                                    negTargets=[m0_jid], negRequester=orch_jid, skillParams}

    Machine(s) HandleNegotiationBehaviour (built-in SMIA):
      1. Checks capability exists (capability checking)
      2. Calls agent service 'machineAvailValue' → GET Node-RED /availability → 1.0 or 0.0
      3. If only 1 machine in negTargets: wins immediately (line 108 handle_negotiation_behaviour.py)
         If multiple: sends PROPOSE to peers, compares values, highest wins
      4. Winner sends: INFORM({winner: True}) to negRequester=orchestrator

PHASE 3 — Capability execution:
    Orchestrator → Winner: REQUEST (ontology=css-service)
                           body: {capabilityIRI, skillParams: {position: "0"}}

    Winner HandleCapabilityBehaviour (built-in SMIA):
      1. Resolves skill via AID → HTTP POST to Node-RED /smia/lego/pick
      2. Node-RED publishes MQTT command to crane
      3. Sends: INFORM(result) to orchestrator

PHASE 4 — Result forwarding:
    Orchestrator → Operator: INFORM(result)

═══════════════════════════════════════════════════════════════════════════════
SPADE MESSAGE ROUTING — HOW WE AVOID CONFLICTS WITH BASE SMIA
═══════════════════════════════════════════════════════════════════════════════
SPADE uses a broadcast delivery model: when a message arrives, it is copied to the
mailboxes of ALL active behaviours whose templates match.

The base SMIA's ACLHandlingBehaviour (acl_handling_behaviour.py) is a CyclicBehaviour
that receives ALL messages. When it receives a CSSRequest, it spawns a HandleCapabilityBehaviour
to handle it — but ONLY if the message thread is NOT in `self.myagent.reserved_threads`:
    if msg.thread not in self.myagent.reserved_threads:     # line 67
        specific_handling_behaviour = HandleCapabilityBehaviour(...)

This class calls `await self.myagent.add_reserved_thread(thread)` immediately upon receiving
a CSSRequest from the operator. This prevents ACLHandlingBehaviour from double-handling it.
For INFORM messages from machines: these belong to threads we reserved, so ACLHandlingBehaviour
also skips them.

═══════════════════════════════════════════════════════════════════════════════
STATE TRACKING — TWO THREADS PER ORCHESTRATION
═══════════════════════════════════════════════════════════════════════════════
Each orchestration involves two distinct conversation threads:

    neg_thread  — CFP/PROPOSE/winner-INFORM between orchestrator ↔ machines
    exec_thread — CSSRequest/execution-INFORM between orchestrator ↔ winner

self.myagent.pending_orchestrations dict maps both threads to orchestration state:
    neg_thread  → {'phase': 'negotiation', 'op_thread', 'op_sender', 'capability_iri',
                   'resolved_position', 'skill_params'}
    exec_thread → {'phase': 'awaiting_result', 'neg_thread', 'op_thread', 'op_sender'}
"""

import json
import logging
import os
import uuid

import basyx.aas.adapter.aasx
import basyx.aas.model
from spade.behaviour import CyclicBehaviour
from spade.message import Message

from smia.utilities.fipa_acl_info import FIPAACLInfo, ACLSMIAOntologyInfo

_logger = logging.getLogger(__name__)

# Folder where all AASX files are mounted inside every SMIA container.
# The orchestrator scans this folder to discover machine agents.
AAS_FOLDER = "/smia_archive/config/aas"

# IDTA standard IRI for the SoftwareNameplate submodel.
# Used to identify the submodel that contains the agent's XMPP JID.
SEMANTICID_SOFTWARE_NAMEPLATE = "https://admin-shell.io/idta/SoftwareNameplate/1/0"

# IRI for the InstanceName property inside SoftwareNameplate/SoftwareNameplateInstance.
# Its value is the SMIA's XMPP JID (e.g. "SMIA_agent@ejabberd").
SEMANTICID_INSTANCE_NAME = (
    "https://admin-shell.io/idta/SoftwareNameplate/1/0/"
    "SoftwareNameplate/SoftwareNameplateInstance/InstanceName"
)

# IRI of the Skill_NegAvailability OWL individual that machines use to compute negValue.
# Format: css-smia ontology base IRI + idShort of the Skill element in the AASX.
# Must match exactly: get_ontology_instance_by_iri() does a string equality check.
NEG_CRITERION_IRI = "http://www.w3id.org/upv-ehu/gcis/css-smia#Skill_NegAvailability"

# Hardcoded mapping from piece color to physical warehouse slot number.
# The LEGO crane picks by position (slot index), not by color — it has no color sensor.
# The orchestrator translates the operator's color request into a position before
# forwarding the execution CSSRequest to the winning machine.
#
# Mapping:
#   red   → slot 0 (leftmost column in the warehouse matrix)
#   blue  → slot 1
#   white → slot 2
COLOR_POSITION_MAP = {
    "red":   "0",
    "blue":  "1",
    "white": "2",
}


class OrchestratorDispatchBehaviour(CyclicBehaviour):
    """
    Custom SPADE CyclicBehaviour implementing the FIPA-CNP initiator role.

    Added to the orchestrator SMIA via:
        smia_agent.add_new_agent_capability(OrchestratorDispatchBehaviour())

    This behaviour runs alongside the base SMIA's ACLHandlingBehaviour and
    NegotiatingBehaviour. Message conflicts are prevented via thread reservation
    (self.myagent.add_reserved_thread).
    """

    async def on_start(self):
        """
        Called once when the behaviour is first started by SPADE.
        Initializes the orchestration state dictionary on the agent object
        so it can be accessed by all methods in this class.
        """
        # pending_orchestrations maps thread IDs to orchestration state dicts.
        # Two entries exist per active orchestration (neg_thread + exec_thread).
        self.myagent.pending_orchestrations = {}
        _logger.info("OrchestratorDispatchBehaviour started and ready.")

    async def run(self):
        """
        Main loop: called repeatedly by SPADE. Receives one message per iteration
        (with 5-second timeout) and routes it to the appropriate handler.

        Routing logic (checked in order):
          1. REQUEST + css-service + new thread → new CSSRequest from operator
          2. INFORM + known neg_thread + phase=negotiation → winner notification from machine
          3. INFORM + known exec_thread + phase=awaiting_result → execution result from machine
          4. FAILURE + known thread → negotiation or execution failed
        """
        msg = await self.receive(timeout=5)
        if msg is None:
            return  # No message in this iteration — loop back

        ontology = msg.get_metadata(FIPAACLInfo.FIPA_ACL_ONTOLOGY_ATTRIB)
        performative = msg.get_metadata(FIPAACLInfo.FIPA_ACL_PERFORMATIVE_ATTRIB)
        thread = msg.thread

        _logger.debug(f"Orchestrator received: performative={performative}, ontology={ontology}, thread={thread}")

        # ── Route 1: New CSSRequest from operator ────────────────────────────
        # The operator sends REQUEST with ontology 'css-service' to ask the orchestrator
        # to execute a capability (e.g. PickPiece with color=red).
        # We check that this thread is not already being handled (not in reserved_threads
        # and not in pending_orchestrations) before taking it over.
        if (performative == FIPAACLInfo.FIPA_ACL_PERFORMATIVE_REQUEST
                and ontology == ACLSMIAOntologyInfo.ACL_ONTOLOGY_CSS_SERVICE
                and thread not in self.myagent.reserved_threads
                and thread not in self.myagent.pending_orchestrations):

            # Reserve the thread IMMEDIATELY before any await, so ACLHandlingBehaviour
            # skips this message when it also receives it from SPADE's broadcast delivery.
            await self.myagent.add_reserved_thread(thread)
            _logger.info(f"Orchestrator: new CSSRequest from operator (thread={thread})")
            await self._start_negotiation(msg)

        # ── Route 2: Winner INFORM from negotiation ──────────────────────────
        # The winning machine sends INFORM({winner: True}) to negRequester (us)
        # after winning the decentralized FIPA-CNP among machines.
        # We now know which machine won and send it the actual execution request.
        elif (performative == FIPAACLInfo.FIPA_ACL_PERFORMATIVE_INFORM
              and thread in self.myagent.pending_orchestrations
              and self.myagent.pending_orchestrations[thread].get('phase') == 'negotiation'):

            _logger.info(f"Orchestrator: winner INFORM from {msg.sender} (neg_thread={thread})")
            body = {}
            try:
                body = json.loads(msg.body) if msg.body else {}
            except json.JSONDecodeError:
                pass

            if body.get('winner'):
                await self._send_execution_request(thread, str(msg.sender))
            else:
                # Machine reports it is NOT the winner (shouldn't reach here normally,
                # since only the winner sends INFORM — losers stay silent).
                _logger.warning(f"Orchestrator: received non-winner INFORM (thread={thread}) — ignoring")

        # ── Route 3: Execution INFORM from winner machine ────────────────────
        # The winning machine executed the capability (POST to Node-RED → MQTT) and sends
        # the result back to us. We forward it unchanged to the original operator.
        elif (performative == FIPAACLInfo.FIPA_ACL_PERFORMATIVE_INFORM
              and thread in self.myagent.pending_orchestrations
              and self.myagent.pending_orchestrations[thread].get('phase') == 'awaiting_result'):

            _logger.info(f"Orchestrator: execution INFORM received (exec_thread={thread})")
            await self._forward_result_to_operator(thread, msg.body)

        # ── Route 4: FAILURE from machines ───────────────────────────────────
        # Sent by machines when the negotiation times out or fails (e.g. all machines busy).
        elif (performative == FIPAACLInfo.FIPA_ACL_PERFORMATIVE_FAILURE
              and thread in self.myagent.pending_orchestrations):

            state = self.myagent.pending_orchestrations[thread]
            body = {}
            try:
                body = json.loads(msg.body) if msg.body else {}
            except json.JSONDecodeError:
                pass
            reason = body.get('reason', 'Unknown negotiation failure')
            _logger.warning(f"Orchestrator: FAILURE received (thread={thread}): {reason}")
            await self._send_failure_to_operator(thread, reason)

    # =========================================================================
    # PHASE 1: AAS discovery + color filtering + CFP broadcast
    # =========================================================================

    async def _start_negotiation(self, operator_msg):
        """
        Discover eligible machine SMIAs, resolve color to position, send FIPA-CNP CFP.

        Step-by-step:
          1. Parse the operator's request body to extract capabilityIRI, skillParams, color.
          2. Map color string to physical warehouse slot position (COLOR_POSITION_MAP).
          3. Scan the AAS folder with _discover_machines_for_request() to find machines
             whose Capability_PickPiece/color property matches the requested color.
          4. Generate a new UUID as the negotiation thread (neg_thread).
          5. Reserve neg_thread and store orchestration state.
          6. Send a CFP to every discovered machine JID.

        The CFP body follows the SMIA FIPA-CNP schema (fipa_acl_info.py JSON_SCHEMA_CSS_SERVICE):
          capabilityIRI — which capability machines must have (filters by SMIA's capability checking)
          negCriterion  — IRI of the Skill that machines will use to compute their negValue
          negTargets    — list of all participating machine JIDs (used by machines for PROPOSE routing)
          negRequester  — our JID (winner sends INFORM here after winning the negotiation)
          skillParams   — forwarded context (used during capability checking on machine side)
        """
        op_body = {}
        try:
            op_body = json.loads(operator_msg.body)
        except json.JSONDecodeError:
            _logger.error("Orchestrator: could not parse operator request body")

        capability_iri = op_body.get('capabilityIRI', '')
        skill_params = op_body.get('skillParams', {})
        op_thread = operator_msg.thread
        op_sender = str(operator_msg.sender)

        # ── Color → Position mapping ─────────────────────────────────────────
        # Extract color from the operator's skillParams. This is the piece color
        # requested in the manufacturing order. The physical crane operates by
        # slot position, so we translate here before dispatching to the winner.
        color = skill_params.get('color', '').lower() if isinstance(skill_params, dict) else ''

        resolved_position = None
        if color:
            resolved_position = COLOR_POSITION_MAP.get(color)
            if resolved_position is None:
                valid = ', '.join(COLOR_POSITION_MAP.keys())
                await self._send_failure_direct(
                    op_sender, op_thread,
                    f"Unknown color '{color}'. Valid values: {valid}")
                return
            _logger.info(f"Orchestrator: color='{color}' → position={resolved_position}")

        # ── AAS-based discovery with color filtering ─────────────────────────
        # Extract idShort from the capability IRI (e.g. "Capability_PickPiece" from the full IRI).
        # We use idShort to locate the capability SMC inside each AASX's CapabilitiesAndSkills submodel.
        cap_id_short = capability_iri.split('#')[-1] if '#' in capability_iri else capability_iri

        machines = self._discover_machines_for_request(
            cap_id_short=cap_id_short,
            exclude_jid=str(self.agent.jid),
            color_filter=color if color else None
        )
        machine_jids = [m['jid'] for m in machines]

        if not machine_jids:
            msg = f"No machine available for color='{color}'" if color else "No machines discovered"
            _logger.error(f"Orchestrator: {msg}")
            await self._send_failure_direct(op_sender, op_thread, msg)
            return

        _logger.info(f"Orchestrator: eligible machines for color='{color}': {machine_jids}")

        # ── Build and send CFP ────────────────────────────────────────────────
        neg_thread = str(uuid.uuid4())
        await self.myagent.add_reserved_thread(neg_thread)

        # Store full orchestration state keyed by neg_thread.
        # resolved_position is stored separately — the winner receives {position: N},
        # not the original {color: X}, since the machine's AID/Node-RED uses position.
        self.myagent.pending_orchestrations[neg_thread] = {
            'phase': 'negotiation',
            'op_thread': op_thread,
            'op_sender': op_sender,
            'skill_params': skill_params,
            'capability_iri': capability_iri,
            'resolved_position': resolved_position,
        }

        cfp_body = {
            'capabilityIRI': capability_iri,
            'negCriterion': NEG_CRITERION_IRI,
            'negTargets': machine_jids,      # machines route PROPOSE to each other via this list
            'negRequester': str(self.agent.jid),  # winner sends INFORM to us
            'skillParams': skill_params,
        }

        for jid in machine_jids:
            cfp = Message(to=jid)
            cfp.thread = neg_thread
            cfp.set_metadata(FIPAACLInfo.FIPA_ACL_PERFORMATIVE_ATTRIB, FIPAACLInfo.FIPA_ACL_PERFORMATIVE_CFP)
            cfp.set_metadata(FIPAACLInfo.FIPA_ACL_ONTOLOGY_ATTRIB, ACLSMIAOntologyInfo.ACL_ONTOLOGY_CSS_SERVICE)
            cfp.set_metadata(FIPAACLInfo.FIPA_ACL_PROTOCOL_ATTRIB, FIPAACLInfo.FIPA_ACL_CONTRACT_NET_PROTOCOL)
            cfp.set_metadata(FIPAACLInfo.FIPA_ACL_ENCODING_ATTRIB, FIPAACLInfo.FIPA_ACL_DEFAULT_ENCODING)
            cfp.set_metadata(FIPAACLInfo.FIPA_ACL_LANGUAGE_ATTRIB, FIPAACLInfo.FIPA_ACL_DEFAULT_LANGUAGE)
            cfp.body = json.dumps(cfp_body)
            await self.send(cfp)
            _logger.info(f"Orchestrator: CFP sent to {jid} (neg_thread={neg_thread})")

    # =========================================================================
    # PHASE 3: Send capability execution request to winner
    # =========================================================================

    async def _send_execution_request(self, neg_thread, winner_jid):
        """
        Send a direct CSSRequest to the winning machine to execute the capability.

        This is a plain REQUEST message with ontology 'css-service' — the same type
        of message the operator would send directly to a machine in Case 0.
        The winner machine's ACLHandlingBehaviour receives it, spawns a
        HandleCapabilityBehaviour, which:
          1. Finds the capability in the AAS CSS model
          2. Resolves the skill → accessibleThroughAssetService → AID endpoint
          3. Executes HTTP POST to Node-RED /smia/lego/pick with {position: N}
          4. Node-RED publishes MQTT command to the crane
          5. Returns INFORM(result) to us

        Note on skillParams: we replace {color: X} with {position: N} here.
        The machine's AID endpoint and Node-RED flow expect a numeric position,
        not a color string.
        """
        state = self.myagent.pending_orchestrations[neg_thread]

        # Generate a new unique thread for the execution phase.
        # This is separate from neg_thread to avoid routing conflicts.
        exec_thread = str(uuid.uuid4())
        await self.myagent.add_reserved_thread(exec_thread)

        # Store execution phase state under exec_thread.
        # We keep a reference back to neg_thread for cleanup.
        self.myagent.pending_orchestrations[exec_thread] = {
            'phase': 'awaiting_result',
            'neg_thread': neg_thread,
            'op_thread': state['op_thread'],
            'op_sender': state['op_sender'],
        }
        # Mark negotiation phase as done to prevent re-entry.
        state['phase'] = 'done'

        # Build the execution skillParams: use resolved position if color was given,
        # otherwise forward the original skillParams unchanged.
        resolved_position = state.get('resolved_position')
        if resolved_position is not None:
            exec_skill_params = {'position': resolved_position}
        else:
            exec_skill_params = state['skill_params']

        exec_body = {
            'capabilityIRI': state['capability_iri'],
            'skillParams': exec_skill_params,
        }

        req = Message(to=winner_jid)
        req.thread = exec_thread
        req.set_metadata(FIPAACLInfo.FIPA_ACL_PERFORMATIVE_ATTRIB, FIPAACLInfo.FIPA_ACL_PERFORMATIVE_REQUEST)
        req.set_metadata(FIPAACLInfo.FIPA_ACL_ONTOLOGY_ATTRIB, ACLSMIAOntologyInfo.ACL_ONTOLOGY_CSS_SERVICE)
        req.set_metadata(FIPAACLInfo.FIPA_ACL_PROTOCOL_ATTRIB, FIPAACLInfo.FIPA_ACL_REQUEST_PROTOCOL)
        req.set_metadata(FIPAACLInfo.FIPA_ACL_ENCODING_ATTRIB, FIPAACLInfo.FIPA_ACL_DEFAULT_ENCODING)
        req.set_metadata(FIPAACLInfo.FIPA_ACL_LANGUAGE_ATTRIB, FIPAACLInfo.FIPA_ACL_DEFAULT_LANGUAGE)
        req.body = json.dumps(exec_body)
        await self.send(req)
        _logger.info(
            f"Orchestrator: execution REQUEST sent to {winner_jid} "
            f"(exec_thread={exec_thread}, skillParams={exec_skill_params})"
        )

    # =========================================================================
    # PHASE 4: Forward result to operator
    # =========================================================================

    async def _forward_result_to_operator(self, exec_thread, result_body):
        """
        Forward the execution INFORM from the winner machine back to the operator.

        The result_body is passed unchanged — whatever the machine's HandleCapabilityBehaviour
        produced (typically the HTTP response from Node-RED) is what the operator sees.
        Cleanup removes both exec_thread and neg_thread entries from pending_orchestrations.
        """
        state = self.myagent.pending_orchestrations[exec_thread]

        inform = Message(to=state['op_sender'])
        inform.thread = state['op_thread']
        inform.set_metadata(FIPAACLInfo.FIPA_ACL_PERFORMATIVE_ATTRIB, FIPAACLInfo.FIPA_ACL_PERFORMATIVE_INFORM)
        inform.set_metadata(FIPAACLInfo.FIPA_ACL_ONTOLOGY_ATTRIB, ACLSMIAOntologyInfo.ACL_ONTOLOGY_CSS_SERVICE)
        inform.set_metadata(FIPAACLInfo.FIPA_ACL_ENCODING_ATTRIB, FIPAACLInfo.FIPA_ACL_DEFAULT_ENCODING)
        inform.set_metadata(FIPAACLInfo.FIPA_ACL_LANGUAGE_ATTRIB, FIPAACLInfo.FIPA_ACL_DEFAULT_LANGUAGE)
        inform.body = result_body
        await self.send(inform)
        _logger.info(f"Orchestrator: result forwarded to operator (op_thread={state['op_thread']})")

        # Cleanup both thread entries
        neg_thread = state.get('neg_thread')
        self.myagent.pending_orchestrations.pop(exec_thread, None)
        self.myagent.pending_orchestrations.pop(neg_thread, None)

    async def _send_failure_to_operator(self, thread, reason):
        """Send FAILURE to operator when orchestration fails after state was stored."""
        state = self.myagent.pending_orchestrations.get(thread, {})
        op_sender = state.get('op_sender')
        op_thread = state.get('op_thread')
        if op_sender and op_thread:
            await self._send_failure_direct(op_sender, op_thread, reason)
        self.myagent.pending_orchestrations.pop(thread, None)

    async def _send_failure_direct(self, op_sender, op_thread, reason):
        """Send FAILURE to operator with explicit sender/thread (before state is stored)."""
        fail = Message(to=op_sender)
        fail.thread = op_thread
        fail.set_metadata(FIPAACLInfo.FIPA_ACL_PERFORMATIVE_ATTRIB, FIPAACLInfo.FIPA_ACL_PERFORMATIVE_FAILURE)
        fail.set_metadata(FIPAACLInfo.FIPA_ACL_ONTOLOGY_ATTRIB, ACLSMIAOntologyInfo.ACL_ONTOLOGY_CSS_SERVICE)
        fail.set_metadata(FIPAACLInfo.FIPA_ACL_ENCODING_ATTRIB, FIPAACLInfo.FIPA_ACL_DEFAULT_ENCODING)
        fail.body = json.dumps({'reason': reason})
        await self.send(fail)
        _logger.warning(f"Orchestrator: FAILURE sent to operator — {reason}")

    # =========================================================================
    # AAS folder scanning — dynamic machine discovery with color filtering
    # =========================================================================

    def _discover_machines_for_request(self, cap_id_short, exclude_jid, color_filter=None):
        """
        Scan the AAS folder and return machines eligible to handle this request.

        Replicates the operator GUI's AAS scanning mechanism (operator_gui_logic.py:44-56)
        to discover available SMIAs. Extends it with capability color filtering.

        For each .aasx file in AAS_FOLDER:
          1. Parse the AASX with basyx.aas.adapter.aasx.AASXReader
          2. Extract SMIA JID from SoftwareNameplate/SoftwareNameplateInstance/InstanceName
          3. Find the capability SMC by idShort and read its 'color' child property
          4. If color_filter is set, only include machines whose color matches

        This is AAS-based dynamic discovery: to add a new machine to the system,
        simply drop its AASX into the aas/ folder. No code changes needed.

        Args:
            cap_id_short:  idShort of the capability SMC (e.g. 'Capability_PickPiece')
            exclude_jid:   the orchestrator's own JID — never included in results
            color_filter:  if set, only include machines with matching color property

        Returns:
            list[dict]: [{'jid': 'SMIA_agent@ejabberd', 'color': 'red'}, ...]
        """
        machines = []
        if not os.path.isdir(AAS_FOLDER):
            _logger.warning(f"AAS folder not found: {AAS_FOLDER}")
            return machines

        for filename in os.listdir(AAS_FOLDER):
            if not filename.endswith('.aasx'):
                continue
            filepath = os.path.join(AAS_FOLDER, filename)
            try:
                object_store = basyx.aas.model.DictObjectStore()
                with basyx.aas.adapter.aasx.AASXReader(filepath) as reader:
                    reader.read_into(object_store=object_store)

                jid = self._extract_jid_from_store(object_store)
                if not jid:
                    continue  # No SoftwareNameplate → not a machine AASX (e.g. operator)
                if jid == exclude_jid:
                    continue  # Skip our own AASX

                color = self._find_capability_color(object_store, cap_id_short)
                if color is None:
                    continue  # This AASX has no matching capability (e.g. operator AASX)

                if color_filter and color.lower() != color_filter.lower():
                    _logger.debug(f"Skipping {jid}: color={color} ≠ filter={color_filter}")
                    continue

                machines.append({'jid': jid, 'color': color})
                _logger.info(f"Eligible machine: {jid} (color={color}) from {filename}")

            except Exception as e:
                _logger.warning(f"Could not read AASX {filename}: {e}")

        return machines

    def _extract_jid_from_store(self, object_store):
        """
        Extract the SMIA JID from an AAS object store.

        Searches all Submodel objects for one with semantic ID matching
        SEMANTICID_SOFTWARE_NAMEPLATE. Within that submodel, searches recursively
        for a Property with semantic ID SEMANTICID_INSTANCE_NAME.

        The InstanceName property value is the SMIA's full XMPP JID
        (e.g. "SMIA_agent@ejabberd").

        Returns:
            str | None: the JID string, or None if not found
        """
        for item in object_store:
            if not isinstance(item, basyx.aas.model.Submodel):
                continue
            if not self._has_semantic_id(item, SEMANTICID_SOFTWARE_NAMEPLATE):
                continue
            for sme in item.submodel_element:
                result = self._find_property_by_semantic_id(sme, SEMANTICID_INSTANCE_NAME)
                if result is not None:
                    return result
        return None

    def _find_capability_color(self, object_store, cap_id_short):
        """
        Find the 'color' property inside a Capability SMC identified by cap_id_short.

        The Capability SMC in machine AASXs has this structure:
            Capability_PickPiece [SubmodelElementCollection]
                position         [Property xs:int]
                color            [Property xs:string]  ← constraint

        Searches all submodels for a SubmodelElementCollection with matching idShort,
        then looks for a child Property named 'color'.

        Returns:
            str | None: the color value (e.g. 'red'), or None if not found
        """
        for item in object_store:
            if not isinstance(item, basyx.aas.model.Submodel):
                continue
            for sme in item.submodel_element:
                if (isinstance(sme, basyx.aas.model.SubmodelElementCollection)
                        and sme.id_short == cap_id_short):
                    for child in sme.value:
                        if (isinstance(child, basyx.aas.model.Property)
                                and child.id_short == 'color'):
                            return child.value
        return None

    def _has_semantic_id(self, element, expected_iri):
        """Return True if the AAS element has a semantic ID key matching expected_iri."""
        try:
            for key in element.semantic_id.key:
                if key.value == expected_iri:
                    return True
        except (AttributeError, TypeError):
            pass
        return False

    def _find_property_by_semantic_id(self, element, semantic_id_iri):
        """
        Recursively search for a Property whose semantic ID matches semantic_id_iri.

        Handles both flat Properties and Properties nested inside
        SubmodelElementCollections (the SoftwareNameplate structure uses SMCs
        like SoftwareNameplateInstance that contain the InstanceName property).

        Returns:
            str | None: the property value if found, else None
        """
        if isinstance(element, basyx.aas.model.Property):
            if self._has_semantic_id(element, semantic_id_iri):
                return element.value
        if isinstance(element, basyx.aas.model.SubmodelElementCollection):
            for child in element.value:
                result = self._find_property_by_semantic_id(child, semantic_id_iri)
                if result is not None:
                    return result
        return None
