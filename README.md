# えびの円卓　出会った数 × 試した数

> 会いに行く前に、会える。

**English summary:** Ebino Round Table is a tool for high school students in Ebino, Miyazaki. A student asks one question, and the real words of local adults and seniors light up on a hand-drawn map of the basin. The AI never gives its own opinion: everything the seats say is original text, verified character by character by code outside the AI.

このAIは自分の意見を言わない。話すのは全部、実在のえびのの大人の原文。

## 何のための道具か

えびの市の高校生が、地域の大人と先輩の言葉に一度に話を聞ける、会いに行く前の入口です。

<!-- TODO 11/7: 画面の説明と動画へのリンク -->

## 触ってみる

<!-- TODO 11/7: 見本モードの手順（APIキーなしで、問いからふりかえりの1枚まで） -->

リポジトリにあるのは架空の見本データだけです。

## APIキーを渡して動かす

`.env.example` を `.env` に写して、`ANTHROPIC_API_KEY` を入れます。`.env` はリポジトリに入りません。

<!-- TODO 11/7: 起動の手順 -->

## テスト

```
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m pytest
```

テストの本文はすべて架空です。

## 外から持ち込んだデータ

実データはこのリポジトリに入っていません。入っているのは架空の見本だけです。実データは作者の手元のPCだけで取り込み、開発の Claude Code にも中身は渡していません。

どれも、作者が勤める高校の進路指導の主任と管理職の許可を得て使っています。

| 種類 | 何か |
|---|---|
| 志事図鑑 | 1年生が地域で働く人を取材した記事の冊子4年分（古い2年分は紙の冊子をスキャンして写した）。記事は、取材した大人ご本人が確認したもの。同じ会社は1つの席にまとめて89席 |
| 先輩の探究 | 先輩が探究の発表で使ったポスター3年分36枚（1ページずつのPDF）と、発表スライド14本。50席 |
| 越境した人の話 | 1年生が県外・海外の研修を学年に伝えた会の発表スライド。文字が取れる7人分 |
| 研修・交流の報告スライド | 先輩が作った、台湾研修・マレーシア研修・志事図鑑サミット（他県の高校と合同）の報告スライド5本 |
| 外からえびのに来た大人の話 | 1年生のオリエンテーションで話した講演スライド1本（ご本人から受け取り、使う了解ももらった） |
| 先生の話 | 作者（教員）が書いた記事1本 |
| 期間中に返った答え | 試した1年生が選んだ質問カード1枚への、大人2人と作者の答え（答えた本人の了解つき） |

- 生徒の氏名・取材した生徒の名前・電話番号・番地は、モデルに渡す前にコードで外しています。外し忘れがないかは、最後に関所で確かめます。
- 人の名前は、画面にも動画にも出しません。席の札は肩書きだけです。校内で1年生が使う画面だけ、会社名を添えます。

### 地図

- 地図（えびの市の境界・川内川・地名・学校の位置）は、OpenStreetMap のデータから作りました。**© OpenStreetMap contributors**。地図のデータ（`mapdata/ebino_osm.json`）は OpenStreetMap からの派生データで、ODbL 1.0（Open Database License）に従います。
- 地図のデータは `python tools/fetch_osm_map.py` で1回だけ取ってきて、リポジトリに入れました。アプリは動いている間に外へ取りに行きません。
- 手描き風の線は rough.js 4.6.6（MIT License）を同梱して描いています（`ebino/static/rough.js`、ライセンスの文は `ebino/static/rough.LICENSE.txt`）。
- 地図を重ねる立体の絵（南から北を見下ろした、ふつうの地図と同じく北が上の夜の地形模型）は、Copernicus DEM GLO-30 の標高から Blender で描きました。リポジトリに入れたのは、小さく縮めた絵（`mapdata/relief.webp`）、絵の画素と地図の座標の対応（`mapdata/relief_projection.json`）、粗い高さの網（`mapdata/relief_heights.json`、10単位ごと）の3つだけです。生の標高と大きな絵は入れていません。アプリは動いている間に外へ取りに行きません。3つのどれかが無い・読めないときは平らな地図に、地図も無ければ席の一覧に戻ります。
- produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved
- The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.
- 標高を取ってくる（4タイル・約110MB。置き場所はリポジトリの外で、2回目からは使い回す）：`python tools/fetch_copernicus_dem.py 作業フォルダ`
- 立体の絵を描く（上の作業フォルダの高さの網から）：`blender -b --python tools/render_relief.py -- 作業フォルダ`
- 2本の台本には numpy と Pillow が要ります（Blender の中で流す方は、Blender に入っている numpy を使います）。アプリ本体は標準ライブラリだけです。
- 題の書体は Shippori Mincho B1（SIL Open Font License 1.1）から、題に使う字だけを切り出して同梱しています（`ebino/static/title.woff`、ライセンスの文は `ebino/static/title.OFL.txt`）。

## 作る途中で変えたこと

実データ（取材記事・ポスター・スライド）は作者の手元だけで流し、開発の Claude Code には件数と形（見出しの書き方など）だけを渡して直しました。

- **ポスターの見出しは、年度や学年で書き方がばらばらでした。**「２　研究仮説」「＜目的＞」「【目的】」「なぜ○○なのか（探究テーマ設定理由）」などです。見出しを5つの役（背景と課題・目的・手法・結果・結論と展望）に寄せる読み方を3回作り直しました。最初に流したときは、そのころ取り込んでいた22枚のうち17枚が止まっていましたが、いまは席に入れたポスターがすべて読めます。
- **「生徒の名前はポスターのいちばん上にある」という前提が外れました。** 本文の途中や真ん中に名前がある作品がありました。位置で落とすのに加えて、伏せる語の表を作り、最後に「伏せた語が残っていないか」を確かめる関所を置きました。関所に引っかかった席は、画面にもモデルにも渡しません。
- **PDF の中に、見た目は同じで文字コードが違う漢字（部首の字）が混ざっていました。** 名前が伏せられずに関所で止まったことで見つかりました。文字を取り出した直後に、ふつうの漢字へ置き換えています。
- **紙しかなかった過去の冊子2冊（スキャン41ページ）を写して加えました。** 4年分の冊子がそろい、席は101から152になりました。
- **「やり残しが多い場所ほど光る」点は、今回は作らないことにしました。**

## 作らなかったもの

<!-- TODO: 撤退ラインで外したものがあれば、ここに書く -->

## 動画

<!-- TODO 11/7 -->
