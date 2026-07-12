#!/usr/bin/env bash
# 确保使用 Node >= 20.19（Vite 7 要求），不依赖终端是否 source 过 bashrc
set -euo pipefail

use_node() {
  export PATH="$1:$PATH"
}

if [ -s "$HOME/.nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.nvm"
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  nvm use 22.12.0 --silent 2>/dev/null || nvm use default --silent 2>/dev/null || true
fi

if ! node -e 'const [maj,min]=process.versions.node.split(".").map(Number); process.exit(maj>20||(maj===20&&min>=19)?0:1)' 2>/dev/null; then
  for dir in /opt/node/bin "$HOME/.nvm/versions/node/v22.12.0/bin"; do
    if [ -x "$dir/node" ]; then
      use_node "$dir"
      break
    fi
  done
fi

if ! node -e 'const [maj,min]=process.versions.node.split(".").map(Number); process.exit(maj>20||(maj===20&&min>=19)?0:1)' 2>/dev/null; then
  echo "错误: 需要 Node >= 20.19（当前: $(node -v 2>/dev/null || echo 未知)）" >&2
  echo "请执行: source ~/.bashrc  或  nvm install 22.12.0" >&2
  exit 1
fi

exec "$@"
