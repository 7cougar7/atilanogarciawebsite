#!/usr/bin/env bash
pip install -r requirements.txt
python scripts/setup_fontawesome.py

# Build the React/Vite frontend. Render's Python runtime ships an ancient default Node
# (14, EOL) whose npm cannot read our lockfile, so check the MAJOR version and fetch a
# pinned modern Node into the build environment when what's available is too old (or
# absent). The bundle is NOT committed to git (mainwebsite/static/dist/ is gitignored) —
# it is produced fresh here and published by collectstatic below. Any failure aborts.
NODE_MAJOR="$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/')"
if [ -z "$NODE_MAJOR" ] || [ "$NODE_MAJOR" -lt 18 ]; then
    NODE_VERSION=20.18.1
    echo "Node ${NODE_MAJOR:-none} is too old; installing Node ${NODE_VERSION}..."
    NODE_DIR="$PWD/.render-node"
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -o /tmp/node.tar.xz \
        || { echo "Node download failed"; exit 1; }
    mkdir -p "$NODE_DIR"
    tar -xJf /tmp/node.tar.xz -C "$NODE_DIR" --strip-components=1 \
        || { echo "Node extraction failed"; exit 1; }
    export PATH="$NODE_DIR/bin:$PATH"
fi
echo "Building frontend with Node $(node -v), npm $(npm -v)"
npm ci && npm run build || { echo "Frontend build failed"; exit 1; }

python manage.py migrate
python manage.py collectstatic --noinput --clear
