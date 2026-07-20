# Shortest-Path Percolation 二次元正方格子シミュレーション設計

## 1. 目的とモデル

本プロジェクトは、開放境界を持つ `L × L` の二次元正方格子上で Shortest-Path Percolation（SPP）をシミュレーションし、要求単位および辺単位の解析を行う。格子は無向・無重みであり、頂点数と初期辺数は次である。

```text
N  = L^2
M0 = 2L(L - 1)
```

頂点IDは0始まりの座標 `(row, column)` に対して `row * L + column` とする。境界条件は現在 `OPEN` のみを実装している。

各要求では、異なる2頂点 `source` と `target` を全頂点から一様ランダムに選ぶ。現在有効な辺だけを使った最短距離を `Q` とし、`Q <= C` なら選択した最短経路上の全辺を同一要求で削除する。距離 `C` 以内に到達できなければ要求を棄却し、辺状態を変えない。削除はrun内で累積し、runごとに完全格子から開始する。

`N` 頂点の単純路長は最大 `N - 1` なので、`C >= N - 1` は同一連結成分内の要求を常に受理する無限予算相当である。パラメータ走査では、この範囲の指定を重複排除し、代表値 `C = N` の `UNBOUNDED` 条件として1回だけ実行する。

## 2. 最短経路の厳密な一様選択

`SPPSimulator` は有効辺上で深さ `C` までBFSを行う。到達可能なら、BFS距離が1ずつ増える辺から最短経路DAGを定義し、`source` から各頂点までの最短経路数を `BigInteger` で数える。

`target` から逆向きに経路を復元するとき、各前駆頂点をそこまでの最短経路数に比例して選ぶ。重み付き乱数は剰余を使わず、上限のビット長に合わせた候補を生成して範囲外を捨てる棄却法を使う。このため、隣接配列順や頂点IDによらず、全最短経路から1本を厳密に一様選択できる。

選択された経路は `source` から `target` の順で保持し、経路上の全辺を要求処理の一部として削除する。モデル上は同時削除であり、経路内の逐次的な辺順は要求単位の状態を変えない。

## 3. 格子と状態

各無向辺には `0` から `M0 - 1` の連続した `edgeId` を割り当て、両端の隣接情報から同じIDを参照する。辺状態は `boolean[] activeEdge` で管理する。削除時に隣接配列を組み替えず、探索時に状態を確認する。

主な責務は次のとおりである。

- `SquareLattice`: 格子、隣接情報、辺ID、辺状態
- `SPPSimulator`: 要求抽選、最短経路選択、辺削除、累積カウンタ
- `ClusterAnalyzer`: 有効辺上の連結成分と統計量
- `SPPExperimentRunner`: 1条件の複数run、測定、CSV出力
- `SPPParameterSweepRunner`: 複数の `L` と `C` の逐次実行
- `SPPScalingV1`: scaling-v1条件の構築と実行

## 4. 乱数と再現性

run番号は0始まりであり、`SeedUtils` がSplitMix64 finalizerを使って用途別seedを決定的に生成する。

```text
runSeed  = mix64(baseSeed + run)
pairSeed = mix64(runSeed XOR PAIR_STREAM_CONSTANT)
pathSeed = mix64(runSeed XOR PATH_STREAM_CONSTANT)
```

加算とmixはJavaの符号付き64ビットのラップアラウンドを意図した演算である。`pairRandom` は頂点対だけ、`pathRandom` は最短経路だけに使い、run途中で作り直さない。したがって経路選択が消費する乱数個数を変えても頂点対系列は変わらない。同一 `L`・同一runで `C` を比較するときも条件番号をseedへ加えず、同じ `baseSeed` を使う。

## 5. 測定方式と観測量

`MeasurementMode` は次の2方式を持つ。

- `STEP_INTERVAL`: step 0、`measurementInterval` の倍数、未測定の終了stepで測定する。
- `ACCEPTED_REQUEST`: step 0、最短経路全体を削除した各accepted要求の直後、未測定の終了stepで測定する。rejected要求だけでは通常の途中測定を行わない。

研究解析では `ACCEPTED_REQUEST` を主に使う。この名称は、論文のsingle-edge event-based ensembleと区別するためのものである。

基本量は次である。

```text
t = step = accepted_requests + rejected_requests
p = removed_edges / M0
P = largest_cluster_size / N
S = sum(s^2 n_s) / sum(s n_s)
```

`S` は最大連結成分を1個だけ除いた有限クラスターの重み付き平均サイズである。最大サイズが同率でも1成分だけを除外し、分母が0なら `0.0` とする。詳しい解析上の定義は [ANALYSIS_DEFINITIONS.md](ANALYSIS_DEFINITIONS.md) にまとめる。

## 6. 停止条件

`RunStopMode` は次の2方式を持つ。

- `MAX_STEPS_OR_ALL_EDGES`: `maxSteps` 到達または全辺削除で停止する。
- `TRANSITION_WINDOW_COMPLETE`: 上記に加え、accepted要求後の測定で `P <= transitionThresholdMultiplier/L` になった時点で停止する。倍率は有限かつ正でなければならず、既定値は `1.0` である。

既定値では転移幅の下側閾値 `P <= 1/L` まで観測してrunを終了し、大規模計算で転移後の長いrejected系列を省く。停止位置の延長診断では、同じ乱数系列のまま倍率を `0.5` として `P <= 1/(2L)` まで記録できる。終了理由は `MAX_STEPS`、`ALL_EDGES_REMOVED`、`TRANSITION_WINDOW_COMPLETE` を区別し、`run_summary.csv` に最終step、最終 `p`、最終 `P`、run seed、実行時間とともに記録する。実際の倍率は `manifest.csv` の `transition_threshold_multiplier` に記録する。

## 7. CSV出力

### results.csv

1行は1 run の1測定時点であり、既存14列を固定する。

```text
run,L,C,step,removed_edges,remaining_edges,
removed_edge_fraction,largest_cluster_size,largest_cluster_fraction,
second_largest_cluster_size,mean_cluster_size,
accepted_requests,rejected_requests,seed
```

全行で次を満たす。

```text
accepted_requests + rejected_requests = step
removed_edges + remaining_edges = M0
0 <= p <= 1
0 <= P <= 1
```

### manifest.csv とrun要約

走査の `manifest.csv` は条件番号、`L`、`C`、budget mode、run数、最大step、測定方式、測定間隔、停止方式、base seed、結果相対パス、および任意のedge trace相対パスを記録する。各条件ディレクトリは原則 `L={L}/C={C}/` である。

`run_summary.csv` は1 run 1行で、終了理由と終端状態を解析側へ渡す。既存ファイルは実験開始時に上書きし、中断再開や追記は実装していない。

## 8. 辺削除トレース

edge traceを有効にすると、`results.csv` とは別に `edge_removals.csv` を出力する。

```text
run,edge_order,step,edge_index_in_request,path_length,
edge_id,source,target,seed
```

`edge_order` はrun内で0から始まる削除辺の通し番号、`edge_index_in_request` は `source` から `target` へ向かう最短経路内の0始まり位置である。rejected要求は行を作らず、同じ `edge_id` は同一runで一度だけ現れる。トレースobserverはpair/path乱数を消費せず、トレースの有無でモデル結果は変化しない。

トレースはUnion-Findによる辺単位状態の逆再構成と、経路内辺順序の感度解析に使う。scaling-v1本計算では容量削減のため無効とし、順序感度の副解析だけで有効にした。

## 9. 要求単位解析と辺単位解析

SPPモデルの基本イベントは最短経路全体の同時削除である。したがって主解析では、連続する `ACCEPTED_REQUEST` 状態間の最大 `P` 落下を request event とする。

一方、edge traceから各削除辺数 `k` の状態を厳密に復元し、平均 `S(k/M0)` の最大を conventional疑似臨界点、単一辺削除による最大 `P` 落下を edge event とする解析も保持する。edge eventは原論文のsingle-edge event-based ensembleとの比較に有用だが、1要求で複数辺を削除する場合には、モデル上同時である辺へ人工的な順序を与える必要がある。

`C = 1` では1要求1辺なのでrequest eventとedge eventは一致する。`C = 2` と特に `UNBOUNDED` ではedge eventが経路内順序に依存し得る。`SOURCE_TO_TARGET`、逆順、決定的shuffleの比較で、`UNBOUNDED` の依存性が確認された。このためrequest-level結果をモデル本来の主結果とし、edge-level結果は規約と感度を明記した副解析として扱う。

## 10. 疑似臨界点と有限サイズスケーリング

疑似臨界点には複数の定義があり、相互に同じ量とはみなさない。

- conventional: 全run平均の `S(p)` が最大となる点
- edge event: run内の最大単一辺 `P` 落下点
- request event: run内の最大要求単位 `P` 落下点

転移幅は実際に測定された要求後状態から、`P > 0.5` の最大点と `P > 1/L` の最大点の差で定義し、補間しない。

二次元格子では頂点数 `N` ではなく線形サイズ `L` をFSS変数とする。通常の二次元パーコレーションとの比較値は次である。

```text
beta/nu  = 5/48  ~= 0.10417
gamma/nu = 43/24 ~= 1.79167
1/nu     = 3/4   = 0.75
```

既知指数は仮定して固定するのではなく、SPPデータから得た有効指数との比較対象にする。有限サイズ補正と採用する最小サイズ `L_min` への依存性を必ず確認する。scaling-v1の具体的な手法と結果は [SCALING_V1_RESULTS.md](SCALING_V1_RESULTS.md) に記録する。

## 11. 検証方針と既知の限界

Java側では格子、BFS、一様経路選択、seed分離、測定、停止、trace、走査を単体・結合・小格子参照実装で検証する。Python側ではCSV不変条件、欠損処理、再構成、疑似臨界点、bootstrap、回帰を手計算可能なデータで検証する。

現在の主な限界は次である。

- 開放境界だけを実装している。
- 大きい `L` と `C` では要求ごとのBFSと `BigInteger` 経路数が支配的になり得る。
- scaling-v1は `L <= 64` であり、漸近結論には有限サイズ補正の検討が必要である。
- `UNBOUNDED` のedge-level量は経路内辺順序規約に依存する。
- 中断再開、並列実行、周期境界は未実装である。

## 12. 独立性

本リポジトリは先輩リポジトリから独立している。エントリーポイントとモデル処理の責務分離などを設計上の参考にしたが、コード、データ、ビルド、実行環境の依存関係は持たない。
