# WhatsApp Agent Listener

**A local Python listener that connects the WhatsApp Third-Party Agent Platform to Groq AI.**

This project receives messages from a WhatsApp agent, asks a Groq model to generate a reply, and sends that reply back through the WhatsApp Agent Platform API. It is intended to become a reusable foundation for developers who want to build their own WhatsApp AI agents and, in the future, extend them with plugins and additional AI providers.

> **Current implementation:** The listener uses the platform's long-polling `/updates` endpoint. Despite `Webhook` in the repository name, the current version does **not** run an incoming HTTP webhook server and does not require a public webhook URL.

**Repository:** <https://github.com/Saif-Ali-109/Whatsapp-Agent-Webhook>

---

## Contents

- [What is this?](#what-is-this)
- [Features](#features)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Install uv](#1-install-uv)
- [Get the project](#2-get-the-project)
- [Create and activate a virtual environment](#3-create-and-activate-a-virtual-environment)
- [Install project dependencies](#4-install-project-dependencies)
- [Configure API credentials](#5-configure-api-credentials)
- [Run the listener](#6-run-the-listener)
- [Configuration reference](#configuration-reference)
- [Project structure](#project-structure)
- [Message handling and memory](#message-handling-and-memory)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## What is this?

The WhatsApp Agent Listener is a Python application that joins three pieces together:

1. **WhatsApp Third-Party Agent Platform API** — delivers updates from the agent's chat and accepts outgoing replies.
2. **Python listener** — polls for incoming messages, extracts their contents, and manages message-processing state.
3. **Groq API** — generates a response from the incoming text and recent in-memory conversation history.

The current implementation is a personal-agent prototype. It is not a shared WhatsApp bot that can join arbitrary personal chats or WhatsApp groups. The WhatsApp Agent Platform's documented API and recipient restrictions apply.

## Features

- Receives updates with long polling; no public webhook endpoint is required.
- Sends text responses through the WhatsApp Agent Platform API.
- Generates replies using the Groq API.
- Lets you select a Groq model with an environment variable.
- Keeps a separate in-memory conversation history for each sender identifier while the program is running.
- Saves polling offsets and processed message IDs in a local JSON state file.
- Attempts to mark supported incoming messages as read and display a typing indicator.
- Logs major events and errors to the terminal.
- Retries after failures with exponential backoff.
- Uses `uv` to manage Python versions, dependencies, and the project environment.

## How it works

```text
You send a message to your WhatsApp agent
                  |
                  v
       WhatsApp Agent Platform API
                  |
                  | GET /agent/v1/updates (long polling)
                  v
          Python listener (agent.py)
                  |
                  | Extract sender and message text
                  v
           Conversation history
                  |
                  | Chat completion request
                  v
                Groq API
                  |
                  | Generated answer
                  v
          Python listener (agent.py)
                  |
                  | POST /agent/v1/messages
                  v
       WhatsApp Agent Platform API
                  |
                  v
          Reply in agent chat
```

### Long polling instead of webhooks

A traditional webhook server waits for another service to send an HTTP request to a publicly reachable URL. This project works differently: the Python process makes outbound requests to the WhatsApp Agent Platform's updates endpoint and waits for available updates. As a result, you can run it from your own computer without setting up a public webhook URL or a tunnel.

The process must remain running to reply to messages. When you stop the program, it stops checking for updates and generating replies.

## Requirements

- **Python 3.14**, as requested by the project's `.python-version` and `pyproject.toml`.
- **uv**, the Python project and package manager used by this repository.
- A WhatsApp Third-Party Agent and its API token.
- A Groq account and API key.
- Internet connectivity.

You do not need to install dependencies globally with `pip`; `uv sync` installs the project dependencies in the project environment.

## 1. Install uv

If `uv` is already installed, skip to [Get the project](#2-get-the-project). After installing it, open a new terminal if the command is not immediately available.

### Windows — PowerShell

Open PowerShell and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell if needed, then verify:

```powershell
uv --version
```

### Windows — Command Prompt (CMD)

The command above can be run from PowerShell. If you use CMD, open PowerShell to install `uv`, then return to CMD and verify:

```bat
uv --version
```

### Linux / macOS

Open a terminal and run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If `uv` is not found afterward, open a new terminal or follow the installation instructions for your shell at <https://docs.astral.sh/uv/getting-started/installation/>.

Verify the installation:

```bash
uv --version
```

## 2. Get the project

Clone the repository:

```bash
git clone https://github.com/Saif-Ali-109/Whatsapp-Agent-Webhook.git
cd Whatsapp-Agent-Webhook
```

Run the remaining commands from the repository's root directory—the directory containing `pyproject.toml`, `uv.lock`, and `agent.py`.

## 3. Create and activate a virtual environment

The repository specifies Python 3.14. `uv` can install and manage that Python version for you. Run the Python-install command once if you do not already have a suitable Python 3.14 installation:

```bash
uv python install 3.14
```

Create a project virtual environment:

```bash
uv venv --python 3.14
```

This creates `.venv/` in the project directory. Activate it using the instructions for your shell below.

### Windows — PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation because of its execution policy, you can either use `uv run agent.py` without activating the environment, or review Microsoft's execution-policy guidance before changing your policy. Do not change system-wide security settings just to run this project.

### Windows — Command Prompt (CMD)

```bat
.venv\Scripts\activate.bat
```

### Linux / macOS — Bash, Zsh, or a similar shell

```bash
source .venv/bin/activate
```

When activation succeeds, your terminal prompt will usually show `(.venv)`.

To leave the virtual environment later, run:

```bash
deactivate
```

> **Alternative:** You do not have to activate the environment to use `uv`. The command `uv run agent.py` can run the script inside the project's managed environment.

## 4. Install project dependencies

From the project root, run:

```bash
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, creates or updates the project's `.venv` environment, and installs the locked project dependencies. Run it again after pulling changes that update the project's dependencies or lockfile.

To check the Python version selected by `uv`, run:

```bash
uv run python --version
```

It should report Python 3.14.x. If it does not, check `.python-version`, `pyproject.toml`, and your environment.

## 5. Configure API credentials

Create your local environment file from the example:

### Windows — PowerShell

```powershell
Copy-Item .env.example .env
```

### Windows — CMD

```bat
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Open `.env` in a text editor and replace the placeholder values. The file should look like this:

```dotenv
WHATSAPP_AGENT_TOKEN=your_whatsapp_agent_token
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

The model shown is the default used by the current script. Groq model availability can change; if it is unavailable to your account, set `GROQ_MODEL` to a currently available model listed in your Groq account or Groq's documentation.

### WhatsApp Agent API token

Obtain the API key from the API-key settings for your WhatsApp Third-Party Agent. Keep it private. The token authorizes API requests for that agent and does not turn the agent into a bot that can freely access other WhatsApp chats or groups.

### Groq API key

Create or manage your key at <https://console.groq.com/keys>. Keep it private and do not commit it to Git.

### Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `WHATSAPP_AGENT_TOKEN` | Yes | Authorizes requests to the WhatsApp Agent Platform API. |
| `GROQ_API_KEY` | Yes | Authorizes requests to Groq. |
| `GROQ_MODEL` | No | Model used for responses; the current script defaults to `openai/gpt-oss-20b` when unset. |

## 6. Run the listener

From the root directory, run the requested command:

```bash
uv run agent.py
```

`uv run` runs the script in the project environment and can synchronize the environment when needed. If you already ran `uv sync`, it will use the prepared environment.

The terminal should show startup logs with the selected model and API endpoint. Keep the terminal open while you want the listener to reply. Stop it with **Ctrl+C**.

If the virtual environment is activated and dependencies are installed, you can also run the script directly:

```bash
python agent.py
```

The recommended command for this repository is still:

```bash
uv run agent.py
```

## Example interaction

A conversation might look like this:

```text
You: My name is Saif.
Agent: Nice to meet you, Saif! How can I help you today?

You: What's my name?
Agent: Your name is Saif.
```

The model can answer this because the current process includes recent messages in the conversation context. This is not permanent memory: restarting the program clears the in-memory conversation history.

## Project structure

```text
Whatsapp-Agent-Webhook/
├── agent.py                 # Polling loop, WhatsApp API calls, Groq responses
├── src/
│   └── whatsapp_agent/
│       └── __init__.py      # Python package initialization
├── pyproject.toml           # Project metadata and dependencies
├── uv.lock                  # Locked dependency versions
├── .python-version          # Requested Python version (3.14)
├── .env.example             # Safe template with placeholder credentials
├── .env                     # Local secrets; create locally, do not commit
├── agent_state.json         # Local runtime state; generated while running
└── README.md                # Project documentation
```

`.env` and `agent_state.json` are local files and should not be tracked by Git. The exact files present may differ depending on whether you have run the application.

## Message handling and memory

### Incoming messages

The listener extracts messages from the update payload. Text messages are sent to Groq with the system prompt and the sender's recent conversation history. The generated answer is then sent back to the message's sender identifier, subject to the WhatsApp Agent Platform's restrictions.

### Unsupported message types

The current implementation primarily supports text messages. For other message types, it sends a fallback reply asking the user to send text. Reactions are ignored. Image, audio, video, document, and sticker understanding is not implemented yet.

### Polling state and duplicate handling

The application stores the update offset and a collection of processed message IDs in `agent_state.json`. This helps it continue from its saved update position and avoid processing a message ID more than once in normal retries. It is not an exactly-once delivery guarantee; in some network failure cases, a reply may be sent twice.

The current code also skips messages whose timestamps are earlier than the process startup time. Conversation history is held in RAM and is cleared when the application restarts, even though the polling state remains on disk.

## Limitations

- The current transport is **long polling**, not an incoming HTTP webhook.
- The current example is designed for the WhatsApp agent creator's permitted conversation; it cannot be assigned to arbitrary personal chats or groups through this API.
- The current AI provider integration is Groq.
- Text is the primary supported input type.
- Conversation memory is not persisted across restarts.
- Local state is stored in a JSON file.
- The project does not yet provide a stable third-party plugin API or hosted dashboard.
- Reliability and security hardening are still needed before using it as a production multi-user service.

## Troubleshooting

### `uv` is not recognized

Open a new terminal after installing `uv`. If the command still cannot be found, check the official installation instructions: <https://docs.astral.sh/uv/getting-started/installation/>.

### Python version or installation error

The project requests Python 3.14. Run:

```bash
uv python install 3.14
uv python list
```

Then create the environment again if necessary:

```bash
uv venv --python 3.14
uv sync
```

### PowerShell does not allow environment activation

You can skip activation and run the project using:

```powershell
uv sync
uv run agent.py
```

Alternatively, use Command Prompt and activate with `.venv\Scripts\activate.bat`. Avoid changing machine-wide execution policies just for this project.

### Missing environment variable

Confirm that `.env` exists in the project root and contains `WHATSAPP_AGENT_TOKEN` and `GROQ_API_KEY`. Check that there are no accidental spaces around the variable names and that the values are valid.

### WhatsApp authentication or recipient error

Verify the WhatsApp token and make sure the agent and recipient are permitted by the platform. The sender identifier should come from the incoming message payload; do not substitute an ordinary phone number unless the API explicitly requires it.

### Groq authentication or model error

Verify the key at <https://console.groq.com/keys> and confirm that `GROQ_MODEL` names a model available to your account. Do not publish API keys in issue reports or screenshots.

### No reply arrives

1. Confirm that `uv run agent.py` is still running.
2. Inspect the terminal logs for HTTP or Groq errors.
3. Confirm that you are messaging the dedicated agent chat supported by the platform.
4. Send a text message; non-text inputs are not processed by Groq in the current implementation.
5. Check API availability, credentials, and rate limits.

### Rate limit errors

The platform limits how frequently some endpoints can be polled or used to send messages. Avoid running multiple listeners against the same agent. If the rate limit persists, stop repeatedly retrying and review the platform's limits and error response.

## Security

- Never commit `.env`, API tokens, or private conversation data.
- The `.env.example` file should contain placeholders only, never working credentials.
- Keep `agent_state.json` out of the repository if it contains identifiers or operational state you do not want to publish.
- Message content submitted to Groq is processed by an external AI provider; disclose this to users before offering the service to others.
- If a real token or API key has ever been pushed to a public repository, revoke/rotate it. Deleting `.env` in a later commit does not remove it from earlier Git history.
- Before hosting the application for multiple customers, implement credential protection, tenant isolation, data-retention controls, monitoring, and additional testing.

## Roadmap

The project aims to evolve into an extensible toolkit. Potential next steps include:

- [ ] Split WhatsApp transport, message dispatch, AI generation, and state management into modules.
- [ ] Add tests for parsing updates, retries, and message processing.
- [ ] Define a stable event-handler and plugin interface.
- [ ] Introduce a common interface for AI providers.
- [ ] Add provider integrations beyond Groq.
- [ ] Add persistent conversation storage with configurable retention.
- [ ] Add structured logs, health checks, and graceful shutdown.
- [ ] Document deployment and production security.
- [ ] Explore an optional hosted dashboard.

Roadmap items are plans, not features currently implemented.

## Contributing

Contributions, bug reports, documentation improvements, and feature suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make and test your changes.
4. Commit your work with a clear message.
5. Open a pull request describing the problem and solution.

Example branch and commit:

```bash
git checkout -b feature/my-improvement
git add .
git commit -m "feat: describe the improvement"
git push -u origin feature/my-improvement
```

For major changes—especially plugin API or storage design—open an issue to discuss the approach before making a large implementation.

## License

No license has been selected for this repository yet. Until a license file is added, visitors should not assume they have permission to redistribute, modify, or use this project's code. Choose and add a license before marketing it as open source.

## Disclaimer

This is an independent community project. It is not affiliated with, endorsed by, or officially supported by WhatsApp, Meta, or Groq. Product and company names are used only to identify the relevant services. Users are responsible for following applicable platform terms, privacy requirements, and laws.

## Useful links

- **Repository:** <https://github.com/Saif-Ali-109/Whatsapp-Agent-Webhook>
- **uv installation:** <https://docs.astral.sh/uv/getting-started/installation/>
- **uv project guide:** <https://docs.astral.sh/uv/guides/projects/>
- **Groq Console and API keys:** <https://console.groq.com/keys>
- **Groq API documentation:** <https://console.groq.com/docs>
