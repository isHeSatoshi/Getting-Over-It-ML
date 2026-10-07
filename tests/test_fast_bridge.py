import json
import threading
import unittest
from research.fast_bridge import FastBridge
from research.fast_fidelity import compare, NUMERIC, DISCRETE


class Connection:
    def __init__(self, reply):
        self.reply = reply
        self.sent = []

    def send(self, data):
        self.sent.append(json.loads(data))

    def recv(self, timeout):
        return json.dumps(self.reply)


def bridge(reply):
    b = object.__new__(FastBridge)
    b._rpc_ready = True
    b._connection = Connection(reply)
    b._rpc_lock = threading.Lock()
    b._request_id = 0
    return b


class FastProtocol(unittest.TestCase):
    def test_valid_response_and_command(self):
        b = bridge({"id": 1, "value": [1, 2]})
        self.assertEqual(b._rpc("step", commands=[]), [1, 2])
        self.assertEqual(b._connection.sent[0], {"id": 1, "method": "step", "commands": []})

    def test_out_of_order_and_remote_errors_fail(self):
        with self.assertRaisesRegex(RuntimeError, "Out-of-order"):
            bridge({"id": 2, "value": []})._rpc("state")
        with self.assertRaisesRegex(RuntimeError, "physics error"):
            bridge({"id": 1, "error": "physics error"})._rpc("state")

    def test_disconnected_worker_fails(self):
        b = bridge({})
        b._rpc_ready = False
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            b._rpc("state")

    def test_fidelity_rejects_nan_and_different_lengths(self):
        state = {key: 0 for key in NUMERIC + DISCRETE}
        with self.assertRaisesRegex(AssertionError, "Non-finite"):
            compare([state], [{**state, "player_world_x": float("nan")}])
        with self.assertRaisesRegex(AssertionError, "lengths"):
            compare([state], [])

    def test_exact_fidelity_accepts_and_rejects_contact(self):
        state = {key: 0 for key in NUMERIC + DISCRETE}
        self.assertEqual(max(compare([state], [state]).values()), 0)
        with self.assertRaisesRegex(AssertionError, "Discrete mismatch"):
            compare([state], [{**state, "body_collision": True}])


if __name__ == "__main__":
    unittest.main()
