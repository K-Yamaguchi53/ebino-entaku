"""One to one (直し34): a student and one seat. The questions offered are the
teacher's (texts/ask_questions.txt), one an item of that seat's words that
has some; what the seat says is its own paragraph for that item, as spoken
words where the speaker's checks let them through, as everywhere.

Which items a seat's words have:
  - an article (地域で働く大人, and 外から来た大人・先生 from a docx): its
    rows (ingest/article_docx.py USED_ROWS), 本文タイトル and 本文 one item;
  - a poster (探究をした先輩): its roles (ingest/poster_pdf.py ROLES);
  - pages only (県外・海外に出た人, 外から来た大人・先生 from a PDF): the
    axes a page answers, from the table the teacher keeps (ask_pages.tsv in
    the data folder: 席・ページ・軸); with no such row, none.
"""

# 種類 in ask_questions.txt.
GROUP_ARTICLE = "記事"
GROUP_POSTER = "ポスター"
GROUP_CROSS = "県外・海外"
GROUP_OUTSIDER = "外から来た"
GROUPS = (GROUP_ARTICLE, GROUP_POSTER, GROUP_CROSS, GROUP_OUTSIDER)

# The axes of the words that have pages only, in the order asked.
CROSS_AXES = ("行く前", "向こうで", "帰ってきて", "これから")
OUTSIDER_AXES = ("来たわけ", "見えたこと", "したかったこと")

# An article's sections that are one item, and those with no question.
ARTICLE_SAME_ITEM = {"本文タイトル": "本文"}
ARTICLE_NO_QUESTION = ("キャッチコピー", "ランキング")

