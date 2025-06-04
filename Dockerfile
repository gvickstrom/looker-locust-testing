FROM python:3.13-slim

# Install system dependencies including Chrome driver and Google Cloud SDK
RUN apt-get update && apt-get install -y \
    chromium-driver \
    curl \
    gnupg \
    lsb-release \
    ca-certificates \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy your application code
COPY lkr ./lkr

# Set environment for uv
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"

# Install dependencies using uv (keep original locked versions)
RUN uv sync --frozen --no-dev


# Command to run when container starts
ENTRYPOINT ["lkr"]