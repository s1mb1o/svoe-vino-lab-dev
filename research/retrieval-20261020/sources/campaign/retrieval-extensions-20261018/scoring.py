"""Score complete wine arrays and preserve every ranked candidate list."""
import hashlib
import importlib.util
import io
import sqlite3
import sys
import time
import zipfile
import numpy as np
from settings import *

sys.path.insert(0,str(ROOT/"my-matrix-20261017"))
import core
spec=importlib.util.spec_from_file_location("extension_topk",AXM/"fast_topk.py")
fast=importlib.util.module_from_spec(spec);spec.loader.exec_module(fast)
core.topk=fast.topk

def key_of(recipe):
    return "x-"+hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()[:24]

def known_control(recipe):
    inverse={value:key for key,value in ALIASES.items()}
    if recipe['reference_pool']!=recipe['query_pool'] or recipe['reference_pool'] not in inverse:return None
    if recipe['reference_budget']!=512 or recipe['query_budget']!=512:return None
    if recipe['reference_margin'] is not None or recipe['query_margin'] is not None or recipe['aggregation']!='max':return None
    if recipe['gallery'] not in GALLERIES:return None
    return 'b-'+inverse[recipe['reference_pool']]+'-'+recipe['query_geometry']+'-'+recipe['gallery']+('+axial' if recipe['axial_union'] else '')

def aggregate(raw, owners, wines, k=1):
    """Average the best k vectors per wine. Keep distinct equal-score vectors."""
    order=np.argsort(owners,kind="stable");grouped=owners[order]
    starts=np.r_[0,np.flatnonzero(np.diff(grouped))+1];columns=grouped[starts]
    result=np.full((raw.shape[1],wines),-np.inf,np.float32)
    values=np.ascontiguousarray(raw[order],np.float32)
    if k==1:
        result[:,columns]=np.maximum.reduceat(values,starts,axis=0).T
        return result
    # Encode float order and inverse row order into one exact uint64 reduction.
    bits=values.view(np.uint32)
    ordered=np.where(bits & np.uint32(0x80000000),~bits,bits ^ np.uint32(0x80000000))
    packed=(ordered.astype(np.uint64)<<np.uint64(32)) | (np.uint64(0xffffffff)-np.arange(len(values),dtype=np.uint64))[:,None]
    sums=np.zeros((len(columns),raw.shape[1]),np.float64)
    counts=np.minimum(np.diff(np.r_[starts,len(values)]),k)
    for position in range(k):
        best=np.maximum.reduceat(packed,starts,axis=0)
        indices=(np.uint64(0xffffffff)-(best & np.uint64(0xffffffff))).astype(np.int64)
        valid=counts>position
        sums[valid]+=values[indices[valid],np.arange(raw.shape[1])[None,:]]
        packed[indices[valid],np.arange(raw.shape[1])[None,:]]=0
    result[:,columns]=(sums/counts[:,None]).T
    return result

def controls():
    rng=np.random.default_rng(4018)
    owners=np.repeat(np.arange(15),rng.integers(1,8,15))
    raw=rng.choice(np.array([-.5,-.1,0.,.1,.5,.9],np.float32),(len(owners),9))
    for k in (1,2,3):
        actual=aggregate(raw,owners,17,k)
        for wine in range(15):
            expected=np.sort(raw[owners==wine],axis=0)[-k:].mean(0,dtype=np.float64)
            assert np.allclose(actual[:,wine],expected,atol=1e-7),(wine,k)
        assert np.isneginf(actual[:,15:]).all()
    dump(HERE/"aggregation-controls.json",dict(passed=True,tests=45,equal_scores=True,negative_scores=True,missing_wines=True,small_groups=True))

class Scorer:
    def __init__(self,rank_scores=True,cohorts=None):
        self.cohorts=tuple(cohorts or FOLDERS)
        self.ctx=read(HERE/"context.json");self.ids=self.ctx["ids"];self.slugs=self.ctx["slugs"]
        self.conn=sqlite3.connect(HERE/"metrics.sqlite3",timeout=120)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("CREATE TABLE IF NOT EXISTS metrics (cohort TEXT, variant_id TEXT, bottle_id TEXT, label_id TEXT, policy_id TEXT, family TEXT, recipe TEXT, n INTEGER, top1 INTEGER, top5 INTEGER, top10 INTEGER, mrr REAL, image_n INTEGER, image_top1 INTEGER, image_top5 INTEGER, image_top10 INTEGER, image_mrr REAL, negative_false1 INTEGER, negative_false10 INTEGER, no_match_false1 INTEGER, no_answer INTEGER, fix1 INTEGER, regression1 INTEGER, fix5 INTEGER, regression5 INTEGER, fix10 INTEGER, regression10 INTEGER, PRIMARY KEY(cohort,variant_id))")
        self.conn.execute('CREATE INDEX IF NOT EXISTS metrics_bottle_scope ON metrics(bottle_id,cohort)')
        self.contexts={};self.evaluators={};self.indices={};self.image_evaluators={};self.baselines={};self.positives={}
        for cohort,folder in FOLDERS.items():
            ctx=read(ROOT/folder/"context.json")
            for row in ctx["assignments"]:row.setdefault("label","positive")
            self.contexts[cohort]=ctx;self.evaluators[cohort]=core.evaluator(ctx)
            self.indices[cohort]=np.asarray([self.ids.index(image) for image in ctx["ids"]])
            groups={}
            for row in ctx["assignments"]:
                if row["label"]=="positive":groups.setdefault(row["image"],set()).update(row["truth"])
            image_ctx=dict(ctx,assignments=[dict(image=image,truth=sorted(truth),label="positive",slug="") for image,truth in groups.items()])
            self.image_evaluators[cohort]=core.evaluator(image_ctx)
            self.positives[cohort]=np.asarray([row["label"]=="positive" for row in ctx["assignments"]])
            self.baselines[cohort]=np.asarray(read(ROOT/folder/"singles/b-u-original-rot5.json")["ranks"])
        manifest=read(ROOT/"my-matrix-20261017/manifest.json")
        anchors=read(HERE/"protocol.json")["fixed_fusion_anchors"]
        self.policies={key:manifest["policies"][key] for key in anchors["policies"]}
        self.labels={}
        for label in anchors["labels"]:
            if not rank_scores:
                self.labels[label]=None
                continue
            values=np.full((len(self.ids),len(self.slugs)),-np.inf,np.float32)
            for cohort,folder in reversed(list(FOLDERS.items())):
                values[self.indices[cohort]]=np.load(ROOT/folder/"components"/(label+".npy"),allow_pickle=False)
            self.labels[label]=core.prepared(values)
        (HERE/"tops").mkdir(exist_ok=True)

    def done(self,recipe):
        return all(self.conn.execute('SELECT count(*) FROM metrics WHERE bottle_id=? AND cohort=?',(key_of(recipe),cohort)).fetchone()[0]==11 for cohort in self.cohorts)

    def record(self,recipe,family,scores=None,variants_override=None):
        key=key_of(recipe)
        if self.done(recipe):return
        pending=[cohort for cohort in self.cohorts if self.conn.execute('SELECT count(*) FROM metrics WHERE bottle_id=? AND cohort=?',(key,cohort)).fetchone()[0]!=11]
        began=time.monotonic()
        if variants_override is None:
            assert scores.shape==(len(self.ids),len(self.slugs)) and not np.isnan(scores).any()
            bottle=core.prepared(scores)
            variants=[(key,"","",bottle["top"])]
            for label,data in self.labels.items():
                cache={}
                for policy,definition in self.policies.items():
                    top,_=core.fusion(bottle,data,definition,cache)
                    variants.append((key+"__"+label+"__"+policy,label,policy,top))
        else:variants=variants_override
        rows=[];saved={};known=known_control(recipe)
        target=HERE/"tops"/(key+".npz")
        if target.exists():
            with np.load(target,allow_pickle=False) as previous:saved={name:previous[name] for name in previous.files}
        exact={}
        if known:
            for cohort in pending:
                folder=FOLDERS[cohort]
                source=(AXM/cohort if recipe['axial_union'] else ROOT/folder)/'components'/(known+'.npy')
                exact_bottle=core.prepared(np.load(source,allow_pickle=False))
                actual={key:exact_bottle['top']}
                for label in self.labels:
                    local_label=core.prepared(np.load(ROOT/folder/'components'/(label+'.npy'),allow_pickle=False));cache={}
                    for policy,definition in self.policies.items():actual[key+'__'+label+'__'+policy]=core.fusion(exact_bottle,local_label,definition,cache)[0]
                exact[cohort]=actual
        for vid,label,policy,top in variants:
            for cohort in pending:
                picked=exact[cohort][vid] if known else top[self.indices[cohort]]
                saved[cohort+'__'+vid]=picked
                metrics,ranks=self.evaluators[cohort](picked)
                images,image_ranks=self.image_evaluators[cohort](picked)
                positive=self.positives[cohort];base=self.baselines[cohort]
                paired=[]
                for k in (1,5,10):paired.extend([int((positive&(base>k)&(ranks<=k)).sum()),int((positive&(base<=k)&(ranks>k)).sum())])
                rows.append((cohort,vid,key,label,policy,str(family),json.dumps(recipe,sort_keys=True),int(positive.sum()),
                             metrics["top1"],metrics["top5"],metrics["top10"],metrics["mrr"],len(image_ranks),
                             images["top1"],images["top5"],images["top10"],images["mrr"],metrics["negative_false1"],
                             metrics["negative_false10"],metrics["no_match_false1"],metrics["no_answer"],*paired))
        target=HERE/"tops"/(key+".npz");tmp=target.with_suffix(".tmp.npz")
        with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
            for name,array in saved.items():
                stream=io.BytesIO();np.lib.format.write_array(stream,np.asarray(array),allow_pickle=False)
                archive.writestr(name+'.npy',stream.getvalue())
        tmp.replace(target)
        with self.conn:self.conn.executemany("INSERT OR REPLACE INTO metrics VALUES ("+",".join("?" for _ in rows[0])+")",rows)
        dump(HERE/("score-"+str(family)+"-status.json"),dict(at=now(),state="Score retrieval extension",family=str(family),bottle=key,
                                                                  rows=self.conn.execute("SELECT count(*) FROM metrics").fetchone()[0],seconds=time.monotonic()-began))

def recipe(rp,qp,q,g,axial=False,aggregation="max",**kwargs):
    return dict(reference_pool=ALIASES.get(rp,rp),query_pool=ALIASES.get(qp,qp),query_geometry=q,gallery=g,
                axial_union=axial,aggregation=aggregation,reference_budget=512,query_budget=512,
                reference_margin=None,query_margin=None,**kwargs)

if __name__=="__main__":controls()
