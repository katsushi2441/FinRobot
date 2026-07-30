# FinRobot 日本語ファースト派生版 (Japanese-first derivative)

> このリポジトリは [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)
> （Apache License 2.0）の**派生fork**です。AI4Finance Foundationの公式製品ではありません。
> "FinRobot" は AI4Finance Foundation の商標です。本forkは同財団の
> TRADEMARK_POLICY.md に従い、独自の製品名を名乗らず「FinRobotの日本語派生」としてのみ配布します。

FinRobotのマルチエージェント金融分析を、日本語・日本の利用環境で使いやすくするための追加層
`finrobot_jp/` を提供します。上流のコードは変更せず、追加のみで構成しています。

## 追加機能

### 1. 日本語アナリストレポート (`finrobot_jp.analyst`)

yfinanceのデータから日本語のマーケットレポート(Markdown)を生成します。
日本株(`7203.T`)・米国株・暗号資産(`BTC-USD`)・FX(`USDJPY=X`)に対応。

```bash
python tutorials_jp/market_report_ja.py 7203.T
```

ペルソナは「自然な日本語で書く・機械向け識別子(ティッカー、RSI等)は翻訳しない・
データにない事実を作らない・投資助言をしない」に固定しています。

### 2. ローカル/低コストLLM対応 (`finrobot_jp.llm_ja`)

環境変数だけでLLMを切り替えられます。フロンティアモデル不要の設計です。

| provider | 用途 | 主な環境変数 |
|---|---|---|
| `deepseek` (既定) | 低コストAPI。x402課金レールと同じ系列 | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| `ollama` | セルフホスト・ローカルLLM | `OLLAMA_URL`, `OLLAMA_MODEL` |
| `openai` | OpenAI互換全般 | `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` |

思考型のローカルモデル向けに `think:false` を明示するなど、運用の落とし穴に対処済み。

### 3. Kurage判断API接続 (`finrobot_jp.kbrain`)

Kurageシリーズの判断API（[kcbrain](https://kcbrain.exbridge.jp/)=暗号資産 /
[kfxbrain](https://kfxbrain.exbridge.jp/)=FX / [ksbrain](https://ksbrain.exbridge.jp/)=日本株）を
レポートの所見ソースとして組み込めます。未設定でもレポート生成は動作します(fail-open)。

## セットアップ (日本語層のみ)

```bash
python3 -m venv .venv-jp
.venv-jp/bin/pip install yfinance pandas requests
export DEEPSEEK_API_KEY=sk-...   # 既定プロバイダ(deepseek)を使う場合
.venv-jp/bin/python tutorials_jp/market_report_ja.py 7203.T
```

上流のマルチエージェント機能(AutoGen)を使う場合は、上流READMEの手順に従って
`requirements.txt` をインストールしてください。`OAI_CONFIG_LIST` に `base_url` を
書けばDeepSeekやOllamaのOpenAI互換エンドポイントでも動きます。

## ライセンス・商標

- コード: Apache License 2.0（上流に同じ）。追加分も同ライセンスです
- "FinRobot"・"AI4Finance" は AI4Finance Foundation の商標です（`TRADEMARK_POLICY.md` 参照）
- 本forkを組み込んだ製品は「built on FinRobot (Apache 2.0)」形式で表記してください

## 免責

本ソフトウェアは情報提供のみを目的とし、投資助言ではありません。投資は自己責任で行ってください。
