import random

import torch

SUBJECTS = ["the cat", "the dog", "a bird", "my friend", "the robot"]
VERBS = ["sat on", "ran to", "looked at", "jumped over", "found"]
OBJECTS = ["the mat", "the park", "a box", "the river", "my desk"]


def build_corpus(n_sentences=4000, seed=1234):
    rng = random.Random(seed)
    parts = []
    for _ in range(n_sentences):
        s = rng.choice(SUBJECTS)
        v = rng.choice(VERBS)
        o = rng.choice(OBJECTS)
        parts.append(f"{s} {v} {o} .\n")
    return "".join(parts)


class CharTokenizer:
    def __init__(self, text):
        self.chars = sorted(set(text))
        self.stoi = {c: i for i, c in enumerate(self.chars)}
        self.itos = {i: c for c, i in self.stoi.items()}

    @property
    def vocab_size(self):
        return len(self.chars)

    def encode(self, s):
        return [self.stoi[c] for c in s]

    def decode(self, ids):
        return "".join(self.itos[int(i)] for i in ids)


def load_data(seed=1234):
    text = build_corpus(seed=seed)
    tok = CharTokenizer(text)
    ids = torch.tensor(tok.encode(text), dtype=torch.long)
    n = int(0.9 * len(ids))
    return tok, ids[:n], ids[n:]


def get_batch(data, block_size, batch_size, generator=None):

    ix = torch.randint(
        len(data) - block_size - 1, (batch_size,), generator=generator
    )
    x = torch.stack([data[i : i + block_size] for i in ix])
   
    # y가 정답 한 칸 시프트 5번 
    y = torch.stack([data[i + 1 : i + 1 + block_size] for i in ix]) 
    return x, y
