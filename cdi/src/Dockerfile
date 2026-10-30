FROM python:3.10-slim

# System tools the ported background-jobs need at runtime:
#   curl/wget  - download NDMC percentiles
#   jq         - rewrite cdi_project_settings.conf (change-cdi-*.sh)
#   pup        - parse the NDMC HTML directory listings (utils.sh)
#   unzip/ca-certificates - fetch the pup release below
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl wget jq unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# pup has no apt package; install the pinned GitHub release binary.
RUN wget -q https://github.com/ericchiang/pup/releases/download/v0.4.0/pup_v0.4.0_linux_amd64.zip -O /tmp/pup.zip \
    && unzip -o /tmp/pup.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/pup \
    && rm /tmp/pup.zip

WORKDIR /app/src

# Python deps for both layers (science scripts + orchestration jobs)
COPY cdi-scripts/requirements.txt cdi-scripts/requirements.txt
COPY background-jobs/requirements.txt background-jobs/requirements.txt
RUN pip install --no-cache-dir -r cdi-scripts/requirements.txt \
    && pip install --no-cache-dir -r background-jobs/requirements.txt

# Code: the science scripts and the orchestration jobs as siblings under /app/src.
# The scripts resolve input_data/output_data two levels up (/app/input_data,
# /app/output_data) and the config at /app/src/cdi-scripts/ — both provided by
# compose volume mounts.
COPY cdi-scripts/ cdi-scripts/
COPY background-jobs/ background-jobs/

WORKDIR /app
# job.sh is driven via `docker compose exec` and self-locates (cd $(dirname $0));
# keep the container alive for Rundeck/manual exec.
CMD ["sleep", "infinity"]
