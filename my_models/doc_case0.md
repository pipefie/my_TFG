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

In SMIA's extension (`CSS-ontology-smia.owl`), the key concepts are:

- **Capability**: An abstract ability of an asset or agent (e.g., "pick a piece"). Not tied to any specific implementation.
- **Skill**: A concrete implementation of a capability (e.g., "call the Node-RED HTTP endpoint to pick"). Linked to a capability via `isRealizedBy`.
- **SkillInterface**: Describes how a skill is accessed (e.g., an HTTP action in the AID submodel). Linked to a skill via `accessibleThroughAssetService` (for physical assets) or `accessibleThroughAgentService` (for agent services).

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

```
owl:Thing
└── Capability
    ├── AgentCapability
    └── AssetCapability     ← used in Case 0
└── Skill                   ← used in Case 0
└── SkillInterface
└── SkillParameter
└── StateMachine
```

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
