FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    gnupg \
    && wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - \
    && echo "deb http://repo.mongodb.org/apt/debian bullseye/mongodb-org/7.0 main" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list \
    && apt-get update \
    && apt-get install -y mongodb-mongosh \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary files
COPY mcp_interface.py .
COPY db.py .
COPY ticktick_api.py .
COPY start.sh .
COPY prompts/ prompts/

# Create necessary directories
RUN mkdir -p /app/logs /app/prompts

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Make start.sh executable
RUN chmod +x start.sh

# Use a shell as the entrypoint to keep the container running
CMD ["/bin/bash"]
