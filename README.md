# Hermes

A Python application that periodically runs internet speed tests and exports results to multiple destinations (CSV, Prometheus, Loki/OTel), with a browser-based UI to trigger runs and view results.

## Architecture

### Data Flow

> Solid lines = implemented. Dashed lines = planned.

```mermaid
flowchart TD
    subgraph current["Current Implementation"]
        MAIN["**main.py**\nEntry point"]
        RUNNER["**SpeedtestRunner**\nsrc/services/speedtest_runner.py"]
        MODEL["**SpeedResult**\nsrc/models/speed_results.py"]
        STDOUT["Console output\nstdout"]
    end

    subgraph planned["Planned"]
        UI["Frontend\nWeb UI"]
        WEB["Web Layer\nsrc/web/app.py"]
        DISP["ResultDispatcher\nsrc/dispatcher.py"]
        CSV["CSVExporter"]
        PROM["PrometheusExporter"]
        LOKI["LokiExporter"]
    end

    MAIN --> RUNNER
    RUNNER --> MODEL
    MODEL --> STDOUT

    UI -. "HTTP" .-> WEB
    WEB -. " " .-> RUNNER
    MODEL -. " " .-> DISP
    DISP -. " " .-> CSV
    DISP -. " " .-> PROM
    DISP -. " " .-> LOKI

    style current fill:#1b5e20,stroke:#66bb6a,color:#ffffff
    style planned fill:#1a237e,stroke:#5c6bc0,color:#ffffff,stroke-dasharray: 4 4
    style MAIN fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style RUNNER fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style MODEL fill:#2e7d32,stroke:#a5d6a7,color:#ffffff
    style STDOUT fill:#f57f17,stroke:#ffca28,color:#000000
    style UI fill:#283593,stroke:#7986cb,color:#ffffff
    style WEB fill:#283593,stroke:#7986cb,color:#ffffff
    style DISP fill:#283593,stroke:#7986cb,color:#ffffff
    style CSV fill:#283593,stroke:#7986cb,color:#ffffff
    style PROM fill:#283593,stroke:#7986cb,color:#ffffff
    style LOKI fill:#283593,stroke:#7986cb,color:#ffffff
```

## Project Structure

```
Hermes/
├── src/
│   ├── main.py                        # Entry point — wires everything together,
│   │                                  #   starts scheduler + web server
│   ├── dispatcher.py                  # ResultDispatcher — fans out SpeedResult to exporters
│   ├── models/
│   │   └── speed_results.py           # SpeedResult dataclass — shared data contract
│   ├── services/
│   │   ├── speedtest_runner.py        # SpeedtestRunner — runs test, returns SpeedResult
│   │   └── logging.py                 # Logging configuration
│   ├── exporters/
│   │   ├── base_export.py             # Abstract BaseExporter interface
│   │   ├── csv_export.py              # CSVExporter — appends rows, serves file for download
│   │   ├── prometheus_exporter.py     # PrometheusExporter — updates Gauges, /metrics endpoint
│   │   └── loki_exporter.py           # LokiExporter — ships JSON log events via HTTP push
│   └── web/
│       ├── app.py                     # Flask app — routes only, no business logic
│       └── templates/
│           └── index.html             # Frontend UI
├── tests/
│   ├── __init__.py
│   └── test_main.py
├── .env.example                       # Example environment variables
├── requirements.txt                   # Project dependencies
├── pytest.ini                         # pytest configuration
└── README.md
```

## Setup

1. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   ```bash
   copy .env.example .env
   ```

## Running the App

```bash
python -m src.main
```

Or use the **Run Hermes** task in VS Code (Terminal → Run Task).

## Running Tests

```bash
pytest
```

Test
