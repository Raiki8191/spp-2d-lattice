# UNBOUNDED v6: L=320パイロットと逐次予測評価

## 1. 目的と事前登録

UNBOUNDED v5では、最大request jumpの漸近挙動についてzero-logがAICc、BIC、LOOで最良だった一方、有限極限モデルの区間は広く、ゼロ漸近と有限値漸近を識別できなかった。v6では同一サイズの反復追加より新しいサイズ情報を優先し、`L=320`を20 runだけ追加した。

観測前に、v5の`L<=256`データだけから4モデルのL=320予測を[事前登録文書](UNBOUNDED_L320_PREREGISTRATION.md)と`analysis/reference/unbounded_l320_preregistered_predictions.csv`へ固定した。事前登録コミットは`0ef0cb5c394e4c67dfe8359c61f5a3c9016197e0`である。予測生成時には`app/out/unbounded-l320`が存在せず、L=320は0 runだった。観測後に登録表を変更していない。

最大request jumpの登録値は次の通りである。CIはモデル平均のbootstrap 95%区間、PIは残差を含めた95%予測区間である。

| model | point prediction | 95% CI | 95% PI |
|---|---:|---:|---:|
| zero-power | 0.273341 | [0.261926, 0.285262] | [0.255421, 0.291261] |
| finite-power | 0.281654 | [0.262774, 0.297263] | [0.260973, 0.302335] |
| zero-log | 0.279439 | [0.269251, 0.288653] | [0.264654, 0.294223] |
| finite-log | 0.281197 | [0.269824, 0.296312] | [0.263967, 0.298428] |

## 2. L=320段階実験

条件はUNBOUNDED、`L=320`、`N=C=102,400`、OPEN境界、`ACCEPTED_REQUEST`測定、`TRANSITION_WINDOW_COMPLETE`停止、閾値`P<=1/L`、edge trace無効、要求上限`2N^2`である。入力seed名前空間はL=192、L=256と重複しない`3,200,000`から開始した。

| stage | input seed | runs | aggregate rows | aggregate results bytes | metadata elapsed |
|---|---:|---:|---:|---:|---:|
| benchmark | 3,200,000--3,200,002 | 3 | 4,390 | 534,571 | 22.704 s |
| pilot | 3,200,003--3,200,019 | 17 | 24,026 | 2,937,661 | 120.907 s |
| total | -- | 20 | 28,416 | 3,472,232 | 143.611 s |

20 runの1 run時間は平均7.181 s、中央値7.078 s、最小5.985 s、最大8.505 sだった。実測最大heap使用量は323,664,400 bytes（約308.7 MiB）、committed heap最大は536,870,912 bytesだった。L=320生出力全体は停止監査を含め約8.53 MB、v6解析生成物は約2.60 MBである。benchmarkだけからの中央値外挿は20/50/100 runで約151/378/756 sであり、実測20 runは同じ桁だった。実行時間はマシン状態を含む観測値で、他環境の保証ではない。

全20 runが`TRANSITION_WINDOW_COMPLETE`で終了した。resultsは既存14列を維持し、欠損0、各run内step厳密増加、removed edges単調非減少、全行の不変条件成立を確認した。benchmark、pilot、L=192、L=256間のrun seed重複は0だった。各runを独立shardに保存し、完全なshardは再実行時に`resume-skip`する。破損・欠損shardは共通stage engineの検査で拒否される。

## 3. benchmark判断と停止監査

benchmark 3 runはすべて正常終了し、実行時間6.735--8.408 s、最大heap約210 MiB、集約4,390行だった。異常な性能劣化、形式不整合、停止不完全性がなかったため、追加17 runへ進んだ。L=384、L=256反復追加、C=1/C=2追加、L=320の50 run以上は実行していない。

benchmarkと同じ3 seedを別出力で`P<=0.5/L`まで継続する停止監査も行った。元resultsは監査resultsの完全な14列prefixであり、最大request jump、event `p_after`、S peak、transition `delta_p`は3 runすべて完全一致した。監査も全runが`TRANSITION_WINDOW_COMPLETE`で終了し、より遅い停止位置により主要量が変わらないことを確認した。

## 4. L=320の記述統計

run層別bootstrapは5,000標本、seed `20260720`で記述区間を計算した。

| observable | estimate | sample SD | SEM | median | Q1--Q3 | min--max | bootstrap 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|
| maximum request jump | 0.245623 | 0.064798 | 0.014489 | 0.222061 | 0.196023--0.292625 | 0.165264--0.367988 | [0.219380, 0.273982] |
| transition `delta_p` | 0.239283 | 0.021043 | 0.004705 | 0.241014 | 0.222753--0.249388 | 0.207969--0.278874 | [0.230578, 0.248480] |
| `delta_t/N^2` | 0.0000755 | 0.0000192 | 0.0000043 | 0.000070 | 0.000061--0.000090 | 0.000050--0.000119 | [0.000068, 0.000084] |
| request event `p_after` | 0.438233 | 0.021323 | 0.004768 | 0.436555 | 0.423027--0.453022 | 0.394005--0.478105 | [0.429102, 0.447255] |
| `std(p_mid)` | 0.021172 | -- | 0.003098 | -- | -- | -- | [0.014318, 0.026435] |
| S peak | 12,414.26 | 4,158.33 | 929.83 | 10,875.82 | 9,190.88--15,071.84 | 7,067.60--22,500.18 | [10,779.90, 14,268.15] |

`std(p_mid)`は20 event位置の標準偏差であり、表中の個々のevent位置の中央値・四分位とは別の量なので省略した。S peakは各runの要求後測定点における有限クラスター平均サイズSの最大値である。

## 5. 事前予測の検証

最大jumpの観測平均0.245623は4モデルの点予測より0.027718--0.036031低かった。絶対誤差はzero-powerが最小（0.027718）、zero-log 0.033816、finite-log 0.035574、finite-power 0.036031だった。観測平均はすべての登録PIの下側にあり、標準化誤差は-1.91から-2.49 SEMだった。一方、観測平均のbootstrap区間と各PIは重なる。20 runのSEM 0.014489は4モデルの登録点予測range約0.00831より大きく、モデル同士を単一Lで精密に順位付けするには不足している。

L=256ではzero-logが事前予測誤差最小だったが、L=320ではzero-powerが最小になった。L=192、256、320の逐次絶対誤差合計はzero-log 0.03913、finite-log 0.04193、finite-power 0.04281、zero-power 0.04445で、zero-logがわずかに最小である。ただしL=192予測は当時固定表が残っていないため、L=192追加前データからの事後再構成であり、L=256とL=320の厳密な事前登録とは区別する。

他のL=320観測でもtransition `delta_p`は全登録点より約0.031--0.036低かった。event `p_after`はfinite-powerの誤差0.00889が最小、`std(p_mid)`はzero-log/finite-logの誤差0.00078が最小、S peakは探索的zero-logの誤差3,274が最小だった。S peak登録fitは境界解・強相関を含むため、外挿検証は副次的である。

## 6. v6モデル比較

比較モデルは次の4つである。

```text
zero-power:  Y(L) = a L^(-x)
finite-power:Y(L) = Y_inf + a L^(-x)
zero-log:    Y(L) = a / (log L)^q
finite-log:  Y(L) = Y_inf + a / (log L)^q
```

全`L=8,12,16,24,32,48,64,96,128,192,256,320`を使用した。power指数境界は`[0.001,5]`、log指数は`[0.001,10]`、`Y_inf`は`[0,1]`、振幅は正とした。zeroモデルは6初期値、finiteモデルは15初期値でbounded multi-start fitを行い、AICc、BIC、LOO、共分散、境界解、最大相関を記録した。run層別bootstrapは500標本である。

最大request jumpの結果は次の通りである。

| model | AICc | BIC | LOO MAE | LOO RMSE | point `Y_inf` | decay exponent | max correlation | status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| zero-power | -106.12 | -106.48 | 0.01005 | **0.01254** | 0 | 0.07984 | 0.955 | admissible |
| finite-power | -102.45 | -103.99 | 0.01074 | 0.01420 | ~0 | 0.07984 | 0.9998 | boundary/inadmissible |
| zero-log | -104.52 | -104.89 | **0.00896** | 0.01274 | 0 | 0.28791 | 0.969 | admissible |
| finite-log | -100.86 | -102.40 | 0.00910 | 0.01314 | ~0 | 0.28791 | 0.9997 | boundary/inadmissible |

v4とv5ではzero-logがAICc/BIC 1位だったが、L=320追加後のv6ではzero-powerが両基準1位になった。LOOはMAEでzero-log、RMSEでzero-powerが最良であり、一つの指標に収束していない。有限モデルの点fitは`Y_inf=0`境界へ落ち、追加パラメーターの改善がなく不採用となった。L_minを8から96へ上げても有限モデルの点解はゼロ境界だった。一方、run bootstrapの有限極限95%上限はfinite-power 0.265、finite-log 0.217と広く、極限と減衰指数の相関もほぼ1である。optimizerの非負境界によりbootstrap下限が微小な正値になることを「有限極限の検出」とは解釈しない。

transition `delta_p`と`delta_t/N^2`もzero-powerがAICc/BICで最良で、finite点fitはゼロ境界だった。event位置分散はzero-powerがAICc最良だがfinite-powerも許容解だった。request event `p_after`はfinite-powerがAICc/BIC、LOOで最良で、推定極限0.4301、bootstrap 95%区間[0.4238,0.4344]だった。これは転移位置の漸近であり、最大jumpが有限値へ収束する証拠ではない。

## 7. 累積的に変わったこと

- v4（最大L=192）とv5（最大L=256）ではmaximum jumpのzero-logがAICc/BIC 1位だった。
- v6（最大L=320）では低いL=320観測によりzero-powerが1位へ移り、finiteモデルは点fitでゼロ境界へ移動した。
- zero-logのL=256事前予測は良好だったが、L=320事前予測誤差はzero-powerより大きかった。
- 逐次予測の累積絶対誤差はzero-logがわずかに最小だが、最新点と全点情報量規準ではzero-powerが優勢である。
- モデル順位が新サイズごとに変化したこと自体が、利用可能なサイズ範囲で漸近形の識別が安定していない証拠である。

## 8. 外挿と次の実験

v6は`L=384,512,768,1024`への点外挿、bootstrap区間、モデル間rangeを生成した。これらは観測ではない。maximum jumpのモデル間rangeはL=384で約0.0074、L=1024で約0.0156に広がり、長距離外挿ほどモデル選択依存性が増す。

同一L=320を50/100 runへ増やす単純推定ではjump SEMは約0.00916/0.00648、時間は約354/708 sとなる。一方、粗い`L^4`外挿によるL=384は3/20 runで約44/294 sである。これは性能計画用の概算にすぎない。新サイズは漸近曲率へ直接leverageを加え、同一サイズ反復はL=320平均の不確実性だけを減らす。

したがって次の情報価値は、まずL=384の3 run benchmark、問題がなければ20 run pilotにある。L=320を50または100 runへ増やす案は、L=384の安全性に問題がある場合か、L=320平均を精密化する別目的に限る。v6ではいずれも自動実行していない。

## 9. 暫定結論

L=320追加後、最大request jumpの点fit、AICc、BICはゼロ漸近を明確に優先し、有限モデルはゼロ境界へ退いた。しかし、finite bootstrapは極限と減衰指数の強相関および広い区間を残し、LOO指標もzero-powerとzero-logで分かれる。したがって最も防御可能な判定は、**「ゼロ漸近が優勢だが、有限値漸近を現在のデータだけでは排除できない」**である。特に「zero-logが最良」と「有限値モデルを排除できる」は別の主張であり、前者もv6では維持されなかった。

転移次数はまだ未確定である。有限jumpの証拠は弱くなったが、`L<=320`の12サイズと各大サイズ20 runだけで真の連続転移を確定したとはしない。追加L=384はモデル順位の安定性と有限極限区間の縮小を確認するための次候補である。

## 10. 再現方法と生成物

```powershell
.\gradlew.bat run --args="--unbounded-l320-benchmark"
.\gradlew.bat run --args="--unbounded-l320-pilot"
.\gradlew.bat run --args="--unbounded-l320-stop-audit"
python -m analysis.unbounded_v6 --bootstrap-samples 500 --output app/out/unbounded-v6
```

実験はrun shard単位で再開できる。v6は観測統計、事前予測score、逐次予測、4モデルfit、AICc/BIC、LOO、bootstrap、L_min依存性、v4/v5/v6比較、停止・seed・品質監査、外挿、費用対効果のCSVと18図を`app/out/unbounded-v6/`へ出力する。CSV/PNGと生データはGit管理対象外である。

解析上の限界は、L=320が20 runであること、S peakの登録外挿が探索的であること、有限モデルの非識別性と境界制約、サイズ間でrun数が異なること、外挿性能モデルが粗いことにある。観測値、事前予測、L=320を含む事後fit、未観測サイズへの外挿を混同してはならない。
