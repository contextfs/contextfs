# ContextFS CLI wrapper for Windows PowerShell (Docker)
#
# Setup:
#   1. Set CONTEXTFS_WORKSPACE environment variable:
#      [Environment]::SetEnvironmentVariable("CONTEXTFS_WORKSPACE", "C:\Users\YourName\Projects", "User")
#   2. Add this script's directory to your PATH, or create an alias:
#      Set-Alias contextfs "C:\path\to\contextfs.ps1"
#   3. Start the container: docker-compose --profile local up -d
#
# Usage:
#   contextfs memory list
#   contextfs search "query"
#   contextfs index /workspace/my-repo

if (-not $env:CONTEXTFS_WORKSPACE) {
    Write-Warning "CONTEXTFS_WORKSPACE not set. Using current directory."
    Write-Warning "Set it with: [Environment]::SetEnvironmentVariable('CONTEXTFS_WORKSPACE', 'C:\path\to\projects', 'User')"
}

# Pass all arguments to the containerized CLI
docker exec -it contextfs-local python -m contextfs.cli @args
