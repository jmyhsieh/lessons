# AI Workflow Composition Resources

## 2026/04+ Claude Code 職能案例

案例庫嚴格篩選條件：來源需在 2026-04-01 之後發布，且案例本身需明確使用 Claude Code。

- [Postmortem: "An update on recent Claude Code quality reports" — Anthropic](https://www.anthropic.com/engineering/april-23-postmortem)
  2026/04 工程與平台治理案例：Claude Code 品質回歸、dogfooding、code review、evals、rollout controls 與 incident learning。
- [Article: "The next big job in tech may be the 'product engineer'" — Business Insider](https://www.businessinsider.com/ai-jobs-product-engineers-managers-2026-4)
  2026/04 產品組織案例：Claude Code 改變工程、PM、設計之間的工作邊界。
- [Article: "AI coders are carrying half-open laptops through airports, offices, and ice rinks" — Business Insider](https://www.businessinsider.com/coders-keep-laptops-open-in-public-ai-agent-2026-5)
  2026/05 工作流案例：Claude Code 出現在產品、創業與 RevOps 類工作流，包含 CRM enrichment 與長時間執行 session。
- [Article: "Inside startups, Claude has already won the AI coding wars" — Business Insider](https://www.businessinsider.com/inside-startups-claude-has-already-won-the-ai-coding-wars-2026-5)
  2026/05 創業與工程案例：Claude Code 用於 QA pipelines、deployment workflows、incident investigation、project management 與 internal tools。
- [Article: "Amazon employees pushed for Claude Code. Now they're getting it — and Codex, too" — Business Insider](https://www.businessinsider.com/amazon-claude-code-codex-all-employees-after-pushback-2026-5)
  2026/05 企業治理案例：Amazon 在先前 production-use 摩擦後，透過 Bedrock/AWS 標準化 Claude Code access。
- [Article: "Claude Code creator says 22-year-old CS grads should found startups" — Business Insider](https://www.businessinsider.com/claude-code-creator-advice-cs-grads-startup-2026-5)
  2026/05 founder 案例：YC founders 據報讓 Claude Code 撰寫大量程式，讓 founder 工作重心轉向 user understanding、specs 與 review。
- [Article: "I'm a product manager who used Claude to build a postcard business in 4 hours" — Business Insider](https://www.businessinsider.com/product-manager-san-francisco-used-claude-build-postcard-business-2026-5)
  2026/05 產品回顧案例：需求、prototype、feedback、payment integration、security review 與 launch 都串到 Claude Code 工作流。
- [Article: "C-suites have decided: It's time to put AI on a diet" — Business Insider](https://www.businessinsider.com/ai-companies-raising-prices-internal-token-limits-openai-anthropic-ipo-2026-6)
  2026/06 成本治理案例：Business Insider 報導 Claude Code 使用讓 Harness 的 AI 成本快速上升，並描述公司透過 training 與 internal tooling 收斂成本。
- [Paper: "Physics Is All You Need? A Case Study in Physicist-Supervised AI Development of Scientific Software" — arXiv](https://arxiv.org/abs/2605.30353)
  2026/05 研究案例：Claude Code 在物理學家監督下建立 scientific software，說明 oracle tests 有效處與 domain knowledge 仍必要處。
- [Paper: "AI Coding Agents Can Reproduce Social Science Findings" — arXiv](https://arxiv.org/abs/2606.11447)
  2026/06 研究 / 資料案例：Claude Code 被評估於 computational social science reproduction tasks，且 prompt framing 會影響 bias。

## Knowledge

- [Postmortem: "An update on recent Claude Code quality reports" — Anthropic](https://www.anthropic.com/engineering/april-23-postmortem)
  Official 2026/04 Claude Code quality postmortem covering reasoning effort, cache behavior, system prompt changes, dogfooding, code review, evals, and rollout controls. Use for: agent-tool governance.
- [Article: "Anthropic's New Product Aims to Handle the Hard Part of Building AI Agents" — WIRED](https://www.wired.com/story/anthropic-launches-claude-managed-agents/)
  2026/04 operations and platform case: Claude Managed Agents provides harnesses, memory, sandboxing, monitoring, permissions, and a Notion client-onboarding demo. Use for: operations/customer-success workflow design.
- [Article: "Anthropic rolls out a host of new AI agents to target financial services" — TechRadar](https://www.techradar.com/pro/anthropic-rolls-out-a-host-of-new-ai-agents-to-target-the-most-time-consuming-work-in-financial-services)
  2026/05 finance-function case: Claude finance agents include pitch builder, market researcher, valuation reviewer, connectors, skills, and subagents. Use for: finance/strategy workflows and regulated review gates.
- [Article: "The next big job in tech may be the 'product engineer'" — Business Insider](https://www.businessinsider.com/ai-jobs-product-engineers-managers-2026-4)
  2026/04 product-organization case: Claude Code speeds engineering work and shifts pressure toward PM/design, with Anthropic testing engineers as mini PMs for small projects. Use for: role-boundary changes.
- [Article: "AI coders are carrying half-open laptops through airports, offices, and ice rinks" — Business Insider](https://www.businessinsider.com/coders-keep-laptops-open-in-public-ai-agent-2026-5)
  2026/05 workflow behavior case: Claude Code sessions can be long enough that users manage laptop sleep, Wi-Fi, and mobility as part of the work. Use for: checkpoint and session-survival practices.
- [Article: "Inside startups, Claude has already won the AI coding wars" — Business Insider](https://www.businessinsider.com/inside-startups-claude-has-already-won-the-ai-coding-wars-2026-5)
  2026/05 startup adoption case covering Chainguard, VaryAI, Alma, Wordsmith AI, Tenzai, QA pipelines, deployment workflows, incident investigation, and project management. Use for: startup developer workflow patterns.
- [Article: "Amazon employees pushed for Claude Code. Now they're getting it — and Codex, too" — Business Insider](https://www.businessinsider.com/amazon-claude-code-codex-all-employees-after-pushback-2026-5)
  2026/05 enterprise rollout case: Amazon standardizes Claude Code access through Bedrock/AWS after prior production-use friction. Use for: secure enterprise adoption.
- [Article: "Claude Code creator says 22-year-old CS grads should found startups" — Business Insider](https://www.businessinsider.com/claude-code-creator-advice-cs-grads-startup-2026-5)
  2026/05 startup-creation case: YC founders reportedly let Claude Code write large shares of code, shifting attention toward user understanding, spec writing, and review. Use for: founder and product-engineer workflows.
- [Article: "ChatGPT is no longer OpenAI's most important product. Here's why." — Business Insider](https://www.businessinsider.com/openai-merging-codex-into-chatgpt-lock-in-code-2026-6)
  2026/06 platform-strategy case: Claude Code and Codex can become sticky developer platforms; Walmart's Code Puppy counters vendor lock-in through model-switching. Use for: portability and tool strategy.
- [Article: "C-suites have decided: It's time to put AI on a diet" — Business Insider](https://www.businessinsider.com/ai-companies-raising-prices-internal-token-limits-openai-anthropic-ipo-2026-6)
  2026/06 governance case: covers AI coding costs, Coinbase usage caps, and Business Insider's Harness example about Claude Code cost growth plus training/internal tooling. Use for: token budget and ROI gates.
- [Paper: "Physics Is All You Need? A Case Study in Physicist-Supervised AI Development of Scientific Software" — arXiv](https://arxiv.org/abs/2605.30353)
  2026/05 scientific software case: Claude Code builds a JAX perturbation-theory module under physicist supervision, showing where oracle tests help and where domain knowledge remains necessary. Use for: supervision design.
- [Paper: "AI Coding Agents Can Reproduce Social Science Findings" — arXiv](https://arxiv.org/abs/2606.11447)
  2026/06 benchmark case: Claude Code and Codex reproduce computational social science findings, with Claude Code outperforming Codex but prompt framing affecting bias. Use for: research workflow validation.
- [Article: "I'm a product manager who used Claude to build a postcard business in 4 hours" — Business Insider](https://www.businessinsider.com/product-manager-san-francisco-used-claude-build-postcard-business-2026-5)
  2026/05 retrospective PM example: need, fast prototype, live feedback, payment integration, security review, and launch with Claude Code. Use for: showing the whole idea-to-delivery loop.
- [Article: "A Meta product manager with no technical background says vibe coding gave him 'superpowers'" — Business Insider](https://www.businessinsider.com/meta-product-manager-vibe-coding-superpowers-non-technical-builder-2026-1)
  PM-as-builder example: product ideas, build plans, code, review, and documentation. Use for: role-boundary discussions between PM and engineering.
- [Article: "Figma's AI app building tool is now available for everyone" — The Verge](https://www.theverge.com/news/712995/figma-make-ai-general-availability-announcement)
  Tool workflow example: natural-language prompt plus design references become working prototypes/apps. Use for: design-reference-to-prototype workflows.
- [Article: "A Cursor developer says engineers need to set 'clear expectations' as AI lets product managers build prototypes" — Business Insider](https://www.businessinsider.com/product-manager-ai-builder-prototypes-cursor-engineer-clear-expectations-2026-4)
  Boundary-setting example: PM prototypes should demonstrate behavior without pretending to be production systems. Use for: handoff and engineering review.
- [Article: "Andrew Ng says the real bottleneck in AI startups isn't coding — it's product management" — Business Insider](https://www.businessinsider.com/andrew-ng-product-management-bottleneck-coding-ai-startups-2025-8)
  Strategic framing: AI compresses coding time, so decision quality and feedback loops become bottlenecks. Use for: why PM judgment matters more, not less.
- [Article: "5 interesting things we just learned about the people who use Lovable" — Business Insider](https://www.businessinsider.com/lovable-arr-hit-500-million-surprising-facts-about-its-users-2026-6)
  Adoption data: many users are non-engineers and solo builders. Use for: market context around prompt-to-app builders.
- [Paper: "User-Centered Design with AI in the Loop" — arXiv](https://arxiv.org/abs/2507.21012)
  Case study: generative UI prototyping helped a team test design alternatives with highway traffic domain experts. Use for: user-feedback loops and domain-expert collaboration.
- [Paper: "PromptInfuser" — arXiv](https://arxiv.org/abs/2310.15435)
  Research example: coupling prompt behavior and UI mockups inside Figma helped designers communicate ideas and identify constraints. Use for: AI-feature prototyping.
- [Paper: "From Prompt to Product" — arXiv](https://arxiv.org/abs/2512.18080)
  Benchmark: evaluates prompt-to-app systems by usability, visual quality, completeness, and trust. Use for: why prototype validation needs more than "it generated something."
- [Guide: "Best practices for Claude Code" — Anthropic](https://code.claude.com/docs/en/best-practices)
  Developer workflow guidance: verification-first, explore-plan-code, commit/PR, subagents, hooks, and parallel sessions. Use for: turning engineering tasks into agent-ready workflows.
- [Reference: "Commands" — Anthropic](https://code.claude.com/docs/en/commands)
  Official Claude Code command reference for slash commands such as /plan, /model, /effort, /diff, /compact, /goal, /run, /review, and /permissions. Use for: Phase 1 session-control teaching.
- [Guide: "Model configuration" — Anthropic](https://code.claude.com/docs/en/model-config)
  Official Claude Code model and effort configuration guide covering model aliases, /model, /effort, opusplan, effort levels, extended thinking, and extended context. Use for: teaching model/effort decisions.
- [Guide: "How Claude remembers your project" — Anthropic](https://code.claude.com/docs/en/memory)
  Official Claude Code memory guide for CLAUDE.md, .claude/rules, auto memory, load order, and when instructions should become project memory. Use for: deciding what belongs in repo-level guidance.
- [Guide: "Claude Code settings" — Anthropic](https://code.claude.com/docs/en/settings)
  Official settings and permissions reference for user/project/local/managed scopes, .claude/settings.json, permissions, hooks, MCP servers, and shared team configuration. Use for: deciding when a contract should become enforceable project configuration.
- Local skill: `/Users/jmh/.agents/skills/handoff/SKILL.md`
  Local handoff workflow source: save a focused handoff document to OS temp, include suggested skills, reference existing artifacts by path, redact sensitive data, and tailor the summary to the next session. Use for: report-to-handoff boundaries.
- [Reference: "Hooks reference" — Anthropic](https://code.claude.com/docs/en/hooks)
  Official Claude Code hooks reference, including blocking behavior, exit code 2, Stop hooks, and task-completion enforcement. Use for: turning gates from prompt instructions into deterministic checks.
- [Guide: "Agent SDK overview" — Anthropic](https://code.claude.com/docs/en/agent-sdk/overview)
  Official Agent SDK overview for building programmable agents with Claude Code's file, command, editing, context-management, permissions, hooks, and observability capabilities. Use for: deciding when a stable contract is ready to become a runner.
- [Guide: "Observability with OpenTelemetry" — Anthropic](https://code.claude.com/docs/en/agent-sdk/observability)
  Official Agent SDK observability guide for traces, metrics, events, token/cost counters, tool calls, and failure locations. Use for: deciding which evidence belongs in long-running harness telemetry.
- [Guide: "Persist sessions to external storage" — Anthropic](https://code.claude.com/docs/en/agent-sdk/session-storage)
  Official Agent SDK session store guide for mirroring transcripts to S3, Redis, Postgres, or custom stores. Use for: distinguishing run history from resumable session storage.
- [Guide: "Track cost and usage" — Anthropic](https://code.claude.com/docs/en/agent-sdk/cost-tracking)
  Official Agent SDK cost and usage guide explaining per-call cost estimates, token accounting, and failed-conversation usage. Use for: deciding what cost metadata belongs in run history.
- [Reference: "Checkpointing" — Anthropic](https://code.claude.com/docs/en/checkpointing)
  Official Claude Code checkpointing reference for session-level restore, summarize, and limitations around Bash/external changes. Use for: defining rerun and recovery boundaries.
- [Reference: "CLI reference" — Anthropic](https://code.claude.com/docs/en/cli-reference)
  Official Claude Code CLI flags and subcommands, including non-interactive, background, permission, and tool-selection options. Use for: runner design after input contracts are stable.
- [Guide: "Best practices for Claude Code" — Anthropic, non-interactive mode section](https://code.claude.com/docs/en/best-practices#run-non-interactive-mode)
  Official guidance for using `claude -p`, structured output, fan-out scripts, scoped allowed tools, and first testing a few files before scaling. Use for: deciding the first minimal runner slice.
- [Reference: "CLI reference" — Anthropic, print/output/tool flags](https://code.claude.com/docs/en/cli-reference)
  Official CLI reference for `--print`, `--output-format`, `--json-schema`, `--tools`, `--allowedTools`, and related flags. Use for: deciding what dry-run should preview before a runner calls Claude Code.
- [Article: "GitHub Copilot Workspace" — GitHub Blog](https://github.blog/news-insights/product-news/github-copilot-workspace/)
  Official task-centric workflow from GitHub issue/repo to plan, code, tests, PR, and human review. Use for: developer workflow artifacts.
- [Article: "Nvidia now produces three times as much code as before AI" — Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/nvidia-now-produces-three-times-as-much-code-as-before-ai-specialized-version-of-cursor-is-being-used-by-over-30-000-nvidia-engineers-internally)
  Enterprise-scale Cursor adoption example across code, review, tests, QA, debugging, and git flow. Use with caution: productivity claims are vendor-adjacent and should not be treated as independent proof.
- [Article: "Cursor's New Bugbot Is Designed to Save Vibe Coders From Themselves" — WIRED](https://www.wired.com/story/cursor-releases-new-ai-tool-for-debugging-code)
  Developer review example: AI-generated or human changes get a separate bug-finding gate inside GitHub. Use for: writer/reviewer separation.
- [Paper: "Experience with GitHub Copilot for Developer Productivity at Zoominfo" — arXiv](https://arxiv.org/abs/2501.13282)
  Enterprise deployment case: four-phase rollout across 400+ developers with quantitative and qualitative signals. Use for: adoption and measurement.
- [Paper: "Developer Productivity With and Without GitHub Copilot" — arXiv](https://arxiv.org/abs/2509.20353)
  Longitudinal case at NAV IT using 703 repositories, commit activity, surveys, and interviews. Use for: separating perceived productivity from measurable activity.
- [Paper: "AIDev: Studying AI Coding Agents on GitHub" — arXiv](https://arxiv.org/abs/2602.09185)
  Large dataset of agent-authored PRs across real GitHub repositories. Use for: understanding agentic PRs as a real developer workflow.
- [Paper: "Where Do AI Coding Agents Fail?" — arXiv](https://arxiv.org/abs/2601.15195)
  Empirical study of failed agentic PRs and merge outcomes. Use for: task slicing, CI gates, and risk patterns.
- [Paper: "Why Are AI Agent Involved Pull Requests Remain Unmerged?" — arXiv](https://arxiv.org/abs/2602.00164)
  Fix-related PR failure study with manual analysis of unmerged cases. Use for: bug-fix task selection and duplicate/CI checks.
- [Paper: "Does AI Code Review Lead to Code Changes?" — arXiv](https://arxiv.org/abs/2508.18771)
  Study of 16 AI code review GitHub Actions and 22,000+ comments. Use for: making AI review comments actionable instead of noisy.

## Wisdom (Communities)

- [Lenny's Newsletter / Lenny's Podcast](https://www.lennysnewsletter.com/)
  High-signal product community that frequently discusses AI, PM workflows, and product-builder role shifts. Use for: practitioner patterns and current debate.

## Gaps

- Need more first-party writeups from product teams that document their exact AI workflow from raw requirement to shipped internal tool.
- Need Taiwan/local-language practitioner examples beyond meetup slides and social posts.
- Need more first-party developer writeups that include exact prompts, repo constraints, CI outputs, and final PR links.
