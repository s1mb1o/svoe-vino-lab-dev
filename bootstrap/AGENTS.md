# Bootstrap Rules

Read the workspace `CLAUDE.md` before you change this directory.

The bootstrap MUST run without a Hugging Face token after model bundle installation.
The bootstrap MUST bind to loopback by default.
The bootstrap MUST NOT require `llama-swap`.
The bootstrap MUST use the model `qwen3.5-9b`. Do not change it to `qwen3.5-9b-nvfp4`: the bootstrap is deployed on generic GPUs, and `qwen3.5-9b-nvfp4` is the model of the gx10 gateway only (owner rule, 2026-09-29).
The bootstrap MUST use the model `qwen3.5-9b`. Do not change it to `qwen3.5-9b-nvfp4`: the bootstrap is deployed on generic GPUs, and `qwen3.5-9b-nvfp4` is the model of the gx10 gateway only (owner rule, 2026-09-29).
The Apple Silicon instructions and the Selectel instructions MUST stay separate.
Do not commit model tarballs, extracted model files, virtual environments, logs, or runtime state.
