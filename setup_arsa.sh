#!/bin/bash

# ARSA Setup Script - Phase 2
# System Admin & DevOps Expert Mode

echo "--- Starting ARSA Environment Setup ---"

# 1. System Dependencies for Crawling (Playwright/Chromium)
echo "Installing system dependencies..."
sudo apt-get update && sudo apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libmagic1 \
    python3-venv \
    python3-pip \
    curl \
    git \
    sqlite3

# 2. Python Virtual Environment Setup
echo "Setting up Python virtual environment 'arsa-env'..."
python3 -m venv arsa-env
source arsa-env/bin/activate

echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# 3. Core AI & Scraping Installation
echo "Installing Python requirements..."
pip install -r requirements.txt

echo "Initializing Crawl4AI and Playwright..."
crawl4ai-setup
playwright install --with-deps chromium

# 4. GPU Validation
echo "Verifying GPU accessibility (NVIDIA 1650)..."
if command -v nvidia-smi &> /dev/null
then
    nvidia-smi
    echo "SUCCESS: GPU is accessible in WSL2."
else
    echo "WARNING: nvidia-smi not found. Ensure NVIDIA Container Toolkit is installed on the host and WSL2 is updated."
fi

# 5. Database Initialization (Using Phase 1 Schema)
echo "Initializing research.db..."
if [ -f "schema.sql" ]; then
    sqlite3 research.db < schema.sql
    echo "SUCCESS: research.db initialized."
else
    echo "ERROR: schema.sql not found. Skipping DB initialization."
fi

echo "--- Setup Complete! ---"
echo "To activate the environment: source arsa-env/bin/activate"
echo "Note: If running Ollama on Windows Host, ensure OLLAMA_ORIGINS='*' is set."
