# Case 0 — Full Technical Documentation

**Date:** 2026-03-04
**Status:** Working end-to-end (verified)
**Physical asset:** fischertechnik Training Factory Industry 4.0 24V (ref. 554868) — warehouse crane (Hochregallager)
**Scope:** Warehouse crane pick/place via SMIA, AASX, Node-RED, and MQTT.

> **Naming note:** File names and AAS identifiers (`LEGO_factory_case0.aasx`, `LEGO_factory`, `/smia/lego/pick`, topic `vicom/61/piso_0/lab/lego/commands`) are historical artifacts from initial development. They refer to the fischertechnik Training Factory and its warehouse crane.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Technologies Used](#3-technologies-used)
4. [Repository Layout](#4-repository-layout-my_models)
5. [Key Semantic IDs Reference](#5-key-semantic-ids-reference)
6. [CSS Ontology](#6-css-ontology)
7. [LEGO_factory_case0.aasx — Detailed Structure](#7-lego_factory_case0aasx--detailed-structure)
8. [AASX Package Explorer — From-Scratch Tutorial](#8-aasx-package-explorer--from-scratch-tutorial)
9. [SMIA_Operator_article.aasx — Operator Agent AAS](#9-smia_operator_articleaasx--operator-agent-aas)
10. [Configuration Files](#10-configuration-files)
11. [Docker Compose Deployment](#11-docker-compose-deployment)
12. [Node-RED Flow (DIDA Central)](#12-node-red-flow-dida-central)
13. [smia_agent.py Patch](#13-smia_agentpy-patch)
14. [Deployment and Test Procedure](#14-deployment-and-test-procedure)
15. [Troubleshooting](#15-troubleshooting)
16. [Replication Checklist](#16-replication-checklist)

---

## 1. Introduction

Case 0 demonstrates flexible manufacturing using digital twins: an operator uses a web-based GUI to request a pick or place operation on the **fischertechnik Training Factory Industry 4.0 24V** warehouse crane. The request travels through a chain of standard technologies — AAS, CSS ontology, XMPP, and HTTP — reaching Node-RED on a remote machine, which then publishes an MQTT message that triggers the warehouse crane macro.

### What Case 0 Achieves

The operator requests `Capability_PickPiece` (or `Capability_PlacePiece`) through a browser. These capabilities are bound to the **warehouse crane (Hochregallager crane)** of the fischertechnik Training Factory — **not** the central crane with vacuum suction cup (ventose), which is a separate component. SMIA resolves the capability to a concrete skill and then to an HTTP interface defined in the AAS. It calls Node-RED's HTTP endpoint; Node-RED publishes `bandera_custom:<position>` to an MQTT topic; the fischertechnik machine subscribes to that topic and executes the warehouse crane macro.

No hard-coded logic about the physical asset lives in SMIA. The AAS model — specifically the `AssetInterfacesDescription` (AID) submodel — fully describes the HTTP endpoint, and the CSS ontology relationships in `SemanticRelationships` connect capabilities to skills to those endpoints.

### How to Use This Document

- **Understand the system**: Read sections 2–6.
- **Understand the AAS model**: Read section 7.
- **Recreate the AAS from scratch**: Follow section 8.
- **Deploy and run**: Follow sections 10–14.
- **Troubleshoot**: See section 15.
- **Replicate from zero**: Use the checklist in section 16.

---

## 2. System Architecture

### 2.1 Machines

Three physical machines are involved:

| # | Machine | Role |
|---|---------|------|
| 1 | Linux dev machine (this repo) | Runs Docker Compose: `smia`, `smia-operator`, `ejabberd` |
| 2 | DIDA central machine (IP: `192.168.155.10`) | Runs Node-RED + Mosquitto broker |
| 3 | fischertechnik/PLC Windows machine | Receives MQTT command, executes warehouse crane macro (Training Factory Industry 4.0 24V) |

### 2.2 End-to-End Data Flow

```
[Browser]
    |
    | HTTP GET/POST :10000
    v
[smia-operator container]  ←──volume── operator_gui_*.py, htmls/
    |
    | FIPA-ACL over XMPP (port 5222)
    v
[ejabberd container]  ──── SMIA_agent@ejabberd / operator001@ejabberd
    |
    | FIPA-ACL REQUEST: execute Capability_PickPiece
    v
[smia container]
    | 1. Resolve capability → skill (via isRealizedBy relationship)
    | 2. Resolve skill → HTTP action (via accessibleThroughAssetService relationship)
    | 3. Read HTTP endpoint from AssetInterfacesDescription submodel
    |
    | HTTP POST http://192.168.155.10:1880/smia/lego/pick
    |           body: {"color":"...", "position":...}
    v
[Node-RED — DIDA central machine]
    | Function: validate position, build MQTT payload
    |
    | MQTT publish (QoS 1)
    |   topic:   vicom/61/piso_0/lab/lego/commands
    |   payload: bandera_custom:<position>
    v
[Mosquitto broker — central]
    |
    | MQTT bridge central → fischertechnik machine
    v
[fischertechnik/PLC Windows machine]
[  Training Factory Industry 4.0 24V  ]
    | Subscribes to vicom/61/piso_0/lab/lego/commands
    v
[Warehouse crane macro triggered]
```

### 2.3 Docker Network

The three containers (`smia`, `smia-operator`, `ejabberd`) run in the same Docker Compose network and resolve each other by container name. SMIA and SMIA Operator both connect to ejabberd at the hostname `ejabberd` on port `5222`. The `smia-operator` exposes port `10000` to the host for browser access.

### 2.4 Architectural Rationale

Two deliberate architectural choices drive this deployment. A full academic justification with alternatives and trade-off analysis is in `memoire.md §14.7`. A summary follows.

**Decision 1 — Docker Compose for the SMIA stack**

The core problem: SMIA and SMIA-Operator must reach the same XMPP server by hostname. Without containers this requires manual ejabberd installation and hostname configuration on a shared lab machine — error-prone and non-reproducible.

Docker Compose puts all three services (`xmpp-server`, `smia`, `smia-operator`) on a shared Docker bridge network. The hostname `ejabberd` resolves automatically. `depends_on: condition: service_healthy` enforces startup order. `CTL_ON_CREATE` auto-registers XMPP accounts on first boot.

- **Strengths:** one-command deploy, reproducible on any machine, isolated network, startup order enforced, version-controlled in git.
- **Weaknesses:** single host = single point of failure; no horizontal scaling; the `smia_agent.py` volume-mount patch is fragile if the upstream image updates.
- **Rejected alternatives:** bare-metal install (dependency conflicts, not reproducible), Kubernetes (overkill), Docker Swarm (unnecessary complexity for single-host).

**Decision 2 — Edge + Central data processing**

The lab hosts multiple physical machines (fischertechnik, KUKA, etc.). A per-machine **edge stack** (mosquitto + node-red + postgres) provides local processing, data locality, and fault isolation — if the central node goes down, each machine keeps operating locally. A shared **central DIDA node** (`192.168.155.10`) aggregates cross-machine data and hosts the HTTP→MQTT bridge used by SMIA.

- **Strengths:** fault isolation (edge survives central failure), separation of concerns (per-machine flows vs. global knowledge), independent scalability (add a machine without touching others).
- **Weaknesses:** SMIA's AID endpoint points to DIDA central, not to a fischertechnik-specific edge node — so the central Node-RED **is** in the critical path for Case 0 commands despite the edge architecture; operational complexity grows with the number of nodes.
- **Rejected alternatives:** single centralised broker (single point of failure for all machines), direct SMIA→MQTT (SMIA uses HTTP-only AID; no native MQTT output).
- **Improvement path:** deploy a Linux edge node per machine so SMIA's AID can point to the edge directly, reserving central for aggregation only.

---

## 3. Technologies Used

| Technology | Role in Case 0 | Docker Image / Tool |
|---|---|---|
| **AAS / AASX** (IEC 63278) | Digital twin standard; `.aasx` packages define the agent model | AASX Package Explorer (authoring), basyx-python-sdk (runtime parsing) |
| **CSS Ontology** (OWL 2) | Capability–Skill–Service model; defines relationships between capabilities, skills, and interfaces | `CSS-ontology-smia.owl` (embedded in AASX) |
| **AID Submodel** (IDTA 02017) | W3C WoT-inspired submodel; describes HTTP endpoints, methods, and parameters | Defined inside `LEGO_factory_case0.aasx` |
| **SMIA** | SPADE-based Python industrial agent; reads AAS + CSS ontology at startup, handles capability requests | `ekhurtado/smia:latest-alpine` |
| **SMIA Operator** | Web GUI agent; allows operator to discover SMIAs and request capabilities | `ekhurtado/smia-use-cases:latest-operator` |
| **ejabberd** | XMPP server; transports FIPA-ACL messages between agents | `ghcr.io/processone/ejabberd` |
| **SPADE** | Python multi-agent framework built on XMPP; used internally by SMIA | (bundled inside SMIA image) |
| **basyx-python-sdk** | AAS parsing library; used internally by SMIA to read AASX models | (bundled inside SMIA image) |
| **Docker Compose v2** | Container orchestration for the 3-service stack | `docker compose` (v2 CLI — **not** `docker-compose` v1) |
| **Node-RED** | Flow-based programming tool; bridges HTTP to MQTT on DIDA central | Running on `192.168.155.10` |
| **Mosquitto** | MQTT broker; central broker bridges commands to fischertechnik machine broker | Running on DIDA central + fischertechnik machine |
| **AASX Package Explorer** | Windows GUI tool for authoring `.aasx` files | GitHub releases (Windows, .NET, no install) |

> **Important:** Always use `docker compose` (v2, with a space) instead of `docker-compose` (v1). The v1 binary crashes with a `KeyError: 'ContainerConfig'` error when used with current Docker image metadata.

---

## 4. Repository Layout (`my_models/`)

```
my_models/
├── aas/
│   ├── LEGO_factory_case0.aasx       # Main SMIA AAS model (Case 0)
│   └── SMIA_Operator_article.aasx    # Operator agent AAS (from SMIA repo)
├── xmpp_server/
│   └── ejabberd.yml                  # ejabberd XMPP server configuration
├── ontology/
│   └── CSS-ontology-smia.owl         # CSS OWL ontology (also embedded in AASX)
├── docker-compose.yml                # 3-service Docker deployment
├── smia-initialization.properties    # SMIA runtime configuration
├── flow_dida_central_lego.json       # Node-RED flow (import on DIDA central)
└── doc_case0.md                      # This document
```

Files outside `my_models/` that are also used at runtime (mounted into containers via Docker volumes):

```
src/smia/agents/smia_agent.py         # Patched asset-connection lookup (mounted into smia container)
additional_tools/extended_agents/smia_operator_agent/
├── operator_gui_behaviours.py        # Mounted into smia-operator container
├── operator_gui_logic.py             # Mounted into smia-operator container
└── htmls/                            # HTML templates mounted into smia-operator container
```

> **Important:** The `my_models/aas/` folder must contain **only valid `.aasx` files**. Any other files (backups, `.bak`, `.bak2`, etc.) in this folder will be processed by the operator's file scanner, returned as invalid, and cause the operator GUI to fail loading with an HTTP 500 error.

---

## 5. Key Semantic IDs Reference

All semantic IDs listed here are verified from the SMIA source code (`src/smia/utilities/smia_info.py` and `src/smia/css_ontology/css_ontology_utils.py`) and from the working `LEGO_factory_case0.aasx` model.

### 5.1 CSS Ontology IRIs

These IRIs are used as `semanticId` values on AAS elements to connect them to the CSS ontology.

| Concept | IRI |
|---|---|
| Capability (base class) | `http://www.w3id.org/hsu-aut/css#Capability` |
| AssetCapability | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` |
| AgentCapability | `http://www.w3id.org/upv-ehu/gcis/css-smia#AgentCapability` |
| Skill | `http://www.w3id.org/hsu-aut/css#Skill` |
| SkillInterface | `http://www.w3id.org/hsu-aut/css#SkillInterface` |
| SkillParameter | `http://www.w3id.org/hsu-aut/css#SkillParameter` |
| isRealizedBy (object property) | `http://www.w3id.org/hsu-aut/css#isRealizedBy` |
| accessibleThroughAssetService (object property) | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` |
| accessibleThroughAgentService (object property) | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` |

### 5.2 AID (Asset Interfaces Description) Semantic IDs

These IRIs are used as `semanticId` values on the AID submodel elements.

| Concept | Semantic ID |
|---|---|
| AID Submodel | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel` |
| Interface SMC | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Interface` |
| EndpointMetadata SMC | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/EndpointMetadata` |
| InteractionMetadata SMC | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/InteractionMetadata` |
| base URL property | `https://www.w3.org/2019/wot/td#baseURI` |
| ActionAffordance SMC | `https://www.w3.org/2019/wot/td#ActionAffordance` |
| PropertyAffordance SMC | `https://www.w3.org/2019/wot/td#PropertyAffordance` |
| hasForm (forms SMC) | `https://www.w3.org/2019/wot/td#hasForm` |
| href / hasTarget property | `https://www.w3.org/2019/wot/hypermedia#hasTarget` |
| contentType property | `https://www.w3.org/2019/wot/hypermedia#forContentType` |
| HTTP method property | `https://www.w3.org/2011/http#methodName` |
| Input schema SMC | `https://www.w3.org/2019/wot/td#hasInputSchema` |
| HTTP supplemental semanticId (Interface) | `http://www.w3.org/2011/http` |

---

## 6. CSS Ontology

### 6.1 What is the CSS Ontology?

The **Capability–Skill–Service (CSS)** ontology is an OWL 2 ontology that provides a standard vocabulary for describing industrial automation capabilities and how they are implemented.

**Source:** The base ontology is the **CaSkade-Automation CSS-ontology v1.0.1** (October 2024), maintained at `https://github.com/CaSkade-Automation/CSS`. SMIA extends this with two subclasses of `css:Capability`:
- SMIA extension IRI: `http://www.w3id.org/upv-ehu/gcis/css-smia`
- W3ID permanent identifier: `https://w3id.org/upv-ehu/gcis/css-smia/`

In SMIA's extension (`CSS-ontology-smia.owl`), the key concepts are:

- **Capability**: An abstract ability of an asset or agent (e.g., "pick a piece"). Not tied to any specific implementation. SMIA distinguishes two subtypes:
  - **`css-smia:AssetCapability`** — a physical capability inherent to the **machine** (e.g., PickPiece, PlacePiece). Used in Case 0 because the crane's physical actions are the capabilities being modelled.
  - **`css-smia:AgentCapability`** — a capability of the **DT agent itself** (e.g., Negotiate, Coordinate). Not used in Case 0; relevant in multi-agent scenarios where agents offer coordination functions to each other.
- **CapabilityConstraint**: A restriction on when a capability can be used (`css:Capability --isRestrictedBy--> css:CapabilityConstraint`). Not used in Case 0 but available for future capability matching.
- **Skill**: A concrete implementation of a capability. Linked to a capability via `isRealizedBy`.
- **SkillInterface**: Describes how a skill is accessed. Linked to a skill via one of two paths:
  - `accessibleThroughAssetService` — physical execution via HTTP (`AssetConnection`). **Case 0 uses this.**
  - `accessibleThroughAgentService` — internal execution via Python method (for `AgentCapability`, future cases).

### 6.2 Relationship Chain

```
Capability_PickPiece
    |
    | isRealizedBy
    v
Skill_PickPiece
    |
    | accessibleThroughAssetService
    v
AID/InterfaceHTTP/InteractionMetadata/actions/pickPiece
    |
    | forms.href + htv_methodName
    v
HTTP POST http://192.168.155.10:1880/smia/lego/pick
```

SMIA reads this chain at startup from the `SemanticRelationships` submodel and uses it to know which HTTP action to call when a capability request arrives.

### 6.3 Why the Ontology is Embedded in the AASX

The properties file contains `ontology.inside-aasx=true`. This tells SMIA to find the `.owl` file inside the AASX ZIP package at `aasx/CSS-ontology-smia.owl` rather than loading it from a separate file path. This makes the AASX self-contained: one file contains both the AAS model and the ontology.

### 6.4 Key Class Hierarchy (in SMIA's CSS ontology)

Based on the SMIA paper Fig. 4 (UML class diagram):

```
css:Capability  ──isRestrictedBy──►  css:CapabilityConstraint
    │                                    (+hasCondition: constraintCondition)
    │
    ├──► css-smia:AssetCapability   ← PHYSICAL capabilities (Case 0)
    │    e.g. PickPiece, PlacePiece — functions inherent to the machine
    │    (+hasLifecycle: OFFER | ASSURANCE | REQUIREMENT)
    │
    └──► css-smia:AgentCapability   ← AGENT capabilities (future cases)
         e.g. Negotiate, Coordinate — functions of the DT agent

css:Capability ──isRealizedBy──► css:Skill
                                     │ (+hasImplementationType: OPERATION | ...)
                                     │ (+hasParameter ──► css:SkillParameter)
                                     │
                                     ├──accessibleThroughAssetService──► css:SkillInterface
                                     │  ← HTTP via AssetConnection (Case 0 uses this)
                                     │
                                     └──accessibleThroughAgentService──► css:SkillInterface
                                        ← Python method (future AgentCapability cases)
```

**Capability lifecycle qualifier values (hasLifecycle):**
- `OFFER` — this capability is being offered/available by this asset ← used in Case 0
- `ASSURANCE` — capability offered with a quality guarantee
- `REQUIREMENT` — capability required/needed from another agent (used in requesting agents)

---

## 7. LEGO_factory_case0.aasx — Detailed Structure

> **Asset:** This AASX models the **fischertechnik Training Factory Industry 4.0 24V** warehouse crane. The file name and AAS shell identifiers use historical names; see the naming note at the top of this document.

The file `my_models/aas/LEGO_factory_case0.aasx` is a ZIP archive containing:
- `aasx/LEGO_factory/LEGO_factory.aas.xml` — the main AAS model (XML, AAS metamodel v3)
- `aasx/CSS-ontology-smia.owl` — embedded CSS OWL ontology (36 KB)
- `aasx/smia-initialization.properties` — properties template (not used at runtime; see §10.1)

### 7.1 AAS Shells

The package contains **two AAS shells**:

| AAS idShort | AAS id | Purpose |
|---|---|---|
| `LEGO_factory` | `urn:uuid:6475_0111_2062_9689` | Main digital twin of the fischertechnik Training Factory warehouse crane (historical name) |
| `SMIA_agent` | `urn:uuid:6373_1111_2062_6896` | Digital twin of the SMIA software agent itself |

The `AAS_ID` environment variable in Docker Compose (`urn:uuid:6475_0111_2062_9689`) tells SMIA to use the `LEGO_factory` shell as its active AAS.

### 7.2 Submodels

The `LEGO_factory` AAS references four submodels:

#### 7.2.1 SubmodelWithCapabilitySkillOntology

Contains `ConceptDescription` entries that document the CSS ontology concepts used in the model. These act as an inline catalog of definitions. SMIA does not actively process this submodel for execution; it serves as documentation within the AASX package.

#### 7.2.2 AssetInterfacesDescription

**Submodel semanticId:** `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel`

This submodel follows the IDTA AID standard and describes the HTTP interface of the fischertechnik Training Factory warehouse crane.

```
AssetInterfacesDescription  [semanticId: AID/Submodel]
└── InterfaceHTTP  [SMC, semanticId: AID/Interface, suppl. semanticId: http://www.w3.org/2011/http]
    ├── EndpointMetadata  [SMC, semanticId: AID/EndpointMetadata]
    │   ├── base  [Property, xs:anyURI, semanticId: td#baseURI]
    │   │         value: http://192.168.155.10:1880
    │   ├── contentType  [Property, semanticId: hypermedia#forContentType]
    │   │                value: application/json
    │   └── htv_methodName  [Property, semanticId: http#methodName]
    │                        value: POST
    └── InteractionMetadata  [SMC, semanticId: AID/InteractionMetadata]
        └── actions  [SMC]
            ├── pickPiece  [SMC, semanticId: td#ActionAffordance]
            │   ├── forms  [SMC, semanticId: td#hasForm]
            │   │   ├── href  [Property, semanticId: hypermedia#hasTarget]
            │   │   │         value: /smia/lego/pick
            │   │   ├── htv_methodName  [Property, semanticId: http#methodName]
            │   │   │                    value: POST
            │   │   └── contentType  [Property, semanticId: hypermedia#forContentType]
            │   │                    value: application/json
            │   └── input  [SMC, semanticId: td#hasInputSchema]
            │       ├── color     [Property, xs:string]
            │       └── position  [Property, xs:int]
            └── placePiece  [SMC, semanticId: td#ActionAffordance]
                ├── forms  [SMC, semanticId: td#hasForm]
                │   ├── href  [Property, semanticId: hypermedia#hasTarget]
                │   │         value: /smia/lego/place
                │   ├── htv_methodName  [Property, semanticId: http#methodName]
                │   │                    value: POST
                │   └── contentType  [Property, semanticId: hypermedia#forContentType]
                │                    value: application/json
                └── input  [SMC, semanticId: td#hasInputSchema]
                    └── position  [Property, xs:int]
```

At runtime, SMIA combines the `base` URL from `EndpointMetadata` with the `href` from `forms` to build the final HTTP URL:
- pickPiece: `http://192.168.155.10:1880` + `/smia/lego/pick` → `http://192.168.155.10:1880/smia/lego/pick`
- placePiece: `http://192.168.155.10:1880` + `/smia/lego/place` → `http://192.168.155.10:1880/smia/lego/place`

#### 7.2.3 CapabilitiesAndSkills

Contains four CSS-annotated elements — two capabilities and two skills.

```
CapabilitiesAndSkills
├── Capability_PickPiece  [SMC, semanticId: css-smia#AssetCapability]
│   ├── Qualifier: type=hasLifecycle, value=OFFER
│   └── position  [Property, xs:int]
├── Capability_PlacePiece  [SMC, semanticId: css-smia#AssetCapability]
│   ├── Qualifier: type=hasLifecycle, value=OFFER
│   └── position  [Property, xs:int]
├── Skill_PickPiece  [Property, xs:string, semanticId: css#Skill]
│   └── Qualifier: type=hasImplementationType, value=OPERATION
└── Skill_PlacePiece  [Property, xs:string, semanticId: css#Skill]
    └── Qualifier: type=hasImplementationType, value=OPERATION
```

> **Lifecycle values:** `hasLifecycle = OFFER` means this asset is advertising/providing this capability. Other valid values: `ASSURANCE` (offered with quality guarantee) and `REQUIREMENT` (capability needed from another agent — used on the requesting side, e.g., in the operator AAS).

> **Critical:** `Skill_PickPiece` and `Skill_PlacePiece` are defined as `<property>` AAS elements (not `<submodelElementCollection>`). Using a `SubmodelElementCollection` for skills causes an unresolvable Python method resolution order (MRO) conflict in SMIA's internal class extension system, which prevents `InitAASModelBehaviour` from completing. The system silently fails to register skills, and the operator GUI shows 0 capabilities. Skills must be `<property>` elements to avoid this.

#### 7.2.4 SemanticRelationships

Contains four `RelationshipElement` entries that encode the CSS ontology graph in AAS form.

| idShort | semanticId | first (subject) | second (object) |
|---|---|---|---|
| `rel_CapPick_isRealizedBySkill_SkillPick` | `css#isRealizedBy` | `CapabilitiesAndSkills/Capability_PickPiece` | `CapabilitiesAndSkills/Skill_PickPiece` |
| `rel_CapPlace_isRealizedBySkill_SkillPlace` | `css#isRealizedBy` | `CapabilitiesAndSkills/Capability_PlacePiece` | `CapabilitiesAndSkills/Skill_PlacePiece` |
| `rel_SkillPick_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | `CapabilitiesAndSkills/Skill_PickPiece` | `AssetInterfacesDescription/InterfaceHTTP/InteractionMetadata/actions/pickPiece` |
| `rel_SkillPlace_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | `CapabilitiesAndSkills/Skill_PlacePiece` | `AssetInterfacesDescription/InterfaceHTTP/InteractionMetadata/actions/placePiece` |

SMIA reads these four relationships during startup (`InitAASModelBehaviour`) to build the complete capability→skill→interface map.

---

## 8. AASX Package Explorer — From-Scratch Tutorial

This section explains how to create `LEGO_factory_case0.aasx` from scratch using AASX Package Explorer (AASX PE). This AASX models the **fischertechnik Training Factory Industry 4.0 24V warehouse crane**. If you already have the file, use this as a verification guide.

**Process reference (paper Fig. 6):** The SMIA paper defines the canonical CSS-enriched AAS development workflow as:
1. Open AASX Package Explorer
2. For each SubmodelElement that represents a CSS concept: get the CSS class IRI from the ontology (e.g., using Protégé) → add it to the `semanticId` field
3. For each relationship between CSS elements: get the CSS ObjectProperty IRI → add it to a `RelationshipElement`'s `semanticId`
4. Add the `AssetInterfacesDescription` submodel with `EndpointMetadata` + `InteractionMetadata`
5. Save the CSS ontology OWL file inside the AASX (as a supplementary file)
6. Save the AASX

Note: SMIA also extends the AID submodel with two optional attributes (paper §4.1.1): `data-Query` (JSONPath/XPath/regex for extracting specific data from asset responses) and `htv_params` (HTTP request parameters). These are available for advanced use but not required and not used in Case 0.

### 8.1 Install AASX Package Explorer

1. Go to: `https://github.com/admin-shell-io/aasx-package-explorer/releases`
2. Download the latest release ZIP (Windows only, .NET 6+).
3. Extract the ZIP. Run `AasxPackageExplorer.exe` directly — no installation required.

### 8.2 Create a New AASX Package

1. Open AASX Package Explorer.
2. Menu: **File → New…**
3. Save the new package as `LEGO_factory_case0.aasx` in `my_models/aas/`.

### 8.3 Embed Supplementary Files

The CSS ontology `.owl` file must be embedded in the package so SMIA can load it.

1. In the left panel, click **"Workspace"** or look for the package file tree.
2. Menu: **File → AASX → Add supplementary file…** (exact label may differ by version; look for "Add file to package" or drag onto the resource panel).
3. Select `my_models/ontology/CSS-ontology-smia.owl`.
4. Set the internal package path to: `aasx/CSS-ontology-smia.owl`
5. Confirm. The file now appears in the package resources tree.

Optionally embed `smia-initialization.properties`:
- Internal path: `aasx/smia-initialization.properties`
- This is a template and is not used at runtime when Docker env vars are set.

### 8.4 Add AAS Shell 1: LEGO_factory (fischertechnik warehouse crane)

1. In the main panel, click **"Add AAS"** or right-click → **Add AAS element → AssetAdministrationShell**.
2. Fill in:
   - `idShort`: `LEGO_factory` *(historical name — represents the fischertechnik Training Factory warehouse crane)*
   - `id` (identifier): `urn:uuid:6475_0111_2062_9689`
   - Asset Kind: `Instance`
3. Confirm.

### 8.5 Add AAS Shell 2: SMIA_agent

1. Add a second AAS shell:
   - `idShort`: `SMIA_agent`
   - `id`: `urn:uuid:6373_1111_2062_6896`
2. This shell represents the software agent's own digital twin. You can add a `SoftwareNameplate` submodel to it with agent metadata if desired (not required for Case 0 execution).

### 8.6 Create Submodel: AssetInterfacesDescription

This is the most detailed submodel. Follow the AID standard (IDTA 02017).

**Create the submodel:**
1. Select the `LEGO_factory` AAS. Right-click → **Add Submodel**.
2. Set:
   - `idShort`: `AssetInterfacesDescription`
   - `id`: choose a URN (e.g., `urn:uuid:aid_lego_factory`)
   - `semanticId` (ExternalReference, GlobalReference): `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel`

**Add `InterfaceHTTP` (SubmodelElementCollection):**
1. Inside the submodel, add a `SubmodelElementCollection`:
   - `idShort`: `InterfaceHTTP`
   - `semanticId`: `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Interface`
   - Supplemental semanticId: `http://www.w3.org/2011/http` (marks it as HTTP type)

**Add `EndpointMetadata` inside `InterfaceHTTP`:**
1. Add SMC:
   - `idShort`: `EndpointMetadata`
   - `semanticId`: `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/EndpointMetadata`
2. Inside `EndpointMetadata`, add three Properties:

   | idShort | valueType | semanticId | value |
   |---|---|---|---|
   | `base` | `xs:anyURI` | `https://www.w3.org/2019/wot/td#baseURI` | `http://192.168.155.10:1880` |
   | `contentType` | `xs:string` | `https://www.w3.org/2019/wot/hypermedia#forContentType` | `application/json` |
   | `htv_methodName` | `xs:string` | `https://www.w3.org/2011/http#methodName` | `POST` |

**Add `InteractionMetadata` inside `InterfaceHTTP`:**
1. Add SMC:
   - `idShort`: `InteractionMetadata`
   - `semanticId`: `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/InteractionMetadata`
2. Add SMC `actions` inside `InteractionMetadata` (no semanticId required on the container).

**Add action `pickPiece` inside `actions`:**
1. Add SMC:
   - `idShort`: `pickPiece`
   - `semanticId`: `https://www.w3.org/2019/wot/td#ActionAffordance`
2. Inside `pickPiece`, add SMC `forms`:
   - `idShort`: `forms`
   - `semanticId`: `https://www.w3.org/2019/wot/td#hasForm`
3. Inside `forms`, add Properties:

   | idShort | valueType | semanticId | value |
   |---|---|---|---|
   | `href` | `xs:anyURI` | `https://www.w3.org/2019/wot/hypermedia#hasTarget` | `/smia/lego/pick` |
   | `htv_methodName` | `xs:string` | `https://www.w3.org/2011/http#methodName` | `POST` |
   | `contentType` | `xs:string` | `https://www.w3.org/2019/wot/hypermedia#forContentType` | `application/json` |

4. Inside `pickPiece`, add SMC `input`:
   - `idShort`: `input`
   - `semanticId`: `https://www.w3.org/2019/wot/td#hasInputSchema`
5. Inside `input`, add Properties:

   | idShort | valueType |
   |---|---|
   | `color` | `xs:string` |
   | `position` | `xs:int` |

**Add action `placePiece` inside `actions`:**
1. Add SMC `placePiece` (same pattern as `pickPiece`):
   - `semanticId`: `https://www.w3.org/2019/wot/td#ActionAffordance`
2. Inside `placePiece`, add SMC `forms` with Properties:

   | idShort | value |
   |---|---|
   | `href` | `/smia/lego/place` |
   | `htv_methodName` | `POST` |
   | `contentType` | `application/json` |

3. Inside `placePiece`, add SMC `input` (`semanticId: td#hasInputSchema`) with one Property:

   | idShort | valueType |
   |---|---|
   | `position` | `xs:int` |

### 8.7 Create Submodel: CapabilitiesAndSkills

**Create the submodel:**
1. Add Submodel to `LEGO_factory` AAS:
   - `idShort`: `CapabilitiesAndSkills`
   - `id`: choose a URN
   - No semanticId required on the submodel itself.

**Add `Capability_PickPiece` (SubmodelElementCollection):**
1. Add SMC:
   - `idShort`: `Capability_PickPiece`
   - `semanticId`: `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability`
2. Add Qualifier on the SMC:
   - Type: `hasLifecycle`
   - Value: `OFFER`
3. Inside `Capability_PickPiece`, add Property:
   - `idShort`: `position`
   - `valueType`: `xs:int`

**Add `Capability_PlacePiece` (SubmodelElementCollection):**
1. Same structure as `Capability_PickPiece`.

**Add `Skill_PickPiece` (Property — NOT SubmodelElementCollection):**

> This is the critical step. SMIA requires skills to be `Property` elements. Do NOT use `SubmodelElementCollection` for skills.

1. Add **Property** (not SMC):
   - `idShort`: `Skill_PickPiece`
   - `valueType`: `xs:string`
   - `semanticId`: `http://www.w3id.org/hsu-aut/css#Skill`
2. Add Qualifier on the Property:
   - Type: `hasImplementationType`
   - Value: `OPERATION`

**Add `Skill_PlacePiece` (Property):**
1. Same structure as `Skill_PickPiece`.

### 8.8 Create Submodel: SemanticRelationships

**Create the submodel:**
1. Add Submodel to `LEGO_factory` AAS:
   - `idShort`: `SemanticRelationships`
   - `id`: choose a URN

**Add 4 RelationshipElements:**

For each RelationshipElement, you need to set:
- `idShort` (name)
- `semanticId` (the CSS object property IRI)
- `first` (ModelReference to the subject element)
- `second` (ModelReference to the object element)

**Relationship 1: `rel_CapPick_isRealizedBySkill_SkillPick`**
- `semanticId`: `http://www.w3id.org/hsu-aut/css#isRealizedBy`
- `first`: ModelReference → `CapabilitiesAndSkills / Capability_PickPiece`
- `second`: ModelReference → `CapabilitiesAndSkills / Skill_PickPiece`

In AASX PE, to create a ModelReference: click on the `first` or `second` field → Add ModelReference → select the AAS, then the Submodel, then drill down to the target element.

**Relationship 2: `rel_CapPlace_isRealizedBySkill_SkillPlace`**
- `semanticId`: `http://www.w3id.org/hsu-aut/css#isRealizedBy`
- `first`: → `CapabilitiesAndSkills / Capability_PlacePiece`
- `second`: → `CapabilitiesAndSkills / Skill_PlacePiece`

**Relationship 3: `rel_SkillPick_hasSkillInterface`**
- `semanticId`: `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService`
- `first`: → `CapabilitiesAndSkills / Skill_PickPiece`
- `second`: → `AssetInterfacesDescription / InterfaceHTTP / InteractionMetadata / actions / pickPiece`

**Relationship 4: `rel_SkillPlace_hasSkillInterface`**
- `semanticId`: `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService`
- `first`: → `CapabilitiesAndSkills / Skill_PlacePiece`
- `second`: → `AssetInterfacesDescription / InterfaceHTTP / InteractionMetadata / actions / placePiece`

### 8.9 Save and Verify

1. **Save**: File → Save.
2. **Verify**: Re-open the file and check all elements are present as listed in section 7.2.
3. Quick checklist from the working model:
   - `AssetInterfacesDescription` → `InterfaceHTTP` → `EndpointMetadata` → `base` = `http://192.168.155.10:1880`
   - `InteractionMetadata` → `actions` → `pickPiece` → `forms` → `href` = `/smia/lego/pick`
   - `InteractionMetadata` → `actions` → `placePiece` → `forms` → `href` = `/smia/lego/place`
   - `CapabilitiesAndSkills` → `Skill_PickPiece` is a **Property** (not SMC)
   - `SemanticRelationships` → 4 RelationshipElements present
   - Package resources contain `aasx/CSS-ontology-smia.owl`

---

## 9. SMIA_Operator_article.aasx — Operator Agent AAS

The file `my_models/aas/SMIA_Operator_article.aasx` is taken directly from the SMIA repository examples without modification. It defines the digital twin of the operator agent.

**AAS shell:** `operatorAAS`, id: `urn:ehu:gcis:submodel:1:1:operator001`

**Submodels:**
- `SoftwareNameplate` — operator agent metadata
- `Capabilities` — defines `GUICapability`, `RequestTransport`, `RequestNegotiation`
- `Skills` — operator skills linked to the above capabilities
- `Contact` — contact information

The `smia-operator` container loads this file as its own AAS model. When the operator GUI scans the `my_models/aas/` folder to discover target SMIAs, it skips files whose AAS IDs match the operator's own configured `AAS_MODEL_NAME` (set via the `CM_AAS_MODEL_FILENAME` environment variable mechanism). This is why both AASX files can live in the same folder without conflict.

Do not modify this file.

---

## 10. Configuration Files

### 10.1 smia-initialization.properties

File: `my_models/smia-initialization.properties`
Mounted into the `smia` container at: `/smia_archive/config/smia-initialization.properties`

```properties
[DT]
dt.version=0.2.0
dt.agentID=SMIA_agent@ejabberd
dt.password=asd
dt.xmpp-server=ejabberd
dt.web-ui=false

[AAS]
aas.meta-model.version=3.0
aas.model.serialization=AASX
aas.model.folder=/smia_archive/config/aas
aas.model.file=LEGO_factory_case0.aasx

[ONTOLOGY]
ontology.file=CSS-ontology-smia.owl
ontology.inside-aasx=true
```

| Key | Value | Explanation |
|---|---|---|
| `dt.agentID` | `SMIA_agent@ejabberd` | XMPP JID for the SMIA agent |
| `dt.password` | `asd` | XMPP password (must match ejabberd registration) |
| `dt.xmpp-server` | `ejabberd` | Container hostname of the XMPP server |
| `dt.web-ui` | `false` | Disables built-in web UI (operator GUI is separate) |
| `aas.meta-model.version` | `3.0` | AAS metamodel version |
| `aas.model.serialization` | `AASX` | Use AASX format (not raw XML) |
| `aas.model.folder` | `/smia_archive/config/aas` | Container path where AASX files are mounted |
| `aas.model.file` | `LEGO_factory_case0.aasx` | Which AASX file to load |
| `ontology.file` | `CSS-ontology-smia.owl` | OWL ontology filename to look for |
| `ontology.inside-aasx` | `true` | Look for the `.owl` file inside the AASX package (at `aasx/<ontology.file>`) |

> **Note on environment variable priority:** Docker Compose also sets `AAS_MODEL_NAME` and `AGENT_PASSWD` as environment variables. These environment variables override the properties file values. The effective runtime values come from the Docker Compose environment section.

### 10.2 ejabberd.yml

File: `my_models/xmpp_server/ejabberd.yml`
Mounted into the `xmpp-server` container at: `/opt/ejabberd/conf/ejabberd.yml`

Key configuration points:

```yaml
hosts:
  - localhost
  - ejabberd            # Both SMIA_agent@ejabberd and operator001@ejabberd register here

listen:
  - port: 5222          # XMPP C2S (client-to-server) — agents connect here
    module: ejabberd_c2s
    starttls_required: true
  - port: 5223          # XMPP C2S with TLS
    module: ejabberd_c2s
  - port: 5269          # XMPP S2S (server-to-server)
    module: ejabberd_s2s_in
  - port: 5443          # HTTPS (admin, API, BOSH, WebSocket)
    module: ejabberd_http
  - port: 5280          # HTTP (admin, ACME)
    module: ejabberd_http
  - port: 1883          # MQTT (via mod_mqtt)
    module: mod_mqtt

modules:
  mod_mqtt: {}          # Enables built-in MQTT broker on port 1883
  mod_register:
    ip_access: all      # Allows account registration from any IP
                        # Required for CTL_ON_CREATE to auto-register accounts
```

The `mod_register: ip_access: all` setting is what allows the `CTL_ON_CREATE` command in Docker Compose to automatically register the SMIA and operator XMPP accounts when the container starts for the first time.

---

## 11. Docker Compose Deployment

File: `my_models/docker-compose.yml`

Run all commands from the **repository root** (`SMIA/`), not from `my_models/`:

```bash
docker compose -f my_models/docker-compose.yml up -d
```

### 11.1 Services Overview

```yaml
services:

  smia:                                       # SMIA industrial agent
    image: ekhurtado/smia:latest-alpine
    container_name: smia
    environment:
      - AAS_MODEL_NAME=LEGO_factory_case0.aasx    # Which AASX to load from aas/ folder
      - AAS_ID=urn:uuid:6475_0111_2062_9689        # Filter to load this specific AAS shell
      - AGENT_ID=SMIA_agent@ejabberd               # XMPP JID
      - AGENT_PASSWD=asd                            # XMPP password
    depends_on:
      xmpp-server:
        condition: service_healthy
    volumes:
      - ../src/smia/agents/smia_agent.py:/usr/local/lib/python3.12/site-packages/smia/agents/smia_agent.py
      #   ↑ Patched file that fixes asset-connection lookup (see §13)
      - ./aas:/smia_archive/config/aas
      #   ↑ Mounts my_models/aas/ as the AASX file folder inside the container

  xmpp-server:                                # XMPP server (ejabberd)
    image: ghcr.io/processone/ejabberd
    container_name: ejabberd
    environment:
      - ERLANG_NODE_ARG=admin@ejabberd
      - ERLANG_COOKIE=dummycookie123
      - CTL_ON_CREATE=! register SMIA_agent ejabberd asd ; register operator001 ejabberd gcis1234
      #   ↑ Registers both agent accounts on first startup
    ports:
      - "5222:5222"     # XMPP C2S
      - "5269:5269"     # XMPP S2S
      - "5280:5280"     # HTTP admin
      - "5443:5443"     # HTTPS admin/API
    volumes:
      - ./xmpp_server/ejabberd.yml:/opt/ejabberd/conf/ejabberd.yml
      - ejabberd_data:/opt/ejabberd/database   # Persistent account data
    healthcheck:
      test: netstat -nl | grep -q 5222
      start_period: 5s
      interval: 5s
      timeout: 5s
      retries: 10

  smia-operator:                              # Operator GUI agent
    image: ekhurtado/smia-use-cases:latest-operator
    container_name: smia-operator
    environment:
      - AAS_MODEL_NAME=SMIA_Operator_article.aasx  # Operator's own AAS
      - AGENT_ID=operator001@ejabberd               # XMPP JID
      - AGENT_PASSWD=gcis1234                        # XMPP password
    depends_on:
      xmpp-server:
        condition: service_healthy
    volumes:
      - ./aas:/smia_archive/config/aas
      #   ↑ Same aas/ folder — operator scans this to find SMIA targets (skips its own file)
      - ../additional_tools/extended_agents/smia_operator_agent/operator_gui_behaviours.py:/operator_gui_behaviours.py
      - ../additional_tools/extended_agents/smia_operator_agent/operator_gui_logic.py:/operator_gui_logic.py
      - ../additional_tools/extended_agents/smia_operator_agent/htmls:/htmls
      #   ↑ Override operator GUI files with updated versions from repo
    ports:
      - "10000:10000"   # Web GUI exposed to host

volumes:
  ejabberd_data:        # Persistent volume for ejabberd account database
```

### 11.2 XMPP Accounts

Two XMPP accounts are registered automatically on first ejabberd startup:

| Account | Password | Used by |
|---|---|---|
| `SMIA_agent@ejabberd` | `asd` | `smia` container |
| `operator001@ejabberd` | `gcis1234` | `smia-operator` container |

These credentials must match across:
1. `CTL_ON_CREATE` in docker-compose.yml
2. `AGENT_PASSWD` env vars in docker-compose.yml
3. `dt.password` in `smia-initialization.properties` (fallback for smia)

### 11.3 Common Commands

```bash
# Start all services in background
docker compose -f my_models/docker-compose.yml up -d

# Check service status
docker compose -f my_models/docker-compose.yml ps

# View live logs for all services
docker compose -f my_models/docker-compose.yml logs -f smia smia-operator xmpp-server

# View last 100 lines of smia logs
docker compose -f my_models/docker-compose.yml logs -n 100 smia

# Stop and remove all containers (preserves ejabberd_data volume)
docker compose -f my_models/docker-compose.yml down

# Stop, remove containers AND volume (full reset — re-registers XMPP accounts on next start)
docker compose -f my_models/docker-compose.yml down -v

# Restart just the smia container (after changing smia_agent.py)
docker compose -f my_models/docker-compose.yml restart smia
```

### 11.4 Startup Order

The `depends_on: condition: service_healthy` ensures:
1. `xmpp-server` starts and port 5222 becomes available.
2. Only then `smia` and `smia-operator` start and attempt XMPP connection.

If `smia` or `smia-operator` start before ejabberd is ready, the XMPP connection fails and the container exits. The `healthcheck` on `xmpp-server` prevents this.

---

## 12. Node-RED Flow (DIDA Central)

File: `my_models/flow_dida_central_lego.json`

### 12.1 Import the Flow

1. Open Node-RED on the DIDA central machine (`http://192.168.155.10:1880`).
2. Top-right menu → **Import**.
3. Paste the content of `flow_dida_central_lego.json` or import the file directly.
4. Click **Deploy**.

### 12.2 Flow Structure

```
[HTTP In]  POST /smia/lego/pick
    |
    v
[JSON]  Parse incoming body
    |
    v
[Function: Validate+Publish pickPiece]
    |
    ├── MQTT Out → topic: vicom/61/piso_0/lab/lego/commands
    |              payload: bandera_custom:<position>
    |              broker: mosquitto-central:1883, QoS 1
    |
    v
[HTTP Response]  JSON body with status
```

### 12.3 Function Node Logic

The function node extracts `position` from the incoming request with a priority order:
1. `msg.payload.position` (JSON body field)
2. `msg.req.query.position` (URL query parameter)
3. `msg.payload.skillParams.position` (nested in SMIA's ACL message format)

If none is found, it uses `DEFAULT_POSITION = 0`.

Validation: position must be an integer between 0 and 8 (inclusive). Invalid values return HTTP 400.

**MQTT publish:**
- Topic: `vicom/61/piso_0/lab/lego/commands`
- Payload: `bandera_custom:<position>` (e.g., `bandera_custom:0`)
- Broker: `mosquitto-central` host, port `1883`, QoS `1`

**HTTP response body (JSON):**
```json
{
  "status": "ok",
  "published": "vicom/61/piso_0/lab/lego/commands",
  "payload": "bandera_custom:0",
  "position": 0,
  "source": "default"
}
```

The `source` field is `"request"` if position came from the request, or `"default"` if the fallback was used.

### 12.4 MQTT Chain

```
Node-RED (DIDA central)
    → Mosquitto broker (mosquitto-central:1883)
        → bridge to fischertechnik/PLC Windows machine broker
            → subscriber picks up vicom/61/piso_0/lab/lego/commands
                → warehouse crane macro triggered (fischertechnik Training Factory 24V)
```

The bridge between the central Mosquitto and the fischertechnik machine broker is configured separately on the fischertechnik/PLC side. This is outside the scope of this repository.

---

## 13. smia_agent.py Patch

### 13.1 Why the Patch Was Needed

SMIA's `get_asset_connection_by_model_reference()` method compared the requested AAS reference object against stored asset connection references using Python object identity (`is` or `==`). When SMIA resolves a capability to a skill interface reference and then looks it up in the asset connections dictionary, the reference objects may not be identical Python objects even though they point to the same logical AAS element. This caused the lookup to silently return `None`, meaning SMIA could not find the HTTP interface to call, and the capability request failed at line 291 of the behaviour.

### 13.2 What the Patch Does

The patched `src/smia/agents/smia_agent.py` adds two additional comparison strategies in the asset-connection lookup:

1. **String equality**: Compares `str(conn_ref) == str(asset_connection_ref)` — works when both objects serialize to the same string representation.
2. **Normalized reference key tuples**: Extracts the key sequence as `tuple((str(key.type), key.value) for key in ref_obj.key)` and compares those tuples — works when the reference objects have the same logical keys regardless of identity.

### 13.3 How It Is Applied

The patch is applied without modifying the Docker image by using a volume mount in `docker-compose.yml`:

```yaml
volumes:
  - ../src/smia/agents/smia_agent.py:/usr/local/lib/python3.12/site-packages/smia/agents/smia_agent.py
```

This overrides the file inside the container at runtime. After changing `smia_agent.py`, restart the `smia` container:

```bash
docker compose -f my_models/docker-compose.yml restart smia
```

---

## 14. Deployment and Test Procedure

### 14.1 Prerequisites

Before starting:
1. Docker and Docker Compose v2 are installed on the Linux dev machine.
2. Node-RED flow from `my_models/flow_dida_central_lego.json` is deployed on DIDA central.
3. MQTT chain from DIDA central to the fischertechnik/PLC machine is online.
4. `my_models/aas/` folder contains **only** these two files:
   - `LEGO_factory_case0.aasx`
   - `SMIA_Operator_article.aasx`

### 14.2 Start the Stack

```bash
# From SMIA repo root
cd /path/to/SMIA

docker compose -f my_models/docker-compose.yml up -d
```

Expected output: three containers starting — `ejabberd`, `smia`, `smia-operator`.

### 14.3 Verify Healthy Startup

```bash
docker compose -f my_models/docker-compose.yml logs smia smia-operator xmpp-server | grep -E "AAS model initialized|Analyzed capabilities|Executing skill|HTTP communication successfully completed|Configuration loaded"
```

Expected healthy SMIA log lines:

```
INFO  Reading the AAS model to get all defined ontology elements...
INFO  Reading the AAS model to get all relationships...
INFO  Reading the AAS model to get all asset connections...
INFO  AAS model analysis results.
      - Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']
      - Analyzed skills: ['Skill_PickPiece', 'Skill_PlacePiece']
      - Analyzed skill interfaces: ['pickPiece', 'placePiece']
      - Analyzed asset connections: ['InterfaceHTTP', ...]
      - Errors found: []
INFO  AAS model initialized.
INFO  smia_agent@ejabberd agent has finished its Boot state.
```

Expected ejabberd log line:
```
Configuration loaded successfully
```

### 14.4 Direct HTTP Test (Bypass SMIA)

Use this to verify Node-RED is working before involving SMIA:

```bash
curl -i -X POST http://192.168.155.10:1880/smia/lego/pick \
  -H 'Content-Type: application/json' \
  -d '{"position":0}'
```

Expected:
- HTTP 200
- Body: `{"status":"ok","published":"vicom/61/piso_0/lab/lego/commands","payload":"bandera_custom:0","position":0,...}`
- MQTT publish appears on central broker
- fischertechnik warehouse crane macro triggers

### 14.5 Full End-to-End Test via Operator GUI

1. Open browser: `http://localhost:10000/smia_operator`
2. Click **"Load"** — the GUI scans the AAS folder and queries all discovered SMIAs via XMPP.
3. Wait for the SMIA list to appear. Select the fischertechnik factory SMIA.
4. From the capability list, select **`Capability_PickPiece`**.
5. Click **Submit**.

Expected SMIA log output:
```
INFO  Executing skill of the capability through an asset service...
INFO  HTTP communication successfully completed.
```

Expected operator GUI response:
```json
{"status":"ok","published":"vicom/61/piso_0/lab/lego/commands","payload":"bandera_custom:0","position":0}
```

Expected physical result: fischertechnik warehouse crane macro executes.

---

## 15. Troubleshooting

### 15.1 Quick Troubleshooting Matrix

| Symptom | Where to Check | Fix |
|---|---|---|
| GUI cannot load / HTTP 500 on Load | `docker logs smia-operator` — look for `NoneType` or file scan errors | Remove all non-`.aasx` files from `my_models/aas/` (backups, `.bak`, `.bak2`, etc.) |
| GUI loads but shows 0 capabilities / 0 SMIAs | `docker logs smia` — look for `AAS model initialized` and `Analyzed capabilities` | Check that SMIA started cleanly; verify AASX structure matches §7 |
| Submit spins forever / no response | `docker logs smia` — look for `Exception` at `line:291` or `HandleCapabilityBehaviour` | Confirm patched `smia_agent.py` volume mount is active; `docker compose restart smia` |
| SMIA logs `HTTP communication successfully completed` but no warehouse crane action | Node-RED debug panel; MQTT Explorer on central broker | Check topic is exactly `vicom/61/piso_0/lab/lego/commands`; check MQTT bridge to fischertechnik machine |
| `docker-compose up` crashes with `KeyError: 'ContainerConfig'` | — | Use `docker compose` (v2), **not** `docker-compose` (v1) |
| XMPP authentication failures / agents not online | `docker logs ejabberd` | Verify credentials match CTL_ON_CREATE and AGENT_PASSWD env vars; try `docker compose down -v` then `up` to re-register accounts |
| Skills not found / InitAASModelBehaviour MRO error | `docker logs smia` — `Cannot create a consistent method resolution order` | Skills in AASX are `SubmodelElementCollection` — change them to `Property` elements |
| Node-RED returns HTTP 400 | Node-RED function node debug output | Ensure `position` is passed, or verify DEFAULT_POSITION fallback is in function code |

### 15.2 Issue History (Resolved During This Setup)

These issues were encountered and resolved during the initial Case 0 setup:

**Issue 1: Docker Compose v1 crash (`ContainerConfig`)**
Symptom: `docker-compose up -d` fails with a Python traceback ending in `KeyError: 'ContainerConfig'`.
Cause: Docker Compose v1.29.2 is incompatible with current Docker image metadata format.
Fix: Switch to v2 CLI — `docker compose` (with a space, no hyphen).

**Issue 2: Operator request not completing — `line:291` exception**
Symptom: Submit button stays loading; `smia` logs `Exception running behaviour ... line:291`.
Cause: `get_asset_connection_by_model_reference()` used Python object identity for comparison and returned `None`.
Fix: Applied patch to `src/smia/agents/smia_agent.py` adding string and key-tuple equality fallbacks; mounted the patched file into the container.

**Issue 3: Node-RED returns `Missing field: position`**
Symptom: SMIA calls Node-RED but receives HTTP 400.
Cause: SMIA's ACL capability request message does not include `position` in the expected field.
Fix: Updated Node-RED function with `DEFAULT_POSITION = 0` fallback and multi-path extraction.

**Issue 4: Operator GUI HTTP 500 on Load**
Symptom: `GET /smia_operator/load` returns HTTP 500; smia-operator logs show `NoneType is not iterable`.
Cause: A `.bak2` backup file was present in `my_models/aas/`. The file scanner returned `None` for the invalid file; `analyze_aas_model_store(agent, None)` set the store to `None`; all CSS queries crashed.
Fix: Delete backup files from `my_models/aas/`.

**Issue 5: Python MRO crash (Skills as SubmodelElementCollection)**
Symptom: `docker logs smia` shows `Cannot create a consistent method resolution order (MRO) for bases HasSemantics, Qualifiable`.
Cause: Skill AAS elements were `SubmodelElementCollection`, causing `ExtendedComplexSkill` + `ExtendedSubmodelElementCollection` MRO conflict.
Fix: Change Skill elements from `submodelElementCollection` to `property` in the AASX.

---

## 16. Replication Checklist

Use this checklist to replicate Case 0 from scratch.

### Environment Setup
- [ ] Clone the SMIA repository
- [ ] Install Docker and Docker Compose v2 (`docker compose version` should show v2.x)
- [ ] Windows machine with AASX Package Explorer available (for AAS authoring)
- [ ] Node-RED running on DIDA central machine (192.168.155.10:1880)
- [ ] Mosquitto broker running on DIDA central; bridge to fischertechnik machine configured

### AAS Authoring
- [ ] Created `LEGO_factory_case0.aasx` with AASX PE (or verified existing file matches §7) — this models the fischertechnik warehouse crane
- [ ] Two AAS shells: `LEGO_factory` (urn:uuid:6475_0111_2062_9689) and `SMIA_agent`
- [ ] Embedded `CSS-ontology-smia.owl` at path `aasx/CSS-ontology-smia.owl`
- [ ] `AssetInterfacesDescription` submodel present with `InterfaceHTTP`, `EndpointMetadata`, `actions/pickPiece`, `actions/placePiece`
- [ ] `EndpointMetadata/base` = `http://192.168.155.10:1880`
- [ ] `pickPiece/forms/href` = `/smia/lego/pick`; `placePiece/forms/href` = `/smia/lego/place`
- [ ] `CapabilitiesAndSkills`: `Capability_PickPiece` and `Capability_PlacePiece` as SMC with qualifier `hasLifecycle=OFFER`
- [ ] `Skill_PickPiece` and `Skill_PlacePiece` as **Property** (not SMC) with qualifier `hasImplementationType=OPERATION`
- [ ] `SemanticRelationships`: 4 RelationshipElements with correct semanticIds and references

### File Placement
- [ ] `my_models/aas/LEGO_factory_case0.aasx` in place
- [ ] `my_models/aas/SMIA_Operator_article.aasx` in place (from SMIA repo examples)
- [ ] `my_models/aas/` contains ONLY the two `.aasx` files above — no backups, no other files
- [ ] `my_models/smia-initialization.properties` configured (see §10.1)
- [ ] `my_models/xmpp_server/ejabberd.yml` configured (see §10.2)
- [ ] `my_models/docker-compose.yml` configured with correct credentials and volume paths

### Node-RED
- [ ] Imported `my_models/flow_dida_central_lego.json` into Node-RED on DIDA central
- [ ] Flow deployed
- [ ] Direct test: `curl -X POST http://192.168.155.10:1880/smia/lego/pick -H 'Content-Type: application/json' -d '{"position":0}'` returns HTTP 200
- [ ] MQTT publish confirmed on `vicom/61/piso_0/lab/lego/commands`

### Docker Deployment
- [ ] Start: `docker compose -f my_models/docker-compose.yml up -d`
- [ ] All 3 containers running: `ejabberd`, `smia`, `smia-operator`
- [ ] `docker logs smia` shows `AAS model initialized.` and `Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']`
- [ ] `docker logs smia-operator` shows no errors

### End-to-End Test
- [ ] Open `http://localhost:10000/smia_operator`
- [ ] Click Load → SMIA appears in list
- [ ] Select `Capability_PickPiece` → Submit
- [ ] SMIA logs show `HTTP communication successfully completed.`
- [ ] Operator GUI shows success response with `status: ok`
- [ ] fischertechnik warehouse crane macro triggered physically

---

*This document was generated from verified runtime behavior and source files in `my_models/` as of 2026-03-04. All semantic IDs, values, and configuration snippets are taken directly from the implemented files.*

---

## 19. Case 1 — Multi-Agent Orchestration: Technical Reference

This section documents everything added for Case 1: the four custom Python files, the docker-compose changes, the AASX Package Explorer tutorial for the new AAS models, and the Node-RED modifications. Read §16 of `memoire.md` for the academic-level explanation of *why* the architecture is designed this way.

---

### 19.1 New Python Files

Case 1 requires four Python files, all under `additional_tools/extended_agents/`. None of these files are asset-specific code inside SMIA — they are extension-layer files that use the official SMIA extension hooks (`ExtensibleSMIAAgent`).

---

#### 19.1.1 `smia_machine_starter.py`

**Full path:** `additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py`

**Volume mount target (inside container):**
```
/usr/local/lib/python3.12/site-packages/smia/launchers/smia_docker_starter.py
```

**What it does.** The SMIA Docker image executes `python3 -m smia.launchers.smia_docker_starter` at startup. The default file at that path creates a plain `SMIAAgent`. By volume-mounting our file over it, Docker executes our code instead. Our file creates an `ExtensibleSMIAAgent` and calls `add_new_agent_service('machineAvailValue', get_machine_availability)` before starting the agent.

**Key design decision — why `sys.path.insert`:**
```python
sys.path.insert(0, os.path.dirname(__file__))
import smia_machine_agent_services as machine_svc
```
When Python runs this file as `smia.launchers.smia_docker_starter`, the module's directory (`/usr/local/lib/python3.12/site-packages/smia/launchers/`) is not automatically on `sys.path`. The explicit insert ensures `import smia_machine_agent_services` resolves to the companion file mounted in the same directory.

**Step-by-step walkthrough:**
1. `smia.initial_self_configuration()` — loads `smia-initialization.properties` from AASX or config folder, sets up logging, reads XMPP server address
2. `DockerUtils.get_aas_model_from_env_var()` — reads `AAS_MODEL_NAME` env var, prepends the AAS folder path → returns absolute path to the `.aasx` file inside the container
3. `smia.load_aas_model(aas_model_path)` — parses the AASX with the BaSyx Python SDK; stores the AAS object store in memory for subsequent self-configuration
4. Read `AGENT_ID` and `AGENT_PASSWD` from environment — each machine has its own XMPP credentials
5. `ExtensibleSMIAAgent(jid, passwd)` — creates the agent with extension hooks enabled
6. `add_new_agent_service('machineAvailValue', get_machine_availability)` — registers the Python function under the ID `'machineAvailValue'`, which must exactly match the `id_short` of the `SkillInterface` AAS element that references it via `accessibleThroughAgentService`
7. `smia.run(smia_agent)` — starts the SPADE event loop; SMIA runs its three-track self-configuration (AID, CSS, relationships), then enters `StateRunning`

**Shared across all machines.** machine0, machine1, and machine2 all use this same file. The only difference between them is in the AASX model and environment variables.

---

#### 19.1.2 `smia_machine_agent_services.py`

**Full path:** `additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py`

**Volume mount target (inside container):**
```
/usr/local/lib/python3.12/site-packages/smia/launchers/smia_machine_agent_services.py
```

**What it does.** Provides the `get_machine_availability()` function — the agent service that SMIA calls to compute the machine's negotiation score (`negValue`) during FIPA-CNP.

**How SMIA calls it.** When the orchestrator sends a CFP with `negCriterion = "http://www.w3id.org/upv-ehu/gcis/css-smia#Skill_NegAvailability"`, `HandleNegotiationBehaviour` looks up the OWL individual with that IRI, finds its associated `SkillInterface` (`machineAvailValue`), checks that its parent submodel is NOT the AID (which would make it an asset service), and calls:
```python
await agent_services.execute_agent_service_by_id('machineAvailValue')
```
which eventually calls `await get_machine_availability()`.

**Key design decision — no `self` parameter:**
```python
async def get_machine_availability():
    ...
```
SMIA stores external functions via `types.MethodType` binding, but when called, invokes them as `await get_machine_availability(**adapted_params)` with no positional arguments. Writing it as a plain `async def` (no `self`) is correct. Adding `self` would cause a `TypeError` at call time.

**Why `aiohttp` and not `requests`:**
```python
async with aiohttp.ClientSession() as session:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
```
SMIA runs in an `asyncio` event loop. A synchronous `requests.get()` call would block the entire event loop for up to 5 seconds, preventing all other SMIA behaviours (`ACLHandlingBehaviour`, etc.) from running during that time. `aiohttp` is the correct async HTTP client for this context.

**Return value semantics:**
- `1.0` — machine is free and ready
- `0.0` — machine is executing a task (busy) or Node-RED is unreachable
- Any error (connection, parse, unexpected) returns `0.0` — safe-fail default

**SMIA normalization note.** SMIA's `services_utils.py` divides `negValue` by 100 if it is greater than 1.0. Values in `[0.0, 1.0]` are used as-is. Returning `1.0` is always interpreted as "fully available."

---

#### 19.1.3 `smia_orchestrator_starter.py`

**Full path:** `additional_tools/extended_agents/smia_orchestrator_agent/smia_orchestrator_starter.py`

**Volume mount target (inside container):**
```
/usr/local/lib/python3.12/site-packages/smia/launchers/smia_docker_starter.py
```

**What it does.** Identical pattern to `smia_machine_starter.py` but for the orchestrator. The key difference is using `add_new_agent_capability()` instead of `add_new_agent_service()`:

```python
orch_behaviour = OrchestratorDispatchBehaviour()
smia_agent.add_new_agent_capability(orch_behaviour)
```

`add_new_agent_capability()` accepts a **SPADE behaviour instance** (not a class). The instance is stored internally and started alongside all base SMIA behaviours when `smia.run()` launches the agent. This means `OrchestratorDispatchBehaviour.on_start()` is called once at startup and `OrchestratorDispatchBehaviour.run()` is called repeatedly in the event loop thereafter.

---

#### 19.1.4 `orchestrator_dispatch_behaviour.py`

**Full path:** `additional_tools/extended_agents/smia_orchestrator_agent/orchestrator_dispatch_behaviour.py`

**Volume mount target (inside container):**
```
/usr/local/lib/python3.12/site-packages/smia/launchers/orchestrator_dispatch_behaviour.py
```

**What it does.** Implements the complete FIPA-CNP initiator logic. This is the primary software contribution of Case 1.

**Class structure:**
```
OrchestratorDispatchBehaviour (spade.behaviour.CyclicBehaviour)
    │
    ├── on_start()                       initialise pending_orchestrations dict
    ├── run()                            message router (4 routes)
    │
    ├── _start_negotiation(msg)          Phase A: discover + send CFP
    ├── _send_execution_request(thread, winner_jid)  Phase B: dispatch to winner
    ├── _forward_result_to_operator(thread, body)    Phase C: return result
    ├── _send_failure_to_operator(thread, reason)
    ├── _send_failure_to_operator_direct(sender, thread, reason)
    │
    ├── _discover_machines_for_request(cap_id_short, exclude_jid, color_filter)
    ├── _find_capability_color(object_store, cap_id_short)
    ├── _extract_jid_from_store(object_store)
    ├── _has_semantic_id(element, expected_iri)
    └── _find_property_by_semantic_id(element, semantic_id_iri)
```

**Key constants:**
```python
CSS_SMIA_IRI     = "http://www.w3id.org/upv-ehu/gcis/css-smia#"
NEG_CRITERION_IRI = CSS_SMIA_IRI + "Skill_NegAvailability"
AAS_FOLDER       = "/smia_archive/config/aas"
SEMANTICID_SOFTWARE_NAMEPLATE = "https://admin-shell.io/idta/SoftwareNameplate/1/0"
SEMANTICID_INSTANCE_NAME = (
    "https://admin-shell.io/idta/SoftwareNameplate/1/0/"
    "SoftwareNameplate/SoftwareNameplateInstance/InstanceName"
)
COLOR_POSITION_MAP = {"red": "0", "blue": "1", "white": "2"}
```

**`run()` — the message router:**
```python
async def run(self):
    msg = await self.receive(timeout=5)
    if msg is None:
        return
    # Route 1: new operator CSSRequest
    if (performative == REQUEST and ontology == css-service
            and thread not in reserved_threads
            and thread not in pending_orchestrations):
        await self._start_negotiation(msg)
    # Route 2: winner INFORM from negotiation
    elif (performative == INFORM
          and thread in pending_orchestrations
          and phase == 'negotiation'):
        if body.winner: await self._send_execution_request(thread, sender)
        else: await self._send_failure_to_operator(thread, "No machine available")
    # Route 3: execution INFORM from winner machine
    elif (performative == INFORM
          and thread in pending_orchestrations
          and phase == 'awaiting_result'):
        await self._forward_result_to_operator(thread, msg.body)
    # Route 4: FAILURE
    elif (performative == FAILURE
          and thread in pending_orchestrations):
        await self._send_failure_to_operator(thread, "Negotiation failed")
```

**`_start_negotiation()` — Phase A detail:**
1. Parse `capabilityIRI` and `skillParams` from operator message body
2. Extract `color` from `skillParams`; look up `resolved_position` in `COLOR_POSITION_MAP`
3. Derive `cap_id_short` from `capabilityIRI` (split on `#`)
4. Call `_discover_machines_for_request(cap_id_short, own_jid, color_filter=color)`
5. If no machines found → send FAILURE to operator immediately
6. Generate `neg_thread = str(uuid.uuid4())`; reserve it
7. Store in `pending_orchestrations[neg_thread]`: phase, op_thread, op_sender, skill_params, capability_iri, resolved_position
8. Build CFP body: `{capabilityIRI, negCriterion, negTargets, negRequester=own_jid, skillParams}`
9. Send CFP to each machine JID

**`_discover_machines_for_request()` — AAS folder scan:**
```
for each .aasx in AAS_FOLDER:
    open with AASXReader → DictObjectStore
    extract JID from SoftwareNameplate/InstanceName
    if JID == own_jid → skip
    find Capability SMC by cap_id_short → read color child property
    if color_filter and color != filter → skip
    append {jid, color} to results
```

**`_send_execution_request()` — Phase B detail:**
1. Read `resolved_position` from the negotiation state (stored in Phase A)
2. Generate `exec_thread = str(uuid.uuid4())`; reserve it
3. Store in `pending_orchestrations[exec_thread]`: phase=awaiting_result, neg_thread, op_thread, op_sender
4. Set negotiation state phase → 'done'
5. Build execution body: `{capabilityIRI, skillParams: {position: resolved_position}}`
6. Send REQUEST to winner JID on exec_thread

**`_forward_result_to_operator()` — Phase C detail:**
1. Build INFORM message to op_sender on op_thread
2. Copy result body from machine's execution INFORM
3. Send INFORM
4. Clean up: remove exec_thread and neg_thread entries from pending_orchestrations

---

### 19.2 docker-compose.yml Changes

**Summary of changes from Case 0:**

| Change | Detail |
|---|---|
| Renamed `smia` → `smia-machine0` | Explicit naming for clarity |
| Added `smia-machine1` | `LEGO_machine1_case0.aasx`, `smia_machine1@ejabberd:machine1pass` |
| Added `smia-machine2` | `LEGO_machine2_case0.aasx`, `smia_machine2@ejabberd:machine2pass` |
| Added `smia-orchestrator` | `Orchestrator_case0.aasx`, `smia_orch@ejabberd:password` |
| Updated `CTL_ON_CREATE` | Registers all 5 agent accounts in ejabberd |
| Added volume mounts for starters | 2 mounts per machine service + 2 mounts for orchestrator |

**Volume mount pattern — why two mounts per machine:**

```yaml
volumes:
  # Mount 1: replaces the Docker entrypoint module
  - ../additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py:
    /usr/local/lib/python3.12/site-packages/smia/launchers/smia_docker_starter.py

  # Mount 2: the companion services module — must be in the same directory
  # so that `import smia_machine_agent_services` resolves from the starter
  - ../additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py:
    /usr/local/lib/python3.12/site-packages/smia/launchers/smia_machine_agent_services.py
```

Mount 1 replaces the entrypoint. Mount 2 places the imported module in the same directory as the entrypoint so Python's module search finds it.

**Orchestrator dependency chain:**
```yaml
smia-orchestrator:
  depends_on:
    xmpp-server:
      condition: service_healthy
    smia-machine0:
      condition: service_started
    smia-machine1:
      condition: service_started
    smia-machine2:
      condition: service_started
```
The orchestrator waits for all machines to be started (not necessarily healthy) to ensure their XMPP accounts are registered and their agents are booting before the orchestrator tries to send CFPs.

**Phase 1 startup command (machines only, no orchestrator):**
```bash
cd my_models
docker compose up xmpp-server smia-machine0 smia-machine1 smia-machine2 smia-operator
```

**Phase 2 startup command (full system):**
```bash
cd my_models
docker compose up
```

**Full reset (including ejabberd user database):**
```bash
docker compose down -v
```
Note: `-v` removes the `ejabberd_data` volume. Accounts registered via `CTL_ON_CREATE` are re-created on next `docker compose up`. Omit `-v` to preserve the volume between restarts.

---

### 19.3 AASX Package Explorer — Case 1 Tutorial

The following four tasks must be completed manually in AASX Package Explorer before starting the Docker Compose deployment.

---

#### 19.3.A Modify `LEGO_factory_case0.aasx` (machine0 — red pieces)

Open `my_models/aas/LEGO_factory_case0.aasx` in AASX Package Explorer.

**Step 1 — Add `color` property inside `Capability_PickPiece`:**
- Navigate to: `LEGO_factory` shell → `CapabilitiesAndSkills` submodel → `Capability_PickPiece` SMC
- Right-click → Add Element → **Property**
- `idShort`: `color`
- `valueType`: `xs:string`
- `value`: `red`
- No semanticId needed (plain constraint property)

**Step 2 — Add `color` property inside `Capability_PlacePiece`:**
- Repeat Step 1 inside `Capability_PlacePiece`
- Same values: idShort=`color`, valueType=`xs:string`, value=`red`

**Step 3 — Add `Skill_NegAvailability` at submodel level:**
- Navigate to: `CapabilitiesAndSkills` submodel (not inside a SMC — at the top level)
- Right-click → Add Element → **Property**
- `idShort`: `Skill_NegAvailability`
- `valueType`: `xs:string`
- `value`: (leave empty)
- **SemanticId**: `http://www.w3id.org/hsu-aut/css#Skill` (ExternalReference, ModelReference=false)
- **Qualifier**: Add Qualifier
  - `type`: `hasImplementationType`
  - `value`: `OPERATION`
  - `valueType`: `xs:string`

> **Why is it a `Skill` and not a `SkillInterface` directly?**
>
> In the CSS model, a **Skill** is a *concrete, technology-specific implementation* of a function. A **SkillInterface** is the *access point* to invoke that implementation. `Skill_NegAvailability` IS a Skill because "check availability via HTTP GET to Node-RED" is a specific implementation choice — another machine could implement the same role differently. The `negCriterion` field in the CFP body points to a Skill IRI because SMIA resolves: `negCriterion → Skill OWL individual → .get_associated_skill_interface_instances() → SkillInterface → agent service`. If `negCriterion` pointed directly at the SkillInterface, `get_associated_skill_interface_instances()` would return nothing and the negotiation score would default to 0.0 (source: `handle_negotiation_behaviour.py:304`, `capability_skill_ontology.py:126`). The naming follows the existing SMIA convention: `Skill_PickPiece`, `Skill_PlacePiece`, `Skill_NegAvailability`.
>
> Note: `Skill_NegAvailability` does NOT need an `isRealizedBy` link to any Capability. The negotiation behaviour accesses it directly by IRI from the CFP `negCriterion` field — the Capability layer is bypassed for negotiation purposes.

**Step 4 — Add `machineAvailValue` at submodel level:**
- Navigate to: `CapabilitiesAndSkills` submodel (same level as Step 3)
- Right-click → Add Element → **Property**
- `idShort`: `machineAvailValue` ← must be exactly this string — it is the key used to call `execute_agent_service_by_id('machineAvailValue')` at runtime
- `valueType`: `xs:string`
- `value`: (leave empty)
- **SemanticId**: `http://www.w3id.org/hsu-aut/css#SkillInterface` (ExternalReference)

> **Why `machineAvailValue` must be in `CapabilitiesAndSkills` and NOT in `AssetInterfacesDescription`:**
>
> SMIA checks which submodel the SkillInterface element lives in (source: `handle_negotiation_behaviour.py:309`):
> - Parent submodel has AID semantic ID → **asset service** path: SMIA makes an HTTP call following the AID `forms/href/method` structure
> - Parent submodel is anything else → **agent service** path: SMIA calls `execute_agent_service_by_id(id_short)`
>
> `machineAvailValue` has no AID structure (no forms/href/method). Placing it in the AID would send SMIA down the asset service path, which would fail. Placing it in `CapabilitiesAndSkills` correctly routes SMIA to call the Python function registered via `add_new_agent_service('machineAvailValue', get_machine_availability)` in `smia_machine_starter.py`.

**Step 5 — Add relationship in `SemanticRelationships` submodel:**
- Navigate to: `LEGO_factory` shell → `SemanticRelationships` submodel
- Right-click → Add Element → **RelationshipElement**
- `idShort`: `rel_SkillNegAvail_accessibleThroughAgentService`
- **SemanticId**: `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService`
- **First reference** (the skill): navigate to `CapabilitiesAndSkills / Skill_NegAvailability`
- **Second reference** (the interface): navigate to `CapabilitiesAndSkills / machineAvailValue`

**Save the file.** File → Save.

---

#### 19.3.B Create `LEGO_machine1_case0.aasx` (blue pieces)

1. **Clone** `LEGO_factory_case0.aasx`:
   - File → Save As → `LEGO_machine1_case0.aasx` (save to same `my_models/aas/` folder)

   > From this point, all edits are on the clone.

2. **Update the factory shell identity:**
   - Click on the `LEGO_factory` AAS shell
   - Change `idShort`: `LEGO_machine1`
   - Change `id`: `urn:uuid:6475_0111_2062_0001`

3. **Update the SMIA agent shell identity:**
   - Click on the `SMIA_agent` AAS shell
   - **Leave `idShort` as `SMIA_agent`** — this display name has no runtime significance. Each file is a separate AASX package, so no conflict arises. Keeping the same idShort is intentional and consistent with the original.
   - Change `id`: `urn:uuid:6475_1111_2062_0001` (new UUID — this IS significant, must be globally unique)
   - Navigate to: `SMIA_agent` shell → `SoftwareNameplate` submodel → find the SMC that contains `InstanceName`
   - Change `InstanceName` value: `smia_machine1@ejabberd`

   > **Why the `SMIA_agent` shell exists (two-shell architecture):**
   >
   > Each machine AASX contains two AAS shells. This is a deliberate SMIA design choice from the paper (§3):
   > - `LEGO_factory` / `LEGO_machine1` — the **physical asset** DT: AID, Capabilities, Skills, CSS relationships. Used by SMIA for self-configuration, selected via the `AAS_ID` Docker env var.
   > - `SMIA_agent` — the **software agent** DT: SoftwareNameplate (identity, XMPP JID). Used by the operator GUI for discovery.
   >
   > The operator GUI's `get_smia_jid_from_aas_store()` searches every AASX for a submodel with the SoftwareNameplate semantic ID, then reads the `InstanceName` property value. This is what appears in the GUI list — not the shell's `idShort`. So when you load `LEGO_machine1_case0.aasx`, the GUI shows `smia_machine1@ejabberd` as the agent entry.
   >
   > The two shells are packaged together in one AASX because they are deployed together in one Docker container. The AAS standard explicitly supports multiple shells per package for exactly this reason.

4. **Update colour constraints:**
   - Navigate to: `LEGO_machine1` shell → `CapabilitiesAndSkills` → `Capability_PickPiece` → `color` property
   - Change value: `blue`
   - Navigate to: `Capability_PlacePiece` → `color` property
   - Change value: `blue`

5. **Save the file.** File → Save.

---

#### 19.3.C Create `LEGO_machine2_case0.aasx` (white pieces)

Repeat the same steps as 19.3.B. The two-shell rationale and idShort explanation from §19.3.B apply equally here. With these values:

| Field | Value |
|---|---|
| Output filename | `LEGO_machine2_case0.aasx` |
| Factory shell idShort | `LEGO_machine2` |
| Factory shell id | `urn:uuid:6475_0111_2062_0002` |
| Agent shell id | `urn:uuid:6475_1111_2062_0002` |
| InstanceName | `smia_machine2@ejabberd` |
| Capability_PickPiece/color | `white` |
| Capability_PlacePiece/color | `white` |

---

#### 19.3.D Create `Orchestrator_case0.aasx` (from scratch)

File → New → Create empty AASX package. Then:

**Step 1 — Create the orchestrator AAS shell:**
- Add AAS shell
- `idShort`: `SMIA_orchestrator`
- `id`: `urn:uuid:8888_0001_2026_0001`

**Step 2 — Create `SoftwareNameplate` submodel:**
- Add Submodel
- `idShort`: `SoftwareNameplate`
- `id`: `urn:uuid:sw_nameplate_orch_001`
- **SemanticId**: `https://admin-shell.io/idta/SoftwareNameplate/1/0` (ExternalReference)
- Inside this submodel, add a **SubmodelElementCollection**:
  - `idShort`: `SoftwareNameplateInstance_smia_orch`
  - Inside the SMC, add a **Property**:
    - `idShort`: `InstanceName`
    - `valueType`: `xs:string`
    - `value`: `smia_orch@ejabberd`
    - **SemanticId**: `https://admin-shell.io/idta/SoftwareNameplate/1/0/SoftwareNameplate/SoftwareNameplateInstance/InstanceName`
- Link this submodel to the orchestrator AAS shell

**Step 3 — Create `CapabilitiesAndSkills` submodel:**
- Add Submodel with `idShort`: `CapabilitiesAndSkills`
- Add **SubmodelElementCollection** `Capability_PickPiece`:
  - **SemanticId**: `http://www.w3id.org/upv-ehu/gcis/css-smia#AgentCapability`
  - **Qualifier**: `hasLifecycle = OFFER`
  - Child **Property** `position` (xs:int) — declares that the capability accepts a position parameter
- Add **SubmodelElementCollection** `Capability_PlacePiece` (same pattern)
- Add **Property** `Skill_Orchestrate_PickPiece`:
  - `valueType`: `xs:string`
  - **SemanticId**: `http://www.w3id.org/hsu-aut/css#Skill`
  - **Qualifier**: `hasImplementationType = OPERATION`
- Add **Property** `Skill_Orchestrate_PlacePiece` (same pattern)
- Link this submodel to the orchestrator AAS shell

**Why `AgentCapability` (not `AssetCapability`)?** The orchestrator does not directly control a physical machine. Its capability is an *agent-level* function — coordination and delegation. `AgentCapability` is the correct CSS class for functions performed by the digital twin agent itself rather than by a physical asset.

**Step 4 — Create `SemanticRelationships` submodel:**
- Add Submodel with `idShort`: `SemanticRelationships`
- Add **RelationshipElement** `rel_CapPick_isRealizedBy_SkillOrchPick`:
  - **SemanticId**: `http://www.w3id.org/hsu-aut/css#isRealizedBySkill`
  - First: `CapabilitiesAndSkills / Capability_PickPiece`
  - Second: `CapabilitiesAndSkills / Skill_Orchestrate_PickPiece`
- Add **RelationshipElement** `rel_CapPlace_isRealizedBy_SkillOrchPlace` (same pattern for place)
- **Do NOT add** `accessibleThroughAssetService` or `accessibleThroughAgentService` relationships — the orchestrator's capabilities are handled entirely by `OrchestratorDispatchBehaviour`, not by a registered skill interface
- Link this submodel to the orchestrator AAS shell

**Step 5 — Embed required files:**
- In AASX Package Explorer: Extras → AASX File Repository → Add supplemental files
- Add `aasx/CSS-ontology-smia.owl` (copy from `LEGO_factory_case0.aasx`)
- Add `aasx/smia-initialization.properties` (copy from `LEGO_factory_case0.aasx`)
- The properties file can be the same content — runtime values come from Docker env vars

**Step 6 — Save:** File → Save → `Orchestrator_case0.aasx` in `my_models/aas/`

---

### 19.4 Node-RED Changes (DIDA Central — 192.168.155.10:1880)

Three changes are needed in the Node-RED instance on the DIDA central machine.

---

#### 19.4.1 Add busy flag to the pick flow

Open the existing `POST /smia/lego/pick` flow.

**Add a Function node immediately after the HTTP In node** (before the JSON parse):
- Node name: `Set busy`
- Code:
```javascript
global.set("machine_busy", true);
return msg;
```

**Add a Function node immediately before the HTTP Response node** (after the MQTT Out node):
- Node name: `Set free`
- Code:
```javascript
global.set("machine_busy", false);
return msg;
```

---

#### 19.4.2 Add busy flag to the place flow

Repeat 19.4.1 for the `POST /smia/lego/place` flow. The same global variable `machine_busy` is used.

---

#### 19.4.3 Add the `GET /smia/lego/availability` endpoint

Create a new flow:

**Node 1 — HTTP In:**
- Method: `GET`
- URL: `/smia/lego/availability`

**Node 2 — Function:**
- Name: `Read busy flag`
- Code:
```javascript
var busy = global.get("machine_busy") || false;
msg.payload = busy ? "0.0" : "1.0";
msg.statusCode = 200;
msg.headers = { "Content-Type": "text/plain" };
return msg;
```

**Node 3 — HTTP Response**
- Connect: HTTP In → Function → HTTP Response

**Why plain text response (not JSON)?** The `get_machine_availability()` Python function parses the response as `float(text.strip())`. A JSON response like `{"availability": 1.0}` would cause `float('{"availability": 1.0}')` to raise a `ValueError`, which is caught and causes the function to return `0.0` (machine appears busy). Plain text `"1.0"` or `"0.0"` parses directly.

**Deploy all flows** after making these changes. Test the endpoint:
```bash
curl http://192.168.155.10:1880/smia/lego/availability
# Expected: 1.0
```

---

### 19.5 Phase 1 Testing Procedure (Machines Only)

This validates the extension mechanism (custom Docker entrypoint, `ExtensibleSMIAAgent`, `machineAvailValue` service) without the orchestrator.

```bash
cd my_models
docker compose up xmpp-server smia-machine0 smia-machine1 smia-machine2 smia-operator
```

**Expected startup logs for each machine:**
```
Machine SMIA: initial self-configuration complete.
Machine SMIA: loading AAS model from /smia_archive/config/aas/LEGO_factory_case0.aasx
Machine SMIA: registered 'machineAvailValue' agent service.
AAS model initialized.
Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']
[StateRunning]
```

**Validation checklist:**

- [ ] `docker logs smia-machine0` shows `Analyzed capabilities` and `StateRunning`
- [ ] `docker logs smia-machine1` shows the same for `LEGO_machine1_case0.aasx`
- [ ] `docker logs smia-machine2` shows the same for `LEGO_machine2_case0.aasx`
- [ ] Operator GUI at `http://localhost:10000/smia_operator` → Load → shows all 3 machine JIDs
- [ ] Send `Capability_PickPiece` with `skillParams: {position: 0}` directly to `SMIA_agent@ejabberd` → crane moves
- [ ] `curl http://192.168.155.10:1880/smia/lego/availability` returns `1.0` at rest
- [ ] Trigger pick → immediately query availability → should return `0.0` (busy)

---

### 19.6 Phase 2 Testing Procedure (Full Orchestration)

```bash
cd my_models
docker compose up
```

**Expected orchestrator startup logs:**
```
Orchestrator SMIA: initial self-configuration complete.
Orchestrator SMIA: registered OrchestratorDispatchBehaviour.
OrchestratorDispatchBehaviour started.
[StateRunning]
```

**Validation — full orchestration flow:**

1. Open `http://localhost:10000/smia_operator`
2. Click Load → `smia_orch@ejabberd` appears alongside the 3 machines
3. Select `smia_orch@ejabberd` and `Capability_PickPiece`
4. Set `skillParams: {color: "red"}`
5. Submit

**Expected orchestrator log sequence:**
```
new CSSRequest from operator (thread=<op_T>)
Eligible machine: SMIA_agent@ejabberd (color=red) from LEGO_factory_case0.aasx
CFP sent to SMIA_agent@ejabberd (neg_thread=<neg_T>)
received winner INFORM (thread=<neg_T>) from SMIA_agent@ejabberd
execution REQUEST sent to SMIA_agent@ejabberd (exec_thread=<exec_T>)
result forwarded to operator (exec_thread=<exec_T>)
```

**Colour routing test:**
- Send `{color: "blue"}` to orchestrator → watch `smia-machine1` logs, NOT machine0 or machine2
- Send `{color: "white"}` → watch `smia-machine2` logs only

**Failure test:**
- Send `{color: "green"}` → orchestrator returns `FAILURE` immediately (no machine with color=green)
- Operator GUI displays failure response

**Troubleshooting Case 1:**

| Symptom | Most likely cause | Fix |
|---|---|---|
| Orchestrator logs show `no machines found` | AASX not in `aas/` folder, or color not in capability | Verify `.aasx` files exist in `my_models/aas/`; check `Capability_PickPiece/color` value |
| Machine never reaches StateRunning | `Skill_NegAvailability` or `machineAvailValue` incorrectly defined | Check semanticId matches exactly; Skills must be Property not SMC |
| `INFORM(winner)` never arrives at orchestrator | `negRequester` field missing or wrong | Check `negRequester` is set to orchestrator JID in CFP body |
| Operator GUI crashes on Load (500 error) | Non-AASX file in `aas/` folder | Remove any backup, XML, or JSON files from `my_models/aas/` |
| `aiohttp` import error in machine logs | `aiohttp` not installed in image | aiohttp is a smia dependency — verify image version |

---

*Case 1 implementation completed 2026-03-16. All Python files are in `additional_tools/extended_agents/`. AAS models must be created manually in AASX Package Explorer following §19.3 above.*
