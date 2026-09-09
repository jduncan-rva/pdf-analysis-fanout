# Scion Agent Chat & Interactivity Guide

This guide details the capabilities, workflows, and protocols for interacting with autonomous agents in the `pdf-analysis-fanout` project using Scion's **Native Web Chat**, CLI, and external federation bridges.

---

## 🏛️ Architecture & Overview

Scion promotes chat to a first-class, top-level workspace in the Web Dashboard (a fourth `ShellType` alongside standalone, profile, and app). The chat system is backed by a persistent PostgreSQL event store (`webchat_*` tables), real-time Server-Sent Events (SSE) streams, and an in-process FanOut Message Broker.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Scion Web Dashboard                           │
│  ┌───────────────────────────┐  ┌────────────────────────────────────┐  │
│  │   Thread Rail (Sidebar)   │  │       Main Chat Panel              │  │
│  │  • PDF Fanout Space       │  │  • Dialogue / Markdown Bubbles     │  │
│  │    ├── #general           │  │  • Interactive Code / Diffs        │  │
│  │    └── #reconciliation    │  │  • Clickable /workspace/ Paths     │  │
│  │  • DMs (H2A / H2H)        │  │  • Chat ⇄ Execution Log Toggle    │  │
│  │    ├── @foreman1          │  │  • Visibility: Conv | Verb | Full  │  │
│  │    └── @claude-probe      │  │  • @mention Autocomplete Composer  │  │
│  └───────────────────────────┘  └────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                             (SSE / REST API)
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │    Scion Hub (Server)        │
                      │  • WebChatStore (PostgreSQL) │
                      │  • FanOut EventBus           │
                      │  • Mention Parser & Dispatch │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │   GKE Agents (Pods)          │
                      │  • @foreman1 (Antigravity)   │
                      │  • @claude-probe (Claude)    │
                      └──────────────────────────────┘
```

---

## 💬 Core Interaction Surfaces

### 1. Project Spaces & Collaborative Threads
* **Project Spaces:** Conversations are organized into project-scoped spaces (e.g. `PDF Fanout Analysis Demo`).
* **Default & Custom Threads:** Every project space includes a `#general` discussion thread and supports creating custom threads (e.g. `#pdf-ingestion-debug`, `#financial-reconciliation`).
* **Context Preservation:** Switching between dashboard views (such as agent detail or run views) and Chat maintains your active project and agent context without page reloads.

### 2. 1-on-1 Direct Messaging (DMs)
* **Human-to-Agent (H2A):** Direct 1-on-1 conversations with specific agents (e.g. `@foreman1`).
* **Human-to-Human (H2H):** Direct messaging between team members.
* **DM-to-Thread Promotion:** If a 1-on-1 conversation with an agent develops context valuable to the team, click **Promote to Thread** in the DM header. The messages are atomically re-keyed into a shared space thread in real time.

---

## 🎯 Addressing & Targeting Agents

### Interactive `@-Mentions`
* **Fuzzy Autocomplete:** Typing `@` in the chat composer triggers a popup list of active agents in the project with full keyboard navigation (`Arrow` keys to select, `Enter` to insert).
* **Code Fence Guard:** Autocomplete is automatically disabled inside Markdown code fences (```` ``` ```` blocks) so code snippets do not trigger unwanted popups.
* **Fan-Out Limits:** A single message can fan out to a maximum of **10 recipients** per `@-mention` broadcast.
* **Default Agent Disambiguation:** When sending an untargeted instruction in a multi-agent project space without an explicit `@-mention`, the UI prompts you to choose the target agent or fall back to the project default.

---

## 🔄 Agent Execution & The `ask_user` Loop

### Message Envelopes & Inbound Types
Messages delivered to agents are packaged with standard metadata envelopes:
```text
---BEGIN SCION MESSAGE---
sender: user:Jamie Duncan
type: instruction
thread_id: 4310f489-0e5d-4b3d-9ad0-8d3dfb8a6005
conversation_id: 2103f225-f020-4a1a-9e21-a4443a91f1d0
---
Please audit the ingestion pipeline for PDF statement discrepancies.
---END SCION MESSAGE---
```

Agents discriminate on the message `type`:
| Message Type | Meaning | Action Taken |
|---|---|---|
| `instruction` | Direct task or question sent to the agent | Executes task and responds |
| `mention` | Agent was referenced/CC'd in a message | Analyzes context; responds if addressed |
| `input-needed` | Agent requested input via `ask_user` | Human responds to unblock execution |
| `group-set` | Broadcast message to multiple agents | Acts on the group instruction |
| `state-change` | Status update (e.g. agent stopped/stalled) | Informational |
| `system` | Hub operational notice or delivery notice | Informational / diagnostic |

### Handling `ask_user` (`WAITING_FOR_INPUT`)
1. When an agent requires clarification or human approval, it transitions its state to `WAITING_FOR_INPUT`.
2. An `input-needed` notification is dispatched to the Chat thread and the **Inbox Tray**.
3. Replying to the agent in the chat thread or via CLI delivers the human response directly into the agent's active execution loop, immediately resuming its work.

### Chat ⇄ Log Stream Toggle
The main conversation header includes a **Chat / Log** toggle:
* **Chat Mode:** Focuses on dialogue, formatted responses, markdown tables, and interactive diffs.
* **Log Mode:** Streams raw terminal stdout/stderr and container execution logs in real time.

---

## 📁 Rich Media, Workspace Links & Attachments

* **Clickable Workspace Paths:** File paths starting with `/workspace/...` or `/scion-volumes/...` render as clickable interactive links. Clicking opens a modal file viewer displaying file contents directly from the workspace without leaving chat.
* **Syntax-Highlighted Markdown:** Full Markdown rendering for syntax blocks, LaTeX formulas, and comparison diffs.
* **Developer Attachment Uploads:** Drag-and-drop or paste files directly into the composer. Supports **34+ developer extensions** (`.py`, `.json`, `.yaml`, `.csv`, `.pdf`, `.sql`, etc.) while enforcing security deny-lists against executable binaries.
* **Collapsed Agent-to-Agent (A2A) Messages:** Background communication between sub-agents is collapsed into compact clickable pills (with 2-line truncation and a full-screen expander overlay) to keep main threads clean.

---

## 🎛️ Three-State Visibility Filtering

Filter discussion density on demand (persisted per-thread/agent):
1. **Conversation (Default):** Clean view displaying only direct human instructions and agent responses.
2. **Verbose:** Adds CCs, explicit `@-mentions`, and user-directed warnings.
3. **Full:** Displays all system events, state changes, and background agent-to-agent operations.

---

## 🌐 External Bridges & Federation

### 1. Discord & Telegram
* **Bidirectional Bots:** Interact with project agents directly inside team Discord channels or Telegram groups with synced unread badges and avatar attribution.
* **Outbound Webhooks:** Stream alerts, stage completions, and `ask_user` prompts to external channels.

### 2. A2A Protocol Bridge (Desktop Federation)
Scion implements the open **Google A2A (Agent-to-Agent) Protocol** (JSON-RPC 2.0). You can connect desktop applications like **Claude Desktop** or **Codex Desktop** directly to your hosted GKE agents:

```bash
# 1. Create a Personal Access Token (PAT)
scion token create \
  --name "desktop-chat" \
  --project "PDF Fanout Analysis Demo" \
  --scope agent:message,agent:read \
  --expires 30d

# 2. Query Agent Card
curl -s -H "Authorization: Bearer scion_pat_..." \
  http://localhost:8080/projects/pdf-fanout-analysis-demo/agents/foreman1/.well-known/agent-card.json
```

---

## 💻 CLI Messaging Reference

You can also interact with chat threads and agents from the terminal:

```bash
# Send direct instruction to an agent
scion message @foreman1 "Check the BM25 index status for the last batch."

# Send message with a file attachment
scion message @foreman1 "Review this invoice" --attach sample_statement.pdf

# Broadcast to all agents in the current project
scion broadcast "Deployment rollout starting in 5 minutes."

# Check unread messages in the inbox
scion messages
```
