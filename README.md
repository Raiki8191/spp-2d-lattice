# Shortest-Path Percolation on a 2D Square Lattice

二次元正方格子上の Shortest-Path Percolation（SPP）を、Java 21 でシミュレーションし、Python で検証・可視化・有限サイズスケーリング（FSS）解析する独立した研究プロジェクトです。

各要求では異なる2頂点を一様に選び、現在の有効辺上の最短距離が予算 `C` 以下なら、全最短経路から一様に選んだ1本をまとめて削除します。シミュレーションは測定結果、run要約、条件manifest、および必要に応じて辺削除トレースをCSVへ出力します。Python側では入力検証、要求単位・辺単位の疑似臨界事象、転移幅、bootstrap、FSSを扱います。

詳細は次を参照してください。

- [設計と実装](docs/DESIGN.md)
- [解析量と疑似臨界点の定義](docs/ANALYSIS_DEFINITIONS.md)
- [scaling-v1 の条件・結果](docs/SCALING_V1_RESULTS.md)
- [scaling-v2 の条件・統合FSS・結果](docs/SCALING_V2_RESULTS.md)
- [scaling-v3 有限サイズ補正解析](docs/SCALING_V3_RESULTS.md)
- [UNBOUNDED v4: L=192段階実験と漸近モデル再評価](docs/UNBOUNDED_V4_RESULTS.md)
- [UNBOUNDED v5: L=256パイロットとモデル識別力再評価](docs/UNBOUNDED_V5_RESULTS.md)
- [UNBOUNDED L=320事前予測登録](docs/UNBOUNDED_L320_PREREGISTRATION.md)
- [UNBOUNDED v6: L=320パイロットと逐次予測評価](docs/UNBOUNDED_V6_RESULTS.md)

## 環境

- Java 21
- Gradle Wrapper
- Python 3
- NumPy / pandas / Matplotlib / pytest

Python依存関係は次で導入します。

```powershell
python -m pip install -r requirements.txt
```

## 主なディレクトリ

```text
app/src/main/java/spp/  Javaシミュレーションと実行エントリーポイント
app/src/test/java/spp/  Javaテスト
analysis/               Python解析コード
analysis/tests/         pytest
docs/                   設計、解析定義、研究記録
app/out/                実験・解析の生成物（Git管理対象外）
```

## テスト

リポジトリルートから実行します。

```powershell
.\gradlew.bat test
.\gradlew.bat build
python -m pytest analysis/tests
```

## 再現用の実行コマンド

小規模な smoke 走査:

```powershell
.\gradlew.bat run
python -m analysis.plot_smoke app/out/sweep-smoke/manifest.csv
```

pilot 走査と解析:

```powershell
.\gradlew.bat run --args="--pilot"
python -m analysis.plot_ensemble app/out/sweep-pilot/manifest.csv
```

scaling-v1 の軽量確認:

```powershell
.\gradlew.bat run --args="--scaling-v1-smoke"
```

scaling-v1 本計算とFSS解析:

```powershell
.\gradlew.bat run --args="--scaling-v1"
python -m analysis.plot_scaling app/out/scaling-v1/manifest.csv
```

scaling-v2前段のL=96/128・各5 run停止延長benchmark:

```powershell
.\gradlew.bat run --args="--scaling-v2-benchmark"
python -m analysis.scaling_v2_benchmark app/out/scaling-v2-benchmark/manifest.csv
```

scaling-v2 本計算、停止監査、scaling-v1との論理統合解析:

```powershell
.\gradlew.bat run --args="--scaling-v2-main"
.\gradlew.bat run --args="--scaling-v2-stop-audit"
python -m analysis.scaling_v2 stop-audit app/out/scaling-v2-main/manifest.csv app/out/scaling-v2-stop-audit/manifest.csv --output app/out/scaling-v2-stop-audit/analysis
python -m analysis.scaling_v2 analyze app/out/scaling-v1/manifest.csv app/out/scaling-v2-main/manifest.csv --output app/out/scaling-v2-analysis --bootstrap-samples 5000
```

確定済みscaling-v2集約値を用いる有限サイズ補正解析（新しいシミュレーションは実行しない）:

```powershell
python -m analysis.scaling_v3 --source app/out/scaling-v2-analysis --output app/out/scaling-v3-analysis --bootstrap-samples 500
```

UNBOUNDEDのL=192追加実験は、benchmark（3 run）、pilot（追加17 run）、main（追加30 run）の独立manifestに分け、run単位で安全に再開できます。既存のscaling-v2/v3データは再生成しません。

```powershell
.\gradlew.bat run --args="--unbounded-l192-benchmark"
.\gradlew.bat run --args="--unbounded-l192-pilot"
.\gradlew.bat run --args="--unbounded-l192-main"
.\gradlew.bat run --args="--unbounded-l192-stop-audit"
python -m analysis.unbounded_v4 --stage main --bootstrap-samples 500
```

UNBOUNDEDのL=256段階実験（benchmark 3 run、pilot追加17 run）とv5解析:

```powershell
.\gradlew.bat run --args="--unbounded-l256-benchmark"
.\gradlew.bat run --args="--unbounded-l256-pilot"
.\gradlew.bat run --args="--unbounded-l256-stop-audit"
python -m analysis.unbounded_v5 --bootstrap-samples 500 --output app/out/unbounded-v5
```

UNBOUNDEDのL=320段階実験（benchmark 3 run、pilot追加17 run）、独立停止監査、v6解析:

```powershell
.\gradlew.bat run --args="--unbounded-l320-benchmark"
.\gradlew.bat run --args="--unbounded-l320-pilot"
.\gradlew.bat run --args="--unbounded-l320-stop-audit"
python -m analysis.unbounded_v6 --bootstrap-samples 500 --output app/out/unbounded-v6
```

L=320の予測は実験前コミットで固定済みであり、再生成コマンドは既存のL=320出力を検出すると拒否します。L=320は合計20 runに固定し、50 run以上やL=384を上記コマンドから自動実行しません。

各stageはrun単位で再開でき、完了済みrunは`resume-skip`されます。今回の研究記録は合計20 runまでであり、50 run以上への増加は自動実行しません。

大容量のシャード、集約CSV、解析CSV、PNGはすべて`app/out/`以下に生成され、Git管理対象外です。L=256は上記の専用引数を明示した場合だけ実行され、通常のsmoke/scalingコマンドからは自動実行しません。

経路内辺順序の副解析用データは次で生成できます。

```powershell
.\gradlew.bat run --args="--scaling-v1-order-check"
python -m analysis.order_sensitivity app/out/scaling-v1-order-check/manifest.csv --output app/out/scaling-v1-order-check
```

本計算はCPU時間とディスク容量を消費します。既存結果を確認するだけなら再実行は不要です。`app/out/` 以下のCSV・PNGなどは再生成可能な成果物としてGit管理しません。

## プロジェクトの独立性

本リポジトリは先輩リポジトリとは独立したプロジェクトです。先行実装は責務分離などの設計上の参考に限り、ビルド依存関係や実行時依存関係を持ちません。
