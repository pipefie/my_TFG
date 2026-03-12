# Case 0 — Implementation Walkthrough
## Flexible Manufacturing with Digital Twins: AAS + CSS + SMIA

**Andrés Felipe Fierro Fonseca — TFG Presentation**
**Physical asset:** fischertechnik Training Factory Industry 4.0 24V (ref. 554868)
**Status:** Working end-to-end ✓ (2026-03-05)

> **How to use this document:** Each `---` section is one slide. Bullet points are slide content. Code blocks and detailed paragraphs are **speaker notes** — collapse them in the presentation tool or use them to prepare your narration.

---

## Slide 1 — Title

# Case 0: Flexible Manufacturing with Digital Twins
### AAS · CSS Ontology · SMIA · Node-RED · MQTT

**Andrés Felipe Fierro Fonseca**
Universidad de Deusto · Vicomtech — Data Intelligence for Industry
Tutors: Ander García Gangoiti / Xabier Oregui Biain
TFG — Degree in Data Science

Physical asset: **fischertechnik Training Factory Industry 4.0 24V**

---

## Slide 2 — Agenda

1. What are we building and why?
2. Physical asset: fischertechnik Training Factory
3. System architecture (3 machines, full data flow)
4. Key technologies in 60 seconds each
5. The AAS model: design decisions + AASX walkthrough
6. CSS ontology: how SMIA reads capabilities
7. Communication layer: XMPP → HTTP → MQTT → crane
8. Docker deployment: configuration and wiring
9. **Why these architecture choices?** (decision justification + alternatives)
10. Live demo / results
11. Problems we hit and how we solved them

---

## Slide 3 — The Goal: What Case 0 Does

**One sentence:** An operator clicks a button in a web GUI, and a warehouse crane in a real factory moves — with zero asset-specific code in the software.

### How?
- The crane is described as a **digital twin** (AAS)
- The digital twin says: *"I can pick pieces, and here's the HTTP endpoint to call"*
- A software agent (SMIA) reads that description and acts on it autonomously
- No hard-coded IP, no hard-coded endpoint, no asset-specific logic

### The claim we are validating
> Can a manufacturing agent configure itself **entirely from a standard digital twin** and execute physical actions without knowing anything about the specific asset in advance?

---

## Slide 4 — The Physical Asset

### fischertechnik Training Factory Industry 4.0 24V

Professional industrial simulation model replicating a complete Industry 4.0 factory.

**What it contains:**
- High-bay warehouse (Hochregallager) + **warehouse crane** ← Case 0
- Machining center with CNC-style tool
- Conveyor belt and sorting system
- Central crane with **vacuum suction cup (ventose)** ← NOT Case 0
- Color sensor, quality control station

### Case 0 Scope
- `Capability_PickPiece` → **warehouse crane only**
- `Capability_PlacePiece` → **warehouse crane only**
- The ventose (central crane) is a separate component, reserved for future cases

> **Speaker note:** The distinction matters because the factory has two cranes with completely different mechanics. The warehouse crane moves along X/Y/Z axes to reach storage slots. The ventose uses vacuum to grip and move pieces between stations. Case 0 only models and uses the warehouse crane. When you look at the AAS model you will see that the capabilities and skills are only connected to the warehouse crane's HTTP endpoint — not any other component of the factory.

---

## Slide 5 — System Architecture: 3 Machines

```
┌─────────────────────────────────┐
│  Linux Dev Machine              │
│                                 │
│  Docker Compose                 │
│  ┌──────────┐   ┌──────────┐   │
│  │ ejabberd │   │   smia   │   │
│  │  (XMPP)  │◄──►  (agent) │   │
│  └──────────┘   └────┬─────┘   │
│  ┌──────────┐        │ HTTP    │
│  │  smia-   │        │ POST    │
│  │ operator │        │         │
│  │ (GUI:    │        │         │
│  │ :10000)  │        │         │
│  └──────────┘        │         │
└─────────────────────-┼─────────┘
                       │ 192.168.155.10:1880
          ┌────────────▼────────────┐
          │   DIDA Central Machine  │
          │   Node-RED + Mosquitto  │
          └────────────┬────────────┘
                       │ MQTT bridge
          ┌────────────▼────────────┐
          │ fischertechnik Windows  │
          │  Warehouse crane macro  │
          └─────────────────────────┘
```

| Machine | Role |
|---|---|
| Linux dev | Runs all 3 Docker containers |
| DIDA Central (192.168.155.10) | HTTP→MQTT bridge via Node-RED |
| fischertechnik/Windows | Physical crane control |

---

## Slide 6 — Full Data Flow (End-to-End)

```
[Browser]
    │  HTTP :10000/smia_operator
    ▼
[smia-operator container]
    │  FIPA-ACL REQUEST over XMPP :5222
    ▼
[ejabberd container]
    │  routes to smia_agent@ejabberd
    ▼
[smia container]
    │  1. reads AAS: Capability_PickPiece
    │  2. → isRealizedBy → Skill_PickPiece
    │  3. → accessibleThrough → AID/pickPiece
    │  4. reads: base=192.168.155.10:1880, href=/smia/lego/pick
    │  HTTP POST http://192.168.155.10:1880/smia/lego/pick
    ▼
[Node-RED — DIDA Central]
    │  function: extract position, build payload
    │  MQTT publish QoS=1
    │    topic:   vicom/61/piso_0/lab/lego/commands
    │    payload: bandera_custom:0
    ▼
[Mosquitto — central broker]
    │  MQTT bridge
    ▼
[fischertechnik Windows machine]
    │  subscriber → control software
    ▼
[Warehouse crane picks from slot 0]
```

> **Speaker note:** The key insight here is step 3–4: SMIA does not have the URL hard-coded anywhere. It reads the AAS model at startup, finds the AID submodel, and builds the URL from `base + href`. If we change the Node-RED server IP, we only update the AAS model — not the code.

---

## Slide 7 — Technologies in 60 Seconds Each

| Technology | What it is | Our use |
|---|---|---|
| **AAS** (Asset Administration Shell) | Standard digital twin format (IDTA/I4.0) | Describes the factory crane: capabilities, HTTP interface, metadata |
| **CSS Ontology** (OWL) | Semantic model: Capability→Skill→Interface | Tells SMIA what capabilities exist and how to execute them |
| **SMIA** | Python agent (SPADE + AAS + CSS) | The "brain" that reads the AAS and calls the crane |
| **ejabberd** | XMPP server | Routes messages between operator agent and SMIA agent |
| **FIPA-ACL** | Agent message standard | Format of the REQUEST/INFORM messages |
| **Node-RED** | Visual flow tool (HTTP→MQTT bridge) | Receives HTTP from SMIA, publishes MQTT to crane |
| **MQTT** | Lightweight pub-sub protocol | Carries the crane command to the fischertechnik machine |
| **Docker Compose** | Multi-container orchestration | Runs ejabberd + smia + smia-operator together |
| **AASX Package Explorer** | Windows GUI to author `.aasx` files | Used to build the AAS model for the factory |

---

## Slide 8 — AAS: What It Is (1 Slide)

### Asset Administration Shell = Structured Digital Twin

```
AssetAdministrationShell (LEGO_factory)
│  id: urn:uuid:6475_0111_2062_9689
│
├── Submodel: AssetInterfacesDescription   ← HOW to talk to the crane (HTTP)
├── Submodel: CapabilitiesAndSkills        ← WHAT the crane can do
├── Submodel: SemanticRelationships        ← HOW capabilities connect to HTTP calls
└── Submodel: SubmodelWithCapabilitySkillOntology  ← concept catalog
```

**Key concept: semanticId**
Every element carries a URI that links it to a standard or ontology.

```
Property "base"
  value: http://192.168.155.10:1880
  semanticId: https://www.w3.org/2019/wot/td#baseURI   ← says: "this is a WoT base URL"
```

This is what makes AAS interoperable: two systems that don't know each other can agree on meaning via shared semanticIds.

---

## Slide 9 — CSS Ontology: Capability→Skill→Interface

### The Chain That Drives Everything

```
Capability_PickPiece          ← WHAT (abstract, implementation-independent)
    │  [css-smia:AssetCapability — physical machine capability]
    │  [hasLifecycle = OFFER — this asset is advertising it]
    │
    │  isRealizedBy
    ▼
Skill_PickPiece               ← HOW (concrete implementation reference)
    │
    │  accessibleThroughAssetService  ← physical execution path
    ▼
AID/InterfaceHTTP/            ← WHERE (the actual HTTP call)
    InteractionMetadata/
    actions/pickPiece
    │
    │  forms.href + base
    ▼
POST http://192.168.155.10:1880/smia/lego/pick
```

**SMIA reads this chain from the AAS model at startup.**
No code changes needed when the asset changes — just update the AAS.

### Two types of Capability (paper Fig. 4)

| Type | What it represents | Case 0? |
|---|---|---|
| `css-smia:AssetCapability` | Physical capability of the **machine** (PickPiece, PlacePiece) | ✓ **yes** |
| `css-smia:AgentCapability` | Capability of the **DT agent itself** (Negotiate, Coordinate) | ✗ future |

Case 0 only uses `AssetCapability` because we are modelling the warehouse crane's physical actions. `AgentCapability` will be relevant when SMIA agents need to negotiate with each other (multi-agent scenarios, Case 1+).

> **Speaker note (paper §3.2):** The CSS ontology is an extension of the CaSkade-Automation CSS-ontology v1.0.1. SMIA adds two subclasses of `css:Capability`: `AssetCapability` for physical machine functions and `AgentCapability` for the DT's own coordination functions. The chain — Capability → isRealizedBy → Skill → accessibleThroughAssetService → SkillInterface → AID action — is the complete path SMIA follows when it receives a REQUEST message. Without the CSS model, someone would hard-code "if capability is PickPiece, call this URL". With CSS, SMIA follows the chain generically: it works for any capability as long as it is correctly described in the AAS.

---

## Slide 10 — The AAS Model We Built: Overview

### File: `LEGO_factory_case0.aasx`
(Historical name — models the fischertechnik warehouse crane)

**Two AAS shells in one package:**

| Shell | id | Purpose |
|---|---|---|
| `LEGO_factory` | `urn:uuid:6475_0111_2062_9689` | Digital twin of the factory warehouse crane |
| `SMIA_agent` | `urn:uuid:6373_1111_2062_6896` | Digital twin of the software agent |

**Four submodels (in `LEGO_factory`):**
1. `SubmodelWithCapabilitySkillOntology` — CSS ConceptDescription catalog
2. `AssetInterfacesDescription` — HTTP endpoint descriptions (AID standard)
3. `CapabilitiesAndSkills` — what the crane can do
4. `SemanticRelationships` — the CSS graph connecting everything

**Embedded files in the AASX package:**
- `aasx/CSS-ontology-smia.owl` — the CSS OWL ontology (loaded by SMIA at startup)
- `aasx/smia-initialization.properties` — template (not used at runtime)

---

## Slide 11 — AASX Package Explorer: Creating the Package

### Tool: AASX Package Explorer (Windows, free, open-source)
Download: `https://github.com/admin-shell-io/aasx-package-explorer/releases`
No install needed — extract ZIP, run `AasxPackageExplorer.exe`.

### Steps to create the package

**Step 1: New package**
```
File → New → AASX Package
Save as: LEGO_factory_case0.aasx
```

**Step 2: Add two AAS shells**
```
Add AAS: idShort=LEGO_factory, id=urn:uuid:6475_0111_2062_9689
Add AAS: idShort=SMIA_agent,   id=urn:uuid:6373_1111_2062_6896
```

**Step 3: Embed the CSS ontology**
```
AASX → Add supplementary file
File: CSS-ontology-smia.owl (from my_models/ontology/)
Internal path: aasx/CSS-ontology-smia.owl
```

> **Speaker note:** Embedding the ontology in the AASX is critical because `smia-initialization.properties` has `ontology.inside-aasx=true`. This tells SMIA: "find the OWL file inside the ZIP package, at path `aasx/CSS-ontology-smia.owl`." If the file is missing from the package, SMIA fails to load the ontology and the CSS reasoning chain breaks completely.

---

## Slide 12 — Submodel 1: AssetInterfacesDescription (AID)

### What it does: describes the HTTP endpoint of the crane

**AID Standard (IDTA 02017)** — based on W3C Web of Things

```
AssetInterfacesDescription   semanticId: …AID/1/0/Submodel
└── InterfaceHTTP            semanticId: …AID/1/0/Interface
    │                        suppl. semanticId: http://www.w3.org/2011/http  ← marks it as HTTP
    ├── EndpointMetadata     semanticId: …AID/1/0/EndpointMetadata
    │   ├── base = http://192.168.155.10:1880   semanticId: td#baseURI
    │   ├── contentType = application/json       semanticId: forContentType
    │   └── htv_methodName = POST                semanticId: http#methodName
    └── InteractionMetadata  semanticId: …AID/1/0/InteractionMetadata
        └── actions
            ├── pickPiece    semanticId: td#ActionAffordance
            │   ├── forms    semanticId: td#hasForm
            │   │   ├── href = /smia/lego/pick   semanticId: hypermedia#hasTarget
            │   │   ├── htv_methodName = POST     semanticId: http#methodName
            │   │   └── contentType = application/json
            │   └── input    semanticId: td#hasInputSchema
            │       ├── color    [Property, xs:string]
            │       └── position [Property, xs:int]
            └── placePiece   semanticId: td#ActionAffordance
                ├── forms → href=/smia/lego/place, POST, application/json
                └── input → position [xs:int]
```

**Runtime result:** SMIA builds `http://192.168.155.10:1880/smia/lego/pick` from `base + href`

---

## Slide 13 — Submodel 1: Building AID in AASX PE (Step by Step)

### In AASX Package Explorer:

```
1. Right-click LEGO_factory AAS → Add Submodel
   idShort:   AssetInterfacesDescription
   semanticId: https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel

2. Add SMC: InterfaceHTTP
   semanticId: https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Interface
   Supplemental semanticId: http://www.w3.org/2011/http

3. Inside InterfaceHTTP, add SMC: EndpointMetadata
   semanticId: https://admin-shell.io/idta/AssetInterfacesDescription/1/0/EndpointMetadata
   → Add Property: base, value=http://192.168.155.10:1880, type=xs:anyURI
     semanticId: https://www.w3.org/2019/wot/td#baseURI

4. Inside InterfaceHTTP, add SMC: InteractionMetadata
   semanticId: https://admin-shell.io/idta/AssetInterfacesDescription/1/0/InteractionMetadata
   → Add SMC: actions (no semanticId)
     → Add SMC: pickPiece
       semanticId: https://www.w3.org/2019/wot/td#ActionAffordance
       → Add SMC: forms
         semanticId: https://www.w3.org/2019/wot/td#hasForm
         → Property: href = /smia/lego/pick
           semanticId: https://www.w3.org/2019/wot/hypermedia#hasTarget
         → Property: htv_methodName = POST
           semanticId: https://www.w3.org/2011/http#methodName
         → Property: contentType = application/json
           semanticId: https://www.w3.org/2019/wot/hypermedia#forContentType
       → Add SMC: input
         semanticId: https://www.w3.org/2019/wot/td#hasInputSchema
         → Property: color (xs:string)
         → Property: position (xs:int)
     → Repeat for placePiece (href=/smia/lego/place, input: position only)
```

---

## Slide 14 — Submodel 2: CapabilitiesAndSkills

### Capabilities: what the crane can do

```
CapabilitiesAndSkills
│
├── Capability_PickPiece   [SubmodelElementCollection]
│   semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability
│   Qualifier: hasLifecycle = OFFER
│   └── position [Property, xs:int]
│
├── Capability_PlacePiece  [SubmodelElementCollection]
│   semanticId: same AssetCapability IRI
│   Qualifier: hasLifecycle = OFFER
│   └── position [Property, xs:int]
│
├── Skill_PickPiece        [Property ← NOT SubmodelElementCollection!]
│   semanticId: http://www.w3id.org/hsu-aut/css#Skill
│   valueType: xs:string
│   Qualifier: hasImplementationType = OPERATION
│
└── Skill_PlacePiece       [Property ← NOT SubmodelElementCollection!]
    semanticId: http://www.w3id.org/hsu-aut/css#Skill
    valueType: xs:string
    Qualifier: hasImplementationType = OPERATION
```

**Qualifiers** are the metadata attached to each element. They follow ontology-defined semantics.

---

## Slide 15 — CRITICAL: Why Skills Must Be Property, Not SMC

### The Problem We Hit

If you define `Skill_PickPiece` as a `SubmodelElementCollection`:

```
ERROR during startup:
Cannot create a consistent method resolution order (MRO)
for bases HasSemantics, Qualifiable
```

**What happens internally:**

```
SMIA sees Skill in an SMC
    → uses ExtendedComplexSkill as base class
    → also uses ExtendedSubmodelElementCollection as base
    → Python tries to combine them:
         ExtendedComplexSkill    → HasSemantics BEFORE Qualifiable
         ExtendedSubmodelElementCollection → Qualifiable BEFORE HasSemantics
         ↳ CONFLICT → Python crashes
```

**Symptom:** SMIA starts without error, but logs show 0 capabilities and 0 skills.

### The Fix

Define Skills as **Property** (not SMC):
```
Skill_PickPiece → Property, valueType=xs:string
```
SMIA then uses `ExtendedSimpleSkill` → no MRO conflict.

> **Speaker note:** This took a while to diagnose because SMIA does not crash loudly — it catches the MRO error internally and continues, but the skill is never registered. The operator GUI shows 0 capabilities and you see no errors. We had to trace the issue through the SMIA source code to find `add_inheritance_of_extended_class()` in `extended_submodel.py` and understand why the class creation was failing.

---

## Slide 16 — Submodel 3: SemanticRelationships

### Encoding the CSS graph in AAS form

Four `RelationshipElement` entries. Each has:
- `semanticId` = the CSS object property IRI
- `first` = model reference to the subject
- `second` = model reference to the object

```
rel_CapPick_isRealizedBySkill_SkillPick
  semanticId: http://www.w3id.org/hsu-aut/css#isRealizedBy
  first:  → CapabilitiesAndSkills/Capability_PickPiece
  second: → CapabilitiesAndSkills/Skill_PickPiece

rel_CapPlace_isRealizedBySkill_SkillPlace
  semanticId: isRealizedBy
  first:  → Capability_PlacePiece
  second: → Skill_PlacePiece

rel_SkillPick_hasSkillInterface
  semanticId: http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService
  first:  → CapabilitiesAndSkills/Skill_PickPiece
  second: → AssetInterfacesDescription/InterfaceHTTP/
             InteractionMetadata/actions/pickPiece

rel_SkillPlace_hasSkillInterface
  semanticId: accessibleThroughAssetService
  first:  → Skill_PlacePiece
  second: → .../actions/placePiece
```

### How to create in AASX PE
```
Add RelationshipElement → idShort = rel_CapPick_isRealizedBySkill_SkillPick
Set semanticId → http://www.w3id.org/hsu-aut/css#isRealizedBy
Set first → Add ModelReference → navigate: LEGO_factory > CapabilitiesAndSkills > Capability_PickPiece
Set second → Add ModelReference → navigate: LEGO_factory > CapabilitiesAndSkills > Skill_PickPiece
```

> **Speaker note:** The `second` of `rel_SkillPick_hasSkillInterface` is the deepest reference: it points all the way into the AID submodel to the specific action element (`pickPiece`). SMIA resolves this reference to the `AssetConnection` object it created for that action at startup. This resolution is what makes the mapping work at runtime.

---

## Slide 17 — The CSS Ontology: What SMIA Loads

### File: `CSS-ontology-smia.owl` (embedded in AASX, also in `my_models/ontology/`)

- OWL 2 ontology, RDF/XML format, 36 KB
- Base: **CaSkade-Automation CSS-ontology v1.0.1** (`https://github.com/CaSkade-Automation/CSS`, IRI: `http://www.w3id.org/hsu-aut/css`)
- SMIA-specific extensions: `AssetCapability`, `AgentCapability`, `accessibleThroughAssetService`

### What SMIA does with it at startup

```python
# SMIA loads the ontology at boot:
ontology.inside-aasx = true
→ reads aasx/CSS-ontology-smia.owl from inside the AASX ZIP

# For each AAS element, SMIA checks its semanticId:
if semanticId == "http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability":
    → wrap element as ExtendedCapability

if semanticId == "http://www.w3id.org/hsu-aut/css#Skill":
    → wrap element as ExtendedSkill (simple if Property, complex if SMC)

if semanticId == "http://www.w3id.org/hsu-aut/css#isRealizedBy":
    → register: Capability_PickPiece → Skill_PickPiece

if semanticId == "accessibleThroughAssetService":
    → register: Skill_PickPiece → AssetConnection(pickPiece HTTP action)
```

### Key IRIs to remember

| What | IRI |
|---|---|
| AssetCapability | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` |
| Skill | `http://www.w3id.org/hsu-aut/css#Skill` |
| isRealizedBy | `http://www.w3id.org/hsu-aut/css#isRealizedBy` |
| accessibleThroughAssetService | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` |

---

## Slide 18 — smia-initialization.properties

### Runtime configuration for the SMIA agent

File: `my_models/smia-initialization.properties`
Mounted into container at: `/smia_archive/config/smia-initialization.properties`

```properties
[DT]
dt.agentID=SMIA_agent@ejabberd   # XMPP JID (must match ejabberd account)
dt.password=asd                   # XMPP password
dt.xmpp-server=ejabberd           # ejabberd container hostname

[AAS]
aas.model.serialization=AASX
aas.model.folder=/smia_archive/config/aas   # where AASX files are mounted
aas.model.file=LEGO_factory_case0.aasx      # which file to load

[ONTOLOGY]
ontology.file=CSS-ontology-smia.owl
ontology.inside-aasx=true   # ← find the .owl INSIDE the AASX ZIP package
```

### Critical settings explained

| Setting | Why it matters |
|---|---|
| `dt.xmpp-server=ejabberd` | This is the Docker container hostname, not `localhost` |
| `aas.model.folder=/smia_archive/config/aas` | This path is inside the container (volume mounted from `./aas`) |
| `ontology.inside-aasx=true` | Without this, SMIA looks for the .owl on the filesystem and fails |

> **Speaker note:** There is a subtle difference between the properties file values and Docker env vars. Docker Compose sets `AAS_MODEL_NAME`, `AGENT_ID`, `AGENT_PASSWD` as environment variables, and these override the properties file. So the properties file is a fallback/template. The `AGENT_PASSWD` env var is critical — the old example docker-compose used a typo `AGENT_PSSWD` that was silently ignored, causing SMIA to fall back to the properties file for the password. We fixed this in our docker-compose.

---

## Slide 19 — Docker Compose: 3 Services

### `my_models/docker-compose.yml`

```yaml
services:

  xmpp-server:              # ← starts FIRST (healthcheck on port 5222)
    image: ghcr.io/processone/ejabberd
    environment:
      - CTL_ON_CREATE=! register SMIA_agent ejabberd asd ;
                             register operator001 ejabberd gcis1234
    volumes:
      - ./xmpp_server/ejabberd.yml:/opt/ejabberd/conf/ejabberd.yml
    ports: ["5222", "5269", "5280", "5443"]
    healthcheck:
      test: netstat -nl | grep -q 5222   # wait until XMPP port is up

  smia:                     # ← waits for ejabberd to be healthy
    image: ekhurtado/smia:latest-alpine
    environment:
      - AAS_MODEL_NAME=LEGO_factory_case0.aasx
      - AAS_ID=urn:uuid:6475_0111_2062_9689
      - AGENT_ID=SMIA_agent@ejabberd
      - AGENT_PASSWD=asd
    volumes:
      - ../src/smia/agents/smia_agent.py:/usr/.../smia_agent.py  ← patched file
      - ./aas:/smia_archive/config/aas                            ← our AASX files

  smia-operator:            # ← waits for ejabberd to be healthy
    image: ekhurtado/smia-use-cases:latest-operator
    environment:
      - AAS_MODEL_NAME=SMIA_Operator_article.aasx
      - AGENT_ID=operator001@ejabberd
      - AGENT_PASSWD=gcis1234
    volumes:
      - ./aas:/smia_archive/config/aas
      - ...operator_gui_behaviours.py, operator_gui_logic.py, htmls/
    ports: ["10000:10000"]
```

**Always use `docker compose` (v2) — NOT `docker-compose` (v1)**

---

## Slide 20 — Docker Compose: Key Wiring Details

### ejabberd: auto-registers both accounts

```yaml
CTL_ON_CREATE=! register SMIA_agent ejabberd asd ; register operator001 ejabberd gcis1234
```
Runs once on first container creation. Creates both XMPP accounts automatically.
`ejabberd.yml` must have `mod_register: ip_access: all` for this to work.

### SMIA: the `aas/` folder

```yaml
volumes:
  - ./aas:/smia_archive/config/aas
```
⚠️ **Only valid `.aasx` files in this folder.**
If a backup file (`.bak`, `.bak2`) is present, the scanner returns `None` for it, which crashes the operator GUI with HTTP 500.

### smia-operator: shares the same `aas/` folder

Both `smia` and `smia-operator` mount `./aas/`. The operator scans this folder to discover SMIAs. It skips files matching its own `AAS_MODEL_NAME`.

### startup order guaranteed by healthcheck

```
ejabberd starts → port 5222 up → healthcheck passes
    → smia starts (connects to ejabberd XMPP)
    → smia-operator starts (connects to ejabberd XMPP)
```

---

## Slide 21 — XMPP: How Agents Communicate

### Protocol Stack

```
FIPA-ACL message (structured content)
    wrapped in XMPP stanza (like an XML envelope)
        transported via XMPP C2S (port 5222, TLS)
            routed by ejabberd
```

### XMPP Addressing (JIDs)

```
SMIA agent:     SMIA_agent@ejabberd
Operator agent: operator001@ejabberd
```

Both agents connect to `ejabberd:5222`. The domain `ejabberd` is the Docker container hostname.

### FIPA-ACL Message Structure (paper Fig. 16)

```
Field         │ REQUEST (operator → SMIA)
──────────────┼────────────────────────────────────────────────
to            │ SMIA_agent@ejabberd
sender        │ operator001@ejabberd
performative  │ Request
ontology      │ CSSRequest       ← tells SMIA this is a CSS capability request
body          │ {"skill": "Skill_PickPiece",
              │  "constraints": [],
              │  "params": {"position": 0}}

Field         │ INFORM (SMIA → operator)
──────────────┼────────────────────────────────────────────────
performative  │ Inform
ontology      │ CSSRequest
body          │ {"status": "ok", "payload": "bandera_custom:0", ...}
```

**The `ontology` field is critical:** SMIA's `ACLHandlingBehaviour` checks this field to route the message:
- `CSSRequest` → spawns `HandleCapabilityBehaviour`
- `SvcRequest` → routes to Functional View services
- `Negotiation` → routes to negotiation behaviours (future multi-agent scenarios)

### FIPA-ACL Flow for Case 0

```
Operator → REQUEST (ontology=CSSRequest) → SMIA
SMIA: capability → skill → HTTP POST → Node-RED → MQTT → crane
SMIA → INFORM (ontology=CSSRequest) → Operator
Operator shows result in GUI
```

> **Speaker note (paper §3.3 + Fig. 16):** FIPA-ACL (Foundation for Intelligent Physical Agents — Agent Communication Language) is the standard for multi-agent communication in I4.0. The `ontology` field is what lets SMIA distinguish a capability request from a negotiation from a service call — all using the same transport. Without it, SMIA could not route the message correctly. The actual transport is XMPP — the FIPA-ACL content is the structured body. ejabberd certificate warnings in the logs are non-blocking for our local test setup.

---

## Slide 22 — Node-RED: The Protocol Bridge

### Flow structure on DIDA central (192.168.155.10:1880)

```
[HTTP In]                         [MQTT Out]
POST /smia/lego/pick   →  [JSON]  →  [Function]  →  topic: vicom/61/piso_0/lab/lego/commands
                                                        payload: bandera_custom:<pos>
                                                        broker: mosquitto-central:1883
                                                        QoS: 1
                                        ↓
                               [HTTP Response]
                               {"status":"ok","payload":"bandera_custom:0",...}
```

### Import the flow

```
Node-RED UI → top-right menu → Import
Paste or upload: my_models/flow_dida_central_lego.json
Click Deploy
```

### Function node logic

```javascript
// Priority order for position extraction:
position = msg.payload.position
         ?? msg.req.query.position
         ?? msg.payload.skillParams.position
         ?? DEFAULT_POSITION (= 0)   ← fallback so SMIA's request never fails

// Validation
if (position < 0 || position > 8) → return HTTP 400

msg.topic   = "vicom/61/piso_0/lab/lego/commands"
msg.payload = "bandera_custom:" + position
```

> **Speaker note:** The `DEFAULT_POSITION = 0` fallback was added specifically because SMIA, in its current implementation, sends the capability request without including the `position` parameter in the expected field name. Rather than fixing the SMIA side (which would require deeper patching), we made Node-RED resilient. In practice, the crane moves to position 0 which is the defined test position for Case 0.

---

## Slide 23 — MQTT Chain: Central to Factory

### Broker chain

```
Node-RED publishes to → mosquitto-central (DIDA central, port 1883)
                            ↓
                    MQTT bridge (pre-configured)
                            ↓
                    Mosquitto (fischertechnik Windows machine)
                            ↓
                    Control software subscribes to topic
                            ↓
                    Warehouse crane macro executes
```

### The message

```
Topic:   vicom/61/piso_0/lab/lego/commands
Payload: bandera_custom:0
QoS:     1 (at least once delivery)
```

The topic `vicom/61/piso_0/lab/lego/commands` uses a legacy name — it was named when the setup used LEGO hardware. The topic is now subscribed by the fischertechnik machine's control software, which maps `bandera_custom:<n>` to warehouse slot `n`.

### Quick test (bypass SMIA entirely)

```bash
curl -i -X POST http://192.168.155.10:1880/smia/lego/pick \
  -H 'Content-Type: application/json' \
  -d '{"position":0}'
```
Expected: HTTP 200, MQTT publish, crane moves.

---

## Slide 24 — Startup and Healthy State Verification

### Start everything

```bash
cd /path/to/SMIA
docker compose -f my_models/docker-compose.yml up -d
docker compose -f my_models/docker-compose.yml ps
```

### Watch logs

```bash
docker compose -f my_models/docker-compose.yml logs -f smia smia-operator xmpp-server
```

### Expected healthy smia logs

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

If you see `Analyzed capabilities: []` → something is wrong with the AAS model (wrong semanticIds, wrong element types, .bak file in aas/ folder).

---

## Slide 25 — Troubleshooting We Encountered (Part 1)

### Problem 1: `docker-compose up` crashes with `KeyError: 'ContainerConfig'`

**Cause:** `docker-compose` v1 (legacy binary) is incompatible with current Docker image metadata format.

**Fix:**
```bash
# DON'T:
docker-compose -f my_models/docker-compose.yml up -d

# DO:
docker compose -f my_models/docker-compose.yml up -d
#        ↑ space, not hyphen — this is Compose v2
```

---

### Problem 2: Operator GUI shows 0 capabilities after successful load

**Cause:** `Skill_PickPiece` and `Skill_PlacePiece` were defined as `SubmodelElementCollection` in the AASX. SMIA's internal class extension system fails silently with a Python MRO error. The skill is never registered.

**Symptom in logs:** No error message visible. `Analyzed skills: []`

**Diagnosis:** Look for this in smia logs during boot:
```
ERROR: Cannot create a consistent method resolution order
       (MRO) for bases HasSemantics, Qualifiable
```

**Fix:** Change Skill elements from `SubmodelElementCollection` to `Property` in AASX Package Explorer.

---

## Slide 26 — Troubleshooting We Encountered (Part 2)

### Problem 3: Operator GUI HTTP 500 on "Load"

**Cause:** A backup file (`LEGO_factory_case0.aasx.bak2`) was present in `my_models/aas/`. The operator's file scanner tried to parse it, got `None` (not a valid AASX), then passed `None` to `analyze_aas_model_store()`, which set the AAS store to `None`. All subsequent CSS queries crashed with `NoneType is not iterable`.

**Symptom:** Browser shows HTTP 500. Logs show `NoneType is not iterable`.

**Fix:** Remove all non-`.aasx` files from `my_models/aas/`. Keep only:
```
my_models/aas/
├── LEGO_factory_case0.aasx
└── SMIA_Operator_article.aasx
```

---

### Problem 4: Submit spins forever (capability request never completes)

**Cause:** SMIA's `get_asset_connection_by_model_reference()` compared AAS reference objects using Python object identity (`is` / `==`). The reference created during skill resolution was a different Python object than the one stored during startup — different identity, same logical content. Lookup returned `None`. Execution failed at line 291 of `HandleCapabilityBehaviour`.

**Fix:** Patched `src/smia/agents/smia_agent.py` to add:
1. String comparison: `str(conn_ref) == str(asset_connection_ref)`
2. Key-tuple comparison: compare `(type, value)` tuples from reference keys

Mounted into container via Docker volume:
```yaml
volumes:
  - ../src/smia/agents/smia_agent.py:/usr/local/lib/python3.12/site-packages/smia/agents/smia_agent.py
```

---

## Slide 27 — Troubleshooting We Encountered (Part 3)

### Problem 5: Node-RED returns HTTP 400 "Missing field: position"

**Cause:** SMIA's capability execution message did not include `position` in the specific field name the Node-RED function was checking.

**Fix:** Added multi-path extraction with fallback in the Node-RED function:
```javascript
let position = msg.payload.position
            ?? msg.req.query.position
            ?? msg.payload.skillParams?.position
            ?? DEFAULT_POSITION; // = 0
```

Now the flow works even when SMIA does not pass position explicitly.

---

### Problem 6: ejabberd certificate warnings (non-blocking)

**Symptom in ejabberd logs:**
```
No certificate found matching ...
```

**Cause:** ejabberd generates self-signed certificates but can't find a matching cert for the `ejabberd` domain in the local setup.

**Impact:** None for Case 0 — XMPP communication works fine over the Docker internal network without TLS validation. These are warnings, not errors.

**Action:** No fix needed for development/testing. Production would require proper TLS certificates.

---

## Slide 28 — Summary: What Makes This Work

### The chain, end to end

```
AASX model (LEGO_factory_case0.aasx)
  ↓ SMIA reads at startup
  ↓ CSS ontology IRIs → wraps elements as ExtendedCapability, ExtendedSkill
  ↓ SemanticRelationships → builds: PickPiece → Skill_PickPiece → pickPiece action
  ↓ AID → creates AssetConnection with URL http://192.168.155.10:1880/smia/lego/pick

Operator clicks "Submit Capability_PickPiece"
  ↓ FIPA-ACL REQUEST over XMPP
  ↓ SMIA looks up chain: Capability → Skill → AssetConnection
  ↓ HTTP POST to Node-RED
  ↓ Node-RED MQTT publish: bandera_custom:0
  ↓ Warehouse crane moves
```

### What makes it "flexible"

- Change the IP → update `base` in AASX → no code change
- Add a new capability → add to AASX model → SMIA picks it up automatically
- Add a new SMIA for another machine → create new AASX → plug in Docker Compose

---

## Slide 29 — Why Docker Compose? (Decision 1 Justification)

### The problem we had to solve

Without containers, running SMIA + SMIA-Operator + ejabberd on the same machine looks like this:

```
┌─── Linux dev machine (bare metal) ──────────────────────────────────┐
│                                                                      │
│  Process A: python smia.py                                          │
│    → connects to localhost:5222                                     │
│    → BUT how does it know the hostname "ejabberd" ?                 │
│    → /etc/hosts hack? environment variable? hardcoded IP?           │
│                                                                      │
│  Process B: python smia_operator.py                                 │
│    → same problem, plus: same Python env? version conflicts?        │
│                                                                      │
│  ejabberd (XMPP server)                                             │
│    → manual apt install or source build                             │
│    → accounts created manually with ejabberdctl                     │
│    → startup order: who starts first?                               │
│                                                                      │
│  Result: works on YOUR machine. Not on a colleague's. Not tomorrow. │
└──────────────────────────────────────────────────────────────────────┘
```

### The solution: shared Docker network

```
┌─── docker-compose.yml ─────────────────────────────────────────────┐
│                                                                      │
│  Docker bridge network: "smia_default"                              │
│                                                                      │
│  ┌──────────────────┐    hostname: ejabberd                        │
│  │  xmpp-server     │◄────────────────────────────────┐            │
│  │  (ejabberd)      │                                 │            │
│  │                  │  healthcheck: port 5222 open?   │            │
│  │  CTL_ON_CREATE:  │  if NO → smia waits             │            │
│  │  register        │  if YES → smia starts           │            │
│  │  SMIA_agent asd  │                                 │            │
│  │  operator001 ... │                                 │            │
│  └──────────────────┘                                 │            │
│                                                        │            │
│  ┌────────────────┐      depends_on (healthy) ────────┘            │
│  │  smia          │      resolves "ejabberd" via Docker DNS         │
│  │  (agent)       │◄── volume: ./aas → /smia_archive/config/aas    │
│  │                │◄── volume: smia_agent.py (patched override)     │
│  └────────────────┘                                                 │
│                                                                      │
│  ┌────────────────┐      depends_on (healthy)                      │
│  │  smia-operator │      resolves "ejabberd" via Docker DNS         │
│  │  (GUI :10000)  │◄── volume: ./aas (shared with smia)            │
│  └────────────────┘                                                 │
└──────────────────────────────────────────────────────────────────────┘
```

**Key insight:** Docker's internal DNS automatically makes `ejabberd` resolve to the `xmpp-server` container's IP. No `/etc/hosts`, no manual config — it just works for every container in the Compose network.

### Strengths vs. weaknesses

| ✅ Strength | ⚠️ Weakness |
|---|---|
| `docker compose up -d` — zero manual steps | All 3 services on 1 machine → 1 host failure = full outage |
| Same result on any machine with Docker | `smia_agent.py` patch is a volume mount → breaks if image updates |
| `depends_on: service_healthy` → race-free startup | Port 5222 exposed on host (acceptable in lab, not in production) |
| `CTL_ON_CREATE` auto-registers XMPP accounts | Shared `aas/` folder: one bad file → GUI 500 error |
| Entire config (yml, ejabberd.yml, AASX) in git | Scaling to many assets = bloated single Compose file |

### Why not Kubernetes / bare-metal?

| Alternative | Why rejected |
|---|---|
| **Bare-metal** | Non-reproducible, dependency hell, manual ejabberd, no restart policy |
| **Kubernetes** | Overkill for 3 services on 1 lab machine (PVCs, manifests, cluster overhead) |
| **Docker Swarm** | Multi-host benefits don't apply here; adds config complexity for zero gain |
| **VMs** | Heavier than containers, slower to start, harder to network |

> **Speaker note:** The `smia_agent.py` volume mount is the one known technical debt. The correct fix is a PR upstream. For now, it works reliably because we control when we pull new images.

---

## Slide 30 — Why Edge + Central? (Decision 2 Justification)

### The two extremes — and why neither works

```
EXTREME A — Fully Centralised                EXTREME B — Fully Isolated
─────────────────────────────                ───────────────────────────
┌─── DIDA Central ──────────┐               ┌─── fischertechnik ────┐
│  ALL machines route here  │               │  Its own everything   │
│  One broker for all       │               └───────────────────────┘
│  One Node-RED for all     │               ┌─── KUKA ──────────────┐
└─────────────────────────── ┘               │  Its own everything   │
                                             └───────────────────────┘
  PROBLEM: single point of failure            PROBLEM: no shared data,
  fischertechnik down? KUKA down?             no cross-machine analytics,
  Central failure = ALL machines stop         duplicated config everywhere
```

### The chosen middle ground: Edge + Central

```
┌───────────────────────────────────────────────────────────────────┐
│                    DIDA Central (192.168.155.10)                  │
│                                                                    │
│  ┌────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │  Node-RED      │    │  Mosquitto       │    │  PostgreSQL  │  │
│  │  (HTTP→MQTT    │    │  central broker  │    │  (aggregated │  │
│  │  bridge)       │    │                  │    │   data)      │  │
│  │  POST :1880    │    │  ← SMIA talks    │    │              │  │
│  └────────────────┘    │    here via      │    └──────────────┘  │
│                        │    MQTT bridge   │                       │
│                        └──────┬──────┬───┘                       │
└───────────────────────────────│──────│───────────────────────────┘
                                │      │  MQTT bridges (pre-configured)
               ┌────────────────┘      └──────────────────────┐
               ▼                                               ▼
┌──── fischertechnik edge ───────┐       ┌──── KUKA edge ─────────────┐
│  Mosquitto (local)             │       │  Mosquitto (local)         │
│  Node-RED (local flows)        │       │  Node-RED (local flows)    │
│  PostgreSQL (local raw data)   │       │  PostgreSQL (local data)   │
│  Control software              │       │  KUKA controller           │
│  Warehouse crane               │       │  Robot arm                 │
└────────────────────────────────┘       └────────────────────────────┘
```

### Case 0 specific data path — and the honest trade-off

```
SMIA container
    │
    │  HTTP POST  ← AID defines base = 192.168.155.10:1880
    │
    ▼
DIDA Central — Node-RED     ← ⚠️ CENTRAL IS IN THE CRITICAL PATH
    │                            if central Node-RED is down:
    │  MQTT publish               command never reaches fischertechnik
    ▼                            even if fischertechnik edge is healthy
DIDA Central — Mosquitto
    │
    │  MQTT bridge (stable, pre-configured)
    ▼
fischertechnik — Mosquitto local
    │
    ▼
Control software → Warehouse crane macro
```

**Why central instead of pointing SMIA directly to a fischertechnik edge?**
1. The fischertechnik machine is Windows — it doesn't run a custom HTTP server
2. DIDA central already had Node-RED + the bridge pre-configured in the lab
3. This was the path of least resistance and it works reliably

This is a **pragmatic trade-off**, not an architectural purity claim.

### Strengths vs. weaknesses

| ✅ Strength | ⚠️ Weakness |
|---|---|
| Fault isolation: fischertechnik edge survives central failure (for local ops) | Central IS in the critical path for SMIA commands in Case 0 |
| Add a new machine = deploy new edge stack, nothing else changes | More nodes = more things to monitor/maintain |
| Machine-specific data stays at the edge (latency, bandwidth, privacy) | Config duplication across edge nodes (risk of drift) |
| Edge processing: validation, fallback defaults near the hardware | MQTT bridge must be stable; silent failure if bridge drops |
| KUKA and fischertechnik flows fully independent | No unified monitoring dashboard out of the box |

### How to fix the central-in-critical-path problem (future improvement)

```
CURRENT (Case 0):                    IMPROVED (future):
─────────────────────                ────────────────────────────────
SMIA                                 SMIA
  │ HTTP POST → DIDA Central           │ HTTP POST → fischertechnik edge
  │ (central in critical path)         │ (central NOT in critical path)
  ▼                                    ▼
  DIDA central Node-RED              fischertechnik Linux edge node
  DIDA central Mosquitto               (Raspberry Pi or equivalent)
  MQTT bridge → fischertechnik          Local Node-RED + Mosquitto
                                      ↓
                                     Selectively forward to DIDA central
                                     for aggregation only
```

> **Speaker note:** This improvement requires adding a Linux edge node per machine, which changes the AID `base` URL in the AASX to point to the edge. No SMIA code changes — just an AAS model update. That's the power of the AID approach.

### Alternatives rejected

| Alternative | Why |
|---|---|
| **Single central broker** | Single point of failure for ALL machines simultaneously |
| **Direct SMIA → MQTT** | AID standard only defines HTTP interfaces; SMIA has no native MQTT output |
| **Direct SMIA → fischertechnik** | Windows machine, not reachable as HTTP server; violates SMIA's asset-agnostic design |

---

## Slide 31 — Live Demo

### What to show

1. Start stack:
   ```bash
   docker compose -f my_models/docker-compose.yml up -d
   docker compose -f my_models/docker-compose.yml logs -f smia
   ```
   → Point out `AAS model initialized.` and `Analyzed capabilities: [...]`

2. Open GUI: `http://localhost:10000/smia_operator`
   → Click **Load** → SMIA appears

3. Select `Capability_PickPiece` → **Submit**
   → Watch smia logs: `Executing skill... HTTP communication successfully completed.`
   → Watch operator GUI: shows `{"status":"ok","payload":"bandera_custom:0",...}`
   → Observe physical crane movement

4. Direct test (optional):
   ```bash
   curl -i -X POST http://192.168.155.10:1880/smia/lego/pick \
     -H 'Content-Type: application/json' -d '{"position":0}'
   ```

---

## Slide 32 — What's Next

### Case 0 is the baseline. Future cases will:

| Case | What we add |
|---|---|
| **Case 1** | Second SMIA agent (e.g., transport AGV) + multi-agent negotiation |
| **Case 2** | Capability constraints (pre/post-conditions, matching logic) |
| **Case 3** | Human agent (SMIA-HI) representing an operator as an AAS |
| **Case 4** | BPMN process orchestration via SMIA-PE |
| **Case 5** | Full AAS server (BaSyx) + standard AAS API exposure |

### What Case 0 proved
- ✓ AAS + CSS is sufficient to fully describe a physical asset's interface
- ✓ SMIA self-configures from the AAS with no asset-specific code
- ✓ The full stack (XMPP + HTTP + MQTT) works reliably end-to-end
- ✓ The approach is reproducible (any colleague can replicate with the docs)

---

## Slide 33 — Resources and Repo Structure

### Where everything is

```
SMIA/
├── my_models/                       ← everything for Case 0
│   ├── aas/
│   │   ├── LEGO_factory_case0.aasx  ← the AAS model (open in AASX PE)
│   │   └── SMIA_Operator_article.aasx
│   ├── xmpp_server/ejabberd.yml
│   ├── ontology/CSS-ontology-smia.owl
│   ├── docker-compose.yml
│   ├── smia-initialization.properties
│   ├── flow_dida_central_lego.json  ← import this in Node-RED
│   ├── doc_case0.md                 ← full technical reference
│   ├── memoire.md                   ← academic document base
│   └── playBook.md                  ← operational runbook
└── src/smia/agents/smia_agent.py    ← patched file (mounted into container)
```

### Key references
- SMIA repo + docs: `https://github.com/ekhurtado/SMIA`
- AAS standard: IDTA 01001-3-0
- AID submodel: IDTA 02017-1-0
- CSS ontology: `https://w3id.org/hsu-aut/css`
- AASX Package Explorer: `https://github.com/admin-shell-io/aasx-package-explorer`
- fischertechnik factory: product ref. 554868

---

## Appendix A — Semantic IDs Quick Reference

### CSS Ontology IRIs
| Concept | IRI |
|---|---|
| AssetCapability | `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability` |
| Skill | `http://www.w3id.org/hsu-aut/css#Skill` |
| isRealizedBy | `http://www.w3id.org/hsu-aut/css#isRealizedBy` |
| accessibleThroughAssetService | `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService` |

### AID Semantic IDs
| Concept | Semantic ID |
|---|---|
| AID Submodel | `https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel` |
| Interface | `…/Interface` |
| EndpointMetadata | `…/EndpointMetadata` |
| InteractionMetadata | `…/InteractionMetadata` |
| base URL | `https://www.w3.org/2019/wot/td#baseURI` |
| ActionAffordance | `https://www.w3.org/2019/wot/td#ActionAffordance` |
| hasForm | `https://www.w3.org/2019/wot/td#hasForm` |
| href (hasTarget) | `https://www.w3.org/2019/wot/hypermedia#hasTarget` |
| HTTP method | `https://www.w3.org/2011/http#methodName` |
| contentType | `https://www.w3.org/2019/wot/hypermedia#forContentType` |
| hasInputSchema | `https://www.w3.org/2019/wot/td#hasInputSchema` |

---

## Appendix B — Docker Commands Cheat Sheet

```bash
# Start all services
docker compose -f my_models/docker-compose.yml up -d

# Stop all (keep data)
docker compose -f my_models/docker-compose.yml down

# Full reset (re-registers XMPP accounts on next start)
docker compose -f my_models/docker-compose.yml down -v

# Live logs
docker compose -f my_models/docker-compose.yml logs -f smia smia-operator xmpp-server

# Restart only smia (after patching smia_agent.py)
docker compose -f my_models/docker-compose.yml restart smia

# Check container status
docker compose -f my_models/docker-compose.yml ps
```

---

## Appendix C — Troubleshooting Decision Tree

```
Operator GUI won't load?
  → Check: docker logs smia-operator
  → Check: only .aasx files in my_models/aas/  (remove backups!)
  → Check: ejabberd is healthy (docker ps)

GUI loads but 0 capabilities?
  → Check: docker logs smia | grep "Analyzed"
  → If "Analyzed capabilities: []" → AAS model issue
  → Check: Skills are Property (not SMC) in AASX
  → Check: semanticIds are exact (copy from Appendix A)

Submit hangs?
  → Check: docker logs smia | grep "Exception\|line:291"
  → If line 291 error → smia_agent.py patch not applied
  → Check volume mount in docker-compose.yml

HTTP done but no crane movement?
  → Test Node-RED directly with curl (Slide 23)
  → Check Node-RED debug panels
  → Check MQTT Explorer on central broker (topic: vicom/61/piso_0/lab/lego/commands)
  → Check MQTT bridge to fischertechnik machine

XMPP errors?
  → Check credentials: SMIA_agent@ejabberd:asd / operator001@ejabberd:gcis1234
  → Check ejabberd container is healthy
  → Try: docker compose down -v && docker compose up -d (re-registers accounts)
```
