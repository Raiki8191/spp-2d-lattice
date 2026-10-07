# Python解析監査の補正記録・成果物参照台帳

この文書は、Phase 4Fを引き継いだ連続監査の訂正・来歴・成果物参照を記録する。Phase 4Fで意図的に残された未commit変更を監査baselineとして保持した。Phase 4〜15の再監査は完了し、Phase 16の最終tests・保護SHA照合も完了した。全Phaseの判定と卒論で安全に使用できる結論は[最終研究監査報告](FINAL_RESEARCH_AUDIT.md)、卒論表の列別出典は[tables/README.md](tables/README.md)を参照する。

**Phase 4判定: REPAIRED。** 有限C主解析、joint/shift、scaling-v2の25,000 finite-limit refitは正式生成・独立検算済み。B4の点/bootstrap開始点不一致と、v2 producerの全fit失敗時の区間flag処理は修正・回帰検証済み。今回の正式25,000 fitは全収束し、post-generation failure handling修正による正式数値への影響は0。Phase 5〜15でraw・停止条件・科学的支持範囲との縦照合を完了した。

## 変更範囲と証拠の保持

ユーザーの連続監査指示に従い、既存仕様から期待挙動が一意に決まるCLASS Bを修正した。raw simulation results、run metadata、manifestの実験事実、original seeds、事前登録原本、事前登録予測原本、完成済み実験データ、Git履歴は修正対象にしていない。旧derived成果物は残し、訂正成果物を別ディレクトリへ生成した。大規模simulation、commit、push、reset、clean、rebaseは実行していない。

継承baselineはbranch main、HEAD b40df04cadd6f6e2c838bd7ce628bff6b59262fd。Phase 4F由来の変更8ファイル・新規5項目を保持した。連続監査開始時の保護対象スナップショットは1,895ファイル、2,139,750,724 bytesである。最終[保護SHA照合](../app/out/final-research-audit/evidence/phase16-root/final_immutable_verification.json)はbaseline全1,895ファイル・2,139,750,724 bytesを再照合して変更0、errors=[]。baselineを再取得して差を消していない。最終Git状態は[最終監査報告](FINAL_RESEARCH_AUDIT.md)に記載する。

Phase 4Fの方法・訂正済みUNBOUNDED正式成果物・事前登録との区別は、[UNBOUNDED_BOOTSTRAP_CORRECTION.md](UNBOUNDED_BOOTSTRAP_CORRECTION.md)を参照する。主fit、RSS、AICc、BICは継承訂正時も不変であり、旧quick bootstrapから得た不確実性だけを現行値へ置き換える。

## 成果物の状態

状態はファイル全体と列・行を区別して適用する。同じ旧CSV内で、点推定値が現行でも区間が失効している場合がある。

| 状態 | 意味 |
|---|---|
| CURRENT | 現行の定義・点推定値・実験事実として参照する。 |
| CORRECTED | 検証された訂正成果物。該当する旧derived値の代わりに参照する。 |
| SUPERSEDED | 現行推定器と不整合な旧区間等。現在の科学的根拠には使わない。 |
| HISTORICAL | 当時の記録・予測・分析結果として保持する。現在の訂正を遡って事前登録したことにはしない。 |

| 対象 | 現行の参照先・状態 |
|---|---|
| raw、run metadata、manifest、seed、事前登録原本 | 保存された実験事実・歴史的証拠。訂正bootstrapで変更しない。 |
| v1/v2 run-derived、condition summary | CURRENT。全cached runの集計、全rawの不変条件、停止延長prefixと主要eventのtail boundをPhase 6/7で独立照合済み。 |
| scaling-v3有限Cの点fit | [finite_correction_fits.csv](../app/out/scaling-v3-analysis/finite_correction_fits.csv)の既存点推定値はCURRENT。 |
| 有限C主解析の区間 | [finite_primary_corrected_table.csv](../app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)、[bootstrap_intervals.csv](../app/out/scaling-v3-finite-bootstrap-corrected/bootstrap_intervals.csv)はCORRECTED。対象はL_min=8の14 simple fitと既存選択omegaの10 correction fit。 |
| joint・corrected shiftの点fit | [universality_model_fits.csv](../app/out/scaling-v3-analysis/universality_model_fits.csv)、[pseudocritical_shift_corrections.csv](../app/out/scaling-v3-analysis/pseudocritical_shift_corrections.csv)の点推定値はCURRENT。 |
| joint・corrected shiftの区間 | [bootstrap_intervals.csv](../app/out/scaling-v3-joint-shift-bootstrap-corrected/bootstrap_intervals.csv)はCORRECTED。全24 parameter区間を[interval_comparison.csv](../app/out/scaling-v3-joint-shift-bootstrap-corrected/interval_comparison.csv)で旧値と比較できる。 |
| v1/v2 log regressionの区間 | [v1_scaling_fit_results.csv](../app/out/scaling-log-ci-corrected/v1_scaling_fit_results.csv)、[v2_scaling_fit_results.csv](../app/out/scaling-log-ci-corrected/v2_scaling_fit_results.csv)の区間列はCORRECTED。点・SE・RSS・情報量規準は保存値を保持。 |
| v2 finite-limit bootstrap | [unbounded_model_bootstrap.csv](../app/out/scaling-v2-bootstrap-corrected/unbounded_model_bootstrap.csv)はCORRECTED。[旧/新区間比較](../app/out/scaling-v2-bootstrap-corrected/bootstrap_correction_comparison.csv)と[独立検証](../app/out/scaling-v2-bootstrap-corrected/audit_verification.json)を参照。 |
| scaling-v3 UNBOUNDEDの区間 | [scaling-v3-unbounded-bootstrap-corrected](../app/out/scaling-v3-unbounded-bootstrap-corrected/)のPhase 4F訂正値を使用する。 |
| UNBOUNDED v4〜v7の区間 | [v4](../app/out/unbounded-v4-bootstrap-corrected/)、[v5](../app/out/unbounded-v5-bootstrap-corrected/)、[v6](../app/out/unbounded-v6-bootstrap-corrected/)、[v7](../app/out/unbounded-v7-bootstrap-corrected/)のPhase 4F正式訂正値を使用する。 |
| UNBOUNDEDモデル履歴の区間付き比較 | [unbounded-history-bootstrap-corrected](../app/out/unbounded-history-bootstrap-corrected/)はCORRECTED。主fit・LOOは既存値、区間は訂正済みv4〜v7から解決する。 |
| 旧bootstrap CSV、旧図・旧研究記録 | HISTORICALとして保存。訂正対象に該当する旧区間・分布はSUPERSEDED。未訂正の別L_min等へこの検証結果を一般化しない。 |
| L=320/384事前登録原本・点予測原本 | HISTORICALな事前証拠として保持。事後訂正bootstrapを元の事前登録区間として引用しない。 |

## CLASS B修正一覧

### B1: 間引き測定を1 requestとして扱う危険

期待挙動は、1 accepted requestの前後を主解析の1物理eventとすること。[request_event.py](../analysis/request_event.py)のbuild_request_transitionsは、以前はremoved countの正の増加を1 eventとして扱い、STEP_INTERVALの間引き状態も受け入れていた。実在するmode-comparison/L=4/C=2のinterval測定ではaccepted増分が1,2,2,2で、4 transition中3件は複数requestをまとめたものだった。旧抽出にはC=2なのに見かけのpath length=3も生じた。

require_request_measurementsで科学解析CLIのmanifestをACCEPTED_REQUESTに限定し、counter列があるときは状態変化行でΔaccepted=1、非変化行でΔaccepted=0を要求した。[plot_request_event.py](../analysis/plot_request_event.py)、[plot_scaling.py](../analysis/plot_scaling.py)、scaling-v2 analyze/audit入口にも適用した。counterなしの手作りfixtureを下位builderで扱う場合は、完全なaccepted状態列であるという呼出側の前提が必要であり、科学解析CLIの検証を省略する理由にはならない。

回帰テストは[request event tests](../analysis/tests/test_request_event.py)の4追加ケースと[scaling-v2 request guards](../analysis/tests/test_scaling_v2_request_guards.py)の4件。後者は同じL/Cのmainとstop-auditを実際の小CSVで組み合わせ、正当な重複条件は許可し、interval manifestは出力前に拒否する。修正過程で一時的に導入された「main/auditを統合manifestとして検証する」案はこのレビューで棄却し、各manifestを個別検証した。研究成果物には使用されていない。

現在の本解析入力はACCEPTED_REQUESTであり、既存数値の変更・raw変更・成果物再生成は不要。今後の誤用を防ぐAPI検証の修正である。

### B2: raw validatorの不変条件不足

[validation.py](../analysis/validation.py)のvalidate_sweepは、NaN/InfのS、不可能なsecond cluster size、宣言runの欠落、初期step=0の欠落、run内seedの変更を含む独立改変コピー6種を以前は通していた。

修正は全numericの有限性、完全初期行、run内seed一定、cluster sizeの範囲・最大2成分の整合、連結状態のS=0、非連結状態の1≤S≤second size、manifest内の期待local run ID、condition内のrun seed重複に対する検証を追加した。履歴stageのrunは0..runs−1のlocal番号で検証され、その後の統合時にoffsetされる。未統合shardを完成済みmanifest全体として誤検証する仕様にはしていない。

[validation tests](../analysis/tests/test_validation.py)に13ケースを追加。改変コピー6種は修正後にすべて拒否。関連51件PASS。既存rawの代表2,413,020行・919 runは修正後validatorを通過した。現在データの異常が見つかったという意味ではなく、異常を見逃す検証体系の欠落を修正した。現在の数値変更はない。

### B3: finite-C joint/shift bootstrapの推定器・bounds不一致

点fitは元スケールのbounded nonlinear multistart fitなのに、旧U1/U2 bootstrapは単純なlog OLS、旧U3は異なるprofile探索・penalty、旧corrected shiftは別boundsのprofileだった。C=2 shiftの旧500標本にはq<0.05が23件、pc>1が12件（最大11.0529143245）含まれ、点fitのq∈[0.05,4]、pc∈[0,1]と不整合だった。

[scaling_v3.py](../analysis/scaling_v3.py)と[universality_fitting.py](../analysis/universality_fitting.py)で、point/bootstrap双方が同じ既存helper、開始点、目的関数、bounds、maxfevを呼ぶよう統一した。fit_corrected_shift_fixed_omegaは既存point処理の抽出であり、新しいモデル・L_min・omega・boundsは選んでいない。U1_C1/U1_C2は元のU1_independentの各指数、U2は元の自由omega共通指数、U3は元のomega=1共通指数へ明示対応させた。

[正式生成器](../analysis/scaling_v3_joint_shift_correction.py)は500 draw、seed=20260720、workers=4で11,000 parameter-report行を生成した。実際のmodel refitは8,500回、失敗は162回（parameter-reportでは273行）。元の500 drawによる旧OLS値7,500件を独立再計算して差0、draw statistics SHA-256も一致した。点fit37 shift行・70 universality行は修正前後bit-exact。[audit_verification.json](../app/out/scaling-v3-joint-shift-bootstrap-corrected/audit_verification.json)に検証・入力/出力SHA・コマンドを保存。[11件の回帰テスト](../analysis/tests/test_scaling_v3_joint_shift_estimator.py)はPASS。

| parameter区間の例 | 旧SUPERSEDED | CORRECTED |
|---|---:|---:|
| U2 P_after共通指数 | [0.094399, 0.119651] | [-0.091730, 0.208312] |
| U2 S_after共通指数 | [1.666903, 1.708240] | [1.603529, 2.130832] |
| U2 std(p_mid)共通指数 | [0.661411, 0.709993] | [0.572538, 0.881016] |
| C=2 corrected shift指数 | [0.018607, 1.525735] | [0.050000, 1.525566] |
| C=2 corrected shift pc | [0.491561, 0.867414] | [0.491856, 0.633288] |

旧bootstrapは不確実性を過度に小さく示していた。訂正後もsimple finite-C fitは別の証拠として残るが、補正付き共通指数を精密に確定したという主張は支えられない。負の指数を含む区間を理論値に合わせて切り取っていない。

S_after U1は68/500失敗、S_beforeはU1 43、U2 18、U3 33失敗。既存の正値予測gateを満たさないfitやmaxfev超過を失敗として保持した。区間は「収束・有効fitに条件付けたpercentile範囲」であり、失敗を含む無条件95% coverageは確認していない。diagnosticsのcovariance_failure_frequencyには未計算の失敗行も含まれるため、それだけから失敗原因を共分散と判断しない。

### B4: scaling-v2 finite-limit bootstrapの開始点不一致

[scaling_v2.py](../analysis/scaling_v2.py)の旧bootstrapはsingle start、対応するpointはfit_power_modelsのmultistartだった。期待挙動は同じdrawに同じpoint helperを適用すること。boundsやモデル形を変更せず、共通helperへ統一し、[新規2件の回帰テスト](../analysis/tests/test_scaling_v2_bootstrap_estimator.py)を追加し、[既存test_scaling_v2.py](../analysis/tests/test_scaling_v2.py)の1件を合わせた関連3件がPASS。

40 drawの独立比較では、L_min=32/sample=5のfinite limitが0.0003664784516996682から5.87231426975976e-12へ変化し、RSSは2.6218955662315e-5から2.6215939265617187e-5へ低下した。旧と新の最適化が同一ではなかったことを示す例であり、正式全区間の変化量とは区別する。

[訂正生成器](../analysis/scaling_v2_bootstrap_correction.py)による5 L_min×5,000 draw=25,000 refitを正式生成した。seed=20260720、workers=2。25,000/25,000が収束し、全draw・5 percentile区間・bounds（limit≥0、amplitude>0、0<q≤10）を独立確認した。保存された点fitは不変。[audit_verification.json](../app/out/scaling-v2-bootstrap-corrected/audit_verification.json)と[input provenance](../app/out/scaling-v2-bootstrap-corrected/correction_provenance.json)に記録した。

| L_min | 有効/要求draw | 訂正finite limit区間の上限 |
|---:|---:|---:|
| 8 | 5000/5000 | 0.2953216266682532 |
| 12 | 5000/5000 | 0.2476752170502492 |
| 16 | 5000/5000 | 0.2786576274695715 |
| 24 | 5000/5000 | 0.2845427774251629 |
| 32 | 5000/5000 | 0.2973262256393795 |

旧/新上限の最大絶対差は3.3775430030580367e-7で、この訂正によって有限極限の排除可否に関する解釈は変わらない。旧single-start bootstrap区間はSUPERSEDEDとして残す。formal fit/区間と、全fit失敗時にundefined区間をFalseのinterval_includes_zeroとして表示するproducerのAPI欠落は別問題である。後者もCLASS B修正を完了し、区間下端が非finiteならflagをpd.NA、全失敗時のboundary frequencyをNaNとした。[4ケースの回帰テスト](../analysis/tests/test_scaling_v2_bootstrap_correction.py)で修正前1失敗/3 PASSを再現、修正後の関連13件はPASS（1.56秒）。今回の25,000 fitはすべて収束したため正式CSVの数値への影響は0。[producer_post_generation_revision.json](../app/out/scaling-v2-bootstrap-corrected/producer_post_generation_revision.json)に正式生成時/修正後source SHA、diff、正式CSV・provenance・audit JSONのSHA不変、5 groupのpercentile/flag一致を記録した。

### B5: log regressionの95%区間におけるt分布近似

[scaling_fit.py](../analysis/scaling_fit.py)の_fit_rowは、df≥6では1.96を使っていた。有限nの通常OLS区間の既存定義に合わせ、全df=n−2についてStudent tの0.975分位点へ統一した。[新規4ケース](../analysis/tests/test_scaling_fit_intervals.py)と[既存2件](../analysis/tests/test_scaling_fit.py)を合わせた関連6件がPASS。

v1 96行・v2 144行、計240行を別ディレクトリへ訂正生成した。保存された点、slope SE、RSS、AICc、BICをコピー保持し、区間だけを更新した。[provenance](../app/out/scaling-log-ci-corrected/correction_provenance.json)と旧/新比較CSVを参照する。CSVを再読込してfitを独立再計算した際の最大AICc/BIC差約6.01e-10は丸めによる照合誤差であり、保存した情報量規準を書き換えたものではない。モデル形や有限サイズの系統誤差を含む区間へ変えたわけではない。

### B6: UNBOUNDED履歴が失効したquick bootstrapを再参照

v5/v6/v7解析の履歴比較経路が、Phase 4F後も旧区間を読み得た。[artifact_status.py](../analysis/artifact_status.py)のcorrected_unbounded_intervalsを追加し、[unbounded_v5.py](../analysis/unbounded_v5.py)、[v6](../analysis/unbounded_v6.py)、[v7](../analysis/unbounded_v7.py)から訂正済みの専用パスを参照する。訂正ファイル欠落時は失敗し、旧quick区間へ黙ってfallbackしない。

[artifact status tests](../analysis/tests/test_artifact_status.py)を含む関連18件PASS。新しい履歴ディレクトリにv4→v5比較16行、v4→v6比較56行、全model history 76行を生成した。[provenance](../app/out/unbounded-history-bootstrap-corrected/correction_provenance.json)には4つの訂正区間CSVのSHA-256を保存した。主fit・LOO・事前登録原本を変更せず、歴史的順位の点推定と現在訂正された不確実性を分けた。歴史的解釈・元予測と事後訂正の区別はPhase 11〜15で再監査済み。

## 有限C主解析の正式区間と生成器の検証

[finite_primary_corrected_table.csv](../app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)にはsimple 14行と既存選択omegaのcorrection 10行を保存した。L_min=8、使用L=8,12,16,24,32,48,64,96,128、500 draw、seed=20260720。点推定値は既存fitを独立再計算して一致し、simple 14行は先行するestimator consistency auditとも一致した。

以下はsimple fitの事実として照合した値であり、臨界指数の理論値再現や普遍性を判定した表ではない。P、std、jump、widthはL^(-x)、SはL^xの指数xを示す。P/S/stdはbounded nonlinear fit（元スケール）、jump/widthはlog OLSであり、推定器を混同しない。全14行が500/500有効fit。

| C | observable | 点指数x | 2.5–97.5 percentile |
|---|---|---:|---:|
| C=1 | P_before | 0.106997 | [0.092906, 0.120037] |
| C=1 | P_after | 0.104559 | [0.085716, 0.123933] |
| C=1 | S_before | 1.586319 | [1.440979, 1.766440] |
| C=1 | S_after | 1.772434 | [1.636596, 1.940062] |
| C=1 | std_p_mid | 0.669957 | [0.619438, 0.720652] |
| C=1 | delta_P_request | 0.112735 | [0.093617, 0.130109] |
| C=1 | transition_delta_p | 0.192369 | [0.181129, 0.204654] |
| C=2 | P_before | 0.117370 | [0.103927, 0.130509] |
| C=2 | P_after | 0.108595 | [0.092684, 0.126449] |
| C=2 | S_before | 1.590865 | [1.463514, 1.772335] |
| C=2 | S_after | 1.768067 | [1.616833, 1.935314] |
| C=2 | std_p_mid | 0.667847 | [0.611793, 0.731183] |
| C=2 | delta_P_request | 0.131630 | [0.114912, 0.148921] |
| C=2 | transition_delta_p | 0.180488 | [0.170152, 0.191778] |

C=1 S_afterの旧区間[1.6596044643066314, 1.7233962912781975]はSUPERSEDED。正式訂正値は点1.7724344469180395、percentile範囲[1.6365961736787689, 1.9400621511352605]である。旧simple区間で点を含まなかったC=1 S_after、C=2 S_before、C=2 S_afterも、[historical_interval_comparison.csv](../app/out/scaling-v3-finite-bootstrap-corrected/historical_interval_comparison.csv)に保存した。

正式12,000 fit行のうち11,951有効、49失敗。49件はすべてC=1 S_before/omega=0.5で、点1.42793115436967、451有効fitに条件付けた範囲[1.2287201092045241, 1.994072426073986]。失敗・boundary fitは保持した。補正fitのboundary_frequencyはC=1 S_after/omega=1が72.2%、C=2 S_before/omega=2が60.8%、C=2 S_after/omega=0.75が73.4%であり、補正指数を精密な根拠として扱えない。

正式生成後、1 drawの開発smokeで全fit失敗groupのformatterが停止する欠落を再現した。既存仕様に従い、全失敗ならNaN区間とrequested/converged/failedを明示し、bootstrap checkpointを先に保存するよう[生成器](../analysis/scaling_v3_finite_bootstrap_correction.py)を最小修正した。fit、draw、boundsを変更していない。正式生成時のv1 sourceは[generation_source_snapshot.py](../app/out/scaling-v3-finite-bootstrap-corrected/generation_source_snapshot.py)として保持し、後のv2 hardeningとの違いは[generator_revision_verification.json](../app/out/scaling-v3-finite-bootstrap-corrected/generator_revision_verification.json)で記録した。正式48区間を再計算して差0、14 simple audit照合の最大差2.22e-16、正式CSV数値はv2 formatterでも差0。[10件の回帰テスト](../analysis/tests/test_scaling_v3_finite_bootstrap_correction.py)はPASS。

[有限主解析の区間図](../app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_bootstrap_ci.png)と[bootstrap分布図](../app/out/scaling-v3-finite-bootstrap-corrected/bootstrap_exponent_distributions.png)も訂正CSVから生成した。旧図・旧CSVは削除していない。

## CLASS Aと解析定義の明確化

[ANALYSIS_DEFINITIONS.md](ANALYSIS_DEFINITIONS.md)のedge reconstructionの範囲は、早期停止traceで0..M0を観測できるとの記述が不正確だった。実際は0..K_final（観測された最終削除辺数）であり、未観測の後半を再構成しない。conventional meanのpeakは共通coverage、n_eff==runsの範囲で扱う。この文書説明を実装・既存データに合わせるCLASS A訂正で、rawやobservableは変更しない。

request-levelが主解析、edge-levelが副解析である。forward/reverse/shuffleの途中edge状態はrequestの物理測定状態を置換しない。shuffleは保存された1つの固定seed順序を比較する感度分析であり、全shuffle ensembleの推定ではない。

## 独立照合の範囲と数値

P=max cluster/N。Sは最大componentを1つだけ除いた有限componentのsize-weighted meanで、最大sizeのtieでは他の同size componentを残す。全連結ではS=0。この定義、initial row、accepted path全辺削除後の行、terminal rejectionの非event扱いをJava/Python/docsで照合した。

独立CSV/integer oracleで106,971 raw行・608 run・10,372比較を確認し、最大差2.78e-17。terminal unchanged行を除いてもevent/widthが変わらないことを既存smoke 10 runで確認した。edge側はL=2..5の80履歴・919状態を独立forward BFSとreverse union-findで比較し、代表pilotの229 raw状態・224 pathも確認した。これは全大規模raw全件の監査とは区別する。

cached v1の4,200 event行は、統合v2の対応4,200行と11指標でbit-exact。統合v2は5,800 event行と5,800 width行、27条件。独立csv/statistics集計2,640件（mean、ddof=1 std、SEM、median）とbootstrap endpoint 936件を再計算した。最大scaled丸め差は3.20e-16。v1に保存済みper-run width CSVは存在しないため、v1 width summaryは同じsource manifest/conditionを持つ統合v2 cached width列から照合し、代表rawによる独立width検算も併用した。

v1 summary bootstrapは2,000 draw/seed20260715、v2は5,000 draw/seed20260720。request summaryはcondition内のresampled indexをobservable間で共有し、direct bootstrap summaryはmetric別にdrawする。同じrun-level推定器の周辺区間でも有限drawのMonte Carlo差が生じる。direct summary CSVだけをpaired joint分布として扱わない。

情報量規準は独立353 fitのRSS・n・kから再計算し、228 percentile区間も照合した。この数は上記の新しいfinite/joint正式成果物の別検算と重複し得るため、総テスト件数として加算しない。

## 残存する統計・実装上の規約

### 情報量規準のk

既存実装はAIC=n log(RSS/n)+2k、AICc=AIC+2k(k+1)/(n-k-1)、BIC=n log(RSS/n)+k log n。kは回帰関数のfree parameter数で、残差分散の追加parameterを数えていない。simpleは2、固定omega correctionは3、自由omegaは4、UNBOUNDED zeroは2/finiteは3、joint U1は8/U2は7/U3固定1は5。Gaussianの共通常数も省略している。

n≤k+1ではAICcは有限な比較値にならない。同じobservable、同じL、同じRSS尺度・nのモデル間で比較する。残差分散を別parameterとする他の規約へ監査中に黙って変更していない。boundary・非識別性を伴うfitの情報量規準順位を、そのまま漸近的な物理結論の証明にしない。

### request時間幅

保存stepはrejectを含む総request countである。ただしwidthの「最後に閾値より上の状態」は、記録されたACCEPTED_REQUEST状態列で定義される。全rejected requestのplateau終端を記録した幅とは異なる。

P≤0.5へ初めてcrossするaccepted stepをT_H、その前の記録stepをA_H、P≤1/Lへのcrossと前の記録をT_L,A_Lとすると、保存幅はA_L−A_H。全request状態のplateau終端で定義する幅はT_L−T_Hで、差は(T_H−A_H)−(T_L−A_L)。L=8/C=1の既存200 runで平均保存幅1189.57、全request幅1219.73、199 runに差がある。pはreject中に不変なのでdelta_pにはこの差がない。

コードは現在のaccepted-state設計と一致している。新しい時間observableを選んで置換していない。卒論では「記録されたaccepted-state間の総request時間幅」と明記し、全request plateau終端そのものと混同しない。

### 共通seedと独立condition bootstrap

全5,800 cached run seedを独立64bit mixで再現して差0だが、unique seedは400だけ。runSeed=mix64(baseSeed+run)にL/Cが含まれず、異なる条件で元seedを共有する。Lによる乱数変換やCによる履歴分岐は、出力独立性の証明ではない。

現在のrun-level bootstrapはcondition/Lごとに独立resampleし、共通seedに由来するcross-L/C covarianceを含めない。特にfinite-C joint/shared-exponentの不確実性にもこの条件が付く。記述的な共通run相関の最大|r|は0.2073（L=64/C1とC2のp_mid、n=200）。多数比較を伴うこの値や非有意性から独立性を断定しない。

Phase 4Rの既存UNBOUNDED局所delta-method比較でzero-family SEの変化は約−2.3%〜+2.5%だったが、finite boundaryモデルやC1/C2 joint fitのcoverage確認ではない。paired seed-block感度解析という別手法へ黙って変更していない。現在の限界を明記した慎重な結論を述べるために、大規模再simulationが必須という証拠はない。

### bootstrap区間の範囲

run内requestを独立標本としてresampleせず、complete runを単位とする。失敗fitを保持し、boundary solutionも残す。区間は固定L_min、固定model、既存選択omega、採用optimizerの収束条件に対するpercentile範囲で、model-form、L_min/omega選択、有限サイズ系統誤差を自動的には含まない。数値が理論値を含むようにCI、L_min、bounds、outlierを変更していない。

## 実行・証拠への入口

正式derived生成時に実行したコマンドは次の通り。再実行先で旧成果物を上書きせず、生成器のoutput guardを守る。

~~~text
python.exe -B -m analysis.scaling_v3_finite_bootstrap_correction --bootstrap-samples 500 --seed 20260720 --output app/out/scaling-v3-finite-bootstrap-corrected
python.exe -B -m analysis.scaling_v3_joint_shift_correction --bootstrap-samples 500 --workers 4
~~~

個別回帰検証の記録はrequest/validation関連51 PASS、stop-audit guard 4 PASS、joint/shift新規11 PASS、finite generator 10 PASS、v2 bootstrap関連3 PASS（新規2件＋既存1件）・producer修正関連13 PASS（新規4ケース）、log CI関連6 PASS（新規4ケース＋既存2件）、history関連18 PASS、edge関連19 PASS。これらはsuiteの重複を含み、最終全Python suite件数ではない。最終Javaは30 classes・182 tests・failure/error/skipped 0、build成功。Pythonは180 PASS（126.37秒）。実行ログ・環境上の再試行・保護SHAは[phase16-root](../app/out/final-research-audit/evidence/phase16-root/)と[最終監査報告](FINAL_RESEARCH_AUDIT.md)を参照する。

Phase 4時点の一時検証ディレクトリ（来歴として保持）:

- C:/Users/yoshi/AppData/Local/Temp/spp-p4-semantics-f5nDTu: Phase4_semantics_report.md、Phase4_aggregation_conventions_report.md、独立raw/集計/seed/width検算JSON、pytest XML。
- C:/Users/yoshi/AppData/Local/Temp/spp-p4-edge-l1olts: phase4_edge_report.md、phase4_finite_bootstrap_report.md、finite formal検証・pytest記録。
- C:/Users/yoshi/AppData/Local/Temp/spp-p4-fit-trYl4f: Phase4_fit_report.md、fit_audit_summary.json、point_invariance.json、draw_identity.json、formal_verification.json、pytest記録。
- C:/Users/yoshi/AppData/Local/Temp/spp-continuous-audit-bMx4sU: audit_working_record.json、phase4_criteria_quantiles.json、v2再生成ログ、t区間・履歴訂正スクリプト。

tempの証拠だけに依存する正式成果物にはしていない。有限/joint/Phase 4Fの専用ディレクトリにprovenance、input/source/output SHA、正式draw、diagnostics、訂正前後比較を保存した。連続監査証拠は[final-research-audit/evidence](../app/out/final-research-audit/evidence/)へ保全し、各Phaseの報告・検算器・SHAから追跡できる。

## Phase 5: pilot timingと旧smoke図の参照（CLASS A）

Phase 5の独立集計は対象5実験48条件・243 run・196,587 raw行に対して736,418比較を行い、physical/run/condition集約の不一致はなかった。補助177比較と代表8図の画素・SHA完全一致も確認した。証拠は[phase5-summary report](../app/out/final-research-audit/evidence/phase5-summary/phase5_summary_report.md)と[検算JSON](../app/out/final-research-audit/evidence/phase5-summary/phase5_summary_verification.json)を参照する。後続Phaseの科学的評価は別扱い。

[旧pilot_summary.csv](../app/out/sweep-pilot/pilot_summary.csv)のelapsed_msは[execution_times.csv](../app/out/sweep-pilot/execution_times.csv)の現行値と9条件すべてで異なる（合計422ms対545ms）。analysis/pilot_report.py::create_pilot_summaryはtiming列をそのままコピーするため、分析時間との定義差ではない。physical summary列は全てrawと一致し、summaryのmtimeがtimingより約49分前であることは旧snapshotの解釈を支持する。ただしmtimeのみで再実行履歴を断定しない。

参照案内を訂正し、pilot_summaryのphysical列はCURRENT、elapsed_ms列はHISTORICALと区別する。現在の条件時間を引用するならexecution_timesを優先する。時間はJVM warm-up、I/O、停止位置、millisecond切捨て等を含むwall-clock記録で、物理量の再現性の証拠や直接の計算量指数にしない。旧CSVを上書き・削除していない。

sweep-smoke/figuresのLを含まない汎用名3図は現行multi-L plotterの出力対象外としてHISTORICAL扱いとする。現行参照はL=4_ / L=6_で始まる6図で、既存rawから再現して画素・SHA完全一致を確認した。旧図を削除しない。これは参照案内のCLASS Aであり、物理データ・研究結論に変更はない。


## Phase 7: v2参照・表示桁の訂正（CLASS A5/A6）

[semantic report](../app/out/final-research-audit/evidence/phase7-semantic/phase7_semantic_report.md)と[独立検算JSON](../app/out/final-research-audit/evidence/phase7-semantic/phase7_semantic_verification.json)に、benchmark30run・288,329raw行、14runtime projection、raw由来の停止150runから12条件summary、27条件/5,800cachedrunのsource接続、L128 direct-bootstrap36metric行の検算を保存した。41,785比較の不一致0、最大scaled差3.20e-16。benchmark8図はtemp再生成と元図の画素・SHAが完全一致した。

SCALING_V2_RESULTSの旧bootstrap SUPERSEDED案内を第8節のUNBOUNDED finite-limitに限定し、正常な第5節のrun平均CIはbootstrap_summary.csvを参照すると明記した。監査中に広すぎる案内を加えた点も訂正対象である。停止監査のpost_request_conventional_peak_after_oldは各runのraw S最大フラグの別名であり、common-p ensemble平均Sのconventional peakそのものではない。文書で区別した。科学量の新定義は選んでいない。

文書表示の3末尾桁も一意訂正した：L128 UNBOUNDED P_after平均0.42646→0.42647（保存値0.42646514892578125）、C1 p_mid CI下端0.49420→0.49419（0.49419472041092516）、C2 P_before CI下端0.52389→0.52388（0.5238847045898437）。最大表示差1e-5、raw/既存CSV/fit変更0。訂正前の不一致と訂正後PASSを両方保全した。

runtime projectionは5run・停止multiplier0.5の歴史的候補予測で、mainのmultiplier1.0の実測と一致を要求しない。memory byte列も当時のPandas/source構成に依存するtelemetryである。本追記はsemantic/provenance担当範囲の結果であり、Phase7全体のFSS判定または後続Phaseの合格を代行しない。


## Phase 8: C1のRSS選好・相関・L_min表現（CLASS A7/A8）

[semantic report](../app/out/final-research-audit/evidence/phase8-semantic/phase8_semantic_report.md)と[検算JSON](../app/out/final-research-audit/evidence/phase8-semantic/phase8_semantic_verification.json)に、C1正式12group/6,000要求fitの保存sample percentile・mean・median・失敗/boundary数とpoint/table/source SHA照合を保存した。6,328比較PASS、最大scaled差1.42e-16。C1 S_after正式simple区間は[1.6365961737,1.9400621511]、S_before correctionの451/500有効/49失敗を再確認した。

V3§4の理論固定shiftは最小RSSではない。pc=.5/q=.75固定RSS2.59293145e-5、pc=.5/q自由2.50444160e-5、pc/q自由2.16589117e-5だが、既存k規約のAICc/BICは少数parameterの理論固定を選好する。『残差と情報量規準の双方で支持』を根拠の違いが分かる文言へ訂正し、『相関0.985』は最大絶対parameter相関と明記した。特定pc–qペアの値とは区別する。

V3§3のP_after安定性も弱化した。全サイズpointは参照に近いが、L_min全系列の範囲幅はbefore約.03030、after約.04623。L_min8..32では双方約.00585の変動、4点のL_min48ではbefore.136934/after.148132へずれる。全系列でafterが安定とは断定しない。既存point/CSV/CI/サイズ選択に変更0。

rawとの縦接続はPhase6/7の独立検算・source manifest対応を確認し、正式generator provenanceが同じv2run/summary SHAを参照することを照合した。訂正CI/分布2図と独立analytic C1残差図は画素・SHA完全一致。旧bootstrap図はSUPERSEDED、point曲線・残差図に旧CIの混入はない。

root指示による追加[注記付きCI図](../app/out/final-research-audit/evidence/phase8-semantic/finite_primary_ci_annotated.png)と[provenance](../app/out/final-research-audit/evidence/phase8-semantic/finite_primary_ci_annotated_provenance.json)は、正式値を保持して451/500有効・conditional percentile・fixed-omega有限range診断の脚注を追加した別名図。元15正式filesは不変。有限primaryのraw exponent boundsは[-5,5]で、[-2,4]等の他fit境界と混同しない。C2/Uの普遍性評価は本追記の担当範囲ではない。


## Phase 9: C2の支持範囲とpoint図欠落修復（B7、A9）

[報告](../app/out/final-research-audit/evidence/phase9-semantic/phase9_semantic_report.md)と[独立JS検算](../app/out/final-research-audit/evidence/phase9-semantic/phase9_semantic_verification.json)は、C2 finite12group、joint/shift24正式percentile、120jointpoint n/k/score、48同endpoint hyperscaling、本文10simple/20joint区間に151,569比較PASSを記録した。C1/C2の周辺CI重なりだけで同一普遍クラスを証明しない。C2 S_before/std simpleはordinary referenceを含まず、S_after/Pの整合可能性とは分ける。

正式bootstrapのcoverageはLmin8、U1独立8parameter、U2共通指数/別自由omega7parameter、U3共通指数/omega1固定5parameter。点fitのfreeU3は6parameter、fixedomega2とLmin16/32のpointにはomega1正式CIを転用しない。Lmin8/16/32はn18/14/10で、Lmin32 U1は残差自由度2・AICc分母1。U1 S_after68、S_before43、U2 S_before18、U3 S_before33/500のmodel失敗を保持した条件付きpercentileで、無条件95% coverageは未検証。

exact joint/finite boundはa[1e-12,1e6]、raw exponent[-5,5]、b[-20,20]、freeomega[.05,4]。shiftはpc[0,1]、a[-10,10]、q[.05,4]、b[-20,20]。コードの数値admissible flagは物理的漸近の許容性ではない。C2 S_after選択補正gamma2.089753、boundary73.4%、364/500drawのgamma>2はfinite-range診断で、S≤L²のleading asymptoteとして解釈しない。

B7は旧共有図U1の全NaN列選択と、P_before図のselected theory-fixed simple curve除外という描画欠落。2plot区画/2helperだけを最小修復し、新5＋関連21=26tests PASS。26既存nonfigure関数/全top-level constants・importsのASTは不変、point/seed/bootstrap変更0。別担当second reviewもPASS。[新図dir](../app/out/scaling-v3-shared-exponent-figure-corrected/README.md)の[共有指数図](../app/out/scaling-v3-shared-exponent-figure-corrected/c1_c2_shared_exponent_corrected.png)、[P_before図](../app/out/scaling-v3-shared-exponent-figure-corrected/simple_vs_corrected_P_before_corrected.png)、[provenance](../app/out/scaling-v3-shared-exponent-figure-corrected/correction_provenance.json)を参照する。旧PNG/CSV/formal provenanceは保存し、whole module SHAの変更がplotだけであることをsource前後snapshot/ASTで示した。

A9として、4start最小RSS≠global minimum、nested-model理想RSS不等式が保存local解で保証されないことを明記する。P_after U2の別start診断は両correction境界・非採用で、fixedomega2の選好と既存推定方針は変えていない。freejoint45fitのmaxcorr≥.99、70対象33数値採用/37境界、15群中6群は採用modelなし、という別fit監査の限界も維持する。

scoreはunweighted等残差分散Gaussian・回帰function k規約。残差分散をkに追加したPhase8感度ではC1std ΔAICc−.3411→+2.0589となった。既存scoreは変更せず、微小な改善を頑健な補正・普遍性根拠にしない。C1shift max|corr|.98534はq–aの符号−、q–pcは−.90686と別ペアである。共有seed covarianceとmodel/Lmin/omega選択誤差を現在bootstrapは含めない。


## Phase 10: request主解析とedge順序感度（A10）

主request eventは要求境界の辺集合だけで決まる。Javaは全path削除後にtrace observerとcluster測定へ進み、PythonのFSS/UNBOUNDED主量もrequest由来で、人工的な要求内edge順序へ依存しない。C1は同じevent・P/S before-after・deltaP・step・p_afterで一致する。request p_midとedge p_afterは1/(2M0)だけ違う座標規約であり、比較API/図は双方p_afterを用いる。独立64bit BigInt shuffle168vectorとmetadata/indexチェック217確認PASS、関連23テストPASS。

order-checkの独立edge event再集約18行・range30値・docs12セルは一致し、L64UB代表2図は独立DSU/eventから元PNG SHA/全画素まで再現した。初回8画素差は検算CSVのparser末尾丸めで、round_trip読込により解消し、既存解析/図変更0。証拠は `app/out/final-research-audit/evidence/phase10-semantic/`、全traceとC1の独立再構成は `phase10-edge/` に保全。

A10としてSCALING_V1_RESULTS§11を最小訂正：UB conventional rangeは縮むが、edge event平均rangeはL32の0.005151からL64の0.005310へ僅かに増え、両者の単調縮小を主張しない。各50run・固定3順序の感度はworst-orderや漸近消失の保証ではない。一様ordered pair/pathの理想モデルではsource/reverseの周辺分布は対称対応により同一であり、同じ有限履歴のpaired平均差を方向選好と解釈しない。固定shuffleは一様全順列ensembleの証明ではない。raw・table・元図・科学的主量の変更0。


## Phase 11: UNBOUNDED L≤128の歴史的支持範囲（A11/A12）

raw→request集約はPhase6/7証拠に接続し、Phase11 dataの9条件2200run・495値、fit担当の40＋24point/72LOO/保存29k bootstrapを照合。semantic担当は文書fit表20セル・外挿15セル・3予測サイズの現行区間共通交差・4F入力hashを含む58確認PASS。代表点model図と訂正finite-limit CDFの2枚は元PNG SHA/全画素まで一致し、新sim/fit/drawは0。証拠は `app/out/final-research-audit/evidence/phase11-semantic/`。

CURRENTなrequest run/summaryと主点fitはサイズ範囲を明記して使用する。L≤128の歴史モデル比較ではzero_logのAICc−85.638200/BIC−87.243751/LOO RMSE .008704958が比較候補内最良だが、Lmin依存とpower/logの競争を残す。CORRECTED uncertaintyはv2の `scaling-v2-bootstrap-corrected/`、v3の `scaling-v3-unbounded-bootstrap-corrected/`。v3有限極限区間power [2.065053e−17,.29628109735629915]、log [5.177459e−22,.28882739938850516]はliteralな0でなく数値的ゼロ境界を含む。SUPERSEDEDの旧quick bootstrapを正式fit CIへ使用しない。L≤128記録・追加計算案を現在の全サイズ結論と混ぜない。

A11はV1§9に当時の『真の不連続／弱い不連続』をHISTORICALとして残して用語・支持範囲を注記し、ゆっくりゼロへ減衰する可能性を明示した。最大単一request jumpのゼロ極限だけでは熱力学極限P(p)の連続性を証明せず、多数小jumpの累積や他の臨界点定義と区別する。p幅は非単調で、dt/N²の縮小と取り違えない。A12はV3§6のLOO RMSE末尾2セル .01116→.01115、.00871→.00870 をCSVから最小訂正。旧/訂正LOO72行のSHAは完全一致で、source差との初期推測は撤回した。最大転記変化1e−5、ランキング/科学値/raw/prereg変更0。


## Phase 12: L192履歴・区間案内・実行中央値（A13）

[semantic報告](../app/out/final-research-audit/evidence/phase12-semantic/phase12_semantic_report.md)の65確認は、50run=3 benchmark＋17 pilot＋30 main、同seed audit3、文書20modelセル、訂正主jump2区間、4F入力hash・Java core6file・代表2図の元SHA/全画素一致を含む。新sim/fit/draw0。正式finite-limitはpower [6.063111e-19,.2972719367697124]、log [1.302514e-21,.2922683953852698]。V4冒頭と旧区間inlineにHISTORICAL/SUPERSEDEDと現行リンクを追加し、当時の生成コマンドを再実行して完了成果物を上書きしない。v3_v4_information_gain.csv旧CI欄は当時の値であり現行formal区間ではない。

main30の元表median1.421秒はJava lower median、通常medianは1.430秒で定義注記を追加した。raw・点推定・元CSV/PNG変更0。初回v4commitは実験完了後だが、当時のworktree実行→commitとは整合し、Java物理coreは当該blobと現行で一致。実行source/binary hash、実際のresume回数は記録されていないため、その保証を主張しない。今回の53shardの独立byte/terminal/metadata検算で現在の整合を補完した。4F metadata内v5 codehashと現行の差は既知のPhase4歴史区間resolverだけで、v4/fit/boot core hashと元provenanceは保持した。Lmin一律zero支持や熱力学極限の次数を断定しない。


## Phase 13: L256履歴・訂正区間・図枚数（A14）

[semantic報告](../app/out/final-research-audit/evidence/phase13-semantic/phase13_semantic_report.md)の136確認は、20主run=benchmark3＋pilot17、同seed audit3、model24/単一サイズ20/外挿8の文書セル、v4固定予測と歴史・訂正双方の被覆、4F入力hash、Java8fileの初回blob/現行一致を含む。主点図と訂正CDF2図は元PNG SHA/全画素まで一致、新sim/fit/draw0。正式finite-limitはpower [7.005897e-21,.29582631138191345]、log [1.476253e-22,.29031000578315364]。CURRENTはL≤256観測/点fit、CORRECTED uncertaintyはunbounded-v5-bootstrap-corrected。旧v4_v5_model_comparison区間幅はHISTORICAL/SUPERSEDEDで、現行履歴比較はunbounded-history-bootstrap-corrected/v4_v5_comparison.csvへ接続する。

A14でV5冒頭と旧CI inline/現行リンク、当時command、永続log未確認のresume実施記録という証拠範囲を最小注記し、15図を実在/生成17図へ訂正した。20run中央値3.427秒は通常中央値で正しく変更しない（Java progress lower medianなら3.410秒と別）。初回commitはstage完了後、実行source/binary hashは無い。現在23shardのbyte/metadata/prefix検算で現存整合を補完するが、実際のresume回数や当時実行binaryのhash保証は主張しない。主zero-log順位は維持、4予測の被覆はモデル識別の証明でなく、境界集中power11.6%/log36.8%・高相関・Lmin依存を残す。raw/既存CSV/PNG/prereg変更0。


## Phase 14: L320原登録の保持・時系列・候補限定（A15）

[semantic報告](../app/out/final-research-audit/evidence/phase14-semantic/phase14_semantic_report.md)と[audit proof](../app/out/final-research-audit/evidence/phase14-semantic/audit_verification.json)に1583独立確認・guard1test PASSを保全。原登録は6観測×4model=24行（20主＋4探索S_peak）。原MD/reference CSVは0ef0cb5cでaddition-only一回、以後committed/workingdiff空。MD blob SHA897701c5…とworkingはbyte一致。CSVはGitLF blob06961241…とworkspaceCRLF cf74ca86…の25改行差だけで全値/正規化text一致、事後改変の形跡なし。登録source4SHAも現存入力と一致。

予測freeze11:01:24.488978UTC、登録commit11:02:24、最初L320sim11:03:40.6436174、audit終了11:07:28.8954304、V6commit11:25:38と整合。全23runが登録commit後に開始。原生成guardは実L320出力の存在で書込前に拒否し、原本編集/再生成0。後日S_peak helperはtarget_Lをparameter化しただけでdefault320/他関数AST不変。手元Git/metadataの整合であり、外部timestamp/実行binary hash sealは主張しない。

全24固定point/PI/scoreと文書引用を独立検算。原fixed PIは事前証拠、4F20主retrospective corrected PIは事後訂正で、S_peak探索4件へ転用しない。原meanCI外4件は既知Phase4 defectをfrozenのまま保持し、現行intervalとは区別する。現行finite-limit主jumpはpower [7.839682e-23,.26529939459513097]、log [7.773895e-23,.2167621549656135]、数値ゼロ率63%/86.8%。原PI図と訂正CDF2図は元PNG SHA/全画素一致、新sim/fit/draw0。

A15でV6 size-scope/current uncertainty案内、当時生成command、18→実19図、L192事後再構成/L256保存事前予測/L320正式登録の根拠差、候補・現行制約に限定したzero-powerのAICc/BIC選好を最小訂正。全登録PIから外れたL320meanはモデル識別や∞転移次数を単独確定せず、原本/raw/CSV/PNG/prereg変更0。


## Phase 15: L384原登録・卒論表・性能source・区間定義（A16）

[semantic報告](../app/out/final-research-audit/evidence/phase15-semantic/phase15_semantic_report.md)の2061確認とguard1testはPASS。原登録は24行（20主＋4探索S_peak）、両原本d0117df7でaddition-only一回・以後diff空。MD blob/working SHA81fc8e77… byte一致、CSV GitLF34ef528c…/workingCRLF4b74ed51…は25改行だけ違い全値一致、4F baseline不変。登録commit11:45:38UTC→firstsim11:46:44.7836983（66.783698秒後）→audit終了11:59:12→V7commit12:30:40と整合。原CSV generation_timestamp_utcはsourcecommitter時刻、実生成時計ではなく、原欄を変更しない。

全24point/PI/score/density・登録入力13SHA、正式currentCI・文書表を独立照合。卒論SUMMARY13行は全field HEAD不変、各L fixedseed20260720/5000直接mean drawも一致。MODEL_HISTORY16行はpoint/LOO/score/rank等nonCI全field HEAD exact、8finite行16区間セルのみ4F正式CIへ訂正済み。現行主jump有限極限はpower [3.444047e-23,.24804549549439403]、log [5.107526e-23,.10002518030960122]。数値ゼロ集中66.8%/95%を∞ゼロ極限証明にしない。代表主図＋訂正CDFの元SHA/全画素一致、新sim/fit/nonlinearboot0（軽量mean CIの再検算65000draw）。

A16でV7に原/current/retrospective案内、当時command、generation時刻欄の意味、性能sourceを最小訂正。metadata和38.467＋254.907=293.374秒、pilotspan255.197秒と別。v6実CSV予測293.538816との差−.05615%で、旧v5由来235秒/9%の混在を解消。逐次2/3はL256平均CIとL320/384残差合成PIで共通95%校正不可。parametric率80.6%/82.6%は独立Gaussian mean/SEM・数値floor・2zero候補AICc選択という条件付き診断で、物理真クラス確率/finite排除率ではない。原固定PI・事後訂正20区間・S_peak探索4件の根拠を混ぜず、raw/原prereg/既存CSV/PNGの本担当変更0。


## Phase 16: 最終案内・Java検証・原本保護

CURRENT/CORRECTED/SUPERSEDED/HISTORICALをファイル全体と列別に区別し、[卒論表のREADME](tables/README.md)を追加した。元2 CSVは変更しない。全Phaseの科学的判定と正式値は[最終研究監査報告](FINAL_RESEARCH_AUDIT.md)へ集約する。

Java production/test 63ファイルはPhase 3の記録SHAと現行SHAが全一致。恒常SPPModelValidationTestはL2全16状態・576距離/受付比較、L3は24標本状態・6,912比較で、L3全状態検証ではない。ShortestPathFinderTestの一様性試験は対称2経路4,000抽選のみで、非対称predecessor重みやlong超過を単独では証明しない。

これを補うPhase 3独立oracleはL3全4,096状態・2,359,296 queries、独立Floyd距離＋DFS最短路数、非対称count 1:2の完全3経路各2/6、C(68,34)=28,453,041,475,240,576,740（65 bits）、randomBelowの841決定的scriptsを検証した。最大成分1つ除外のS、accepted path全辺削除後のobserver、initial/terminal rejected行、pair/path RNG分離は独立成分・request・CSV検証で補完した。元検算ソースとPhase 3記録を[phase16-semantic](../app/out/final-research-audit/evidence/phase16-semantic/)へ保全した。これは今回新しい大規模simulationを実行した件数ではない。

最終全testsはJava182・Python180 PASS。Gradleの初回network/NIO制約でtest未起動だった試行もログに保持し、既存Phase 3 cache・同source・同引数による承認済み再実行で成功した。buildのtestはUP-TO-DATEであり、2回の独立182件実行と数えない。保護原本1,895ファイルは全SHA不変。新しい科学的方針やraw/原登録変更を必要とするCLASS Cは担当範囲で検出していない。

最終Python件数の増分は継承120＋新規60=180。新規60の内訳はrequest guard8、validator13、finite/joint21、v2 estimator/producer6、Student t4、resolver3、plot5。関連suite件数を新規件数に加算しない。B4の以前の「3件追加」とlog CIの「6件」表記は新規/既存の区別が不十分だったため、このA2 bookkeepingで訂正した。研究code/resultsと元test実行記録は変更していない。

A2最終草稿の転記訂正: UNBOUNDEDをInteger.MAX_VALUEと記した初回草稿を、実際のSPPSweepPlan.conditions / SPPUnboundedL192.Stage.budgetのC=N=L²へ訂正した。初回レビューでは実験budget値の転記を見落としたが、最短距離≤N−1による「連結なら受理」の等価性・研究source・数値は不変。訂正後の独立確認は[unbounded_budget_final_review.json](../app/out/final-research-audit/evidence/phase16-semantic/unbounded_budget_final_review.json)。
