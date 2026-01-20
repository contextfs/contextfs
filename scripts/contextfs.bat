@echo off
REM ContextFS CLI wrapper for Windows (Docker)
REM
REM Setup:
REM   1. Set CONTEXTFS_WORKSPACE to your projects folder:
REM      setx CONTEXTFS_WORKSPACE "C:\Users\YourName\Projects"
REM   2. Add this script's directory to your PATH
REM   3. Start the container: docker-compose --profile local up -d
REM
REM Usage:
REM   contextfs memory list
REM   contextfs search "query"
REM   contextfs index /workspace/my-repo

IF "%CONTEXTFS_WORKSPACE%"=="" (
    echo Warning: CONTEXTFS_WORKSPACE not set. Using current directory.
    echo Set it with: setx CONTEXTFS_WORKSPACE "C:\path\to\your\projects"
)

docker exec -it contextfs-local python -m contextfs.cli %*
