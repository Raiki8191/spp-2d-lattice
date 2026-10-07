# UNBOUNDED bootstrap訂正記録 — Phase 4F

2026年10月7日に、Phase 4で検出しPhase 4Rで影響評価した、UNBOUNDED主fitとbootstrap推定器の不一致を訂正した。この記録の不確実性評価を正式な訂正版とする。既存v3〜v7出力は当時の出力として保存し、raw simulation、manifest、run metadata、事前登録原本を変更していない。

## 問題と原因

旧`analysis/unbounded_model_comparison.py::_quick_models`は、zeroモデルをlog-scale OLSで推定した。一方、主fitはoriginal-scale RSSを最小化していた。旧finiteモデルも、指数の単一profile探索と無制約線形係数、負の極限に対するsoft penalty、返却時の非負clipを使用した。主fitが要求する正の振幅・上限10・極限[0,1]を共有せず、負振幅や範囲外振幅の解を許していた。共分散を計算せず`covariance_ok=True`としていた診断も訂正対象である。

この差はoptimizerの実装上の違いではなく、objective・残差尺度・モデル制約を含む推定量の違いだった。旧区間を主fitの信頼区間として使用できない。旧`scaling_v3._bootstrap_ub_models`も同型だった。

## corrected estimatorと再標本化

v4〜v7は主点推定とbootstrapの双方から`analysis.unbounded_model_comparison.fit_models`を呼ぶ。元のYに対する無重みRSS、bounded `curve_fit` TRF、全初期値から最小RSSを採用する規則、収束・共分散・境界診断を共有する。zeroモデル6初期値、finiteモデル15初期値、`maxfev=20,000`を保持した。

v3は`analysis.scaling_v3.fit_unbounded_models`を双方から呼び、当時の主fitの5／12初期値と`maxfev=5,000`を保持する。後のv4〜v7の仕様へ置き換えていない。全モデルで振幅a∈[10⁻¹²,10]、finite極限c∈[0,1]、power指数x∈[.001,5]、log指数q∈[.001,10]とした。

モデル式はzero-power `a L^(-x)`、finite-power `c + a L^(-x)`、zero-log `a (log L)^(-q)`、finite-log `c + a (log L)^(-q)`であり、正の指数は減衰を表す。

run単位、各Lの元run数を保持した独立再標本化、500標本、percentile 2.5%／97.5%を維持した。v4〜v7のseedは20260720に観測量indexを加え、最大jump／δp／δt/N²／std(p_mid)／p_afterは順に0／1／2／3／4である（v4は最初の4観測量）。v3はseed20260720の単一streamを使用し、有限Cの従来のdrawも同順序で消費してからUNBOUNDEDだけfitする。有限C成果物は再生成していない。

## 正式成果物と再現確認

正式成果物は次に新規生成した。旧出力を削除・上書きしていない。

- `app/out/unbounded-v4-bootstrap-corrected/`
- `app/out/unbounded-v5-bootstrap-corrected/`
- `app/out/unbounded-v6-bootstrap-corrected/`
- `app/out/unbounded-v7-bootstrap-corrected/`
- `app/out/scaling-v3-unbounded-bootstrap-corrected/`

v4〜v7の38,000 fitは、Phase 4Rの一時検算と推定値・RSS・AICc/BIC・保存した共分散診断を比較し最大差0だった。v3を含む42,000 fitすべてが収束し、宣言boundsを満たした。全CSVからpercentile区間を独立再計算した。共分散が有限であることは、パラメータが十分に識別できることを意味しない。

`python -m pytest analysis/tests`の検証済みsource版は**120 PASS、72.81秒**。同一入力・identity resampling、全bounds、旧負振幅反例、v7 δtの既知不一致、固定seed/draw、旧quick経路を正式CIへ使用しないこと、失敗診断・出力先保護・有限C経路不変を回帰検証した。CIが必ずpointを含むという一般条件は設けていない。

旧成果物・raw・保護対象の**1,823ファイル、2,118,899,437 bytes（約2.12 GB）**は訂正前snapshotとのSHA-256がすべて一致した。各訂正directoryの`correction_provenance.json`に実行条件、環境、入力hash、コードhashを保存した。

## v4〜v7最大request jumpの主要訂正値

| version | 主AICc/BIC最良 | 点推定指数 | 訂正95% CI |
| --- | --- | --- | --- |
| v4 | zero_log | 0.2516052674 | [0.203490089, 0.2984525234] |
| v5 | zero_log | 0.2525133093 | [0.2039083266, 0.3104369579] |
| v6 | zero_power | 0.07983731333 | [0.06359220017, 0.09497313055] |
| v7 | zero_power | 0.08135894317 | [0.06599911602, 0.09496388174] |

## v7主要値

指数の主点推定・bootstrap中央値・両側95% percentile区間は次のとおり。

| 観測量 | モデル | 主点推定 | 中央値 | 95% CI |
| --- | --- | --- | --- | --- |
| 最大request jump | zero_power | 0.081359 | 0.080735 | [0.065999, 0.094964] |
| 最大request jump | zero_log | 0.299479 | 0.297159 | [0.246842, 0.345731] |
| δt/N² | zero_power | 1.294867 | 1.290631 | [1.200262, 1.391556] |
| δt/N² | zero_log | 3.510320 | 3.501016 | [3.304039, 3.715058] |
| std(p_mid) | zero_log | 1.497824 | 1.514392 | [1.413023, 1.616829] |

最大request jumpのfinite極限は次のとおり。ゼロ境界頻度は`c≤10⁻⁸`の頻度であり、任意パラメータ境界の頻度と区別した。局所rhoは各fitの共分散に基づく極限–指数相関の中央値、標本間rhoは500推定値の相関である。

| モデル | 主極限 | 中央値 | 95% CI | ゼロ境界率 | 主fit rho | 局所rho中央値 | 標本間rho |
| --- | --- | --- | --- | --- | --- | --- | --- |
| finite_power | 5.57126e-15 | 7.63685e-17 | [3.44405e-23, 0.248045] | 66.8% | 0.999080 | 0.998960 | 0.899452 |
| finite_log | 1.46113e-20 | 8.38498e-20 | [5.10753e-23, 0.100025] | 95.0% | 0.999039 | 0.999035 | 0.895130 |

| モデル | パラメータ | 主点推定 | 中央値 | 95% CI |
| --- | --- | --- | --- | --- |
| finite_power | amplitude | 0.424598 | 0.418936 | [0.231874, 0.443790] |
| finite_power | decay_exponent | 0.081359 | 0.086462 | [0.070661, 0.367660] |
| finite_log | amplitude | 0.457121 | 0.455825 | [0.350187, 0.483245] |
| finite_log | decay_exponent | 0.299479 | 0.300126 | [0.251504, 0.393053] |

約0.248／0.100までの正のtailが残り、有限極限を排除できない。強い極限–指数相関と境界集中は識別の難しさを示す。区間下端が厳密には正でも、数値的ゼロ境界を物理的な正の極限検出と解釈しない。

v4〜v7の主点推定とpercentile区間の照合では、形式的に区間外となる残存箇所は以下の2件で、すべて極限パラメータの数値的ゼロ境界（値・区間端とも10⁻⁸未満）だった。指数・振幅の同型不整合は残っていない。

| version | 観測量 | モデル | 主極限 | 95% CI |
| --- | --- | --- | --- | --- |
| v4 | transition_delta_p | finite_power | 5.82465e-11 | [1.1239e-19, 3.58577e-11] |
| v7 | transition_delta_p | finite_log | 1.9918e-13 | [8.59587e-22, 3.13232e-14] |

上記2件はpoint・区間端とも同じゼロ境界判定内にあり、境界近傍のflatなfitでoptimizerが微小な異なる値へ接近することによる数値差として扱う。推定器の再不一致ではなく、pointのclipやCIの拡張は行っていない。

## AICc/BICと結論

主fit仕様は変更していない。v4〜v7の保存主fitに対するRSS・AICc/BICの意図しない変化はない。最大jumpの履歴は次のとおり。

| version | AICc最良 | AICc | BIC | zero-log−zero-power ΔAICc |
| --- | --- | --- | --- | --- |
| v4 | zero_log | -96.717644 | -97.826760 | -3.545575 |
| v5 | zero_log | -108.210578 | -108.914788 | -4.357884 |
| v6 | zero_power | -106.115401 | -106.478921 | 1.592922 |
| v7 | zero_power | -116.315871 | -116.385972 | 2.773259 |

zero-logからzero-powerへの順位移動はデータ追加と主fitに由来する。v7では比較した候補内でzero-powerが優勢だが、漸近ゼロの証明、有限極限排除、power/logの確定、転移次数の確定へ強めない。有限サイズでの急激なrequest-level変化という観測は維持される。

v4 δpについて、旧bootstrapの`c≈0.29`への移動や指数上限・負振幅を、宣言した正振幅モデルの不確実性・不安定性として解釈した記述を撤回する。それらは主モデル範囲外の別推定器の結果だった。訂正bootstrapはゼロ境界へ集中するが、それ自体をゼロ漸近の証明とはしない。小さい主減衰指数、L_min感度という別の限界は残る。

## unaffectedなものと事前登録

raw観測値、単一サイズのrun平均・標準偏差・その直接再標本化区間、主fit・AICc/BIC・LOO、固定点予測、点予測のMAE/RMSE、事前登録日時・Git履歴・入力hashはこの推定器訂正で変更しない。parametric identificationは主fitとGaussian生成仮定を使う別経路であり、旧quick推定器への直接依存はない。生成仮定に条件付けた率として扱う。

L=320／L=384の`docs/UNBOUNDED_L*_PREREGISTRATION.md`と`analysis/reference/unbounded_l*_preregistered_predictions.csv`は原本のまま保存した。訂正後区間の予測評価は**事後訂正解析**であり、原登録値を置き換えない。訂正directoryの`retrospective_prediction_scores.csv`は固定点予測を保持して歴史区間と訂正区間を並べる。

最大jumpの12比較で被覆変更0、Gaussian density順位変更0だった。ただしL256はモデルCI、L320／L384は残差を合成したPIであり、混在した2/3被覆を均一な名目95%予測校正の確認とは扱えない。区間・densityの数値は訂正対象であり、点予測が不変であることだけから区間がunaffectedとはしない。

## scaling-v3有限Cとsummary table

修正済みfinite-C S_afterとUNBOUNDEDは別経路である。有限条件関連12関数のAST不変と、実run-levelデータの2標本・FINITE/joint/shift92行（S_after16行）の旧コードとの厳密一致を確認した。既存finite-C成果物のhashは保持された。

`docs/tables/UNBOUNDED_SUMMARY.csv`の平均・SD/SEM・幅・event位置・S_peak・単一サイズjump平均CIは旧quickに依存しないため、ファイルをbyte単位で保持する。訂正前SHA-256との一致を確認した。`UNBOUNDED_MODEL_HISTORY.csv`は最大jumpのfiniteモデル8行のCI端16セルだけ訂正し、主極限・AICc/BIC・LOO・相関・boundary・順位などを変更しない。対応は以下のとおり。

| version | モデル | セル | 旧値 | 訂正値 |
| --- | --- | --- | --- | --- |
| v4 | finite_power | ci95_low | 5.6136954628722381e-06 | 6.0631112049751539e-19 |
| v4 | finite_power | ci95_high | 0.29727253553503757 | 0.29727193676971242 |
| v4 | finite_log | ci95_low | 3.7390233431923632e-07 | 1.3025138167167907e-21 |
| v4 | finite_log | ci95_high | 0.2922687929389306 | 0.29226839538526977 |
| v5 | finite_power | ci95_low | 2.683376548858653e-06 | 7.0058971505704167e-21 |
| v5 | finite_power | ci95_high | 0.2958264359300829 | 0.29582631138191345 |
| v5 | finite_log | ci95_low | 2.9444850595967612e-07 | 1.4762532025118005e-22 |
| v5 | finite_log | ci95_high | 0.29030997768460148 | 0.29031000578315364 |
| v6 | finite_power | ci95_low | 3.5448750195209762e-07 | 7.8396818778898764e-23 |
| v6 | finite_power | ci95_high | 0.2652990287867335 | 0.26529939459513097 |
| v6 | finite_log | ci95_low | 1.2446927740202214e-07 | 7.7738947346454495e-23 |
| v6 | finite_log | ci95_high | 0.2167619879593467 | 0.21676215496561349 |
| v7 | finite_power | ci95_low | 5.268735535473101e-07 | 3.44404704787548e-23 |
| v7 | finite_power | ci95_high | 0.2480449713419455 | 0.24804549549439403 |
| v7 | finite_log | ci95_low | 8.2983434241356793e-08 | 5.1075260127602576e-23 |
| v7 | finite_log | ci95_high | 0.1000158452208838 | 0.10002518030960122 |

修正前はbranch `main`、HEAD `b40df04cadd6f6e2c838bd7ce628bff6b59262fd`、git status/diffは空だった。commit/push・Git history変更は行っていない。未commitの修正を識別できるようcode hashを併記した。全実コマンド、HEAD、環境、原本保護、新成果物hashと照合結果は `app/out/unbounded-v7-bootstrap-corrected/audit_verification.json` に保存した。

## 再現方法と限界

同じproduction CLIで再現できる。すでに存在する出力directoryは上書きせず拒否するため、再検算には新しい出力先を指定する。大規模simulationは不要である。

```powershell
python -B -m analysis.unbounded_bootstrap_correction --version v7 --samples 500 --seed 20260720 --workers 4 --output app/out/unbounded-v7-bootstrap-corrected-reproduction
python -B -m analysis.unbounded_bootstrap_correction --version v3 --samples 500 --seed 20260720 --output app/out/scaling-v3-unbounded-bootstrap-corrected-reproduction
```

v4〜v6も`--version`と新出力先を変更する。同じrun数・seed・draw・主推定器を使用する。parallel処理はfitを別の推定量へ置き換えない。

この区間は各Lで独立にrunを再標本化する既存設計への条件付き訂正である。共通seedによるサイズ間共分散、model-form、L_min選択、有限サイズ系統誤差を含まない。共分散近似・percentile法だけで境界極限の厳密検定や転移次数判定を行わない。今回の修正完了は後続Phaseの研究結論監査を代替しない。
