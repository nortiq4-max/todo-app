# タスク管理ツール（todo-app）

## 概要

コマンドで使える、小さなタスク管理ツールです。タスクの追加、完了、一覧、件数のまとめができます。データはJSONファイル（tasks.json）に保存します。

## 使い方

`PYTHONPATH=src python -m todo_app add 牛乳を買う`

`PYTHONPATH=src python -m todo_app list`

`PYTHONPATH=src python -m todo_app done 1`

## テストの実行方法

`pip install -r requirements-dev.txt`

`python -m pytest -q`

## AIの利用

このREADMEの下書きに、生成AI（Claude）を使いました。