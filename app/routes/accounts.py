import base64
import json
import sqlite3
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_conn
from app.models import TransactionRequest

router = APIRouter()


@router.get("/accounts/{account_id}")
def get_account(account_id: str, conn: sqlite3.Connection = Depends(get_conn)):
    row = conn.execute(
        "SELECT id, client_name, balance FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="account not found")
    return {"id": row["id"], "client_name": row["client_name"], "balance": f'{row["balance"]:.2f}'}


@router.get("/accounts/{account_id}/positions")
def get_positions(account_id: str, conn: sqlite3.Connection = Depends(get_conn)):
    if conn.execute("SELECT 1 FROM accounts WHERE id = ?", (account_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="account not found")
    funds = conn.execute("SELECT positions.fund_code, funds.name, funds.nav, positions.units from positions "
                         "join funds on positions.fund_code = funds.code where account_id = ?",
                         (account_id,)).fetchall()
    result = []
    for fund in funds:
        result.append({
            "fund_code": fund["fund_code"],
            "fund_name": fund["name"],
            "units": f"{fund['units']:.4f}",
            "market_value": f"{fund['units'] * fund['nav']:.2f}",
        })

    return {"account_id": account_id, "positions": result}


def encode_cursor(created_at: str, txn_id: int) -> str:
    payload = json.dumps({"created_at": created_at, "id": txn_id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, int]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return payload["created_at"], payload["id"]
    except Exception:
        raise HTTPException(status_code=400, detail="invalid cursor")


@router.get("/accounts/{account_id}/transactions")
def list_transactions(
        account_id: str,
        query: Annotated[TransactionRequest, Query()],
        conn: sqlite3.Connection = Depends(get_conn),
):
    account = conn.execute("SELECT 1 FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")

    conditions = ["account_id = ?"]
    params: list = [account_id]

    if query.from_time:
        conditions.append("created_at >= ?")
        params.append(query.from_time.isoformat())
    if query.to_time:
        # inclusive of the whole day, since created_at is a full timestamp
        conditions.append("created_at <= ?")
        params.append(query.to_time.isoformat())
    if query.type:
        conditions.append("type = ?")
        params.append(query.type)

    if query.cursor:
        cursor_created_at, cursor_id = decode_cursor(query.cursor)
        # keyset predicate: strictly "after" the last row of the previous page,
        # ordered by (created_at, id)
        conditions.append("(created_at, id) > (?, ?)")
        params.extend([cursor_created_at, cursor_id])

    where_clause = " AND ".join(conditions)
    # fetch one extra row to know whether a next page exists
    sql = f"""
        SELECT id, account_id, type, amount, created_at, transfer_id
        FROM transactions
        WHERE {where_clause}
        ORDER BY created_at, id
        LIMIT ?
    """
    params.append(query.limit + 1)

    rows = conn.execute(sql, params).fetchall()

    has_more = len(rows) > query.limit
    page_rows = rows[: query.limit]

    next_cursor = None
    if has_more:
        last = page_rows[-1]
        next_cursor = encode_cursor(last["created_at"], last["id"])

    return {
        "transactions": [
            {
                "id": row["id"],
                "account_id": row["account_id"],
                "type": row["type"],
                "amount": f'{row["amount"]:.2f}',
                "created_at": row["created_at"],
                "transfer_id": row["transfer_id"],
            }
            for row in page_rows
        ],
        "next_cursor": next_cursor
    }
