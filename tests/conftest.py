import datetime

import pytest
from fastapi.testclient import TestClient

from app.db import connect, get_conn, init_db
from app.main import app


class QueryLog:
    def __init__(self):
        self.statements = []

    def __call__(self, sql):
        self.statements.append(sql)

    def selects(self):
        return [s for s in self.statements if s.lstrip().upper().startswith("SELECT")]

    def reset(self):
        self.statements.clear()


@pytest.fixture
def start_day():
    return datetime.datetime(2026, 9, 26)


@pytest.fixture
def db_path(tmp_path, start_day):
    path = str(tmp_path / "test.db")
    conn = connect(path)
    init_db(conn)
    conn.executemany("INSERT INTO funds VALUES (?, ?, ?)", [
        ("FND-101", "Maple Canadian Equity", 24.51),
        ("FND-102", "Maple Canadian Bond", 10.18),
        ("FND-103", "Maple Balanced Income", 15.77),
        ("FND-104", "Maple Global Dividend", 18.90),
        ("FND-105", "Maple Money Market", 10.00),
        ("FND-106", "Maple Canadian Small Cap", 31.40),
    ])
    conn.executemany("INSERT INTO accounts VALUES (?, ?, ?, ?)", [
        ("ACC-1001", "Client One", "0012345678901", 1000.00),
        ("ACC-1002", "Client Two", "0098765432109", 500.00),
    ])
    conn.executemany("INSERT INTO positions (account_id, fund_code, units) VALUES (?, ?, ?)", [
        ("ACC-1001", code, 100.0 + i) for i, code in
        enumerate(["FND-101", "FND-102", "FND-103", "FND-104", "FND-105", "FND-106"])
    ])
    conn.executemany(
        "INSERT INTO transactions (account_id, type, amount, created_at, transfer_id) VALUES (?, ?, ?, ?, ?)", [
            ("ACC-1001", "deposit", 200, (start_day - datetime.timedelta(days=0)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 100, (start_day - datetime.timedelta(days=10)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 300, (start_day - datetime.timedelta(days=5)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 400, (start_day - datetime.timedelta(days=1)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 500, (start_day - datetime.timedelta(days=3)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 400, (start_day - datetime.timedelta(days=4)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 200, (start_day - datetime.timedelta(days=2)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 100, (start_day - datetime.timedelta(days=5)).isoformat(timespec="seconds"), None),
            ("ACC-1001", "deposit", 300, (start_day - datetime.timedelta(days=10)).isoformat(timespec="seconds"), None),
        ])

    conn.commit()
    conn.close()
    return path


@pytest.fixture
def query_log():
    return QueryLog()


@pytest.fixture
def client(db_path, query_log):
    def _conn():
        conn = connect(db_path)
        conn.set_trace_callback(query_log)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_conn] = _conn
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
