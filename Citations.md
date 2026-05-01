# Code Citations

## Source Reference

**License:** unknown

**Source:** <https://github.com/jdharmon/speedtest/blob/d1b344bc5099f842e091cfe7e73fb5dc969472e3/Dockerfile>

## Overview

Hermes uses the official Ookla CLI binary for speed testing instead of the unofficial Python
`speedtest-cli` library. This migration provides improved reliability and official support from
Ookla.

## Implementation

### 1. Dockerfile - Ookla CLI Binary Installation

The Dockerfile installs the official Ookla speedtest CLI:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 curl ca-certificates gnupg \
    && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | bash \
    && apt-get install -y speedtest \
    && rm -rf /var/lib/apt/lists/*
```

### 2. Requirements

The Python `speedtest-cli` library has been removed from requirements.txt. Hermes now invokes the
official Ookla CLI binary directly via `subprocess`.
