import hashlib
import json
from time import time


class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_genesis_block()

    def create_genesis_block(self):
        self.chain.append({
            "index": 1,
            "timestamp": 0,
            "transactions": [],
            "nonce": 0,
            "previous_hash": "0" * 64,
        })

    @staticmethod
    def hash(block, *, sort_keys=True):
        block_string = json.dumps(block, sort_keys=sort_keys).encode("utf-8")
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, transactions):
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "transactions": list(transactions),
            "nonce": 0,
            "previous_hash": self.hash(self.last_block),
        }
        self.chain.append(block)
        return block

    def is_chain_valid(self):
        """Return the validation result and the number of the first broken link."""
        for index in range(1, len(self.chain)):
            previous = self.chain[index - 1]
            current = self.chain[index]
            if current["previous_hash"] != self.hash(previous):
                return False, index + 1
        return True, None


def main():
    bc = Blockchain()
    bc.add_block(["Alice -> Bob: 5"])
    bc.add_block(["Bob -> Carol: 2"])
    bc.add_block(["Carol -> Dave: 1"])

    print("=== Lancuch i skroty blokow ===")
    for block in bc.chain:
        print(json.dumps(block, indent=2, ensure_ascii=False))
        print("SHA-256:", bc.hash(block))

    print("\n=== Sprawdzenie powiazan ===")
    for previous, current in zip(bc.chain, bc.chain[1:]):
        matches = current["previous_hash"] == bc.hash(previous)
        print(f"Blok {current['index']} wskazuje na {previous['index']}: {matches}")

    print("\n=== Eksperyment z kolejnoscia pol ===")
    original = bc.chain[1]
    reordered = dict(reversed(list(original.items())))
    for sort_keys in (True, False):
        original_hash = bc.hash(original, sort_keys=sort_keys)
        reordered_hash = bc.hash(reordered, sort_keys=sort_keys)
        print(f"sort_keys={sort_keys}")
        print("  Kolejnosc oryginalna:", original_hash)
        print("  Kolejnosc odwrocona: ", reordered_hash)
        print("  Jednakowe skroty:    ", original_hash == reordered_hash)

    print("\n=== Weryfikacja integralnosci ===")
    print("Oryginalny lancuch:     ", bc.is_chain_valid())
    bc.chain[1]["transactions"][0] = "Alice -> Bob: 500"
    print("Po zmianie bloku 2:     ", bc.is_chain_valid())

    for index in range(2, len(bc.chain)):
        bc.chain[index]["previous_hash"] = bc.hash(bc.chain[index - 1])
    print("Po przeliczeniu linkow:", bc.is_chain_valid())

    old_hash = bc.hash(bc.last_block)
    bc.last_block["transactions"][0] = "Carol -> Dave: 100"
    print("Po zmianie bloku 4:     ", bc.is_chain_valid())
    print("Skrot bloku 4 zmienil sie:", old_hash != bc.hash(bc.last_block))


if __name__ == "__main__":
    main()

