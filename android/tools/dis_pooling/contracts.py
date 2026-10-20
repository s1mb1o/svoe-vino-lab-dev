"""Independent DIS normalization and source-mask projection for device captures."""
import math
import numpy as np


def normalized_dis(raw):
    values=np.asarray(raw,dtype=np.float32)
    if not values.size or not np.isfinite(values).all():raise ValueError('Invalid DIS output')
    span=values.max()-values.min()
    if not np.isfinite(span) or span<=1e-6:raise ValueError('Constant DIS mask')
    return np.clip((values-values.min())/span,0,1)


def dis_foreground(mask,width,height,frame):
    mask=np.asarray(mask,dtype=np.float32)
    if mask.ndim!=2 or mask.shape[0]!=mask.shape[1] or mask.shape[0] not in (512,768,1024):
        raise ValueError('Unexpected DIS mask resolution')
    size=mask.shape[0]
    if frame=='full-image':left=top=0;crop_width=out_width=width;crop_height=out_height=height
    elif frame=='bottle-crop-white':
        y,x=np.where(mask>=.5)
        if len(x)<4:raise ValueError('Empty foreground')
        x0=x.min()*width/size;x1=(x.max()+1)*width/size
        y0=y.min()*height/size;y1=(y.max()+1)*height/size
        dx=(x1-x0)*.04;dy=(y1-y0)*.04
        left=math.floor(x0-dx);top=math.floor(y0-dy)
        crop_width=max(1,math.ceil(x1+dx-left));crop_height=max(1,math.ceil(y1+dy-top))
        scale=min(1,1024/max(crop_width,crop_height))
        out_width=max(1,round(crop_width*scale));out_height=max(1,round(crop_height*scale))
    else:raise ValueError('Unknown frame')
    sx=left+(np.arange(out_width,dtype=np.float64)+.5)*crop_width/out_width
    sy=top+(np.arange(out_height,dtype=np.float64)+.5)*crop_height/out_height
    mx=np.clip(sx*size/width-.5,0,size-1);my=np.clip(sy*size/height-.5,0,size-1)
    ix=np.floor(mx).astype(int);iy=np.floor(my).astype(int)
    fx=mx-ix;fy=my-iy;xx=np.minimum(ix+1,size-1);yy=np.minimum(iy+1,size-1)
    result=((1-fy[:,None])*((1-fx)*mask[iy[:,None],ix]+fx*mask[iy[:,None],xx])+
        fy[:,None]*((1-fx)*mask[yy[:,None],ix]+fx*mask[yy[:,None],xx]))
    result[:,(sx<0)|(sx>=width)]=0;result[(sy<0)|(sy>=height),:]=0
    return result.astype(np.float32)
