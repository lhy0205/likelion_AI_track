import torch

from data import get_batch, load_data
from gpt import GPT

BLOCK_SIZE = 64
BATCH_SIZE = 32
MAX_STEPS = 500
EVAL_EVERY = 50
LEARNING_RATE = 1e-3


@torch.no_grad()
def estimate_loss(model, train_data, val_data, iters=20):
    model.eval()
    out = {}
    for name, data in [("train", train_data), ("val", val_data)]:
        losses = torch.zeros(iters)
        for i in range(iters):
            x, y = get_batch(data, BLOCK_SIZE, BATCH_SIZE)
            _, loss = model(x, y)
            losses[i] = loss.item()
        out[name] = losses.mean().item()
    model.train()
    return out


def main():
    torch.manual_seed(0)
    tok, train_data, val_data = load_data()
    model = GPT(vocab_size=tok.vocab_size, block_size=BLOCK_SIZE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)

    print(f"vocab_size={tok.vocab_size}, params={sum(p.numel() for p in model.parameters()):,}")
    print(f"{'step':>6} {'train':>8} {'val':>8}")

    for step in range(MAX_STEPS + 1):
        if step % EVAL_EVERY == 0:
            losses = estimate_loss(model, train_data, val_data)
            print(f"{step:>6} {losses['train']:>8.4f} {losses['val']:>8.4f}")

        x, y = get_batch(train_data, BLOCK_SIZE, BATCH_SIZE)
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

    print("\n--- 생성 결과 ---")
    start = torch.tensor([tok.encode("the cat ")], dtype=torch.long)
    out = model.generate(start, max_new_tokens=120)
    print(tok.decode(out[0].tolist()))


if __name__ == "__main__":
    main()
