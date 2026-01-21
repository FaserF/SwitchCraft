# Dockerfile for SwitchCraft Web App Verification
FROM python:3.14-rc-slim

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

# Install dependencies (Modern Flet only)
# Note: We omit 'gui' (Legacy Tkinter) to avoid system package requirements
RUN pip install --no-cache-dir .[modern]

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

# Command to run the application in web mode
CMD ["flet", "run", "--web", "--port", "8080", "--host", "0.0.0.0", "src/switchcraft/modern_main.py"]
