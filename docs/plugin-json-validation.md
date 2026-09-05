# plugin.json 検証手順（公開前チェック 2）

> English summary: `.cursor-plugin/plugin.json` was written from search-result fragments because Cursor's Plugins Reference was unreachable from the authoring environment. This is the maintainer procedure for checking its field names and shapes against the official reference, the Marketplace publish form, and a live install — and for reporting back what to fix. The dangerous failure is silent: the plugin installs, but the skills are not found.

委譲版: パソコン操作権限を持つエージェント（Cowork）に任せる場合は `cowork-marketplace-registration.md` を使う。停止条件と証跡要件を足した同内容。

目的は 1 つだけです。**推測で書いた登録票（`.cursor-plugin/plugin.json`）の項目名と形が、Cursor 公式の書き方と一致しているか**を確かめます。

plugin.json は Cursor に提出する「登録票」です。「スキルはこのフォルダ、ルールはこのフォルダ、エージェントはこのフォルダにあります」と Cursor に教える書類で、項目名や書き方が公式と少しでも違うと、プラグインは入るのに中身が Cursor に見つけてもらえない「静かな失敗」（KARAPPO の状態）が起きます。

## 現在の登録票（要約）

| 項目 | 現在の値 |
|---|---|
| name | `"poka-mon"` |
| displayName | `"POKA-MON — Jig-Driven Development"` |
| description | 一文の説明 |
| version | `"0.1.2"` |
| author | `{ name, url }` の入れ子 |
| repository | GitHub の URL |
| homepage | README の URL |
| license | `"MIT"` |
| keywords | 単語のリスト |
| category | `"engineering"` |
| tags | 単語のリスト |
| skills | `"./skills"`（文字列） |
| rules | `"./rules"`（文字列） |
| agents | `"./agents"`（文字列） |

実体のフォルダ: `skills/`（jig-mode ＋ 7 体）、`rules/`（3 本）、`agents/`（1 本）。

## 手順 A：公式ページと突き合わせる（10 分）

1. ブラウザで cursor.com/docs を開き、左メニューの「Plugins」を開く。その中の「Reference」または「plugin.json」のページを探す。見つからなければ、ページ内の検索窓に `plugin.json` と入れる。
2. そのページで、plugin.json の項目一覧（表、またはコード例）を見つける。
3. 下の表を埋める。「公式にある？」はその項目名が公式ページに出てくるか。「形が同じ？」は公式の例と同じ書き方か（文字列か、リストか、入れ子か）。

| 項目 | 公式にある？ | 必須？ | 形が同じ？ | メモ |
|---|---|---|---|---|
| name | | | | |
| displayName | | | | |
| description | | | | |
| version | | | | |
| author | | | | |
| repository | | | | |
| homepage | | | | |
| license | | | | |
| keywords | | | | |
| category | | | | |
| tags | | | | |
| skills | | | | |
| rules | | | | |
| agents | | | | |

4. **最重要は下 3 行（skills / rules / agents）。** 公式の例が次のどれかを見る。
   - `"skills": "./skills"` のような文字列
   - `"skills": ["./skills"]` のようなリスト
   - `"skills": { ... }` のような入れ子
   - そもそも plugin.json に書かず、フォルダ名だけで自動認識
5. できれば、そのページの本文を全部コピーして持ち帰る。表が埋まらなくても、本文があれば突き合わせできる。

## 手順 B：公開フォームでも確かめる（5 分）

1. cursor.com/marketplace/publish を開く（提出はしない。見るだけ）。
2. フォームが「リポジトリの URL を入れる」形か、「項目を一つずつ入力する」形かを見る。
3. 項目入力の形なら、必須マークが付いている項目名を書き留める。それが「本当に必要な項目」の一次情報になる。

## 手順 C：実機で見る（できれば。一番確実）

1. Cursor アプリを開き、設定（Settings）から「Plugins」または「Marketplace」を探す。
2. 「GitHub から追加」「ローカルのフォルダから追加」に相当する項目があれば、このリポジトリ（private のままで可。自分のアカウントなら読める）か、手元に clone したフォルダを指定する。
3. 入れたあと、次の 3 つが見えるか数える。
   - スキル：7 体（hakari, sekisho, sakigaki, namamono, karappo, pokayoke, yamedoki）と、入口の jig-mode
   - ルール：3 本
   - エージェント：1 本（jig-auditor）
4. プラグイン自体は入るのに数が足りない場合、それが「静かな失敗」。項目名か形が違っている可能性が高い。見えた数を記録する。

## 持ち帰るもの

- 手順 A の表（埋まった分だけで可）と、公式ページ本文のコピー
- 手順 B で必須になっていた項目名
- 手順 C で見えたスキル・ルール・エージェントの数

これがあれば plugin.json の差分を直せる。手順 A の本文コピーだけでも作業に入れる。

## 検証が終わったら

- 差分があれば `.cursor-plugin/plugin.json` を直し、CHANGELOG に「公式リファレンスと照合済み」と日付を書く。
- README「Before publishing」の該当項目を消す。
- この文書は残す。次に項目名が変わったときの手順でもある。
