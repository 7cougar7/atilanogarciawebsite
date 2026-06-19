#!/usr/bin/env bash
pip install -r requirements.txt
python scripts/setup_fontawesome.py

# Build the React/Vite frontend if Node is available on the build host. If it is not,
# the committed mainwebsite/static/dist/ bundle is used as-is. Either way the bundle is
# published by collectstatic below. A failed build aborts the deploy (better than
# shipping a stale/broken bundle).
if command -v npm >/dev/null 2>&1; then
    echo "Node detected — building frontend with Vite"
    npm ci && npm run build || { echo "Frontend build failed"; exit 1; }
else
    echo "Node not found — using the committed mainwebsite/static/dist/ bundle"
fi

python manage.py migrate
python manage.py collectstatic --noinput --clear
