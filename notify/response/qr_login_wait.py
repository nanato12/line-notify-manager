from typing import Optional

from pydantic import BaseModel


class QRLoginWaitResponse(BaseModel):
    pinCode: Optional[str]
    redirectPath: Optional[str]
    errorCode: Optional[int]
    error: Optional[str]
