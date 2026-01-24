# Dockerfile for SwitchCraft Web App Verification
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    wine \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src ./src

# Install dependencies (Modern Flet + Web Server + Web WASM)
# Explicitly avoid 'modern' extra which includes flet-desktop (causes issues in Docker)
# PIN VERSIONS to ensure frontend (JS) matches backend (Python) capabilities (Fixes FilePicker issue)
RUN pip install --no-cache-dir .[web-server] flet==0.80.4 flet-web==0.80.4 flet-charts==0.80.4 packaging

# Generate Addons (Pre-installed)
RUN python src/generate_addons.py

# Install bundled addons to user addon directory
# The addons are generated as ZIP files; we need to extract them
RUN mkdir -p /root/.switchcraft/addons && \
    for zip in /app/src/switchcraft/assets/addons/*.zip; do \
        unzip -o "$zip" -d /root/.switchcraft/addons/$(basename "$zip" .zip); \
    done

# Expose Flet web port
EXPOSE 8080

# Environment variables
ENV FLET_SERVER_PORT=8080
# Disable Winget auto install attempts / reduce noise
ENV SC_DISABLE_WINGET_INSTALL=1

# Command to run the application in web mode
# Create symlink for assets so Flet can find them at /app/assets
RUN ln -s /app/src/switchcraft/assets /app/assets

# Command to run the application using the Auth Proxy Server
CMD ["uvicorn", "switchcraft.server.app:app", "--host", "0.0.0.0", "--port", "8080"]
