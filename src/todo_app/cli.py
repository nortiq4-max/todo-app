"""コマンドラインの入り口（ここを実装する）。

使い方は CHALLENGE.md の「コマンドの仕様」を見てください。
"""

import os
import sys

from todo_app import core

DEFAULT_FILE = "tasks.json"


def main(argv=None, path=None):
    """コマンドを実行して、終了コード（0: 成功、1: 見つからない、2: 使い方の誤り）を返す。"""
    if argv is None:
        argv = sys.argv[1:]
    if path is None:
        path = os.environ.get("TODO_FILE", DEFAULT_FILE)
    raise NotImplementedError("main を実装してください")
