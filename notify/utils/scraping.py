from typing import Any

from bs4 import BeautifulSoup
from requests import Response


def extract_input_value(r: Response, name: str) -> str | list[str] | Any:
    soup = BeautifulSoup(r.content, "html.parser")
    i = soup.find("input", attrs={"name": name})
    if not (v := i.get("value")):
        return ""
    return v


def extract_csrf(r: Response, name: str = "__csrf") -> str:
    v = extract_input_value(r, name)
    if isinstance(v, list):
        return v[0]
    return str(v)
