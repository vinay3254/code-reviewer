#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="self-improving-agent"

mkdir -p "$PROJECT_NAME"/{orchestrator,roles,sandbox,memory,llm,benchmark/tasks,prompts,data/chroma}

touch "$PROJECT_NAME"/orchestrator/__init__.py
touch "$PROJECT_NAME"/orchestrator/loop.py
touch "$PROJECT_NAME"/orchestrator/task.py
touch "$PROJECT_NAME"/orchestrator/run_log.py

touch "$PROJECT_NAME"/roles/__init__.py
touch "$PROJECT_NAME"/roles/planner.py
touch "$PROJECT_NAME"/roles/patcher.py
touch "$PROJECT_NAME"/roles/verifier.py

touch "$PROJECT_NAME"/sandbox/__init__.py
touch "$PROJECT_NAME"/sandbox/docker_runner.py
touch "$PROJECT_NAME"/sandbox/Dockerfile.base
touch "$PROJECT_NAME"/sandbox/entrypoint.sh

touch "$PROJECT_NAME"/memory/__init__.py
touch "$PROJECT_NAME"/memory/store.py
touch "$PROJECT_NAME"/memory/embed.py
touch "$PROJECT_NAME"/memory/schema.py

touch "$PROJECT_NAME"/llm/__init__.py
touch "$PROJECT_NAME"/llm/ollama_client.py

touch "$PROJECT_NAME"/benchmark/__init__.py
touch "$PROJECT_NAME"/benchmark/report.py
touch "$PROJECT_NAME"/benchmark/history.jsonl

touch "$PROJECT_NAME"/prompts/planner_system.md
touch "$PROJECT_NAME"/prompts/patcher_system.md
touch "$PROJECT_NAME"/prompts/verifier_system.md
touch "$PROJECT_NAME"/prompts/CHANGELOG.md

cat > "$PROJECT_NAME"/config.yaml << 'EOF'
models:
  planner: qwen2.5-coder:32b
  patcher: qwen2.5-coder:14b
  verifier: qwen2.5-coder:32b
  embedding: nomic-embed-text
retry_cap: 5
sandbox:
  timeout_seconds: 120
  memory_limit: 1g
  cpus: 1
memory:
  top_k: 5
  chroma_path: ./data/chroma
EOF

touch "$PROJECT_NAME"/main.py
touch "$PROJECT_NAME"/README.md

# copy specs into the project for reference during build
mkdir -p "$PROJECT_NAME"/specs
cp ./*.md "$PROJECT_NAME"/specs/ 2>/dev/null || true

echo "Scaffolded $PROJECT_NAME/"
echo "Next: implement M1 per 00-workflow-starter.md — sandbox/docker_runner.py + Dockerfile.base"
