"""公開テスト（10本）。応募時は、これとは別の追加テストでも確認します。"""

import pytest

from todo_app import core
from todo_app.cli import main


def test_add_task_returns_task_with_id_1():
    tasks = []
    task = core.add_task(tasks, "牛乳を買う")
    assert task == {"id": 1, "title": "牛乳を買う", "done": False}
    assert tasks == [task]


def test_add_task_increments_id():
    tasks = []
    core.add_task(tasks, "A")
    second = core.add_task(tasks, "B")
    assert second["id"] == 2


def test_add_task_strips_title():
    tasks = []
    task = core.add_task(tasks, "  本を返す  ")
    assert task["title"] == "本を返す"


def test_add_task_empty_title_raises():
    with pytest.raises(ValueError):
        core.add_task([], "   ")


def test_complete_task_marks_done():
    tasks = []
    core.add_task(tasks, "掃除")
    task = core.complete_task(tasks, 1)
    assert task["done"] is True
    assert tasks[0]["done"] is True


def test_complete_task_unknown_id_raises():
    with pytest.raises(KeyError):
        core.complete_task([], 99)


def test_remaining_excludes_done():
    tasks = []
    core.add_task(tasks, "A")
    core.add_task(tasks, "B")
    core.complete_task(tasks, 1)
    assert [t["id"] for t in core.remaining(tasks)] == [2]


def test_summary_counts():
    tasks = []
    core.add_task(tasks, "A")
    core.add_task(tasks, "B")
    core.add_task(tasks, "C")
    core.complete_task(tasks, 2)
    assert core.summary(tasks) == "全3件中1件完了"


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "tasks.json"
    tasks = []
    core.add_task(tasks, "牛乳を買う")
    core.save_tasks(tasks, path)
    assert core.load_tasks(path) == tasks


def test_cli_add_and_list(tmp_path, capsys):
    path = tmp_path / "tasks.json"
    assert main(["add", "牛乳を買う"], path=path) == 0
    assert main(["list"], path=path) == 0
    out = capsys.readouterr().out
    assert "[ ] 1 牛乳を買う" in out
