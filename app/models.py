from datetime import datetime

from pydantic import BaseModel, model_validator, PositiveFloat, Field, ConfigDict
from typing import Literal


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: PositiveFloat

    @model_validator(mode="after")
    def check_different_accounts(self) -> "TransferRequest":
        if self.from_account == self.to_account:
            raise ValueError("from_account and to_account must be different")
        return self


class TransferResponse(BaseModel):
    transfer_id: str
    from_balance: str
    to_balance: str


TransactionType = Literal["deposit", "withdrawal", "transfer_in", "transfer_out"]


class TransactionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_time: datetime | None = Field(default=None, alias="from")
    to_time: datetime | None = Field(default=None, alias="to")
    type: TransactionType | None = None
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = None

    @model_validator(mode="after")
    def check_date_range(self) -> "TransactionRequest":
        if self.from_time and self.to_time and self.from_time > self.to_time:
            raise ValueError("from_date must not be after to_date")
        return self
