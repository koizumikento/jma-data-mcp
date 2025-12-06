# JMA Data MCP

Japan Meteorological Agency (JMA) data MCP server.

## Features

- AMeDAS (Automated Meteorological Data Acquisition System) station data
- 1286 observation stations across Japan
- Search by station code, name, or location
- Real-time weather observation data (temperature, humidity, wind, precipitation, etc.)
- Weather forecast by prefecture

## Data Source

- AMeDAS station data: https://www.jma.go.jp/bosai/amedas/
- Real-time observation: https://www.jma.go.jp/bosai/amedas/
- Weather forecast: https://www.jma.go.jp/bosai/forecast/

## Installation

```bash
uv pip install -e .
```

## Usage

### As MCP Server

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "jma-data": {
      "command": "uv",
      "args": ["run", "jma-data-mcp"]
    }
  }
}
```

### Available Tools

#### Station Tools
- `get_station` - Get station by code
- `search_stations_by_name` - Search stations by name
- `search_stations_by_location` - Search stations within radius
- `get_stations_by_type` - Get stations by type (A-F)
- `list_all_stations` - List all stations with pagination

#### Weather Tools
- `get_current_weather` - Get current weather observation from AMeDAS
- `get_weather_by_location` - Get weather from nearest station to coordinates
- `get_forecast` - Get weather forecast for a prefecture
- `list_prefectures` - List available prefecture codes

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

## License

MIT
