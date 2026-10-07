# 卒論表の出典と状態

全研究の判定と卒論で使用する主要値は[最終研究監査報告](../FINAL_RESEARCH_AUDIT.md)、訂正の来歴は[解析監査台帳](../ANALYSIS_AUDIT_CORRECTIONS.md)、物理量の定義は[ANALYSIS_DEFINITIONS.md](../ANALYSIS_DEFINITIONS.md)を参照する。ここにある2 CSVは保存済み表であり、Phase 16では変更していない。

| 状態 | 使用方法 |
|---|---|
| CURRENT | 検算済みの現行点推定・観測集約として使用する。 |
| CORRECTED | 指定された旧derived区間の代わりに使用する。 |
| SUPERSEDED | 現行の科学的根拠として使用しない。旧値は歴史的比較のため保存する。 |
| HISTORICAL | 当時の分析・事前予測として引用する。事後訂正を元の予測へ置き換えない。 |

## UNBOUNDED_SUMMARY.csv

[UNBOUNDED_SUMMARY.csv](UNBOUNDED_SUMMARY.csv)はL=8〜384の13条件・2,310 main runsのrequest-level観測集約（CURRENT）。audit runは同seed履歴の停止延長検証であり、この標本数へ追加しない。各行の`source`と`analysis_version`からrun-derived・condition summaryの保存元を追跡できる。

| 列 | 意味と出典 |
|---|---|
| maximum_request_jump_mean / sd / sem | runごとの最大request jumpを条件内集約。sdは標本標準偏差（ddof=1）、sem=sd/√runs。 |
| maximum_request_jump_bootstrap_ci95_low / high | 条件内run meanの直接bootstrap percentile区間。5,000 draw・seed 20260720。modelの漸近fit区間とは別。 |
| transition_delta_p | 保存されたaccepted状態列の閾値幅のrun平均。p=removed edges / initial edges。 |
| transition_delta_t_normalized | 保存accepted状態列のstep閾値幅 / N²。stepにはrejectも含むが、全request plateau終端を記録した幅とは異なる。 |
| request_event_p_after / std_p_mid | 最大request jump eventの削除後座標の平均 / midpoint座標の標本標準偏差。通常のoccupation probabilityはq=1−p。 |
| S_peak | 保存状態列のrunごとのS最大値の平均。ensemble mean Sのpeakや最大jump eventでのSとは別。 |

raw→run-derived→summaryの独立検算は[Phase 11 data](../../app/out/final-research-audit/evidence/phase11-data/)と[Phase 12〜15 evidence](../../app/out/final-research-audit/evidence/)、13条件の直接mean-bootstrap再計算は[Phase 15 semantic](../../app/out/final-research-audit/evidence/phase15-semantic/)。同seedのL間対応があり、13条件を独立に増えた標本として数えない。

## UNBOUNDED_MODEL_HISTORY.csv

[UNBOUNDED_MODEL_HISTORY.csv](UNBOUNDED_MODEL_HISTORY.csv)はv4/v5/v6/v7各4候補の16行。各versionの入力上限はそれぞれL=192/256/320/384で、古いversionの順位はHISTORICAL、対応する保存点fit・RSS由来のscore・LOO値はそのversionの数値としてCURRENT。全行が最新L≤384のfitを表すわけではない。

| 列 | 現行の出典・注意 |
|---|---|
| model / aicc / bic / loo_mae / loo_rmse / limit | [v4 main50](../../app/out/unbounded-v4/main50/)、[v5](../../app/out/unbounded-v5/)、[v6](../../app/out/unbounded-v6/)、[v7](../../app/out/unbounded-v7/)の保存点fit・LOO。点推定・score・LOOはPhase 4F訂正で変更していない。 |
| ci95_low / ci95_high | finite 8行・16セルはPhase 4FのCORRECTED値。[v4](../../app/out/unbounded-v4-bootstrap-corrected/unbounded_bootstrap_intervals.csv)、[v5](../../app/out/unbounded-v5-bootstrap-corrected/unbounded_bootstrap_intervals.csv)、[v6](../../app/out/unbounded-v6-bootstrap-corrected/unbounded_bootstrap_intervals.csv)、[v7](../../app/out/unbounded-v7-bootstrap-corrected/unbounded_bootstrap_intervals.csv)のmaximum request jump・parameter cと照合する。 |
| max_parameter_correlation / boundary_solution | 既存bounds・局所optimizerの診断。boundaryや非識別性を精密な漸近指数・limitの証明として扱わない。 |
| aicc_rank / conclusion_classification | 比較した候補・既存制約・同一入力に限定した順位と解釈。熱力学極限の転移次数の証明ではない。 |

zero-familyのlimit=0、区間[0,0]はモデル固定値であり、データが有限極限0を誤差なく確定した意味ではない。finite-familyのごく小さい正の区間下端は、既存c≤10⁻⁸の数値ゼロ診断と区別する。literal下端>0だけから非零極限検出と主張しない。

現行v7 finite-limit cのpercentile範囲は、finite-powerが約[3.444047×10⁻²³, 0.2480455]、finite-logが約[5.107526×10⁻²³, 0.1000252]。保存bounds・収束/有効fitに条件付けた範囲であり、model form・L_min・共有seed covariance・系統誤差を全て含む無条件95%保証ではない。旧quick-bootstrap区間はSUPERSEDED。新しい履歴比較出力は[maximum_jump_model_history.csv](../../app/out/unbounded-history-bootstrap-corrected/maximum_jump_model_history.csv)。

有限サイズの強い急激さは観測事実。最新の比較候補ではzero-powerが相対的に支持されるが、finite極限を排除できず、power/log則も確定できない。最大request jump→0の候補が有利でも、全P(p)の熱力学極限の連続性が証明されたことにはならない。

## 原登録と事後訂正

L=320/384の元preregistration MDと`analysis/reference`の固定予測CSVはHISTORICALな事前証拠として不変。元点予測/予測区間で観測をscoreし、事後訂正区間と明確に区別する。訂正bootstrapを元の事前登録区間として使用しない。[UNBOUNDED_BOOTSTRAP_CORRECTION.md](../UNBOUNDED_BOOTSTRAP_CORRECTION.md)と[Phase 14](../../app/out/final-research-audit/evidence/phase14-semantic/)/[Phase 15](../../app/out/final-research-audit/evidence/phase15-semantic/)にGit addition-only履歴・元blob/working file・実験UTC時刻・scoreの証拠がある。

L=384元CSVのgeneration timestampはsource commitのcommitter timeで、実際の生成時計ではない。現在のGit・保存metadataの順序が事前性と整合することと、外部認証された時刻証明とは区別する。
