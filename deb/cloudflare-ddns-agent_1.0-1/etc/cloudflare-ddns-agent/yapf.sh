#!/bin/bash
echo 'Running yapf...'
PYTHONPATH=/Users/Daniel/Projects/Other/yapf python /Users/Daniel/Projects/Other/yapf/yapf --verify -i agent.py
echo 'Done.'
