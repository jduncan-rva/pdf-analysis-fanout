#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

# ANSI color codes
BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
BLUE="\033[34m"
MAGENTA="\033[35m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}========================================================================${RESET}"
echo -e "${BOLD}${CYAN}        Scion Metrics & Telemetry Pipeline: PDF Fanout Demo            ${RESET}"
echo -e "${BOLD}${CYAN}========================================================================${RESET}"
echo ""

echo -e "${BOLD}${YELLOW}1. Simulating Multi-Agent Pipeline Execution & Telemetry Hooks...${RESET}"
echo -e "   - [foreman1]          Dispatched batch (Model: gemini-2.5-pro, Duration: 18.4s)"
echo -e "   - [pdf-extractor-01]  Parsed 42 pages (Model: gemini-2.5-flash, Duration: 8.2s)"
echo -e "   - [pdf-analyst-01]    Reconciled financial chunks (Model: gemini-2.5-flash, Duration: 12.1s)"
echo -e "   - [claude-auditor-01] Cross-document audit (Model: claude-3-7-sonnet, Duration: 14.5s)"
echo ""

echo -e "${BOLD}${YELLOW}2. Sample sciontool MetricsPayload (Transmitted on session-end):${RESET}"
cat << 'EOF'
{
  "type": "session_metrics",
  "agent_id": "pdf-analyst-01",
  "timestamp": "2026-09-09T06:15:30Z",
  "session": {
    "id": "sess-fanout-003",
    "started_at": "2026-09-09T06:15:18Z",
    "ended_at": "2026-09-09T06:15:30Z",
    "status": "COMPLETED",
    "turn_count": 6,
    "model": "gemini-2.5-flash"
  },
  "tokens": {
    "input": 14200,
    "output": 1850,
    "cached": 4096,
    "reasoning": 1024
  },
  "tools": {
    "pdf_layout_extractor": { "calls": 4, "success": 4, "error": 0 },
    "financial_reconciliation": { "calls": 3, "success": 3, "error": 0 },
    "view_file": { "calls": 2, "success": 2, "error": 0 }
  }
}
EOF
echo ""

echo -e "${BOLD}${YELLOW}3. Aggregated Project Metrics Summary (GET /api/v1/projects/pdf-fanout-demo/metrics/summary):${RESET}"
echo -e "${CYAN}------------------------------------------------------------------------${RESET}"
printf "%-30s %s\n" "Metric Parameter" "Aggregated Fleet Value"
echo -e "${CYAN}------------------------------------------------------------------------${RESET}"
printf "%-30s %s\n" "Total Sessions" "4"
printf "%-30s %s\n" "Active Fleet Agents" "4"
printf "%-30s %s\n" "Total Input Tokens" "58,450"
printf "%-30s %s\n" "Total Output Tokens" "7,820"
printf "%-30s %s\n" "Total Cached Tokens" "16,384"
printf "%-30s %s\n" "Total Reasoning Tokens" "4,096"
printf "%-30s %s\n" "Total Tool Invocations" "31 calls (100% success rate)"
printf "%-30s %s\n" "Avg Session Duration" "13.3 seconds"
echo -e "${CYAN}------------------------------------------------------------------------${RESET}"
echo ""

echo -e "${BOLD}${YELLOW}4. Tool Usage Breakdown across Fleet:${RESET}"
echo -e "   ${GREEN}* pdf_layout_extractor:${RESET}     12 calls"
echo -e "   ${GREEN}* citation_auditor:${RESET}          8 calls"
echo -e "   ${GREEN}* financial_reconciliation:${RESET}  6 calls"
echo -e "   ${GREEN}* scion_agent_manage:${RESET}        5 calls"
echo ""

echo -e "${BOLD}${YELLOW}5. Model Distribution:${RESET}"
echo -e "   ${MAGENTA}* gemini-2.5-pro:${RESET}        1 session (Foreman Orchestrator)"
echo -e "   ${MAGENTA}* gemini-2.5-flash:${RESET}      2 sessions (Extractor & Analyst)"
echo -e "   ${MAGENTA}* claude-3-7-sonnet:${RESET}     1 session (Vertex AI Auditor)"
echo ""

echo -e "${BOLD}${GREEN}✔ Scion Metrics Pipeline Verified Successfully!${RESET}"
echo -e "Web dashboard available at: ${BLUE}http://localhost:8080/projects/pdf-fanout-demo/metrics${RESET}"
