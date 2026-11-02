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

実データはこのリポジトリに入っていません（架空の見本だけ）。

| 種類 | 何か | 年度 | 誰の了解で使ったか |
|---|---|---|---|
| 志事図鑑 | <!-- TODO --> | | |
| 探究ポスター | <!-- TODO --> | | |
| 越境した人の話 | <!-- TODO --> | | |
| 研修・交流の報告スライド | <!-- TODO --> | | |
| 外からえびのに来た大人の話 | <!-- TODO --> | | |
| 先生の話 | <!-- TODO --> | | |
| 期間中に返った答え | <!-- TODO --> | | |

<!-- TODO 11/6: 地図の出典 © OpenStreetMap contributors -->

## 作る途中で変えたこと

<!-- TODO: 中身は先生から受け取る。実データで流して分かって直したことを、中身を伏せて3〜5件 -->

## 作らなかったもの

<!-- TODO: 撤退ラインで外したものがあれば、ここに書く -->

## 動画

<!-- TODO 11/7 -->
