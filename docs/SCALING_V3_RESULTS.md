# scaling-v3 有限サイズ補正解析

> **UNBOUNDED bootstrap訂正（Phase 4F、2026-10-07）**：本文のUNBOUNDEDモデルfit区間は、主fitと異なる旧bootstrap推定器による当時の出力である。正式な訂正版は[UNBOUNDED_BOOTSTRAP_CORRECTION.md](UNBOUNDED_BOOTSTRAP_CORRECTION.md)と`app/out/scaling-v3-unbounded-bootstrap-corrected/`を参照する。v3固有の主fit仕様を保持して訂正した。有限CのS_after修正済み成果物は別経路で、このUNBOUNDED訂正による変更はない。


> **有限C bootstrap訂正（Phase 4追加監査、2026-10-07）**：点fitは保持し、finite-primary、U1/U2/U3、corrected shiftのbootstrapを対応する点推定器・bounds・multistartへ統一した。現行区間は[有限主解析正式表](../app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)、[joint/shift正式区間](../app/out/scaling-v3-joint-shift-bootstrap-corrected/bootstrap_intervals.csv)、[補正来歴台帳](ANALYSIS_AUDIT_CORRECTIONS.md)を参照する。本文§3–5の区間はこれらへ照合・訂正した。旧derived値は削除せずHISTORICAL、該当する旧区間・精度主張はSUPERSEDEDとして保存する。
>
> 本書のサイズ範囲はscaling-v3当時のL≤128である。§6–9のUNBOUNDED解釈・追加計算案は当時の記録であり、現在のL=384までの結論に置き換えない。今回の区間訂正は後続Phaseの科学的判定完了を意味しない。

## 1. 目的と使用データ

scaling-v3 は新しいシミュレーションを行わず、確定済みの scaling-v1/v2 の run-level 集約値を再解析する。目的は、単純な冪則に残る有限サイズ補正を可視化し、`C=1` の既知指数との整合性、`C=2` との普遍性、および UNBOUNDED の最大 request jump の漸近挙動を評価することである。

- 線形サイズ: `L = 8, 12, 16, 24, 32, 48, 64, 96, 128`
- 条件: `C=1`, `C=2`, `UNBOUNDED`
- 有限 `C`: 各サイズ 200 runs
- UNBOUNDED: `L<=64` は200 runs、`L=96,128` は400 runs
- 入力: `app/out/scaling-v2-analysis/request_event_{runs,summary}.csv` と `transition_width_{runs,summary}.csv`
- runtime 入力: `app/out/scaling-v2-main/**/run_summary.csv`
- bootstrap: complete run再標本化500回、seed `20260720`。主要P/S/std、joint、corrected shiftの区間は対応する点fitと同じ元スケールのbounded nonlinear multistartを適用する。jump/widthのsimple fitは既存のlog OLSを保持する。旧生成物との不整合は [SCALING_V3_S_AFTER_AUDIT.md](SCALING_V3_S_AFTER_AUDIT.md) と [ANALYSIS_AUDIT_CORRECTIONS.md](ANALYSIS_AUDIT_CORRECTIONS.md) を参照。
- 当時の出力: `app/out/scaling-v3-analysis/`（HISTORICAL。点fitはCURRENTだが、訂正対象のbootstrap区間・分布はSUPERSEDED）。正式訂正出力は冒頭の専用ディレクトリを使用する。

解析は既存CSVを読み取るだけであり、本計算データを再生成・変更・削除しない。

## 2. モデルと判定規則

主要量 `P_before`, `P_after`, `S_before`, `S_after`, `std(p_mid)` に対して、

```text
Y(L) = a L^x
Y(L) = a L^x (1 + b L^(-omega))
     = a L^x + (ab) L^(x-omega)
```

を比較した。`omega` は自由 fit と、`0.5, 0.75, 1.0, 1.5, 2.0` の固定感度解析に分けた。振幅、指数、補正係数、補正指数にはコード上で境界を設定し、複数初期値から最小RSS解を選んだ。`n <= k+1` の fit は AICc が定義できないため不採用とした。収束失敗、境界解、共分散非有限、最大パラメーター相関はCSVへ残した。

`L_min = 8, 12, 16, 24, 32, 48` の系列を単純冪則と自由補正 fit で調べた。固定 `omega` の全感度解析は全9サイズを用いる `L_min=8` で行った。同時 fit は点数とパラメーター数の釣り合いを保つため `L_min=8,16,32` とした。モデル比較には同じ応答量内の AICc と BICを用いる。値のスケールが違う別観測量間で AICc/BIC を比較していない。

`C=1` と `C=2` の同時 fit は次の通りである。

- U1: 条件ごとに主指数と `omega` を独立化
- U2: 主指数を共通化し、振幅・補正係数・`omega` は条件別
- U3: 主指数と `omega` を共通化し、振幅・補正係数は条件別
- U3固定感度: 共通 `omega` を上記5値へ固定

疑似臨界点シフトは

```text
p_c(L) = p_c + a L^(-1/nu)
p_c(L) = p_c + a L^(-1/nu) (1 + b L^(-omega))
```

で比較した。`C=1` では `p_c=0.5` 固定、`p_c` 自由、さらに `p_c=0.5` かつ `1/nu=0.75` 固定を区別した。

UNBOUNDED には過剰な候補を加えず、ゼロ漸近と有限値漸近について冪則と対数的な遅い収束を各1種類比較した。

```text
zero power:   Y = a L^(-x)
finite power: Y = Y_inf + a L^(-x)
zero log:     Y = a (log L)^(-x)
finite log:   Y = Y_inf + a (log L)^(-x)
```

全モデルで AICc/BIC、`L_min`、leave-one-size-out (LOO)、bootstrap、境界到達を確認した。外挿値は予測であり観測ではない。

## 3. C=1 と既知指数

二次元通常パーコレーションの参照値は `beta/nu=5/48=0.104167`, `gamma/nu=43/24=1.791667`, `1/nu=3/4=0.75` である。

全サイズの自由な単純冪則 fit は次の通りである。

| 量 | 推定指数 | bootstrap percentile範囲 | 参照値 |
|---|---:|---:|---:|
| P_before | 0.106997 | [0.09291, 0.12004] | 0.104167 |
| P_after | 0.104559 | [0.08572, 0.12393] | 0.104167 |
| S_before | 1.586319 | [1.44098, 1.76644] | 1.791667 |
| S_after | 1.772434 | [1.63660, 1.94006] | 1.791667 |

`P_before` の単純自由 fit は AICc `-80.03`、理論指数固定 fit は `-83.15`、`P_after` はそれぞれ `-82.86`, `-86.28` で、少ないパラメーターの理論固定モデルが選好された。固定 `omega` 補正や自由 `omega` は AICc を改善せず、自由 `omega` の `P_before` は下限 `omega=0.05` に到達した。したがって「補正項を入れたから理論値へ近づいた」のではなく、Pは補正なしでも理論値と整合的である。全サイズの点推定では `P_after` が参照値に近い。`L_min=8..32` のP指数はbefore/afterとも小幅に変動するが、4点の `L_min=48` ではbefore `0.136934`、after `0.148132` へずれる。全系列でafterの方が安定しているとは断定しない。

Sは `before` と `after` の定義依存性が大きい。`S_after` は単純 fitで参照値に近く、`L_min=8..48` で `1.7724..1.7923` と比較的安定する。一方 `S_before` は `1.5863..1.5838`（途中の揺れを含む）で理論値より低い。補正モデルは高相関・境界解を生じ、Sの差を安定に解消しなかった。監査前の `S_after` 区間 `[1.65960,1.72340]` は対数OLS bootstrapであり、元スケールfitの点推定と同じ推定量ではなかった。同じ推定量へ揃えた区間は `[1.63660,1.94006]` で点推定を含む。ただしrun再標本化だけではサイズ選択やモデル誤指定などの系統誤差を表さない。

`std(p_mid)` は単純 fit `0.66996` に対して固定 `omega=2` 補正が `0.78289` となり、AICcは `-99.82` から `-100.16` へわずかに改善した。しかし固定 `omega` 間の推定幅が大きく、自由 `omega` は不安定である。`1/nu=0.75` との整合性改善は示唆的だが決定的ではない。現行スコアは平均関数のパラメーター数kを使用する。Gaussian残差分散も数えるk+1の感度診断では、補正−simpleのΔAICcは−0.34110から+2.05890へ反転し、simpleが選好される。BIC順位は不変である。従ってomega=2の選択はスコア規約に条件付きで、真のnuの回復を示さない。

上のsimple P/Sとstdの正式bootstrapはすべて500/500有効fitである。有限主解析全体（simple 14 group＋既存選択omegaのcorrection 10 group）は12,000 fit中49失敗し、49件はC=1 S_before/omega=0.5だけに生じた。その点指数1.427931、451/500有効fitに条件付けた範囲は[1.22872, 1.99407]。C=1 S_after/omega=1のboundary frequencyは72.2%、C=2 S_before/omega=2は60.8%、C=2 S_after/omega=0.75は73.4%であり、補正指数を精密に確定したと扱わない。[正式diagnostics](../app/out/scaling-v3-finite-bootstrap-corrected/bootstrap_diagnostics.csv)と[生成器検証](../app/out/scaling-v3-finite-bootstrap-corrected/generator_revision_verification.json)に失敗・boundaryを保持した。

## 4. 疑似臨界点シフト

| 条件 | モデル | p_c | 1/nu | AICc | BIC | 診断 |
|---|---|---:|---:|---:|---:|---|
| C=1 | `p_c=0.5`, `1/nu=0.75` 固定 | 0.5 | 0.75 | -112.24 | -112.62 | 最良、1パラメーター |
| C=1 | `p_c=0.5`, 指数自由 | 0.5 | 0.71363 | -109.13 | -110.73 | 有効 |
| C=1 | `p_c`・指数自由 | 0.49671 | 0.96852 | -105.64 | -109.84 | 最大絶対パラメーター相関0.985 |
| C=2 | `p_c`・指数自由 | 0.49710 | 0.94702 | -98.49 | -102.70 | 最大絶対パラメーター相関0.985 |

`C=1` の理論値固定モデルは最小RSSではないが、残差の増加が小さい一方、少ない自由パラメーターを考慮した現行AICc/BICは、数値的採用可能モデルの範囲でこのモデルを選好する。非採用の境界補正モデルを含む全候補の最小と同義ではない。RSSは理論固定 `2.592931×10⁻⁵`、`p_c=0.5`・指数自由 `2.504442×10⁻⁵`、`p_c`・指数自由 `2.165891×10⁻⁵` である。C=1自由pc fitの最大絶対相関0.98534は指数−振幅（符号−）であり、pc−指数は−0.90686である。補正付き `C=1` fit は `omega` の選択により `1/nu=0.43..0.57` へ動き、自由補正 fit は高相関または境界へ達した。`C=2` の補正 fit も `p_c`, `1/nu`, 補正係数の相関がほぼ1で、例えば固定 `omega=0.5..1.5` で `1/nu=0.69..0.19` と動く。`p_c` は0.5付近だが、現在の9点だけで `C=2` のシフト指数が `C=1` へ収束すると主張できない。

補正shift（固定 `omega=1`）の旧区間は以下のSUPERSEDED列に残す。旧profileの探索では点fitのboundsを引き継いでおらず、C=2の旧500 drawに指数<0.05が23件、pc>1が12件（最大11.0529）あった。現行値は同じdrawを既存point helperでrefitした結果であり、区間の端だけをclipしたものではない。点推定値・主fitのRSS/AICc/BICは不変。

| 条件 | parameter | 旧SUPERSEDED範囲 | CORRECTED範囲 | 有効/要求draw |
|---|---|---:|---:|---:|
| C=1 | 1/nu | [0.26312, 0.95201] | [0.26310, 0.95200] | 500/500 |
| C=2 | 1/nu | [0.01861, 1.52574] | [0.05000, 1.52557] | 500/500 |
| C=2 | pc | [0.49156, 0.86741] | [0.49186, 0.63329] | 500/500 |

C=1のpcはpoint/bootstrapとも0.5固定。両conditionのshiftは500/500有効fitで、表は収束・有効fitに条件付けた2.5–97.5 percentile範囲である。C=2の下端は既存指数bounds [0.05,4]に対応し、指数・pc・補正係数の高相関が残る。区間の広さやboundaryだけから漸近シフト指数を確定しない。[正式24区間](../app/out/scaling-v3-joint-shift-bootstrap-corrected/bootstrap_intervals.csv)と[旧/新比較](../app/out/scaling-v3-joint-shift-bootstrap-corrected/interval_comparison.csv)を参照。

## 5. C=1 と C=2 の普遍性

全サイズの単純 fit は以下である。

| 量 | C=1 点指数 | C=1 percentile範囲 | C=2 点指数 | C=2 percentile範囲 |
|---|---:|---:|---:|---:|
| P_before | 0.106997 | [0.09291, 0.12004] | 0.117370 | [0.10393, 0.13051] |
| P_after | 0.104559 | [0.08572, 0.12393] | 0.108595 | [0.09268, 0.12645] |
| S_before | 1.586319 | [1.44098, 1.76644] | 1.590865 | [1.46351, 1.77233] |
| S_after | 1.772434 | [1.63660, 1.94006] | 1.768067 | [1.61683, 1.93531] |
| std(p_mid) | 0.669957 | [0.61944, 0.72065] | 0.667847 | [0.61179, 0.73118] |

全10行は500/500有効fitで、[有限主解析正式表](../app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_corrected_table.csv)のsimple fitに対応する。周辺区間が各量で重なることは確認できるが、それだけで共通指数・同一普遍クラスを証明しない。

`P_before` のU3固定 `omega=2` は共通指数 `0.10404`、`P_after` は `0.10048` を与え、独立U1より AICc/BIC が小さい。`std(p_mid)` の同モデルは `0.72010` である。Sについても共通指数モデルは情報量規準上競争力があるが、最良補正モデルの一部は係数境界へ達し、`S_before` の共通指数は固定 `omega` により大きく動く。

> 旧記述（HISTORICAL、bootstrap精度の根拠としてはSUPERSEDED）：「単純 bootstrap では C=1/C=2 の指数区間が全主要量で重なり、U2の共通指数も各独立推定の間にある。補正付き bootstrap は補正係数との縮退が大きく、単純 bootstrap より安定しない。」旧U1/U2 bootstrapは実際の補正付き点モデルと異なるlog OLSだったため、その狭い区間を補正モデルの精度として用いない。

現行joint bootstrapは、U1が条件別自由指数・自由omega、U2が共通指数・条件別自由omega、U3がomega=1固定共通指数という実際の点モデルをrefitする。全500 draw、seed20260720を保持した正式区間は次の通り。U3の列はomega=1のみであり、上記点fitのomega=2を含む他の固定omegaの区間ではない。

| 量 | U1 C=1（有効/500） | U1 C=2（有効/500） | U2 共通指数（有効/500） | U3 omega=1共通指数（有効/500） |
|---|---:|---:|---:|---:|
| P_before | [-0.17741, 0.26909] (500/500) | [-0.25052, 0.17886] (500/500) | [-0.05491, 0.16844] (500/500) | [0.07550, 0.12400] (500/500) |
| P_after | [-0.19414, 0.28760] (500/500) | [-0.27482, 0.24886] (500/500) | [-0.09173, 0.20831] (500/500) | [0.06672, 0.13083] (500/500) |
| S_before | [1.05150, 1.98676] (457/500) | [1.02888, 1.96385] (457/500) | [1.15761, 1.93413] (482/500) | [1.40345, 1.87566] (467/500) |
| S_after | [1.44280, 2.15377] (432/500) | [1.34028, 2.16792] (432/500) | [1.60353, 2.13083] (500/500) | [1.70544, 2.09620] (500/500) |
| std(p_mid) | [0.63163, 0.97044] (500/500) | [0.29740, 0.86967] (500/500) | [0.57254, 0.88102] (500/500) | [0.63082, 0.85723] (500/500) |

U1 S_afterは68/500失敗（C1/C2の2指数は同じ68回のmodel失敗）、U1 S_beforeは43、U2 S_beforeは18、U3 S_beforeは33失敗した。実際のjoint＋shift model refitは8,500回、失敗162回で、2指数等のparameter-reportでは11,000行中273失敗行となる。失敗・boundary fitを保持したpercentile範囲であり、無条件95% coverageは確認していない。U2のboundary frequencyはP_after 77.8%、S_after 65.2%、std 89.8%で、強いパラメーター相関も残る。[audit_verification.json](../app/out/scaling-v3-joint-shift-bootstrap-corrected/audit_verification.json)と[diagnostics](../app/out/scaling-v3-joint-shift-bootstrap-corrected/bootstrap_diagnostics.csv)を参照。

例えばU2 S_afterの旧区間[1.66690,1.70824]はSUPERSEDEDで、現行は[1.60353,2.13083]。U2 P_afterは旧[0.09440,0.11965]から[-0.09173,0.20831]へ広がった。共通指数を精密に確定したという証拠は弱まる。simple fitの整合可能性とjoint点fitのモデル競争力は別の証拠として残るが、「同一普遍クラスへ向かう可能性と整合的」という慎重な表現までとし、「証明済み」とはしない。S_beforeとshiftの判定力の弱さ、固定omega依存性も併記する。 多始点法は指定した開始点の最小RSSを選ぶ規約で、大域最適解を保証しない。P_afterのU2は入れ子のU3自由omegaよりRSSが0.485%大きく、U3の解を追加開始点にした監査専用診断でU2のRSSは0.547%下がった。両方は補正係数境界で、採用可能なU3固定omega=2の優位は変わらなかった。公式点fit・bootstrap・開始点規約は保持している。

単純 fit の hyperscaling 和 `2 beta/nu + gamma/nu` は、`L_min=8` で C=1 before `1.8003`, after `1.9816`、C=2 before `1.8256`, after `1.9853` である。afterは空間次元2に近い一方、beforeはずれるため、要求の前後状態を混同しないことが重要である。

## 6. UNBOUNDED

### 最大 request jump

全サイズ (`L_min=8`) の比較は次の通りである。

| モデル | Y_inf | 減衰指数 | AICc | BIC | LOO RMSE |
|---|---:|---:|---:|---:|---:|
| zero power | 0固定 | 0.07827 | -83.71 | -85.31 | 0.00998 |
| finite power | 0.25986 | 0.42000 | -80.31 | -84.52 | 0.01115 |
| zero log | 0固定 | 0.25822 | **-85.64** | **-87.24** | **0.00870** |
| finite log | 0.16180 | 0.51587 | -80.93 | -85.14 | 0.00966 |

全サイズでは zero log が最良だが、zero powerとの差は小さい。`L_min=16` では有限値モデルが下限0へ達し、`L_min=32` では有限値が再び約0.24–0.26になる。有限値 bootstrap は power で概ね `[0,0.296]`、logでも `[0,0.289]` を許し、境界0を排除しない。従って「ゼロへ収束する」モデルがやや選好されるが、小さい減衰指数のため真のゼロと有限値を識別できない。

外挿は次の通りである（予測であって観測ではない）。

| L | zero power | finite power | zero log | finite log | モデル間range |
|---:|---:|---:|---:|---:|---:|
| 160 | 0.2824 | 0.2889 | 0.2876 | 0.2890 | 0.0066 |
| 192 | 0.2784 | 0.2868 | 0.2850 | 0.2867 | 0.0084 |
| 256 | 0.2722 | 0.2837 | 0.2811 | 0.2833 | 0.0115 |

各モデルのbootstrap予測区間は全3サイズで重なる。`L=256` は最大観測サイズの2倍であり、区間は統計再標本化だけを反映し、モデル誤指定を含まない。LOOでもモデル差は小さいため、`L=160` 単独の少数runで識別できる可能性は低い。追加するならまず `L=192` または `256` の UNBOUNDED を50–100 runs行い、モデル間差がrun誤差を上回るか再評価するのが防御的である。

transition width はさらに不安定である。全サイズの zero power 減衰指数は `0.00167`、zero log は下限 `0.001` に達し、有限値モデルも境界解となる。`L_min=16,32` では指数が大きく変わる。現サイズ範囲から width の漸近値を決めることはできない。

## 7. 追加計算の費用対効果

`L=96,128` の各run実測時間から `t=A L^z` を条件別に外挿した。推定指数は C=1 `z=4.072`, C=2 `z=4.028`, UNBOUNDED `z=3.190` である。表は100 runsの推定壁時計時間である。

| L | C=1 | C=2 | UNBOUNDED |
|---:|---:|---:|---:|
| 160 | 1.05 h | 0.61 h | 0.020 h |
| 192 | 2.20 h | 1.27 h | 0.036 h |
| 256 | 7.09 h | 4.06 h | 0.090 h |

総時間はrun数に比例し、20 runsは表の0.2倍、50 runsは0.5倍である。1 run の推定は C=1 で `37.7,79.1,255.3 s`、C=2で `22.0,45.9,146.2 s`、UNBOUNDEDで `0.73,1.30,3.26 s`（L=160,192,256）である。bootstrap区間は実測run間変動に対して狭いが、2サイズだけの外挿であり、I/O、GC、停止時刻分布、マシン差による系統的不確実性を含まない。

情報価値の優先順位は次の通りである。

1. **UNBOUNDED L=192/256, 50–100 runs**: 計算費が小さく、ゼロ／有限値モデル識別に直接効く。ただし予測上のモデル差が小さいため、まず一方のサイズで再判定する。
2. **C=2 L=160/192, 50–100 runs**: P/Sの共通指数仮説と不安定なshiftを改善する。C=1より安価で、普遍性判断の情報価値が高い。
3. **C=1 L=160/192, 20–50 runs**: 既にPと理論指数の整合性が良いため、主目的はSとshiftの補正確認である。優先度は相対的に低い。

`L=256` の有限Cを100 runs一括実行する前に、`L=160/192` の結果で補正モデルの識別が改善するか確認すべきである。

## 8. 不安定性と限界

- 9サイズに対して4–5パラメーターの自由補正 fit は識別余力が小さい。
- 条件平均への無重み元スケールRSSに基づくスコアは、等分散Gaussian作業仮定に条件付きである。数値的admissibleや有限共分散は物理的漸近性・識別可能性を保証しない。例えば補正S_afterの一部は指数>2だが、正の振幅で永久に続くとS≤L²に反するため、有限範囲の診断としてのみ使用する。
- 多くの自由 `omega` fit は `omega=0.05`、指数下限、補正係数境界、または相関係数ほぼ1へ達した。
- AICcは複雑モデルを強く罰し、補正が物理的に存在しないことではなく「現在の点数では推定に値しない」ことを示す場合がある。
- run bootstrapのpercentile範囲は収束・有効fitに条件付きであり、サイズ選択、omega選択、モデル誤指定、境界条件、request-level定義による系統誤差を含まない。
- 各L/Cで元run seedを共有するが、現行bootstrapはcondition/Lを独立resampleし、cross-L/C covarianceを含めない。simpleの周辺区間重なりやjoint区間を、paired seed-block検証済みの証拠として扱わない。
- request-level最大落下は最短経路全体を同時削除するSPP本来のイベントであり、論文比較用single-edge event-based ensembleとは異なる。
- UNBOUNDED のsingle-edge結果は要求内辺順序に依存する。本章の主結論は順序に依存しないrequest-level解析に基づく。
- 外挿は最大2倍のLまでであり、観測と同列に扱えない。

## 9. 現時点で最も防御可能な結論

1. `C=1` のP指数と疑似臨界点シフトは既知の二次元通常パーコレーションと整合し、補正項を追加しても情報量規準は改善しない。Sはrequestのbefore/afterに依存し、afterの方が理論値とhyperscalingに近い。
2. `C=2` のP、S_after、`std(p_mid)` のsimple点指数・周辺区間はC=1に近く、共通指数モデルは点fitの情報量規準上競争力を持つ。同一普遍クラスへ向かう可能性と整合的だが、訂正joint bootstrapは強い縮退・boundary・失敗を含み、共通指数を精密に確定した証拠にはならない。S_beforeとshiftの不安定性も残る。
3. UNBOUNDED は有限Cと明確に異なる大きなrequest jumpを持つ。ゼロ漸近モデルがAICc/BIC/LOOでわずかに優勢だが、有限値モデルのbootstrap区間は0から約0.3までを許す。`L<=128` では真の不連続、弱い不連続、非常に遅い連続転移を識別できない。

### 卒論本文向け要約

`L=8–128` の有限サイズ補正解析では、`C=1` の最大クラスター割合の指数比は `beta/nu=5/48` と整合し、理論値固定モデルが自由指数・補正付きモデルより情報量規準で支持された。`C=2` については、PとS_afterを C=1 と共通指数で記述するモデルが競争力を持ち、同一普遍クラスへ向かう可能性と整合した。一方、有限クラスター量のbefore状態と疑似臨界点シフトには強いパラメーター相関が残った。UNBOUNDED の最大request jumpはゼロ漸近の冪則または対数モデルがわずかに優勢であったが、有限値漸近もbootstrapで排除できず、`L<=128` から転移次数を確定することはできない。追加計算は、費用が小さくモデル識別へ直結する UNBOUNDED の `L=192` または `256` を優先し、その後に `C=2` の追加サイズを検討する。

## 10. 再現方法と成果物

以下は当時の生成コマンド（HISTORICAL）。完成済みの出力へ再実行して上書きしない。現行訂正値の参照先は冒頭と[補正台帳](ANALYSIS_AUDIT_CORRECTIONS.md)に示す。

```powershell
python -m analysis.scaling_v3 `
  --source app/out/scaling-v2-analysis `
  --output app/out/scaling-v3-analysis `
  --bootstrap-samples 500
```

当時の主要CSVは `finite_correction_fits.csv`, `universality_model_fits.csv`, `hyperscaling_corrections.csv`, `pseudocritical_shift_corrections.csv`, `unbounded_asymptotic_fits.csv`, `unbounded_leave_one_size_out.csv`, `unbounded_extrapolations.csv`, `bootstrap_intervals.csv`, `runtime_forecasts.csv`, `fit_stability_summary.csv` である。図は `app/out/scaling-v3-analysis/figures/` に保存される。旧bootstrap CSV・図はHISTORICALとして残し、該当区間はSUPERSEDED。有限主解析の訂正図は[finite_primary_bootstrap_ci.png](../app/out/scaling-v3-finite-bootstrap-corrected/finite_primary_bootstrap_ci.png)と[bootstrap_exponent_distributions.png](../app/out/scaling-v3-finite-bootstrap-corrected/bootstrap_exponent_distributions.png)を使用する。joint/shift bootstrapの訂正による旧区間図の差し替えは生じていない。Phase9では点比較図のU1独立2系列とC1理論固定simple曲線の描画欠落を修正した。旧 `c1_c2_shared_exponent.png` と `simple_vs_corrected_P_before.png` はSUPERSEDED表示とし、[訂正共通指数図](../app/out/scaling-v3-shared-exponent-figure-corrected/c1_c2_shared_exponent_corrected.png)と[訂正P_before比較図](../app/out/scaling-v3-shared-exponent-figure-corrected/simple_vs_corrected_P_before_corrected.png)を使用する。点CSV・区間・選択規約は不変。CSVとPNGは再生成可能な成果物としてGitへコミットしない。
