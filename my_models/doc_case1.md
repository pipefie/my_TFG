# Case 1 — Full Technical Documentation

**Date:** 2026-04-15
**Status:** Implemented — end-to-end testing in progress
**Physical asset:** fischertechnik Training Factory Industry 4.0 24V (ref. 554868) — warehouse crane (Hochregallager)
**Scope:** Multi-agent FIPA-CNP negotiation across three machine SMIAs coordinated by an orchestrator, all deployed via a single Docker Compose command.

> **Builds on Case 0.** This document assumes familiarity with `doc_case0.md`. Only differences and additions are described from scratch; concepts already documented in Case 0 are referenced, not repeated.

> **Naming note:** File names (`LEGO_factory_case0.aasx`, `LEGO_machine1_case0.aasx`, etc.) and AAS identifiers are historical artifacts. They refer to the fischertechnik Training Factory warehouse crane. Do not rename them — they appear in running configs and logs.

---

## 0. Terminology Reference

This section establishes precise definitions for terms that have specific technical meanings in this implementation. Readers who completed Case 0 already know AAS, CSS, SMIA self-configuration, and the AID submodel. The following covers what is new or more deeply used in Case 1.

### 0.1 FIPA-ACL Message Fields

All inter-agent messages in this system are FIPA-ACL messages. Four fields appear repeatedly in logs and code. Their meaning in this system:

| Field | Values used | Routing significance |
|---|---|---|
| `performative` | `request`, `cfp`, `propose`, `inform`, `failure` | Determines what action the receiver should take |
| `ontology` | `css-service` | Used by `ACLHandlingBehaviour` and `NegotiatingBehaviour` to decide which behaviour processes the message |
| `protocol` | `fipa-contract-net`, `fipa-request` | Used to distinguish CFP/PROPOSE exchanges from direct execution requests |
| `thread` | UUID string | Identifies a conversation; all messages in one negotiation share a thread; used to correlate request↔response and to implement thread reservation |

### 0.2 SPADE Behaviour Model and Asyncio

SMIA runs entirely inside a single Python thread using Python's `asyncio` event loop. All concurrency is cooperative: a coroutine runs until it hits an `await`, at which point the event loop schedules another. There is no OS-level thread parallelism.

**Behaviour types:**
- `CyclicBehaviour` — `run()` is called in a tight loop by SPADE; used for permanent message listeners. Examples: `ACLHandlingBehaviour`, `NegotiatingBehaviour`, `OrchestratorDispatchBehaviour`.
- `OneShotBehaviour` — `run()` executes once and the behaviour exits; used to handle one specific conversation. Examples: `HandleCapabilityBehaviour`, `HandleNegotiationBehaviour`.

**Broadcast delivery:** When a message arrives at an XMPP JID, SPADE delivers it to **all** active behaviours whose message template matches — not just the first one. This is the architectural root of the race condition fixed in Patch 2 (§18.2): `ACLHandlingBehaviour` and `OrchestratorDispatchBehaviour` both receive the same operator REQUEST in the same event loop tick.

**Consequence for blocking I/O:** Any synchronous blocking call (e.g., `requests.get()`) inside a behaviour's `run()` would freeze the entire event loop until it returns — no other behaviour can receive or send messages during that time. All I/O in Case 1 uses `aiohttp` (async HTTP client) to avoid this.

### 0.3 Full XMPP JID vs. Bare JID

XMPP addresses have two forms:
- **Bare JID:** `username@domain` — the account identity (e.g., `SMIA_agent@ejabberd`)
- **Full JID:** `username@domain/resource` — the specific active connection (e.g., `SMIA_agent@ejabberd/1718375723884498033169`)

SPADE's `str(msg.sender)` returns the full JID. The orchestrator uses the sender's full JID when addressing the winner's execution REQUEST to ensure the reply reaches the same active connection, not an alternative session if the same account were connected twice.

### 0.4 OWL Instance IRI Resolution

During self-configuration (Track 1), SMIA creates OWLready2 instances for each CSS element found in the AASX. The IRI of each instance is assembled as `css_namespace + id_short` (e.g., `http://www.w3id.org/hsu-aut/css#Skill_NegAvailability`). The `negCriterion` field in a CFP body is one of these IRIs. SMIA resolves it via a linear scan: `if instance.iri == negCriterion_iri`. Consequences:
- The `negCriterion` IRI sent in the CFP must exactly match the IRI produced from the machine's AASX `id_short`.
- Any case difference or namespace mismatch silently returns `None` — no exception is raised; the negotiation value defaults to 0.0 and the machine loses every negotiation.
- The namespace prefix `http://www.w3id.org/hsu-aut/css#` (for CSS standard concepts) vs. `http://www.w3id.org/upv-ehu/gcis/css-smia#` (for SMIA extensions) must be correct in every IRI.

### 0.5 `pending_orchestrations` as an Orchestrator Signal

`OrchestratorDispatchBehaviour.on_start()` sets `self.agent.pending_orchestrations = {}` on the agent object before any messages are processed. This attribute does not exist on plain machine agents (`SMIAAgent` or `ExtensibleSMIAAgent` without the orchestrator behaviour). Patch 2 (`acl_handling_behaviour.py`) uses `hasattr(self.myagent, 'pending_orchestrations')` as the discriminator to determine whether the agent is running in orchestrator mode. This avoids modifying the constructor of any base class.

---

## Table of Contents

0. [Terminology Reference](#0-terminology-reference)
   - [0.1 FIPA-ACL Message Fields](#01-fipa-acl-message-fields)
   - [0.2 SPADE Behaviour Model and Asyncio](#02-spade-behaviour-model-and-asyncio)
   - [0.3 Full XMPP JID vs. Bare JID](#03-full-xmpp-jid-vs-bare-jid)
   - [0.4 OWL Instance IRI Resolution](#04-owl-instance-iri-resolution)
   - [0.5 `pending_orchestrations` as an Orchestrator Signal](#05-pending_orchestrations-as-an-orchestrator-signal)
1. [Introduction and Motivation](#1-introduction-and-motivation)
   - [1.1 What Is Flexible Manufacturing?](#11-what-is-flexible-manufacturing)
   - [1.2 From One Machine to Many](#12-from-one-machine-to-many)
   - [1.3 Research Contribution — What This TFG Implements vs. What Existed](#13-research-contribution--what-this-tfg-implements-vs-what-existed)
   - [1.4 Scope of This Document](#14-scope-of-this-document)
2. [What Case 1 Adds Over Case 0](#2-what-case-1-adds-over-case-0)
3. [Design Requirements Validated](#3-design-requirements-validated)
4. [System Architecture](#4-system-architecture)
5. [Technologies Used](#5-technologies-used)
6. [Repository Layout](#6-repository-layout)
7. [SMIA Framework — Deeper Concepts for Case 1](#7-smia-framework--deeper-concepts-for-case-1)
8. [SMIA Extensibility Mechanism](#8-smia-extensibility-mechanism)
   - [8.1 Machine Launcher — `smia_machine_starter.py`](#81-machine-launcher--smia_machine_starterpy)
   - [8.2 Orchestrator Launcher — `smia_orchestrator_starter.py`](#82-orchestrator-launcher--smia_orchestrator_starterpy)
9. [FIPA-CNP Multi-Agent Negotiation Protocol](#9-fipa-cnp-multi-agent-negotiation-protocol)
10. [AASX Models — Full Structure](#10-aasx-models--full-structure)
11. [Agent Services vs. Agent Capabilities](#11-agent-services-vs-agent-capabilities)
12. [Machine Availability Service](#12-machine-availability-service)
13. [Orchestrator Dispatch Behaviour](#13-orchestrator-dispatch-behaviour)
14. [Custom Docker Images and Patches](#14-custom-docker-images-and-patches)
    - [14.2 Machine Image](#142-machine-image-my_modelsdockersmia-machinedockerfile)
    - [14.3 Orchestrator Image](#143-orchestrator-image-my_modelsdockersmia-orchestratordockerfile)
    - [14.4 Build Lifecycle](#144-build-lifecycle)
15. [Docker Compose Deployment — 8 Services](#15-docker-compose-deployment--8-services)
16. [Configuration Files](#16-configuration-files)
17. [Deployment and Test Procedure](#17-deployment-and-test-procedure)
18. [Known Issues and Patches Applied](#18-known-issues-and-patches-applied)
    - [18.1 Patch 1 — `smia_agent.py`](#181-patch-1--smia_agentpy-asset-connection-object-identity-bug)
    - [18.2 Patch 2 — `acl_handling_behaviour.py`](#182-patch-2--acl_handling_behaviourpy-orchestrator-race-condition)
    - [18.3 Patch 3 — `operator_gui_logic.py`](#183-patch-3--operator_gui_logicpy-skillparameter-processing-bugs)
    - [18.4 Thread Reservation Design Requirement](#184-orchestratordispatchbehaviourrun-thread-reservation-before-await)
19. [Troubleshooting](#19-troubleshooting)
20. [Replication Checklist](#20-replication-checklist)

---

## 1. Introduction and Motivation

### 1.1 What Is Flexible Manufacturing?

One of the core promises of Industry 4.0 is **flexible manufacturing**: production systems that can adapt dynamically to changing requirements — different product types, variable demand, substitution of one machine for another — without manual reconfiguration or re-programming. Achieving this requires that machines be able to:

1. Advertise their capabilities in a machine-readable, standardized way.
2. Discover each other's capabilities at runtime.
3. Negotiate task assignment autonomously, without a central authority having pre-programmed knowledge of each machine.
4. Execute assigned tasks and report results in a standardized way.

This is the problem that Case 1 addresses.

### 1.2 From One Machine to Many

Case 0 demonstrated that a single machine can represent itself as an AAS-compliant Digital Twin and execute physical actions autonomously from a standardized capability request. It validated that the AAS and CSS models can fully describe a physical asset's interface so that no asset-specific code lives inside the agent.

Case 1 scales this to a **multi-machine scenario**: three machines, each modeled as a separate SMIA agent, each offering the same logical capability (`Capability_PickPiece`) but for pieces of a different color stored in different physical slots. An **orchestrator** agent receives the operator's request, discovers which machines can handle it, runs a FIPA-ACL Contract Net Protocol (FIPA-CNP) negotiation to select the best available machine, instructs the winner to execute, and returns the result to the operator.

The key point: **none of this logic is hardcoded**. The orchestrator discovers machines dynamically by reading their AASX files. The machines determine their own availability autonomously. The protocol is standardized (FIPA-CNP). Any new machine can be added to the system by dropping its AASX into a shared folder and registering its XMPP account — no code changes required.

### 1.3 Research Contribution — What This TFG Implements vs. What Existed

The SMIA framework (Hurtado et al., 2025) published the FIPA-CNP **responder side** complete: machines can receive CFPs, compute availability, exchange PROPOSEs, self-declare a winner, and notify the requester. The **initiator side** did not exist in the framework at the time of this work.

| Component | In SMIA upstream | This TFG |
|---|---|---|
| FIPA-CNP responder (machine side) | ✓ `HandleNegotiationBehaviour` | — |
| AAS self-configuration | ✓ `InitAASModelBehaviour` (3 tracks) | — |
| Direct capability execution | ✓ `HandleCapabilityBehaviour` | — |
| FIPA-CNP **initiator** (orchestrator side) | ✗ | ✓ `OrchestratorDispatchBehaviour` |
| AAS-based dynamic machine discovery | ✗ | ✓ `_discover_machines_for_request()` |
| Capability constraint routing (color→position) | ✗ | ✓ `COLOR_POSITION_MAP` + AASX color filter |
| Execution delegation to negotiation winner | ✗ | ✓ `_send_execution_request()` |
| Result forwarding to original requester | ✗ | ✓ `_forward_result_to_operator()` |
| Multi-machine containerized deployment | ✗ | ✓ 8-service Docker Compose stack |
| Framework bug fixes (upstream) | — | ✓ 3 patches documented in §18 |

The primary research artifact is `orchestrator_dispatch_behaviour.py` (~650 lines, fully documented). All other files (`smia_machine_starter.py`, `smia_machine_agent_services.py`, `smia_orchestrator_starter.py`, Dockerfiles, AASX models) are the infrastructure required to deploy, test, and verify it in a physically wired multi-agent system.

### 1.4 Scope of This Document

This document covers the full technical implementation of Case 1:
- The multi-agent architecture and message flow.
- The three machine AASXs and the orchestrator AASX.
- The FIPA-CNP negotiation protocol as implemented in SMIA.
- The custom extension code: `OrchestratorDispatchBehaviour`, `get_machine_availability()`.
- The 8-service Docker Compose deployment with environment-variable-driven configuration.
- All patches applied to the upstream SMIA framework and their justification.

---

## 2. What Case 1 Adds Over Case 0

| Feature | Case 0 | Case 1 |
|---|---|---|
| Number of machine agents | 1 | 3 (machine0, machine1, machine2) |
| Number of Docker services | 3 | 8 |
| Orchestrator agent | None | 1 (`smia-orchestrator`) |
| MQTT broker | External (DIDA central) | Containerized (`mosquitto-central`) |
| Node-RED | External (DIDA central) | Containerized (`nodered`) |
| Machine discovery | Not needed | AAS-based dynamic scan at orchestrator |
| Capability routing | Direct operator → machine | Operator → orchestrator → [negotiation] → winner |
| Negotiation protocol | None | FIPA-CNP (Contract Net Protocol) |
| Availability service | None | `get_machine_availability()` (async HTTP to Node-RED) |
| Config management | Manual env vars | `.env` file + `.env.example` template |
| SMIA extension used | None (base SMIAAgent) | `add_new_agent_service` (machines) + `add_new_agent_capability` (orchestrator) |
| Custom Dockerfiles | None (base image used directly) | 2 custom Dockerfiles (machine, orchestrator) |
| Patches applied | 1 (smia_agent.py) | 2 (smia_agent.py + acl_handling_behaviour.py) |

---

## 3. Design Requirements Validated

The SMIA paper (Hurtado et al., 2025, DOI: 10.1016/j.jii.2025.100915, Table 1) defines 8 design requirements for the SMIA approach. Case 1 adds evidence for requirements not fully demonstrated in Case 0:

| Req. | Description | Case 0 | Case 1 |
|---|---|---|---|
| R1 | Compliance with AAS and CSS industry standards | ✓ | ✓ |
| R2 | Automated self-configuration of Digital Twins | ✓ | ✓ (3 machines + orchestrator self-configure) |
| R3 | Integration of physical assets via standard interfaces (AID) | ✓ | ✓ |
| R4 | Adaptability to flexible/reconfigurable architectures | Partial | **✓** (any machine can be added by dropping an AASX) |
| R5 | Inclusion in distributed and decentralized systems | Partial | **✓** (3 independent agents, no shared state) |
| R6 | Peer-to-peer communication and negotiation via FIPA-ACL | — | **✓** (FIPA-CNP implemented end-to-end) |
| R7 | Separation between physical asset and Digital Twin | ✓ | ✓ |
| R8 | Modular and extensible software design | ✓ | **✓** (extension hooks used for both agent types) |

R6 is the central new contribution of Case 1: autonomous peer-to-peer negotiation between agents using the standardized FIPA-ACL Contract Net Protocol, driven entirely by AAS models and CSS ontology relationships.

---

## 4. System Architecture

### 4.1 Physical Infrastructure

Three physical machines are involved, same as Case 0:

| # | Machine | Role |
|---|---------|------|
| 1 | Linux dev machine (this repo) | Runs all 8 Docker services |
| 2 | DIDA central machine (`192.168.155.10`) | *Reference only* — not used in Case 1 (Node-RED and Mosquitto are now containerized) |
| 3 | fischertechnik Windows machine | Receives MQTT commands, executes warehouse crane macro |

In Case 1, Node-RED and Mosquitto run inside Docker containers on Machine 1, eliminating the external dependency on the DIDA central machine for the core pipeline.

### 4.2 Logical Architecture — 8 Docker Services

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        smia-net (Docker bridge)                         │
│                                                                         │
│  ┌───────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │ ejabberd  │    │ smia-machine0│    │ smia-machine1│                 │
│  │  (XMPP)  │◄───│ (SMIA_agent) │    │(smia_machine1│                 │
│  │  :5222   │◄───│  red pieces  │    │ blue pieces) │                 │
│  └─────┬─────┘    └──────────────┘    └──────────────┘                 │
│        │          ┌──────────────┐    ┌──────────────┐                 │
│        │◄─────────│ smia-machine2│    │smia-orchestr.│                 │
│        │◄─────────│(smia_machine2│◄───│(smia_orch)   │                 │
│        │          │ white pieces)│    │FIPA-CNP init │                 │
│        │          └──────────────┘    └──────────────┘                 │
│        │          ┌──────────────┐    ┌──────────────┐   ┌──────────┐  │
│        │◄─────────│ smia-operator│    │   nodered    │   │mosquitto │  │
│        │          │  GUI :10000  │    │  :1880       │──►│-central  │  │
│        │          └──────────────┘    └──────────────┘   │  :1883   │  │
│                                                           └────┬─────┘  │
└───────────────────────────────────────────────────────────────┼─────────┘
                                                                │ MQTT bridge
                                                                ▼
                                                    [fischertechnik machine]
                                                    [warehouse crane macro]
```

All 8 services share the `smia-net` Docker bridge network. Docker DNS resolves all service names (`ejabberd`, `nodered`, `mosquitto-central`) automatically inside the network. No IP addresses are hardcoded in the Python code.

### 4.3 End-to-End Data Flow — Case 1

```
[Browser — Operator]
    │ selects smia_orch@ejabberd in GUI
    │ selects Capability_PickPiece → Skill_Orchestrate_PickPiece → color=red
    │ HTTP POST :10000
    ▼
[smia-operator container]
    │ FIPA-ACL REQUEST (performative=request, ontology=css-service)
    │ thread=T_op, body={capabilityIRI: ..., skillParams: {color: "red"}}
    │ → XMPP → ejabberd → smia_orch@ejabberd
    ▼
[smia-orchestrator container — OrchestratorDispatchBehaviour]
    │
    │ ── PHASE 1: DISCOVERY AND ROUTING ──────────────────────────────
    │ 1. Reserves T_op immediately (prevents ACLHandlingBehaviour from double-handling)
    │ 2. Extracts color="red", maps red → position="0" (COLOR_POSITION_MAP)
    │ 3. Scans /smia_archive/config/aas/*.aasx (shared volume) with BaSyx:
    │    - Reads SoftwareNameplate → InstanceName → JID per AASX
    │    - Reads Capability_PickPiece/color property per AASX
    │    - Filters: only machines where color == "red"
    │    → eligible machines: ["SMIA_agent@ejabberd"]
    │ 4. Generates neg_thread=T_neg (UUID), reserves T_neg
    │ 5. Stores: pending_orchestrations[T_neg] = {phase: 'negotiation', op_thread: T_op, ...}
    │
    │ FIPA-ACL CFP (performative=cfp, protocol=fipa-contract-net, ontology=css-service)
    │ thread=T_neg, to=SMIA_agent@ejabberd
    │ body={capabilityIRI, negCriterion: Skill_NegAvailability IRI,
    │       negTargets: [SMIA_agent@ejabberd], negRequester: smia_orch@ejabberd,
    │       skillParams: {color: "red"}}
    ▼
[smia-machine0 container — NegotiatingBehaviour → HandleNegotiationBehaviour]
    │
    │ ── PHASE 2: FIPA-CNP NEGOTIATION (built-in SMIA) ───────────────
    │ on_start():
    │   1. Capability checking: does this machine have Capability_PickPiece? ✓
    │   2. negTargets has 1 element → this machine is the ONLY candidate
    │      → immediate winner, no PROPOSE exchange needed
    │
    │ FIPA-ACL INFORM (performative=inform, protocol=fipa-contract-net)
    │ thread=T_neg, to=smia_orch@ejabberd
    │ body={winner: true}
    ▼
[smia-orchestrator — OrchestratorDispatchBehaviour]
    │
    │ ── PHASE 3: CAPABILITY EXECUTION ───────────────────────────────
    │ 1. Generates exec_thread=T_exec (UUID), reserves T_exec
    │ 2. Stores: pending_orchestrations[T_exec] = {phase: 'awaiting_result', ...}
    │ 3. Marks pending_orchestrations[T_neg].phase = 'done'
    │ 4. Builds execution request: skillParams = {position: "0"} (position, not color)
    │
    │ FIPA-ACL REQUEST (performative=request, ontology=css-service)
    │ thread=T_exec, to=SMIA_agent@ejabberd
    │ body={capabilityIRI: Capability_PickPiece IRI, skillParams: {position: "0"}}
    ▼
[smia-machine0 — ACLHandlingBehaviour → HandleCapabilityBehaviour]
    │
    │ ── PHASE 4: PHYSICAL EXECUTION (built-in SMIA) ─────────────────
    │ 1. Resolves capabilityIRI → Capability_PickPiece OWL instance
    │ 2. Follows isRealizedBy → Skill_PickPiece OWL instance
    │ 3. Follows accessibleThroughAssetService → pickPiece AID action
    │ 4. Reads AID: base=http://nodered:1880, href=/smia/lego/pick, method=POST
    │
    │ HTTP POST http://nodered:1880/smia/lego/pick  ← body is EMPTY
    │ (Skill_PickPiece has no hasParameter → received_skill_input_data={} →
    │  no body added; position reaches Node-RED via AID URL query param or
    │  DEFAULT_POSITION=0; see §13.5)
    ▼
[nodered container]
    │ Node-RED flow: extracts position, publishes MQTT
    │
    │ MQTT publish QoS=1
    │   broker: mosquitto-central:1883
    │   topic:  vicom/61/piso_0/lab/lego/commands
    │   payload: bandera_custom:0
    ▼
[mosquitto-central container]
    │ MQTT bridge → fischertechnik machine broker
    ▼
[fischertechnik machine — warehouse crane]
    │ slot 0 picked
    ▼

    ── RESULT PROPAGATION ────────────────────────────────────────────

[smia-machine0 → smia-orchestrator]
    FIPA-ACL INFORM thread=T_exec, body=<HTTP response from Node-RED>

[smia-orchestrator → smia-operator]
    FIPA-ACL INFORM thread=T_op, body=<same result>

[smia-operator → Browser]
    GUI displays: "INFORM received" / result
```

### 4.4 Multi-Machine Negotiation (when multiple machines match)

When two or more machines are eligible for the same color (future scenario, e.g. two red-piece machines), the negotiation proceeds through peer-to-peer PROPOSE exchange:

```
Orchestrator         Machine A (avail=1.0)    Machine B (avail=0.0)
     │                       │                       │
     │──CFP(negTargets:[A,B])─►                       │
     │──CFP(negTargets:[A,B])────────────────────────►│
     │                       │                       │
     │           on_start: get negValue              on_start: get negValue
     │           → GET /availability → 1.0          → GET /availability → 0.0
     │                       │                       │
     │          A sends PROPOSE(negValue=1.0) ───────►│
     │          B sends PROPOSE(negValue=0.0) ◄───────│
     │                       │                       │
     │       A receives 0.0 < 1.0 → A wins           │
     │       B receives 1.0 > 0.0 → B loses          │
     │                       │                       │
     │◄──INFORM({winner:True})│                       │
     │                                               │ (B stays silent)
     │
  Orchestrator sends REQUEST to A → execution proceeds
```

Tie-breaking: if both machines return the same value, `handle_neg_values_tie()` applies a seeded PRNG (seed = `msg.thread`) so all agents compute the same winner deterministically.

---

## 5. Technologies Used

This table extends the one in `doc_case0.md §3` with additions specific to Case 1.

| Technology | Role in Case 1 | Docker Image / Source |
|---|---|---|
| **FIPA-ACL** | Standardized agent communication language; all inter-agent messages follow FIPA-ACL structure (performative, ontology, protocol, thread) | Built into SPADE/SMIA |
| **FIPA-CNP** | Contract Net Protocol; the negotiation protocol used between orchestrator and machines | Built into SMIA (`HandleNegotiationBehaviour`), initiator side implemented in this TFG |
| **SPADE** | Python multi-agent framework (asyncio + XMPP); all SMIA behaviours are SPADE behaviours | Bundled in SMIA image |
| **ExtensibleSMIAAgent** | SMIA subclass that exposes three official extension hooks: `add_new_agent_service`, `add_new_agent_capability`, `add_new_asset_connection` | `src/smia/agents/extensible_smia_agent.py` |
| **OrchestratorDispatchBehaviour** | Custom `CyclicBehaviour` implementing the FIPA-CNP initiator side: AAS-based discovery, color routing, CFP broadcast, winner dispatch, result forwarding | `additional_tools/extended_agents/smia_orchestrator_agent/orchestrator_dispatch_behaviour.py` |
| **aiohttp** | Async HTTP client used by machines to query Node-RED availability endpoint without blocking SPADE's asyncio event loop | Bundled in SMIA image |
| **Mosquitto** | MQTT broker containerized inside Docker; bridges commands to fischertechnik machine's broker | `eclipse-mosquitto:2` |
| **Node-RED** | HTTP→MQTT bridge; also tracks machine busy state via global variable | `nodered/node-red:latest` |
| **`.env` + `.env.example`** | Environment-variable-based configuration for all 8 services; `.env.example` is the committed template | Docker Compose built-in |

---

## 6. Repository Layout

New files added for Case 1 (relative to Case 0):

```
SMIA/
├── my_models/
│   ├── aas/
│   │   ├── LEGO_factory_case0.aasx         ← machine0 (red pieces, slot 0) — updated from Case 0
│   │   ├── LEGO_machine1_case0.aasx        ← machine1 (blue pieces, slot 1) — NEW
│   │   ├── LEGO_machine2_case0.aasx        ← machine2 (white pieces, slot 2) — NEW
│   │   ├── SMIA_orchestrator.aasx          ← orchestrator — NEW
│   │   └── SMIA_Operator_article.aasx      ← operator (unchanged from Case 0)
│   ├── docker/
│   │   ├── smia-machine/Dockerfile         ← custom image for all 3 machine agents — NEW
│   │   └── smia-orchestrator/Dockerfile    ← custom image for orchestrator — NEW
│   ├── mosquitto/
│   │   ├── mosquitto.conf                  ← Mosquitto broker config — NEW
│   │   └── conf.d/bridge.conf              ← MQTT bridge to fischertechnik machine — NEW
│   ├── nodered/
│   │   └── flows.json                      ← Node-RED flows (HTTP→MQTT bridge + availability) — NEW
│   ├── xmpp_server/
│   │   └── ejabberd.yml                    ← Updated: 5 XMPP accounts instead of 2
│   ├── docker-compose.yml                  ← Updated: 8 services, .env-driven config
│   ├── .env.example                        ← NEW: template for all credentials/config
│   ├── .env                                ← NOT committed (gitignored)
│   └── doc_case1.md                        ← This document
│
├── src/smia/
│   ├── agents/smia_agent.py                ← PATCHED (asset connection object-identity bug)
│   └── behaviours/acl_handling_behaviour.py ← PATCHED (orchestrator race condition)
│
└── additional_tools/extended_agents/
    ├── smia_machine_agent/
    │   ├── smia_machine_starter.py         ← NEW: ExtensibleSMIAAgent launcher for machines
    │   └── smia_machine_agent_services.py  ← NEW: get_machine_availability() agent service
    └── smia_orchestrator_agent/
        ├── smia_orchestrator_starter.py    ← NEW: ExtensibleSMIAAgent launcher for orchestrator
        └── orchestrator_dispatch_behaviour.py ← NEW: FIPA-CNP initiator + result forwarding
```

> **Critical:** The `my_models/aas/` folder must contain **only valid `.aasx` files**. Any other file type (`.json`, `.md`, `.bak`) causes the operator GUI scanner to fail with HTTP 500 during AAS discovery.

---

## 7. SMIA Framework — Deeper Concepts for Case 1

This section covers SMIA internals that are directly involved in the Case 1 flow and are required to understand the extensions implemented in this TFG.

### 7.1 AAS Types — Why SMIA is Type 3

The RAMI 4.0 and SMIA paper classify AAS implementations into three types by interaction capability:

| Type | Interaction | Description |
|---|---|---|
| Type 1 | Passive | Static file exchange. The AASX is read by external applications. No real-time interaction. |
| Type 2 | Reactive | REST API. The AAS responds to external queries. Reactive but not autonomous. |
| **Type 3** | **Proactive** | **Peer-to-peer communication. FIPA-ACL. Autonomous behaviour. Can initiate interactions.** |

SMIA implements Type 3. Each SMIA agent is not just a data store about an asset — it is an autonomous software agent that can *initiate* communication, *participate* in protocols, and *decide* how to act. Case 1 demonstrates this fully: machines autonomously compute their availability and decide whether they won the negotiation; the orchestrator autonomously discovers peers and drives the FIPA-CNP protocol.

### 7.2 The SMIA Dual-Layer Architecture

The SMIA paper (§3) describes the framework as a dual-layer solution:

**Layer 1 — Methodology:** A defined process for enriching an AAS with CSS ontology semantics via `semanticId` fields. This is the AASX authoring work done in AASX Package Explorer: assigning CSS IRIs to AAS elements so that capabilities, skills, and skill interfaces are declared in a machine-readable, standards-compliant way.

**Layer 2 — Technology:** The Python software toolchain (SMIA) that reads those enriched AAS descriptions at startup and automatically generates an executable Digital Twin. The agent does not need to be programmed with knowledge of the specific asset — it derives all this from the AAS model.

This is the key principle: **"The AAS is treated as a static, administrative model, while the DT represents its dynamic, operational counterpart."** The AAS declares what an asset can do and how to interface with it. SMIA instantiates that declaration as a running agent.

### 7.3 SMIA Self-Configuration — Three Tracks During Booting

When a SMIA agent starts, it executes `InitAASModelBehaviour` (a `OneShotBehaviour` in the Booting state). This reads the AASX model and builds an in-memory semantic network of Python objects. Three parallel tracks of work are performed:

**Track 1 — CSS class instances (capabilities, skills, skill interfaces):**
For each IRI in `CSS_ONTOLOGY_THING_CLASSES_IRIS`, SMIA calls BaSyx to find all AAS elements whose `semanticId` matches that IRI. For each found element, it:
1. Creates an OWLready2 instance of the corresponding OWL class.
2. Calls `get_qualifier_value_by_semantic_id(iri)` for each OWL data property in the class's domain — populating the instance with values from the AAS qualifiers.
3. Converts the BaSyx Python class to the corresponding SMIA extended class (e.g., `ExtendedSimpleSkill`, `ExtendedCapability`).

**Track 2 — CSS object property relationships:**
For each IRI in `CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS`, SMIA finds all `RelationshipElement`s in the AAS model whose `semanticId` matches. For each found relationship, it links the two previously created OWL instances via the corresponding OWL object property.

**Track 3 — Asset connections (AID submodel):**
SMIA reads the `AssetInterfacesDescription` submodel, finds each interface element, and creates an `HTTPAssetConnection` Python object configured from the `EndpointMetadata` (base URL, content type) and `InteractionMetadata` (actions, properties).

**Result:** an executable semantic network:
```
Capability_PickPiece (OWL instance)
    └── isRealizedBy → Skill_PickPiece (OWL instance)
                            └── accessibleThroughAssetService → pickPiece (OWL instance)
                                    └── aas_sme_ref → AID/pickPiece (BaSyx element)
                                            └── associated HTTPAssetConnection
                                                    (base=http://nodered:1880, href=/smia/lego/pick)
```

**Critical IRI case-sensitivity:** The matching in Track 2 is an exact lowercase string comparison. Every `RelationshipElement.semanticId` in the AASX must be lowercase. A single capital letter causes a silent skip — the OWL link is never created — leading to a `NoneType` crash at runtime (typically in `HandleNegotiationBehaviour`).

### 7.4 SMIA Behaviours in the Running State

Once self-configuration completes, the FSM transitions to `StateRunning`, which adds two permanent `CyclicBehaviour` instances to the agent:

**`ACLHandlingBehaviour`:** Receives all non-negotiation FIPA-ACL messages (10-second timeout per iteration). Validates the `ontology` field against the SMIA schema map. For `ontology=css-service`, spawns a `HandleCapabilityBehaviour` (a `OneShotBehaviour`) to handle that specific request. For each message, the spawned behaviour runs to completion and exits.

**`NegotiatingBehaviour`:** Receives all FIPA-ACL messages with `ontology=Negotiation` or negotiation-related performatives. When a CFP arrives, spawns a `HandleNegotiationBehaviour` (a `CyclicBehaviour`) with a message template restricted to the specific negotiation thread.

In addition, any behaviour added via `add_new_agent_capability()` — such as `OrchestratorDispatchBehaviour` — also starts here.

---

## 8. SMIA Extensibility Mechanism

SMIA provides three official extension hooks via `ExtensibleSMIAAgent` (inherits from `SMIAAgent`):

| Hook | Signature | What it adds |
|---|---|---|
| `add_new_agent_capability(behaviour)` | SPADE behaviour instance | A new autonomous behaviour that runs concurrently with the base SMIA behaviours |
| `add_new_agent_service(id, fn)` | string + Python function | A callable registered in a dict under `id`; called by SMIA internals when needed |
| `add_new_asset_connection(id_short, conn)` | string + `AssetConnection` subclass | A new asset communication protocol (OPC UA, MQTT, etc.) |

This TFG uses the first two:
- **Machines** use `add_new_agent_service` to register `get_machine_availability` under `'machineAvailValue'`.
- **Orchestrator** uses `add_new_agent_capability` to register `OrchestratorDispatchBehaviour`.

The fundamental distinction is explained in §11.

### 8.1 Machine Launcher — `smia_machine_starter.py`

**File:** `additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py`

This is the entry point executed by all three machine containers (`smia-machine0`, `smia-machine1`, `smia-machine2`). The Dockerfile replaces the default SMIA launcher with this file via `CMD ["python3", "-u", "smia_machine_starter.py"]`.

```python
def main():
    smia.initial_self_configuration()          # reads smia-initialization.properties;
                                               # sets up logging and framework config

    aas_model_path = DockerUtils.get_aas_model_from_env_var()
    smia.load_aas_model(aas_model_path)        # AAS_MODEL_NAME env var → AASX path;
                                               # BaSyx parses the AASX into memory

    smia_jid    = os.environ.get('AGENT_ID')   # full XMPP JID from env
    smia_passwd = os.environ.get('AGENT_PASSWD')

    smia_agent = ExtensibleSMIAAgent(smia_jid, smia_passwd)  # supports extension hooks

    # Register the availability service. The string 'machineAvailValue' must exactly
    # match the id_short of the SkillInterface AAS element in the machine AASX.
    # SMIA resolves: negCriterion IRI → Skill_NegAvailability OWL instance
    #                → accessibleThroughAgentService → machineAvailValue id_short
    #                → execute_agent_service_by_id('machineAvailValue')
    #                → calls get_machine_availability()
    smia_agent.add_new_agent_service('machineAvailValue', machine_svc.get_machine_availability)

    smia.run(smia_agent)   # starts the SMIA lifecycle: Booting → (3 tracks) → Running
```

All three machines use **the same file**. The distinction between machine0 (red), machine1 (blue), and machine2 (white) is entirely in:
- `AAS_MODEL_NAME` env var → which AASX file is loaded
- `AAS_ID` env var → which AAS shell inside the AASX SMIA uses for self-configuration
- `AGENT_ID` / `AGENT_PASSWD` env vars → which XMPP account the agent authenticates with

### 8.2 Orchestrator Launcher — `smia_orchestrator_starter.py`

**File:** `additional_tools/extended_agents/smia_orchestrator_agent/smia_orchestrator_starter.py`

Same structure as the machine launcher, but registers a behaviour instead of a service:

```python
def main():
    smia.initial_self_configuration()
    aas_model_path = DockerUtils.get_aas_model_from_env_var()  # SMIA_orchestrator.aasx
    smia.load_aas_model(aas_model_path)

    smia_jid    = os.environ.get('AGENT_ID')    # smia_orch@ejabberd
    smia_passwd = os.environ.get('AGENT_PASSWD')

    smia_agent = ExtensibleSMIAAgent(smia_jid, smia_passwd)

    # add_new_agent_capability() accepts a SPADE behaviour INSTANCE.
    # The instance is appended to extended_agent_capabilities and started alongside
    # ACLHandlingBehaviour and NegotiatingBehaviour when smia.run() enters StateRunning.
    # OrchestratorDispatchBehaviour.on_start() sets self.agent.pending_orchestrations = {}
    # — this attribute is the discriminator used by Patch 2 to detect orchestrator mode.
    orch_behaviour = OrchestratorDispatchBehaviour()
    smia_agent.add_new_agent_capability(orch_behaviour)

    smia.run(smia_agent)
```

**Critical difference from machines:** The orchestrator's AASX declares `AgentCapability` (not `AssetCapability`) for `Capability_PickPiece`. This means SMIA's self-configuration does NOT create an `HTTPAssetConnection` for it — there is no AID endpoint for the orchestrator to call directly. All execution is delegated to the winning machine agent via FIPA-ACL. If `AssetCapability` were used instead, SMIA would attempt to find an HTTP interface during `HandleCapabilityBehaviour` execution and fail silently.

---

## 9. FIPA-CNP Multi-Agent Negotiation Protocol

### 9.1 What is FIPA-CNP?

The **Foundation for Intelligent Physical Agents Contract Net Protocol (FIPA-CNP)** is a standardized multi-agent interaction protocol for task allocation. It is designed for scenarios where a manager agent needs to find the best responder among a set of participants to execute a given task.

The protocol defines three roles:
- **Initiator (Manager):** Sends a Call For Proposals (CFP), evaluates offers, and accepts the best one.
- **Participant (Responder):** Receives the CFP, evaluates its own capacity, and submits a PROPOSE or REFUSE.
- **Winner:** The participant whose PROPOSE is accepted; executes the task and reports results.

Standard FIPA-CNP message flow (classical, as defined by FIPA):

```
Initiator          Participant A      Participant B
     │                  │                  │
     │── CFP ──────────►│                  │
     │── CFP ───────────────────────────── ►│
     │                  │                  │
     │◄── PROPOSE ───────│                  │   (or REFUSE)
     │◄── PROPOSE ─────────────────────────│
     │                  │                  │
     │── ACCEPT ────────►│  (winner)        │
     │── REJECT ──────────────────────────►│  (losers)
     │                  │                  │
     │◄── INFORM ────────│  (done)          │
```

### 9.2 How SMIA Adapts FIPA-CNP

The SMIA implementation differs from classical FIPA-CNP in one critical way: the **PROPOSE exchange is peer-to-peer among participants** (not funneled through the initiator). The initiator sends no ACCEPT/REJECT — participants self-determine the winner and only the winner notifies the initiator. This reduces the orchestrator's message load by `O(n)` and makes the protocol more decentralized.

SMIA's FIPA-CNP (as implemented, with 2 competing machines for illustration):

```
Orchestrator       Machine A (avail=1.0)    Machine B (avail=0.0)
     │                    │                       │
     │── CFP ────────────►│                       │
     │── CFP ─────────────────────────────────── ►│
     │                    │                       │
     │         ┌──────────┤ computes negValue     │
     │         │ GET /availability → 1.0          │ GET /availability → 0.0
     │         └──────────┤                       │
     │                    │                       │
     │                    │── PROPOSE(1.0) ───────►│
     │                    │◄── PROPOSE(0.0) ────────│
     │                    │                       │
     │                    │ 1.0 > 0.0 → A wins    │ 0.0 < 1.0 → B loses
     │                    │                       │
     │◄── INFORM(winner) ──│                       │  (B is silent)
     │                    │                       │
     │── REQUEST ─────────►│  (execute task)       │
     │◄── INFORM(result) ──│                       │
```

Key differences from classical FIPA-CNP:
- Machines exchange PROPOSEs directly among themselves (not via orchestrator)
- No explicit ACCEPT/REJECT from orchestrator — winner self-declares
- Orchestrator only sends: CFP → (later) REQUEST to winner

This TFG implemented the missing **initiator side**: `OrchestratorDispatchBehaviour`.

In SMIA's implementation (paper §4.2, `HandleNegotiationBehaviour.py`):
1. Each machine receives the CFP with the full `negTargets` list (all participants).
2. Each machine independently computes its `negValue` (availability score).
3. Each machine broadcasts a **PROPOSE** to all other machines in `negTargets` (not to the orchestrator).
4. Each machine compares received values to its own; if its value is highest, it declares itself the winner.
5. **Only the winner** sends `INFORM({winner: True})` to the `negRequester` (orchestrator).

The orchestrator never sees PROPOSE messages. It only sees the final winner INFORM. This means the SMIA framework built the **responder side** of FIPA-CNP — machines negotiate among themselves. This TFG implemented the missing **initiator side**: `OrchestratorDispatchBehaviour`.

### 9.3 FIPA-ACL Message Structure

All inter-agent messages follow the FIPA-ACL standard. In SMIA's implementation (via SPADE), a message has:

| Field | Set via | Case 1 values used |
|---|---|---|
| `to` | `Message(to=jid)` | target agent's XMPP JID |
| `thread` | `msg.thread = uuid` | identifies the conversation; used to correlate request/response |
| `performative` | metadata `'performative'` | `request`, `cfp`, `propose`, `inform`, `failure`, `refuse` |
| `ontology` | metadata `'ontology'` | `css-service` (capability requests and CFPs), `Negotiation` (legacy) |
| `protocol` | metadata `'protocol'` | `fipa-contract-net` (for CFP/PROPOSE), `fipa-request` (for REQUEST) |
| `body` | `msg.body = json.dumps(...)` | JSON string |

**CFP body (orchestrator → machines):**
```json
{
  "capabilityIRI": "http://www.w3id.org/upv-ehu/gcis/css-smia#Capability_PickPiece",
  "negCriterion":  "http://www.w3id.org/hsu-aut/css#Skill_NegAvailability",
  "negTargets":    ["SMIA_agent@ejabberd"],
  "negRequester":  "smia_orch@ejabberd",
  "skillParams":   {"http://www.w3id.org/hsu-aut/css#color": "red"}
}
```

**PROPOSE body (machine → machine, in multi-machine scenario):**
```json
{
  "capabilityIRI": "...",
  "negCriterion":  "...",
  "negTargets":    ["SMIA_agent@ejabberd", "smia_machine1@ejabberd"],
  "negRequester":  "smia_orch@ejabberd",
  "skillParams":   {"...": "red"},
  "negValue":      1.0
}
```

**Winner INFORM body (machine → orchestrator):**
```json
{"winner": true}
```

**Execution REQUEST body (orchestrator → winner machine):**
```json
{
  "capabilityIRI": "http://www.w3id.org/upv-ehu/gcis/css-smia#Capability_PickPiece",
  "skillParams":   {"position": "0"}
}
```

Note: the orchestrator replaces `{color: "red"}` with `{position: "0"}` before sending the execution request. The physical crane operates by slot position — it has no color sensor. The mapping is in `COLOR_POSITION_MAP` in `orchestrator_dispatch_behaviour.py`.

### 9.4 Thread Management

Each orchestration involves **two distinct conversation threads**:

- `T_op` (operator thread): created by the operator GUI, used for the full operator ↔ orchestrator conversation.
- `T_neg` (negotiation thread): generated by the orchestrator as a UUID, used for the CFP/winner-INFORM exchange.
- `T_exec` (execution thread): generated by the orchestrator as another UUID, used for the execution REQUEST/INFORM exchange.

All three threads are reserved in `agent.reserved_threads` as soon as the orchestrator takes ownership. This prevents `ACLHandlingBehaviour` (which receives all messages) from spawning duplicate `HandleCapabilityBehaviour` instances for the same messages.

---

## 10. AASX Models — Full Structure

All five AASX files live in `my_models/aas/`. They are mounted as a shared volume into all containers at `/smia_archive/config/aas`. Each container loads only its own AASX (identified by `AAS_MODEL_NAME` env var), but all files are visible — the orchestrator and operator scan the full folder for AAS discovery.

### 10.1 Machine AASXs (machine0, machine1, machine2)

All three machine AASXs follow the same structure. The only differences are: UUID identifiers, XMPP JID (in SoftwareNameplate), color value (in `Capability_PickPiece`), and AID `href` (pick endpoint includes a position query parameter for machines 1 and 2).

#### AAS Shells in each machine AASX

| AAS idShort | AAS id (example: machine0) | Role |
|---|---|---|
| `LEGO_factory` (or `LEGO_machine1`, `LEGO_machine2`) | `urn:uuid:6475_0111_2062_9689` | Machine's physical Digital Twin |
| `SMIA_agent` (or `SMIA_machine1`, `SMIA_machine2`) | `urn:uuid:6373_1111_2062_6896` | Software agent's own Digital Twin |

#### Submodel 1: SubmodelWithCapabilitySkillOntology

Contains `ConceptDescription` entries documenting the CSS ontology concepts. Not processed by SMIA for execution; serves as inline documentation within the package.

#### Submodel 2: AssetInterfacesDescription (AID)

```
AssetInterfacesDescription  [semanticId: AID/Submodel]
├── InterfaceHTTP  [SMC, semanticId: AID/Interface, suppl.semanticId: http://www.w3.org/2011/http]
│   ├── EndpointMetadata  [SMC, semanticId: AID/EndpointMetadata]
│   │   ├── base  [Property, xs:anyURI, semanticId: td#baseURI]
│   │   │         value: http://nodered:1880    ← Docker DNS name (not IP)
│   │   └── contentType  [Property, semanticId: hypermedia#forContentType]
│   │                    value: application/json
│   └── InteractionMetadata  [SMC, semanticId: AID/InteractionMetadata]
│       └── actions  [SMC]
│           ├── pickPiece  [SMC, semanticId: td#ActionAffordance]
│           │   ├── forms  [SMC, semanticId: td#hasForm]
│           │   │   ├── href  [Property, semanticId: hypermedia#hasTarget]
│           │   │   │         machine0: /smia/lego/pick
│           │   │   │         machine1: /smia/lego/pick?position=1
│           │   │   │         machine2: /smia/lego/pick?position=2
│           │   │   └── htv_methodName  [Property, semanticId: http#methodName]  POST
│           │   └── input [SMC, semanticId: td#hasInputSchema]
│           │       ├── color     [Property, xs:string]
│           │       └── position  [Property, xs:int]
│           └── placePiece  [SMC, semanticId: td#ActionAffordance]  (same pattern)
│
└── Interface_00  [SMC, semanticId: AID/Interface]  ← agent service interface
    └── InteractionMetadata  [SMC, semanticId: AID/InteractionMetadata]
        └── actions  [SMC]
            └── machineAvailValue  [SMC, semanticId: td#ActionAffordance]
```

`Interface_00` is the agent service interface for the FIPA-CNP negotiation value. Its parent submodel does **not** have the `AssetInterfacesDescription` semanticId — this is what SMIA checks to distinguish agent services from asset services. When `HandleNegotiationBehaviour` resolves `Skill_NegAvailability → machineAvailValue`, it checks the parent submodel: since `Interface_00` does not belong to `AssetInterfacesDescription`, SMIA calls the registered Python function instead of making an HTTP call.

> **Why position is in the AID URL, not the HTTP body.** `HandleCapabilityBehaviour.execute_capability()` only populates `received_skill_input_data` (the HTTP body) if the CSS ontology shows `hasParameter` relationships for the Skill. Machine AASXs do NOT define `hasParameter` for `Skill_PickPiece` (the operator GUI doesn't need to show a position field for machines — position is determined by the orchestrator). Therefore `received_skill_input_data = {}` and SMIA sends an empty POST body. Node-RED's `pick_handler` fallback chain: body → query param → DEFAULT_POSITION. Each machine's position is therefore encoded in the AID `href`:
> - machine0 (red): `href = /smia/lego/pick` → `DEFAULT_POSITION = 0` ✓
> - machine1 (blue): `href = /smia/lego/pick?position=1` → `query.position = 1` ✓
> - machine2 (white): `href = /smia/lego/pick?position=2` → `query.position = 2` ✓

#### Submodel 3: CapabilitiesAndSkills

```
CapabilitiesAndSkills
├── Capability_PickPiece  [SMC, semanticId: css-smia#AssetCapability]
│   ├── Qualifier: type=hasLifecycle, value=OFFER
│   │             semanticId: css-smia#hasLifecycle
│   ├── color     [Property, xs:string]
│   │             value: "red" | "blue" | "white"  ← differentiates machines
│   └── position  [Property, xs:int]
├── Skill_PickPiece  [Property, xs:string, semanticId: css#Skill]
│   └── Qualifier: type=SkillImplementationType, value=OPERATION
│                 semanticId: css-smia#hasImplementationType  ← REQUIRED for Case 1
├── Skill_NegAvailability  [Property, xs:string, semanticId: css#Skill]
│   └── Qualifier: type=SkillImplementationType, value=OPERATION
│                 semanticId: css-smia#hasImplementationType
└── Skill_PlacePiece  [Property, xs:string, semanticId: css#Skill]  (same)
```

> **Critical — SkillImplementationType semanticId:** For Case 0 (single-machine), the `SkillImplementationType` qualifier's `semanticId` can be left empty — SMIA finds it by the `type` string. For Case 1, this semanticId **must** be set to `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`. Without it, `InitAASModelBehaviour`'s Track 1 cannot populate the skill's OWL instance, and `get_associated_skill_interface_instances()` returns `None`, crashing `HandleNegotiationBehaviour`.

#### Submodel 4: SemanticRelationships

Five `RelationshipElement`s encode the CSS ontology graph:

| idShort | semanticId (IRI) | first | second |
|---|---|---|---|
| `rel_CapPick_isRealizedBySkill_SkillPick` | `css#isRealizedBy` | `Capability_PickPiece` | `Skill_PickPiece` |
| `rel_CapPlace_isRealizedBySkill_SkillPlace` | `css#isRealizedBy` | `Capability_PlacePiece` | `Skill_PlacePiece` |
| `rel_SkillPick_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | `Skill_PickPiece` | `AID/.../pickPiece` |
| `rel_SkillPlace_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | `Skill_PlacePiece` | `AID/.../placePiece` |
| `rel_SkillNegAvail_agentSvc` | `css-smia#accessibleThroughAgentService` | `Skill_NegAvailability` | `AID/Interface_00/.../machineAvailValue` |

The last relationship is unique to Case 1. It links `Skill_NegAvailability` to `machineAvailValue` via `accessibleThroughAgentService`, telling SMIA to call a Python agent service (not an HTTP endpoint) when the orchestrator requests this skill for negotiation evaluation.

> **All semanticId IRIs must be fully lowercase.** The matching is a string equality check in SMIA source code. Any uppercase letter causes a silent skip (no error logged at WARNING level), producing `NoneType` crashes at runtime.

#### Submodel 5: SoftwareNameplate

Present on the second AAS shell (`SMIA_agent`). Contains the XMPP JID in `SoftwareNameplateInstance/InstanceName`. This is the only submodel the orchestrator reads from each machine's AASX during discovery.

```
SoftwareNameplate  [semanticId: https://admin-shell.io/idta/SoftwareNameplate/1/0]
└── SoftwareNameplateInstance  [SMC]
    ├── InstanceName  [Property, semanticId: .../InstanceName]
    │                 value: "SMIA_agent@ejabberd"   ← full XMPP JID
    ├── InstalledVersion  [Property]   value: "0.3.1"
    └── ...
```

### 10.2 Orchestrator AASX (SMIA_orchestrator.aasx)

The orchestrator's AASX models it as an agent that offers coordination capabilities (not physical capabilities). This is why `Capability_PickPiece` uses `css-smia#AgentCapability` semanticId — the orchestrator itself does not move the crane; it delegates.

```
AAS: SMIA_orchestrator  (id: urn:uuid:8888_0001_2026_0001)
└── Submodels:
    1. SubmodelWithCapabilitySkillOntology  (CSS ConceptDescriptions)
    2. CapabilitiesAndSkills
       ├── Capability_PickPiece  [SMC, semanticId: css-smia#AgentCapability]  ← AgentCapability!
       │   ├── Qualifier: hasLifecycle=OFFER
       │   ├── color     [Property, xs:string]   ← displayed in operator GUI
       │   └── position  [Property, xs:int]
       ├── Skill_Orchestrate_PickPiece  [Property, xs:string, semanticId: css#Skill]
       └── SkillParameter_color  [Property, xs:string, semanticId: css#SkillParameter]
    3. SemanticRelationships
       ├── rel_CapPick_isRealizedBy_SkillOrchPick
       │   semanticId: css#isRealizedBy
       │   first: Capability_PickPiece  second: Skill_Orchestrate_PickPiece
       └── rel_SkillOrch_hasParam_color
           semanticId: css#hasParameter
           first: Skill_Orchestrate_PickPiece  second: SkillParameter_color
    4. SoftwareNameplate
       └── SoftwareNameplateInstance
           └── InstanceName: "smia_orch@ejabberd"
```

The `hasParameter` relationship between `Skill_Orchestrate_PickPiece` and `SkillParameter_color` is what makes the operator GUI show a color input field when that skill is selected. The GUI reads this relationship from the AASX and renders a form field for each parameter.

`AgentCapability` vs `AssetCapability`:
- `AssetCapability` (machines): physical capability inherent to the machine hardware.
- `AgentCapability` (orchestrator): capability of the software agent itself — coordination, dispatching, negotiation. The orchestrator has no physical hardware; its "capability" is to orchestrate.

### 10.3 Operator AASX (SMIA_Operator_article.aasx)

Unchanged from Case 0. Taken directly from the SMIA repository examples. Not modified.

---

## 11. Agent Services vs. Agent Capabilities

Understanding the distinction between these two SMIA extension hooks is essential for understanding the Case 1 architecture.

### 11.1 Agent Service (`add_new_agent_service`)

An agent service is a **Python function registered under a string identifier** that matches the `id_short` of an AAS element. It is **passive**: it never runs by itself. SMIA calls it when internal machinery needs a computed value.

The registration stores the function in a dictionary:
```python
# In AgentServices.__init__:
self.services = {
    'RAM_memory_function':   <method ...>,
    'random_float_function': <method ...>,
    'machineAvailValue':     <function get_machine_availability>  ← registered by machine starter
}
```

When SMIA needs the value for `machineAvailValue`, it calls:
```python
result = await self.myagent.agent_services.execute_agent_service_by_id('machineAvailValue')
```
which does a dict lookup → calls `safe_execute_agent_service()` → checks if the function is `async` via `inspect.iscoroutinefunction()` → `await`s it if so.

**Use when:** You need to provide a value or compute a result on demand, as a response to SMIA's internal request. The base SMIA machinery already knows when and how to call it.

**In Case 1:** `get_machine_availability()` is an agent service. `HandleNegotiationBehaviour` calls it automatically when it needs the negotiation value for `Skill_NegAvailability`.

### 11.2 Agent Capability (`add_new_agent_capability`)

An agent capability is a **SPADE behaviour instance** (CyclicBehaviour, OneShotBehaviour, etc.) that **runs autonomously** in SPADE's asyncio event loop alongside the base SMIA behaviours. It is **active**: SPADE calls its `run()` method in a loop. It has its own message queue, can send and receive messages, and maintains its own state.

The registration appends to a list:
```python
smia_agent.extended_agent_capabilities.append(OrchestratorDispatchBehaviour())
```
When `smia.run()` is called and the agent enters `StateRunning`, SMIA starts all behaviours in `extended_agent_capabilities` alongside `ACLHandlingBehaviour` and `NegotiatingBehaviour`.

**Use when:** You need entirely new autonomous logic that doesn't exist in base SMIA — a new protocol, a new interaction pattern, new message routing. The logic must run independently, receiving messages and making decisions without being called by the existing framework.

**In Case 1:** `OrchestratorDispatchBehaviour` is an agent capability. It implements the FIPA-CNP initiator role, which does not exist anywhere in base SMIA.

### 11.3 Summary

| Question | Agent Service | Agent Capability |
|---|---|---|
| Does it run on its own? | No — called by SMIA internals | Yes — SPADE calls `run()` in a loop |
| Does it receive FIPA-ACL messages? | No | Yes |
| Does it maintain state across calls? | No (stateless function) | Yes (instance variables) |
| What does it provide? | A computed value or result | A new autonomous protocol or behaviour |
| Analogy | A library function your code calls | A separate thread with its own logic |

---

## 12. Machine Availability Service

### 12.1 Purpose

Each machine must report its availability (0.0 = busy, 1.0 = free) to participate in FIPA-CNP negotiation. This value is the machine's `negValue`: the criterion by which the winner is selected. Node-RED tracks whether the machine is currently processing a command by maintaining a `machine_busy` global variable, set to `true` when a POST arrives and cleared to `false` after the MQTT publish completes.

### 12.2 Implementation

**File:** `additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py`

The module-level constant reads the target URL from an environment variable, allowing the deployment target (containerized Node-RED vs. external host) to change without rebuilding the image:

```python
NODE_RED_BASE = os.environ.get('NODERED_URL', 'http://nodered:1880')
```

The default `'http://nodered:1880'` is the Docker DNS name of the containerized Node-RED service (see §15.4). If `NODERED_URL` is not set (e.g., local testing outside Docker), the default resolves to whatever answers at `nodered:1880` — which may be nothing.

The full availability function:

```python
async def get_machine_availability():
    """
    Agent service registered under id 'machineAvailValue'.

    Queries the Node-RED availability endpoint to determine whether the physical
    machine is currently free to accept a new task.

    Node-RED tracks busy state via a global variable 'machine_busy':
      - Set to true when a pick/place POST request arrives.
      - Cleared to false after the MQTT command is published.
    The endpoint GET /smia/lego/availability reads that variable and returns
    '1.0' (free) or '0.0' (busy) as plain text.

    Returns:
        float: 1.0 if available, 0.0 if busy or unreachable.
    """
    url = f"{NODE_RED_BASE}/smia/lego/availability"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                text = await resp.text()
                value = float(text.strip())           # Node-RED returns "1.0" or "0.0"
                _logger.info(f"[machineAvailValue] availability: {value}")
                return value
    except aiohttp.ClientConnectorError:
        # Node-RED container is not running or not reachable on the Docker network.
        # Conservative: treat as busy so this machine cannot win and receive a task
        # it cannot execute.
        _logger.warning(f"[machineAvailValue] Cannot connect to {url} — returning 0.0")
        return 0.0
    except ValueError:
        # Node-RED returned a non-float response (empty body, HTML error page, etc.)
        _logger.warning(f"[machineAvailValue] Non-float response — returning 0.0")
        return 0.0
    except Exception as e:
        _logger.error(f"[machineAvailValue] Unexpected error: {e} — returning 0.0")
        return 0.0
```

**Why `aiohttp` instead of `requests`:** SMIA runs all its behaviours in a single Python thread using `asyncio`. There is no parallelism — only cooperative concurrency. Every `await` is a checkpoint where the current coroutine suspends and other SPADE behaviours can run. If `requests.get()` (synchronous blocking) were used here, the entire asyncio event loop would freeze until the HTTP response arrived — no other SMIA behaviour could receive or send messages during that time. `aiohttp` is async: the coroutine suspends at `await resp.text()` while Node-RED processes the request, allowing other behaviours to run normally.

**Why three separate `except` clauses:** Each error source has a distinct diagnostic log message, making troubleshooting faster. `ClientConnectorError` means the Node-RED container is unreachable (network or service down). `ValueError` means Node-RED is reachable but the flow is misconfigured (non-numeric response). The generic `Exception` catches any other library-level error (SSL, timeout expiry beyond `ClientTimeout`, etc.) without swallowing the error log.

**Why no `self` parameter:** SMIA's `save_agent_service()` uses `types.MethodType` to bind the function to the `AgentServices` instance. For a plain function (not a class method), `MethodType` stores it as-is — no implicit `self` is injected. The function is then called as `await get_machine_availability()` with no positional arguments. Adding a `self` parameter would cause a `TypeError` at call time.

**Error conservatism:** All three error paths return `0.0`. An unreachable machine — whether due to Node-RED being down, a misconfigured flow, or any other failure — is treated as busy. This ensures such a machine cannot win a FIPA-CNP negotiation and be sent an execution request it cannot fulfill.

### 12.3 Registration

In `smia_machine_starter.py`:
```python
smia_agent.add_new_agent_service('machineAvailValue', machine_svc.get_machine_availability)
```

The string `'machineAvailValue'` must exactly match the `id_short` of the `machineAvailValue` action inside `Interface_00` in the machine's AASX. This is the only link between the AAS model and the Python function. If the `id_short` or the string key differ, the service is never found and the negotiation falls back to `negValue=0.0`.

### 12.4 How SMIA Calls It

`HandleNegotiationBehaviour.get_neg_value_with_criteria()`:
1. Gets the OWL instance of `Skill_NegAvailability` by resolving the `negCriterion` IRI from the CFP.
2. Gets the associated skill interface instance via `get_associated_skill_interface_instances()` (traverses the `accessibleThroughAgentService` OWL link).
3. Gets the AAS element via `get_aas_sme_ref()` → `aas_model.get_object_by_reference()`.
4. Gets its parent submodel and checks whether it belongs to the `AssetInterfacesDescription` submodel (AID semanticId check).
5. Since `Interface_00` is not the AID submodel → falls into the `else` branch → calls:
   ```python
   current_neg_value = await self.myagent.agent_services.execute_agent_service_by_id(
       aas_skill_interface_elem.id_short)   # 'machineAvailValue'
   ```
6. The value is normalized: if `1.0 < value ≤ 100.0`, it is divided by 100. Since `get_machine_availability()` returns `0.0` or `1.0`, no normalization is applied.
7. `self.neg_value = current_neg_value` — the machine's value for this negotiation round is set.

---

## 13. Orchestrator Dispatch Behaviour

### 13.1 Why It Was Implemented

The SMIA framework implements the **responder side** of FIPA-CNP: machines know how to receive a CFP, compute their value, exchange PROPOSEs, and declare a winner. What SMIA does not implement is the **initiator side**:
- Who sends the initial CFP?
- Who discovers which agents can handle a request?
- Who routes by capability constraints (e.g. color)?
- Who sends the execution request to the winner?
- Who forwards the result back to the original requester?

`OrchestratorDispatchBehaviour` implements all of this. It is a `CyclicBehaviour` (SPADE calls its `run()` every loop iteration) added to the orchestrator agent via `add_new_agent_capability()`.

### 13.2 State Tracking

Each orchestration creates two entries in `self.agent.pending_orchestrations`:

```python
pending_orchestrations = {
    T_neg:  {'phase': 'negotiation',     'op_thread': T_op, 'op_sender': jid,
             'capability_iri': ..., 'resolved_position': '0', 'skill_params': {...}},
    T_exec: {'phase': 'awaiting_result', 'neg_thread': T_neg, 'op_thread': T_op, 'op_sender': jid}
}
```

This dict also serves as the signal to `ACLHandlingBehaviour`: if `hasattr(self.myagent, 'pending_orchestrations')` is True, `ACLHandlingBehaviour` skips all `css-service REQUEST` messages (the patch in §18.1). This prevents double-handling of the operator's request.

### 13.3 Message Routing — `run()`

Every call to `run()` receives one message (5-second timeout) and routes it through four branches:

**Route 1 — New request from operator:**
Condition: `performative=request` AND `ontology=css-service` AND `thread not in reserved_threads` AND `thread not in pending_orchestrations`.
Action: Reserve `op_thread` immediately (before any `await`), then call `_start_negotiation()`.

> **Why reserve before `await`?** SPADE delivers the same message to both `OrchestratorDispatchBehaviour` and `ACLHandlingBehaviour` (broadcast delivery). `ACLHandlingBehaviour` checks `msg.thread not in self.myagent.reserved_threads` before spawning a `HandleCapabilityBehaviour`. If the orchestrator reserved the thread only *after* the async operation, there would be a window during which `ACLHandlingBehaviour` could also process the message. Reserving first (before `await`) ensures the check fails before `ACLHandlingBehaviour` can act.

**Route 2 — Winner INFORM from negotiation:**
Condition: `performative=inform` AND `thread in pending_orchestrations` AND `phase == 'negotiation'`.
Action: Call `_send_execution_request(neg_thread, winner_jid)`.

**Route 3 — Execution INFORM from winner:**
Condition: `performative=inform` AND `thread in pending_orchestrations` AND `phase == 'awaiting_result'`.
Action: Call `_forward_result_to_operator(exec_thread, msg.body)`. Cleanup both thread entries.

**Route 4 — FAILURE from machine:**
Condition: `performative=failure` AND `thread in pending_orchestrations`.
Action: Forward failure reason to operator. Cleanup state.

### 13.4 AAS-Based Machine Discovery — `_discover_machines_for_request()`

At Phase 1, the orchestrator does not have a hardcoded list of machine JIDs. It discovers them dynamically by scanning the shared `/smia_archive/config/aas/` folder (the same Docker volume that all containers share):

```python
for filename in os.listdir(AAS_FOLDER):
    if not filename.endswith('.aasx'):
        continue
    with basyx.aas.adapter.aasx.AASXReader(filepath) as reader:
        reader.read_into(object_store, file_store)
    jid = self._extract_jid_from_store(object_store)     # reads SoftwareNameplate/InstanceName
    color = self._find_capability_color(object_store, cap_id_short)  # reads Capability/color property
    if color == color_filter:
        machines.append({'jid': jid, 'color': color})
```

This replicates the pattern used by the operator GUI (`operator_gui_logic.py`) for AAS discovery. To add a new machine to the system, the only required steps are:
1. Drop its AASX into `my_models/aas/`.
2. Register its XMPP account in `ejabberd.yml` and `docker-compose.yml` (CTL_ON_CREATE).
3. Add a new service entry in `docker-compose.yml`.

No Python code changes are needed.

### 13.5 Color → Position Mapping

The operator GUI sends `color="red"` as the skill parameter. The physical crane operates by slot index (position), not by color. The orchestrator translates:

```python
COLOR_POSITION_MAP = {
    "red":   "0",   # leftmost slot in the warehouse matrix
    "blue":  "1",
    "white": "2",
}
```

This mapping is hardcoded in `orchestrator_dispatch_behaviour.py`. The resolved position is stored in `pending_orchestrations[T_neg]['resolved_position']` and used in Phase 3 when building the execution request to the winner.

**Why `{position: "0"}` in the FIPA message doesn't reach the HTTP body.** The execution REQUEST sent to the winner contains `skillParams = {position: "0"}`. However, `HandleCapabilityBehaviour.execute_capability()` (source: `handle_capability_behaviour.py:403-406`) only builds `received_skill_input_data` (the HTTP body dict) if the CSS ontology contains `hasParameter` relationships for the Skill:

```python
received_skill_input_data = {}
if skill_instance.get_associated_skill_parameter_instances() is not None:  # None for Skill_PickPiece
    for iri, value in received_body_json['skillParams'].items():
        instance = get_ontology_instance_by_iri(iri)
        received_skill_input_data[instance.name] = value
# → len({}) == 0 → add_asset_service_data() NOT called → request_body = None
```

Machine AASXs intentionally have NO `hasParameter` for `Skill_PickPiece` — the operator GUI must not show a position field for machine agents (position is determined by the orchestrator, not the operator). Therefore SMIA sends `POST /smia/lego/pick` with an **empty body**. The position reaches Node-RED instead via the AID `href` URL query parameter (`?position=N`) for machines 1 and 2, or falls back to `DEFAULT_POSITION = 0` for machine 0. The `skillParams: {position: "0"}` in the FIPA message is present for protocol completeness — it documents the execution context — but the physical routing is handled by the AID URL.

---

## 14. Custom Docker Images and Patches

### 14.1 Why Custom Images Are Needed

The base SMIA Docker image (`ekhurtado/smia:latest-alpine`) uses `SMIAAgent` as the agent class, which does not support the extension hooks (`add_new_agent_service`, `add_new_agent_capability`). To use `ExtensibleSMIAAgent` and register custom behaviours/services, the container must run a custom Python entry point instead of the default one.

### 14.2 Machine Image (`my_models/docker/smia-machine/Dockerfile`)

Build context: repo root (`SMIA/`). All three machine services (`smia-machine0`, `smia-machine1`, `smia-machine2`) use **the same Dockerfile** — differences between machines are entirely in environment variables (`AAS_MODEL_NAME`, `AAS_ID`, `AGENT_ID`, `AGENT_PASSWD`).

```dockerfile
# ================================================================
# SMIA Machine Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA image with:
#   1. smia_agent.py bug fix (asset connection object-identity comparison)
#      TODO: remove once upstream PR is merged into ekhurtado/smia
#   2. ExtensibleSMIAAgent launcher that registers the
#      get_machine_availability() FIPA-CNP negotiation service
#
# Build context: repo root (SMIA/)
# ================================================================

FROM ekhurtado/smia:latest-alpine
# Base image: Alpine Linux + Python 3.12 + pip install smia
# (SMIA framework and all its dependencies are already installed)

LABEL maintainer="afierro@vicomtech.org"
LABEL description="SMIA Machine Agent — fischertechnik warehouse crane"

# ── Patch: fix asset connection object-identity bug ──────────────
# SMIA_PKG is resolved at Docker BUILD TIME by running Python inside
# the base image. This makes the patch version-independent: it works
# regardless of Python version or future SMIA package location changes.
COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py
RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    echo "[smia-machine] Applying smia_agent.py patch at: $SMIA_PKG" && \
    cp /tmp/smia_agent_patch.py "$SMIA_PKG/agents/smia_agent.py" && \
    rm /tmp/smia_agent_patch.py

# ── Custom launcher and service module ───────────────────────────
# Files are placed at / (root). WORKDIR / puts / on sys.path so that
# `import smia_machine_agent_services` resolves without sys.path manipulation.
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /smia_machine_starter.py
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py /smia_machine_agent_services.py

WORKDIR /

# Override the default SMIA launcher (smia_docker_starter.py → SMIAAgent).
# Our launcher uses ExtensibleSMIAAgent to register custom behaviours/services.
# -u: unbuffered stdout so `docker compose logs` shows output immediately.
CMD ["python3", "-u", "smia_machine_starter.py"]
```

**Instruction-by-instruction explanation:**

| Instruction | Effect |
|---|---|
| `FROM ekhurtado/smia:latest-alpine` | Inherits Alpine Linux, Python 3.12, and `pip install smia` from the base image |
| `LABEL ...` | Metadata only; no filesystem changes |
| `COPY src/smia/agents/smia_agent.py /tmp/...` | Stages the patched file in the build layer |
| `RUN set -e && SMIA_PKG=$(...)` | Resolves SMIA package path at build time; copies patch file over the installed version |
| `COPY smia_machine_starter.py /` | The custom entry point at `/smia_machine_starter.py` |
| `COPY smia_machine_agent_services.py /` | The availability service module at `/smia_machine_agent_services.py`; imported by starter |
| `WORKDIR /` | Sets `/` as the working directory; Python's `sys.path` includes CWD, so `import smia_machine_agent_services` resolves |
| `CMD ["python3", "-u", "smia_machine_starter.py"]` | Replaces the default SMIA launcher; `-u` = unbuffered stdout |

### 14.3 Orchestrator Image (`my_models/docker/smia-orchestrator/Dockerfile`)

Same pattern as the machine image, but applies **two patches** (Patch 1 + Patch 2) in a single `RUN` layer:

```dockerfile
# ================================================================
# SMIA Orchestrator Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA image with:
#   1. smia_agent.py bug fix (asset connection object-identity comparison)
#   2. acl_handling_behaviour.py patch (orchestrator race condition fix)
#   3. ExtensibleSMIAAgent launcher that registers OrchestratorDispatchBehaviour
# ================================================================

FROM ekhurtado/smia:latest-alpine

LABEL maintainer="afierro@vicomtech.org"
LABEL description="SMIA Orchestrator Agent — FIPA-CNP multi-machine dispatch"

# ── Patch 1: fix asset connection object-identity bug ────────────
COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py

# ── Patch 2: fix ACL race condition for orchestrator mode ─────────
# ACLHandlingBehaviour receives css-service REQUESTs simultaneously with
# OrchestratorDispatchBehaviour, but checks reserved_threads before the
# orchestrator can reserve the thread — causing both to handle the same
# message. The patch adds an early return when pending_orchestrations is
# present (orchestrator-only attribute set by OrchestratorDispatchBehaviour).
COPY src/smia/behaviours/acl_handling_behaviour.py /tmp/acl_handling_patch.py

# Both patches applied in one RUN layer to minimize image layers.
RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    echo "[smia-orchestrator] Applying patches at: $SMIA_PKG" && \
    cp /tmp/smia_agent_patch.py     "$SMIA_PKG/agents/smia_agent.py" && \
    cp /tmp/acl_handling_patch.py   "$SMIA_PKG/behaviours/acl_handling_behaviour.py" && \
    rm /tmp/smia_agent_patch.py /tmp/acl_handling_patch.py

# ── Custom launcher and FIPA-CNP dispatch behaviour ──────────────
COPY additional_tools/extended_agents/smia_orchestrator_agent/smia_orchestrator_starter.py /smia_orchestrator_starter.py
COPY additional_tools/extended_agents/smia_orchestrator_agent/orchestrator_dispatch_behaviour.py /orchestrator_dispatch_behaviour.py

WORKDIR /

# Override default SMIA launcher.
CMD ["python3", "-u", "smia_orchestrator_starter.py"]
```

The `orchestrator_dispatch_behaviour.py` module is COPYd to `/` so that `from orchestrator_dispatch_behaviour import OrchestratorDispatchBehaviour` in the starter resolves via `WORKDIR /` → `sys.path`.

### 14.4 Build Lifecycle

```bash
# Required ONCE after initial clone or after any Python file change:
docker compose -f my_models/docker-compose.yml build

# Rebuild only specific services (faster):
docker compose -f my_models/docker-compose.yml build smia-machine0 smia-orchestrator

# No rebuild needed for:
# - .env changes (env vars are injected at container start, not at build)
# - AASX file changes (mounted as a volume, read at container start)
# - mosquitto/nodered config changes (also mounted as volumes)
```

**What triggers a rebuild requirement:**
| Changed file | Rebuild which service |
|---|---|
| `src/smia/agents/smia_agent.py` | `smia-machine0/1/2` and `smia-orchestrator` |
| `src/smia/behaviours/acl_handling_behaviour.py` | `smia-orchestrator` only |
| `additional_tools/.../smia_machine_starter.py` | `smia-machine0/1/2` |
| `additional_tools/.../smia_machine_agent_services.py` | `smia-machine0/1/2` |
| `additional_tools/.../smia_orchestrator_starter.py` | `smia-orchestrator` |
| `additional_tools/.../orchestrator_dispatch_behaviour.py` | `smia-orchestrator` |
| `additional_tools/.../operator_gui_logic.py` | `smia-operator` |

---

## 15. Docker Compose Deployment — 8 Services

### 15.1 One-Click Deployment

Case 1 is designed for near-zero-touch deployment:

```bash
cd /path/to/SMIA
cp my_models/.env.example my_models/.env   # fill in passwords
# Edit my_models/mosquitto/conf.d/bridge.conf: set address to fischertechnik machine IP
docker compose -f my_models/docker-compose.yml build    # build custom images (~2 min, once)
docker compose -f my_models/docker-compose.yml up -d    # start all 8 services
```

Browse to `http://localhost:10000/smia_operator` to access the operator GUI.

> **Use `docker compose` (v2, with a space), not `docker-compose` (v1, hyphen).** The v1 binary crashes with `KeyError: 'ContainerConfig'` on current Docker image metadata.

### 15.2 Service Summary

| Service | Image | Role | Port |
|---|---|---|---|
| `xmpp-server` (`ejabberd`) | `ghcr.io/processone/ejabberd` | XMPP message broker; routes FIPA-ACL messages between all agents | 5222 |
| `smia-machine0` | Built from `docker/smia-machine/Dockerfile` | Machine agent (red pieces, slot 0); JID: `SMIA_agent@ejabberd` | — |
| `smia-machine1` | Built from `docker/smia-machine/Dockerfile` | Machine agent (blue pieces, slot 1); JID: `smia_machine1@ejabberd` | — |
| `smia-machine2` | Built from `docker/smia-machine/Dockerfile` | Machine agent (white pieces, slot 2); JID: `smia_machine2@ejabberd` | — |
| `smia-orchestrator` | Built from `docker/smia-orchestrator/Dockerfile` | Orchestrator; JID: `smia_orch@ejabberd` | — |
| `mosquitto-central` | `eclipse-mosquitto:2` | MQTT broker; bridges to fischertechnik machine | 1883 (internal) |
| `nodered` | `nodered/node-red:latest` | HTTP→MQTT bridge; tracks machine busy state | 1880 |
| `smia-operator` | Built from `smia_operator_agent/Dockerfile` | Operator web GUI; JID: `operator001@ejabberd` | 10000 |

### 15.3 Startup Order

Docker Compose `depends_on` enforces the following order:

```
1. xmpp-server         (health check: TCP 5222 listening)
2. mosquitto-central   (no health check — starts fast)
3. nodered             (depends_on: mosquitto-central)
4. smia-machine0/1/2   (depends_on: xmpp-server healthy + nodered started)
5. smia-orchestrator   (depends_on: xmpp-server healthy + all machines started)
6. smia-operator       (depends_on: xmpp-server healthy)
```

The orchestrator waits for all machines because it needs them registered in ejabberd before sending CFPs. However, the machines' SMIA self-configuration (CSS booting) takes 10–30 seconds after the container starts, so the orchestrator may be ready before the machines finish booting. This is safe: the orchestrator only processes operator requests; it does not proactively send CFPs at startup.

### 15.4 Environment Variables and `.env` File

All credentials and configuration are externalized to a `.env` file (gitignored). The `.env.example` file is the committed template; copy and fill it before first use:

```bash
cp my_models/.env.example my_models/.env
# Edit my_models/.env — replace all 'change_me' values
```

Full content of `my_models/.env.example`, with annotations:

```bash
# ================================================================
# SMIA Deployment Configuration
# ================================================================
# USAGE:
#   cp .env.example .env
#   # Edit .env with real values for your deployment
#   docker compose build
#   docker compose up -d
#
# .env is listed in .gitignore and must NEVER be committed.
# This .env.example file IS committed as a template.
# ================================================================

# ── XMPP server ─────────────────────────────────────────────────
# Internal Erlang cluster cookie — any random string, keep secret.
# Used by ejabberd nodes to authenticate to each other (irrelevant
# for single-node deployment, but required by ejabberd to start).
EJABBERD_COOKIE=change_me_in_production

# ── Machine 0 — fischertechnik crane (Case 0, original) ─────────
# AAS_FILE: filename inside my_models/aas/ (no path, no leading slash)
# AAS_ID:   the 'id' attribute of the AAS shell SMIA should self-configure from
# AGENT_ID: full XMPP JID (must match the account registered in ejabberd CTL_ON_CREATE)
# PASSWD:   XMPP account password (must match CTL_ON_CREATE registration)
MACHINE0_AAS_FILE=LEGO_factory_case0.aasx
MACHINE0_AAS_ID=urn:uuid:6475_0111_2062_9689
MACHINE0_AGENT_ID=SMIA_agent@ejabberd
MACHINE0_PASSWD=change_me

# ── Machine 1 ────────────────────────────────────────────────────
MACHINE1_AAS_FILE=LEGO_machine1_case0.aasx
MACHINE1_AAS_ID=urn:uuid:6475_0111_2062_0001
MACHINE1_AGENT_ID=smia_machine1@ejabberd
MACHINE1_PASSWD=change_me

# ── Machine 2 ────────────────────────────────────────────────────
MACHINE2_AAS_FILE=LEGO_machine2_case0.aasx
MACHINE2_AAS_ID=urn:uuid:6475_0111_2062_0002
MACHINE2_AGENT_ID=smia_machine2@ejabberd
MACHINE2_PASSWD=change_me

# ── Orchestrator ─────────────────────────────────────────────────
ORCH_AAS_FILE=SMIA_orchestrator.aasx
ORCH_AAS_ID=urn:uuid:8888_0001_2026_0001
ORCH_AGENT_ID=smia_orch@ejabberd
ORCH_PASSWD=change_me

# ── Operator GUI ─────────────────────────────────────────────────
# The operator agent's own AASX (scanned by the GUI at startup)
OPERATOR_AAS_FILE=SMIA_Operator_article.aasx
OPERATOR_AGENT_ID=operator001@ejabberd
OPERATOR_PASSWD=change_me

# ── Node-RED ──────────────────────────────────────────────────────
# Internal Docker service URL — do not change unless you rename the
# 'nodered' service in docker-compose.yml.
# Docker DNS resolves 'nodered' to the Node-RED container on smia-net.
NODERED_URL=http://nodered:1880
# Credential encryption key for Node-RED (any random string).
# Keep consistent across restarts — changing it invalidates stored
# Node-RED credentials (e.g., MQTT broker credentials in the flow).
NODERED_CREDENTIAL_SECRET=change_me_in_production

# ── MQTT Bridge (informational only) ─────────────────────────────
# The actual bridge target is configured in:
#   my_models/mosquitto/conf.d/bridge.conf  (edit the 'address' line)
# These variables document the intended target for reference only.
# They are NOT read by any container or Python code.
MACHINE_MQTT_HOST=192.168.155.10
MACHINE_MQTT_PORT=1883
```

**How variables reach containers:** Docker Compose reads `.env` from the directory where `docker-compose.yml` lives (i.e., `my_models/`). Variables are referenced in `docker-compose.yml` as `${VAR_NAME}`. Each service's `environment:` block maps variables to the container:

```yaml
# In docker-compose.yml, smia-machine0 service:
environment:
  - AAS_MODEL_NAME=${MACHINE0_AAS_FILE}    # read by smia_machine_starter.py
  - AAS_ID=${MACHINE0_AAS_ID}              # filters which AAS shell to self-configure
  - AGENT_ID=${MACHINE0_AGENT_ID}          # XMPP JID
  - AGENT_PASSWD=${MACHINE0_PASSWD}        # XMPP password
  - NODERED_URL=${NODERED_URL}             # read by smia_machine_agent_services.py
```

`smia_machine_agent_services.py` reads it:
```python
NODE_RED_BASE = os.environ.get('NODERED_URL', 'http://nodered:1880')
```
The fallback default (`'http://nodered:1880'`) ensures the code works even without the env var — useful for local testing inside the Docker network.

### 15.5 XMPP Account Auto-Registration

The `xmpp-server` service uses `CTL_ON_CREATE` to auto-register all agent accounts on first container creation:

```yaml
CTL_ON_CREATE=! register SMIA_agent ejabberd ${MACHINE0_PASSWD} ;
               register smia_machine1 ejabberd ${MACHINE1_PASSWD} ;
               register smia_machine2 ejabberd ${MACHINE2_PASSWD} ;
               register smia_orch ejabberd ${ORCH_PASSWD} ;
               register operator001 ejabberd ${OPERATOR_PASSWD}
```

This runs **only on first creation** (not on restart). If you change passwords, run `docker compose down -v` (wipes the ejabberd database volume) then `docker compose up -d` to re-register with new passwords.

### 15.6 Shared AAS Volume

All containers mount the same folder as a read-only volume:
```yaml
volumes:
  - ./aas:/smia_archive/config/aas
```

This is what allows the orchestrator to read all machine AASXs for discovery, and the operator GUI to scan all AASXs to display available SMIAs. It is also what makes adding a new machine require only dropping a file — no container restart needed for the operator GUI to discover it (it rescans on page reload). Machine containers and orchestrator read their own AASX from this volume at startup.

---

## 16. Configuration Files

### 16.1 `.env` File

Created from `.env.example`. Never committed to git (listed in `.gitignore`). Contains all passwords and per-machine configuration. See `.env.example` for the full template with comments.

### 16.2 `ejabberd.yml`

Updated for Case 1 to include 5 XMPP domains (one per agent). The XMPP domain used is `ejabberd` (the Docker container hostname). All accounts use the format `username@ejabberd`. See Case 0 doc §10.2 for the full ejabberd configuration reference.

### 16.3 `mosquitto.conf` and `bridge.conf`

**`mosquitto/mosquitto.conf`:** Basic Mosquitto broker configuration. Enables anonymous connections (no authentication) on port 1883. Persistence is enabled (`persistence_location /mosquitto/data/`) — messages are written to the `mosquitto_data` Docker volume and survive container restarts. Logs go to stdout so `docker compose logs mosquitto-central` shows them. Includes the `conf.d/` directory so bridge configuration is managed separately in `bridge.conf`.

**`mosquitto/conf.d/bridge.conf`:** Configures the MQTT bridge from the containerized Mosquitto broker to the physical machine's MQTT broker. Full content:

```conf
# ================================================================
# MQTT Bridge — SMIA to physical machine MQTT broker
# ================================================================
#
# MANUAL SETUP REQUIRED (one-time per lab/deployment):
#   Edit the 'address' line below to the IP:port of the MQTT broker
#   running on or near the physical machine (fischertechnik crane).
#   This is the ONLY host-specific line in the entire deployment.
#
# All other configuration (topics, QoS, etc.) is pre-configured
# and does not need to change between deployments.
# ================================================================

connection bridge-to-machine
address 192.168.155.10:1883       # ← SET THIS to the machine broker IP:port

bridge_protocol_version mqttv311
cleansession true
start_type automatic

# Forward crane command topics from this broker to the machine broker (out)
# Receive status/telemetry topics from the machine broker (in)
topic vicom/61/piso_0/lab/lego/# out 1
topic vicom/61/piso_0/lab/lego/# in 0
```

**Field-by-field explanation:**

| Field | Value | Meaning |
|---|---|---|
| `connection` | `bridge-to-machine` | Logical name for this bridge connection (for Mosquitto logs) |
| `address` | `192.168.155.10:1883` | IP:port of the remote broker (DIDA Central or fischertechnik machine). **Edit this line per lab.** |
| `bridge_protocol_version` | `mqttv311` | Use MQTT 3.1.1 (compatible with all common brokers) |
| `cleansession` | `true` | Do not persist subscriptions across broker restarts |
| `start_type` | `automatic` | Bridge starts when Mosquitto starts (no manual trigger) |
| `topic ... out 1` | `vicom/61/piso_0/lab/lego/# out 1` | Forward matching topics FROM this broker TO the remote (outbound); QoS 1 (at least once delivery) |
| `topic ... in 0` | `vicom/61/piso_0/lab/lego/# in 0` | Receive matching topics FROM the remote TO this broker (inbound); QoS 0 (fire and forget) |

**Topic wildcard (`#`):** Matches everything under `vicom/61/piso_0/lab/lego/`. The only outbound topic used in practice is `vicom/61/piso_0/lab/lego/commands`, which carries the `bandera_custom:<position>` crane command. The `in` subscription brings back any telemetry the machine publishes on the same prefix.

**QoS asymmetry:** Commands are `out 1` (at-least-once) to ensure the crane command is not silently dropped if the bridge connection is momentarily interrupted. Telemetry is `in 0` (fire-and-forget) because re-reading a stale status value is not harmful.

**Before deployment:** Edit `bridge.conf` to replace `192.168.155.10:1883` with the IP of the MQTT broker visible to the Docker host. This is the **only host-specific configuration** in the entire stack. Everything else uses Docker DNS names.

### 16.4 `nodered/flows.json`

The flow file (`my_models/nodered/flows.json`) is loaded by the `nodered` container on startup via the `FLOWS=flows.json` environment variable. It defines three HTTP endpoints that together implement the HTTP→MQTT bridge and the FIPA-CNP availability signal.

#### Flow 1 — POST `/smia/lego/pick`

Node-RED node structure:

```
[HTTP In: POST /smia/lego/pick]
        │
        ▼
[Function: pick_handler]
        │
        ├──────────────────────────────────────────────┐
        ▼                                              ▼
[MQTT Out: mosquitto-central:1883              [HTTP Response: 200 JSON]
           topic: vicom/61/piso_0/lab/lego/commands
           QoS: 1]
```

The `pick_handler` function node (JavaScript):

```javascript
var DEFAULT_POSITION = 0;
var body  = msg.payload || {};
var query = msg.req.query || {};

// Position resolution — three-level fallback:
// 1. body.position  → set by SMIA when skillParams contains position (orchestrator path)
// 2. query.position → encoded in AID href URL (?position=N) for machines 1 and 2
// 3. DEFAULT_POSITION → always 0 (machine0 / red / slot 0)
var posRaw = body.position;
if (posRaw === undefined) posRaw = query.position;
if (posRaw === undefined) posRaw = DEFAULT_POSITION;

var position = parseInt(posRaw, 10);
if (isNaN(position) || position < 0 || position > 8) {
    msg.payload = { error: "invalid position", received: posRaw };
    msg.statusCode = 400;
    return msg;
}

// Signal that the machine is busy (read by GET /smia/lego/availability)
global.set("machine_busy", true);

// MQTT payload format expected by fischertechnik control software
msg.payload = "bandera_custom:" + position;
msg.topic   = "vicom/61/piso_0/lab/lego/commands";

// After MQTT Out publishes, the wire continues to HTTP Response
// Clear busy flag and build response body
global.set("machine_busy", false);
msg.payload = { status: "ok", payload: "bandera_custom:" + position, position: position };
return msg;
```

**The three-level position fallback is the critical design.** SMIA sends an empty POST body when `Skill_PickPiece` has no `hasParameter` (see §13.5). The URL query parameter (`?position=N`) in the AID `href` carries the position for machines 1 and 2. Machine 0's href has no `?position` — it falls back to `DEFAULT_POSITION = 0`. This means the position encoding is AID-model-driven, not agent-code-driven.

#### Flow 2 — GET `/smia/lego/availability`

```
[HTTP In: GET /smia/lego/availability]
        │
        ▼
[Function: availability_handler]
        │
        ▼
[HTTP Response: 200 plain text]
```

The `availability_handler` function node:

```javascript
var busy = global.get("machine_busy") || false;
msg.payload = busy ? "0.0" : "1.0";
msg.headers = { "Content-Type": "text/plain" };
return msg;
```

Returns `"1.0"` (free) or `"0.0"` (busy) as **plain text** — not JSON — so `get_machine_availability()` can call `float(text.strip())` without any JSON parsing. The Node-RED global variable `machine_busy` is the shared state between the pick flow and the availability flow. This is a deliberate design: availability is not an independently-queried property; it directly reflects whether the pick flow is currently active.

**Concurrency note:** Node-RED runs a single-threaded Node.js event loop. `global.set` / `global.get` are synchronous — no race condition is possible between the pick handler setting the flag and the availability handler reading it.

#### Flow 3 — POST `/smia/lego/place`

Same structure as the pick flow. Uses a different MQTT payload format or topic segment appropriate for the place operation on the fischertechnik machine.

#### MQTT broker target inside the flow

The MQTT Out node is configured with `broker: mosquitto-central`, `port: 1883`. Docker DNS resolves `mosquitto-central` to the `mosquitto-central` container on the `smia-net` bridge network — no IP address is hardcoded in the flow file. `mosquitto-central` then bridges commands to the physical machine's broker via the `bridge.conf` MQTT bridge (§16.3).

---

## 17. Deployment and Test Procedure

### 17.1 Prerequisites

- Docker Desktop or Docker Engine with Compose v2 plugin installed.
- Network access to the fischertechnik Windows machine (for MQTT bridge).
- The fischertechnik machine's MQTT broker must be running and subscribed to `vicom/61/piso_0/lab/lego/commands`.
- Files: `LEGO_factory_case0.aasx`, `LEGO_machine1_case0.aasx`, `LEGO_machine2_case0.aasx`, `SMIA_orchestrator.aasx`, `SMIA_Operator_article.aasx` all present in `my_models/aas/`. **Only `.aasx` files — no other file types.**

### 17.2 First-Time Setup

```bash
cd /path/to/SMIA

# 1. Configure environment
cp my_models/.env.example my_models/.env
# Edit my_models/.env — set all *_PASSWD values and EJABBERD_COOKIE

# 2. Configure MQTT bridge
# Edit my_models/mosquitto/conf.d/bridge.conf
# Set: address <fischertechnik_machine_ip>:1883

# 3. Build custom Docker images (required after any Python file change)
docker compose -f my_models/docker-compose.yml build

# 4. Start all services
docker compose -f my_models/docker-compose.yml up -d
```

### 17.3 Verification

```bash
# Check all services are running
docker compose -f my_models/docker-compose.yml ps

# Watch machine and orchestrator logs
docker compose -f my_models/docker-compose.yml logs -f smia-machine0 smia-orchestrator

# Expected in machine0 logs (after ~20-30s):
# "AAS model analysis results"
# "Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']"
# "Analyzed skills: ['Skill_PickPiece', 'Skill_PlacePiece', 'Skill_NegAvailability']"
# "Analyzed skill interfaces: ['machineAvailValue', 'pickPiece', 'placePiece']"
# "AAS model initialized."
# "ACLHandlingBehaviour starting..."
# "NegotiationBehaviour starting..."
```

### 17.4 Running Case 0 (Single Machine, Direct)

1. Open browser: `http://localhost:10000/smia_operator`
2. Click **"Load SMIA list"** — should show available agents.
3. Select `SMIA_agent@ejabberd` (machine0).
4. Select `Capability_PickPiece`.
5. Select `Skill_PickPiece`.
6. No parameter input field appears — machine AASXs define no `hasParameter` for `Skill_PickPiece`. The GUI sends empty `skillParams`. Node-RED uses `DEFAULT_POSITION = 0`.
7. Click **Send**. The operator GUI should show an INFORM response and the crane should move to slot 0.

### 17.5 Running Case 1 (Orchestrated, Multi-Machine)

1. Open browser: `http://localhost:10000/smia_operator`
2. Select `smia_orch@ejabberd` (orchestrator).
3. Select `Capability_PickPiece`.
4. Select `Skill_Orchestrate_PickPiece`.
5. Enter color value (`red`, `blue`, or `white`).
6. Click **Send**.

Expected behavior:
- The orchestrator discovers the matching machine (e.g., `SMIA_agent@ejabberd` for `red`).
- CFP is sent; machine wins immediately (1 target → no PROPOSE exchange needed).
- Orchestrator sends REQUEST to winner with `{position: "0"}`.
- Machine executes HTTP POST to Node-RED; crane moves.
- INFORM propagates back: machine → orchestrator → operator.
- GUI shows: `"INFORM received"` with the HTTP response body.

### 17.6 Common Operations

```bash
# Stop all services (keep data volumes)
docker compose -f my_models/docker-compose.yml down

# Full reset (wipe ejabberd DB — forces XMPP account re-registration on next up)
docker compose -f my_models/docker-compose.yml down -v

# Rebuild images after Python code changes
docker compose -f my_models/docker-compose.yml build smia-machine0 smia-orchestrator

# Start a single service
docker compose -f my_models/docker-compose.yml up -d smia-machine0

# Check Node-RED availability endpoint manually
curl http://localhost:1880/smia/lego/availability
# Expected: "1.0" (machine free) or "0.0" (machine busy)
```

---

## 18. Known Issues and Patches Applied

### 18.1 Patch 1 — `smia_agent.py`: Asset Connection Object-Identity Bug

**Symptom:** `HandleCapabilityBehaviour` and `HandleNegotiationBehaviour` return `None` when trying to retrieve the `HTTPAssetConnection` object, causing a crash during skill execution.

**Root cause:** SMIA stores asset connections in a dict keyed by `ModelReference` objects. When looking them up, it creates a new `ModelReference` for the same AAS element and uses it as a key. Since `ModelReference` objects in BaSyx Python SDK do not implement `__hash__` and `__eq__` based on content (they use Python's default object identity), two distinct `ModelReference` objects pointing to the same element are not considered equal. The dict lookup always misses.

**Fix applied:** `src/smia/agents/smia_agent.py` — modified the asset connection retrieval to compare by resolving the reference and checking the resulting element object, not the reference itself.

**Where applied:** Both `smia-machine` and `smia-orchestrator` Dockerfiles copy and apply this patch.

### 18.2 Patch 2 — `acl_handling_behaviour.py`: Orchestrator Race Condition

**Symptom:** When the operator sends a `css-service REQUEST` to the orchestrator, both `OrchestratorDispatchBehaviour` and `ACLHandlingBehaviour` attempt to handle the same message. `ACLHandlingBehaviour` spawns a `HandleCapabilityBehaviour` that crashes trying to execute `Skill_Orchestrate_PickPiece` as a physical skill (it has no AID interface), while `OrchestratorDispatchBehaviour` correctly handles it as a dispatch request.

**Root cause:** SPADE delivers messages to all registered behaviours simultaneously (broadcast delivery). `ACLHandlingBehaviour` checks `msg.thread not in self.agent.reserved_threads` before spawning, but `OrchestratorDispatchBehaviour` reserves the thread inside `_start_negotiation()`, which runs *after* the `await self.receive()` completes. `ACLHandlingBehaviour` can process the message in the same event loop iteration before the thread is reserved.

**Fix applied:** `src/smia/behaviours/acl_handling_behaviour.py` — added an early-return check:
```python
if (msg.get_metadata('ontology') == 'css-service'
        and msg.get_metadata('performative') == 'request'
        and hasattr(self.myagent, 'pending_orchestrations')):
    return   # OrchestratorDispatchBehaviour handles css-service REQUESTs
```
The attribute `pending_orchestrations` is set on the agent object by `OrchestratorDispatchBehaviour.on_start()`, making it a reliable signal that the agent is running in orchestrator mode. It is absent in plain machine agents, so this patch has no effect on them.

**Where applied:** `smia-orchestrator` Dockerfile only.

### 18.3 Patch 3 — `operator_gui_logic.py`: SkillParameter Processing Bugs

**Symptom:** When the orchestrator AASX defines a `hasParameter` relationship (required for the operator GUI to show the `color` input field), loading the SMIAs in the operator GUI fails. The GUI shows `SyntaxError: Unexpected non-whitespace character after JSON at position 4`. The real error in the `smia-operator` container logs is:

```
TypeError: unhashable type: 'list'
  File "operator_gui_logic.py", line 129, in analyze_aas_model_store
    param_set.add(skill_param)   ← skill_param is a list, sets require hashable elements
```

**Root cause:** Three latent bugs in the `hasParameter` processing block of `operator_gui_logic.py`, never triggered in any standard SMIA AASX (none uses `hasParameter` relationships by default):

| Bug | Location | Error |
|---|---|---|
| Bug 1 | `if skill not in css_elems_info['skillData']` | `KeyError` — this key never exists in `css_elems_info`; correct dict is `self.myagent.skills_info` |
| Bug 2 | `param_set.add(skill_param)` | `TypeError: unhashable type: 'list'` — `aas_elems` values are always lists (same structure as `isRealizedBy`); cannot add a list to a set |
| Bug 3 | Storing `skill_param` (an AAS object) instead of `skill_param.id_short` | `SyntaxError` later when `eval(skill_params)` is called — AAS object representations like `ExtendedSkillParameter[https://...]` are not valid Python syntax |

**Fix applied:** `additional_tools/extended_agents/smia_operator_agent/operator_gui_logic.py` — replaced the entire `hasParameter` block:

```python
# BEFORE (3 bugs):
if CapabilitySkillOntologyInfo.CSS_ONTOLOGY_PROP_HASPARAMETER_IRI == rel.iri:
    for skill, skill_param in aas_elems.items():
        if skill not in css_elems_info['skillData']:  # Bug 1: KeyError
            param_set = set()
            param_set.add(skill_param)               # Bug 2: TypeError (list not hashable)
            self.myagent.skills_info[skill] = param_set
        else:
            self.myagent.skills_info[skill].add(skill_param)  # Bug 3: AAS object, not id_short

# AFTER (all 3 fixed):
if CapabilitySkillOntologyInfo.CSS_ONTOLOGY_PROP_HASPARAMETER_IRI == rel.iri:
    for skill, skill_params_list in aas_elems.items():
        if skill not in self.myagent.skills_info:    # correct dict
            self.myagent.skills_info[skill] = set()
        self.myagent.skills_info[skill].update(      # handles list, stores id_short strings
            p.id_short for p in skill_params_list)
```

**Where applied:** The file is modified in place. The `smia-operator` Dockerfile (inside `additional_tools/extended_agents/smia_operator_agent/`) copies all files from that directory, so the fix is automatically included when the operator image is rebuilt.

**Upstream status:** Latent upstream bug. The fix has been documented; a PR to the SMIA upstream repo is pending.

---

### 18.4 `OrchestratorDispatchBehaviour.run()`: Thread Reservation Before `await`

Not a bug in the upstream code but a design requirement that must be maintained in any future modifications: `await self.agent.add_reserved_thread(thread)` must be called **before** the first `await` that suspends execution inside `_start_negotiation()`. Any `await` suspends the coroutine and allows other SPADE behaviours to run, including `ACLHandlingBehaviour` checking `reserved_threads`. The thread must be reserved atomically (before the first suspension) to prevent the race.

---

## 19. Troubleshooting

### 19.1 Operator GUI shows 0 capabilities / 0 skills for a machine

**Check 1 — `isRealizedBy` IRI casing.** All `RelationshipElement.semanticId` values in the AASX must be exactly `http://www.w3id.org/hsu-aut/css#isRealizedBy` (all lowercase). Open the AASX in AASX Package Explorer and verify each RelationshipElement.

**Check 2 — Skill element type.** Skills must be `Property` elements, not `SubmodelElementCollection`. An SMC skill causes an MRO conflict in SMIA's class extension system and silently fails to register.

**Check 3 — AAS volume.** Verify that the `my_models/aas/` folder contains only `.aasx` files. Any other file type causes the operator GUI scanner to fail on that file and possibly crash (HTTP 500).

### 19.2 Machine logs show "Errors found: ['Skill_NegAvailability']"

**Cause:** The `SkillImplementationType` qualifier on `Skill_NegAvailability` is missing its `semanticId` (`http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`).

**Fix:** Open the machine AASX in AASX Package Explorer → `CapabilitiesAndSkills` → `Skill_NegAvailability` → Qualifier → set semanticId to the IRI above. Save and redeploy.

### 19.3 Negotiation hangs — machine never sends INFORM

**Check 1 — `accessibleThroughAgentService` IRI casing.** The RelationshipElement linking `Skill_NegAvailability` to `machineAvailValue` must have exactly `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` (all lowercase) as its semanticId.

**Check 2 — Agent service registration.** The machine starter must register `'machineAvailValue'` (matching the `id_short` exactly). Verify in `smia_machine_starter.py` and confirm the log line `"Machine SMIA: registered 'machineAvailValue' agent service."`.

**Check 3 — Node-RED availability endpoint.** `curl http://localhost:1880/smia/lego/availability` should return `1.0`. If Node-RED is not running or the flow is not imported, the machine returns `0.0` and the negotiation value is 0.

### 19.4 `docker-compose` crashes with `KeyError: 'ContainerConfig'`

Use `docker compose` (v2, space) instead of `docker-compose` (v1, hyphen). Docker Compose v1 is incompatible with current Docker image metadata.

### 19.5 Orchestrator sends CFP but receives no INFORM

**Check 1 — `negCriterion` IRI.** The CFP body includes `negCriterion: "http://www.w3id.org/hsu-aut/css#Skill_NegAvailability"`. This must exactly match the IRI of the `Skill_NegAvailability` OWL instance created during the machine's self-configuration. The instance is named by `id_short`, and the IRI is assembled as `css_namespace + id_short`. Check the machine logs for the analyzed skills list.

**Check 2 — Machine capability checking.** `HandleNegotiationBehaviour.on_start()` performs capability checking before the negotiation value computation. If the machine's CSS ontology does not contain `Capability_PickPiece`, capability checking fails and the machine sends `REFUSE`. Check machine logs for `"capability checking failed"`.

**Check 3 — `NegotiatingBehaviour` receiving CFPs.** CFPs arrive with `ontology=css-service` (not `Negotiation`). `NegotiatingBehaviour` must be configured to receive this ontology. Check the `ACLSMIAJSONSchemas.JSON_SCHEMA_ACL_SMIA_ONTOLOGIES_MAP` in `fipa_acl_info.py` to confirm `css-service` is included.

### 19.6 `smia-orchestrator` logs show "No AAS folder found"

The orchestrator container scans `/smia_archive/config/aas`. This path must be mounted via the Docker volume:
```yaml
volumes:
  - ./aas:/smia_archive/config/aas
```
Verify this line is present in the `smia-orchestrator` service in `docker-compose.yml`.

### 19.7 Orchestrator logs show dozens of `[ERROR]` lines during each request — is something broken?

**This is normal and expected.** Every time the orchestrator scans the AAS folder (on each operator request), BaSyx Python SDK parses all 5 AASX files, including `SMIA_Operator_article.aasx` (the upstream operator AASX) and some ConceptDescription entries. These generate two categories of benign errors:

**Category A — `AASConstraintViolation: The id_short must contain only letters, digits and underscore`**
Cause: `SMIA_Operator_article.aasx` (the upstream operator AASX, not our file) contains elements with hyphens in their `id_short` values (e.g., `RAM-memory-property`). The AAS metamodel spec (Constraint AASd-002) prohibits hyphens. BaSyx logs each invalid element as an ERROR but continues loading the rest of the file. These elements are not needed by the orchestrator — it only reads `SoftwareNameplate` and `Capability_PickPiece` from each AASX.

**Category B — `ConceptDescription[...] has a duplicate identifier already parsed in the document!`**
Cause: Multiple AASXs embed the same CSS ontology `ConceptDescription` entries (since each AASX is self-contained). When BaSyx parses all 5 AASXs into the same `DictObjectStore`, it sees the same IRI twice and logs a warning. This has no functional impact.

**Category C — `KeyError: {https://...}contentType on line N has no text!`**
Cause: Some AAS `File` elements in `SMIA_Operator_article.aasx` are missing a required `contentType` attribute. BaSyx logs the error and skips those elements. The orchestrator does not use `File` elements.

**In all cases:** after these errors, you will see `[INFO] Eligible machine: ... (color=...) from ...aasx` — the orchestrator successfully extracted what it needed. As long as this line appears and the negotiation proceeds, the errors are harmless. The source is upstream AASX authoring in files you do not control.

---

## 20. Replication Checklist

Use this checklist to reproduce the Case 1 deployment from scratch on a new machine.

**Repository:**
- [ ] Clone the SMIA repository
- [ ] Verify `my_models/aas/` contains exactly 5 `.aasx` files and no other file types
- [ ] Copy `.env.example` → `.env` and fill in all credentials

**AASX verification (each machine AASX):**
- [ ] `CapabilitiesAndSkills` → `Skill_NegAvailability` is a `Property` (not SMC)
- [ ] `Skill_NegAvailability` qualifier `SkillImplementationType` has semanticId `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`
- [ ] `SemanticRelationships` → `rel_SkillNegAvail_agentSvc` semanticId is `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` (all lowercase)
- [ ] `SemanticRelationships` → `rel_SkillPick_hasSkillInterface` semanticId is `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` (all lowercase)
- [ ] `SemanticRelationships` → `rel_CapPick_isRealizedBySkill_SkillPick` semanticId is `http://www.w3id.org/hsu-aut/css#isRealizedBy` (all lowercase)
- [ ] `SoftwareNameplate` → `InstanceName` has the correct XMPP JID for this machine
- [ ] `Capability_PickPiece` → `color` property has the correct value (`red`/`blue`/`white`)
- [ ] `AssetInterfacesDescription` → `base` = `http://nodered:1880` (Docker DNS, not IP)

**AASX verification (orchestrator AASX):**
- [ ] `Capability_PickPiece` has semanticId `css-smia#AgentCapability` (not `AssetCapability`)
- [ ] `SoftwareNameplate` → `InstanceName` = `smia_orch@ejabberd`

**Network configuration:**
- [ ] `my_models/mosquitto/conf.d/bridge.conf` — `address` set to fischertechnik machine IP

**Docker:**
- [ ] `docker compose build` completes without errors
- [ ] `docker compose up -d` — all 8 services reach `running` state
- [ ] `docker compose logs xmpp-server` — shows `ejabberd running`
- [ ] `docker compose logs smia-machine0` — shows `AAS model initialized` and `NegotiationBehaviour starting`
- [ ] `docker compose logs smia-orchestrator` — shows `OrchestratorDispatchBehaviour started and ready`

**Functional test:**
- [ ] `http://localhost:10000/smia_operator` — GUI loads
- [ ] "Load SMIA list" — shows `smia_orch@ejabberd` and machine agents
- [ ] Case 0 flow (direct to `SMIA_agent@ejabberd`) — works
- [ ] Case 1 flow (via `smia_orch@ejabberd`, color=`red`) — INFORM received, crane moves
- [ ] `curl http://localhost:1880/smia/lego/availability` — returns `1.0`
