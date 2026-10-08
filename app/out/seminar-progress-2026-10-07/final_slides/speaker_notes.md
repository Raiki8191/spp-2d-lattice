# 発表者用メモ

本編55分＋質疑・補足5分を目安。図を読む順序と結論の範囲を中心に記載。テスト件数は最終監査時の保存結果で、今回再実行した件数ではない。

## 1. 二次元正方格子上の Shortest-Path Percolation

目安：1分

約1時間の進捗報告。最短経路をまとめて削除するモデルを、構造が固定された二次元正方格子で調べた。背景、モデルと検証、有限Cの再現、経路長制限なし、相談事項の順に話す。現時点の結論と未確定な点を分ける。

参照：`README.md`、`docs/FINAL_RESEARCH_AUDIT.md`

## 2. 経路をまとめて削除すると何が変わるか

目安：3分

通常のボンドパーコレーションは辺単位の無作為占有が基本。SPPでは経路上の複数辺が同じ要求で消え、相関を生む。元論文の主要対象であるERと二次元格子は異なるネットワークなので、結果をそのまま移植しない。元論文の単一辺単位の最大変化量との比較にも注意する。この研究の主観測量は要求全体の前後差。背景出典：Phys. Rev. Lett. 133, 047402 (2024)、https://homes.luddy.indiana.edu/filiradi/Mypapers/PhysRevLett.133.047402.pdf 。既存研究文書に基づく紹介で、新たな文献評価は行っていない。

参照：`README.md`、`docs/FINAL_RESEARCH_AUDIT.md`、`docs/ANALYSIS_DEFINITIONS.md`

## 3. 二次元正方格子なら構造とサイズが明確

目安：3分

開放境界なので端と端をつながない。M0は水平方向と垂直方向にそれぞれL(L−1)本あることから求まる。マンハッタン距離と二項係数は完全な初期格子についての式。削除後の距離・経路数にはこの式を流用しない。正方格子なら理論を全部解いたという意味ではなく、比較条件と幾何学が明確になる。

参照：`README.md`、`docs/FINAL_RESEARCH_AUDIT.md`、`app/src/main/java`

## 4. 1回の要求で、最短経路を1本まとめて削除

目安：4分

頂点対は順序付きで一様、同一頂点は選ばない。順序を逆にした頂点対は同じ確率で選ばれる。C=1の残存辺の一様性は9枚目で示す。最短経路の一様性は単に前の頂点を一様に選ぶ方法ではない。幅優先探索で距離を作り、最短経路の数をBigIntegerで数える。戻る頂点uは、その頂点までの経路数n(u)に比例して選ぶ。経路全体の確率は比の積が打ち消し合って1/n(t)になる。全辺を削除し終わってから要求後の観測を行う。制限なしは連結頂点間なら常に受理と等価。

参照：`README.md`、`docs/FINAL_RESEARCH_AUDIT.md`、`docs/ANALYSIS_DEFINITIONS.md`

## 5. 内部標準から拡張し、予測と検証を積み重ねた

目安：3分

C=1を検証の出発点とし、有限C、経路長制限なしへ広げた。v3は分析の追加であり新規シミュレーションではない。L=320と384の事前登録は対応する結果に先行したことをGit履歴で監査済み。L=192・256の予測資料は同じ強さの正式な事前登録として扱わない。元の事前登録予測と、後で推定器を訂正した区間も区別する。最終監査後のGit baselineは12fade2。

参照：`README.md`、`docs/FINAL_RESEARCH_AUDIT.md`、`docs/UNBOUNDED_L320_PREREGISTRATION.md`、`docs/UNBOUNDED_L384_PREREGISTRATION.md`、`docs/ANALYSIS_AUDIT_CORRECTIONS.md`

## 6. 有限CはL=128、制限なしはL=384まで計算

目安：3分

NとM0はスライド3の幾何学式から求まる整数で、追加の科学的推定ではない。有限Cは9サイズ・各200試行。制限なしのL=96と128は各400試行、192は50試行、256・320・384は各20試行。大きいサイズほど試行数が少なく、誤差と有限サイズの限界を意識する。表は本計算の構成。小さい格子の例示用試行、停止監査や再利用した検証計算を独立な本計算へ加算していない。

参照：`docs/FINAL_RESEARCH_AUDIT.md`、`app/out/unbounded-v7/unbounded_size_summary.csv`、`README.md`

## 7. 数値結果を使う前に、モデルと計算を検証

目安：3分

今回の資料作成ではテストを再実行していない。件数は最終監査の保存済み結果を示す。Java側は小規模全状態や独立探索との照合を含み、一様な経路抽出は経路数の比とオーバーフロー回避を調べた。L=3全4096状態の独立監査は182件のJUnit件数とは別。Python側は解析の入力不変条件、イベント抽出、前後量、転移幅、推定器を確認。UNBOUNDEDと有限Cで点推定とbootstrapが食い違っていた問題は訂正し、回帰テストと正式表を残した。テストが通るだけでは科学的結論の証明にならない。保存済み証拠：app/out/final-research-audit/evidence/phase16-root/。

参照：`docs/FINAL_RESEARCH_AUDIT.md`、`docs/ANALYSIS_AUDIT_CORRECTIONS.md`、`docs/UNBOUNDED_BOOTSTRAP_CORRECTION.md`、`app/out/final-research-audit/evidence/phase16-root/final_java_test_results.json`、`app/out/final-research-audit/evidence/phase16-root/final_python_test.log`

## 8. 小さい格子で見る転移

目安：3分

横軸は初期辺に対する削除率、縦軸は最大連結成分の頂点割合。各条件10試行、合計30試行を全て示す。これは小規模の例示で代表試行の選別ではない。線は初期状態と受理要求後の記録を結んだもので、線の間の連続的な物理状態を測った意味ではない。C=1と2は辺数の制限、制限なしは連結なら受理。見た目の急激さは導入であり、熱力学極限の不連続性の根拠にしない。

参照：`app/out/seminar-progress-2026-10-07/figure_talk_notes.md`、`app/out/seminar-progress-2026-10-07/revised_figures_verification.md`

## 9. C=1は、削除順序を検証できる内部標準

目安：4分

辺の両端を選ぶ順序付き対は2通りで、各対は1/[N(N−1)]。棄却中はグラフが変わらないため次に消える辺の条件付き分布は変わらない。1本削除後も残る辺から一様なので、受理列は初期辺の一様なランダム順列。固定削除辺数のensembleで通常のランダムボンド削除と等価になる。一方、固定要求数tには棄却の待ち時間が入る。独立Bernoulli占有のensembleは辺数の混合であり、固定本数とそのまま同一としない。pc=1/2は占有率と削除率の向きが逆でも同じ値。C=1では要求単位と辺単位が一致する。モデル論理の等価性と、有限サイズで既知の指数が完全に再現されたという主張は分ける。

参照：`docs/FINAL_RESEARCH_AUDIT.md`、`docs/ANALYSIS_DEFINITIONS.md`、`README.md`

## 10. Pのサイズ依存

目安：4分

左は各試行の最大変化を起こした要求の直前、右は直後。Pは最大連結成分の頂点数をNで割った割合。点は200試行の平均、誤差棒は標準誤差であり95%区間ではない。実線は元スケールでの単純べきフィット、灰色破線はC=1で指数5/48を固定した比較。両対数の見た目と推定器の尺度は別。固定p=pcの量ではないため、ここでの指数は有限範囲・最大イベント条件付きの有効指数。C=1はPについてかなり良く一致するが全ての指標を完全再現したとは言わない。C=2も近い。

参照：`app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv`、`app/out/seminar-progress-2026-10-07/figure_talk_notes.md`

## 11. 有効指数と訂正済み不確かさ

目安：5分

図はC=1・C=2について、5種類の有効指数と訂正済みbootstrap95%区間を示す。各500再標本、点推定と同じ元スケールの推定器を使った。Pの直前・直後とSの直後は参照値を区間に含むが、Sの直前と擬臨界点ばらつきの指数は参照値を区間に含まない。Sは最大クラスターを1個だけ除いた重み付き平均クラスターサイズ。全体としてC=1はPを中心に概ね再現。区間は標本不確かさであり、補正モデル・L最小値・有限サイズ系統誤差まで包含するものではない。点推定：C=1のP直前0.106997、P直後0.104559、S直前1.586319、S直後1.772434、std(p_mid)0.669957。参照値は5/48、43/24、3/4。図の下部2行がこのスライドの要点。

参照：`app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv`、`docs/ANALYSIS_AUDIT_CORRECTIONS.md`、`docs/FINAL_RESEARCH_AUDIT.md`

## 12. C=2は、同じ普遍クラスの可能性と整合的

目安：3分

2辺の削除には局所相関があるので、モデル論理だけからC=1と同じと決めない。元論文の有限Cの議論は比較の動機になるが、ERと格子の構造差、NとLのスケーリング表記、主観測量の定義を区別する。図3のC=1と2の近さと区間は統計的な整合性。固定pでの測定ではなく最大イベントの前後であることも残る限界。共通指数フィットや補正の感度は補足19枚目で議論できる。局所相関から同じクラスへ向かうという説明は現時点では解釈・可能性。

参照：`docs/FINAL_RESEARCH_AUDIT.md`、`docs/ANALYSIS_AUDIT_CORRECTIONS.md`、`app/out/seminar-progress-2026-10-07/figure_talk_notes.md`

## 13. 最大変化量のサイズ依存

目安：5分

1要求の前後でPが最も大きく低下した量ΔPの平均を比較。点は各Lの平均±標準誤差、曲線は保存済み4候補。L=384は20試行、ΔP=0.257431±0.013342（標準誤差）。これはPの絶対差であり、その時の値から25.7%低下したという相対率ではない。観測L≤384、灰色域は外挿。v7ではzero-powerが比較上有利だが、zero-logとのAICc差は2.773259で決着とはいえない。有限極限モデルの極限値が0付近の境界に来ても、正の値が完全に排除されたことを意味しない。補足20枚目の訂正後区間を参照。最大変化量が0へ向かうことだけでも、狭い区間への多数の小変化の集中などを排除せず、連続性の証明にはならない。 非負極限を許すモデルはc≥0で、c=0も含む。

参照：`app/out/unbounded-v7/unbounded_size_summary.csv`、`app/out/unbounded-v7/unbounded_model_fits.csv`、`docs/UNBOUNDED_BOOTSTRAP_CORRECTION.md`、`docs/FINAL_RESEARCH_AUDIT.md`

## 14. 削除率で見る転移幅

目安：4分

ΔpはP=1/2側とP=1/L側の状態閾値で区切った削除率の幅。実装はそれぞれ閾値より大きい最後の保存状態を端点にするので、厳密な閾値交差の補間値ではない。L8の平均0.272902からL32で0.304738へ一度増え、L384では0.230410。全Lで単調に減少しているとは言わない。描画済みの4候補は単調型で、初期の山を再現できない。灰色は未観測サイズへの外挿。幅の縮小と最大変化量を合わせても熱力学極限の次数を確定しない。

参照：`app/out/unbounded-v7/unbounded_size_summary.csv`、`docs/ANALYSIS_DEFINITIONS.md`、`app/out/seminar-progress-2026-10-07/figure_talk_notes.md`

## 15. 要求数で見る転移幅

目安：3分

tは受理と棄却を含む要求数。表示量はΔt/N²で、非規格化のΔtが小さくなったという主張ではない。端点は受理後に保存された状態の要求番号であり、全要求のplateauの厳密な終端ではない。縦軸を対数表示しただけで再フィットはしていない。保存済みフィットは元スケール・無重みなので大きい値の絶対誤差が強く効く。L384の観測値5.7520437e−5に対しzero-power1.3349832e−4、zero-log5.1315459e−4と相対差が残る。全観測値を残しており、大きいLだけ除外していない。曲線の見た目から正確な漸近的時間指数を主張しない。

参照：`analysis/transition_width.py`、`app/out/unbounded-v7/unbounded_size_summary.csv`、`app/out/seminar-progress-2026-10-07/revised_figures_verification.md`

## 16. 現時点で支持されることと、残る限界

目安：2分

研究の成果は、モデルを検証した上で比較できるデータと解析体系を作り、C=1のPで基準を確認し、C=2の可能性と制限なしの未確定性を区別したこと。厳密な漸近結論へ強めない。最大イベント前後、定義が一致する量を使う。古い未訂正区間や事前登録原本の予測を現在の正式値として混ぜていない。

参照：`docs/FINAL_RESEARCH_AUDIT.md`、`docs/ANALYSIS_AUDIT_CORRECTIONS.md`、`docs/UNBOUNDED_BOOTSTRAP_CORRECTION.md`

## 17. 今後、何を優先して議論したいか

目安：2分

本編は約55分、残り約5分を質疑・補足に配分する想定。新しい大規模計算をこの資料作成で実施したわけではない。相談の重点は、現データの漸近解釈の限界、モデル形や補正の不確かさ、次の検討優先度。新しい解析を自動的に予定・実行する宣言にはしない。必要に応じて3枚の補足へ戻る。

参照：`docs/FINAL_RESEARCH_AUDIT.md`、`app/out/seminar-progress-2026-10-07/final_figure_plan.md`

## 18. 補足：Sのサイズ依存

目安：質疑時

Sは最大クラスターを1個だけ除いた重み付き平均サイズ。最大サイズ同数のクラスターを全て除く定義ではない。直前と直後を混ぜて指数やhyperscalingを構成しない。図は平均±標準誤差と元スケール単純べきフィット。直後の指数は参照43/24をbootstrap区間に含むが、直前は含まない。定義・最大イベント条件付き・有限サイズ補正が解釈の限界になる。

参照：`app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv`、`docs/FINAL_RESEARCH_AUDIT.md`

## 19. 補足：共通指数と補正の感度

目安：質疑時

左はL最小値の変更に対する独立・共通指数などの比較。右は固定した補正指数omegaに対する指数推定。負の推定も境界到達も隠さず表示する。曲線が見栄え良く当たるだけでは補正の識別性が保証されない。自由omegaや境界・多始点・モデルパラメータ数の問題を監査済み。共通指数の可能性への補助情報であり証明ではない。 正式フィットは固定開始点の方針を保持しており、大域的最小値を保証する意味ではない。

参照：`docs/ANALYSIS_AUDIT_CORRECTIONS.md`、`app/out/seminar-progress-2026-10-07/figure_talk_notes.md`

## 20. 補足：訂正後の有限極限区間

目安：質疑時

有限極限モデルのbootstrap経験累積分布。点推定と同じ元スケール推定器で各500標本を計算した訂正済み結果。最大変化量の正の極限値には上側0.2480455（finite-power）や0.1000252（finite-log）が残る。右の転移幅で0付近へ集中しても、母数が真に0である事後確率ではない。境界、弱い識別性、有限サイズ・モデル形の不確かさを含めた断言はできない。横軸が極限値で縦軸は再標本推定の経験分布、正の極限の有無の検定結果と置き換えない。 右のΔpは2モデル合計1000標本すべてがc≤10⁻⁸の数値ゼロ判定内。左の最大変化量と同じ広い上側区間が残るとは説明しない。

参照：`docs/UNBOUNDED_BOOTSTRAP_CORRECTION.md`、`docs/FINAL_RESEARCH_AUDIT.md`、`app/out/seminar-progress-2026-10-07/revised_figures_verification.md`

