import json
from os import makedirs
from os.path import dirname
from typing import TYPE_CHECKING, Callable, ParamSpec, TypeVar

if TYPE_CHECKING:
    from notify_manager import Notify

T = TypeVar("T")
P = ParamSpec("P")


def save_cookie(func: Callable[P, T]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        result = func(*args, **kwargs)

        n: Notify = args[0]  # type: ignore

        makedirs(dirname(n.cookie_path), exist_ok=True)
        with open(n.cookie_path, "w") as f:
            json.dump(n.session.cookies.get_dict(), f, indent=2)  # type: ignore

        return result

    return wrapper
