# Preliminary local-profile readiness

Recorded on 2026-09-27 at approximately 04:25 MSK.
This note records a read-only delegated inspection before G10.
It is not a launch gate. Recheck capacity when G10 is next.
No torch import, model load, GPU context, network request, or file write occurred
in the inspection. This parent report is the first saved output.

## Runtime and model cache

The runtime has Python 3.14.7, torch 2.14.0, torchvision 0.29.0, and transformers 5.17.0.
The existing local index records the same versions and device `mps`.
The model configuration, image processor, weights, and tokenizer files are cached.
The cached revision is `cc24074f717b612951c2dead130904ab9b65a81e`.
The safetensors header matches the file length. The payload hash was not checked.
The header records approximately 1.13567 billion float32 parameters.
The weight payload occupies 4.231 GiB and includes both text and vision towers.

`LocalBackend` in `pipeline/build_embeddings.py` loads the full float32 model.
It selects MPS when available and otherwise selects CPU.
A planning estimate is 5 to 8 GiB resident memory.
A conservative total additional allowance is 12 to 16 GiB for loading and transient work.
Neither value is a measured peak on this Mac.
Do not add these overlapping estimates as if both were separate measured allocations.

## Capacity observation

The Mac is an M2 Max with 32 GiB RAM.
The inspection found approximately 12.13 GiB of compressor occupancy.
Swap use was 37.98 GiB of 39 GiB. Swap free was 1.03 GiB.
`memory_pressure` reported 33 percent free and pressure code 2.
The free percentage is not a guarantee of allocatable model capacity.
This observation does not pass a launch gate for the proposed additional allowance.
Do not stop applications or services to make capacity.
Do not mark the four local profiles failed from this preliminary snapshot.
Recheck current memory and record a justified budget when G10 becomes runnable.

## Cache and network limits

The current `from_pretrained` calls do not set `local_files_only=True`.
The inspecting shell had no Hugging Face offline flags.
The lab-server child environment was not verified.
Cached files alone do not prove that loading will make no metadata network request.
A model metadata request is distinct from transferring query photos to an external
recognizer. The external photo recognizer remains excluded.

The `sentencepiece` and `protobuf` packages are absent.
This path uses `AutoImageProcessor` and does not instantiate a tokenizer.
Their absence alone does not establish a failure in this image-only path.

## Retained observation details

`system_profiler` emitted the timestamp 2026-09-27 04:21:30.030 MSK.
The memory commands ran during that inspection.
Separate timestamps for each command were not retained.
The successful commands were:

```sh
system_profiler SPHardwareDataType
vm_stat
memory_pressure -Q
/usr/sbin/sysctl hw.memsize hw.model hw.ncpu vm.swapusage kern.memorystatus_vm_pressure_level
```

The cached snapshot directory is:

```text
/Users/ashmelev/.cache/huggingface/hub/models--google--siglip2-so400m-patch16-naflex/snapshots/cc24074f717b612951c2dead130904ab9b65a81e
```

The header has 1,135,670,962 float32 parameters and 4,542,683,848 payload bytes.
The vision tower has 427,888,064 parameters.
The text tower has 707,782,896 parameters.
Two scalar parameters complete the total.
Package versions came from `importlib.metadata` in the configured interpreter.
Only standard-library `struct` and `json` were used to inspect the weight header.
The agent confirmed that the 12 to 16 GiB allowance includes the resident estimate.

## Capacity-policy scope audit

A read-only audit on 2026-09-27 separates three rules.
The original 20 GB reserve in `GPU_SERVERS.md` applies explicitly to GX10.
The current queue helper applies a minimum 20 GiB reserve to every backend.
The current heartbeat also says every unloaded model.
The current execution must retain that broader rule until an explicit scope amendment.
No helper, service, or launch policy was changed by the audit.

A conservative 16 GiB total additional allowance plus the current 20 GiB reserve
requires 36 GiB on a 32 GiB Mac. Cached weights do not make the allowance zero.
Check actual capacity again when G10 becomes next.
If the gate cannot pass, record four explicit `unavailable` outcomes for capacity with
fresh evidence and the policy reason. Do not call these inference failures.
Do not omit the profiles or lower the reserve silently.
The previous memory-pressure observation does not justify a launch.

A host-specific policy would require an explicit recorded amendment before use.
The audit proposed 16 GiB total additional peak plus 4 GiB headroom, one worker,
at least 20 GiB directly reported free physical memory, normal pressure in two
samples 30 to 60 seconds apart, and no sustained swap-out growth.
These are proposed conservative allowances, not measured safe limits.
They are not authorized for execution by this note.
Remote SAM3 use would still require the unchanged GX10 checks.

## Queue status compatibility

The reporter recognizes `status: unavailable` as terminal but unsuccessful.
It does not recognize `unavailable_capacity` as terminal.
For a profile that never launched, keep `attempts: []`, `run_id: null`, and `pid: null`.
Keep `authorized_to_start: true` so the profile stays in the 53-profile denominator.
Put the capacity reason, evidence path, and evidence SHA-256 in `reason`.
Do not fabricate an unavailable inference attempt.
The launcher does not treat an unavailable attempt as terminal.
A fully terminal queue with unavailable profiles reports `terminal_with_failures`.
The reporter can exit zero for a partial snapshot; inspect the report status.
No local profile has been marked unavailable by this audit.
