# ゼミ発表用図一覧

対象baseline: 12fade220d65db716511527b0789b49fb52fc317。現行・訂正済みの既存図9枚から、日本語表示版を作成した。新しい科学的解析、simulation、fit、bootstrap、平均化、理論線追加は行っていない。

全9枚で、英語replayと元PNGの画素・SHAが完全一致し、日本語版と英語replayの数値配列、誤差棒、曲線、軸範囲、scale、ticks、系列style、axes位置が完全一致した。保護対象3,040ファイルの作業前後SHAは不変。日本語fontはMeiryo、missing glyph警告0。全9枚の目視確認もPASS。詳細は [scientific_identity_verification.json](scientific_identity_verification.json)、[visual_verification.json](visual_verification.json) を参照する。

今回のwrapperは [render_japanese_existing_figures.py](render_japanese_existing_figures.py)。CURRENTは現行の観測・点推定として使用できる図、CORRECTEDは監査で訂正された正式図。状態は、図が使用する観測・点推定・区間を区別して判断した。

## 図1

- 発表用日本語版: [figure_01_finite_P_scaling_ja.png](figure_01_finite_P_scaling_ja.png)
- 元図: [simple_vs_corrected_P_before_corrected.png](../scaling-v3-shared-exponent-figure-corrected/simple_vs_corrected_P_before_corrected.png)
- 元図の状態: **CORRECTED**。B7の理論指数固定simple曲線の描画欠落を修復した正式図。
- generating script: [analysis/scaling_v3.py](../../../analysis/scaling_v3.py) の create_figures（P_before枝）、_plot_finite_point_curves。訂正原図の記録は [generate_corrected_figures.py](../scaling-v3-shared-exponent-figure-corrected/generate_corrected_figures.py)。
- source CSV: [request_event_summary.csv](../scaling-v2-analysis/request_event_summary.csv)、[finite_correction_fits.csv](../scaling-v3-analysis/finite_correction_fits.csv)。run-level出典は [request_event_runs.csv](../scaling-v2-analysis/request_event_runs.csv)。
- observable / L / C: 最大request変化event直前のP_beforeのrun平均。L=8,12,16,24,32,48,64,96,128、C1/C2、各条件200run。
- axes / fit: 横軸L、縦軸P_before、両対数。scatter2組、保存curve4本、SEM/CIなし。既存AICc順上位2曲線/条件。C1は理論指数固定5/48と自由simple、C2は自由simpleとω2補正。モデルは aL^x と aL^x(1+bL^-ω)。
- 何を示しているか: 巨大連結成分の割合のサイズ依存と、保存fitによるC1/C2比較。
- 発表で説明する内容: C1のモデル論理を先に示し、simple指数0.106997と5/48を比較する。既存の理論指数固定曲線がある。
- 注意点: event直前量と固定p=pcのPは区別する。曲線の近さだけで指数一致・普遍性を確定しない。主解析は全経路を1requestとして削除する。
- 元論文との関係: Fig.2（PDF 2頁）のPと削除率、Fig.3（PDF 3頁）のFSSとの概念比較。ERネットワーク・N基準の論文と、正方格子・L基準の本図を区別する。

## 図2

- 発表用日本語版: [figure_02_finite_S_scaling_ja.png](figure_02_finite_S_scaling_ja.png)
- 元図: [simple_vs_corrected_S_before.png](../scaling-v3-analysis/figures/simple_vs_corrected_S_before.png)
- 元図の状態: **CURRENT（点推定図）**。旧bootstrap区間は使用しない。
- generating script: [analysis/scaling_v3.py](../../../analysis/scaling_v3.py) の create_figures（S_before枝）、_plot_finite_point_curves。
- source CSV: [request_event_summary.csv](../scaling-v2-analysis/request_event_summary.csv)、[finite_correction_fits.csv](../scaling-v3-analysis/finite_correction_fits.csv)。
- observable / L / C: 最大request変化event直前のS_beforeのrun平均。L8〜128の9サイズ、C1/C2、各条件200run。
- axes / fit: 横軸L、縦軸S_before、両対数。scatter2組、curve4本、SEM/CIなし。C1は自由simpleとω0.5補正、C2は自由simpleとω2補正。モデル形式は図1と同じ。
- 何を示しているか: 平均クラスターサイズの成長と、C1/C2の有限サイズ傾向。
- 発表で説明する内容: C1 simple指数1.586319、C2は1.590865。before/afterによる違いを図3と合わせて説明する。
- 注意点: **既存図には43/24理論線なし**。C1 S_beforeの訂正simple区間上端1.766440は参照43/24=1.791667を含まず、通常指数の完全再現とは言えない。高相関・固定ω依存があり、補正による理論値回復を示した図ではない。
- 元論文との関係: Fig.2(c,d)（PDF 2頁）のS、Fig.3（PDF 3頁）のFSSが背景。1辺削除の最大eventと全経路削除のrequest eventを区別する。

## 図3

- 発表用日本語版: [figure_03_finite_exponent_intervals_ja.png](figure_03_finite_exponent_intervals_ja.png)
- 元図: [finite_primary_bootstrap_ci.png](../scaling-v3-finite-bootstrap-corrected/finite_primary_bootstrap_ci.png)
- 元図の状態: **CORRECTED**。点推定器とbootstrap推定器を統一した正式区間図。
- generating script: [analysis/scaling_v3_finite_bootstrap_correction.py](../../../analysis/scaling_v3_finite_bootstrap_correction.py) の create_ci_figure(table, destination, samples=500, seed=20260720)。訂正生成CLIは実行せず、保存済み正式表を同関数へ渡した。
- source CSV: [finite_primary_corrected_table.csv](../scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)。正式sampleは [bootstrap_distributions.csv](../scaling-v3-finite-bootstrap-corrected/bootstrap_distributions.csv)。元集約はv2の [request_event_summary.csv](../scaling-v2-analysis/request_event_summary.csv)、[transition_width_summary.csv](../scaling-v2-analysis/transition_width_summary.csv)。
- observable / L / C: P_before/P_after/S_before/S_after/std(p_mid)/最大request変化/転移幅Δpの7パネル。C1/C2、L8〜128、L_min=8。24保存済みpoint/interval組。
- axes / fit: 横軸C条件、縦軸scaling exponent、linear。丸=simple、四角=選択済み固定ω補正。棒=収束・有効fitに条件付けた2.5–97.5 percentile。P/S/stdは元スケールbounded nonlinear multistart、jump/widthのsimpleは既存log OLS。第8枠は元の方法・制限注記。
- 何を示しているか: C1/C2の指数、不確実性、補正modelによる変化。
- 発表で説明する内容: C1 P_before/P_after/S_afterのsimple区間はordinary参照値と整合する一方、S_beforeとstd(p_mid)は参照値を含まない。内部標準のモデル論理と、数値の完全再現は別の問いである。
- 注意点: **既存図には理論線なし**。500draw、seed20260720、固定L_min/選択済みω条件付き。モデル選択・finite-size系統誤差・共通seedのサイズ間共分散を含まない。C1 S_before/ω0.5は451/500有効・49失敗。補正fitの高boundary頻度を精密指数の証拠としない。
- 元論文との関係: Fig.3（PDF 3頁）のFSSとの概念比較。論文Fig.3のC=Nと本図の有限C比較は直接同一の対象ではない。

## 図4

- 発表用日本語版: [figure_04_c1_c2_shared_exponent_ja.png](figure_04_c1_c2_shared_exponent_ja.png)
- 元図: [c1_c2_shared_exponent_corrected.png](../scaling-v3-shared-exponent-figure-corrected/c1_c2_shared_exponent_corrected.png)
- 元図の状態: **CORRECTED**。B7のU1独立C1/C2系列の欠落を修復した正式図。
- generating script: [analysis/scaling_v3.py](../../../analysis/scaling_v3.py) の create_figures（共有指数枝）、_plot_shared_exponent_series。
- source CSV: [universality_model_fits.csv](../scaling-v3-analysis/universality_model_fits.csv)。P_beforeかつconvergedの14保存行。
- observable / L / C: P_beforeの補正joint fit。C1/C2、元サイズL8〜128、L_min=8/16/32の各部分集合、固定ω感度はL_min=8。
- axes / fit: 横軸L_min、縦軸β/ν、linear。U1独立C1/C2、U2共通指数、U3共通指数・共通ω、U3固定ω=0.5/0.75/1/1.5/2の計9系列。既存5/48線を維持。誤差棒なし。
- 何を示しているか: 指数独立/共有の仮説と、L_min・固定ωによる変動。
- 発表で説明する内容: 共通指数候補の競争力と補正fitの不安定性。「同じ普遍クラスへ向かう可能性と整合的」という支持範囲まで説明する。
- 注意点: **P_beforeの点推定図であり、joint CI図ではない**。正式U3区間はω1のみで、他ω・L_min16/32へ転用できない。高相関・boundary・小点数を省かず、普遍性の証明としない。
- 元論文との関係: Fig.2/3（PDF 2/3頁）のFSSを背景とする本研究の有限C比較。ERの結果を格子へ移す根拠とはしない。

## 図5

- 発表用日本語版: [figure_05_max_change_scaling_ja.png](figure_05_max_change_scaling_ja.png)
- 元図: [maximum_request_jump_size_dependence.png](../unbounded-v7/figures/maximum_request_jump_size_dependence.png)
- 元図の状態: **CURRENT**。観測mean/SEM・保存point fitだけを使い、旧bootstrap区間を使わない。
- generating script: [analysis/unbounded_v7.py](../../../analysis/unbounded_v7.py) の create_figures（size dependence先頭枝）。正式captionは [figure_captions.csv](../unbounded-v7/figure_captions.csv)。
- source CSV: [unbounded_size_summary.csv](../unbounded-v7/unbounded_size_summary.csv)、[unbounded_model_fits.csv](../unbounded-v7/unbounded_model_fits.csv)。
- observable / L / C: 最大request変化ΔP。L=8,12,16,24,32,48,64,96,128,192,256,320,384、UNBOUNDED（C=N=L²）。計2,310主run、L256/320/384は各20run。
- axes / fit: 横軸Lはlog、縦軸最大変化はlinear。run平均±SEM。4保存モデル: aL^-x、c+aL^-x、a(log L)^-x、c+a(log L)^-x。元スケール無重みRSSのbounded multistart。既存曲線gridはL8〜1536の300点。384以降は補外、最大観測L縦線も元のまま。
- 何を示しているか: 有限Lで大きいrequest変化が残り、漸近候補の区別が難しいこと。
- 発表で説明する内容: 現行候補・規準ではzero-familyが相対的に支持され、v7ではzero-power優勢。ただし減衰は遅く、転移次数は未確定。
- 注意点: 「有限値へ収束」はc≥0のfamily名で、正の極限の確定ではない。finite pointはゼロ境界付近。補外は観測ではない。最大1request変化のゼロ極限だけでP(p)全体の連続性は証明しない。
- 元論文との関係: Fig.2(a)（PDF 2頁）の急峻性を漸近仮説で補足する本研究の図。論文Fig.2〜5に同一の4モデル比較はない。1辺eventとrequest eventの定義差を保持する。

## 図6

- 発表用日本語版: [figure_06_corrected_finite_limit_ja.png](figure_06_corrected_finite_limit_ja.png)
- 元図: [corrected_finite_limit_distributions.png](../unbounded-v7-bootstrap-corrected/figures/corrected_finite_limit_distributions.png)
- 元図の状態: **CORRECTED**。Phase4Fでpointと同じ推定器へ統一した正式分布。
- generating script: [analysis/unbounded_bootstrap_correction.py](../../../analysis/unbounded_bootstrap_correction.py) の correction_figures（finite-limit CDF先頭枝）。保存sampleのみ使用。
- source CSV: [unbounded_bootstrap_samples.csv](../unbounded-v7-bootstrap-corrected/unbounded_bootstrap_samples.csv)。正式区間は [unbounded_bootstrap_intervals.csv](../unbounded-v7-bootstrap-corrected/unbounded_bootstrap_intervals.csv)。
- observable / L / C: 最大request変化と転移幅Δpのfinite-power/finite-log極限parameter。UNBOUNDED、L8〜384、L_min=8、complete-run bootstrap500draw。
- axes / fit: 2panel、横軸有限極限c、縦軸bootstrap経験累積割合、linear。保存sampleの既存CDF描画。新fit・再標本化なし。
- 何を示しているか: 境界集中と広い不確実性。
- 発表で説明する内容: 最大request変化の有限極限区間上限はpower約0.248045、log約0.100025で、有限極限を排除できない。
- 注意点: 境界集中は真のゼロ極限の証明ではない。percentileは固定model・L_min条件付きで、model-form/finite-size系統誤差を含まない。旧quick-bootstrap精度を混ぜない。
- 元論文との関係: 原論文Fig.2〜5に同一CDFはない。本研究の漸近仮説比較の不確実性を補足する。

## 図7

- 発表用日本語版: [figure_07_transition_width_p_ja.png](figure_07_transition_width_p_ja.png)
- 元図: [transition_delta_p_size_dependence.png](../unbounded-v7/figures/transition_delta_p_size_dependence.png)
- 元図の状態: **CURRENT**。
- generating script: [analysis/unbounded_v7.py](../../../analysis/unbounded_v7.py) の create_figures（Δp size dependence枝）。captionは [figure_captions.csv](../unbounded-v7/figure_captions.csv)。幅定義は [analysis/transition_width.py](../../../analysis/transition_width.py) の calculate_transition_widths。
- source CSV: [unbounded_size_summary.csv](../unbounded-v7/unbounded_size_summary.csv)、[unbounded_model_fits.csv](../unbounded-v7/unbounded_model_fits.csv)。
- observable / L / C: Δp、UNBOUNDED、図5と同じL8〜384の13サイズ。
- axes / fit: 横軸Lはlog、縦軸Δpはlinear。run平均±SEMと保存4モデル。既存L8〜1536の曲線・最大観測L縦線を維持。
- 何を示しているか: 巨大成分から小さい成分へ変わる削除率の幅とサイズ依存。
- 発表で説明する内容: 保存状態でP>0.5の最後のpをp₂、P>1/Lの最後をp₁、Δp=p₁−p₂。pは削除率、occupation fractionは1−p。
- 注意点: 狭い幅・有限サイズの急峻性だけで不連続転移と判定しない。閾値と保存状態の定義を説明する。
- 元論文との関係: **Fig.5(a)（PDF 4頁）への対応図**。論文横軸Nと本図L（N=L²）の指数を同じ数値のまま比較しない。

## 図8

- 発表用日本語版: [figure_08_transition_width_time_ja.png](figure_08_transition_width_time_ja.png)
- 元図: [transition_delta_t_normalized_size_dependence.png](../unbounded-v7/figures/transition_delta_t_normalized_size_dependence.png)
- 元図の状態: **CURRENT**。
- generating script: [analysis/unbounded_v7.py](../../../analysis/unbounded_v7.py) の create_figures（normalized request width枝）。caption・幅定義は図7と同じ。
- source CSV: [unbounded_size_summary.csv](../unbounded-v7/unbounded_size_summary.csv)、[unbounded_model_fits.csv](../unbounded-v7/unbounded_model_fits.csv)。
- observable / L / C: Δt/N²=(t₁−t₂)/L⁴、UNBOUNDED、L8〜384の13サイズ。
- axes / fit: 横軸Lはlog、縦軸Δt/N²はlinear。run平均±SEMと保存4モデル。既存L8〜1536の曲線・最大観測L縦線を維持。
- 何を示しているか: 削除率と要求数による時間表現の違い。
- 発表で説明する内容: tはaccepted数でなくrejectも含む総request counter。
- 注意点: 幅は**保存accepted状態のstep**から取る。counterはrejectを含むが、全reject plateau末端の保存はないため、論文の全request時刻の最大値による幅との完全一致は保証しない。幅縮小だけで転移次数を確定しない。
- 元論文との関係: **Fig.5(b)（PDF 4頁）への対応図**。Fig.4（PDF 3頁）のp対tを背景に、reject待ち時間を説明する。

## 図9

- 発表用日本語版: [figure_09_small_lattice_transition_ja.png](figure_09_small_lattice_transition_ja.png)
- 元図: [L=16_largest_cluster_fraction_vs_removed_edge_fraction.png](../sweep-pilot/figures/L=16_largest_cluster_fraction_vs_removed_edge_fraction.png)
- 元図の状態: **CURRENT（小格子pilot観測）**。Phase5でraw/run集約の独立照合済み。最新多L本解析を表す図ではない。
- generating script: [analysis/plot_smoke.py](../../../analysis/plot_smoke.py) の create_plots。
- source CSV: [manifest.csv](../sweep-pilot/manifest.csv)、[C1 results.csv](../sweep-pilot/L=16/C=1/results.csv)、[C2 results.csv](../sweep-pilot/L=16/C=2/results.csv)、[UNBOUNDED results.csv](../sweep-pilot/L=16/C=256/results.csv)。
- observable / L / C: 初期状態と保存されたrequest後の巨大連結成分割合P。L=16、C1/C2/UNBOUNDED（C=N=256）、各10run、全30系列。
- axes / fit: 横軸削除率p、縦軸P、linear。元のaccepted-state座標間の直線接続を維持。run曲線を平均化せず、fit・理論線・誤差棒なし。
- 何を示しているか: モデルを直感的に紹介する小格子でのC依存とrun変動。
- 発表で説明する内容: C1/C2に対し経路長制限なしでは、一度のrequestで全経路を削除し大きいP変化が生じる例を説明する。
- 注意点: 記録済み範囲の曲線であり、tail完全性をこの図から主張しない。直線接続は記録状態間の描画規約で、途中の物理状態を生成したものではない。L16単独・pilot30runから熱力学極限の転移次数や最新複数L傾向を判断しない。
- 元論文との関係: Fig.2(a)（PDF 2頁）のP対pを背景にした、格子SPPモデルの観測導入。最新多L主結果の直接対応図ではない。

## 元論文との比較条件

原論文は *Shortest-Path Percolation on Random Networks*。repo内に指定名PDFは見つからなかったため、著者公開の [出版版PDF](https://homes.luddy.indiana.edu/filiradi/Mypapers/PhysRevLett.133.047402.pdf) を参照した。論文画像は編集していない。

| 論文図 | PDF頁 | 内容 | 発表図との関係 |
|---|---:|---|---|
| Fig.2 | 2 | P対p、C依存、擬臨界点対N、S対p | 背景と図9・図1〜4 |
| Fig.3 | 3 | C=Nの再スケール擬臨界P/S分布・データ崩壊 | 図1〜4のFSS概念比較 |
| Fig.4 | 3 | p対要求数t、tのN再スケーリング、擬臨界/解体要求数 | 図8の時間表現の背景 |
| Fig.5 | 4 | Δp対N、正規化時間幅対N、べき乗fit | 図7・8の直接的比較対象 |

Fig.5のp₂,t₂はP>0.5を満たす最大値、p₁,t₁はP>1/√Nを満たす最大値。Δp=p₁−p₂、Δt̃=(t₁−t₂)N^-2。閾値以下への初到達、accepted数、保存accepted-state stepによる幅を無条件に同一視しない。論文は平均次数4のER、本研究はopen boundaryの二次元正方格子。論文サイズNと本研究LはN=L²の関係。論文event-based ensembleは1辺削除の最大変化、本研究主eventは1requestの全経路削除。Fig.5の急峻性議論をそのまま格子SPPの転移次数結論に用いない。

## 採用しなかった図

- v3旧 c1_c2_shared_exponent.png / simple_vs_corrected_P_before.png: B7の描画欠落があるためSUPERSEDED。図1・4を使用。
- v3旧 bootstrap_exponent_distributions.png: 点と異なる旧bootstrap推定器を含みSUPERSEDED。図3を使用。
- v7旧 finite_limit_bootstrap.png / decay_exponent_bootstrap.png と旧bootstrap依存予測・補外区間図: 旧quick bootstrapに依存。図6を使用。
- v4〜v6点モデル図: そのサイズ範囲ではCURRENTでも最新v7を優先。旧uncertaintyと当時の解釈を主結果に混ぜない。
- 原preregistration予測区間図: HISTORICALな事前証拠。事後訂正bootstrapで遡及置換せず、今回主図には採らない。
- v2 finite_P_vs_L.png / finite_S_vs_L.png: mean±SEMはCURRENTだが、linear軸・UNBOUNDED込み6系列。今回は有限C log scalingと正式区間を優先。系列削除による別図は作らない。
- request-analysisのL8/12/16図、scaling-v1単独C1図: 小規模/以前のサイズ範囲の比較で、最新有限C L≤128を優先。
- L16以外の旧pilot図: 今回の9図に加えず、図9をモデル導入として選定。図9も最新複数L主解析の代用ではない。
- exact_mean_P_vs_p / order-checkのP(p): edge-level副解析。request-level急転移主図へ置き換えない。
- 局所指数、joint残差、LOO、L_min全感度、計算費用、model順位移動: 詳細検証では有用だが、約1時間の主発表では方法説明量が多く今回の主図から外した。

## 適切な既存図が存在しなかった項目

- **NOT FOUND — C: 最新本解析の複数L UNBOUNDED request-level P(p)**。既存PNG・plot code・指定出力を探索した範囲で適合図がなかった。新raw解析・平均化は行わない。図9は単Lpilot導入、図5は最大request変化の漸近図であり、どちらも複数L P(p)主図の代用とは扱わない。
- **NOT FOUND — P_after/S_afterの訂正joint CIを直接表示する既存図**。訂正CSVは存在するが新しい図は設計しない。図3の条件別primary区間をjoint共通指数CIと取り違えない。
- 今回採るS scaling図に43/24理論線はない。理論値は説明文で比較し、線を追加しない。

## 約1時間の推奨発表順

1. 背景・モデル・論文Fig.2→図9（8分）。ER/格子、p/1−p、request/edgeを区別。
2. 図1→図2→図3（15分）。C1内部標準、数値再現の支持範囲、before/after、訂正区間。
3. 図4（8分）。C2共通指数候補と未確定点。
4. 図5→図6（15分）。UNBOUNDED最大request変化、漸近4モデル、訂正uncertainty。
5. 論文Fig.4・Fig.5→図7→図8（10分）。幅と総request時間、reject plateau・保存状態の比較制限。
6. 現在の支持範囲と残る問い（4分）。C2普遍性・UNBOUNDED転移次数の未確定性を保持。

## 来歴・同一性確認

- 状態判断: [最終研究監査](../../../docs/FINAL_RESEARCH_AUDIT.md)、[解析監査訂正台帳](../../../docs/ANALYSIS_AUDIT_CORRECTIONS.md)、[UNBOUNDED訂正記録](../../../docs/UNBOUNDED_BOOTSTRAP_CORRECTION.md)。
- 既存正式図のSHA・過去独立replay: [figure_provenance.csv](../final-research-audit/evidence/phase16-data/figure_provenance.csv)。
- 今回の数値一致: [scientific_identity_verification.json](scientific_identity_verification.json)、[plot_numeric_arrays.json](plot_numeric_arrays.json)。
- 翻訳文字列: [label_translations.json](label_translations.json)。
- 保護原本SHA: [protected_file_sha256.json](protected_file_sha256.json)。
- 目視QA: [visual_verification.json](visual_verification.json)。
- 変更は表示文字列と翻訳文字の日本語fontのみ。科学的数値・軸・系列・原図・正式CSV・raw・metadata・manifest・preregistration・production sourceは不変。commit/pushなし。

再描画・検証の実行コマンド（更新先はこのseminarディレクトリのみ）:

```powershell
python -B app/out/seminar-progress-2026-10-07/render_japanese_existing_figures.py --refresh-labels
```

この入口は既存のplot関数へ保存CSVを渡し、不要な作図枝へ進む前に終了する。`run_analysis`/訂正生成CLIは呼ばない。英語replayは一時領域に保存し、元PNGとの画素/SHAを確認する。元図・入力・production sourceへの書き込みは行わない。
