# Development Dockerfile for CXM
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install git and system dependencies required for context gathering
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (for caching)
COPY meta-orchestrator/requirements.txt meta-orchestrator/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy the source code
COPY meta-orchestrator/ ./meta-orchestrator/

# Install CXM in editable mode
RUN pip install -e ./meta-orchestrator

# Set entrypoint to bash for interactive dev
CMD ["/bin/bash"]
