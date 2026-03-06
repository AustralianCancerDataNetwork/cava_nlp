# CAVA-NLP

This project provides advanced NLP extraction for pathology reports, built as a 
layer on top of the **omop-spires** engine.

## Prerequisites

- Docker and Docker Compose (v2.20+)
- NVIDIA Container Toolkit (for GPU-accelerated Ollama)
- `omop-spires` must be cloned in the same parent directory as this project.

## Installation & Setup

NOTE: This package relies currently on `omop-spires` and its docker setup. Therefore, both need to be cloned and installed.

1. **Clone the repositories side-by-side:**
   ```bash
   git clone https://github.com/AustralianCancerDataNetwork/omop-spires.git -b spires
   git clone https://github.com/AustralianCancerDataNetwork/cava_nlp.git cava-nlp -b medtagger
2. **Install `omop-spires`**
   Follow the installation instructions at the [official documentation of `omop-spires`](https://github.com/AustralianCancerDataNetwork/omop-spires/blob/spires/docs/installation.md) including Steps:
   - *1. Configuration (.env)*
   - *2. Obtain the required Ollama models*
3. **Verify the setup**

   The folder structure needs to be this:
   ```
   parent-folder/
   │
   ├── omop-spires/
   │   ├── docker/                 # Shared infrastructure (DB, Ollama)
   │   │   └── docker-compose.yaml
   │   ├── scripts/
   │   │   └── bootstrap.py
   │   ├── Dockerfile.python
   │   └── docker-compose.yaml
   │
   ├── cava-nlp/                   # This project
   │   ├── Dockerfile              
   │   └── docker-compose.yaml     # Includes ../omop-spires/docker/docker-compose.yaml
   │   └── .env                    # Credentials for DB (see Step 1 of omop-spires setup)
   │
   ├── omop-graph/                 # Sibling dependency: Will be a PyPI package after development
   ├── OMOP_Alchemy/               # Sibling dependency: Will be a PyPI package after development
   └── spaczz/                     # Sibling dependency: Will be a PyPI package after development
   ```
4. **Spin up the container**
   ```bash
   docker compose up -d --build
   ```

Further information about how to setup docker and the VSCode development environment can be found in the [official documentation of `omop-spires`](https://github.com/AustralianCancerDataNetwork/omop-spires/blob/spires/docs/installation.md)