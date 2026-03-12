# CLAUDE.md — Full Project Context for Case 0

> This file gives Claude (or any AI assistant) the complete picture of what this project is, what has been implemented, what works, what is patched, and how to help with it. Read this before anything else.
>
> **Primary scientific source:** E. Hurtado et al., *"Self-configurable Manufacturing Industrial Agents (SMIA): a standardized approach for digitizing manufacturing assets"*, Journal of Industrial Information Integration 47 (2025) 100915. DOI: 10.1016/j.jii.2025.100915

---

## 1. Project Overview

**What:** Bachelor's thesis (TFG — Trabajo de Fin de Grado) at **Universidad de Deusto**.
**Title:** "Flexible manufacturing based on digital twins using AAS and CSS model"
**Author:** Andrés Felipe Fierro Fonseca — intern at **Vicomtech**, department: **Data Intelligence for Industry (DII)**.
**SMIA framework:** Developed by UPV/EHU (Ekaitz Hurtado et al.) — this TFG uses their framework to implement Case 0.
**Status:** Case 0 is **fully working end-to-end** as of 2026-03-04.

**What we are proving:** A manufacturing agent (SMIA) can configure itself entirely from a standard digital twin (AAS enriched with CSS ontology) and execute physical actions on a real factory machine — with **zero asset-specific code** inside the agent. This directly validates requirement R2 (automated self-configuration) and R7 (separation between physical asset and Digital Twin) from the SMIA paper.

---

## 2. What is SMIA

**SMIA** = Self-configurable Manufacturing Industrial Agents.
- Open-source Python framework: GitHub `https://github.com/ekhurtado/SMIA`
- Docker image: `ekhurtado/smia:latest-alpine`
- Authors: Ekaitz Hurtado, Arantzazu Burgos, Aintzane Armentia, Oskar Casquero — UPV/EHU
- Papers: DOI 10.1016/j.jii.2025.100915 (JIII) · DOI 10.1016/j.simpa.2025.100807 (Software Impacts)

### 2.1 Dual-layer architecture (paper §3)

SMIA is a **dual-layer solution**:
1. **Methodology layer** — a process for characterizing proactive AAS (Type 3) by semantically enriching their descriptions with the CSS ontology via `semanticId` fields
2. **Technology layer** — a software toolchain that automatically generates executable Digital Twins as FIPA-compliant industrial agents using SPADE, from those enriched AAS descriptions

The key conceptual distinction: **"The AAS is treated as a static, administrative model, while the DT represents its dynamic, operational counterpart"** (paper §3). SMIA agents are not wrappers — they are functional DTs that interpret standardized descriptions and expose capabilities to the system.

### 2.2 Design requirements (paper Table 1)

| # | Requirement | Justification |
|---|---|---|
| R1 | Compliance with industry integration models | Integrate heterogeneous assets using AAS and CSS standards |
| R2 | Automated self-configuration of DTs | Reduce human intervention; align with AAS Type 3 specifications |
| R3 | Integration of physical assets via standard interfaces | Interpret physical/logical asset interfaces from the AID submodel |
| R4 | Adaptability to flexible/reconfigurable architectures | Support runtime reconfiguration via the CSS model |
| R5 | Inclusion in distributed and decentralized systems | Resilience, scalability, decentralization per Industry 4.0 |
| R6 | P2P communication with I4.0-compliant language | Autonomous cooperation, negotiation, coordination via FIPA-ACL |
| R7 | Separation between physical asset and Digital Twin | Functional layer independent of asset hardware specifics |
| R8 | Modular and extensible software design | Maintainability and scalability across industrial contexts |

### 2.3 AAS Types — why SMIA implements Type 3 (paper §2.1)

| Type | Interaction | Description |
|---|---|---|
| Type 1 | Passive | File exchange — AASX/XML/JSON read by external applications |
| Type 2 | Reactive | Responds to REST/API service requests from external systems |
| **Type 3** | **Proactive** | **Peer-to-peer I4.0 communication, FIPA-ACL, autonomous behaviour** ← SMIA |

SMIA implements Type 3: agents communicate directly, negotiate, coordinate, and act without supervision.

### 2.4 FSM States (paper Fig. 5) — 4 states

```
[Switched off]
    │ switch on
    ▼
┌─────────────────────────────────────┐
│  BOOTING                            │  ← self-configuration happens here
│  - Boot behavior (init SPADE)       │
│  - AAS model init behavior          │
│    (load AASX + OWL, create         │
│     AssetConnections, instantiate   │
│     CSS OWL classes, link           │
│     relationships)                  │
└──────────────┬──────────────────────┘
               │ booted
               ▼
┌────────────────────────────────────────────────────────────┐
│  RUNNING                                                   │
│  - Service management (CyclicBehaviour)                    │
│  - Capability management (CyclicBehaviour +               │
│    OneShotBehaviour per request)                           │
└──────────────┬──────────────────────┬──────────────────────┘
               │ non-operational      │ stopping request
               │ asset                │
               ▼                      ▼
┌─────────────────────┐   ┌────────────────────────┐
│  IDLE               │   │  STOPPING              │
│  (asset unavailable)│   │  Finalization (end     │
│  - Idle behavior    │   │  behavior)             │
│  ← operational ─── ─ ─  └────────────────────────┘
│    asset                       │ stopped
└─────────────────────┘          ▼
                             [Switched off]
```

White boxes = IAMS Core behaviors; Green boxes = SMIA Customization (AAS init + capability handling).

### 2.5 Self-configuration process (paper Fig. 8) — 3 parallel tracks during Booting

All executed by `AASInitializationBehaviour` during the Booting state:

**Track 1 — Asset interfaces (AID submodel):**
```
Read AssetInterfacesDescription submodel (BaSyx SDK)
    → Extract Interface SubmodelElements
    → Create AssetConnection instance for each interface
```

**Track 2 — CSS-enriched AAS elements:**
```
Loop for each CSS class IRI:
    Get AAS SubmodelElements by semanticId (BaSyx SDK)
    Validate element against CSS ontology (OWLready2)
    If valid → Create CSS OWL ontology instance (OWLready2)
```

**Track 3 — CSS relationships:**
```
Loop for each CSS ObjectProperty IRI:
    Get AAS RelationshipElements by semanticId (BaSyx SDK)
    Validate against CSS ontology (OWLready2)
    If valid → Link CSS OWL instances together (OWLready2)
```

Result: an executable semantic network of Capabilities, Skills, and AssetConnections ready for runtime.

### 2.6 Capability request handling (paper Fig. 9)

When a FIPA-ACL `REQUEST` arrives:
1. `ACLHandlingBehaviour` (CyclicBehaviour) receives it; checks `ontology` field
2. If `ontology = CSSRequest` → spawns `HandleCapabilityBehaviour` (OneShotBehaviour)
3. Validates capability name + constraints against the CSS OWL ontology
4. If skill not specified → SMIA infers the matching skill via `isRealizedBy`
5. If skill interface not specified → SMIA gets it via `accessibleThroughAssetService`
6. Determines executor: **asset service** → HTTP via `AssetConnection`; **agent service** → Python method
7. Executes; sends FIPA-ACL `INFORM` with result + execution timeline

### 2.7 FIPA-ACL message structure for CSS requests (paper Fig. 16)

```
Field         | Value for CSS capability request
--------------|-----------------------------------------
to            | SMIA_agent@ejabberd
sender        | operator001@ejabberd
body          | {"skill": "Skill_PickPiece",
              |  "constraints": [],
              |  "params": {"position": 0}}
performative  | Request
ontology      | CSSRequest      ← critical: tells SMIA this is a CSS request
              |                   (other values: SvcRequest, Negotiation)
```

### 2.8 Extensibility (paper Fig. 10 — ExtensibleSMIAAgent)

Three extension hooks on `ExtensibleSMIAAgent`:
- `add_new_asset_connection(interface_aas_ref, handler)` — new physical protocol support (e.g., OPC UA, MQTT)
- `add_new_agent_capability(handler)` — new AgentCapabilities (negotiation, planning, learning)
- `add_new_agent_service(service_id, executable_method)` — new internal agent services

### 2.9 Key dependencies

- `spade 4.0.3` — Python multi-agent framework (XMPP-based)
- `basyx-python-sdk 1.2.1` — AAS model parsing and manipulation
- `owlready2 0.48` — OWL ontology loading and reasoning
- `python 3.12` (inside container)

---

## 3. What is Case 0

**Physical asset:** fischertechnik Training Factory Industry 4.0 24V (ref. 554868)
- Product: https://www.fischertechnik.de/es-es/productos/industria-y-universidades/modelos-de-simulacion/554868-training-factory-industry-4-0-24v
- **Scope:** ONLY the **warehouse crane (Hochregallager)** is wired in Case 0
- NOT in scope: the central crane with ventose (vacuum suction cup) — physically present but not connected

**What Case 0 does:** An operator clicks a button in the SMIA Operator web GUI → the warehouse crane moves to pick a piece from a slot — with zero asset-specific code in SMIA.

**Naming note:** Files use `LEGO_factory`, `/smia/lego/pick`, `vicom/61/piso_0/lab/lego/commands` — historical artifacts from early development. They physically refer to the fischertechnik factory. Do not rename; they appear in code and running configs.

---

## 4. System Architecture

### 4.1 Three physical machines

| # | Machine | IP | Role |
|---|---|---|---|
| 1 | Linux dev machine (this repo) | localhost | Docker Compose: `ejabberd` + `smia` + `smia-operator` |
| 2 | DIDA Central machine | 192.168.155.10 | Node-RED (port 1880) + Mosquitto broker (port 1883) |
| 3 | fischertechnik Windows machine | lab network | Receives MQTT, runs warehouse crane control software |

### 4.2 End-to-end data flow

```
[Browser]
    │ HTTP :10000
    ▼
[smia-operator container]  — operator agent with GUI, scans aas/ for SMIAs
    │ FIPA-ACL REQUEST (performative=Request, ontology=CSSRequest) over XMPP :5222
    ▼
[ejabberd container]  — XMPP routing between agents
    │ routes to SMIA_agent@ejabberd
    ▼
[smia container]  — manufacturing agent (SMIA Type 3 proactive DT)
    │ 1. Capability_PickPiece → isRealizedBy → Skill_PickPiece
    │ 2. Skill_PickPiece → accessibleThroughAssetService → AID action pickPiece
    │ 3. AID: base=http://192.168.155.10:1880, href=/smia/lego/pick, method=POST
    │ HTTP POST {"color":"...", "position":...}
    ▼
[Node-RED — DIDA Central 192.168.155.10:1880]
    │ Function: extract position, default=0, build payload
    │ MQTT publish QoS=1  topic=vicom/61/piso_0/lab/lego/commands
    ▼
[Mosquitto central — DIDA] → MQTT bridge → [Mosquitto local — fischertechnik]
    ▼
[Warehouse crane macro — picks from slot <position>]
```

### 4.3 Architecture decisions (summary — full justification in `memoire.md §14.7`)

**Docker Compose:** Solves shared XMPP infrastructure — all services need the same `ejabberd` hostname. Docker bridge network provides automatic DNS. Weakness: single host SPOF.

**Edge + Central:** Per-machine edge stack (mosquitto + node-red + postgres) for isolation and local processing. DIDA central aggregates. Trade-off: SMIA's AID points to central (192.168.155.10:1880), not a fischertechnik edge, so central is in the critical command path for Case 0.

---

## 5. File Structure

```
SMIA/
├── my_models/                              ← ALL Case 0 deployment files
│   ├── CLAUDE.md                           ← this file
│   ├── docker-compose.yml                  ← deploy with: docker compose up -d
│   ├── smia-initialization.properties      ← SMIA config (XMPP, AAS, ontology)
│   ├── aas/
│   │   ├── LEGO_factory_case0.aasx         ← main AAS model (fischertechnik factory)
│   │   └── SMIA_Operator_article.aasx      ← operator agent's own AAS (from repo examples)
│   ├── ontology/
│   │   └── CSS-ontology-smia.owl           ← CSS ontology (also embedded inside AASX)
│   ├── xmpp_server/
│   │   └── ejabberd.yml                    ← ejabberd configuration
│   ├── flow_dida_central_lego.json         ← Node-RED flow (import on DIDA central)
│   ├── doc_case0.md                        ← full technical reference + AASX PE tutorial
│   ├── memoire.md                          ← formal TFG academic document base
│   ├── presentation_case0.md               ← colleague presentation (33 slides + appendices)
│   └── playBook.md                         ← operational runbook
│
├── src/smia/agents/smia_agent.py           ← PATCHED file (mounted into smia container)
│
└── additional_tools/extended_agents/smia_operator_agent/
    ├── operator_gui_behaviours.py          ← mounted into smia-operator container
    ├── operator_gui_logic.py               ← mounted into smia-operator container
    └── htmls/                              ← mounted into smia-operator container
```

**Important:** Only `.aasx` files should be in `my_models/aas/`. Any other file causes the smia-operator GUI to crash with a 500 error during AAS discovery.

---

## 6. Docker Compose Services

```yaml
# deploy: docker compose -f my_models/docker-compose.yml up -d
# stop:   docker compose -f my_models/docker-compose.yml down
# logs:   docker compose -f my_models/docker-compose.yml logs -f smia smia-operator xmpp-server

services:
  xmpp-server:   image: ghcr.io/processone/ejabberd
                 # auto-registers: SMIA_agent@ejabberd:asd  operator001@ejabberd:gcis1234
                 # healthcheck: waits for port 5222

  smia:          image: ekhurtado/smia:latest-alpine
                 AAS_MODEL_NAME=LEGO_factory_case0.aasx
                 AAS_ID=urn:uuid:6475_0111_2062_9689      ← filters for fischertechnik shell
                 AGENT_ID=SMIA_agent@ejabberd
                 AGENT_PASSWD=asd
                 volumes: ./aas → /smia_archive/config/aas
                          ../src/smia/agents/smia_agent.py → [patched override]

  smia-operator: image: ekhurtado/smia-use-cases:latest-operator
                 AAS_MODEL_NAME=SMIA_Operator_article.aasx
                 AGENT_ID=operator001@ejabberd
                 AGENT_PASSWD=gcis1234
                 ports: 10000:10000   ← GUI: http://localhost:10000/smia_operator
```

**CRITICAL:** Use `docker compose` (v2, with space). NOT `docker-compose` (v1 hyphen — crashes with `KeyError: 'ContainerConfig'`).

---

## 7. LEGO_factory_case0.aasx — AAS Model Structure

### 7.1 AAS shells in the package

| AAS idShort | AAS id | Submodels |
|---|---|---|
| `LEGO_factory` | `urn:uuid:6475_0111_2062_9689` | AID, CapabilitiesAndSkills, SemanticRelationships, SubmodelWithCapabilitySkillOntology |
| `SMIA_agent` | `urn:uuid:6373_1111_2062_6896` | SoftwareNameplate only |

`AAS_ID=urn:uuid:6475_0111_2062_9689` filters for the fischertechnik factory shell, not the operator AASX.

### 7.2 Submodel: AssetInterfacesDescription (AID)
semanticId: `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel`

SMIA extends the standard AID with two additional attributes (paper §4.1.1):
- `data-Query`: JSONPath/XPath/regex for extracting specific data from asset responses (not used in Case 0)
- `htv_params`: HTTP request parameters for invocation (not used in Case 0 but available)

```
AssetInterfacesDescription
└── InterfaceHTTP  (semanticId: .../Interface)
    ├── EndpointMetadata  (semanticId: .../EndpointMetadata)
    │   ├── base = "http://192.168.155.10:1880"  (semanticId: wot/td#baseURI)
    │   └── contentType = "application/json"     (semanticId: hypermedia#forContentType)
    └── InteractionMetadata  (semanticId: .../InteractionMetadata)
        └── actions  (SMC)
            ├── pickPiece  (semanticId: wot/td#ActionAffordance)
            │   ├── forms  (SMC, semanticId: wot/td#hasForm)
            │   │   ├── href = "/smia/lego/pick"        (semanticId: hypermedia#hasTarget)
            │   │   └── htv_methodName = "POST"         (semanticId: http#methodName)
            │   └── input  (SMC, semanticId: wot/td#hasInputSchema)
            │       ├── color    (Property xs:string)
            │       └── position (Property xs:int)
            └── placePiece  (semanticId: wot/td#ActionAffordance)
                ├── forms  → href="/smia/lego/place", method=POST
                └── input  → position (xs:int)
```

### 7.3 Submodel: CapabilitiesAndSkills

Capabilities use `css-smia:AssetCapability` (physical machine capabilities) — see §10 for the distinction with `AgentCapability`.

`hasLifeCycle = OFFER` means the capability is being **offered/available** by this asset. Other values: `ASSURANCE` (offered with guarantee), `REQUIREMENT` (capability required from another agent).

```
CapabilitiesAndSkills
├── Capability_PickPiece   (SMC, semanticId: css-smia#AssetCapability)
│   ├── qualifier: hasLifecycle = OFFER    ← capability is offered by this asset
│   └── position (Property xs:int)
├── Capability_PlacePiece  (SMC, same pattern)
├── Skill_PickPiece        ← MUST be Property, NOT SMC (see §8 below)
│   ├── valueType: xs:string
│   └── qualifier: hasImplementationType = OPERATION
└── Skill_PlacePiece       ← same
```

### 7.4 Submodel: SemanticRelationships

4 RelationshipElements — CSS wiring of the fischertechnik warehouse crane capabilities:

| idShort | semanticId | first | second |
|---|---|---|---|
| `rel_CapPick_isRealizedBySkill_SkillPick` | `css#isRealizedBy` | Capability_PickPiece | Skill_PickPiece |
| `rel_CapPlace_isRealizedBySkill_SkillPlace` | `css#isRealizedBy` | Capability_PlacePiece | Skill_PlacePiece |
| `rel_SkillPick_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | Skill_PickPiece | AID/.../pickPiece |
| `rel_SkillPlace_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | Skill_PlacePiece | AID/.../placePiece |

`accessibleThroughAssetService` = the skill is executed by the **physical asset** via HTTP (paper Fig. 4). Compare with `accessibleThroughAgentService` (not used in Case 0) = skill executed by the **agent itself** via an internal Python method.

### 7.5 Embedded files in the AASX package
- `aasx/CSS-ontology-smia.owl` — the CSS ontology (36KB)
- `aasx/smia-initialization.properties` — template only; runtime values come from Docker env vars

---

## 8. CRITICAL: Why Skills Must Be Property Elements (Not SMC)

**Problem:** When Skills are defined as `SubmodelElementCollection`, SMIA tries to create a Python class via multiple inheritance: `ExtendedComplexSkill + ExtendedSubmodelElementCollection`. Both base classes define `HasSemantics` and `Qualifiable` in conflicting MRO orders. Python raises `TypeError: Cannot create a consistent method resolution order (MRO)` during `AASInitializationBehaviour` in the Booting state — the agent never reaches Running.

**Fix:** Define Skills as `Property` elements (valueType: xs:string). SMIA uses `ExtendedSimpleSkill` — no MRO conflict.

**How to spot it:** SMIA logs show `AASInitializationBehaviour` starting but never completing. Never reaches `StateRunning`. Operator GUI Submit button spins forever.

---

## 9. smia_agent.py Patch

**Why it exists:** `get_asset_connection_by_model_reference()` matched AID references using Python object identity. The reference obtained during skill execution was a different Python instance from the one stored during initialization — lookup returned `None`, no HTTP call was made.

**Fix:** Added two comparison strategies:
1. String comparison: `str(conn_ref) == str(asset_connection_ref)`
2. Key-tuple comparison: normalize `(type, value)` tuples from reference key lists

**Applied via:** Docker volume mount overriding the file inside the container image. Verify compatibility whenever pulling a new image version. Long-term fix: upstream PR.

---

## 10. CSS Ontology (paper §3.2 + §4.1.2)

File: `my_models/ontology/CSS-ontology-smia.owl` (also embedded in AASX at `aasx/CSS-ontology-smia.owl`)

**Source:** CaSkade-Automation CSS-ontology v1.0.1 (October 2024), extended by SMIA.
- CaSkade base: `https://github.com/CaSkade-Automation/CSS`
- SMIA extension IRI: `http://www.w3id.org/upv-ehu/gcis/css-smia`
- W3ID permanent identifier: `https://w3id.org/upv-ehu/gcis/css-smia/`

SMIA loads it via `owlready2` during Booting (Track 2 and Track 3 of self-configuration).

### CSS class hierarchy in SMIA (paper Fig. 4)

```
css:Capability  ──isRestrictedBy──►  css:CapabilityConstraint
    │                                    (+hasCondition: constraintCondition)
    │ (superclass)
    ├──► css-smia:AssetCapability   ← PHYSICAL capabilities (Case 0 uses this)
    │    e.g. PickPiece, PlacePiece — functions inherent to the machine
    │
    └──► css-smia:AgentCapability   ← AGENT capabilities (NOT in Case 0)
         e.g. Negotiate, Coordinate — functions of the DT agent itself

css:Capability ──isRealizedBy──► css:Skill
                                     │ (+hasImplementationType)
                                     │ (+hasParameter ──► css:SkillParameter)
                                     │                        (+hasType: parameterType)
                                     │
                                     ├──accessibleThroughAssetService──► css:SkillInterface
                                     │  ← PHYSICAL execution via AssetConnection (HTTP)
                                     │    ← Case 0 uses this
                                     │
                                     └──accessibleThroughAgentService──► css:SkillInterface
                                        ← AGENT execution via Python method
                                          ← Used for AgentCapabilities (future cases)
```

**Case 0 only uses:** `AssetCapability` + `accessibleThroughAssetService` (physical, HTTP execution).
**Future cases (negotiation, coordination)** will add: `AgentCapability` + `accessibleThroughAgentService`.

### Key IRIs (verified from `src/smia/css_ontology/css_ontology_utils.py`)

| Concept | IRI |
|---|---|
| Capability | `http://www.w3id.org/hsu-aut/css#Capability` |
| **AssetCapability** | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` ← use for Capabilities in Case 0 |
| AgentCapability | `http://www.w3id.org/upv-ehu/gcis/css-smia#AgentCapability` ← for agent-side capabilities |
| Skill | `http://www.w3id.org/hsu-aut/css#Skill` |
| isRealizedBy | `http://www.w3id.org/hsu-aut/css#isRealizedBy` |
| **accessibleThroughAssetService** | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` ← Case 0 |
| accessibleThroughAgentService | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` |
| CapabilityConstraint | `http://www.w3id.org/hsu-aut/css#CapabilityConstraint` |
| SkillParameter | `http://www.w3id.org/hsu-aut/css#SkillParameter` |

### Capability lifecycle values
- `OFFER` — this capability is offered/available by this asset ← used in Case 0
- `ASSURANCE` — offered with a quality guarantee
- `REQUIREMENT` — capability required from another agent (used in operator/requester AAS)

### CSS chain in Case 0
```
Capability_PickPiece (AssetCapability, OFFER)
    ──isRealizedBy──►  Skill_PickPiece (hasImplementationType=OPERATION)
                           ──accessibleThroughAssetService──►
                               AID/InterfaceHTTP/actions/pickPiece
                                   ──► HTTP POST 192.168.155.10:1880/smia/lego/pick
```

---

## 11. AID Semantic IDs (verified from `src/smia/utilities/smia_info.py`)

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

## 12. Configuration Files

### smia-initialization.properties
```properties
[DT]
dt.agentID=SMIA_agent@ejabberd   # XMPP JID
dt.password=asd                   # XMPP password
dt.xmpp-server=ejabberd           # Docker container hostname (NOT localhost)

[AAS]
aas.model.serialization=AASX
aas.model.folder=/smia_archive/config/aas   # container-internal path (mounted from ./aas)
aas.model.file=LEGO_factory_case0.aasx

[ONTOLOGY]
ontology.file=CSS-ontology-smia.owl
ontology.inside-aasx=true   # reads .owl from inside the AASX ZIP package
```

The `[DT]` section maps to the `ConfigurationPaths` extension in the Nameplate for Software in Manufacturing submodel (paper §4.1.1). It specifies XMPP credentials and server so SMIA connects to the right ejabberd instance.

### ejabberd.yml (key settings)
- `hosts: [localhost, ejabberd]` — ejabberd responds to both
- `mod_register: ip_access: all` — allows CTL_ON_CREATE auto-registration
- `mod_mqtt: {}` — MQTT over XMPP enabled
- Ports: 5222 (XMPP C2S), 5269 (S2S), 5280 (HTTP), 5443 (HTTPS/WS)

---

## 13. Node-RED Flow (DIDA Central — 192.168.155.10:1880)

File to import: `my_models/flow_dida_central_lego.json`

This is the **AssetConnection** target defined in the AID submodel. It implements requirement R3 (integration of physical assets via standard interfaces) — SMIA uses the AID-described HTTP endpoint; the actual MQTT translation is hidden behind Node-RED.

```
HTTP In (POST /smia/lego/pick)
    → JSON parse
    → Function: position = payload.position || query.position || skillParams.position || 0
                validate 0 ≤ position ≤ 8
                payload = "bandera_custom:" + position
    → MQTT Out (mosquitto-central:1883, topic: vicom/61/piso_0/lab/lego/commands, QoS=1)
    → HTTP Response {"status":"ok", "payload":"bandera_custom:<n>", ...}
```

Test directly (bypass SMIA):
```bash
curl -i -X POST http://192.168.155.10:1880/smia/lego/pick \
  -H 'Content-Type: application/json' -d '{"position":0}'
```

---

## 14. Deployment — Quick Reference

```bash
docker compose -f my_models/docker-compose.yml up -d
docker compose -f my_models/docker-compose.yml ps
docker compose -f my_models/docker-compose.yml logs -f smia smia-operator xmpp-server
docker compose -f my_models/docker-compose.yml down
docker compose -f my_models/docker-compose.yml down -v  # full reset incl. ejabberd DB
```

### Healthy startup log signatures
- **ejabberd:** `Starting ejabberd ... done`
- **smia:** `AAS model initialized.` then `Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']`
- **smia-operator:** `Starting web server on port 10000`

**Operator GUI:** http://localhost:10000/smia_operator → Load → SMIA_agent appears → select Capability → Submit

---

## 15. Troubleshooting Quick Reference

| Symptom | Most likely cause | Fix |
|---|---|---|
| `KeyError: 'ContainerConfig'` on compose up | Docker Compose v1 | Use `docker compose` (space, v2) |
| ejabberd loops, never healthy | ejabberd.yml syntax error or port conflict | Check `docker logs ejabberd` |
| SMIA never reaches StateRunning (MRO error) | Skills defined as SMC | Redefine Skills as Property in AASX PE |
| Operator GUI 500 on Load | Non-AASX file in `my_models/aas/` | Remove backups/XMLs from `aas/` |
| Submit spins (no HTTP in logs) | smia_agent.py patch not mounted | Check volume mount path |
| HTTP OK but crane does not move | MQTT bridge down or wrong topic | Check Node-RED debug + bridge |
| XMPP auth failure | AGENT_PASSWD mismatch | Verify CTL_ON_CREATE matches AGENT_PASSWD |

---

## 16. Validation Metrics (paper §5.2.3)

From the paper's robotic logistics validation scenario (quantitative benchmarks):

| Metric | Value | Context |
|---|---|---|
| Self-configuration time (robotic agent, 21 CSS elements) | **6.73 s** average | Time from startup to Running state |
| Self-configuration time (operator agent, 7 CSS elements) | **3.39 s** | Time from startup to Running state |
| Messages per direct task execution | **2** (REQUEST + INFORM) | Single-agent execution |
| Messages per distributed negotiation | **5** (2n+1, n=2 agents) | Multi-agent negotiation |
| Total response time | **0.034–0.098 s** | Operator request → action complete |

Case 0 has only 4 CSS elements per capability (simpler than the paper's scenario) — expected self-configuration time is well under the paper's benchmarks.

---

## 17. Documents Index

| File | Purpose | When to use |
|---|---|---|
| `CLAUDE.md` (this file) | AI assistant context — full project state + paper-verified theory | First thing to read |
| `doc_case0.md` | Full technical reference — AASX PE tutorial, all IDs, deployment, troubleshooting | Replication, technical questions |
| `memoire.md` | Formal TFG academic document — SMIA theory, AAS, CSS, architecture justification | Academic writing, TFG base |
| `presentation_case0.md` | 33-slide presentation — walkthrough, schemas, architecture decisions | Presentations, demos |
| `playBook.md` | Operational runbook — verified runtime values, step-by-step | Day-to-day operations |
| `SMIA.pdf` | Primary scientific paper (DOI: 10.1016/j.jii.2025.100915) | Theory reference, citation source |

---

## 18. Current Implementation State

### What works ✓
- Full end-to-end: operator GUI → XMPP → SMIA → HTTP → Node-RED → MQTT → warehouse crane
- SMIA self-configures from AAS (validates R2 and R7 from paper)
- CSS ontology tracks resolves Capability → Skill → AID action (validates R1, R3, R4)
- Docker Compose deploys everything one-command (validates R5, R8)

### Known technical debt
- `smia_agent.py` bug fix via Docker volume mount — needs upstream PR
- Central DIDA in critical command path (architectural trade-off — documented in `memoire.md §14.7`)

### What is NOT implemented yet (future cases)
- Case 1: second SMIA + multi-agent negotiation (R6 — FIPA-ACL AgentCapability)
- Case 2: CapabilityConstraints matching (R4 — `css:CapabilityConstraint`)
- Case 3: SMIA-HI (human interface agent — Human-in-the-Mesh paradigm)
- Case 4: BPMN orchestration via SMIA-PE
- Case 5: AAS server (BaSyx) + standard AAS API exposure

---

## 19. Key Identifiers and Credentials

| Item | Value |
|---|---|
| fischertechnik AAS id | `urn:uuid:6475_0111_2062_9689` |
| SMIA_agent AAS id | `urn:uuid:6373_1111_2062_6896` |
| SMIA XMPP JID | `SMIA_agent@ejabberd` |
| SMIA XMPP password | `asd` |
| Operator XMPP JID | `operator001@ejabberd` |
| Operator password | `gcis1234` |
| DIDA Central IP | `192.168.155.10` |
| Node-RED port | `1880` |
| MQTT topic | `vicom/61/piso_0/lab/lego/commands` |
| MQTT payload format | `bandera_custom:<position>` (position 0–8) |
| Operator GUI | `http://localhost:10000/smia_operator` |
