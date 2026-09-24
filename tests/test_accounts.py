import datetime


def test_get_account(client):
    r = client.get("/accounts/ACC-1001")
    assert r.status_code == 200
    assert r.json()["client_name"] == "Client One"


def test_get_account_not_found(client):
    assert client.get("/accounts/ACC-9999").status_code == 404


def test_positions_shape(client):
    r = client.get("/accounts/ACC-1001/positions")
    assert r.status_code == 200
    positions = r.json()["positions"]
    assert len(positions) == 6
    assert positions[0] == {"fund_code": "FND-101", "fund_name": "Maple Canadian Equity",
                            "units": "100.0000", "market_value": "2451.00"}


def test_positions_query_count(client, query_log):
    query_log.reset()
    r = client.get("/accounts/ACC-1001/positions")
    assert r.status_code == 200
    assert len(query_log.selects()) <= 2, f"{len(query_log.selects())} SELECT statements for one request"


def test_get_transactions_unknown_account(client):
    r = client.get("/accounts/ACC-1003/transactions")
    assert r.status_code == 404


def test_get_transactions_invalid_cursor(client):
    r = client.get("/accounts/ACC-1001/transactions", params={'cursor': 'INVALID_CURSOR'})
    assert r.status_code == 400


def test_get_transactions_empty_account(client):
    r = client.get("/accounts/ACC-1002/transactions")
    assert r.status_code == 200
    response = r.json()

    assert response['transactions'] == []
    assert response['next_cursor'] is None


def test_get_transactions_no_filter(client, start_day):
    r = client.get("/accounts/ACC-1001/transactions")
    assert r.status_code == 200
    transactions = r.json()["transactions"]
    assert len(transactions) == 9

    # transactions should be ordering by created_at
    assert [x['created_at'] for x in transactions] == [
        (start_day - datetime.timedelta(days=x)).isoformat(timespec="seconds") for x in
        [10, 10, 5, 5, 4, 3, 2, 1, 0]]


def test_get_transactions_invalid_from_filter(client):
    r = client.get("/accounts/ACC-1001/transactions", params={'from': 'INVALID_STRING'})
    assert r.status_code == 422


def test_get_transactions_from_filter(client, start_day):
    r = client.get("/accounts/ACC-1001/transactions",
                   params={'from': (start_day - datetime.timedelta(days=1)).isoformat(timespec="seconds")})
    assert r.status_code == 200
    transactions = r.json()["transactions"]
    # only 2 of the transactions are after start_day - 1 day
    assert len(transactions) == 2


def test_get_transactions_invalid_to_filter(client):
    r = client.get("/accounts/ACC-1001/transactions", params={'to': 'INVALID_STRING'})
    assert r.status_code == 422


def test_get_transactions_to_filter(client, start_day):
    r = client.get("/accounts/ACC-1001/transactions",
                   params={'to': (start_day - datetime.timedelta(days=2)).isoformat(timespec="seconds")})
    assert r.status_code == 200
    transactions = r.json()["transactions"]
    # only 7 of the transactions are before start_day - 2 days
    assert len(transactions) == 7


def test_get_transactions_invalid_from_to_fileter(client, start_day):
    r = client.get("/accounts/ACC-1001/transactions",
                   params={'from': (start_day - datetime.timedelta(days=1)).isoformat(timespec="seconds"),
                           'to': (start_day - datetime.timedelta(days=2)).isoformat(timespec="seconds")})
    assert r.status_code == 422


def test_get_transactions_from_to_filter(client, start_day):
    r = client.get("/accounts/ACC-1001/transactions",
                   params={'from': (start_day - datetime.timedelta(days=4)).isoformat(timespec="seconds"),
                           'to': (start_day - datetime.timedelta(days=2)).isoformat(timespec="seconds")})
    assert r.status_code == 200
    transactions = r.json()["transactions"]
    # only 3 of the transactions are within the given range
    assert len(transactions) == 3


def test_get_transactions_with_invalid_limit(client):
    r = client.get("/accounts/ACC-1001/transactions", params={'limit': 101})
    assert r.status_code == 422


def test_get_transactions_with_limit(client):
    r = client.get("/accounts/ACC-1001/transactions", params={'limit': 1})
    assert r.status_code == 200
    transactions = r.json()["transactions"]
    assert len(transactions) == 1
    assert r.json()['next_cursor'] is not None


def test_get_transactions_with_invalid_cursor(client):
    r = client.get("/accounts/ACC-1001/transactions", params={'cursor': 'INVALID_CURSOR'})
    assert r.status_code == 400


def test_get_transactions_with_cursor(client):
    r = client.get("/accounts/ACC-1001/transactions", params={'limit': 1})
    assert r.status_code == 200
    transactions = r.json()["transactions"]
    assert len(transactions) == 1
    next_cursor = r.json()['next_cursor']

    r = client.get("/accounts/ACC-1001/transactions", params={'cursor': next_cursor})
    assert r.status_code == 200
    transactions = r.json()["transactions"]
    assert len(transactions) == 8
