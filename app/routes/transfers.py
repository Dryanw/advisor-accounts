import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header, Request

from app.db import get_conn
from app.idempotency_cache import IdempotencyCache
from app.models import TransferRequest, TransferResponse

router = APIRouter()


@router.post("/transfers", status_code=201, response_model=TransferResponse)
def create_transfer(req: TransferRequest, request: Request,
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
                    conn: sqlite3.Connection = Depends(get_conn)):
    cache: IdempotencyCache = request.app.state.idempotency_cache
    if idempotency_key:
        cached = cache.get(idempotency_key)
        if cached is not None:
            if cached["result"] is None:
                raise HTTPException(status_code=409, detail="request already in progress")
            return cached["result"]

        if not cache.set_if_absent(idempotency_key):
            raise HTTPException(status_code=409, detail="request already in progress")

    # existence check
    rows = conn.execute(
        "SELECT id FROM accounts WHERE id IN (?, ?)", (req.from_account, req.to_account), ).fetchall()
    found_ids = {row["id"] for row in rows}
    if req.from_account not in found_ids:
        raise HTTPException(status_code=404, detail="from_account not found")
    if req.to_account not in found_ids:
        raise HTTPException(status_code=404, detail="to_account not found")

    # use BEGIN IMMEDIATE to prevent race condition
    conn.execute("BEGIN IMMEDIATE")
    try:
        src_row = conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ? RETURNING balance",
            (req.amount, req.from_account, req.amount),
        ).fetchone()
        if src_row is None:
            conn.rollback()
            raise HTTPException(status_code=409, detail="insufficient funds")

        dst_row = conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ? RETURNING balance",
            (req.amount, req.to_account),
        ).fetchone()

        new_src, new_dst = Decimal(src_row["balance"]), Decimal(dst_row["balance"])

        transfer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO transfers (id, from_account, to_account, amount, created_at) VALUES (?, ?, ?, ?, ?)",
            (transfer_id, req.from_account, req.to_account, req.amount, now),
        )
        conn.execute(
            "INSERT INTO transactions (account_id, type, amount, created_at, transfer_id) VALUES (?, 'transfer_out', ?, ?, ?)",
            (req.from_account, req.amount, now, transfer_id),
        )
        conn.execute(
            "INSERT INTO transactions (account_id, type, amount, created_at, transfer_id) VALUES (?, 'transfer_in', ?, ?, ?)",
            (req.to_account, req.amount, now, transfer_id),
        )
        conn.commit()
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        if idempotency_key:
            cache.release(idempotency_key)
        raise
    result = {"transfer_id": transfer_id, "from_balance": f'{new_src:.2f}', "to_balance": f'{new_dst:.2f}'}
    if idempotency_key:
        cache.complete(idempotency_key, result)
    return result
