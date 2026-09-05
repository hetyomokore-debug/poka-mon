# Cowork 委譲指示書 — Cursor マーケットプレイス登録の下調べ

> English summary: an operating order for a computer-use agent (Cowork) that has been granted control of the author's machine. It gathers the facts needed to publish this plugin to the Cursor Marketplace — the official manifest reference, a real install, and the publish form's required fields — and stops before every irreversible act. Making the repository public and submitting the form are the author's decisions, not the agent's.

対象: パソコン操作権限を委譲された Cowork セッション
関連: `docs/plugin-json-validation.md`（人が手で行う版。本書はそれを委譲用に、停止条件と証跡要件を足して書き直したもの）

---

## 0. この作業の性質

この指示書自体が POKA-MON の作法に従っています。**「確認しました」は完了ではありません。** 各手順には「完了条件」があり、そこに書かれた証跡（保存されたファイル、スクリーンショット、数値）が揃ってはじめて完了です。証跡が出せない手順は、未完了として報告してください。隠さないことが唯一の要求です。

---

## 1. ゴールと非ゴール

**ゴール（4 つの事実を持ち帰る）**

| # | 持ち帰るもの |
|---|---|
| G1 | Cursor 公式の plugin.json リファレンス本文（全文） |
| G2 | 現在の `.cursor-plugin/plugin.json` と公式仕様の差分 |
| G3 | 実機インストールで、スキル 8・ルール 3・エージェント 1 が見えるか（実測値） |
| G4 | マーケットプレイス公開フォームの必須項目名と、非公開リポジトリの扱いに関する記述 |

**非ゴール（やってはいけないこと）**

- リポジトリを public にすること
- マーケットプレイスへ最終送信すること
- リポジトリへ commit / push すること
- `.cursor-plugin/plugin.json` を書き換えること

差分が見つかっても**直さないでください**。事実の採取だけが仕事です。修正は持ち帰った情報をもとに別途行います。

---

## 2. 停止条件（STOP）

次のいずれかに当たったら、**その場で手を止めて人に確認**してください。判断で進めないこと。

1. 「リポジトリを public にする必要がある」と画面が求めた、またはそう読み取れた
2. ログイン、二要素認証、パスワード入力を求められた
3. 課金、規約同意、支払い情報の入力を求められた
4. 送信・公開・Submit・Publish に相当するボタンの手前に達した
5. 本書に書かれていない外部サービスへ、画面の内容を貼るよう求められた
6. 画面に、この作業と無関係な情報（他リポジトリ名、業務メール、第三者の氏名など）が写り込んだ

6 番について: 写り込んだ情報は**報告に含めないでください**。スクリーンショットに入ってしまった場合は、該当箇所を塗りつぶすか、その部分を除いて撮り直してください。

---

## 3. 手順

### 手順 0 — 準備

対象リポジトリ: `hetyomokore-debug/poka-mon`（**private**。所有者のアカウントでのみ読めます）

1. ローカルに clone があるか確認する。無ければ任意の作業ディレクトリへ clone する。
2. 最新の main であることを確認する。

```
git -C <poka-mon のパス> fetch origin main
git -C <poka-mon のパス> log --oneline -1 origin/main
```

**完了条件**: 上のコマンドの出力が `6ac1170`（0.1.2 のマージコミット）を先頭に含むこと。異なる場合は、出た値をそのまま報告して次へ進む。

---

### 手順 1 — 公式リファレンスの採取（G1）

1. ブラウザで `https://cursor.com/docs` を開く。
2. 左メニューから「Plugins」を探し、その配下の「Reference」または「plugin.json」に相当するページを開く。見つからない場合はサイト内検索に `plugin.json` と入力する。
3. そのページの**本文を全文コピー**し、次のファイルに保存する。

```
~/Desktop/poka-mon-check/01_cursor_plugins_reference.txt
```

4. ファイルの先頭 3 行に、次を書き足す。

```
URL: <実際に開いた URL>
取得日時: <YYYY-MM-DD HH:MM>
ページタイトル: <画面に出ているタイトル>
```

**完了条件**: 上記ファイルが存在し、本文が 500 文字以上あること。「読んだ」では完了になりません。ページが見つからなかった場合は、同じファイルに「見つからず。検索した語と、たどったメニュー階層」を書いて保存する。

---

### 手順 2 — 差分表（G2）

1. ローカルの `.cursor-plugin/plugin.json` を開く（`cat` でよい）。
2. 手順 1 で保存した本文と突き合わせ、次の表を埋めて保存する。

```
~/Desktop/poka-mon-check/02_manifest_diff.md
```

| 項目 | 現在の形 | 公式にある？ | 必須？ | 形が同じ？ | 公式の書き方 |
|---|---|---|---|---|---|
| name | 文字列 | | | | |
| displayName | 文字列 | | | | |
| description | 文字列 | | | | |
| version | 文字列 | | | | |
| author | `{name, url}` の入れ子 | | | | |
| repository | URL 文字列 | | | | |
| homepage | URL 文字列 | | | | |
| license | 文字列 | | | | |
| keywords | 文字列のリスト | | | | |
| category | 文字列 | | | | |
| tags | 文字列のリスト | | | | |
| skills | `"./skills"` 文字列 | | | | |
| rules | `"./rules"` 文字列 | | | | |
| agents | `"./agents"` 文字列 | | | | |

3. **最重要は下 3 行**（skills / rules / agents）。公式の例が次のどれかを特定し、「公式の書き方」欄に実際の記述をそのまま写す。

- 文字列: `"skills": "./skills"`
- リスト: `"skills": ["./skills"]`
- 入れ子: `"skills": { ... }`
- plugin.json には書かず、フォルダ名で自動認識

4. 公式に載っていない項目、逆に公式にあるのに現在の manifest に無い項目も、行を足して記録する。

**完了条件**: 全 14 行の「公式にある？」欄が埋まっていること。判断できない行は空欄にせず「未確認」と書く。

---

### 手順 3 — 実機インストール（G3）

1. Cursor アプリを開く。
2. 設定（Settings）から「Plugins」または「Marketplace」を探す。
3. 「GitHub から追加」「ローカルフォルダから追加」に相当する機能があれば、手順 0 の clone、またはリポジトリ URL を指定して読み込む。
4. 読み込み後、次の 3 つを**数える**。

| 種別 | 期待値 | 内訳 |
|---|---|---|
| スキル | 8 | jig-mode, hakari, sekisho, sakigaki, namamono, karappo, pokayoke, yamedoki |
| ルール | 3 | no-manual-checklists, never-green-by-deletion, self-report-is-not-a-pass |
| エージェント | 1 | jig-auditor |

5. 一覧が見えている画面のスクリーンショットを撮り、次に保存する。

```
~/Desktop/poka-mon-check/03_install_skills.png
~/Desktop/poka-mon-check/03_install_rules.png
~/Desktop/poka-mon-check/03_install_agents.png
```

6. 実測値を次のファイルに書く。

```
~/Desktop/poka-mon-check/03_install_counts.md
```

**完了条件**: 実測値が 3 つとも記録されていること。**数が合わなくても、それが最も価値のある結果です。** 合わない場合は、見えたものの名前を全部書き出してください。プラグインは入るのに中身が見えない状態こそ、この確認の目的です。

インストール機能が見つからない場合は、設定画面で探した場所を記録して次へ進む。

---

### 手順 4 — 公開フォームの調査（G4）

1. ブラウザで `https://cursor.com/marketplace/publish` を開く。**提出はしません。見るだけです。**
2. 次を記録する。

- フォームの形式（リポジトリ URL を 1 つ入れる形か、項目を個別入力する形か）
- 必須マークが付いている項目名（すべて）
- 非公開リポジトリに関する記述の有無。「public である必要がある」旨の文言があれば、その文をそのまま引用する
- 審査の有無、所要日数の記載

3. フォーム全体のスクリーンショットを撮る。

```
~/Desktop/poka-mon-check/04_publish_form.png
```

4. 記録を次に保存する。

```
~/Desktop/poka-mon-check/04_publish_form.md
```

**完了条件**: 必須項目名の一覧と、非公開リポジトリに関する記述の有無が書かれていること。

**この手順で送信ボタンを押さないこと。** ログインを求められたら停止条件 2 に該当します。

---

## 4. 報告

作業後、`~/Desktop/poka-mon-check/` に次が揃っている状態にしてください。

```
01_cursor_plugins_reference.txt
02_manifest_diff.md
03_install_counts.md
03_install_skills.png / 03_install_rules.png / 03_install_agents.png
04_publish_form.md
04_publish_form.png
```

そのうえで、次のテンプレートで報告してください。

```
## 完了した手順
手順 0: 完了 / 未完了（理由）
手順 1: 完了 / 未完了（理由）
手順 2: 完了 / 未完了（理由）
手順 3: 完了 / 未完了（理由）
手順 4: 完了 / 未完了（理由）

## 実測値
スキル: N 個（期待 8）
ルール: N 個（期待 3）
エージェント: N 個（期待 1）

## manifest の差分
（合っていた項目 / 違っていた項目 / 公式に無かった項目）

## 非公開リポジトリの扱い
（公式ページの記述をそのまま引用。記述が無ければ「記述なし」）

## 停止条件に当たったか
（当たった番号と、そのときの画面の状況）

## 想定外だったこと
（指示書に書かれていなかった画面・挙動）
```

**最後の欄を空にしないでください。** 想定外が何も無かった場合は「無し」と書いてください。空欄と「無し」は別の情報です。

---

## 5. Cowork に渡す最初のメッセージ（コピー用）

```
poka-mon プラグインを Cursor マーケットプレイスに登録するための下調べをお願いします。
指示書はリポジトリの docs/cowork-marketplace-registration.md にあります（私の GitHub の
hetyomokore-debug/poka-mon、private です。ローカルに clone があればそちらを見てください）。

指示書の「非ゴール」と「停止条件」を先に読んでから始めてください。
特に、リポジトリを public にすること・フォームを送信することは、どちらも私の判断です。
その手前で必ず止まってください。

事実の採取だけをお願いします。差分が見つかっても直さないでください。
```

---

## 6. なぜ登録作業そのものを委譲しないのか

マーケットプレイス公開は、押した瞬間から取り消しが効きにくい行為です。公開後の URL は索引され、削除しても痕跡が残ります。このリポジトリは現在 private で、公開は「レビュー完了後」と決めてあります。

したがってこの委譲は、**公開の判断に必要な事実を集めるところまで**です。集まった事実を見てから、公開するか、manifest を直してからにするか、そもそも登録を見送るかを人が決めます。

判断を機械に委ねず、判断に必要な材料を機械に集めさせる。ジグの使い方としてはこれが正しい形です。
