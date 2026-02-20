# JMA Data MCP

Japan Meteorological Agency (JMA) data MCP server.

## Features

- AMeDAS (Automated Meteorological Data Acquisition System) station data
- 1286 observation stations across Japan
- Search by station code, name, or location
- Real-time weather observation data (temperature, humidity, wind, precipitation, etc.)
- Historical weather data (past 1-2 weeks)
- Time series data for trend analysis
- Weather forecast by prefecture

## Data Source

- AMeDAS station data: https://www.jma.go.jp/bosai/amedas/
- Real-time observation: https://www.jma.go.jp/bosai/amedas/
- Weather forecast: https://www.jma.go.jp/bosai/forecast/

## Installation

```bash
uv tool install git+https://github.com/koizumikento/jma-data-mcp.git
```

Or install locally:

```bash
git clone https://github.com/koizumikento/jma-data-mcp.git
cd jma-data-mcp
uv sync
```

## CLI Usage

`jma-data-mcp` now supports both MCP server mode and CLI mode:

- No arguments: start MCP server (backward compatible)
- `serve`: start MCP server explicitly
- Subcommands: run CLI and print JSON output

### Examples

```bash
# Backward-compatible MCP server startup
jma-data-mcp

# Explicit MCP server startup
jma-data-mcp serve

# Station info
jma-data-mcp station get --code 44132

# Nearby stations
jma-data-mcp station nearby --lat 35.6812 --lon 139.7671 --radius-km 10

# Current weather
jma-data-mcp weather current --station-code 44132

# Forecast
jma-data-mcp forecast get --prefecture tokyo

# Historical data
jma-data-mcp history get --station-code 44132 --target-datetime "2025-12-01 12:00"
```

### CLI Command List

- `jma-data-mcp serve`
- `jma-data-mcp station get --code <code>`
- `jma-data-mcp station search --name <name>`
- `jma-data-mcp station nearby --lat <lat> --lon <lon> [--radius-km <float>]`
- `jma-data-mcp station type --station-type <A|B|C|D|E|F>`
- `jma-data-mcp station list [--limit <int>] [--offset <int>]`
- `jma-data-mcp weather current [--station-code <code>]`
- `jma-data-mcp weather by-location --lat <lat> --lon <lon>`
- `jma-data-mcp forecast get --prefecture <name>`
- `jma-data-mcp forecast list-prefectures`
- `jma-data-mcp history get --station-code <code> --target-datetime "<datetime>"`
- `jma-data-mcp history series --station-code <code> [--hours <int>] [--interval-minutes <10|30|60>]`

## Windows Executable

Windows standalone executable is published in GitHub Releases:

- Asset: `jma-data-mcp.exe`
- Checksum file: `SHA256SUMS.txt`

## MCP Server Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

**Installed version:**

```json
{
  "mcpServers": {
    "jma-data-mcp": {
      "command": "jma-data-mcp"
    }
  }
}
```

**Direct from GitHub:**

```json
{
  "mcpServers": {
    "jma-data-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/koizumikento/jma-data-mcp.git",
        "jma-data-mcp"
      ]
    }
  }
}
```

**Local development:**

```json
{
  "mcpServers": {
    "jma-data-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/jma-data-mcp",
        "jma-data-mcp"
      ]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "jma-data-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/koizumikento/jma-data-mcp.git",
        "jma-data-mcp"
      ]
    }
  }
}
```

### Cline

Add to Cline MCP settings:

```json
{
  "mcpServers": {
    "jma-data-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/koizumikento/jma-data-mcp.git",
        "jma-data-mcp"
      ]
    }
  }
}
```

## Available Tools

#### Station Tools
- `get_station_info` - Get station by code
- `search_stations` - Search stations by name
- `search_nearby_stations` - Search stations within radius
- `get_stations_of_type` - Get stations by type (A-F)
- `list_stations` - List all stations with pagination

#### Weather Tools
- `get_current_weather` - Get current weather observation from AMeDAS
- `get_weather_by_location` - Get weather from nearest station to coordinates
- `get_forecast` - Get weather forecast for a prefecture
- `list_prefectures` - List available prefecture codes

#### Historical Data Tools
- `get_historical_weather` - Get weather data for a specific past date/time (available for ~1-2 weeks)
- `get_weather_time_series` - Get time series data for trend analysis (hourly data up to 1 week)

## Weather Data

The `get_current_weather` tool returns:

| Field | Description | Unit |
|-------|-------------|------|
| temperature | Air temperature | ℃ |
| humidity | Relative humidity | % |
| pressure | Station pressure | hPa |
| sea_level_pressure | Sea level pressure | hPa |
| wind.speed | Wind speed | m/s |
| wind.direction | Wind direction | 16 directions |
| precipitation.10min | 10-min precipitation | mm |
| precipitation.1h | 1-hour precipitation | mm |
| precipitation.3h | 3-hour precipitation | mm |
| precipitation.24h | 24-hour precipitation | mm |
| sunshine.1h | 1-hour sunshine | hours |
| snow.depth | Snow depth | cm |
| snow.1h/6h/12h/24h | Snowfall | cm |

## Station Types

| Type | Description |
|------|-------------|
| A | Staffed observatory (官署) |
| B | Special regional weather station (特別地域気象観測所) |
| C | AMeDAS station (アメダス) |
| D | Rain gauge station (雨量観測所) |
| E | Snow depth station (積雪観測所) |
| F | Regional rain station (地域雨量観測所) |

## Examples

### Get current weather in Tokyo

```
Tool: get_current_weather
Arguments: {"station_code": "44132"}
```

### Get weather by coordinates

```
Tool: get_weather_by_location
Arguments: {"lat": 35.6812, "lon": 139.7671}
```

### Get forecast for Tokyo

```
Tool: get_forecast
Arguments: {"prefecture": "tokyo"}
```

### Get historical weather data

```
Tool: get_historical_weather
Arguments: {"station_code": "44132", "datetime": "2025-12-01 12:00"}
```

### Get time series data (last 24 hours)

```
Tool: get_weather_time_series
Arguments: {"station_code": "44132", "hours": 24, "interval_minutes": 60}
```

## Data Availability

| Data Type | Availability |
|-----------|--------------|
| Real-time observation | ~30 min delay |
| Historical data | Past 1-2 weeks |
| Time series | Up to 168 hours (1 week) |
| Forecast | 7 days ahead |

## Release

Push a version tag to trigger automated Windows build and GitHub Release upload:

```bash
git tag v0.2.0
git push origin v0.2.0
```

Release workflow publishes:

- `jma-data-mcp.exe`
- `SHA256SUMS.txt`

## License

MIT
