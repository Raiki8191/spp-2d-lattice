# 解析量と疑似臨界点の定義

この文書は、SPPの要求処理そのものと、その出力から構成する複数の解析ensembleを区別するための用語集である。実装全体は [DESIGN.md](DESIGN.md)、scaling-v1の数値は [SCALING_V1_RESULTS.md](SCALING_V1_RESULTS.md) を参照する。

## 1. 基本変数

`L × L` 開放境界正方格子について、

```text
N  = L^2
M0 = 2L(L - 1)
t  = 処理した全要求数
k  = removed_edges
p  = k / M0
P  = largest_cluster_size / N
```

とする。`t` はacceptedとrejectedの両方を数える。`p` は要求数ではなく、初期辺に対する実際の削除辺割合である。

有限クラスター平均サイズ `S` は、サイズ `s` の成分数を `n_s` として、

```text
S = sum(s^2 n_s) / sum(s n_s)
```

で定義する。最大連結成分をちょうど1個だけ除外する。同率最大成分が複数ある場合、残りの同率成分は有限クラスターへ含める。分母が0なら `S = 0` とする。

## 2. 状態を記録する単位

### ACCEPTED_REQUEST状態

step 0と、受理要求による最短経路全体の削除が完了した直後の状態である。これはSPPモデルの自然な状態列であり、経路内の辺順序を必要としない。

### edge-level状態

edge traceへ記録された順序を使い、ちょうど `k` 本の辺を削除した中間状態を復元したものである。1要求で複数辺を同時削除するSPPでは、中間状態はモデルの要求境界には存在しない。原論文とのsingle-edge比較や診断のための補助的な状態列として扱う。

source-to-target順は保存規約である。逆順または決定的shuffleでも状態を構成できるが、`C > 1` では辺単位結果が変わり得る。 同じ履歴の要求内順序を変える感度と、ensembleの周辺分布を区別する。一様ordered pairと一様経路の理想モデルでは、全要求の `(s,t,path)` を `(t,s,reversed path)` へ対応させても確率と要求後グラフは変わらず、source順とreverse順の周辺分布は同じである。有限標本のpaired平均差を物理的な方向選好と解釈しない。決定的shuffleは別の固定診断規約で、全順列を一様に標本化した証明や最大感度の保証ではない。

## 3. conventional疑似臨界点

edge traceがある場合、各runについて実際に観測された削除本数までの `k = 0, ..., K_final` の状態をUnion-Findの逆追加で厳密に再構成する。`K_final` はそのrunの最終削除本数であり、早期停止後の `k > K_final` は未観測として扱う。条件ごとに同じ `k` で `S` を平均し、平均 `S` が最大となる点を conventional疑似臨界点とする。同率なら小さい `k` を選ぶ。

初期探索で使用したpost-request resamplingは、各grid点 `k` に `removed_edges >= k` を初めて満たす要求後状態を割り当てる。複数辺ジャンプでは同じ状態が複数grid点へ入るため、exact edge-level conventionalとは別の近似である。

## 4. edge event

各runのedge-level状態について、

```text
deltaP_edge(k) = P(k - 1) - P(k)
```

が最大となる単一辺削除をedge pseudocritical eventとする。同率なら小さい `k` を選ぶ。代表位置は削除後の `p_after = k/M0` である。

この定義は論文のsingle-edge event-based ensembleに対応する比較量である。ただし複数辺要求では経路内辺順序に依存するため、順序規約と感度を併記する必要がある。`ACCEPTED_REQUEST` という測定方式自体をevent-based ensembleとは呼ばない。

## 5. request event

連続するグラフ変化後の `ACCEPTED_REQUEST` 行について、

```text
deltaP_request = P_before - P_after
path_length    = removed_edges_after - removed_edges_before
delta_p_request = path_length / M0
```

を計算する。各runで `deltaP_request` が最大となる受理要求をrequest pseudocritical eventとする。同率なら、まず小さい `p_after`、次に小さい `step` を選ぶ。

これは最短経路全体を同時削除するSPP本来の要求単位イベントであり、scaling-v1の主解析である。 最大request jumpの漸近値は主要な診断対象だが、最大jumpがゼロへ向かうだけで、全ての要求後状態からなる熱力学極限のP(p)が連続だと証明したことにはならない。p_midはこの有限runの最大jump基準による位置であり、別の転移基準の臨界点と自動的に同一視しない。`C = 1` では1要求1辺なのでedge eventと一致するが、`C > 1` では別の量である。

## 6. 転移幅

各runの実在する要求後状態だけを使い、補間せずに次を定義する。

```text
p2 = P > 0.5 を満たす最大の p
p1 = P > 1/L を満たす最大の p
delta_p = p1 - p2

t2 = P > 0.5 を満たす最大の step
t1 = P > 1/L を満たす最大の step
delta_t = t1 - t2
delta_t_normalized = delta_t / N^2
```

閾値まで到達しなかったrunは欠損とし、0で置換しない。`TRANSITION_WINDOW_COMPLETE` はaccepted要求後に `P <= 1/L` を確認して停止するため、この窓を完了させる停止方式である。

## 7. scaling-v1のFSS量

条件ごとのrequest event統計から、線形サイズ `L` に対して次のpower lawを対数最小二乗で評価する。

```text
P_before              ~ L^(-x_before)
P_after               ~ L^(-x_after)
deltaP_request         ~ L^(-omega)
S_before               ~ L^(y_before)
S_after                ~ L^(y_after)
std(p_mid)             ~ L^(-1/nu_eff)
delta_p_request        ~ L^(-z)
transition delta_p     ~ L^(-alpha)
```

ここで `p_mid = (p_before + p_after)/2` である。非正値は対数fitへ含めない。`L_min = 8, 12, 16, 24` を変えて有限サイズ補正への感度を確認し、傾きの95%区間と決定係数を記録する。

raw run bootstrapはrunを条件内で復元抽出し、scaling-v1では2,000標本、固定seed `20260715` を使った。bootstrap区間は統計的不確実性を示すが、境界条件、有限サイズ補正、疑似臨界点定義などの系統誤差を含み切るものではない。

## 8. 通常の二次元パーコレーションとの比較

比較対象とする既知値は、

```text
beta/nu  = 5/48
gamma/nu = 43/24
1/nu     = 3/4
2 beta/nu + gamma/nu = 2
```

である。これらをSPPへあらかじめ仮定するのではなく、得られた有効指数、`L_min` 依存性、hyperscaling和を評価する基準として使う。

## 9. 現行解析を読む際の注意

- 本研究の `p` は削除率であり、通常のボンド占有率は `q=1-p` である。正方格子の参照 `q_c=1/2` はこの変換でも `p_c=1/2` となる。
- `ACCEPTED_REQUEST` CSVの末尾には、reject後の変化していない終了snapshotが入る場合がある。これは新しい物理eventではない。request解析は削除辺数が増えた行のみをeventとして扱う。
- `delta_t` は上記の記録された受理状態のstep間の幅である。reject中も状態が持続する全要求列でのplateau終端間の幅とは異なる。後者へ定義を変更して比較してはいけない。`delta_p`にはこの時刻規約の差はない。
- 対数回帰の解析的な傾き95%区間は自由度 `n-2` のStudent t分位を使う。run bootstrapとは別の区間であり、回帰残差についての仮定に条件付けられる。
- 現行AICc/BICの `k` は平均モデルの自由パラメーター数であり、残差分散の推定パラメーターを含めない。この実装上の規約と、元スケール・対数スケールのどちらのRSSかを明記する。異なる目的関数間のAICcをそのまま比較してはいけない。
- 共通base seedは複数のL/Cで再利用される。条件内run bootstrapは各条件の標本単位を保つが、条件間を独立に再標本化する区間はcross-L/C共分散を含まない。多変量fitや指数差の区間へ適用する際の限界である。
- 補正モデルのbootstrapで失敗標本を記録し、収束標本からpercentileを作った場合、その区間は有効fitに条件付けられる。高いfailure/boundary frequencyの区間を精密な漸近指数の証拠として使わない。

`boundary_solution` は、有限boundsの幅に比例した `1e-8` の数値判定である。例えば振幅boundsが `[1e-12,1e6]` の場合、約 `0.01` 以下の振幅でもlower-bound flagが立つ。flagだけから厳密な境界到達や物理的不適切さを断定せず、実パラメーター、bounds、予測の正値性、相関を併記する。UNBOUNDED有限極限のzero-boundary frequencyは別に `0 <= Y_inf <= 1e-8` を使う。
