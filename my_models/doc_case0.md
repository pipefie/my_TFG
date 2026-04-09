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
                                     │ (+SkillImplementationType: OPERATION | ...)
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

## 6.5 AAS Qualifiers and the OWL Bridge

### 6.5.1 What is a Qualifier?

A **Qualifier** (AAS metamodel Part 1, §10.2.3) is a metadata annotation that can be attached to any `SubmodelElement`. It is the AAS standard extension mechanism for expressing domain-specific semantic attributes of an element that the fixed AAS element types (`Property`, `SubmodelElementCollection`, etc.) cannot capture alone.

A Qualifier has three fields that matter at runtime:

| Field | Type | Role |
|---|---|---|
| `type` | string | Human-readable label: e.g. `"SkillImplementationType"`, `"hasLifecycle"` |
| `value` | string | The attribute's data value: e.g. `"OPERATION"`, `"OFFER"` |
| `semanticId` | GlobalReference (IRI) | Links this qualifier to a concept in an external ontology |

### 6.5.2 Why two semanticIds? Element vs. Qualifier

This is the key distinction. A `SubmodelElement` can have its own `semanticId` **and** its qualifiers each have their own `semanticId`. These are not redundant — they answer two completely different questions:

| Level | Question | Maps to OWL |
|---|---|---|
| **Element `semanticId`** | *What type/class is this element?* | An `owl:Class` |
| **Qualifier `semanticId`** | *What attribute/property does this qualifier represent?* | An `owl:DatatypeProperty` |

Example — `Skill_PickPiece`:
```
AAS element                              OWL ontology
──────────────────────────────────────   ────────────────────────────────
Property "Skill_PickPiece"
  semanticId: css#Skill           →      owl:Class "Skill"

  Qualifier:
    type:  "SkillImplementationType"
    value: "OPERATION"
    semanticId: css-smia#hasImpl… →      owl:DatatypeProperty "hasImplementationType"
                                             domain: Skill
                                             range: {OPERATION, STATE, TRIGGER, FUNCTIONBLOCK}
```

The element's `semanticId` (`css#Skill`) tells SMIA: "this AAS `Property` element represents an individual of the OWL class `Skill`."
The qualifier's `semanticId` (`css-smia#hasImplementationType`) tells SMIA: "this qualifier carries the value of the OWL data property `hasImplementationType` on that individual."

Without the qualifier's `semanticId`, SMIA cannot perform step 2 below — it cannot know which OWL data property this qualifier's value belongs to.

### 6.5.3 How SMIA uses the Qualifier semanticId at boot

During self-configuration (Booting state), `add_ontology_required_information()` (`init_aas_model_behaviour.py:188-204`) bridges AAS qualifiers into the OWL ontology:

1. For each CSS OWL class instance just created (e.g., `Skill_PickPiece`), ask the OWL ontology: "which `owl:DatatypeProperty` declarations have this class in their `rdfs:domain`?" (`capability_skill_module.py:71-75`)
   - For `Skill`: the ontology returns `hasImplementationType` (IRI: `css-smia#hasImplementationType`)
   - For `Capability`: the ontology returns `hasLifecycle` (IRI: `css-smia#hasLifecycle`)

2. For each data property IRI found, call `get_qualifier_value_by_semantic_id(iri)` on the AAS element — which loops over all qualifiers and checks whether `qualifier.semanticId == iri`.

3. Store the found value on the OWL instance: `ontology_instance.set_data_property_value('hasImplementationType', 'OPERATION')`.

4. The OWL instance is now a fully populated Python representation of that CSS individual.

**If step 2 fails** (no qualifier has a matching semanticId) → `AASModelReadingError` → the OWL instance's data property value is never set → any runtime code that reads this property gets `None` → `HandleNegotiationBehaviour.get_neg_value_with_criteria()` crashes at `list(None)[0]`.

### 6.5.4 Two lookup mechanisms — why the semanticId is context-dependent

SMIA has two completely independent methods for reading a skill qualifier value:

**Mechanism 1 — type-based** (`extended_submodel.py:99`):
```python
skill_qualifier = self.get_qualifier_by_type('SkillImplementationType')
```
Searches by the `type` string field. Used by `check_cap_skill_ontology_qualifier_for_skills()` when validating a capability request. **Does not need a semanticId.** Used in the direct execution path (Case 0, single machine).

**Mechanism 2 — semanticId-based** (`init_aas_model_behaviour.py:200`):
```python
required_value = aas_model_elem.get_qualifier_value_by_semantic_id(required_value_iri)
```
Searches by the `semanticId` IRI. Used during boot to populate OWL instances. **Requires the semanticId to be set.** Used in the multi-agent path (Case 1, FIPA-CNP negotiation).

The official preset file (`SMIA-css-qualifier-presets.json`) defines `SkillImplementationType` with `semanticId: null` — it was written for single-machine deployments where only Mechanism 1 is needed.

### 6.5.5 No ConceptDescription needed

A `ConceptDescription` is a documentation element inside the AASX package — it embeds a human-readable definition of a concept for self-contained use. The qualifier's `semanticId` is an `ExternalReference` (GlobalReference) pointing to an IRI in an external standard (the OWL ontology). SMIA's lookup (`check_semantic_id_exist()` in `extended_base.py:14-29`) does a plain string comparison on the IRI — it does not require a `ConceptDescription` to exist in the package.

### 6.5.6 The three CSS qualifiers — complete reference

| Qualifier `type` string | OWL DatatypeProperty IRI | OWL domain | Allowed values | SemanticId required? |
|---|---|---|---|---|
| `hasLifecycle` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasLifecycle` | `css#Capability` | `OFFER`, `ASSURANCE`, `REQUIREMENT` | **Yes** (present in preset) |
| `SkillImplementationType` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` | `css#Skill` | `OPERATION`, `STATE`, `TRIGGER`, `FUNCTIONBLOCK` | **Only for Case 1+** (missing in preset) |
| `hasCondition` | `http://www.w3id.org/upv-ehu/gcis/css-smia#hasCondition` | `css#CapabilityConstraint` | `PRECONDITION`, `POSTCONDITION`, `INVARIANT` | **Yes** (present in preset) |

Note: the `type` field of the `SkillImplementationType` qualifier says `"SkillImplementationType"`, but the OWL DatatypeProperty is named `hasImplementationType`. The `type` string is a human-readable label chosen by the SMIA team for AASX PE convenience. The `semanticId` IRI is the authoritative, machine-readable reference. Both come from the UPV/EHU team's SMIA CSS ontology; they are not invented.

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
│   └── Qualifier: type=SkillImplementationType, value=OPERATION
└── Skill_PlacePiece  [Property, xs:string, semanticId: css#Skill]
    └── Qualifier: type=SkillImplementationType, value=OPERATION
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

> **Critical — `#isRealizedBy` NOT `#isRealizedBySkill`:** The CSS OWL ontology (`CSS-ontology-smia.owl`) defines `#isRealizedBySkill` as a valid sub-property of `#isRealizedBy` (with domain=`Capability`, range=`Skill`). However, SMIA resolves AAS `RelationshipElement` semanticIds using **exact string comparison** against the constants in `CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS` (`css_ontology_utils.py:230`). Only `http://www.w3id.org/hsu-aut/css#isRealizedBy` is in that list — `#isRealizedBySkill` is not. Any relationship tagged with `#isRealizedBySkill` is silently skipped during Track 3 of self-configuration. The operator GUI uses the same constant list to count capabilities and skills: using `#isRealizedBySkill` causes the GUI to display **0 capabilities and 0 skills** for every loaded SMIA. The AASX PE preset file (`SMIA-css-semantic-ids-sm.add-options.json`) correctly defines only `#isRealizedBy` — there is no `#isRealizedBySkill` entry.

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

**Import SMIA qualifier presets (recommended):** The SMIA repository ships an official preset file for AASX PE that defines all CSS qualifiers with the correct types and semanticIds:

```
additional_resources/aasx_package_explorer_resources/SMIA-css-qualifier-presets.json
```

To import it in AASX PE: **Edit → Edit Options… → Qualifier Presets → Load…** → select the JSON file. After importing, you can apply qualifiers via **Add Qualifier → (preset dropdown)** instead of typing IRIs manually. The presets are authoritative — they define exactly:
- `hasLifecycle` qualifier for Capabilities (semanticId: `css-smia#hasLifecycle`, values: `OFFER/ASSURANCE/REQUIREMENT`)
- `SkillImplementationType` qualifier for Skills (values: `OPERATION/STATE/TRIGGER/FUNCTIONBLOCK`). The preset has `semanticId: null` — this is sufficient for **single-machine** execution (Case 0), where SMIA checks the qualifier by `type` string only. For **multi-agent** machines (Case 1+), a `semanticId` must be added (see §19.3.A Step 3 note).
- `hasCondition` qualifier for CapabilityConstraints (semanticId: `css-smia#hasCondition`, values: `PRECONDITION/POSTCONDITION/INVARIANT`)

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
   - Type: `SkillImplementationType`
   - Value: `OPERATION`
   - SemanticId: (leave empty for Case 0 single-machine only — see the note below for Case 1 machines)

> **SemanticId on `SkillImplementationType` — two mechanisms, two contexts:**
>
> SMIA reads `SkillImplementationType` via two independent mechanisms:
>
> **Mechanism 1 — type-based** (`extended_submodel.py:99`): `get_qualifier_by_type('SkillImplementationType')`. Searches by qualifier `type` string. Used by `check_cap_skill_ontology_qualifier_for_skills()` during capability request validation. **Works without semanticId.** This is what single-machine Case 0 uses.
>
> **Mechanism 2 — semanticId-based** (`init_aas_model_behaviour.py:198-202`): During boot, SMIA reads all OWL data properties of the `Skill` class from the loaded ontology. `hasImplementationType` is such a property (defined in `CSS-ontology-smia.owl:429` as `owl:DatatypeProperty` at IRI `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`). SMIA then calls `get_qualifier_value_by_semantic_id(iri)` — which searches qualifiers by their `semanticId`, not by `type`. If no qualifier has that semanticId → `AASModelReadingError` → the skill's OWL instance is not fully populated → `get_associated_skill_interface_instances()` returns `None` → `HandleNegotiationBehaviour` crashes.
>
> **For Case 0 single-machine AASXs** (this file): leave semanticId empty — Mechanism 1 is sufficient.
>
> **For Case 1 multi-agent machine AASXs** (`LEGO_factory_case0.aasx`, `LEGO_machine1_case0.aasx`, `LEGO_machine2_case0.aasx`): the semanticId on every skill's `SkillImplementationType` qualifier **must** be set to `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` — otherwise the negotiation path crashes at boot.

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

The compose file defines 7 services across two categories. All services share the `smia-net`
Docker bridge network — Docker DNS resolves container names (`ejabberd`, `nodered`,
`mosquitto-central`) automatically without any `/etc/hosts` changes. Credentials come from
`my_models/.env` (gitignored); copy `.env.example` to `.env` and fill in passwords before
the first `docker compose up`.

**Pre-built public images — no Dockerfile, no build step:**

| Service | Image | Role |
|---|---|---|
| `xmpp-server` | `ghcr.io/processone/ejabberd` | XMPP message broker; auto-registers all agent accounts on first start via `CTL_ON_CREATE` |
| `nodered` | `nodered/node-red:latest` | HTTP→MQTT bridge; loads `./nodered/flows.json` on startup |
| `mosquitto-central` | `eclipse-mosquitto:2` | Central MQTT broker; bridges to the physical machine's MQTT broker via `./mosquitto/conf.d/bridge.conf` |

**Custom images — built from Dockerfiles (run `docker compose build` first):**

| Service | Dockerfile | Role |
|---|---|---|
| `smia-machine0`, `smia-machine1`, `smia-machine2` | `my_models/docker/smia-machine/Dockerfile` | Machine agents; share one Dockerfile, differ only in AASX and env vars |
| `smia-orchestrator` | `my_models/docker/smia-orchestrator/Dockerfile` | FIPA-CNP dispatcher; receives capability requests from operator and negotiates with machines |
| `smia-operator` | `additional_tools/extended_agents/smia_operator_agent/Dockerfile` | Web GUI agent; exposes port 10000; scans `aas/` to discover SMIA targets |

**Key design decisions:**
- All machine services `depends_on: xmpp-server: condition: service_healthy` and `nodered: condition: service_started` — agents never attempt XMPP connection before the server is ready
- Volume `./aas:/smia_archive/config/aas` is shared by all agents — one folder holds all AASX files
- `NODERED_URL=http://nodered:1880` is injected into all machine containers; Docker DNS resolves `nodered` to the Node-RED service

### 11.2 XMPP Accounts

All XMPP accounts are registered automatically on first ejabberd startup via `CTL_ON_CREATE`:

| Account | Service that uses it |
|---|---|
| `SMIA_agent@ejabberd` | `smia-machine0` |
| `smia_machine1@ejabberd` | `smia-machine1` |
| `smia_machine2@ejabberd` | `smia-machine2` |
| `smia_orch@ejabberd` | `smia-orchestrator` |
| `operator001@ejabberd` | `smia-operator` |

Credentials are defined in `.env` via `MACHINEx_PASSWD`, `ORCH_PASSWD`, `OPERATOR_PASSWD`.
These must match the `AGENT_PASSWD` env vars passed to each container. To add a new account
(e.g., when adding a new machine), append to `CTL_ON_CREATE` in `docker-compose.yml` — or,
if ejabberd is already running, register manually:
```bash
docker exec ejabberd ejabberdctl register smia_machineN ejabberd <password>
```

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
2. Only then machine agents, orchestrator, and operator start and attempt XMPP connection.

If any agent starts before ejabberd is ready, the XMPP connection fails and the container exits. The `healthcheck` on `xmpp-server` prevents this.

### 11.5 Docker Image Build Process

#### What `docker compose build` does

`docker compose build` executes the Dockerfile for every service that has a `build:` block.
Services using a public `image:` (ejabberd, nodered, mosquitto) are skipped — Docker pulls
those automatically on first `up`. You only need to run `build` once, and again after changing
a Dockerfile or any `.py` file that is `COPY`d into a custom image.

A Dockerfile is a **recipe**: each instruction adds a layer on top of the previous one.
The result is an immutable image that can be started as many containers as needed.

#### Why COPY instead of `pip install smia`

`ekhurtado/smia:latest-alpine` already has SMIA installed via `pip install smia` — it is the
base layer. We do not reinstall the framework; we build our application on top of it.

| Dockerfile layer | Analogy | What it actually is |
|---|---|---|
| `FROM ekhurtado/smia:latest-alpine` | Python + framework already installed | Alpine Linux + Python + `pip install smia` already done by the SMIA team |
| `COPY + RUN` patch block | Patching a bug in the framework | Overwriting the installed `smia_agent.py` with our fixed version |
| `COPY smia_machine_starter.py /` | Copying your `app.py` | Our custom launcher that creates `ExtensibleSMIAAgent` |

#### Machine Dockerfile walkthrough (`my_models/docker/smia-machine/Dockerfile`)

```dockerfile
FROM ekhurtado/smia:latest-alpine
# ↑ Start from the official SMIA image. Python, SMIA, and all dependencies
#   are already installed. This is our base — we add layers on top.

LABEL maintainer="afierro@vicomtech.org" ...
# ↑ Metadata only. No filesystem change. Useful for `docker inspect`.

COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py
# ↑ Stage our patched version of the SMIA framework file in /tmp.

RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    cp /tmp/smia_agent_patch.py "$SMIA_PKG/agents/smia_agent.py" && \
    rm /tmp/smia_agent_patch.py
# ↑ Detect where pip installed SMIA (version-independent — works even if the base
#   image upgrades Python from 3.12 to 3.13). Copy the fix there. Clean up /tmp.
#   set -e aborts the build if any command fails.

COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /smia_machine_starter.py
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py /smia_machine_agent_services.py
# ↑ Copy OUR application code to the container root (/).

WORKDIR /
# ↑ Set the working directory to /. Python adds WORKDIR to sys.path, so
#   `import smia_machine_agent_services` resolves correctly at runtime.

CMD ["python3", "-u", "smia_machine_starter.py"]
# ↑ Replace the default SMIA launcher (`python3 -m smia.launchers.smia_docker_starter`)
#   with our custom one. -u = unbuffered stdout so logs appear immediately in
#   `docker compose logs -f`.
```

#### Which files are ours vs SMIA's

| File | Origin | Classification | Role |
|---|---|---|---|
| `smia_machine_starter.py` | Written by us | **Type A — New implementation** | Creates `ExtensibleSMIAAgent`; registers `get_machine_availability` as agent service `machineAvailValue` via `add_new_agent_service()` |
| `smia_machine_agent_services.py` | Written by us | **Type A — New implementation** | `async get_machine_availability()`: HTTP GET to Node-RED `/smia/lego/availability`; returns 1.0 (free) or 0.0 (busy) as FIPA-CNP negotiation score |
| `smia_orchestrator_starter.py` | Written by us | **Type A — New implementation** | Creates `ExtensibleSMIAAgent` for orchestrator; registers `OrchestratorDispatchBehaviour` via `add_new_agent_capability()` |
| `orchestrator_dispatch_behaviour.py` | Written by us | **Type A — New implementation** | FIPA-CNP initiator: AAS-based machine discovery, colour routing, CFP broadcast, winner selection, task delegation |
| `smia_agent.py` (patched) | SMIA framework file | **Type B — Bug fix** | Asset-connection object-identity lookup bug fixed; all other framework code unchanged; TODO: upstream PR to `ekhurtado/SMIA` |

> **Note on Type A vs framework extension:** All Type A files use the official SMIA extension
> API (`add_new_agent_service`, `add_new_agent_capability`) — they are extensions of SMIA,
> not forks. The framework core is untouched except for the Type B bug fix.

#### Recommended incremental test strategy

Build all images once, then start services incrementally to isolate issues:

```bash
# Step 1 — Build all custom images (one-time; redo only if .py files or Dockerfiles change)
docker compose -f my_models/docker-compose.yml build

# Step 2 — Start infrastructure + machines only (validate single-machine flow)
docker compose -f my_models/docker-compose.yml up -d \
  xmpp-server mosquitto-central nodered \
  smia-machine0 smia-machine1 smia-machine2 smia-operator

# Verify machines reach StateRunning:
docker compose -f my_models/docker-compose.yml logs -f smia-machine0 smia-machine1 smia-machine2
# Expected: "Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']"

# Test: Operator GUI → Load → pick smia_machine0 directly → Capability_PickPiece → Submit
# If crane moves → machine layer is working

# Step 3 — Add orchestrator (validate FIPA-CNP multi-machine flow)
docker compose -f my_models/docker-compose.yml up -d smia-orchestrator
docker compose -f my_models/docker-compose.yml logs -f smia-orchestrator
# Expected: "OrchestratorDispatchBehaviour started."

# Test: Operator GUI → Load → select smia_orch → Capability_PickPiece
#        skillParams: {color: "red"} → Submit
# Orchestrator should negotiate with machines and delegate to the winner
```

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
- [ ] `Skill_PickPiece` and `Skill_PlacePiece` as **Property** (not SMC) with qualifier `SkillImplementationType=OPERATION`
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

## 17. Adding a New Machine to the Deployment

This section is the definitive guide for Vicomtech DII colleagues to add a new physical machine to the SMIA system. The architecture is designed so that adding a machine requires **no Python code changes and no new Dockerfiles** — only AAS modelling and configuration.

### Prerequisites

- AASX Package Explorer installed
- Access to the `my_models/` directory (clone the repo)
- The new machine has an MQTT-capable controller (or Node-RED can relay commands to it)
- The machine's physical interface is known: what commands it accepts, what topics it uses

### Step 1 — Create the AAS model in AASX Package Explorer

Use an existing machine AASX (e.g. `LEGO_machine1_case0.aasx`) as a template:

1. **Copy** the file and rename it: `LEGO_machineN_case0.aasx`
2. **Assign new UUIDs** to both AAS shells (Asset Management shell and SMIA_agent shell):
   - Select the AAS → edit the `id` field → generate a new UUID
   - Repeat for the SMIA_agent shell
3. **Update `SoftwareNameplate` → `InstanceName`** in the SMIA_agent shell:
   - Set to the **local part of the XMPP JID only** — e.g. `smia_machine3`
   - Do NOT include `@ejabberd` — the operator GUI appends the domain automatically
4. **Update the AID base URL** (`AssetInterfacesDescription` → `InterfaceHTTP` → `EndpointMetadata` → `base`):
   - If using the same containerized Node-RED: keep `http://nodered:1880`
   - If the machine has its own Node-RED or API: set the correct URL
5. **Update `CapabilitiesAndSkills`** to match the new machine's actual capabilities
6. **Update `SemanticRelationships`** to wire Capabilities → Skills → AID actions
7. **Save** the file to `my_models/aas/`

> **Important:** `InstanceName` must match the XMPP JID local part exactly.
> If the XMPP JID is `smia_machine3@ejabberd`, InstanceName must be `smia_machine3`.
> Using the full JID causes a doubled-`@` bug in the operator GUI (NoneType split error).

### Step 2 — Add credentials to `.env`

Add 4 lines to `my_models/.env`:

```env
MACHINE3_AAS_FILE=LEGO_machineN_case0.aasx
MACHINE3_AAS_ID=urn:uuid:<new-uuid-of-factory-shell>
MACHINE3_AGENT_ID=smia_machine3@ejabberd
MACHINE3_PASSWD=<strong-random-password>
```

### Step 3 — Register the XMPP account in ejabberd

In `my_models/docker-compose.yml`, append to the `CTL_ON_CREATE` line of `xmpp-server`:

```yaml
- CTL_ON_CREATE=! ... ; register smia_machine3 ejabberd ${MACHINE3_PASSWD}
```

> If ejabberd is already running, either restart it (`docker compose restart xmpp-server`)
> or register the account manually:
> ```bash
> docker exec ejabberd ejabberdctl register smia_machine3 ejabberd <password>
> ```

### Step 4 — Add a service block to `docker-compose.yml`

Copy any existing `smia-machineN` block and update the 4 environment variable names:

```yaml
  smia-machine3:
    build:
      context: ..
      dockerfile: my_models/docker/smia-machine/Dockerfile
    container_name: smia-machine3
    environment:
      - AAS_MODEL_NAME=${MACHINE3_AAS_FILE}
      - AAS_ID=${MACHINE3_AAS_ID}
      - AGENT_ID=${MACHINE3_AGENT_ID}
      - AGENT_PASSWD=${MACHINE3_PASSWD}
      - NODERED_URL=${NODERED_URL}
    depends_on:
      xmpp-server:
        condition: service_healthy
      nodered:
        condition: service_started
    volumes:
      - ./aas:/smia_archive/config/aas
    restart: unless-stopped
    networks:
      - smia-net
```

No new Dockerfile is needed — all machines share `docker/smia-machine/Dockerfile`.

### Step 5 — (Optional) Add a Node-RED flow for the new machine's commands

If the new machine uses the same MQTT command format as the existing crane (`bandera_custom:<position>`),
the existing flow in `nodered/flows.json` already handles it — no changes needed.

If the new machine requires a different command format or endpoint:
1. Open Node-RED at `http://localhost:1880`
2. Add new HTTP In + handler + MQTT Out nodes for the new machine's endpoints
3. Export the updated flow: Menu → Export → Download → replace `my_models/nodered/flows.json`

### Step 6 — Start the new machine

```bash
# Rebuild images if smia_machine_agent_services.py or Dockerfiles changed
docker compose -f my_models/docker-compose.yml build smia-machine3

# Start only the new machine (others keep running)
docker compose -f my_models/docker-compose.yml up -d smia-machine3
```

### Step 7 — Verify

1. Check the container starts: `docker compose logs -f smia-machine3`
   - Should reach: `Analyzed capabilities: ['Capability_...']`
2. Open Operator GUI → Load → the new machine should appear with its capabilities
3. Select the machine → Submit a capability request → verify the machine responds

### Summary checklist

```
[ ] New AASX created with unique UUIDs
[ ] InstanceName = local JID part only (no @ejabberd)
[ ] AID base URL correct (http://nodered:1880 for containerized Node-RED)
[ ] isRealizedBy (not isRealizedBySkill) used in SemanticRelationships
[ ] AASX saved to my_models/aas/
[ ] .env updated with 4 new variables
[ ] ejabberd CTL_ON_CREATE updated (or account registered manually)
[ ] docker-compose.yml service block added
[ ] docker compose up -d smia-machineN
[ ] Operator GUI Load → machine appears with correct capabilities and skills
```

---

## 18. Architecture Roadmap

### Current architecture (implemented)

```
Operator GUI
    └─► SMIA Agent (FIPA-ACL / XMPP)
            └─► Node-RED (HTTP POST)
                    └─► Mosquitto (MQTT)
                            └─► [bridge] ─► Physical machine broker
```

This architecture is fully functional and industry-deployable. Node-RED provides visual
debugging, flow modification without redeployment, and a tested HTTP→MQTT bridge.

### Planned improvement — Direct MQTT (future)

The AID standard (IDTA 02017-1-0) and WoT Thing Description both define MQTT bindings.
The SMIA framework already has `ArchitectureStyle.PUBSUB` in the `AssetConnection` base
class (`src/smia/assetconnection/asset_connection.py`, line 20) — the framework was
designed to support this.

A future `MQTTAssetConnection` class registered via `add_new_asset_connection()` would
allow SMIA to publish MQTT messages directly to the machine's broker, **eliminating
Node-RED entirely**:

```
Operator GUI
    └─► SMIA Agent (FIPA-ACL / XMPP)
            └─► Mosquitto (MQTT — direct, no HTTP layer)
                    └─► [bridge] ─► Physical machine broker
```

**What this requires:**
1. Implement `MQTTAssetConnection(AssetConnection)` with the 5 abstract methods
2. Modify `init_aas_model_behaviour.py` (lines 349-360) to detect MQTT supplementary semantic IDs
3. Update AID submodel to use MQTT bindings (WoT TD MQTT binding template)
4. Register the handler in `smia_machine_starter.py` via `add_new_asset_connection()`

This is tracked as a future development item (not in scope for the current TFG delivery).

---

## 19. Case 1 — Multi-Agent Orchestration: Technical Reference

This section documents everything added for Case 1: the four custom Python files, the docker-compose changes, the AASX Package Explorer tutorial for the new AAS models, and the Node-RED modifications. Read §16 of `memoire.md` for the academic-level explanation of *why* the architecture is designed this way.

---

### 19.1 New Python Files

Case 1 requires four Python files, all under `additional_tools/extended_agents/`. None of these files are asset-specific code inside SMIA — they are extension-layer files that use the official SMIA extension hooks (`ExtensibleSMIAAgent`).

---

#### 19.1.1 `smia_machine_starter.py`

**Full path:** `additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py`

**Location inside container (after `docker compose build`):**
```
/smia_machine_starter.py      (COPY'd by my_models/docker/smia-machine/Dockerfile)
```

**What it does.** The SMIA Docker image's default entrypoint (`python3 -m smia.launchers.smia_docker_starter`) creates a plain `SMIAAgent` with no extension hooks. Our Dockerfile replaces the `CMD` with `python3 -u smia_machine_starter.py`, which creates an `ExtensibleSMIAAgent` and calls `add_new_agent_service('machineAvailValue', get_machine_availability)` before starting the agent.

**Key design decision — `sys.path.insert`:**
```python
sys.path.insert(0, os.path.dirname(__file__))
import smia_machine_agent_services as machine_svc
```
`WORKDIR /` in the Dockerfile ensures Python's working directory is `/`, so `smia_machine_agent_services.py` (also at `/`) is importable. The explicit `sys.path.insert` is a defensive guard that works correctly regardless of how the file is invoked.

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

**Location inside container (after `docker compose build`):**
```
/smia_machine_agent_services.py      (COPY'd by my_models/docker/smia-machine/Dockerfile)
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

**Location inside container (after `docker compose build`):**
```
/smia_orchestrator_starter.py      (COPY'd by my_models/docker/smia-orchestrator/Dockerfile)
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

**Location inside container (after `docker compose build`):**
```
/orchestrator_dispatch_behaviour.py      (COPY'd by my_models/docker/smia-orchestrator/Dockerfile)
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
| Custom Dockerfiles for machine and orchestrator agents | All machines share `docker/smia-machine/Dockerfile`; orchestrator has `docker/smia-orchestrator/Dockerfile` |

**Custom Dockerfile approach — why two COPY instructions per agent type:**

```dockerfile
# my_models/docker/smia-machine/Dockerfile (relevant excerpt)
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /smia_machine_starter.py
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py /smia_machine_agent_services.py
WORKDIR /
CMD ["python3", "-u", "smia_machine_starter.py"]
```

- **COPY 1** (`smia_machine_starter.py → /`): provides the custom launcher; the Dockerfile `CMD` points directly to it — no Python path lookup needed
- **COPY 2** (`smia_machine_agent_services.py → /`): the module imported by the starter; both files land in `/` and `WORKDIR /` puts `/` on `sys.path`, so `import smia_machine_agent_services` resolves at runtime
- No Python-version-locked paths; works regardless of Python version in future base image upgrades

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
docker compose -f my_models/docker-compose.yml up -d \
  xmpp-server mosquitto-central nodered smia-machine0 smia-machine1 smia-machine2 smia-operator
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

**Step 0 — Fix the `SMIA_agent` shell InstanceName (CRITICAL):**
- Navigate to: `SMIA_agent` shell → `SoftwareNameplate` submodel → find the `InstanceName` property (inside `SoftwareNameplateInstance` or `SoftwareNameplateInstance_smia_agent` SMC)
- The current value is `smia_agent` — this is **wrong** for Case 1
- Change value to: **`SMIA_agent@ejabberd`** (full XMPP JID including `@ejabberd` domain)

> **Why the full JID is required:** The orchestrator's `_extract_jid_from_store()` reads `InstanceName` and uses that string directly as the XMPP address to send CFP messages to. If InstanceName is just `smia_agent` (no domain), SMIA will try to send to a non-existent XMPP address and machine0 will never participate in any negotiation. The value must be a complete JID: `user@domain`.

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
  - `type`: `SkillImplementationType`
  - `value`: `OPERATION`
  - `valueType`: `xs:string`
  - `semanticId` (ExternalReference, GlobalReference): `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`

> **Why the semanticId is required here (unlike in Case 0 Step 8.7):**
>
> SMIA uses two mechanisms to read `SkillImplementationType`. For multi-agent negotiation (Case 1), the boot-time OWL loading path (Mechanism 2) is critical: `InitAASModelBehaviour.add_ontology_required_information()` reads the CSS-SMIA OWL ontology, finds that `Skill` has the data property `hasImplementationType` at IRI `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`, then calls `get_qualifier_value_by_semantic_id(iri)` to find the value in the AAS. If no qualifier has that semanticId, an `AASModelReadingError` is raised, the skill OWL instance is not populated, and `HandleNegotiationBehaviour` crashes at `get_associated_skill_interface_instances()` returning `None`.
>
> This applies to **all skills** in all machine AASXs used in Case 1: `Skill_PickPiece`, `Skill_PlacePiece`, and `Skill_NegAvailability`. All must have the semanticId set.
>
> The IRI is not invented — it is defined in `additional_resources/css_smia_ontology/CSS-ontology-smia.owl:429` as an `owl:DatatypeProperty` by the SMIA team. The official preset file (`SMIA-css-qualifier-presets.json`) has `semanticId: null` because it was designed for the single-machine case. No ConceptDescription needs to be created in the AASX package — the semanticId is an external (GlobalReference) IRI pointing to the OWL ontology.

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
- `idShort`: `rel_SkillNegAvail_agentSvc`
- **SemanticId**: `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService`
- **First reference** (the skill): navigate to `CapabilitiesAndSkills / Skill_NegAvailability`
- **Second reference** (the interface): navigate to `CapabilitiesAndSkills / machineAvailValue`

> **Which `accessibleThrough*` IRI to use?** SMIA defines three IRIs (all listed in `CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS`, all chained in `get_associated_skill_interface_instances()`):
> - `http://www.w3id.org/hsu-aut/css#accessibleThrough` — base CSS standard (CaSkade); works for all cases
> - `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` — SMIA extension; semantically signals physical HTTP execution
> - `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` — SMIA extension; semantically signals agent-internal Python execution
>
> All three work at runtime: routing is determined by whether the SkillInterface element's parent submodel is the AID submodel (`handle_negotiation_behaviour.py:309-310`), NOT by which IRI was used. Use the most specific applicable sub-property: since `machineAvailValue` is an agent service (Python method, not HTTP), **`#accessibleThroughAgentService`** is the semantically precise choice (OWL best practice: use the most specific applicable sub-property).
>
> **Note on capitalization:** The AASX PE preset file (`SMIA-css-semantic-ids-sm.add-options.json`) defines the SMIA-specific sub-properties with capital 'A': `#AccessibleThroughAgentService` and `#AccessibleThroughAssetService`. Always verify the exact IRI against the `css_ontology_utils.py` constants in the Docker image version you are using — the preset file and the runtime constants must agree.

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
   - Change `id`: `urn:uuid:6373_1111_2062_0001` (new UUID — this IS significant, must be globally unique; use the `6373` prefix to follow the SMIA agent shell convention)
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

5. **Verify the `rel_SkillNegAvail_agentSvc` IRI** (inherited from machine0 clone):
   - Navigate to: `LEGO_machine1` shell → `SemanticRelationships` → `rel_SkillNegAvail_agentSvc`
   - Confirm the semanticId value is exactly: `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService`
   - If it says `#AccessibleThroughAgentService` (capital 'A') — fix it to the lowercase form above

6. **Save the file.** File → Save.

---

#### 19.3.C Create `LEGO_machine2_case0.aasx` (white pieces)

Repeat the same steps as 19.3.B. The two-shell rationale and idShort explanation from §19.3.B apply equally here. With these values:

| Field | Value |
|---|---|
| Output filename | `LEGO_machine2_case0.aasx` |
| Factory shell idShort | `LEGO_machine2` |
| Factory shell id | `urn:uuid:6475_0111_2062_0002` |
| Agent shell id | **`urn:uuid:6373_1111_2062_0002`** ← must be unique, different from machine0 (`6896`) and machine1 (`0001`) |
| InstanceName | `smia_machine2@ejabberd` |
| Capability_PickPiece/color | `white` |
| Capability_PlacePiece/color | `white` |

> **CRITICAL — Duplicate UUID:** Each AAS shell must have a globally unique `id` (AAS Part 1, §5.3.1). The SMIA agent shell in machine0 uses `urn:uuid:6373_1111_2062_6896` and machine1 uses `urn:uuid:6373_1111_2062_0001`. Machine2's agent shell MUST use `urn:uuid:6373_1111_2062_0002` (or any other UUID not used by the others). If you clone machine1's file without changing this UUID, both machine1 and machine2 will have the same identifier — BaSyx SDK may silently discard one entry from the object store, making machine2's `SoftwareNameplate` (and thus its XMPP JID) invisible to the orchestrator's AAS scanner.

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
  - Child **Property** `color` (xs:string, no value) — declares that the operator must specify a piece color
- Add **SubmodelElementCollection** `Capability_PlacePiece` (same pattern — also uses `color` xs:string)

> **Why `color` and NOT `position` here:** The orchestrator's external interface accepts `color` from the operator (e.g., `"red"`, `"blue"`, `"white"`). The crane position is an internal implementation detail — the orchestrator translates `color → position` in code via `COLOR_POSITION_MAP` before dispatching to the winning machine. The AAS must reflect what the *external caller* (operator) sends, not what the *internal implementation* uses. Declaring `position` in the orchestrator's AAS would be semantically wrong — the orchestrator never exposes position to the operator.
- Add **Property** `Skill_Orchestrate_PickPiece`:
  - `valueType`: `xs:string`
  - **SemanticId**: `http://www.w3id.org/hsu-aut/css#Skill`
  - **Qualifier**: `SkillImplementationType = OPERATION` (no semanticId)
- Add **Property** `Skill_Orchestrate_PlacePiece` (same pattern)
- Link this submodel to the orchestrator AAS shell

**Why `AgentCapability` (not `AssetCapability`)?** The orchestrator does not directly control a physical machine. Its capability is an *agent-level* function — coordination and delegation. `AgentCapability` is the correct CSS class for functions performed by the digital twin agent itself rather than by a physical asset.

**Step 4 — Create `SemanticRelationships` submodel:**
- Add Submodel with `idShort`: `SemanticRelationships`
- Add **RelationshipElement** `rel_CapPick_isRealizedBy_SkillOrchPick`:
  - **SemanticId**: `http://www.w3id.org/hsu-aut/css#isRealizedBy` ← use exactly this IRI
  - First: `CapabilitiesAndSkills / Capability_PickPiece`
  - Second: `CapabilitiesAndSkills / Skill_Orchestrate_PickPiece`
- Add **RelationshipElement** `rel_CapPlace_isRealizedBy_SkillOrchPlace` (same pattern for place)
- **Do NOT add** `accessibleThroughAssetService` or `accessibleThroughAgentService` relationships — the orchestrator's capabilities are handled entirely by `OrchestratorDispatchBehaviour`, not by a registered skill interface

> **`isRealizedBy` NOT `isRealizedBySkill`:** The correct CSS ObjectProperty IRI is `http://www.w3id.org/hsu-aut/css#isRealizedBy` (verified from `css_ontology_utils.py:CSS_ONTOLOGY_PROP_ISREALIZEDBY_IRI` and the OWL file). `#isRealizedBySkill` is a valid OWL sub-property of `#isRealizedBy` defined in the CSS ontology, but SMIA uses **exact string matching** — it is not in `CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS` and is therefore ignored. Using it causes Track 3 to skip those relationships and the operator GUI to show 0 capabilities/skills. The orchestrator still functions at runtime (its dispatch is in `OrchestratorDispatchBehaviour` which bypasses the CSS graph), but the AAS is semantically incorrect.
- Link this submodel to the orchestrator AAS shell

**Step 5 — Embed required files:**
- In AASX Package Explorer: Extras → AASX File Repository → Add supplemental files
- Add `aasx/CSS-ontology-smia.owl` (copy from `LEGO_factory_case0.aasx`)
- Add `aasx/smia-initialization.properties` (copy from `LEGO_factory_case0.aasx`)
- The properties file can be the same content — runtime values come from Docker env vars

**Step 6 — Save:** File → Save → `SMIA_orchestrator.aasx` in `my_models/aas/`

> The filename `SMIA_orchestrator.aasx` must match exactly what `docker-compose.yml` declares as `AAS_MODEL_NAME=SMIA_orchestrator.aasx` for the `smia-orchestrator` service.

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
| Operator GUI shows 0 capabilities and 0 skills after Load | All AASXs use `#isRealizedBySkill` instead of `#isRealizedBy` for isRealizedBy relationships | In AASX PE, open each AASX → `SemanticRelationships` submodel → change semanticId of every `rel_Cap*_isRealizedBy*_Skill*` element from `#isRealizedBySkill` to `http://www.w3id.org/hsu-aut/css#isRealizedBy`. (`#isRealizedBySkill` is a valid CSS OWL sub-property but is not in `CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS` — SMIA skips it silently.) |
| Orchestrator logs show `no machines found` | AASX not in `aas/` folder, or color not in capability | Verify `.aasx` files exist in `my_models/aas/`; check `Capability_PickPiece/color` value |
| Machine never reaches StateRunning | `Skill_NegAvailability` or `machineAvailValue` incorrectly defined | Check semanticId matches exactly; Skills must be Property not SMC |
| `HandleNegotiationBehaviour` crashes: `'NoneType' object is not iterable` | `SkillImplementationType` qualifier on any skill has no semanticId | In AASX PE, open each machine AASX → find every skill Property → edit the `SkillImplementationType` qualifier → set semanticId to `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`. Affects all skills: `Skill_PickPiece`, `Skill_PlacePiece`, `Skill_NegAvailability`. See §8.7 / §19.3.A Step 3 for explanation. |
| Machine always reports score 0.0 in negotiation | `rel_SkillNegAvail_agentSvc` uses a wrong or non-existent IRI | Set semanticId to `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` (lowercase 'a') |
| Machine0 never participates in CFP | InstanceName in `LEGO_factory_case0.aasx` is not a full JID | Change SMIA_agent shell InstanceName to `SMIA_agent@ejabberd` |
| `INFORM(winner)` never arrives at orchestrator | `negRequester` field missing or wrong | Check `negRequester` is set to orchestrator JID in CFP body |
| Orchestrator container never starts | `AAS_MODEL_NAME` doesn't match filename | Verify docker-compose uses `SMIA_orchestrator.aasx` (exact name) |
| Operator GUI crashes on Load (500 error) | Non-AASX file in `aas/` folder | Remove any backup, XML, or JSON files from `my_models/aas/` |
| Machine2 JID not discovered | Duplicate SMIA agent shell UUID in machine2 AASX | Set machine2 SMIA_agent shell id = `urn:uuid:6373_1111_2062_0002` (unique) |
| `aiohttp` import error in machine logs | `aiohttp` not installed in image | aiohttp is a smia dependency — verify image version |

---

### 19.7 IRI Reference — Common Mistakes

This table shows the exact correct IRIs for all CSS elements used in Case 1, alongside the most common
mistakes discovered during AAS authoring. **SMIA uses string equality for IRI comparison** — a single
wrong character causes silent failure.

| CSS Concept | Correct IRI | Common Wrong Value | Notes |
|---|---|---|---|
| `isRealizedBy` | `http://www.w3id.org/hsu-aut/css#isRealizedBy` | `#isRealizedBySkill` | `#isRealizedBySkill` IS a valid OWL sub-property of `#isRealizedBy` in the CSS ontology (domain=Capability, range=Skill), but SMIA uses exact string matching. Only `#isRealizedBy` is in `CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS`. Using `#isRealizedBySkill` → operator GUI shows 0 capabilities/skills. |
| `accessibleThroughAgentService` (for `rel_SkillNegAvail_agentSvc`) | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` | `#AccessibleThroughAgentService` (capital 'A') | SMIA extension sub-property for agent-internal Python execution. The base CSS property `#accessibleThrough` also works at runtime but is less semantically precise. All three variants are processed by SMIA; routing is determined by SkillInterface submodel membership, not the IRI. |
| Capability qualifier type | `hasLifecycle` (string in type field) | `ExpressionSemantic` | Capability not validated by SMIA |
| Skill qualifier type | `SkillImplementationType` with semanticId `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` (Case 1 machines) | `SkillImplementationType` with no semanticId (sufficient only for Case 0 single-machine) | SMIA uses two mechanisms: (1) type-based lookup — works without semanticId, used for direct execution; (2) OWL data property lookup by semanticId — required for multi-agent negotiation boot path. Preset file has `semanticId: null` — incomplete for Case 1. |
| `AssetCapability` | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` | `#AgentCapability` for machines | Wrong OWL class → wrong runtime behaviour type |
| `AgentCapability` | `http://www.w3id.org/upv-ehu/gcis/css-smia#AgentCapability` | `#AssetCapability` for orchestrator | Orchestrator tries to use AID asset service path |

**Source for all IRIs:** `src/smia/css_ontology/css_ontology_utils.py` (constants) and `my_models/ontology/CSS-ontology-smia.owl` (OWL definitions).

---

### 19.8 E2E Readiness Checklist

This section tracks the exact state of each pending fix and the conditions required before testing end-to-end at each stage.

#### Stage A — E2E without orchestrator (Case 0 single machine)

**Goal:** Operator GUI → SMIA_agent@ejabberd → HTTP → Node-RED → crane.

**Blocking fix (AASX PE required):**

| File | Fix | Why it blocks |
|---|---|---|
| `LEGO_factory_case0.aasx` | `SMIA_agent` shell → `SoftwareNameplate` → `InstanceName` value: `SMIA_agent@ejabberd` | Operator GUI reads `InstanceName` via semantic ID (`operator_gui_logic.py:447`) and uses the raw value as the XMPP JID for message routing. A value without `@ejabberd` is not a valid XMPP JID — SPADE rejects it silently. |

**Non-blocking issues for this stage:**
- `rel_SkillNegAvail_agentSvc` IRI bug (`#AccessibleThroughAgentService`) causes a Track 3 warning during SMIA boot but does NOT prevent `StateRunning`. The pick/place flow does not involve negotiation and is unaffected.
- Other machine/orchestrator AASX issues do not affect machine0's operation.

**Node-RED:** `POST /smia/lego/pick` must be working (already exists).

**How to test:** Run `docker compose up -d`, open `http://localhost:10000/smia_operator`, click Load, select `SMIA_agent@ejabberd`, select `Capability_PickPiece`, submit. All other services (orchestrator, machine1, machine2) start alongside but are not involved.

---

#### Stage B — E2E with orchestrator (Case 1 multi-machine)

**Goal:** Operator GUI → smia_orch@ejabberd → FIPA-CNP → winning machine → HTTP → Node-RED → crane.

**All AASX PE fixes must be done before testing this stage:**

| File | Fix | Why it blocks |
|---|---|---|
| `LEGO_factory_case0.aasx` | InstanceName → `SMIA_agent@ejabberd` | (same as Stage A) |
| `LEGO_factory_case0.aasx` | `rel_SkillNegAvail_agentSvc` semanticId → `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` | SMIA's Track 3 uses exact IRI string matching. Capital 'A' → IRI not found → `Skill_NegAvailability` OWL instance has no linked `SkillInterface` → `get_associated_skill_interface_instances()` returns `None` → negotiation score defaults to 0.0 for all machines → winner selection is arbitrary or fails |
| `LEGO_machine1_case0.aasx` | Same `rel_SkillNegAvail_agentSvc` IRI fix | Same impact |
| `LEGO_machine2_case0.aasx` | Same `rel_SkillNegAvail_agentSvc` IRI fix | Same impact |
| `LEGO_machine2_case0.aasx` | `SMIA_agent` shell `id` → `urn:uuid:6373_1111_2062_0002` | Duplicate UUID with machine0's SMIA shell — AAS Part 1 §5.3.1 requires globally unique shell IDs; BaSyx SDK may raise a conflict error during model loading |
| `SMIA_orchestrator.aasx` | `SMIA_agent` shell → `InstanceName`: remove trailing space → `smia_orch@ejabberd` | Trailing space makes the JID invalid; SPADE rejects it; operator GUI cannot route requests to the orchestrator |
| `SMIA_orchestrator.aasx` | `rel_CapPick_isRealizedBy_*` and `rel_CapPlace_isRealizedBy_*`: semanticId `isRealizedBySkill` → `http://www.w3id.org/hsu-aut/css#isRealizedBy` | `isRealizedBySkill` is not a valid CSS IRI — Track 3 cannot link the relationship. The orchestrator functions correctly without it (its dispatch logic is in `OrchestratorDispatchBehaviour`, not the CSS model), but the AASX is semantically incorrect and will fail AAS validation |
| `SMIA_orchestrator.aasx` | `Capability_PickPiece` and `Capability_PlacePiece` child property: rename `position` (xs:int) → `color` (xs:string) | `OrchestratorDispatchBehaviour._find_capability_color()` scans all AASXs for a property named `color` inside the matching capability SMC. The orchestrator's own AASX is also in the `aas/` folder — if it has a `position` property instead of `color`, the color filter won't match and the orchestrator's own AASX won't contaminate results. However, this is a semantic correctness issue: the orchestrator's AAS must reflect that it accepts `color` (not `position`) as the input parameter from the operator |

**Node-RED fix required (on DIDA central 192.168.155.10:1880):**

Add a global `machine_busy` flag and a `GET /smia/lego/availability` endpoint:
- Set `machine_busy = true` at the start of the pick HTTP handler, `false` after MQTT publish
- `GET /smia/lego/availability` → returns `"1.0"` if `!machine_busy`, else `"0.0"`, as plain text (not JSON)

Without this, `smia_machine_agent_services.get_machine_availability()` catches a `ClientConnectorError` and returns `0.0` — every machine always scores 0.0, making winner selection non-deterministic.

**Python code status: complete and verified.** `orchestrator_dispatch_behaviour.py`, `smia_machine_starter.py`, `smia_machine_agent_services.py`, and both starters require no further changes.

**Source verification:**
- Operator sends `ontology: 'css-service'` (`operator_gui_behaviours.py:264`)
- Orchestrator filters on `ACL_ONTOLOGY_CSS_SERVICE = 'css-service'` (`fipa_acl_info.py:68`) ✓
- Routing (asset vs agent service) decided by `handle_negotiation_behaviour.py:309-310` (submodel membership, not IRI) ✓

**Source for all IRIs:** `src/smia/css_ontology/css_ontology_utils.py` (constants) and `my_models/ontology/CSS-ontology-smia.owl` (OWL definitions).

---

*Case 1 implementation completed 2026-03-16. All Python files are in `additional_tools/extended_agents/`. AAS models must be created manually in AASX Package Explorer following §19.3 above. Bugs B1–B8 discovered and corrected 2026-03-25 after full AAS inspection.*
