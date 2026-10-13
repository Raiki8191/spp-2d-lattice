"""Prepare the FSS appendix only. Original slides, notes and research data are read-only."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

TASK=Path(__file__).resolve().parent
ROOT=TASK.parents[1]
BUILD=TASK/'.build/fss_append'
ASSETS=BUILD/'assets'
BLUE,ORANGE,INK='#17365D','#E57A26','#253746'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def formula(name,latex):
    path=ASSETS/(name+'.png')
    fig=plt.figure(figsize=(12,1.6),dpi=260)
    fig.patch.set_alpha(0)
    fig.text(.01,.5,'$'+latex+'$',fontsize=32,color=BLUE,va='center',math_fontfamily='stix')
    fig.savefig(path,transparent=True,bbox_inches='tight',pad_inches=.08)
    plt.close(fig)
    return path.relative_to(TASK).as_posix()


def text(value,x,y,w,h,size=23,color=INK,bold=False,math=False):
    if math:
        # Delimit editable math runs explicitly, so adjacent Japanese text is
        # never consumed as part of a subscript/superscript by the old renderer.
        value=re.sub(r'([A-Za-z])_([A-Za-z0-9]+)',r'\1_{\2}',value)
        value=re.sub(r'\^([A-Za-z0-9]+)',r'^{\1}',value)
    return dict(kind='text',text=value,x=x,y=y,w=w,h=h,size=size,color=color,bold=bold,math=math)


def image(path,x,y,w,h):
    return dict(kind='image',path=path,x=x,y=y,w=w,h=h)


def main():
    ASSETS.mkdir(parents=True,exist_ok=True)
    raw=TASK/'sources_local/papers/spp_supplement.pdf'
    assert sha(raw)=='d6660c8a293ef8cc8856a6654eafbf8b6166ad00aa8d3edb1330b16d510764d0'
    main_pdf=TASK/'sources_local/papers/spp_main.pdf'
    assert sha(main_pdf)=='832a33f7605fbb72fac0a5493bcfa5a053e9908afdb856f34c6fc5660003b6bb'
    protected_path=BUILD/'protected_inputs.json'
    if not protected_path.exists():
        paths=[TASK/'slides/seminar_01-10.pptx',TASK/'slides/seminar_01-10.pdf',
               TASK/'board/board_notes_01-10.md',TASK/'board/board_notes_01-10.pdf',
               main_pdf,raw,TASK/'slides/seminar.pptx',TASK/'slides/seminar.pdf',
               ROOT/'app/out/seminar-progress-2026-10-08/revised_slides/seminar_spp_2d_2026-10-08-final.pdf']
        protected_path.write_text(json.dumps([dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
                                              for p in paths],indent=2),encoding='utf-8')
    for item in json.loads(protected_path.read_text(encoding='utf-8')):
        path=(ROOT/item['path']).resolve()
        assert path.is_relative_to(ROOT) and sha(path)==item['sha256'],item['path']
    crops={
        'fig_s1_ab':(3,(102,48,519,203)),
        'fig_s1_cd':(3,(102,204,519,356)),
        'fig_s2_a':(4,(50,188,146,295)),
        'fig_s2_bc':(4,(146,188,335,295)),
        'fig_s2_de':(4,(335,188,520,295)),
        'fig_s2_legend':(4,(522,215,568,256)),
        'table_s2':(4,(145,407,468,497)),
    }
    source_pages={}
    for page in [3,4]:
        prefix=ASSETS/f'sm-page{page}'
        subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-singlefile',
                        '-r','340','-png',str(raw),str(prefix)],check=True)
        source_pages[page]=Image.open(prefix.with_suffix('.png'))
    crop_paths={}
    for name,(page,box) in crops.items():
        source=source_pages[page];scale=source.width/612
        path=ASSETS/(name+'.png')
        source.crop(tuple(round(v*scale) for v in box)).save(path)
        crop_paths[name]=path.relative_to(TASK).as_posix()
    (BUILD/'source_crops.json').write_text(json.dumps(crops,indent=2),encoding='utf-8')
    definitions={
        's6':r'\langle P(p,N)\rangle=N^{-\beta/\bar\nu}F^{(1)}[(p-p_c)N^{1/\bar\nu}]\qquad\mathrm{(S6)}',
        's7':r'\langle S(p,N)\rangle=N^{\gamma/\bar\nu}F^{(2)}[(p-p_c)N^{1/\bar\nu}]\qquad\mathrm{(S7)}',
        'u':r'u=(p-p_c)N^{1/\bar\nu}',
        's8':r'p_c(N)=\underset{p}{\operatorname{arg\,max}}\,\langle S(p,N)\rangle\qquad\mathrm{(S8)}',
        's9':r'p_c=p_c(N)+bN^{-1/\bar\nu}\qquad\mathrm{(S9)}',
        's10':r'P(p_c)=\langle P(p=p_c,N)\rangle\sim N^{-\beta/\bar\nu}\qquad\mathrm{(S10)}',
        'zero':r'p=p_c\quad\Longrightarrow\quad u=0',
        's11':r'P_c(N)=\langle P(p=p_c(N),N)\rangle\sim N^{-\beta/\bar\nu}\quad\mathrm{(S11)}',
        's12':r'S_c(N)=\langle S(p=p_c(N),N)\rangle\sim N^{\gamma/\bar\nu}\quad\mathrm{(S12)}',
        'slope_shift':r'|p_c-p_c(N)|\sim N^{-1/\bar\nu}',
        'slope_p':r'\log\langle P(p_c,N)\rangle=\mathrm{const}-\frac{\beta}{\bar\nu}\log N',
    }
    (TASK/'fss_equations.json').write_text(json.dumps(definitions,ensure_ascii=False,indent=2),encoding='utf-8')
    f={key:formula('eq_'+key,value) for key,value in definitions.items()}
    slides=[]
    def add(title,elements,source,notes):
        slides.append(dict(id=11+len(slides),title=title,elements=elements,footer=source,notes=notes,header=True))
    sm='Kim & Radicchi (2024), Supplemental Material '
    add('有限サイズスケーリング（FSS）',[
        text('有限サイズでは、転移の位置や観測量が頂点数Nに依存する。',50,125,860,40,25),
        text('異なるNの結果を比較するため、臨界点付近のサイズ依存性を\n一定のスケーリング則で表す。',50,210,860,75,25,BLUE),
        text('サイズ依存性から、臨界点と臨界指数を推定する。',50,330,860,40,25),
        text('スライド9の「サイズを変える理由」と、10の「べき乗回帰」を結び付ける。\nFSSの形は仮定であり、当てはまりだけで正しさが保証されるわけではない。',50,415,860,65,20),
    ],sm+'IV.A、PDF2／印刷2、式(S6)・(S7)。',
    '有限サイズの位置と観測量を共通のスケーリング仮定で結び付ける動機。自分のデータは新規に示さない。前10枚の定義と回帰に続く追加部分。FSSはSPPの定義からの厳密な恒等式ではない。')
    add('Pの有限サイズスケーリング',[
        image(f['s6'],50,122,860,80),
        text('前の係数はPのサイズ依存、関数の引数は臨界点からの距離を表す。',50,214,860,35,21),
        image(f['u'],50,266,405,55),
        text('異なるNを、共通の変数uで比較する。\nuは説明用に導入する補助記号。',490,263,420,65,20),
        text('β（ベータ）：Pの臨界指数\nν̄（ニューバー）：相関体積の臨界指数\n〈…〉：試行間平均',50,359,445,102,20,INK,False,True),
        text('p_c：無限サイズの臨界点\nF⁽¹⁾：Pのスケーリング関数\np：辺の削除率　N：頂点数',510,359,400,102,20,INK,False,True),
    ],sm+'IV.A、PDF2／印刷2、式(S6)。',
    'S6原文照合。βはpercolation strength、ν̄はcorrelation volumeに対応。uは説明用の補助記号。p-p_cがN^{-1/ν̄}程度ならuは同程度となり、p-p_cをN^{1/ν̄}倍して比較するというFSSの考え方。関数形を独自に決定しない。p_cは無限サイズ、p_c(N)は後で定義する。')
    add('Sの有限サイズスケーリング',[
        image(f['s7'],50,130,860,80),
        text('γ（ガンマ）：平均クラスターサイズSの臨界指数\nF⁽²⁾：Sに対応するスケーリング関数',50,245,860,70,23),
        text('PとSは共通の変数uを使う。\n前の係数は、PではNの負の指数、Sでは正の指数。',50,355,860,70,23,BLUE),
        text('β・γ・ν̄が正なら、同じuでのPの減少とSの増大を表す。\nF⁽¹⁾とF⁽²⁾の具体的な形は、ここでは指定しない。',50,430,860,55,18),
    ],sm+'IV.A、PDF2／印刷2、式(S7)。',
    'S7はS6と同じスケーリング変数を使う。PとSの大きさを表す指数の符号は異なる。指数の正値と適切な関数値という条件の下でサイズ依存を解釈する。Sは最大成分1個を除いた定義を引き継ぐ。')
    add('疑似臨界点：平均Sのピーク位置',[
        image(f['s8'],70,135,820,90),
        text('p_c(N)：サイズNでの疑似臨界点（ピー・シー・エヌ）\nargmax（アーグマックス）：最大値を取る変数の値を求める。',50,255,860,76,23,INK,False,True),
        text('ここで求めるのは、平均Sのピークの高さではなく、その削除率p。',50,355,860,40,23,BLUE),
        text('同じpで試行間平均し、その曲線の最大位置を求める。\n各試行のピーク位置を求めてから平均する操作とは異なる。',50,415,860,60,21),
    ],sm+'IV.A、PDF3／印刷3、式(S8)。',
    '通常のアンサンブルにおける著者の疑似臨界点の定義。argmaxは最大値そのものではなく横軸の位置。疑似臨界点には他の定義もあるが、この資料はS8に限定する。イベント基準のS13以降へ広げない。')
    add('臨界点と疑似臨界点の関係',[
        image(f['s9'],90,133,780,85),
        text('p_c(N)とp_cのずれを、Nのべき乗で表すシフト則。\n原論文は推定したp_cと複数サイズのp_c(N)から、1/ν̄を調べる。',50,265,860,75,24,BLUE,False,True),
        text('b（ビー）：サイズに依存しない係数。符号は固定しない。\nν̄>0なら、この形のずれはNの増大とともに小さくなる。',50,365,860,70,21,INK,False,True),
        text('S7のピークが一定のuに対応する等の前提を置いた、FSSのシフト則。',50,453,860,30,18),
    ],sm+'IV.A、PDF3／印刷3、式(S9)。',
    '原文の符号はp_c=p_c(N)+bN^{-1/ν̄}。S7のスケーリング関数の最大位置u_*がNによらず、ピークが観測範囲内で、サイズ補正を無視できる等の追加前提の下でb=-u_*と対応付けられる。bの正負やどちら側から近づくかを無条件に断定しない。')
    add('臨界点でのサイズ依存性',[
        image(f['s10'],50,125,860,80),
        text('原論文のP(p_c)は、N依存を省略した平均Pの簡略表記。\n全サイズで同じp=p_cを使う。',50,225,860,70,22,INK,False,True),
        image(f['zero'],50,325,380,55),
        text('F⁽¹⁾(0)が有限の非零定数なら、\nNに関するべき乗則が得られる。',480,320,430,62,21),
        text('横軸log N、縦軸log〈P〉の傾きは−β/ν̄。\n候補のpを変えて回帰の当てはまりを比較し、p_cを調べる。',50,416,860,67,21,BLUE,False,True),
    ],sm+'IV.B、PDF3／印刷3、式(S10)。',
    'S10の正確な左辺はP(p_c)=〈P(p=p_c,N)〉。同じp_cで全Nを評価し、P_c(N)とは異なる。S6にp=p_cを代入しF^{(1)}(0)が有限非零という前提で比例則。候補pごとにlogNとlog平均Pを回帰し最も良いべき乗近似を探す。~は漸近的なべき乗関係。Fig.S1で実例を説明する。')
    add('疑似臨界点での指数推定',[
        image(f['s11'],50,124,860,75),
        image(f['s12'],50,225,860,75),
        text('小文字p_c(N)は削除率の位置。\n大文字P_c(N)・S_c(N)は、その位置での平均P・平均S。',50,330,860,65,22,INK,False,True),
        text('S9を使うと、スケーリング変数はu=−bでNによらず一定。\nFSSとシフト則、有限の非零関数値の前提の下で、\nサイズ依存から指数比を推定できる。',50,400,860,84,20,BLUE,False,True),
    ],sm+'IV.B、PDF4／印刷4、式(S11)・(S12)。',
    'P_c(N)=〈P(p=p_c(N),N)〉、S_c(N)=〈S(p=p_c(N),N)〉。S8の平均S最大位置で評価する。S9から[p_c(N)-p_c]N^{1/ν̄}=-b。そのためS6/S7の関数値がNによらない定数となる。対数の傾きはP側−β/ν̄、S側γ/ν̄。これは仮定からの数学的説明で、SPP転移次数の証明ではない。')
    add('原論文の臨界点推定：C=1',[
        image(crop_paths['fig_s1_ab'],40,130,670,250),
        text('ER上の結果\np_c=0.750\nΔ=0.005',745,140,180,100,21,BLUE,False,True),
        text('Δ：比較するpの幅\nr：回帰の相関係数',745,270,180,80,18,INK,False,True),
        text('(a) 固定pで平均PとNを両対数回帰し、決定係数r²の最大位置を探す。\n(b) p_cと、その前後p_c±Δの平均Pのサイズ依存を比較する。',50,405,860,65,21,INK,False,True),
    ],sm+'III・IV.B、PDF2–3／印刷2–3、Fig.S1(a)(b)。',
    '元図を正確に抽出。aは線形p対r²、bは両対数N対平均P。rは回帰のPearson相関係数、r²は決定係数。Δは比較するpの正の幅。黄色ひし形がr²最大のp_c=0.750、Δ=0.005。r²が高いことだけで転移次数の証明にはならない。図中Pは平均の簡略記法。')
    add('原論文の臨界点推定：制限なし',[
        image(crop_paths['fig_s1_cd'],40,130,670,250),
        text('ER上の結果\np_c=0.646\nΔ=0.01',745,140,180,100,21,BLUE,False,True),
        text('黒：p=p_c\n紫：p=p_c−Δ\n赤：p=p_c+Δ',745,270,180,95,18,INK,False,True),
        text('(c)(d)はC=1と同じ手順。図(c)のr²軸は約0.7〜1に拡大。\n著者は、制限なしの固定p_cでの指数に強い有限サイズ効果を指摘する。',50,405,860,65,21,INK,False,True),
    ],sm+'IV.B、PDF3／印刷3、Fig.S1(c)(d)。',
    '制限なしは原図C=∞、数値設定はC=N。cのr²縦軸は0.7付近から1付近でaと同じ範囲ではない。dは両対数。著者は固定p_cに基づく制限なしの臨界指数に強い有限サイズ効果があり、p_cの推定は影響されないと述べる。これは著者の評価で、2D格子へ移さない。')
    add('原論文のシフト則の当てはめ',[
        image(crop_paths['fig_s2_a'],45,125,285,320),
        image(f['slope_shift'],390,130,510,68),
        text('Fig.S2(a)：両対数の傾きから−1/ν̄を推定する。\nS9が成り立ち、b≠0の場合。',390,225,520,72,21,BLUE,False,True),
        image(crop_paths['fig_s2_legend'],400,326,185,120),
        text('縦軸は見やすさのため10^Xで割る。\nX=0,1,2,3をC=1,2,3,Nに対応。\n定数倍は両対数の傾きを変えない。',610,333,300,95,18,INK,False,True),
        text('絶対値の図なので、bの符号や近づく側は分からない。',390,454,520,27,18),
    ],sm+'IV.B、PDF4／印刷4、Fig.S2(a)、式(S9)。',
    'S2aはN対|p_c-p_c(N)|/10^X、両対数。線はlog変換したデータへの単回帰、点は平均値、混雑回避で誤差棒は非表示。凡例C=∞はC=N。Xは表示のずらし用定数で、旧スライド10のlog yのXとは別記号。絶対値からbの符号は推定できない。')
    add('固定した臨界点でのP・Sの指数',[
        image(crop_paths['fig_s2_bc'],40,125,560,320),
        text('(b) 平均Pの傾き：−β/ν̄\n(c) 平均Sの傾き： γ/ν̄\n全Nで同じp_cを用いる。',650,145,275,115,20,BLUE,False,True),
        image(crop_paths['fig_s2_legend'],650,292,190,122),
        text('両対数軸。縦軸の10^Xによる定数倍、誤差棒省略は原図の表示。',50,457,860,27,17,INK,False,True),
    ],sm+'IV.B、PDF4／印刷4、Fig.S2(b)(c)、式(S6)・(S7)・(S10)。',
    'b固定p_cの平均P、c固定p_cの平均S。cのべき則はS7にp_cを代入した対応で、S12ではない。S12はピーク位置のSなので区別。両対数N対平均観測量/10^X。制限なしの固定p_c指数には強い有限サイズ効果があると著者が説明。図を実測2D格子と呼ばない。')
    add('疑似臨界点でのP・Sの指数',[
        image(crop_paths['fig_s2_de'],40,125,560,320),
        text('(d) P_c(N)の傾き：−β/ν̄\n(e) S_c(N)の傾き： γ/ν̄\nNごとにp_c(N)を用いる。',650,145,275,115,20,BLUE,False,True),
        image(crop_paths['fig_s2_legend'],650,292,190,122),
        text('同じ指数比を狙う方法でも、評価位置と有限サイズ効果を区別する。',50,457,860,27,18),
    ],sm+'IV.B、PDF4／印刷4、Fig.S2(d)(e)、式(S11)・(S12)。',
    'd/eのPc/Scは平均Sのピーク位置p_c(N)での平均。著者はこの方法が任意Cで適切な指数推定を与えると述べるが、数学的保証とは説明しない。固定p_cとピーク位置の結果を比較し、評価位置の違いを保持。軸は両対数、表示倍率/10^Xは原図どおり。')
    add('原論文の推定値と2D格子との区別',[
        image(crop_paths['table_s2'],55,117,850,233),
        text('ERのTable S2：criticalは固定p_c、pseudo-criticalは平均Sのピーク位置。\n有限C=1,2,3は近い指数比。制限なしは異なる推定値を報告。\n制限なしの固定p_cの指数には、強い有限サイズ効果がある。',50,354,860,77,19,INK,False,True),
        text('2D格子ではN=L²とサイズ変数を明示し、指数と転移の性質を別に調べる。',50,435,860,27,17,BLUE),
        text('C=1のS_c指数の誤差：表は±0.001、主論文PDF3は±0.01（原文どおり掲載）。',50,466,860,20,15,INK,False,True),
    ],sm+'IV.B、PDF4／印刷4、Table S2。主論文PDF3／047402-3。',
    '原表を数値変更せず抽出。C=1,2,3,∞の全行。∞はC=N。列はpc,1/ν̄、固定pcでのβ/ν̄,γ/ν̄、疑似臨界でのβ/ν̄,γ/ν̄。指数の±はSecIIIが残差正規性仮定の回帰係数標準誤差と説明。pcの±の決め方まで同じとは断定しない。表のC1ピークγ/ν̄誤差±.001と主論文PDF3左段±.01は出典内表記差であり無断修正しない。2Dのν̄=2νを理論前提なしに断定せず、指数比だけで不連続性を証明しない。')
    assert len(slides)==13 and slides[-1]['id']==23
    payload=dict(canvas=[960,540],font='Meiryo',colors=dict(blue=BLUE,orange=ORANGE,ink=INK),
                 slides=slides,total_slides=23,scope='Append S6-S12; conventional ensemble only',
                 source_pdfs=[str(raw)],source_crops=crops)
    (BUILD/'deck_fss.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared slides 11-23 (13 additional), S6-S12 and original Fig.S1/S2/Table S2 only.')


if __name__=='__main__':
    main()
