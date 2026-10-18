# WhatsApp Agent Listener

### Connect WhatsApp AI Agents to Groq using Python

A Python-based listener for the WhatsApp Third-Party Agent Platform API.
It receives incoming messages, sends them to a Groq-powered AI model,
and delivers the generated responses back through WhatsApp.

The project aims to provide a simple foundation for building extensible
WhatsApp AI agents, with support for additional AI providers, custom
message handlers, plugins, and future hosted deployments.

**Run the listener locally. Connect your AI model. Start chatting.**

<p align="center">
  <a href="https://github.com/Saif-Ali-109/Whatsapp-Agent-Webhook">
    GitHub Repository
  </a>
  |
  <a href="https://console.groq.com/keys">
    Get a Groq API Key
  </a>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Why This Project?](#why-this-project)
- [Features](#features)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Listener](#running-the-listener)
- [Example Conversation](#example-conversation)
- [Supported Messages](#supported-messages)
- [Conversation Memory](#conversation-memory)
- [Project Structure](#project-structure)
- [How the Listener Works Internally](#how-the-listener-works-internally)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Overview

The WhatsApp Agent Listener connects a WhatsApp Third-Party Agent to an
AI model through the Groq API.

Instead of manually responding to messages, the Python application
continuously checks the WhatsApp Agent Platform for incoming messages.

When a new text message arrives, the listener:

1. Receives the message from WhatsApp.
2. Extracts the sender identifier and message text.
3. Loads the relevant conversation history.
4. Sends the conversation to a Groq AI model.
5. Receives the model-generated response.
6. Sends the response back through the WhatsApp Agent API.
7. Records the processed message to help prevent duplicate processing.

The result is a conversational AI assistant that runs on your own
computer.

### What does this project use?

| Component | Purpose |
|---|---|
| Python | Main application language |
| WhatsApp Agent Platform API | Receiving and sending messages |
| Groq API | Generating AI responses |
| `requests` | Making HTTP requests |
| `python-dotenv` | Loading configuration from `.env` |
| `uv` | Python project and dependency management |
| JSON state file | Persisting polling state and processed message IDs |

The listener does not require a public webhook URL because it receives
updates by polling the WhatsApp Agent Platform API.

---

## Why This Project?

Building a WhatsApp AI agent from scratch requires several components:

- API authentication
- Incoming message retrieval
- Message parsing
- AI model integration
- Outgoing message delivery
- Error handling
- Rate-limit handling
- Duplicate-message protection
- Conversation management
- Configuration and secret management

This project brings those components together in one Python application.

The long-term goal is to make it easier for developers to build their
own WhatsApp AI agents without repeatedly implementing the same
messaging infrastructure.

Developers should eventually be able to choose an AI provider, add
custom plugins, and implement their own message handlers without
rewriting the listener.

---

## Features

### WhatsApp Integration

- Connects to the WhatsApp Third-Party Agent Platform API.
- Retrieves incoming messages through long polling.
- Sends text responses through the platform API.
- Uses sender identifiers supplied by incoming messages.
- Supports the agent creator's permitted conversation.

### AI Integration

- Uses Groq to generate responses.
- Supports configurable model selection.
- Includes a system prompt for assistant behavior.
- Maintains separate in-memory conversation histories for different
  sender identifiers while the process is running.

### Reliability

- Saves the polling offset to a local state file.
- Tracks processed message IDs.
- Retries after errors with exponential backoff.
- Handles HTTP errors and API rate limits.
- Uses logging to report incoming messages and failures.
- Attempts to mark incoming messages as read.

### Developer Experience

- Uses environment variables for credentials.
- Supports local development.
- Uses `uv` for dependency management.
- Provides a foundation for future modular architecture and plugins.

---

## How It Works

The listener follows this message flow:

```text
             WhatsApp Agent Chat
                      |
                      | User sends a message
                      v
           WhatsApp Agent Platform
                      |
                      | GET /agent/v1/updates
                      v
                Python Listener
                      |
                      | Extract message and sender
                      v
              Conversation Handler
                      |
                      | Build AI conversation
                      v
                   Groq API
                      |
                      | Generated response
                      v
                Python Listener
                      |
                      | POST /agent/v1/messages
                      v
           WhatsApp Agent Platform
                      |
                      v
             WhatsApp Agent Chat
