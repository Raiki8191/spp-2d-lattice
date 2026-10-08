# 既存9図の再監査

基準HEAD: 12fade220d65db716511527b0789b49fb52fc317。今回の指示は表示文字以外の再描画・系列整理を許可する。正式解析の推定器・L_min・fit・bootstrapは変更せず、元CSVと原図を保全する。監査はTask 1、図セット決定はTask 2、再描画はTask 3の順で進める。

| 図 | 元ファイル | 元データ | 目的 | 科学的妥当性 | 見やすさ・問題点 | 必要な修正 | 分類 |
|---|---|---|---|---|---|---|---|
| 1 | [元図](../scaling-v3-shared-exponent-figure-corrected/simple_vs_corrected_P_before_corrected.png) | v2 request_event_summary.csv / v3 finite_correction_fits.csv | イベント直前Pのサイズ依存・C比較 | CORRECTED。log-logと保存fitは妥当 | 前後の文脈不足、色とfitの対応が不明瞭、4曲線が過密 | イベント直前/直後2パネル、C別色、全Lの平均±保存SEM、simplefitとC1の保存理論指数固定fit | REPLACE → MAIN |
| 2 | [元図](../scaling-v3-analysis/figures/simple_vs_corrected_S_before.png) | 同上 | Sの有限サイズ傾向 | CURRENT点図。Sは最大成分を同率でも1個除外したΣs²/Σs | 算術平均との混同、beforeだけでafterとの違いを隠す | 平均有限クラスターサイズ、前後2パネル、各Cの保存simplefitに統一 | SUPPLEMENT |
| 3 | [元図](../scaling-v3-finite-bootstrap-corrected/finite_primary_bootstrap_ci.png) | finite_primary_corrected_table.csv | 訂正指数区間とC1/C2比較 | CORRECTED。point/bootstrap推定器一致 | 7量・単純/補正混在、参照値なし、文字が小さい | P/S前後とstd(p_mid)の5量・simpleのみ。既知参照値を明示。省略対象と条件付き区間を記録 | REPLACE → MAIN |
| 4 | [元図](../scaling-v3-shared-exponent-figure-corrected/c1_c2_shared_exponent_corrected.png) | universality_model_fits.csv | 共通指数と補正感度 | CORRECTED診断図。14収束fit中6は境界/数値的非採用 | 内部名9系列、固定ω点重なり、境界と採用可能解が同じ見せ方 | L_min感度と固定補正設定感度の2パネル。全点・負指数保持、非採用点に×、自然語凡例 | SUPPLEMENT |
| 5 | [元図](../unbounded-v7/figures/maximum_request_jump_size_dependence.png) | unbounded_size_summary.csv / unbounded_model_fits.csv | 最大request変化と4漸近候補 | CURRENT平均SEM/点fit。13L・2310試行 | finiteはc=0を含むが凡例が正の極限の検出に読める。外挿混在 | 極限c≥0を許すモデル、今回c≈0、全4曲線、同法則の色/線種統一、外挿背景、縦軸0始まり | REPLACE → MAIN |
| 6 | [元図](../unbounded-v7-bootstrap-corrected/figures/corrected_finite_limit_distributions.png) | 訂正unbounded_bootstrap_samples.csv / intervals.csv | 極限parameterの再標本化不確実性 | CORRECTED、各CDF500標本 | Δpの10^-13程度の境界内差が物理的正極限に見える。CDFを真の極限の確率と誤読 | 2パネル/全標本維持。候補モデルparameterと明記。Δpは全標本c≤10^-8の数値ゼロ境界内と注記 | SUPPLEMENT |
| 7 | [元図](../unbounded-v7/figures/transition_delta_p_size_dependence.png) | v7 summary / fits | 削除率の転移幅 | CURRENT。保存受理状態のP>0.5/P>1/L最後のpの差 | 小Lの山を単調4候補は再現しない。外挿/finite表現の問題 | 閾値・削除率・N=L²を注記、全観測点/4fit維持、外挿明示、縦軸0始まり | REPLACE → MAIN |
| 8 | [元図](../unbounded-v7/figures/transition_delta_t_normalized_size_dependence.png) | v7 summary / fits | 保存受理状態の総要求時間幅 | CURRENT。tはrejectも含む総request counter | linearYで大L点が潰れる。論文の全request plateau終端定義とは異なる | log-logへ変更(全13点のmean−SEM>0)。保存元スケールfitは変更せず、Δt/N²=Δt/L⁴と記録時刻の差を明記 | REPLACE → MAIN |
| 9 | [元図](../sweep-pilot/figures/L=16_largest_cluster_fraction_vs_removed_edge_fraction.png) | sweep-pilot manifest / L16 C1,C2,C256 results.csv | 小格子のモデル・request変化導入 | CURRENT物理観測。L16各C10試行。単Lpilot | 30凡例が過密、巨大成分という用語、線の途中を物理状態に誤読 | 全30曲線/全行保持、凡例3条件のみ、最大連結成分、pilot/開放境界/pを注記 | REPLACE → MAIN |

## 数値と定義の照合

- 有限Cは18条件×200＝3600既存試行からP/Sの72平均・SEMを独立照合。平均差最大2.842170943040401e-14、SEM差最大1.4210854715202004e-14（丸め範囲）。simple10点と元fitの差最大2.220446049250313e-16。
- C1のP直前/直後simple区間は5/48、S直後は43/24を含む。S直前上限1.766440は43/24=1.791667を含まない。std(p_mid)上限0.720652は3/4を含まない。全部再現したとは述べない。
- C2は近い有限サイズ傾向。普遍性クラスの断定を避け、同じクラスへ向かう可能性と整合的とする。
- v7と訂正dirのpointfit全表は同じ。3量×13平均39セルはdocs/tablesの正式表と一致、L384の平均/SEM6セルはfinal_valuesと一致。tiny cの再serialization差最大2.524e-29は丸めで発表値への影響なし。
- UNBOUNDEDはL8..384の13条件、2310主試行。zero-power対zero-logのAICc差2.773。有限極限区間上限power0.2480455/log0.1000252。正の有限極限・転移次数は未確定。
- ΔpはL8で0.272902、L32で0.304738、L384で0.230410。全域単調減少ではない。小Lの山と保存単調fitの不一致を隠さない。
- 訂正CDFは4系列各500標本。Δpの1000標本は全て既存の数値的ゼロ判定c≤1e-8以内。極限差の検出として扱わない。

## 用語・比較のルール

Pは最大連結成分の頂点割合。Sは最大成分を同率でも1個だけ除外した頂点重み付き平均有限クラスターサイズ。最大変化イベントは1回の受理requestによる全経路削除で選ぶ。固定p=pcの測定とは区別する。

二次元正方格子は開放境界（反対側の端を接続しない）、N=L²、M₀=2L(L−1)、p=削除辺数/M₀。通常の占有率は1−p。元論文のER/辺単位event/N横軸との違いを保持する。L^-x=N^(-x/2)。要求数tにはrejectも含むが、幅の保存受理状態時刻は全request plateau末端時刻とは異なる。

## 修正範囲と判定

図の解釈・ラベル・凡例・密度に関する問題を自律的に修正する。生データ・正式pointfit/区間・preregistration・production sourceの不整合は今回の照合では発見していない。元9PNGは保持し、全9図を別revised_figuresへ再描画する。完全なDROPは0枚。旧図1/3/5/7/8/9の見せ方はREPLACE、旧図2/4/6は補足用途に限定する。

## 確認した主要記録

[元選定一覧](seminar_figure_selection.md)、[最終監査](../../../docs/FINAL_RESEARCH_AUDIT.md)、[解析訂正台帳](../../../docs/ANALYSIS_AUDIT_CORRECTIONS.md)、[V3](../../../docs/SCALING_V3_RESULTS.md)、[V4](../../../docs/UNBOUNDED_V4_RESULTS.md)、[V5](../../../docs/UNBOUNDED_V5_RESULTS.md)、[V6](../../../docs/UNBOUNDED_V6_RESULTS.md)、[V7](../../../docs/UNBOUNDED_V7_RESULTS.md)、[tables案内](../../../docs/tables/README.md)、[正式finite表](../scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)、[shift表](../scaling-v3-analysis/pseudocritical_shift_corrections.csv)、[最終数値](../final-research-audit/evidence/phase16-fit/final_values.csv)。
