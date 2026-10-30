# Project Synopsis & Ethical Compliance Report

**HCLTech Career Shaper Programme | Project No. 77**  
**Project Title:** Agentic AI Task Planner  
**Domain:** Artificial Intelligence & Autonomous Agent Systems  
**Status:** Ready for Submission  

---

## 1. Problem Statement (5W1H Format)

- **What:** Contemporary conversational AI systems frequently fail to accomplish complex, multi-stage workflows because standard chatbots generate textual suggestions without executing the underlying tasks. Autonomous agent systems that integrate tool use can solve complex problems, but unconstrained tool execution introduces substantial risks of unintended side effects, security breaches, or system failures.
- **Why:** Real-world enterprise operations require dependable AI systems that can decompose unstructured goals into orderly execution plans, invoke domain-specific tools (calculators, data parsers, search engines, APIs), enforce safety boundaries before irreversible actions (e.g. executing code or sending messages), and provide a full execution audit log.
- **Who:** Enterprise operators, data analysts, and knowledge workers who require autonomous task completion paired with human oversight and verifiable auditability.
- **Where:** Deployed within modern cloud or on-premise analytical environments with sandboxed execution runtimes.
- **When:** Whenever complex, multi-step analytical, mathematical, computational, or research tasks must be executed without continuous manual step-by-step guidance.
- **How:** By utilizing a cyclic state graph architecture (LangGraph) integrated with Google Gemini LLMs for planning, an Abstract Syntax Tree (AST) evaluator for mathematics, sandboxed subprocesses for code execution, Human-in-the-Loop (HITL) approval gates for sensitive operations, and an SQLite database for observability.

---

## 2. Proposed Solution & Technical Approach

The proposed solution is a modular, production-ready Agentic AI Task Planner featuring:
1. **Goal Decomposition Engine:** Translates natural language requests into structured execution plans using Gemini LLM and intelligent heuristic fallbacks.
2. **Tool Registry & Execution Sandbox:** Eight sandboxed tools (AST Calculator, Directory-Sandboxed File Reader, Pandas Data Analyzer, Web Researcher, Subprocess Code Executor, Watermarked Email Drafter, HTTP API Caller, and Markdown Report Writer).
3. **Cyclic Orchestration State Graph:** Implemented via LangGraph with conditional routing for step execution, error handling with configurable retry budgets, and human-in-the-loop pause/resume states.
4. **Dual Data Architecture:** Preserves the supplied historical dataset (`dataset.csv`) as strictly read-only for Exploratory Data Analysis, while storing live execution traces in an independent SQLite database (`execution_logs.db`).
5. **Interactive UI & Observability:** Streamlit multi-page interface featuring a live Task Planner, an Execution Log Explorer with tool metrics, and an EDA Dashboard with seven distinct visualisations.

---

## 3. System Architecture & Data Flow

```
[User Input] ---> [Streamlit UI] ---> [LangGraph State Machine]
                                             |
                   +-------------------------+-------------------------+
                   |                         |                         |
            [Planner Node]           [Executor Node]          [Error Handler]
                   |                         |                         |
          (Gemini 1.5 / Rules)      [Tool Registry]           (Retry Policy)
                                             |
                         +-------------------+-------------------+
                         |                   |                   |
                     Safe Tools         Sensitive Tools    [SQLite DB]
                   (Calc, Files,       (Code, Emails)     (Audit Traces)
                    Search, Data)             |
                                      [HITL Approval Gate]
```

### Data Flow Diagram (DFD Level 0):
- **Inputs:** User natural language task description, execution configuration (auto-approve toggle, retry limits), and human approval decisions.
- **Processing:** Goal decomposition -> Step validation -> Sensitivity check -> Tool execution -> Error handling/retries -> Final synthesis.
- **Outputs:** Synthesized task report, execution timeline, tool output previews, Plotly performance analytics, and SQLite trace records.

---

## 4. Technology Stack

| Category | Technology & Version | Role |
|----------|----------------------|------|
| Language | Python 3.11+ / 3.14 | Core backend and logic |
| Orchestration | LangGraph 1.2+, LangChain 1.4+ | Cyclic state graph orchestration and tool abstraction |
| Model API | Google Gemini 1.5 Flash / Pro | Goal decomposition and report synthesis |
| Presentation | Streamlit 1.66+ | Multi-page interactive user interface |
| Data Processing | Pandas 2.3+ | Dataframe manipulation, aggregations, and EDA |
| Database | SQLite 3 | Runtime trace persistence (WAL mode, foreign keys) |
| Visualisation | Plotly 7.1+, Matplotlib 3.11+, Seaborn 0.13+ | Interactive and static analytics dashboards |
| Validation & Config | Pydantic 2.13+, Pydantic-Settings 2.16+ | Validated environment variables and settings |
| Testing | Pytest 9.0+, Pytest-Asyncio, Pytest-Mock | 93-test automated test suite (100% pass) |

---

## 5. Dataset Details & Preprocessing

- **Dataset Source:** Supplied historical agent execution log (`dataset.csv`).
- **Dimensions:** 500 rows × 7 columns.
- **Key Columns:**
  - `task_id` (object): Categorical task identifier (T001–T100, 100 unique tasks).
  - `step_id` (int64): Global sequential counter (1–500).
  - `tool_called` (object): Categorical tool name (calc, email_draft, web_search, code_exec, api_call, file_read).
  - `tool_success` (int64): Binary flag (1 = success, 0 = failure).
  - `tokens_used` (int64): Token consumption per step (109 to 3,999; mean = 2,055).
  - `duration_s` (float64): Execution latency in seconds (0.18s to 29.89s; mean = 15.1s).
  - `retry_count` (int64): Retries attempted (0, 1, or 2).
- **Data Quality Findings (Documented in EDA):**
  - Zero missing values and zero duplicate rows.
  - `step_id` represents a global chronological counter rather than resetting per task.
  - Supplied dataset is an operational execution log without prompt text or tool payloads; runtime database resolves this by capturing complete `user_goal`, `tool_input`, `tool_output`, and plan JSON.
- **Data Dictionary:** All 7 column descriptions completed in `data_dictionary.csv` with RFC 4180 compliant quotation.

---

## 6. Key Results & Performance Metrics

1. **Overall Tool Reliability:** 89.2% overall success rate across 500 historical execution steps; runtime agent implements automatic retries with graceful fallbacks.
2. **Mean Execution Latency & Efficiency:** 15.1 seconds average step latency; AST-based calculator responds in under 0.01 seconds without LLM overhead.
3. **Safety & Zero Security Breaches:** 100% interception of sensitive operations (`code_exec` and `email_draft`) at the HITL approval gate, preventing unauthorized subprocess executions or unapproved emails.
4. **Test Suite Coverage:** 93 automated tests passed with 0 failures across configuration, database, EDA, all 8 tools, planner, executor, and LangGraph state machine.

---

## 7. Challenges Faced & Engineering Solutions

| Challenge | Impact | Engineering Solution |
|-----------|--------|----------------------|
| **Arbitrary Code Injection in Calculator** | Traditional `eval()` allows malicious code execution (`os.system`). | Built an Abstract Syntax Tree (AST) evaluator (`ast.parse`) that explicitly whitelists only mathematical binary ops and functions, rejecting statements, imports, and attributes. |
| **Directory Traversal Vulnerabilities** | Tools might access sensitive host files (`../../Windows/System32`). | Implemented strict path resolution with `is_path_allowed()` enforcing file boundaries within configured directories only. |
| **LLM Quota Expiration & Offline Testing** | Agent would fail if API keys are missing or free quotas expire. | Built a dual planning mechanism: uses Google Gemini when configured, and falls back to an intelligent heuristic intent analyzer that produces valid multi-step plans offline. |
| **Separation of Read-Only Dataset vs Runtime Logs** | Risk of polluting or overwriting benchmark data with live agent traces. | Architected a strict two-database separation: `dataset.csv` is opened read-only, and runtime traces are written to an isolated SQLite database (`execution_logs.db`). |

---

## 8. References

1. Yao, S., Zhao, J., Yu, D., et al. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models*. International Conference on Learning Representations (ICLR).
2. LangChain Team. (2024). *LangGraph: Building Cyclical Agent Architectures and State Machines*. Documentation: https://langchain-ai.github.io/langgraph/
3. Google DeepMind. (2024). *Gemini 1.5: Unlocking Multimodal Understanding Across Millions of Tokens of Context*. Technical Report, Google AI.
4. McKinney, W. (2022). *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. 3rd Edition, O'Reilly Media.

---

## 9. Ethical Compliance Declaration

I hereby declare that this individual academic project:
- ✅ Implements Human-in-the-Loop (HITL) approval gates before sensitive actions (file modifications, code execution, email drafting).
- ✅ Enforces draft-only mode for email operations with explicit watermarking (`[DRAFT — NOT SENT]`).
- ✅ Isolates code execution within sandboxed subprocesses with strict timeout boundaries.
- ✅ Maintains complete auditability by logging all tool calls, inputs, outputs, and timestamps.
- ✅ Preserves original datasets without fabrication, unauthorized modification, or data corruption.
- ✅ Adheres strictly to the ethical requirements established in the HCLTech Career Shaper Programme.
