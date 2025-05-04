#!/bin/bash
set -x

# Start Gunicorn
gunicorn -w 1 -k uvicorn.workers.UvicornWorker app:app 