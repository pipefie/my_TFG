# ================================================================
# SMIA Orchestrator Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA image with:
#   1. smia_agent.py bug fix (asset connection object-identity comparison)
#      TODO: remove once upstream PR is merged into ekhurtado/smia
#   2. ExtensibleSMIAAgent launcher that registers
#      OrchestratorDispatchBehaviour for FIPA-CNP multi-machine dispatch
#
# Build context: repo root (SMIA/)
# Called from docker-compose as:
#   build:
#     context: ..
#     dockerfile: my_models/docker/smia-orchestrator/Dockerfile
# ================================================================

FROM ekhurtado/smia:latest-alpine

LABEL maintainer="afierro@vicomtech.org"
LABEL org="Vicomtech — Data Intelligence for Industry (DII)"
LABEL description="SMIA Orchestrator Agent — FIPA-CNP multi-machine dispatch"
LABEL project="smia-lego-case0"

# ── Patch 1: fix asset connection object-identity bug ────────────
COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py

# ── Patch 2: fix ACL race condition for orchestrator mode ─────────
# ACLHandlingBehaviour receives css-service REQUESTs at the same time as
# OrchestratorDispatchBehaviour, but checks reserved_threads before the
# orchestrator behaviour can reserve the thread — causing both to handle
# the same message. The patch adds an early return for css-service REQUESTs
# when pending_orchestrations is present (orchestrator-only attribute).
COPY src/smia/behaviours/acl_handling_behaviour.py /tmp/acl_handling_patch.py

RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    echo "[smia-orchestrator] Applying patches at: $SMIA_PKG" && \
    cp /tmp/smia_agent_patch.py "$SMIA_PKG/agents/smia_agent.py" && \
    cp /tmp/acl_handling_patch.py "$SMIA_PKG/behaviours/acl_handling_behaviour.py" && \
    rm /tmp/smia_agent_patch.py /tmp/acl_handling_patch.py

# ── Custom launcher and FIPA-CNP dispatch behaviour ──────────────
# Placed at WORKDIR / so that `from orchestrator_dispatch_behaviour import ...`
# resolves correctly (Python includes the working directory in sys.path).
COPY additional_tools/extended_agents/smia_orchestrator_agent/smia_orchestrator_starter.py /smia_orchestrator_starter.py
COPY additional_tools/extended_agents/smia_orchestrator_agent/orchestrator_dispatch_behaviour.py /orchestrator_dispatch_behaviour.py

WORKDIR /

# Replace the default SMIA launcher with our ExtensibleSMIAAgent starter.
CMD ["python3", "-u", "smia_orchestrator_starter.py"]
