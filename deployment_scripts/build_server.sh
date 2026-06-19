#!/usr/bin/env bash
pip install -r requirements.txt
python scripts/setup_fontawesome.py

# Build the React/Vite frontend. Render's Python runtime has no Node, so fetch a pinned
# Node into the build environment, then build. The bundle is NOT committed to git
# (mainwebsite/static/dist/ is gitignored) — it is produced fresh here and published by
# collectstatic below. Any failure aborts the deploy.
if ! command -v npm >/dev/null 2>&1; then
    NODE_VERSION=20.18.1
    echo "Installing Node ${NODE_VERSION} for the frontend build..."
    NODE_DIR="$PWD/.render-node"
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -o /tmp/node.tar.xz \
        || { echo "Node download failed"; exit 1; }
    mkdir -p "$NODE_DIR"
    tar -xJf /tmp/node.tar.xz -C "$NODE_DIR" --strip-components=1 \
        || { echo "Node extraction failed"; exit 1; }
    export PATH="$NODE_DIR/bin:$PATH"
fi
echo "Building frontend with Node $(node --version), npm $(npm --version)"
npm ci && npm run build || { echo "Frontend build failed"; exit 1; }

python manage.py migrate
python manage.py collectstatic --noinput --clear
