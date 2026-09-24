1. app/services/ledger_client.py:L17 BLOCKER: it is catching all errors including payload validation 422, malformed
   request 4xx and then retrying with a blocking sleep. Those errors should not be retried as the payload needs to be
   updated. should catch HTTPStatusError and check its status code to determine if it should be retried
2. app/services/ledger_client.py:L30 SHOULD FIX: it is using datetime.now () instead of datetime.now (timezone.utc) like
   everywhere in the codebase
3. app/routes/search.py:L13 SHOULD FIX: it should have some limit on name together with pagination, otherwise a query
   with name=a could take ages and returning an extremely long list.
4. app/routes/search.py:L14 BLOCKER: it is vulnerable to SQL injection as users can pass in anything as the name, fix it
   with LIKE ? ORDER BY client_name, (f'%{name}%',)
5. app/routes/serach.py:L18 BLOCKER: it should not just silently return empty result. The error should at least be
   logged for debugging
6. app/routes/search.py SHOULD FIX: there is no test for this new route, 
6. app/routes/transfers.py:L45 BLOCKER: there is no protection against post_transfer, and it is after conn.commit (), so
   there will be a discrepancy between the ledger and our database if it fails. There should be protected by try-catch
   and have some mechanism to reconcile it such as having a db column in transfer as the ledger status and set it to
   pending before the external post_transfer call. Then another reconciliation app can be set up to reconcile those
   failure in post_transfer

Request Changes