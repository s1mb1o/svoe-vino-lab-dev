"""Specialize only the spatial dimensions of the pinned fully convolutional DIS graph."""
import argparse
import hashlib
import json
from pathlib import Path

import flatbuffers
import numpy as np
from ai_edge_litert import schema_py_generated as schema
from ai_edge_litert.interpreter import Interpreter

SOURCE_SHA='0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087'
SIZES=(512,768,1024)
SHAPE_TENSORS={228:[1,1,1024,1024],231:[1024,1024],232:[512,512],233:[256,256],
               234:[128,128],235:[64,64],236:[32,32]}


def sha(data):return hashlib.sha256(data).hexdigest()


def spatial_shape(shape,size,nchw=False,padded=False):
    if size not in SIZES or len(shape)!=4 or shape[0]!=1:raise ValueError('Unexpected DIS shape')
    axes=(2,3) if nchw else (1,2);result=list(map(int,shape))
    for axis in axes:
        original=result[axis]-2 if padded else result[axis]
        if padded and original!=1024:raise ValueError('Unexpected padded activation')
        if original*size%1024:raise ValueError('Nonintegral spatial dimension')
        result[axis]=original*size//1024+(2 if padded else 0)
    return result


def specialize(raw,size):
    if sha(raw)!=SOURCE_SHA or size not in SIZES:raise ValueError('Require the pinned DIS graph and supported size')
    model=schema.ModelT.InitFromObj(schema.Model.GetRootAsModel(raw,0))
    if len(model.subgraphs)!=1:raise ValueError('Unexpected subgraph count')
    graph=model.subgraphs[0]
    if (len(graph.operators)!=247 or len(graph.tensors)!=485 or list(graph.inputs)!=[0] or list(graph.outputs)!=[484]):
        raise ValueError('Unexpected pinned graph layout')
    before={i:sha(bytes(b.data)) for i,b in enumerate(model.buffers) if b.data is not None}
    changed=[];mutable=set()
    for index,expected in SHAPE_TENSORS.items():
        tensor=graph.tensors[index];buffer=model.buffers[tensor.buffer]
        if tensor.type!=schema.TensorType.INT32:raise ValueError('Unexpected shape tensor dtype')
        values=np.frombuffer(bytes(buffer.data),dtype='<i4').tolist()
        if values!=expected:raise ValueError('Unexpected spatial constant')
        actual=([1,1,size,size] if index==228 else [v*size//1024 for v in values])
        buffer.data=np.frombuffer(np.asarray(actual,dtype='<i4').tobytes(),dtype=np.uint8).copy()
        mutable.add(int(tensor.buffer));changed.append(dict(tensor=index,kind='shape-constant',before=values,after=actual))
    for index,tensor in enumerate(graph.tensors):
        buffer=model.buffers[tensor.buffer]
        if buffer.data is not None and len(buffer.data):continue
        if tensor.type!=schema.TensorType.FLOAT32 or len(tensor.shape)!=4:raise ValueError('Unexpected activation')
        previous=list(map(int,tensor.shape));actual=spatial_shape(previous,size,index in (0,484),index==239)
        tensor.shape=np.asarray(actual,dtype=np.int32)
        if tensor.shapeSignature is not None and len(tensor.shapeSignature):
            if list(tensor.shapeSignature)!=previous:raise ValueError('Unexpected dynamic signature')
            tensor.shapeSignature=np.asarray(actual,dtype=np.int32)
        changed.append(dict(tensor=index,kind='activation-shape',before=previous,after=actual))
    for signature in model.signatureDefs or []:
        if signature.subgraphIndex!=0:raise ValueError('Unexpected signature subgraph')
    for index,buffer in enumerate(model.buffers):
        if index not in mutable and buffer.data is not None and sha(bytes(buffer.data))!=before[index]:
            raise RuntimeError('An immutable payload changed')
    builder=flatbuffers.Builder(len(raw));offset=model.Pack(builder);builder.Finish(offset,file_identifier=b'TFL3')
    output=bytes(builder.Output())
    # Packing must not alter any operator, option, tensor payload, or channel dimension.
    restored=schema.ModelT.InitFromObj(schema.Model.GetRootAsModel(output,0))
    immutable={str(i):before[i] for i in before if i not in mutable}
    for index,expected in immutable.items():
        if sha(bytes(restored.buffers[int(index)].data))!=expected:raise RuntimeError('Packed weights changed')
    return output,dict(source_sha256=SOURCE_SHA,input_size=size,model_sha256=sha(output),
        method='Static spatial specialization; unchanged learned weights and operator options',
        changed_tensors=changed,mutable_shape_buffers=sorted(mutable),immutable_buffer_sha256=immutable,
        operators=247,weights_preserved=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--size',type=int,choices=SIZES,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.out.exists():raise ValueError('Preserve existing exports')
    raw=args.source.read_bytes();candidate,record=specialize(raw,args.size)
    # CPU execution verifies inferred activation shapes, concat compatibility, and finite masks.
    cpu=Interpreter(model_content=candidate,num_threads=4);cpu.allocate_tensors()
    graph=schema.Model.GetRootAsModel(candidate,0).Subgraphs(0)
    for detail in cpu.get_tensor_details():
        if detail['index']<graph.TensorsLength() and detail['shape'].tolist()!=graph.Tensors(detail['index']).ShapeAsNumpy().tolist():
            raise RuntimeError('Runtime changed a declared static activation shape')
    inp=cpu.get_input_details()[0];out=cpu.get_output_details()[0]
    if inp['shape'].tolist()!=[1,3,args.size,args.size] or out['shape'].tolist()!=[1,1,args.size,args.size]:
        raise RuntimeError('Unexpected candidate I/O')
    rng=np.random.default_rng(20261020);values=rng.uniform(-.5,.5,inp['shape']).astype(np.float32)
    cpu.set_tensor(inp['index'],values);cpu.invoke();actual=cpu.get_tensor(out['index'])
    if not np.isfinite(actual).all() or actual.max()-actual.min()<=1e-6:raise RuntimeError('Invalid candidate mask')
    record['cpu_smoke']=dict(passed=True,all_static_shapes_verified=True,input_shape=inp['shape'].tolist(),output_shape=out['shape'].tolist(),
        minimum=float(actual.min()),maximum=float(actual.max()))
    if args.size==1024:
        reference=Interpreter(model_content=raw,num_threads=4);reference.allocate_tensors()
        reference.set_tensor(reference.get_input_details()[0]['index'],values);reference.invoke()
        error=float(np.max(np.abs(actual-reference.get_tensor(reference.get_output_details()[0]['index']))))
        if error!=0:raise RuntimeError('Identity specialization changed CPU output')
        record['identity_cpu_max_error']=error
    args.out.mkdir(parents=True)
    (args.out/'dis.tflite').write_bytes(candidate)
    (args.out/'export-record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('changed_tensors','immutable_buffer_sha256')}))


if __name__=='__main__':main()
