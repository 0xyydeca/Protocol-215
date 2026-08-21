#!/bin/zsh
set -e
cd "$(dirname "$0")"
export PATH="$(pwd)/.tools:$HOME/.local/bin:/opt/homebrew/bin:$PATH"
echo "cwd: $(pwd)"
echo "uv: $(command -v uv) — $($(command -v uv) --version 2>/dev/null || echo missing)"
echo "claude: $(command -v claude || echo missing)"
exec claude "$@"
