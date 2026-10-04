"""タスク管理の中身（ここを実装する）。

仕様は CHALLENGE.md の「作るもの」を見てください。
タスクは次の形の辞書で表します。

    {"id": 1, "title": "牛乳を買う", "done": False}
"""

import json
from pathlib import Path


def add_task(tasks, title):
    """タスクを追加して、追加したタスクを返す。

    - title の前後の空白は取り除く
    - 空白を取り除いて空になる title は ValueError
    - id は「今ある最大の id + 1」（最初は 1）
    """
    raise NotImplementedError("add_task を実装してください")


def complete_task(tasks, task_id):
    """指定した id のタスクを完了にして、そのタスクを返す。

    - 見つからない id は KeyError
    """
    raise NotImplementedError("complete_task を実装してください")


def remaining(tasks):
    """未完了のタスクだけを、id の小さい順に並べて返す。"""
    raise NotImplementedError("remaining を実装してください")


def summary(tasks):
    """「全3件中1件完了」の形の文字列を返す。タスクがなければ「タスクはありません」。"""
    raise NotImplementedError("summary を実装してください")


def save_tasks(tasks, path):
    """タスクを JSON で保存する（UTF-8、日本語はそのまま書く）。"""
    raise NotImplementedError("save_tasks を実装してください")


def load_tasks(path):
    """JSON からタスクを読み込む。ファイルがなければ空のリストを返す。"""
    raise NotImplementedError("load_tasks を実装してください")
