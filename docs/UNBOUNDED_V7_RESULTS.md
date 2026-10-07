# UNBOUNDED v7: L=384 事前登録実験と停止監査

> **CURRENT / CORRECTED / HISTORICAL**：v7は最新のL≤384段階である。観測・主点fitはCURRENT、正式なfit不確実性はPhase 4FのCORRECTED成果物を用いる。原登録予測と当時の区間はHISTORICALな事前証拠として保持し、旧fit bootstrap区間を現在の正式値に使用しない。

> **bootstrap訂正（Phase 4F、2026-10-07）**：本文のモデルfit bootstrap CI、区間由来の予測・被覆・densityは当時の出力である。主fitと異なる推定器を使っていたため、正式な不確実性評価は[UNBOUNDED_BOOTSTRAP_CORRECTION.md](UNBOUNDED_BOOTSTRAP_CORRECTION.md)と`app/out/unbounded-v7-bootstrap-corrected/`を参照する。raw観測、単一サイズの直接再標本化CI、主fit・AICc/BIC・LOO・固定点予測・事前登録原本はこの訂正で変更しない。歴史的出力は保存する。


## 1. 目的と位置づけ

本解析は、UNBOUNDED 条件の最大 request jump がゼロへ漸近するか、有限値へ漸近するかを、`L=384` の観測を追加して再評価するものである。`L=384` を見る前に v6（最大 `L=320`）だけから予測を固定し、その後に benchmark 3 run、pilot 17 runを順に実行した。したがって、本章では事前予測と事後fitを区別する。

本研究の request event は、受理要求で最短経路全体を同時削除した前後の最大クラスター割合 `P` の落下である。論文比較用の single-edge event-based ensemble とは異なる。

## 2. 事前登録

事前登録は commit `d0117df7c8aa50bd078755b1aed18aa93eae0d0a`（`docs: preregister unbounded L384 predictions`）で固定した。

- 文書: `docs/UNBOUNDED_L384_PREREGISTRATION.md`
- 機械可読表: `analysis/reference/unbounded_l384_preregistered_predictions.csv`
- 使用データ: `L=8,12,16,24,32,48,64,96,128,192,256,320`
- 比較モデル: zero-power、finite-power、zero-log、finite-log
- bootstrap seed: `20260720`

最大 request jump の `L=384` 点予測は、zero-power/finite-power が `0.262769`、zero-log/finite-log が `0.270196` であった。power/log 間の点予測差 `0.007427` は、20 runで想定した SEM `0.014489` より小さく、事前登録時点から単一サイズだけでの識別困難性が予想されていた。

原CSVの`generation_timestamp_utc`は、生成器が解析元commitのcommitter時刻を保存する欄であり、実生成のwall-clock時刻ではない。登録が観測前である根拠は、原本を追加した登録commitと最初のシミュレーション開始の順序である。原欄を変更せず、実生成時刻が記録されているとは主張しない。

## 3. 実験設計と実行

共通条件は `L=384`、`N=C=147456`、開放境界、`ACCEPTED_REQUEST` 測定、`TRANSITION_WINDOW_COMPLETE` 停止、edge trace 無効である。seed は専用範囲 `3840000` から連続に割り当て、既存の `L=192,256,320` と重複しない。

| stage | runs | seed範囲 | 出力 |
|---|---:|---:|---|
| benchmark | 3 | 3840000–3840002 | `app/out/unbounded-l384/benchmark/` |
| pilot | 17 | 3840003–3840019 | `app/out/unbounded-l384/pilot/` |
| stop audit | 3 | benchmarkと同じ | `app/out/unbounded-l384/stop-audit/` |

metadata elapsedの和はbenchmark38.5秒、pilot254.9秒、合計20 runで293.4秒であった。run時間は平均14.67秒、中央値14.58秒、最小11.94秒、最大19.27秒である。最大heapは約406 MiB、20 runのresults shard合計は約4.50 MB、統合データ行数は34,831行だった。全runが `TRANSITION_WINDOW_COMPLETE` で終了し、14列、不変条件、欠損、step順、削除辺単調性、seed一意性を検証した。

実metadata合計293.4秒は、[v6性能候補表](../app/out/unbounded-v6/experiment_options.csv)のL^4外挿293.5秒と約0.1%以内で一致した。ここでstage別・全run合計はmetadata elapsedの和を示す。pilotの最初の開始から最後の終了までのspanは255.2秒であり、計測範囲が異なる。性能外挿はモデル仮定に基づく概算で、他環境や将来サイズでの一致を保証しない。

## 4. 停止監査

benchmarkの3 seedを、より遅い停止位置まで独立出力へ延長した。旧停止位置までの14列prefixは3 runすべて完全一致した。最大 request jump、event `p_after`、`S_peak`、transition widthもすべて不変だった。監査終了stepは `4,237,552`、`3,686,324`、`5,126,606` で、元の `940,283`、`1,109,462`、`955,660` より後まで進んでいる。この範囲では停止条件による主要量の取りこぼしは認められない。

## 5. L=384 の記述統計

| 観測量 | 平均/推定値 | SD | SEM | bootstrap 95% CI |
|---|---:|---:|---:|---:|
| 最大 request jump | 0.257431 | 0.059666 | 0.013342 | [0.232724, 0.284325] |
| transition `delta_p` | 0.230410 | 0.013456 | 0.003009 | [0.224854, 0.236385] |
| `delta_t/N^2` | 0.00005752 | 0.00001332 | 0.00000298 | [0.00005199, 0.00006365] |
| request event `p_after` | 0.443031 | 0.011571 | 0.002587 | [0.438111, 0.448041] |
| `std(p_mid)` | 0.011676 | — | bootstrap SE 0.001578 | [0.008168, 0.014341] |
| `S_peak` | 18,991.6 | 6,463.7 | 1,445.3 | [16,484.1, 21,805.5] |

最大 request jump の中央値は0.231300、四分位範囲は[0.221196, 0.294105]、範囲は[0.168070, 0.376390]で、Tukey基準の外れ値は0件だった。20 runであるため、特にtailや分散の推定には大きな不確実性が残る。

## 6. L=320 から L=384 への変化

`L=320` の平均 `0.245623 ± 0.014489 SEM` に対し、`L=384` は `0.257431 ± 0.013342 SEM` だった。差（384−320）は `+0.011808`、独立標本の合成SEMは0.019696、標準化差は0.599、Cohenの `d=0.190` である。差のbootstrap 95% CIは[-0.025777, 0.049301]で0を含み、`L=384` が小さいbootstrap確率は0.274だった。

したがって、L=320で見られた低下がL=384でも単調に継続したとは言えない。ただし、2サイズ比較だけから漸近形を決めることもできないため、全サイズfitと逐次予測を併用する。

## 7. 事前予測の評価

最大 request jump の観測値に対する誤差は次の通りである。

| model | 事前予測 | 観測−予測 | 絶対誤差 | 標準化誤差 | 95%予測区間内 |
|---|---:|---:|---:|---:|---:|
| zero-power | 0.262769 | -0.005338 | 0.005338 | -0.400 | yes |
| finite-power | 0.262769 | -0.005338 | 0.005338 | -0.400 | yes |
| zero-log | 0.270196 | -0.012765 | 0.012765 | -0.957 | yes |
| finite-log | 0.270196 | -0.012765 | 0.012765 | -0.957 | yes |

4モデルすべての95%予測区間が観測bootstrap区間と重なった。絶対誤差とpredictive log densityではzero-powerが最良だったが、事前予測区間自体が広く、L=384単独で他モデルを排除する証拠にはならない。`S_peak` は事前予測モデル間の幅が大きく、fit境界・補外依存も強いため探索的結果とする。

L=256、320、384の逐次予測をまとめると、zero-powerのMAE `0.01287`、RMSE `0.01661` が最小だった。全モデルの区間内率は3サイズ中2サイズ（0.667）であり、L=320は全モデルにとって難しい観測だった。特定の1サイズだけの勝敗ではなく、この累積性能を重視する。ただしL=256はモデル平均CI、L=320/384は残差合成PIであり、この2/3を均一な名目95%予測区間の校正確認とはしない。原登録PIと事後訂正区間も区別する。

## 8. v7 漸近モデルfit

比較式は次の4つである。

- zero-power: `Y(L)=a L^(-x)`
- finite-power: `Y(L)=Y_inf+a L^(-x)`
- zero-log: `Y(L)=a/(log L)^q`
- finite-log: `Y(L)=Y_inf+a/(log L)^q`

全13サイズ（`L=8`〜384）の最大 request jump fitは次の通りである。

| model | AICc | BIC | LOO MAE | LOO RMSE | decay exponent | `Y_inf` point |
|---|---:|---:|---:|---:|---:|---:|
| zero-power | -116.316 | -116.386 | 0.009516 | 0.011633 | 0.08136 | 0固定 |
| finite-power | -112.849 | -113.821 | 0.009622 | 0.011860 | 0.08136 | 約0（境界） |
| zero-log | -113.543 | -113.613 | 0.009522 | 0.012393 | 0.29948 | 0固定 |
| finite-log | -110.076 | -111.048 | 0.009522 | 0.012393 | 0.29948 | 約0（境界） |

zero-powerはAICc、BIC、LOO RMSEで最良で、LOO MAEも僅差で最良だった。finiteモデルの点推定はゼロ境界へ退化し、追加パラメータの利得がないため主fitでは不採用である。一方、finite-powerのbootstrap `Y_inf` 95%区間は概ね `[5.3e-7, 0.248]`、finite-logは `[8.3e-8, 0.100]` と広い。これらは旧HISTORICAL / SUPERSEDED区間である。現行の有限極限区間はpower `[3.444047e-23, 0.2480454955]`、log `[5.107526e-23, 0.1000251803]`で、[正式CSV](../app/out/unbounded-v7-bootstrap-corrected/unbounded_bootstrap_intervals.csv)を参照する。高いパラメータ相関（最大0.999以上）もあり、有限極限を統計的に排除したとは解釈しない。

`L_min=8`〜96ではzero-powerのAICc順位が一貫してzero-log以上だった。ただし両者の差は大サイズ側だけでは縮まり、局所有効指数は `192→256`、`256→320`、`320→384` で大きく揺れ、最後の区間では符号が反転した。このため、全サイズでのzero-power優位と、局所漸近形の未確定性を分けて記述する。

## 9. power と log の識別力

parametric bootstrap 500反復では、zero-powerを真としたときzero-powerを選ぶ率は0.806、zero-logを真としたときzero-logを選ぶ率は0.826だった。誤選択率はそれぞれ0.194、0.174である。この率は、当てはめた各zeroモデルを真とし、各サイズのmean SEMを用いた独立Gaussian生成と非正値の数値floor、二つのzero候補のAICc選択に条件付けた値である。実モデルが真である確率、finite候補を排除する率、全候補間の識別率ではない。生成仮定の下での識別力診断として扱う。

モデル順位はv4（最大L=192）とv5（256）ではzero-logが1位、v6（320）とv7（384）ではzero-powerが1位へ移った。新しいサイズ追加ごとに証拠が一方向に強まり続けたわけではない。現時点の分類は「ゼロ漸近が優勢、その中ではzero-powerが優勢だが、power/logを確定できない」である。

ここで「ゼロ漸近が支持されること」と「powerかlogかを識別できること」は別の主張である。前者は点fitと情報量基準が支持するが、有限モデルのbootstrap上限が広いため有限極限の厳密な排除には至らない。後者も局所有効指数と20 runの誤差から最終確定には至らない。

## 10. 補外

L=512、768、1024、1536への値は観測ではない。最大 request jump の点予測は、zero-powerで `0.2556, 0.2473, 0.2416, 0.2337`、zero-logで `0.2642, 0.2593, 0.2560, 0.2517` である。L=1536は最大観測サイズの4倍であり、zero-power/logの差は約0.0179まで広がる一方、個々の95%予測区間はなお大きく重なる。これらを確定値として扱ってはならない。

## 11. 追加計算の費用対効果と停止判断

L=384を50 runに増やすと推定SEMは0.00844、100 runでも0.00597である。L=512におけるpower/logの点予測rangeは約0.00860なので、その半分を目安にすると必要SEMは約0.00430であり、L=384で同程度へ達する単純見積りは約193 runとなる。同一サイズのrun追加は平均の精度を上げるが、漸近曲率を増やさない。

L=512の3 run benchmarkは約138秒、20 run pilotは約922秒という経験的外挿になるが、新しいサイズは曲率情報を増やす代わりに、20 runでは依然としてモデル差より標本誤差が大きい可能性が高い。さらに大きなLへの外挿は実測範囲外である。

今回の停止基準、すなわち (1) zeroモデルがAICc/BIC/LOOで優位、(2) finite点推定がゼロ境界、(3) v6から結論分類が変わらない、(4) 次サイズのモデル差が現在のSEM以下、を概ね満たす。ただしこれは有限極限を証明したという意味ではない。

したがって、選択肢E「UNBOUNDED追加計算をいったん終了し、卒論本文・図表の整理へ移る」を推奨する。追加計算を行うなら、同一Lのrun増加より、新しいLで十分なrun数を事前に設計した独立研究として実施する。L=512以上は本作業では実行していない。

## 12. 卒論本文に使える要約

UNBOUNDED条件についてL=384、20 runを事前登録方式で追加した。最大 request jump は `0.2574±0.0133`（SEM）で、L=320より平均は0.0118大きかったが、差のbootstrap区間は0を含んだ。L=8〜384の全サイズfitではゼロ漸近power則がAICc、BICおよびLOO RMSEで最良となり、有限極限モデルの点推定はゼロ境界へ退化した。逐次予測でもzero-powerの誤差が最小であった。一方、有限極限のbootstrap上限は広く、局所有効指数も大サイズ側で揺れるため、有限極限を厳密に排除した、またはpower則と対数則を確定的に識別したとは言えない。現サイズ範囲では「最大request jumpはゼロへ減衰する描像が優勢だが、漸近関数形は未確定」という結論が最も防御可能である。

## 13. 成果物と再現

以下は当時の生成コマンド（HISTORICAL）。完成済み実験・解析出力や原登録を上書きしない。現在の訂正成果物と[監査台帳](ANALYSIS_AUDIT_CORRECTIONS.md)を優先する。

解析:

```powershell
python -m analysis.unbounded_v7 --bootstrap-samples 500 --identification-samples 500 --output app/out/unbounded-v7 --docs-tables docs/tables
```

主要な機械可読成果物は `app/out/unbounded-v7/`、図は同 `figures/` に生成する。大容量CSVとPNGはGit管理対象外である。Gitには軽量な論文用表 `docs/tables/UNBOUNDED_SUMMARY.csv` と `docs/tables/UNBOUNDED_MODEL_HISTORY.csv` のみを含める。

## 14. 限界

- L=384は20 runであり、平均、tail、分散の不確実性が大きい。
- 4つの候補式は漸近仮説であり、真の関数形を網羅しない。
- finiteモデルはパラメータ相関と境界解の影響が強い。
- AICc/BIC、LOO、bootstrap、逐次予測は異なる問いに答えるため、単一指標だけで採否を断定しない。
- 補外値は最大観測サイズから離れるほど不確実で、観測値ではない。
- request-level eventはsingle-edge event-based ensembleと同一ではない。
