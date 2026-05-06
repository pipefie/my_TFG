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

## Patch 4 — `negotiating_behaviour.py`: Concurrent negotiations cross-contaminate messages

### File and method

`src/smia/behaviours/negotiating_behaviour.py`
Method: the block that spawns `HandleNegotiationBehaviour` (~line 80)

### Symptom

When multiple simultaneous FIPA-CNP negotiations are running (e.g., two operators trigger requests in quick succession), `HandleNegotiationBehaviour` instances intended for different negotiation threads receive each other's PROPOSE messages. This produces incorrect negotiation outcomes — a machine may lose a negotiation it should have won, or declare itself the winner when it should not.

### Root cause

In the upstream code, `NegotiatingBehaviour` adds `HandleNegotiationBehaviour` with the standard negotiation template but **without a thread filter**:

```python
# ORIGINAL — no thread-specific template
self.myagent.add_behaviour(specific_neg_handling_behaviour)
```

SPADE matches behaviours to messages by template. Without a per-thread filter, every `HandleNegotiationBehaviour` instance receives every negotiation message that matches the base template — including PROPOSE messages from completely different negotiations. With multiple concurrent negotiations, the wrong handler processes the wrong message.

### Fix

Pass a combined per-thread template when registering the behaviour:

```python
# PATCHED
handle_neg_template_propose = GeneralUtils.create_acl_template(
    performative=FIPAACLInfo.FIPA_ACL_PERFORMATIVE_PROPOSE,
    protocol=FIPAACLInfo.FIPA_ACL_CONTRACT_NET_PROTOCOL, thread=msg.thread)
handle_neg_template_request = GeneralUtils.create_acl_template(
    performative=FIPAACLInfo.FIPA_ACL_PERFORMATIVE_REQUEST,
    protocol=FIPAACLInfo.FIPA_ACL_CONTRACT_NET_PROTOCOL, thread=msg.thread)
handle_neg_template = handle_neg_template_propose | handle_neg_template_request
self.myagent.add_behaviour(specific_neg_handling_behaviour, handle_neg_template)
```

This restricts each `HandleNegotiationBehaviour` instance to only receiving messages whose `thread` matches the specific CFP it was spawned for. Concurrent negotiations are fully isolated.

### Why this approach

The template is built using `GeneralUtils.create_acl_template` — the same utility used elsewhere in SMIA for template construction — so the approach is consistent with the existing codebase. The `|` operator on SPADE templates produces a union template, so the handler receives both PROPOSE and REQUEST messages for its thread (REQUEST is needed for the retry mechanism in Patch 4). The fix is localized to a single `add_behaviour` call.

**Applied to:** machine and orchestrator Dockerfiles (machines participate as responders, orchestrator as CFP initiator whose machines then use this behaviour).

---

## Patch 5 — `handle_negotiation_behaviour.py`: Negotiation deadlock and lost PROPOSE messages

### File and method

`src/smia/behaviours/specific_handle_behaviours/handle_negotiation_behaviour.py`
Multiple methods throughout the class.

### Symptom

With more than 2 machines in a negotiation round, negotiations frequently failed to resolve: the orchestrator waited indefinitely for a winner INFORM that never arrived, or logged a negotiation timeout. This happened reliably with 3+ eligible machines (e.g., a `color=red` request with machines 0, 3, and 5 all eligible).

### Root cause

The upstream negotiation algorithm has two interacting problems:

**Problem A — Race on first PROPOSE delivery:**
Each machine receives a CFP, computes its availability value, and then immediately sends PROPOSE messages to all other negotiation targets. If a machine's PROPOSE arrives at a peer *before* the peer has registered its `HandleNegotiationBehaviour` (i.e., before the peer has processed its own CFP and spawned the behaviour), the PROPOSE falls through to the generic `ACLHandlingBehaviour`, which ignores it. The sending machine's PROPOSE is permanently lost from the recipient's perspective.

With the original timeout of 10s and no retry mechanism, a machine that missed a PROPOSE simply waited until the timeout expired, then declared itself the winner (incorrectly) because `len(targets_processed) == len(targets) - 1` was satisfied with zero processed targets when there was only one target to process.

**Problem B — Behaviour kills itself too early:**
In the upstream code, when a machine determined it had lost (received a higher value), it called `exit_negotiation(is_winner=False)` and returned immediately, removing the behaviour. If a late PROPOSE arrived afterward (from a machine that retried), the behaviour was already gone — that message was never processed.

**Problem C — Single long receive timeout:**
The original code used `await self.receive(timeout=10)` — a 10-second blocking receive per iteration. This made retry logic impossible: if no message arrived for 10 seconds (because the PROPOSE was lost in Problem A), the behaviour had no way to re-request it.

### Fix overview

The patch is a substantial rewrite of `HandleNegotiationBehaviour` that addresses all three problems:

**Fix A — Deferred exit, not immediate:**
Instead of calling `exit_negotiation()` and returning as soon as a higher value is received, the result is stored in `self.negotiation_result`:
```python
self.negotiation_result = {'winner': False, 'timestamp': GeneralUtils.get_current_timestamp()}
# Processing continues — behaviour stays alive to handle any late messages
```
The behaviour only terminates at the end of the iteration budget (`self.final_iteration`).

**Fix B — Short receive timeout + iteration counter:**
The receive timeout is reduced from 10s to 0.01s:
```python
msg = await self.receive(timeout=0.01)
```
On each `None` return (no message), `self.iterations_pending` is incremented. At specific iterations (randomly chosen in the range 20–60% of `final_iteration`), the machine sends a `REQUEST` message to peers that have not yet been processed:
```python
await self.request_remaining_neg_acl_msgs()
```
This explicitly asks lagging peers to re-send their PROPOSE.

**Fix C — Individual PROPOSE dispatch:**
The original code sent PROPOSE to all peers in a single batch. The patch sends to one target at a time via `targets_remaining_propose` (a set populated at init), with a small `asyncio.sleep(0.01)` between sends, reducing the chance that all machines flood each other simultaneously.

**Fix D — Proper thread reservation:**
`HandleNegotiationBehaviour.on_start()` now calls `await self.myagent.add_reserved_thread(self.neg_thread)`, and `exit_negotiation()` calls `await self.myagent.remove_reserved_thread(self.neg_thread)`. This cooperates with `ACLHandlingBehaviour`'s `reserved_threads` check, ensuring that once a `HandleNegotiationBehaviour` is running for a thread, `ACLHandlingBehaviour` does not also process messages on that thread.

**Fix E — Failure INFORM on timeout:**
If the behaviour reaches `final_iteration` without a resolved result, it sends a `FAILURE` performative to the `negRequester` (orchestrator) with a clear reason, rather than hanging indefinitely.

### Why this approach

The retry and deferred-exit design follows the same pattern already used by SMIA for service timeouts elsewhere in the framework. The iteration budget (`max(5, len(targets) + 3)`) scales with the number of negotiation participants, avoiding a fixed constant that would be wrong for both small and large negotiations. The `asyncio.sleep(0.01)` between individual sends is the minimum delay that allows SPADE's event loop to deliver in-flight messages between sends — the value was determined empirically.

**Applied to:** machine and orchestrator Dockerfiles (both roles participate in the PROPOSE exchange as responders).

---

## Upstream PR status

| Patch | Status |
|---|---|
| Patch 1 — `smia_agent.py` | Pending — awaiting upstream PR submission |
| Patch 2 — `acl_handling_behaviour.py` | Pending — awaiting upstream PR submission (remove debug lines 77–78 first) |
| Patch 3 — `operator_gui_logic.py` | Pending — awaiting upstream PR submission |
| Patch 4 — `negotiating_behaviour.py` | Pending — awaiting upstream PR submission |
| Patch 5 — `handle_negotiation_behaviour.py` | Pending — awaiting upstream PR submission (remove TODO BORRAR BUG TEST warning lines first) |

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

---

## Deep-Dive Walkthrough — For Presentation to the SMIA Author

The sections below provide a complete step-by-step trace for each patch: exactly which file and line to open, how to mentally execute the code path, why the bug is triggered, and why the fix cannot break anything. This is intended for the technical walkthrough with Ekaitz Hurtado.

---

### Walkthrough 1 — Patch 1: The Silent Crane

#### The symptom in plain language

You click the operator GUI, the operator sends a FIPA REQUEST to the machine, the machine's log says it received the message and started handling the capability — and then nothing. No HTTP call to Node-RED. No error. No timeout. The crane sits still. Looking at the logs you see "capability handling started" and then the next message is the idle heartbeat. The failure is completely silent.

#### Full execution path with file:line references

**Step 1 — Boot: AID parsing and storage**

File: `src/smia/behaviours/init_aas_model_behaviour.py`

During Track 1 of self-configuration, SMIA iterates over all `Interface` SubmodelElements in the `AssetInterfacesDescription` submodel. For each interface it:
1. Creates an `AssetConnection` handler object (an HTTP client configured with the base URL from EndpointMetadata)
2. Creates a `ModelReference` pointing to that interface element in the AAS model: `interface_model_ref = ModelReference.from_referable(interface_elem)` — this is around line 353 in v0.3.x
3. Stores it: `self.myagent.asset_connections[interface_model_ref] = asset_connection_instance`

The key point: `ModelReference.from_referable()` is a BaSyx SDK factory method that walks the element's parent chain to build the key sequence. It produces a `ModelReference` whose `.key` list encodes the full path: `[AssetInterfacesDescription, InterfaceHTTP, InteractionMetadata, actions, pickPiece]`.

**Step 2 — Execution: CSS chain traversal**

File: `src/smia/behaviours/handle_capability_behaviour.py`

When `HandleCapabilityBehaviour` runs (spawned per-request), it resolves the CSS chain:
- `Capability_PickPiece` → `isRealizedBy` → `Skill_PickPiece`
- `Skill_PickPiece` → `accessibleThroughAssetService` → OWL SkillInterface instance

The OWL SkillInterface instance holds a reference to the AAS `RelationshipElement` that was used to create it. From that element, SMIA navigates to the second element (the AID action element) to build a new `ModelReference`. This happens around line 419:
```python
aas_asset_interface_elem = aas_skill_interface_elem.get_associated_asset_interface()
# aas_asset_interface_elem is the AID action SubmodelElement
# A new ModelReference is constructed from it
```

**Step 3 — The failed lookup**

File: `src/smia/agents/smia_agent.py`, method `get_asset_connection_class_by_ref()` (line ~220)

```python
for conn_ref, conn_class in self.asset_connections.items():
    if conn_ref == asset_connection_ref:   # always False
        return conn_class
raise AASModelReadingError(...)
```

The `conn_ref` was built by `ModelReference.from_referable()` during boot. The `asset_connection_ref` was built through a different path during execution. Both represent the same logical reference path. But in `basyx-python-sdk 1.2.1`, `ModelReference.__eq__` is not overridden to perform a structural comparison — Python falls back to `object.__eq__`, which is object identity (`is`). Two distinct `ModelReference` instances are never the same object, so `==` returns `False` on every iteration.

**Step 4 — Silent swallowing**

The `AASModelReadingError` raised by step 3 is caught somewhere in the call chain and logged at DEBUG level (not ERROR), so it doesn't appear prominently in the logs unless you set `LOG_LEVEL=DEBUG`. The capability handling coroutine exits without sending any INFORM back to the operator. The operator GUI waits for a response that never comes, and after a timeout it shows a generic error.

#### How to verify the bug without the patch

To confirm the bug yourself before applying the patch, add this inside the loop in `smia_agent.py`:

```python
for conn_ref, conn_class in self.asset_connections.items():
    print(f"[DEBUG] comparing: {conn_ref!r} == {asset_connection_ref!r} → {conn_ref == asset_connection_ref}")
    print(f"[DEBUG] str: '{str(conn_ref)}' vs '{str(asset_connection_ref)}' → {str(conn_ref) == str(asset_connection_ref)}")
    print(f"[DEBUG] same object: {conn_ref is asset_connection_ref}")
```

You will see: `==` → `False`, `str()` comparison → `True`, `is` → `False`. This confirms the bug: the two objects represent the same path (equal string representations) but are different objects (unequal by identity).

#### Why the fix is backward-compatible

The fix adds two fallback strategies inside the same loop iteration. Strategy 1 (`==`) is kept first — if BaSyx ever fixes `ModelReference.__eq__` to be structural, it will take priority and the fallbacks are never reached. Strategy 2 (`str()`) and Strategy 3 (key-tuple) both extract a canonical representation of the reference path, so they match iff the paths are logically identical. No behavior changes for any code path that doesn't enter this method, and the method's return type is unchanged.

---

### Walkthrough 2 — Patch 2: The Phantom Capability Execution

#### The symptom in plain language

In orchestrator mode, when the operator sends a pick request, two things happen at once on the orchestrator. One is correct: `OrchestratorDispatchBehaviour` starts the FIPA-CNP negotiation round. The other is wrong: `ACLHandlingBehaviour` also picks up the same message and tries to execute `Capability_PickPiece` locally on the orchestrator — which has no HTTP AssetConnection, so it crashes with a `NoneType` error, or it sends a premature INFORM back to the operator before the real negotiation finishes.

#### Full execution path with file:line references

**Step 1 — SPADE message delivery model**

SPADE (file `spade/behaviour.py` in the spade package — not in SMIA's source) uses an asyncio event loop. When a message arrives on the XMPP transport, SPADE runs through all registered behaviours and checks each behaviour's `template`. If a behaviour has `template.match(msg) == True`, the message is placed in that behaviour's asyncio `Queue`.

Crucially: SPADE does this placement for **all matching behaviours simultaneously** within the same event loop tick. There is no priority queue. There is no first-claim mechanism. The message lands in every matching inbox.

The orchestrator has two behaviours registered:
- `ACLHandlingBehaviour` — SMIA built-in, template matches all FIPA messages with `ontology=css-service`
- `OrchestratorDispatchBehaviour` — TFG extension, template also matches `ontology=css-service, performative=request`

Both inboxes receive the same message simultaneously.

**Step 2 — The `reserved_threads` mechanism and why it fails here**

File: `src/smia/behaviours/acl_handling_behaviour.py`, method `run()` (line ~42)

SMIA has a mechanism for INFORM messages (replies to earlier requests) where only one behaviour should process a given reply. The mechanism is `reserved_threads`: the handler that initiated a request registers the `thread` ID so that ACLHandlingBehaviour skips it:

```python
if msg.thread not in self.myagent.reserved_threads:
    # spawn HandleCapabilityBehaviour
```

But this cannot work for initial REQUEST messages because:
1. For a REQUEST, no behaviour has pre-registered the thread (it's a new conversation)
2. Even if `OrchestratorDispatchBehaviour` tried to register the thread before `ACLHandlingBehaviour` checked, both behaviours wake up in the same asyncio scheduling cycle — they both run `receive()` concurrently within the same `asyncio.gather` call. There is no guaranteed ordering.

The debug lines currently in the file (lines 77–78) — `TODO BORRAR BUG TEST` — print the `reserved_threads` set right before the check. During testing they always showed `set()` (empty), confirming that the race window is real and that `reserved_threads` is always empty when `ACLHandlingBehaviour` evaluates it.

**Step 3 — The wrong execution on the orchestrator**

If `ACLHandlingBehaviour` proceeds past the `reserved_threads` check, it calls:
```python
handle_capability_behaviour = HandleCapabilityBehaviour(...)
self.agent.add_behaviour(handle_capability_behaviour)
```

`HandleCapabilityBehaviour` resolves `Capability_PickPiece` → `Skill_Orchestrate_PickPiece`. But the orchestrator's AASX declares `Skill_Orchestrate_PickPiece` with `hasImplementationType=OPERATION` and its SkillInterface connected via `accessibleThroughAgentService`. There is no `AssetConnection` for this skill — the orchestrator has no physical machine to call. The code path either:
- Raises `NoneType is not subscriptable` when it tries to call `asset_connection.http_post()`
- Or, if the service registration lookup succeeds by chance, sends a malformed INFORM back to the operator immediately, before the FIPA-CNP round completes

#### How to verify the bug without the patch

Remove the `hasattr` check block and add logging before the `reserved_threads` check:

```python
print(f"[DEBUG Patch2] ACLHandlingBehaviour got msg: ontology={msg.get_metadata('ontology')} performative={msg.get_metadata('performative')}")
print(f"[DEBUG Patch2] reserved_threads: {self.myagent.reserved_threads}")
```

Send a REQUEST from the operator. You will see two log lines: one from `OrchestratorDispatchBehaviour` (correctly identifying it as a new negotiation task) and one from `ACLHandlingBehaviour` (incorrectly trying to handle the same message). The `reserved_threads` set will be empty both times.

#### Why the fix is backward-compatible

`pending_orchestrations` is a `dict` attribute set in `OrchestratorDispatchBehaviour.on_start()`. On any agent that does NOT run `OrchestratorDispatchBehaviour`, this attribute is never set, so `hasattr(self.myagent, 'pending_orchestrations')` returns `False` and the early return is never taken. The patch is physically transparent on all machine agents and the operator agent. Only on the orchestrator — where the attribute exists and where `ACLHandlingBehaviour` must not process initial css-service REQUESTs — does the early return fire.

**Note:** The debug lines 77–78 (`TODO BORRAR BUG TEST`) were added during diagnosis and should be removed before the upstream PR. They remain in the current patched file.

---

### Walkthrough 3 — Patch 3: The Invisible Form Fields

#### The symptom in plain language

When the operator GUI performs a "Load" (scanning all AASX files in the `aas/` folder), it returns HTTP 500. The `smia-operator` Docker log shows a Python traceback. If you look at the traceback carefully, you see a `KeyError` on a key called `'skillData'`. This only happens when the `aas/` folder contains the orchestrator AASX — because that AASX has a `hasParameter` relationship. Remove the orchestrator AASX from the folder, and the Load works fine.

#### Why these bugs were never found before

No AASX file in the upstream SMIA repository or examples has a `RelationshipElement` with `semanticId = http://www.w3id.org/hsu-aut/css#hasParameter`. The entire `hasParameter` branch in `operator_gui_logic.py` was written but never executed. The bugs are latent — they exist in the source code but only activate when you provide an AASX that actually uses `hasParameter`. The orchestrator AASX in this project is the first to do so.

#### Full execution path with file:line references

File: `additional_tools/extended_agents/smia_operator_agent/operator_gui_logic.py`

The upstream version of this file is at: `use_cases/simple_human_in_the_mesh/smia_operator_code/operator_gui_logic.py`

Method: `operator_load_controller()`, the block inside `if CapabilitySkillOntologyInfo.CSS_ONTOLOGY_PROP_HASPARAMETER_IRI == rel.iri:` — around line 125 in v0.3.x.

**The load loop structure:**

```python
for rel in skill_relationships:             # iterates RelationshipElements by semanticId
    aas_elems = get_css_elements_by_relationship(rel)
    # aas_elems: dict mapping domain_element → [list of range_elements]
    # e.g. { 'Skill_Orchestrate_PickPiece': [<SkillParameter_color object>] }

    if rel.iri == CSS_ONTOLOGY_PROP_HASPARAMETER_IRI:
        for skill, skill_param in aas_elems.items():   # Bug B: skill_param is a list, not an element
            if skill not in css_elems_info['skillData']:  # Bug A: 'skillData' key doesn't exist
                param_set = set()
                param_set.add(skill_param)             # Bug B: list is unhashable
                self.myagent.skills_info[skill] = param_set
            else:
                self.myagent.skills_info[skill].add(skill_param)  # Bug B again; also Bug C
```

**Bug A in detail (line 127 approx):**

`css_elems_info` is a `dict` populated earlier in the same method with capability `id_short` strings as keys. Its schema is something like `{ 'Capability_PickPiece': {...}, 'Capability_PlacePiece': {...} }`. The key `'skillData'` is **never assigned** anywhere in `operator_gui_logic.py`. It is a dead reference to a variable or dict key that does not exist. The line `css_elems_info['skillData']` always raises `KeyError: 'skillData'`.

The correct guard should use `self.myagent.skills_info` (the dict being populated), not `css_elems_info`.

**Bug B in detail (lines 129–130, 132):**

`get_css_elements_by_relationship()` is defined earlier in the same file and returns a `dict` mapping **each domain element to a list of range elements**. This is consistent with how `isRealizedBy`, `isRestrictedBy`, and all other CSS relationship types are processed — they all return lists (because a Capability can be realized by multiple Skills, for example).

So `aas_elems.items()` yields `(skill_id_short, [<SkillParameter object>, ...])`. The loop variable `skill_param` holds the entire list. Then `param_set.add(skill_param)` tries to add a list to a Python `set`. Lists are mutable and therefore unhashable. This raises `TypeError: unhashable type: 'list'`. (If Bug A hadn't already crashed the method, Bug B would.)

**Bug C in detail (line 130):**

Even if you fixed Bugs A and B naively (e.g., checked `self.myagent.skills_info` and iterated the list), the code would store the `SkillParameter` AAS element object in `skills_info`. The downstream code that renders the operator's form fields and processes submissions does:

```python
skill_params = eval(available_smia['skillParameters'])
# then later:
value = form.get(param_name)
```

`skillParameters` is the string representation of the `skills_info` set. If that set contains an `ExtendedSkillParameter` object, its `__repr__` produces something like `<ExtendedSkillParameter object at 0x7f…>`, which is not a valid Python literal. `eval()` raises `SyntaxError`. Even before that, `form.get(<object>)` returns `None` because form keys are strings, not AAS objects.

The correct value to store is `p.id_short` — the short name of the `SkillParameter` element in the AAS (e.g., `'color'`). The orchestrator AASX must name this element with `id_short='color'` (not `'SkillParameter_color'`) because the GUI uses it as the HTML `<input name="…">` directly.

#### How to verify Bug A without the patch

Add a print before the problematic line:

```python
print(f"[DEBUG Patch3] css_elems_info keys: {list(css_elems_info.keys())}")
print(f"[DEBUG Patch3] trying: css_elems_info['skillData']")
```

You will see the keys are capability `id_short` strings — `'skillData'` is absent. The `KeyError` follows immediately.

#### Why the fix is backward-compatible

The fixed code path:
```python
for skill, skill_params_list in aas_elems.items():
    if skill not in self.myagent.skills_info:
        self.myagent.skills_info[skill] = set()
    self.myagent.skills_info[skill].update(p.id_short for p in skill_params_list)
```
is only entered when `rel.iri == CSS_ONTOLOGY_PROP_HASPARAMETER_IRI`. No upstream SMIA AASX has a `hasParameter` relationship. For all existing deployments, this branch is never reached and the fix has zero effect. For the orchestrator AASX in this project, the fix produces correct behavior.

---

### Summary Table — All Three Patches

| | Patch 1 | Patch 2 | Patch 3 |
|---|---|---|---|
| **File** | `src/smia/agents/smia_agent.py` | `src/smia/behaviours/acl_handling_behaviour.py` | `additional_tools/.../operator_gui_logic.py` |
| **Method** | `get_asset_connection_class_by_ref()` | `run()` | `operator_load_controller()` |
| **Root cause** | `ModelReference.__eq__` uses object identity, not structural comparison | SPADE delivers to all matching behaviour inboxes; `reserved_threads` check has a fundamental race window | Three bugs in a code path never reached by any existing upstream AASX (no `hasParameter` used anywhere) |
| **Symptom** | Crane never moves; no error in logs | Two conflicting executions for one operator REQUEST; orchestrator crash or duplicate INFORM | HTTP 500 on operator Load; `KeyError: 'skillData'` in log |
| **Fix** | Three-strategy cascade: `==`, `str()`, key-tuple | `hasattr(agent, 'pending_orchestrations')` early return | Fix dict key, iterate list, store `id_short` strings |
| **How applied** | `RUN cp` in machine + orchestrator Dockerfiles | `RUN cp` in orchestrator Dockerfile only | `COPY` patched file to WORKDIR (no `RUN` needed) |
| **Backward-compatible?** | Yes — Strategy 1 preserved; fallbacks only fire when `==` fails | Yes — attribute absent on all non-orchestrator agents; early return never taken on machines | Yes — branch never entered if no `hasParameter` in AASX |
| **Upstream PR status** | Pending | Pending (remove debug lines 77–78 first) | Pending |
