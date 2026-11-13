"""NFR-1 請求登記的離線驗收：冪等、內容不符拒絕、多程序只有一個取得執行權。"""
import multiprocessing
from pathlib import Path
import tempfile
import unittest
import uuid

from app.storage import db
from app.storage.requests import CLAIMED, EXISTING, REJECTED, claim


def race(path, request_id, payload, start, results):
    start.wait(5)
    connection = db.connect(Path(path))
    try:
        results.put((payload['text'], claim(connection, request_id, 'private_turn', payload).outcome))
    finally:
        connection.close()


class RequestClaimTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-requests-test-')
        self.addCleanup(self.temporary.cleanup)
        self.path = db.prepare(Path(self.temporary.name) / 'state')
        self.connection = db.connect(self.path)
        self.addCleanup(self.connection.close)
        self.id = str(uuid.uuid4())

    def test_first_claim_then_resend_then_changed_payload(self):
        payload = {'member': 'm1', 'text': 'hello'}
        self.assertEqual(claim(self.connection, self.id, 'private_turn', payload).outcome, CLAIMED)
        again = claim(self.connection, self.id, 'private_turn', dict(reversed(list(payload.items()))))
        self.assertEqual((again.outcome, again.state), (EXISTING, CLAIMED))
        self.assertEqual(claim(self.connection, self.id, 'private_turn', {**payload, 'text': 'changed'}).outcome,
                         REJECTED)
        self.assertEqual(claim(self.connection, self.id, 'other_kind', payload).outcome, REJECTED)

    def test_resend_returns_stored_result(self):
        claim(self.connection, self.id, 'private_turn', {'text': 'a'})
        self.connection.execute("UPDATE requests SET state='done', result='r' WHERE id=?", (self.id,))
        again = claim(self.connection, self.id, 'private_turn', {'text': 'a'})
        self.assertEqual((again.outcome, again.state, again.result), (EXISTING, 'done', 'r'))

    def test_only_hash_is_stored(self):
        claim(self.connection, self.id, 'private_turn', {'text': 'secret-looking prompt'})
        row = self.connection.execute('SELECT * FROM requests').fetchone()
        self.assertNotIn('secret-looking prompt', ' '.join(str(value) for value in tuple(row)))

    def test_on_claim_runs_in_the_same_transaction(self):
        seen = []
        claim(self.connection, self.id, 'private_turn', {'text': 'a'},
              on_claim=lambda connection, now: seen.append(connection.in_transaction))
        self.assertEqual(seen, [True])
        claim(self.connection, self.id, 'private_turn', {'text': 'a'}, on_claim=lambda c, now: seen.append('again'))
        self.assertEqual(seen, [True])  # 重送不再呼叫

    def test_on_claim_failure_rolls_back_the_claim(self):
        def refuse(connection, now):
            raise LookupError('busy')
        with self.assertRaises(LookupError):
            claim(self.connection, self.id, 'private_turn', {'text': 'a'}, on_claim=refuse)
        self.assertFalse(self.connection.in_transaction)
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM requests').fetchone()[0], 0)
        self.assertEqual(claim(self.connection, self.id, 'private_turn', {'text': 'a'}).outcome, CLAIMED)

    def test_invalid_input_is_rejected_without_writing(self):
        for request_id, kind in (('not-a-uuid', 'private_turn'), (self.id.upper(), 'private_turn'),
                                 (None, 'private_turn'), (self.id, ''), (self.id, None)):
            with self.subTest(request_id=request_id, kind=kind), self.assertRaises(ValueError):
                claim(self.connection, request_id, kind, {'text': 'a'})
        self.assertEqual(self.connection.execute('SELECT COUNT(*) FROM requests').fetchone()[0], 0)

    def test_concurrent_claims_give_one_winner(self):
        context = multiprocessing.get_context('spawn')
        start, results = context.Event(), context.Queue()
        payloads = [{'text': 'A'}, {'text': 'B'}] * 4
        workers = [context.Process(target=race, args=(str(self.path), self.id, p, start, results))
                   for p in payloads]
        for worker in workers:
            worker.start()
        start.set()
        outcomes = [results.get(timeout=30) for _ in workers]
        for worker in workers:
            worker.join(10)
        winners = [text for text, outcome in outcomes if outcome == CLAIMED]
        self.assertEqual(len(winners), 1, outcomes)
        for text, outcome in outcomes:
            if outcome != CLAIMED:
                self.assertEqual(outcome, EXISTING if text == winners[0] else REJECTED, outcomes)


if __name__ == '__main__':
    unittest.main()
