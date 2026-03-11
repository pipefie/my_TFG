# CLAUDE.md — Full Project Context for Case 0

> This file gives Claude (or any AI assistant) the complete picture of what this project is, what has been implemented, what works, what is patched, and how to help with it. Read this before anything else.

---

## 1. Project Overview

**What:** Bachelor's thesis (TFG — Trabajo de Fin de Grado) in Data Science at UPV/EHU.
**Title:** "Flexible manufacturing based on digital twins using AAS and CSS model"
**Author:** Working at Vicomtech (DIDA lab), tutored by UPV/EHU.
**Status:** Case 0 is **fully working end-to-end** as of 2026-03-04.

**What we are proving:** A manufacturing agent (SMIA) can configure itself entirely from a standard digital twin (AAS + CSS ontology) and execute physical actions on a real factory machine — with **zero asset-specific code** inside the agent.

---

## 2. What is SMIA

**SMIA** = Self-configurable Manufacturing Industrial Agents.
- Open-source Python framework: GitHub `https://github.com/ekhurtado/SMIA`
- Docker image: `ekhurtado/smia:latest-alpine`
- Author: Ekaitz Hurtado, UPV/EHU (Vicomtech spinoff)
- Scientific papers:
  - DOI: 10.1016/j.jii.2025.100915 (Journal of Industrial Information Integration)
  - DOI: 10.1016/j.simpa.2025.100807 (Software Impacts)

**How SMIA works (startup sequence):**
1. Reads `smia-initialization.properties` → gets XMPP credentials, AAS file path, ontology settings
2. Loads the AASX file (ZIP containing `.aas.xml` + supplementary files)
3. Loads the CSS OWL ontology (from inside the AASX if `ontology.inside-aasx=true`)
4. Introspects AAS elements: wraps Capabilities as `ExtendedCapability`, Skills as `ExtendedSimpleSkill` (if Property) or `ExtendedComplexSkill` (if SMC)
5. Resolves relationships: `isRealizedBy` (Capability→Skill), `accessibleThroughAssetService` (Skill→AID action)
6. Creates `AssetConnection` objects from the AID submodel (HTTP endpoint + method)
7. Enters `StateRunning` — listens for FIPA-ACL `REQUEST` messages over XMPP
8. On request: looks up Capability → Skill → AssetConnection → executes HTTP POST

**Key dependencies:**
- `spade 4.0.3` — Python multi-agent framework (XMPP-based)
- `basyx-python-sdk 1.2.1` — AAS parsing
- `owlready2 0.48` — OWL ontology loading
- `python 3.12` (inside container)

---

## 3. What is Case 0

**Physical asset:** fischertechnik Training Factory Industry 4.0 24V (ref. 554868)
- Product: https://www.fischertechnik.de/es-es/productos/industria-y-universidades/modelos-de-simulacion/554868-training-factory-industry-4-0-24v
- **Scope:** ONLY the **warehouse crane (Hochregallager)** is wired in Case 0
- NOT in scope: the central crane with ventose (vacuum suction cup) — it is physically present but not connected in Case 0

**What Case 0 does:** An operator clicks a button in the SMIA Operator web GUI → the warehouse crane in the fischertechnik Training Factory moves to pick a piece from a slot.

**Naming note:** Files and identifiers use `LEGO_factory`, `/smia/lego/pick`, `vicom/61/piso_0/lab/lego/commands` — these are **historical artifacts** from early development. They physically refer to the fischertechnik factory and its warehouse crane. Do not rename them; they appear in code and running configs.

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
[smia-operator container]  — GUI agent, scans aas/ folder for SMIAs
    │ FIPA-ACL REQUEST over XMPP port 5222
    ▼
[ejabberd container]  — XMPP routing
    │ delivers to SMIA_agent@ejabberd
    ▼
[smia container]
    │ 1. Resolve: Capability_PickPiece → isRealizedBy → Skill_PickPiece
    │ 2. Resolve: Skill_PickPiece → accessibleThroughAssetService → AID action pickPiece
    │ 3. Read from AID: base=http://192.168.155.10:1880, href=/smia/lego/pick, method=POST
    │ HTTP POST {"color":"...", "position":...}
    ▼
[Node-RED — DIDA Central 192.168.155.10:1880]
    │ Function: extract position, default=0, build payload bandera_custom:<position>
    │ MQTT publish QoS=1  topic=vicom/61/piso_0/lab/lego/commands
    ▼
[Mosquitto central — DIDA]
    │ MQTT bridge (pre-configured)
    ▼
[Mosquitto local — fischertechnik Windows]
    │ subscribe vicom/61/piso_0/lab/lego/commands
    ▼
[fischertechnik control software]
    ▼
[Warehouse crane macro — picks from slot <position>]
```

### 4.3 Docker Compose network

All three containers (`ejabberd`, `smia`, `smia-operator`) share the same Docker bridge network. The hostname `ejabberd` resolves automatically inside the network — no `/etc/hosts` needed. Agents wait for ejabberd's health check (port 5222) before starting.

### 4.4 Architecture decisions (summary)

**Docker Compose:** Chosen to solve shared infrastructure problem — all three services need the same XMPP hostname. Alternatives (bare-metal, K8s, Swarm) were rejected as either non-reproducible or overkill. Weakness: single host = single point of failure.

**Edge + Central:** Each lab machine has a dedicated edge stack (mosquitto + node-red + postgres). DIDA central aggregates cross-machine data. **Trade-off for Case 0:** SMIA's AID points to central (192.168.155.10:1880), not a fischertechnik-specific edge node, because the fischertechnik machine is Windows and cannot run a custom HTTP server. Central is in the critical command path for Case 0. Full justification in `memoire.md §14.7`.

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
│   └── playBook.md                         ← operational runbook (verified runtime values)
│
├── src/smia/agents/smia_agent.py           ← PATCHED file (mounted into smia container)
│
└── additional_tools/extended_agents/smia_operator_agent/
    ├── operator_gui_behaviours.py          ← mounted into smia-operator container
    ├── operator_gui_logic.py               ← mounted into smia-operator container
    └── htmls/                              ← mounted into smia-operator container
```

**Important:** Only `.aasx` files should be in `my_models/aas/`. Any other file (backups, XML exports) causes the smia-operator GUI to crash with a 500 error during AAS discovery.

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

`AAS_ID=urn:uuid:6475_0111_2062_9689` in docker-compose tells SMIA to use the `LEGO_factory` shell (not the operator's own AASX also in the same folder).

### 7.2 Submodel: AssetInterfacesDescription (AID)
semanticId: `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel`

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

```
CapabilitiesAndSkills
├── Capability_PickPiece   (SMC, semanticId: css-smia#AssetCapability)
│   ├── qualifier: hasLifecycle = OFFER
│   └── position (Property xs:int)
├── Capability_PlacePiece  (SMC, same)
├── Skill_PickPiece        ← MUST be Property, NOT SMC (see §8 below)
│   ├── valueType: xs:string
│   └── qualifier: hasImplementationType = OPERATION
└── Skill_PlacePiece       ← same, Property
```

### 7.4 Submodel: SemanticRelationships

4 RelationshipElements — this is the CSS wiring:

| idShort | semanticId | first | second |
|---|---|---|---|
| `rel_CapPick_isRealizedBySkill_SkillPick` | `css#isRealizedBy` | Capability_PickPiece | Skill_PickPiece |
| `rel_CapPlace_isRealizedBySkill_SkillPlace` | `css#isRealizedBy` | Capability_PlacePiece | Skill_PlacePiece |
| `rel_SkillPick_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | Skill_PickPiece | AID/.../pickPiece |
| `rel_SkillPlace_hasSkillInterface` | `css-smia#accessibleThroughAssetService` | Skill_PlacePiece | AID/.../placePiece |

### 7.5 Embedded files in the AASX package
- `aasx/CSS-ontology-smia.owl` — the CSS ontology (36KB)
- `aasx/smia-initialization.properties` — template only; runtime values come from Docker env vars

---

## 8. CRITICAL: Why Skills Must Be Property Elements (Not SMC)

**Problem:** When Skills are defined as `SubmodelElementCollection`, SMIA tries to create a Python class using multiple inheritance: `ExtendedComplexSkill + ExtendedSubmodelElementCollection`. Both base classes define `HasSemantics` and `Qualifiable` in conflicting MRO orders. Python raises a `TypeError: Cannot create a consistent method resolution order (MRO)` during `InitAASModelBehaviour`, which means the agent boots but never becomes operational.

**Fix:** Define Skills as `Property` elements (valueType: xs:string). SMIA then uses `ExtendedSimpleSkill` which has no MRO conflict.

**How to spot the symptom:** SMIA logs show `InitAASModelBehaviour` starting but never completing. The agent never reaches `StateRunning`. The operator GUI loads but the Submit button spins forever.

---

## 9. smia_agent.py Patch

**Why it exists:** SMIA's method `get_asset_connection_by_model_reference()` matched AID references using Python object identity (`is` / `==`). The reference object obtained during skill execution was a different Python instance from the one stored during AAS initialization, so the lookup returned `None` and the HTTP call was never made.

**What was fixed:** Two additional comparison strategies added:
1. String comparison: `str(conn_ref) == str(asset_connection_ref)`
2. Key-tuple comparison: normalize `(type, value)` tuples from reference key lists

**How it's applied:** Volume mount in docker-compose.yml:
```yaml
- ../src/smia/agents/smia_agent.py:/usr/local/lib/python3.12/site-packages/smia/agents/smia_agent.py
```
This overrides the file inside the container image. If you pull a new version of `ekhurtado/smia:latest-alpine`, verify the patch is still compatible.

**Long-term fix:** Submit a PR to the upstream SMIA repo.

---

## 10. CSS Ontology

File: `my_models/ontology/CSS-ontology-smia.owl` (also embedded in the AASX at `aasx/CSS-ontology-smia.owl`)

The OWL ontology extends `http://www.w3id.org/hsu-aut/css` with SMIA-specific classes. SMIA loads it via `owlready2` at startup when `ontology.inside-aasx=true`.

### Key IRIs (verified from `src/smia/css_ontology/css_ontology_utils.py`)

| Concept | IRI |
|---|---|
| Capability | `http://www.w3id.org/hsu-aut/css#Capability` |
| **AssetCapability** | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` ← use this for semanticId |
| Skill | `http://www.w3id.org/hsu-aut/css#Skill` |
| isRealizedBy | `http://www.w3id.org/hsu-aut/css#isRealizedBy` |
| **accessibleThroughAssetService** | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` |

### CSS chain in Case 0
```
Capability_PickPiece  --isRealizedBy-->  Skill_PickPiece
                                              │
                                    --accessibleThroughAssetService-->
                                              │
                                         AID/actions/pickPiece
                                              │
                                    HTTP POST http://192.168.155.10:1880/smia/lego/pick
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
ontology.inside-aasx=true   # reads .owl from inside the AASX ZIP
```

### ejabberd.yml (key settings)
- `hosts: [localhost, ejabberd]` — ejabberd responds to both
- `mod_register: ip_access: all` — allows auto-registration via API
- `mod_mqtt: {}` — MQTT over XMPP enabled
- Ports: 5222 (XMPP C2S), 5269 (S2S), 5280 (HTTP), 5443 (HTTPS/WS)

---

## 13. Node-RED Flow (DIDA Central — 192.168.155.10:1880)

File to import: `my_models/flow_dida_central_lego.json`

Flow structure:
```
HTTP In (POST /smia/lego/pick)
    → JSON parse
    → Function node:
         position = msg.payload.position
                 || msg.query.position
                 || msg.payload.skillParams?.position
                 || DEFAULT_POSITION (= 0)
         validate: 0 ≤ position ≤ 8
         payload = "bandera_custom:" + position
    → MQTT Out (broker: mosquitto-central:1883, topic: vicom/61/piso_0/lab/lego/commands, QoS=1)
    → HTTP Response (JSON: {status:"ok", payload:..., topic:...})
```

Test directly (bypass SMIA):
```bash
curl -i -X POST http://192.168.155.10:1880/smia/lego/pick \
  -H 'Content-Type: application/json' \
  -d '{"position":0}'
```

---

## 14. Deployment — Quick Reference

```bash
# From repo root (SMIA/):
docker compose -f my_models/docker-compose.yml up -d

# Check status:
docker compose -f my_models/docker-compose.yml ps

# Watch logs:
docker compose -f my_models/docker-compose.yml logs -f smia smia-operator xmpp-server

# Stop:
docker compose -f my_models/docker-compose.yml down

# Full reset (delete ejabberd data):
docker compose -f my_models/docker-compose.yml down -v
```

### Healthy startup signatures in logs

**ejabberd:** `Starting ejabberd ... done`
**smia:** `AAS model initialized.` then `Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']`
**smia-operator:** `Starting web server on port 10000`

**Operator GUI:** http://localhost:10000/smia_operator → click Load → SMIA_agent appears → select Capability → Submit

---

## 15. Troubleshooting Quick Reference

| Symptom | Most likely cause | Fix |
|---|---|---|
| `KeyError: 'ContainerConfig'` on `docker-compose up` | Using Docker Compose v1 | Use `docker compose` (space, v2) |
| ejabberd loops, never healthy | ejabberd.yml syntax error or port conflict | Check `docker logs ejabberd` |
| SMIA exits after boot, never reaches StateRunning | Skills defined as SMC (MRO crash) | Redefine Skills as Property in AASX PE |
| Operator GUI `500 Internal Server Error` on Load | Non-AASX file in `my_models/aas/` | Remove backups, XMLs, etc. from `aas/` |
| Submit spins indefinitely (no HTTP call in logs) | `smia_agent.py` patch not mounted | Check volume mount path is correct |
| HTTP POST succeeds but crane does not move | MQTT bridge down, wrong topic/payload | Check Node-RED debug, check bridge between central and fischertechnik mosquitto |
| XMPP auth failure | `AGENT_PASSWD` not matching registered password | `CTL_ON_CREATE` registered the account; verify `AGENT_PASSWD` env var value |

---

## 16. Documents Index

| File | Purpose | When to use |
|---|---|---|
| `CLAUDE.md` (this file) | AI assistant context — full project state | First thing to read |
| `doc_case0.md` | Full technical reference — AASX PE tutorial, all semantic IDs, deployment steps, troubleshooting | Replication, technical questions |
| `memoire.md` | Formal TFG academic document — explains SMIA, AAS, CSS, ontology, architecture justification | Academic writing, TFG document base |
| `presentation_case0.md` | 33-slide presentation for colleagues — walkthrough, schemas, troubleshooting, architecture decisions | Presentations, demos |
| `playBook.md` | Operational runbook — verified runtime values, step-by-step deploy/test | Day-to-day operations |

---

## 17. Current Implementation State

### What works ✓
- Full end-to-end: operator GUI → XMPP → SMIA → HTTP → Node-RED → MQTT → warehouse crane
- SMIA self-configures from AAS (no asset-specific code)
- CSS ontology resolves Capability → Skill → AID action
- Docker Compose deploys everything in one command
- Operator GUI lists SMIA, shows capabilities, executes them

### Known technical debt
- `smia_agent.py` bug fix applied via Docker volume mount (fragile if image updates) — needs upstream PR
- Central DIDA is in the critical command path for Case 0 (architectural trade-off — documented in §14.7 of memoire.md)

### What is NOT implemented yet (future cases)
- Case 1: second SMIA + multi-agent negotiation
- Case 2: capability constraint matching (pre/post-conditions)
- Case 3: SMIA-HI (human interface agent)
- Case 4: BPMN orchestration via SMIA-PE
- Case 5: AAS server (BaSyx) + standard AAS API

---

## 18. Key Identifiers and Credentials

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
