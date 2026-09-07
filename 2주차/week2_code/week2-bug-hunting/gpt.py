import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class LayerNorm(nn.Module):
    """LayerNorm 직접 구현."""

    def __init__(self, n_embd, eps=1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(n_embd))
        self.bias = nn.Parameter(torch.zeros(n_embd))
        self.eps = eps

    def forward(self, x):
        # x: (B, T, C)
       
        #차원(Dimension) 축 지정:함수가 실행될 방향이나 기준이 되는 축을 의미합니다.
        #dim=0: 첫 번째 차원(행, 세로 방향)을 뜻합니다.
        #dim=1: 두 번째 차원(열, 가로 방향)을 뜻합니다.
        #dim=-1: 가장 마지막 차원을 뜻합니다/ 차원의 개수를 몰라도 코드 재사용 가능

        #1

        mean = x.mean(dim=-1, keepdim=True)
        var = x.var(dim=-1, keepdim=True, unbiased=False)

        x_hat = (x - mean) / torch.sqrt(var + self.eps)
        return self.weight * x_hat + self.bias


class CausalSelfAttention(nn.Module):
    def __init__(self, n_embd, n_head, block_size):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head = n_head
        self.n_embd = n_embd
        self.qkv = nn.Linear(n_embd, 3 * n_embd, bias=False)
        self.proj = nn.Linear(n_embd, n_embd, bias=False)
        self.register_buffer(
            "mask",
            torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size),
        )
        self.last_att = None 

    def forward(self, x):
        B, T, C = x.shape
        head_size = C // self.n_head

        q, k, v = self.qkv(x).split(self.n_embd, dim=2)
        q = q.view(B, T, self.n_head, head_size).transpose(1, 2)  # (B, nh, T, hs)
        k = k.view(B, T, self.n_head, head_size).transpose(1, 2)
        v = v.view(B, T, self.n_head, head_size).transpose(1, 2)

        att = (q @ k.transpose(-2, -1)) / math.sqrt(head_size)  # (B, nh, T, T)
        att = att.masked_fill(self.mask[:, :, :T, :T] == 0, 0.0)

        #2
        #차원 변경
        att = F.softmax(att, dim=-1)
        self.last_att = att

        y = att @ v                                   # (B, nh, T, hs)
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.proj(y)


class Block(nn.Module):
    def __init__(self, n_embd, n_head, block_size):
        super().__init__()
        self.ln1 = LayerNorm(n_embd)
        self.attn = CausalSelfAttention(n_embd, n_head, block_size)
        self.ln2 = LayerNorm(n_embd)
        self.mlp = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd),
            nn.GELU(),
            nn.Linear(4 * n_embd, n_embd),
        )

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class GPT(nn.Module):
    def __init__(self, vocab_size, n_embd=64, n_head=4, n_layer=2, block_size=64):
        super().__init__()
        self.block_size = block_size
        self.tok_emb = nn.Embedding(vocab_size, n_embd)
        self.pos_emb = nn.Embedding(block_size, n_embd)
        self.blocks = nn.ModuleList(
            [Block(n_embd, n_head, block_size) for _ in range(n_layer)]
        )
        self.ln_f = LayerNorm(n_embd)
        self.head = nn.Linear(n_embd, vocab_size, bias=False)

    def forward(self, idx, targets=None):
        B, T = idx.shape
        assert T <= self.block_size, f"시퀀스 길이 {T}가 block_size {self.block_size}를 넘음"

        pos = torch.arange(T, device=idx.device)
        tok_emb = self.tok_emb(idx)      # (B, T, C)
        pos_emb = self.pos_emb(pos)      # (T, C)
        
        #pos_emb 를 만들긴 했는데, 어디에다가 쓰는걸까?

        x = tok_emb
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.head(x)            # (B, T, vocab_size)

        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.reshape(-1)
            )
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens, temperature=1.0):
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_id], dim=1)
        return idx
