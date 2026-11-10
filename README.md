# JMA Data MCP

気象庁の観測・天気予報・気候統計を調べ、直近に配信された気象警報・注意報を確認できるMCPサーバーです。全国1,286観測所のスナップショットを同梱し、地点名や座標からAMeDAS観測所を検索できます。

## 実行

Python 3.11+ と [`uv`](https://docs.astral.sh/uv/) が必要です。

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

引数なし、または `serve` でMCPサーバーを起動します。`station`、`weather`、`forecast`、`history`、`climate`、`warnings` はCLI用のサブコマンドです。

## CLIとPythonライブラリ

リポジトリのルートで、次の例を実行できます。

```bash
uv run jma-data-mcp station get --code 44132
uv run jma-data-mcp climate normals --station-code 44132 --month 8
uv run jma-data-mcp climate anomalies --metric temperature --start-year 2000
uv run jma-data-mcp warnings list --office 松山 --limit 5
```

Pythonからは `jma_data_mcp.api` の非同期関数を呼び出せます。

```python
import asyncio

from jma_data_mcp.api import get_climate_normals

print(asyncio.run(get_climate_normals("44132", month=8)))
```

## MCP tools

- 観測所: `get_station_info`、`search_stations`、`search_nearby_stations`、`get_stations_of_type`、`list_stations`
- 観測・予報: `get_current_weather`、`get_weather_by_location`、`get_forecast`、`list_prefectures`
- 過去・時系列: `get_historical_weather`、`get_weather_time_series`
- 気候統計: `get_climate_normals`、`get_japan_climate_anomalies`
- 警報・注意報の配信履歴: `list_weather_warning_reports`

| 調べたいこと | 取得できる範囲 |
| --- | --- |
| 最近の観測 | 気象庁が配信している直近の観測。時系列は最大168時間。観測所ごとの長期記録は、地点・期間・項目を選んで [気象庁の公式画面](https://www.data.jma.go.jp/risk/obsdl/) からCSVをダウンロードできます。 |
| 観測所の平年値 | 気象庁が公開している1991〜2020年平年値のうち、平均気温、日最高・最低気温の平均、風速、日照時間、降水量、積雪深、降雪量の月・年別統計。統計に用いた年数・期間と気象庁のリマーク番号を返します。欠測は `null` です。 |
| 日本の長期気候統計 | 1898年から公開済みの最新年までの年平均気温・年降水量の偏差。基準は1991〜2020年平均で、全国の観測地点から気象庁が集計した値です。 |
| 直近の警報・注意報の電文 | 数日分を掲載する気象庁の毎時更新のAtomフィードから、VPWW53〜VPWW61の電文の発表官署・配信日時・概要・原文URLを返します。解除電文も含まれます。発表中の情報は [気象庁の警報・注意報ページ](https://www.jma.go.jp/bosai/warning/) で確認できます。 |

実行中のプロセスでは、平年値のZIPを1時間、警報・注意報の配信履歴を1分キャッシュします。

## Sitesでの実行

[`sites/`](sites/README.md) に認証付き `POST /mcp` Worker ESM adapterとbuild設定があります。
全14ツールはPythonバックエンドで実行します。Sitesとは別にHTTPS接続可能なPythonホストが必要です。
stdio・CLI・Python libraryはそのまま利用できます。設定、secret名、再現手順、検証範囲は上記手順を参照してください。

## データ出典・利用条件

出典: [気象庁ホームページ](https://www.jma.go.jp/)

- [AMeDAS観測所・観測データ](https://www.jma.go.jp/bosai/amedas/)
- [天気予報](https://www.jma.go.jp/bosai/forecast/)
- [AMeDASの平年値とファイル仕様](https://www.data.jma.go.jp/stats/data/mdrr/normal/index.html)
- [日本の年平均気温偏差](https://www.data.jma.go.jp/cpdinfo/temp/list/an_jpn.html)・[年降水量偏差](https://www.data.jma.go.jp/cpdinfo/temp/list/an_jpn_r.html)
- [気象庁防災情報XMLの配信仕様](https://xml.kishou.go.jp/xmlpull.html)
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
npm --prefix sites test
npm --prefix sites run build
npm --prefix sites run validate
```

Sites契約検証にはNode 22+も必要です。テストではJMA取得をfixtureで置き換え、使用したloopbackサーバーを停止します。

観測所スナップショットの差分チェックは週次でも実行されます。

## License

Windows EXE: [release security checks and outstanding distribution work](docs/releasing.md).

[MIT](LICENSE)
