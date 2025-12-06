# JMA Data MCP

Japan Meteorological Agency (JMA) data MCP server.

## Features

- AMeDAS (Automated Meteorological Data Acquisition System) station data
- 1286 observation stations across Japan
- Search by station code, name, or location

## Data Source

- AMeDAS station data: https://www.jma.go.jp/bosai/amedas/
- CSV data: https://www.data.jma.go.jp/stats/data/mdrr/docs/csv_dl_readme.html

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

- `get_station` - Get station by code
- `search_stations_by_name` - Search stations by name
- `search_stations_by_location` - Search stations within radius
- `get_stations_by_type` - Get stations by type (A-F)
- `list_all_stations` - List all stations with pagination

## Station Types

| Type | Description |
|------|-------------|
| A | Staffed observatory (官署) |
| B | Special regional weather station (特別地域気象観測所) |
| C | AMeDAS station (アメダス) |
| D | Rain gauge station (雨量観測所) |
| E | Snow depth station (積雪観測所) |
| F | Regional rain station (地域雨量観測所) |

## License

MIT
