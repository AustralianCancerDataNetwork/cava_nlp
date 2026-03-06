# 1. Inherit everything (including the vscode user and installed tools)
FROM python-omop:latest

# 2. Switch back to root temporarily to set up new workspace directories
USER root

# Pre-create the workspace and .venv directory for cava-nlp, assign ownership
RUN mkdir -p /workspace/cava-nlp/.venv \
    && chown -R vscode:vscode /workspace/cava-nlp

# 3. Switch back to the non-root user for runtime
USER vscode

WORKDIR /workspace/cava-nlp

# 4. Update PATH to prioritize the cava-nlp virtual environment
# Note: This simply prepends to the existing PATH inherited from the parent
ENV PATH="/workspace/cava-nlp/.venv/bin:$PATH"