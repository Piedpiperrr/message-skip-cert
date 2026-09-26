"""P2-2 runtime copy, extended only for full-vector AC(W) replacement."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

from protocol_min import apply_generation_config, extract_answer_from_content, generate_receiver, receiver_prompt_tensors

ROOT = Path(__file__).resolve().parent


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def synchronize():
    torch.cuda.synchronize(0)
    torch.cuda.synchronize(1)


class StopHelper(Exception):
    pass


@torch.inference_mode()
def helper_vector(model, tensors, full=False):
    """Capture the block output BEFORE final norm, stop after 20 blocks."""
    state = {'target_calls': 0, 'block21_calls': 0, 'full_forward': full}
    vector = None

    def capture(module, args, output):
        nonlocal vector
        state['target_calls'] += 1
        h = output[0]
        assert h.shape == (1, tensors['input_ids'].shape[1], model.config.hidden_size)
        vector = h[:, -1, :].detach().clone()
        assert torch.isfinite(vector).all().item()
        if not full:
            raise StopHelper()

    def next_block(module, args):
        state['block21_calls'] += 1

    hooks = [model.model.layers[19].register_forward_hook(capture),
             model.model.layers[20].register_forward_pre_hook(next_block)]
    try:
        try:
            # Full reference includes all blocks, final norm and LM head;
            # production exits at block 19 and executes none of those later ops.
            model(**tensors, use_cache=False, return_dict=True, logits_to_keep=1)
        except StopHelper:
            assert not full
    finally:
        for hook in hooks:
            hook.remove()
    assert state['target_calls'] == 1
    assert state['block21_calls'] == int(full)
    assert vector is not None
    state.update({'shape': list(vector.shape), 'finite': True, 'dtype': str(vector.dtype),
                  'norm': vector.float().norm().item()})
    return vector, state


@torch.inference_mode()
def receiver_run(model, tokenizer, tensors, mode='receiver_only', vector=None, check=False, prefix_allowed_tokens_fn=None):
    """Keep historical generation; hooks observe cache/logits and inject once."""
    length = tensors['input_ids'].shape[1]
    assert tensors['input_ids'].shape[0] == 1
    assert tensors['attention_mask'].sum().item() == length
    state = {'mode': mode, 'injections': 0, 'target_block_calls': 0,
             'decode_calls': 0, 'logits_finite': True, 'cache_used': True,
             'block_index': 19, 'prompt_position': length - 1}
    first_logits = None
    if vector is not None:
        vector = vector.to(device=model.device, dtype=torch.bfloat16)
        assert vector.shape == (1, 1024 if mode == 'acw_replace' else 896)

    def inject(module, args, kwargs, output):
        h = output[0]
        call = state['target_block_calls']
        state['target_block_calls'] += 1
        pos = kwargs['cache_position']
        if call:
            assert h.shape == (1, 1, 1024)
            assert pos.numel() == 1 and pos.item() == length + call - 1
            assert kwargs['past_key_value'] is not None
            state['decode_calls'] += 1
            return output
        assert h.shape == (1, length, 1024)
        assert torch.equal(pos, torch.arange(length, device=pos.device))
        if mode == 'receiver_only':
            return output
        assert mode in ('self_replace', 'ac_replace', 'acw_replace')
        assert torch.isfinite(h).all().item()
        modified = h.clone()
        if mode == 'self_replace':
            modified[:, -1, :] = h[:, -1, :].clone()
        elif mode == 'acw_replace':
            modified[:, -1, :] = vector
            assert torch.equal(modified[:, -1, :], vector)
            state['full_1024_replaced_exactly'] = True
        else:
            modified[:, -1, 128:] = vector
            assert torch.equal(modified[:, -1, 128:], vector)
        assert torch.equal(modified[:, :-1, :], h[:, :-1, :])
        prefix_same = torch.equal(modified[:, -1, :128], h[:, -1, :128])
        if mode != 'acw_replace':
            assert prefix_same
        assert torch.isfinite(modified).all().item()
        state.update({'injections': 1, 'non_target_positions_unchanged': True,
                      'first_128_unchanged': prefix_same, 'residual_finite': True,
                      'receiver_original_norm': h[:, -1].float().norm().item(),
                      'receiver_modified_norm': modified[:, -1].float().norm().item(),
                      'replacement_delta_norm': (modified[:, -1].float() - h[:, -1].float()).norm().item()})
        return (modified,) + output[1:]

    def inspect_output(module, args, output):
        nonlocal first_logits
        assert torch.isfinite(output.logits).all().item(), 'NaN/Inf receiver logits'
        assert output.past_key_values is not None, 'missing decode cache'
        if check and first_logits is None:
            first_logits = output.logits[:, -1, :].detach().float().cpu()

    hooks = [model.model.layers[19].register_forward_hook(inject, with_kwargs=True),
             model.register_forward_hook(inspect_output)]
    try:
        text, ids = generate_receiver(model, tokenizer, tensors, prefix_allowed_tokens_fn=prefix_allowed_tokens_fn)
    finally:
        for hook in hooks:
            hook.remove()
    assert state['injections'] == (0 if mode == 'receiver_only' else 1)
    assert state['target_block_calls'] == ids.numel()
    parsed = extract_answer_from_content(text)
    result = {'raw_answer': text, 'generated_token_ids': ids.cpu().tolist(),
              'parsed_answer': parsed, 'parse_failure': parsed is None,
              'runtime_error': None, 'input_tokens': length, 'output_tokens': ids.numel(),
              'hit_generation_cap': ids.numel() == 64, 'audit': state}
    return result, first_logits


def prompt_record(tokenizer, row, device):
    body, rendered, tensors = receiver_prompt_tensors(tokenizer, row, device)
    assert tensors['input_ids'].shape[0] == 1
    assert tensors['attention_mask'].sum().item() == tensors['input_ids'].shape[1]
    return {'body_sha256': hashlib.sha256(body.encode()).hexdigest(),
            'rendered_prompt': rendered, 'rendered_sha256': hashlib.sha256(rendered.encode()).hexdigest(),
            'token_ids': tensors['input_ids'][0].cpu().tolist()}, tensors


def load(spec, device):
    tok = AutoTokenizer.from_pretrained(spec['path'], local_files_only=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(spec['path'], local_files_only=True,
                torch_dtype=torch.bfloat16, attn_implementation='sdpa').to(device).eval()
    model.requires_grad_(False)
    apply_generation_config(model, {'do_sample': False, 'max_new_tokens': 64})
    return tok, model
