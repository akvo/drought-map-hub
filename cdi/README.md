# Composite Drought Indicator

This project includes scripts for the cdi-script, which was developed by the [National Drought Mitigation Center (NDMC)](https://drought.unl.edu/). The script is intended to run periodically—ideally on a monthly basis—to ensure that the data stays current.

Now fully dockerized for easy setup and repeatable execution. This guide helps you run the scripts in a Docker container using Docker Compose, with persistent access to input, output, and configuration files from your local system.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup Guide](#setup-guide)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Prepare Data and Config Directories](#2-prepare-data-and-config-directories)
  - [3. Configuration Files](#3-configuration-files)
  - [4. Build the Docker Image](#4-build-the-docker-image)
  - [5. Start the Service (Docker Compose)](#5-start-the-service-docker-compose)
  - [6. Running the Workflow (Docker Compose)](#6-running-the-workflow-docker-compose)
  - [7. Run Without Docker Compose](#7-run-without-docker-compose)
- [Usage Tips](#usage-tips)

---

## Features

- **Run Akvo CDI scripts in Docker:** No need to install Python or dependencies.
- **Easy data exchange:** Input/output data directories are shared with your host.
- **Configurable:** All key configuration files are editable outside the container.
- **Simple command execution:** Run the full workflow or custom steps via Docker Compose or a single Docker command.

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (optional, for compose workflow)

---

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/akvo/cdi-scripts.git
cd cdi-scripts
```

---

### 2. Prepare Data and Config Directories

Create local directories for input data, output data, and configuration files:

```bash
mkdir -p source/input_data
mkdir -p source/output_data
mkdir -p config
touch config/cdi_directory_settings.json
touch config/cdi_pattern_settings.json
touch config/cdi_project_settings.json
```

You can now edit the `.json` files in the `config/` folder as needed.

---

### 3. Configuration Files

The following configuration files must exist in the `config/` directory at the project root:

- `config/cdi_directory_settings.json`
- `config/cdi_pattern_settings.json`
- `config/cdi_project_settings.json`

These files are mounted into the container at `/app/`.

---

### 4. Build the Docker Image

```bash
docker build -t cdi-scripts:latest .
```

---

### 5. Start the Service (Docker Compose)

```bash
docker compose up -d
```

This starts the container in the background, ready for you to run scripts as needed.

---

### 6. Running the Workflow (Docker Compose)

To execute the main workflow script inside the running container, use:

```bash
docker compose exec cdi python STEP_0000_execute_all_steps.py
```

You can also run other scripts or steps in a similar manner.

---

### 7. Run Without Docker Compose

You may run the container directly without Docker Compose using the following command:

```bash
docker run --rm -it \
  -v "$PWD/source/input_data:/app/source/input_data" \
  -v "$PWD/source/output_data:/app/source/output_data" \
  -v "$PWD/config/cdi_directory_settings.json:/app/config/cdi_directory_settings.json" \
  -v "$PWD/config/cdi_pattern_settings.json:/app/config/cdi_pattern_settings.json" \
  -v "$PWD/config/cdi_project_settings.json:/app/config/cdi_project_settings.json" \
  -w /app \
  cdi-scripts:latest \
  python STEP_0000_execute_all_steps.py
```

- This command mounts your local input/output data and config files into the container.
- You can substitute the last line to run a different script if needed.

**To start a shell instead (for debugging):**
```bash
docker run --rm -it \
  -v "$PWD/source/input_data:/app/source/input_data" \
  -v "$PWD/source/output_data:/app/source/output_data" \
  -v "$PWD/config/cdi_directory_settings.json:/app/config/cdi_directory_settings.json" \
  -v "$PWD/config/cdi_pattern_settings.json:/app/config/cdi_pattern_settings.json" \
  -v "$PWD/config/cdi_project_settings.json:/app/config/cdi_project_settings.json" \
  -w /app \
  cdi-scripts:latest \
  bash
```

---

## Usage Tips

- Place input files in `source/input_data/` on your host machine.  
- Output files will be generated in `source/output_data/` and will be immediately accessible on your host.
- Edit `config/*.json` files as needed before running the workflow.
- You can stop the container (if running with Compose) with `docker compose down`.

