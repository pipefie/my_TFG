# ================================================================
# SMIA Orchestrator Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA image with 4 patches + custom launcher.
#
# Patch 1 — smia_agent.py
#   Asset connection lookup uses ModelReference.__eq__ (object identity
#   in basyx-python-sdk 1.2.1). Fix: three-strategy cascade.
#   See patches/PATCHES.md §1. TODO: remove once upstream PR merged.
#
# Patch 2 — acl_handling_behaviour.py
#   SPADE delivers css-service REQUEST to all matching behaviour inboxes
#   simultaneously. ACLHandlingBehaviour checks reserved_threads before
#   OrchestratorDispatchBehaviour can reserve the thread — duplicate
#   execution. Fix: early return when hasattr(agent, 'pending_orchestrations').
#   See patches/PATCHES.md §2. TODO: remove once upstream PR merged.
#
# Patch 3 — negotiating_behaviour.py
#   Per-thread template passed when adding HandleNegotiationBehaviour,
#   preventing concurrent negotiations from cross-delivering messages.
#   See patches/PATCHES.md §3. TODO: remove once upstream PR merged.
#
# Patch 4 — handle_negotiation_behaviour.py (specific_handle_behaviours/)
#   Iteration-based retry, individual PROPOSE dispatch, proper thread
#   reservation/release, failure INFORM on timeout.
#   See patches/PATCHES.md §4. TODO: remove once upstream PR merged.
#
# Build context: NEW REPO ROOT (the directory containing docker-compose.yml)
#
# docker-compose calls this as:
#   build:
#     context: .
#     dockerfile: agents/orchestrator/Dockerfile
# ================================================================

FROM ekhurtado/smia:latest-alpine

LABEL maintainer="afierro@vicomtech.org"
LABEL org="Vicomtech — Data Intelligence for Industry (DII)"
LABEL description="SMIA Orchestrator Agent — FIPA-CNP multi-machine dispatch"
LABEL project="smia-flexible-manufacturing"

# ── Patches ───────────────────────────────────────────────────────
# Detects the installed SMIA package path at build time — version-independent.
COPY patches/smia_agent.py /tmp/smia_agent_patch.py
COPY patches/acl_handling_behaviour.py /tmp/acl_handling_patch.py
COPY patches/negotiating_behaviour.py /tmp/negotiating_patch.py
COPY patches/handle_negotiation_behaviour.py /tmp/handle_neg_patch.py

RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    echo "[smia-orchestrator] Applying patches at: $SMIA_PKG" && \
    cp /tmp/smia_agent_patch.py    "$SMIA_PKG/agents/smia_agent.py" && \
    cp /tmp/acl_handling_patch.py  "$SMIA_PKG/behaviours/acl_handling_behaviour.py" && \
    cp /tmp/negotiating_patch.py   "$SMIA_PKG/behaviours/negotiating_behaviour.py" && \
    cp /tmp/handle_neg_patch.py    "$SMIA_PKG/behaviours/specific_handle_behaviours/handle_negotiation_behaviour.py" && \
    rm /tmp/smia_agent_patch.py /tmp/acl_handling_patch.py /tmp/negotiating_patch.py /tmp/handle_neg_patch.py

# ── Custom launcher and FIPA-CNP dispatch behaviour ──────────────
# Placed at WORKDIR / so that `from orchestrator_dispatch_behaviour import ...`
# resolves correctly — Python includes the working directory in sys.path.
COPY agents/orchestrator/smia_orchestrator_starter.py /smia_orchestrator_starter.py
COPY agents/orchestrator/orchestrator_dispatch_behaviour.py /orchestrator_dispatch_behaviour.py

WORKDIR /

# Replaces the default SMIA launcher with our ExtensibleSMIAAgent starter,
# which registers OrchestratorDispatchBehaviour for FIPA-CNP negotiation.
# Default image CMD: ["python3", "-m", "smia.launchers.smia_docker_starter"]
CMD ["python3", "-u", "smia_orchestrator_starter.py"]
