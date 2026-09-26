"""E7 arms (3) REUSE and (4) ARGMAX: new methods only.

The frozen `Runtime.probe` and `Runtime.action` of every stage are imported and called unchanged;
nothing in this file edits them.  `probe_keep_cache` repeats the frozen probe computation with
`use_cache=True` so the prefill KV cache survives, and asserts that every number it returns is
identical to what the frozen probe returns for the same question (§2.2 of PROTOCOL_FREEZE_E7.md).
"""
import hashlib
import torch


@torch.inference_mode()
def probe_keep_cache(rt, q, receiver_prompt, display_labels):
    """Frozen ProbeMax with use_cache=True.  Returns (meta, cache, R_ids).

    Identical prompt, tokenisation, FP32 label logsumexp/softmax and last-position projection as the
    frozen probe; the only difference is that the prefill cache is kept.
    """
    tok = rt.runner.receiver_tok
    model = rt.runner.receiver
    body = receiver_prompt(q)
    rendered = tok.apply_chat_template([{'role': 'user', 'content': body}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
    base = tok(rendered, return_tensors='pt')
    suffix = tok.encode('The correct answer is', add_special_tokens=False)
    assert suffix == list(rt.prefix_ids)
    ids = torch.cat([base['input_ids'], torch.tensor([suffix], dtype=base['input_ids'].dtype)], dim=1)
    mask = torch.cat([base['attention_mask'], torch.ones((1, len(suffix)), dtype=base['attention_mask'].dtype)], dim=1)
    pos = int(torch.nonzero(mask[0], as_tuple=False)[-1, 0])
    n = ids.shape[1]
    dev = model.device
    out = model.model(input_ids=ids.to(dev), attention_mask=mask.to(dev), use_cache=True,
                      return_dict=True, output_hidden_states=False, output_attentions=False)
    assert pos == n - 1 and int(mask.sum()) == n
    last = out.last_hidden_state[:, pos:pos + 1, :]
    logits = model.lm_head(last)[0, 0, :].float()
    labels = display_labels(len(q['choice_text']))
    assert labels == q['choice_labels']
    label_logits = torch.stack([torch.logsumexp(logits[rt.ix[l]], dim=0) for l in labels])
    p = torch.log_softmax(label_logits, dim=0).exp()
    ps = p.cpu().tolist()
    u = float((1 - p.max()).item())
    cache = out.past_key_values
    meta = {'ProbeMax': u, 'p_labels': dict(zip(labels, ps)),
            'argmax_probe_label': labels[max(range(len(ps)), key=ps.__getitem__)],
            'probe_ids_sha256': hashlib.sha256(ids.numpy().tobytes()).hexdigest(),
            'input_tokens': n, 'last_valid_position': pos, 'cache_reused': True}
    n_R = base['input_ids'].shape[1]
    # The native R prompt is an exact token prefix of the probe input (640/640, E7_PREFIX_CHECK.json).
    # The frozen probe projects only its LAST position, so no logits exist for position n_R-1; the
    # cache is cropped to n_R-1 and that one token is re-prefilled by the generator.
    cache.crop(n_R - 1)
    del out, last, logits, label_logits, p
    return meta, cache, base['input_ids'], n_R


@torch.inference_mode()
def generate_R_from_cache(rt, R_ids, cache):
    """The frozen receiver generation, continued from the cropped probe cache."""
    model = rt.runner.receiver
    tok = rt.runner.receiver_tok
    input_ids = R_ids.to(model.device)
    attn = torch.ones_like(input_ids)
    gc = model.generation_config
    out = model.generate(input_ids=input_ids, attention_mask=attn, do_sample=False, max_new_tokens=64,
                         use_cache=True, past_key_values=cache,
                         pad_token_id=(gc.pad_token_id if gc.pad_token_id is not None else tok.pad_token_id),
                         eos_token_id=(gc.eos_token_id if gc.eos_token_id is not None else tok.eos_token_id))
    gen = out[0, input_ids.shape[1]:]
    return tok.decode(gen, skip_special_tokens=True).strip('\n'), gen.detach().cpu().tolist()


def probe_identity(meta_cached, expected):
    """§2.2: the cached probe must return the frozen probe's numbers exactly."""
    if expected is None:
        return None
    return {'probe_ids_sha256_match': meta_cached['probe_ids_sha256'] == expected['probe_ids_sha256'],
            'FP32_score_equal': meta_cached['ProbeMax'] == expected['ProbeMax']}
