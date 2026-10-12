# 2026年10月15日 卒業研究ゼミ

原論文・補足資料・教科書・講義に基づき、SPPの相転移と数値解析方法を説明する日本語資料。2D正方格子での不連続転移は確定していない。

SPPはShortest-Path Percolation。主な原典はKim & Radicchi, “Shortest-Path Percolation on Random Networks”, Physical Review Letters **133**, 047402 (2024), DOI: 10.1103/PhysRevLett.133.047402。

## 成果物

- `slides/seminar.pptx`：本編24枚、質疑導入1枚、予備10枚。本文・表・研究グラフは編集可能。全ページに発表者ノートを付す。
- `slides/seminar.pdf`：同じ35ページの閲覧・投影用PDF。
- `outline.md`：7章と時間配分。本編88分、質疑・議論32分。
- `source_map.md`：全スライドの主張、式・図、PDF／印刷ページ、導出・解釈の区別。
- `study/`：学習計画、数式導出、想定質問。発表前に原典へ戻って確認するための資料。
- `open_questions.md`：未確認事項と判断の限界。
- `data/`：研究図に使う既存数値表の複写と入力SHA256。曲線はL=128、最大要求落下は制限なし全16サイズ。
- `progress.md`：完了工程、検証、Git保存、再開手順。
- `validation_report.md`：最終の出典・数値・表示の検証結果と限界。

## 発表で守る区別

`p`は辺の削除率、`q`は通常ボンドの占有確率。`S`は最大クラスターを1個だけ除いた頂点重み平均。ER論文の`ν̄`と2D格子の`ν`は別の指数。原論文の最大単一辺落下と本研究の最大要求落下は別のイベントである。急峻化、幅縮小、最大要求落下の正の極限、極限平均曲線の不連続性は同じ主張ではない。

原典図2・3・5を引用する。研究図は既存03・06・11に対応する数値表だけを使う。図11は予備へ置く。誤差帯を省いた平均曲線、終端印、最大要求落下の平均±標準誤差を表示し、平滑化や未観測部分の補完は行わない。

## 再生成

Windows、Microsoft PowerPointとExcel、Python 3、Pillow、Poppler（`pdftoppm`、`pdftotext`、`pdfinfo`、`pdffonts`）を使う。今回の環境で既存インストールを利用し、追加購入・大規模シミュレーションは行っていない。

リポジトリ直下で実行する。

```powershell
python -B presentation/2026-10-15/prepare_deck.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File presentation/2026-10-15/build_powerpoint.ps1
python -B presentation/2026-10-15/validate_deck.py
```

生成にはローカルの`source_map.md`記載の原典PDFと、`analysis/presentation_spp_comparison_ja_v2/data/`の入力が必要。GitHub上の完成PPTX／PDFの閲覧にはこれらのローカル入力は不要。原典を公開するためのスクリプトではない。

`prepare_deck.py`が出典・本文・ノート・研究図データを`.build/deck.json`へまとめ、原典図を切り出す。`build_powerpoint.ps1`がPowerPointのネイティブオブジェクトを作り、PPTX／PDF／全ページPNGを出力する。研究グラフの元値と標準誤差はPPTX内のExcelワークブックにも格納する。模式図だけは定義用の任意関数であり、研究データではない。

作成用artifact-toolランタイムが利用できなかったため、PowerPoint COMへ切り替えた。専用ランタイムの検証は実行していない。代わりにPowerPointでの保存・再読込、OOXMLのキャッシュ値とSEMの照合、PDFのページ・フォント確認、全ページ画像の目視確認を完了した。検証結果は`validation_report.md`と`progress.md`に記録する。

`sources_local/`と`.build/`はGit管理外。原典PDF、元データ、既存研究図、シミュレーションコードは変更しない。
