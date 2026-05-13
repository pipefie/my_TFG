# Flexible Manufacturing Based on Digital Twins Using AAS and CSS Model

**Bachelor's Thesis (Trabajo de Fin de Grado)**
**Degree:** Bachelor's in Data Science and Artificial Intelligence (Bilingual)
**University:** Universidad de Deusto — Faculty of Engineering
**Author:** Andrés Felipe Fierro Fonseca
**Institution:** Vicomtech — Data Intelligence for Industry (DII)
**Supervisors:** Ander García Gangoiti / Xabier Oregui Biain
**Academic year:** 2025–2026

---

> **Working draft — in progress.** This document is being written in parallel with the implementation work. Sections describing completed work (Cases 0 and 1, bug fixes, validation) reflect the current state of the project. Sections covering future work (extended negotiation testing, repository migration, additional machine scenarios) will be updated as that work is completed. The Vicomtech internship agreement runs until June 2026; submission to Universidad de Deusto is planned for end of May 2026.
>
> For deeper technical reference (AASX modelling tutorials, exact IRI tables, per-instruction Dockerfile walkthroughs, troubleshooting guides), see the companion technical documents `doc_case0.md` and `doc_case1.md`.

---

## Abstract

This work investigates and implements a flexible manufacturing scenario grounded in two complementary industrial standards: the Asset Administration Shell (AAS) — the reference framework for Industrial Digital Twins within Industry 4.0 — and the Capability-Skill-Service (CSS) ontological model, which describes what a manufacturing asset can do and how it does it. The implementation vehicle is SMIA (Self-configurable Manufacturing Industrial Agents), an open-source research framework developed at the University of the Basque Country (UPV/EHU) that combines AAS and CSS to generate autonomous software agents directly from standardized machine descriptions.

Two use cases are implemented. Case 0 validates the fundamental self-configuration concept: a single SMIA agent representing a fischertechnik Training Factory Industry 4.0 24V warehouse crane reads its AAS model at startup, derives the complete execution path autonomously — from a human operator's capability request to a physical MQTT command that moves the crane — without any asset-specific code in the agent. Case 1 extends this to a multi-agent scenario with six machine agents (three colours, with duplicates and a multicolour agent) and an orchestrator: when an operator requests a pick task specifying a colour constraint, the orchestrator discovers eligible machines from the AAS folder, runs a FIPA Contract Net Protocol (FIPA-CNP) negotiation round to select the most available machine, delegates execution to the winner, and returns the result to the operator.

The primary software contribution of this TFG is the `OrchestratorDispatchBehaviour` — the FIPA-CNP initiator side of the negotiation, which does not exist in the base SMIA framework. Five bugs were identified in the SMIA framework and patched at Docker image build time, with upstream PRs planned. The system is deployed as eleven Docker containers, fully reproducible from a single `docker compose up` command. The final MVP adds a Node-RED virtual factory dashboard that replaces the physical crane, making the system self-contained and demonstrable without external hardware.

---

## Keywords

Asset Administration Shell (AAS) · Capability-Skill-Service (CSS) · Self-configurable Manufacturing Industrial Agents (SMIA) · FIPA Contract Net Protocol (FIPA-CNP) · Industrial Digital Twin · Flexible Manufacturing · Multi-Agent Systems

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 Context and Motivation
   - 1.2 Scope
   - 1.3 Document Structure
2. [Background and Justification](#2-background-and-justification)
   - 2.1 The Flexibility Gap in Modern Manufacturing
   - 2.2 State of the Art
   - 2.3 Justification
3. [Objectives and Scope](#3-objectives-and-scope)
   - 3.1 General Objective
   - 3.2 Specific Objectives
   - 3.3 Research Questions
   - 3.4 Scope and Limitations
4. [Project Planning](#4-project-planning)
   - 4.1 Work Breakdown Structure
   - 4.2 Schedule
   - 4.3 Human Resources Plan
   - 4.4 Milestones
5. [Budget](#5-budget)
6. [Methodology](#6-methodology)
7. [Development](#7-development)
   - 7.1 Requirements and Design
   - 7.2 Implementation
   - 7.3 Verification
   - 7.4 Packaging
   - 7.5 Launch
   - 7.6 Configuration
   - 7.7 Monitoring
8. [Ethical Assessment](#8-ethical-assessment)
9. [Incidents and Issues Resolved](#9-incidents-and-issues-resolved)
10. [Conclusions and Future Work](#10-conclusions-and-future-work)
11. [References](#11-references)
12. [Definitions, Acronyms, and Abbreviations](#12-definitions-acronyms-and-abbreviations)
- [Appendices](#appendices)

---

## 1. Introduction

### 1.1 Context and Motivation

Manufacturing is undergoing a profound transformation driven by Industry 4.0: the convergence of physical production systems with cloud computing, artificial intelligence, the Internet of Things, and advanced data analytics. Despite substantial progress in automation, modern production lines remain fundamentally rigid — designed for repeatability, not adaptability. A robotic arm optimized for one product requires significant engineering effort to adapt to a new one. This incompatibility with market trends toward short product life cycles, mass customization, and on-demand production constitutes what is referred to in the literature as the **flexibility gap** [1].

Two standards address this challenge at complementary levels:

**The Asset Administration Shell (AAS)** [1] is the IDTA reference standard for Industrial Digital Twins. It provides a universal, machine-readable structure for representing any manufacturing asset's identity, properties, capabilities, and interfaces. Rather than proprietary integration adapters, assets described by AAS can be discovered and used by software systems without prior knowledge of their specific implementation.

**The Capability-Skill-Service (CSS) ontological model** [2] separates the *what* (capabilities — the abstract function an asset can perform) from the *how* (skills — the concrete technology-specific implementation). This semantic layer enables software systems to match tasks to assets based on what they can do, without hard-coded knowledge of how they do it.

**SMIA** (Self-configurable Manufacturing Industrial Agents) [3] is an open-source framework developed at UPV/EHU that operationalizes this combination: it reads an AAS+CSS-enriched model at startup and autonomously generates a functional Digital Twin agent that can receive capability requests via standardized FIPA-ACL messages and execute them against the physical asset. This TFG uses and extends SMIA as the implementation platform.

The work is conducted at **Vicomtech's Data Intelligence for Industry (DII)** department, which investigates industrial AI and digital twin technologies. The physical asset used throughout the project is a **fischertechnik Training Factory Industry 4.0 24V** (ref. 554868) [4] — specifically its warehouse crane (Hochregallager), a compact, real actuator with pick-and-place functionality.

### 1.2 Scope

This TFG focuses on:

1. Understanding and applying the AAS standard at a detailed technical level, including the AASX package format, the Asset Interfaces Description (AID) submodel, and CSS semantic enrichment.
2. Modeling the fischertechnik warehouse crane as a complete AAS digital twin.
3. Deploying SMIA to interpret that model autonomously (Case 0: single agent).
4. Extending SMIA with a custom FIPA-CNP orchestrator to coordinate multiple machine agents (Case 1: multi-agent).
5. Validating both cases end-to-end with a real physical crane.
6. Documenting all design decisions so the work can be reproduced by other researchers and extended by colleagues.

**Out of scope:** Cases 2 (capability constraint matching) and 3 (human interface agents) are identified as future work but not implemented. OPC UA asset connections, AAS server integration, and production-grade security are not in scope.

### 1.3 Document Structure

Section 2 provides the theoretical background and justifies the technical approach. Section 3 states the objectives and research questions. Section 4 presents the project plan and Section 5 the budget. Section 6 describes the methodology. Section 7 is the main development section, covering design, implementation, verification, packaging, deployment, configuration, and monitoring. Sections 8 and 9 address ethical considerations and technical incidents. Section 10 presents conclusions and future work. Sections 11–12 and the appendices complete the document.

---

## 2. Background and Justification

### 2.1 The Flexibility Gap in Modern Manufacturing

Modern manufacturing automation is designed for repeatability: a production line optimized for one product family requires substantial re-engineering to adapt to changes in product design, volume, or variant mix. This rigidity is increasingly incompatible with market demands for personalization, short life cycles, and supply chain resilience.

The solution proposed by Industry 4.0 is **flexible manufacturing** — systems that can adapt dynamically to new production requirements without manual reconfiguration of hardware or re-programming of control logic. Achieving this requires three conditions:

1. **Standardized asset descriptions** — so that machines can describe their capabilities in a machine-readable, technology-neutral format that any software system can interpret.
2. **Standardized communication** — so that machines, software agents, and operators can exchange requests and results using a shared language without proprietary integrations.
3. **Autonomous decision-making** — so that the system can match tasks to available machines at runtime, without a human engineer specifying the assignment in advance.

This TFG addresses all three conditions using AAS (standardized description), FIPA-ACL (standardized communication), and SMIA agents (autonomous decision-making).

### 2.2 State of the Art

#### 2.2.1 Asset Administration Shell (AAS)

The **Asset Administration Shell** [1] is the IDTA standard for Industrial Digital Twins, operationalizing the Industry 4.0 "Verwaltungsschale" concept. An AAS consists of one or more *Submodels*, each containing *SubmodelElements* — structured data describing a specific aspect of the asset. Three AAS types exist:

- **Type 1**: Passive — a file exchanged between partners.
- **Type 2**: Reactive — provides a REST API for external queries.
- **Type 3**: Proactive — a live agent that initiates peer-to-peer communication, negotiates, and acts autonomously.

This TFG implements **Type 3** AAS through SMIA agents.

The AAS package format (AASX) is a ZIP file containing XML/JSON model descriptions and supporting files (ontologies, properties files). Models are created with the open-source **AASX Package Explorer** tool. A key submodel standard used in this project is the **Asset Interfaces Description (AID)** [5], which describes how a physical asset's interfaces can be accessed using Web of Things (WoT) Thing Description semantics — enabling SMIA to find and call the correct HTTP endpoint from the model description alone.

#### 2.2.2 Capability-Skill-Service (CSS) Ontological Model

The **CSS model** [2] introduces three abstraction levels:

- **Capability**: an abstract description of a manufacturing function (e.g., "pick a piece"). Defined independently of any specific machine. Described using OWL ontology classes.
- **Skill**: a concrete, technology-specific implementation of a capability on a particular machine (e.g., "execute an HTTP POST to Node-RED to trigger the warehouse crane macro"). A capability can be realized by multiple skills.
- **Service (SkillInterface)**: the access mechanism for invoking a skill — describing its input parameters and protocol binding.

The CSS ontology used in this project is the **CaSkade-Automation CSS-ontology v1.0.1**, extended by the SMIA team with two additional classes: `AssetCapability` (for physical-asset functions) and `AgentCapability` (for software-agent functions). The ontology is embedded inside each AASX package as an OWL file, enabling each SMIA agent to reason semantically about its own capabilities at runtime.

CSS elements are linked to AAS elements via the `semanticId` field — a URI that identifies the OWL class an AAS element belongs to. SMIA reads these URIs during self-configuration (the "semantic enrichment" step) to build the execution graph: Capability → Skill → SkillInterface → AssetConnection.

#### 2.2.3 Multi-Agent Systems and FIPA-ACL

A **multi-agent system (MAS)** is a collection of autonomous software agents that communicate and cooperate to achieve individual or collective goals. For manufacturing, each machine is represented by one agent; an orchestrator agent coordinates task allocation.

**SPADE** (Smart Python Agent Development Environment) [6] is the Python MAS framework underlying SMIA. It uses **XMPP** as the transport layer — an open, standardized messaging protocol — and provides abstractions for agent behaviours, message routing, and finite state machines.

Agents communicate using **FIPA-ACL** (Foundation for Intelligent Physical Agents — Agent Communication Language) [7], a standardized format for expressing the intent behind a message (request, inform, propose, etc.) and linking it to a semantic ontology.

Task allocation in Case 1 uses the **FIPA Contract Net Protocol (FIPA-CNP)** [7]: an initiator broadcasts a Call For Proposals (CFP) to contractors; contractors compute their bid (availability score); in SMIA's peer-to-peer adaptation, machines compare bids directly with each other and the winner reports to the initiator.

#### 2.2.4 SMIA: Self-configurable Manufacturing Industrial Agents

SMIA [3] is the framework that integrates AAS, CSS, SPADE, and FIPA-ACL. Its self-configuration process runs three parallel tracks during agent startup (paper §4.2):

- **Track 1**: Reads the AID submodel and creates an `AssetConnection` object for each interface (the HTTP caller).
- **Track 2**: For each CSS class IRI (Capability, Skill, SkillInterface...), finds matching AAS elements by `semanticId`, validates them against the OWL ontology, and creates OWL individual instances.
- **Track 3**: Links the OWL instances together using CSS object property IRIs (`isRealizedBy`, `accessibleThroughAssetService`), building the execution graph.

The result is a fully autonomous agent that can receive capability requests and execute them against the physical asset — with zero hard-coded asset knowledge.

SMIA is extensible via three official hooks (`ExtensibleSMIAAgent`): `add_new_agent_service()`, `add_new_agent_capability()`, and `add_new_asset_connection()`. This TFG uses the first two to add the availability agent service and the FIPA-CNP initiator behaviour.

#### 2.2.5 Comparison with Alternative Frameworks

The SMIA paper [3] compares SMIA against three alternative frameworks for deploying manufacturing agents as digital twins:

| Criterion | **SMIA** | MAS4AI | NOVAAS | FA3ST |
|---|---|---|---|---|
| **AAS compliance** | ✓ | ✗ | ✓ | ✓ |
| **CSS semantic model** | ✓ | ✗ | ✗ | ✗ |
| **FIPA-ACL communication** | ✓ | ✓ | ✗ | ✗ |
| **Self-configuration from AAS** | ✓ | ✗ | ✗ | ✗ |
| **P2P multi-agent negotiation** | ✓ | ✓ | ✗ | ✗ |
| **Physical asset integration (AID)** | ✓ | ✗ | ✓ | ✓ |
| **Extensible architecture** | ✓ | ✗ | ✓ | ✓ |
| **Open source** | ✓ | ✗ | ✓ | ✓ |

SMIA is the only framework combining all four key properties: AAS compliance, CSS capability semantics, FIPA-ACL multi-agent communication, and automated self-configuration from the AAS model. This makes it uniquely suited for validating the AAS Type 3 paradigm in a real flexible manufacturing context.

### 2.3 Justification

The combination of AAS and CSS has been proposed theoretically for several years, but few implementations demonstrate the complete pipeline from a standardized AAS model to physical actuation in a real industrial asset, and none with multi-agent FIPA-CNP orchestration. This TFG fills that gap by:

1. Providing a fully reproducible end-to-end implementation of AAS Type 3 + CSS for a real physical asset (fischertechnik warehouse crane).
2. Contributing a FIPA-CNP initiator behaviour (`OrchestratorDispatchBehaviour`) that is missing from the base SMIA framework — the existing framework only implements the responder/proposer side.
3. Identifying and fixing three bugs in the SMIA framework (with upstream PRs planned), contributing directly to the open-source community.
4. Demonstrating that the AAS + CSS approach scales from a single agent (Case 0) to a multi-agent negotiation scenario (Case 1) without changing any agent code — only the AAS models differ.

**Economic and technical justification:** The containerized approach (all eight services in a single `docker compose up`) reduces deployment effort from days to minutes and makes the system fully portable across lab environments. All software used (SMIA, Docker, Python, Node-RED, ejabberd, Mosquitto) is open source — zero licensing cost. The only hardware cost is the fischertechnik factory already present at Vicomtech.

---

## 3. Objectives and Scope

### 3.1 General Objective

Design and implement a prototype flexible manufacturing scenario in which a physical manufacturing asset — represented by a standardized AAS digital twin enriched with CSS semantics — is autonomously managed by a SMIA agent (Case 0) and by a multi-agent orchestration system using FIPA-CNP negotiation (Case 1), enabling a human operator to discover available capabilities and trigger their execution through a standardized digital interface.

### 3.2 Specific Objectives

1. **Understand and apply the AAS standard** at a detailed technical level, including the AASX package format, submodel structure, CSS semantic enrichment via `semanticId`, and the AID submodel specification (IDTA 02017).

2. **Model the fischertechnik warehouse crane** as a complete AAS digital twin (Case 0), including identity submodels, CSS capability and skill definitions, HTTP interface description via AID, and OWL semantic relationships.

3. **Extend the AAS model for multi-agent deployment** (Case 1): create AASX models for three colour-constrained machine agents and one orchestrator agent with FIPA-CNP coordination capability.

4. **Deploy and configure SMIA** using Docker Compose, with correct XMPP credentials, AAS model loading, OWL ontology parsing, and Node-RED HTTP→MQTT communication.

5. **Extend the SMIA framework** using the official `ExtensibleSMIAAgent` API:
   - Implement `get_machine_availability()` as an agent service for real-time availability reporting via Node-RED.
   - Implement `OrchestratorDispatchBehaviour` as the FIPA-CNP initiator — the missing piece of the multi-agent negotiation.

6. **Identify and patch upstream bugs** in the SMIA framework — five bugs patched: `smia_agent.py` (asset-connection lookup), `acl_handling_behaviour.py` (orchestrator race condition), `operator_gui_logic.py` (`hasParameter` processing), `negotiating_behaviour.py` (concurrent negotiation cross-contamination), `handle_negotiation_behaviour.py` (deadlock with 3+ machines) — and document them for upstream contribution.

7. **Validate the complete end-to-end pipeline** for both cases: operator capability request → XMPP → SMIA skill resolution → HTTP POST → MQTT → physical crane actuation.

8. **Document all design decisions and implementation details** at publication quality so the work can be reproduced by other researchers and extended by colleagues at Vicomtech.

### 3.3 Research Questions

- **RQ1:** Can a manufacturing asset's capabilities be fully described using the AAS + CSS standard combination such that a SMIA agent derives the correct execution path — from capability to physical HTTP call — without any asset-specific hard-coded logic?
- **RQ2:** Can the same AAS + CSS + SMIA approach scale from a single agent to a multi-agent FIPA-CNP negotiation scenario, with machine selection based on runtime availability, without modifying any agent code?
- **RQ3:** Is the overhead introduced by the standardization layer (AAS parsing, CSS semantic reasoning, XMPP messaging) acceptable for a real-time manufacturing actuation scenario?

### 3.4 Scope and Limitations

**In scope:**
- Case 0: Single machine agent (SMIA_agent) → fischertechnik warehouse crane (pick/place operations, slots 0–8).
- Case 1: Three machine agents + one orchestrator agent, FIPA-CNP negotiation, colour-based routing.
- Containerized deployment (Docker Compose, 8 services).
- End-to-end validation with the physical fischertechnik factory at Vicomtech.

**Out of scope:**
- Case 2 (CapabilityConstraint matching) and Case 3 (SMIA-HI human interface): identified as future work.
- OPC UA or direct MQTT asset connections (only HTTP via AID is implemented).
- Production-grade security (TLS, authentication for HTTP endpoints).
- AAS server integration (BaSyx server, REST API exposure).
- The fischertechnik central crane (ventose/vacuum suction cup) — only the warehouse crane is in scope.

**Known limitations:**
- The `COLOR_POSITION_MAP` in the orchestrator is hardcoded — extending to new colours requires a code change (a deliberate simplification, noted as future work).
- The `machine_busy` flag in Node-RED measures command dispatch latency, not physical crane completion time.
- All three machines physically share the same warehouse crane in the lab (the multi-machine differentiation is logical, not physical).

---

## 4. Project Planning

### 4.1 Work Breakdown Structure (WBS)

The project was structured in seven sequential phases:

**Phase 1 — Framework study (February 2026, weeks 1–2)**
- 1.1 Study AAS standard (IDTA 01001-3-0, metamodel, AASX format)
- 1.2 Study CSS ontological model (CaSkade CSS-ontology v1.0.1)
- 1.3 Study SMIA architecture (source code, paper, self-configuration process)
- 1.4 Study SPADE, FIPA-ACL, and XMPP
- 1.5 Set up development environment (Docker, AASX Package Explorer, VS Code)

**Phase 2 — Case 0 implementation (February 2026, weeks 2–4)**
- 2.1 Create fischertechnik AAS model (AASX Package Explorer)
- 2.2 Configure AID submodel (HTTP endpoints for Node-RED)
- 2.3 Define CSS capabilities, skills, and semantic relationships
- 2.4 Deploy Docker Compose stack (ejabberd, SMIA, operator)
- 2.5 Configure Node-RED flows (HTTP→MQTT bridge)
- 2.6 Debug and resolve initial framework issues (MRO crash, asset connection bug)

**Phase 3 — Case 0 validation and documentation (late February – early March 2026)**
- 3.1 End-to-end validation (crane moves on operator click)
- 3.2 Write `doc_case0.md` technical reference document
- 3.3 Write `memoire.md` academic base (sections 1–15)

**Phase 4 — Case 1 architecture design (February – March 2026)**
- 4.1 Design multi-agent architecture (3 machines + orchestrator)
- 4.2 Create machine AASXs (machine1, machine2) with colour constraints
- 4.3 Create orchestrator AASX (AgentCapability, SkillParameter)
- 4.4 Design `Skill_NegAvailability` and `machineAvailValue` agent service

**Phase 5 — Case 1 implementation (March 2026)**
- 5.1 Implement `get_machine_availability()` agent service
- 5.2 Implement `OrchestratorDispatchBehaviour` (FIPA-CNP initiator)
- 5.3 Implement custom Dockerfiles (machine + orchestrator images)
- 5.4 Add Node-RED availability endpoint (`GET /smia/lego/availability`)
- 5.5 Containerize Node-RED and Mosquitto

**Phase 6 — Case 1 debugging and E2E validation (March – April 2026)**
- 6.1 Debug IRI casing issues in Track 3 relationship matching
- 6.2 Debug qualifier `semanticId` typo (`https://` vs `http://`)
- 6.3 Debug SPADE concurrent delivery race condition (`ACLHandlingBehaviour` vs `OrchestratorDispatchBehaviour`)
- 6.4 Debug operator GUI `hasParameter` processing bugs
- 6.5 E2E validation (orchestrator receives request, selects machine, crane moves)

**Phase 7 — Extended testing (April – May 2026) ✓ Complete**
- 7.1 ✓ Add duplicate-colour machine agents (machines 3 and 4 — red and blue duplicates)
- 7.2 ✓ Add a multicolour machine agent (machine5 — `color="red,blue"`) and validate it participates in negotiation for both colours
- 7.3 ✓ Prepare new standalone repo layout (`new_arch/` Dockerfiles and docker-compose.yml aligned with clean repo structure); write professional `README.md` and `PATCHES.md` for upstream contribution
- 7.4 ✓ Implement per-machine availability tracking (`machine_busy_<id>` flags in Node-RED); validate all extended scenarios end-to-end

**Phase 8 — Memory writing and finalization (April – May 2026)**
- 8.1 Complete `doc_case1.md` technical reference
- 8.2 Complete `memoire.md` (all sections)
- 8.3 Finalize `memoria_tfg.md` (this document) — LaTeX conversion
- 8.4 Final review and submission preparation

### 4.2 Schedule — Gantt Chart

The following table shows the actual schedule. Each cell represents one week. ● = active, ◐ = partial activity.

```
Phase / Activity        │      February      │        March       │        April       │        May
                        │ W1   W2   W3   W4  │ W1   W2   W3   W4  │ W1   W2   W3   W4  │ W1   W2   W3   W4
────────────────────────┼────────────────────┼────────────────────┼────────────────────┼────────────────────
Ph.1 Framework study    │  ●    ●    ◐        │                    │                    │
Ph.2 Case 0 impl.       │       ◐    ●    ●   │  ◐                 │                    │
Ph.3 Case 0 val.+docs   │                     │  ●    ●    ◐       │                    │
Ph.4 Case 1 design      │            ◐    ●   │  ●    ◐            │                    │
Ph.5 Case 1 impl.       │                     │  ◐    ●    ●    ◐  │                    │
Ph.6 Case 1 debug+E2E   │                     │            ◐    ●  │  ●    ●            │
Ph.7 Extended testing   │                     │                    │       ◐    ●    ●  │  ●    ●
Ph.8 Memory + submit    │       ◐             │       ◐            │  ●    ●    ●    ●  │  ●    ●    ●    ●
```

**Total duration:** ~4 months (February – May 2026), part-time alongside internship duties at Vicomtech. The Vicomtech agreement runs until June 2026; submission is planned for end of May 2026.

### 4.3 Human Resources Plan

| Role | Person | Dedication | Responsibilities |
|---|---|---|---|
| **Student / Developer** | Andrés Felipe Fierro Fonseca | ~450 hours total (part-time, ~4 months) | All development, debugging, AAS modelling, testing, documentation |
| **Academic tutor (Universidad de Deusto)** | Ander García Gangoiti | ~15 hours | Academic guidance, TFG structure review, evaluation preparation |
| **Technical tutor (Vicomtech)** | Xabier Oregui Biain | ~20 hours | Industrial alignment, lab access, fischertechnik asset, technical environment support |

### 4.4 Milestones

| # | Milestone | Date | Deliverable |
|---|---|---|---|
| M1 | Framework understood; first AASX created | End of February 2026 | `LEGO_machine0.aasx` (initial version) |
| M2 | Case 0 end-to-end validated | Early March 2026 | Crane moves on operator click; logs confirm E2E |
| M3 | Multi-agent AASX models complete | Mid-March 2026 | 3 machine AASXs + orchestrator AASX |
| M4 | FIPA-CNP flow operational | Late March 2026 | Orchestrator selects winner, crane executes |
| M5 | All bugs resolved; E2E Case 1 validated | Mid-April 2026 | Full Case 1 working end-to-end |
| M6 | Extended negotiation scenarios validated ✓ | End of April 2026 | Machines 3–5 deployed; multicolour filter implemented; per-machine busy tracking; new repo layout prepared |
| M7 | TFG memory finalized and submitted | End of May 2026 | This document (LaTeX) + `memoire.md` + `doc_case1.md` |

---

## 5. Budget

### 5.1 Labor Costs

The student performed multiple roles throughout the project. Hours are estimated per phase and allocated to the dominant role during that phase.

| Role | Hours | Rate (€/h) | Cost |
|---|---|---|---|
| Technical developer (implementation, debugging) | 250 h | €20 | €5,000 |
| Systems analyst (architecture design, AAS modelling) | 120 h | €20 | €2,400 |
| Technical writer (documentation) | 80 h | €20 | €1,600 |
| **Student subtotal** | **450 h** | | **€9,000** |
| Academic tutor — Ander García Gangoiti (Univ. Deusto) | 15 h | €80 | €1,200 |
| Technical tutor — Xabier Oregui Biain (Vicomtech) | 20 h | €80 | €1,600 |
| **Labor total** | | | **€11,800** |

### 5.2 Equipment and Hardware

| Item | Total value | Useful life | Usage period | Amortization |
|---|---|---|---|---|
| fischertechnik Training Factory Industry 4.0 24V | €2,500 | 5 years | 3 months | **€125** |
| Development laptop (existing Vicomtech equipment) | €1,200 | 3 years | 3 months | **€100** |
| **Equipment total** | | | | **€225** |

### 5.3 Software and Licenses

All software used is open source or freely available:

| Tool | License | Cost |
|---|---|---|
| SMIA framework | MIT | €0 |
| Docker / Docker Compose | Apache 2.0 | €0 |
| Python 3.12 | PSF License | €0 |
| AASX Package Explorer | MIT | €0 |
| Node-RED | Apache 2.0 | €0 |
| ejabberd | GPL v2 | €0 |
| Eclipse Mosquitto | EPL 2.0 | €0 |
| owlready2, basyx-python-sdk, SPADE, aiohttp | Open source | €0 |
| VS Code | MIT | €0 |
| **Software total** | | **€0** |

### 5.4 Total Budget Summary

| Category | Cost |
|---|---|
| Labor | €11,800 |
| Equipment (amortization) | €225 |
| Software | €0 |
| Travel and accommodation | €0 |
| Other costs | €0 |
| **Total** | **€12,025** |

---

## 6. Methodology

### 6.1 Development Approach

The project follows an **iterative and incremental** development approach, organized around two delivery increments corresponding to the two use cases:

- **Increment 1 (Case 0):** Deliver a working single-agent system that validates the fundamental self-configuration concept. This increment provides the architectural foundation, the AAS modelling process, and the Docker deployment stack.
- **Increment 2 (Case 1):** Extend the system to multi-agent orchestration. This increment introduces three additional machine agents, the orchestrator, and the FIPA-CNP negotiation flow, building directly on the validated Case 0 baseline.

Each increment follows three sub-phases: **design** (architecture and AAS modelling), **implementation** (Python code, Dockerfiles, configuration), and **verification** (end-to-end testing with the physical asset). The design of increment 2 began before increment 1 was fully documented — allowing the multi-agent architecture to benefit from the lessons learned during Case 0.

### 6.2 Iterative and Incremental Process

The development within each increment is driven by the **AAS model as the source of truth**: the AASX model is designed first, the Python code is written to interpret and extend it, and the deployment configuration is derived from the model's identifiers (JIDs, AAS IDs, capability names). This AAS-first principle mirrors the SMIA design philosophy and ensures that no asset-specific knowledge is hard-coded in the agent software.

Debugging cycles were significant in this project — particularly in Case 1, where the CSS semantic relationships impose high precision requirements (single-character IRI errors cause silent runtime failures). Each debugging cycle followed a systematic process: reproduce the failure in logs, trace the execution path in SMIA source code, identify the root cause (not just the symptom), apply a minimal fix, and re-validate end-to-end.

### 6.3 Tools and Development Environment

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12 | Agent implementation language |
| SMIA | 0.3.x (latest-alpine) | Base agent framework (Docker image) |
| AASX Package Explorer | Latest | AAS model creation and editing |
| Docker Compose | v2 | Multi-container deployment |
| VS Code | Latest | Development environment |
| Git | 2.x | Version control |
| Node-RED | 3.x | HTTP→MQTT protocol bridge |
| ejabberd | Latest | XMPP message broker |
| Mosquitto | 2.x | MQTT broker with bridge support |
| OWLready2 | 0.48 | OWL ontology processing |
| basyx-python-sdk | 1.2.1 | AAS model parsing |
| SPADE | 4.0.3 | Multi-agent framework |

**Version control:** The project is maintained in a Git repository with branch `my_implementation` for the active TFG work. All deployment files are in `my_models/` within the SMIA repository.

---

## 7. Development

*This section follows the §5.2 Operativización de modelos structure from the TFG specification.*

### 7.1 Requirements and Design

#### 7.1.1 Functional Requirements

| ID | Requirement | Case |
|---|---|---|
| FR1 | The system shall allow an operator to discover available manufacturing capabilities through a web interface without prior knowledge of the asset's implementation. | 0 + 1 |
| FR2 | The system shall derive the complete execution path (capability → skill → interface → HTTP call) autonomously from the AAS model, with zero hard-coded asset logic in agent code. | 0 + 1 |
| FR3 | The system shall trigger physical actuation of the fischertechnik warehouse crane in response to an operator capability request. | 0 + 1 |
| FR4 | The system shall support multiple machine agents with colour constraints; the operator shall only need to specify the desired colour, not the specific machine. | 1 |
| FR5 | The system shall select the executing machine using a distributed negotiation protocol (FIPA-CNP) based on real-time machine availability. | 1 |
| FR6 | The system shall be deployable from a single command (`docker compose up`) on any Linux host with Docker installed. | 0 + 1 |

**Non-functional requirements:**

| ID | Requirement |
|---|---|
| NFR1 | All agent communication shall use FIPA-ACL over XMPP — no proprietary messaging. |
| NFR2 | All asset descriptions shall be valid AAS models (IDTA 01001-3-0 compliant). |
| NFR3 | The system shall log sufficient information to diagnose communication failures without access to agent source code. |
| NFR4 | All custom code shall be under version control and reproducible by a third party from the repository alone (no undocumented manual steps). |

#### 7.1.2 System Architecture — Case 0

Case 0 is a single-agent scenario. The communication chain from operator request to physical actuation:

```
[Browser] ──HTTP:10000──► [smia-operator]
  ──FIPA-ACL REQUEST (XMPP:5222)──► [ejabberd] ──► [smia-machine0]
  ──HTTP POST──► [nodered] ──MQTT──► [mosquitto-central]
  ──MQTT bridge──► [Physical machine broker] ──► [Warehouse crane]
```

Four Docker services suffice for Case 0: `ejabberd`, `smia-machine0`, `smia-operator`, and Node-RED (containerized in Case 1; external in the initial Case 0 prototype).

#### 7.1.3 System Architecture — Case 1

Case 1 adds six machine agents, an orchestrator, a containerized MQTT broker, and a containerized Node-RED instance:

```
[Browser] ──► [smia-operator] ──FIPA-ACL──► [ejabberd]
                                                 │
                              [smia-orchestrator] ←── operator REQUEST (color=red)
                                 │ AAS discovery (scans /aas/*.aasx)
                                 │ colour filter: machines where color list contains "red"
                                 │ CFP (fipa-contract-net) → machine0, machine3, machine5
                              [smia-machine0] [smia-machine3] [smia-machine5]
                                 │ GET /smia/lego/availability?machine=<id>
                                 │ PROPOSE exchange (peer-to-peer)
                                 │ INFORM(winner) → orchestrator
                              [smia-machineN (winner)]
                                 │ HTTP POST /smia/lego/pick?machine=<id>&position=0
                              [nodered] sets machine_busy_<id>=true
                                 ──MQTT──► [mosquitto-central] ──bridge──► [Physical crane]
```

Eleven Docker services share the `smia-net` bridge network: three infrastructure services (`ejabberd`, `mosquitto-central`, `nodered`), six machine agents (`smia-machine0` through `smia-machine5`), one orchestrator, and one operator. Docker DNS resolves service names internally without any IP configuration.

### 7.2 Implementation

#### 7.2.1 AAS Model Creation

All AAS models were created using **AASX Package Explorer**. Each machine AASX contains two AAS shells:

1. **Asset shell** (`LEGO_factory`, `LEGO_machine1` … `LEGO_machine5`): holds the AID submodel, CSS capabilities/skills, and semantic relationships. Loaded by SMIA during self-configuration (filtered by `AAS_ID` environment variable).

2. **Agent shell** (`SMIA_agent`, `SMIA_machine1` … `SMIA_machine5`): holds only the `SoftwareNameplate` submodel, read by the operator GUI and orchestrator for agent discovery (JID extraction from `InstanceName` property).

Six machine AASXs were created in total:

| File | JID | Color | Notes |
|---|---|---|---|
| `LEGO_machine0.aasx` | `smia_machine0@ejabberd` | red | Original Case 0 machine |
| `LEGO_machine1.aasx` | `smia_machine1@ejabberd` | blue | — |
| `LEGO_machine2.aasx` | `smia_machine2@ejabberd` | white | — |
| `LEGO_machine3.aasx` | `smia_machine3@ejabberd` | red | Duplicate — tests negotiation under competition |
| `LEGO_machine4.aasx` | `smia_machine4@ejabberd` | blue | Duplicate — same purpose |
| `LEGO_machine5.aasx` | `smia_machine5@ejabberd` | red,blue | Multicolour — participates in both red and blue negotiations |

Machines 3 and 4 are direct clones of machines 0 and 1 with different UUIDs and JIDs. Machine 5 has `color = "red,blue"` (comma-separated); the orchestrator's discovery filter uses list membership (`color_filter in color.split(',')`) to match it for both red and blue requests.

The **AID submodel** specifies the HTTP interface:
- `base = http://nodered:1880` (Docker DNS name of the containerized Node-RED)
- `actions/pickPiece`: POST to `/smia/lego/pick?machine=smia_machineN&position=N` — both the machine identifier and the warehouse slot are encoded as URL query parameters

The **CapabilitiesAndSkills submodel** defines:
- `Capability_PickPiece` (semanticId: `css-smia#AssetCapability`) with a `color` property (`"red"`, `"blue"`, or `"white"`)
- `Skill_PickPiece` (semanticId: `css#Skill`) with qualifier `hasImplementationType=OPERATION`
- `Skill_NegAvailability` (semanticId: `css#Skill`) — a TFG-created element for FIPA-CNP negotiation (see §7.2.3)

The **SemanticRelationships submodel** defines four `RelationshipElements` that link CSS OWL instances together. The semanticId IRIs must be **exactly lowercase** — a single capital letter causes SMIA's Track 3 to silently skip the link, breaking the execution graph at runtime.

The orchestrator AASX (`SMIA_orchestrator.aasx`) uses `AgentCapability` instead of `AssetCapability` for `Capability_PickPiece`, reflecting that the orchestrator does not directly control a physical asset. Its `SoftwareNameplate` `InstanceName` must be `smia_orch@ejabberd` (with domain) — without the domain, the operator GUI's version lookup fails silently, causing it to use the old FIPA-ACL message format that the orchestrator does not recognize.

#### 7.2.2 CSS Semantic Enrichment

Each AAS element that participates in the SMIA self-configuration must have a `semanticId` pointing to a CSS OWL class IRI:

| Element | semanticId | Track |
|---|---|---|
| Capability SMC | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` | 2 |
| Skill Property | `http://www.w3id.org/hsu-aut/css#Skill` | 2 |
| AID Interface SMC | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Interface` | 1 |
| AID EndpointMetadata | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/EndpointMetadata` | 1 |
| Rel: isRealizedBy | `http://www.w3id.org/hsu-aut/css#isRealizedBy` | 3 |
| Rel: accessibleThrough | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` | 3 |

Additionally, each Skill element requires a `Qualifier` with `semanticId = http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` (note: `http://`, not `https://`) and `value = OPERATION`. Without this qualifier, SMIA cannot validate the Skill and the self-configuration fails silently.

#### 7.2.3 Machine Agent Extension — Agent Service and `Skill_NegAvailability`

The machine agent requires one extension beyond the base SMIA: reporting its availability as a floating-point score for FIPA-CNP negotiation.

**`Skill_NegAvailability`** is a new AAS element created by this TFG — it does not exist in the upstream SMIA framework or in the CSS ontology. It is defined as a `Property` with `semanticId = css#Skill` and linked to the `machineAvailValue` SkillInterface via `accessibleThroughAgentService`. When SMIA's self-configuration loads it (Track 2), OWLready2 creates an individual named `Skill_NegAvailability` in the `css:Skill` class — giving it the IRI `http://www.w3id.org/hsu-aut/css#Skill_NegAvailability`. This IRI must match exactly the `NEG_CRITERION_IRI` constant in `orchestrator_dispatch_behaviour.py:126`.

The agent service function `get_machine_availability()` (file: `smia_machine_agent_services.py`) makes an async HTTP GET to Node-RED and returns `1.0` (machine free) or `0.0` (busy). It uses `aiohttp` instead of the synchronous `requests` library because SMIA runs all behaviours in a single Python asyncio event loop — a blocking HTTP call would freeze the entire event loop.

The URL includes a per-machine identifier derived from the `AGENT_ID` environment variable:
```python
MACHINE_ID = os.environ.get('AGENT_ID', 'machine').split('@')[0]
# e.g. 'smia_machine0@ejabberd' → 'smia_machine0'
url = f"{NODE_RED_BASE}/smia/lego/availability?machine={MACHINE_ID}"
```

Node-RED maintains a separate boolean flag per machine (`machine_busy_smia_machine0`, `machine_busy_smia_machine1`, etc.) in its global context. The `/smia/lego/pick` handler sets `machine_busy_<id>=true` on receipt and clears it after 8 seconds (enough time for the crane to complete its cycle). This ensures that when two machines with the same colour are both queried during FIPA-CNP negotiation, each reports its own real availability rather than sharing a single flag.

**Registration** in `smia_machine_starter.py`:
```python
smia_agent = ExtensibleSMIAAgent(...)
smia_agent.add_new_agent_service('machineAvailValue', get_machine_availability)
smia_agent.start()
```

#### 7.2.4 Orchestrator Extension — FIPA-CNP Initiator

The base SMIA framework implements the FIPA-CNP **responder/proposer** side (`HandleNegotiationBehaviour`): machines can receive a CFP, compute their bid, compare with peers, and declare a winner. The **initiator** side — formulating the CFP, waiting for the winner, delegating execution, and forwarding the result — does not exist in the framework. This is the primary software contribution of this TFG.

`OrchestratorDispatchBehaviour` is a SPADE `CyclicBehaviour` registered as an agent capability. Its `run()` method processes one message per event loop iteration and routes it through four states:

| Route | Trigger | Action |
|---|---|---|
| 1 | `REQUEST` + `css-service` + new thread | New task from operator → AAS discovery → colour filter → CFP |
| 2 | `INFORM` + negotiation thread | Winner notification → delegate execution REQUEST to winner |
| 3 | `INFORM` + execution thread | Result from winner → forward to operator |
| 4 | `FAILURE` + tracked thread | Propagate failure to operator |

**AAS-based machine discovery** (`_discover_machines_for_request()`): the orchestrator scans every `.aasx` file in the shared AAS folder at runtime, reads each machine's XMPP JID from `SoftwareNameplate.InstanceName` and its colour from `Capability_PickPiece.color`, and filters by the requested colour. The color value may be a comma-separated list (e.g., `"red,blue"` for machine5); the filter checks membership in that list:
```python
machine_colors = [c.strip().lower() for c in (color or '').split(',')]
if color_filter.lower() not in machine_colors:
    continue
```
This eliminates any hardcoded machine list — adding a new machine requires only a new AASX file, a new ejabberd account, and a new Docker Compose service, with no changes to orchestrator code.

**`_get_skill_param(params, name)`**: a helper function that extracts skill parameter values tolerating both bare keys (`'color'`) and full IRI keys (`'http://www.w3id.org/hsu-aut/css#color'`), since the operator GUI prepends the CSS namespace to parameter names before sending them.

### 7.3 Verification

#### 7.3.1 Case 0 End-to-End Validation

Validated end-to-end on 2026-03-04. The successful validation sequence:

1. SMIA agent starts → logs confirm: `Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']`
2. Operator GUI loads → discovers `smia_machine0@ejabberd` → displays capabilities
3. Operator selects `Capability_PickPiece` → clicks Submit
4. SMIA logs: `Executing skill of the capability through an asset service...` and `HTTP communication successfully completed.`
5. Node-RED publishes `bandera_custom:0` to MQTT topic `vicom/61/piso_0/lab/lego/commands`
6. Warehouse crane macro triggers physically
7. Operator GUI displays: `{"status":"ok","payload":"bandera_custom:0","position":0}`

**Validation of RQ1:** The agent derived the correct execution path (capability → `Skill_PickPiece` → AID `pickPiece` action → HTTP POST to `http://nodered:1880/smia/lego/pick`) entirely from the AAS model. No hard-coded asset knowledge exists in any Python file.

#### 7.3.2 Case 1 End-to-End Validation

Validated end-to-end. The orchestrator log sequence for a successful `color=red` request with multiple eligible machines:

```
OrchestratorDispatchBehaviour started.
new CSSRequest from operator (thread=op_T)
Eligible machine: smia_machine0@ejabberd (color=red) from LEGO_machine0.aasx
Eligible machine: smia_machine3@ejabberd (color=red) from LEGO_machine3.aasx
Eligible machine: smia_machine5@ejabberd (color=red,blue) from LEGO_machine5.aasx
CFP sent to [smia_machine0, smia_machine3, smia_machine5] (neg_thread=neg_T)
received winner INFORM from smia_machine0@ejabberd
execution REQUEST sent to smia_machine0@ejabberd
result forwarded to operator
```

**Validation of RQ2:** Six machine agents (three colours, with duplicates and a multicolour agent) self-configure from the same Python codebase with different AASX models. The orchestrator discovers eligible machines at runtime — no machine list is hardcoded. Machine5 participates in both red and blue negotiations by declaring `color="red,blue"`. Adding a seventh machine requires only a new AASX + docker-compose service block, zero code changes.

#### 7.3.3 Performance Metrics

The SMIA paper [3] reports benchmarks from a comparable deployment scenario (three robotic agents):

| Metric | Paper value | Case 0 expected |
|---|---|---|
| Self-configuration time (21 CSS elements) | 6.73 s | < 6.73 s (fewer CSS elements) |
| Self-configuration time (7 CSS elements) | 3.39 s | — |
| Messages per direct execution | 2 (REQUEST + INFORM) | 2 ✓ (confirmed) |
| End-to-end response time | 0.034–0.098 s | Within this range |

**Validation of RQ3:** The XMPP-based FIPA-ACL communication adds negligible latency relative to typical manufacturing operation timescales (seconds to minutes for physical actuation). The self-configuration time (under 7 seconds) is a one-time startup cost, not a per-request overhead.

For Case 1, the total message count for a single-machine colour match (no PROPOSE exchange): 1 (operator→orch REQUEST) + 1 (orch→machine CFP) + 1 (machine→orch INFORM winner) + 1 (orch→machine REQUEST) + 1 (machine→orch INFORM result) + 1 (orch→operator INFORM result) = **6 messages**. With n machines competing for the same colour: add n(n-1) PROPOSE messages.

### 7.4 Packaging

#### 7.4.1 Custom Docker Images

Two custom Docker images extend the base `ekhurtado/smia:latest-alpine` image via Dockerfiles in `my_models/docker/`:

**Machine image** (`docker/smia-machine/Dockerfile`):
1. `FROM ekhurtado/smia:latest-alpine` — SMIA, Python, all dependencies already installed
2. `COPY + RUN` — applies three patches (`smia_agent.py`, `negotiating_behaviour.py`, `handle_negotiation_behaviour.py`) using version-independent path detection (`python3 -c "import smia, os; print(os.path.dirname(smia.__file__))"`)
3. `COPY` — places `smia_machine_starter.py` and `smia_machine_agent_services.py` at `/`
4. `WORKDIR /` — adds `/` to Python's `sys.path` so `import smia_machine_agent_services` resolves
5. `CMD ["python3", "-u", "smia_machine_starter.py"]` — overrides the default SMIA launcher

All six machine agents share this single Dockerfile; they differ only in their AASX model and environment variables (`AAS_MODEL_NAME`, `AAS_ID`, `AGENT_ID`).

**Orchestrator image** (`docker/smia-orchestrator/Dockerfile`): same pattern, with four patches (adds `acl_handling_behaviour.py`, `negotiating_behaviour.py`, `handle_negotiation_behaviour.py` on top of `smia_agent.py`) and two additional files (`smia_orchestrator_starter.py`, `orchestrator_dispatch_behaviour.py`).

**Operator image** (`smia_operator_agent/Dockerfile`): uses `ekhurtado/smia:latest-alpine-base` (lighter variant); applies Patch 5 (`operator_gui_logic.py`) implicitly by COPY-ing the patched file to `/` — no `RUN` step needed since this file is not part of the installed SMIA package.

#### 7.4.2 Patches Applied to the SMIA Framework

During the implementation of Cases 0 and 1, five bugs were identified in the base SMIA framework (v0.3.x). All were fixed via build-time patches applied in the Dockerfiles (the patched files replace the originals inside the container image at build time, using a version-independent path detection technique). All patches are pending upstream PR submission to the SMIA repository. Each bug is documented in full below.

---

**Bug 1 — `smia_agent.py`: asset connection lookup failure due to Python object identity comparison**

*Affected file:* `src/smia/agents/smia_agent.py`, method `get_asset_connection_class_by_ref()`

*When it was first encountered:* Case 0, first end-to-end test. The operator GUI submitted a pick request; SMIA logs showed the capability and skill resolved correctly; but no HTTP call was made and the crane did not move.

*Root cause:*

During self-configuration (Track 1, `AASInitializationBehaviour`), SMIA reads the Asset Interfaces Description (AID) submodel, creates an `AssetConnection` object for each interface, and stores it in the agent's `asset_connections` dictionary with the `ModelReference` object (a BaSyx Python SDK object) to the AID interface as the key:

```python
self.asset_connections[interface_reference] = asset_connection
```

Later, during skill execution (`HandleCapabilityBehaviour`), SMIA retrieves the AID interface reference for the matched skill (e.g. `pickPiece`) and calls `get_asset_connection_class_by_ref(asset_connection_ref)` to look up the stored connection. This method iterates over `self.asset_connections.items()` and compares:

```python
for conn_ref, conn_class in self.asset_connections.items():
    if conn_ref == asset_connection_ref:   # original — only this comparison existed
        return conn_class
```

The problem is that `conn_ref` (stored during boot) and `asset_connection_ref` (obtained during execution) are **two different Python objects** — both represent the same AAS model path, but they are separately instantiated `ModelReference` instances from the BaSyx SDK. Python's `==` operator, when the class does not override `__eq__`, falls back to identity comparison (`is`), which is `False` for two different instances of the same path. Even if BaSyx has a partial `__eq__` implementation, the comparison failed in practice: the loop always exhausted without finding a match and raised `AASModelReadingError("There is not asset connection class linked to ...")`. The error was caught upstream, logged, and the skill execution path returned without making any HTTP call — silently.

*Fix applied:*

Added two additional comparison strategies as fallbacks:

```python
for conn_ref, conn_class in self.asset_connections.items():
    if conn_ref == asset_connection_ref:            # 1. original: BaSyx __eq__
        return conn_class
    if str(conn_ref) == str(asset_connection_ref):  # 2. string representation
        return conn_class
    if _ref_keys_tuple(conn_ref) == requested_ref_keys:  # 3. key-tuple comparison
        return conn_class
raise AASModelReadingError(...)
```

The key-tuple helper normalizes each `ModelReference` to a tuple of `(str(key.type), key.value)` pairs — the actual semantic content of the reference — and compares those. This is unambiguous and works regardless of object identity. Strategy 2 (string comparison) was added as an intermediate fallback since `str(ModelReference)` includes the path.

*Impact:* Without this fix, no HTTP call is ever made to Node-RED, and the physical crane never moves. This bug affects **all** SMIA deployments that call `get_asset_connection_class_by_ref()`, i.e. any skill execution via an asset service. It was not caught in the SMIA paper's test scenario because the paper's operator used the newer `css-service` ontology format that follows a different code path.

---

**Bug 2 — `acl_handling_behaviour.py`: concurrent message delivery to two behaviours causes double processing**

*Affected file:* `src/smia/behaviours/acl_handling_behaviour.py`, method `run()`

*When it was first encountered:* Case 1 integration testing. After the orchestrator received a `css-service` REQUEST from the operator, two conflicting executions started simultaneously: `OrchestratorDispatchBehaviour` began the FIPA-CNP negotiation flow, while `ACLHandlingBehaviour` spawned a `HandleCapabilityBehaviour` that tried to directly execute the capability on the orchestrator itself (which has no AID asset service defined for it), producing errors and leaving the system in an inconsistent state.

*Root cause:*

SMIA uses SPADE's multi-behaviour architecture. In the `RUNNING` state, the agent runs multiple `CyclicBehaviour` instances concurrently within the same asyncio event loop. `ACLHandlingBehaviour` calls `await self.receive(timeout=10)` each iteration. `OrchestratorDispatchBehaviour` (our custom extension) also calls `await self.receive(...)` to watch for incoming operator requests.

SPADE routes incoming XMPP messages to **all behaviours** that have a matching message template. When the operator sends a `css-service` REQUEST to the orchestrator, both `ACLHandlingBehaviour` and `OrchestratorDispatchBehaviour` receive the same message in their respective `receive()` calls during the same asyncio scheduling round.

The existing SMIA framework had a `reserved_threads` mechanism designed to prevent this: when `OrchestratorDispatchBehaviour` receives and takes ownership of a message, it was supposed to call `add_reserved_thread(msg.thread)`, and `ACLHandlingBehaviour` would then skip that thread. However, this mechanism has a fundamental race: both `receive()` calls return in the same asyncio scheduling round. By the time `ACLHandlingBehaviour` checks `reserved_threads`, `OrchestratorDispatchBehaviour` has not yet had a chance to execute its next statement and call `add_reserved_thread()`. The check therefore finds an empty set and proceeds to process the message.

*Fix applied:*

Introduced a sentinel attribute `pending_orchestrations` on the orchestrator agent only (set in `OrchestratorDispatchBehaviour.on_start()`). Added an early return in `ACLHandlingBehaviour.run()` before the thread reservation check:

```python
if (msg.get_metadata(FIPAACLInfo.FIPA_ACL_ONTOLOGY_ATTRIB) ==
        ACLSMIAOntologyInfo.ACL_ONTOLOGY_CSS_SERVICE and
        msg.get_metadata(FIPAACLInfo.FIPA_ACL_PERFORMATIVE_ATTRIB) ==
        FIPAACLInfo.FIPA_ACL_PERFORMATIVE_REQUEST and
        hasattr(self.myagent, 'pending_orchestrations')):
    return  # OrchestratorDispatchBehaviour handles css-service REQUESTs
```

This check is evaluated synchronously, before any `await`, so it cannot race with `OrchestratorDispatchBehaviour`. Machine agents do not have the `pending_orchestrations` attribute, so `hasattr(...)` returns `False` for them and the patch is completely transparent — their `css-service` REQUEST handling is unaffected.

*Impact:* Without this fix, every operator request to the orchestrator triggers two conflicting processing paths. The `HandleCapabilityBehaviour` spawned by `ACLHandlingBehaviour` fails because the orchestrator has no AID-defined asset service; the error propagates and the operator receives a malformed or missing response. The FIPA-CNP negotiation started by `OrchestratorDispatchBehaviour` may also be disrupted by the concurrent state changes. This bug only manifests when a custom `AgentCapability` behaviour (like our orchestrator) is added to an ExtensibleSMIAAgent alongside the built-in `ACLHandlingBehaviour`.

---

**Bug 3 — `operator_gui_logic.py`: two latent errors in `hasParameter` relationship processing**

*Affected file:* `additional_tools/extended_agents/smia_operator_agent/operator_gui_logic.py`, method `operator_load_controller()` (the handler executed when the operator clicks "Load" in the GUI)

*When it was first encountered:* Case 1 GUI testing, after adding `SkillParameter_color` with a `hasParameter` relationship to the orchestrator AASX. Clicking "Load" in the operator GUI returned a 500 error; the smia-operator container logs showed a `KeyError` or `TypeError`.

*Why it was never triggered before:* No AASX model shipped with the SMIA framework uses a `css:hasParameter` relationship. Both bugs are latent — they exist in the original code but are only reached when the `operator_load_controller` processes an AASX that contains at least one `RelationshipElement` with `semanticId = http://www.w3id.org/hsu-aut/css#hasParameter`. Our orchestrator AASX introduced this pattern for the first time.

*Background — how the GUI processes AAS relationships:*

The `operator_load_controller` reads each AASX from the `aas/` folder, extracts all `RelationshipElement`s grouped by their `semanticId` IRI, and iterates over them. For each relationship type there is a dedicated `if` branch. The `hasParameter` branch was the one with bugs. The data structure is `aas_elems: dict[AASElement, list[AASElement]]` — exactly the same pattern as `isRealizedBy` (mapping a Capability to a list of Skills), but mapping a Skill to a list of SkillParameter elements.

*Bug 3a — wrong dictionary key (`KeyError`):*

The original code in the `hasParameter` branch referenced `css_elems_info['skillData']`. The variable `css_elems_info` is a dictionary keyed by capability `id_short` strings (e.g. `css_elems_info['Capability_PickPiece']`). The key `'skillData'` is never set anywhere in the function — it does not exist. This `KeyError` propagated up through the aiohttp request handler and caused the 500 response.

*Bug 3b — unhashable type when adding to a set (`TypeError`):*

The `aas_elems` dictionary maps each Skill (domain) to a **list** of SkillParameter elements (range) — the same `dict[elem, list]` pattern used for `isRealizedBy`. The original code attempted:

```python
param_set.add(skill_param)   # skill_param is the whole list, not an individual element
```

Python `set.add()` requires hashable elements. A `list` is not hashable, so this raises `TypeError: unhashable type: 'list'`. Even if bug 3a had been absent, bug 3b would have prevented correct execution.

*Additional issue — AAS objects stored instead of id_short strings:*

The GUI's request submission logic (`operator_request_controller`) passes skill parameters to the FIPA-ACL message using their `id_short` strings, retrieved via `form.get(param)` where `param` is an id_short string. If the `skills_info` dictionary stored AAS objects instead of strings, `eval(skill_params)` would produce a `SyntaxError` and `form.get(param)` would look up the wrong key. Skill parameters must be stored as their `id_short` string values.

*Fix applied — replaces the entire `hasParameter` block:*

```python
if CapabilitySkillOntologyInfo.CSS_ONTOLOGY_PROP_HASPARAMETER_IRI == rel.iri:
    for skill, skill_params_list in aas_elems.items():
        if skill not in self.myagent.skills_info:
            self.myagent.skills_info[skill] = set()
        self.myagent.skills_info[skill].update(p.id_short for p in skill_params_list)
```

This: (1) uses the correct dictionary `self.myagent.skills_info` (keyed by AAS skill elements); (2) iterates over individual elements in `skill_params_list` rather than treating the list as a single value; (3) stores `id_short` strings (hashable, and compatible with the downstream request controller). The fix is backward compatible: machine AASXs have no `hasParameter` relationships, so this branch is never entered for them.

*AASX design consequence discovered during debugging:* The SkillParameter element's `id_short` must be `color` (not `SkillParameter_color`). The GUI uses the id_short directly as the HTML form field name, so it must match the parameter name used downstream in the FIPA-ACL message body and in `_get_skill_param(params, 'color')` in the orchestrator code.

---

**Bug 4 — `negotiating_behaviour.py`: concurrent negotiations cross-contaminate each other's messages**

*Affected file:* `src/smia/behaviours/negotiating_behaviour.py`

*When it was first encountered:* Case 1 multi-machine testing, when two operator requests were sent in quick succession (or when the orchestrator triggered back-to-back negotiations). Negotiation outcomes became incorrect — a machine would declare itself winner when it should not, or the wrong machine would win.

*Root cause:* `NegotiatingBehaviour` spawns a `HandleNegotiationBehaviour` instance for each incoming CFP to manage the proposal exchange. In the upstream code, this instance was registered with SPADE's `add_behaviour()` without a message template:

```python
self.myagent.add_behaviour(specific_neg_handling_behaviour)   # no template
```

Without a per-thread template, SPADE delivered every incoming `PROPOSE` message to **every registered `HandleNegotiationBehaviour` instance**, regardless of which negotiation thread the PROPOSE belonged to. When two negotiations ran concurrently, each handler received messages from the other's exchange and made decisions based on wrong values.

*Fix:* Pass a combined per-thread SPADE template when registering the behaviour:

```python
handle_neg_template = (
    GeneralUtils.create_acl_template(performative=PROPOSE, protocol=CNP, thread=msg.thread)
    | GeneralUtils.create_acl_template(performative=REQUEST, protocol=CNP, thread=msg.thread)
)
self.myagent.add_behaviour(specific_neg_handling_behaviour, handle_neg_template)
```

Each `HandleNegotiationBehaviour` now only receives messages whose `thread` matches the specific CFP it was spawned for. The `REQUEST` performative is also included because Patch 5 (below) introduces a retry mechanism that sends `REQUEST`-for-negValue messages on the same thread.

---

**Bug 5 — `handle_negotiation_behaviour.py`: negotiation deadlock with three or more machines**

*Affected file:* `src/smia/behaviours/specific_handle_behaviours/handle_negotiation_behaviour.py`

*When it was first encountered:* Case 1 testing with three eligible machines (color=red request reaching machines 0, 3, and 5). Negotiations frequently failed to resolve: the orchestrator waited indefinitely for a winner INFORM that never arrived.

*Root cause — three interacting problems:*

(A) **Race on PROPOSE arrival.** When a machine receives a CFP, it computes its availability value and immediately sends PROPOSE messages to all other negotiation targets. If a PROPOSE arrives at a peer *before* that peer has processed its own CFP and registered its `HandleNegotiationBehaviour`, the PROPOSE falls through to the generic `ACLHandlingBehaviour`, which ignores it. Because the upstream code had no retry mechanism, this lost message meant the recipient could never determine whether it had the highest value among all peers.

(B) **Premature behaviour exit.** When a machine received a PROPOSE with a higher value than its own, it called `exit_negotiation(is_winner=False)` immediately and removed the behaviour. Any late PROPOSE from a machine that had not yet replied was then delivered to a behaviour that no longer existed. The recipient therefore had an incomplete picture of the negotiation state.

(C) **10-second blocking receive.** The original loop used `await self.receive(timeout=10)`. This meant the behaviour could only take one action every 10 seconds, making any retry mechanism impractically slow.

*Fix (multi-part):*

1. **Deferred exit:** instead of calling `exit_negotiation()` immediately on detecting a loss, the result is stored in `self.negotiation_result`. The behaviour stays alive until the end of the iteration budget and only terminates then.

2. **Short receive timeout + iteration counter:** the receive timeout is reduced to 0.01 s. Each iteration without a message increments `self.iterations_pending`. The total budget is `max(5, len(targets) + 3)` iterations.

3. **REQUEST-for-negValue retry:** at randomly chosen iterations within 20–60% of the budget, the machine sends a `REQUEST` message to any peer that has not yet sent a PROPOSE, explicitly asking for its value. This recovers from lost initial PROPOSE messages.

4. **Individual PROPOSE dispatch with small delays:** PROPOSE messages are sent to targets one at a time (with `asyncio.sleep(0.01)` between sends) rather than broadcasting to all simultaneously, reducing the chance that all machines flood each other before any `HandleNegotiationBehaviour` is registered.

5. **Thread reservation:** `on_start()` calls `add_reserved_thread(self.neg_thread)` and `exit_negotiation()` calls `remove_reserved_thread()`, cooperating with `ACLHandlingBehaviour`'s reservation mechanism.

---

### 7.5 Launch

#### 7.5.1 Docker Compose Deployment

All eight services are defined in `my_models/docker-compose.yml`. Credentials are provided via `my_models/.env` (gitignored; template in `.env.example`):

```bash
# First time: build custom images
docker compose -f my_models/docker-compose.yml build

# Start all services
docker compose -f my_models/docker-compose.yml up -d

# View logs
docker compose -f my_models/docker-compose.yml logs -f smia-machine0 smia-orchestrator
```

**Critical note:** Docker Compose **v2** (`docker compose` with a space) must be used. The legacy `docker-compose` v1 (hyphen) crashes with `KeyError: 'ContainerConfig'`.

#### 7.5.2 Incremental Startup Strategy

For debugging and phased validation, services can be started incrementally:

```bash
# Phase 1: infrastructure + machines (validate Case 0 / machine extension)
docker compose -f my_models/docker-compose.yml up -d \
  ejabberd mosquitto-central nodered \
  smia-machine0 smia-machine1 smia-machine2 smia-operator

# Phase 2: add orchestrator (validate FIPA-CNP)
docker compose -f my_models/docker-compose.yml up -d smia-orchestrator
```

This two-phase approach allows Case 0 to be validated independently of the orchestrator, and allows the orchestrator to be restarted independently without affecting the machine agents.

### 7.6 Configuration

#### 7.6.1 XMPP (ejabberd) and Agent Credentials

ejabberd is configured in `my_models/xmpp_server/ejabberd.yml`. Agent accounts are registered automatically at container startup via the `CTL_ON_CREATE` environment variable in the ejabberd Docker Compose service. All passwords come from `my_models/.env`.

**Critical:** If `.env` is modified after the first `docker compose up`, the ejabberd database still holds the old passwords. After too many failed authentication attempts, ejabberd blacklists the container's IP. Fix: `docker compose down -v && docker compose up -d` (full volume wipe, forces re-registration with current `.env` passwords).

#### 7.6.2 MQTT Broker and Bridge

`my_models/mosquitto/mosquitto.conf` configures the containerized Mosquitto broker (listener on port 1883, anonymous access, persistence enabled). `my_models/mosquitto/conf.d/bridge.conf` configures a bridge to the physical fischertechnik machine's Mosquitto broker:

- `address 192.168.155.10:1883` — the DIDA central machine's IP (**only configuration value that must be changed per deployment**)
- `topic vicom/61/piso_0/lab/lego/# out 1` — forward commands from containerized broker to physical machine
- QoS 1 outbound (ensures delivery), QoS 0 inbound (status updates, best-effort)

#### 7.6.3 Node-RED HTTP→MQTT Flow

Node-RED loads `my_models/nodered/flows.json` at startup. The flow exposes three HTTP endpoints:

| Endpoint | Method | Function |
|---|---|---|
| `/smia/lego/pick` | POST | Extracts `position` from body → URL query param → default; sets `machine_busy=true`; publishes `bandera_custom:<N>` to MQTT; clears `machine_busy=false` |
| `/smia/lego/place` | POST | Same pattern for place operations |
| `/smia/lego/availability` | GET | Reads `machine_busy` global flag; returns `"1.0"` (free) or `"0.0"` (busy) as plain text |

The `pick` handler uses a three-level position fallback: `body.position` → `query.position` (URL parameter, used by machines 1 and 2 via AID `href`) → `DEFAULT_POSITION=0` (used by machine 0). This is why machine 0's AID `href` is `/smia/lego/pick` (no query parameter) — the fallback covers it, and the position sent by the orchestrator in `skillParams` does not reach the body because `Skill_PickPiece` has no `hasParameter` relationship in the machine AASXs.

The MQTT broker node in the flow points to `mosquitto-central:1883` (Docker DNS, auto-resolved). No IP changes are needed inside the flow — only the `bridge.conf` address requires deployment-specific configuration.

### 7.7 Monitoring

#### 7.7.1 Docker Log Analysis

SMIA agents log to stdout with unbuffered output (`-u` flag in CMD). Key log patterns to monitor:

| Service | Expected pattern | Meaning |
|---|---|---|
| `smia-machine0/1/2` | `AAS model initialized.` | Self-configuration completed successfully |
| `smia-machine0/1/2` | `Analyzed skills: ['Skill_PickPiece', 'Skill_PlacePiece', 'Skill_NegAvailability']` | All three skills loaded and linked |
| `smia-orchestrator` | `Analyzed capabilities: ['Capability_PickPiece']` | Orchestrator AAS loaded |
| `smia-operator` | `Starting web server on port 10000` | Operator GUI ready |
| any SMIA | `No message received within 10 seconds` | Normal idle polling — not an error |
| `ejabberd` | `Starting ejabberd ... done` | XMPP broker operational |

#### 7.7.2 Health Checks and Startup Validation

Docker Compose `depends_on` with `service_healthy` is configured for the `ejabberd` service, preventing SMIA agents from starting before the XMPP server is ready. The `smia-operator` and machine agents wait for `ejabberd` to be healthy before attempting XMPP login.

After `docker compose up -d`:
1. Wait for ejabberd health: `docker compose -f my_models/docker-compose.yml ps ejabberd`
2. Check machine self-configuration: `docker compose logs smia-machine0 | grep "AAS model"`
3. Check operator GUI: `curl http://localhost:10000/smia_operator` (HTTP 200)
4. Check Node-RED availability: `curl http://localhost:1880/smia/lego/availability` (returns `1.0`)

---

## 8. Ethical Assessment

### 8.1 Data and Privacy

This project processes no personal data of any kind. The system handles only:
- Manufacturing capability names and parameters (e.g., colour of a piece to pick)
- XMPP agent identifiers and credentials (local lab network, not publicly exposed)
- Machine availability status (a boolean flag in Node-RED memory)

No user profiles, biometric data, location data, or any other personal information is collected, stored, or transmitted. The system is fully compliant with GDPR by design — there is no applicable personal data processing.

### 8.2 Physical Safety

The physical asset (fischertechnik Training Factory Industry 4.0 24V) is a professional-grade educational simulation model. During all tests:
- No human workers are present in the warehouse crane operating area during automated actuation.
- The crane operates at low speed within a physically bounded area (the fischertechnik chassis).
- Emergency stop is always available by disconnecting power or killing the Docker stack.
- The system operates only on Vicomtech's internal lab network, not accessible from the internet.

The scope is explicitly limited to the **warehouse crane** (Hochregallager). The central crane with vacuum suction cup (ventose) is physically present but not connected to the system in any use case of this TFG.

### 8.3 Open Source and Transparency

The SMIA framework is published under an open-source license [3]. This TFG's contributions — the `OrchestratorDispatchBehaviour`, agent service, AAS models, and bug fixes — are intended for upstream contribution to the SMIA repository, increasing the framework's openness and reproducibility. The five bug fixes identified (§7.4.2) are documented with root cause analysis and minimal patches, enabling independent verification.

### 8.4 Bias and Discrimination

The system makes routing decisions based entirely on physical and technical criteria: the colour property declared in each machine's AASX model (corresponding to the physical colour of pieces stored in warehouse slots), and real-time machine availability. No human characteristics are involved in any decision. The FIPA-CNP winner selection is deterministic for equal availability scores (alphabetical JID tie-break).

### 8.5 Environmental Considerations

The containerized deployment minimizes resource consumption: all services run on a single development machine, no cloud infrastructure is required, and containers can be stopped when not in use (`docker compose down`). The fischertechnik factory's 24V power consumption is negligible. The use of open-source software eliminates the environmental cost of proprietary license servers.

### 8.6 Acknowledged Limitations

The current system has no authentication layer on HTTP endpoints: Node-RED accepts any POST to `/smia/lego/pick` without credentials. In the current lab deployment this is acceptable (internal network, no internet exposure), but would require TLS and API key authentication before any production deployment. This limitation is explicitly documented and noted as a future work item.

---

## 9. Incidents and Issues Resolved

The following non-trivial issues were identified and resolved during implementation. Each entry includes the root cause (not just the symptom) and the resolution applied.

| # | Issue | Root cause | Resolution |
|---|---|---|---|
| 1 | Docker Compose crash: `KeyError: 'ContainerConfig'` | Legacy `docker-compose` v1 (hyphen) incompatible with compose file v3 features | Switched to `docker compose` v2 (space); all instructions updated |
| 2 | SMIA `InitAASModelBehaviour` MRO crash | Skills defined as `SubmodelElementCollection` — SMIA uses `types.new_class` for dynamic subclassing, which requires a concrete Python class to subclass, not a collection container | Changed all Skill elements to `Property` type in AASX Package Explorer |
| 3 | Capability request hangs, crane never moves | `get_asset_connection_class_by_ref()` matched AID references using Python object identity; a different Python instance of the same reference was created during skill execution → lookup returned `None` | Patched `smia_agent.py` with string comparison and key-tuple comparison strategies |
| 4 | Operator GUI HTTP 500 on Load | Non-AASX file (`.bak2` backup) in `my_models/aas/` folder scanned by operator as an AASX and causing a JSON parse exception | Moved all non-`.aasx` files out of the `aas/` folder; added this constraint to documentation |
| 5 | Node-RED returning HTTP 400 for pick request | Machine AASXs have no `hasParameter` relationship for `Skill_PickPiece`, so SMIA sends an empty HTTP body; Node-RED required `position` in the body | Added three-level position fallback in Node-RED `pick_handler`: `body.position` → `query.position` → `DEFAULT_POSITION=0`. Position encoded in AID `href` as URL query parameter for machines 1 and 2 |
| 6 | `HandleNegotiationBehaviour: 'NoneType' object is not iterable` | RelationshipElement `semanticId` IRIs in machine AASXs used wrong casing: `#AccessibleThroughAgentService` (capital 'A'); SMIA Track 3 requires exact lowercase — silent skip, OWL link never created | Fixed all three machine AASXs with a Python zipfile+regex script correcting IRI casing in all five relationship semanticIds |
| 7 | `hasImplementationType not found` at boot | Qualifier `semanticId` was `https://www.w3id.org/...` instead of `http://www.w3id.org/...` (a single character typo inserted by AASX Package Explorer autofill); SMIA's `get_qualifier_value_by_semantic_id()` does exact string comparison | Fixed all three machine AASXs (four qualifiers per file); documented the correct IRI in CLAUDE.md |
| 8 | Orchestrator race condition: both `ACLHandlingBehaviour` and `OrchestratorDispatchBehaviour` handle the same `css-service` message | SPADE broadcasts every incoming message to all matching behaviours; `ACLHandlingBehaviour` processed the operator REQUEST before `OrchestratorDispatchBehaviour` could reserve its thread | Patched `acl_handling_behaviour.py`: early return for `css-service` ontology messages when `pending_orchestrations` attribute is present (orchestrator-only) |
| 9 | Operator GUI crash (`SyntaxError`) on Load when selecting orchestrator | Two latent bugs in `operator_gui_logic.py`'s `hasParameter` block, never triggered because no default SMIA AASX uses `hasParameter` relationships. Bug 1: `css_elems_info['skillData']` → `KeyError`. Bug 2: `param_set.add(skill_param)` where `skill_param` is a list → `TypeError: unhashable type` | Patched `operator_gui_logic.py`: replaced block with `self.myagent.skills_info[skill].update(p.id_short for p in skill_params_list)` |
| 10 | Concurrent negotiations produce incorrect outcomes (wrong machine wins) | `NegotiatingBehaviour` registered `HandleNegotiationBehaviour` without a per-thread SPADE message template; all instances received all PROPOSE messages regardless of thread, making concurrent negotiations corrupt each other | Patched `negotiating_behaviour.py`: pass `handle_neg_template_propose | handle_neg_template_request` (both filtered to `msg.thread`) to `add_behaviour()` |
| 11 | Negotiation deadlock with three or more eligible machines; orchestrator waits indefinitely for winner INFORM | Three interacting problems: (A) initial PROPOSE can arrive before the peer's `HandleNegotiationBehaviour` is registered → silently dropped, never retried; (B) machine exits the behaviour immediately on detecting a loss → late PROPOSE from slow peers hits a dead behaviour; (C) 10-second receive timeout prevents any retry logic | Patched `handle_negotiation_behaviour.py`: short 0.01 s receive timeout + iteration counter; deferred exit (keep behaviour alive until budget exhausted); REQUEST-for-negValue retry at random iterations 20–60% of budget; individual PROPOSE dispatch with async micro-delays; proper thread reservation/release |

Each of these issues was diagnosed by reading SMIA source code, identifying the precise line causing the failure, and applying a minimal targeted fix. The pattern across incidents 6, 7, and 9 is consistent: SMIA uses exact string comparison throughout, and a single-character error in any semanticId IRI causes a silent failure that manifests as a `NoneType` error later in the execution chain — far from the actual defect. Incidents 10 and 11 reflect an important limitation of the SMIA negotiation algorithm under concurrent load: the protocol was designed and tested for sequential, single-negotiation scenarios and needed robustness improvements before being able to handle the multi-machine configurations required by this TFG. All five patches are documented in `PATCHES.md` with root cause analysis, and are pending upstream PR submission to the SMIA repository.

---

## 10. Conclusions and Future Work

### 10.1 Conclusions

This TFG demonstrates that the AAS Type 3 + CSS paradigm provides a technically viable and reproducible foundation for flexible manufacturing. The following conclusions address the three research questions stated in §3.3.

**RQ1: Can a manufacturing asset's capabilities be fully described in AAS + CSS such that a SMIA agent derives the complete execution path without any asset-specific hard-coded logic?**

Yes — confirmed by Case 0. The SMIA agent reads the `LEGO_machine0.aasx` model at startup and derives the entire chain: `Capability_PickPiece → isRealizedBy → Skill_PickPiece → accessibleThroughAssetService → AID pickPiece action → HTTP POST to http://nodered:1880/smia/lego/pick`. No Python file contains the crane's IP address, endpoint path, capability name, or skill name. If a different machine were added with a different AID endpoint, the agent would handle it without code modification. This validates requirements R2 (automated self-configuration) and R7 (separation between physical asset and Digital Twin).

**RQ2: Can the same approach scale from a single agent to a multi-agent FIPA-CNP negotiation, with machine selection based on runtime availability, without modifying agent code?**

Yes — confirmed by Case 1. All six machine agents run identical Python code (`smia_machine_starter.py`, `smia_machine_agent_services.py`). Their difference is entirely in their AASX model and environment variables. The orchestrator discovers eligible machines at runtime by scanning the AAS folder — no machine list is hardcoded. The FIPA-CNP protocol selects the most available machine dynamically. Multicolour support (machine5 responding to both red and blue requests) required only a comma-separated value in the AASX `color` property and a one-line filter change in the orchestrator — zero new agent code. This validates requirements R4 (adaptability), R5 (distributed systems), and R6 (P2P FIPA-ACL communication).

The primary software contribution — `OrchestratorDispatchBehaviour` — fills the gap left by the base SMIA framework, which only provides the responder/proposer side of FIPA-CNP. Five bugs were identified and patched in the SMIA framework during this TFG; two of them (`negotiating_behaviour.py`, `handle_negotiation_behaviour.py`) were required to make multi-machine negotiation robust under realistic concurrent load. All contributions are designed for upstream submission to the SMIA repository.

**RQ3: Is the overhead of the standardization layer acceptable for real-time manufacturing actuation?**

Yes — within the acceptable range. Self-configuration time is under 7 seconds (one-time startup cost). Per-request latency (XMPP messaging + semantic reasoning) is in the 34–98 ms range reported by the paper [3], well within the operational timescales of physical manufacturing (seconds to minutes for crane movements). The overhead is dominated by network round-trips, not by the semantic reasoning itself.

**Overall conclusion:** The AAS + CSS + SMIA combination successfully satisfies all eight SMIA design requirements (R1–R8) in a real, reproducible deployment. The primary challenge is not the technology itself but the precision required in AAS authoring: a single incorrect character in a semanticId IRI causes silent failures that can be difficult to diagnose without source-level debugging. Improved validation tooling in the AAS ecosystem would significantly lower the barrier to adoption.

### 10.2 Future Work

1. **Upstream contributions:** Submit the five framework bug fixes and `OrchestratorDispatchBehaviour` as PRs to the SMIA repository, making them available to the broader community. Clean-up required before PR submission: remove `TODO BORRAR BUG TEST` warning log lines from `acl_handling_behaviour.py` and `handle_negotiation_behaviour.py`.

2. **Node-RED virtual factory dashboard (MVP):** Replace the MQTT output in the current Node-RED flows with a visual Node-RED dashboard (using the `node-red-dashboard` package) that simulates the warehouse: four coloured slots, animated picking state per machine, real-time machine busy/free status panel, and operations log. This removes the dependency on the physical fischertechnik crane, making the entire system self-contained and demonstrable from a single `docker compose up` on any laptop. The HTTP API endpoints (`/smia/lego/pick`, `/smia/lego/availability`) and per-machine busy flag logic remain unchanged — only the Node-RED output changes from MQTT publish to dashboard update.

3. **Strict busy-rejection:** Currently, if all machines are busy, the orchestrator waits indefinitely. A timeout with a `FAILURE` response to the operator would make the system more predictable in production.

4. **Configurable colour-to-slot mapping:** The current colour-to-warehouse-slot mapping (red=0, blue=1, white=2) is hardcoded in `orchestrator_dispatch_behaviour.py`. Moving this mapping to the AASX model (e.g., as a `position` property on each machine's `Capability_PickPiece`) would make it fully AAS-driven and remove the last hardcoded element from the orchestrator.

4. **Direct MQTT asset connection:** The current architecture uses HTTP → Node-RED → MQTT. The AID standard (IDTA 02017) and the SMIA `AssetConnection` abstraction (`ArchitectureStyle.PUBSUB`) are designed to support MQTT natively. Implementing a `MQTTAssetConnection` class would eliminate the Node-RED middleware layer.

5. **Formal capability constraint matching (Case 2):** Extend the CSS model with `CapabilityConstraint` pre/post-conditions and implement reasoning-based capability matching — checking not just whether a capability exists but whether it can be executed given the current system state.

6. **AAS server integration:** Connect the digital twins to a BaSyx AAS server to expose them via the standard REST API (IDTA 01002), enabling interoperability with third-party AAS-compliant tools.

7. **Security layer:** Add TLS to HTTP endpoints (Node-RED + XMPP) and API key authentication for capability requests, making the system suitable for production deployment.

---

## 11. References

[1] Industrial Digital Twin Association (IDTA). *Details of the Asset Administration Shell — Part 1: The Exchange of Information between Partners in the Value Chain of Industrie 4.0 (Version 3.0)*. IDTA 01001-3-0, 2023.

[2] Plattform Industrie 4.0. *The Plattform I4.0 Capability, Skill and Service Concept*. Federal Ministry for Economic Affairs and Energy (BMWi), 2020.

[3] E. Hurtado, A. Burgos, A. Armentia, and O. Casquero, "Self-configurable Manufacturing Industrial Agents (SMIA): a standardized approach for digitizing manufacturing assets," *Journal of Industrial Information Integration*, vol. 47, p. 100915, Sept. 2025. DOI: 10.1016/j.jii.2025.100915

[4] fischertechnik GmbH. *Training Factory Industry 4.0 24V — Product Reference 554868*. Available: https://www.fischertechnik.de/es-es/productos/industria-y-universidades/modelos-de-simulacion/554868-training-factory-industry-4-0-24v

[5] Industrial Digital Twin Association (IDTA). *Asset Interfaces Description — Submodel Template (IDTA 02017-1-0)*. 2023.

[6] J. Palanca, A. Terrasa, V. Julian, and C. Carrascosa, "SPADE 3: Supporting the New Generation of Multi-Agent Systems," *IEEE Access*, vol. 8, pp. 182537–182549, 2020. DOI: 10.1109/ACCESS.2020.3027357

[7] Foundation for Intelligent Physical Agents (FIPA). *FIPA ACL Message Structure Specification* and *FIPA Contract Net Interaction Protocol Specification*. FIPA, 2002. Available: http://www.fipa.org/repository/ips.php3

[8] W3C. *Web of Things (WoT) Thing Description*. W3C Recommendation, 2020. Available: https://www.w3.org/TR/wot-thing-description/

[9] OASIS. *MQTT Version 5.0 OASIS Standard*. 2019. Available: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html

[10] CaSkade-Automation. *CSS-ontology v1.0.1*. GitHub, 2024. Available: https://github.com/CaSkade-Automation/CSS

[11] Eclipse BaSyx. *basyx-python-sdk — Python implementation of the Asset Administration Shell*. Available: https://github.com/eclipse-basyx/basyx-python-sdk

[12] SMIA GitHub Repository. Available: https://github.com/ekhurtado/SMIA

[13] AASX Package Explorer. Available: https://github.com/admin-shell-io/aasx-package-explorer

[14] Node-RED. Available: https://nodered.org/

[15] ejabberd. Available: https://www.ejabberd.im/

[16] Eclipse Mosquitto. Available: https://mosquitto.org/

---

## 12. Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| **AAS** | Asset Administration Shell. The IDTA standard for representing manufacturing assets as structured digital twins. |
| **AASX** | ZIP-based file format for storing AAS models, with an internal XML/JSON representation and supporting files (ontologies, properties). |
| **AID** | Asset Interfaces Description. IDTA submodel standard (02017-1-0) for describing asset communication interfaces using W3C WoT semantics. |
| **AgentCapability** | In the SMIA CSS ontology: a capability provided by a software agent (e.g., FIPA-CNP orchestration), as opposed to a physical machine function. |
| **AssetCapability** | In the SMIA CSS ontology: a capability provided directly by a physical manufacturing asset (e.g., picking a piece). |
| **asyncio** | Python's standard library for asynchronous I/O using coroutines and an event loop. Used by SPADE and SMIA for concurrent behaviour execution. |
| **CSS** | Capability-Skill-Service. An ontological model for describing manufacturing functions at three abstraction levels (capability, skill, service/interface). |
| **CyclicBehaviour** | A SPADE behaviour type that re-executes its `run()` method in a loop on every event loop iteration. Used for `OrchestratorDispatchBehaviour`. |
| **Docker** | Container platform for packaging and running software in isolated, reproducible environments. |
| **Docker Compose** | Tool for defining and running multi-container Docker applications from a YAML file. Must be v2 (`docker compose` with space). |
| **ejabberd** | Production-grade open-source XMPP server. Used as the FIPA-ACL transport layer for all agent communication. |
| **FIPA-ACL** | Foundation for Intelligent Physical Agents — Agent Communication Language. Standardized format for agent messages (request, inform, propose, etc.). |
| **FIPA-CNP** | FIPA Contract Net Protocol. A task allocation protocol in which an initiator broadcasts a CFP and contractors bid; the winner executes the task. |
| **GCIS** | Control and Systems Integration research group at UPV/EHU. Developers of the SMIA framework. |
| **HTTP** | Hypertext Transfer Protocol. Used for SMIA → Node-RED communication. |
| **IDTA** | Industrial Digital Twin Association. Maintains the AAS standard. |
| **Industry 4.0** | The Fourth Industrial Revolution: convergence of physical production systems with digital technologies. |
| **IRI** | Internationalized Resource Identifier. A URL-like string uniquely identifying a resource in semantic web and OWL systems. |
| **MAS** | Multi-Agent System. A collection of autonomous software agents that communicate and cooperate. |
| **MES** | Manufacturing Execution System. Software tracking and controlling manufacturing processes. |
| **MQTT** | Message Queuing Telemetry Transport. Lightweight publish-subscribe messaging protocol for IoT and industrial communication. |
| **MRO** | Method Resolution Order. Python's algorithm for method lookup in multiple inheritance hierarchies. |
| **Node-RED** | Flow-based visual programming tool for IoT and protocol bridging. Used as HTTP→MQTT bridge. |
| **OWL** | Web Ontology Language. W3C standard for defining ontologies. Used via OWLready2 in SMIA for semantic reasoning. |
| **RAMI 4.0** | Reference Architectural Model for Industrie 4.0. Three-dimensional framework for Industry 4.0 concepts. |
| **semanticId** | A URI assigned to an AAS element that links it to an OWL class or property in an external ontology. The mechanism by which SMIA performs semantic reasoning. |
| **SMIA** | Self-configurable Manufacturing Industrial Agents. Open-source AAS+CSS agent framework developed at UPV/EHU. |
| **SPADE** | Smart Python Agent Development Environment. Python MAS framework using asyncio and XMPP. |
| **Skill** | CSS concept: a concrete, technology-specific implementation of a Capability on a particular machine. |
| **SkillInterface** | CSS concept: the access point for invoking a Skill (describes protocol binding and parameters). |
| **TFG** | Trabajo de Fin de Grado. Spanish term for Bachelor's Thesis. |
| **UPV/EHU** | Universidad del País Vasco / Euskal Herriko Unibertsitatea (University of the Basque Country). Developers of SMIA. |
| **Ventose** | Vacuum suction cup. Refers to the central crane of the fischertechnik Training Factory. Not in scope for this TFG. |
| **WoT** | Web of Things. W3C standard for describing IoT device interfaces in machine-readable form. Used by the AID submodel. |
| **XMPP** | Extensible Messaging and Presence Protocol. Open real-time messaging standard used as transport layer for SMIA FIPA-ACL communication. |

---

## Appendices

### Appendix A — AASX Model Structure (Machine Agent)

Each machine AASX (`LEGO_machine0.aasx`, `LEGO_machine1.aasx`, `LEGO_machine2.aasx`) contains two AAS shells. The asset shell structure:

```
AAS: LEGO_factory  (id: urn:uuid:6475_0111_2062_9689)
├── Submodel: SubmodelWithCapabilitySkillOntology
│   └── ConceptDescriptions (CSS OWL class definitions — also in embedded .owl file)
├── Submodel: AssetInterfacesDescription
│   └── InterfaceHTTP
│       ├── EndpointMetadata
│       │   ├── base: "http://nodered:1880"
│       │   └── contentType: "application/json"
│       ├── InteractionMetadata
│       │   └── actions
│       │       ├── pickPiece  (semanticId: ActionAffordance)
│       │       │   └── forms: href=/smia/lego/pick  method=POST
│       │       └── placePiece (semanticId: ActionAffordance)
│       │           └── forms: href=/smia/lego/place method=POST
│       └── Interface_00  (agent service interface)
│           └── InteractionMetadata
│               └── actions
│                   └── machineAvailValue (semanticId: ActionAffordance)
├── Submodel: CapabilitiesAndSkills
│   ├── Capability_PickPiece  (semanticId: css-smia#AssetCapability)
│   │   ├── qualifier: hasLifecycle=OFFER
│   │   └── color (Property xs:string, value: "red"|"blue"|"white")
│   ├── Capability_PlacePiece (same pattern)
│   ├── Skill_PickPiece        (Property xs:string, semanticId: css#Skill)
│   │   └── qualifier: SkillImplementationType=OPERATION
│   │       semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType
│   ├── Skill_PlacePiece       (same pattern)
│   └── Skill_NegAvailability  (Property xs:string, semanticId: css#Skill)
│       └── qualifier: SkillImplementationType=OPERATION (same semanticId as above)
└── Submodel: SemanticRelationships
    ├── rel_CapPick_isRealizedBySkill_SkillPick
    │   semanticId: http://www.w3id.org/hsu-aut/css#isRealizedBy
    │   first: Capability_PickPiece  second: Skill_PickPiece
    ├── rel_CapPlace_isRealizedBySkill_SkillPlace  (same pattern)
    ├── rel_SkillPick_hasSkillInterface
    │   semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService
    │   first: Skill_PickPiece  second: AID/.../pickPiece
    ├── rel_SkillPlace_hasSkillInterface  (same pattern)
    └── rel_SkillNegAvail_agentSvc
        semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService
        first: Skill_NegAvailability  second: AID/Interface_00/.../machineAvailValue

AAS: SMIA_agent  (id: urn:uuid:6373_1111_2062_6896)
└── Submodel: SoftwareNameplate
    └── SoftwareNameplateInstance
        ├── InstanceName: "smia_machine0@ejabberd"  ← XMPP JID (must include @ejabberd domain)
        └── InstalledVersion: "0.3.1"
```

### Appendix B — Docker Compose Services Summary

```yaml
services:
  ejabberd:          ghcr.io/processone/ejabberd   — XMPP broker (port 5222)
  mosquitto-central: eclipse-mosquitto:2            — MQTT broker (internal)
  nodered:           nodered/node-red:latest        — HTTP→MQTT bridge (port 1880)
  smia-machine0:     build: docker/smia-machine     — red   (smia_machine0@ejabberd)
  smia-machine1:     build: docker/smia-machine     — blue  (smia_machine1@ejabberd)
  smia-machine2:     build: docker/smia-machine     — white (smia_machine2@ejabberd)
  smia-machine3:     build: docker/smia-machine     — red duplicate  (smia_machine3@ejabberd)
  smia-machine4:     build: docker/smia-machine     — blue duplicate (smia_machine4@ejabberd)
  smia-machine5:     build: docker/smia-machine     — red+blue multicolour (smia_machine5@ejabberd)
  smia-orchestrator: build: docker/smia-orchestrator — FIPA-CNP dispatcher (smia_orch@ejabberd)
  smia-operator:     build: additional_tools/...    — web GUI (port 10000)

All services: network smia-net (Docker bridge, DNS resolves service names)
Credentials: from my_models/.env (gitignored; template: .env.example)
AAS files: shared volume my_models/aas/ → /smia_archive/config/aas/ in all agent containers
```

### Appendix C — Node-RED Flow Structure

Per-machine busy state is tracked using separate global context flags keyed by machine ID (`smia_machine0`, `smia_machine1`, etc.). This allows independent availability reporting when multiple machines with the same colour participate in a FIPA-CNP round simultaneously.

```
HTTP In (POST /smia/lego/pick)
    → Function (pick_handler):
        1. machineId = query.machine || 'default'
        2. position  = query.position || body.position || DEFAULT_POSITION (0)
        3. global.set('machine_busy_' + machineId, true)
        4. Validate position (int, 0–8); build payload "bandera_custom:<position>"
        5. chainMsg.payload = { action:'pick', position, machine: machineId }
        → MQTT Out (mosquitto-central:1883, topic: vicom/61/piso_0/lab/lego/commands, QoS=1)
        → Delay (8 s)
        → Function (clear_busy): global.set('machine_busy_' + msg.payload.machine, false)
    → HTTP Response 200

HTTP In (GET /smia/lego/availability)
    → Function (availability_handler):
        var machineId = req.query.machine || 'default';
        var busy = global.get('machine_busy_' + machineId) || false;
        msg.payload = busy ? "0.0" : "1.0";
    → HTTP Response 200 (text/plain)
```

### Appendix D — Environment Variable Reference (`.env.example`)

```env
# ejabberd
EJABBERD_COOKIE=<random_string>

# Machine 0 (smia_machine0@ejabberd, LEGO_machine0.aasx, red)
MACHINE0_AAS_FILE=LEGO_machine0.aasx
MACHINE0_AAS_ID=urn:uuid:6475_0111_2062_9689
MACHINE0_AGENT_ID=smia_machine0@ejabberd
MACHINE0_PASSWD=<password>

# Machine 1 (smia_machine1@ejabberd, LEGO_machine1.aasx, blue)
MACHINE1_AAS_FILE=LEGO_machine1.aasx
MACHINE1_AAS_ID=urn:uuid:6475_0111_2062_0001
MACHINE1_AGENT_ID=smia_machine1@ejabberd
MACHINE1_PASSWD=<password>

# Machine 2 (smia_machine2@ejabberd, LEGO_machine2.aasx, white)
MACHINE2_AAS_FILE=LEGO_machine2.aasx
MACHINE2_AAS_ID=urn:uuid:6475_0111_2062_0002
MACHINE2_AGENT_ID=smia_machine2@ejabberd
MACHINE2_PASSWD=<password>

# Machine 3 (smia_machine3@ejabberd, LEGO_machine3.aasx, red — duplicate for negotiation testing)
MACHINE3_AAS_FILE=LEGO_machine3.aasx
MACHINE3_AAS_ID=urn:uuid:6475_0111_2062_0003
MACHINE3_AGENT_ID=smia_machine3@ejabberd
MACHINE3_PASSWD=<password>

# Machine 4 (smia_machine4@ejabberd, LEGO_machine4.aasx, blue — duplicate)
MACHINE4_AAS_FILE=LEGO_machine4.aasx
MACHINE4_AAS_ID=urn:uuid:6475_0111_2062_0004
MACHINE4_AGENT_ID=smia_machine4@ejabberd
MACHINE4_PASSWD=<password>

# Machine 5 (smia_machine5@ejabberd, LEGO_machine5.aasx, red+blue multicolour)
MACHINE5_AAS_FILE=LEGO_machine5.aasx
MACHINE5_AAS_ID=urn:uuid:6475_0111_2062_0005
MACHINE5_AGENT_ID=smia_machine5@ejabberd
MACHINE5_PASSWD=<password>

# Orchestrator (smia_orch@ejabberd, SMIA_orchestrator.aasx)
ORCH_AAS_FILE=SMIA_orchestrator.aasx
ORCH_AAS_ID=urn:uuid:8888_0001_2026_0001
ORCH_AGENT_ID=smia_orch@ejabberd
ORCH_PASSWD=<password>

# Operator (operator001@ejabberd)
OPERATOR_AAS_FILE=SMIA_Operator_article.aasx
OPERATOR_AGENT_ID=operator001@ejabberd
OPERATOR_PASSWD=<password>

# Node-RED
NODERED_URL=http://nodered:1880
NODERED_CREDENTIAL_SECRET=<random_string>

# MQTT bridge (physical machine — set actual IP in config/mosquitto/conf.d/bridge.conf)
MACHINE_MQTT_HOST=192.168.155.10
MACHINE_MQTT_PORT=1883
```
