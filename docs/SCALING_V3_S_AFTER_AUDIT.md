# scaling-v3 `S_after` 点推定・bootstrap整合性監査

## 1. 発見された問題

`docs/SCALING_V3_RESULTS.md` は `C=1`, `S_after` の単純冪則指数を `1.772434`、run bootstrap 95%区間を `[1.65960, 1.72340]` と報告していた。点推定が区間外であること自体は直ちにバグを意味しないが、コードと生成CSVを追跡すると、両者は同じ `simple_power` ラベルの下で異なる残差を最小化していた。

原因分類は **A（同じ推定量として扱うべき処理の実装不整合）** である。シミュレーション、request event抽出、各サイズのrun平均には不整合がなく、点推定とbootstrap fitの段階だけが異なっていた。

## 2. 点推定の生成方法

- 入力: `app/out/scaling-v2-analysis/request_event_summary.csv`
- 元となるrun-level入力: `request_event_runs.csv` の `S_after`
- 使用列: `S_after_mean`（各 `L` のrun算術平均）
- 使用サイズ: `L = 8, 12, 16, 24, 32, 48, 64, 96, 128`
- `L_min = 8`
- run数: 各サイズ200
- サイズ間の重み付け: なし
- モデル: `Y(L) = a L^x`（`simple_power`）
- 目的関数: 元スケールの非加重RSS `sum((Y_i-aL_i^x)^2)`
- optimizer: SciPy `curve_fit` による有界非線形最小二乗、複数初期値のうち最小RSS解
- 初期値: `a=S_after_mean(L=8)`、`x=-1,-0.2,0.2,1`
- bounds: `1e-12 <= a <= 1e6`, `-5 <= x <= 5`
- `maxfev = 5000`
- 自由パラメーター: `a`, `x`。固定パラメーターなし
- 最終値: `a=0.206700530371`, `x=1.772434446918`
- 4初期値すべて収束、境界解ではない
- `S` は増大型なので符号変換は `scaling_exponent=+x`
- 出力: 旧 `finite_correction_fits.csv` の `condition_label=C=1, observable=S_after, model=simple_power, L_min=8` 行

run-level CSVを再集約し、同じ `power_model_fits` を独立に呼び出して `1.772434446918` を再現した。

## 3. 旧bootstrap区間の生成方法

- 入力: `app/out/scaling-v2-analysis/request_event_runs.csv`
- 再標本化単位: 各 `L` 内のrun（各200本を復元抽出）
- 標本数: 500
- seed: `20260720`、NumPy `default_rng`
- 各標本の集約: `S_after` の算術平均
- 使用サイズ・`L_min`: 点推定と同じ9サイズ、`L_min=8`
- 旧モデル実装: `polyfit(log L, log mean(S_after), 1)`
- optimizer・初期値・bounds: 対数OLSのためなし
- 失敗fit: 0
- 区間: bootstrap指数の2.5/97.5 percentile
- bootstrap平均: `1.691557423379`
- bootstrap中央値: `1.691547706329`
- 再計算95%区間: `[1.659604464307, 1.723396291278]`

監査コードは旧処理と同じobservable順で乱数を消費し、旧 `bootstrap_distributions.csv` / `bootstrap_intervals.csv` の値を再現した。旧点推定はこのCSVへ別フィールドとして保存されておらず、文書作成時に `finite_correction_fits.csv` の元スケール点推定と組み合わされた。

## 4. 不一致の理由と修正

元スケール非線形最小二乗は絶対残差を最小化するため大きい `L` の大きい `S` が目的関数へ強く寄与する。一方、対数OLSは相対的な偏差に近い重みを与える。このため同じ9点でも、点推定は `1.772434`、旧bootstrap分布の中心は約 `1.692` になった。データ列、使用サイズ、`L_min`、run抽出、指数符号は一致しており、相違はfit estimatorである。

`analysis.scaling_v3.bootstrap_primary` を修正し、主要5量では各bootstrap標本にも点推定と同じ `power_model_fits` を適用するようにした。`source_column`, estimator名, `L_min`, 使用サイズ, seed, 収束状態, failureを標本行へ保存し、要約には要求標本数と失敗数を残す。`delta_P_max` とtransition `delta_p` は点推定自体がscaling-v2の対数OLSなので、そのbootstrapも対数OLSを維持する。simple/correctionモデルは別ラベルのまま扱う。

既存 `app/out/scaling-v3-analysis/` は上書きせず、修正確認を `app/out/scaling-v3-s-after-audit/` に生成した。

## 5. 修正前後の値

| 項目 | 修正前 | 同一推定量へ整合後 |
|---|---:|---:|
| point estimate | 1.772434446918 | 1.772434446918（変更なし） |
| bootstrap mean | 1.691557423379 | 1.774788166866 |
| bootstrap median | 1.691547706329 | 1.770750159898 |
| bootstrap 95% CI | [1.659604464307, 1.723396291278] | [1.636596173679, 1.940062151135] |
| fit failures / 500 | 0 | 0 |
| point estimate in CI | no | yes |

点推定、研究データ、AICc/BIC、`L_min` 系列は変更していない。変更したのは点推定へ対応づけるbootstrap区間と、その生成処理・ラベルである。

## 6. 他の観測量への影響

`C=1,2` の `P_before`, `P_after`, `S_before`, `S_after`, `std(p_mid)`, transition `delta_p`, `delta_P_max` の計14組を同じseed・500標本で監査した。旧区間から点推定が外れていたのは3組（`C=1 S_after`, `C=2 S_before`, `C=2 S_after`）で、同一推定量へ揃えた後は14組すべて点推定を含み、fit失敗は0だった。

主要な整合後区間は次の通りである。

| 条件 | 量 | 点推定 | 整合後95% CI |
|---|---|---:|---:|
| C=1 | P_before | 0.106997 | [0.092906, 0.120037] |
| C=1 | P_after | 0.104559 | [0.085716, 0.123933] |
| C=1 | S_before | 1.586319 | [1.440979, 1.766440] |
| C=1 | S_after | 1.772434 | [1.636596, 1.940062] |
| C=1 | std(p_mid) | 0.669957 | [0.619438, 0.720652] |
| C=2 | P_before | 0.117370 | [0.103927, 0.130509] |
| C=2 | P_after | 0.108595 | [0.092684, 0.126449] |
| C=2 | S_before | 1.590865 | [1.463514, 1.772335] |
| C=2 | S_after | 1.768067 | [1.616833, 1.935314] |
| C=2 | std(p_mid) | 0.667847 | [0.611793, 0.731183] |

対数OLSが点推定でもあるtransition `delta_p` と `delta_P_max` は修正前後で同じ区間になった。完全な一覧、run数、使用サイズ、旧CSV区間の再現値は `estimator_consistency_audit.csv` に保存した。

## 7. 研究結論への影響

`C=1 S_after` の点推定は変わらず、理論値 `gamma/nu=43/24` は整合後区間内にある。Pの点推定・理論指数固定モデルのAICc/BIC、疑似臨界点shift、UNBOUNDED解析も変わらない。このため「C=1は通常二次元パーコレーションを概ね再現する」という定性的結論は維持される。

整合後のC=1/C=2区間はP、S、`std(p_mid)` のすべてで重なる。したがって「C=2は同じ普遍クラスと整合的だが証明ではない」という分類も維持される。Sの区間は旧表示より広く、有限サイズ補正とestimator依存性への留保はむしろ明確になった。UNBOUNDEDの転移次数に関する結論への影響はない。

## 8. 再現コマンドとテスト

```powershell
python -m analysis.scaling_v3_audit --bootstrap-samples 500 --seed 20260720
python -m pytest analysis/tests
.\gradlew.bat test
.\gradlew.bat build
```

関連テストは、同じサイズ集合・`L_min`・観測列・estimatorラベルの保持、seed再現性、percentile、失敗数、入力DataFrame非変更、人工冪指数の復元を確認する。

## 9. SHA-256

旧生成物（監査前・未変更）:

- `finite_correction_fits.csv`: `570e5ae525e68e3100da80069ecb3491374b496be2fbb116a1d6f2d7c12d045b`
- `bootstrap_distributions.csv`: `edc4404ceab3b306e91af45c1cbfccb6ff43d82a911c71016f9238d8036f3c80`
- `bootstrap_intervals.csv`: `0dd111dc21f19367362d0602c21b2ca6d17dbb3f04eb487b16e1e22c2c7ad2cb`
- `request_event_runs.csv`: `a0e9d50b1d5f1ed92e8db06e6735c813441594150c35b18e54c3162a5801d719`
- `transition_width_runs.csv`: `f7d4af1297874fe3c2c55e8b20f0b63055d7b37c83aa7c6bead75b615242bed1`

新しい監査CSV:

- `estimator_consistency_audit.csv`: `7815996a5b4c195683ed6759fcac860d9d2787ce2dacbe762b49f844cd580fca`
- `s_after_bootstrap_audit.csv`: `c11c13df6115a8e5e66e4169448ff76cf0c4a9d32bddee3f42afd244542ee01c`

監査CSVは再生成可能なためGit管理しない。
