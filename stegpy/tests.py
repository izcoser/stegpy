import unittest
import numpy as np

try:
    from .lsb import decode_message
except:
    from lsb import decode_message

with open("test.npy", "rb") as f:
    decode_message_input = np.load(f)
    decode_message_output = np.load(f)


class StegpyTests(unittest.TestCase):
    def test_decode_message(self):
        self.assertTrue(
            np.array_equal(decode_message(decode_message_input), decode_message_output)
        )


if __name__ == "__main__":
    unittest.main()
