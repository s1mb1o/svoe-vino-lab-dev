#!/bin/sh
set -eu
python3 -m unittest discover -s tests -p test_local_comparison.py -q
python3 -m unittest discover -s tests -p test_pipelines.py -q
python3 -m unittest discover -s tests -p test_embedding_run.py -q
python3 -m unittest discover -s tests -p test_run_steps.py -q
python3 -m unittest discover -s tests -p test_rebuild_on_run.py -q
