# 作成結果・自己点検

日本語の研究室ゼミ資料を、本編17枚＋補足3枚で作成した。PDFを正式な発表・配布用成果物とし、編集用PPTXと共有ソースも保存した。本編55分＋質疑・補足5分の目安を発表者メモに付した。

## 正式成果物

| ファイル | 用途 |
|---|---|
| [seminar_spp_2d_2026-10-07.pdf](seminar_spp_2d_2026-10-07.pdf) | 完成PDF、20ページ |
| [PowerPoint v5](presentation/seminar_spp_2d_2026-10-07-v5.pptx) | 編集可能な本文・表、元PNG9図、話すメモ |
| [slide_source.json](slide_source.json) / [slides.md](slides.md) | 共通ソース／読みやすい本文 |
| [speaker_notes.md](speaker_notes.md) | スライドごとの話すメモ・留保・出典 |
| [figure_mapping.md](figure_mapping.md) | 本編6図・補足3図の対応 |
| [slide_plan.md](slide_plan.md) | 構成と時間配分 |
| build_slides.mjs / build_pdf.py | 再出力用ソース |
| assets/ | 原本とバイト一致したPDF/PNG9図ずつ |
| [README.md](README.md) | 開き方・編集・PDF再生成手順 |

## 自己点検

| 項目 | 結果・根拠 |
|---|---|
| 図の参照切れ | 無。図コピー18ファイルと本文の参照先を全確認。 |
| 図の内部埋め込み | PDF9ページで元PDFの描画命令列の保持を検証。PPTX9PNGは元ファイルとSHA-256一致。外部画像リンク0。 |
| 日本語の表示 | PDF全20ページを個別表示。欠字・文字化け・切れを修正後再確認。使用フォントはPDF内に埋め込み。 |
| レイアウト | 図は1枚のスライドを大きく使用。PPTX全ページプレビューを個別確認。最終構造/レイアウト検証は警告0。 |
| 数値・結論 | 有限Cと制限なしの2系統で参照資料と相互レビュー。幾何学式でN/M₀を検算。試行数は各有限C1,800、制限なし2,310。 |
| C=1 | Pを中心に概ね再現。S直前と擬臨界点ばらつきのずれを明記。固定削除数と要求時間を区別。 |
| C=2 | 同じ普遍クラスへ向かう可能性と整合的まで。普遍性の証明としない。 |
| 制限なし | 有限サイズで急激、候補内で0極限が比較上有利。正の極限を排除できず、次数未確定。 |
| 解析定義 | 最大イベント前後と固定p、SEMと95%区間、ΔtとΔt/N²、再標本分布と母数の確率を区別。 |
| 文字量・時間 | 本文は2〜3項目中心。計算規模は13行表でまとめた。20枚中9枚が既存図。55分＋質疑5分の説明メモ。時間は配分案で、実測リハーサルではない。 |
| 原本保全 | 保護一覧の研究原本3,040ファイル、既存ゼミ関連47ファイルのSHA-256がすべて一致。元図・raw data・事前登録・コード・研究文書は変更なし。 |
| Git | worktree clean、diff --check問題なし。HEADは12fade220d65db716511527b0789b49fb52fc317のまま。出力先はGit ignore対象。commit/pushなし。 |

## 作成の範囲

新規解析・fit・bootstrap・simulationを実行していない。既存9図の曲線・点・誤差棒・観測範囲・注記を改変していない。NとM₀の整数表は、依頼で指定された幾何学の恒等式から作成した。Java182件・Python180件は最終監査の保存結果として紹介し、今回の再実行結果とはしていない。

形式は、PPTX（Artifact Tool、編集可能な本文と表）とPDF（ReportLabで本文を描画し、pypdfで元PDF図を保持）。本文・表・図指定・話すメモの共通ソースはJSON。図は独立した元資料をそのまま使い、余白に独立した要点テキストとページ番号を付した。

PowerPointアプリ実機での描画は未確認。配布用PDFは全ページ確認済み。検証の詳細は [verification.json](verification.json)、[visual_verification.json](visual_verification.json)、[repository_verification.json](repository_verification.json) を参照。
