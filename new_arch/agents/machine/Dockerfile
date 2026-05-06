# ================================================================
# SMIA Machine Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA image with 3 patches + custom launcher.
#
# Patch 1 — smia_agent.py
#   Asset connection lookup uses ModelReference.__eq__ (object identity
#   in basyx-python-sdk 1.2.1). Fix: three-strategy cascade (==, str(),
#   key-tuple). See patches/PATCHES.md §1.
#   TODO: remove once upstream PR is merged into ekhurtado/smia
#
# Patch 3 — negotiating_behaviour.py
#   Per-thread template passed when adding HandleNegotiationBehaviour,
#   preventing concurrent negotiations from cross-delivering messages.
#   See patches/PATCHES.md §4.
#   TODO: remove once upstream PR is merged
#
# Patch 4 — handle_negotiation_behaviour.py (specific_handle_behaviours/)
#   Iteration-based retry, individual PROPOSE dispatch, proper thread
#   reservation/release, failure INFORM on timeout.
#   See patches/PATCHES.md §5.
#   TODO: remove once upstream PR is merged
#
# Build context: NEW REPO ROOT (the directory containing docker-compose.yml)
#
# docker-compose calls this as:
#   build:
#     context: .
#     dockerfile: agents/machine/Dockerfile
# ================================================================

FROM ekhurtado/smia:latest-alpine

LABEL maintainer="afierro@vicomtech.org"
LABEL org="Vicomtech — Data Intelligence for Industry (DII)"
LABEL description="SMIA Machine Agent — virtual factory integration"
LABEL project="smia-flexible-manufacturing"

# ── Patches ───────────────────────────────────────────────────────
# Detects the installed SMIA package path at build time — version-independent.
COPY patches/smia_agent.py /tmp/smia_agent_patch.py
COPY patches/negotiating_behaviour.py /tmp/negotiating_patch.py
COPY patches/handle_negotiation_behaviour.py /tmp/handle_neg_patch.py

RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    echo "[smia-machine] Applying patches at: $SMIA_PKG" && \
    cp /tmp/smia_agent_patch.py    "$SMIA_PKG/agents/smia_agent.py" && \
    cp /tmp/negotiating_patch.py   "$SMIA_PKG/behaviours/negotiating_behaviour.py" && \
    cp /tmp/handle_neg_patch.py    "$SMIA_PKG/behaviours/specific_handle_behaviours/handle_negotiation_behaviour.py" && \
    rm /tmp/smia_agent_patch.py /tmp/negotiating_patch.py /tmp/handle_neg_patch.py

# ── Custom launcher and availability service ──────────────────────
# Placed at WORKDIR / so that `import smia_machine_agent_services`
# resolves correctly — Python includes the working directory in sys.path.
COPY agents/machine/smia_machine_starter.py /smia_machine_starter.py
COPY agents/machine/smia_machine_agent_services.py /smia_machine_agent_services.py

WORKDIR /

# Replaces the default SMIA launcher with our ExtensibleSMIAAgent starter,
# which registers the machineAvailValue agent service for FIPA-CNP negotiation.
# Default image CMD: ["python3", "-m", "smia.launchers.smia_docker_starter"]
CMD ["python3", "-u", "smia_machine_starter.py"]
