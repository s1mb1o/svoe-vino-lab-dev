"""Rank compact score arrays with deterministic wine ties."""
from pathlib import Path
import json
import numpy as np
from plan import HERE, OUT, dump


def context():
    return json.loads((HERE / "context.json").read_text())


def save_component(key,scores,metadata):
    path=HERE / "components" / (key+".npy");path.parent.mkdir(exist_ok=True)
    ctx=context()
    assert scores.shape==(len(ctx["ids"]),len(ctx["slugs"])) and not np.isnan(scores).any()
    assert np.isfinite(scores).sum(1).max()>0
    if path.exists():
        assert np.array_equal(np.load(path,allow_pickle=False),scores),key
        return
    temporary=path.with_suffix(".tmp.npy");np.save(temporary,np.asarray(scores,np.float32),allow_pickle=False);temporary.replace(path)
    dump(path.with_suffix(".json"),metadata)


def topk(scores,k=10):
    """Columns are in ascending wine_slug order. Preserve this order for a tie."""
    scores=np.asarray(scores,np.float64)
    cutoff=np.partition(scores,-k,axis=1)[:,-k]
    better=scores>cutoff[:,None]
    slots=k-better.sum(1)
    ties=scores==cutoff[:,None]
    chosen=better | (ties & (np.cumsum(ties,axis=1)<=slots[:,None]))
    assert np.all(chosen.sum(1)==k)
    numbers=np.where(chosen)[1].reshape(len(scores),k)
    values=np.take_along_axis(scores,numbers,axis=1)
    indices=np.argsort(-values,axis=1,kind="stable")
    numbers=np.take_along_axis(numbers,indices,axis=1)
    values=np.take_along_axis(values,indices,axis=1)
    numbers[~np.isfinite(values)]=-1
    return numbers.astype(np.int16),values


def prepared(scores):
    scores=np.asarray(scores,np.float64)
    top,values=topk(scores)
    ranked=np.argsort(-scores,axis=1,kind="stable")
    ranks=np.empty(scores.shape,np.int16)
    np.put_along_axis(ranks,ranked,np.broadcast_to(np.arange(1,scores.shape[1]+1),(len(scores),scores.shape[1])),axis=1)
    rr=np.where(np.isfinite(scores),1/(60.+ranks),-np.inf)
    gap=np.full(len(values),-np.inf)
    np.subtract(values[:,0],values[:,1],out=gap,where=np.isfinite(values[:,:2]).all(1))
    return {"scores":scores,"top":top,"values":values,"gap":gap,"rrf":rr,"present":top[:,0]>=0}


def merged(b,l,policy):
    bs,ls=b["scores"],l["scores"]
    if policy["merge"]=="max":return np.maximum(bs,ls)
    if policy["merge"]=="rrf":return np.where(np.isfinite(b["rrf"]),b["rrf"],0)+np.where(np.isfinite(l["rrf"]),l["rrf"],0)
    alpha=policy["bottle_weight"]
    both=np.isfinite(bs)&np.isfinite(ls)
    result=np.maximum(bs,ls).copy()
    result[both]=alpha*bs[both]+(1-alpha)*ls[both]
    return result


def fusion(b,l,policy,merge_cache):
    key=(policy["merge"],policy["bottle_weight"])
    if key not in merge_cache:merge_cache[key]=topk(merged(b,l,policy))[0]
    fallback=merge_cache[key]
    if policy["mode"]=="always":
        result=fallback.copy();route=np.full(len(result),2,np.uint8)
    else:
        bt,lt=policy["bottle_threshold"],policy["label_threshold"]
        bc,lc=b["gap"]>=bt,l["gap"]>=lt
        bottle=bc & (~lc | (b["gap"]/bt>=l["gap"]/lt))
        label=lc & ~bottle
        if policy["mode"]=="conflict":
            conflict=bc & lc & (b["top"][:,0]!=l["top"][:,0]);bottle[conflict]=False;label[conflict]=False
        result=fallback.copy();route=np.full(len(result),2,np.uint8)
        result[bottle]=b["top"][bottle];route[bottle]=0
        result[label]=l["top"][label];route[label]=1
        if policy["mode"]=="pin":
            for number in np.flatnonzero(bottle|label):
                winner=int(result[number,0]);tail=[int(n) for n in fallback[number] if n>=0 and n!=winner]
                result[number]=[winner]+tail[:9]
    missing=~l["present"]
    result[missing]=b["top"][missing];route[missing]=0
    assert np.all(result>=-1)
    return result,route


def evaluator(ctx):
    lookup={s:i for i,s in enumerate(ctx["slugs"])}
    images={s:i for i,s in enumerate(ctx["ids"])}
    n=len(ctx["assignments"])
    truth=np.zeros((n,len(lookup)),bool)
    assignment=np.array([images[q["image"]] for q in ctx["assignments"]])
    positive=np.array([q["label"]=="positive" for q in ctx["assignments"]])
    negative=np.array([q["label"]=="negative" for q in ctx["assignments"]])
    nomatch=np.array([q["label"]=="no_match" for q in ctx["assignments"]])
    rejected=np.array([lookup.get(q["slug"],-2) for q in ctx["assignments"]])
    for i,q in enumerate(ctx["assignments"]):
        for slug in q["truth"]:
            if slug in lookup:truth[i,lookup[slug]]=True
    def evaluate(top):
        candidates=top[assignment]
        hits=truth[np.arange(n)[:,None],np.maximum(candidates,0)]&(candidates>=0)
        ranks=np.where(hits.any(1),hits.argmax(1)+1,11).astype(np.uint8)
        ranks[~positive]=0
        pos=ranks[positive]
        invalid=(candidates==rejected[:,None])&negative[:,None]
        return {"top1":int((pos<=1).sum()),"top5":int((pos<=5).sum()),
                "top10":int((pos<=10).sum()),"mrr":float(np.where(pos<=10,1/pos,0).mean()),
                "negative_false1":int(invalid[:,0].sum()),
                "negative_false10":int(invalid.any(1).sum()),
                "no_match_false1":int((nomatch&(candidates[:,0]>=0)).sum()),
                "no_answer":int((candidates[:,0]<0).sum())},ranks
    return evaluate


def checks():
    # Compare every policy with the scalar experiment-8 rule at its matching levels.
    import importlib.util
    spec=importlib.util.spec_from_file_location("scalar_matrix_control",OUT / "fusion-20261017/fusion.py")
    scalar=importlib.util.module_from_spec(spec);spec.loader.exec_module(scalar)
    from plan import policies
    rng=np.random.default_rng(3817)
    bs=rng.uniform(.3,.9,(41,31));ls=rng.uniform(.3,.9,(41,31));ls[0]=-np.inf
    bs[1,:12]=.8;ls[2,:12]=.8
    slugs=[f"wine-{i:03d}" for i in range(31)]
    b,l=prepared(bs),prepared(ls)
    for key,p in policies().items():
        actual,_=fusion(b,l,p,{})
        assert all(len(set(r.tolist()))==10 for r in actual)
        for i in range(len(bs)):
            if p["merge"] not in ("mean","max","rrf") or p["bottle_weight"] not in (None,.5):continue
            if p["mode"] not in ("always","gate","conflict") or p["bottle_threshold"]!=p["label_threshold"]:continue
            condition={"merge":p["merge"],"threshold":p["bottle_threshold"],"conflict_fallback":p["mode"]=="conflict"}
            scores,_=scalar.choose(bs[i],ls[i],slugs,condition)
            assert actual[i].tolist()==scalar.order(scores,slugs)[:10],(key,i)
    # Exact cutoff ties MUST retain the first ten lexical wine identities.
    tie=np.ones((3,31));assert np.all(topk(tie)[0]==np.arange(10))
    return {"passed":True,"scalar_control_queries":41,"policies":42,"tie_control":"passed"}
