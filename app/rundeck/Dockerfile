FROM rundeck/rundeck:5.8.0

USER root

# Install curl and gnupg if not present, then install rundeck-cli
RUN apt-get update \
    && apt-get install -y curl gnupg \
    && curl -s https://packagecloud.io/install/repositories/pagerduty/rundeck/script.deb.sh | os=any dist=any bash \
    && apt-get install -y rundeck-cli \
    && rm -rf /var/lib/apt/lists/*

USER rundeck
