"""Standard-library data tests only; these do not exercise the provider."""
import base64
import binascii
import hashlib
import json
import unittest
import probe


class EncodingTests(unittest.TestCase):
    def test_canonical_is_stable_across_key_order(self):
        a = probe.canonical({"b": 2, "a": True})
        b = probe.canonical({"a": True, "b": 2})
        self.assertEqual(a, b)
        self.assertTrue(a.endswith(b"\n"))

    def test_boolean_and_number_are_distinct(self):
        self.assertNotEqual(probe.canonical({"x": True}), probe.canonical({"x": 1}))

    def test_nonfinite_is_rejected(self):
        with self.assertRaises(ValueError):
            probe.canonical({"x": float("nan")})

    def test_git_blob_identity_is_content_bound(self):
        raw = probe.canonical({"schema": 1, "operation_id": "fixture-0000000001"})
        first = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        changed = raw.replace(b"0001", b"0002")
        second = hashlib.sha1(b"blob " + str(len(changed)).encode() + b"\0" + changed).hexdigest()
        self.assertNotEqual(first, second)

    def test_canonical_roundtrip(self):
        value = {"한글": "response-loss", "items": [True, 1, None]}
        self.assertEqual(json.loads(probe.canonical(value)), value)

    def test_github_wrapped_base64(self):
        raw = b"provider-state\nwith exact bytes\n"
        encoded = base64.b64encode(raw).decode("ascii")
        wrapped = encoded[:12] + "\n" + encoded[12:24] + "\r\n" + encoded[24:]
        self.assertEqual(probe.decode_github_content(wrapped), raw)

    def test_invalid_base64_still_rejected(self):
        with self.assertRaises(binascii.Error):
            probe.decode_github_content("YWJj$GVm")


if __name__ == "__main__":
    unittest.main()
