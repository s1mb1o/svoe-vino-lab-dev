# Final G10 capacity outcome

At 06:51:39 MSK on 2026-09-27, all 49 remote attempts were terminal.
The parent then read current Mac hardware, VM, swap, pressure, and process state.
The existing queue check found no active measurement or profile job.

The four authorized local profiles are **unavailable under the current memory policy**.
They have no launch attempt, PID, or run ID. They are not inference failures.
They remain in the 53-profile denominator.

The Mac has 32 GiB of physical RAM. The conservative total additional allowance is 16 GiB.
This allowance includes loading, resident model memory, and transient work. It is not a measured peak.
The unchanged queue helper requires a further 20 GiB reserve for every backend.
The required 36 GiB exceeds the physical upper bound before existing memory use.
Waiting for an application to release memory cannot satisfy this unchanged 36 GiB requirement.
The original infrastructure reserve targets GX10, but this queue explicitly applies the broader gate.
No host-specific policy amendment was authorized or applied.
This result does not prove that the model can never run on this Mac under another policy.

The fresh observation also records pressure code 2, 35.35 GiB swap used, and 0.65 GiB swap free.
Compressor occupancy is 11.11 GiB. Direct free pages total approximately 0.078 GiB.
The memory-pressure tool reports 40 percent free. That figure is not allocatable model capacity.
The capacity decision does not treat swap or compressed memory as a guaranteed GPU allocation.

No model was loaded. No inference request, metadata request, or source-photo transfer was made.
No application or service was stopped. The parent did not reduce the memory reserve.
Weight payload hashes and the lab-server child offline environment remain unverified.
Capacity failed before those checks could authorize a launch.

| Profile | Status | Attempts | Workers if runnable |
|---|---|---:|---:|
| `local-siglip2-p256-as-is` | unavailable | 0 | 1 |
| `local-siglip2-p256-crop` | unavailable | 0 | 1 |
| `barcode-local-siglip2-p256-as-is` | unavailable | 0 | 1 |
| `barcode-local-siglip2-p256-crop` | unavailable | 0 | 1 |

Evidence: [fresh observations](g10-readiness-final.json), [capacity decision and hashes](g10-capacity-decision.json),
and [policy scope and allowance](local-readiness-preliminary.md).
