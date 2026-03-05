# Case 0 Playbook (SMIA + AAS + Node-RED + MQTT)

Date: 2026-03-05  
Scope: Case 0 only (fischertechnik Training Factory Industry 4.0 24V), end-to-end execution and troubleshooting.

This document contains only facts verified from:
1. User-confirmed runtime behavior.
2. Files currently in `my_models` and `src/smia/agents/smia_agent.py`.
3. Current container logs from `smia`, `smia-operator`, and `ejabberd`.

---

## 1) Objective of Case 0

Execute Case 0 end-to-end:
1. Operator requests `Capability_PickPiece` (or `Capability_PlacePiece`) from SMIA Operator GUI.
2. `smia` resolves the capability/skill from the AAS model.
3. `smia` calls Node-RED HTTP endpoint defined in AAS `AssetInterfacesDescription`.
4. Node-RED publishes MQTT command to topic used by the fischertechnik integration.
5. The warehouse crane macro is triggered.

Physical asset reference:
1. `fischertechnik Training Factory Industry 4.0 24V`
2. Product page: `https://www.fischertechnik.de/es-es/productos/industria-y-universidades/modelos-de-simulacion/554868-training-factory-industry-4-0-24v`

Scope clarification for capabilities:
1. `Capability_PickPiece` and `Capability_PlacePiece` refer to the **warehouse crane** only.
2. They do **not** refer to the central crane with suction cup (`ventose`).

Current status at this snapshot: **working end-to-end**.

---

## 2) Real Architecture Used

### 2.1 Machines
1. Linux dev machine (this repo):
   - Runs Docker Compose for `smia`, `smia-operator`, `ejabberd`.
   - Hosts AASX files and SMIA config under `my_models`.
2. DIDA central machine:
   - Runs Node-RED + Mosquitto (+ PostgreSQL in your stack).
   - Exposes HTTP endpoint consumed by SMIA.
   - Publishes MQTT command to central topic.
3. fischertechnik/PLC Windows machine:
   - Receives MQTT command and executes the warehouse crane macro.

### 2.2 Runtime path used in Case 0
1. Browser -> `smia-operator` (`/smia_operator`).
2. `smia-operator` -> XMPP (`ejabberd`) -> `smia_agent@ejabberd`.
3. `smia` -> HTTP `POST` to Node-RED base URL from AAS (`http://192.168.155.10:1880`) + path (`/smia/lego/pick`).
4. Node-RED function -> MQTT publish:
   - topic: `vicom/61/piso_0/lab/lego/commands`
   - payload: `bandera_custom:<position>`
5. fischertechnik side consumes topic and triggers warehouse crane macro.

Naming note:
1. Some technical names keep `lego` for historical reasons (file names, endpoint path, MQTT topic).
2. In this document, physical system references are to the fischertechnik Training Factory.

---

## 3) Exact Artifacts and Values

### 3.1 Files
1. `my_models/docker-compose.yml`
2. `my_models/smia-initialization.properties`
3. `my_models/aas/LEGO_factory_case0.aasx`
4. `my_models/aas/SMIA_Operator_article.aasx`
5. `my_models/flow_dida_central_lego.json`
6. `src/smia/agents/smia_agent.py` (patched and mounted into container)

### 3.2 Hashes (reproducibility)
1. `LEGO_factory_case0.aasx`: `2bab8d6a6a1f3b6a67e3c20a9707990e918575553d0878950da14236bf9f12ca`
2. `flow_dida_central_lego.json`: `fb1a5a5ddcbafa970b0363b8728ee283aebea339471d0e8d401f3cb0b5dc3565`
3. `docker-compose.yml`: `a4fbbe724c653656729eb843c435d1d6dfda0b9b9d01308be737a2d749863be5`
4. `smia-initialization.properties`: `992d4ae7b43e637c952ec84006b4f0ec6287b76d78ab923093408a554f328b46`

### 3.3 Docker Compose (effective values)
1. `smia`:
   - image: `ekhurtado/smia:latest-alpine`
   - env:
     - `AAS_MODEL_NAME=LEGO_factory_case0.aasx`
     - `AAS_ID=urn:uuid:6475_0111_2062_9689`
     - `AGENT_ID=SMIA_agent@ejabberd`
     - `AGENT_PASSWD=asd`
   - volumes:
     - `../src/smia/agents/smia_agent.py:/usr/local/lib/python3.12/site-packages/smia/agents/smia_agent.py`
     - `./aas:/smia_archive/config/aas`
2. `xmpp-server` (`ejabberd`):
   - image: `ghcr.io/processone/ejabberd`
   - `CTL_ON_CREATE=! register SMIA_agent ejabberd asd ; register operator001 ejabberd gcis1234`
   - exposed ports: `5222`, `5269`, `5280`, `5443`
3. `smia-operator`:
   - image: `ekhurtado/smia-use-cases:latest-operator`
   - env:
     - `AAS_MODEL_NAME=SMIA_Operator_article.aasx`
     - `AGENT_ID=operator001@ejabberd`
     - `AGENT_PASSWD=gcis1234`
   - volumes:
     - `./aas:/smia_archive/config/aas`
     - `../additional_tools/extended_agents/smia_operator_agent/operator_gui_behaviours.py:/operator_gui_behaviours.py`
     - `../additional_tools/extended_agents/smia_operator_agent/operator_gui_logic.py:/operator_gui_logic.py`
     - `../additional_tools/extended_agents/smia_operator_agent/htmls:/htmls`
   - exposed port: `10000`

### 3.4 `smia-initialization.properties` (external file)
1. `dt.agentID=SMIA_agent@ejabberd`
2. `dt.password=asd`
3. `dt.xmpp-server=ejabberd`
4. `aas.model.serialization=AASX`
5. `aas.model.folder=/smia_archive/config/aas`
6. `aas.model.file=LEGO_factory_case0.aasx`
7. `ontology.file=CSS-ontology-smia.owl`
8. `ontology.inside-aasx=true`

Note: the AASX package also contains an embedded `aasx/smia-initialization.properties` template with other values (`gcis1`, `xmpp.jp`, etc.). Runtime values used here are the external Docker/environment values listed above.

---

## 4) AAS Configuration (Case 0) with Concrete Mapping

Source verified from `my_models/LEGO_factory_case0.json` and `LEGO_factory_case0.aasx` internal XML.

### 4.1 AAS identities
1. Main training factory AAS ID: `urn:uuid:6475_0111_2062_9689`
2. Operator/agent AAS appears in model with:
   - `idShort`: `SMIA_agent`
   - `id`: `urn:uuid:6373_1111_2062_6896`

### 4.2 Submodels used for execution
1. `AssetInterfacesDescription`
2. `CapabilitiesAndSkills`
3. `SemanticRelationships`

### 4.3 Capability and Skill elements
1. `Capability_PickPiece`
   - semanticId: `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability`
   - qualifier:
     - `hasLifecycle` -> `OFFER`
   - value includes property: `position` (`xs:int`)
2. `Capability_PlacePiece`
   - semanticId: `http://www.w3id.org/upv-ehu/gcis/css-smia#AssetCapability`
   - qualifier:
     - `hasLifecycle` -> `OFFER`
   - value includes property: `position` (`xs:int`)
3. `Skill_PickPiece`
   - semanticId: `http://www.w3id.org/hsu-aut/css#Skill`
   - qualifier:
     - `hasImplementationType` -> `OPERATION`
4. `Skill_PlacePiece`
   - semanticId: `http://www.w3id.org/hsu-aut/css#Skill`
   - qualifier:
     - `hasImplementationType` -> `OPERATION`

Capability scope note:
1. `pickPiece/placePiece` in this Case 0 mapping are bound to warehouse crane actions.
2. Central crane with suction cup is out of scope for these two capabilities.

### 4.4 Semantic relationship mapping
1. `rel_CapPick_isRealizedBySkill_SkillPick`
   - semanticId: `http://www.w3id.org/hsu-aut/css#isRealizedBy`
   - `Capability_PickPiece` -> `Skill_PickPiece`
2. `rel_CapPlace_isRealizedBySkill_SkillPlace`
   - semanticId: `http://www.w3id.org/hsu-aut/css#isRealizedBy`
   - `Capability_PlacePiece` -> `Skill_PlacePiece`
3. `rel_SkillPick_hasSkillInterface`
   - semanticId: `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService`
   - `Skill_PickPiece` -> `InterfaceHTTP/InteractionMetadata/actions/pickPiece`
4. `rel_SkillPlace_hasSkillInterface`
   - semanticId: `http://www.w3id.org/upv-ehu/gcis/css-smia#accessibleThroughAssetService`
   - `Skill_PlacePiece` -> `InterfaceHTTP/InteractionMetadata/actions/placePiece`

### 4.5 Asset interface mapping (HTTP)
1. Interface idShort: `InterfaceHTTP`
2. Interface supplemental semantic ID present in AASX XML:
   - `http://www.w3.org/2011/http`
3. EndpointMetadata base:
   - `http://192.168.155.10:1880`
4. Action `pickPiece`:
   - `href`: `/smia/lego/pick`
   - `htv_methodName`: `POST`
   - `contentType`: `application/json`
   - input schema collection semantic entry present:
     - `https://www.w3.org/2019/wot/td#hasInputSchema`
   - inputs modeled:
     - `color` (`xs:string`)
     - `position` (`xs:int`)
5. Action `placePiece`:
   - `href`: `/smia/lego/place`
   - `htv_methodName`: `POST`
   - `contentType`: `application/json`
   - input schema collection semantic entry present:
     - `https://www.w3.org/2019/wot/td#hasInputSchema`
   - input modeled:
     - `position` (`xs:int`)

### 4.6 Ontology embedding
1. AASX contains `aasx/CSS-ontology-smia.owl`.
2. `ontology.inside-aasx=true` is configured in external properties.

---

## 5) AASX Package Explorer Verification Checklist (What to Click)

Open `my_models/aas/LEGO_factory_case0.aasx` in AASX Package Explorer and verify:
1. `Submodels` -> `AssetInterfacesDescription` exists.
2. `AssetInterfacesDescription` -> `InterfaceHTTP` exists.
3. `InterfaceHTTP` -> `EndpointMetadata` -> `base` is `http://192.168.155.10:1880`.
4. `InterfaceHTTP` -> `InteractionMetadata` -> `actions` -> `pickPiece`.
5. `pickPiece` -> `forms` contains:
   - `href=/smia/lego/pick`
   - `htv_methodName=POST`
   - `contentType=application/json`
6. `pickPiece` -> `input` collection exists and includes `position` (and `color` if kept in your model).
7. `actions` -> `placePiece` contains:
   - `href=/smia/lego/place`
   - `htv_methodName=POST`
   - `contentType=application/json`
8. `CapabilitiesAndSkills` contains:
   - `Capability_PickPiece`
   - `Capability_PlacePiece`
   - `Skill_PickPiece`
   - `Skill_PlacePiece`
9. `SemanticRelationships` contains the 4 mapping relationships listed in section 4.4.
10. Embedded ontology file is present in package resources.

---

## 6) Node-RED Flow Implemented in DIDA Central

Source: `my_models/flow_dida_central_lego.json`

### 6.1 Nodes and contract
1. HTTP In:
   - Method: `POST`
   - URL: `/smia/lego/pick`
2. JSON parser node.
3. Function node `Validate+Publish pickPiece`:
   - `DEFAULT_POSITION = 0`
   - accepts position from:
     - `msg.payload.position`
     - `msg.req.query.position`
     - `msg.payload.skillParams.position`
   - validates integer range `0..8`
   - publishes:
     - `msg.topic = "vicom/61/piso_0/lab/lego/commands"`
     - `msg.payload = "bandera_custom:<pos>"`
   - returns HTTP response JSON:
     - `status`
     - `published`
     - `payload`
     - `position`
     - `source` (`request` or `default`)
4. MQTT out:
   - broker: `mosquitto-central`
   - port: `1883`
   - QoS: `1`

### 6.2 Behavior that made Case 0 robust
1. If SMIA does not pass `position`, function uses `DEFAULT_POSITION=0`.
2. This avoids HTTP 400 from Node-RED for current Case 0 request shape.

---

## 7) Deployment Steps (Exact Commands)

Run from repo root:

```bash
cd /home/VICOMTECH/afierro/tfg_mio/repo_smia/SMIA
docker compose -f my_models/docker-compose.yml up -d
docker compose -f my_models/docker-compose.yml ps
```

Expected services up:
1. `smia`
2. `smia-operator`
3. `ejabberd`

Open GUI:
1. `http://localhost:10000/smia_operator`

Useful log command:

```bash
docker compose -f my_models/docker-compose.yml logs -f smia smia-operator xmpp-server
```

---

## 8) End-to-End Test Procedure (Case 0)

### 8.1 Pre-checks
1. Confirm `my_models/aas` contains only valid active `.aasx` files.
2. Confirm Node-RED flow is deployed in DIDA central.
3. Confirm MQTT chain central -> fischertechnik PLC side is online.

### 8.2 Direct HTTP test to Node-RED (bypass SMIA)

```bash
curl -i -X POST http://192.168.155.10:1880/smia/lego/pick \
  -H 'Content-Type: application/json' \
  -d '{"position":0}'
```

Expected:
1. HTTP 200
2. JSON with `status: "ok"` and payload `bandera_custom:0`
3. MQTT publish on `vicom/61/piso_0/lab/lego/commands`

### 8.3 Full SMIA path test
1. Open operator GUI.
2. Click load to discover SMIAs.
3. Select SMIA target.
4. Select capability `Capability_PickPiece`.
5. Submit execution request.

Expected logs:
1. `smia-operator`: selected capability and ACL `inform` response.
2. `smia`: `Executing skill ... through an asset service...`
3. `smia`: `HTTP communication successfully completed.`

Expected operator response content:
1. `{"status":"ok","published":"vicom/61/piso_0/lab/lego/commands","payload":"bandera_custom:0","position":0}`

Expected physical result:
1. Warehouse crane macro is triggered on the fischertechnik Training Factory.

---

## 9) What Went Wrong and How It Was Troubleshot

This section records issues actually observed in this setup cycle.

### 9.1 Docker Compose v1 crash (`ContainerConfig`)
1. Symptom:
   - `docker-compose up -d --force-recreate` failed with Python traceback ending in `KeyError: 'ContainerConfig'`.
2. Cause:
   - Legacy `docker-compose` v1.29.2 incompatibility with current Docker image metadata.
3. Resolution:
   - Use Compose v2 CLI: `docker compose ...` (space, not hyphen).

### 9.2 Operator request previously hanging / no MQTT publish
1. Symptom:
   - Submit stayed loading.
   - No publish observed at central MQTT.
   - `smia` log had `Exception running behaviour OneShotBehaviour/HandleCapabilityBehaviour: line:291`.
2. Observed outcome after fixes:
   - `smia` logs now show:
     - `Executing skill of the capability through an asset service...`
     - `HTTP communication successfully completed.`
   - `smia-operator` receives ACL `inform` with published topic/payload.
3. Implemented fixes in this repository:
   - Mounted updated operator files in Compose:
     - `operator_gui_behaviours.py`
     - `operator_gui_logic.py`
     - `htmls/`
   - Patched `src/smia/agents/smia_agent.py` asset-connection lookup to compare:
     - direct object equality
     - string equality
     - normalized reference key tuples
   - Mounted patched `smia_agent.py` into `smia` container.

### 9.3 Node-RED contract mismatch (`position` parameter)
1. Symptom:
   - Node-RED returned `Missing field: position` when SMIA request did not include params.
2. Resolution:
   - Updated flow function with `DEFAULT_POSITION = 0` compatibility mode.
3. Result:
   - SMIA execution path became stable for Case 0.

### 9.4 MQTT message arriving but macro not moving (intermediate stage)
1. Symptom:
   - Message reached broker but macro did not trigger.
2. Verification path used:
   - Check Node-RED debug node output type and exact string payload.
   - Compare against known working manual publish from MQTT Explorer.
3. Final state:
   - Now working; user confirmed warehouse crane macro triggers with end-to-end path.

### 9.5 ejabberd certificate warnings
1. Observed lines:
   - `No certificate found matching ...`
2. Interpretation:
   - Non-blocking warnings for this local/non-TLS test path.
3. Action:
   - No change required for current Case 0 objective.

---

## 10) Fast Troubleshooting Matrix

1. Symptom: GUI cannot load SMIAs.
   - Check: `docker compose -f my_models/docker-compose.yml logs -n 200 smia-operator`
   - Check: AAS files in `my_models/aas` are valid `.aasx` only.
   - Fix: move backups to `my_models/aas_backup`.

2. Symptom: submit spins forever.
   - Check: `smia` logs for `line:291`, `Exception`, missing interface mapping.
   - Check: `smia-operator` logs for request/response ACL lines.
   - Fix: ensure patched `smia_agent.py` mount is active and restart `smia`.

3. Symptom: SMIA says HTTP completed but no warehouse crane action.
   - Check: Node-RED debug after function node.
   - Check: topic equals `vicom/61/piso_0/lab/lego/commands`.
   - Check: payload exact raw string `bandera_custom:<n>`.
   - Check: broker bridge central -> fischertechnik PLC side.

4. Symptom: compose recreate crashes with `ContainerConfig`.
   - Fix: use `docker compose` (v2), not `docker-compose` (v1).

5. Symptom: XMPP auth/online issues.
   - Check Compose env:
     - `SMIA_agent@ejabberd / asd`
     - `operator001@ejabberd / gcis1234`
   - Check ejabberd container health and port 5222.

---

## 11) Verified Healthy Log Signatures

Use:

```bash
docker compose -f my_models/docker-compose.yml logs smia smia-operator xmpp-server | rg "AAS model initialized|Analyzed capabilities|Executing skill|HTTP communication successfully completed|selected capability|FIPA-ACL Message received|Configuration loaded successfully"
```

Expected patterns:
1. `smia`: `AAS model initialized.`
2. `smia`: `Analyzed capabilities: ['Capability_PickPiece', 'Capability_PlacePiece']`
3. `smia`: `Analyzed skill interfaces: ['pickPiece', 'placePiece']`
4. `smia`: `Analyzed asset connections: ['InterfaceHTTP', 'Interface_00']`
5. `smia`: `Executing skill ...`
6. `smia`: `HTTP communication successfully completed.`
7. `smia-operator`: selected capability line.
8. `smia-operator`: ACL `inform` response with published topic/payload.
9. `ejabberd`: `Configuration loaded successfully`.

---

## 12) Replication Checklist for a Colleague

1. Clone repo and go to `SMIA` root.
2. Ensure `my_models/aas` contains:
   - `LEGO_factory_case0.aasx`
   - `SMIA_Operator_article.aasx`
3. Ensure `my_models/docker-compose.yml` mounts are exactly as listed.
4. Deploy Node-RED flow from `my_models/flow_dida_central_lego.json` in DIDA central.
5. Validate Node-RED endpoint:
   - `POST /smia/lego/pick`
6. Start stack:
   - `docker compose -f my_models/docker-compose.yml up -d`
7. Open GUI:
   - `http://localhost:10000/smia_operator`
8. Execute `Capability_PickPiece`.
9. Confirm:
   - operator receives `status: ok`
   - MQTT publish appears in central topic
   - warehouse crane macro triggers

This is the complete Case 0 baseline documented from the implemented configuration and observed execution.
