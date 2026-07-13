# spp-2d-lattice

## 卒業研究タイトル（仮）
二次元正方格子における Shortest-Path Percolation の有限サイズ解析

## 研究目的
二次元正方格子上の Shortest-Path Percolation (SPP) を対象に、臨界現象と臨界指数の振る舞いを調べる。有限サイズスケーリングを用いて、系サイズ依存性を整理し、解析結果を比較しやすい形でまとめる。

## 使用予定技術
- Java
- Gradle
- VS Code
- Python
- 二次元正方格子モデル
- Shortest-Path Percolation (SPP)
- Finite Size Scaling
- 臨界指数解析

## ディレクトリ構成
```
spp-2d-lattice/
├── README.md
├── .gitignore
├── src/
│   ├── main/
│   │   └── java/
│   └── test/
│       └── java/
├── python/
├── data/
├── docs/
└── results/
```

## 今後の予定
1. Gradle プロジェクトの基本構成を作成する。
2. SPP のシミュレーション実装を Java で整備する。
3. Python で結果の集計・可視化・有限サイズスケーリング解析を行う。
4. 実験条件、再現手順、結果を段階的に記録する。