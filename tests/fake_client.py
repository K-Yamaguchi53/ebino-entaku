"""A stand-in for anthropic.Anthropic that records every request it is given."""

import json
from types import SimpleNamespace


def text_response(value, stop_reason="end_turn"):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason)


def tool_response(*calls, text=""):
    """calls: (id, name, input) for each tool_use block."""
    blocks = [SimpleNamespace(type="text", text=text)] if text else []
    blocks += [SimpleNamespace(type="tool_use", id=i, name=n, input=x) for i, n, x in calls]
    return SimpleNamespace(content=blocks, stop_reason="tool_use")


class FakeClient:
    """answers: a list of responses given in order, or a function of the request."""

    def __init__(self, answers):
        self.requests: list[dict] = []
        self._answers = answers
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **request):
        self.requests.append(json.loads(json.dumps(request, ensure_ascii=False, default=vars)))
        if callable(self._answers):
            return self._answers(request)
        if not self._answers:
            raise RuntimeError("no more scripted answers")
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def all_sent(self) -> str:
        return json.dumps(self.requests, ensure_ascii=False)
