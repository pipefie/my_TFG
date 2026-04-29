# SMIA Framework — Bug Fixes and Patches

This document describes three bugs found in the SMIA framework (v0.3.x) during the
implementation of this project. Each section covers: where the bug lives, how it was
discovered, the exact root cause traced through the source code, the fix applied, and
why that specific approach was chosen.

All three patches are applied at Docker image build time — the corrected files are
copied over the installed SMIA package inside the container. None of the fixes require
changes to the SMIA public API or to any AASX model. Once upstream PRs are merged,
the `patches/` folder and the corresponding `RUN` steps in the Dockerfiles can be removed.

**SMIA repository:** https://github.com/ekhurtado/SMIA
**SMIA version tested:** 0.3.1 (Docker image `ekhurtado/smia:latest-alpine`)

---

## Patch 1 — `smia_agent.py`: Asset connection lookup fails silently

### File and method

`src/smia/agents/smia_agent.py`
Method: `SMIAAgent.get_asset_connection_class_by_ref()` (line 220 in v0.3.x)

### Symptom

In Case 0 (direct operator → machine execution): the operator GUI submitted a pick
request, the machine SMIA received the FIPA-ACL message, successfully resolved the CSS
chain (`Capability → Skill → SkillInterface → AID action element`), and then produced
**no HTTP call** to Node-RED and **no visible error** in the logs. The crane never moved.

The only diagnostic signal was that the SMIA log showed the capability resolution
completing but no outgoing HTTP request — the agent silently swallowed the failure.

### Root cause

During boot (Track 1 of self-configuration, `AASInitializationBehaviour`), SMIA parses
the AID submodel and stores each interface's `AssetConnection` object in a dictionary
keyed by the AAS `ModelReference` of that interface:

```python
# init_aas_model_behaviour.py (simplified)
self.asset_connections[interface_reference] = asset_connection_instance
```

Later, during capability execution (`HandleCapabilityBehaviour`), SMIA resolves the CSS
chain and needs to retrieve the stored `AssetConnection`. It calls:

```python
# smia_agent.py — ORIGINAL (buggy) code
async def get_asset_connection_class_by_ref(self, asset_connection_ref):
    async with self.lock:
        for conn_ref, conn_class in self.asset_connections.items():
            if conn_ref == asset_connection_ref:   # ← the problem
                return conn_class
        raise AASModelReadingError(...)
```

The comparison `conn_ref == asset_connection_ref` uses Python's default `==` operator.
Both variables are instances of `basyx.aas.model.ModelReference` — a BaSyx SDK class
representing an AAS reference path (a sequence of `Key` objects, each with a type and a
value string).

The critical observation: **the two `ModelReference` instances were created at different
points in the execution**. The one stored as the dictionary key was created during
initialization when parsing the AID submodel. The one passed as `asset_connection_ref`
was constructed fresh during skill execution when the CSS chain traversal reached the
AID element. Even though both describe the same path (e.g.,
`[AssetInterfacesDescription → InterfaceHTTP → InteractionMetadata → actions → pickPiece]`),
they are **different Python objects created through different code paths**.

We verified by inspection that `basyx.aas.model.ModelReference.__eq__` is not
implemented in `basyx-python-sdk 1.2.1` in a way that performs a value-based
structural comparison across independently constructed instances. The result is that
`==` falls back to object identity (`is`), which returns `False` for two distinct
instances even if they represent identical paths. The loop exhausts without a match and
raises `AASModelReadingError`, which is caught upstream and silently logged at debug
level — the operator GUI shows no error either.

### Fix

The fix adds two fallback comparison strategies after the default `==` check:

```python
# smia_agent.py — PATCHED
async def get_asset_connection_class_by_ref(self, asset_connection_ref):
    async with self.lock:
        def _ref_keys_tuple(ref_obj):
            if ref_obj is None or not hasattr(ref_obj, "key"):
                return None
            try:
                return tuple((str(key.type), key.value) for key in ref_obj.key)
            except Exception:
                return None

        requested_ref_keys = _ref_keys_tuple(asset_connection_ref)
        for conn_ref, conn_class in self.asset_connections.items():
            if conn_ref == asset_connection_ref:          # Strategy 1: original (object identity)
                return conn_class
            if str(conn_ref) == str(asset_connection_ref): # Strategy 2: string representation
                return conn_class
            if requested_ref_keys is not None and _ref_keys_tuple(conn_ref) == requested_ref_keys:
                return conn_class                         # Strategy 3: key-tuple structural comparison
        raise AASModelReadingError(...)
```

**Strategy 1** (`==`) is kept as-is — if BaSyx ever adds a proper `__eq__`, it takes priority.

**Strategy 2** (`str()` comparison) exploits the fact that `ModelReference.__str__`
serializes the full key path as a human-readable string. Both instances, representing
the same path, produce the same string. This is the fastest fallback and handles the
common case.

**Strategy 3** (key-tuple) is a structural comparison that normalizes each `Key` in the
reference into a `(type_string, value_string)` tuple and compares the resulting tuples.
This is the most explicit and robust form — it would catch cases where `str()` differs
due to formatting changes but the underlying path is identical.

### Why this approach

Alternative approaches considered:

- **Pre-converting references to strings at storage time** — would require modifying
  the AAS initialization code and would lose the original `ModelReference` object,
  breaking any downstream code that expects it as the key.
- **Patching BaSyx `ModelReference.__eq__`** — would require a separate dependency
  patch and introduces risk of side effects in BaSyx's own comparison logic.
- **Using `id_short` strings as keys instead of `ModelReference`** — would be a
  larger refactor of `smia_agent.py` and might break other callers.

The three-strategy cascade is the minimal, backward-compatible fix: it changes only
one method, adds no new dependencies, and degrades gracefully if BaSyx's behavior
changes in future versions.

---

## Patch 2 — `acl_handling_behaviour.py`: Message delivered to both behaviours simultaneously

### File and method

`src/smia/behaviours/acl_handling_behaviour.py`
Class: `ACLHandlingBehaviour`, method: `run()` (line 42)

### Symptom

In Case 1 (orchestrated mode): when the operator GUI sent a `css-service` REQUEST to
the orchestrator agent, the orchestrator executed two conflicting actions concurrently:

1. `OrchestratorDispatchBehaviour` (the TFG extension) correctly handled the message —
   discovered eligible machines, built a FIPA-CNP CFP, sent it to machine agents.

2. `ACLHandlingBehaviour` (SMIA built-in) also handled the same message — spawned a
   `HandleCapabilityBehaviour` on the orchestrator, which attempted to resolve
   `Capability_PickPiece` locally as if the orchestrator were a machine agent.

This produced either a crash (`NoneType` error because the orchestrator has no AID
asset service for physical execution) or a duplicate INFORM sent back to the operator,
corrupting the response.

### Root cause

SPADE (the underlying Python multi-agent framework) runs all behaviours within a single
`asyncio` event loop. Message delivery in SPADE works as follows: when an XMPP message
arrives, SPADE evaluates the `template` of every registered behaviour. If the message
matches a behaviour's template, **the message is placed in that behaviour's inbox**. If
multiple behaviour templates match the same message, **the message is placed in all of
them simultaneously** — there is no first-come-first-served claiming.

Both `ACLHandlingBehaviour` and `OrchestratorDispatchBehaviour` are registered on the
orchestrator agent with templates that match `css-service` REQUEST messages. SPADE
delivers the message to both inboxes in the same asyncio scheduling round.

SMIA has an existing mechanism called `reserved_threads` to prevent duplicate handling
of INFORM messages (which arrive as replies to earlier requests, and only one behaviour
should process each reply). The check in `ACLHandlingBehaviour.run()` is:

```python
if msg.thread not in self.myagent.reserved_threads:
    # spawn HandleCapabilityBehaviour
```

This mechanism **cannot solve the problem here** for a fundamental timing reason:
`ACLHandlingBehaviour` processes its inbox in `run()`, which is a coroutine yielding
control only at `await` points. When `ACLHandlingBehaviour.run()` wakes up and receives
the message, it checks `reserved_threads` *before* `OrchestratorDispatchBehaviour` has
had the chance to run `add_reserved_thread()`. Since both behaviours check their inboxes
in the same asyncio scheduling cycle, `reserved_threads` is still empty when
`ACLHandlingBehaviour` performs its check.

### Fix

The fix uses a **synchronous sentinel attribute check**:

```python
# acl_handling_behaviour.py — PATCHED (added block after the ontology validity check)
if (msg.get_metadata(FIPAACLInfo.FIPA_ACL_ONTOLOGY_ATTRIB) ==
        ACLSMIAOntologyInfo.ACL_ONTOLOGY_CSS_SERVICE and
        msg.get_metadata(FIPAACLInfo.FIPA_ACL_PERFORMATIVE_ATTRIB) ==
        FIPAACLInfo.FIPA_ACL_PERFORMATIVE_REQUEST and
        hasattr(self.myagent, 'pending_orchestrations')):
    return  # OrchestratorDispatchBehaviour handles css-service REQUESTs
```

`pending_orchestrations` is an attribute set in `OrchestratorDispatchBehaviour.on_start()`,
which SMIA calls during agent initialization — well before any messages are processed.
Machine agents and the operator agent never have this attribute.

The check is entirely synchronous — it does not involve any `await`, no coroutine
scheduling, no shared mutable state beyond a simple `hasattr()` call. There is no window
in which this check can race with anything: if the orchestrator is running, the attribute
exists; if it is not, the attribute does not exist.

### Why this approach

The ideal fix would be to give `OrchestratorDispatchBehaviour` a SPADE template that is
more specific than `ACLHandlingBehaviour`'s template, so that SPADE routes initial
`css-service` REQUESTs exclusively to the orchestrator behaviour. However, SPADE's
template priority mechanism requires that one behaviour's template be a strict subset of
another's — and because both behaviours must also receive INFORM messages (replies from
machine agents), their templates cannot be cleanly separated by performative alone
without breaking the INFORM reception chain.

The `hasattr` sentinel is the least invasive approach: it touches only
`ACLHandlingBehaviour` (one early-return block), makes no changes to the orchestrator
behaviour, and the condition is physically impossible to be true on a machine agent
(machine agents never run `OrchestratorDispatchBehaviour.on_start()`, so
`pending_orchestrations` is never set on them). The patch is therefore transparent on
all non-orchestrator agents.

---

## Patch 3 — `operator_gui_logic.py`: Three latent bugs in `hasParameter` processing

### File and method

`additional_tools/extended_agents/smia_operator_agent/operator_gui_logic.py`
Class: `OperatorGUILogic`, method: `operator_load_controller()` — the `hasParameter` branch

### Background: why these bugs were never triggered before

The `hasParameter` CSS relationship connects a `Skill` to its `SkillParameter` elements,
allowing the operator GUI to render dynamic input fields for each parameter (e.g., a
colour selector when the skill requires a colour argument).

No SMIA example AASX in the upstream repository has a `RelationshipElement` with
`semanticId = http://www.w3id.org/hsu-aut/css#hasParameter`. The `hasParameter` block
in `operator_gui_logic.py` was therefore **never executed in any known SMIA deployment**
before this project. The bugs are latent — they exist in the upstream code but only
manifest when an AASX actually uses `hasParameter`, which the orchestrator AASX in this
project does (for `SkillParameter_color` linked to `Skill_Orchestrate_PickPiece`).

### Symptom

When the operator GUI performed a Load operation (scanning all AASX files), it returned
a 500 error or malformed JSON. The Python traceback visible in the `smia-operator`
Docker log showed a `KeyError` on the first frame, before any CSS elements were displayed.

### Original buggy code

```python
# operator_gui_logic.py — ORIGINAL (upstream, v0.3.x)
if CapabilitySkillOntologyInfo.CSS_ONTOLOGY_PROP_HASPARAMETER_IRI == rel.iri:
    for skill, skill_param in aas_elems.items():
        if skill not in css_elems_info['skillData']:      # Bug A
            param_set = set()
            param_set.add(skill_param)                    # Bug B
            self.myagent.skills_info[skill] = param_set
        else:
            self.myagent.skills_info[skill].add(skill_param)   # Bug B again
```

### Bug A — `KeyError: 'skillData'`

`css_elems_info` is a plain `dict` populated during the load loop. Its keys are
capability `id_short` strings (e.g., `'Capability_PickPiece'`). The key `'skillData'`
is **never assigned anywhere** in the entire `operator_load_controller()` method or
anywhere else in the class. The very first evaluation of `css_elems_info['skillData']`
raises `KeyError`, which propagates up through the aiohttp request handler, causing the
HTTP response to be an unhandled 500.

The correct check should be against `self.myagent.skills_info`, which is the actual
dict being populated with skill-to-parameter mappings.

### Bug B — `TypeError: unhashable type: 'list'`

`aas_elems` is the return value of `get_css_elements_by_relationship()`, which maps
each domain element (the `Skill`) to a **list** of range elements (the `SkillParameter`
objects). This is consistent with how all other CSS relationship types are handled in
the same method — `isRealizedBy` maps `Capability → [Skill1, Skill2, ...]`,
`isRestrictedBy` maps `Capability → [Constraint1, ...]`.

The original code iterates with `for skill, skill_param in aas_elems.items()` — meaning
`skill_param` is the **entire list** `[SkillParameter_color]`, not a single element.
Then `param_set.add(skill_param)` attempts to add a list to a `set`. Lists are unhashable
and cannot be elements of a set. This raises `TypeError: unhashable type: 'list'`.

Even the `else` branch — `self.myagent.skills_info[skill].add(skill_param)` — has the
same error, since it also passes the full list to `set.add()`.

### Bug C — AAS objects stored instead of `id_short` strings

Even if Bugs A and B were fixed naively (e.g., by iterating the list correctly), the
code would store the AAS `SkillParameter` object itself in `skills_info`. Downstream,
the operator GUI's request controller uses `skills_info` to render form fields and
then reads submitted form values by key:

```python
# operator_request_controller (downstream)
skill_params = eval(available_smia['skillParameters'])   # expects string repr of id_short names
value = form.get(param)                                  # expects param to be an id_short string
```

Storing an `ExtendedSkillParameter` AAS object produces a `SyntaxError` on `eval()` and
a `None` on `form.get()` because Python's `__repr__` of an AAS element is not a valid
Python literal. The GUI would render broken input fields and fail silently when the form
was submitted.

### Fix

```python
# operator_gui_logic.py — PATCHED
if CapabilitySkillOntologyInfo.CSS_ONTOLOGY_PROP_HASPARAMETER_IRI == rel.iri:
    for skill, skill_params_list in aas_elems.items():
        if skill not in self.myagent.skills_info:
            self.myagent.skills_info[skill] = set()
        self.myagent.skills_info[skill].update(p.id_short for p in skill_params_list)
```

Changes made:

- **Fix A:** `css_elems_info['skillData']` → `self.myagent.skills_info` (the correct dict).
- **Fix B:** renamed `skill_param` → `skill_params_list` to make clear it is a list; used
  `.update(generator)` to iterate the list and add elements individually.
- **Fix C:** `p.id_short for p in skill_params_list` stores the `id_short` string of each
  `SkillParameter` AAS element, not the AAS object itself. This is what the downstream
  request controller expects.
- **Backward compatibility:** machine AASXs have no `hasParameter` relationship, so this
  branch is never entered for them. The fix has zero impact on existing deployments.

### AASX consequence

The `SkillParameter` element's `id_short` is used directly as the HTML form field name.
For the CSS IRI `http://www.w3id.org/hsu-aut/css#color` to be matched by the request
controller's `_get_skill_param(params, 'color')`, the AAS element must have
`id_short = "color"` (not `"SkillParameter_color"`). The orchestrator AASX in this
project names the element accordingly.

---

## Upstream PR status

| Patch | Status |
|---|---|
| Patch 1 — `smia_agent.py` | Pending — awaiting upstream PR submission |
| Patch 2 — `acl_handling_behaviour.py` | Pending — awaiting upstream PR submission |
| Patch 3 — `operator_gui_logic.py` | Pending — awaiting upstream PR submission |

Once any patch is merged into the official `ekhurtado/smia` repository and released on
the Docker Hub image (`ekhurtado/smia:latest-alpine`), the corresponding `COPY` and `RUN`
lines can be removed from the relevant Dockerfile.

To check whether a patch is still needed against the current upstream version:

```bash
# Pull the latest SMIA image and inspect the relevant file
docker run --rm ekhurtado/smia:latest-alpine \
  python3 -c "
import smia, os
pkg = os.path.dirname(smia.__file__)
with open(f'{pkg}/agents/smia_agent.py') as f:
    src = f.read()
# Patch 1 is needed if the three-strategy lookup is absent
print('Patch 1 needed:', 'str(conn_ref) ==' not in src)
"
```
