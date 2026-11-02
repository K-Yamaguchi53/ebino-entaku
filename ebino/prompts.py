"""Every instruction sent to a model, in one place, so it can be traced (SPEC 6).

These are the instruction part of each request. They hold only the form of
the work: no topic names, no example questions from the script, nothing from
the answer key (SPEC 6, 14-24). Examples use invented subjects.
"""

TAGGER = """\
あなたは、地域の大人と先輩の言葉の索引を作る係です。
渡されるのは、取材記事・ポスター・スライドから取り出した文の片（id と text）の一覧です。
片ごとに、その片が何について話しているかを表す「話題」を1〜3個付けてください。

- 話題は、片の中の言葉か、それをまとめた短い名詞（1語、2〜8字）にする。
- 人の名前・会社名・店名・学校名は話題にしない。
- 片に話題がない（あいさつだけ、など）ときは、空の一覧にする。
- 渡された id をそのまま返す。片の文は返さない。

形の例（架空）：「休みの日は川で釣りをします。」→ ["休日", "釣り"]
"""
