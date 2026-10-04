# GH-900 チャレンジ #1：タスク管理ツールを作って公開する

Pythonで小さなタスク管理ツールを作り、GitHubで公開するまでを7日間で体験する課題です。
GitHub Foundations（GH-900）の出題範囲（7分野）に沿って、実際に手を動かしながら学べるようにしています。

- 自動採点で **90点を超える** と合格ラインです（90.0点ちょうどは届かない扱い）
- 1日の目安は30〜60分です
- 本課題はMicrosoft・GitHubの公式教材ではありません。資格の合格を保証するものでもありません

---

## 始め方

1. このリポジトリの「Use this template」→「Create a new repository」で、自分のリポジトリを作る
2. 手元のPCで進める場合：`git clone` して、`pip install -r requirements-dev.txt`
3. ブラウザだけで進める場合：リポジトリの「Code」→「Codespaces」で開く（無料の利用枠があります）
4. 自分のPCで採点するには `python grader/grade.py`、GitHubでは push するたびに「Actions」タブで採点されます

---

## 作るもの

`src/todo_app/core.py` と `src/todo_app/cli.py` を完成させます。タスクは次の形の辞書で表します。

```python
{"id": 1, "title": "牛乳を買う", "done": False}
```

### 関数の仕様（core.py）

| 関数 | 動き |
| --- | --- |
| `add_task(tasks, title)` | 前後の空白を除いた title でタスクを追加し、追加したタスクを返す。空なら `ValueError`。id は「今ある最大の id + 1」（最初は 1） |
| `complete_task(tasks, task_id)` | 指定した id を完了にして、そのタスクを返す。見つからなければ `KeyError` |
| `remaining(tasks)` | 未完了のタスクを id の小さい順に返す |
| `summary(tasks)` | 「全3件中1件完了」の形で返す。タスクがなければ「タスクはありません」 |
| `save_tasks(tasks, path)` | JSONで保存する（UTF-8、日本語はそのまま書く） |
| `load_tasks(path)` | JSONから読み込む。ファイルがなければ空のリスト |

### コマンドの仕様（cli.py）

`main(argv, path)` は終了コード（0：成功、1：見つからない、2：使い方の誤り）を返します。
データの保存先は `path`、なければ環境変数 `TODO_FILE`、それもなければ `tasks.json` です。

| コマンド | 表示 |
| --- | --- |
| `python -m todo_app add 牛乳を買う` | `追加しました: 1 牛乳を買う` |
| `python -m todo_app list` | 1件ずつ `[ ] 1 牛乳を買う`（完了は `[x]`）。0件なら `タスクはありません` |
| `python -m todo_app done 1` | `完了にしました: 1 牛乳を買う`。ない番号なら標準エラーに `見つかりません: 9` を出して 1 を返す |
| `python -m todo_app summary` | `summary()` の結果 |
| それ以外 | 標準エラーに使い方を出して 2 を返す |

`src` を使うので、手元で動かすときは `PYTHONPATH=src python -m todo_app list` のように実行します。

---

## 7日間の進め方

| 日 | やること | GH-900の分野 |
| --- | --- | --- |
| Day1 | README.md を書き換える（見出し「概要」「使い方」「テストの実行方法」）。`.github/ISSUE_TEMPLATE/` にバグ報告と機能要望のテンプレートを作り、Issueを3つ立てる（#1 add_task、#2 complete_task ほか、#3 保存とコマンド） | GitとGitHubの基本、リポジトリの扱い |
| Day2 | `git switch -c feature/add-task` でブランチを切り、`add_task` を実装。`python -m pytest -q` で確かめ、メッセージに `Closes #1` を入れてコミット | GitとGitHubの基本 |
| Day3 | push してプルリクエストを作り、説明欄に「やったこと」「確かめたこと」を書く。自分でレビューしてから「Create a merge commit」でマージ | 共同作業の機能 |
| Day4 | 残りの関数とコマンドを、同じ流れ（ブランチ → プルリクエスト → マージ）で作る。`Closes #2`、`Closes #3` を忘れずに | 共同作業の機能、プロジェクト管理 |
| Day5 | `LICENSE`、`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`、`.gitignore`（`__pycache__/` と `.venv/`）を追加 | GitHubコミュニティ、セキュリティ |
| Day6 | `.github/workflows/ci.yml`（push と pull_request で pytest を実行）、`.github/dependabot.yml`、`.github/PULL_REQUEST_TEMPLATE.md`、`.github/CODEOWNERS` を追加 | モダンな開発、セキュリティ、共同作業 |
| Day7 | 採点結果の「直すところ」をつぶして90点超えを目指す。`quiz/answers.yaml` を埋めて `python grader/quiz.py` で理解度チェック。余裕があれば第2セット（場面で考える30問）`--set 2` と第3セット（仕上げの30問）`--set 3`、最後に90問の模擬テスト `--set all` | 全分野の復習 |

### Day6 のヒント

`ci.yml` の骨組み（空欄を埋めてください）：

```yaml
name: ci
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements-dev.txt
      - run: # ここで pytest を実行する
```

`dependabot.yml` の例：

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

`CODEOWNERS` の例（自分のユーザー名に変える）：

```text
* @your-github-name
```

---

## 採点の内訳（100点）

| 区分 | 配点 | 見ているもの |
| --- | --- | --- |
| A. Python実装 | 40 | テストの合格率（応募時は非公開の追加テストも使う） |
| B. リポジトリの整備 | 30 | README（5）、LICENSE（2）、.gitignore（3）、CONTRIBUTING（2）、CODE_OF_CONDUCT（2）、SECURITY（3）、PRテンプレート（4）、Issueテンプレート2つ（4）、CODEOWNERS（2）、dependabot.yml（3） |
| C. Gitの使い方 | 15 | コミット8件以上（4）、プルリクエストのマージ（6）、`Closes #番号` でのIssueのひも付け（5） |
| D. CI | 10 | push か pull_request で動く（5）、pytest を実行する（5） |
| E. 秘密情報 | 5 | APIキーやトークン、秘密鍵などが入っていない。見つかった場合は、点数にかかわらず合格ラインに届かない扱い |

---

## ルール

- AI（GitHub Copilot など）を使ってかまいません。使ったツールは README に書いてください。進め方は `docs/VIBE_CODING.md` を見てください
- 他人のコードを丸写ししない。参考にしたものは README に書く
- パスワードやAPIキーをコミットしない。誤ってコミットしたら、すぐにキーを無効化して作り直す
- 資格試験の実際の問題を書いたり、共有したりしない
- 応募時は、運営が同じ基準と非公開の追加テストで採点し直します。`grader/` やテストを書き換えても、応募時の点数は変わりません
