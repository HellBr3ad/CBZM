"""Run Lab 2 demonstrations and record the raw measurements."""

import json
import platform
from copy import deepcopy
from pathlib import Path
from statistics import mean
from time import perf_counter

from blockchain import Blockchain


def demonstrate_mining():
    chain = Blockchain()
    first = chain.mine("Alice")  # Fund Alice before accepting a transfer.
    assert chain.new_transaction("Alice", "Bob", 0.75) == 3
    second = chain.mine("miner-1")
    assert chain.new_transaction("Bob", "Carol", 0.25) == 4
    assert chain.new_transaction("Alice", "Dave", 0.25) == 4
    third = chain.mine("miner-1")
    print("2.1 | Wydobycie i pełny łańcuch")
    print(json.dumps(chain.chain, indent=2, ensure_ascii=False))
    for block in (first, second, third):
        digest = chain.hash(block)
        assert digest.startswith("0000")
        print(f"Blok {block['index']} | nonce={block['nonce']} | SHA-256 {digest}")
    assert not chain.current_transactions and chain.valid_chain(chain.chain)
    print("Poprawny łańcuch:", chain.valid_chain(chain.chain))


def benchmark():
    print("\n2.2 | Pomiary wydobycia")
    measurements = []
    for difficulty in range(1, 7):
        chain = Blockchain(difficulty)
        trials = []
        for _ in range(1 if difficulty == 6 else 5):
            start = perf_counter()
            block = chain.mine("benchmark")
            duration = perf_counter() - start
            digest = chain.hash(block)
            assert digest.startswith("0" * difficulty)
            trials.append({"nonce": block["nonce"], "seconds": duration, "hash": digest})
        assert chain.valid_chain(chain.chain)
        average_nonce = mean(trial["nonce"] for trial in trials)
        average_time = mean(trial["seconds"] for trial in trials)
        print(f"d={difficulty} | n={len(trials)} | 16^d={16**difficulty:>8} | "
              f"śr. nonce={average_nonce:>12.1f} | śr. czas={average_time:.6f} s",
              flush=True)
        measurements.append({"difficulty": difficulty, "trials": trials})
    return measurements


def remine_suffix(blockchain, chain, start_position):
    """Rebuild commitments and PoW for the changed suffix of this local chain."""
    for position in range(start_position, len(chain)):
        block = chain[position]
        block["previous_hash"] = blockchain.hash(chain[position - 1])
        block["merkle_root"] = blockchain.merkle_root(block["transactions"])
        digest = blockchain.proof_of_work(block)
        assert digest == blockchain.hash(block)


def demonstrate_integrity():
    print("\n2.3 | Spójność łańcucha")
    results = []
    for difficulty in (4, 5):
        chain = Blockchain(difficulty)
        chain.mine("Alice")
        for recipient in ("Bob", "Carol", "Dave"):
            chain.new_transaction("Alice", recipient, 0.25)
            chain.mine("miner-1")
        assert len(chain.chain) == 5
        initial = chain.valid_chain(chain.chain)
        modified = deepcopy(chain.chain)
        modified[1]["transactions"][0]["amount"] = 2
        changed = chain.valid_chain(modified)
        start = perf_counter()
        remine_suffix(chain, modified, 1)
        duration = perf_counter() - start
        rebuilt = chain.valid_chain(modified)
        assert initial and not changed and rebuilt and chain.valid_chain(chain.chain)
        assert modified[1]["transactions"][0]["amount"] == 2
        attempts = sum(block["nonce"] + 1 for block in modified[1:])
        print(f"d={difficulty} | oryginał={initial} | po zmianie={changed} | "
              f"po wydobyciu={rebuilt} | próby={attempts} | czas={duration:.6f} s",
              flush=True)
        results.append({"difficulty": difficulty, "attempts": attempts,
                        "seconds": duration, "blocks": len(modified) - 1})
    return results


def demonstrate_transactions():
    print("\n2.4 | Walidacja transakcji i saldo")
    chain = Blockchain(1)
    chain.mine("Alice")
    cases = [
        ("Pusty adres", (" ", "Bob", 0.5)),
        ("Adres spoza typu str", ("Alice", None, 0.5)),
        ("Ten sam adres", ("Alice", " Alice ", 0.5)),
        ("Kwota ujemna", ("Alice", "Bob", -1)),
        ("Kwota zero", ("Alice", "Bob", 0)),
        ("Kwota jako napis", ("Alice", "Bob", "1")),
        ("Kwota nieskończona", ("Alice", "Bob", float("inf"))),
        ("Brak środków", ("Bob", "Carol", 0.5)),
    ]
    for label, transaction in cases:
        check_rejection(chain, label, transaction)
    assert chain.new_transaction("Alice", "Bob", 0.75) == 3
    assert str(chain.get_balance("Alice")) == "0.25"
    assert str(chain.get_balance("Bob")) == "0.75"
    print("Po przyjęciu do puli | Alice=0.25 | Bob=0.75")
    check_rejection(chain, "Ponowne wydanie 0.5", ("Alice", "Carol", 0.5))
    mined = chain.mine("miner-1")
    assert not chain.current_transactions and str(chain.get_balance("Bob")) == "0.75"
    assert chain.valid_chain(chain.chain)
    print("Po wydobyciu | pula pusta | Alice=0.25 | Bob=0.75")
    changed = deepcopy(mined["transactions"])
    changed[1]["amount"] = 0.5
    assert chain.merkle_root(changed) != mined["merkle_root"]
    print("\n2.5 | Korzeń Merkle")
    print("Oryginał:", mined["merkle_root"])
    print("Po zmianie:", chain.merkle_root(changed))


def check_rejection(chain, label, transaction):
    previous = list(chain.current_transactions)
    try:
        chain.new_transaction(*transaction)
    except ValueError as error:
        print(f"{label} | ValueError | {error}")
    else:
        raise AssertionError(f"Przyjęto błędną transakcję: {label}")
    assert chain.current_transactions == previous


def main():
    print(f"Python {platform.python_version()} | {platform.system()} "
          f"{platform.release()} | {platform.machine()}\n", flush=True)
    demonstrate_mining()
    measurements = benchmark()
    integrity = demonstrate_integrity()
    demonstrate_transactions()
    Path("pomiary.json").write_text(
        json.dumps({"benchmark": measurements, "integrity": integrity}, indent=2) + "\n",
        encoding="utf-8",
    )
    print("\nWszystkie sprawdzenia zakończone pomyślnie.")


if __name__ == "__main__":
    main()
