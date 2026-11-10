# 台風位置表とベストトラック

## MCPツール

| ツール | 用途 |
| --- | --- |
| `list_typhoons` | 台風位置表にある確定済みの台風を年ごとに一覧（2001年以降） |
| `get_typhoon_track` | 台風位置表の経路を年と台風番号で取得（2001年以降） |
| `list_best_track_typhoons` | RSMC東京台風センターのベストトラックにある台風を年ごとに一覧（1951年以降） |
| `get_best_track` | ベストトラックの経路を年と台風番号で取得（1951年以降） |

結果の `analysis` は台風位置表で `final`、ベストトラックで `best_track` です。ベストトラックの `revision_date` は台風ごとのデータ改訂日です。


## データの更新

MCP・CLI・Pythonは同じローカルキャッシュを使います。台風位置表は年別CSVを取得し、今年分は24時間、過去年は30日ごとに確認します。ベストトラックは全年分のZIPを取得し、24時間ごとに確認します。どちらも期限を過ぎた最初の照会時に更新を確認します。更新に失敗した場合は直前の正常な版を返し、`cache.refresh_failed` と `cache.checked_at` で失敗の有無と最後に確認できた日時を判別できます。初回取得に失敗した場合はエラーになります。

台風位置表の更新をすぐに確認するには、次を実行します。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/jma-data-mcp.git@master jma-data-mcp typhoon refresh --year 2025
```

キャッシュの保存先は次のとおりです。

- Windows: `%LOCALAPPDATA%/jma-typhoon-mcp`
- その他: `$XDG_CACHE_HOME/jma-typhoon-mcp` または `~/.cache/jma-typhoon-mcp`

`JMA_TYPHOON_CACHE_DIR` で保存先を指定できます。


## データの出典と利用条件

台風位置表には事後解析済みの確定値を使います。速報値は気象庁の年別ページにあるPDFで確認できます。ベストトラックはRSMC東京台風センターの公開アーカイブです。日時はUTC、風速はノットです。東経180度を超える値は西経の負値に変換します。風速や中心気圧が記録されていないときは `null` になります。利用する際は気象庁の出典を示し、加工した場合はその旨を明記してください。[台風位置表](https://www.data.jma.go.jp/typhoon/position_table/index.html)・[ベストトラックの配布ページ](https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/besttrack.html)・[気象庁ホームページ利用規約](https://www.jma.go.jp/jma/kishou/info/coment.html)

MIT Licenseはこのリポジトリのコードに適用します。
