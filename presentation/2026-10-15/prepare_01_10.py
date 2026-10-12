"""Prepare the new ten-slide deck. No simulation or research-data change.

Original PDFs are read only. All temporary assets stay in .build/ten-slide/.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
from collections import deque

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
BUILD = TASK / '.build' / 'ten-slide'
ASSETS = BUILD / 'assets'
BLUE, ORANGE, INK = '#17365D', '#E57A26', '#253746'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f'Outside this repository: {path}')
    return path


def formula(name, latex):
    path = ASSETS / f'{name}.png'
    fig = plt.figure(figsize=(10, 1.6), dpi=240)
    fig.patch.set_alpha(0)
    fig.text(0.01, 0.5, '$' + latex + '$', fontsize=32, color=BLUE,
             va='center', math_fontfamily='stix')
    fig.savefig(path, transparent=True, bbox_inches='tight', pad_inches=0.08)
    plt.close(fig)
    return str(path.relative_to(TASK)).replace('\\', '/')


def text(value, x, y, w, h, size=23, color=INK, bold=False, math=False):
    return dict(kind='text', text=value, x=x, y=y, w=w, h=h,
                size=size, color=color, bold=bold, math=math)


def image(path, x, y, w, h):
    return dict(kind='image', path=path, x=x, y=y, w=w, h=h)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    main_pdf = allowed(TASK / 'sources_local/papers/spp_main.pdf')
    sm_pdf = allowed(TASK / 'sources_local/papers/spp_supplement.pdf')
    for path in (main_pdf, sm_pdf, TASK/'slides/seminar.pptx', TASK/'slides/seminar.pdf'):
        if not path.is_file():
            raise FileNotFoundError(path)
    expected_sources = {
        main_pdf: '832a33f7605fbb72fac0a5493bcfa5a053e9908afdb856f34c6fc5660003b6bb',
        sm_pdf: 'd6660c8a293ef8cc8856a6654eafbf8b6166ad00aa8d3edb1330b16d510764d0',
    }
    for path, expected in expected_sources.items():
        if sha(path) != expected:
            raise ValueError(f'Source version differs from the checked publication: {path}')
    inventory_path = BUILD / 'protected_inputs.json'
    protected = [main_pdf, sm_pdf, TASK/'slides/seminar.pptx', TASK/'slides/seminar.pdf',
                 ROOT/'app/out/seminar-progress-2026-10-08/revised_slides/seminar_spp_2d_2026-10-08-final.pdf']
    if inventory_path.exists():
        inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
        for record in inventory:
            assert sha(allowed(ROOT / record['path'])) == record['sha256'], record['path']
    else:
        inventory = [{'path':str(allowed(p).relative_to(ROOT)).replace('\\','/'), 'sha256':sha(p)}
                     for p in protected]
        inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')

    # Source page 2. Crop contains the complete original panels (a) and (b),
    # without redrawing, recolouring or modifying any graph content.
    prefix = ASSETS/'main-page2'
    subprocess.run(['pdftoppm','-f','2','-l','2','-singlefile','-r','240','-png',
                    str(main_pdf), str(prefix)], check=True)
    page = Image.open(prefix.with_suffix('.png'))
    # Publisher PDF coordinates: top-left graph panels, before Fig.1 caption.
    box_pt = (50, 44, 298, 150)
    scale = page.width / 612.0
    crop = page.crop(tuple(round(v*scale) for v in box_pt))
    crop.save(ASSETS/'paper_fig1_ab.png')

    f = {
        's1': formula('eq_s1', r'p(t)=1-\frac{E_t}{E_1}\qquad\mathrm{(S1)}'),
        's2': formula('eq_s2', r'P=\frac{s_R}{\sum_{r=1}^{R}s_r}=\frac{s_R}{N}\qquad\mathrm{(S2)}'),
        'sort': formula('cluster_order', r's_1\leq s_2\leq\cdots\leq s_R'),
        's3': formula('eq_s3', r'S=\frac{\sum_{r=1}^{R-1}s_r^2}{\sum_{r=1}^{R-1}s_r}\qquad\mathrm{(S3)}'),
        'n': formula('size_n', r'N=L^2'),
        's4': formula('eq_s4', r'x=z\,y^{\zeta}\qquad\mathrm{(S4)}'),
        's5': formula('eq_s5', r'\log x=\log z+\zeta\log y\qquad\mathrm{(S5)}'),
    }

    # Open 3x3 illustration only. Its geometry is not used to infer the
    # boundary convention or measured values of any research dataset.
    vertices = [[3*r+c, 27+65*c, 22+65*r] for r in range(3) for c in range(3)]
    edges = [[3*r+c, 3*r+c+1] for r in range(3) for c in range(2)]
    edges += [[3*r+c, 3*(r+1)+c] for r in range(2) for c in range(3)]
    path_nodes = [0, 1, 2, 5, 8]
    selected = list(map(list, zip(path_nodes, path_nodes[1:])))
    norm = lambda e: tuple(sorted(e))
    E = {norm(e) for e in edges}
    D = {norm(e) for e in selected}
    assert len(vertices)==9 and len(E)==12 and len(D)==4 and D <= E
    assert all(abs(u//3-v//3)+abs(u%3-v%3)==1 for u,v in E)
    adjacency = {i:[] for i in range(9)}
    for u,v in edges:
        adjacency[u].append(v);adjacency[v].append(u)
    dist={0:0};count={0:1};queue=deque([0])
    while queue:
        u=queue.popleft()
        for v in adjacency[u]:
            if v not in dist:
                dist[v]=dist[u]+1;count[v]=0;queue.append(v)
            if dist[v]==dist[u]+1:count[v]+=count[u]
    assert dist[8]==4 and count[8]==6 and len(E-D)==8
    grid_check = dict(vertices=9, edges_before=12, selected_path=path_nodes,
                      selected_edges=selected, shortest_length=dist[8],
                      shortest_path_count=count[8], edges_after=8,
                      removed_edges_exactly_selected=True,
                      vertices_preserved=True,
                      illustration_only=True,
                      crop_source_page=2, crop_box_pt=box_pt)
    (BUILD/'grid_check.json').write_text(json.dumps(grid_check, ensure_ascii=False, indent=2),encoding='utf-8')

    slides=[]
    def add(title, elements, footer, notes, header=True):
        slides.append(dict(id=len(slides)+1,title=title,elements=elements,footer=footer,
                           notes=notes,header=header))
    paper='Kim & Radicchi (2024), PRL 133, 047402'
    add('2次元正方格子上のShortest-Path Percolation', [
        text('卒業研究 ゼミ発表',55,70,850,45,25,BLUE,True),
        text('2次元正方格子上の\nShortest-Path Percolation',55,180,850,135,42,BLUE,True),
        text('2026年10月15日',55,365,850,45,25),
    ],'', '今回の対象は2次元正方格子上のSPPです。研究途中であり、不連続転移の成立を確定した発表ではありません。今回の説明は研究背景、操作、研究目的、Supplemental Materialの式(S1)〜(S5)までです。所属・氏名は追加していません。板書なし。',False)
    add('研究背景 ― パーコレーションと相転移',[
        text('パーコレーションでは、辺の占有率などの変化に伴い、\nネットワーク全体の連結性がどのように変化するかを調べる。',50,125,860,75,23),
        text('最大連結成分の大きさ',50,225,355,32,22,BLUE,True),
        text('全体の頂点のうち、どの程度が一つにつながっているか。',50,260,860,35,21),
        text('臨界点と転移の性質',50,320,355,32,22,BLUE,True),
        text('転移が起こる位置と、連結成分の大きさが\n連続的に変化するのか、不連続に変化するのかに注目する。',50,355,860,65,21),
        text('これらの性質は、ネットワークの構造や辺の削除方法によって異なる場合がある。',50,450,860,32,19),
    ],paper+' 本文 PDF1／印刷047402-1',
    '板書なし。連結性・最大連結成分・臨界点・転移の性質を簡潔に導入します。削除だけがパーコレーションの本質とは説明しません。本文PDF1の一般的な背景とモデル依存性を日本語で要約しています。数学的な観測量はスライド7以降で定義します。')
    add('SPPの基本操作',[
        image('.build/ten-slide/assets/paper_fig1_ab.png',50,125,410,165),
        text('原論文 図1(a)(b)\n例：Q_t=4。C≥4なら削除可能。',55,300,410,50,18,BLUE,False,True),
        text('1. 異なる2頂点を同じ確率で選ぶ。\n2. 最短経路があり、\n　 長さがC以内か確認する。\n3. 最短経路を1本選ぶ。\n4. 経路上の全辺をまとめて削除する。',490,125,420,195,21),
        text('複数の最短経路がある場合は、\nその中から1本を等確率で選ぶ。',490,325,420,58,18),
        text('Q_t：最短経路の長さ（辺の本数）　 C：経路長の上限\nt：始点・終点の組が要求された回数',55,375,850,50,18,INK,False,True),
        text('経路がない、またはQ_t>Cなら削除しない。\n削除できなくてもtは1増え、辺集合は変わらない。',55,430,850,54,19,BLUE,False,True),
    ],paper+' 本文 PDF1–2／印刷047402-1–2、図1',
    '板書補助：G_t=(V,ℰ_t)、E_t=|ℰ_t|、Q_t≤C。G_tは要求tに利用可能なグラフで、削除後の状態と呼びません。元のFig.1(a)(b)を引用し、Q_t=4、C≥4を確認。成功なら選択経路の全辺を除き、失敗なら辺集合を保ったまま次の要求へ進みます。いずれもtが1増えます。本文PDF1–2、Fig.1 captionに基づく日本語説明です。')
    grid_elements=[]
    captions=['① 2頂点を選ぶ','② 最短経路を調べる','③ 最短経路を1本選ぶ','④ 選んだ4辺を削除']
    for stage,x in enumerate([40,272,504,736],1):
        grid_elements.append(text(captions[stage-1],x,130,190,50,17,BLUE,True))
        grid_elements.append(dict(kind='lattice',stage=stage,x=x,y=188,w=190,h=190,
                                  vertices=vertices,edges=edges,selected_edges=selected,
                                  source=0,target=8))
        label=['左上と右下を指定','長さ4の経路が6本','C≥4なら、1本を\n等確率で選ぶ','4辺を削除。\n9頂点は残る。'][stage-1]
        grid_elements.append(text(label,x,380,190,58,16))
    grid_elements += [
        text('横2辺＋縦2辺で最短経路長は4。C<4なら削除しない。',50,430,860,28,20,BLUE),
        text('削除の成否にかかわらず、次の要求へ進む。',50,459,860,25,18),
    ]
    add('2次元正方格子上でのSPPの操作',grid_elements,
    '説明用3×3格子（実験サイズではない）。原論文のSPP規則を適用した作図。',
    '板書補助：横2回＋縦2回＝4辺。初期3×3格子の左上と右下には6本の最短経路があります（横2回・縦2回の順序）。図では上側2辺、右側2辺の計4辺を選び、C≥4の場合だけ削除します。除去辺集合は{0–1,1–2,2–5,5–8}、初期12辺から8辺になります。9頂点は削除しません。C<4なら初期の辺集合を保持して次の要求へ進みます。図の開いた外周はこの説明例の指定であり、研究本体の境界条件をこの図から断定しません。')
    add('SPP論文における先行研究',[
        text('Kim & Radicchi (2024) は、ERランダムネットワーク上でSPPを実行し、\n経路長の上限Cによる相転移の違いを調べた。',50,125,860,76,23),
        text('Cが有限の場合',50,230,860,32,23,BLUE,True),
        text('通常のパーコレーションと同じ普遍性クラスに属する\n連続転移が報告された。',50,270,860,64,22),
        text('経路長に制限がない場合',50,355,860,32,23,BLUE,True),
        text('通常のパーコレーションより急激な転移が報告された。',50,395,860,36,22),
        text('著者の表現は “weakly discontinuous”。数値解析に基づく評価である。',50,452,860,32,19),
    ],paper+' 本文 PDF1–2／047402-1–2。用語はPDF4／047402-4。',
    '板書なし。これはER上での著者の数値的報告です。有限CはNを増やしても固定された予算を指します。有限グラフでは到達可能な最短経路はN−1辺以下なのでC=Nなら長さ制限は実質ありません。weakly discontinuousという語は本文PDF4にあり、今回その転移幅の詳細は説明しません。数学的に不連続転移が証明されたとは述べません。')
    add('本研究の目的',[
        text('ERランダムネットワーク上のSPPでは、\n経路長に制限がない場合に急激な転移が報告された。',50,125,860,72,23),
        text('ネットワークの構造が異なる場合にも、\n同様の転移が見られるのだろうか。',50,230,860,72,25,BLUE),
        text('規則的な構造を持つ2次元正方格子上でSPPを実行する。',50,335,860,38,23),
        text('特に経路長に制限がない場合に、\n不連続転移が起こるかどうかを調べる。',50,400,860,70,26,BLUE,True),
    ],'先行研究：本文 PDF1–2。研究目的は本研究の問い（原論文の結論ではない）。',
    '板書なし。研究目的は制限なしSPPで不連続転移が起こるかを調べることであり、weakly discontinuousの再現を目的に変えません。サイズを大きくしても不連続性が残るかが重要です。ERでの結果を格子へ無条件に適用しません。研究結果・指数は今回の10枚には掲載しません。')
    add('SPPにおける制御変数と最大連結成分',[
        image(f['s1'],50,130,360,78),
        text('p(t)：要求tに対応する時点の辺の削除率\nE_1：初期辺数\nE_t：要求tに利用可能なグラフの辺数',440,128,470,95,19,INK,False,True),
        text('t：始点・終点の組が要求された回数',50,232,860,30,19,INK,False,True),
        image(f['s2'],50,292,360,92),
        text('P：最大連結成分の割合\ns_R：最大連結成分の頂点数\nR：連結成分の総数　 N：総頂点数',440,285,470,98,20,INK,False,True),
        text('pで削除の進行、Pで最大連結成分の大きさを測る。\n削除できない要求でもtは増えるが、pは変わらない。',50,425,860,65,20,BLUE,False,True),
    ],'Kim & Radicchi (2024), Supplemental Material II、PDF1–2、式(S1)・(S2)。',
    '板書案No.1。SM PDF1式(S1)はG_tがt番目の要求に利用可能なグラフと定義します。辺集合ℰ_tと辺数E_t=|ℰ_t|を区別します。p=(E_1−E_t)/E_1から導出。SM PDF2式(S2)は全連結成分の頂点数の和がNなのでP=s_R/N。この等号は代数的補足です。tを要求tの削除後という意味にしません。')
    add('平均クラスターサイズ S',[
        image(f['sort'],50,120,360,45),
        image(f['s3'],50,195,430,105),
        text('R：連結成分の総数\ns_r：第r番目の連結成分の頂点数\ns_R：最大連結成分の頂点数\nS：最大連結成分を除いた\n　 平均クラスターサイズ',525,124,385,172,19,INK,False,True),
        text('最大連結成分を1個除き、残りのクラスターの大きさからSを定義する。',50,335,860,36,21),
        text('残りの頂点を一様ランダムに選んだとき、その頂点が属する\nクラスターの大きさの期待値として解釈できる。',50,395,860,66,22,BLUE),
        text('期待値の説明は、式(S3)の数学的な補足。',50,462,860,24,16),
    ],'Kim & Radicchi (2024), Supplemental Material II、PDF2／印刷2、式(S3)。',
    '板書案No.2。S3の和はr=1からR−1で最大を1個除きます。期待値解釈は数学的補足であり、原論文が頂点を抽出して測定したという主張ではありません。詳細な頂点重みの導出、m_s・n_sとの等価性、最大成分の支配的寄与、R=1の注意は独立した板書案に記載します。同率最大なら1個だけ除きます。')
    add('ネットワークサイズと相転移の関係',[
        text('有限サイズのネットワークでは、相転移付近の観測量が\nネットワークサイズNの影響を受ける。',50,125,860,70,23),
        text('Pが急激に減少しても、有限サイズでの観測だけでは、\n大きなサイズの極限でも不連続な変化が残るとは判断できない。',50,225,860,70,23),
        text('Nを変えて観測量の変化を調べ、大きなサイズでの振る舞いを推定する。',50,326,860,40,22,BLUE),
        image(f['n'],50,406,225,54),
        text('N：ネットワークの頂点数\nL：2次元正方格子の一辺の頂点数\nP：最大連結成分の割合',330,395,580,85,20),
    ],'サイズ依存解析への動機付け（本発表の説明）。Pの定義：補足 式(S2)。',
    '板書案No.3-A。P=s_max/N、N=L²。有限Nでs_maxは整数であり、Pの取り得る値は離散的です。要求1回で複数辺を削除することもあります。ある有限サイズでの急変だけでは無限サイズの不連続性は判断できません。これは解析への動機付けで、原論文の日本語逐語引用ではありません。S4/S5と指数計算は次のスライドへ進め、FSSの式は先取りしません。')
    add('べき乗則と指数の推定方法',[
        text('数値データのサイズ依存性を調べるため、原論文ではべき乗則を仮定し、\n回帰分析によって指数を推定する。',50,125,860,72,23),
        image(f['s4'],50,220,300,70),
        image(f['s5'],410,220,500,70),
        text('x, y：関係を調べる正の量　 z：比例係数（z>0）\nζ：推定するべき指数（ゼータ）　 log：対数',50,320,860,62,20),
        text('対数変換したデータに直線回帰を行い、傾きから指数ζを推定する。',50,410,860,36,22,BLUE),
        text('この方法を、後に扱う有限サイズスケーリングでの臨界指数推定に利用する。',50,457,860,28,18),
    ],'Kim & Radicchi (2024), Supplemental Material III、PDF2／印刷2、式(S4)・(S5)。',
    '板書案No.3-B。S4は仮定、S5はx,y,z>0で対数法則を適用した結果です。X=log y、Y=log x、b=log zとすればY=ζX+bとなり、傾きが指数です。対数の底は共通で1以外の正数を使います。最小二乗公式は板書補足のみ。FSSの関係はS4/S5から自動的に導出されず、直線への当てはまりだけでべき乗則は証明されません。今回はS5で終え、S6以降の詳細や未定義の臨界指数を先取りしません。')
    assert len(slides)==10
    for i,s in enumerate(slides,1):assert s['id']==i
    payload=dict(canvas=[960,540], font='Meiryo', colors=dict(blue=BLUE,orange=ORANGE,ink=INK),
                 slides=slides, scope='S1-S5 only', source_pdfs=[str(main_pdf),str(sm_pdf)])
    (BUILD/'deck.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared exactly 10 slides; grid assertions passed (9 vertices, 12 -> 8 edges, Q=4, 6 shortest paths).')


if __name__ == '__main__':
    main()
