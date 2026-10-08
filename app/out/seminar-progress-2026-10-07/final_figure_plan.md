# 最終発表図セット

対象baseline: 12fade220d65db716511527b0789b49fb52fc317。本編6図・補足3図を採用する。既存9図を出発点とし、正式な観測集約・保存fit・訂正済み区間から発表用に再描画する。元図、raw、正式CSV、production解析コード、事前登録原本は保持する。科学的根拠の確認は[revision_audit.md](revision_audit.md)、生成後の確認は[revised_figures_verification.md](revised_figures_verification.md)を参照する。

以下はスライド構成案であり、PowerPointファイルの作成を意味しない。図番号は前回の9図と共通にする。最終PNGと同stemのPDFを revised_figures/ に保存する。

## 本編：6図

| 発表順 / 元番号 | 使用するスライド | 最終PNG / PDF | 説明する内容 | 話す際の注意 |
|---|---|---|---|---|
| M1 / 図9 | 5：モデルの観測例 | [PNG](revised_figures/figure_09_small_lattice_transition_ja.png) / [PDF](revised_figures/figure_09_small_lattice_transition_ja.pdf) | L=16・開放境界でのP–p曲線。3条件各10試行を全て残し、凡例は3条件へ整理する。 | 単Lのpilot導入。平均曲線・最新複数L主結果・転移次数の証明として扱わない。記録状態間の直線は描画規約。 |
| M2 / 図1 | 7：C=1内部標準とPのサイズ依存 | [PNG](revised_figures/figure_01_finite_P_scaling_ja.png) / [PDF](revised_figures/figure_01_finite_P_scaling_ja.pdf) | 最大変化イベント直前/直後のPを2パネルに分ける。C1/C2の全9サイズ、既存の平均±標準誤差、保存simple fit、既存C1理論指数固定fitを表示する。 | 固定p=pcのPとは異なるイベント条件付き量。理論固定曲線の近さだけで全指数の再現を断定しない。 |
| M3 / 図3 | 8：C=1の支持範囲とC=2との比較 | [PNG](revised_figures/figure_03_finite_exponent_intervals_ja.png) / [PDF](revised_figures/figure_03_finite_exponent_intervals_ja.pdf) | P前後、S前後、擬臨界点midpointの標準偏差の5量。正式simple点推定・500再標本化区間とordinary参照値を比較する。 | P前後・S後は参照を含む一方、S前・stdは含まない。有限サイズの有効指数。C2は同じ普遍性クラスへ向かう可能性と整合的という範囲に留める。 |
| M4 / 図5 | 9：経路長制限なしの最大変化量 | [PNG](revised_figures/figure_05_max_change_scaling_ja.png) / [PDF](revised_figures/figure_05_max_change_scaling_ja.pdf) | 全13サイズの平均±標準誤差と保存4モデル。縦軸0起点、横軸log L。L>384を外挿として区別する。 | finite-familyはc≥0でゼロも含む。今回c≈0の境界fitであり、正の極限の確定ではない。最大jumpの消失候補が有利でも熱力学的転移次数は未確定。 |
| M5 / 図7 | 10：削除率による転移幅と論文Fig.5(a) | [PNG](revised_figures/figure_07_transition_width_p_ja.png) / [PDF](revised_figures/figure_07_transition_width_p_ja.pdf) | 保存状態のP>0.5とP>1/Lに基づくΔp。全13サイズ・4保存fitを表示し、外挿を区別する。 | 小Lでは幅が増える範囲があり、全サイズで単調縮小とは言わない。幅縮小のみで不連続転移を判定しない。 |
| M6 / 図8 | 11：要求数による転移幅と論文Fig.5(b) | [PNG](revised_figures/figure_08_transition_width_time_ja.png) / [PDF](revised_figures/figure_08_transition_width_time_ja.pdf) | Δt/N²=Δt/L⁴の全13サイズ・平均±標準誤差と4保存fit。正のデータ・誤差棒を両対数で示す。 | tはrejectを含む総要求数。測定は保存accepted状態のstepであり、全reject plateau末端の幅と同一視しない。両対数表示への変更はfitをlog回帰に変更した意味ではない。保存fitは大Lの値を十分再現せず、時間幅の漸近指数を精密に確定する用途には使わない。 |

C=1を重視するため、図1だけで「理論再現」とまとめず、図3でP/S前後・stdの一致と残るずれを並べて示す。C=2の解釈も図3の同じ観測定義から説明する。経路長制限なしでは、観測された急激さ、最大1要求変化の漸近候補、幅の定義を分けて話す。

## 補足・質疑：3図

| 補足順 / 元番号 | 使用するスライド | 最終PNG / PDF | 役割 | 注意 |
|---|---|---|---|---|
| S1 / 図2 | A1：Sの前後差 | [PNG](revised_figures/figure_02_finite_S_scaling_ja.png) / [PDF](revised_figures/figure_02_finite_S_scaling_ja.pdf) | S_before/S_afterを2パネルで比較。全9サイズ・平均±標準誤差・保存simple fitを示す。 | Sは最大連結成分を1つだけ除いたサイズ加重平均。43/24の振幅を新しく決めた理論線は追加しない。図3の参照指数比較と合わせる。 |
| S2 / 図4 | A2：共有指数仮説の感度 | [PNG](revised_figures/figure_04_c1_c2_shared_exponent_ja.png) / [PDF](revised_figures/figure_04_c1_c2_shared_exponent_ja.pdf) | 最小採用サイズの4系列と固定補正指数の5点を別パネルにする。非採用の診断解を×で区別する。 | 不安定解を含む有効減衰指数。負の推定値も残す。点推定のみでありjoint CI・普遍性の証明ではない。 |
| S3 / 図6 | A3：有限極限推定の不確実性 | [PNG](revised_figures/figure_06_corrected_finite_limit_ja.png) / [PDF](revised_figures/figure_06_corrected_finite_limit_ja.pdf) | 訂正済み500保存標本のCDF。最大変化量とΔpの2パネル、両モデルを全て保持する。 | 最大変化量では正の極限を排除できない。Δp側は全標本c≤10⁻⁸という既存数値ゼロ判定内であり、微小な曲線差を有限極限差の検出としない。 |

## 約1時間の構成案

| 時間 | スライド | 内容 |
|---|---|---|
| 0〜8分 | 1〜4 | 研究背景、ERネットワークの元論文、格子SPP、開放境界、P/S/p、1要求で全経路削除。 |
| 8〜13分 | 5 | M1：小格子pilotでモデルの挙動を紹介。 |
| 13〜19分 | 6 | C1では受理条件下の辺削除確率1/E。固定削除数の一様辺削除（microcanonical）ensembleとの等価性、固定要求時間との違い。 |
| 19〜24分 | 7 | M2：Pの有限サイズ依存と参照指数。 |
| 24〜34分 | 8 | M3：Pの整合、S前後差、stdのずれ、C2の支持範囲。 |
| 34〜42分 | 9 | M4：経路長制限なしの大きな有限サイズ変化と漸近4候補。 |
| 42〜48分 | 10 | 元論文Fig.5(a)→M5：削除率幅。 |
| 48〜53分 | 11 | 元論文Fig.4/5(b)→M6：総要求数・reject待ち時間・正規化幅。 |
| 53〜56分 | 12 | 支持できる結論と未確定事項。 |
| 56〜60分 | A1〜A3を必要時 | 質疑。S前後差、fit感度、有限極限区間を補足。 |

## 元の9図からの変更と省略の理由

- 図1・2は保存summaryの前後両量とSEMを使う2パネルへ置き換える。新しいfit・平均化は行わず、元の補正モデル曲線は本編の単純なサイズ比較から省く。補正の感度は図4と監査記録で扱う。
- 図3は正式表のsimple5量へ焦点を絞る。旧7パネル中の最大要求変化・Δp指数は通常のβ/ν・γ/ν・1/νと同じ参照検証ではなく、今回のC1/P/S説明には必要でないため省く。固定補正モデルは強い相関・境界解を伴い、simpleとの混在が精密再現の印象を生みやすいため本編から省く。省略した旧図は[前回の全7パネル版](figure_03_finite_exponent_intervals_ja.png)に保持される。
- 図3のordinary参照線はAGENTS.mdの5/48、43/24、3/4に基づく比較目標の追加であり、データへの制約や新しいfitではない。
- 図4は内部名を減らし、サイズ選択と固定補正指数の感度を分ける。負の値・不安定な診断点を除かない。
- 図5・7は0起点の縦軸で量の大きさを示す。図8はサイズ間で大きく異なる正の幅を両対数で読みやすくする。全4モデル・全観測サイズを残し、保存fitの数値は変更しない。
- 図6は主張の補足に回す。Δp側の数値ゼロ判定内の差を物理的な極限差として見せない。
- 図9は各条件全10試行を残し、凡例だけを3条件へまとめる。小格子pilotという位置づけを図と説明で明示する。
- この9図セットから図全体のDROPは行わない。最新複数LのP–p図を新たに設計したとは主張しない。図9はその代用ではない。

## 全図に共通する比較上の条件

本研究は開放境界の二次元正方格子でN=L²、初期辺数M0=2L(L−1)。pは削除辺割合で、通常の占有率は1−p。元論文はERネットワークであり、サイズNと格子サイズLを同じ数値・同じべき指数のまま比較しない。Y∝L^(−x)ならY∝N^(−x/2)に対応する。

主観測は全経路を1要求として削除した境界での値。元論文の1辺削除eventと交換しない。幅は保存状態で定義し、要求数のカウンタと記録時刻の範囲を区別する。誤差棒の標準誤差と、fitパラメータの再標本化区間も別である。同じseedのサイズ間対応があるため、異なるLの点を全て独立試行として数えない。

来歴は[seminar_figure_selection.md](seminar_figure_selection.md)、現行科学判断は[最終研究監査](../../../docs/FINAL_RESEARCH_AUDIT.md)、正式値の案内は[tables/README.md](../../../docs/tables/README.md)。発表者向けの具体的な言い方は、生成図の検証終了後に[figure_talk_notes.md](figure_talk_notes.md)へまとめる。
