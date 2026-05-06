# CLAUDE.md — Full Project Context for SMIA TFG (Case 0 + Case 1)

> This file gives Claude (or any AI assistant) the complete picture of what this project is,
> what has been implemented, what works, what is patched, and how to help with it.
> Read this before anything else.
>
> **Primary scientific source:** E. Hurtado et al., *"Self-configurable Manufacturing Industrial
> Agents (SMIA): a standardized approach for digitizing manufacturing assets"*, Journal of
> Industrial Information Integration 47 (2025) 100915. DOI: 10.1016/j.jii.2025.100915

---

## 1. Project Overview

**What:** Bachelor's thesis (TFG — Trabajo de Fin de Grado) at **Universidad de Deusto**.
**Title:** "Flexible manufacturing based on digital twins using AAS and CSS model"
**Author:** Andrés Felipe Fierro Fonseca — intern at **Vicomtech**, department: **Data Intelligence for Industry (DII)**.
**SMIA framework:** Developed by UPV/EHU (Ekaitz Hurtado et al.) — this TFG uses their framework and extends it.

### Implementation status
| Case | Description | Status |
|---|---|---|
| **Case 0** | Single machine, direct operator → SMIA → crane | **Working end-to-end** |
| **Case 1** | 6 machines + orchestrator, FIPA-CNP multi-agent negotiation | **Implemented, E2E testing** |
| Case 2 | CapabilityConstraints matching | Not implemented |
| Case 3 | SMIA-HI (human interface agent) | Not implemented |

**What we are proving:**
- Case 0 validates R2 (automated self-configuration) and R7 (separation of physical asset and Digital Twin): a SMIA agent configures itself entirely from a standard AAS and executes physical actions with zero asset-specific code inside the agent.
- Case 1 validates R6 (P2P communication and negotiation via FIPA-ACL): multiple SMIA agents discover each other, negotiate task assignment via FIPA-CNP, and execute collaboratively — all driven by the AAS model, without hardcoded logic.

---

## 2. What is SMIA

**SMIA** = Self-configurable Manufacturing Industrial Agents.
- Open-source Python framework: `https://github.com/ekhurtado/SMIA`
- Docker image: `ekhurtado/smia:latest-alpine`
- Authors: Ekaitz Hurtado, Arantzazu Burgos, Aintzane Armentia, Oskar Casquero — UPV/EHU
- Papers: DOI 10.1016/j.jii.2025.100915 (JIII) · DOI 10.1016/j.simpa.2025.100807 (Software Impacts)

### 2.1 Dual-layer architecture (paper §3)

SMIA is a **dual-layer solution**:
1. **Methodology layer** — a process for characterizing proactive AAS (Type 3) by semantically enriching their descriptions with the CSS ontology via `semanticId` fields
2. **Technology layer** — a software toolchain that automatically generates executable Digital Twins as FIPA-compliant industrial agents using SPADE, from those enriched AAS descriptions

Key distinction: **"The AAS is treated as a static, administrative model, while the DT represents its dynamic, operational counterpart"** (paper §3). SMIA agents are not wrappers — they are functional DTs that interpret standardized descriptions.

### 2.2 Design requirements (paper Table 1)

| # | Requirement | Case |
|---|---|---|
| R1 | Compliance with industry integration models (AAS, CSS) | 0 + 1 |
| R2 | Automated self-configuration of Digital Twins | 0 + 1 |
| R3 | Integration of physical assets via standard interfaces (AID) | 0 + 1 |
| R4 | Adaptability to flexible/reconfigurable architectures | 0 + 1 |
| R5 | Inclusion in distributed and decentralized systems | 0 + 1 |
| R6 | P2P communication with I4.0-compliant language (FIPA-ACL) | **1** |
| R7 | Separation between physical asset and Digital Twin | 0 + 1 |
| R8 | Modular and extensible software design | 0 + 1 |

### 2.3 AAS Types — why SMIA implements Type 3

| Type | Interaction | Description |
|---|---|---|
| Type 1 | Passive | File exchange — AASX/XML/JSON read by external applications |
| Type 2 | Reactive | Responds to REST/API service requests from external systems |
| **Type 3** | **Proactive** | **Peer-to-peer I4.0 communication, FIPA-ACL, autonomous behaviour** ← SMIA |

### 2.4 FSM States (paper Fig. 5) — 4 states

```
[Switched off]
    │ switch on
    ▼
┌─────────────────────────────────────┐
│  BOOTING                            │  ← self-configuration happens here
│  - Boot behavior (init SPADE)       │
│  - AAS model init behavior          │
│    (load AASX + OWL + AID,          │
│     instantiate CSS OWL classes,    │
│     link relationships)             │
└──────────────┬──────────────────────┘
               │ booted
               ▼
┌────────────────────────────────────────────────────────────┐
│  RUNNING                                                   │
│  - ACLHandlingBehaviour (CyclicBehaviour)                  │
│  - NegotiatingBehaviour (CyclicBehaviour)                  │
│  - HandleCapabilityBehaviour (OneShotBehaviour per req)    │
│  - HandleNegotiationBehaviour (OneShotBehaviour per CFP)   │
└──────────────┬──────────────────────┬──────────────────────┘
               │ non-operational      │ stopping request
               │ asset                │
               ▼                      ▼
         [IDLE state]           [STOPPING state]
```

### 2.5 Self-configuration process — 3 parallel tracks during Booting

All executed by `AASInitializationBehaviour` (`init_aas_model_behaviour.py`):

**Track 1 — Asset interfaces (AID submodel):**
```
Read AssetInterfacesDescription submodel (BaSyx SDK)
    → Extract Interface SubmodelElements
    → Create AssetConnection instance for each interface
```

**Track 2 — CSS-enriched AAS elements:**
```
Loop for each CSS class IRI (Capability, AssetCapability, AgentCapability, Skill, SkillInterface...):
    Get AAS SubmodelElements by semanticId (BaSyx SDK)
    Validate element against CSS ontology (OWLready2)
    If valid → Create CSS OWL ontology instance
    Then: read all owl:DatatypeProperty IRIs in the instance's class domain
          call get_qualifier_value_by_semantic_id(iri) for each → populate OWL attributes
```

**Track 3 — CSS relationships:**
```
Loop for CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS (exact lowercase match!):
    Get AAS RelationshipElements by semanticId (BaSyx SDK)
    Validate against CSS ontology (OWLready2)
    If valid → Link CSS OWL instances together (OWLready2)
```

Result: an executable semantic network of Capabilities, Skills, SkillInterfaces, and AssetConnections.

**CRITICAL IRI PRECISION:** Track 3 uses a fixed list of lowercase IRIs for matching:
- `http://www.w3id.org/hsu-aut/css#isRealizedBy`
- `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService`  ← all lowercase
- `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService`  ← all lowercase

Any capital letter in an AASX RelationshipElement semanticId causes a silent skip — the OWL link is never created — causing crashes later at negotiation time.

### 2.6 Capability request handling (paper Fig. 9)

When a FIPA-ACL `REQUEST` arrives:
1. `ACLHandlingBehaviour` receives it; checks `ontology` field
2. If `ontology = css-service` (new format) or `ontology = CSSRequest` (old format) → spawns `HandleCapabilityBehaviour`
3. Validates capability name + constraints against the CSS OWL ontology
4. If skill not specified → SMIA infers the matching skill via `isRealizedBy`
5. If skill interface not specified → SMIA gets it via `accessibleThrough*`
6. Determines executor: **asset service** → HTTP via AssetConnection; **agent service** → Python method
7. Executes; sends FIPA-ACL `INFORM` with result + execution timeline

### 2.7 FIPA-ACL message formats

**Direct capability request (operator → machine, or orchestrator → winner):**
```
performative: request
ontology:     css-service     ← new format (SMIA ≥ 0.2.4)
body:         {"capabilityIRI": "http://...css-smia#AssetCapability",
               "skillIRI":      "...",
               "skillParams":   {"http://www.w3id.org/hsu-aut/css#color": "red"}}
```

**Negotiation CFP (orchestrator → machines):**
```
performative: cfp
protocol:     fipa-contract-net
ontology:     Negotiation
body:         {"capabilityIRI": "...",
               "negCriterion":  "http://www.w3id.org/upv-ehu/gcis/css-smia#Skill_NegAvailability",
               "negTargets":    ["smia_machine1@ejabberd", ...],
               "negRequester":  "smia_orch@ejabberd",
               "skillParams":   {"http://www.w3id.org/hsu-aut/css#color": "red"}}
```

### 2.8 ExtensibleSMIAAgent — extensibility hooks (paper Fig. 10)

Three extension hooks:
- `add_new_asset_connection(interface_aas_ref, handler)` — new physical protocols (OPC UA, MQTT)
- `add_new_agent_capability(handler)` — new AgentCapabilities (negotiation, planning)
- `add_new_agent_service(service_id, executable_method)` — new internal Python services

**This TFG uses `add_new_agent_service`** to register `machineAvailValue` on each machine agent:
```python
smia_agent.add_new_agent_service('machineAvailValue', get_machine_availability)
```
The orchestrator uses `add_new_agent_capability` to register `OrchestratorDispatchBehaviour`.

### 2.9 Key dependencies
- `spade 4.0.3` — Python multi-agent framework (XMPP-based)
- `basyx-python-sdk 1.2.1` — AAS model parsing and manipulation
- `owlready2 0.48` — OWL ontology loading and reasoning
- `python 3.12` (inside container)

---

## 3. Physical Setup

**Physical asset:** fischertechnik Training Factory Industry 4.0 24V (ref. 554868)
- **Case 0 scope:** ONLY the **warehouse crane (Hochregallager)** — picks from slot by position (0–8)
- NOT in scope: the central crane with ventuse (vacuum suction cup) — present but not connected

**Naming note:** Files use `LEGO_factory`, `/smia/lego/pick`, `vicom/61/piso_0/lab/lego/commands` — historical artifacts. They physically refer to the fischertechnik factory. Do not rename; they appear in code and running configs.

### Physical machines

| # | Machine | IP | Role |
|---|---|---|---|
| 1 | Linux dev machine (this repo) | localhost | All Docker containers |
| 2 | DIDA Central machine | 192.168.155.10 | Node-RED (port 1880) + Mosquitto (port 1883) |
| 3 | fischertechnik Windows machine | lab network | Receives MQTT, runs warehouse crane control |

---

## 4. System Architecture — Case 0 (Direct Execution)

### End-to-end data flow Case 0

```
[Browser]
    │ HTTP :10000
    ▼
[smia-operator container]  — operator agent, web GUI, scans aas/ for SMIAs
    │ FIPA-ACL REQUEST (ontology=css-service) over XMPP :5222
    ▼
[ejabberd container]  — XMPP routing
    │ routes to smia_machine0@ejabberd (machine0)
    ▼
[smia-machine0 container]  — SMIA machine agent (fischertechnik factory)
    │ 1. Capability_PickPiece → isRealizedBy → Skill_PickPiece
    │ 2. Skill_PickPiece → accessibleThroughAssetService → AID pickPiece action
    │ 3. AID: base=http://nodered:1880, href=/smia/lego/pick, method=POST
    │ HTTP POST {"color":"...", "position":...}
    ▼
[nodered container]  — HTTP→MQTT bridge
    │ extracts position, builds payload "bandera_custom:<n>"
    │ MQTT publish QoS=1  topic=vicom/61/piso_0/lab/lego/commands
    ▼
[mosquitto-central container] → MQTT bridge → [Mosquitto on fischertechnik machine]
    ▼
[Warehouse crane macro — picks from slot <position>]
```

---

## 5. System Architecture — Case 1 (Orchestrated FIPA-CNP)

### Multi-agent negotiation flow

```
[Browser]  → selects smia_orch@ejabberd → Capability_PickPiece → Skill_Orchestrate_PickPiece → color=red
    │ HTTP :10000
    ▼
[smia-operator container]
    │ FIPA-ACL REQUEST (ontology=css-service) to smia_orch@ejabberd
    │ body: {capabilityIRI, skillParams: {"http://...css#color": "red"}}
    ▼

PHASE 1 — Color routing by orchestrator:
[smia-orchestrator container]  ← OrchestratorDispatchBehaviour intercepts (before ACLHandlingBehaviour)
    │ 1. Scans all .aasx files in aas/ folder
    │ 2. Reads each machine's Capability_PickPiece → color property value
    │ 3. Filters: machines where color list contains requested color
    │    (comma-separated: "red,blue" matches both red and blue requests)
    │ 4. Maps color → position: {"red": "0", "blue": "1", "white": "2", ...} (hardcoded)
    │
    │ FIPA-ACL CFP (protocol=fipa-contract-net, ontology=Negotiation)
    │ body: {capabilityIRI, negCriterion=Skill_NegAvailability IRI,
    │        negTargets=[matching machine JIDs], negRequester=smia_orch@ejabberd,
    │        skillParams={color, position}}
    ▼

PHASE 2 — FIPA-CNP negotiation (built-in SMIA, each machine):
[smia-machineN container] — HandleNegotiationBehaviour (built-in SMIA)
    │ 1. Resolves negCriterion IRI → OWL Skill_NegAvailability instance
    │ 2. Gets associated SkillInterface (machineAvailValue) via accessibleThroughAgentService OWL link
    │ 3. Calls agent service 'machineAvailValue'
    │    → async GET http://nodered:1880/smia/lego/availability?machine=<MACHINE_ID>
    │    → Node-RED checks global flag machine_busy_<MACHINE_ID>
    │    → returns 1.0 (free) or 0.0 (busy)
    │ 4. If 1 machine in negTargets: wins immediately
    │    If multiple: sends PROPOSE to peers, compares, highest wins
    │ 5. Winner sends INFORM({winner: True}) to negRequester=orchestrator
    ▼

PHASE 3 — Capability execution (built-in SMIA, winner machine):
[smia-orchestrator] sends REQUEST to winner
[smia-machineN winner] — HandleCapabilityBehaviour
    │ Resolves Skill_PickPiece → AID HTTP action → POST to nodered:1880/smia/lego/pick?machine=<ID>
    │ Node-RED → sets machine_busy_<ID>=true → MQTT → crane moves → clears flag after 8s
    │ INFORM(result) → orchestrator → operator
    ▼

[Browser shows "INFORM received" / crane moved]
```

### Color-to-slot mapping (hardcoded in orchestrator)

| Color | Warehouse slot (position) |
|---|---|
| red | 0 |
| blue | 1 |
| white | 2 |
| yellow | 3 |

This mapping is in `orchestrator_dispatch_behaviour.py` (`_start_negotiation` method). Each machine AASX declares its color via `Capability_PickPiece` → `color` property. Multicolour machines use comma-separated values (e.g., `"red,blue"`).

### Per-machine availability tracking

Node-RED maintains a separate busy flag per machine ID: `machine_busy_<machineId>` (global context). The machine ID (`smia_machine0`, `smia_machine1`, etc.) flows through the system as:
```
AGENT_ID env var → MACHINE_ID = AGENT_ID.split('@')[0]  (in smia_machine_agent_services.py)
  → availability GET: /smia/lego/availability?machine=<MACHINE_ID>
  → pick href in AASX: /smia/lego/pick?machine=<MACHINE_ID>&position=<n>
  → Node-RED: reads query.machine → sets/gets global machine_busy_<machineId>
```
Falls back to `'default'` for legacy AASXs without the `?machine=` parameter.

---

## 6. File Structure (CURRENT — in this SMIA repo)

```
SMIA/                                       ← repo root (ekhurtado/SMIA fork)
│
├── my_models/                              ← TFG deployment workspace (main working folder)
│   ├── CLAUDE.md                           ← this file
│   ├── README.md                           ← professional README for the new standalone repo
│   ├── PATCHES.md                          ← detailed bug documentation for upstream PRs
│   ├── docker-compose.yml                  ← 11 services (CURRENT deployment file)
│   ├── .env                                ← credentials (gitignored; copy from .env.example)
│   ├── .env.example                        ← template with all required variables
│   ├── aas/                                ← ALL AASX files (operator scans this folder)
│   │   ├── LEGO_machine0.aasx              ← machine0 (smia_machine0@ejabberd, red)
│   │   ├── LEGO_machine1.aasx              ← machine1 (smia_machine1@ejabberd, blue)
│   │   ├── LEGO_machine2.aasx              ← machine2 (smia_machine2@ejabberd, white)
│   │   ├── LEGO_machine3.aasx              ← machine3 (smia_machine3@ejabberd, red duplicate)
│   │   ├── LEGO_machine4.aasx              ← machine4 (smia_machine4@ejabberd, blue duplicate)
│   │   ├── LEGO_machine5.aasx              ← machine5 (smia_machine5@ejabberd, multicolour red,blue)
│   │   ├── SMIA_orchestrator.aasx          ← orchestrator (smia_orch@ejabberd)
│   │   └── SMIA_Operator_article.aasx      ← operator agent's own AAS
│   ├── docker/
│   │   ├── smia-machine/Dockerfile         ← OLD machine Dockerfile (build context: repo root SMIA/)
│   │   └── smia-orchestrator/Dockerfile    ← OLD orchestrator Dockerfile (build context: repo root)
│   ├── mosquitto/
│   │   ├── mosquitto.conf
│   │   └── conf.d/bridge.conf              ← SET TARGET IP HERE (fischertechnik machine)
│   ├── nodered/
│   │   └── flows.json                      ← Node-RED flows: HTTP→MQTT + per-machine busy flags
│   ├── ontology/
│   │   └── CSS-ontology-smia.owl
│   ├── xmpp_server/
│   │   └── ejabberd.yml
│   ├── doc_case0.md                        ← full AASX PE tutorial + Case 0 technical reference
│   ├── doc_case1.md                        ← Case 1 multi-agent architecture deep-dive
│   ├── memoire.md                          ← formal TFG academic document (technical deep-dive)
│   ├── memoria_tfg.md                      ← TFG document (Universidad de Deusto official structure)
│   └── playBook.md                         ← operational runbook
│
├── new_arch/                               ← NEW REPO LAYOUT (files to copy to standalone repo)
│   ├── docker-compose.yml                  ← NEW compose file (context: new repo root, no -f flag)
│   └── agents/
│       ├── machine/Dockerfile              ← NEW machine Dockerfile (COPY from patches/ and agents/)
│       ├── orchestrator/Dockerfile         ← NEW orchestrator Dockerfile (2 patches applied)
│       └── operator/Dockerfile             ← NEW operator Dockerfile (latest-alpine-base)
│
├── src/smia/
│   ├── agents/smia_agent.py                ← PATCHED (Patch 1: asset connection object-identity)
│   └── behaviours/
│       ├── acl_handling_behaviour.py       ← PATCHED (Patch 2: orchestrator race condition)
│       ├── negotiating_behaviour.py        ← PATCHED (Patch 3: per-thread template for concurrent negotiations)
│       └── specific_handle_behaviours/
│           └── handle_negotiation_behaviour.py  ← PATCHED (Patch 4: retry, deferred exit, thread reservation)
│
└── additional_tools/extended_agents/
    ├── smia_machine_agent/                 ← shared by ALL 6 machine containers (same code, diff env)
    │   ├── smia_machine_starter.py         ← launcher: ExtensibleSMIAAgent + machineAvailValue service
    │   └── smia_machine_agent_services.py  ← GET /smia/lego/availability?machine=<ID> → 0.0 or 1.0
    ├── smia_orchestrator_agent/
    │   ├── smia_orchestrator_starter.py    ← launcher: ExtensibleSMIAAgent + OrchestratorDispatchBehaviour
    │   └── orchestrator_dispatch_behaviour.py ← FIPA-CNP initiator: discovery, CFP, winner, forwarding
    └── smia_operator_agent/
        ├── operator_gui_behaviours.py
        ├── operator_gui_logic.py           ← PATCHED (Patch 3: hasParameter 3 bugs)
        └── htmls/
```

**CRITICAL:** Only `.aasx` files in `my_models/aas/`. Any other file causes the operator GUI to crash with a 500 error during AAS discovery.

---

## 7. Docker Compose Services

### Current working deployment (my_models/)

```bash
# All commands run from repo root SMIA/ with -f flag:
deploy:  docker compose -f my_models/docker-compose.yml up -d
build:   docker compose -f my_models/docker-compose.yml build
stop:    docker compose -f my_models/docker-compose.yml down
reset:   docker compose -f my_models/docker-compose.yml down -v   ← wipes ejabberd DB

# Case 0 only (no orchestrator):
docker compose -f my_models/docker-compose.yml up -d xmpp-server mosquitto-central nodered smia-machine0 smia-operator

# Full Case 1:
docker compose -f my_models/docker-compose.yml up -d
```

| Service | Image / Build | Role | Port |
|---|---|---|---|
| `xmpp-server` | `ghcr.io/processone/ejabberd` | XMPP broker; auto-registers all agents via CTL_ON_CREATE | 5222 |
| `mosquitto-central` | `eclipse-mosquitto:2` | MQTT broker; bridges to fischertechnik machine | internal |
| `nodered` | `nodered/node-red:latest` | HTTP→MQTT bridge; per-machine busy flags | 1880 |
| `smia-machine0` | `docker/smia-machine/Dockerfile` | Machine (smia_machine0@ejabberd), red | — |
| `smia-machine1` | `docker/smia-machine/Dockerfile` | Machine (smia_machine1@ejabberd), blue | — |
| `smia-machine2` | `docker/smia-machine/Dockerfile` | Machine (smia_machine2@ejabberd), white | — |
| `smia-machine3` | `docker/smia-machine/Dockerfile` | Machine (smia_machine3@ejabberd), red duplicate | — |
| `smia-machine4` | `docker/smia-machine/Dockerfile` | Machine (smia_machine4@ejabberd), blue duplicate | — |
| `smia-machine5` | `docker/smia-machine/Dockerfile` | Machine (smia_machine5@ejabberd), red+blue multicolour | — |
| `smia-orchestrator` | `docker/smia-orchestrator/Dockerfile` | Orchestrator (smia_orch@ejabberd) | — |
| `smia-operator` | `smia_operator_agent/Dockerfile` | Operator web GUI (operator001@ejabberd) | 10000 |

All services share the `smia-net` Docker bridge network. **Use `docker compose` (v2, space). NOT `docker-compose` (v1 hyphen — crashes with `KeyError: 'ContainerConfig'`).**

### New repo deployment (new_arch/ → standalone repo root)

When the new standalone repo is created, the docker-compose.yml is at the root (no `-f` flag needed):
```bash
# From the new repo root:
docker compose build
docker compose up -d
docker compose down
docker compose down -v
```

Build context changes: `context: .` (new repo root), Dockerfiles reference `patches/` and `agents/` directly.

### Dockerfile pattern (old vs new)

**Old (my_models/docker/, build context = `SMIA/`):**
```dockerfile
COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /
```

**New (new_arch/agents/, build context = new repo root):**
```dockerfile
COPY patches/smia_agent.py /tmp/smia_agent_patch.py
COPY agents/machine/smia_machine_starter.py /
```

Patch application (both old and new — same RUN step):
```bash
SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))")
cp /tmp/smia_agent_patch.py "$SMIA_PKG/agents/smia_agent.py"
```

---

## 8. AASX Models — Structure (all 8 files)

### 8.1 Machine AASXs — Machines 0, 1, 2

All three have the same submodel structure (different UUIDs, JIDs, colors):

```
AAS: LEGO_factory / LEGO_machine1 / LEGO_machine2
    AAS id: urn:uuid:6475_0111_2062_9689 (machine0)
            urn:uuid:6475_0111_2062_0001 (machine1)
            urn:uuid:6475_0111_2062_0002 (machine2)
    └── Submodels:
        1. SubmodelWithCapabilitySkillOntology — CSS ConceptDescriptions

        2. AssetInterfacesDescription (AID)
               └── InterfaceHTTP
                   ├── EndpointMetadata
                   │   ├── base = "http://nodered:1880"
                   │   └── contentType = "application/json"
                   └── InteractionMetadata / actions
                       ├── pickPiece (ActionAffordance)
                       │   └── forms: href=/smia/lego/pick?machine=smia_machine0 (machine0)
                       │             href=/smia/lego/pick?machine=smia_machine1&position=1 (machine1)
                       │             href=/smia/lego/pick?machine=smia_machine2&position=2 (machine2)
                       │   NOTE: position baked into href since SMIA sends no HTTP body
                       │   (no hasParameter on Skill_PickPiece); Node-RED reads query params
                       └── placePiece (ActionAffordance)
                           └── forms: href=/smia/lego/place, method=POST
               └── Interface_00 (agent service interface)
                   └── InteractionMetadata / actions
                       └── machineAvailValue (ActionAffordance)

        3. CapabilitiesAndSkills
               ├── Capability_PickPiece (css-smia#AssetCapability)
               │   ├── qualifier: hasLifecycle=OFFER
               │   └── color (Property xs:string): "red" / "blue" / "white"
               ├── Capability_PlacePiece (same pattern)
               ├── Skill_PickPiece (Property xs:string)
               │   └── qualifier: hasImplementationType=OPERATION
               │       semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType
               ├── Skill_PlacePiece (Property, same)
               └── Skill_NegAvailability (Property xs:string)
                   └── qualifier: hasImplementationType=OPERATION (same IRI)

        4. SemanticRelationships
               ├── rel_CapPick_isRealizedBySkill_SkillPick
               │   semanticId: http://www.w3id.org/hsu-aut/css#isRealizedBy
               ├── rel_CapPlace_isRealizedBySkill_SkillPlace  (same)
               ├── rel_SkillPick_hasSkillInterface
               │   semanticId: ...#accessibleThroughAssetService
               │   first: Skill_PickPiece  second: AID/.../pickPiece
               ├── rel_SkillPlace_hasSkillInterface  (same pattern)
               └── rel_SkillNegAvail_agentSvc
                   semanticId: ...#accessibleThroughAgentService   ← ALL LOWERCASE
                   first: Skill_NegAvailability  second: AID/Interface_00/.../machineAvailValue

AAS: SMIA_agent / SMIA_machine1 / SMIA_machine2
    └── SoftwareNameplate / SoftwareNameplateInstance
        └── InstanceName: smia_machine0@ejabberd (machine0) ← ⚠ AASX BINARY PENDING UPDATE
                          smia_machine1@ejabberd (machine1)
                          smia_machine2@ejabberd (machine2)
```

**⚠ PENDING (machine0 only):** The `LEGO_machine0.aasx` binary still has `InstanceName = SMIA_agent@ejabberd`. The XMPP JID has been renamed to `smia_machine0@ejabberd` in `.env` and docker-compose, but the AASX binary must be updated manually in AASX Package Explorer:
`LEGO_machine0.aasx` → `SMIA_agent` shell → `SoftwareNameplate` → `SoftwareNameplateInstance` → `InstanceName` → change to `smia_machine0@ejabberd`.

Without this fix, the orchestrator reads `SMIA_agent@ejabberd` from the AASX but tries to send a FIPA message to `smia_machine0@ejabberd` — mismatch causes negotiation failures for machine0.

**CRITICAL IRI casing:** All RelationshipElement semanticIds use lowercase IRIs. Capital letters cause silent Track 3 failures.

### 8.2 Machine AASXs — Machines 3, 4, 5

Clones of machines 0-2 with different UUIDs, JIDs, and colors:

| File | JID | AAS UUID | Color |
|---|---|---|---|
| `LEGO_machine3.aasx` | `smia_machine3@ejabberd` | `urn:uuid:6475_0111_2062_0003` | red (duplicate of machine0) |
| `LEGO_machine4.aasx` | `smia_machine4@ejabberd` | `urn:uuid:6475_0111_2062_0004` | blue (duplicate of machine1) |
| `LEGO_machine5.aasx` | `smia_machine5@ejabberd` | `urn:uuid:6475_0111_2062_0005` | red,blue (multicolour) |

Machine5 has `color = "red,blue"` (comma-separated). The orchestrator filter uses list membership:
```python
machine_colors = [c.strip().lower() for c in color.split(',')]
if color_filter.lower() not in machine_colors:
    continue
```

### 8.3 Orchestrator AASX (SMIA_orchestrator.aasx)

```
AAS: SMIA_orchestrator (urn:uuid:8888_0001_2026_0001)
    └── Submodels:
        1. SubmodelWithCapabilitySkillOntology
        2. CapabilitiesAndSkills
               ├── Capability_PickPiece (css-smia#AgentCapability)  ← NOT AssetCapability!
               │   ├── qualifier: hasLifecycle=OFFER
               │   ├── color (Property xs:string)
               │   └── position (Property xs:int)
               ├── Skill_Orchestrate_PickPiece (Property xs:string)
               └── SkillParameter_color (Property xs:string, semanticId: css#SkillParameter)
                   └── id_short MUST be "color" (not "SkillParameter_color") — GUI uses it
                       directly as HTML form field name
        3. SemanticRelationships
               ├── rel_CapPick_isRealizedBy_SkillOrchPick
               └── rel_SkillOrch_hasParam_color
                   semanticId: http://www.w3id.org/hsu-aut/css#hasParameter
                   ← makes operator GUI show a color input field
        4. SoftwareNameplate
               └── InstanceName: smia_orch@ejabberd  ← MUST include @ejabberd domain!

AAS: SMIA_orch_agent
    └── SoftwareNameplate only
```

**Why `AgentCapability`?** Orchestrator coordinates other agents — it has no physical asset. `AgentCapability` = DT-level function. `AssetCapability` = physical machine function.

**Why `InstanceName: smia_orch@ejabberd`?** Operator GUI parses InstanceName for SMIA version lookup. Without `@ejabberd`, JID lookup fails → version `(0,0,0)` → old message format used → orchestrator rejects it.

### 8.4 Operator AASX (SMIA_Operator_article.aasx)

Standard operator AASX from SMIA examples. Operator scans all `.aasx` files in the `aas/` mount and presents discovered agents in the GUI.

---

## 9. CSS Ontology

File: `my_models/ontology/CSS-ontology-smia.owl` (also embedded in each AASX at `aasx/CSS-ontology-smia.owl`)

**Source:** CaSkade-Automation CSS-ontology v1.0.1 (October 2024), extended by SMIA.
- CaSkade base: `https://github.com/CaSkade-Automation/CSS`
- SMIA extension IRI: `http://www.w3id.org/upv-ehu/gcis/css-smia`

### CSS class hierarchy (paper Fig. 4)

```
css:Capability  ──isRestrictedBy──►  css:CapabilityConstraint
    │
    ├──► css-smia:AssetCapability    ← PHYSICAL capabilities
    │    e.g. PickPiece, PlacePiece — functions inherent to the machine
    │
    └──► css-smia:AgentCapability    ← AGENT capabilities
         e.g. Orchestrate_PickPiece — functions of the DT agent itself

css:Capability ──isRealizedBy──► css:Skill
                                     │
                                     ├──accessibleThroughAssetService──► css:SkillInterface
                                     │  → PHYSICAL execution via AssetConnection (HTTP)
                                     │
                                     └──accessibleThroughAgentService──► css:SkillInterface
                                        → AGENT execution via Python method (agent service)
```

### Key IRIs

| Concept | IRI |
|---|---|
| AssetCapability | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` |
| AgentCapability | `http://www.w3id.org/upv-ehu/gcis/css-smia#AgentCapability` |
| Skill | `http://www.w3id.org/hsu-aut/css#Skill` |
| isRealizedBy | `http://www.w3id.org/hsu-aut/css#isRealizedBy` |
| accessibleThroughAssetService | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` |
| accessibleThroughAgentService | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` |

### AAS Qualifier — OWL DatatypeProperty bridge (CRITICAL)

A Qualifier has three fields: `type` (string label), `value` (data), `semanticId` (IRI).

**Two levels of semanticId — DO NOT confuse:**
- **Element semanticId** → OWL **Class** (what TYPE is this element? e.g. `css#Skill`)
- **Qualifier semanticId** → OWL **DatatypeProperty** (what ATTRIBUTE does this qualifier represent?)

**How the bridge works (Track 2, `init_aas_model_behaviour.py:200`):**
At boot, SMIA reads all `owl:DatatypeProperty` declarations whose `rdfs:domain` includes the instance's class. For each IRI, it calls `get_qualifier_value_by_semantic_id(iri)` → finds the qualifier whose `semanticId` matches → reads its `value` → populates the OWL attribute. No match → `AASModelReadingError` → OWL instance attribute stays empty → FIPA-CNP crashes with `NoneType`.

| type string | OWL DatatypeProperty IRI | Note |
|---|---|---|
| `hasLifecycle` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasLifecycle` | |
| `SkillImplementationType` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` | type ≠ OWL property name! |
| `hasCondition` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasCondition` | |

### CSS semantic chains

**Case 0 — Direct execution:**
```
Capability_PickPiece (AssetCapability, OFFER, color="red")
    ──isRealizedBy──►  Skill_PickPiece (hasImplementationType=OPERATION)
                           ──accessibleThroughAssetService──►
                               AID/InterfaceHTTP/actions/pickPiece
                                   ──► HTTP POST nodered:1880/smia/lego/pick?machine=smia_machine0
```

**Case 1 — Negotiation criterion:**
```
Skill_NegAvailability (hasImplementationType=OPERATION)
    ──accessibleThroughAgentService──►
        AID/Interface_00/actions/machineAvailValue
            ──► Python: await get_machine_availability()
                    ──► async GET nodered:1880/smia/lego/availability?machine=smia_machine0
                    ──► Node-RED checks global.machine_busy_smia_machine0 → 1.0 or 0.0
```

---

## 10. AID Semantic IDs (verified from `src/smia/utilities/smia_info.py`)

| Element | semanticId URI |
|---|---|
| AID Submodel | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel` |
| Interface SMC | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Interface` |
| EndpointMetadata | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/EndpointMetadata` |
| InteractionMetadata | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/InteractionMetadata` |
| base URL | `https://www.w3.org/2019/wot/td#baseURI` |
| contentType | `https://www.w3.org/2019/wot/hypermedia#forContentType` |
| ActionAffordance | `https://www.w3.org/2019/wot/td#ActionAffordance` |
| PropertyAffordance | `https://www.w3.org/2019/wot/td#PropertyAffordance` |
| hasForm | `https://www.w3.org/2019/wot/td#hasForm` |
| href (hasTarget) | `https://www.w3.org/2019/wot/hypermedia#hasTarget` |
| HTTP method | `https://www.w3.org/2011/http#methodName` |
| hasInputSchema | `https://www.w3.org/2019/wot/td#hasInputSchema` |

---

## 11. Framework Patches Applied

Five bugs/deficiencies found in SMIA v0.3.x. Full documentation + deep-dive walkthrough: `my_models/PATCHES.md`.

**Patch matrix — which Dockerfiles apply which patches:**

| Patch | Machine Dockerfile | Orchestrator Dockerfile | Operator Dockerfile |
|---|---|---|---|
| Patch 1 — `smia_agent.py` | ✓ | ✓ | — |
| Patch 2 — `acl_handling_behaviour.py` | — | ✓ | — |
| Patch 3 — `negotiating_behaviour.py` | ✓ | ✓ | — |
| Patch 4 — `handle_negotiation_behaviour.py` | ✓ | ✓ | — |
| Patch 5 — `operator_gui_logic.py` | — | — | ✓ (implicit COPY) |

### 11.1 Patch 1 — `smia_agent.py`: asset connection object-identity bug

**File:** `src/smia/agents/smia_agent.py`, method `get_asset_connection_class_by_ref()`
**Applied:** machine + orchestrator Dockerfiles (RUN step at build time)
**Bug:** AID reference lookup used `==` on `ModelReference` (basyx-python-sdk 1.2.1 doesn't implement structural `__eq__`). Two independently constructed instances representing the same path fail identity comparison → no HTTP call → crane never moves.
**Fix:** Three-strategy cascade: `==` (original), `str()` comparison, key-tuple structural comparison.

### 11.2 Patch 2 — `acl_handling_behaviour.py`: orchestrator race condition

**File:** `src/smia/behaviours/acl_handling_behaviour.py`, method `run()`
**Applied:** orchestrator Dockerfile only
**Bug:** SPADE delivers css-service REQUEST to both `ACLHandlingBehaviour` and `OrchestratorDispatchBehaviour` simultaneously. `ACLHandlingBehaviour` spawns `HandleCapabilityBehaviour` on the orchestrator (which has no asset service) — crashes or duplicates the response.
**Fix:** Early return when `hasattr(self.myagent, 'pending_orchestrations')`. Synchronous check, no race window.

### 11.3 Patch 3 (operator) — `operator_gui_logic.py`: three latent `hasParameter` bugs

**File:** `additional_tools/extended_agents/smia_operator_agent/operator_gui_logic.py`
**Applied:** operator Dockerfile implicitly (patched file COPY'd to WORKDIR `/`, no RUN needed)
**Why latent:** no upstream SMIA AASX uses `hasParameter` — bugs never triggered before.
**Bugs:** `KeyError: 'skillData'` (wrong dict key), `TypeError: unhashable list` (full list added to set), `SyntaxError` on downstream `eval()` (AAS object stored instead of `id_short` string).
**Fix:** single corrected loop: `self.myagent.skills_info[skill].update(p.id_short for p in skill_params_list)`

### 11.4 Patch 3 (negotiation) — `negotiating_behaviour.py`: concurrent negotiation cross-contamination

**File:** `src/smia/behaviours/negotiating_behaviour.py`
**Applied:** machine + orchestrator Dockerfiles
**Bug:** `HandleNegotiationBehaviour` registered without a per-thread template → all instances receive all negotiation messages → concurrent negotiations corrupt each other.
**Fix:** Pass `handle_neg_template_propose | handle_neg_template_request` (both filtered to `msg.thread`) when calling `add_behaviour()`.

### 11.5 Patch 4 (negotiation) — `handle_negotiation_behaviour.py`: deadlock with 3+ machines

**File:** `src/smia/behaviours/specific_handle_behaviours/handle_negotiation_behaviour.py`
**Applied:** machine + orchestrator Dockerfiles
**Bug:** Three interacting problems — (A) if PROPOSE arrives before the peer's `HandleNegotiationBehaviour` is registered it is silently dropped; (B) machine calls `exit_negotiation()` immediately on loss but may still need to process late messages; (C) 10s receive timeout prevents retry logic.
**Fix:** Short 0.01s receive timeout + iteration counter; deferred exit (store result, keep behaviour alive until iteration budget); `REQUEST`-for-negValue retry at random iterations 20–60% of budget; individual PROPOSE dispatch with small delays; proper thread reservation/release via `add_reserved_thread`/`remove_reserved_thread`.

---

## 12. Custom Extensions (TFG Contribution)

### 12.1 `smia_machine_starter.py` — machine launcher

Replaces default SMIA launcher. Creates `ExtensibleSMIAAgent` and registers the `machineAvailValue` agent service:
```python
smia_agent = ExtensibleSMIAAgent(smia_jid, smia_passwd)
smia_agent.add_new_agent_service('machineAvailValue', get_machine_availability)
smia.run(smia_agent)
```
All 6 machine containers run the same code — differentiated only by `AGENT_ID` and `AAS_MODEL_NAME` env vars.

### 12.2 `smia_machine_agent_services.py` — per-machine availability service

Python coroutine `get_machine_availability()` registered as `machineAvailValue`.

```python
MACHINE_ID = os.environ.get('AGENT_ID', 'machine').split('@')[0]
# e.g. AGENT_ID='smia_machine0@ejabberd' → MACHINE_ID='smia_machine0'

async def get_machine_availability(agent_service_data):
    url = f"{NODE_RED_BASE}/smia/lego/availability?machine={MACHINE_ID}"
    # → Node-RED checks global.machine_busy_smia_machine0
    # → returns "1.0" (free) or "0.0" (busy)
```

Each machine queries its own busy flag. Falls back to `'default'` if `AGENT_ID` is not set.

### 12.3 `smia_orchestrator_starter.py` — orchestrator launcher

Creates `ExtensibleSMIAAgent` and registers `OrchestratorDispatchBehaviour`:
```python
orch_behaviour = OrchestratorDispatchBehaviour()
smia_agent.add_new_agent_capability(orch_behaviour)
smia.run(smia_agent)
```

### 12.4 `orchestrator_dispatch_behaviour.py` — FIPA-CNP initiator

**What base SMIA provides:** responder side (`HandleNegotiationBehaviour`) — receives CFP, computes negValue, sends PROPOSE/INFORM.

**What this class provides (TFG contribution):**
1. **Discovery:** scans `.aasx` files; reads JID from `SoftwareNameplate.InstanceName` and color from `Capability_PickPiece.color` (supports comma-separated multicolour)
2. **Color routing:** filters machines by color; maps color → warehouse slot position
3. **CFP dispatch:** builds and sends negotiation CFP to eligible machines
4. **Winner reception:** awaits `INFORM({winner: True})` from winning machine
5. **Execution delegation:** sends capability REQUEST to winner with `position` in skillParams
6. **Result forwarding:** relays winner's INFORM back to operator

---

## 13. Node-RED Flows

**Endpoints exposed:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/smia/lego/pick` | POST | Execute pick; reads `query.machine` and `query.position`; sets `machine_busy_<id>=true`; clears after 8s |
| `/smia/lego/place` | POST | Execute place |
| `/smia/lego/availability` | GET | Reads `query.machine`; returns `"1.0"` (free) or `"0.0"` (busy) |

**MQTT topic:** `vicom/61/piso_0/lab/lego/commands`
**MQTT payload:** `bandera_custom:<position>` (position 0–8)

Node-RED maintains per-machine state in global context: `machine_busy_smia_machine0`, `machine_busy_smia_machine1`, etc. The `pick` handler extracts `machineId = query.machine || 'default'` and uses it as the flag key. The 8-second delayed chain carries `machineId` so the right flag is cleared.

---

## 14. Deployment Quick Reference

```bash
# Build after any .py change:
docker compose -f my_models/docker-compose.yml build

# Incremental startup (recommended for debugging):
docker compose -f my_models/docker-compose.yml up -d xmpp-server mosquitto-central nodered
docker compose -f my_models/docker-compose.yml up -d smia-machine0 smia-machine1 smia-machine2 smia-operator
docker compose -f my_models/docker-compose.yml up -d smia-machine3 smia-machine4 smia-machine5 smia-orchestrator

# Logs:
docker compose -f my_models/docker-compose.yml logs -f smia-machine0 smia-orchestrator smia-operator

# Full reset (needed after password changes or XMPP auth lockouts):
docker compose -f my_models/docker-compose.yml down -v && docker compose -f my_models/docker-compose.yml up -d
```

### Healthy startup signatures

| Service | Expected log |
|---|---|
| `xmpp-server` | `Starting ejabberd ... done` (then healthcheck passes) |
| `smia-machine0..5` | `AAS model initialized.` + `Analyzed skills: ['Skill_PickPiece', 'Skill_PlacePiece', 'Skill_NegAvailability']` |
| `smia-orchestrator` | `AAS model initialized.` + `Analyzed capabilities: ['Capability_PickPiece']` |
| `smia-operator` | `Starting web server on port 10000` |
| Idle (all) | `No message received within 10 seconds on SMIA (ACLHandlingBehaviour)` |

**Operator GUI:** http://localhost:10000/smia_operator

---

## 15. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'ContainerConfig'` on compose up | Docker Compose v1 | Use `docker compose` (space, v2) |
| ejabberd never healthy | ejabberd.yml syntax error or port conflict | `docker compose logs xmpp-server` |
| SMIA MRO error at boot | Skills defined as SMC instead of Property | Redefine as Property in AASX PE |
| Operator GUI 500 on Load | Non-AASX file in `aas/` | Remove non-.aasx files from `aas/` |
| Submit spins, no HTTP in logs | Patch 1 not applied | `docker compose build smia-machine0`; check Dockerfile RUN log |
| HTTP OK but crane does not move | MQTT bridge down or wrong IP | Check Node-RED debug + `bridge.conf` address |
| XMPP auth failure / IP blacklisting | Password mismatch between `.env` and ejabberd DB | `docker compose down -v && up -d` |
| `NoneType is not iterable` in negotiation | OWL link missing — IRI casing wrong | `rel_SkillNegAvail_agentSvc` semanticId must be exactly `...#accessibleThroughAgentService` (lowercase 'a') |
| `hasImplementationType not found` at boot | Qualifier semanticId uses `https://` not `http://` | Fix in AASX PE: use `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` |
| CFP sent but `color=''` (all machines respond) | Orchestrator AASX has no `hasParameter` rel | Add `SkillParameter_color` + `rel_SkillOrch_hasParam_color` — **already done** in current AASX |
| Machine not discovered by orchestrator | `InstanceName` in AASX ≠ `AGENT_ID` in `.env` | Update AASX in AASX PE → SoftwareNameplate → InstanceName |
| machine0 not participating in negotiation | InstanceName still `SMIA_agent@ejabberd` in AASX | **PENDING**: update LEGO_machine0.aasx in AASX PE to `smia_machine0@ejabberd` |
| `AASConstraintViolation: id_short` in orchestrator logs | SMIA_Operator_article.aasx has hyphens in element names | **Benign** — doesn't affect color/JID discovery |
| `ConceptDescription duplicate identifier` | Multiple AASXs embed the same CSS CDs | **Benign** — BaSyx skips duplicates |
| SCRAM-SHA-512-PLUS warnings in ejabberd | SPADE tries channel-binding variant first | No action needed — harmless |

---

## 16. Validation Metrics (paper §5.2.3)

| Metric | Value | Context |
|---|---|---|
| Self-configuration time (21 CSS elements) | **6.73 s** avg | Paper robotic agent |
| Self-configuration time (7 CSS elements) | **3.39 s** | Paper operator agent |
| Messages per direct execution | **2** (REQUEST + INFORM) | Case 0 |
| Messages per distributed negotiation | **5** (2n+1, n=2) | Base SMIA paper |
| Total response time | **0.034–0.098 s** | Operator request → action complete |

Case 1 message count with 3 eligible machines: 1 (op→orch) + 3 (CFP→machines) + 3 (PROPOSE within machines) + 1 (INFORM winner→orch) + 1 (orch→winner REQUEST) + 1 (winner INFORM→orch) + 1 (orch INFORM→op) = **11 messages**.

---

## 17. Key Identifiers and Credentials

| Item | Value |
|---|---|
| machine0 AAS id | `urn:uuid:6475_0111_2062_9689` |
| machine1 AAS id | `urn:uuid:6475_0111_2062_0001` |
| machine2 AAS id | `urn:uuid:6475_0111_2062_0002` |
| machine3 AAS id | `urn:uuid:6475_0111_2062_0003` |
| machine4 AAS id | `urn:uuid:6475_0111_2062_0004` |
| machine5 AAS id | `urn:uuid:6475_0111_2062_0005` |
| orchestrator AAS id | `urn:uuid:8888_0001_2026_0001` |
| machine0 JID | `smia_machine0@ejabberd` (⚠ AASX binary still says SMIA_agent — needs PE fix) |
| machine1 JID | `smia_machine1@ejabberd` |
| machine2 JID | `smia_machine2@ejabberd` |
| machine3 JID | `smia_machine3@ejabberd` |
| machine4 JID | `smia_machine4@ejabberd` |
| machine5 JID | `smia_machine5@ejabberd` |
| orchestrator JID | `smia_orch@ejabberd` |
| operator JID | `operator001@ejabberd` |
| Passwords | See `.env` or `.env.example` |
| DIDA Central IP | `192.168.155.10` |
| Node-RED (Docker) | `http://nodered:1880` |
| Node-RED (host) | `http://192.168.155.10:1880` |
| MQTT topic | `vicom/61/piso_0/lab/lego/commands` |
| MQTT payload | `bandera_custom:<position>` (0–8) |
| Operator GUI | `http://localhost:10000/smia_operator` |

---

## 18. Documents Index

| File | Purpose | When to use |
|---|---|---|
| `CLAUDE.md` (this file) | AI assistant context — complete project state | First thing to read in any new session |
| `PATCHES.md` | Detailed bug documentation for upstream PRs (Ekaitz Hurtado) | Explaining the 3 bug fixes |
| `README.md` | Professional README for the standalone Vicomtech repo | Sharing with colleagues / new repo |
| `doc_case0.md` | Full AASX PE tutorial + Case 0 technical reference | Building AASX models, replication |
| `doc_case1.md` | Case 1 multi-agent architecture deep-dive | Orchestration design, FIPA-CNP details |
| `memoire.md` | TFG academic document (technical deep-dive, free form) | Academic writing base |
| `memoria_tfg.md` | TFG document (Universidad de Deusto official structure) | Official TFG submission |
| `playBook.md` | Operational runbook — verified runtime values | Day-to-day deployment |

---

## 19. What Has Been Custom-Implemented (TFG vs Framework)

| Component | Type | Description |
|---|---|---|
| `smia_machine_starter.py` | **New — TFG** | ExtensibleSMIAAgent launcher; registers machineAvailValue |
| `smia_machine_agent_services.py` | **New — TFG** | Per-machine availability GET → Node-RED per-machine flag |
| `smia_orchestrator_starter.py` | **New — TFG** | ExtensibleSMIAAgent launcher; registers OrchestratorDispatchBehaviour |
| `orchestrator_dispatch_behaviour.py` | **New — TFG** | FIPA-CNP initiator; AAS discovery; multicolour routing |
| All 8 AASX files | **New — TFG** | AAS models for 6 machines + orchestrator + operator |
| `smia_agent.py` (patched) | **SMIA bug fix** | Patch 1: ModelReference object-identity; pending upstream PR |
| `acl_handling_behaviour.py` (patched) | **SMIA bug fix** | Patch 2: orchestrator race condition; pending upstream PR |
| `operator_gui_logic.py` (patched) | **SMIA bug fix** | Patch 3: three hasParameter bugs; pending upstream PR |
| `negotiating_behaviour.py` (patched) | **SMIA bug fix** | Patch 3b: per-thread template; prevents concurrent negotiation cross-contamination |
| `handle_negotiation_behaviour.py` (patched) | **SMIA bug fix** | Patch 4: retry logic, deferred exit, thread reservation for 3+ machine negotiations |
| `flows.json` | **Infrastructure — TFG** | Per-machine busy flag Node-RED logic |
| `docker-compose.yml`, Dockerfiles, `ejabberd.yml` | **Infrastructure — TFG** | Full containerized deployment stack |

**What SMIA provides out of the box (patched but not reimplemented):**
- `HandleCapabilityBehaviour` — skill resolution → AID → HTTP (unmodified)
- `HandleNegotiationBehaviour` — FIPA-CNP responder (**Patch 4 applied**: retry + deferred exit)
- `NegotiatingBehaviour` — peer PROPOSE exchange (**Patch 3b applied**: per-thread template)
- `AASInitializationBehaviour` — all 3 tracks of self-configuration (unmodified)
- `ACLHandlingBehaviour` — FIPA-ACL dispatch (**Patch 2 applied** on orchestrator only)
- OWL management via `owlready2`, AAS parsing via `basyx-python-sdk`

---

## 20. New Standalone Repo Layout

The `new_arch/` folder contains files for the professional standalone Vicomtech repo (to be created separately). This is the target layout once migrated:

```
smia-flexible-manufacturing/        ← new standalone repo root
├── README.md                       ← from my_models/README.md
├── PATCHES.md                      ← from my_models/PATCHES.md (detail for Ekaitz)
├── docker-compose.yml              ← from new_arch/docker-compose.yml
├── .env.example                    ← from my_models/.env.example
│
├── agents/
│   ├── machine/
│   │   ├── Dockerfile              ← from new_arch/agents/machine/Dockerfile
│   │   ├── smia_machine_starter.py ← from additional_tools/.../smia_machine_agent/
│   │   └── smia_machine_agent_services.py
│   ├── orchestrator/
│   │   ├── Dockerfile              ← from new_arch/agents/orchestrator/Dockerfile
│   │   ├── smia_orchestrator_starter.py ← from additional_tools/.../smia_orchestrator_agent/
│   │   └── orchestrator_dispatch_behaviour.py
│   └── operator/
│       ├── Dockerfile              ← from new_arch/agents/operator/Dockerfile
│       ├── smia_operator_starter.py ← from additional_tools/.../smia_operator_agent/
│       ├── operator_gui_behaviours.py
│       ├── operator_gui_logic.py   ← PATCHED version (Patch 3 applied)
│       └── htmls/
│
├── patches/                        ← SMIA framework patches (applied at Docker build time)
│   ├── smia_agent.py               ← from src/smia/agents/smia_agent.py (Patch 1)
│   ├── acl_handling_behaviour.py   ← from src/smia/behaviours/acl_handling_behaviour.py (Patch 2)
│   ├── negotiating_behaviour.py    ← from src/smia/behaviours/negotiating_behaviour.py (Patch 3b)
│   └── handle_negotiation_behaviour.py ← from src/smia/behaviours/specific_handle_behaviours/ (Patch 4)
│
├── aas/                            ← all 8 AASX files (from my_models/aas/)
│
├── config/
│   ├── ejabberd.yml                ← from my_models/xmpp_server/ejabberd.yml
│   ├── mosquitto/
│   │   ├── mosquitto.conf          ← from my_models/mosquitto/mosquitto.conf
│   │   └── conf.d/bridge.conf      ← SET MACHINE IP HERE
│   └── nodered/
│       └── flows.json              ← from my_models/nodered/flows.json
│
├── ontology/
│   └── CSS-ontology-smia.owl       ← from my_models/ontology/
│
└── docs/
    ├── memoire.md                  ← technical deep-dive
    └── memoria_tfg.md              ← university TFG document
```

### Path mapping (old my_models → new repo)

| my_models/ (old) | new repo (new) |
|---|---|
| `xmpp_server/ejabberd.yml` | `config/ejabberd.yml` |
| `mosquitto/` | `config/mosquitto/` |
| `nodered/flows.json` | `config/nodered/flows.json` |
| `docker/smia-machine/Dockerfile` | `agents/machine/Dockerfile` |
| `docker/smia-orchestrator/Dockerfile` | `agents/orchestrator/Dockerfile` |
| Build context: `../` (SMIA repo root) | Build context: `.` (new repo root) |
| `COPY src/smia/agents/smia_agent.py` | `COPY patches/smia_agent.py` |
| `COPY additional_tools/.../smia_machine_starter.py` | `COPY agents/machine/smia_machine_starter.py` |

### Pending manual tasks before final migration

1. **machine0 AASX InstanceName** — open `LEGO_machine0.aasx` in AASX Package Explorer → `SMIA_agent` shell → `SoftwareNameplate` → `SoftwareNameplateInstance` → `InstanceName` → change to `smia_machine0@ejabberd`
2. **machine0, 1, 2 pick hrefs** — verify AID pick href includes `?machine=smia_machineN` for per-machine busy tracking (machines 1 and 2 may already have `?position=N`; add `&machine=smia_machineN`)
3. **Rename AASX binary files** in `aas/` if `LEGO_factory_case0.aasx` still exists — rename to `LEGO_machine0.aasx`

---

## 21. Next Task — Node-RED Virtual Factory Dashboard (MVP)

**Goal:** Replace the physical fischertechnik crane with a Node-RED dashboard that simulates the warehouse, making the entire system self-contained and demonstrable on any laptop.

### Why

- No external hardware or lab network required — `docker compose up -d` is the only step
- SMIA authors (Ekaitz Hurtado) can run the MVP themselves to validate the TFG contributions
- All FIPA-CNP negotiation logic, AASX-driven self-configuration, and multi-agent orchestration remain exactly the same — only the final actuator output changes

### What the dashboard must do

1. **Visual warehouse grid** — 4 colored slots (slot 0 = red, slot 1 = blue, slot 2 = white, slot 3 = yellow). Each slot shows: piece color, current state (idle / picking / empty), and which machine is assigned.
2. **Pick simulation** — when `/smia/lego/pick?machine=X&position=N` is called: mark slot N as "picking" (visual state change), set `machine_busy_X = true`, after 8s reset to idle, clear busy flag.
3. **Availability endpoint** — `/smia/lego/availability?machine=X` unchanged: returns `"1.0"` or `"0.0"` based on `machine_busy_X` global flag.
4. **No MQTT** — remove the MQTT output nodes and the bridge to the physical machine. No `mosquitto-central` service needed. `nodered` container becomes fully self-contained.
5. **Dashboard URL** — accessible at `http://localhost:1880/ui`

### Node-RED flows required

#### Flow 1 — Pick endpoint (replace MQTT with dashboard)
```
[HTTP IN POST /smia/lego/pick]
    → [Function: extract machineId + position from query params]
    → [Function: set global.machine_busy_<machineId> = true]
    → [Link Out → dashboard update: slot N → state="picking, machine=X"]
    → [Delay 8s] → [Function: clear global.machine_busy_<machineId>]
                 → [Link Out → dashboard update: slot N → state="idle"]
    → [HTTP Response 200 OK]
```

#### Flow 2 — Availability endpoint (unchanged)
```
[HTTP IN GET /smia/lego/availability]
    → [Function: machineId = query.machine || 'default'
                 busy = global.machine_busy_<machineId> || false
                 return busy ? "0.0" : "1.0"]
    → [HTTP Response]
```

#### Flow 3 — Dashboard tab "Virtual Factory"
Nodes needed (install `node-red-dashboard`):
- `[ui_tab]` "Virtual Factory"
- `[ui_group]` "Warehouse" (width 12)
- 4 × `[ui_template]` nodes — one per slot — rendering a colored card that reacts to state changes via `msg.topic = "slot/<N>"` events
- `[ui_text]` nodes showing last pick log (machine, position, timestamp)

### Dashboard slot card (Node-RED template HTML)
```html
<!-- slot-card template — receives msg.payload = {state, machine} -->
<div ng-style="{'background': slotColor, 'padding': '12px', 'border-radius': '8px',
                'opacity': state == 'empty' ? 0.3 : 1}">
  <div style="font-size: 18px; font-weight: bold">{{slotLabel}}</div>
  <div>State: <b>{{state}}</b></div>
  <div ng-if="machine">Machine: {{machine}}</div>
</div>
<script>
  (function(scope) {
    scope.$watch('msg', function(msg) {
      if (msg) {
        scope.state  = msg.payload.state;
        scope.machine = msg.payload.machine;
      }
    });
    scope.slotLabel = scope.ui.label;
    scope.slotColor = {'red':'#ff6b6b','blue':'#6b9eff','white':'#f0f0f0','yellow':'#ffe66b'}[scope.ui.label] || '#ccc';
    scope.state = 'idle';
  })(scope);
</script>
```

### docker-compose changes for MVP mode

Remove the `mosquitto-central` dependency from the `nodered` service (and remove the MQTT bridge config volume mount). The `nodered` service becomes:
```yaml
nodered:
  image: nodered/node-red:latest
  user: root
  container_name: nodered
  environment:
    - NODE_RED_CREDENTIAL_SECRET=${NODERED_CREDENTIAL_SECRET}
    - FLOWS=flows.json
  volumes:
    - ./config/nodered:/data
  ports:
    - "1880:1880"
    - "1880:1880"   # dashboard also on :1880/ui
  restart: unless-stopped
  networks:
    - smia-net
```

The `mosquitto-central` service and `nodered/conf.d/bridge.conf` can be left in the compose file but `nodered` no longer depends on them.

### Node-RED package requirement
Add to `config/nodered/package.json` (Node-RED loads this at startup):
```json
{
  "name": "smia-nodered-flows",
  "dependencies": {
    "node-red-dashboard": "3.x"
  }
}
```

### Acceptance criteria for the MVP demo
1. `docker compose up -d` starts all 11 services with no external dependencies
2. `http://localhost:10000/smia_operator` — operator GUI loads, shows orchestrator + 6 machines
3. Select orchestrator → Capability_PickPiece → color=red → Submit
4. Logs show: orchestrator receives REQUEST → discovers 3 red-capable machines → sends CFP → negotiation completes → winner receives REQUEST → HTTP POST to nodered
5. `http://localhost:1880/ui` — dashboard shows the winning machine ID and slot 0 changing from "idle" to "picking" then back to "idle"
6. Repeat with color=blue → slot 1 animates, a different machine wins if machine0 is busy
