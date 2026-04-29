# SMIA Flexible Manufacturing — Fischertechnik Orchestration

A multi-agent Digital Twin system for flexible manufacturing using the
**Asset Administration Shell (AAS)**, the **Capability-Skill-Service (CSS)** ontological model,
and the **SMIA** (Self-configurable Manufacturing Industrial Agents) framework.

Developed as a Bachelor's Thesis at **Universidad de Deusto** in collaboration with
**Vicomtech — Data Intelligence for Industry (DII)**.

**Primary scientific base:**
E. Hurtado et al., *"Self-configurable Manufacturing Industrial Agents (SMIA): a standardized
approach for digitizing manufacturing assets"*, Journal of Industrial Information Integration 47
(2025) 100915. DOI: [10.1016/j.jii.2025.100915](https://doi.org/10.1016/j.jii.2025.100915)

---

## What this project demonstrates

Two validated scenarios using a **fischertechnik Training Factory Industry 4.0 24V** warehouse crane:

| Scenario | Description | Validates |
|---|---|---|
| **Case 0** | Operator selects a machine directly; SMIA agent reads its AAS model, resolves the skill, and sends an HTTP command to Node-RED, which triggers the crane via MQTT — zero asset-specific code in the agent | R2 (auto self-configuration), R7 (DT/asset separation) |
| **Case 1** | Operator sends a colour-based pick request to an orchestrator; the orchestrator discovers eligible machines from their AAS models, runs a FIPA Contract Net Protocol negotiation based on machine availability, and delegates execution to the winning agent | R6 (P2P FIPA-ACL negotiation), R4 (flexible reconfiguration) |

All agent behaviour is derived at runtime from the AASX Digital Twin models — no hardcoded
machine addresses, capability names, or skill logic exist in the Python source.

---

## System architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Browser  http://localhost:10000/smia_operator                              │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │ HTTP
                       ▼
┌──────────────────────────────┐
│  smia-operator               │  Operator GUI — scans aas/ for SMIA agents,
│  operator001@ejabberd        │  presents capabilities, routes FIPA-ACL REQUESTs
└──────────────────────────────┘
          │ FIPA-ACL REQUEST (XMPP)
          ▼
┌─────────────────────────────────────────────────────────────┐
│  ejabberd  (XMPP broker)                                    │
└──────┬──────────────────┬──────────────────────────────────-┘
       │                  │
       │ direct           │ via orchestrator (Case 1)
       ▼                  ▼
┌─────────────┐   ┌──────────────────────────────────────────┐
│ smia-       │   │  smia-orchestrator  smia_orch@ejabberd   │
│ machineN    │   │                                          │
│             │   │  1. Reads AAS models → discovers         │
│ Reads its   │   │     eligible machines by colour          │
│ own AASX    │   │  2. Sends FIPA-CNP CFP to all eligible   │
│ resolves    │   │     machines simultaneously              │
│ skill →     │   │  3. Machines compute availability        │
│ HTTP POST   │   │     score via Node-RED GET endpoint      │
│ to Node-RED │   │  4. Winner sends INFORM; orchestrator    │
└──────┬──────┘   │     sends execution REQUEST to winner   │
       │          └──────────────────────────────────────────┘
       │ HTTP POST /smia/lego/pick?machine=<id>&position=<n>
       ▼
┌──────────────────────────┐
│  nodered  (Node-RED)     │  HTTP → MQTT bridge; tracks per-machine
│  port 1880               │  busy state; exposes /availability endpoint
└──────────┬───────────────┘
           │ MQTT  vicom/61/piso_0/lab/lego/commands
           ▼
┌─────────────────────────┐
│  mosquitto-central      │  MQTT broker with bridge to fischertechnik PC
└──────────┬──────────────┘
           │ MQTT bridge
           ▼
┌─────────────────────────────────────────────────────────┐
│  fischertechnik machine (192.168.155.10)                │
│  Receives bandera_custom:<position> → crane picks slot  │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Docker + Docker Compose v2** | `docker compose` (space, not hyphen). Minimum: Docker 24+ |
| **fischertechnik Training Factory 24V** | Physical asset; connects via MQTT to the machine on the lab network |
| **Node-RED** running on `192.168.155.10:1880` | Edit `config/mosquitto/conf.d/bridge.conf` to set the actual IP |
| **AASX Package Explorer** (Windows) | Only needed to create or modify `.aasx` model files |
| No Python installation required | All agents run inside Docker containers |

---

## Quick start

```bash
# 1. Clone and enter the repository
git clone <repo-url>
cd smia-flexible-manufacturing

# 2. Create your credentials file
cp .env.example .env
# Edit .env — set passwords for all SMIA agents and ejabberd cookie

# 3. Set the physical machine IP
# Edit config/mosquitto/conf.d/bridge.conf → change "address" to the lab PC IP

# 4. Build custom agent images
docker compose build

# 5. Start everything
docker compose up -d

# Operator GUI is now at http://localhost:10000/smia_operator
```

**To run only Case 0 (single machine, no orchestrator):**
```bash
docker compose up -d xmpp-server mosquitto-central nodered smia-machine0 smia-operator
```

**To run Case 1 (full multi-agent negotiation):**
```bash
docker compose up -d   # starts all 11 services
```

---

## How the self-configuration works

Each SMIA agent starts with no knowledge of its physical asset. During the boot phase it:

1. **Loads its AASX model** — a standard binary package containing two AAS shells:
   the asset shell (describes the physical machine: interfaces, capabilities, skills) and
   the agent shell (identity: XMPP JID in `SoftwareNameplate.InstanceName`).

2. **Parses the Asset Interfaces Description (AID) submodel** — extracts HTTP endpoint URLs,
   methods, and parameters. Creates `AssetConnection` objects for each interface.

3. **Instantiates the CSS ontology** — reads `RelationshipElement` entries with CSS semantic IDs,
   creates OWL instances for each `Capability`, `Skill`, and `SkillInterface`, and links them.

4. **Enters the RUNNING state** — the agent can now receive FIPA-ACL messages, resolve
   capability requests through the CSS chain, and execute asset services (HTTP calls) or
   agent services (Python methods) with zero hardcoded logic.

**The entire chain for a pick request:**
```
FIPA-ACL REQUEST (capability=PickPiece, color=red)
  → CSS: Capability_PickPiece → isRealizedBy → Skill_PickPiece
  → CSS: Skill_PickPiece → accessibleThroughAssetService → AID/pickPiece action
  → AID: base=http://nodered:1880, href=/smia/lego/pick?machine=smia_machine0, method=POST
  → HTTP POST → Node-RED → MQTT publish → crane moves
```

---

## Project structure

```
smia-flexible-manufacturing/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── agents/
│   ├── machine/            ← Machine SMIA agent (pick/place + availability service)
│   ├── orchestrator/       ← Orchestrator SMIA agent (FIPA-CNP initiator)
│   └── operator/           ← Operator GUI agent
│
├── patches/
│   ├── PATCHES.md          ← Detailed documentation of each SMIA framework bug fix
│   ├── smia_agent.py       ← Patch 1: asset connection identity comparison
│   └── acl_handling_behaviour.py  ← Patch 2: orchestrator message race condition
│
├── aas/                    ← AASX Digital Twin model files (binary, edit with AASX PE)
│   ├── LEGO_machine0.aasx  ← smia_machine0@ejabberd — red
│   ├── LEGO_machine1.aasx  ← smia_machine1@ejabberd — blue
│   ├── LEGO_machine2.aasx  ← smia_machine2@ejabberd — white
│   ├── LEGO_machine3.aasx  ← smia_machine3@ejabberd — red (duplicate, for negotiation testing)
│   ├── LEGO_machine4.aasx  ← smia_machine4@ejabberd — blue (duplicate)
│   ├── LEGO_machine5.aasx  ← smia_machine5@ejabberd — red+blue (multicolour)
│   ├── SMIA_orchestrator.aasx
│   └── SMIA_Operator_article.aasx
│
├── config/
│   ├── ejabberd.yml
│   ├── mosquitto/
│   │   ├── mosquitto.conf
│   │   └── conf.d/bridge.conf   ← SET TARGET IP HERE
│   └── nodered/
│       └── flows.json
│
├── ontology/
│   └── CSS-ontology-smia.owl
│
└── docs/
    ├── memoire.md          ← Full technical deep-dive
    └── memoria_tfg.md      ← Official TFG document (Universidad de Deusto)
```

---

## Adding a new machine

1. **Create the AASX model** in AASX Package Explorer — clone an existing machine AASX,
   change the AAS UUIDs, `InstanceName` (JID), `color` property, and AID `href`
   (include `?machine=<agent_id>&position=<slot>`).

2. **Add the AASX to `aas/`** — the operator GUI and orchestrator auto-discover all `.aasx`
   files in this folder. No code change needed.

3. **Add to `.env`:**
   ```env
   MACHINE6_AAS_FILE=LEGO_machine6.aasx
   MACHINE6_AAS_ID=urn:uuid:6475_0111_2062_0006
   MACHINE6_AGENT_ID=smia_machine6@ejabberd
   MACHINE6_PASSWD=your_password
   ```

4. **Add the service to `docker-compose.yml`** — copy an existing machine service block,
   substitute the variable names.

5. **Register the XMPP account** — append to `CTL_ON_CREATE` in the ejabberd service:
   ```
   ; register smia_machine6 ejabberd ${MACHINE6_PASSWD}
   ```

6. **Reset ejabberd** to apply new account registration:
   ```bash
   docker compose down -v && docker compose up -d
   ```

---

## Deployed services

| Service | Role | Port |
|---|---|---|
| `xmpp-server` | ejabberd XMPP broker; auto-registers all agent accounts | 5222 |
| `mosquitto-central` | MQTT broker; bridges to fischertechnik PC | — (internal) |
| `nodered` | HTTP→MQTT bridge; availability state tracking | 1880 |
| `smia-machine0` | Machine SMIA — red pieces, slot 0 | — |
| `smia-machine1` | Machine SMIA — blue pieces, slot 1 | — |
| `smia-machine2` | Machine SMIA — white pieces, slot 2 | — |
| `smia-machine3` | Machine SMIA — red pieces, slot 0 (duplicate) | — |
| `smia-machine4` | Machine SMIA — blue pieces, slot 1 (duplicate) | — |
| `smia-machine5` | Machine SMIA — red+blue multicolour | — |
| `smia-orchestrator` | Orchestrator SMIA — FIPA-CNP dispatcher | — |
| `smia-operator` | Operator web GUI | 10000 |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'ContainerConfig'` on `compose up` | Docker Compose v1 (`docker-compose`) | Use `docker compose` (space, v2) |
| ejabberd never healthy | Config syntax error or port conflict | `docker compose logs xmpp-server` |
| Operator GUI 500 on Load | Non-`.aasx` file in `aas/` | Remove all non-AASX files from `aas/` |
| Submit button spins, no HTTP in logs | `smia_agent.py` patch not applied | `docker compose build smia-machine0`; verify Dockerfile RUN output |
| HTTP 200 but crane does not move | MQTT bridge down or wrong IP | Check `config/mosquitto/conf.d/bridge.conf` and Node-RED debug tab |
| XMPP auth failure or agent blacklisted | Password mismatch between `.env` and ejabberd DB | `docker compose down -v && docker compose up -d` (wipes ejabberd DB) |
| `NoneType is not iterable` in negotiation logs | OWL link missing — IRI casing error in AASX | Open AASX PE → `rel_SkillNegAvail_agentSvc` semanticId must be exactly `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAgentService` (lowercase `a`) |
| CFP sent but `color=''` (all machines respond) | Skill has no `hasParameter` relationship in orchestrator AASX | Add `SkillParameter_color` + `rel_SkillOrch_hasParam_color` (semanticId `css#hasParameter`) to SMIA_orchestrator.aasx |
| Machine not discovered by orchestrator | `InstanceName` in AASX does not match `AGENT_ID` in `.env` | Open AASX PE → agent shell → SoftwareNameplate → InstanceName must equal `smia_machineN@ejabberd` |
| `hasImplementationType not found` at boot | Qualifier semanticId uses `https://` instead of `http://` | Fix in AASX PE: `http://www.w3id.org/upv-ehu/gcis/css-smia#hasImplementationType` |

---

## Key identifiers

| Agent | XMPP JID | AASX file | AAS UUID |
|---|---|---|---|
| Machine 0 (red) | `smia_machine0@ejabberd` | `LEGO_machine0.aasx` | `urn:uuid:6475_0111_2062_9689` |
| Machine 1 (blue) | `smia_machine1@ejabberd` | `LEGO_machine1.aasx` | `urn:uuid:6475_0111_2062_0001` |
| Machine 2 (white) | `smia_machine2@ejabberd` | `LEGO_machine2.aasx` | `urn:uuid:6475_0111_2062_0002` |
| Machine 3 (red dup.) | `smia_machine3@ejabberd` | `LEGO_machine3.aasx` | `urn:uuid:6475_0111_2062_0003` |
| Machine 4 (blue dup.) | `smia_machine4@ejabberd` | `LEGO_machine4.aasx` | `urn:uuid:6475_0111_2062_0004` |
| Machine 5 (red+blue) | `smia_machine5@ejabberd` | `LEGO_machine5.aasx` | `urn:uuid:6475_0111_2062_0005` |
| Orchestrator | `smia_orch@ejabberd` | `SMIA_orchestrator.aasx` | `urn:uuid:8888_0001_2026_0001` |
| Operator | `operator001@ejabberd` | `SMIA_Operator_article.aasx` | — |

---

## Citation

If you use this work, please cite the underlying SMIA framework paper:

```bibtex
@article{hurtado2025smia,
  title   = {Self-configurable Manufacturing Industrial Agents (SMIA):
             a standardized approach for digitizing manufacturing assets},
  author  = {Hurtado, Ekaitz and Burgos, Arantzazu and Armentia, Aintzane and Casquero, Oskar},
  journal = {Journal of Industrial Information Integration},
  volume  = {47},
  pages   = {100915},
  year    = {2025},
  doi     = {10.1016/j.jii.2025.100915}
}
```

---

## Authors

- **Andrés Felipe Fierro Fonseca** — implementation, extensions, bug fixes, documentation
  (Universidad de Deusto / Vicomtech DII internship)
- **Academic tutor:** Ander García Gangoiti (Universidad de Deusto)
- **Technical tutor:** Xabier Oregui Biain (Vicomtech)
