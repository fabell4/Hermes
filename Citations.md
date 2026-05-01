# Code Citations

## Source Reference

**License:** unknown

**Source:** <https://github.com/jdharmon/speedtest/blob/d1b344bc5099f842e091cfe7e73fb5dc969472e3/Dockerfile>

## Overview

Here's what the refactor would look like to switch from the Python `speedtest-cli` library to the official Ookla CLI:

## Implementation Changes

### 1. Dockerfile - Install Ookla CLI Binary

After the apt-get install line (around line 27):

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 curl ca-certificates gnupg \
    && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash \
    && apt-get install -y speedtest \
    && rm -rf /var/lib/apt/lists/*
```

### 2. Requirements

Update the requirements.txt file to remove the Python speedtest-cli library if present,
as we're now using the official Ookla CLI binary instead.
