# Bootstrap Rules

Read the workspace `CLAUDE.md` before you change this directory.

The bootstrap MUST run without a Hugging Face token after model bundle installation.
The bootstrap MUST bind to loopback by default.
The bootstrap MUST NOT require `llama-swap`.
The Apple Silicon instructions and the Selectel instructions MUST stay separate.
Do not commit model tarballs, extracted model files, virtual environments, logs, or runtime state.
