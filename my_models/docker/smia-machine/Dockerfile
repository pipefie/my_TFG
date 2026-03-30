# ================================================================
# SMIA Machine Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA image with:
#   1. smia_agent.py bug fix (asset connection object-identity comparison)
#      TODO: remove once upstream PR is merged into ekhurtado/smia
#   2. ExtensibleSMIAAgent launcher that registers the
#      get_machine_availability() FIPA-CNP negotiation service
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

# ── Patch: fix asset connection object-identity bug ──────────────
# Detects the SMIA package path at build time — version-independent.
COPY src/smia/agents/smia_agent.py /tmp/smia_agent_patch.py
RUN set -e && \
    SMIA_PKG=$(python3 -c "import smia, os; print(os.path.dirname(smia.__file__))") && \
    echo "[smia-machine] Applying smia_agent.py patch at: $SMIA_PKG" && \
    cp /tmp/smia_agent_patch.py "$SMIA_PKG/agents/smia_agent.py" && \
    rm /tmp/smia_agent_patch.py

# ── Custom launcher and service module ───────────────────────────
# Placed at WORKDIR / so that `import smia_machine_agent_services`
# resolves correctly (Python includes the working directory in sys.path).
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_starter.py /smia_machine_starter.py
COPY additional_tools/extended_agents/smia_machine_agent/smia_machine_agent_services.py /smia_machine_agent_services.py

WORKDIR /

# Replace the default SMIA launcher with our ExtensibleSMIAAgent starter.
# Default image CMD: ["python3", "-m", "smia.launchers.smia_docker_starter"]
CMD ["python3", "-u", "smia_machine_starter.py"]
