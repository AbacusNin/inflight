import hashlib
import json
import os


def _digest(entry: dict, prev: str) -> str:
    payload = json.dumps(entry, sort_keys=True) + prev
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self, path: str):
        self.path = path

    def _last_hash(self) -> str:
        if not os.path.exists(self.path):
            return ""
        last = ""
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)["hash"]
        return last

    def append(self, entry: dict) -> str:
        prev = self._last_hash()
        h = _digest(entry, prev)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"entry": entry, "prev": prev, "hash": h}) + "\n")
        return h

    def verify(self) -> bool:
        prev = ""
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec["prev"] != prev or rec["hash"] != _digest(rec["entry"], prev):
                    return False
                prev = rec["hash"]
        return True
