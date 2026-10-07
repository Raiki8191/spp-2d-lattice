# 最終研究監査結果

対象: C:/Users/yoshi/graduation-research/spp-2d-lattice。監査終了時HEADは b40df04cadd6f6e2c838bd7ce628bff6b59262fd、branch main。Phase 4Fの未commit訂正状態を継承し、ユーザーが許可したCLASS A/B修復に限って実施した。Phase 0〜3はユーザー受理済みの結果を継承し、最終段階でモデル実装・検証証拠・原本保全・全テストを再確認した。Phase 0〜3の全監査を今回初めから実行したとは主張しない。

## 総合判定

**PASS WITH CORRECTIONS**。

研究モデル、Javaの主request処理、C=1のaccepted-event等価性、既存本計算データ、事前登録の順序には、今回確認した範囲で結論変更を必要とする破綻を認めなかった。Pythonの推定器・検証・図の不整合は修復し、旧成果物を残したまま訂正成果物を生成した。科学的解釈は、C=2の普遍性およびUNBOUNDEDの熱力学的転移次数を未確定とする範囲までである。

全保護原本1,895ファイル、2,139,750,724 bytesの最終SHA-256はbaselineと一致。不一致0。Java182件・Python180件PASS、build成功。大規模物理simulation、raw変更、事前登録原本変更、Git履歴変更、commit/pushは行っていない。

## Phase一覧

| Phase | 判定 | 確認内容・留保 |
|---|---|---|
| 0 | PASS WITH NOTES | 受理済み履歴監査を継承。最終HEAD・原本・事前登録・Git状態を再確認。 |
| 1 | PASS | 受理済みモデル監査を継承。格子、ordered pair、経路重み、全辺削除後の測定を再読。 |
| 2 | PASS WITH NOTES | C=1は固定accepted数/削除率の通常bond ensembleと等価。固定request時間やBernoulli ensembleと区別。 |
| 3 | PASS WITH NOTES | 受理済み独立小状態検算を継承。恒常テストの限界を明記し、最終全テスト再実行。 |
| 4 | REPAIRED | B1〜B6を修復。継承B0再監査。失敗fit・boundsを保持し訂正bootstrapを独立検算。 |
| 5 | PASS WITH NOTES | 48条件243run、196,587raw行。旧pilot時間表の参照差を明記。 |
| 6 | PASS WITH NOTES | v1 4,200run、3,702,767raw行。C1数値指数の完全再現とは言えない。 |
| 7 | PASS WITH NOTES | benchmark30/main1,600/audit120run、統合5,800run。延長auditの主event更新0。 |
| 8 | PASS WITH NOTES | finite fit192行、shift37行、正式bootstrap。補正・相関・L_min依存は強い。 |
| 9 | REPAIRED | universality70点fit・24区間を照合。B7の2図を訂正。普遍性の証明には達しない。 |
| 10 | PASS WITH NOTES | 3順序870,624request境界状態一致。人工辺順は副解析だけに影響。 |
| 11 | PASS WITH NOTES | UNBOUNDED L≤128、2,200本標本。歴史的急峻性と漸近転移次数を区別。 |
| 12 | PASS WITH NOTES | L192主50/audit3run、53shard、42,532raw行、v4 fit・訂正CI。 |
| 13 | PASS WITH NOTES | L256主20/audit3run、23shard、27,014raw行、v5 fit・訂正CI。 |
| 14 | PASS WITH NOTES | L320主20/audit3run、34,760raw行、原本事前登録24予測、v6再評価。 |
| 15 | PASS WITH NOTES | L384主20/audit3run、42,379raw行、原本24予測、v7、識別1,000試行独立再現。 |
| 16 | PASS WITH NOTES | 主要値の縦provenance、統合科学判断、全テスト、全原本SHA、最終Git・文書案内。28代表chain/828検査。 |

各Phaseの具体的パス、実行コマンド、独立検算の入力・出力・SHAは[監査台帳](../app/out/final-research-audit/audit_record.json)と[証拠ディレクトリ](../app/out/final-research-audit/evidence/)を参照。個別検算の件数は相互に重複するため加算して独立証拠数にしない。

## 監査中に発見した全問題

CLASS Bは8項目（継承B0を含む）、CLASS Aは16項目。CLASS Cに該当する未解決問題はない。修復によって理論値・既存結論に近づけるためのmodel/L_min/bounds/outlier変更はしていない。統計的留保は後述する。

| ID / Phase / CLASS / severity | 原因・修正・場所 | regression / 検証 | numerical / scientific impact |
|---|---|---|---|
| B0 / 4,4R,4F / B / 重大な不確実性 | 継承済み: original-scale bounded point fitと旧quick logOLS/profile/soft penalty bootstrap不一致。unbounded_model_comparison.py/scaling_v3.pyを共通helper化。 | 継承24 regression、42,000正式fit。v4〜7の38,000 fitは4Rとbit一致。現監査で保存draw/RSS/quantile/sourceを再照合。 | 点/RSS/AICc/BIC・順位不変、CI/分布/boundary頻度訂正。旧負amplitude・境界移動からの漸近解釈を撤回。 |
| B1 / 4 / B / event定義の誤用 | request_event.build_request_transitionsが間引き状態を1request扱い。manifest ACCEPTED_REQUESTとΔaccepted=1/0 guardを追加、3 CLIも適用。 | request4追加ケース＋scaling-v2 guard4。既存mode-comparisonで旧path length=3/C2を再現。 | 本解析入力は元から完全accepted状態列、既存正式数値不変。主event定義の将来誤用を拒否。 |
| B2 / 4 / B / validator欠落 | validation.validate_sweepに有限性・完全初期行・run数/seed・成分整合検査が不足。独立改変6種を旧検証が受理。 | 13追加ケース、関連51PASS。後続各Phaseで既存raw独立検査。 | 現存rawの破損を発見したものではなくguard不足。正式数値不変。 |
| B3 / 4 / B / 重大なCI | finite-C/S_after、U1/U2/U3、corrected shiftの旧bootstrapが別推定器・bounds。scaling_v3/universality_fittingの既存点helperへ統一。 | finite producer10＋joint/shift11。12,000 primary fitと8,500 joint model fit、点37shift/70joint不変。 | S_after CI拡大、共通指数等の精密主張を撤回。49 primary/162 joint失敗は保持しconditional CIとして扱う。 |
| B4 / 4 / B / optimizer/API | v2 single-start bootstrap対multistart point。fit_power_models共用。訂正producerの全失敗flagもundefinedに修復。 | estimator新規2＋既存1の関連3、全失敗を含むproducer新規4ケース、修正関連13PASS。正式25,000/25,000収束。 | 上限CI差最大3.377543e−7、点不変。全失敗処理修正の正式数値影響0。有限極限排除の可否不変。 |
| B5 / 4 / B / OLS区間 | scaling_fit._fit_rowがdf≥6でt分位の代わりに1.96。scipy.stats.t.ppf(.975,n−2)へ。 | log CI新規4＋既存2の6PASS。v1 96/v2 144、計240行検算。 | 点/SE不変。df7では区間幅約20.6%増。旧狭い区間からの精度主張不可。 |
| B6 / 4 / B / obsolete入力 | v5〜7履歴関数が旧quick CIを読み得た。artifact_status.corrected_unbounded_intervalsで訂正専用参照、欠落時停止。 | artifact resolver含む関連18PASS、履歴16/56/76行照合。 | 点/LOO不変、区間参照を訂正。事後訂正を事前予測と混同しない。 |
| B7 / 9 / B / 図の欠落 | U1全NaN shared列を存在だけで選択し2独立系列を消す、theory-fixed simple曲線も分岐で省く。scaling_v3の2plot分岐修復。 | 5追加plot test＋関連21、26PASS。非figure26関数AST不変、別読者/画像QA。 | 2 successor PNGのみ新規。fit/CI/元図不変。図からの共通指数確定を避ける。 |
| A1 / 4 / A / 軽微 | exact ensemble観測範囲0..M0を0..K_finalへ。ANALYSIS_DEFINITIONS。 | 80履歴/919状態・coverage検算。 | 数値不変。未観測tailを観測済みとしない。 |
| A2 / 4〜16 / A / 案内 | CURRENT/CORRECTED/SUPERSEDED/HISTORICALと現行コマンドの区別不足。README・定義・台帳・tables案内追加。最終草稿のUNBOUNDED数値budget説明もC=Nへ訂正。 | 主要値の縦source照合、リンク/ファイル確認。 | 数値不変。失効区間の卒論再引用を防ぐ。 |
| A3 / 5 / A / 時間記録 | old pilot_summaryの9時間値が現execution_timesと異なる。summaryが49分古い。古いCSVを保持し現時間参照を注記。 | raw物理値/時間CSV照合。mtimeだけで再runを証明しない。 | 422ms対545ms等、時間参照のみ。物理結論不変。 |
| A4 / 6 / A / 主張範囲 | C1の広い「再現」表現。V1にequivalenceと有限サイズ指数検証の区別追記。 | 指数/CI/同endpoint hyperscaling再計算。 | 数値不変。全canonical指数再現とは言わない。 |
| A5 / 7 / A / 用語 | v2失効bootstrapのscopeが広い、run別Smaxとensemble共通pのS_peak混同。限定・区別追記。 | raw/summary・CI出典検算。 | 数値不変。observable置換を防ぐ。 |
| A6 / 7 / A / 転記 | V2の3最終桁を.42647/.49419/.52388に訂正。 | 元CSV丸めチェック。 | 最大1e−5、文書のみ。順位/結論不変。 |
| A7 / 8 / A / fit説明 | theory-fixed shiftをRSS最小とも記述、最大相関とpc-q混同の余地。V3を具体化。 | 独立RSS/criterion/相関照合。 | 数値不変。少parameter規準選好と残差最小を区別。 |
| A8 / 8 / A / L_min説明 | P_afterが一般により安定との主張はL_min48で成立しない。8..32と4点fit48を分けて注記。 | L_min fit表照合。 | 数値不変。安定性の過大評価を除去。 |
| A9 / 9 / A / 最適化留保 | P_after U2のRSSがnested U3より小さくない局所解。現行固定開始点policy保持、embedded-start診断を文書化。 | 診断RSS−0.5467%、指数+.001015、優位候補は同じ。 | 正式点/CI不変。global minimum/精密指数は保証しない。両fitはboundary。 |
| A10 / 10 / A / 傾向説明 | order range単調縮小をedge-eventにも一般化。L32→64 .005151→.005310等と3固定順序の限界追記。 | 3順序raw/12文書セル検算。 | 数値不変。順序依存の漸近消失とは言わない。 |
| A11 / 11 / A / 歴史的解釈 | V1のtrue/weak discontinuityの二択がslow-vanishingを落とす。歴史を残しゼロjumpの可能性追記。 | ≤128 model/width/jump/CI照合。 | 数値不変。連続転移の可能性は排除しない。 |
| A12 / 11 / A / 丸め | V3 LOO RMSE .01116/.00871を.01115/.00870へ。 | old/new LOO CSV SHA一致。 | 2文書セル1e−5、順位不変。 |
| A13 / 12 / A / provenance | v4旧区間/生成コマンド/current scope、Java下側median未明記。V4に出典/注記。 | 65semantic確認、summary/図確認。 | 点不変。1.421下側medianと通常1.430を区別。 |
| A14 / 13 / A / 案内・転記 | v5旧区間/コマンド、resume証拠scope、15対17図。V5を訂正。 | 136semantic確認・図inventory。 | 物理値不変。旧uncertaintyをcurrentにしない。 |
| A15 / 14 / A / 事前/事後 | v6 18対19図、L256保存予測をformal preregとする表現、強いzero断定。V6にoriginal/currentCI区別。 | 1,583semantic確認、24凍結予測・Git履歴。 | 原本不変。事後CIを事前登録済みと呼ばず候補内選好に限定。 |
| A16 / 15 / A / 時刻・精度 | v7 235秒/9%は予測元混在、frozen generation時刻はsource commit時刻、CI/PI coverage・識別解釈が曖昧。V7を注記。 | 2,061semantic確認、metadata和、1,000識別試行再現。 | 実時間293.374s/対応予測293.538816s、差−.05615%。物理fit/原本不変。識別率は条件付き。 |

修復の詳しい期待挙動・関数・旧/新値・tests・生成コマンドは[補正台帳](ANALYSIS_AUDIT_CORRECTIONS.md)。局所optimizer、boundary、共通seed、500draw、有限サイズ等は独立の統計的限界であり、都合よく仕様を選び直して「解消」していない。

## Java最終評価

意図されたopen L×L undirected/unweighted格子、N=L²、M0=2L(L−1)、現在active辺上のBFSと一致する。stepはsourceをnextInt(N)、targetをnextInt(N−1)からsourceを飛ばす一対一写像で選び、ordered pairは1/[N(N−1)]。同頂点は生成されない。

ShortestPathFinder.runBfsは各距離層の全predecessor寄与を足し、c(s)=1、c(v)=Σc(u)をBigIntegerで計算する。target発見後も距離d(t)−1の層をすべて処理する。selectPathはpredecessor uをc(u)/c(v)で後向きに選び、randomBelowはbit maskと棄却抽選でmodulo偏りを避ける。完全最短経路s=v0,…,vd=tの確率は積Πc(vi−1)/c(vi)=1/c(t)で全経路共通。無重みpredecessor抽選だから一様という判断ではない。

distanceは辺数、C1/C2はそれぞれ1/2以下、UNBOUNDEDはSPPSweepPlan.conditionsとSPPUnboundedL192.Stage.budgetでC=N=L²として実現する。最短距離は単純路のN−1以下なので、この有限budgetで連結なら受理と等価（入力C≥N−1もsweepではこの条件へ集約）。processRequestは全path辺のactiveを確認し、全辺を削除し、個数を検査し、counter/observerを更新してからrunner測定。途中edge状態は物理requestの測定に使わない。terminal rejectionはcounterだけの行でPython主eventでは除外する。P=最大component/N、Sは最大componentを1つだけ除くΣs²/Σs（最大tieの残りは含む、全連結なら0）。

Phase3独立検算を継承: L2全16/L3全4096状態の独立Floyd/DFS距離・完全path数、受理939,108queryのcountと経路、2359872検索の状態不変、非対称1:2重み、65bit count、randomBelow841script、component4113状態等。恒常JUnitの距離比較はL2全16状態576query、L3は24標本状態6,912queryであり、上記独立全4096状態検算とは別である。恒常テストの対称4,000抽選だけでは非対称経路重みを検出しない限界を保持する。最終182testsは別に再実行し、テスト通過だけを科学的証明とはしない。Java sourceは監査開始baselineから不変。

## Python最終評価

initial/accepted/terminal行、最大request jumpのtie規約、before/after/p_mid、width、ddof=1 std/SEM、run bootstrap、point推定器、bounds、param数、RSS、CIの照合を完了。主解析はrequest-level。edge reconstructionは観測された0..K_finalの副解析。

現行point/bootstrapは対象ごとに同じ既存目的関数・bounds・開始点policyを使う。run全体をresampleし、requestを独立標本にしない。失敗fitを残す。AIC=n log(RSS/n)+2k、AICc=AIC+2k(k+1)/(n−k−1)、BIC=n log(RSS/n)+k log n。kは回帰関数のfree parameter数という既存規約で残差分散を加算していない。n≤k+1のAICcは比較不能。異なるRSS尺度/observable/使用Lの規準値を直接比較しない。最終180tests PASS。

## C=1最終評価

**accepted-event列の内部benchmarkとして妥当。** 現active無向辺eを削除するpairは2方向だけなので1requestの確率2/[N(N−1)]、accepted確率2E/[N(N−1)]、条件付き確率1/E。rejectではgraph不変、待ち時間を合計しても次の辺は一様。順列全体は1/M0!。accepted数k/削除率p=k/M0を固定すると一様k辺削除のmicrocanonical ordinary bond ensembleであり、occupation q=1−p。Bernoulli occupation ensembleは削除数をbinomial混合したときに対応する。固定request数の過程をそれと同一視しない。

C1ではrequest/edgeの削除集合と前後物理量は一致。p_mid対edgeのp_after座標には1/(2M0)の定義差があり、bugではない。pc=.5は削除率の向きでも整合する。C1のモデル等価性から、現在のevent-conditioned有限サイズfitがすべてcanonical exponentを再現するとは結論しない。simple S_beforeとstd(p_mid)の訂正CIは参照値を含まない。finite-size effectとobservable/model fit系統誤差の寄与を一意に分離していない。

## C=2最終評価

主finite-size量はC1に近く、**「同じuniversality classへ向かう可能性と整合的」**までは支持される。共有指数は証明されない。joint70fitのうちboundary37、45自由補正fitは最大|相関|≥.99、15 observable/L_min群の6群にnumerically admitted fitなし。訂正CI、omega/L_min/local minimum依存、paired seed covariance留保を伴う。theory値とCI overlapだけで普遍性を確定しない。

同endpoint hyperscalingの点チェックはC1 before1.800313/after1.981552、C2 before1.825606/after1.985258。beforeとafterを混ぜて2へ近づけない。これらは相関を含むhyperscaling区間の検定ではない。

## UNBOUNDED最終評価

有限サイズでは大きなrequest-level jumpを示す。主標本はL8〜384の13サイズ、2,310run（最大3サイズは各20run）。現行候補・目的関数・規準では最大request jumpが漸近的ゼロへ向かう候補が相対的に支持され、v7ではzero-power優勢。ただしzero-power対zero-logのAICc差は2.773259で決定的ではなく、finite極限は排除できない。

finite-power/logはc≥0のfamilyでc=0も含み、別個の純粋な「正の極限」仮説ではない。finiteのpointはboundary/nonadmittedの診断fitである。point c≈0、bootstrap数値境界頻度66.8%/95.0%にもかかわらず上限は.248045/.100025、point c-q相関約.999。正の微小CI下端をゼロ排除と解釈しない。run-bootstrap500drawの全4候補比較でzero-power415/zero-log85回（83%/17%）を選択した。[保存fit draw](../app/out/unbounded-v7-bootstrap-corrected/unbounded_bootstrap_samples.csv)に基づく条件付き選択頻度でありmodel真実確率ではない。

L320平均jump.245623046875、L384 .257430691189。差.0118076443、bootstrap範囲[−.0257770847,.0493013774]で単調性の証拠ではない。L256/320/384の3逐次予測点ではzero-powerのMAE/RMSEが最小だが、独立大量の外部検証ではない。parametric識別率80.6%/82.6%は独立Gaussian SEM、eps clipping、2zero familyという仮定に条件付きであり、finite候補排除や物理モデルの真実確率ではない。

最大単一jump→0だけでは、多数の小jumpが縮む窓に集まる場合を排除できず、極限P(p)の連続性の数学的証明にはならない。熱力学的転移次数は未確定。

## preregistration最終評価

| 対象 | source→登録→本計算 | 結果 |
|---|---|---|
| L320 | source67c0c9c 2026-07-20 10:00:56UTC →freeze11:01:24.488978 →登録0ef0cb5c 11:02:24 →最初のrun11:03:40.643617400 | MD/予測CSVとも追加1commitのみ、事後変更なし。 |
| L384 | source8afdのcommit時刻11:25:38UTC →登録d0117df7 11:45:38 →最初のrun11:46:44.7836983 | MD/予測CSVとも追加1commitのみ、全23runのstartが登録後。 |

Git LF/working CRLF差はcore.autocrlfと正規化bytesで説明でき、値変更ではない。L384のgeneration_timestamp_utcは実際の生成clockでなくsource commit時刻を保存する実装だった。原本を書き換えず意味を明記し、順序判断は登録commitを用いる。Git/metadataの時刻は外部署名付きtimestampの証明ではない。

L320の4元PIはobserved meanを含まず、L384は4元PIに入る。元PIと事後corrected PI、observed mean CIを区別し、混合した2/3 inclusionをcalibrated95% coverageと呼ばない。元予測/元区間は歴史的証拠として保持し、事後CIを遡って事前登録済みにしない。

## reproducibility最終評価

原本1,895SHA一致、旧実験run数・shard・seed namespace・統合bytes・cached/run/summaryを相互照合。[縦provenance](../app/out/final-research-audit/evidence/phase16-data/vertical_provenance.csv)は28代表chain・828検査、201独立集約値・別読者20point/CI・5代表図を接続した。主標本はC1 1,800/C2 1,800/UB 2,310、計5,910 condition-runで、共通seedを含むため5,910 iid runとは呼ばない。benchmark再使用・stop-auditを本計算への追加独立標本にしていない。

同seed trace on/offや延長auditのprefixはbytes/14物理列で一致。v2延長120run、L192以降各3auditで主event更新0。停止時最大component Bを用いる将来drop上界（有限Cはfloor(CB/(C+1))、UNBOUNDEDはB−1）でも全主標本の最大request eventを取り逃さないことを確認。v1の副解析global Smaxは345runでtail上界だけでは未保証、主jumpとは分ける。

resume markerとvalidateShardは宣言invariantを検査するが全bytes破損検出器ではなく、当時のskip個数の恒久ログもない。今回の独立全metadata/merge/hash照合はこの留保を置換しない。

## 卒論で使用すべき正式値

有限CはL8,12,16,24,32,48,64,96,128、各C/各L200run、L_min8、以下の5量はoriginal-scale simple NLSと500 run-level bootstrap（別表のjump/width指数は既存log OLS）。P/stdは減衰指数、Sは増大指数。これらは最大request jump eventの前後で評価した有限サイズ有効指数であり、確定した漸近臨界指数と呼ばない。

source: [finite_primary_corrected_table.csv](../app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)。

| 量 | C1点 | C1 2.5–97.5 percentile | C2点 | C2 2.5–97.5 percentile |
|---|---:|---|---:|---|
| P_before | .106997 | [.092906,.120037] | .117370 | [.103927,.130509] |
| P_after | .104559 | [.085716,.123933] | .108595 | [.092684,.126449] |
| S_before | 1.586319 | [1.440979,1.766440] | 1.590865 | [1.463514,1.772335] |
| S_after | 1.772434 | [1.636596,1.940062] | 1.768067 | [1.616833,1.935314] |
| std(p_mid) | .669957 | [.619438,.720652] | .667847 | [.611793,.731183] |

source: [pseudocritical_shift_corrections.csv](../app/out/scaling-v3-analysis/pseudocritical_shift_corrections.csv)。同じモデルのCIがない行に別omega/modelのCIを付けない。

| C | simple shift policy、L_min8 | pc | q |
|---|---|---:|---:|
| 1 | pc=.5/q=.75理論固定 | .5（目標値） | .75（目標値） |
| 1 | pc=.5、q free | .5（固定） | .7136269364 |
| 1 | pc/q free | .4967105832 | .9685205880 |
| 2 | pc/q free | .4971043670 | .9470151618 |

C1 std fixed omega2の診断指数.7828899601、範囲[.6886905981,.8753673353]。correction S_afterはC1 omega1で1.981087/[1.584745,2.135938]、C2 omega.75で2.089753/[1.516073,2.247184]だが高boundary頻度。S≤L²の上界に対してleading exponent>2を文字通りの漸近指数として採用できず、finite-range診断としてのみ示す。

UB v7最大request jump、13サイズL8〜384、L_min8、500draw。source: [unbounded_model_fits.csv](../app/out/unbounded-v7-bootstrap-corrected/unbounded_model_fits.csv)、[unbounded_bootstrap_intervals.csv](../app/out/unbounded-v7-bootstrap-corrected/unbounded_bootstrap_intervals.csv)。

| model / parameter | 点 | 2.5–97.5 percentile | AICc | BIC |
|---|---:|---|---:|---:|
| zero-power x | .0813589432 | [.0659991160,.0949638817] | −116.3158706424 | −116.3859719275 |
| zero-log x | .2994788406 | [.2468417724,.3457305932] | −113.5426120362 | −113.6127133213 |
| finite-power c | 5.5713e−15 | [3.4440e−23,.2480454955] | −112.8492039758 | −113.8210225701 |
| finite-log c | 1.4611e−20 | [5.1075e−23,.1000251803] | −110.0759453695 | −111.0477639638 |

原本予測は[PREREGISTRATION文書](UNBOUNDED_L384_PREREGISTRATION.md)と対応frozen CSVから引用し、上の事後corrected CIとは別表にする。正確な非丸め値は[final_values.csv](../app/out/final-research-audit/evidence/phase16-fit/final_values.csv)、縦source一覧は[Phase16 data証拠](../app/out/final-research-audit/evidence/phase16-data/)を参照。

## 使用してはいけない旧値

- C1 scaling-v3 S_after旧CI [1.65960,1.72340]。現行は[1.6365961737,1.9400621511]。
- scaling-v3旧finite-C/joint/corrected-shift bootstrapの失効区間。例U2 P_after [.094399,.119651]→[−.091730,.208312]。
- scaling-v3 UNBOUNDEDおよびv4〜7の旧quick bootstrap CI/CDF/境界頻度、旧履歴CSV内の該当CI列。点/RSS/criterionは別扱いで現行。
- scaling-v2 single-start finite-limit旧区間、v1/v2旧t近似OLS区間。訂正専用ディレクトリを使う。
- 欠落するU1系列を含む旧shared exponent図とtheory-fixed simpleを省く旧比較図。

元事前登録区間は現在推定器の不確実性として使わないが、当時の予測検証・歴史的証拠には必ず元値を使う。SUPERSEDEDは削除を意味しない。

## 卒論で安全に主張できること

- 定義されたSPPをJavaが実装し、数学的経路一様性・独立小状態/trace検算・既存データ照合が裏づける。
- C1のaccepted列/固定削除率は通常random sequential bond deletionと等価で内部benchmarkになる。
- C2の主要有限サイズ量はC1に近く、同じuniversality classへ向かう可能性と整合的。
- UNBOUNDEDは有限サイズで強く急激。現行候補間ではvanishing maximum request jump候補が相対的に支持されるが、正の極限・power/log・熱力学的次数は未確定。
- L320/384の原本予測は登録commitが本計算より前に存在し、結果後の内容変更は認めない。

## 卒論でまだ主張してはいけないこと

C1で全canonical指数を精密に再現済み、C2の普遍性を証明、UNBOUNDEDが不連続/連続と確定、finite-limitを排除、zero-powerが真の漸近則、識別率/選択頻度がmodel真実確率、事後訂正CIが事前登録済み、bootstrapがmodel/L_min/有限サイズ系統誤差を全包含、3辺順序で全人工順序依存を排除、といった主張。

## 追加simulationの必要性

**任意。** 現データの限界を明記した卒論には追加大規模simulationは必須でない。普遍性・正のjump極限の排除・転移次数やpower/logの確定へ主張を強めるには、別途事前設計したより大きいL/より多いrun/compatible observableと不確実性の検証が必要になり得る。今回は実行していない。

## 残存する統計的限界

有限サイズ/event-conditioning/open boundary、L_min/model/omega系統誤差、freeomega/joint/finite-limitの強相関とboundary非識別性、固定開始点の局所解、500draw Monte Carlo誤差を残す。49/162失敗fitの区間は有効fit条件付きで、無条件95%coverageは未確認。

共通seedのcross-L/C covarianceを独立condition bootstrapは含まない。paired C1/C2 mean SEM比.8905〜1.0767や小相関から指数coverage/独立性は証明できない。情報量規準のstructural kを残し、k+1規約の診断ではC1 std AICc winnerが変わる。Gaussian無重みfitの仮定、LOOのin-range性、最大3サイズ各20run、元PIのheuristic式とCI/PI混合coverageも留保する。主maximum jump以外の数値境界例はv4 delta_p finite-power c=5.82465e−11対CI上端3.58577e−11、v7 delta_p finite-log c=1.9918e−13対上端3.13232e−14。点とCIのliteral不包含は残したまま、すべて既存数値境界閾値1e−8未満の平坦なc=0解と説明する。同じ推定器でありCIをpointに合わせてclipしていない。これを正の極限/ゼロ排除と解釈しない。

## 残存する実装上の限界

大規模mainはtrace offのため全辺ID/連結性を保存rawだけから再構築できない。恒常JUnitのpath一様性testは対称例中心で、現在の非対称/overflow根拠は独立監査scriptと数理証明を含む。古いmetadataに実行binary/source hash、外部署名時刻、恒久resume countはない。marker検証だけで全bit破損を検出しない。

request時間widthは記録accepted-state間の総request時間であり全reject plateau終端幅とは異なる。counterなし下位builderは完全accepted列を呼出前提とする。v1副Smax tail345runは上界だけで未保証。Python guardがraw生成を正しくした証明ではなく、現在rawの独立検査は別証拠として扱う。

## 修正したファイル

最終Git一覧に示す24tracked files。継承4F変更8fileを含む。Java source、raw/manifests/prereg原本の変更は0。docs/tables/UNBOUNDED_MODEL_HISTORY.csvの16CIセルは継承4F修正で、今回さらに書き換えていない。

- [README.md](../README.md)
- [analysis/plot_request_event.py](../analysis/plot_request_event.py)
- [analysis/plot_scaling.py](../analysis/plot_scaling.py)
- [analysis/request_event.py](../analysis/request_event.py)
- [analysis/scaling_fit.py](../analysis/scaling_fit.py)
- [analysis/scaling_v2.py](../analysis/scaling_v2.py)
- [analysis/scaling_v3.py](../analysis/scaling_v3.py)（4Fから継承）
- [analysis/tests/test_request_event.py](../analysis/tests/test_request_event.py)
- [analysis/tests/test_validation.py](../analysis/tests/test_validation.py)
- [analysis/unbounded_model_comparison.py](../analysis/unbounded_model_comparison.py)（4Fから継承）
- [analysis/unbounded_v5.py](../analysis/unbounded_v5.py)
- [analysis/unbounded_v6.py](../analysis/unbounded_v6.py)
- [analysis/unbounded_v7.py](../analysis/unbounded_v7.py)
- [analysis/universality_fitting.py](../analysis/universality_fitting.py)
- [analysis/validation.py](../analysis/validation.py)
- [docs/ANALYSIS_DEFINITIONS.md](ANALYSIS_DEFINITIONS.md)
- [docs/SCALING_V1_RESULTS.md](SCALING_V1_RESULTS.md)
- [docs/SCALING_V2_RESULTS.md](SCALING_V2_RESULTS.md)
- [docs/SCALING_V3_RESULTS.md](SCALING_V3_RESULTS.md)（4Fから継承）
- [docs/UNBOUNDED_V4_RESULTS.md](UNBOUNDED_V4_RESULTS.md)（4Fから継承）
- [docs/UNBOUNDED_V5_RESULTS.md](UNBOUNDED_V5_RESULTS.md)（4Fから継承）
- [docs/UNBOUNDED_V6_RESULTS.md](UNBOUNDED_V6_RESULTS.md)（4Fから継承）
- [docs/UNBOUNDED_V7_RESULTS.md](UNBOUNDED_V7_RESULTS.md)（4Fから継承）
- [docs/tables/UNBOUNDED_MODEL_HISTORY.csv](tables/UNBOUNDED_MODEL_HISTORY.csv)（4Fから継承）

## 新規作成したファイル

継承4F新規5項目を含む最終20untracked source/test/docs。研究出力と証拠はGit ignored app/outに別保存。

- [analysis/artifact_status.py](../analysis/artifact_status.py)
- [analysis/scaling_v2_bootstrap_correction.py](../analysis/scaling_v2_bootstrap_correction.py)
- [analysis/scaling_v3_finite_bootstrap_correction.py](../analysis/scaling_v3_finite_bootstrap_correction.py)
- [analysis/scaling_v3_joint_shift_correction.py](../analysis/scaling_v3_joint_shift_correction.py)
- [analysis/tests/test_artifact_status.py](../analysis/tests/test_artifact_status.py)
- [analysis/tests/test_scaling_fit_intervals.py](../analysis/tests/test_scaling_fit_intervals.py)
- [analysis/tests/test_scaling_v2_bootstrap_correction.py](../analysis/tests/test_scaling_v2_bootstrap_correction.py)
- [analysis/tests/test_scaling_v2_bootstrap_estimator.py](../analysis/tests/test_scaling_v2_bootstrap_estimator.py)
- [analysis/tests/test_scaling_v2_request_guards.py](../analysis/tests/test_scaling_v2_request_guards.py)
- [analysis/tests/test_scaling_v3_finite_bootstrap_correction.py](../analysis/tests/test_scaling_v3_finite_bootstrap_correction.py)
- [analysis/tests/test_scaling_v3_joint_shift_estimator.py](../analysis/tests/test_scaling_v3_joint_shift_estimator.py)
- [analysis/tests/test_scaling_v3_shared_exponent_figure.py](../analysis/tests/test_scaling_v3_shared_exponent_figure.py)
- [analysis/tests/test_scaling_v3_unbounded_estimator.py](../analysis/tests/test_scaling_v3_unbounded_estimator.py)（4Fから継承）
- [analysis/tests/test_unbounded_bootstrap_correction.py](../analysis/tests/test_unbounded_bootstrap_correction.py)（4Fから継承）
- [analysis/tests/test_unbounded_bootstrap_estimator.py](../analysis/tests/test_unbounded_bootstrap_estimator.py)（4Fから継承）
- [analysis/unbounded_bootstrap_correction.py](../analysis/unbounded_bootstrap_correction.py)（4Fから継承）
- [docs/ANALYSIS_AUDIT_CORRECTIONS.md](ANALYSIS_AUDIT_CORRECTIONS.md)
- [docs/FINAL_RESEARCH_AUDIT.md](FINAL_RESEARCH_AUDIT.md)
- [docs/UNBOUNDED_BOOTSTRAP_CORRECTION.md](UNBOUNDED_BOOTSTRAP_CORRECTION.md)（4Fから継承）
- [docs/tables/README.md](tables/README.md)

## corrected / superseded成果物

| CORRECTED参照先（app/out/） | 対応SUPERSEDED |
|---|---|
| scaling-v3-finite-bootstrap-corrected | v3有限Cの旧選択区間/図 |
| scaling-v3-joint-shift-bootstrap-corrected | v3 U1/U2/U3・corrected shift旧bootstrap |
| scaling-v2-bootstrap-corrected | v2 single-start finite-limit CI |
| scaling-log-ci-corrected | v1/v2旧OLS区間 |
| scaling-v3-unbounded-bootstrap-corrected | v3旧UNBOUNDED quick CI |
| unbounded-v4/v5/v6/v7-bootstrap-corrected | 各旧quick CI/CDF |
| unbounded-history-bootstrap-corrected | v5〜7履歴の旧CI列 |
| scaling-v3-shared-exponent-figure-corrected | shared系列欠落/simple分岐欠落の旧2図 |

すべて別の出力先。元完了データ/旧derived/原本preregは保持。[成果物台帳](ANALYSIS_AUDIT_CORRECTIONS.md)、[tables案内](tables/README.md)参照。監査script・JSON/CSV・source snapshot・test XML・図QAはapp/out/final-research-audit/に保存。

## 最終test結果

Java: **30classes/182tests、failure0/error0/skipped0**。test --rerun-tasksで実行、build成功（build内testはUP-TO-DATE）。Temurin21.0.11/Gradle9.6.1/JUnit5.13.4。

Python: **180 passed in126.37s**、exit0。継承120件を含み追加60件（request guard8、validator13、finite/joint21、v2 estimator2/producer4、t区間4、resolver3、plot5）。Python3.13.14、NumPy2.5.1/pandas3.0.3/SciPy1.18.0/pytest9.1.1。

~~~powershell
$env:GRADLE_USER_HOME = 'C:\Users\yoshi\AppData\Local\Temp\spp-phase3-gradle-hyAwBh\user-home'
.\gradlew.bat test --no-daemon --offline --project-cache-dir 'C:\Users\yoshi\AppData\Local\Temp\spp-phase3-gradle-hyAwBh\project-cache' --rerun-tasks --warning-mode all --console plain
.\gradlew.bat build --no-daemon --offline --project-cache-dir 'C:\Users\yoshi\AppData\Local\Temp\spp-phase3-gradle-hyAwBh\project-cache' --warning-mode all --console plain
python.exe -m pytest analysis/tests
~~~

初回default Gradleはdistribution取得のnetwork拒否、既存cacheによるsandbox retryはNIO JARアクセス拒否でテスト未起動。研究コードを変更せず自動承認された実行制限外の同条件で全testを実行した。これは科学的test failureではない。BLAS threads1/MPLtemp/bytecodeoffでPythonを実行した。ログ・実行exit・JUnit全XML・原本SHAscriptは[evidence/phase16-root](../app/out/final-research-audit/evidence/phase16-root/)に保存。

## Git状態

main/HEAD不変。継承8modified/5untrackedを保持。最終24modified/20untracked。git diff --checkは出力なし、Git追跡app/outは0、raw/manifests/prereg/app/srcのdiffなし。未commitでありユーザー変更をrevertしていない。24tracked変更は647 insertions/254 deletions。全パス/サイズ・開始時との差は[最終Git証拠](../app/out/final-research-audit/evidence/phase16-root/final_git_verification.json)参照。変更/新規ファイルの最大サイズは約51KBで大容量データの誤追跡はない。commit/push/reset/clean/rebaseは未実行。

## 卒論執筆へ進んでよいか

**YES。** 正式訂正値を使用し、上の主張範囲・統計的限界・事前/事後の区別を明記すること。普遍性や熱力学的転移次数を確定した卒論結論には進めない。
