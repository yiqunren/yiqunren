"""FR-2 回合狀態與事件的離線驗收；只使用臨時目錄。"""
from pathlib import Path
import tempfile
import unittest
import uuid

from app.storage import db, requests, turns


class TurnStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='yiqunren-turns-test-')
        self.addCleanup(self.temporary.cleanup)
        self.path = db.prepare(Path(self.temporary.name) / 'state')
        self.connection = db.connect(self.path)
        self.addCleanup(self.connection.close)
        self.conversation = str(uuid.uuid4())

    def start(self, conversation=None):
        turn_id = str(uuid.uuid4())
        conversation = conversation or self.conversation
        result = requests.claim(self.connection, turn_id, 'private_turn', {'c': conversation, 't': turn_id},
                                on_claim=lambda c, now: turns.insert_running(c, turn_id, conversation, 'm1', now))
        self.assertEqual(result.outcome, requests.CLAIMED)
        return turn_id

    def test_progress_then_finish_writes_ordered_events(self):
        turn_id = self.start()
        self.assertEqual(turns.append_progress(self.connection, turn_id, {'step': 1}, 1.0), 1)
        self.assertEqual(turns.append_progress(self.connection, turn_id, {'step': 2}, 2.0), 2)
        self.assertTrue(turns.finish(self.connection, turn_id, turns.COMPLETED, 3.0, reply='ok'))
        self.assertEqual(turns.events_after(self.connection, turn_id, 0),
                         [(1, 'progress', {'step': 1}), (2, 'progress', {'step': 2}),
                          (3, 'done', {'state': 'completed', 'error_kind': None})])
        self.assertEqual(turns.events_after(self.connection, turn_id, 2)[0][0], 3)
        row = turns.get(self.connection, turn_id)
        self.assertEqual((row['state'], row['reply'], row['finished']), ('completed', 'ok', 3.0))

    def test_finished_turn_is_not_changed_again(self):
        turn_id = self.start()
        self.assertTrue(turns.finish(self.connection, turn_id, turns.FAILED, 1.0, error_kind=turns.INTERNAL_ERROR))
        self.assertFalse(turns.finish(self.connection, turn_id, turns.COMPLETED, 2.0, reply='late'))
        self.assertIsNone(turns.append_progress(self.connection, turn_id, {'step': 9}, 3.0))
        self.assertEqual(turns.get(self.connection, turn_id)['state'], 'failed')
        self.assertEqual(len(turns.events_after(self.connection, turn_id, 0)), 1)

    def test_finish_rejects_inconsistent_outcomes(self):
        turn_id = self.start()
        for state, kwargs in ((turns.RUNNING, {}), (turns.COMPLETED, {}), (turns.FAILED, {}),
                              (turns.FAILED, {'error_kind': 'raw message'}),
                              (turns.UNKNOWN, {'reply': 'x'}), (turns.COMPLETED, {'reply': 'x', 'error_kind': turns.INTERNAL_ERROR})):
            with self.subTest(state=state, kwargs=kwargs), self.assertRaises(ValueError):
                turns.finish(self.connection, turn_id, state, 1.0, **kwargs)
        self.assertEqual(turns.get(self.connection, turn_id)['state'], 'running')

    def test_one_running_turn_per_conversation(self):
        first = self.start()
        blocked_id = str(uuid.uuid4())
        with self.assertRaises(turns.ConversationBusy):
            requests.claim(self.connection, blocked_id, 'private_turn', {'x': 1},
                           on_claim=lambda c, now: turns.insert_running(c, blocked_id, self.conversation, 'm1', now))
        # 被擋下時請求登記一起撤銷，同一個 ID 之後還能重送。
        self.assertIsNone(self.connection.execute('SELECT 1 FROM requests WHERE id = ?', (blocked_id,)).fetchone())
        self.start(conversation=str(uuid.uuid4()))  # 其他對話不受影響
        turns.finish(self.connection, first, turns.COMPLETED, 1.0, reply='ok')
        self.start()  # 上一個結束後可以開新回合

    def test_database_index_also_blocks_a_second_running_turn(self):
        self.start()
        other = str(uuid.uuid4())
        self.connection.execute("INSERT INTO requests VALUES (?, 'private_turn', 'h', 'claimed', 1, 1, NULL)", (other,))
        with self.assertRaises(Exception):
            self.connection.execute("INSERT INTO turns (id, conversation_id, member, state, started)"
                                    " VALUES (?, ?, 'm1', 'running', 1)", (other, self.conversation))

    def test_restart_marks_running_turns_unknown(self):
        running, finished = self.start(), self.start(conversation=str(uuid.uuid4()))
        turns.finish(self.connection, finished, turns.COMPLETED, 1.0, reply='ok')
        self.assertEqual(turns.mark_running_unknown(self.connection, 5.0), [running])
        self.assertEqual(turns.get(self.connection, running)['state'], 'unknown')
        self.assertEqual(turns.events_after(self.connection, running, 0)[-1],
                         (1, 'done', {'state': 'unknown', 'error_kind': None}))
        self.assertEqual(turns.get(self.connection, finished)['state'], 'completed')


if __name__ == '__main__':
    unittest.main()
