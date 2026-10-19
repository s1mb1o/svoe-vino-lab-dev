#!/usr/bin/env python3
"""Add an explicit log-weight input to only the complete graph's pooling logits."""

import argparse
import gc
import hashlib
import json
from pathlib import Path

import flatbuffers
import numpy as np
from litert_converter import schema_py_generated as schema


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.source_manifest.read_text())
    source = args.source_manifest.parent / manifest['model_file']
    if sha(source) != manifest['model_sha256']:
        raise ValueError('The source model checksum does not match its manifest.')
    if args.out.exists() or args.out.with_suffix('.manifest.json').exists():
        raise FileExistsError('Keep each generated model version separate.')
    packed = bytearray(source.read_bytes())
    model = schema.ModelT.InitFromObj(schema.Model.GetRootAsModel(packed, 0))
    external_buffers = [buffer for buffer in model.buffers if buffer.offset]
    external_start = min((buffer.offset for buffer in external_buffers), default=None)
    if external_start is not None:
        if external_start % 16 or any(buffer.offset + buffer.size > len(packed) for buffer in external_buffers):
            raise ValueError('The source external-weight range is invalid.')
        payload_digest = hashlib.sha256(memoryview(packed)[external_start:]).hexdigest()
    if len(model.subgraphs) != 1:
        raise ValueError('Require one complete encoder subgraph.')
    graph = model.subgraphs[0]
    if len(graph.inputs) != 3:
        raise ValueError('Require the original three-input complete encoder.')
    budget = manifest['profile']['max_num_patches']
    bias = schema.TensorT()
    bias.shape = np.array([1, budget], dtype=np.int32)
    bias.type = schema.TensorType.FLOAT32
    bias.buffer = 0
    bias.name = b'pooling_log_weights'
    bias_index = len(graph.tensors)
    graph.tensors.append(bias)
    graph.inputs = np.append(graph.inputs, np.int32(bias_index))
    add_opcode = next(i for i, code in enumerate(model.operatorCodes)
                      if code.builtinCode == schema.BuiltinOperator.ADD)
    operators, modified = [], []
    for operator in graph.operators:
        opcode = model.operatorCodes[operator.opcodeIndex].builtinCode
        if opcode == schema.BuiltinOperator.SOFTMAX:
            tensor = graph.tensors[operator.inputs[0]]
            shape = list(tensor.shape)
            if shape == [1, budget]:
                if tensor.type != schema.TensorType.FLOAT32:
                    raise ValueError('Require float32 pooling activations.')
                weighted = schema.TensorT()
                weighted.shape = tensor.shape.copy()
                weighted.type = tensor.type
                weighted.buffer = 0
                weighted.name = ('weighted_pool_logits_' + str(len(modified))).encode()
                weighted_index = len(graph.tensors)
                graph.tensors.append(weighted)
                addition = schema.OperatorT()
                addition.opcodeIndex = add_opcode
                addition.inputs = np.array([operator.inputs[0], bias_index], dtype=np.int32)
                addition.outputs = np.array([weighted_index], dtype=np.int32)
                addition.builtinOptionsType = schema.BuiltinOptions.AddOptions
                addition.builtinOptions = schema.AddOptionsT()
                addition.builtinOptions.fusedActivationFunction = schema.ActivationFunctionType.NONE
                operators.append(addition)
                modified.append(int(operator.inputs[0]))
                operator.inputs = np.array([weighted_index], dtype=np.int32)
        operators.append(operator)
    expected_heads = 16 if manifest['profile']['embedding_dimension'] == 1152 else 12
    if len(modified) != expected_heads:
        raise ValueError(f'Expected {expected_heads} pooling heads, got {len(modified)}.')
    graph.operators = operators
    for signature in model.signatureDefs or []:
        mapping = schema.TensorMapT()
        mapping.name = b'args_3'
        mapping.tensorIndex = bias_index
        signature.inputs.append(mapping)
    builder = flatbuffers.Builder(1024)
    offset = model.Pack(builder)
    builder.Finish(offset, file_identifier=b'TFL3')
    external_destination = None
    if external_start is not None:
        # LiteRT exports can keep weights after the FlatBuffer. Relocate offsets,
        # then append those bytes unchanged. ModelT.Pack does not append them.
        external_destination = (len(builder.Output()) + 15) // 16 * 16
        relocation = external_destination - external_start
        for buffer in external_buffers:
            buffer.offset += relocation
        del builder
        builder = flatbuffers.Builder(1024)
        offset = model.Pack(builder)
        builder.Finish(offset, file_identifier=b'TFL3')
        if (len(builder.Output()) + 15) // 16 * 16 != external_destination:
            raise ValueError('External offset serialization changed header length.')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('wb') as stream:
        stream.write(builder.Output())
        if external_start is not None:
            stream.write(bytes(external_destination - stream.tell()))
            stream.write(memoryview(packed)[external_start:])
    if external_start is not None and args.out.stat().st_size != external_destination + len(packed) - external_start:
        raise ValueError('The external-weight output is incomplete.')
    del builder, model, graph, packed
    gc.collect()
    manifest.update(model_file=args.out.name, model_sha256=sha(args.out),
                    model_bytes=args.out.stat().st_size, source_model_sha256=sha(source),
                    adaptation='Add log weights to pooling only. Keep transformer masks unchanged.',
                    modified_pooling_heads=len(modified), numerical_validation='pending')
    if external_start is not None:
        with args.out.open('rb') as stream:
            stream.seek(external_destination)
            actual_payload = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual_payload != payload_digest:
            raise ValueError('The external model weights changed.')
        manifest.update(external_weight_buffers=len(external_buffers),
                        external_payload_sha256=payload_digest,
                        external_payload_unchanged=True)
    manifest['inputs'].append(dict(dtype='float32', index=bias_index,
                                   logical_name='pooling_log_weights', name='pooling_log_weights',
                                   shape=[1, budget], signature_name='args_3'))
    manifest['operators']['ADD'] += len(modified)
    if 'serving_default' in manifest.get('signatures', {}):
        manifest['signatures']['serving_default']['inputs'].append('args_3')
    args.out.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({key:manifest[key] for key in ('model_file','model_bytes','model_sha256',
                                                   'source_model_sha256','modified_pooling_heads')}))


if __name__ == '__main__':
    main()
