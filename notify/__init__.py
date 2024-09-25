import json
from os import makedirs
from os.path import dirname, exists
from os.path import join as path_join
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from pydantic import BaseModel, Field
from requests import Session

from notify import config
from notify.decorator import save_cookie
from notify.exceptions import AuthorizeException
from notify.logger import get_file_path_logger
from notify.models.group import Group
from notify.response.get_group_list import GetGroupListResponse
from notify.response.qr_login_pin_wait import QRLoginPINWaitResponse
from notify.response.qr_login_session import QRLoginSessionResponse
from notify.response.qr_login_wait import QRLoginWaitResponse
from notify.urls.access import LINEAccessURL
from notify.urls.notify import NotifyURL
from notify.utils.countdown import Countdown
from notify.utils.scraping import extract_csrf

logger = get_file_path_logger(__name__)


class Notify(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    email: str = Field(default="")
    password: str = Field(default="")
    cookie_name: str = Field(default="notify")
    session: Session = Field(init=False, default_factory=Session)

    @save_cookie
    def model_post_init(self, __context: Any) -> None:
        if exists(self.cookie_path):
            # login with cookie
            with open(self.cookie_path) as j:
                c = json.load(j)
            self.session.cookies.update(c)
        elif all((self.email, self.password)):
            # login with Email and Password
            raise NotImplementedError("Email login not yet implemented.")
        else:
            # login with QR
            r = self.session.get(NotifyURL.WEP_LOGIN)
            params = parse_qs(urlparse(r.url).query)
            csrf_token = extract_csrf(r)

            logger.debug(f"{csrf_token=}")
            logger.debug(f"{params=}")

            qr_login_params = params.copy()
            qr_login_params.pop("loginState")
            qr_login_params["channelId"] = qr_login_params.pop(
                "loginChannelId"
            )

            # get QR image url path
            res = QRLoginSessionResponse.model_validate(
                self.session.get(
                    LINEAccessURL.QR_LOGIN_SESSION, params=qr_login_params
                ).json()
            )
            logger.debug(f"{res=}")

            # get QR image
            r = self.session.get(urljoin(LINEAccessURL.HOST, res.qrCodePath))
            qr_path = path_join(config.TMP_DIR, f"{res.code}.png")

            makedirs(dirname(qr_path), exist_ok=True)
            with open(qr_path, "wb") as f:
                f.write(r.content)

            # wait QR login
            print(f"Please Login with QR.\nQR code: {qr_path}")
            countdown = Countdown(seconds=180, message="QR limit")
            countdown.start()

            res = QRLoginWaitResponse.model_validate(
                self.session.get(LINEAccessURL.QR_LOGIN_WAIT).json()
            )
            countdown.stop()
            logger.debug(f"{res=}")

            if not res.pinCode:
                raise AuthorizeException(f"[{res.errorCode}] {res.error}")

            # wait input PIN code
            print(f"Please input PIN code: {res.pinCode}")
            countdown = Countdown(seconds=180, message="PIN limit")
            countdown.start()

            res = QRLoginPINWaitResponse.model_validate(
                self.session.get(LINEAccessURL.QR_LOGIN_PIN_WAIT).json()
            )
            countdown.stop()
            logger.debug(f"{res=}")

            if not res.redirectPath:
                raise AuthorizeException(f"[{res.errorCode}] {res.error}")

            # login
            login_params = params.copy()
            login_params.update({"__csrf": csrf_token})
            r = self.session.get(
                urljoin(LINEAccessURL.HOST, res.redirectPath),
                params=login_params,
            )

            logger.info(f"saved cookie: {self.cookie_path}")

    @property
    def cookie_path(self) -> str:
        return path_join(config.COOKIE_DIR, f"{self.cookie_name}.json")

    def get_group_list(self) -> list[Group]:
        r = self.session.get(NotifyURL.API_GROUP_LIST)
        logger.debug(f"get-group-list: {r.json()}")

        res = GetGroupListResponse.model_validate(r.json())
        return res.results
