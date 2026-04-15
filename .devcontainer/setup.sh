#!/bin/bash
# .devcontainer/setup.sh
# Codespaces startup script to ensure Docker Compose plugin is available

set -e

echo "=== Docker Compose Plugin Setup ==="

# Check if docker compose works (v2 syntax)
if docker compose version >/dev/null 2>&1; then
    echo "✓ Docker Compose plugin is already available:"
    docker compose version
else
    echo "⚠ Docker Compose plugin not found. Installing..."
    
    # Install Docker Compose plugin
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    mkdir -p "$DOCKER_CONFIG/cli-plugins"
    
    # Download the latest stable version
    COMPOSE_VERSION="v2.29.2"
    curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
        -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
    
    chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
    
    # Verify installation
    if docker compose version >/dev/null 2>&1; then
        echo "✓ Docker Compose plugin installed successfully:"
        docker compose version
    else
        echo "✗ ERROR: Failed to install Docker Compose plugin"
        exit 1
    fi
fi

echo "=== Setup Complete ==="
