"""Read-only source/data preparation; creates outputs only in this seminar folder."""
from pathlib import Path
import csv, json, hashlib, subprocess
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUILD = HERE / '.build'
BUILD.mkdir(exist_ok=True)
SLIDES = []
def slide(title, chapter, minutes, body, source, evidence, kind='text', formula=None, table=None, asset=None, chart=None, classification='A', notes=''):
    i = len(SLIDES)+1
    SLIDES.append(dict(id=i,title=title,chapter=chapter,minutes=minutes,type=kind,body=body,
        formula=formula or [],table=table or [],asset=asset,chart=chart,footer=source,
        classification=classification,evidence=evidence,
        notes=f'【位置づけ】{classification}：A=原典の記載、B=定義・仮定からの導出、C=本研究への応用、D=未確認課題。\n【根拠】{source}\n{evidence}\n【説明】{notes}'))

slide('2次元正方格子上のSPP\n相転移の性質', '第1章 はじめに',3,
 ['卒業研究ゼミ　2026年10月15日','中心的な問い','制限なしSPPで、無限サイズでも\n最大クラスターの割合Pに有限のジャンプが残るか'],
 'Kim & Radicchi, PRL 133, 047402 (2024)；本研究の問い',
 '原論文のER上の評価を説明し、2D正方格子への適用可能性を検討する。',kind='cover',classification='A・D',notes='本編88分、質疑32分。先行研究の理解を主とし、2Dでの不連続性は未確定と最初に述べる。')
slide('ネットワーク構造と削除規則', '第1章 はじめに',5,
 ['通常のボンド：辺を独立に占有する','SPP：現在の最短経路を要求1回でまとめて削除する','ERの先行研究を理解し、幾何が明確な2D格子で問い直す'],
 '本文 PDF 1–2／印刷 047402-1–2；講義9 PDF・スライド49–51',
 '通常ボンドの独立性とSPPの経路削除規則を対比。',notes='7章の順序は基礎、転移の定義、原論文、解析手法、格子実験、研究方針。道路応用や未特定の別モデルを根拠にしない。')
slide('サイトとボンド・パーコレーション','第2章 パーコレーションの基礎',3,
 ['占有確率を変え、連結成分の出現を調べる','通常のモデルでは各占有状態を独立に選ぶ'],
 '教科書 PDF 2–4／印刷151–154、図8.1・8.4；講義9 48–51',
 'サイトは頂点、ボンドは辺の独立占有。',kind='table',table=[['モデル','占有する対象','制御変数'],['サイト','頂点','頂点の占有確率'],['ボンド','辺','辺の占有確率 q']],notes='SPPは辺を除く過程なのでボンドとの比較が自然。ただし同じ残存割合でも独立性は保証されない。')
slide('連結成分・巨大連結成分・臨界点','第2章 パーコレーションの基礎',4,
 ['連結成分：経路で互いに到達できる頂点の集まり','巨大連結成分：無限サイズでも有限割合を占める成分','臨界点：巨大連結成分が出現する境界'],
 '教科書 PDF3／印刷152–153、式8.1–8.5・図8.2；講義7 3・28',
 '教科書のθ(q)=Pr(s=∞)と講義の巨大連結成分の定義を対応づける。',formula=['θ(q) = Pr(s = ∞)','q_c = inf{q : θ(q) > 0}'],notes='有限系の最大成分はいつでも存在する。最大であることと無限系で巨大であることは区別する。θは無限クラスターに属する確率で、有限系Pと同一の有限系量ではない。')
slide('占有確率qと辺の削除率p','第2章 パーコレーションの基礎',4,
 ['SPPのpは、初期辺数に対する実際の削除割合','独立削除の確率をp_delとすれば q=1−p_del','残存割合1−pだけから、辺の独立性は言えない'],
 '補足 PDF1、式S1；教科書 PDF3右／印刷153、表8.2；講義9 49',
 'S1は実現した削除割合。表8.2は正方格子の通常ボンド閾値q_c=1/2。',formula=['p = 1 − E_t / E₁','通常の正方格子ボンド：q_c = 1/2'],classification='A・B',notes='E₁は初期辺数で本研究のE₀に対応する。独立占有のqは確率、1−pは実現値。固定削除辺数の一様アンサンブルと独立Bernoulliは有限系では異なり、後者は前者の二項混合（予備B02）。')
slide('C=1が通常ボンドに対応する条件','第2章 パーコレーションの基礎',4,
 ['異なる2頂点を一様に選ぶ','受理される要求は、現在の辺を1本だけ削除する','受理条件下では、どの残存辺も同じ確率で選ばれる'],
 '本文 PDF2／047402-2；補足 PDF1・11；実装 SPPSimulator・ShortestPathFinder',
 '原論文はC=1を通常ボンドに対応づける。条件付き一様性は削除規則から導出。',formula=['Pr(e を削除 | 受理) = 1 / m','m：現在の残存辺数'],classification='A・B・C',notes='有向に数えた頂点対はN(N−1)、各無向辺は2通り、受理確率2m/[N(N−1)]。棄却は辺状態を変えないため削除順序を偏らせない。pで比較し、全要求時間tでは棄却を別に扱う。C>1は経路に沿う相関を導入する。')
slide('秩序変数と熱力学的極限','第3章 連続転移と不連続転移',4,
 ['有限系では最大クラスターの割合Pを測る','同じモデル・制御変数のままサイズを大きくする','転移次数は、極限の関数の振る舞いで定義する'],
 '補足 PDF2、式S2；教科書 PDF3／152–153；講義7 28',
 'Pの原典定義から極限関数を導入する。本発表の操作的定義であり、極限の存在を証明していない。',formula=['P(p,N) = |C_max| / N','P_∞(p) = lim_{N→∞} ⟨P(p,N)⟩'],classification='A・B',notes='グラフ族、境界条件、Cのサイズ依存を固定して極限を考える。有限Nの階段状ジャンプ自体は無限系の不連続性の証拠ではない。')
slide('連続転移と不連続転移','第3章 連続転移と不連続転移',6,
 ['J=0：秩序変数が臨界点で連続','J>0：有限のジャンプが残る','模式曲線は定義の説明用（研究データではない）'],
 '本発表の操作的定義B；教科書 PDF3／152–153；本文 PDF4／047402-4',
 '左右極限の差によって不連続性を定義。原論文のweakly discontinuousと同義とはしない。',kind='concept',chart='concept',formula=['J = P_∞(p_c−) − P_∞(p_c+)'],classification='B',notes='模式図の式や形は実在モデルの測定・理論曲線ではない。連続転移でも傾きが発散し得るため、急峻さだけではJ>0と言えない。')
slide('有限サイズの急峻化と転移次数','第3章 連続転移と不連続転移',5,
 ['連続転移でも、サイズ増大に伴って曲線は急峻になる','転移幅の縮小は、最大ジャンプの正の極限を保証しない','最大落下・幅・位置を、異なる量として検討する'],
 '本文 PDF2・4、図2・5；補足 PDF2–5、式S6–S18',
 'C=1の通常ボンドとC=Nの曲線・幅を対比。無限系のジャンプへの推論は追加の検討。',classification='A・B・D',notes='N依存の閾値で定義する幅は、その定義を確認する必要がある。フィットの見た目や一つのモデルの外挿だけで転移次数を決めない。')
slide('ER上のSPPモデルとC','第4章 SPP論文における相転移',3,
 ['初期ERネットワーク：平均次数4、初期辺数N×4/2','一様な頂点対の現在の最短経路を求める','連結かつ経路長≤Cなら、一様に選んだ最短経路を全削除','固定した有限Cと、制限なしに相当するC=Nを比較'],
 '本文 PDF1–2／047402-1–2、図1；補足 PDF1・11',
 '論文の固定初期辺数設定、最短経路の一様選択、予算条件を確認。',notes='初期ERを固定辺数の設定として説明する。最短経路のランダムな前駆点選択だけでは一様とは限らず、経路数を重みとする。単純経路は最大N−1辺なのでC=Nは実効的に制限なし。')
slide('原論文 図2：平均曲線とSピーク','第4章 SPP論文における相転移',4,
 ['(a) P(p)：N=2²⁰でCを比較','(b) 平均Sのピーク位置p_c(N)','(c)(d) S(p)：C=1とC=N、複数N','横軸pは辺の削除率'],
 'Kim & Radicchi (2024) 図2、本文 PDF2／047402-2；補足 式S8',
 '図2の軸・条件・測定量を引用。図中のP/Sは平均表記を省略。',kind='figure',asset='.build/assets/fig2.png',notes='(b)の横補助線は推定した無限サイズ位置で、個々の曲線ではない。(c)(d)のピーク高さは同じNで比較する。ERでのC=1はp_c=1−1/4=0.75であり、正方格子の0.5と混同しない。')
slide('原論文 図3：イベント基準の分布','第4章 SPP論文における相転移',4,
 ['C=N：各runの最大単一辺落下を基準に測る','(a) P_c N⁰·²¹、(b) S_c N⁻⁰·⁵⁵','縦軸は確率密度','曲線の重なりは有限サイズスケーリングの検討'],
 'Kim & Radicchi (2024) 図3、本文 PDF3／047402-3；補足 PDF4–6',
 '分布の再スケール表示。図の密度を平均値や信頼区間と説明しない。',kind='figure',asset='.build/assets/fig3.png',notes='指数はERのevent-based解析の報告値であり、2D格子に移植しない。単一辺削除での前後を使い、要求1回の経路全削除と区別する。分布の重なりは厳密な極限の証明ではない。')
slide('原論文 図5：転移幅と著者の評価','第4章 SPP論文における相転移',4,
 ['(a) 削除率の幅 Δp','(b) 全要求回数の幅をN²で割る','C=Nで幅がサイズとともに縮小','著者の表現：weakly discontinuous'],
 'Kim & Radicchi (2024) 図5、本文 PDF4／047402-4',
 'P>0.5とP>1/√Nを最後に満たす状態の差。C=Nの幅指数α=0.13±0.01、α′=0.88±0.01。',kind='figure',asset='.build/assets/fig5.png',notes='両パネル両対数。縦の幅は固定しきい値とN依存しきい値を使う。weakly discontinuousは著者の数値的評価。正の最大要求ジャンプ極限の証明として紹介しない。回帰の±をbootstrap95%区間と呼ばない。')
slide('観測量PとS','第5章 SPP論文の数値解析手法',4,
 ['P：最大クラスターの割合','S：最大クラスターを1個だけ除外し、\n残りの頂点から見たクラスターサイズの平均','単純なクラスター数平均とは異なる'],
 '補足 PDF2、式S2・S3；本研究 ClusterStats.calculateMeanClusterSize',
 'Sはクラスターサイズの頂点重み平均。最大が同率でも1個だけ除外。',formula=['P = s_max / N','S = (Σ_{i≠max} s_i²) / (Σ_{i≠max} s_i)'],notes='孤立点s=1も含む。同率最大のどれを1個除いても式は同じ。分母0の場合は論文に規約が明記されておらず、本実装ではS=0とする。要求で大きく分裂した断片もSに入る。詳細B04。')
slide('臨界点と疑似臨界点','第5章 SPP論文の数値解析手法',3,
 ['無限系の臨界点p_cと、有限系の推定位置は別','A：平均S曲線の最大位置（原論文の従来型）','B：各runのS最大位置の平均','C：最大要求落下区間の中点の平均（本研究）'],
 '補足 PDF3、式S8・S9；本研究 pc_uncertainty.csv・event_summary.csv',
 'S8はargmax of meanであり、mean of argmaxではない。Cは要求基準の別推定量。',formula=['p_c^S(N) = argmax_p ⟨S(p,N)⟩','⟨argmax_p S_r(p,N)⟩ ≠ p_c^S(N) 一般には'],classification='A・B・C',notes='ピーク同値規則、観測範囲、要求状態の対応規約に依存。本研究Aの95%区間はrun再標本化、1000回、固定seed20261013、共通範囲固定。SEMとは別。BをAの不確かさと呼ばない。')
slide('有限サイズスケーリング：LとN','第5章 SPP論文の数値解析手法',4,
 ['原論文は頂点数Nを用いる','2D格子ではN=L²。通常のL基準から変数を変換できる','ν̄は相関体積の指数。ERの値を2Dへ適用しない'],
 '補足 PDF2、式S6・S7；L基準への変換は本発表の導出B',
 'S6/S7はN基準のFSS仮定。通常L基準が成立すればν̄=2νという座標変換。',formula=['⟨P⟩ = N^(−β/ν̄) F₁[(p−p_c) N^(1/ν̄)]','⟨S⟩ = N^(γ/ν̄) F₂[(p−p_c) N^(1/ν̄)]','N=L² のとき β/ν̄=β/(2ν)'],classification='A・B',notes='これはスケーリング仮定で、任意のSPPへの定理ではない。L表示とN表示は同じデータの変換であり独立した証拠ではない。仮定の導出と検査は予備B05。')
slide('臨界指数比と測定位置','第5章 SPP論文の数値解析手法',3,
 ['β：秩序変数、γ：Sの増大、ν：相関長の発散','N基準の傾きで得るのは β/ν̄、γ/ν̄、1/ν̄','p_c固定・Sピーク・イベント前後を混ぜない','対数回帰の傾きと、系統誤差を区別する'],
 '補足 PDF2–4、式S4–S12・表S2；講義3 9・11・52',
 '原論文はx=z y^ζを対数線形回帰。指数比は観測位置とensembleに依存し得る。',formula=['log x = log z + ζ log y','p_c(N) − p_c ∼ N^(−1/ν̄)'],notes='回帰係数標準誤差はモデル形やL_minの不確かさを含まない。講義3のγは次数分布指数でここでのγとは別。指定資料で確認できなかった2D臨界指数の数値は掲載しない。')
slide('conventionalとevent-based','第5章 SPP論文の数値解析手法',3,
 ['測定位置を揃える規則が異なる','原論文eventは最大単一辺落下の直前／直後','本研究の要求区間中点と同一定義ではない'],
 '補足 PDF3–6、式S8・S13–S18・表S2/S3',
 '従来型は共通pまたは平均Sピーク、event型は各runイベントに合わせる。',kind='table',table=[['基準','揃える位置','代表的な量'],['conventional','共通p、平均Sピーク','⟨P(p)⟩、⟨S(p)⟩'],['event-based','各runの最大落下','P⁻、P⁺、p⁻、p⁺']],notes='S13は落下直後p⁺、S14は直前p⁻、S16は⟨p⁺⟩。S17の位置ゆらぎはrun間標準偏差でSEMではない。平均位置のシフト指数と位置標準偏差の指数は区別する。')
slide('転移幅の測定規則と不確かさ','第5章 SPP論文の数値解析手法',3,
 ['p₂,t₂：P>1/2を最後に満たす状態','p₁,t₁：P>1/√Nを最後に満たす状態','tは棄却も含む全要求回数','標準偏差・標準誤差・95%区間・回帰誤差を区別'],
 '本文 PDF4／047402-4、図5；補足 PDF2・5、式S4・S5・S17',
 '幅の定義と要求時間のN⁻²規格化を確認。',formula=['Δp = p₁ − p₂','Δt̃ = (t₁ − t₂) / N²'],notes='図5の閾値を固定Pの差に読み替えない。S17はrun間標準偏差。SEM=s/√Rは平均の精度。bootstrap95%区間は推定量の再標本化分布。転移幅の縮小は有限ジャンプの十分条件ではない。')
slide('開境界の2次元正方格子モデル','第6章 2次元正方格子における数値実験',2,
 ['L：格子の一辺の頂点数','水平・垂直に各L(L−1)本の辺。巻き戻りはない','同じSPP規則を、幾何が明確なグラフで調べる','経路長・切断領域と要求落下を対応づけられる'],
 '本研究 SPPSimulator.processRequest・ShortestPathFinder.selectPath；講義4 8–10',
 '格子辺数は開境界の数え上げ。実装の一様頂点対・経路数重み選択を確認。',formula=['N = L²','E₀ = 2L(L−1)'],classification='B・C',notes='講義4のLは平均距離で、本研究の線形サイズLとは異なる。初期規則格子の距離スケーリングを削除後に無条件適用しない。今回の作業は新しいシミュレーションではなく既存表の再利用。')
slide('同じL=128での条件比較','第6章 2次元正方格子における数値実験',3,
 ['C=1・C=2・制限なしを同じLで比較','平均を表示。誤差は既存の補足資料に掲載','丸印は全run共通の観測終端','急峻な形だけでは転移次数を判定しない'],
 '既存図03：ja_v2/data/curves.csv；要求状態のfirst-crossing集計',
 'L=128、C1/C2各200run、制限なし400run。曲線は共通範囲で終了。',kind='curve',chart='P128',classification='C',notes='p格子に初めて到達または超えた保存要求状態を対応させるfirst-crossing推定量。単一辺の実測ではない。間引き済み表示点からピーク位置を決めない。終端後をゼロ補完しない。')
slide('最大要求落下と残る問い','第6章 2次元正方格子における数値実験',3,
 ['制限なしSPP、要求1回の経路全削除を測定','点：run平均、エラーバー：平均±標準誤差','横軸は対数L、縦軸は線形','ゼロへの遅い減衰と正の極限は、現データでは判別困難'],
 '既存図06：ja_v2/data/event_summary.csv・event_runs.csv',
 '制限なし16サイズ、計2550run。run別値から平均とSEMを再照合。',kind='jump',chart='jump',formula=['ΔP_max = max_request (P_直前 − P_直後)'],classification='C・D',notes='横軸対数で平らに見えることは収束の根拠にならない。単一辺ジャンプではなく自然な要求操作の変化。既存複数モデル比較では正の極限が安定せず判別困難。新たな外挿結果を主役にしない。')
slide('確認できたこと・残る課題','第7章 今後の研究方針',3,
 ['確認：有限サイズで大きい要求落下を観測','確認：制限なし2550runの最大要求落下は停止後上界でも保証','限界：平均Sピークの全過程保証は21/34条件','未確定：無限系で有限ジャンプが残るか'],
 'ja_v2/data/request_guarantees.csv・tail_guarantees.csv・asymptotic_model_fits.csv',
 '保証件数を既存表で確認。保証は要求状態推定量に対する上界判定。',classification='C・D',notes='最大落下の将来上界s_final−1と観測整数落下を比較する。平均Sは共通終端のN⟨P⟩を将来上界にする。未保証はピークが誤りという意味ではない。既存全34条件のデータは6150run。本編では保証の細部より結論の限界を説明。')
slide('今後の解析と必要な記録','第7章 今後の研究方針',4,
 ['最大要求落下・削除率幅・位置を併せて追跡する','ゼロ極限／正の極限の複数モデルとL_min感度を比較する','指数は測定位置・補正項・不確かさを固定して検討する','単一辺比較には要求境界・削除辺列・経路内順序を記録する'],
 '本研究の計画D；補足 PDF1・4–6・10–12（解析方法の参照）',
 '原論文の手法を参照しつつ、未実施の検討は今後の課題として記載。',classification='C・D',notes='次は既存データの感度解析を優先。追加計算が必要なら記録項目と予測を事前固定し、小規模確認から始める。最大落下位置が巨大成分消失位置へ近づくか、経路内辺順序に依存するかも検討。今回大規模計算は実施しない。')
slide('質疑・議論','質疑・議論',32,
 ['定義と原典の対応','有限サイズから何が言えるか','2D正方格子で次に検証すべきこと'],
 '本編88分＋質疑・議論32分＝120分',
 '質疑用の導入。科学的主張を追加しない。',classification='構成',notes='数式の詳細は予備B01–B10とstudy/derivations.mdを参照。知らない事項は未確認と答え、原典に戻る。')
slide('B01　資料と記号の対応','予備スライド',0,
 ['同じ文字でも資料ごとに意味が異なる'],
 '補足 式S1–S3；講義7 28・31；講義4 9；講義3 9',
 '原典の記号の意味を本発表の統一表記へ対応。',kind='table',table=[['資料の記号','元の意味','本発表'],['講義7 S','巨大連結成分の割合','P'],['講義4 L','平均距離','格子サイズLと別'],['講義3 γ','次数分布指数','Sの指数γと別'],['論文 ν̄','相関体積指数','2Dのνと別']],notes='qは通常ボンドの占有確率、pはSPPの実際の削除割合。論文E₁と本研究E₀はいずれも初期辺数。')
slide('B02　C=1の条件付き確率','予備スライド',0,
 ['各無向辺に対応する順序付き頂点対は2通り','受理された削除は残存m辺上で一様','固定削除辺数と独立占有は有限系では異なる'],
 '本文 PDF2；補足 PDF1・11；削除規則からの導出B',
 '一様な頂点対選択とC1の受理条件から条件付き確率を計算。独立占有は固定k一様分布の二項混合。',formula=['Pr(e を削除) = 2/[N(N−1)]','Pr(受理) = 2m/[N(N−1)]','Pr(e を削除 | 受理) = 1/m'],classification='B',notes='独立占有確率qなら削除本数KはBinomial(E₀,1−q)。K=k条件下の残存集合はC1のk受理後と同じ一様分布。固定kで辺状態が独立だとは言わない。棄却要求は順序を変えないが要求時間を増やす。')
slide('B03　ERの巨大連結成分の閾値','予備スライド',0,
 ['u：ランダムな枝の先が巨大連結成分に属さない確率','平均次数zのPoisson分布を仮定','u<1の解が現れる境界はz=1'],
 '講義7 PDF・スライド30–34；教科書 PDF8左／印刷162、式8.20–8.22',
 '講義のuの自己無撞着式と接線条件を展開。教科書はERサイト閾値。',formula=['u = exp[z(u−1)]','u=1−ε：1−ε = 1−zε+O(ε²)','z_c=1、巨大割合P=1−u'],classification='A・B',notes='局所木状・独立性・大サイズのER近似が前提。初期平均次数4の独立ボンド占有では残存平均次数4q、ゆえにq_c=1/4、削除側p_c=3/4。2D正方格子には適用しない。')
slide('B04　Sの頂点重みと除外規則','予備スライド',0,
 ['最大クラスターを1個除いた頂点集合から一様に1頂点を選ぶ','サイズs_iのクラスターに属す確率はs_i/Σs_j','同率最大は1個のみ除外。孤立点も含む','分母0は本実装S=0（原論文の規約は未記載）'],
 '補足 PDF2、式S3；ClusterStats.calculateMeanClusterSize',
 'Sの分子の二乗は頂点による重みから生じる。',formula=['E[s] = Σ_i [s_i/(Σ_j s_j)] s_i','S = Σ_i s_i² / Σ_i s_i'],classification='A・B・C',notes='単純クラスター平均Σs_i/個数と混同しない。最大要求で2つの大断片に分裂すると、最大以外の大断片がSに算入されるためSが大きくなる。増大だけで転移次数を判定しない。')
slide('B05　FSSの変数とN=L²','予備スライド',0,
 ['仮定：相関長 ξ∼|p−p_c|^(−ν)','有限系のクロスオーバーはξとLが同程度','通常のL基準FSSが成立する場合にNへ変換'],
 '補足 PDF2、式S6・S7（N基準）；L基準の動機づけ・変換は導出B',
 'スケーリング仮定から無次元変数(p−pc)L^(1/ν)を構成。N=L²で指数を半分にする。',formula=['|p−p_c| ∼ L^(−1/ν)','⟨P⟩ = L^(−β/ν) F[(p−p_c)L^(1/ν)]','L=N^(1/2) ⇒ ν̄=2ν（この変換の条件下）'],classification='A・B',notes='βはP∞∼(pc−p)^β、γは有限クラスターS∞∼|p−pc|^(−γ)、νは相関長。これは連続転移の通常の仮定を説明するものでSPPへの無条件の適用ではない。N基準のhyperscaling右辺1、2D L基準右辺2も同じ条件の下で対応。')
slide('B06　原論文の指数と測定基準','予備スライド',0,
 ['ER・C=Nの報告値。2D格子の指数ではない','平均位置のシフトとrun間位置標準偏差は別'],
 '補足 PDF4・6、表S2・S3；式S9・S17・S18',
 '同じ無制限モデルでも観測位置やensembleにより推定値が異なる。',kind='table',table=[['測定基準','β/ν̄','γ/ν̄','位置の1/ν̄'],['固定p_c','0.04±0.01','0.15±0.01','―'],['平均Sピーク','0.24±0.01','0.53±0.01','0.18±0.01'],['event直後の平均','0.21±0.01','0.55±0.01','0.15±0.01'],['event位置の標準偏差','―','―','0.50±0.01']],notes='表S2/S3の±は論文の回帰推定誤差であり本研究のbootstrap区間ではない。固定pcには強い有限サイズ効果。平均シフトとゆらぎの指数を一つにまとめない。')
slide('B07　単一辺eventと要求event','予備スライド',0,
 ['原論文：δp=1/E₁で最大単一辺落下を選ぶ','本研究：経路全削除の最大要求落下を選ぶ','要求落下を経路辺数で割って単一辺実測と呼ばない','辺列再生では経路内順序と、その感度を検証する'],
 '補足 PDF4–5、式S13–S16；PDF1・10–12（削除辺列保存）',
 '原論文のpplusは単一辺落下後、pminusは直前。本研究midpointは別の量。',formula=['p⁺ = argmax_p [P(p−δp) − P(p)]','p_mid = (p_直前 + p_直後)/2（要求基準）'],classification='A・C・D',notes='原論文S16は⟨p⁺⟩。要求イベントでのp直前と直後の差は経路辺数/E₀。順向き・逆向き・シャッフルの感度は二次的な単一辺比較として扱う。正式全runに辺列が揃うとは限らない。')
slide('B08　図5の閾値と要求時間','予備スライド',0,
 ['p₂,t₂：P>0.5の最後の状態','p₁,t₁：P>1/√Nの最後の状態','要求時間tは、受理要求数でも削除辺数でもない','幅縮小の評価と、正の極限ジャンプの問いを区別する'],
 '本文 PDF4／047402-4、図5',
 'C=NでΔp∼N^(−0.13)、Δt̃∼N^(−0.88)。有限Cの幅指数はほぼ0と報告。',formula=['Δp = p₁−p₂ ∼ N^(−α)','Δt̃ = (t₁−t₂)N^(−2) ∼ N^(−α′)','C=N：α=0.13±0.01、α′=0.88±0.01'],notes='最後に閾値を超える状態という規則を保つ。両対数直線はべき則当てはめ。固定閾値とサイズ依存閾値の組合せであるため定義に依存する。')
slide('B09　同じLでのS比較と観測終端','予備スライド',0,
 ['L=128でピーク高さを比較','平均を表示。誤差は既存の補足資料に掲載','全run共通範囲のみ。終端以降は補完しない','このLの3条件は終端上界で平均Sピークを保証'],
 '既存図11：ja_v2/data/curves.csv・tail_guarantees.csv',
 'L128のC1/C2/制限なしを同じ線形軸で比較。終端の丸印。',kind='curve',chart='S128',classification='C',notes='制限なしL1024とC1L128のピーク高さを直接比較しない。平均Sの将来上界N⟨P終端⟩が観測ピークより小さい条件で保証。本図の軌跡は表示点であり、ピーク推定の再計算には完全グリッドを使う。')
slide('B10　一次資料と未確認の文献','予備スライド',0,
 ['Kim & Radicchi (2024), PRL 133, 047402','Supplemental Material：定義・回帰・ensemble・実装','教科書『複雑ネットワーク』第8章（印刷149–192）','講義3・4・7・9：用語、連結性、ER、サイト／ボンド','2Dの別モデルでの不連続転移：該当論文は未特定'],
 'DOI: 10.1103/PhysRevLett.133.047402；資料対応はsource_map.md',
 '提供7資料を参照。教科書の著者・版は抜粋から未確定。',classification='A・D',notes='教科書の実際の章見出しは「ネットワーク上の感染伝播モデル」。講義の日本語表現を参考にするが、補足導出や本研究の解釈を教授の見解として扱わない。')

def safe_input(relative):
    p = (ROOT / relative).resolve()
    if not p.is_relative_to(ROOT): raise ValueError('Input outside repository')
    return p

def rows(relative):
    with safe_input(relative).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

curves = rows('analysis/presentation_spp_comparison_ja_v2/data/curves.csv')
selected = [r for r in curves if int(r['L'])==128]
summaries = [r for r in rows('analysis/presentation_spp_comparison_ja_v2/data/event_summary.csv') if r['label']=='UNBOUNDED']
summaries.sort(key=lambda r:int(r['L']))
(HERE/'data').mkdir(exist_ok=True)
for name, data in [('curves_L128.csv',selected),('maximum_request_jump.csv',summaries)]:
    with (HERE/'data'/name).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
tail=rows('analysis/presentation_spp_comparison_ja_v2/data/tail_guarantees.csv')
with (HERE/'data'/'peak_guarantee_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(tail[0]));writer.writeheader();writer.writerows(tail)
request_counts={}
for r in rows('analysis/presentation_spp_comparison_ja_v2/data/request_guarantees.csv'):
    group=request_counts.setdefault(r['condition_id'],dict(condition_id=r['condition_id'],label=r['label'],L=r['L'],n_runs=0,n_certified=0))
    group['n_runs']+=1;group['n_certified']+=int(r['guaranteed_full_process_maximum']=='True')
with (HERE/'data'/'request_guarantee_counts.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(next(iter(request_counts.values()))));writer.writeheader();writer.writerows(request_counts.values())

SLIDES[9]['notes'] += '\n本文PDF2/047402-2で著者は、ER上では有限Cが通常パーコレーションと同じ普遍性クラス、制限なしCが異なる指数とより急峻な転移を示すと報告している。これはER上の著者の結論で、2D格子へ拡張した結論ではない。'
SLIDES[10]['body'].append('ER上の有限C：著者は通常と同じ普遍性と報告')
SLIDES[12]['notes'] = SLIDES[12]['notes'].replace('縦の幅','転移幅')
SLIDES[21]['notes'] += '\n最大要求落下の平均の極限と、極限平均曲線の左右差Jは一般に同じ定義ではない。最大落下位置の収束、削除率区間の縮小、run間ゆらぎを併せて調べる。'
SLIDES[22]['footer'] = SLIDES[22]['footer'].replace('asymptotic_model_fits.csv','limit_model_fits.csv')
SLIDES[22]['notes'] = SLIDES[22]['notes'].replace('asymptotic_model_fits.csv','limit_model_fits.csv')
SLIDES[19]['footer'] = '本研究 SquareLattice.buildAdjacency・SPPSimulator・ShortestPathFinder；講義4 8–10'
SLIDES[19]['notes'] += '\nSquareLatticeの水平ループは各L行にL−1辺、垂直ループは各L列にL−1辺を作り、逆方向も同じ無向辺IDを参照する。境界を越える接続は作らない。'
SLIDES[7]['body'] = ['J=0：臨界点で連続','J>0：有限の\nジャンプが残る','定義を示す模式曲線\n（研究データではない）']
SLIDES[10]['body'] = ['(a) N=2²⁰：Cを比較','(b) 平均Sの最大位置','(c)(d) C=1とC=NのS(p)','横軸p：辺の削除率','有限C：著者は通常と\n同じ普遍性を報告（ER）']
SLIDES[11]['body'][0] = 'C=N：各runの\n最大単一辺落下を基準'
SLIDES[11]['body'][-1] = '異なるNの分布の\n重なりを検討する'
SLIDES[20]['body'][2] = '丸印：全run共通の終端'
SLIDES[21]['body'][-1] = 'ゼロへの遅い減衰か、\n正の極限かは判別困難'
charts={}
colors=['#007F86','#CC6733','#535B9D']
for obs in ['P','S']:
    series=[]
    for j,label in enumerate(['C1','C2','UNBOUNDED']):
        # Table labels are C=1/C=2, so infer finite budgets from C too.
        a=[r for r in selected if (r['label']=='UNBOUNDED' if j==2 else r['budget_mode']!='UNBOUNDED' and int(r['C'])==j+1)]
        a.sort(key=lambda r:float(r['p']))
        if not a: raise ValueError(f'Missing {label}')
        x=[float(a[0]['p'])];y=[float(a[0][obs+'_mean'])]
        for prev,r in zip(a,a[1:]):
            x.extend([float(r['p']),float(r['p'])]); y.extend([float(prev[obs+'_mean']),float(r[obs+'_mean'])])
        series.append(dict(name=f'{"制限なし" if j==2 else "C="+str(j+1)}（{a[0]["n_runs"]}回）',x=x,y=y,color=colors[j],end=[x[-1],y[-1]]))
    charts[obs+'128']=dict(xlabel='辺の削除率 p',ylabel='最大クラスターの割合 P' if obs=='P' else '平均クラスターサイズ S',xlog=False,ylog=False,xmin=0,xmax=1,ymin=0,ymax=1 if obs=='P' else None,series=series)
charts['jump']=dict(xlabel='格子の一辺の頂点数 L（対数軸）',ylabel='最大要求落下 ΔP_max',xlog=True,ylog=False,xmin=8,xmax=1024,ymin=0,ymax=.45,
    series=[dict(name='制限なし：平均±標準誤差',x=[int(r['L']) for r in summaries],y=[float(r['delta_P_max_mean']) for r in summaries],sem=[float(r['delta_P_max_sem']) for r in summaries],color='#007F86',markers=True)])
x=[i/100 for i in range(101)]
charts['concept']=dict(xlabel='辺の削除率 p（模式）',ylabel='P∞（模式）',xlog=False,ylog=False,xmin=0,xmax=1,ymin=0,ymax=1,
 series=[dict(name='連続 J=0',x=x,y=[max(1-2*t,0) for t in x],color='#007F86'),dict(name='不連続 J>0',x=x[:51]+x[50:],y=[.3+.7*(1-2*t) for t in x[:51]]+[0 for t in x[50:]],color='#CC6733')])

assets=BUILD/'assets'; assets.mkdir(exist_ok=True)
for page in [2,3,4]:
    subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-singlefile','-r','180','-png',
        str(safe_input('presentation/2026-10-15/sources_local/papers/spp_main.pdf')),str(assets/f'paper-page-{page}')],check=True,capture_output=True)
for figure,page,box in [('fig2',2,(.512,.535,.920,.770)),('fig3',3,(.085,.058,.490,.188)),('fig5',4,(.085,.058,.490,.188))]:
    with Image.open(assets/f'paper-page-{page}.png') as im:
        w,h=im.size
        im.crop(tuple(round(v*(w if j%2==0 else h)) for j,v in enumerate(box))).save(assets/f'{figure}.png')

(BUILD/'deck.json').write_text(json.dumps(dict(slides=SLIDES,charts=charts),ensure_ascii=False),encoding='utf-8')

intro='''# スライドと出典の対応\n\nA：原典の記載、B：定義・仮定からの導出、C：本研究への応用、D：未確認課題。原典の事実と導出・解釈を区別する。全ページ番号は1始まり。\n\n## 資料のページ規約\n\n- 本文：`sources_local/papers/spp_main.pdf`。PDF1–5＝印刷047402-1–5。\n- 補足：`sources_local/papers/spp_supplement.pdf`。PDF1は印刷番号なし、PDF2–14は印刷2–14。式番号S1–S24等で追跡する。\n- 教科書：`sources_local/textbook/complex_networks_ch8.pdf`。見開き、PDF1左148/右149、PDFk左146+2k/右147+2k。第8章は印刷149–192。表紙・奥付なし、書誌の著者・版は未確定。\n- 講義3・4・7・9：`sources_local/lectures/slide-lectureX.pdf`。PDFページ＝表示スライド番号。用語・説明表現の参考と科学的根拠を区別する。\n- 本研究：`analysis/presentation_spp_comparison_ja_v2/data/`。発表に使う表を`data/`へ複写。コードは`app/src/main/java/spp/`。PDFのページ規約は適用しない。\n\n## スライド別対応\n\n'''
out=[intro]
out.append('主な原典：Kim & Radicchi, “Shortest-Path Percolation on Random Networks”, Physical Review Letters 133, 047402 (2024), DOI: 10.1103/PhysRevLett.133.047402。\n\n')
for s in SLIDES:
    out.append(f'### {s["id"]:02d}　{s["title"].replace(chr(10),"：")}\n\n')
    out.append(f'- 科学的主張：{"；".join(s["body"])}\n- 区分：{s["classification"]}\n- 参照資料・PDF／印刷ページ・式／図：{s["footer"]}\n- 数式・数値・図：{"；".join(s["formula"]) or (s["asset"] or s["chart"] or "上記の定義・比較表")}\n- 根拠となる記述：{s["evidence"]}\n- 導出・解釈と限界：{s["notes"].split("【説明】",1)[1]}\n\n')
out.append('## 再生成とデータの来歴\n\n`prepare_deck.py`→`.build/deck.json`→`build_powerpoint.ps1`→`slides/`。図2・3・5は原典画像を切り出す。研究曲線は既存表の値を変えずnative chartへ格納。要求状態のfirst-crossingに対応する階段を表示し、途中を単一辺の実測とみなさない。最大落下はrun表との平均・SEM照合済み。模式図だけは定義用の任意関数で、研究結果ではない。\n')
(HERE/'source_map.md').write_text(''.join(out),encoding='utf-8')
provenance={}
for rel in ['analysis/presentation_spp_comparison_ja_v2/data/'+name for name in ['curves.csv','event_summary.csv','event_runs.csv','request_guarantees.csv','tail_guarantees.csv','limit_model_fits.csv']]:
    p=safe_input(rel);provenance[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
(HERE/'data'/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
print(f'Prepared {len(SLIDES)} slides, empirical tables, source map, and source-figure crops.')
