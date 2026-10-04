#!/usr/bin/env python3
"""理解度チェックの自己採点。結果は応募の点数には入りません。

    python grader/quiz.py            # 第1セット（基本の30問）
    python grader/quiz.py --set 2    # 第2セット（場面で考える30問）
    python grader/quiz.py --set 3    # 第3セット（仕上げの30問）
    python grader/quiz.py --set all  # 全部まとめて（90問の模擬テスト）
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import yaml

QUIZ = Path(__file__).resolve().parents[1] / "quiz"
SETS = {
    "1": ("questions.yaml", "answers.yaml", "key.yaml"),
    "2": ("questions_set2.yaml", "answers_set2.yaml", "key_set2.yaml"),
    "3": ("questions_set3.yaml", "answers_set3.yaml", "key_set3.yaml"),
}


def load(name: str):
    return yaml.safe_load((QUIZ / name).read_text(encoding="utf-8")) or {}


def load_answers(path: Path) -> dict:
    """答えのファイルを読む。全角の文字や「q01:b」のようなスペースなしの書き方も受け付ける。"""
    answers = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = unicodedata.normalize("NFKC", raw).strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z]+\d+)\s*:\s*([A-Za-z]?)", line)
        if match:
            answers[match.group(1).lower()] = match.group(2).lower()
    return answers


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="理解度チェックの自己採点")
    parser.add_argument("--set", default="1", choices=["1", "2", "3", "all"])
    args = parser.parse_args(argv)
    chosen = list(SETS) if args.set == "all" else [args.set]

    correct = unanswered = total = 0
    by_domain = defaultdict(lambda: [0, 0])
    print("# 理解度チェックの結果\n")
    for set_id in chosen:
        q_file, a_file, k_file = SETS[set_id]
        questions, answers, key = load(q_file), load_answers(QUIZ / a_file), load(k_file)
        for q in questions:
            qid, total = q["id"], total + 1
            given = str(answers.get(qid) or "").strip().lower()
            right = key[qid]["answer"]
            by_domain[q["domain"]][1] += 1
            if not given:
                unanswered += 1
                continue
            if given == right:
                correct += 1
                by_domain[q["domain"]][0] += 1
            else:
                print(f"- {qid} ×（あなた：{given} / 正解：{right}）{q['question']}")
                print(f"    解説：{key[qid]['explanation']}")

    rate = correct / total * 100 if total else 0
    print(f"\n**{correct} / {total} 問正解（{rate:.0f}%）**　未回答 {unanswered} 問\n")
    print("| 分野 | 正解 |")
    print("| --- | --- |")
    for domain, (ok, n) in by_domain.items():
        print(f"| {domain} | {ok} / {n} |")
    weakest = min(by_domain.items(), key=lambda kv: kv[1][0] / kv[1][1])[0] if by_domain else None
    if weakest and unanswered < total:
        print(f"\nいちばん伸ばしたい分野：{weakest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
