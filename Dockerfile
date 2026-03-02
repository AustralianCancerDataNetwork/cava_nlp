# 1. Use the pre-built image from your base project
FROM python-omop:latest

# Create non-root user variables
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Check if user already exists (which it likely does from python-omop), if not create it
RUN if ! getent group $USERNAME > /dev/null 2>&1; then \
        groupadd --gid $USER_GID $USERNAME; \
    fi \
    && if ! id -u $USERNAME > /dev/null 2>&1; then \
        useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash; \
    fi

# Pre-create the workspace and .venv directory so the volume mount inherits vscode ownership
RUN mkdir -p /workspace/cava-nlp/.venv \
    && chown -R $USERNAME:$USERNAME /workspace

# Set the working directory BEFORE switching users
WORKDIR /workspace/cava-nlp

# (Optional) If you actually needed to install mkdocs here, uncomment the next two lines:
# USER root
# RUN pip install mkdocs 

# 2. Switch to the non-root user for runtime
USER $USERNAME

# 3. Update PATH to prioritize the virtual environment
ENV PATH="/workspace/cava-nlp/.venv/bin:$PATH"