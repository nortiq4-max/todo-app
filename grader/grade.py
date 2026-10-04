#!/usr/bin/env python3
"""GH-900 チャレンジ #1 の自動採点スクリプト。

受講者の使い方（自分のリポジトリで）:
    pip install -r requirements-dev.txt
    python grader/grade.py

運営の使い方（応募時の再採点）:
    python grade.py --repo <応募リポジトリのパス> \
        --tests <公開テストのフォルダ> <追加テストのフォルダ> --json result.json

合格ライン: 100点満点で 90 点を「超える」こと（90.0 点ちょうどは不合格）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

PASS_THRESHOLD = 90.0
PLACEHOLDER_MARK = "TODO: このREADMEを書き換えてください"
PROVIDED_WORKFLOWS = {"autograde.yml", "autograde.yaml"}

CATEGORY_MAX = {
    "A": ("A. Python実装（テスト）", 40),
    "B": ("B. リポジトリの整備", 30),
    "C": ("C. Gitの使い方（履歴）", 15),
    "D": ("D. CI（自動テスト）", 10),
    "E": ("E. 秘密情報が入っていない", 5),
}

# 秘密情報のパターン。採点スクリプト自身に引っかからないよう、一部を分けて組み立てる。
SECRET_PATTERNS = [
    ("AWSのアクセスキー", re.compile(r"AKIA" + r"[0-9A-Z]{16}")),
    ("GitHubのトークン", re.compile(r"\bgh[pousr]" + r"_[A-Za-z0-9]{36,}")),
    ("APIキー（sk-で始まるもの）", re.compile(r"\bsk" + r"-[A-Za-z0-9][A-Za-z0-9_\-]{30,}")),
    ("Slackのトークン", re.compile(r"\bxox[baprs]" + r"-[A-Za-z0-9-]{10,}")),
    ("秘密鍵", re.compile("-----BEGIN " + r"(RSA |EC |OPENSSH |DSA )?" + "PRIVATE KEY-----")),
]


@dataclass
class Check:
    category: str
    name: str
    points: float
    max_points: float
    message: str


# ---------------------------------------------------------------- 共通の小道具


def find_file(repo: Path, candidates: list[str]) -> Path | None:
    """候補のパスを、大文字・小文字を区別せずに探す。"""
    for rel in candidates:
        rel_path = Path(rel)
        parent = repo / rel_path.parent
        if not parent.is_dir():
            continue
        target = rel_path.name.lower()
        for child in parent.iterdir():
            if child.is_file() and child.name.lower() == target:
                return child
    return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_yaml(path: Path):
    if yaml is None:
        raise RuntimeError("PyYAML が入っていません（pip install pyyaml）")
    return yaml.safe_load(read_text(path))


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    return proc.stdout if proc.returncode == 0 else ""


def is_git_repo(repo: Path) -> bool:
    return git(repo, "rev-parse", "--is-inside-work-tree").strip() == "true"


# ---------------------------------------------------------------- A. テスト


def run_tests(repo: Path, test_paths: list[Path] | None) -> tuple[int, int, str]:
    """pytest を実行して（合格数, 総数, 出力の末尾）を返す。

    test_paths を渡したとき（運営の再採点）は、受講者の src だけを一時フォルダに写し、
    受講者側の conftest や設定ファイルが採点に影響しないようにする。
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        empty_ini = tmp_dir / "pytest.ini"
        empty_ini.write_text("[pytest]\n", encoding="utf-8")
        report = tmp_dir / "report.xml"

        if test_paths:
            workspace = tmp_dir / "workspace"
            workspace.mkdir()
            if (repo / "src").is_dir():
                shutil.copytree(repo / "src", workspace / "src")
            targets = []
            for i, path in enumerate(test_paths):
                dest = workspace / f"tests_{i}"
                if path.is_dir():
                    shutil.copytree(path, dest)
                else:
                    dest.mkdir()
                    shutil.copy(path, dest / path.name)
                targets.append(str(dest))
            rootdir, src_dir = workspace, workspace / "src"
        else:
            targets = [str(repo / "tests")]
            rootdir, src_dir = repo, repo / "src"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        cmd = [
            sys.executable, "-m", "pytest", "-q", "--no-header",
            "-p", "no:cacheprovider",
            "-c", str(empty_ini),
            "--rootdir", str(rootdir),
            f"--junitxml={report}",
            *targets,
        ]
        try:
            proc = subprocess.run(
                cmd, cwd=rootdir, env=env, capture_output=True, text=True, timeout=300
            )
            output = (proc.stdout or "") + (proc.stderr or "")
        except subprocess.TimeoutExpired:
            return 0, 0, "テストが5分以内に終わりませんでした（無限ループがないか確認してください）"

        if not report.exists():
            return 0, 0, output[-3000:]
        root = ET.parse(report).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        total = sum(int(s.get("tests", 0)) for s in suites)
        failed = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
        skipped = sum(int(s.get("skipped", 0)) for s in suites)
        passed = max(total - failed - skipped, 0)
        return passed, total, output[-3000:]


def check_tests(repo: Path, test_paths: list[Path] | None) -> list[Check]:
    passed, total, output = run_tests(repo, test_paths)
    max_points = CATEGORY_MAX["A"][1]
    if total == 0:
        return [Check("A", "テスト", 0, max_points,
                      "テストを実行できませんでした。src/todo_app の中身と tests/ を確認してください。\n" + output[-800:])]
    points = round(max_points * passed / total, 1)
    message = f"{passed}/{total} 本のテストに合格"
    if passed < total:
        message += "。失敗したテストは `python -m pytest -q` で確認できます"
    return [Check("A", "テスト", points, max_points, message)]


# ---------------------------------------------------------------- B. リポジトリの整備


def check_readme(repo: Path) -> Check:
    path = find_file(repo, ["README.md"])
    if not path:
        return Check("B", "README.md", 0, 5, "README.md がありません")
    text = read_text(path)
    if PLACEHOLDER_MARK in text:
        return Check("B", "README.md", 0, 5, "README.md がテンプレートのままです。CHALLENGE.md の Day1 を見て書き換えてください")
    headings = "\n".join(re.findall(r"^#{1,6}\s*(.+)$", text, flags=re.M)).lower()
    points, missing = 0, []
    if len(text.strip()) >= 200:
        points += 1
    else:
        missing.append("200文字以上の説明")
    if any(k in headings for k in ("概要", "できること", "about", "overview")):
        points += 1
    else:
        missing.append("「概要」の見出し")
    if any(k in headings for k in ("使い方", "usage")):
        points += 2
    else:
        missing.append("「使い方」の見出し")
    if any(k in headings for k in ("テスト", "test")):
        points += 1
    else:
        missing.append("「テストの実行方法」の見出し")
    message = "OK" if not missing else "足りないもの：" + "、".join(missing)
    return Check("B", "README.md", points, 5, message)


def check_simple_file(repo: Path, name: str, candidates: list[str], max_points: float,
                      min_chars: int = 30) -> Check:
    path = find_file(repo, candidates)
    if not path:
        return Check("B", name, 0, max_points, f"{name} がありません")
    if len(read_text(path).strip()) < min_chars:
        return Check("B", name, max_points / 2, max_points, f"{name} の中身が短すぎます")
    return Check("B", name, max_points, max_points, "OK")


def check_gitignore(repo: Path) -> Check:
    path = repo / ".gitignore"
    if not path.is_file():
        return Check("B", ".gitignore", 0, 3, ".gitignore がありません")
    text = read_text(path)
    points, missing = 1, []
    if "__pycache__" in text:
        points += 1
    else:
        missing.append("__pycache__/")
    if ".venv" in text or re.search(r"(^|/)venv", text, flags=re.M):
        points += 1
    else:
        missing.append(".venv/")
    message = "OK" if not missing else "追加したい行：" + "、".join(missing)
    return Check("B", ".gitignore", points, 3, message)


def check_pr_template(repo: Path) -> Check:
    path = find_file(repo, [
        "pull_request_template.md", ".github/pull_request_template.md", "docs/pull_request_template.md",
    ])
    folder = repo / ".github" / "PULL_REQUEST_TEMPLATE"
    if not path and folder.is_dir() and any(p.suffix.lower() == ".md" for p in folder.iterdir()):
        path = folder
    if not path:
        return Check("B", "プルリクエストのテンプレート", 0, 4,
                     ".github/PULL_REQUEST_TEMPLATE.md を作ってください")
    return Check("B", "プルリクエストのテンプレート", 4, 4, "OK")


def check_issue_templates(repo: Path) -> Check:
    folder = repo / ".github" / "ISSUE_TEMPLATE"
    if not folder.is_dir():
        return Check("B", "Issueのテンプレート", 0, 4, ".github/ISSUE_TEMPLATE/ にテンプレートを2つ作ってください")
    templates = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in (".md", ".yml", ".yaml") and p.stem.lower() != "config"
    ]
    if len(templates) >= 2:
        return Check("B", "Issueのテンプレート", 4, 4, f"OK（{len(templates)}個）")
    if len(templates) == 1:
        return Check("B", "Issueのテンプレート", 2, 4, "テンプレートが1つだけです。もう1つ作ってください（例：バグ報告と機能要望）")
    return Check("B", "Issueのテンプレート", 0, 4, ".github/ISSUE_TEMPLATE/ が空です")


def check_codeowners(repo: Path) -> Check:
    path = find_file(repo, ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"])
    if not path:
        return Check("B", "CODEOWNERS", 0, 2, ".github/CODEOWNERS がありません")
    rules = [
        line for line in read_text(path).splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "@" in line
    ]
    if not rules:
        return Check("B", "CODEOWNERS", 1, 2, "担当者（@ユーザー名）を書いた行がありません")
    return Check("B", "CODEOWNERS", 2, 2, "OK")


def check_dependabot(repo: Path) -> Check:
    path = find_file(repo, [".github/dependabot.yml", ".github/dependabot.yaml"])
    if not path:
        return Check("B", "dependabot.yml", 0, 3, ".github/dependabot.yml がありません")
    try:
        data = load_yaml(path) or {}
    except Exception as exc:  # YAML の書き間違い
        return Check("B", "dependabot.yml", 0, 3, f"YAMLとして読めません：{exc}")
    updates = data.get("updates") if isinstance(data, dict) else None
    if data.get("version") != 2 or not isinstance(updates, list) or not updates:
        return Check("B", "dependabot.yml", 1, 3, "version: 2 と updates の一覧を書いてください")
    for item in updates:
        schedule = item.get("schedule") if isinstance(item, dict) else None
        if not (isinstance(item, dict) and item.get("package-ecosystem") and item.get("directory")
                and isinstance(schedule, dict) and schedule.get("interval")):
            return Check("B", "dependabot.yml", 1, 3,
                         "各 updates に package-ecosystem、directory、schedule.interval を書いてください")
    return Check("B", "dependabot.yml", 3, 3, "OK")


def check_repository(repo: Path) -> list[Check]:
    return [
        check_readme(repo),
        check_simple_file(repo, "LICENSE", ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"], 2, min_chars=100),
        check_gitignore(repo),
        check_simple_file(repo, "CONTRIBUTING.md",
                          ["CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"], 2),
        check_simple_file(repo, "CODE_OF_CONDUCT.md",
                          ["CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md", "docs/CODE_OF_CONDUCT.md"], 2),
        check_simple_file(repo, "SECURITY.md",
                          ["SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"], 3),
        check_pr_template(repo),
        check_issue_templates(repo),
        check_codeowners(repo),
        check_dependabot(repo),
    ]


# ---------------------------------------------------------------- C. Gitの使い方


def check_history(repo: Path) -> list[Check]:
    if not is_git_repo(repo):
        return [Check("C", "Gitの履歴", 0, 15, "Gitのリポジトリではないため、履歴を確認できません")]
    shallow = git(repo, "rev-parse", "--is-shallow-repository").strip() == "true"
    count_text = git(repo, "rev-list", "--count", "HEAD").strip()
    count = int(count_text) if count_text.isdigit() else 0
    subjects = git(repo, "log", "--pretty=%s").splitlines()
    bodies = git(repo, "log", "--pretty=%B%x00").split("\x00")

    checks = []
    note = "（履歴が途中までしか取得されていません。fetch-depth: 0 にしてください）" if shallow else ""
    if count >= 8:
        checks.append(Check("C", "コミットの数", 4, 4, f"OK（{count}件）"))
    elif count >= 4:
        checks.append(Check("C", "コミットの数", 2, 4, f"{count}件です。小さく分けて8件以上にしましょう{note}"))
    else:
        checks.append(Check("C", "コミットの数", 0, 4, f"{count}件です。8件以上が目安です{note}"))

    merged = any(
        re.match(r"Merge pull request #\d+", s) or re.search(r"\(#\d+\)\s*$", s) for s in subjects
    )
    checks.append(Check(
        "C", "プルリクエストのマージ", 6 if merged else 0, 6,
        "OK" if merged else "プルリクエストを作ってマージした履歴がありません（CHALLENGE.md の Day3）",
    ))

    closing = re.compile(r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?)\s+#\d+", flags=re.I)
    linked = any(closing.search(body) for body in bodies)
    checks.append(Check(
        "C", "Issueとのひも付け", 5 if linked else 0, 5,
        "OK" if linked else "コミットメッセージに「Closes #1」のようにIssue番号を書いてください",
    ))
    return checks


# ---------------------------------------------------------------- D. CI


def workflow_triggers(data: dict):
    # PyYAML は on: を True として読むことがあるので両方を見る
    return data.get("on", data.get(True)) if isinstance(data, dict) else None


def has_event(triggers, events: set[str]) -> bool:
    if isinstance(triggers, str):
        return triggers in events
    if isinstance(triggers, list):
        return any(t in events for t in triggers)
    if isinstance(triggers, dict):
        return any(k in events for k in triggers)
    return False


def runs_pytest(data: dict) -> bool:
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, dict):
        return False
    for job in jobs.values():
        for step in (job or {}).get("steps", []) or []:
            if isinstance(step, dict) and "pytest" in str(step.get("run", "")):
                return True
    return False


def check_ci(repo: Path) -> list[Check]:
    folder = repo / ".github" / "workflows"
    files = [] if not folder.is_dir() else [
        p for p in sorted(folder.iterdir())
        if p.suffix.lower() in (".yml", ".yaml") and p.name.lower() not in PROVIDED_WORKFLOWS
    ]
    if not files:
        return [Check("D", "CIのワークフロー", 0, 10,
                      ".github/workflows/ci.yml を作ってください（autograde.yml は数に入りません）")]
    best, best_message = 0, ""
    for path in files:
        try:
            data = load_yaml(path) or {}
        except Exception as exc:
            best_message = best_message or f"{path.name} をYAMLとして読めません：{exc}"
            continue
        trig_ok = has_event(workflow_triggers(data), {"push", "pull_request"})
        test_ok = runs_pytest(data)
        score = (5 if trig_ok else 0) + (5 if test_ok else 0)
        if score > best:
            best = score
            missing = []
            if not trig_ok:
                missing.append("push か pull_request で動くこと")
            if not test_ok:
                missing.append("pytest を実行するステップ")
            best_message = f"{path.name}：OK" if not missing else f"{path.name}：足りないもの：" + "、".join(missing)
    if not best_message:
        best_message = "push か pull_request で動き、pytest を実行するワークフローがありません"
    return [Check("D", "CIのワークフロー", best, 10, best_message)]


# ---------------------------------------------------------------- E. 秘密情報


def files_to_scan(repo: Path) -> list[Path]:
    if is_git_repo(repo):
        listed = [repo / line for line in git(repo, "ls-files").splitlines() if line]
    else:
        listed = [p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [
        p for p in listed
        if p.is_file() and "grader" not in p.relative_to(repo).parts and p.stat().st_size < 1_000_000
    ]


def check_secrets(repo: Path) -> list[Check]:
    found = []
    for path in files_to_scan(repo):
        text = read_text(path)
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                found.append(f"{path.relative_to(repo)}（{label}）")
    if found:
        return [Check("E", "秘密情報", 0, 5,
                      "秘密情報らしき文字列があります。すぐ削除し、キーは無効化して作り直してください：" + "、".join(found[:5]))]
    return [Check("E", "秘密情報", 5, 5, "OK")]


# ---------------------------------------------------------------- まとめ


def grade(repo: Path, test_paths: list[Path] | None) -> dict:
    checks = (
        check_tests(repo, test_paths)
        + check_repository(repo)
        + check_history(repo)
        + check_ci(repo)
        + check_secrets(repo)
    )
    categories = {}
    for key, (label, max_points) in CATEGORY_MAX.items():
        points = round(sum(c.points for c in checks if c.category == key), 1)
        categories[key] = {"label": label, "points": points, "max_points": max_points}
    total = round(sum(c["points"] for c in categories.values()), 1)
    secrets_ok = all(c.points == c.max_points for c in checks if c.category == "E")
    return {
        "total": total,
        "threshold": PASS_THRESHOLD,
        "secrets_ok": secrets_ok,
        "passed": total > PASS_THRESHOLD and secrets_ok,
        "categories": categories,
        "checks": [asdict(c) for c in checks],
    }


def to_markdown(result: dict) -> str:
    if result["passed"]:
        status = "合格ライン超え"
    elif not result.get("secrets_ok", True):
        status = "秘密情報が見つかったため、点数にかかわらず合格ラインに届かない扱いです"
    else:
        status = "まだ合格ラインに届いていません"
    lines = [
        "# GH-900 チャレンジ #1 自動採点",
        "",
        f"**{result['total']} / 100 点**（{status}。合格ラインは {result['threshold']:.0f} 点を超えること）",
        "",
        "| 区分 | 点数 |",
        "| --- | --- |",
    ]
    for cat in result["categories"].values():
        lines.append(f"| {cat['label']} | {cat['points']} / {cat['max_points']} |")
    todo = [c for c in result["checks"] if c["points"] < c["max_points"]]
    lines += ["", "## 直すところ" if todo else "## すべての項目を満たしています", ""]
    for c in todo:
        lines.append(f"- [{c['category']}] {c['name']}（{c['points']}/{c['max_points']}）：{c['message']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GH-900 チャレンジ #1 の自動採点")
    parser.add_argument("--repo", default=".", help="採点するリポジトリのパス")
    parser.add_argument("--tests", nargs="*", help="運営用：使うテストのフォルダ（受講者のテストの代わりに使う）")
    parser.add_argument("--summary", help="Markdownの結果を書き出すファイル（GitHub Actions のジョブサマリー用）")
    parser.add_argument("--json", help="結果をJSONで書き出すファイル")
    parser.add_argument("--no-fail", action="store_true", help="合格ラインに届かなくても終了コード0で終える")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    test_paths = [Path(p).resolve() for p in args.tests] if args.tests else None
    result = grade(repo, test_paths)
    markdown = to_markdown(result)
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write(markdown)
    try:
        print(markdown)
    except BrokenPipeError:  # head などで出力を途中で切られた場合
        pass
    if result["passed"] or args.no_fail:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
