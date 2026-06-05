FROM python:3.11-slim

# Install system dependencies for scapy and network operations
RUN apt-get update && apt-get install -y \
    tcpdump \
    libpcap-dev \
    nmap \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run the agent
CMD ["python", "agent.py"]