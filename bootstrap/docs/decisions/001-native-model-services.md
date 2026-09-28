# Decision 001: Native Model Services

Date: 2026-09-28

## Context

The existing GX10 host runs independent FastAPI model services.
The hackathon bootstrap must run on Apple Silicon and on an NVIDIA GPU host.

## Options

### Native services on both platforms

This option uses one process for each model.
It uses one small compatibility gateway.
It keeps one operational model on both platforms.

### Native Apple Silicon and Docker Compose on NVIDIA

This option gives a reproducible NVIDIA environment.
It creates two deployment models.
Docker is not present on the supplied NVIDIA host.

### One multi-model process

This option gives one server process.
It couples model lifecycles and increases memory risk.

## Decision

Use native services on both platforms.
Use one process for each model.
Use a small compatibility gateway.

The QR scanner can stay active because it uses the CPU.
Run one accelerator model at a time by default.

## Consequences

The deployment has one Python environment and one source tree.
The gateway keeps the existing public API paths.
An operator must select the active accelerator model.
The runtime does not provide automatic least-recently-used model switching.
