import pytest
import torch

from data import get_batch, load_data
from gpt import GPT, LayerNorm

VOCAB = 32
BLOCK = 16


def make_model(seed=0):
    torch.manual_seed(seed)
    return GPT(vocab_size=VOCAB, n_embd=32, n_head=4, n_layer=2, block_size=BLOCK)


def attention_weights(model, idx):

    model(idx)
    return model.blocks[0].attn.last_att  # (B, n_head, T, T)


# --- 1 ---------------------------------------------------------------
def test_layernorm_normalizes_each_token():
    """LayerNorm은 토큰마다, feature 축을 따라 정규화한다."""
    ln = LayerNorm(16)
    x = torch.randn(4, 7, 16) * 5.0 + 3.0
    y = ln(x)

    mean = y.mean(dim=-1)
    var = y.var(dim=-1, unbiased=False)
    assert mean.abs().max() < 1e-4, f"토큰별 평균이 0이 아님 (최대 {mean.abs().max():.4f})"
    assert (var - 1).abs().max() < 1e-3, f"토큰별 분산이 1이 아님 (최대 편차 {(var - 1).abs().max():.4f})"


def test_layernorm_is_independent_across_batch():
    """배치에 뭐가 같이 들어오든 각 샘플의 결과는 같아야 한다."""
    ln = LayerNorm(16)
    a = torch.randn(1, 5, 16)
    b = torch.randn(1, 5, 16)

    alone = ln(a)
    together = ln(torch.cat([a, b], dim=0))[:1]
    assert torch.allclose(alone, together, atol=1e-5), \
        "같은 샘플인데 배치 구성에 따라 결과가 달라짐"


# --- 2 ---------------------------------------------------------------
def test_attention_weights_sum_to_one():
    """각 query 위치의 가중치 합은 1이다."""
    model = make_model()
    idx = torch.randint(0, VOCAB, (2, BLOCK))
    att = attention_weights(model, idx)

    sums = att.sum(dim=-1)
    assert torch.allclose(sums, torch.ones_like(sums), atol=1e-5), \
        f"가중치 합이 1이 아님 (최소 {sums.min():.4f}, 최대 {sums.max():.4f})"


# --- 3 ---------------------------------------------------------------
def test_attention_is_causal():
    """t 시점은 t보다 뒤의 토큰을 볼 수 없다. 미래 가중치는 정확히 0이다."""
    model = make_model()
    idx = torch.randint(0, VOCAB, (2, BLOCK))
    att = attention_weights(model, idx)

    future = att.triu(diagonal=1)
    assert future.abs().max() == 0, \
        f"미래 토큰에 가중치가 실림 (최대 {future.abs().max():.4f})"


# --- 4 ---------------------------------------------------------------
def test_positional_embedding_affects_output():
    """위치 임베딩을 바꾸면 출력이 달라져야 한다."""
    model = make_model()
    idx = torch.randint(0, VOCAB, (2, BLOCK))

    before, _ = model(idx)
    with torch.no_grad():
        model.pos_emb.weight.add_(10.0)
    after, _ = model(idx)

    assert not torch.allclose(before, after), \
        "위치 임베딩을 크게 바꿔도 출력이 그대로임"


# --- 5 ---------------------------------------------------------------
def test_targets_are_shifted_by_one():
    """정답은 입력을 한 칸 뒤로 민 것이다."""
    data = torch.arange(200)
    x, y = get_batch(data, block_size=8, batch_size=4)

    assert torch.equal(y[:, :-1], x[:, 1:]), (
        "정답이 한 칸 시프트되지 않음\n"
        f"  입력 첫 행: {x[0].tolist()}\n"
        f"  정답 첫 행: {y[0].tolist()}"
    )


# --- 통합 ------------------------------------------------------------
@pytest.mark.slow
def test_model_actually_learns():
    """위 5개를 다 통과했다면, 500 step에서 loss가 0.5 아래로 내려간다."""
    torch.manual_seed(0)
    tok, train_data, _ = load_data()
    model = GPT(vocab_size=tok.vocab_size, block_size=64)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)

    for _ in range(500):
        x, y = get_batch(train_data, 64, 32)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()

    assert 0.05 < loss.item() < 0.5, (
        f"최종 loss {loss.item():.4f}. "
        "0.5보다 크면 학습을 방해하는 것이 남아있고, "
        "0.05보다 작으면 모델이 너무 쉬운 문제를 풀고 있다."
    )
