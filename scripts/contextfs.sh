#!/bin/bash
# ContextFS CLI wrapper for Mac/Linux (Docker)
#
# Setup:
#   1. Set CONTEXTFS_WORKSPACE in your shell profile (~/.bashrc, ~/.zshrc):
#      export CONTEXTFS_WORKSPACE="$HOME/Projects"
#   2. Add alias to your shell profile:
#      alias contextfs="/path/to/contextfs.sh"
#      # Or add scripts directory to PATH
#   3. Start the container: docker-compose --profile local up -d
#
# Usage:
#   contextfs memory list
#   contextfs search "query"
#   contextfs index /workspace/my-repo

if [ -z "$CONTEXTFS_WORKSPACE" ]; then
    echo "Warning: CONTEXTFS_WORKSPACE not set. Using current directory." >&2
    echo "Set it in ~/.bashrc or ~/.zshrc:" >&2
    echo '  export CONTEXTFS_WORKSPACE="$HOME/Projects"' >&2
fi

# Pass all arguments to the containerized CLI
docker exec -it contextfs-local python -m contextfs.cli "$@"
