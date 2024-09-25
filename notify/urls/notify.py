from urllib.parse import urljoin


class NotifyURL:
    HOST = "https://notify-bot.line.me"
    WEP_LOGIN = urljoin(HOST, "login")

    API_GROUP_LIST = urljoin(HOST, "api/groupList")
