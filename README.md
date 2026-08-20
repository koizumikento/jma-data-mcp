# JMA Data MCP

気象庁のAMeDAS観測・過去データと天気予報を検索するMCPサーバーです。全国1,286観測所のスナップショットを同梱し、地点名・座標から観測所を検索できます。

## 実行

Python 3.10+ と [`uv`](https://docs.astral.sh/uv/) が必要です。

```bash
uvx --from git+https://github.com/koizumikento/jma-data-mcp.git@master jma-data-mcp
```

MCPクライアント設定例:

```json
{
  "mcpServers": {
    "jma-data": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/koizumikento/jma-data-mcp.git@master",
        "jma-data-mcp"
      ]
    }
  }
}
```

引数なし、または `serve` でMCPサーバーを起動します。`station`、`weather`、`forecast`、`history` サブコマンドからCLIとしても利用できます。

## MCP tools

- 観測所: `get_station_info`、`search_stations`、`search_nearby_stations`、`get_stations_of_type`、`list_stations`
- 観測・予報: `get_current_weather`、`get_weather_by_location`、`get_forecast`、`list_prefectures`
- 過去・時系列: `get_historical_weather`、`get_weather_time_series`

過去データは気象庁側で提供される直近約1〜2週間、時系列は最大168時間を対象とします。

## データ出典・利用条件

出典: [気象庁ホームページ](https://www.jma.go.jp/)

- [AMeDAS観測所・観測データ](https://www.jma.go.jp/bosai/amedas/)
- [天気予報](https://www.jma.go.jp/bosai/forecast/)
- [気象庁ホームページ利用規約](https://www.jma.go.jp/jma/kishou/info/coment.html)

同梱する観測所表は気象庁公開データを本ソフトウェア用に加工しています。取得データを利用・再配布する際は、気象庁の利用規約と気象業務法上の制約を確認してください。本ソフトウェアは独自の予報を生成しません。

## 開発

```bash
uv sync --frozen
uv run ruff check .
uv run mypy jma_data_mcp
uv run pytest -m "not integration"
uv run python scripts/check_amedas_snapshot.py
uv build
```

観測所スナップショットの差分チェックは週次でも実行されます。

## License

[MIT](LICENSE)
