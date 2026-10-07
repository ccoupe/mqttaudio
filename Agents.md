# Agent Definition - Distributed Audio Server (mqttaudio)

## Description
A distributed network node managing audio assets, sirens, chimes, neural Text-to-Speech (TTS), and local conversational LLM context.

## Role & Responsibilities
- **Distributed Sound Player:** Plays alarm sirens, doorbell chimes, and system alert audios on request using PyAudio and VLC.
- **LLM Conversation Bridge:** Manages stateful conversational contexts with a local Ollama client to produce snarky GLaDOS chatbot responses.
- **Speech Controller:** Orchestrates TTS requests to the neural GLaDOS server and STT transcription inputs to the Whisper server.

## Key Files
- [bridge.py](file:///home/ccoupe/Projects/iot/mqttaudio/bridge.py) - Main MQTT handler, audio selector, and thread coordinator.
- [Chatbot.py](file:///home/ccoupe/Projects/iot/mqttaudio/Chatbot.py) - Ollama local client integrator and conversation log manager.
- [speechio.py](file:///home/ccoupe/Projects/iot/mqttaudio/speechio.py) - HTTP communication layer connecting to external STT and TTS engines.
- [Audio.py](file:///home/ccoupe/Projects/iot/mqttaudio/Audio.py) - PyAudio playback, device selectors, volume adjustment, and VLC player.

## Integration Points
- **Subscribed MQTT Topics:**
  - `homie/+/speech/say/set` (Trigger GLaDOS to speak an input string)
  - `homie/+/speech/ask/set` (Trigger GLaDOS to speak a prompt, then listen and transcribe response)
  - `homie/+/player/url/set` (Play specific audio stream or sound asset URL)
  - `homie/+/player/volume/set` (Control music playback volume)
  - `homie/+/chime/state/set` / `volume/set` (Trigger doorbell chimes)
  - `homie/+/siren/state/set` / `volume/set` (Trigger emergency alarm siren)
- **External API Integrations:**
  - **GLaDOS TTS Server:** `http://<glados_ip>:8132/v1/audio/speech` (Flask audio endpoint)
  - **Whisper STT Server:** `http://<whisper_ip>:5003/` (Flask transcription endpoint)
  - **Ollama Server:** `http://<ollama_ip>:11434/api/chat` (LLM chat API)

## Context & Memory
- Chatbot context is stateful. System instructions and "snark filters" are customized by deleting "think" blocks or filtering markdown tags before sending content to speech processors.
- Handles PulseAudio and hardware audio devices dynamically based on config structures (`pi5.toml` / `nopi.toml`).
