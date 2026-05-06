# ================================================================
# SMIA Operator Agent — Vicomtech DII
# ================================================================
# Extends the official SMIA base image with:
#   1. operator_gui_logic.py patch — three latent bugs in hasParameter processing
#      (Patch 3, see patches/PATCHES.md §3).
#      Unlike Patches 1 and 2, this patch does NOT require a RUN step:
#      operator_gui_logic.py is NOT part of the installed SMIA Python package —
#      it is a standalone module expected at the working directory. Copying our
#      patched version to WORKDIR / is sufficient — Python finds it first on
#      sys.path and the installed copy (if any) is never loaded.
#      TODO: remove patch note once upstream PR is merged into ekhurtado/smia
#
#   2. Operator GUI behaviours and HTML templates registered as the
#      SMIA operator agent
#
# Base image: ekhurtado/smia:latest-alpine-base
#   This is a lighter variant that includes the SMIA Python package but does NOT
#   include the default machine agent launcher — appropriate for the operator,
#   which runs a different entrypoint and serves an HTTP GUI instead.
#
# Build context: NEW REPO ROOT (the directory containing docker-compose.yml)
#
# docker-compose calls this as:
#   build:
#     context: .
#     dockerfile: agents/operator/Dockerfile
# ================================================================

FROM ekhurtado/smia:latest-alpine-base

LABEL maintainer="afierro@vicomtech.org"
LABEL org="Vicomtech — Data Intelligence for Industry (DII)"
LABEL description="SMIA Operator Agent — web GUI for capability request dispatch"
LABEL project="smia-flexible-manufacturing"

# ── Patch 3 (implicit): patched operator_gui_logic.py ────────────
# The file copied below is the patched version (three bugs fixed).
# Placing it at / (WORKDIR) makes Python import it before any installed
# copy — no RUN step needed. See patches/PATCHES.md §3 for details.
#
# ── Operator GUI modules and HTML templates ───────────────────────
COPY agents/operator/smia_operator_starter.py    /smia_operator_starter.py
COPY agents/operator/operator_gui_behaviours.py  /operator_gui_behaviours.py
COPY agents/operator/operator_gui_logic.py       /operator_gui_logic.py
COPY agents/operator/htmls                       /htmls

WORKDIR /

# Runs the operator GUI launcher (aiohttp-based web server on port 10000).
# The GUI scans all .aasx files in the mounted aas/ volume and presents
# discovered SMIA agents for capability request dispatch.
# Default image CMD: ["python3", "-m", "smia.launchers.smia_docker_starter"]
CMD ["python3", "-u", "smia_operator_starter.py"]
