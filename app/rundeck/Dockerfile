FROM rundeck/rundeck:5.8.0

USER root

# Install curl and gnupg if not present, then install rundeck-cli
RUN apt-get update \
    && apt-get install -y curl gnupg \
    && curl -s https://packagecloud.io/install/repositories/pagerduty/rundeck/script.deb.sh | os=any dist=any bash \
    && apt-get install -y rundeck-cli \
    && rm -rf /var/lib/apt/lists/*

USER rundeck

# Create directory to place project and job templates config files
RUN mkdir -p /home/rundeck/server/config/templates

# Create writable directory for .env file and copy it there
RUN mkdir -p /home/rundeck/server/config
COPY --chown=rundeck:rundeck .env /home/rundeck/server/config/.env
RUN chmod 644 /home/rundeck/server/config/.env

# Copy entrypoint script and make it executable
COPY --chown=rundeck:rundeck rundeck/entrypoint.sh /home/rundeck/entrypoint.sh
RUN chmod +x /home/rundeck/entrypoint.sh

# Set the custom entrypoint
ENTRYPOINT ["/home/rundeck/entrypoint.sh"]