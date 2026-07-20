# UNBOUNDED v4: L=192段階実験と漸近モデル再評価

## 1. 目的と既存結果の保持

scaling-v3では、UNBOUNDEDの最大request jumpについてzero-logがAICc、BIC、LOOでわずかに優勢だった一方、有限値漸近モデルのbootstrap区間は0近傍から約0.29まで広く、転移次数は識別できなかった。v4では既存のscaling-v2/v3データを変更せず、UNBOUNDEDの`L=192`だけを追加し、モデル識別力がどれだけ増すかを調べた。C=1、C=2、L=256の本計算は行っていない。

解析対象はrequest単位の最大落下`delta_P_request`、transition width `delta_p`、`delta_t/N^2`、request-event位置`p_mid`のrun間標準偏差である。ACCEPTED_REQUEST測定はSPPの要求単位状態を記録し、論文のsingle-edge event ensembleとは異なる。

## 2. L=192実験設計

全stageで`L=192`、`C=N=36864`（UNBOUNDED）、OPEN、`ACCEPTED_REQUEST`、`TRANSITION_WINDOW_COMPLETE`、閾値`P <= 1/L`、edge trace無効、上限`2N^2`を使用した。既存のbase seed 42系列と重ならない入力seedを連続範囲で割り当てた。

| stage | 追加run | seed入力範囲 | 出力 |
|---|---:|---:|---|
| benchmark | 3 | 1,920,000–1,920,002 | `app/out/unbounded-l192/benchmark` |
| pilot | 17 | 1,920,003–1,920,019 | `app/out/unbounded-l192/pilot` |
| main | 30 | 1,920,020–1,920,049 | `app/out/unbounded-l192/main` |
| stop audit | 3（別系列ではなくbenchmarkと同seed） | 1,920,000–1,920,002 | `app/out/unbounded-l192/stop-audit` |

各runを独立シャードへ出力し、14列、不変条件、stepとremoved edgeの単調性、seed、最終行、run summary、停止理由を検査してから`.complete`を置く。再実行時は正常な完了シャードだけをスキップし、完了マーカー付きの破損シャードは拒否する。全シャード完了後に互換manifest、`results.csv`、`run_summary.csv`、`run_metadata.csv`を生成する。時刻、経過時間、停止理由、行数、容量、観測heapをrunごとに記録した。観測heapはJVMが報告した測定時点の値であり、OSレベルの厳密なpeak RSSではない。

## 3. benchmark、pilot、main

| stage | run | run時間 min / mean / median / max (s) | データ行 | shard results容量 |
|---|---:|---:|---:|---:|
| benchmark | 3 | 1.476 / 1.593 / 1.646 / 1.657 | 2,464 | 0.307 MB |
| pilot | 17 | 1.173 / 1.440 / 1.422 / 1.742 | 13,441 | 1.656 MB |
| main | 30 | 1.302 / 1.436 / 1.421 / 1.672 | 23,493 | 2.899 MB |

本計算50 runの計測時間合計は約72.4秒（Gradle起動・集約を除く）で、全runが`TRANSITION_WINDOW_COMPLETE`だった。追加実験全体（auditを含む）は228ファイル、約10.6 MBである。全manifestで欠損、seed重複、run欠落、14列違反、不変条件違反はなかった。最大観測heap使用量は約306 MB、committed heapは512 MBだった。

20 run時点では最大jumpが`0.26183 ± 0.01774`（SEM）で、有限値fitの区間が広かった。50 runでは次の値となった。

| 観測量 (L=192) | 推定値 | run標準偏差 | SEM |
|---|---:|---:|---:|
| 最大request jump | 0.289584 | 0.076860 | 0.010870 |
| transition `delta_p` | 0.263334 | 0.018342 | 0.002594 |
| `delta_t/N^2` | 0.00018303 | 0.00004119 | 0.00000582 |
| `std(p_mid)` | 0.022267 | — | — |

追加50 runで100 runへ増やすと最大jumpのSEMは単純見積りで0.01087から0.00769へ下がるが、モデル差はサイズ依存の系統差であり、単一サイズの反復だけでは解消しない。推定追加時間約72秒、results約4.9 MBに対する情報価値は低いと判断し、50 runで停止した。

## 4. 停止監査

benchmarkと同じ3 seedを別出力で`P <= 0.5/L`まで延長した。3/3 runで本計算部分がbit-levelで同一のprefixとなり、最大request event、S peak、transition widthはすべて不変だった。したがって調べたseedでは`P <= 1/L`停止後に主要観測量は更新されなかった。この監査は3 runに限られ、全seedに対する数学的保証ではない。

## 5. モデルと診断

サイズ`L=8,12,16,24,32,48,64,96,128,192`を用い、次を比較した。

```text
zero-power:   Y(L) = a L^(-x)
finite-power: Y(L) = Y_inf + a L^(-x)
zero-log:     Y(L) = a / (log L)^q
finite-log:   Y(L) = Y_inf + a / (log L)^q
```

境界は`a>0`、`Y_inf in [0,1]`、powerの`x in [0.001,5]`、logの`q in [0.001,10]`とした。複数初期値から最小RSS解を選び、AICc、BIC、LOO、共分散、最大パラメータ相関、境界到達、fit失敗を保存した。bootstrapは各Lのrunを独立に再標本化した500標本である。L_min系列は8–64を調べた。

### 最大request jump

| model | Y_inf | x または q | AICc | BIC | LOO MAE |
|---|---:|---:|---:|---:|---:|
| zero-power | 0固定 | 0.07276 | -93.17 | -94.28 | 0.00799 |
| finite-power | 0.26712 | 0.47325 | -92.19 | -95.28 | 0.00761 |
| zero-log | 0固定 | 0.25161 | **-96.72** | **-97.83** | **0.00655** |
| finite-log | 0.20189 | 0.67844 | -92.86 | -95.95 | 0.00666 |

AICc、BIC、LOOはいずれもzero-logを最良とするが、差は決定的ではない。有限powerの`Y_inf` bootstrap 95% percentile区間は約`[0.000006, 0.2973]`、有限logは`[0.0000004, 0.2923]`である。下限が形式上0より大きいのは`Y_inf >= 0`という境界付きfitと有限bootstrap標本によるもので、物理的にゼロを排除した証拠とは解釈しない。最大相関は0.96–1.00と高く、`Y_inf`、振幅、減衰指数の識別は不安定である。

L_minを変えると有限powerの`Y_inf`はほぼ0から0.282、有限logはほぼ0から0.277まで動く。zeroモデルの有効指数も動く。これは都合のよいfitだけを採用できない主要な不安定性である。

### transition width

`delta_p`ではzero-powerがAICc最良（-82.53）、zero-logとの差は0.72、減衰指数はそれぞれ0.0149、0.0331と非常に小さい。有限モデルの主fitは`Y_inf≈0`の境界解である一方、bootstrapは上限境界に近い指数と`Y_inf≈0.29`へ頻繁に移り、境界頻度はpower 0.596、log 0.900だった。したがってtransition widthの漸近値は最大jump以上に不安定である。`delta_t/N^2`と`std(p_mid)`はzero-powerが情報量基準で優勢だが、これも有限値モデルを一般に排除するものではない。

## 6. scaling-v3から変わったこと

L=192の最大jump観測値0.28958に対しv3事前予測はzero-power 0.27840、finite-power 0.28677、zero-log 0.28501、finite-log 0.28671だった。有限モデルの点予測が近かった一方、L=192追加後もzero-logがAICc/BIC/LOOで最良だった。LOO MAEはzero-logで0.00693から0.00655へわずかに改善し、finiteモデルも改善した。つまりL=192は全モデルを更新したが、ゼロ漸近対有限値漸近の予測区間は依然重なる。

L=256における最大jumpの予測（観測ではない）はzero-power 0.2761、finite-power 0.2856、zero-log 0.2824、finite-log 0.2852で、モデル間rangeは0.0095である。各bootstrap予測区間を合わせると概ね0.268–0.299で重なる。L=384、512への外挿は観測最大Lの2倍、2.67倍であり、さらに強い警告を要する。

## 7. 現時点の判定と次の計算

最も防御可能な結論は「zero-logが相対的に優勢だが、ゼロ漸近も有限値漸近も排除できず、現在も判定不能」である。有限値モデルが明確に支持された、またはゼロ漸近が確定したとは言えない。L=192を100 runへ増やすより、異なるサイズを1点追加する方がモデル曲率を直接制約する。

L=256は自動実行していない。v3の実測外挿は約3.26秒/run、20 runで約65秒、50 runで約163秒、100 runで約326秒であり、容量も現実的と予測される。ただしこれは観測ではない。次の推奨は、まずUNBOUNDED L=256を20 runの段階pilotとして実行し、モデル間予測差に対するSEMと整合性を再評価することである。反対に、L=192を100 runへ増やす優先度は低い。

## 8. 再現手順と成果物

```powershell
.\gradlew.bat run --args="--unbounded-l192-benchmark"
.\gradlew.bat run --args="--unbounded-l192-pilot"
.\gradlew.bat run --args="--unbounded-l192-main"
.\gradlew.bat run --args="--unbounded-l192-stop-audit"
python -m analysis.unbounded_v4 --stage pilot --bootstrap-samples 300
python -m analysis.unbounded_v4 --stage main --bootstrap-samples 500
```

CSVと15図は`app/out/unbounded-v4/main50/`、生データは`app/out/unbounded-l192/`に生成され、Git管理しない。主な機械可読表はmodel fit、LOO、bootstrap標本・区間、L_min、外挿、v3/v4比較、停止監査、run数判断、次サイズ判断である。

## 9. 限界

- L=192は50 runで、L<=64の200 run、L=96/128の400 runより少ない。
- 観測量のサイズ間平均に対する非線形fitであり、誤差の異分散やサイズ間系統誤差を完全にはモデル化していない。
- bootstrapの高速fitと主multi-start fitは数値経路が異なる。主推定・診断はmulti-start、区間はrun再標本化の感度評価として読む。
- 有限モデルの境界と高相関により、通常の共分散近似は楽観的になり得る。
- logモデルは経験的な遅い収束候補であり、厳密な理論導出ではない。
- 3 seedの停止監査は完全な証明ではない。
- L=256/384/512は外挿であり観測値ではない。

