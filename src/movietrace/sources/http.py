from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> object:
    full_url = url
    if params:
        full_url = f"{url}?{urlencode(params)}"
    request = Request(full_url, headers=headers or {})
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)

