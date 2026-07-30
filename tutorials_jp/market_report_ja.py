#!/usr/bin/env python3
# coding: utf-8
"""日本語マーケットレポート生成デモ.

使い方:
    python tutorials_jp/market_report_ja.py 7203.T          # トヨタ(日本株)
    python tutorials_jp/market_report_ja.py BTC-USD crypto  # ビットコイン

LLMは環境変数で選択(既定はローカルOllama):
    FINROBOT_JP_LLM=ollama|deepseek|openai
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finrobot_jp import JapaneseMarketAnalyst


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "7203.T"
    market = sys.argv[2] if len(sys.argv) > 2 else "stock"
    print(JapaneseMarketAnalyst().report(symbol, market=market))


if __name__ == "__main__":
    main()
