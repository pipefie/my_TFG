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
| **Case 1** | 3 machines + orchestrator, FIPA-CNP multi-agent negotiation | **Implemented, E2E testing** |
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
    │ routes to SMIA_agent@ejabberd (machine0)
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
    │ 3. Filters: only machines where color == "red"
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
    │ 3. Calls agent service 'machineAvailValue' → async GET http://nodered:1880/smia/lego/availability
    │    → returns 1.0 (free) or 0.0 (busy)
    │ 4. If 1 machine in negTargets: wins immediately
    │    If multiple: sends PROPOSE to peers, compares, highest wins
    │ 5. Winner sends INFORM({winner: True}) to negRequester=orchestrator
    ▼

PHASE 3 — Capability execution (built-in SMIA, winner machine):
[smia-orchestrator] sends REQUEST to winner
[smia-machineN winner] — HandleCapabilityBehaviour
    │ Resolves Skill_PickPiece → AID HTTP action → POST to nodered:1880/smia/lego/pick
    │ Node-RED → MQTT → crane moves
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

This mapping is in `orchestrator_dispatch_behaviour.py` (`_start_negotiation` method). Each machine AASX declares its color via `Capability_PickPiece` → `color` property.

---

## 6. File Structure (CURRENT)

```
SMIA/
├── my_models/                              ← ALL deployment files
│   ├── CLAUDE.md                           ← this file
│   ├── docker-compose.yml                  ← 8 services (see §7)
│   ├── .env                                ← credentials (gitignored; copy from .env.example)
│   ├── .env.example                        ← template with all required variables
│   ├── aas/                                ← ALL AASX files (operator scans this folder)
│   │   ├── LEGO_factory_case0.aasx         ← machine0 (SMIA_agent@ejabberd)
│   │   ├── LEGO_machine1_case0.aasx        ← machine1 (smia_machine1@ejabberd)
│   │   ├── LEGO_machine2_case0.aasx        ← machine2 (smia_machine2@ejabberd)
│   │   ├── SMIA_orchestrator.aasx          ← orchestrator (smia_orch@ejabberd)
│   │   └── SMIA_Operator_article.aasx      ← operator agent's own AAS
│   ├── docker/
│   │   ├── smia-machine/Dockerfile         ← custom image for machine agents
│   │   └── smia-orchestrator/Dockerfile    ← custom image for orchestrator
│   ├── mosquitto/
│   │   ├── mosquitto.conf                  ← Mosquitto broker config
│   │   └── conf.d/bridge.conf              ← MQTT bridge to fischertechnik machine
│   ├── nodered/
│   │   └── flows.json                      ← Node-RED flows (HTTP→MQTT bridge)
│   ├── ontology/
│   │   └── CSS-ontology-smia.owl           ← CSS ontology (also embedded in each AASX)
│   ├── xmpp_server/
│   │   └── ejabberd.yml                    ← ejabberd configuration
│   ├── doc_case0.md                        ← full technical reference + AASX PE tutorial
│   ├── memoire.md                          ← formal TFG academic document base
│   └── flow_dida_central_lego.json         ← Node-RED flow alt (for DIDA central if not containerized)
│
├── src/smia/
│   ├── agents/smia_agent.py                ← PATCHED (asset connection object-identity bug)
│   └── behaviours/acl_handling_behaviour.py ← PATCHED (orchestrator race condition)
│
└── additional_tools/extended_agents/
    ├── smia_machine_agent/
    │   ├── smia_machine_starter.py         ← launcher: creates ExtensibleSMIAAgent + registers machineAvailValue
    │   └── smia_machine_agent_services.py  ← agent service: async GET /smia/lego/availability → 0.0 or 1.0
    ├── smia_orchestrator_agent/
    │   ├── smia_orchestrator_starter.py    ← launcher: creates ExtensibleSMIAAgent + registers OrchestratorDispatchBehaviour
    │   └── orchestrator_dispatch_behaviour.py ← FIPA-CNP initiator: discovery, CFP, winner selection, result forwarding
    └── smia_operator_agent/
        ├── operator_gui_behaviours.py      ← GUI behaviours (mounted into smia-operator container)
        ├── operator_gui_logic.py           ← GUI logic
        └── htmls/                          ← GUI HTML templates
```

**CRITICAL:** Only `.aasx` files in `my_models/aas/`. Any other file causes smia-operator GUI to crash (500 error during AAS discovery).

---

## 7. Docker Compose Services (CURRENT — 8 services)

```
deploy:  docker compose -f my_models/docker-compose.yml up -d
stop:    docker compose -f my_models/docker-compose.yml down
logs:    docker compose -f my_models/docker-compose.yml logs -f smia-machine0 smia-orchestrator
reset:   docker compose -f my_models/docker-compose.yml down -v   ← wipes ejabberd DB
```

| Service | Image / Build | Role | Port |
|---|---|---|---|
| `ejabberd` | `ghcr.io/processone/ejabberd` | XMPP broker; auto-registers all agents via CTL_ON_CREATE | 5222 |
| `mosquitto-central` | `eclipse-mosquitto:2` | MQTT broker; bridges to fischertechnik machine | 1883 |
| `nodered` | `nodered/node-red:latest` | HTTP→MQTT bridge; loads flows from `./nodered/flows.json` | 1880 |
| `smia-machine0` | `docker/smia-machine/Dockerfile` | Machine agent (SMIA_agent@ejabberd), LEGO_factory_case0.aasx | — |
| `smia-machine1` | `docker/smia-machine/Dockerfile` | Machine agent (smia_machine1@ejabberd), LEGO_machine1_case0.aasx | — |
| `smia-machine2` | `docker/smia-machine/Dockerfile` | Machine agent (smia_machine2@ejabberd), LEGO_machine2_case0.aasx | — |
| `smia-orchestrator` | `docker/smia-orchestrator/Dockerfile` | Orchestrator (smia_orch@ejabberd), SMIA_orchestrator.aasx | — |
| `smia-operator` | `additional_tools/.../Dockerfile` | Operator web GUI (operator001@ejabberd) | 10000 |

All services share the `smia-net` Docker bridge network — Docker DNS resolves service names (`ejabberd`, `nodered`, `mosquitto-central`).

**CRITICAL:** Use `docker compose` (v2, with space). NOT `docker-compose` (v1 hyphen — crashes with `KeyError: 'ContainerConfig'`).

### Custom Dockerfile pattern (machine and orchestrator)

Both custom images share the same 3-layer pattern:
```dockerfile
FROM ekhurtado/smia:latest-alpine          # Python + SMIA already installed
COPY src/smia/agents/smia_agent.py /tmp/   # stage patch files
RUN SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    cp /tmp/smia_agent_patch.py "$SMIA_PKG/agents/smia_agent.py"   # apply patch
COPY additional_tools/extended_agents/smia_XXX_agent/smia_XXX_starter.py /
COPY additional_tools/extended_agents/smia_XXX_agent/smia_XXX_behaviour.py /
WORKDIR /    # makes / the Python working directory → imports resolve
CMD ["python3", "-u", "smia_XXX_starter.py"]   # override default SMIA launcher
```

Build is needed after any `.py` file change: `docker compose -f my_models/docker-compose.yml build smia-machine0 smia-orchestrator`

---

## 8. AASX Models — Structure (all 5 files)

### 8.1 Machine AASXs (LEGO_factory_case0, LEGO_machine1_case0, LEGO_machine2_case0)

All three have the same structure (with different UUIDs, JIDs, and color values):

```
AAS: LEGO_factory (or LEGO_machine1, LEGO_machine2)
    AAS id: urn:uuid:6475_0111_2062_9689 (machine0)
            urn:uuid:6475_0111_2062_0001 (machine1)
            urn:uuid:6475_0111_2062_0002 (machine2)
    └── Submodels:
        1. SubmodelWithCapabilitySkillOntology
               └── CSS ConceptDescriptions (class definitions)

        2. AssetInterfacesDescription (AID)
               └── InterfaceHTTP
                   ├── EndpointMetadata
                   │   ├── base = "http://nodered:1880"   (wot#baseURI)
                   │   └── contentType = "application/json"
                   └── InteractionMetadata
                       └── actions
                           ├── pickPiece  (ActionAffordance)
                           │   ├── forms: href=/smia/lego/pick, method=POST
                           │   └── input: color (xs:string), position (xs:int)
                           └── placePiece (ActionAffordance)
                               └── forms: href=/smia/lego/place, method=POST
               └── Interface_00  (agent service interface for machineAvailValue)
                   └── InteractionMetadata
                       └── actions
                           └── machineAvailValue  (ActionAffordance)

        3. CapabilitiesAndSkills
               ├── Capability_PickPiece (semanticId: css-smia#AssetCapability)
               │   ├── qualifier: hasLifecycle=OFFER (semanticId: css-smia#hasLifecycle)
               │   └── color (Property xs:string, value: "red"|"blue"|"white")
               ├── Capability_PlacePiece (same pattern)
               ├── Skill_PickPiece (Property xs:string)
               │   └── qualifier: type=SkillImplementationType, value=OPERATION
               │       semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType
               ├── Skill_PlacePiece (Property xs:string, same)
               └── Skill_NegAvailability (Property xs:string)
                   └── qualifier: type=SkillImplementationType, value=OPERATION
                       semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType

        4. SemanticRelationships
               ├── rel_CapPick_isRealizedBySkill_SkillPick
               │   semanticId: http://www.w3id.org/hsu-aut/css#isRealizedBy
               │   first: Capability_PickPiece  second: Skill_PickPiece
               ├── rel_CapPlace_isRealizedBySkill_SkillPlace
               │   semanticId: ...#isRealizedBy
               │   first: Capability_PlacePiece  second: Skill_PlacePiece
               ├── rel_SkillPick_hasSkillInterface
               │   semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService
               │   first: Skill_PickPiece  second: AID/.../pickPiece
               ├── rel_SkillPlace_hasSkillInterface
               │   semanticId: ...#accessibleThroughAssetService
               │   first: Skill_PlacePiece  second: AID/.../placePiece
               └── rel_SkillNegAvail_agentSvc
                   semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService
                   first: Skill_NegAvailability  second: AID/Interface_00/.../machineAvailValue

AAS: SMIA_agent (or SMIA_machine1, SMIA_machine2)
    └── Submodel: SoftwareNameplate
        └── SoftwareNameplateInstance
            ├── InstanceName: SMIA_agent (machine0) / smia_machine1 / smia_machine2
            ├── InstalledVersion: 0.3.1
            └── ...
```

**CRITICAL IRI casing:** All three RelationshipElement semanticIds use lowercase IRIs. Capital letters cause silent Track 3 failures (no OWL link → `NoneType` crash at negotiation).

### 8.2 Orchestrator AASX (SMIA_orchestrator.aasx)

```
AAS: SMIA_orchestrator
    AAS id: urn:uuid:8888_0001_2026_0001
    └── Submodels:
        1. SubmodelWithCapabilitySkillOntology
        2. CapabilitiesAndSkills
               ├── Capability_PickPiece (semanticId: css-smia#AgentCapability)  ← AgentCapability, not AssetCapability!
               │   └── qualifier: hasLifecycle=OFFER
               └── Skill_Orchestrate_PickPiece (Property xs:string)
        3. SemanticRelationships
               └── rel_CapPick_isRealizedBySkill_Orch
                   semanticId: ...#isRealizedBy
                   first: Capability_PickPiece  second: Skill_Orchestrate_PickPiece
        4. SoftwareNameplate
               └── SoftwareNameplateInstance
                   ├── InstanceName: smia_orch@ejabberd  ← MUST include @ejabberd domain!
                   └── InstalledVersion: 0.3.1

AAS: SMIA_orch_agent
    └── Submodel: SoftwareNameplate only
```

**Why `AgentCapability` for orchestrator?** The orchestrator does not directly operate a physical asset — it coordinates other agents. `AgentCapability` = function of the DT agent itself (negotiation, coordination). `AssetCapability` = function inherent to a physical machine.

**Why `InstanceName: smia_orch@ejabberd`?** The operator GUI parses `InstanceName` to look up the SMIA version and decide the FIPA-ACL message format. Without `@ejabberd` domain, JID lookup fails → returns `None` → version `(0,0,0)` < `(0,2,4)` → old format used → orchestrator doesn't recognize the message.

### 8.3 Operator AASX (SMIA_Operator_article.aasx)

Standard operator AASX from the SMIA examples. The operator agent scans all `.aasx` files in `aas/` and presents discovered SMIAs in the GUI.

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
    │    ← Case 0 and machine agents use this
    │
    └──► css-smia:AgentCapability    ← AGENT capabilities
         e.g. Orchestrate_PickPiece — functions of the DT agent itself
         ← Orchestrator uses this

css:Capability ──isRealizedBy──► css:Skill
                                     │
                                     ├──accessibleThroughAssetService──► css:SkillInterface
                                     │  → PHYSICAL execution via AssetConnection (HTTP)
                                     │  → pick/place skills use this
                                     │
                                     └──accessibleThroughAgentService──► css:SkillInterface
                                        → AGENT execution via Python method (agent service)
                                        → Skill_NegAvailability uses this
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
At boot, after creating an OWL instance from an AAS element, SMIA reads all `owl:DatatypeProperty` declarations whose `rdfs:domain` includes the instance's class. For each such IRI, it calls `get_qualifier_value_by_semantic_id(iri)` → finds the qualifier whose `semanticId` matches → reads its `value` → populates the OWL attribute. If no qualifier has a matching `semanticId` → `AASModelReadingError` → OWL instance attribute stays empty → FIPA-CNP negotiation crashes with `NoneType` error.

**Two lookup mechanisms for qualifiers:**
| Mechanism | Method | Key used | Used for |
|---|---|---|---|
| By `type` string | `get_qualifier_by_type('SkillImplementationType')` | `qualifier.type` | Direct capability validation (Case 0) |
| By `semanticId` IRI | `get_qualifier_value_by_semantic_id(iri)` | `qualifier.semanticId` | OWL instance population (required for FIPA-CNP) |

**The three CSS qualifiers:**

| type string | OWL DatatypeProperty IRI | Required semanticId |
|---|---|---|
| `hasLifecycle` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasLifecycle` | Yes (in preset) |
| `SkillImplementationType` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` | Yes — **NOTE: type ≠ OWL property name** |
| `hasCondition` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasCondition` | Yes (in preset) |

Note: No `ConceptDescription` is needed in the AASX package — the qualifier semanticId is an `ExternalReference` (GlobalReference) pointing to an OWL IRI. SMIA does plain string comparison (`check_semantic_id_exist()` in `extended_base.py:14-29`).

### CSS semantic chains

**Case 0 — Direct execution:**
```
Capability_PickPiece (AssetCapability, OFFER, color="red")
    ──isRealizedBy──►  Skill_PickPiece (hasImplementationType=OPERATION)
                           ──accessibleThroughAssetService──►
                               AID/InterfaceHTTP/actions/pickPiece
                                   ──► HTTP POST nodered:1880/smia/lego/pick
```

**Case 1 — Negotiation criterion:**
```
Skill_NegAvailability (hasImplementationType=OPERATION)
    ──accessibleThroughAgentService──►
        AID/Interface_00/actions/machineAvailValue
            ──► Python: await get_machine_availability()
                    ──► async GET nodered:1880/smia/lego/availability → 1.0 or 0.0
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

### 11.1 `smia_agent.py` — asset connection object-identity bug

**Location in container:** Applied via `RUN` in both Dockerfiles at build time (version-independent path detection).
**Bug:** `get_asset_connection_by_model_reference()` matched AID references using Python object identity. The reference obtained during skill execution was a different Python instance from the one stored during initialization → lookup returned `None` → no HTTP call made → crane never moved.
**Fix:** Added two comparison strategies: string comparison (`str(conn_ref) == str(asset_connection_ref)`) and key-tuple comparison (normalize `(type, value)` tuples).
**Status:** Upstream PR needed. Applied as build-time patch in both Dockerfiles.

### 11.2 `acl_handling_behaviour.py` — orchestrator race condition

**Location in container:** Applied via `RUN` in the orchestrator Dockerfile at build time.
**Bug:** When an operator sends a `css-service` REQUEST to the orchestrator, `ACLHandlingBehaviour` and `OrchestratorDispatchBehaviour` both check the inbox concurrently. `ACLHandlingBehaviour` sees the message before `OrchestratorDispatchBehaviour` reserves it → both behaviours handle the same message.
**Fix:** Early return in `ACLHandlingBehaviour` for `css-service` ontology messages when `pending_orchestrations` attribute exists (orchestrator-only attribute). Machine agents don't have `pending_orchestrations` so the patch is transparent for them.
**Status:** Applied as build-time patch in orchestrator Dockerfile only.

---

## 12. Custom Extensions (TFG Contribution)

### 12.1 `smia_machine_starter.py` — machine launcher

Replaces the default SMIA launcher (`smia_docker_starter.py`) for machine agents. Creates `ExtensibleSMIAAgent` and registers the `machineAvailValue` agent service:
```python
smia_agent = ExtensibleSMIAAgent(...)
smia_agent.add_new_agent_service('machineAvailValue', get_machine_availability)
smia_agent.start()
```

### 12.2 `smia_machine_agent_services.py` — availability agent service

Python coroutine `get_machine_availability()` registered as agent service `machineAvailValue`.
- Called by SMIA's `HandleNegotiationBehaviour` when processing a FIPA-CNP CFP
- Makes async HTTP GET to `http://nodered:1880/smia/lego/availability`
- Returns `1.0` (machine free) or `0.0` (busy)
- SMIA uses this as the `negValue` in FIPA-CNP negotiation

Why an agent service (not AID asset service): availability is a dynamic computed value from Node-RED state, not a static AAS-described endpoint. Agent service keeps the AID clean (only pick/place HTTP actions).

### 12.3 `smia_orchestrator_starter.py` — orchestrator launcher

Creates `ExtensibleSMIAAgent` and registers `OrchestratorDispatchBehaviour` as an agent capability:
```python
smia_agent = ExtensibleSMIAAgent(...)
smia_agent.add_new_agent_capability(OrchestratorDispatchBehaviour)
smia_agent.start()
```

### 12.4 `orchestrator_dispatch_behaviour.py` — FIPA-CNP initiator

**What the base SMIA provides (responder side):**
Machine agents built-in `HandleNegotiationBehaviour` handles CFPs, computes `negValue`, wins or loses.

**What this class provides (initiator side — the TFG contribution):**
1. **AAS discovery:** scans all `.aasx` files in the configured folder; reads each machine's JID from `SoftwareNameplate.InstanceName` and capability color from `Capability_PickPiece.color`
2. **Color routing (Phase 1):** filters machines by `color == requested_color`; maps color to warehouse slot position
3. **CFP dispatch (Phase 2):** builds and sends the negotiation CFP to eligible machines with correct `negCriterion` IRI, `negTargets`, `negRequester`, and `skillParams`
4. **Winner reception:** awaits `INFORM({winner: True})` from the winning machine
5. **Execution delegation (Phase 3):** sends a direct capability REQUEST to the winner with `position` in `skillParams`
6. **Result forwarding (Phase 4):** receives INFORM from winner, forwards to operator

---

## 13. Node-RED Flows

**Endpoints exposed by Node-RED:**

| Endpoint | Method | Purpose |
|---|---|---|
| `/smia/lego/pick` | POST | Execute pick: extracts `position`, publishes MQTT |
| `/smia/lego/place` | POST | Execute place: extracts `position`, publishes MQTT |
| `/smia/lego/availability` | GET | Returns `1.0` (free) or `0.0` (busy) |

**MQTT topic:** `vicom/61/piso_0/lab/lego/commands`
**MQTT payload format:** `bandera_custom:<position>` (position 0–8)

The Node-RED container loads `./nodered/flows.json` on startup. The MQTT broker node inside the flow points to `mosquitto-central:1883` (Docker DNS resolves automatically).

---

## 14. Deployment Quick Reference

```bash
# First time — build custom images
docker compose -f my_models/docker-compose.yml build

# Start all services
docker compose -f my_models/docker-compose.yml up -d

# Start incrementally (recommended for debugging)
docker compose -f my_models/docker-compose.yml up -d xmpp-server mosquitto-central nodered
docker compose -f my_models/docker-compose.yml up -d smia-machine0 smia-machine1 smia-machine2 smia-operator
docker compose -f my_models/docker-compose.yml up -d smia-orchestrator

# Logs
docker compose -f my_models/docker-compose.yml logs -f smia-machine0 smia-machine1 smia-machine2 smia-orchestrator
docker compose -f my_models/docker-compose.yml logs -f smia-operator

# Stop (keep volumes)
docker compose -f my_models/docker-compose.yml down

# Full reset (wipe ejabberd DB — needed after password changes or auth lockouts)
docker compose -f my_models/docker-compose.yml down -v
docker compose -f my_models/docker-compose.yml up -d
```

### Healthy startup signatures

| Service | Expected log |
|---|---|
| ejabberd | `Starting ejabberd ... done` |
| smia-machine0/1/2 | `AAS model initialized.` + `Analyzed skills: ['Skill_PickPiece', 'Skill_PlacePiece', 'Skill_NegAvailability']` |
| smia-orchestrator | `AAS model initialized.` + `Analyzed capabilities: ['Capability_PickPiece']` |
| smia-operator | `Starting web server on port 10000` |
| Running state | `No message received within 10 seconds on SMIA (ACLHandlingBehaviour)` — normal idle polling |

**Operator GUI:** http://localhost:10000/smia_operator

---

## 15. Troubleshooting

| Symptom | Most likely cause | Fix |
|---|---|---|
| `KeyError: 'ContainerConfig'` on compose up | Docker Compose v1 | Use `docker compose` (space, v2) |
| ejabberd loops, never healthy | ejabberd.yml syntax error or port conflict | `docker logs ejabberd` |
| SMIA never reaches StateRunning (MRO error) | Skills defined as SMC | Redefine Skills as Property in AASX PE |
| Operator GUI 500 on Load | Non-AASX file in `aas/` | Remove non-.aasx files from `aas/` |
| Submit spins (no HTTP in logs) | smia_agent.py patch not applied | `docker compose build smia-machine0`; check Dockerfile RUN log |
| HTTP OK but crane does not move | MQTT bridge down | Check Node-RED debug + `bridge.conf` address |
| XMPP auth failure / IP blacklisting | Password mismatch between `.env` and ejabberd DB | `docker compose down -v && up -d` (full ejabberd DB reset) |
| `HandleNegotiationBehaviour: 'NoneType' object is not iterable` | Track 3 OWL link missing — `rel_SkillNegAvail_agentSvc` semanticId has wrong casing | Check IRI: must be exactly `...#accessibleThroughAgentService` (lowercase 'a') |
| Qualifier `hasImplementationType not found` at boot | Qualifier semanticId is `https://` instead of `http://` | Fix in AASX PE: `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` |
| Orchestrator handles request but no CFP sent | Color not extracted from skillParams | Params keys are IRIs (`http://...css#color`), not bare strings; check `_get_skill_param()` |
| Operator shows orchestrator alongside machines in GUI | Expected behavior — orchestrator has `AgentCapability_PickPiece` → appears in discovery | Select `smia_orch@ejabberd` to trigger FIPA-CNP; selecting a machine gives direct execution |
| SCRAM-SHA-512-PLUS warnings in ejabberd logs | Harmless — SPADE tries channel-binding variants first, falls through to plain SCRAM-SHA-512 | No action needed |

---

## 16. Validation Metrics (paper §5.2.3)

| Metric | Value | Context |
|---|---|---|
| Self-configuration time (robotic agent, 21 CSS elements) | **6.73 s** avg | Paper scenario |
| Self-configuration time (operator agent, 7 CSS elements) | **3.39 s** | Paper scenario |
| Messages per direct task execution | **2** (REQUEST + INFORM) | Case 0 |
| Messages per distributed negotiation | **5** (2n+1, n=2 agents) | Base SMIA paper |
| Total response time | **0.034–0.098 s** | Operator request → action complete |

Case 1 message count with 3 machines: 1 (operator→orch) + 3 (CFP→machines) + 3 (PROPOSE/INFORM within machines) + 1 (INFORM winner→orch) + 1 (orch→winner REQUEST) + 1 (INFORM winner→orch) + 1 (orch→operator INFORM) = **11 messages** total.

---

## 17. Key Identifiers and Credentials

| Item | Value |
|---|---|
| fischertechnik AAS id | `urn:uuid:6475_0111_2062_9689` |
| machine1 AAS id | `urn:uuid:6475_0111_2062_0001` |
| machine2 AAS id | `urn:uuid:6475_0111_2062_0002` |
| orchestrator AAS id | `urn:uuid:8888_0001_2026_0001` |
| Machine0 XMPP JID | `SMIA_agent@ejabberd` |
| Machine1 XMPP JID | `smia_machine1@ejabberd` |
| Machine2 XMPP JID | `smia_machine2@ejabberd` |
| Orchestrator XMPP JID | `smia_orch@ejabberd` |
| Operator XMPP JID | `operator001@ejabberd` |
| Passwords | See `.env` file (gitignored) or `.env.example` |
| DIDA Central IP | `192.168.155.10` |
| Node-RED internal URL | `http://nodered:1880` (Docker DNS) |
| Node-RED external URL | `http://192.168.155.10:1880` (if not using container) |
| MQTT topic | `vicom/61/piso_0/lab/lego/commands` |
| MQTT payload format | `bandera_custom:<position>` (position 0–8) |
| Operator GUI | `http://localhost:10000/smia_operator` |

---

## 18. Documents Index

| File | Purpose | When to use |
|---|---|---|
| `CLAUDE.md` (this file) | AI assistant context — complete project state | First thing to read in any new session |
| `doc_case0.md` | Full technical reference — AASX PE tutorial, all IDs, deployment, troubleshooting | Replication, technical questions |
| `memoire.md` | Formal TFG academic document base — SMIA theory, AAS, CSS, architecture | Academic writing, TFG base |
| `playBook.md` | Operational runbook — verified runtime values, step-by-step | Day-to-day operations |

---

## 19. What Has Been Custom-Implemented (TFG Contribution vs Framework)

| Component | Type | Description |
|---|---|---|
| `smia_machine_starter.py` | **New — TFG** | ExtensibleSMIAAgent launcher for machines; registers agent service |
| `smia_machine_agent_services.py` | **New — TFG** | `machineAvailValue` async service: GET Node-RED availability → 0.0/1.0 |
| `smia_orchestrator_starter.py` | **New — TFG** | ExtensibleSMIAAgent launcher for orchestrator; registers OrchestratorDispatchBehaviour |
| `orchestrator_dispatch_behaviour.py` | **New — TFG** | FIPA-CNP initiator: AAS discovery, color routing, CFP, winner selection, execution delegation |
| All `.aasx` machine files | **New — TFG** | AAS models for 3 machines + orchestrator; CSS-enriched with full ontology wiring |
| `smia_agent.py` (patched) | **SMIA bug fix** | Asset-connection object-identity lookup; pending upstream PR |
| `acl_handling_behaviour.py` (patched) | **SMIA bug fix** | Race condition between ACLHandlingBehaviour and OrchestratorDispatchBehaviour |
| `docker-compose.yml`, Dockerfiles, `flows.json`, `ejabberd.yml` | **Infrastructure — TFG** | Full containerized deployment stack |

**What SMIA provides out of the box (we do NOT reimplement this):**
- `HandleCapabilityBehaviour` — capability execution (skill resolution → AID → HTTP)
- `HandleNegotiationBehaviour` — FIPA-CNP responder (compute negValue via agent service, send PROPOSE/INFORM)
- `NegotiatingBehaviour` — peer PROPOSE exchange and winner self-determination
- `AASInitializationBehaviour` — all 3 tracks of self-configuration
- `ACLHandlingBehaviour` — FIPA-ACL message dispatch
- OWL ontology management via `owlready2`
- AAS model parsing via `basyx-python-sdk`
