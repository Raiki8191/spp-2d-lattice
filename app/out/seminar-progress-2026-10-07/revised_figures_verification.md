# 再生成図の妥当性検証

## 判定と範囲

**PASS WITH NOTES**。本編6図（発表順9→1→3→5→7→8）、補足3図（2・4・6）を、日本語PNGと同stemのPDFで完成した。これは発表図の数値・意味・可読性の検証であり、新たな科学的fitや転移次数の判定ではない。

baseline: 12fade220d65db716511527b0789b49fb52fc317。生成スクリプトは[render_revised_figures.py](render_revised_figures.py)、出力は[revised_figures/](revised_figures/)。正式解析コードへの変更、新しいfit、bootstrap再実行、シミュレーション、commit、pushはない。

## 数値照合

描画時に実際のMatplotlib line/errorbar/CDFの座標と入力値を照合した。さらに描画実装とは別に、CSV読み取り・独立集約・手計算のモデル式により検算した。浮動小数点の読取・演算丸めを区別し、「元画像とのpixel一致」とは主張しない。

| 図 / 用途 | 残した値・系列 | 元CSV・モデル式との確認 | 軸・意味と留保 |
|---|---|---|---|
| 1 / MAIN | 前後2パネル、各C全9L、計36平均±SEM点、6保存fit曲線 | summaryのP_before/after_mean・semと一致。C1/C2のsimple_power各2、C1指数固定fit各1。係数と200点gridを照合 | 両対数。Pは最大連結成分割合。最大変化requestイベント前後の条件付き量で、固定pc測定ではない。理論固定線の近さだけで全指数の再現を主張しない |
| 2 / SUPPLEMENT | 前後2パネル、各C全9L、計36平均±SEM点、4保存simple曲線 | S_before/afterの平均とSEM、保存係数・200点gridと一致 | 両対数。最大連結成分を1つだけ除くサイズ加重平均S=Σs²/Σs。最大サイズが同率でも除外は1つ。前後の指数が異なる点を残す |
| 3 / MAIN | 5量×C1/C2の10正式点推定・95%区間 | CORRECTED表のsimple_power、L_min=8。各500有効draw・失敗0。記録10区間と正式最終表を照合 | 有効減衰/成長指数として表示。通常2次元の5/48・43/24・3/4は外部比較目標。制約・新fitではない |
| 4 / SUPPLEMENT | 14保存fit行に対応する17指数点 | 3最小サイズ×4系列、固定ω5点。非採用/境界6fit→8診断点を×で保持。C2 L_min=32の−0.2476848907も保持 | 両パネルlinear。サイズ選択と固定補正指数の感度を別表示。点推定のみ・強い相関・境界解を精密な共有指数の証拠にしない |
| 5 / MAIN | 全13Lの平均±SEMと全4候補曲線 | 保存summary13行・fit4行、300点grid。既存predictと独立式c+aL^(−x) / c+a(log L)^(−x)が一致 | 横log、縦linear・0起点。最大1要求変化量。L>384灰色は外挿、曲線はL=1536まで。有限極限familyはc≥0でゼロも含む |
| 6 / SUPPLEMENT | ΔP・Δpの2量×2family、各500保存drawのCDF | 計2000標本全保持。sortしたlimitと累積割合i/500、正式区間を照合 | linear。再標本化推定値の分布であって真の極限の確率ではない。Δp側の1000値はすべてc≤10⁻⁸の数値ゼロ判定内 |
| 7 / MAIN | 全13L平均±SEM・全4候補曲線 | summary・保存fit・独立式・旧図の数値と一致 | 横log、縦linear・0起点。Δpは保存状態で最後のP>1/Lと最後のP>0.5の削除率差。小Lの増加を消していない |
| 8 / MAIN | 全13L平均±SEM・全4候補曲線 | 13点のmean−SEM>0。300点の全曲線も正で、両対数による値の除外なし。保存fit係数は不変 | 両対数。Δt/N²=Δt/L⁴、tは棄却を含む要求数。表示変更でありlog fitへの変更ではない。保存fitの大L不適合を明記 |
| 9 / MAIN | L16の3条件×10試行、全30曲線・9284記録点 | C1 4733点/C2 3278点/制限なし1273点。既存ローダーの全行順とxyが一致 | linear、p∈[0,1]。平均化なし。凡例だけ3条件へ集約。初期状態と保存要求後状態を結ぶ線であり、経路内中間物理状態を導入していない |

有限Cは各L・各条件200試行、全9L×2Cの3600試行を用いた既存summaryを使用した。独立集約との平均差は最大2.84×10⁻¹⁴、SEM差は最大1.42×10⁻¹⁴。別CSVパーサー・独立curve評価との差は最大4.55×10⁻¹³（大きいS値の浮動丸め）で、意味的な数値変更ではない。保存bootstrap区間を新しく作り直してはいない。

経路長制限なしはL=8,12,16,24,32,48,64,96,128,192,256,320,384の全13サイズ、観測量ごと2310試行。主図の3量39summary行を保持した。CSV全表には他の量も含まれるため、それを本図の行数と混同していない。全4候補curveの独立式との最大数値差は0。訂正済みbootstrap標本も全500成功drawを使い、境界標本を除いていない。

独立検算の詳細は[verification_finite.json](verification_finite.json)、[verification_unbounded.json](verification_unbounded.json)。描画座標は[revised_numeric_arrays.json](revised_numeric_arrays.json)。このJSONは表示文字列も含むため、凡例文言を直すとファイルSHAは変わる。最終版で数値配列を再照合しており、SHA差を科学値の差と取り違えていない。

## 正式値と図の説明

C1の参照値包含を簡略化せず、図3に残した。

| C1の量 | 点推定 | 保存95%区間 | 通常2次元参照値を含むか |
|---|---:|---|---|
| P直前 | 0.106997 | [0.092906, 0.120037] | YES：5/48 |
| P直後 | 0.104559 | [0.085716, 0.123933] | YES：5/48 |
| S直前 | 1.586319 | [1.440979, 1.766440] | NO：43/24 |
| S直後 | 1.772434 | [1.636596, 1.940062] | YES：43/24 |
| std(p_mid) | 0.669957 | [0.619438, 0.720652] | NO：3/4 |

C2の対応量は近い有限サイズ有効指数を示すが、同じ普遍性クラスを証明していない。区間は固定したサイズ選択・モデル下の試行再標本化で、モデル形・有限サイズ系統誤差・共通seedのサイズ間共分散を自動的に含まない。

UNBOUNDED最大変化量のzero_powerはAICc −116.315871、zero_logは−113.542612。2.773259の差は、この候補集合での相対比較であり転移次数の確定ではない。非負極限を許すpoint fitのc≈0は境界解である。訂正済みcの95%区間上端はfinite_power約0.2480455、finite_log約0.1000252で、正の極限を排除できない。ΔpはL8平均0.272902からL32の0.304738まで増え、その後L384の0.230410まで減る。全Lで単調減少とは説明しない。

図8は既存fitの限界を隠さない。L384の観測平均は5.7520437×10⁻⁵、zero_power予測は1.3349832×10⁻⁴（約2.32倍）、zero_log予測は5.1315459×10⁻⁴（約8.92倍）。元スケール・無重みRSSでは、同じ相対誤差でも値の大きい小Lの寄与が大きい。この推定基準と候補モデルの形の下で、大Lの相対誤差が大きく残る。これは既存fitの不適合であり新データの異常ではない。曲線を残し、大Lを十分再現しないことを図注記・発表計画・話者メモへ反映する。この曲線から時間幅の漸近指数を精密に確定しない。

## 参照元と追跡可能性

- 平均・SEM：[scaling-v2 request_event_summary.csv](../scaling-v2-analysis/request_event_summary.csv)
- 有限C保存fit：[finite_correction_fits.csv](../scaling-v3-analysis/finite_correction_fits.csv)
- 有限C正式訂正区間：[finite_primary_corrected_table.csv](../scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)
- 共有指数感度：[universality_model_fits.csv](../scaling-v3-analysis/universality_model_fits.csv)
- UNBOUNDED平均・SEM：[unbounded_size_summary.csv](../unbounded-v7/unbounded_size_summary.csv)
- UNBOUNDED保存fit：[unbounded_model_fits.csv](../unbounded-v7/unbounded_model_fits.csv)
- 訂正済み保存draw：[unbounded_bootstrap_samples.csv](../unbounded-v7-bootstrap-corrected/unbounded_bootstrap_samples.csv)、[intervals](../unbounded-v7-bootstrap-corrected/unbounded_bootstrap_intervals.csv)
- 正式最終値：[final_values.csv](../final-research-audit/evidence/phase16-fit/final_values.csv)
- 小格子pilot：[manifest.csv](../sweep-pilot/manifest.csv)、L=16/C=1・2・256/results.csv
- 既存描画方法：analysis/scaling_v3.py、analysis/scaling_v3_finite_bootstrap_correction.py、analysis/unbounded_v7.py、analysis/unbounded_bootstrap_correction.py、analysis/plot_smoke.py
- 保存係数からの評価：analysis/correction_fitting.py:simple_power、analysis/unbounded_model_comparison.py:predict、pilot読取はanalysis/io.py:load_sweep

各入力SHA、旧ファイルSHA、軸範囲、出力SHAは[revision_provenance.json](revision_provenance.json)。正式値の優先方針は[docs/tables/README.md](../../../docs/tables/README.md)と[FINAL_RESEARCH_AUDIT.md](../../../docs/FINAL_RESEARCH_AUDIT.md)に照合した。元の研究図・前回の日本語図は維持した。

## 元論文との比較

元論文はERネットワーク、本研究は開放境界の二次元正方格子。N=L²のためL^(-x)とN^(-x/2)の対応を使い、同じ数値のLとNを直接比較しない。開放境界は向かい合う端同士を接続しない意味で、境界の格子辺自体をすべて除く意味ではない。

本研究の主観測は全経路削除を1requestとした前後で、論文の単一辺eventと混同しない。pは削除辺割合、通常の占有率は1−p。図7の保存P状態の閾値幅と、図8の保存受理状態の要求番号による幅を区別する。論文の全要求時系列の待機区間末端と、このaccepted状態記録の時刻を同一視しない。

参照は[著者公開版PRL 133, 047402](https://homes.luddy.indiana.edu/filiradi/Mypapers/PhysRevLett.133.047402.pdf)。比較定義は既存選定記録と一次資料のFig.2〜5に照合した。

## 可読性と修正履歴

全9図を2880×1620 PNG、1152×648 ptの1ページPDF（16:9）で保存。日本語はMeiryo、数式は必要に応じDejaVuを用い、PDF内のBaseFont/FontFile2参照を確認した。最終生成の欠字警告0、表示される文字のcanvas越え0。PNG全9枚と、Popplerで110dpiに変換したPDF全9枚を目視し、軸・誤差棒・凡例・外挿注記・日本語・数式に切れや重なりがないことを確認した。図3の小さい注記は15pt、本文・目盛は概ね16〜19pt、主title27〜28pt。実際の会場の投影条件までは検証していない。

作業中に直した点は、旧図の問題に加え、生成スクリプト内の全表/選択行数の取り違え、Meiryoで出ない上付き英字、図1の左軸ラベル切れ、図1/2/9の凡例とxlabelの接近、図3のtitle/参照注記の重なり、図4の凡例と脚注の接近。修正範囲は本出力dirの新スクリプトと新図だけで、保存値は変えていない。log tickの軸範囲外の未描画ラベルはcanvas越え判定から除外し、実際に表示される文字を確認した。

[png/pdf検証記録](revised_visual_verification.json)に各PDFのページ数・サイズ・画像化先・font参照と目視結果を保存した。pdffonts.exeが環境にないため、その追加確認はPDF内部参照の直接検査へ置き換えた。PDF画像化と目視は全枚成功している。

## 実行と保全

実行した主要コマンド（cwdはリポジトリ直下。プロセスは非表示で起動）：

- 既存research PythonでCSVのcolumns/行数・モデル構造を確認する python.exe -B -c ... の読み取りのみの照会。
- PDF skillのmark_artifact_operation_started.mjsをnode.exeで --operation-kind create --expected-output-count 9 --output-format pdf として初回PDF作成前に1回実行。
- C:/Users/yoshi/AppData/Local/Programs/Python/Python313/python.exe -B app/out/seminar-progress-2026-10-07/render_revised_figures.py。作業中の図修正後に再実行、最終exit=0。
- pdfinfo.exe <各最終PDF>（9ファイル）。全てPages=1、Page size=1152×648 pt。
- pdftoppm.exe -f 1 -singlefile -r 110 -png <各最終PDF> <一時出力prefix>（9ファイル）。
- pdffonts.exe <各最終PDF> は実行ファイル未設置で起動不可。PDF内部のfont参照検査へ切替。
- Git状態・HEAD・差分の読み取り確認、SHA-256保護照合。

SHA-256で研究既存3040ファイルと前回seminar成果物17ファイルを生成前後に照合し、不一致0。raw、manifest、run metadata、L320/L384事前登録原本・予測原本、Java source、正式Python source・正式CSV・docsを変更していない。新規成果物はseminar出力dirのみ。Gitの最終状態は[revision_repository_verification.json](revision_repository_verification.json)に記録する。

## 発表で残す留保

C1はPを中心に参照と整合する一方、S直前とstdのずれを残す。C2は同じ普遍性へ向かう可能性と整合的な範囲。経路長制限なしの有限サイズでの急激さと熱力学極限の転移次数を分け、正の極限を完全には排除しない。図8の保存fitの大L不適合と、元論文との時刻/イベント定義差も説明する。採用順は[final_figure_plan.md](final_figure_plan.md)、話す内容は[figure_talk_notes.md](figure_talk_notes.md)に整理する。
