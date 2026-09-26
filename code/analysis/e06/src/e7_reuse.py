"""E7 arms (3) REUSE and (4) ARGMAX.

The ProbeMax probe is unchanged in everything that produces a number: same prompt, same tokenisation,
same FP32 label logsumexp/softmax, same last-position projection.  The only difference in the REUSE
variant is use_cache=True, so the prefill KV cache survives the probe and can be continued.
"""
import hashlib,time,torch

def probe_core(model,tok,q,receiver_prompt,display_labels,prefix_ids,ix,keep_cache):
    """Returns (u, meta, R_ids, cache).  cache is None unless keep_cache."""
    body=receiver_prompt(q)
    rendered=tok.apply_chat_template([{'role':'user','content':body}],tokenize=False,
                                     add_generation_prompt=True,enable_thinking=False)
    base=tok(rendered,return_tensors='pt')
    suffix=tok.encode('The correct answer is',add_special_tokens=False)
    assert suffix==list(prefix_ids)
    ids=torch.cat([base['input_ids'],torch.tensor([suffix],dtype=base['input_ids'].dtype)],dim=1)
    mask=torch.cat([base['attention_mask'],torch.ones((1,len(suffix)),dtype=base['attention_mask'].dtype)],dim=1)
    pos=int(torch.nonzero(mask[0],as_tuple=False)[-1,0]);n=ids.shape[1]
    dev=model.device
    inp={'input_ids':ids.to(dev),'attention_mask':mask.to(dev)}
    out=model.model(**inp,use_cache=bool(keep_cache),return_dict=True,
                    output_hidden_states=False,output_attentions=False)
    assert pos==n-1 and int(mask.sum())==n
    last=out.last_hidden_state[:,pos:pos+1,:];logits=model.lm_head(last)[0,0,:].float()
    labels=display_labels(len(q['choice_text']));assert labels==q['choice_labels']
    label_logits=torch.stack([torch.logsumexp(logits[ix[l]],dim=0) for l in labels])
    p=torch.log_softmax(label_logits,dim=0).exp();ps=p.cpu().tolist()
    u=float((1-p.max()).item())
    cache=out.past_key_values if keep_cache else None
    if not keep_cache:assert out.past_key_values is None
    meta={'ProbeMax':u,'p_labels':dict(zip(labels,ps)),
          'argmax_probe_label':labels[max(range(len(ps)),key=ps.__getitem__)],
          'probe_ids_sha256':hashlib.sha256(ids.numpy().tobytes()).hexdigest(),
          'input_tokens':n,'last_valid_position':pos,'cache_reused':bool(keep_cache)}
    return u,meta,base['input_ids'],cache

def crop_to_R_prefix(cache,n_R):
    """Crop the probe cache to the native R prompt minus its last token.

    The native R prompt is an exact token prefix of the probe input (verified 640/640, see
    E7_PREFIX_CHECK.json).  The frozen probe projects only its LAST position through lm_head, so no
    logits exist for position n_R-1; that one token is re-prefilled by the generator.
    """
    cache.crop(n_R-1)
    return cache

@torch.inference_mode()
def generate_R_from_cache(model,tok,R_ids,cache):
    """generate_receiver() of the frozen protocol, continued from the cropped probe cache."""
    dev=model.device
    input_ids=R_ids.to(dev);attn=torch.ones_like(input_ids)
    out=model.generate(input_ids=input_ids,attention_mask=attn,do_sample=False,max_new_tokens=64,
        use_cache=True,past_key_values=cache,
        pad_token_id=(model.generation_config.pad_token_id if model.generation_config.pad_token_id is not None else tok.pad_token_id),
        eos_token_id=(model.generation_config.eos_token_id if model.generation_config.eos_token_id is not None else tok.eos_token_id))
    gen=out[0,input_ids.shape[1]:]
    return tok.decode(gen,skip_special_tokens=True).strip('\n'),gen.detach().cpu().tolist()
