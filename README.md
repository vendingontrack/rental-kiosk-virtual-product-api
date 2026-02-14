# Virtual Product API

This repository contains two things:

1. **[PROTOCOL.md](PROTOCOL.md)** — the HTTP API contract that 3rd-party providers must implement to integrate virtual products with the Vending on Track kiosk platform (SD-3708).
2. **Mock Server** (`main.py`) — a FastAPI reference implementation of that protocol, used for development and Go integration testing.

## Mock Server

### Quick Start

```bash
pip install -r requirements.txt
python main.py                        # default: examples/golf.json on :8099
python main.py examples/tennis.json   # use tennis data
```

The server starts on port 8099 by default. The data file can be set via command-line argument or the `DATA_FILE` environment variable.

### Environment Variables

| Variable            | Default              | Description                                              |
|---------------------|----------------------|----------------------------------------------------------|
| `API_KEY`           | `test-api-key`       | Expected `X-API-Key` header value                        |
| `DATA_FILE`         | `examples/golf.json` | Path to JSON file with product data                      |
| `PORT`              | `8099`               | Server listen port                                       |
| `RESPONSE_DELAY_MS` | `0`                  | Artificial delay (ms) on responses except `/ping` (timeout testing) |
| `FAIL_PURCHASE`     | `false`              | When `true`, `POST /purchase` always returns failure     |

### Example Data Files

Two data files are included in `examples/`:

- **`golf.json`** (default) — Green Fees: 18-Hole Weekday ($45), 9-Hole Weekday ($25), 18-Hole Weekend ($55)
- **`tennis.json`** — Court Booking: Court A ($30), Court B ($30), Court C ($35); Lessons: 30-min Private ($50), 60-min Group ($25)

Custom data files follow the same JSON schema as the `GET /products` response defined in [PROTOCOL.md](PROTOCOL.md).

### Docker

```bash
docker build -t virtual-product-mock .
docker run -p 8099:8099 -e DATA_FILE=examples/tennis.json virtual-product-mock
```

### Go Integration Test Usage

The server is designed to be started as a subprocess from Go tests:

```go
cmd := exec.Command("python", "main.py")
cmd.Env = append(os.Environ(),
    "PORT=18099",
    "API_KEY=integration-test-key",
)
cmd.Stdout = os.Stdout
cmd.Stderr = os.Stderr
err := cmd.Start()
// ... run tests ...
cmd.Process.Kill()
```

Key properties for test integration:
- Starts in under 1 second
- Logs to stdout (captured by Go test runner)
- Port configurable via `PORT` env var (avoids conflicts)
- `FAIL_PURCHASE` and `RESPONSE_DELAY_MS` allow testing error and timeout paths
- Stateless between restarts (idempotency cache is in-memory only)

### Testing Scenarios

| Scenario            | Configuration                   |
|---------------------|---------------------------------|
| Happy path          | Default settings                |
| Auth failure        | Send wrong `X-API-Key`          |
| Purchase failure    | `FAIL_PURCHASE=true`            |
| Timeout testing     | `RESPONSE_DELAY_MS=600`         |
| Unknown SKU         | POST with non-existent SKU      |
| Tennis venue data   | `DATA_FILE=examples/tennis.json`|
| Idempotency check   | POST same `transaction_id` twice|
