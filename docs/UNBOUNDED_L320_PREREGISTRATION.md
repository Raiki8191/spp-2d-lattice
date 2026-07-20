# UNBOUNDED L=320 事前予測登録

## 目的と固定時点

この文書と機械可読表は、UNBOUNDED `L=320`のシミュレーションを1 runも実行せず、`app/out/unbounded-l320`が存在しない状態で固定した。目的は、L=320観測後の再fit結果と事前予測性能を混同せず、モデルごとの外挿能力を評価することである。

- 登録日時（UTC）: `2026-07-20T11:01:24.488978+00:00`
- 解析元commit: `67c0c9c68861373d89ccd03515d726ff352d1515`
- 最大観測サイズ: `L=256`
- 予測対象: `L=320`（最大観測サイズの1.25倍）
- 使用サイズ: `8,12,16,24,32,48,64,96,128,192,256`
- 登録表: `analysis/reference/unbounded_l320_preregistered_predictions.csv`

## 入力の固定

| 入力 | SHA-256 |
|---|---|
| `app/out/unbounded-v5/unbounded_predictions.csv` | `8759016b35af2bd17f831f18f3afd95eed19724545475db856df45dcc13521b6` |
| `app/out/unbounded-v5/unbounded_model_fits.csv` | `e68ac8f49bad5926b9341e41c0fe4bffbf185e5ba9cdeaaeb502d7216187ae38` |
| `app/out/unbounded-v5/unbounded_bootstrap_samples.csv` | `a2d564a8dfb1d8ec0f44633b29ab5ab6de6657e1dc18b7e1be6e51d6fb8872bf` |
| `app/out/unbounded-v5/unbounded_size_summary.csv` | `3057743ef34efe7fdec2a6cc901e8c9b806773198eda2cae75c23202fc95c94b` |

生成器はL=320出力ディレクトリが存在すると停止する。登録表を観測後fitで上書きしてはならない。

## モデルとfit条件

主要な減少観測量にはv5のfitをそのまま使用した。

```text
zero-power:   Y(L) = a L^(-x)
finite-power: Y(L) = Y_inf + a L^(-x)
zero-log:     Y(L) = a / (log L)^q
finite-log:   Y(L) = Y_inf + a / (log L)^q
```

v5では複数初期値、`Y_inf in [0,1]`、正振幅、power指数`[0.001,5]`、log指数`[0.001,10]`、run層別bootstrap 500標本、seed `20260720`を使用した。登録表にはfitパラメータ、境界解、最大相関、残差RMS、bootstrap信頼区間、残差を加えた予測区間を保存した。

S peakはサイズとともに増加するため、v5の正の減衰指数・正振幅制約をそのまま適用できない。そこで同じ数式に対し、zeroモデルは符号付き指数、finiteモデルは符号付き振幅を許した副次的外挿を登録した。S peakの区間は共分散近似と残差RMSから計算し、bootstrapではない。有限S peak fitは指数下限、zero-logは指数境界に到達し、相関もほぼ1であるため、探索的で不安定な予測として扱う。

## 固定したL=320予測

### 最大request jump

| model | 点予測 | 95%信頼区間 | 95%予測区間 |
|---|---:|---:|---:|
| zero-power | 0.273341 | [0.261926, 0.285262] | [0.255421, 0.291261] |
| finite-power | 0.281654 | [0.262774, 0.297263] | [0.260973, 0.302335] |
| zero-log | 0.279439 | [0.269251, 0.288653] | [0.264654, 0.294223] |
| finite-log | 0.281197 | [0.269824, 0.296312] | [0.263967, 0.298428] |

### その他の観測量の点予測range

| 観測量 | 4モデルの点予測range |
|---|---:|
| transition `delta_p` | 0.270430–0.275004 |
| `delta_t/N^2` | 0.00016959–0.00058709 |
| request event `p_after` | 0.418359–0.429347 |
| `std(p_mid)` | 0.017082–0.021953 |
| S peak | 4,841.4–15,755.7 |

全24予測の個別区間と診断は機械可読表を正本とする。`delta_t/N^2`では主fit点予測と高速bootstrap区間の不整合があり、S peakではモデル間差が極めて大きい。これらを都合よく修正せず、予測の不安定性として事前登録する。

## 観測後の評価規則

L=320の20 runを得た後、各モデル・各観測量について次を計算する。

- 観測平均−点予測（符号付き誤差）
- 絶対誤差、相対誤差、標準化誤差
- squared error
- 観測平均が事前95%予測区間に含まれるか
- 観測bootstrap区間と事前予測区間の重なり

最大request jumpでは、L=256に続いてzero-logの絶対誤差が最小か、finiteモデルが改善するか、20 runのSEMでモデル差を識別できるかを確認する。観測後のL=320を含む再fitは別表とし、この事前予測表を変更しない。

## 再現手順

```powershell
python -m analysis.unbounded_l320_preregistration
python -m pytest analysis/tests/test_unbounded_l320_preregistration.py
```

生成器は`app/out/unbounded-l320`が存在する場合、事前登録ではないため明示的に失敗する。
