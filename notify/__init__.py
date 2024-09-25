import json
from os import makedirs
from os.path import dirname, exists
from os.path import join as path_join
from typing import Any, Optional
from urllib.parse import parse_qs, urljoin, urlparse

from pydantic import BaseModel, Field, ValidationError
from requests import JSONDecodeError, Session

from notify import config
from notify.decorator import save_cookie
from notify.exceptions import (
    AuthorizeException,
    GetGroupListException,
    IssueTokenException,
    QRLoginPINWaitException,
    QRLoginSessionException,
    QRLoginWaitException,
)
from notify.logger import get_file_path_logger
from notify.models.group import Group
from notify.request.issue_token import IssueTokenRequest
from notify.response.get_group_list import GetGroupListResponse
from notify.response.issue_token import IssueTokenResponse
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
            r = self.session.get(NotifyURL.WEB_LOGIN)
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
            try:
                res = QRLoginSessionResponse.model_validate(
                    session_j := (
                        session_r := self.session.get(
                            LINEAccessURL.QR_LOGIN_SESSION,
                            params=qr_login_params,
                        )
                    ).json()
                )
                logger.debug(f"{res=}")
            except ValidationError:
                raise QRLoginSessionException(
                    f"Invalid response json: {session_j}"
                )
            except JSONDecodeError:
                raise QRLoginSessionException(
                    f"Invalid response: [{session_r.status_code}] "
                    f"{session_r.url}"
                )

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

            try:
                res = QRLoginWaitResponse.model_validate(
                    wait_j := (
                        wait_r := self.session.get(LINEAccessURL.QR_LOGIN_WAIT)
                    ).json()
                )
                countdown.stop()
                logger.debug(f"{res=}")
            except ValidationError:
                raise QRLoginWaitException(f"Invalid response json: {wait_j}")
            except JSONDecodeError:
                raise QRLoginWaitException(
                    f"Invalid response: [{wait_r.status_code}] {wait_r.url}"
                )

            if not res.pinCode:
                raise AuthorizeException(f"[{res.errorCode}] {res.error}")

            # wait input PIN code
            print(f"Please input PIN code: {res.pinCode}")
            countdown = Countdown(seconds=180, message="PIN limit")
            countdown.start()

            try:
                res = QRLoginPINWaitResponse.model_validate(
                    pin_j := (
                        pin_r := self.session.get(
                            LINEAccessURL.QR_LOGIN_PIN_WAIT
                        )
                    ).json()
                )
                countdown.stop()
                logger.debug(f"{res=}")
            except ValidationError:
                raise QRLoginPINWaitException(
                    f"Invalid response json: {pin_j}"
                )
            except JSONDecodeError:
                raise QRLoginPINWaitException(
                    f"Invalid response: [{pin_r.status_code}] {pin_r.url}"
                )

            if not res.redirectPath:
                raise AuthorizeException(f"[{res.errorCode}] {res.error}")

            # login
            login_params = params.copy()
            login_params.update({"__csrf": csrf_token})  # type: ignore [dict-item]
            r = self.session.get(
                urljoin(LINEAccessURL.HOST, res.redirectPath),
                params=login_params,
            )

            logger.info(f"saved cookie: {self.cookie_path}")

    @property
    def cookie_path(self) -> str:
        return path_join(config.COOKIE_DIR, f"{self.cookie_name}.json")

    def get_group_list(self) -> list[Group]:
        groups: list[Group] = []
        page = 1
        while True:
            try:
                res = GetGroupListResponse.model_validate(
                    j := (
                        r := self.session.get(
                            NotifyURL.API_GROUP_LIST, params={"page": page}
                        )
                    ).json()
                )
                logger.debug(f"{res=}")
            except ValidationError:
                raise GetGroupListException(f"Invalid response json: {j}")
            except JSONDecodeError:
                raise GetGroupListException(
                    f"Invalid response: [{r.status_code}] {r.url}"
                )

            if not res.results:
                break
            groups.extend(res.results)
            page += 1
        return groups

    def issue_token(self, name: str, group: Optional[Group] = None) -> str:
        csrf_token = extract_csrf(
            self.session.get(NotifyURL.WEB_MYPAGE), "_csrf"
        )
        logger.debug(f"{csrf_token=}")

        if group:
            req = IssueTokenRequest.by_group(group, name, csrf_token)
        else:
            req = IssueTokenRequest.by_user(name, csrf_token)

        try:
            res = IssueTokenResponse.model_validate(
                j := (
                    r := self.session.post(
                        NotifyURL.ISSUE_TOKEN, data=req.data
                    )
                ).json()
            )
            logger.debug(f"{res=}")
        except ValidationError:
            raise IssueTokenException(f"Invalid response json: {j}")
        except JSONDecodeError:
            raise IssueTokenException(
                f"Invalid response: [{r.status_code}] {r.url}"
            )

        return res.token  # type: ignore [no-any-return]
