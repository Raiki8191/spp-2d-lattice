# UNBOUNDED L=384 事前予測登録

## 目的と固定時点

この文書と`analysis/reference/unbounded_l384_preregistered_predictions.csv`は、UNBOUNDED `L=384`を1 runも実行せず、`app/out/unbounded-l384`が存在しない状態で固定した。最大観測サイズは`L=320`であり、v6までのデータだけを使用した。L=384観測後の再fitと本予測を混同せず、予測表は事後に上書きしない。

- 解析元commit: `8afd49f08c4d5be00aa448accfc6e77aaf00387e`
- 最大観測サイズ: `L=320`
- 使用サイズ: `8,12,16,24,32,48,64,96,128,192,256,320`
- run数: `200,200,200,200,200,200,200,400,400,50,20,20`
- run層別bootstrap: 500標本、seed `20260720`
- 対象モデル: zero-power、finite-power、zero-log、finite-log
- L=384出力: 未作成、0 run

機械可読表には入力manifest一覧とSHA-256、v6のprediction、fit、bootstrap、summaryのSHA-256、生成時刻、fitパラメーター、境界、失敗率、境界率、最大相関を行ごとに保存した。

## 最大request jumpの事前予測

| model | point | bootstrap median | 95% CI | 95% prediction interval |
|---|---:|---:|---:|---:|
| zero-power | 0.262769 | 0.262067 | [0.250507, 0.274181] | [0.240502, 0.285035] |
| finite-power | 0.262769 | 0.263301 | [0.252024, 0.281736] | [0.238761, 0.286776] |
| zero-log | 0.270196 | 0.268909 | [0.258829, 0.279558] | [0.247533, 0.292858] |
| finite-log | 0.270196 | 0.270106 | [0.260968, 0.281958] | [0.247474, 0.292918] |

zero-powerとzero-logの点予測差は`0.007427`である。L=320のSDを20 runへ単純移送した想定SEMは`0.014489`であり、モデル差より大きい。したがってL=384の20 runだけでpower/logを識別することは事前時点から困難と予想する。finiteモデルの点fitは最大jumpで`Y_inf=0`境界へ退化しており、対応するzeroモデルと同一点予測になる。bootstrap区間は依然広いため、これは有限極限の統計的排除を意味しない。

## その他の事前予測

| observable | zero-power | finite-power | zero-log | finite-log |
|---|---:|---:|---:|---:|
| transition `delta_p` | 0.260849 | 0.260849 | 0.266539 | 0.266539 |
| `delta_t/N^2` | 0.000134 | 0.000134 | 0.000519 | 0.000519 |
| request event `p_after` | 0.421305 | 0.431319 | 0.423811 | 0.430268 |
| `std(p_mid)` | 0.016167 | 0.017951 | 0.020906 | 0.020906 |
| S peak | 17,852.59 | 8,096.07 | 12,266.99 | 6,836.12 |

transition widthは`delta_p`と`delta_t/N^2`の両方で登録した。S peakは増加量であり、標準の正減衰モデルを直接適用できないため、符号付き指数または振幅を許す探索的fitである。finite S peakは指数下限、zero-logは指数下限、相関はほぼ1であり、S peak予測は特に不安定である。S peak区間は共分散近似で、run bootstrapではない。

## fit条件と限界

powerモデルは指数`[0.001,5]`、logモデルは`[0.001,10]`、finite極限は`[0,1]`、標準観測量の振幅は正とした。zeroモデル6初期値、finiteモデル15初期値を使用した。v6点fitの最大jumpでfiniteモデルは境界解、最大パラメーター相関はfinite-power `0.999827`、finite-log `0.999702`だった。500 bootstrapのfit失敗率は全モデル0だが、非負境界近傍の値を有限極限検出とは扱わない。

予測区間はbootstrap CIとv6残差RMSを合成した近似である。観測後のL=384平均が区間内にあるか、観測bootstrap区間との重なり、予測誤差、逐次予測性能をv7で評価する。特定の1サイズで最小誤差になったモデルだけを採用しない。

## 完全性

生成器は`app/out/unbounded-l384`が存在すると処理を拒否する。テストでは2回の生成結果が完全一致し、全行の最大使用サイズが320、targetが384であることを確認した。本登録後に実験へ進むため、機械表と本書のSHA-256および事前登録commitを記録する。
