# 2026年10月15日ゼミ：10枚版と板書案

今回の協議で確定した10枚構成を新規制作した。旧 `seminar.pptx`／`seminar.pdf` は変更しない。説明範囲はSupplemental Materialの式(S1)〜(S5)まで。式(S6)以降のFSSの詳細、研究データのグラフ、臨界指数の推定結果は今回の資料に含めない。

## 成果物

- `slides/seminar_01-10.pptx`：表紙を含む厳密10枚、各ページに発表者ノート。
- `slides/seminar_01-10.pdf`：同じ10枚の閲覧用PDF。
- `board/board_notes_01-10.md`：編集可能な発表用カンニングペーパー。口頭メモと実際に書く式を分け、重点板書の導出を収録。
- `board/board_notes_01-10.pdf`：A4・3ページ。本文11.5pt、表示数式13.5pt。1ページ目はスライド1〜7、2ページ目は8、3ページ目は9〜10。
- `board/source_check_01-10.md`：一次資料・式・図・作図・出力の検証記録。
- `progress_01-10.md`：進捗と再開手順。

|頁|内容|板書との対応|
|---|---|---|
|1|表紙|板書なし|
|2|研究背景 ― パーコレーションと相転移|板書なし、口頭導入|
|3|SPPの基本操作、原論文Fig.1(a)(b)|図を指す口頭メモ|
|4|2次元正方格子上でのSPPの操作|格子図を指す口頭メモ|
|5|SPP論文における先行研究|板書なし、著者の数値的報告|
|6|本研究の目的|板書なし、未解決の研究目的|
|7|SPPにおける制御変数と最大連結成分|画面の(S1)・(S2)を指し、口頭で説明|
|8|平均クラスターサイズ S|重点板書：二乗の理由→m_s/n_s表記→最大除外|
|9|ネットワークサイズと相転移の関係|口頭のみ。画面のN=L²を指す|
|10|べき乗則と指数の推定方法|重点板書：倍率→対数変換→傾き→回帰|

## 出典と制作方法

原典は `sources_local/papers/spp_main.pdf` と `spp_supplement.pdf`。依頼文の直下パスではなく、実際に存在する `papers/` 内の出版版と対応補足をタイトル・DOI・式番号で確認した。主要出典は本文PDF1〜2のモデルとFig.1、補足PDF1〜2のSec.II/III式(S1)〜(S5)。weakly discontinuousという用語の所在は本文PDF4。

Fig.1は原典PDFから全(a)(b)を切り出した引用画像。3×3格子はPowerPointの編集可能な頂点・辺で描画する。本文・記号説明も編集可能。数式は再現可能なMatplotlib数式画像を比率を保って配置し、元の式と導出は編集可能なMarkdownにも収録する。AI画像生成は使用しない。

格子例は9頂点・12辺、左上から右下まで最短4辺、最短経路6本。選択経路0→1→2→5→8の4辺だけを消し、残り8辺と全9頂点を描く。これは説明用の例であり、実験サイズではない。

既存PowerPoint COMとローカルTeX環境を使用する。専用artifact-toolランタイムは利用できないため、PowerPoint再読込、OOXMLの画像・格子集合、PDFページ・フォント、全ページ画像で検証する。新しいSPPシミュレーションや追加インストールは行わない。

## 再生成

板書だけを更新する場合は、以下のみを実行する。PowerPointやスライドPDFの生成処理は呼ばない。

```powershell
python -B presentation/2026-10-15/build_board_01_10.py
python -B presentation/2026-10-15/validate_01_10.py
pdftoppm -r 130 -png presentation/2026-10-15/board/board_notes_01-10.pdf presentation/2026-10-15/.build/ten-slide/board_cheatsheet/review
```

MDの`<!-- pagebreak -->`がページ境界、`<!-- write -->`〜`<!-- /write -->`が必須板書の枠。生成時に3〜4ページ、文字欠け、TeXのはみ出しを検査する。変更後はレンダリングした全ページを目視する。板書用のTeX・画像・ログは`.build/ten-slide/board_cheatsheet/`に保存し、PDFへ再生成手順のページは加えない。

以下はスライドも含めて最初から生成する場合の手順。今回のカンニングペーパー改訂では、上の板書用コマンドだけを実行した。

リポジトリ直下で以下を実行する。Windows、PowerPoint、Python 3、Matplotlib、Pillow、Poppler、および板書PDF用の既存TeX環境が必要。原典PDFはGit管理外なので、別端末で再生成する場合は正当なローカル資料を同じ位置へ配置する。完成PPTX・PDFの閲覧には原典ファイルは不要。

```powershell
python -B presentation/2026-10-15/prepare_01_10.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File presentation/2026-10-15/build_powerpoint_01_10.ps1
python -B presentation/2026-10-15/build_board_01_10.py
python -B presentation/2026-10-15/validate_01_10.py
```

中間JSON・原典抽出画像・数式画像・TeX中間・検証レポートは `.build/ten-slide/` のみ。`sources_local/` と `.build/` は既存のローカル `.gitignore` で除外する。旧35枚版、10月8日版、研究コード、研究CSVは保護する。

## 完成時の確認

スライド初版はPPTX再読込成功、10枚・発表者ノート10枚・16:9。格子の完成OOXMLで各段階の9頂点と辺集合12/12/12/8を照合し、原典図・式画像の埋込データも生成元と一致した。スライドPDF全10ページを画像化して個別に目視した。

板書は旧24ページ版を3ページの発表用メモへ全面改訂した。新PDF全3ページを130dpiで個別に確認し、必須板書の枠・口頭メモ・質問用補足が区別でき、文字・数式に欠落や重なりがないことを確認した。原典と説明用導出の区別、S3の前提と全計算、S4/S5の仮定・変換も独立レビュー済み。両PDFの全フォントは埋込済み。現行10枚PPTX/スライドPDFに加え、原典2PDF・旧35枚PPTX/PDF・10月8日最終PDFの計7ファイルのSHA-256が改訂前後で一致した。旧24ページ版はGit履歴`2b02f0e`から復元できる。
