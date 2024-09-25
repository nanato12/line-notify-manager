from requests import Response


class Debugger:
    @staticmethod
    def save_html(r: Response, path: str = "index.html") -> None:
        with open(path, "wt") as f:
            f.write(r.text)
