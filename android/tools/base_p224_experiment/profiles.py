"""Contracts for the isolated Base NaFlex pooling comparison."""
import hashlib
import json
import os

import numpy as np
from PIL import Image


MODEL='google/siglip2-base-patch16-naflex'
REVISION='b53b807d3a2d5e2b3911292f2d69e5341cdc064c'
PACKAGE=os.environ.get('BASE_POOLING_PACKAGE','com.alolalab.chtozavino.basepoolbench')
if PACKAGE not in ('com.alolalab.chtozavino.basepoolbench','com.alolalab.chtozavino.fullpoolbench',
                   'com.alolalab.chtozavino.dispoolbench','com.alolalab.chtozavino.disresbench'):
    raise ValueError('Unknown isolated pooling application')
CONDITIONS=(
    dict(number=1,name='base-p224-standard',budget=224,pooling='standard'),
    dict(number=2,name='base-p224-fractional-bg010',budget=224,pooling='fractional-bg010'),
    dict(number=3,name='base-p512-standard',budget=512,pooling='standard'),
    dict(number=4,name='base-p512-fractional-bg010',budget=512,pooling='fractional-bg010'),
)


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def effective_profile(model_manifest,pooling):
    if pooling not in ('standard','fractional-bg010'):raise ValueError('Unknown pooling profile')
    profile=dict(model_manifest['profile'],pooling=pooling,
        mask_coverage='bilinear-float-actual-grid-16x16',background_weight=.1 if pooling!='standard' else None,
        foreground_weight=1.,label_weight=1.,reference_views=1,reference_aggregation='max')
    encoded=json.dumps(profile,sort_keys=True,separators=(',',':')).encode()
    return dict(parameters=profile,sha256=hashlib.sha256(encoded).hexdigest())


def coverage(alpha,rows,columns):
    values=np.asarray(alpha,dtype=np.float32)
    if values.ndim!=2 or min(values.shape)<1 or min(rows,columns)<1:
        raise ValueError('Require a nonempty source mask and grid')
    if not np.isfinite(values).all() or values.min()<0 or values.max()>1:
        raise ValueError('Mask coverage must be finite and within [0,1]')
    resized=np.asarray(Image.fromarray(values).resize((columns*16,rows*16),Image.Resampling.BILINEAR))
    return resized.reshape(rows,16,columns,16).mean(axis=(1,3),dtype=np.float64).astype(np.float32).ravel()


def log_weights(foreground,budget,pooling):
    values=np.asarray(foreground,dtype=np.float32)
    if values.ndim!=1 or not 0<len(values)<=budget or not np.isfinite(values).all():
        raise ValueError('Invalid foreground vector')
    if values.min()<0 or values.max()>1:raise ValueError('Foreground must be within [0,1]')
    if pooling not in ('standard','fractional-bg010'):raise ValueError('Unknown pooling profile')
    result=np.zeros((1,budget),dtype=np.float32)
    if pooling!='standard':result[0,:len(values)]=np.log(.1*(1-values)+values)
    # Valid-patch flags still exclude padding. Zero bias must not unmask padding.
    return result
