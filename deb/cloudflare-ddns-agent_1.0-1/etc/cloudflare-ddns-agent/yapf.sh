#!/bin/bash
echo 'Running yapf...'
PYTHONPATH=/home/dmiddleton/Projects/Other/yapf python /home/dmiddleton/Projects/Other/yapf/yapf --verify -i agent.py
echo 'Done.'
