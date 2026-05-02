# cca-foundations-portfolio
Claude learning &amp; experimentation project in preparation for Architect Certification.
Project 1: RAG Knowledge Assistant
Sequence position: First — establishes core API patterns
Time estimate: 6-8 hours over Week 3
Related courses: Building Applications with the Claude API; Claude 101
Domains covered:

Prompt Engineering & Structured Output (20%)
Context Management & Reliability (15%)

What you build: A document Q&A system that ingests a corpus of PDFs or markdown files, chunks them, embeds them into a local vector store, and answers questions using Claude with retrieved context. Returns answers with structured citations to source chunks.
Why this first: It teaches you the fundamental Claude API call patterns — messages, system prompts, structured output, streaming — without the additional complexity of tool use or autonomy. Every subsequent project builds on this foundation.
Domain-credible content suggestion: Use UK financial services regulatory documents (PRA SS1/23, FCA handbooks excerpts, Bank of England papers on AI risk). This makes the project portfolio-credible for both the GS-MD and consulting paths, and overlaps usefully with your Veritas governance work.
Initial setup steps:

Create project-01-rag/ directory in your repo
Install: uv add anthropic chromadb pypdf python-dotenv pydantic
Create directory structure: documents/ (source files), src/ (code), tests/ (validation queries)
Define a Pydantic schema for the structured response (answer text, list of citations with chunk IDs and source documents, confidence score)
Build incrementally: ingestion → chunking → embedding → retrieval → generation. Don't try to build the whole pipeline before testing each step.

Architectural decisions to document in your README: chunking strategy (fixed vs semantic), retrieval count (k), how you handle "I don't know" cases, how you prevent hallucinated citations.

Project 2: Tool-Using Agent with MCP
Sequence position: Second — introduces autonomy via structured tools
Time estimate: 8-10 hours over Week 4
Related courses: Introduction to Model Context Protocol; Building Applications with the Claude API
Domains covered:

Tool Design & MCP Integration (18%)
Prompt Engineering & Structured Output (20%, reinforced)

What you build: A custom MCP server that exposes 3-4 tools, plus a Claude client that uses those tools to answer multi-step questions. The agent should be able to combine tools (e.g., look up a value, then calculate something with it, then format the result).
Why second: It introduces tool use and the MCP protocol specifically, which is the heaviest non-architecture domain. Building your own MCP server (rather than just consuming one) is the difference between knowing MCP exists and actually understanding it — which is what the exam tests.
Domain-credible content suggestion: Build a "Risk Data Query Agent" — tools could include lookup_counterparty_exposure, calculate_var, fetch_market_data, get_regulatory_threshold. Use mocked data (a local JSON file is fine). This connects directly to your Risk Data Engineering function and is a credible consulting demo asset.
Initial setup steps:

Create project-02-mcp-agent/ directory
Install: uv add anthropic mcp pydantic plus any tool-specific libs
Read the official MCP spec at modelcontextprotocol.io end-to-end before writing code. Don't rely solely on the course.
Build the MCP server first as a standalone process — verify it works using the MCP Inspector tool before connecting Claude to it
Then build the Claude client that connects to it via stdio transport
Add a single tool first, get the loop working end-to-end, then add the others

Architectural decisions to document: transport choice (stdio vs HTTP), how you describe tools to Claude (tool definitions matter enormously for accuracy), how you handle tool errors, how many turns you allow before halting.

Project 3: Agentic Workflow with Claude Code SDK
Sequence position: Third — full autonomy and orchestration
Time estimate: 10-12 hours over Week 5
Related courses: Claude Code developer training; Agent Skills course
Domains covered:

Agentic Architecture & Orchestration (27%) — the heaviest domain
Claude Code Configuration & Workflows (20%) — the second heaviest

What you build: A multi-step autonomous agent that decomposes a complex task, plans a sequence of actions, executes them using tools and subagents, recovers from failures, and produces a structured final output. Use the Claude Agent SDK or Claude Code's programmatic interface.
Why third: This is where it all comes together. You're combining tools (from Project 2), structured output (from Project 1), and adding planning, subagents, and failure recovery. This project alone covers 47% of the exam weight, so it deserves the most time.
Domain-credible content suggestion: "Automated Code Review Agent" — given a Git diff, it analyses changes, runs tests, checks for security patterns, looks up internal coding standards, and produces a structured review. This is highly relevant to your day job and a strong consulting deliverable. Alternative: "Data Quality Investigation Agent" that ties to your ARC Flow observability work — given an anomaly alert, it investigates root cause across multiple data sources and proposes remediation.
Initial setup steps:

Create project-03-agentic-workflow/ directory
Install: uv add claude-agent-sdk anthropic (check current package name on Anthropic's docs as this is evolving)
Read Anthropic's "Building Effective Agents" engineering blog post first — it's the conceptual foundation Anthropic itself recommends and likely informs exam questions directly
Define the agent's loop architecture on paper before coding: what's the planning step, what tools are available, what's the termination condition, what's the failure handling
Configure Claude Code with custom commands and a CLAUDE.md for the project — this is examinable content
Build the simplest possible loop (1 tool, 1 step) and verify it terminates cleanly. Then add planning, then add subagents, then add error recovery.

Architectural decisions to document: when you used subagents vs single-agent loops, how you bounded autonomy (max iterations, cost caps), how you handled partial failures, how you structured your CLAUDE.md and skills.

Project 4: Document Analysis & Structured Extraction
Sequence position: Fourth — reliability and validation under real-world data
Time estimate: 5-6 hours over Week 6
Related courses: Building Applications with the Claude API (advanced sections on structured output)
Domains covered:

Prompt Engineering & Structured Output (20%, depth)
Context Management & Reliability (15%, depth)

What you build: A pipeline that processes messy real-world documents (contracts, reports, forms), extracts structured data conforming to a Pydantic schema, validates it, and handles extraction failures gracefully (retry with different prompts, flag for human review, etc.).
Why fourth: It's deliberately scoped smaller than Project 3, but goes deep on reliability — schema validation, retry logic, confidence scoring, edge case handling. The exam tests these patterns explicitly under "Context Management and Reliability."
Domain-credible content suggestion: Lease document extraction — given your recent leasehold/EWS1 experience, you have domain familiarity. Build something that extracts lease length, ground rent terms, service charge structure, restrictive covenants. This is genuinely useful and personal-relevant. Alternative: extract structured data from earnings reports or risk disclosures.
Initial setup steps:

Create project-04-extraction/ directory
Install: uv add anthropic pydantic instructor (instructor library is useful for retry logic)
Define your Pydantic schema with detailed field descriptions — Claude uses these for extraction
Gather a small dataset of 5-10 real documents (anonymise if needed)
Build a baseline extraction first (single shot), then add validation, then add retry-on-failure, then add confidence scoring
Write tests that deliberately use malformed/edge-case documents to verify your reliability patterns work

Architectural decisions to document: how you handle schema validation failures, your retry strategy (different prompt? different model? human escalation?), how you measure extraction quality.

Project 5: Enterprise Automation Pipeline
Sequence position: Fifth — integration and end-to-end orchestration
Time estimate: 6-8 hours over Week 6 (later half)
Related courses: All — this synthesises everything
Domains covered:

All five domains, integrated

What you build: A production-style automation that connects Claude to external systems, processes incoming events, and takes actions based on Claude's output. Should include scheduling/triggering, error handling, observability, and notification of results.
Why last: It's a synthesis project. You're not learning new Claude concepts — you're applying everything from Projects 1-4 in a more realistic deployment context, with the messy realities of integration. This is also the project closest to what enterprise consulting work actually looks like.
Domain-credible content suggestion: Evolve your existing AI newsletter pipeline. You've already built it in Make + Gmail; rebuild it as a proper Python service with: scheduled trigger, Claude-driven research using web search tool, structured curation with reliability checks, formatted output, delivery, logging. This is a real upgrade to existing work, not a throwaway project — and it directly demonstrates "modernising no-code workflows into production architecture," which is a credible consulting positioning. Alternative: a regulatory change monitor that watches FCA/PRA publications and produces structured impact summaries.
Initial setup steps:

Create project-05-automation/ directory
Decide your deployment target: locally scheduled with cron is fine for portfolio purposes; AWS Lambda or a container if you want to demonstrate cloud deployment skills
Install: based on chosen architecture, plus anthropic and any service SDKs (Gmail API, etc.)
Architect on paper first: trigger → ingest → Claude processing → validation → action → notification → log
Build each stage as a testable unit, then wire them together
Add monitoring: at minimum, structured logs that let you reconstruct any run end-to-end

Architectural decisions to document: trigger mechanism, how you handle Claude API failures (retry? fallback model? alert?), how you ensure idempotency, cost monitoring, how you'd extend this to multi-user scale.
