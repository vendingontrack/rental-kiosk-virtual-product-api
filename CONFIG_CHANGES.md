# Virtual Product Mock Server - Configuration Changes

## Summary of Changes

### Files Created

1. **examples/golf.json** - Golf preset data
2. **examples/tennis.json** - Tennis preset data
3. **pyproject.toml** - Python project configuration with uv settings

### Files Modified

1. **main.py** - Updated to load data from JSON files

## New Usage

### Via Command-Line Argument
```bash
python main.py examples/golf.json
python main.py examples/tennis.json
uv run main.py examples/tennis.json
```

### Via Environment Variable
```bash
DATA_FILE=examples/tennis.json python main.py
DATA_FILE=examples/golf.json python main.py
```

### Default Behavior
If no data file is specified, defaults to `examples/golf.json`
```bash
python main.py
```

## Configuration

All environment variables work as before:
- `API_KEY` - Expected X-API-Key value (default: "test-api-key")
- `DATA_FILE` - Path to JSON file with product data (default: examples/golf.json)
- `PORT` - Server port (default: 8099)
- `RESPONSE_DELAY_MS` - Artificial delay in ms (default: 0)
- `FAIL_PURCHASE` - When "true", POST /purchase always fails (default: false)

## Benefits

- **Easy to extend**: Add new product presets by creating new JSON files in the `examples/` directory
- **Flexible configuration**: Use environment variables or command-line arguments
- **Better separation of concerns**: Product data is decoupled from code logic
- **uv support**: Simplified Python environment management with uv
