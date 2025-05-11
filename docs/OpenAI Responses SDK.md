# OpenAI Responses SDK — Quick Reference

| Aspect | What it is (practical view) | Where to get it / install command |
|--------|-----------------------------|-----------------------------------|
| **Code (libraries)** | Official client libraries you import in your code. | • **Python**: `pip install openai` [[PyPI]](https://pypi.org/project/openai) [[GitHub]](https://github.com/openai/openai-python)  <br>• **Node**: `npm install openai` [[npm]](https://www.npmjs.com/package/openai) |
| **Tools (CLIs & helpers)** | Command-line tools that ship with the libs. | • Python library includes `openai` CLI (`python -m openai …`) <br>• Optional richer terminal for agents: `npm i -g @openai/codex` |
| **Docs & samples** | API reference, how-to guides, example notebooks/apps. | • Official docs → <https://platform.openai.com/docs> <br>• Example notebooks → [OpenAI Cookbook](https://github.com/openai/openai-cookbook) <br>• Starter Next.js demo → [`openai-responses-starter`](https://github.com/openai/openai-responses-starter) |
| **Config files / templates** | Environment & CLI config that the SDK reads. | • `.env` file containing `OPENAI_API_KEY=…` (example in starter repo) <br>• `openai tools config` creates `~/.openai/config.json` for CLI defaults |

---

## Minimal Python Quick-start

```bash
# 1 Install
pip install openai
# 2 Set your key (Unix/macOS)
export OPENAI_API_KEY=sk-…

# 3 Test the Responses API
python - <<'PY'
from openai import OpenAI
client = OpenAI()
r = client.responses.create(
    model="gpt-4o-mini",
    input="Ping",
    instructions="Reply with 'Pong'."
)
print(r.output_text)
PY
