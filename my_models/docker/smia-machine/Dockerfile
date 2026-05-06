# ================================================================
# SMIA Machine Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA image with 3 patches + custom launcher.
#
# Patch 1 — smia_agent.py
#   Asset connection lookup uses ModelReference.__eq__ (object identity
#   in basyx-python-sdk 1.2.1), so two independently constructed
#   ModelReference objects representing the same path never match.
#   Fix: three-strategy cascade (==, str(), key-tuple).
#
# Patch 3 — negotiating_behaviour.py
#   Per-thread template is now passed when adding HandleNegotiationBehaviour,
#   preventing concurrent negotiations from delivering each other's messages.
#
# Patch 4 — handle_negotiation_behaviour.py (specific_handle_behaviours/)
#   Iteration-based retry, individual PROPOSE dispatch, proper thread
#   reservation/release, failure INFORM on timeout.
#
# TODO: remove patches once upstream PRs are merged into ekhurtado/smia
#
# Build context: repo root (SMIA/)
# Called from docker-compose as:
#   build:
#     context: ..
#     dockerfile: my_models/docker/smia-machine/Dockerfile
# ================================================================

FROM ekhurtado/smia:latest-alpine

LABEL maintainer="afierro@vicomtech.org"
LABEL org="Vicomtech — Data Intelligence for Industry (DII)"
LABEL description="SMIA Machine Agent — fischertechnik warehouse crane integration"
LABEL project="smia-lego-case0"

# ── Patches ───────────────────────────────────────────────────────
COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py
COPY src/smia/behaviours/negotiating_behaviour.py /tmp/negotiating_patch.py
COPY src/smia/behaviours/specific_handle_behaviours/handle_negotiation_behaviour.py /tmp/handle_neg_patch.py

RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    echo "[smia-machine] Applying patches at: $SMIA_PKG" && \
    cp /tmp/smia_agent_patch.py    "$SMIA_PKG/agents/smia_agent.py" && \
    cp /tmp/negotiating_patch.py   "$SMIA_PKG/behaviours/negotiating_behaviour.py" && \
    cp /tmp/handle_neg_patch.py    "$SMIA_PKG/behaviours/specific_handle_behaviours/handle_negotiation_behaviour.py" && \
    rm /tmp/smia_agent_patch.py /tmp/negotiating_patch.py /tmp/handle_neg_patch.py

# ── Custom launcher and service module ───────────────────────────
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /smia_machine_starter.py
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py /smia_machine_agent_services.py

WORKDIR /

CMD ["python3", "-u", "smia_machine_starter.py"]
