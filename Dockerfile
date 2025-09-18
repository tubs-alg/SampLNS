FROM ubuntu:24.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    cmake \
    git \
    build-essential \
    python3 \
    python3-venv \
    libboost-all-dev \
    openjdk-11-jdk \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy source code
COPY . /app

# Create a Python virtual environment for SampLNS
RUN python3 -m venv /app/samplns
ENV PATH="/app/samplns/bin:$PATH"

# Install dependencies in the virtual environment
RUN /app/samplns/bin/pip install --upgrade pip
RUN /app/samplns/bin/pip install -v .

# Run tests (optional, can be commented out)
# RUN ./build/Release/test/sammy_test --success

# Default command: run the main program
ENTRYPOINT ["samplns"]
