"""A single-node blockchain prototype for Lab 2."""

import hashlib
import json
import math
from decimal import Decimal
from time import time


class Blockchain:
    def __init__(self, difficulty=4):
        if type(difficulty) is not int or not 1 <= difficulty <= 64:
            raise ValueError("Trudność musi być liczbą całkowitą od 1 do 64.")
        self.chain = [self.create_genesis_block()]
        self.current_transactions = []
        self.difficulty = difficulty

    @staticmethod
    def create_genesis_block():
        return {
            "index": 1,
            "timestamp": 0,
            "transactions": [],
            "nonce": 0,
            "previous_hash": "0" * 64,
        }

    @staticmethod
    def serialize(value):
        return json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")

    @staticmethod
    def hash(block):
        return hashlib.sha256(Blockchain.serialize(block)).hexdigest()

    @staticmethod
    def merkle_root(transactions):
        if not transactions:
            return hashlib.sha256(b"").hexdigest()
        level = [
            hashlib.sha256(Blockchain.serialize(transaction)).digest()
            for transaction in transactions
        ]
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [
                hashlib.sha256(level[i] + level[i + 1]).digest()
                for i in range(0, len(level), 2)
            ]
        return level[0].hex()

    @property
    def last_block(self):
        return self.chain[-1]

    def get_balance(self, address):
        balance = Decimal(0)
        confirmed = (tx for block in self.chain for tx in block["transactions"])
        for transactions in (confirmed, self.current_transactions):
            for tx in transactions:
                amount = Decimal(str(tx["amount"]))
                if tx["sender"] == address:
                    balance -= amount
                if tx["recipient"] == address:
                    balance += amount
        return balance

    def new_transaction(self, sender, recipient, amount):
        if not all(isinstance(address, str) and address.strip()
                   for address in (sender, recipient)):
            raise ValueError("Adresy muszą być niepustymi napisami.")
        sender, recipient = sender.strip(), recipient.strip()
        if sender == recipient:
            raise ValueError("Nadawca i odbiorca muszą się różnić.")
        if "0" in (sender, recipient):
            raise ValueError("Adres 0 jest zarezerwowany dla coinbase.")
        if type(amount) not in (int, float) or (
            isinstance(amount, float) and not math.isfinite(amount)
        ) or amount <= 0:
            raise ValueError("Kwota musi być dodatnią, skończoną liczbą.")
        if self.get_balance(sender) < Decimal(str(amount)):
            raise ValueError("Niewystarczające środki nadawcy.")
        self.current_transactions.append({
            "sender": sender, "recipient": recipient, "amount": amount,
        })
        return self.last_block["index"] + 1

    def proof_of_work(self, block):
        block["nonce"] = 0
        # Only nonce changes. Reuse the SHA-256 state of the JSON prefix.
        prefix, suffix = self.serialize(block).split(b'"nonce": 0', 1)
        initial_hash = hashlib.sha256(prefix + b'"nonce": ')
        target = "0" * self.difficulty
        nonce = 0
        while True:
            candidate = initial_hash.copy()
            candidate.update(str(nonce).encode("ascii") + suffix)
            digest = candidate.hexdigest()
            if digest.startswith(target):
                block["nonce"] = nonce
                return digest
            nonce += 1

    def mine(self, miner_address):
        if not isinstance(miner_address, str) or miner_address.strip() in ("", "0"):
            raise ValueError("Niepoprawny adres górnika.")
        reward = {"sender": "0", "recipient": miner_address.strip(), "amount": 1}
        transactions = [reward] + self.current_transactions
        block = {
            "index": self.last_block["index"] + 1,
            "timestamp": time(),
            "transactions": transactions,
            "nonce": 0,
            "previous_hash": self.hash(self.last_block),
            "merkle_root": self.merkle_root(transactions),
        }
        self.proof_of_work(block)
        self.chain.append(block)
        self.current_transactions.clear()
        return block

    def valid_chain(self, chain):
        if not chain or chain[0] != self.create_genesis_block():
            return False
        previous_hash = self.hash(chain[0])
        target = "0" * self.difficulty
        for index, block in enumerate(chain[1:], 2):
            try:
                if (block["index"] != index
                    or block["previous_hash"] != previous_hash
                    or block["merkle_root"] != self.merkle_root(block["transactions"])):
                    return False
                previous_hash = self.hash(block)
                if not previous_hash.startswith(target):
                    return False
            except (KeyError, TypeError, ValueError):
                return False
        return True
