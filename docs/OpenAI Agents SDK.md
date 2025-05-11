# Project Rules – OpenAI **Agents** SDK

## 1  SDK Quick Reference (Agents Layer)

| Aspect                       | Practical description                                                                                                 | Where to get / install                                                                                                                                                                                                                                                                               |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Code (library)**           | High‑level wrapper that sits on top of `openai` and adds multi‑step agent orchestration utilities.                    | `pip install openai-agents`   [\[PyPI\]](https://pypi.org/project/openai-agents)   [\[GitHub\]](https://github.com/openai/openai-python/tree/main/openai/agents)                                                                                                                                     |
| **Tools (CLI & helpers)**    | `openai-agents` command‑line helper (`-h` shows scaffold, run/play loops). Auto‑installed with the package.           | After install, run `openai-agents init` or `openai-agents run examples/…`                                                                                                                                                                                                                            |
| **Docs & samples**           | *Agents* guide in platform docs; cookbook notebooks; reference Next.js demo with multi‑agent chat.                    | • Docs → [https://platform.openai.com/docs/agents](https://platform.openai.com/docs/agents)  • Cookbook → [https://github.com/openai/openai-cookbook](https://github.com/openai/openai-cookbook)  • Demo Repo → [https://github.com/openai/agents-starter](https://github.com/openai/agents-starter) |
| **Config files / templates** | `.env` containing `OPENAI_API_KEY` and optional `AGENTS_PROFILE=*` ; YAML manifests created via `openai-agents init`. | `.env.example` ships in demo repo. `openai-agents` CLI writes `agent.yaml` when scaffolding a project.                                                                                                                                                                                               |

---

## 2  Minimal Python Quick‑start

```bash
# 1 Install
pip install openai-agents

# 2 Set key (Unix / macOS)
export OPENAI_API_KEY=sk-…

# 3 Run a hello‑world agent
python - <<'PY'
from agents import Agent, run

coder = Agent(
    name="Coder",
    instructions="Write idiomatic Python and explain inline."
)

answer = run(coder, "Implement quicksort in Python, then test it.")
print(answer.output_text)
PY
```

---

## 3  Project Conventions

1. **Version pinning:** keep a *separate* line in `requirements.txt`:

   ```txt
   openai~=1.14
   openai-agents~=0.3
   ```

   Review quarterly.
2. **Secrets handling:** never commit keys. Use `.env` + Cursor Secrets UI.
3. **Runtime guardrails:**

   * default `model="gpt-4o-mini"` unless an experiment branch justifies a larger model.
   * limit tokens with env vars (`AGENT_MAX_TOKENS`).
4. **CI smoke‑test:** include `verify_agents.py` that spins up an agent and exits on failure.
5. **Upgrade policy:** trial new agent versions in a feature branch; merge once smoke‑tests & cost benchmarks pass.

---

## 4  Helpful Links

* **Agents docs:** [https://platform.openai.com/docs/agents](https://platform.openai.com/docs/agents)
* **Agents source:** [https://github.com/openai/openai-python](https://github.com/openai/openai-python)
* **Cookbook notebooks:** [https://github.com/openai/openai-cookbook](https://github.com/openai/openai-cookbook)
