import numpy as np

def normalized(values):
    values = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(values, axis=-1, keepdims=True)
    if not np.isfinite(values).all() or np.any(norms <= 1e-12):
        raise ValueError("descriptor contains a non-finite value or has zero length")
    return values / norms

def weighted_pool_many(head, hidden, weights):
    """Pool one token sequence for several weight profiles without another vision pass."""
    import torch
    from torch.nn import functional as F
    if hidden.shape[0] != 1 or weights.ndim != 2 or weights.shape[1] != hidden.shape[1]:
        raise ValueError("one token sequence and a profile-by-token matrix are required")
    if not torch.isfinite(weights).all() or torch.any(weights < 0) or torch.any(weights.sum(-1) <= 0):
        raise ValueError("patch weights MUST be finite, nonnegative, and have a positive sum")
    attention = head.attention
    dimension, heads = hidden.shape[-1], head.num_heads
    if attention.kdim != dimension or attention.vdim != dimension or attention.add_zero_attn or attention.bias_k is not None:
        raise ValueError("unsupported pooling attention configuration")
    q_weight, k_weight, v_weight = attention.in_proj_weight.chunk(3)
    if attention.in_proj_bias is None:
        q_bias = k_bias = v_bias = None
    else:
        q_bias, k_bias, v_bias = attention.in_proj_bias.chunk(3)
    depth = dimension // heads
    query = F.linear(head.probe, q_weight, q_bias).reshape(1, 1, heads, depth).transpose(1, 2)
    key = F.linear(hidden, k_weight, k_bias).reshape(1, -1, heads, depth).transpose(1, 2)
    value = F.linear(hidden, v_weight, v_bias).reshape(1, -1, heads, depth).transpose(1, 2)
    logits = query @ key.transpose(-2, -1) / depth ** 0.5
    weights = weights.to(hidden)
    bias = weights.clamp_min(torch.finfo(hidden.dtype).tiny).log().masked_fill(weights == 0, float("-inf"))
    probabilities = (logits + bias[:, None, None, :]).softmax(-1)
    pooled = (probabilities @ value).transpose(1, 2).reshape(len(weights), 1, dimension)
    pooled = F.linear(pooled, attention.out_proj.weight, attention.out_proj.bias)
    return (pooled + head.mlp(head.layernorm(pooled)))[:, 0]
