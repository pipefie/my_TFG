# Flexible Manufacturing Based on Digital Twins Using AAS and CSS Model

**Bachelor's Thesis (Trabajo de Fin de Grado)**
**University:** Universidad de Deusto
**Degree in Data Science**
**Author:** Andrés Felipe Fierro Fonseca
**Institution:** Vicomtech — Data Intelligence for Industry (DII)
**Tutor:** Ander García Gangoiti / Xabier Oregui Biain
**Date:** 2026

**Physical asset:** fischertechnik Training Factory Industry 4.0 24V (ref. 554868)
**Product page:** https://www.fischertechnik.de/es-es/productos/industria-y-universidades/modelos-de-simulacion/554868-training-factory-industry-4-0-24v

---

> **Note:** This document is a working memoire that serves as the evolving base for the formal TFG report. It is updated continuously as the project progresses and is not yet in final form. Sections marked with `[TODO]` require further elaboration.

---

## Abstract

This work investigates and implements a flexible manufacturing scenario based on digital twin technologies and standard multi-agent systems. The project combines the Asset Administration Shell (AAS) standard — the reference framework for Industrial Digital Twins (IDT) within Industry 4.0 — with the Capability-Skill-Service (CSS) ontological model to build an intelligent, self-configuring software agent (SMIA) that represents a physical manufacturing asset. The system enables a human operator to discover available manufacturing capabilities and trigger their execution through a standardized digital interface, with the physical action carried out autonomously by the underlying equipment. A concrete industrial use case is implemented using a **fischertechnik Training Factory Industry 4.0 24V** as the physical asset — specifically its warehouse crane (Hochregallager) for pick and place operations — demonstrating the complete pipeline from operator request to physical actuation via semantic reasoning, XMPP communication, HTTP, and MQTT protocols. The work is conducted at Vicomtech's Data Intelligence for Industry (DII) department and submitted to the Universidad de Deusto. It is built upon the open-source SMIA (Self-configurable Manufacturing Industrial Agents) research framework developed at the University of the Basque Country (UPV/EHU).

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Motivation and Problem Statement](#2-motivation-and-problem-statement)
3. [Objectives](#3-objectives)
4. [Background: Industry 4.0 and Smart Manufacturing](#4-background-industry-40-and-smart-manufacturing)
5. [Digital Twins in Manufacturing](#5-digital-twins-in-manufacturing)
6. [Asset Administration Shell (AAS)](#6-asset-administration-shell-aas)
7. [Capability-Skill-Service (CSS) Model](#7-capability-skill-service-css-model)
8. [Semantic Technologies: Ontologies and OWL](#8-semantic-technologies-ontologies-and-owl)
9. [Multi-Agent Systems and SPADE](#9-multi-agent-systems-and-spade)
10. [Industrial Communication Protocols](#10-industrial-communication-protocols)
11. [SMIA: Self-configurable Manufacturing Industrial Agents](#11-smia-self-configurable-manufacturing-industrial-agents)
12. [Use Case: Case 0 — Flexible Factory Assembly (fischertechnik)](#12-use-case-case-0--flexible-factory-assembly-fischertechnik)
13. [System Architecture](#13-system-architecture)
14. [Implementation](#14-implementation)
15. [Results and Validation](#15-results-and-validation)
16. [Discussion and Future Work](#16-discussion-and-future-work)
17. [Glossary](#17-glossary)
18. [References](#18-references)

---

## 1. Introduction

### 1.1 Context

Manufacturing is undergoing a profound transformation driven by the Fourth Industrial Revolution, commonly known as **Industry 4.0**. This transformation is characterized by the convergence of physical production systems with digital technologies: cloud computing, artificial intelligence, the Internet of Things (IoT), and advanced data analytics. The vision that underpins this transformation is that of the **Smart Factory**: an environment in which machines, products, and humans are digitally connected, share information autonomously, and coordinate their actions with minimal human intervention.

Despite substantial progress in automation and robotics over recent decades, modern manufacturing lines continue to face a fundamental limitation: they are designed for **rigidity**. A production line optimized for one product or a small family of products requires significant engineering effort to adapt to changes in volume, product variants, or new designs. This rigidity is increasingly incompatible with market trends toward personalization, short product life cycles, and on-demand production.

The solution to this challenge lies in **flexible manufacturing**: systems capable of adapting dynamically to changing production requirements without requiring manual reconfiguration of hardware or re-programming of control logic. Achieving true flexibility requires not only physical adaptability in the machines themselves, but also a standardized digital layer through which machines, software systems, and humans can communicate and negotiate in an interoperable, technology-agnostic manner.

This project addresses this challenge by designing and implementing a prototype flexible manufacturing scenario grounded in two complementary standards:

1. **Asset Administration Shell (AAS)** — the industrial digital twin standard promoted by the Industrial Digital Twin Association (IDTA) and Plattform Industrie 4.0, which provides a universal way to represent any manufacturing asset as a structured, machine-readable digital entity.
2. **Capability-Skill-Service (CSS) ontological model** — a semantic framework that describes what a manufacturing asset *can do* (capabilities) and *how it does it* (skills), decoupling the abstract ability from its concrete implementation.

The implementation vehicle for these standards is **SMIA** (Self-configurable Manufacturing Industrial Agents), an open-source research framework developed at the University of the Basque Country that combines AAS and CSS into autonomous software agents.

### 1.2 Scope

This TFG focuses on:
- Understanding and applying the AAS standard at a detailed technical level.
- Modeling a physical manufacturing asset (fischertechnik Training Factory Industry 4.0 24V — warehouse crane) as an AAS digital twin.
- Deploying and configuring SMIA to interpret that digital twin autonomously.
- Connecting the digital twin to a real communication chain (HTTP → MQTT) that triggers physical actuation.
- Validating the complete pipeline through a working end-to-end demonstration.

This TFG is developed at **Vicomtech** (Data Intelligence for Industry department) and submitted to **Universidad de Deusto**. It applies the SMIA framework developed at the GCIS (Group of Control and Systems Integration) at UPV/EHU, within their research line on intelligent agents for flexible manufacturing.

### 1.3 Document Structure

This document is organized as follows. Sections 2 and 3 establish the motivation and objectives of the work. Sections 4 through 10 provide the theoretical background necessary to understand the technologies involved. Section 11 describes the SMIA framework in detail. Section 12 presents the specific use case (Case 0). Section 13 details the implemented system architecture. Section 14 documents the implementation. Section 15 presents results and validation. Section 16 discusses conclusions and future work. A glossary and reference list close the document.

---

## 2. Motivation and Problem Statement

### 2.1 The Flexibility Gap in Manufacturing

Modern manufacturing systems have achieved remarkable levels of automation, yet they remain fundamentally inflexible. A robotic arm programmed to perform a specific welding operation on a specific car model must be re-programmed — a process requiring specialized engineers, significant downtime, and substantial cost — to perform a different welding operation on a new model. This is not a failure of automation; it is a structural property of today's manufacturing paradigm: **automation is designed for repeatability, not adaptability**.

The consequences of this inflexibility are increasingly visible in industry:
- **Short product life cycles** require frequent production changeovers.
- **Mass customization** demands the ability to produce individualized products at scale.
- **Supply chain disruptions** require rapid substitution of components or processes.
- **Labour shortages** push industry to automate tasks previously performed by flexible human workers.

Human workers remain indispensable precisely because of our natural flexibility: we can adapt to new tasks, understand context, handle exceptions, and collaborate with machines and each other without requiring explicit re-programming. The challenge for Industry 4.0 is to bring machine systems closer to this level of adaptability.

### 2.2 Why Standardization is the Key

The historical approach to automation integration has been proprietary: each machine vendor provides its own communication interfaces, data formats, and programming environments. This leads to **integration silos** — systems that work in isolation and cannot interoperate without expensive, custom-built adapters.

Flexibility requires interoperability. If a manufacturing system is to adapt dynamically — routing production to different machines, substituting one asset for another, reconfiguring a line on the fly — the assets involved must be able to discover each other's capabilities, communicate in a shared language, and execute tasks without pre-configured, hard-coded relationships.

This is precisely the problem that **standardization** addresses. Standards like AAS, OPC UA, and the CSS ontological model provide the common vocabulary and structure that enable diverse assets to communicate with each other and with software systems in a technology-agnostic way.

### 2.3 The Role of Digital Twins

A **digital twin** is a virtual representation of a physical entity that is kept synchronized with its physical counterpart and can be used to monitor, analyze, simulate, and control that entity. In the manufacturing context, a digital twin acts as the digital interface through which the rest of the system interacts with a machine.

A standardized digital twin — such as one defined using the AAS standard — goes further: it provides not only data about the asset, but also structured information about the asset's *identity*, *properties*, *capabilities*, and *interfaces*. This enables software systems to discover and use assets' capabilities without prior knowledge of their specific implementations.

### 2.4 The Role of Intelligent Agents

Standardized digital twins alone are not sufficient for autonomous, flexible manufacturing. Machines must also be capable of:
- Discovering other machines' capabilities.
- Receiving and interpreting requests from operators or orchestration systems.
- Deciding autonomously how to fulfill a request.
- Executing the required physical actions and reporting results.

This is the domain of **multi-agent systems** (MAS). In a MAS, each asset is represented by an autonomous software agent that can communicate with other agents, reason about requests, and act on behalf of its physical counterpart. When combined with AAS digital twins and CSS capability models, intelligent agents form the backbone of a truly flexible manufacturing system.

---

## 3. Objectives

### 3.1 General Objective

Design and implement a prototype flexible manufacturing scenario in which a physical manufacturing asset — represented by a standardized digital twin (AAS) — is autonomously managed by an intelligent software agent (SMIA), enabling an operator to discover available manufacturing capabilities and trigger their execution through a standardized digital interface.

### 3.2 Specific Objectives

1. **Understand and apply the AAS standard** at a detailed technical level, including the AASX package format, submodel structure, and the Asset Interfaces Description (AID) submodel specification.

2. **Model a physical manufacturing asset** (fischertechnik Training Factory Industry 4.0 24V — warehouse crane) as a complete AAS digital twin, including:
   - Identity and metadata submodels.
   - CSS capability and skill definitions.
   - HTTP interface description via the AID submodel.
   - Semantic relationships linking capabilities to skills to interfaces.

3. **Embed a CSS OWL ontology** within the AAS package to enable semantic reasoning by the SMIA agent.

4. **Deploy and configure SMIA** using Docker Compose, with correct XMPP credentials, AAS model loading, and ontology parsing.

5. **Deploy the operator interface** (SMIA Operator) to validate the complete human-to-machine request cycle.

6. **Connect the digital system to the physical system** via:
   - HTTP endpoint (Node-RED on the DIDA central machine).
   - MQTT message chain from Node-RED to the fischertechnik control machine.
   - Correct payload format for warehouse crane macro triggering.

7. **Validate the complete end-to-end pipeline**: operator capability request → XMPP communication → SMIA skill resolution → HTTP POST → MQTT publish → fischertechnik warehouse crane execution.

8. **Document all design decisions and implementation details** so that the work can be reproduced by other researchers.

### 3.3 Research Questions

- Can a manufacturing asset's capabilities be fully described using the AAS + CSS standard combination, without any asset-specific hard-coded logic in the managing software?
- Can SMIA autonomously derive the correct execution path (from capability to physical HTTP call) from the information encoded in the AAS model alone?
- Is the overhead introduced by the standardization layer (AAS parsing, CSS reasoning, XMPP messaging) acceptable for a real-time manufacturing actuation scenario?

---

## 4. Background: Industry 4.0 and Smart Manufacturing

### 4.1 The Four Industrial Revolutions

Manufacturing has undergone three major transformations throughout history, each driven by a fundamental technological shift:

- **First Industrial Revolution** (~1760–1840): Mechanization of production driven by steam power. Manual craft production replaced by early machines.
- **Second Industrial Revolution** (~1870–1914): Electrification and mass production. Assembly lines, standardized parts, and the birth of modern industrial manufacturing.
- **Third Industrial Revolution** (~1960–2000): Computerization and automation. Programmable logic controllers (PLCs), robotics, and computer-aided design/manufacturing (CAD/CAM).
- **Fourth Industrial Revolution** (2010–present): **Industry 4.0**. The fusion of cyber (digital) and physical systems, driven by IoT, big data, cloud computing, AI, and advanced connectivity.

### 4.2 Industry 4.0: Core Concepts

The term "Industrie 4.0" was coined in Germany in 2011 as part of a national strategic initiative. Its central vision is the **Cyber-Physical System (CPS)**: a physical process or device tightly coupled with a computing and communication infrastructure that monitors and controls it in real time.

Key enabling technologies of Industry 4.0:

| Technology | Role |
|---|---|
| Internet of Things (IoT) | Connecting physical devices to digital networks |
| Cloud Computing | Centralized storage and computation infrastructure |
| Big Data & Analytics | Processing large volumes of production data |
| Artificial Intelligence | Enabling autonomous decision-making |
| Advanced Robotics | Flexible physical actuation |
| Additive Manufacturing | On-demand, customizable production |
| Augmented Reality | Human-machine interface enhancement |
| Cybersecurity | Protecting connected industrial systems |
| **Digital Twins** | Virtual representations of physical assets |
| **Standardized Communication** | AAS, OPC UA, MQTT, etc. |

### 4.3 The Smart Factory Vision

The **Smart Factory** is the manufacturing realization of Industry 4.0 principles. Key characteristics:

- **Interoperability**: Machines, devices, sensors, and people connect and communicate with each other via the Internet of Things (IoT) or the Internet of People (IoP).
- **Information transparency**: The information systems create a virtual copy of the physical world by enriching digital plant models with sensor data.
- **Technical assistance**: Systems support humans in making decisions and solving urgent problems, and assist with tasks that are too difficult or unsafe for people.
- **Decentralized decisions**: Cyber-physical systems make simple decisions autonomously and perform their tasks as independently as possible. Only in exceptional cases, when tasks are too complex, conflicting goals arise, or when something unexpected occurs, are they delegated to a higher level.

### 4.4 The Flexibility Challenge

Despite progress toward Smart Factory ideals, existing manufacturing systems remain largely rigid. The root cause lies in the way automation has been implemented historically:

1. **Functional decomposition**: Manufacturing processes are broken into fixed sequences of operations, each implemented as a specific automation routine.
2. **Hard-coded integration**: Machines communicate with each other and with control systems through proprietary, custom-built interfaces.
3. **Engineering-time configuration**: The behavior of the manufacturing system is defined at engineering time; adapting to new requirements requires re-engineering.

Flexible manufacturing challenges all three of these assumptions. It requires:
- Machines that expose their capabilities in a standardized, technology-agnostic way.
- Software systems that can discover and interpret those capabilities dynamically.
- Communication protocols that work across heterogeneous equipment without custom integration.

This is exactly the problem domain addressed by this project.

### 4.5 Reference Architectural Model Industrie 4.0 (RAMI 4.0)

**RAMI 4.0** (Reference Architectural Model for Industrie 4.0) is a three-dimensional framework that maps the key aspects of Industry 4.0 along three axes:
- **Layers**: from asset to information system (Asset, Integration, Communication, Information, Functional, Business).
- **Life Cycle & Value Stream**: engineering stages from type to instance.
- **Hierarchy Levels**: from individual components to the connected world.

Within RAMI 4.0, the **I4.0 Component** is the fundamental entity: a physical asset combined with its digital representation (the Asset Administration Shell). This is the conceptual origin of the AAS standard.

---

## 5. Digital Twins in Manufacturing

### 5.1 The Digital Twin Concept

The concept of a **Digital Twin** was introduced by Dr. Michael Grieves at the University of Michigan in 2002, originally in the context of Product Lifecycle Management (PLM). The core idea is simple but powerful: create a digital model of a physical object that mirrors its real-world counterpart throughout its lifecycle.

A digital twin has three essential components:
1. **Physical entity**: The real-world object — a machine, a product, a process, or even a human.
2. **Digital model**: The virtual representation, containing data, parameters, states, and descriptions of the physical entity.
3. **Connection**: The data link that keeps the physical and digital entities synchronized — sensor readings, actuator commands, status updates.

### 5.2 Types of Digital Twins

Digital twins can be classified by their relationship with the physical entity and their functional capability:

| Type | Description | Example |
|---|---|---|
| **Digital Twin Prototype** | A digital model created before the physical entity, used for design and simulation. | CAD model of a new machine design |
| **Digital Twin Instance** | A digital model of a specific physical instance, synchronized in real time. | The digital twin of machine #42 on the production floor |
| **Digital Twin Aggregate** | A collection of digital twin instances, used for fleet-level analytics. | All machines of a given model across a plant |
| **AAS Type 1** | Passive digital twin: documentation only, not connected. | A digital product manual |
| **AAS Type 2** | Reactive digital twin: responds to queries in real time. | A machine exposing sensor data via OPC UA |
| **AAS Type 3** | Proactive digital twin: can initiate communication and autonomous actions. | A SMIA agent that negotiates capabilities |

This project works exclusively with **AAS Type 3** digital twins: entities that are not merely passive data repositories but active participants in the manufacturing system.

### 5.3 Why Digital Twins Enable Flexibility

Traditional integration between machines and software systems requires custom adapters for each asset: a specific driver, a specific API, a specific data format. When a new machine is added to the plant, a new integration project is required.

Digital twins break this pattern by providing a **standardized interface layer**. If every asset exposes its data, capabilities, and interfaces through a standardized digital twin, software systems — agents, MES, ERP, analytics platforms — can interact with any asset through the same standard interface, without knowing anything about the asset's internal implementation.

This is analogous to how web standards (HTTP, HTML, JSON) allow any browser to interact with any web server regardless of the underlying technology stack. AAS aims to provide the same role for manufacturing assets.

---

## 6. Asset Administration Shell (AAS)

### 6.1 Overview

The **Asset Administration Shell (AAS)** is the digital twin standard defined by the Industrial Digital Twin Association (IDTA) and Plattform Industrie 4.0. It provides a standardized way to represent any physical or logical asset (a machine, a component, a process, a software system) as a structured, interoperable digital entity.

Formally, the AAS is defined in the specification document "Details of the Asset Administration Shell" (IDTA standard), currently at version 3.0. The standard defines:
- The **metamodel** (data structures that describe how an AAS is organized).
- The **serialization formats** (XML, JSON, RDF — stored in AASX packages).
- The **API** (how an AAS exposes its data via HTTP).
- The **submodel templates** (standardized structures for common use cases, like nameplate, document management, or asset interfaces).

### 6.2 AAS Metamodel

The AAS metamodel defines the building blocks of a digital twin. The key elements are:

#### 6.2.1 AssetAdministrationShell

The top-level container for a digital twin. It has a globally unique identifier and references a set of submodels. One AAS represents one asset.

Example:
```
AssetAdministrationShell
  idShort:  LEGO_factory
  id:       urn:uuid:6475_0111_2062_9689
  assetKind: Instance
  submodels: [ref:AssetInterfacesDescription, ref:CapabilitiesAndSkills, ...]
```

#### 6.2.2 Submodel

A structured group of related information about an asset. Submodels are the primary organizational unit within an AAS. Each submodel has:
- A unique identifier.
- A `semanticId` linking it to a standard or ontology (enabling interoperability).
- A collection of `SubmodelElements`.

Standard submodel templates are published by IDTA for common use cases (e.g., "Technical Data", "Digital Nameplate", "Asset Interfaces Description"). Custom submodels can also be defined.

#### 6.2.3 SubmodelElement

The basic data unit within a submodel. Multiple types exist:

| Type | Description | Example |
|---|---|---|
| **Property** | A single typed value. | `base: "http://192.168.155.10:1880"` |
| **SubmodelElementCollection (SMC)** | A named group of SubmodelElements (like a folder). | `EndpointMetadata { base, contentType, ... }` |
| **RelationshipElement** | A directed relationship between two elements within the model. | `Capability_PickPiece → Skill_PickPiece` |
| **ReferenceElement** | A reference to another element. | Reference to an AAS in another package |
| **Blob** | Binary data (e.g., images, documents). | A PDF datasheet |
| **File** | A reference to a file within the AASX package. | An embedded OWL ontology file |
| **Operation** | A callable function with input/output parameters. | Remote procedure call |
| **MultiLanguageProperty** | A property with multiple language translations. | Product name in 5 languages |

#### 6.2.4 SemanticId

Every AAS element can (and should) carry a `semanticId`: a URI that links the element to an external standard, ontology, or specification. This is the mechanism that enables **semantic interoperability**: two systems can agree on the meaning of a data field if they share the same `semanticId`.

For example, a Property named `base` with semanticId `https://www.w3.org/2019/wot/td#baseURI` is unambiguously identified as the W3C Web of Things base URL property — regardless of what the field is named in a particular implementation.

#### 6.2.5 Qualifier

A **Qualifier** is a metadata annotation that can be attached to any `SubmodelElement` in the AAS metamodel (Part 1, §10.2.3). It is the AAS extension mechanism for expressing attributes of an element that cannot be captured by its element type alone.

##### Structure of a Qualifier

A Qualifier has three principal fields:

| Field | Type | Role |
|---|---|---|
| `type` | string | A human-readable label identifying the qualifier (e.g., `"SkillImplementationType"`, `"hasLifecycle"`) |
| `value` | string | The actual data value of the attribute (e.g., `"OPERATION"`, `"OFFER"`) |
| `semanticId` | ExternalReference / GlobalReference | An IRI that links this qualifier to a concept in an external ontology or standard |

There is also a `kind` field that indicates the qualifier's role in the data model:
- `ConceptQualifier`: the qualifier defines the *concept* the element belongs to — it is part of the element's type definition.
- `TemplateQualifier`: the qualifier appears in a template definition and restricts valid instances.
- `ValueQualifier`: the qualifier adds a runtime measurement or state value.

In the SMIA CSS context, all CSS-related qualifiers use `ConceptQualifier` kind — they define what kind of CSS concept the element represents.

##### Why Qualifiers Are Needed: The Expressiveness Gap

The AAS standard defines a fixed set of element types (`Property`, `SubmodelElementCollection`, `RelationshipElement`, etc.). These types define *structural* roles but carry no domain-specific semantic meaning. When representing a CSS concept such as a `Skill`, the AAS element type alone (`Property`) only tells a machine "this is a data field." It cannot express "this data field has a value of type `OperationImplementationType` from the CSS ontology, and that type has exactly four allowed values."

Qualifiers fill this expressiveness gap without modifying the AAS metamodel itself. They allow any AAS element to carry additional semantic attributes — including enumerated, typed, and ontology-linked values — in a standardized way.

##### The Two-Level SemanticId Architecture

This is one of the most nuanced aspects of the AAS + OWL integration:

**Level 1 — Element `semanticId`:** Identifies what **OWL class** this element is an instance of.

For example, `Skill_PickPiece` is a `Property` element with `semanticId = http://www.w3id.org/hsu-aut/css#Skill`. This tells SMIA: "this AAS Property element represents an individual of the OWL class `Skill`."

**Level 2 — Qualifier `semanticId`:** Identifies which **OWL DatatypeProperty** this qualifier carries the value of.

For example, the qualifier on `Skill_PickPiece` with `type = "SkillImplementationType"` and `value = "OPERATION"` carries `semanticId = http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`. This tells SMIA: "this qualifier carries the value of the OWL DatatypeProperty `hasImplementationType` defined in the CSS-SMIA ontology."

These two levels are completely independent:

```
AAS model element                         OWL ontology
─────────────────────────────────────     ──────────────────────────────────────
Property "Skill_PickPiece"
  semanticId: css#Skill              →    owl:Class "Skill"
  Qualifier:
    type: "SkillImplementationType"
    value: "OPERATION"
    semanticId: css-smia#hasImpl…    →    owl:DatatypeProperty "hasImplementationType"
                                              domain: Skill
                                              range: {OPERATION, STATE, TRIGGER, FUNCTIONBLOCK}
```

In OWL terms: a `Skill` **individual** has a data property `hasImplementationType` with value `"OPERATION"`. In AAS terms: a `Property` element (representing that individual) has an attached `Qualifier` carrying that data property's value. The qualifier's `semanticId` is the unambiguous, machine-readable **bridge** between the flat AAS world and the structured OWL world.

##### The Bridge Mechanism in SMIA

SMIA exploits this bridge during the **Booting state** (Track 2 of self-configuration, `init_aas_model_behaviour.py:188-204`):

1. For each AAS SubmodelElement whose `semanticId` matches a CSS OWL class IRI (e.g., `Skill`), SMIA creates a Python OWL ontology instance via `owlready2`.
2. The OWL instance, on creation (`capability_skill_module.py:66-86`), scans all `owl:DatatypeProperty` declarations in `CSS-ontology-smia.owl` and collects those whose `rdfs:domain` includes its class. For a `Skill` instance, this includes `hasImplementationType` (IRI: `css-smia#hasImplementationType`).
3. SMIA then calls `get_qualifier_value_by_semantic_id(iri)` on the AAS element — searching all its qualifiers for one whose `semanticId` matches `css-smia#hasImplementationType`.
4. The found value (`"OPERATION"`) is stored on the OWL instance via `set_data_property_value()`.
5. The OWL instance is now a fully populated Python representation of that CSS individual, with all ontology-linked attributes set from the AAS.

This population step is what enables the runtime OWL graph to be complete: capability → skill → skill_interface → asset_connection.

##### Two Independent Lookup Mechanisms

SMIA reads `SkillImplementationType` through two independent code paths:

| Mechanism | Method | Lookup by | When used | Works without qualifier semanticId? |
|---|---|---|---|---|
| 1 — Type-based | `get_qualifier_by_type('SkillImplementationType')` | `type` string | Capability request validation | **Yes** |
| 2 — SemanticId-based | `get_qualifier_value_by_semantic_id(iri)` | `semanticId` IRI | Boot-time OWL instance population | **No** → error |

Mechanism 1 is used by `check_cap_skill_ontology_qualifier_for_skills()` in `extended_submodel.py:99` — called when a capability request arrives to validate the skill exists and has a valid implementation type. This path works correctly without a qualifier semanticId.

Mechanism 2 is used by `add_ontology_required_information()` in `init_aas_model_behaviour.py:198-202` — called during boot for every CSS OWL instance. If no qualifier carries the `hasImplementationType` IRI as its `semanticId`, `AASModelReadingError` is raised, the OWL instance is partially initialized, and any downstream code depending on the OWL graph (such as `HandleNegotiationBehaviour.get_neg_value_with_criteria()`) crashes.

**Practical implication:** A `SkillImplementationType` qualifier without a `semanticId` is sufficient for single-machine execution (Case 0, direct capability dispatch). It is insufficient for multi-agent negotiation (Case 1+), where the FIPA-CNP path depends on the fully populated OWL graph.

##### Qualifier SemanticId vs. ConceptDescription

A common confusion is whether the qualifier's `semanticId` needs to be backed by a `ConceptDescription` element inside the AASX package. The answer is **no** — as long as the semanticId is an `ExternalReference` (GlobalReference) pointing to an IRI in an external standard or ontology. The `ConceptDescription` element exists to embed documentation about a concept *inside* the package for self-contained use; it is optional and not required for SMIA's machine-readable IRI lookups.

##### The Three CSS Qualifiers in This Project

| Qualifier `type` | OWL DatatypeProperty IRI | Domain OWL class | Values | SemanticId always required? |
|---|---|---|---|---|
| `hasLifecycle` | `css-smia#hasLifecycle` | `css#Capability` | `OFFER`, `ASSURANCE`, `REQUIREMENT` | Yes (in official preset) |
| `SkillImplementationType` | `css-smia#hasImplementationType` | `css#Skill` | `OPERATION`, `STATE`, `TRIGGER`, `FUNCTIONBLOCK` | Only for multi-agent (Case 1+) |
| `hasCondition` | `css-smia#hasCondition` | `css#CapabilityConstraint` | `PRECONDITION`, `POSTCONDITION`, `INVARIANT` | Yes (in official preset) |

Note the naming asymmetry on the second qualifier: the `type` string is `"SkillImplementationType"` (SMIA convention), but the OWL DatatypeProperty is named `hasImplementationType` (ontology convention). This is because the `type` string is a human-readable label defined by the preset file author, while the `semanticId` IRI is the authoritative, machine-readable reference from the OWL ontology.

The official preset file (`SMIA-css-qualifier-presets.json`) defines `SkillImplementationType` with `semanticId: null`. This was written for single-machine use cases. For multi-agent deployments, the semanticId must be manually added as `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` (GlobalReference, ExternalReference). This IRI is defined at line 429 of `CSS-ontology-smia.owl` as an `owl:DatatypeProperty` by the SMIA team (UPV/EHU).

### 6.3 AAS Types

AAS are classified into three types based on their operational capabilities:

| Type | Name | Description | Communication |
|---|---|---|---|
| **Type 1** | Documentation Twin | Static, offline description. No connectivity to physical asset. | None |
| **Type 2** | Reactive Twin | Online, responds to queries. Passive — waits for requests. | Synchronous API calls |
| **Type 3** | Proactive Twin | Online, autonomous. Can initiate communication, negotiate, execute processes. | Asynchronous, event-driven |

This project implements **Type 3** AAS via SMIA agents: agents that proactively respond to capability requests, reason about their AAS model, and autonomously call physical services.

### 6.4 AASX Package Format

The AAS is persisted in **AASX files**: ZIP archives with a specific internal structure.

```
MyAsset.aasx (ZIP)
├── [Content_Types].xml           # OOXML content type declarations
├── _rels/.rels                   # OPC relationships
├── aasx/
│   └── MyAsset/
│       └── MyAsset.aas.xml       # The AAS model (XML serialization)
├── aasx/                         # Supplementary files embedded in the package
│   ├── CSS-ontology-smia.owl     # OWL ontology (embedded)
│   └── smia-initialization.properties
└── ...
```

The `.aas.xml` file contains the full AAS model in the AAS metamodel XML serialization. The AASX package can also contain supplementary files (documents, ontologies, images) referenced from within the AAS model.

The **AASX Package Explorer** is an open-source Windows tool provided by the IDTA for authoring and inspecting AASX files. It provides a graphical interface to create AAS shells, add submodels, define elements, set semantic IDs, and embed files.

### 6.5 Key Submodel Standards Used in This Project

#### AID — Asset Interfaces Description (IDTA 02017)

The **Asset Interfaces Description (AID)** submodel standard defines how to describe the communication interfaces of a manufacturing asset within its AAS. It is based on the **W3C Web of Things (WoT) Thing Description** specification, adapted for AAS.

An AID submodel contains:
- **Interface**: A named communication interface (e.g., `InterfaceHTTP`).
- **EndpointMetadata**: Connection parameters (base URL, content type, authentication).
- **InteractionMetadata**: Supported interactions — **Properties** (readable values), **Actions** (callable operations), and **Events** (subscribable notifications).
- **Forms**: The specific protocol binding for each interaction (URL path, HTTP method).
- **Input/Output schemas**: The data types expected and returned.

The AID standard decouples what an asset *can do* (an HTTP action) from the specific URL — enabling the endpoint to change (e.g., different IP address) without modifying the capability model.

---

## 7. Capability-Skill-Service (CSS) Model

### 7.1 Overview

The **Capability-Skill-Service (CSS)** model is a conceptual framework originally developed by Plattform Industrie 4.0 that separates the description of manufacturing functions into three distinct abstraction levels. It was designed specifically to enable flexible manufacturing by breaking the tight coupling between production requests and specific machine implementations.

The model was formalized as an **OWL ontology** (see Section 8) to enable machine-readable, semantically rich descriptions of these concepts. The **CaSkade-Automation** project provides an open-source OWL implementation (CSS-ontology v1.0.1, October 2024) at `https://github.com/CaSkade-Automation/CSS` with the base IRI `https://w3id.org/hsu-aut/css`. This is the base ontology extended by SMIA (paper §3.2, §4.1.2).

### 7.2 The Three Abstraction Levels

#### 7.2.1 Capability

A **Capability** describes *what* a manufacturing function achieves at a functional, implementation-independent level. It answers the question: "What can this asset do?"

Key properties:
- Capabilities are **abstract**: they do not specify how the function is implemented.
- Capabilities can have **constraints**: pre-conditions, post-conditions, and invariants that define the operating envelope.
- Capabilities can have **parameters**: inputs that the requester must provide.
- Capabilities belong to a **lifecycle**: `OFFER` (the capability is available/offered by this asset), `ASSURANCE` (offered with a quality guarantee), or `REQUIREMENT` (this capability is required from another agent) (paper §4.1.2).
- Capabilities can be **restricted** by `CapabilityConstraint` objects via the `isRestrictedBy` property — pre/post-conditions defining operating bounds (paper Fig. 4).

Example: `Capability_PickPiece` — the ability to pick a piece from a warehouse slot. This is independent of whether the pick is performed by a robotic arm, a conveyor, or a specific crane mechanism. In Case 0, this capability is offered by the **warehouse crane (Hochregallager)** of the fischertechnik Training Factory Industry 4.0 24V. Note: this capability does *not* apply to the central crane with vacuum suction cup (ventose), which is a separate component of the same factory model.

In an AAS model, a Capability is represented as a `SubmodelElementCollection` whose `semanticId` identifies which CSS capability subclass it belongs to. SMIA defines two subclasses (css_ontology_utils.py:201-202):

- `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` — a capability **of a physical machine** (e.g., a warehouse crane's ability to pick a piece). Execution is delegated to a physical asset through an AID-described HTTP/MQTT/OPC-UA interface. Used in Case 0 for `Capability_PickPiece` and `Capability_PlacePiece` on the fischertechnik factory machines.
- `http://www.w3id.org/upv-ehu/gcis/css-smia#AgentCapability` — a capability **of the software agent itself** (e.g., an orchestrator's ability to coordinate multiple machines). Execution is handled by a SPADE behaviour registered on the agent; no AID interface is required. Used in Case 1 for the orchestrator's `Capability_PickPiece`.

The distinction is not optional: SMIA's `state_running.py` explicitly queries only `AgentCapability` instances when looking for negotiation and agent-level behaviours. Placing an orchestration capability under `AssetCapability` is semantically incorrect and will mislead SMIA's capability classification logic.

#### 7.2.2 Skill

A **Skill** describes *how* a capability is implemented: the concrete mechanism through which the capability is executed. It answers the question: "How does this asset perform that function?"

Key properties:
- Skills are **concrete**: they are tied to a specific implementation.
- Each Skill **realizes** one or more Capabilities (via the `isRealizedBy` object property).
- Skills have an **implementation type**: e.g., `OPERATION` (a callable service), `PROGRAM` (a program to be executed), `WORKFLOW` (a sequence of sub-skills).
- Skills expose themselves through a **Skill Interface**.

Example: `Skill_PickPiece` — calls the Node-RED HTTP endpoint `/smia/lego/pick` with a POST request.

In an AAS model, a Skill is represented as a `Property` element (see Section 14 for the critical reason) with `semanticId: http://www.w3id.org/hsu-aut/css#Skill`.

#### 7.2.3 Service (Skill Interface)

A **Skill Interface** (the "Service" in CSS) describes how a skill is *accessed*: the interface through which it can be invoked. In SMIA, this is represented by the reference to a specific action in the AID submodel.

In the CSS ontology, the object property `accessibleThroughAssetService` links a Skill to its interface in the AID submodel.

### 7.3 Relationships Between CSS Concepts

The CSS model defines five key object properties (paper Fig. 4):

| Object Property | Direction | Meaning |
|---|---|---|
| `isRealizedBy` | Capability → Skill | This capability is implemented by this skill |
| `isRestrictedBy` | Capability → CapabilityConstraint | This capability is bounded by this constraint |
| `accessibleThrough` | Skill → SkillInterface | **Base CSS standard** (CaSkade): skill is accessible through this interface |
| `accessibleThroughAssetService` | Skill → SkillInterface | **SMIA extension**: skill executes via a **physical asset** service (HTTP) ← Case 0 |
| `accessibleThroughAgentService` | Skill → SkillInterface | **SMIA extension**: skill executes via an **agent-internal** service (Python method) |
| `hasParameter` | Skill → SkillParameter | This skill has this input/output parameter |

The base CSS standard (CaSkade, `http://www.w3id.org/hsu-aut/css`) defines `accessibleThrough` as the canonical property linking a Skill to its SkillInterface. SMIA adds two sub-properties as framework extensions (`http://www.w3id.org/upv-ehu/gcis/css-smia`): `accessibleThroughAssetService` for physical HTTP execution and `accessibleThroughAgentService` for agent-internal Python execution. Both SMIA sub-properties inherit the semantics of the base `accessibleThrough` property. Case 0 uses the SMIA `accessibleThroughAssetService` extension for the pick/place skills.

The CSS ontology also defines `isRealizedBySkill` as a sub-property of `isRealizedBy` (with domain `Capability` and range `Skill`). It is more specific than the base property, explicitly constraining the range to `Skill` elements only. However, the SMIA framework processes AAS `RelationshipElement` semanticIds using **exact string comparison** against a fixed list of IRIs (`CSS_ONTOLOGY_OBJECT_PROPERTIES_IRIS` in `css_ontology_utils.py`). Only `http://www.w3id.org/hsu-aut/css#isRealizedBy` is in that list — `#isRealizedBySkill` is not, even though it is ontologically valid. Using `#isRealizedBySkill` in an AASX causes SMIA to silently skip those relationships during self-configuration (Track 3), and causes the operator GUI to display zero capabilities and zero skills for that agent. The correct IRI to use in AAS RelationshipElement semanticIds is always `http://www.w3id.org/hsu-aut/css#isRealizedBy`.

### 7.4 Why CSS Enables Flexibility

Without the CSS model, a system that wants to execute a manufacturing function must know in advance:
- Which specific machine to call.
- What specific API endpoint to use.
- What specific protocol and data format to use.

With the CSS model, a system only needs to know:
- What **capability** it needs (e.g., `PickPiece`).

The CSS reasoning chain handles the rest:
1. Find an asset that OFFERs `PickPiece`.
2. Determine which Skill realizes that capability (`isRealizedBy`).
3. Find the Skill Interface through which the Skill is accessible (`accessibleThroughAssetService`).
4. Read the interface details from the AID submodel (URL, method, parameters).
5. Execute the call.

This chain is entirely driven by the information in the AAS model — no hard-coded logic required.

### 7.5 CSS Ontology in SMIA

SMIA uses a customized CSS OWL ontology (`CSS-ontology-smia.owl`) that (paper §4.1.2):
- Extends the **CaSkade-Automation CSS-ontology v1.0.1** base (`http://www.w3id.org/hsu-aut/css`).
- Adds SMIA-specific classes: `css-smia:AssetCapability` (physical machine capabilities) and `css-smia:AgentCapability` (agent software capabilities).
- Adds SMIA-specific object properties: `accessibleThroughAssetService` (HTTP execution) and `accessibleThroughAgentService` (agent-internal execution).
- Is embedded directly in the AASX package (`aasx/CSS-ontology-smia.owl`) so that each asset's digital twin is entirely self-contained.
- Extended ontology IRI: `http://www.w3id.org/upv-ehu/gcis/css-smia`, W3ID: `https://w3id.org/upv-ehu/gcis/css-smia/`

The key class hierarchy in the SMIA CSS ontology:

```
owl:Thing
├── Capability
│   ├── AgentCapability    (capability offered by a software agent) ← used in Case 1 orchestrator
│   └── AssetCapability    (capability offered by a physical asset) ← used in Case 0 machines
├── Skill                  (concrete implementation of a capability)
├── SkillInterface         (how a skill is accessed)
├── SkillParameter         (input/output of a capability or skill)
└── StateMachine           (state-based skill execution model)
```

---

## 8. Semantic Technologies: Ontologies and OWL

### 8.1 What is an Ontology?

In computer science, an **ontology** is a formal, machine-readable representation of a body of knowledge about a domain. It defines:
- **Classes**: Categories or types of things (e.g., `Capability`, `Skill`, `Machine`).
- **Individuals**: Specific instances of classes (e.g., `Capability_PickPiece` is an individual of `AssetCapability`).
- **Object Properties**: Relationships between individuals (e.g., `isRealizedBy` relates a `Capability` to a `Skill`).
- **Data Properties**: Attributes of individuals with literal values (e.g., `hasName: "PickPiece"`).
- **Axioms**: Logical statements that constrain the interpretation (e.g., "every Skill must be related to at least one SkillInterface").

Ontologies differ from databases or schemas in that they support **reasoning**: a computer can draw new conclusions from the facts stated in an ontology using logical inference. For example, if the ontology states that `X isRealizedBy Y` and `Y accessibleThroughAssetService Z`, an ontology reasoner can infer that `X` is indirectly accessible through `Z`.

### 8.2 OWL: Web Ontology Language

**OWL** (Web Ontology Language) is the standard language for defining ontologies on the Web, developed by the W3C. It is built on:
- **RDF** (Resource Description Framework): A graph-based data model where knowledge is expressed as triples: `subject — predicate — object`.
- **RDFS** (RDF Schema): Extends RDF with classes, properties, and basic hierarchy.
- **OWL**: Extends RDFS with expressive logical constructs (cardinality, disjointness, equivalence, transitivity, etc.).

OWL ontologies are stored in files with the `.owl` extension, usually serialized in RDF/XML format. The CSS ontology used in this project (`CSS-ontology-smia.owl`) is an OWL 2 file.

### 8.3 Semantic Identifiers (IRIs)

In semantic web technologies, every class, property, and individual is identified by an **IRI** (Internationalized Resource Identifier) — essentially a URL that globally and uniquely identifies the concept.

For example:
- The `Skill` class is identified by: `http://www.w3id.org/hsu-aut/css#Skill`
- The `isRealizedBy` property is identified by: `http://www.w3id.org/hsu-aut/css#isRealizedBy`

These IRIs are used as `semanticId` values in AAS elements to link them to the ontology. When SMIA reads the AAS model and encounters an element with `semanticId: http://www.w3id.org/hsu-aut/css#Skill`, it knows unambiguously that this element represents a CSS Skill, regardless of what the element is named (`idShort`).

**IRI correctness and case-sensitivity are critical.** SMIA resolves IRIs using exact string equality — not semantic equivalence. A wrong property name or a single wrong character causes a lookup to fail silently.

**Standard vs. extension properties:** The CaSkade CSS ontology (`http://www.w3id.org/hsu-aut/css`) defines `accessibleThrough` as the canonical property linking a Skill to its SkillInterface. SMIA adds two sub-properties as framework-specific extensions (`http://www.w3id.org/upv-ehu/gcis/css-smia`): `accessibleThroughAssetService` (physical HTTP execution) and `accessibleThroughAgentService` (agent-internal Python execution). SMIA processes all three IRIs independently during AAS initialization (each is a separate constant in `css_ontology_utils.py`) and `get_associated_skill_interface_instances()` chains all three — so any of the three works at runtime.

For AAS authoring, **the CSS-standard-compliant choice is `http://www.w3id.org/hsu-aut/css#accessibleThrough`** — it is the canonical property from the primary CaSkade specification and makes the AASX independent of any particular framework extension. The SMIA sub-properties are valid alternatives but are specific to the SMIA implementation.

**Silent failure example:** If a machine AASX uses `#AccessibleThroughAgentService` (uppercase 'A'), SMIA's `AASInitializationBehaviour` cannot match the IRI, the SkillInterface is never linked to the skill, and the negotiation score defaults to 0.0 with no clear error message. This was identified during a full AAS inspection for Case 1 and required correcting the semanticId in all three machine AASX files.

### 8.4 owlready2: OWL Processing in Python

SMIA uses **owlready2**, a Python library for loading, navigating, and reasoning with OWL ontologies. Through owlready2, SMIA can:
- Load the embedded CSS ontology from the AASX package.
- Parse AAS elements and classify them as ontology individuals (e.g., recognize `Capability_PickPiece` of a machine as an `AssetCapability` individual, or `Capability_PickPiece` of the orchestrator as an `AgentCapability` individual).
- Navigate object properties to find the skill that realizes a capability, and the interface through which that skill is accessible.

### 8.5 Semantic Interoperability

The key benefit of semantic technologies in manufacturing is **interoperability**. Two systems that independently know the CSS ontology — even if they have never communicated before — can exchange information about capabilities and skills and immediately understand each other, because they share the same formal definitions.

This is what enables a new machine, with a new AAS model, to be added to the SMIA ecosystem and immediately be discoverable by the operator agent: the operator agent does not need to be re-programmed; it simply reads the AAS and interprets the CSS semantics.

---

## 9. Multi-Agent Systems and SPADE

### 9.1 Agents and Multi-Agent Systems

An **agent** in computer science is a software entity that:
- Operates **autonomously** — makes decisions without requiring constant human direction.
- Is **situated** in an environment — perceives its environment and acts upon it.
- Is **reactive** — responds to changes in its environment.
- Is **proactive** — takes initiative to achieve its goals.
- Is **social** — communicates and interacts with other agents.

A **Multi-Agent System (MAS)** is a collection of agents that interact with each other and with their environment to solve problems that are beyond the capability or efficiency of any single agent. MAS is a subfield of Artificial Intelligence and Distributed Systems.

In the context of flexible manufacturing, MAS is the natural paradigm: each manufacturing asset (machine, AGV, operator) is represented by an agent. Agents discover each other's capabilities, negotiate the allocation of production tasks, and coordinate execution autonomously.

### 9.2 FIPA-ACL: Agent Communication Language

**FIPA-ACL** (Foundation for Intelligent Physical Agents — Agent Communication Language) is a standard for structured communication between software agents. It defines:
- A set of **performatives** (message types): `REQUEST`, `PROPOSE`, `ACCEPT`, `REFUSE`, `INFORM`, `QUERY-IF`, etc.
- A standard **message structure**: sender, receiver, performative, content, conversation-id, etc.

FIPA-ACL is analogous to HTTP in web systems: it provides a standard protocol for agents to make requests, receive responses, and engage in multi-round conversations (dialogues).

In SMIA, FIPA-ACL is the communication protocol used between the operator agent and the SMIA agent:
1. Operator sends: `REQUEST execute Capability_PickPiece`.
2. SMIA receives, processes, executes, and replies: `INFORM status=ok, payload=...`.

### 9.3 XMPP: The Transport Layer

**XMPP** (Extensible Messaging and Presence Protocol, originally "Jabber") is an open standard for real-time messaging, originally designed for instant messaging applications. FIPA agents using XMPP as transport wrap their FIPA-ACL messages in XMPP stanzas.

XMPP provides:
- **Addressing**: Every agent has a JID (Jabber ID) in the form `agent@domain` (similar to an email address).
- **Presence**: Agents can publish their online/offline status.
- **Federated messaging**: Agents on different XMPP servers can communicate if the servers are peered.
- **Security**: TLS encryption and SASL authentication.

In this project, **ejabberd** is used as the XMPP server. ejabberd is a mature, production-grade open-source XMPP server written in Erlang. The SMIA agent JID is `SMIA_agent@ejabberd` and the operator agent JID is `operator001@ejabberd`.

### 9.4 SPADE: Smart Python Agent Development Environment

**SPADE** (Smart Python Agent Development Environment) is an open-source Python framework for building multi-agent systems using XMPP as the transport layer. SPADE provides:
- An `Agent` base class that handles XMPP connection management.
- A `Behaviour` abstraction for defining agent logic as reusable, composable units:
  - `OneShotBehaviour`: Executes once.
  - `CyclicBehaviour`: Executes repeatedly in a loop.
  - `FSMBehaviour`: A Finite State Machine with explicit state transitions.
  - `PeriodicBehaviour`: Executes at regular intervals.
- Message templates for filtering incoming messages.
- Presence management and discovery.

SMIA is built on top of SPADE. Every SMIA agent is a SPADE agent that uses behaviours to implement the AAS lifecycle (booting, running, idle, stopping) and to handle capability requests.

### 9.5 Agent Lifecycle in SMIA

SMIA implements a Finite State Machine (FSM) with four states:

```
[StateBooting]
    |
    | Successful initialization
    v
[StateRunning]  ←── Handles ongoing messages and capability requests
    |                                         ↑
    | Non-operational asset                   | Asset operational again
    v                                         |
[StateIdle]  ────────────────────────────────┘
    |
    | Shutdown signal (from any state)
    v
[StateStopping]
```

**StateBooting** performs:
1. Load and parse the AASX package from the configured folder.
2. Find the correct AAS shell (filtered by `AAS_ID`).
3. Load the CSS ontology (from the embedded `.owl` file or from a separate path).
4. Run `InitAASModelBehaviour`: parse all submodels, classify elements using ontology semantics, discover capabilities, skills, and interfaces.
5. Establish all asset connections (HTTP interfaces from the AID submodel).
6. Transition to `StateRunning` when all initialization succeeds.

**StateRunning** listens for incoming FIPA-ACL messages and dispatches them to appropriate handlers:
- Capability check requests.
- Capability execution requests.
- Negotiation messages.

---

## 10. Industrial Communication Protocols

### 10.1 MQTT: Message Queuing Telemetry Transport

**MQTT** (Message Queuing Telemetry Transport) is a lightweight publish-subscribe messaging protocol designed for constrained devices and low-bandwidth, high-latency networks. It was originally developed by IBM and is now an ISO standard (ISO/IEC 20922:2016) and an OASIS standard.

**Core concepts:**

- **Broker**: A central server that receives all messages and routes them to subscribers. In this project: Mosquitto broker on the DIDA central machine.
- **Publisher**: A client that sends messages to the broker. In this project: Node-RED, after receiving the HTTP request from SMIA.
- **Subscriber**: A client that receives messages matching a subscribed topic. In this project: the fischertechnik/PLC Windows machine.
- **Topic**: A UTF-8 string that categorizes messages. In this project: `vicom/61/piso_0/lab/lego/commands`.
- **QoS** (Quality of Service): Three levels:
  - `0`: At most once (fire and forget).
  - `1`: At least once (guaranteed delivery, possible duplicates).
  - `2`: Exactly once (guaranteed, no duplicates).
  - This project uses QoS 1.

MQTT is widely used in industrial automation because it is lightweight, works well over unreliable networks, and decouples producers from consumers — the publisher does not need to know who is subscribed to a topic.

### 10.2 HTTP/REST: The Web Standard

**HTTP** (Hypertext Transfer Protocol) is the foundation protocol of the World Wide Web. **REST** (Representational State Transfer) is an architectural style for building APIs using HTTP that defines:
- **Resources** identified by URLs.
- Standard **methods**: GET (read), POST (create/trigger), PUT (update), DELETE (remove).
- Stateless communication: each request contains all the information needed to process it.
- Standard **data formats**: typically JSON.

In this project, SMIA calls Node-RED via a **POST** request to trigger the physical action:
```
POST http://192.168.155.10:1880/smia/lego/pick
Content-Type: application/json
Body: {"color": "red", "position": 0}
```

The URL and method are not hard-coded in SMIA; they are read from the AID submodel at runtime.

### 10.3 Node-RED: Flow-Based Programming

**Node-RED** is an open-source, browser-based visual programming tool for wiring together hardware devices, APIs, and online services. It uses a **flow-based programming** model where:
- **Nodes** perform specific functions (HTTP listener, function, MQTT publisher, etc.).
- **Wires** connect nodes, passing `msg` objects from one to the next.
- **Flows** are collections of connected nodes that define a processing pipeline.

Node-RED is widely used in industrial IoT because it makes it easy to bridge different protocols (HTTP, MQTT, OPC UA, Modbus, etc.) without writing code. Flows are defined visually in a web browser and can be exported/imported as JSON files.

In this project, Node-RED runs on the DIDA central machine and serves as the **protocol bridge** between SMIA's HTTP world and the fischertechnik machine's MQTT world.

### 10.4 Communication Stack Summary

```
[SMIA Agent] ←─── FIPA-ACL over XMPP ───→ [SMIA Operator Agent]
     │
     │ HTTP POST (reads endpoint from AAS model)
     ▼
[Node-RED — DIDA Central]
     │
     │ MQTT publish (QoS 1)
     ▼
[Mosquitto Broker — Central]
     │
     │ MQTT bridge
     ▼
[Mosquitto Broker — fischertechnik Machine]
     │
     │ MQTT subscription
     ▼
[fischertechnik Control Software → Warehouse Crane macro]
```

---

## 11. SMIA: Self-configurable Manufacturing Industrial Agents

### 11.1 Overview

**SMIA** (Self-configurable Manufacturing Industrial Agents) is an open-source framework developed at the Control and Systems Integration research group (GCIS) of the University of the Basque Country (UPV/EHU) by Ekaitz Hurtado, Arantzazu Burgos, Aintzane Armentia, and Oskar Casquero. It is published in the *Journal of Industrial Information Integration* (DOI: 10.1016/j.jii.2025.100915) and *Software Impacts* (DOI: 10.1016/j.simpa.2025.100807).

**Dual-layer architecture (paper §3):** SMIA is simultaneously a methodology and a technology:
1. **Methodology layer**: a process for characterizing proactive AAS (Type 3) by enriching AAS element descriptions with CSS ontology IRIs via the standard `semanticId` field.
2. **Technology layer**: a software toolchain that automatically generates executable Digital Twins as FIPA-compliant industrial agents using SPADE, directly from those CSS-enriched AAS descriptions.

The fundamental conceptual separation: *"The AAS is treated as a static, administrative model, while the DT represents its dynamic, operational counterpart"* (paper §3). SMIA agents are not simple wrappers — they are functional DTs that actively interpret standardized descriptions, expose capabilities, communicate with peers, and execute asset services.

SMIA is published as:
- Python package on PyPI: `pip install smia`
- Docker image on DockerHub: `ekhurtado/smia:latest-alpine`
- Open-source code on GitHub: `https://github.com/ekhurtado/SMIA`

### 11.2 Design Requirements (paper Table 1)

SMIA was designed to satisfy eight functional and design requirements derived from the convergence of industrial domain needs, distributed software engineering principles, and standardization recommendations from organizations such as Plattform Industrie 4.0, IDTA, W3C, and IEEE:

| # | Requirement | Justification |
|---|---|---|
| R1 | Compliance with industry integration models | Integrate heterogeneous assets using AAS (IEC 63278) and CSS standards |
| R2 | Automated self-configuration of Digital Twins | Reduce human intervention; align with AAS Type 3 specifications |
| R3 | Integration of physical assets via standard interfaces | Interpret physical and logical asset interfaces via the AID submodel |
| R4 | Adaptability to flexible and reconfigurable architectures | Support runtime reconfiguration using the CSS model |
| R5 | Inclusion in distributed and decentralized systems | Resilience, scalability, and decentralization per Industry 4.0 |
| R6 | P2P communication with I4.0-compliant language | Autonomous cooperation, negotiation, and coordination via FIPA-ACL |
| R7 | Separation between physical asset and Digital Twin | Functional layer remains independent of the asset's hardware specification |
| R8 | Modular and extensible software design | Maintainability and scalability across industrial contexts |

These requirements are satisfied jointly by the combined use of AAS, CSS, FIPA-ACL, SPADE, BaSyx SDK, and OWLready2 — none of the requirements can be satisfied by any one technology alone.

### 11.3 SMIA Components

SMIA's software architecture consists of the following key components:

#### Extended AAS Model (`smia.aas_model`)

SMIA uses **basyx-python-sdk** to parse AASX files. It then extends the parsed AAS objects with additional Python classes that implement CSS ontology concepts:

- `ExtendedCapability`: A SubmodelElementCollection with `semanticId: AssetCapability` or `AgentCapability`.
- `ExtendedSkill`: A Property with `semanticId: Skill`.
- `ExtendedSkillInterface`: An element linked to the AID submodel via `accessibleThroughAssetService`.

This extension is implemented using Python's dynamic class creation (`types.new_class`) and multiple inheritance.

#### CSS Ontology (`smia.css_ontology`)

- `CapabilitySkillOntology`: Manages the OWL ontology loading (via owlready2) and provides methods to query it.
- `CapabilitySkillOntologyInfo`: Constants class containing all CSS IRI strings.

#### Behaviours (`smia.behaviours`, `smia.states`)

- `AASFSMBehaviour`: Top-level Finite State Machine (SPADE FSM behaviour).
- `StateBooting` → `InitAASModelBehaviour`: Loads and parses the AAS + ontology, classifies all elements.
- `StateRunning` → `HandleCapabilityBehaviour`: Handles incoming capability execution requests.
- `StateRunning` → `HandleNegotiationBehaviour`: Handles multi-agent negotiation.

#### Agent Services (`smia.logic.agent_services`)

Provides the `get_asset_connection_class_by_ref()` method that maps a reference to an AID action element to the actual `AssetConnection` object (the HTTP caller).

### 11.4 FSM States and Runtime Lifecycle (paper Fig. 5)

SMIA agents operate according to a four-state Finite State Machine (FSM) implemented as a SPADE `FSMBehaviour`. The states were defined in prior IAMS (Industrial Agent Management System) work and extended by SMIA (shown in green in paper Fig. 5):

| State | Behaviours | SMIA additions |
|---|---|---|
| **Booting** | Boot behavior (SPADE init) | **AAS model init behavior** (self-configuration) |
| **Running** | Service management (CyclicBehaviour) | **Capability management** (HandleCapabilityBehaviour) |
| **Idle** | Idle behavior (asset-derived tasks) | — |
| **Stopping** | Finalization / end behavior | — |

Transitions: Booting →(booted)→ Running →(non-operational asset)→ Idle →(operational)→ Running; any state →(stopping request)→ Stopping →(stopped)→ off.

### 11.5 Self-Configuration Process (paper Fig. 8)

The self-configuration — executed entirely during **Booting** by `InitAASModelBehaviour` — follows three parallel tracks (paper §4.2):

**Track 1 — Asset interface extraction:**
SMIA reads the `AssetInterfacesDescription` submodel via BaSyx SDK, extracts all `Interface` SubmodelElements, and creates an `AssetConnection` instance for each. These objects later serve as the actual HTTP callers.

**Track 2 — CSS-enriched element instantiation:**
For each CSS class IRI defined in the OWL ontology, SMIA retrieves all AAS `SubmodelElements` whose `semanticId` matches that IRI (via BaSyx SDK). If the element passes semantic validation (OWLready2), SMIA creates a corresponding OWL class instance (Python object) from the ontology — binding the AAS element to its CSS semantic interpretation.

**Track 3 — CSS relationship linking:**
For each CSS `ObjectProperty` IRI (e.g., `isRealizedBy`, `accessibleThroughAssetService`), SMIA retrieves all `RelationshipElements` in the AAS with matching `semanticId`. It validates them and uses OWLready2 to link the previously created OWL instances together, building the execution graph: Capability → Skill → SkillInterface → AssetConnection.

The result is an in-memory semantic execution network fully derived from the AAS + OWL model, with zero hard-coded asset knowledge.

### 11.6 Capability Request Execution (paper Fig. 9)

When a FIPA-ACL `REQUEST` message arrives with `ontology = CSSRequest`:

1. `ACLHandlingBehaviour` (CyclicBehaviour) receives it and dispatches to `HandleCapabilityBehaviour` (OneShotBehaviour).
2. The requested capability name and any constraints are validated against the OWL ontology.
3. If no specific skill is specified → SMIA infers the matching skill via `isRealizedBy`.
4. If no interface is specified → SMIA retrieves it via `accessibleThroughAssetService` (or `accessibleThroughAgentService` for agent-side skills).
5. Constraints (if any) are verified before execution.
6. The appropriate executor is invoked: **AssetConnection** for physical HTTP calls; internal Python method for agent services.
7. A FIPA-ACL `INFORM` response is sent with the result, execution status, and an execution timeline for traceability.

### 11.7 FIPA-ACL Message Structure for CSS Requests (paper Fig. 16)

SMIA uses SPADE's `metadata` field to carry FIPA-ACL semantics. A CSS capability request has the following structure:

| Field | Value |
|---|---|
| `to` | Recipient SMIA JID (e.g., `SMIA_agent@ejabberd`) |
| `sender` | Sender JID (e.g., `operator001@ejabberd`) |
| `body` | JSON: `{"skill": "Skill_PickPiece", "constraints": [], "params": {"position": 0}}` |
| `performative` | `Request` |
| `ontology` | `CSSRequest` ← tells SMIA to route to HandleCapabilityBehaviour |

Other ontology values: `SvcRequest` (Functional View service tasks), `Negotiation` (multi-agent coordination).

### 11.8 Extensibility (paper §4.4 + Fig. 10)

SMIA exposes three extension points via the `ExtensibleSMIAAgent` class:

- `add_new_asset_connection(interface_aas_ref, handler)` — add support for new physical protocols (e.g., OPC UA, raw MQTT, serial)
- `add_new_agent_capability(handler)` — add new `AgentCapability` implementations (e.g., learning, planning, negotiation logic)
- `add_new_agent_service(service_id, executable_method)` — add new internal agent services

This extensibility is what enables the future cases (negotiation in Case 1, constraint matching in Case 2) without modifying the SMIA core.

### 11.9 SMIA Operator Agent

The **SMIA Operator** (`ekhurtado/smia-use-cases:latest-operator`) is a specialized SMIA extension that provides a web-based graphical interface for human operators.

**Capabilities:**
- Scans the AASX folder to discover available SMIA agents.
- For each discovered SMIA, sends a FIPA-ACL query to retrieve its available capabilities.
- Presents the capabilities in a web UI (`http://localhost:10000/smia_operator`).
- Allows the operator to select a capability and submit an execution request.
- Displays the result returned by the SMIA agent.

**Communication flow:**
1. Browser → HTTP → SMIA Operator GUI (port 10000).
2. SMIA Operator → XMPP → SMIA Agent (REQUEST performative).
3. SMIA Agent executes skill → HTTP → Node-RED.
4. SMIA Agent → XMPP → SMIA Operator (INFORM performative with result).
5. SMIA Operator → HTTP → Browser (displays result).

---

## 12. Use Case: Case 0 — Flexible Factory Assembly (fischertechnik)

### 12.1 Use Case Context and Justification

**Case 0** is the first validation use case of the SMIA framework within this TFG. It serves as a proof-of-concept that demonstrates the complete pipeline — from standardized digital twin to physical actuation — in a controlled, observable environment.

The physical asset used is the **fischertechnik Training Factory Industry 4.0 24V** (product reference 554868, https://www.fischertechnik.de/es-es/productos/industria-y-universidades/modelos-de-simulacion/554868-training-factory-industry-4-0-24v). This is a professional-grade industrial training and simulation model designed to replicate the key processes of a real Industry 4.0 factory at a 1:1 functional level. The model includes multiple stations: a high-bay warehouse (Hochregallager) with a dedicated crane, a machining center, a conveyor system, a sorting station, and a central service area with a vacuum suction crane (ventose).

**Scope of Case 0:** The capabilities `Capability_PickPiece` and `Capability_PlacePiece` are bound exclusively to the **warehouse crane (Hochregallager crane)**. This crane stores and retrieves workpieces from the high-bay warehouse slots. The **central crane with vacuum suction cup (ventose)** is a separate component of the factory model and is **not** part of Case 0; it is reserved for future use cases.

The justification for Case 0 within the broader research goals:
- **Validates the AAS model**: Confirms that a physical asset's interface can be fully described in an AAS without any asset-specific logic in the software.
- **Validates CSS reasoning**: Confirms that SMIA can autonomously derive the execution path from capability request to HTTP call using only the CSS ontology model.
- **Validates XMPP communication**: Confirms that operator-to-agent communication via FIPA-ACL over XMPP is reliable.
- **Validates protocol bridging**: Confirms that the HTTP-to-MQTT bridge (Node-RED) correctly routes the command to the physical equipment.
- **Establishes the baseline**: Creates a working, documented reference that future cases (more complex multi-agent scenarios, negotiation, planning) can build upon.

### 12.2 Physical Setup

The physical system involves three machines connected in a network:

| Machine | Hardware | Software | Location |
|---|---|---|---|
| **Linux dev machine** | Standard Linux PC | Docker Compose, SMIA | Development lab |
| **DIDA Central** | Industrial PC/server | Node-RED, Mosquitto broker | Vicomtech DII lab central network |
| **fischertechnik/PLC Windows machine** | Windows PC | fischertechnik control software, Mosquitto subscriber | Vicomtech DII lab |

The **fischertechnik Training Factory Industry 4.0 24V** is a professional industrial simulation model. Its relevant components for Case 0:
- **Warehouse crane (Hochregallager crane)**: An electrically motorized crane that moves along three axes (X, Y, Z) to store and retrieve workpieces from the high-bay warehouse slots. This is the physical actuator for `Capability_PickPiece` and `Capability_PlacePiece`.
- **Control software** on the Windows machine that subscribes to the MQTT topic and triggers the warehouse crane macros when specific command messages are received. Each macro code (`bandera_custom:0`, `bandera_custom:1`, ...) corresponds to a specific warehouse slot position.
- **Note**: The central vacuum suction crane (ventose) is a separate component not involved in Case 0.

The **DIDA Central machine** is a shared infrastructure machine in the **Data Intelligence for Industry (DII)** department at Vicomtech that:
- Runs Node-RED with an HTTP endpoint that receives commands from SMIA.
- Runs a Mosquitto MQTT broker that forwards messages to the fischertechnik machine.
- Is reachable from the dev machine via IP `192.168.155.10`.

### 12.3 Use Case Scenario

The Case 0 scenario is as follows:

1. A human **operator** opens the SMIA Operator web GUI in a browser.
2. The operator clicks **"Load"** to discover available SMIA agents in the network.
3. The SMIA Operator scans the AAS folder, finds `LEGO_factory_case0.aasx` (the AAS model of the fischertechnik factory — note the historical naming), and queries the corresponding SMIA agent via XMPP.
4. The operator sees the factory SMIA with its available capabilities: `Capability_PickPiece` and `Capability_PlacePiece` (both bound to the warehouse crane).
5. The operator selects **`Capability_PickPiece`** and clicks **"Submit"**.
6. The SMIA Operator sends a FIPA-ACL `REQUEST` message to the SMIA agent.
7. The SMIA agent:
   a. Receives the request.
   b. Looks up `Capability_PickPiece` → finds `Skill_PickPiece` (via `isRealizedBy`).
   c. Looks up `Skill_PickPiece` → finds the `pickPiece` action in the AID submodel (via `accessibleThroughAssetService`).
   d. Reads the endpoint: `base=http://192.168.155.10:1880`, `href=/smia/lego/pick`, `method=POST`.
   e. Sends `POST http://192.168.155.10:1880/smia/lego/pick`.
8. Node-RED receives the HTTP POST, processes it, and publishes `bandera_custom:0` to MQTT topic `vicom/61/piso_0/lab/lego/commands`.
9. The fischertechnik machine receives the MQTT message and the warehouse crane macro is triggered.
10. The SMIA agent receives the HTTP response, sends FIPA-ACL `INFORM` with the result to the operator.
11. The operator GUI displays the success response.

**Physical result:** The fischertechnik warehouse crane picks a piece from slot position 0.

### 12.4 Capabilities and Skills Defined

For Case 0, two capability-skill pairs are defined:

| Capability | Skill | HTTP Action | Endpoint |
|---|---|---|---|
| `Capability_PickPiece` | `Skill_PickPiece` | `pickPiece` (POST) | `/smia/lego/pick` |
| `Capability_PlacePiece` | `Skill_PlacePiece` | `placePiece` (POST) | `/smia/lego/place` |

Both capabilities have:
- Lifecycle qualifier: `hasLifecycle = OFFER` (the asset is currently offering these capabilities).
- Parameter: `position` (`xs:int`) — the warehouse slot position (0–8) to pick from or place at.
- Scope: **warehouse crane only**. The central vacuum suction crane (ventose) is out of scope for Case 0.

Both skills have:
- Implementation type qualifier: `SkillImplementationType = OPERATION`. The `semanticId` on this qualifier depends on the deployment context:
  - **Single-machine (Case 0):** leave `semanticId` empty. SMIA validates the qualifier via a type-string lookup (`get_qualifier_by_type('SkillImplementationType')`) — no semanticId needed.
  - **Multi-agent machines (Case 1+):** set `semanticId` to `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType`. During boot, SMIA also reads OWL data properties of the `Skill` class and looks up each by semanticId (`get_qualifier_value_by_semantic_id(iri)`). This IRI is the `hasImplementationType` OWL DatatypeProperty defined in `CSS-ontology-smia.owl`. Without it, the skill OWL instance is not fully populated, and the FIPA-CNP negotiation behaviour crashes at runtime. No ConceptDescription is needed in the AASX package — this is an ExternalReference (GlobalReference) to the OWL ontology IRI.

### 12.5 Design Decisions

Several non-trivial design decisions were made during the implementation:

**Skills as Property elements (not SubmodelElementCollection):**
During implementation, it was discovered that defining Skills as `SubmodelElementCollection` in the AASX causes a Python MRO (Method Resolution Order) conflict in SMIA's internal class extension system. The conflict arises because SMIA dynamically creates a class that inherits from both `ExtendedComplexSkill` and `ExtendedSubmodelElementCollection`, which have incompatible `HasSemantics`/`Qualifiable` inheritance orderings. The solution is to define Skills as `Property` elements — this causes SMIA to use `ExtendedSimpleSkill` instead, which has no MRO conflict.

**Node-RED as the integration layer:**
Rather than connecting SMIA directly to the MQTT broker, Node-RED was placed as an intermediary. This provides:
- Protocol translation (HTTP → MQTT).
- Input validation and defaulting (handling missing `position` parameter).
- Easy monitoring (Node-RED debug panels).
- Reusability (the flow can be shared and modified without touching SMIA).

**XMPP credential management:**
Both agent accounts (`SMIA_agent@ejabberd` and `operator001@ejabberd`) are automatically registered by ejabberd's `CTL_ON_CREATE` feature when the container starts for the first time. This makes deployment reproducible: no manual account creation is required.

---

## 13. System Architecture

### 13.1 Physical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Linux Development Machine                                        │
│                                                                  │
│  Docker Compose                                                  │
│  ┌──────────────┐  XMPP   ┌────────────┐  XMPP  ┌───────────┐ │
│  │   ejabberd   │◄────────►│    smia    │◄───────►│ smia-     │ │
│  │ (XMPP server)│  :5222  │  (SMIA    │         │ operator  │ │
│  └──────────────┘         │   agent)  │         │ (GUI)     │ │
│                           └─────┬──────┘         └─────┬─────┘ │
│                                 │ HTTP POST              │:10000 │
└─────────────────────────────────┼────────────────────────┼──────┘
                                  │                         │
                           192.168.155.10:1880        Browser
                                  │
┌─────────────────────────────────▼───────────────────────────────┐
│ DIDA Central Machine (192.168.155.10)                           │
│                                                                  │
│  Node-RED (:1880)          Mosquitto broker (:1883)             │
│  ┌───────────────────┐     ┌──────────────────────┐            │
│  │ HTTP In           │     │                       │            │
│  │ POST /smia/lego/  │────►│ topic:                │            │
│  │ pick              │     │ vicom/61/piso_0/lab/  │            │
│  └───────────────────┘     │ lego/commands         │            │
│                            └───────────┬──────────┘            │
└────────────────────────────────────────┼────────────────────────┘
                                         │ MQTT bridge
┌────────────────────────────────────────▼────────────────────────┐
│ fischertechnik/PLC Windows Machine                               │
│  (Training Factory Industry 4.0 24V)                            │
│                                                                  │
│  Mosquitto subscriber → control software → warehouse crane macro │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 13.2 Software Architecture

The software system is composed of five functional layers:

| Layer | Components | Technology |
|---|---|---|
| **Human Interface** | Browser, SMIA Operator GUI | HTML/CSS/JS, Python web server |
| **Agent Communication** | FIPA-ACL messages | XMPP (ejabberd, no TLS in current deployment) |
| **Agent Intelligence** | SMIA agent (AAS parsing, CSS reasoning, skill execution) | Python, SPADE, basyx, owlready2 |
| **Protocol Bridge** | Node-RED flow | Node.js, MQTT, HTTP |
| **Physical Interface** | MQTT messages → warehouse crane macro | Mosquitto, fischertechnik control software |

### 13.3 AAS Model Architecture

The `LEGO_factory_case0.aasx` package contains the complete digital twin of the fischertechnik Training Factory warehouse crane asset.

> **Note on naming:** The file and AAS shell identifiers (`LEGO_factory_case0.aasx`, `LEGO_factory`) are historical naming artifacts from the initial development phase. They refer to the fischertechnik Training Factory Industry 4.0 24V and should be interpreted as such in all technical documentation.

```
LEGO_factory_case0.aasx      ← digital twin of fischertechnik Training Factory (warehouse crane)
├── LEGO_factory (AAS shell, id: urn:uuid:6475_0111_2062_9689)
│   ├── SubmodelWithCapabilitySkillOntology  ← CSS concept definitions
│   ├── AssetInterfacesDescription           ← HTTP endpoint descriptions (AID)
│   │   └── InterfaceHTTP
│   │       ├── EndpointMetadata (base: http://192.168.155.10:1880)
│   │       └── InteractionMetadata
│   │           └── actions
│   │               ├── pickPiece (href: /smia/lego/pick, POST)
│   │               └── placePiece (href: /smia/lego/place, POST)
│   ├── CapabilitiesAndSkills               ← CSS capabilities and skills
│   │   ├── Capability_PickPiece [SMC, AssetCapability]
│   │   ├── Capability_PlacePiece [SMC, AssetCapability]
│   │   ├── Skill_PickPiece [Property, Skill]
│   │   └── Skill_PlacePiece [Property, Skill]
│   └── SemanticRelationships              ← CSS graph (OWL-equivalent links)
│       ├── rel_CapPick_isRealizedBySkill_SkillPick (isRealizedBy)
│       ├── rel_CapPlace_isRealizedBySkill_SkillPlace (isRealizedBy)
│       ├── rel_SkillPick_hasSkillInterface (accessibleThroughAssetService)
│       └── rel_SkillPlace_hasSkillInterface (accessibleThroughAssetService)
├── SMIA_agent (AAS shell, id: urn:uuid:6373_1111_2062_6896)
│   └── SoftwareNameplate
└── [Embedded files]
    ├── aasx/CSS-ontology-smia.owl
    └── aasx/smia-initialization.properties
```

### 13.4 Deployment Architecture (Docker Compose)

Three Docker containers run on the same host machine:

```
docker-compose.yml
├── xmpp-server (ejabberd)
│   ├── ports: 5222, 5269, 5280, 5443
│   ├── volume: ./xmpp_server/ejabberd.yml
│   ├── Auto-registers: SMIA_agent@ejabberd:asd
│   └── Auto-registers: operator001@ejabberd:gcis1234
│
├── smia (SMIA agent)
│   ├── depends_on: xmpp-server (healthy)
│   ├── volume: ./aas → /smia_archive/config/aas
│   ├── volume: patched smia_agent.py → container library
│   └── env: AAS_MODEL_NAME, AAS_ID, AGENT_ID, AGENT_PASSWD
│
└── smia-operator (Operator GUI)
    ├── depends_on: xmpp-server (healthy)
    ├── port: 10000 (web GUI)
    ├── volume: ./aas → /smia_archive/config/aas
    ├── volume: operator_gui_behaviours.py, operator_gui_logic.py, htmls/
    └── env: AAS_MODEL_NAME, AGENT_ID, AGENT_PASSWD
```

---

## 14. Implementation

### 14.1 AAS Model Creation (AASX Package Explorer)

The `LEGO_factory_case0.aasx` model (representing the fischertechnik Training Factory warehouse crane) was created using **AASX Package Explorer**, an open-source Windows tool distributed by IDTA. The creation process follows the **CSS-enriched AAS development workflow** defined in the SMIA paper (Fig. 6):

> For each SubmodelElement: if CSS-related → query Protégé for the IRI → add to `semanticId` field. For each relationship: get the CSS `ObjectProperty` IRI → add to `RelationshipElement` `semanticId`. Then add the AID submodel, embed the OWL file, and save the AASX.

In practice, the model creation involved:

1. Creating two AAS shells (`LEGO_factory` and `SMIA_agent`) in the same package. The `LEGO_factory` shell is the digital twin of the fischertechnik factory's warehouse crane (historical naming).
2. Embedding the CSS ontology file (`CSS-ontology-smia.owl`) as a supplementary file at path `aasx/CSS-ontology-smia.owl` — making the AASX self-contained (one file = AAS model + semantic definitions).
3. Building the `AssetInterfacesDescription` submodel following IDTA 02017. Note: SMIA extends the standard AID with `data-Query` (JSONPath/XPath expressions to extract values from responses) and `htv_params` (HTTP request parameters); these extensions are not used in Case 0 but are available for more complex scenarios.
4. Building the `CapabilitiesAndSkills` submodel with `AssetCapability` elements (SMC with semanticId `css-smia#AssetCapability`, `hasLifeCycle=OFFER`) and skills as **`Property`** elements (not SMC — see §14.4 for the reason).
5. Building the `SemanticRelationships` submodel with four `RelationshipElement` entries wiring capabilities to skills (`isRealizedBy`) and skills to AID actions (`accessibleThroughAssetService`).

The complete step-by-step tutorial for recreating this model from scratch is documented in `my_models/doc_case0.md` (Section 8).

### 14.2 smia-initialization.properties

The SMIA agent is configured via a properties file that defines the XMPP credentials, AAS model location, and ontology loading strategy:

```properties
[DT]
dt.agentID=SMIA_agent@ejabberd      # XMPP JID
dt.password=asd                      # XMPP password
dt.xmpp-server=ejabberd              # XMPP server hostname (Docker container name)

[AAS]
aas.model.serialization=AASX        # Use AASX format
aas.model.folder=/smia_archive/config/aas  # Path inside container
aas.model.file=LEGO_factory_case0.aasx     # Which file to load

[ONTOLOGY]
ontology.file=CSS-ontology-smia.owl  # OWL filename
ontology.inside-aasx=true            # Read .owl from inside the AASX package
```

The `ontology.inside-aasx=true` setting instructs SMIA to read the OWL file from within the AASX ZIP package (at `aasx/CSS-ontology-smia.owl`) rather than from the filesystem. This makes the deployment self-contained.

### 14.3 Docker Compose Configuration

The Docker Compose file (`my_models/docker-compose.yml`) defines seven services across three categories, all on a shared `smia-net` Docker bridge network. Docker DNS resolves container names (`ejabberd`, `nodered`, `mosquitto-central`) automatically — no manual `/etc/hosts` changes required. All credentials are stored in `my_models/.env` (gitignored); a template `my_models/.env.example` is committed to the repository.

**Infrastructure services (pre-built public images — no build step required):**

- **xmpp-server** (`ghcr.io/processone/ejabberd`): XMPP message broker. Auto-registers all agent XMPP accounts on first container start via the `CTL_ON_CREATE` environment variable. Exposes a health check on port 5222 — all agent containers use `depends_on: condition: service_healthy` to prevent connection attempts before ejabberd is ready.
- **nodered** (`nodered/node-red:latest`): HTTP→MQTT bridge. Loads the flow from `./nodered/flows.json` on startup. Listens on port 1880; SMIA machine agents call it at `http://nodered:1880` (resolved via Docker DNS).
- **mosquitto-central** (`eclipse-mosquitto:2`): Central MQTT broker. Bridges to the physical machine's MQTT broker via `./mosquitto/conf.d/bridge.conf` (the `address` line is the only host-specific configuration in the entire deployment).

**Custom SMIA agent services (built from Dockerfiles — requires `docker compose build`):**

- **smia-machine0**, **smia-machine1**, **smia-machine2**: Three machine agents that share the same Dockerfile (`my_models/docker/smia-machine/Dockerfile`). They differ only in AASX model and environment variables (`AAS_MODEL_NAME`, `AAS_ID`, `AGENT_ID`, `AGENT_PASSWD`, `NODERED_URL`).
- **smia-orchestrator**: FIPA-CNP dispatcher (`my_models/docker/smia-orchestrator/Dockerfile`). Receives capability requests from the operator and negotiates with machines.
- **smia-operator**: Web GUI (`additional_tools/extended_agents/smia_operator_agent/Dockerfile`). Scans the shared `aas/` folder to discover SMIA targets; exposes port 10000 for browser access.

All agent containers mount `./aas:/smia_archive/config/aas` — a single shared AASX folder that all agents (machines, orchestrator, operator) read from. The SMIA bug fix (`smia_agent.py`) is applied at image build time via the Dockerfile `RUN` step, not at runtime via volume mount (see §14.4).

### 14.4 smia_agent.py Patch

During testing, it was found that SMIA's internal method `get_asset_connection_class_by_ref()` failed to match the AID interface reference with the stored `AssetConnection` object because it used Python object identity (`is` / `==`) for comparison. Since the AID reference object obtained during skill resolution was a different Python object from the one stored during initialization (even though they referred to the same logical AAS element), the lookup returned `None`.

The fix adds two additional comparison strategies:
1. String comparison: `str(conn_ref) == str(asset_connection_ref)`.
2. Key tuple comparison: comparing normalized `(type, value)` tuples extracted from the reference's key list.

This fix is applied at **image build time** via the Dockerfile `RUN` step: the patched file is copied into the container and then placed into the SMIA package directory using a version-independent path detection command (`python3 -c "import smia, os; print(os.path.dirname(smia.__file__))"`). This approach is more robust than a runtime volume mount because it does not depend on the Python version or the exact site-packages path inside the container. The `smia_agent.py` fix is a pending upstream PR to the SMIA repository; once merged, the patch step can be removed from the Dockerfile.

### 14.5 Node-RED Flow

The Node-RED flow (`flow_dida_central_lego.json`) implements the HTTP-to-MQTT bridge:

1. **HTTP In node**: Listens for POST requests at `/smia/lego/pick`.
2. **JSON node**: Parses the request body.
3. **Function node**: Extracts the `position` parameter from the request (tries `payload.position`, `query.position`, `payload.skillParams.position`; falls back to `DEFAULT_POSITION = 0` if not found). Validates that position is an integer 0–8. Builds the MQTT payload: `bandera_custom:<position>`.
4. **MQTT Out node**: Publishes to topic `vicom/61/piso_0/lab/lego/commands` on broker `mosquitto-central:1883`, QoS 1.
5. **HTTP Response node**: Returns a JSON response with the publication status.

### 14.6 MQTT Chain

The MQTT message travels from Node-RED through two brokers:

```
Node-RED → mosquitto-central (DIDA central)
                    ↓
         MQTT bridge (configured separately)
                    ↓
         mosquitto (fischertechnik/PLC Windows machine)
                    ↓
         Subscriber → fischertechnik control software → warehouse crane macro
```

The payload format expected by the fischertechnik control software is `bandera_custom:<n>` where `<n>` is the warehouse slot position index (0–8). The topic `vicom/61/piso_0/lab/lego/commands` retains its historical name; it physically routes to the fischertechnik Training Factory.

### 14.7 Architectural Decisions — Justification and Alternatives

Two major architectural decisions shape the Case 0 deployment. Both were chosen pragmatically to fit a research lab context, and each carries specific trade-offs that must be understood to evaluate, extend, or adapt the system.

#### 14.7.1 Docker Compose for the SMIA Agent Stack

**Problem statement.** SMIA (the manufacturing agent) and SMIA-Operator (the GUI agent) communicate exclusively via XMPP. For that communication to work, both agents must resolve the same XMPP server hostname (`ejabberd`) and reach it on port 5222. Without isolation, this requires manually installing and configuring ejabberd on the host machine, managing hostname resolution across processes, and handling dependency startup order. On a shared lab machine running multiple projects simultaneously, these requirements introduce risk of conflicts and non-reproducibility.

**Chosen approach.** Seven Docker services are defined in a single `docker-compose.yml`: infrastructure services (`xmpp-server`, `nodered`, `mosquitto-central`) and custom agent services (`smia-machine0/1/2`, `smia-orchestrator`, `smia-operator`). All services share the same Docker-managed bridge network (`smia-net`), so hostnames such as `ejabberd`, `nodered`, and `mosquitto-central` are automatically resolvable within the network without any `/etc/hosts` modifications. Agents start only after the XMPP server passes a health check on port 5222 (`depends_on: condition: service_healthy`). Custom agent images are built from Dockerfiles (`docker compose build`) that extend the official `ekhurtado/smia:latest-alpine` image.

**Strengths:**

| Strength | Rationale |
|---|---|
| One-command deployment | `docker compose up -d` from the repository — no manual installation steps for any service |
| Reproducibility | The same images, volumes, and configuration produce identical behaviour on any machine with Docker installed |
| Isolated network | Containers communicate via Docker bridge; the hostname `ejabberd` resolves internally without touching host network configuration |
| Controlled startup order | Health-check-based `depends_on` ensures agents connect to ejabberd only after it is ready, eliminating race conditions |
| Automated XMPP account provisioning | `CTL_ON_CREATE` registers both agent accounts (`SMIA_agent@ejabberd` and `operator001@ejabberd`) on the first container start, removing manual `ejabberdctl` steps |
| Version-controlled configuration | All service definitions, ejabberd configuration, and AASX files are tracked in git alongside the source code |
| Clean code injection via Dockerfiles | Custom agent code is baked into images at build time via `COPY` — no fragile runtime volume mounts for Python files. AASX models and ejabberd config are still mounted as volumes (data, not code) for easy updates without rebuilds |

**Weaknesses and limitations:**

| Limitation | Explanation |
|---|---|
| Single host — single point of failure | All three services run on one machine; host failure takes down the entire SMIA stack |
| No horizontal scaling | Each SMIA container manages one asset; scaling to many assets means expanding the same Compose file rather than distributing across machines |
| Bug fix pending upstream | The `smia_agent.py` fix is baked into the custom Docker image via a `RUN` build step. If `ekhurtado/smia:latest-alpine` is updated, the patch file (`src/smia/agents/smia_agent.py`) may need review for conflicts. The long-term fix is an upstream pull request to the SMIA repository to eliminate the need for the patch entirely |
| Network port exposure | XMPP ports (5222, 5269) and the operator GUI port (10000) are exposed on the host. Acceptable in a controlled lab network; not suitable for production environments without a firewall or reverse proxy |
| Shared AAS folder fragility | Both `smia` and `smia-operator` mount the same `./aas/` directory. Any non-AASX file placed in that folder (e.g., backup files, XML exports) causes the operator GUI to return a 500 error during AAS discovery |

**Alternatives considered and rejected:**

| Alternative | Reason for rejection |
|---|---|
| Bare-metal installation (no Docker) | Non-reproducible; dependency conflicts on shared lab machine; manual XMPP server setup; no clean reset mechanism |
| Kubernetes | Significant operational overhead (cluster setup, manifests, ingress, persistent volume claims) unjustified for a single-host proof-of-concept |
| Docker Swarm | Adds multi-host orchestration complexity not needed when all services fit on one machine |
| One virtual machine per service | Higher resource overhead; slower startup; inter-VM networking requires additional configuration |
| Manual `docker run` with explicit `--network` | Requires scripting the startup sequence, health checks, and dependency ordering by hand — fragile and not reproducible by others |

**Potential improvements for later cases:**
- Submit the `smia_agent.py` fix upstream to the SMIA repository to eliminate the file-level patch.
- Add `mem_limit` and `cpus` constraints in the Compose file to prevent resource starvation on a shared machine.
- For production-scale or multi-machine deployments (Cases 1–N), migrate to a lightweight Kubernetes distribution (k3s) or Docker Swarm to distribute agents across machines.

---

#### 14.7.2 Edge + Central Data Processing Architecture

**Problem statement.** The DIDA laboratory hosts multiple physical manufacturing machines (fischertechnik Training Factory, KUKA robot, others). Each machine produces data (sensor readings, command acknowledgements, status events) and needs to receive commands. Two architectural extremes exist: a fully centralised broker and flow processor (simple to manage but a single point of failure for all machines), or fully isolated per-machine stacks with no shared infrastructure (maximum isolation but no cross-machine knowledge or unified data store). A middle ground was selected.

**Chosen approach.** Each machine has a dedicated **edge node** consisting of its own Mosquitto broker, Node-RED flow, and PostgreSQL database for local, machine-specific data. In addition, a shared **central DIDA node** (IP `192.168.155.10`) runs a Mosquitto broker, Node-RED instance, and PostgreSQL database for aggregated, cross-machine knowledge. An MQTT bridge connects each machine's local broker to the central broker, propagating selected topics.

In Case 0, the specific data path is:

```
SMIA container
    │  HTTP POST to 192.168.155.10:1880 (AID-defined endpoint)
    ▼
DIDA Central — Node-RED (HTTP → MQTT bridge)
    │  MQTT publish (topic: vicom/61/piso_0/lab/lego/commands)
    ▼
DIDA Central — Mosquitto broker (central)
    │  MQTT bridge (pre-configured)
    ▼
fischertechnik machine — Mosquitto broker (local)
    │  MQTT subscribe
    ▼
fischertechnik control software → warehouse crane macro
```

**Strengths:**

| Strength | Rationale |
|---|---|
| Fault isolation | If the central DIDA node goes down, edge nodes continue operating: local brokers still receive and process MQTT messages from local sources |
| Separation of concerns | Machine-specific data pipelines live on their respective edge nodes; the central node handles only aggregation and cross-machine analytics |
| Edge processing | Validation, payload transformation, and defaulting (e.g., the `DEFAULT_POSITION = 0` fallback in Node-RED) happen close to the machine, reducing latency for time-sensitive operations |
| Independent scalability | Adding a new machine means deploying an additional edge stack without modifying any existing node or the central configuration |
| Data locality | Raw, high-frequency machine data remains at the edge; only summary or event-level data is forwarded to the central node, reducing central bandwidth and storage load |
| Clear ownership boundaries | Each edge node can be administered, updated, and restarted independently; teams or individuals responsible for a machine manage their own edge stack |

**Weaknesses and limitations:**

| Limitation | Explanation |
|---|---|
| Operational complexity | More nodes means more services to configure, monitor, and troubleshoot. A silent failure anywhere in the chain (MQTT bridge, edge broker, central broker, Node-RED) can break the flow without an obvious error |
| Configuration duplication | Mosquitto configuration, Node-RED flows, and Docker Compose definitions are replicated across edge machines. Without infrastructure-as-code tooling (e.g., Ansible), configuration drift between machines is difficult to detect |
| Central node in the critical path for Case 0 | SMIA's AID endpoint points to the central DIDA node (`192.168.155.10:1880`), not to a fischertechnik-specific edge node. Consequently, if the central Node-RED instance is unavailable, commands cannot reach the fischertechnik machine even if its local stack is fully healthy. This partially undermines the fault-isolation argument for Case 0 specifically |
| MQTT bridge dependency | The bridge between the central broker and the fischertechnik local broker must be pre-configured and remain stable. If the bridge fails, commands accumulate at the central broker but never arrive at the machine |
| No unified monitoring | Without a tool such as Grafana/Prometheus, there is no single dashboard for health and throughput across all edge nodes |
| Cross-machine data correlation | If cross-machine analytics are required (e.g., correlating fischertechnik events with KUKA robot events), explicit data synchronisation logic must be designed at the Node-RED level; it does not arise automatically |

**Observation — pragmatic trade-off in Case 0.** A strict edge-computing design would have SMIA's AID point to a fischertechnik-specific edge endpoint. The central DIDA node is used instead because: (1) the fischertechnik Windows machine does not expose a general-purpose HTTP server for custom flows; (2) the central DIDA machine has Node-RED pre-installed and already serves as the protocol bridge for the laboratory; (3) the MQTT bridge from central to the fischertechnik machine is already pre-configured. This is a pragmatic and justified choice given the existing lab infrastructure, but it should be explicitly recognised as a limitation of the current deployment.

**Alternatives considered and rejected:**

| Alternative | Reason for rejection |
|---|---|
| Single centralised broker for all machines | Eliminates fault isolation; all machine traffic shares one broker; one broker failure stops all machines simultaneously |
| Direct SMIA → MQTT (bypassing Node-RED) | SMIA's communication interface is defined by the AID standard, which describes HTTP endpoints. SMIA does not natively publish MQTT; bypassing Node-RED would require modifying SMIA or redefining the AID standard for this deployment |
| Direct SMIA → fischertechnik machine | The fischertechnik machine runs Windows-based control software and is not accessible as an HTTP server. Direct access would also break the asset-agnostic design of SMIA (the agent would need asset-specific network knowledge not encoded in the AAS) |
| No edge storage (all data to central) | Central node becomes a bottleneck; machine data is lost if central is unavailable during collection |

**Potential improvements:**
- If a Linux-based edge node (e.g., Raspberry Pi) is deployed per machine, the AID base URL can point to the edge (`http://192.168.155.2x:1880`), removing the central node from the critical command path while keeping it as a purely aggregation layer.
- Standardise edge stack configuration using an Ansible playbook or a shared Docker Compose template to prevent configuration drift.
- Deploy Grafana + Prometheus (or a lightweight alternative such as Netdata) at the central node to provide a unified health dashboard for all edge nodes.
- Add a circuit-breaker pattern to the Node-RED function node: if the MQTT publish times out or fails, return an explicit error JSON so SMIA can propagate an `INFORM status=error` back to the operator rather than silently timing out.

---

#### 14.7.3 Summary Comparison

| Decision | Core problem addressed | Chosen approach | Primary strength | Primary limitation |
|---|---|---|---|---|
| SMIA stack deployment | Shared XMPP infrastructure for multi-agent communication | Docker Compose (8 services: xmpp-server, mosquitto-central, nodered, smia-machine0/1/2, smia-orchestrator, smia-operator — shared Docker network) | One-command reproducible deployment; custom Dockerfiles eliminate runtime file-level patches | Single host = single point of failure |
| Data processing topology | Per-machine vs. shared data pipelines | Edge per machine + shared central DIDA node | Fault isolation and separation of concerns | Central node in critical path for Case 0 commands; operational complexity of multi-node setup |

---

## 15. Results and Validation

### 15.1 End-to-End Validation

The complete Case 0 pipeline has been validated end-to-end and confirmed working as of 2026-03-04. Case 1 (multi-agent orchestration with FIPA-CNP) has been fully implemented and is undergoing E2E validation as of 2026-04-09. The Case 0 validated path:

1. SMIA agent starts, loads AAS model, identifies 2 capabilities and 2 skills.
2. SMIA logs confirm: `Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']`
3. Operator GUI loads, discovers SMIA, displays capabilities.
4. Operator selects `Capability_PickPiece` and submits.
5. SMIA logs confirm: `Executing skill of the capability through an asset service...` and `HTTP communication successfully completed.`
6. Node-RED publishes `bandera_custom:0` to MQTT topic.
7. fischertechnik warehouse crane macro triggers physically.
8. Operator GUI displays: `{"status":"ok","published":"vicom/61/piso_0/lab/lego/commands","payload":"bandera_custom:0","position":0}`.

### 15.2 Issues Encountered and Resolved

The following non-trivial issues were identified and resolved during implementation:

| Issue | Cause | Resolution |
|---|---|---|
| Docker Compose crash (`ContainerConfig`) | Legacy `docker-compose` v1 incompatibility | Switched to `docker compose` v2 |
| SMIA InitAASModelBehaviour MRO crash | Skills defined as `SubmodelElementCollection` | Changed Skills to `Property` type in AASX |
| Capability request hanging in `get_asset_connection_class_by_ref()` | Asset connection lookup using object identity | Patched `smia_agent.py` with string/key comparison |
| Operator GUI HTTP 500 on Load | Backup file (`.bak2`) in AAS folder scanned as invalid | Removed non-`.aasx` files from `aas/` folder |
| Node-RED returning HTTP 400 | Missing `position` parameter in SMIA's request | Added `DEFAULT_POSITION = 0` fallback in Node-RED function |
| `HandleNegotiationBehaviour: 'NoneType' object is not iterable` | RelationshipElement semanticIds in AASX used wrong casing: `#AccessibleThroughAgentService` (capital 'A') instead of `#accessibleThroughAgentService` — Track 3 uses exact lowercase match, so the OWL link was never created | Fixed all 3 machine AASXs with a Python zipfile/regex script: corrected IRI casing for all 5 relationship semanticIds |
| Qualifier `hasImplementationType not found` at boot (Case 1) | Qualifier semanticId was set with `https://` instead of `http://` (typo in AASX PE) — SMIA's `get_qualifier_value_by_semantic_id()` does exact string comparison | Fixed all 3 machine AASXs (4 qualifiers per file) — IRI must be `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` |
| Orchestrator race condition: both `ACLHandlingBehaviour` and `OrchestratorDispatchBehaviour` handling the same css-service message | SPADE broadcasts all messages to all matching behaviours; `ACLHandlingBehaviour` processed the message before the orchestrator could reserve its thread | Patched `acl_handling_behaviour.py`: early return for css-service messages when `pending_orchestrations` attribute present (orchestrator-only) |

### 15.3 Validation of the Self-Configuration Concept

The most significant validation result is the confirmation that **SMIA configures itself entirely from the AAS model**. The process flow does not contain any hard-coded reference to:
- The fischertechnik machine's IP address.
- The specific HTTP endpoint path.
- The capability or skill names.
- The MQTT topic or payload format.

All of this information is read from `LEGO_factory_case0.aasx` (the fischertechnik factory AAS) at startup. If a new machine with a different endpoint were added by creating a new AASX model, SMIA would handle it without any code modification.

### 15.4 Quantitative Performance Metrics (paper §5.2.3)

The SMIA paper reports benchmarks from a robotic logistics validation scenario (three SMIA agents: two robotic arms + one operator). These figures provide reference baselines for Case 0 performance evaluation.

| Metric | Value | Source context |
|---|---|---|
| Self-configuration time — robotic agent (21 CSS elements) | **6.73 s** average | Time from startup to `StateRunning` |
| Self-configuration time — operator agent (7 CSS elements) | **3.39 s** | Time from startup to `StateRunning` |
| Messages per direct task execution | **2** (REQUEST + INFORM) | Single-agent, no negotiation |
| Messages per distributed negotiation | **5** (2n+1, n=2 agents) | Multi-agent propose/accept cycle |
| Total response time (operator request → action complete) | **0.034–0.098 s** | End-to-end including XMPP + HTTP |

Self-configuration time scales with the number of CSS elements in the AAS model (more CSS elements = more OWL instances to load and link). Case 0 defines only 4 CSS elements per capability chain (2 capabilities + 2 skills), significantly fewer than the paper's 21-element scenario — the expected self-configuration time for Case 0 is well under the reported 6.73 s average.

The 2-message pattern (REQUEST + INFORM) observed in Case 0 is confirmed by the paper as the minimum interaction cost for direct execution. Multi-agent negotiation (implemented in Case 1 — see §16) involves more messages: the FIPA-CNP round (CFP + PROPOSE exchange + INFORM winner) plus the execution round (REQUEST + INFORM result) plus the result forwarding step; the total message count for 3 machines with 1 colour match is approximately 5–7 FIPA-ACL messages.

The 0.034–0.098 s end-to-end response time validates that SMIA's XMPP-based FIPA-ACL communication introduces negligible latency relative to typical manufacturing operations (which occur on the scale of seconds to minutes). This supports requirement **R6** (P2P communication with I4.0-compliant language) without compromising responsiveness.

### 15.5 Positioning Relative to Similar Approaches (paper Table 2)

The SMIA paper includes a comparative evaluation against three alternative frameworks for deploying manufacturing agents as digital twins:

| Criterion | **SMIA** | MAS4AI | NOVAAS | FA3ST |
|---|---|---|---|---|
| **Standard: AAS** | ✓ | ✗ | ✓ | ✓ |
| **Standard: CSS** | ✓ | ✗ | ✗ | ✗ |
| **Standard: FIPA-ACL** | ✓ | ✓ | ✗ | ✗ |
| **Self-configuration from AAS** | ✓ | ✗ | ✗ | ✗ |
| **P2P multi-agent communication** | ✓ | ✓ | ✗ | ✗ |
| **Physical asset integration (AID)** | ✓ | ✗ | ✓ | ✓ |
| **Extensible software architecture** | ✓ | ✗ | ✓ | ✓ |
| **Open source** | ✓ | ✗ | ✓ | ✓ |

Key differentiator: SMIA is the **only framework** that combines (a) full AAS compliance, (b) CSS semantic capability modelling, (c) FIPA-ACL multi-agent communication, and (d) automated self-configuration from the AAS model. Competing frameworks implement subsets of these properties but none integrates all four.

For Case 0 specifically, the self-configuration criterion is the primary validation target: the agent **requires no asset-specific code** because all asset knowledge is encoded in the AASX model and read at runtime. This distinguishes SMIA from framework approaches (FA3ST, NOVAAS) that provide AAS APIs but do not generate autonomous agents from those descriptions.

---

## 16. Case 1 — Multi-Agent Orchestration

### 16.1 Motivation and Research Contribution

Case 0 validated two of the eight SMIA design requirements: R2 (automated self-configuration of digital twins from a standardised AAS model) and R7 (separation between the physical asset and its digital twin). In Case 0, the entire execution chain — from AAS parsing to HTTP command — required zero asset-specific code inside the agent. This is a powerful result, but it involves only a single agent acting on a single asset upon direct request from an operator.

Real flexible manufacturing systems involve **pools of interchangeable machines**, tasks with **routing constraints** (e.g., a piece of a given colour must go to the machine handling that colour), and dynamic resource allocation based on real-time machine availability. These scenarios require multiple agents working in concert. Case 1 extends the baseline to address exactly this: it validates requirements R5 (inclusion in distributed and decentralised systems) and R6 (P2P communication with I4.0-compliant FIPA-ACL language).

**Scope of Case 1.** Three machine SMIAs (machine0, machine1, machine2) and one orchestrator SMIA are deployed. Each machine declares a colour constraint in its AAS — machine0 handles red pieces, machine1 handles blue, machine2 handles white. All three physically control the same fischertechnik warehouse crane (the physical differentiation is not the focus; the multi-agent protocol mechanics are). When the operator sends a task specifying a colour, the orchestrator discovers eligible machines, runs a negotiation round using the FIPA Contract Net Protocol (FIPA-CNP) to select the most available one, dispatches execution to the winner, and returns the result to the operator.

**Research contribution.** The SMIA framework provides the FIPA-CNP *responder/proposer* side — the logic that a machine uses to receive a Call For Proposals (CFP), compute its availability, broadcast a PROPOSE to competing peers, compare results, and declare a winner. This is implemented in `HandleNegotiationBehaviour` inside the base image. What does **not** exist in the base framework is the FIPA-CNP *initiator* side: the agent that formulates the problem, sends the CFP, waits for the winner notification, dispatches the work to the winner, and aggregates the result for the original requester. The `OrchestratorDispatchBehaviour` implemented in this TFG is that missing initiator side. It is the primary software contribution of Case 1.

---

### 16.2 Architecture Overview

The Case 1 system consists of six Docker containers sharing one ejabberd XMPP server:

| Container | Role | AAS model |
|---|---|---|
| `ejabberd` | XMPP message broker — routes all agent messages | — |
| `smia-machine0` | Manufacturing SMIA, red colour constraint | `LEGO_factory_case0.aasx` |
| `smia-machine1` | Manufacturing SMIA, blue colour constraint | `LEGO_machine1_case0.aasx` |
| `smia-machine2` | Manufacturing SMIA, white colour constraint | `LEGO_machine2_case0.aasx` |
| `smia-orchestrator` | Orchestrator SMIA | `SMIA_orchestrator.aasx` |
| `smia-operator` | Operator GUI — human entry point | `SMIA_Operator_article.aasx` |

The orchestrator sits between the operator and the machines. It is invisible to the physical asset — it never makes an HTTP call to Node-RED directly. Its sole job is to run the FIPA-CNP negotiation and forward the winning machine's execution result back to the operator.

**The two-shell architecture per machine AASX.** Each machine's AASX package contains two AAS shells, not one. This is a deliberate SMIA design decision that reflects a fundamental distinction in the digital twin concept:

| Shell | Represents | Content | Used by |
|---|---|---|---|
| `LEGO_factory` (or `LEGO_machine1`, etc.) | The **physical asset** DT | AID (HTTP interface), Capabilities, Skills, CSS relationships, ontology | SMIA agent during self-configuration — filtered by `AAS_ID` env var |
| `SMIA_agent` | The **software agent** DT | `SoftwareNameplate` submodel: agent identity, XMPP JID (`InstanceName`), software version | Operator GUI and other SMIAs for agent discovery |

The AAS standard allows multiple shells in one AASX package. In the SMIA philosophy (paper §3), the physical machine and the software agent that controls it are distinct digital entities — the crane has its own DT as a machine, and the SMIA agent has its own DT as a software product. They are packaged together because they are deployed together in one container.

**In practice:**
- The `AAS_ID` Docker environment variable (e.g., `urn:uuid:6475_0111_2062_9689`) tells SMIA which shell to use for self-configuration. SMIA reads the AID and CSS submodels from the `LEGO_factory` shell only.
- The operator GUI's `get_smia_jid_from_aas_store()` searches the entire AASX for a submodel with the `SoftwareNameplate` semantic ID, reads the `InstanceName` property, and displays that JID in the GUI list. The GUI shows `SMIA_agent@ejabberd` — not the shell's `idShort` attribute.
- The `idShort` of the `SMIA_agent` shell is a display label in AASX Package Explorer only. It has no runtime significance. All three machines use `SMIA_agent` as the idShort in their respective AASX files — this is not a conflict because `idShort` uniqueness is only required within a single AASX package.
- The `InstanceName` value must be the **full XMPP JID** including the ejabberd domain — e.g., `SMIA_agent@ejabberd`, `smia_machine1@ejabberd`. The orchestrator's `_extract_jid_from_store()` uses this value directly as the target address for CFP messages. A value like `smia_agent` (missing `@ejabberd`) is not a valid XMPP address and will cause the machine to be silently excluded from all negotiations.
- Each `SMIA_agent` shell must also have a **globally unique `id` (UUID)**. The AAS standard Part 1 (§5.3.1) requires that all shell identifiers be unique across packages. If two machines share the same SMIA agent shell UUID, the BaSyx SDK `DictObjectStore` may silently discard one during deserialization — making that machine's JID unreadable by the orchestrator.

**End-to-end flow (10 steps):**

```
[Operator GUI]
    │ 1. FIPA-ACL REQUEST {capabilityIRI, skillParams: {color: "red"}}
    │    ontology=css-service, thread=op_T
    ▼
[smia-orchestrator] — OrchestratorDispatchBehaviour intercepts
    │ 2. reserves op_T (prevents ACLHandlingBehaviour from double-processing)
    │ 3. scans /smia_archive/config/aas/*.aasx
    │    → finds machine0 (Capability_PickPiece/color=red)
    │    → skips machine1 (color=blue), machine2 (color=white)
    │ 4. maps red → position="0" (hardcoded COLOR_POSITION_MAP)
    │ 5. FIPA-ACL CFP {capabilityIRI, negCriterion, negTargets=[machine0],
    │                   negRequester=smia_orch, skillParams}
    │    thread=neg_T, protocol=fipa-contract-net
    ▼
[smia-machine0] — HandleNegotiationBehaviour (base SMIA, built-in)
    │ 6. single machine in negTargets → wins immediately (no PROPOSE needed)
    │    OR: calls machineAvailValue agent service
    │        → GET http://192.168.155.10:1880/smia/lego/availability
    │        → 1.0 (free) or 0.0 (busy)
    │ 7. sends INFORM {winner: true} to smia_orch (thread=neg_T)
    ▼
[smia-orchestrator]
    │ 8. receives winner INFORM from machine0
    │ 9. sends FIPA-ACL REQUEST {capabilityIRI, skillParams: {position: "0"}}
    │    thread=exec_T (new thread)
    ▼
[smia-machine0] — HandleCapabilityBehaviour (base SMIA, built-in)
    │ 10. resolves Capability_PickPiece → Skill_PickPiece → AID pickPiece action
    │     HTTP POST 192.168.155.10:1880/smia/lego/pick {"position":"0"}
    │     Node-RED → MQTT → crane
    │ 11. sends INFORM {result} to smia_orch (thread=exec_T)
    ▼
[smia-orchestrator]
    │ 12. forwards INFORM {result} to operator (thread=op_T)
    ▼
[Operator GUI] — displays result
```

Notice that steps 10–11 (the actual physical execution) are handled entirely by the base SMIA `HandleCapabilityBehaviour`. The orchestrator never touches Node-RED directly — it delegates the execution to the machine just as the operator would in Case 0.

---

### 16.3 The SMIA Extensibility Mechanism

**The problem with the default Docker entrypoint.** The SMIA Docker image runs the command `python3 -m smia.launchers.smia_docker_starter` at startup. The default `smia_docker_starter.py` creates a plain `SMIAAgent`, which supports self-configuration from AAS but exposes no extension hooks. There is no way to register a custom Python function or a custom SPADE behaviour without modifying the agent class itself.

**The solution: ExtensibleSMIAAgent.** The SMIA authors designed a subclass called `ExtensibleSMIAAgent` that provides exactly three official extension hooks (paper §4.2, Fig. 10):

| Hook | Signature | Purpose |
|---|---|---|
| `add_new_agent_service` | `(service_id: str, method: callable)` | Register a Python function as an **agent service** — called by SMIA when a Skill is linked to it via `accessibleThroughAgentService` |
| `add_new_agent_capability` | `(behaviour: spade.behaviour.Behaviour)` | Add a SPADE behaviour to the agent — started alongside all base SMIA behaviours when the agent enters StateRunning |
| `add_new_asset_connection` | `(interface_ref, connection)` | Register a custom asset protocol handler (e.g., OPC UA, MQTT direct) |

**The Dockerfile-based entrypoint override.** Since we cannot change the upstream Docker image (we do not own it), we replace the default launcher by providing a custom `CMD` in our own Dockerfile:

```dockerfile
# my_models/docker/smia-machine/Dockerfile
FROM ekhurtado/smia:latest-alpine

# Apply smia_agent.py bug fix at build time (version-independent path detection)
COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py
RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    cp /tmp/smia_agent_patch.py "$SMIA_PKG/agents/smia_agent.py" && \
    rm /tmp/smia_agent_patch.py

# Copy our application code into the container
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /smia_machine_starter.py
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py /smia_machine_agent_services.py

WORKDIR /
CMD ["python3", "-u", "smia_machine_starter.py"]
# ↑ Replaces the default CMD ("python3 -m smia.launchers.smia_docker_starter")
#   with our custom launcher. -u = unbuffered stdout for live logging.
```

The default SMIA image CMD (`python3 -m smia.launchers.smia_docker_starter`) is overridden cleanly by our `CMD` — no dependency on the Python version or `site-packages` path. The bug fix (`smia_agent.py`) is applied at build time, not at runtime. The `WORKDIR /` instruction adds `/` to Python's `sys.path`, enabling `import smia_machine_agent_services` to resolve without any path manipulation.

This is architecturally cleaner than the volume-mount override approach (which was Python-version-locked to a hardcoded `site-packages` path). The orchestrator Dockerfile follows the identical pattern (`my_models/docker/smia-orchestrator/Dockerfile`).

**Custom implementation — file classification:**

All Python files in this project belong to one of three types:

| Type | Description | Files |
|---|---|---|
| **A — New implementation** | Written from scratch for this project; implements application logic that did not exist in SMIA | `smia_machine_starter.py`, `smia_machine_agent_services.py`, `smia_orchestrator_starter.py`, `orchestrator_dispatch_behaviour.py` |
| **B — Framework extension** | Type A files are also extensions: they use the official SMIA extension API (`add_new_agent_service`, `add_new_agent_capability`) — they extend SMIA without modifying it | Same as above |
| **C — Bug fix** | One SMIA framework file with a single bug corrected; all other framework code is unmodified | `smia_agent.py` (pending upstream PR) |

**Configuration and data files (not Python code):**
- AASX models (`.aasx`) — digital twin definitions
- `nodered/flows.json` — Node-RED HTTP→MQTT bridge flow
- `mosquitto/mosquitto.conf` + `conf.d/bridge.conf` — MQTT broker + bridge to physical machine
- `.env.example` — credentials template (`.env` is gitignored)
- `xmpp_server/ejabberd.yml` — XMPP server configuration

**The four Python files and why each exists:**

| File | Hook used | Reason for existence |
|---|---|---|
| `smia_machine_starter.py` | `add_new_agent_service()` | Creates `ExtensibleSMIAAgent` instead of plain `SMIAAgent`; registers `get_machine_availability` as agent service `machineAvailValue` |
| `smia_machine_agent_services.py` | — (the function itself) | `async get_machine_availability()`: HTTP GET to Node-RED `/smia/lego/availability`; returns 1.0 (free) or 0.0 (busy) as the FIPA-CNP negotiation score |
| `smia_orchestrator_starter.py` | `add_new_agent_capability()` | Creates `ExtensibleSMIAAgent` for the orchestrator; registers `OrchestratorDispatchBehaviour` as an additional SPADE behaviour |
| `orchestrator_dispatch_behaviour.py` | `add_new_agent_capability()` | **The research contribution** — implements the FIPA-CNP initiator: AAS-based machine discovery, colour routing, CFP broadcast, winner selection, task delegation to winning machine, result forwarding to operator |

All three machines share the same `smia_machine_starter.py` and `smia_machine_agent_services.py`. The difference between machines is entirely in their AASX model and environment variables (`AAS_MODEL_NAME`, `AAS_ID`, `AGENT_ID`, `AGENT_PASSWD`). This directly demonstrates R8 (modular and extensible software design): one generic set of Python files parameterised by standardised AAS descriptions, with zero asset-specific code in the agent software.

---

### 16.4 FIPA-CNP: The Contract Net Protocol in Depth

**What is FIPA-CNP?** The Contract Net Protocol (CNP) is a task allocation protocol standardised by the Foundation for Intelligent Physical Agents (FIPA). It enables a *manager* (initiator) to distribute a task to one of several *contractors* (proposers) without centralised decision logic. The protocol is message-based and fully decentralised on the proposer side: each contractor independently assesses its ability to perform the task and communicates its bid to all other contractors. The FIPA-CNP is referenced in the SMIA paper as the protocol used for R6 (P2P communication with I4.0-compliant FIPA-ACL).

**The protocol messages:**

```
Initiator                         Contractors (all)
    │                                    │
    │── CFP (Call For Proposals) ───────►│  "who can do X?"
    │                                    │
    │◄─ PROPOSE (bid value) ────────────►│  contractors talk to each other
    │   (only winner sends to initiator) │  comparing their bids
    │                                    │
    │◄── INFORM {winner: true} ──────────│  from the winner only
    │                                    │
    │── REQUEST (execute task) ─────────►│  to winner only
    │                                    │
    │◄── INFORM {result} ────────────────│
```

**The responder/proposer side (built into base SMIA — `HandleNegotiationBehaviour`).**
When a machine receives a CFP, `NegotiatingBehaviour` (a base SMIA behaviour) detects the `fipa-contract-net` protocol in the message metadata and spawns a `HandleNegotiationBehaviour` for it. This behaviour:

1. Reserves the `neg_thread` so `ACLHandlingBehaviour` ignores subsequent messages on that thread
2. Validates that the requested capability (`capabilityIRI`) exists in its CSS ontology
3. If only one machine is in `negTargets`: wins immediately — sends `INFORM {winner: true}` to `negRequester` without broadcasting a PROPOSE
4. If multiple machines are in `negTargets`: computes `negValue` via the `negCriterion` agent service, broadcasts `PROPOSE {negValue}` to all other `negTargets`
5. Collects `PROPOSE` messages from peers, compares values; highest value wins
6. Winner sends `INFORM {winner: true}` to `negRequester` (the orchestrator)

The `negValue` is the machine's *negotiation score*: a float in [0.0, 1.0] where 1.0 = fully available and 0.0 = completely occupied. The `negCriterion` field in the CFP body is the IRI of the OWL individual that SMIA uses to find the associated `SkillInterface` and, through it, the registered agent service to call.

**Why `negCriterion` points to a Skill (not directly to a SkillInterface).** In the CSS model, a Skill is a *concrete, technology-specific implementation of a function*. A SkillInterface is only the *access point* to invoke that implementation. The distinction matters here:

- `Skill_NegAvailability` IS a Skill in the CSS sense: it implements the specific function "compute my availability by making an async HTTP GET request to a Node-RED endpoint and parsing the plain-text float response." Different machines could implement the same role (availability reporting) with different technologies — one via HTTP, another via OPC-UA, another via a lookup table — each as a distinct Skill. The IRI uniquely identifies *this particular implementation*.
- `machineAvailValue` is the SkillInterface that describes *how to invoke* that Skill — in this case, via the registered Python agent service.

SMIA's resolution chain for the `negCriterion` IRI is (source: `capability_skill_ontology.py:126`):
```python
for instance_class in self.ontology.individuals():
    if instance_class.iri == instance_iri:   # full IRI comparison
        return instance_class
```
Then: `neg_skill_instance.get_associated_skill_interface_instances()` traverses the `accessibleThroughAgentService` relationship to reach `machineAvailValue`. If `negCriterion` pointed directly at the SkillInterface, `get_associated_skill_interface_instances()` would return an empty set and the negotiation score would default to 0.0 — the machine would never win.

The naming `Skill_NegAvailability` follows the established SMIA convention (cf. `Skill_PickPiece`, `Skill_PlacePiece`) and is unambiguous for a tribunal reviewer: it is a Skill whose purpose is to report negotiation availability. It does NOT need to be linked to a Capability via `isRealizedBy` — the FIPA-CNP behaviour accesses it directly by IRI, bypassing the Capability layer.

**The initiator side (implemented in this TFG — `OrchestratorDispatchBehaviour`).**
The `OrchestratorDispatchBehaviour` is a SPADE `CyclicBehaviour` that runs in the orchestrator's SPADE event loop alongside all base SMIA behaviours. Its `run()` method executes once per event loop iteration, receives one message (or times out), and routes it based on the performative and thread. The four routes are:

| Route | Condition | Action |
|---|---|---|
| 1 | `REQUEST` + `css-service` + unseen thread | New task from operator → start negotiation |
| 2 | `INFORM` + thread in negotiation phase | Winner notification → dispatch execution |
| 3 | `INFORM` + thread in awaiting-result phase | Execution result → forward to operator |
| 4 | `FAILURE` + tracked thread | Negotiation failed → send FAILURE to operator |

**Why decentralised?** In a centralised architecture, the orchestrator would query each machine for its availability, compare the values, and decide the winner itself. In the FIPA-CNP design, the orchestrator only needs to know *who* is eligible (through AAS discovery and colour filtering) and ask them to compete. The machines handle the comparison among themselves. This is more resilient — the orchestrator does not become a bottleneck or a single point of failure for the negotiation computation.

---

### 16.5 AAS-Based Dynamic Agent Discovery

A naive implementation of the orchestrator would maintain a hardcoded list of machine JIDs. This would violate R8 (modular and extensible design) and require code changes every time a machine is added or removed.

Instead, `OrchestratorDispatchBehaviour._discover_machines_for_request()` scans the AAS folder at runtime, reading every `.aasx` file present. This is the same mechanism used by the operator GUI (`operator_gui_logic.py`): both parse the AAS folder with the `basyx.aas.adapter.aasx.AASXReader` and extract the machine's XMPP JID from its `SoftwareNameplate` submodel.

**How discovery works step by step:**

1. For each `.aasx` file in `/smia_archive/config/aas/`:
   - Open it with `basyx.aas.adapter.aasx.AASXReader` and load into a `DictObjectStore`
   - Find the submodel whose `semantic_id` matches `https://admin-shell.io/idta/SoftwareNameplate/1/0`
   - Within that submodel, find the `Property` whose `semantic_id` matches the `InstanceName` IRI
   - The property's value is the XMPP JID (e.g., `smia_machine1@ejabberd`)

2. Within the same AASX, find the `SubmodelElementCollection` whose `id_short` matches the requested capability (e.g., `Capability_PickPiece`), then find the child `Property` with `id_short == "color"`. Its value is the machine's declared colour constraint.

3. If `color_filter` is set and the machine's colour does not match, skip it.

4. Exclude the orchestrator's own JID (avoid sending CFPs to itself).

**Implication for extensibility.** To add a fourth machine (e.g., machine3 handling yellow pieces), it is sufficient to:
- Create `LEGO_machine3_case0.aasx` with `Capability_PickPiece/color = "yellow"`
- Add `yellow → position="3"` to `COLOR_POSITION_MAP` in the orchestrator behaviour
- Add an ejabberd account and a Docker Compose service
- No changes to any existing machine or orchestrator Python code

This is AAS-native agent onboarding: the AAS model is the source of truth for agent identity and capability, exactly as SMIA was designed.

---

### 16.6 Color Constraint Routing

**The two-level translation problem.** The operator specifies a task in terms meaningful to the production process: "pick a red piece." The physical machine, however, operates in terms of physical coordinates: "move to slot 0." Two translation steps are needed:

1. **Semantic filtering (AAS level):** The orchestrator reads each machine's `Capability_PickPiece/color` property from its AASX and retains only machines whose colour matches the operator's request.

2. **Physical mapping (application level):** The matching colour is translated to a warehouse slot number via a hardcoded map:

```python
COLOR_POSITION_MAP = {
    "red":   "0",
    "blue":  "1",
    "white": "2",
}
```

This map is hardcoded because the physical layout of the LEGO warehouse is fixed — slots are numbered 0 to 8 from left to right, and the colour of pieces placed in each slot is determined by the lab setup, not by software.

**Why the machine receives `{position: N}` and not `{color: X}`.** The machine's AID endpoint (`POST /smia/lego/pick`) expects a JSON body containing `position`. Node-RED, which implements the HTTP→MQTT translation, uses the position number to build the `bandera_custom:<N>` MQTT payload. It has no concept of colours — that abstraction exists only at the orchestration and AAS level. The orchestrator performs the translation and stores the `resolved_position` in its `pending_orchestrations` state dict before the negotiation begins, so that when the winner is known, the execution request carries the correct physical parameter.

---

### 16.7 SPADE Broadcast Model and Thread Reservation

**SPADE's message delivery model.** SPADE is the Python multi-agent framework underlying SMIA. Its message delivery model is *broadcast*: every incoming XMPP message is delivered to **all** SPADE behaviours whose template matches, not just one. Both `OrchestratorDispatchBehaviour` and the base `ACLHandlingBehaviour` are `CyclicBehaviour` instances that run concurrently in the same asyncio event loop. Without any coordination mechanism, both would receive and attempt to process every message.

**The conflict.** When the operator sends a `REQUEST` with `ontology=css-service` to the orchestrator, `ACLHandlingBehaviour` would also see it and spawn a `HandleCapabilityBehaviour`. That child behaviour would look for a skill interface in the orchestrator's AAS — but the orchestrator's AAS defines no `accessibleThroughAssetService` relationship (it has no AID endpoint for direct execution). The capability request would fail silently.

**The solution: reserved threads.** `SMIAAgent` maintains a set called `reserved_threads`. `ACLHandlingBehaviour` checks this set before processing any message (source: `acl_handling_behaviour.py:67`):

```python
if msg.thread not in self.myagent.reserved_threads:
    # process message
```

As soon as `OrchestratorDispatchBehaviour` intercepts a message it intends to handle, it calls:

```python
await self.myagent.add_reserved_thread(thread)
```

This atomically registers the thread as owned by the orchestration behaviour. All subsequent messages on that thread are invisible to `ACLHandlingBehaviour`. The same mechanism is used inside `HandleNegotiationBehaviour` on the machines — negotiation threads are reserved at the start of `on_start()` so that competing PROPOSE messages are not accidentally routed elsewhere.

---

### 16.8 Orchestration State Machine

Each active orchestration involves two independent FIPA-ACL conversations, each on its own thread:

- **`neg_thread`** — the negotiation conversation: CFP → (PROPOSE exchange among machines) → INFORM(winner)
- **`exec_thread`** — the execution conversation: REQUEST → (machine executes) → INFORM(result)

The orchestrator tracks the state of each conversation in a dictionary stored directly on the agent object (`self.myagent.pending_orchestrations`), keyed by thread ID. This dict is accessible across all async calls within the same SPADE event loop.

**State transitions:**

```
Operator REQUEST arrives
    │
    ├── neg_thread created (phase="negotiation")
    │   op_thread, op_sender, skill_params, capability_iri,
    │   resolved_position stored
    │
    │  [CFP sent to machines]
    │
    ├── INFORM(winner=True) received on neg_thread
    │   neg_thread phase → "done"
    │   exec_thread created (phase="awaiting_result")
    │       neg_thread, op_thread, op_sender stored
    │
    │  [REQUEST sent to winner]
    │
    ├── INFORM(result) received on exec_thread
    │   result forwarded to operator on op_thread
    │   exec_thread removed from dict
    │   neg_thread removed from dict
    │
    └── (completed)
```

The two threads are necessary because the negotiation and the execution are semantically distinct conversations. A machine that participates in the negotiation and then receives an execution request on a different thread can process both correctly — the negotiation was handled by `HandleNegotiationBehaviour`, the execution is handled by a fresh `HandleCapabilityBehaviour` spawned by `ACLHandlingBehaviour`.

---

### 16.9 Real-Time Availability via Node-RED

**How a machine's availability is determined.** During FIPA-CNP negotiation, SMIA calls the registered agent service `machineAvailValue` to compute the machine's `negValue`. The service function `get_machine_availability()` (file: `additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py`) makes an HTTP GET request to Node-RED:

```
GET http://nodered:1880/smia/lego/availability          (Docker-internal DNS)
Response: "1.0" (plain text, machine is free)
      or: "0.0" (plain text, machine is executing a task)
```

**How Node-RED tracks busyness.** The existing pick and place HTTP flows in Node-RED are modified with a global flag:
- At the start of each flow (immediately after the HTTP In node): `global.set("machine_busy", true)`
- After the MQTT publish (before the HTTP Response node): `global.set("machine_busy", false)`

The availability endpoint reads this flag:
```javascript
var busy = global.get("machine_busy") || false;
msg.payload = busy ? "0.0" : "1.0";
```

**Why plain text and not JSON?** The `get_machine_availability()` function parses the response as `float(text.strip())`. If Node-RED returned `{"availability": 1.0}`, the `float(...)` call would raise a `ValueError`. Plain text is the simplest format that matches the expected type directly.

**Why an agent service (not an asset service)?** An agent service is a Python function registered directly on the SMIA agent. An asset service is an HTTP endpoint defined in the AID submodel. The availability query is performed by the agent's negotiation behaviour — not by a skill execution. Using an agent service avoids adding an unnecessary entry to the AID submodel and keeps the AID clean (it only describes physical action endpoints, not internal monitoring queries). This also allows using Python's `aiohttp` for the GET, which is compatible with SMIA's `asyncio` event loop — using the synchronous `requests` library would block the entire event loop.

**Behaviour on error.** If Node-RED is unreachable, `aiohttp.ClientConnectorError` is caught and `0.0` is returned. Treating an unreachable Node-RED as *busy* (not *available*) is the safe default — it prevents the orchestrator from dispatching work to a machine whose bridge is broken.

---

### 16.10 End-to-End Message Sequence

The following sequence diagram shows the complete Case 1 flow, including all FIPA-ACL messages and their metadata. Thread IDs are symbolic.

```
Operator          Orchestrator         Machine0              Node-RED
  │                    │                   │                     │
  │ REQUEST            │                   │                     │
  │ thread=op_T        │                   │                     │
  │ ontology=css-service                   │                     │
  │ body={color:"red"} │                   │                     │
  │──────────────────► │                   │                     │
  │                    │ reserves op_T     │                     │
  │                    │ scans AAS folder  │                     │
  │                    │ finds machine0    │                     │
  │                    │ red → pos="0"     │                     │
  │                    │ creates neg_T     │                     │
  │                    │ reserves neg_T    │                     │
  │                    │                   │                     │
  │                    │ CFP               │                     │
  │                    │ thread=neg_T      │                     │
  │                    │ protocol=fipa-contract-net              │
  │                    │ body={capIRI,     │                     │
  │                    │  negCriterion,    │                     │
  │                    │  negTargets:[m0], │                     │
  │                    │  negRequester:orch}                     │
  │                    │──────────────────►│                     │
  │                    │                   │ reserves neg_T      │
  │                    │                   │ single target:      │
  │                    │                   │ wins immediately    │
  │                    │                   │ (OR: GET avail)     │
  │                    │                   │────────────────────►│
  │                    │                   │◄────────────────────│
  │                    │                   │ "1.0"               │
  │                    │                   │                     │
  │                    │ INFORM            │                     │
  │                    │ thread=neg_T      │                     │
  │                    │ {winner:true}     │                     │
  │                    │◄──────────────────│                     │
  │                    │ neg_T → done      │                     │
  │                    │ creates exec_T    │                     │
  │                    │ reserves exec_T   │                     │
  │                    │                   │                     │
  │                    │ REQUEST           │                     │
  │                    │ thread=exec_T     │                     │
  │                    │ ontology=css-service                    │
  │                    │ body={capIRI,     │                     │
  │                    │  skillParams:     │                     │
  │                    │  {position:"0"}}  │                     │
  │                    │──────────────────►│                     │
  │                    │                   │ POST /smia/lego/pick│
  │                    │                   │────────────────────►│
  │                    │                   │◄────────────────────│
  │                    │                   │ {status:"ok",...}   │
  │                    │                   │                     │
  │                    │ INFORM            │                     │
  │                    │ thread=exec_T     │                     │
  │                    │ {result}          │                     │
  │                    │◄──────────────────│                     │
  │                    │ cleans up state   │                     │
  │ INFORM             │                   │                     │
  │ thread=op_T        │                   │                     │
  │ {result}           │                   │                     │
  │◄───────────────────│                   │                     │
  │ display result     │                   │                     │
```

**Message count analysis.** This flow requires 7 FIPA-ACL messages for a single-machine negotiation (REQUEST from operator, CFP, INFORM(winner), REQUEST to machine, INFORM(result) from machine, INFORM forwarded to operator). With `n` machines competing for the same colour, each machine broadcasts a PROPOSE to `n-1` peers, adding `n(n-1)` PROPOSE messages. For `n=1` (one machine per colour, as in this deployment), no PROPOSE messages are exchanged.

---

### 16.11 Phased Testing Strategy

The Case 1 implementation is fully modular. The orchestrator can be excluded from the Docker Compose startup without affecting any other service. This enables a two-phase testing approach:

**Phase 1 — Machines only (validate the extension mechanism):**
```bash
cd my_models
docker compose up xmpp-server smia-machine0 smia-machine1 smia-machine2 smia-operator
```
The operator GUI discovers all three machines (their AASXs are in the shared `aas/` folder). The operator can send `Capability_PickPiece` directly to any machine with `skillParams: {position: 0}`. This validates:
- That `smia_machine_starter.py` correctly overrides the Docker entrypoint
- That `ExtensibleSMIAAgent` boots, self-configures, and registers `machineAvailValue`
- That the physical crane responds to direct capability requests from the operator
- That `GET /smia/lego/availability` returns `1.0` normally and `0.0` during execution

**Phase 2 — Full orchestration (validate FIPA-CNP flow):**
```bash
cd my_models
docker compose up
```
The operator sees all four agents including `smia_orch@ejabberd`. A capability request with `skillParams: {color: "red"}` is sent to the orchestrator. The expected log sequence in `smia-orchestrator` is:

```
OrchestratorDispatchBehaviour started.
new CSSRequest from operator (thread=...)
Eligible machine: SMIA_agent@ejabberd (color=red) from LEGO_factory_case0.aasx
CFP sent to SMIA_agent@ejabberd (neg_thread=...)
received winner INFORM (thread=...) from SMIA_agent@ejabberd
execution REQUEST sent to SMIA_agent@ejabberd (exec_thread=...)
result forwarded to operator (exec_thread=...)
```

If the orchestrator returns a `FAILURE`, the most common causes are: colour misspelling in `skillParams`, no AASX in the folder with that colour in its `Capability_PickPiece`, or the `Orchestrator_case0.aasx` not having the correct CSS structure (which would prevent SMIA from booting).

---

## 17. Discussion and Future Work

### 17.1 Discussion

This work demonstrates that the AAS Type 3 + CSS paradigm provides a technically viable foundation for flexible manufacturing. The key strength of the approach is the **complete decoupling** between the capability model and the implementation: an operator (or an orchestration system) can request a capability without knowing anything about how it will be executed. The execution is determined entirely by the semantic model at runtime.

Several challenges and limitations were encountered:

**Complexity of AAS authoring**: Creating a correct AASX model with all required semantic IDs and correct element types is non-trivial. Errors in the model (wrong element type, wrong semanticId) lead to silent failures that are difficult to diagnose. Tooling improvements in AASX Package Explorer and better validation tools would significantly reduce this barrier.

**Limited error reporting**: When SMIA's `InitAASModelBehaviour` fails (e.g., due to an MRO crash), it logs the error but continues; capabilities and skills are simply not registered. The operator GUI shows "0 capabilities" with no indication of why. Better error propagation would improve the developer experience.

**Single-hop execution**: Case 0 involves a single SMIA agent executing a capability on behalf of a single operator. More realistic flexible manufacturing scenarios require multi-agent negotiation: multiple agents offering overlapping capabilities, dynamic task allocation, and conflict resolution. These are addressed in the broader SMIA research agenda but were not within the scope of this TFG.

**No security layer**: The current deployment uses no authentication for HTTP calls (Node-RED accepts any POST without credentials). In a production environment, appropriate security measures (TLS, API keys, OAuth) would be required.

### 17.2 Future Work

Building on the Case 0 and Case 1 baselines, several extensions are planned:

1. **Case 1 extensions**: Case 1 (multi-agent orchestration with three machine SMIAs and an orchestrator) has been implemented and validated (§16). Future improvements include: strict busy-rejection (returning FAILURE to the operator when all machines are busy rather than queueing the task); multi-machine-per-colour support (currently one machine per colour, but the protocol supports multiple by design); and upstream contribution of the FIPA-CNP initiator behaviour to the SMIA repository.

2. **Formal capability matching**: Extend the CSS model to include capability constraints (pre/post-conditions) and implement reasoning-based capability matching — checking not just whether a capability exists but whether it can be executed given the current state.

3. **AAS lifecycle integration**: Connect SMIA to an AAS server (e.g., BaSyx server) to expose the digital twin via the standard AAS API, enabling interoperability with third-party AAS-compliant systems.

4. **Human agent integration**: Integrate SMIA-HI (Human Interface) to represent a human worker as an AAS agent, enabling collaborative scenarios between human and machine agents.

5. **Process orchestration**: Integrate SMIA-PE (Production Execution) to interpret BPMN workflows and coordinate multi-agent execution sequences.

6. **Validation with additional physical assets**: Apply the same AAS + CSS methodology to different physical assets (e.g., a transport AGV, a pick-and-place robot) to validate the generality of the approach.

---

## 18. Glossary

| Term | Definition |
|---|---|
| **AAS** (Asset Administration Shell) | The IDTA standard for representing manufacturing assets as structured digital twins. |
| **AASX** | ZIP-based file format for storing AAS models, with an internal XML representation. |
| **AID** (Asset Interfaces Description) | IDTA submodel standard (02017) for describing communication interfaces of an asset, based on W3C WoT. |
| **Agent** | An autonomous software entity that perceives its environment, makes decisions, and acts to achieve goals. |
| **AssetCapability** | A capability offered by a physical manufacturing asset (in the SMIA CSS ontology). |
| **basyx-python-sdk** | Python library for parsing and working with AAS models (maintained by Eclipse BaSyx). |
| **CSS** (Capability-Skill-Service) | An ontological model for describing manufacturing functions at three abstraction levels. |
| **Cyber-Physical System (CPS)** | A physical process tightly coupled with a computing/communication infrastructure. |
| **Docker** | A container platform for packaging and running software in isolated environments. |
| **Docker Compose** | A tool for defining and running multi-container Docker applications. |
| **ejabberd** | A production-grade open-source XMPP server written in Erlang. |
| **fischertechnik Training Factory Industry 4.0 24V** | Professional-grade industrial simulation model (ref. 554868) replicating a complete Industry 4.0 factory. Used as the physical asset in Case 0. The warehouse crane (Hochregallager) is the actuator for pick/place capabilities. The central crane with vacuum suction cup (ventose) is a separate component not covered in Case 0. |
| **FIPA-ACL** | Foundation for Intelligent Physical Agents — Agent Communication Language. Standard for structured agent messaging. |
| **GCIS** | Control and Systems Integration research group at UPV/EHU. |
| **HTTP** | Hypertext Transfer Protocol. The foundation protocol of the web. |
| **IDTA** | Industrial Digital Twin Association. The organization that maintains the AAS standard. |
| **Industry 4.0** | The Fourth Industrial Revolution, characterized by cyber-physical integration. |
| **IRI** | Internationalized Resource Identifier. A URL-like string that uniquely identifies a resource in semantic web systems. |
| **Hochregallager** | German term for high-bay warehouse. In the fischertechnik Training Factory, this is the storage area with shelved slots served by the warehouse crane. |
| **isRealizedBy** | CSS ontology object property linking a Capability to the Skill that implements it. |
| **MAS** (Multi-Agent System) | A system composed of multiple autonomous agents that interact with each other. |
| **MES** (Manufacturing Execution System) | Software that tracks and controls manufacturing processes on the shop floor. |
| **MQTT** | Lightweight publish-subscribe messaging protocol for IoT and industrial communication. |
| **MRO** (Method Resolution Order) | Python's algorithm for determining the order in which base classes are searched during method lookup in multiple inheritance. |
| **Node-RED** | Flow-based visual programming tool for IoT and protocol bridging. |
| **OPC UA** | OPC Unified Architecture. Industrial communication standard for machine-to-machine data exchange. |
| **OWL** | Web Ontology Language. W3C standard for defining ontologies on the Web. |
| **RAMI 4.0** | Reference Architectural Model for Industrie 4.0. Three-dimensional framework for Industry 4.0 concepts. |
| **RDF** | Resource Description Framework. Graph-based data model for semantic web knowledge. |
| **REST** | Representational State Transfer. Architectural style for building HTTP APIs. |
| **SemanticId** | A URI assigned to an AAS element that links it to an external standard or ontology. |
| **SMIA** | Self-configurable Manufacturing Industrial Agents. Open-source AAS+CSS agent framework. |
| **SPADE** | Smart Python Agent Development Environment. Python framework for building XMPP-based multi-agent systems. |
| **Skill** | CSS concept: a concrete implementation of a Capability. |
| **SkillInterface** | CSS concept: describes how a Skill is accessed (its invocation interface). |
| **SubmodelElementCollection (SMC)** | AAS element type: a named container of other SubmodelElements. |
| **TFG** (Trabajo de Fin de Grado) | Spanish term for Bachelor's Thesis. |
| **Ventose** | Vacuum suction cup. Refers to the central crane of the fischertechnik Training Factory that uses a vacuum gripper. Not part of Case 0. |
| **UPV/EHU** | University of the Basque Country (Universidad del País Vasco / Euskal Herriko Unibertsitatea). |
| **WoT** (Web of Things) | W3C standard for describing IoT devices and their interfaces in a machine-readable way. |
| **XMPP** | Extensible Messaging and Presence Protocol. Open standard for real-time messaging, used as transport for SMIA agent communication. |

---

## 19. References

### Standards and Specifications

1. Industrial Digital Twin Association (IDTA). *Details of the Asset Administration Shell — Part 1: The Exchange of Information between Partners in the Value Chain of Industrie 4.0 (Version 3.0)*. IDTA 01001-3-0, 2023.

2. Industrial Digital Twin Association (IDTA). *Asset Interfaces Description — Submodel Template (IDTA 02017-1-0)*. 2023.

3. Plattform Industrie 4.0. *The Plattform I4.0 Capability, Skill and Service Concept*. Federal Ministry for Economic Affairs and Energy (BMWi), 2020.

4. W3C. *Web of Things (WoT) Thing Description*. W3C Recommendation, 2020. Available: https://www.w3.org/TR/wot-thing-description/

5. OASIS. *MQTT Version 5.0 OASIS Standard*. 2019. Available: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html

6. IEEE. *FIPA ACL Message Structure Specification*. Foundation for Intelligent Physical Agents (FIPA), 2002.

### Software Frameworks and Tools

7. SMIA GitHub Repository: https://github.com/ekhurtado/SMIA

8. AASX Package Explorer: https://github.com/admin-shell-io/aasx-package-explorer

9. Eclipse BaSyx — basyx-python-sdk: https://github.com/eclipse-basyx/basyx-python-sdk

10. SPADE (Smart Python Agent Development Environment): https://github.com/javipalanca/spade

11. ejabberd: https://www.ejabberd.im/

12. Node-RED: https://nodered.org/

13. Eclipse Mosquitto: https://mosquitto.org/

14. owlready2: https://owlready2.readthedocs.io/

### Scientific Papers

15. E. Hurtado, A. Burgos, A. Armentia, and O. Casquero, *"Self-configurable Manufacturing Industrial Agents (SMIA): a standardized approach for digitizing manufacturing assets"*, Journal of Industrial Information Integration, vol. 47, p. 100915, Sept. 2025. DOI: 10.1016/j.jii.2025.100915

16. E. Hurtado, I. Sarachaga, A. Armentia, and O. Casquero, *"An open-source reference framework for the implementation of type 3 Asset Administration Shells"*, Software Impacts, vol. 27, p. 100807, Apr. 2026. DOI: 10.1016/j.simpa.2025.100807

17. Leitão, P., Colombo, A. W., and Karnouskos, S. (2016). *Industrial automation based on cyber-physical systems technologies: Prototype implementations and challenges*. Computers in Industry, 81, 11–25.

18. Grieves, M. (2014). *Digital Twin: Manufacturing Excellence through Virtual Factory Replication*. White Paper.

19. Monostori, L. et al. (2016). *Cyber-physical systems in manufacturing*. CIRP Annals, 65(2), 621–641.

20. Brandl, D., & Lepuschitz, W. (2022). *Asset Administration Shell: A survey on its implementations and use cases*. IEEE Access, 10, 78671–78681.

---

*This memoire is a living document and will be updated as the project evolves. Last updated: 2026-03-05.*
