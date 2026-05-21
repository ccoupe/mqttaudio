# Project Settings Documentation

This document describes the configuration settings used in the project, as defined in `Settings.py` and supported via JSON and TOML files.

## Configuration Formats

The project supports both JSON and TOML configuration files. The loader in `Settings.py` automatically detects the format based on the file extension.

## Settings Categories

### 1. MQTT Settings
Used for connecting to the MQTT broker and defining Homie device properties.

| Key | Type | Default (JSON/TOML) | Description |
| :--- | :--- | :--- | :--- |
| `mqtt_server_ip` | string | "192.168.1.7" / "192.168.1.2" | IP address or hostname of the MQTT broker. |
| `mqtt_port` | integer | 1883 | Port for the MQTT broker. |
| `mqtt_client_name` | string | "trumpy_bridge" | Client ID used when connecting to MQTT. |
| `homie_device` | string | "trumpy_cam" | The Homie device name for this instance. |

### 2. Bridge Settings
Configuration for the bridge component, often associated with Mycroft integration.

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `bridge_ip` | string | "192.168.1.2" | IP address of the bridge service. |
| `bridge_port` | integer | 8281 | Port for the bridge service. |

### 3. TTS (Text-to-Speech) Settings
Defines which TTS engine to use and its endpoint.

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `engine` / `tts_engine` | string | None | Name of the TTS engine (e.g., "glados", "glados2", "mycroft"). |
| `tts_url` | string | None | The URL for the TTS synthesis service. |

**Note:** In JSON, `tts_url` is typically nested within an object named after the engine (e.g., `{"glados": {"tts_url": "..."}}`).

### 4. Microphone Settings
Configures audio input devices and their status reporting via MQTT.

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `microphone` | string | None | The name or identifier of the microphone device. |
| `microphone_volume` | float | 0.5 (JSON) / 0.6 (TOML) | Input volume level (0.0 to 1.0). |
| `microphone_pyaudio _name` | string | "pulse" | The PyAudio device name to use. |
| `mic_pub_type` | string | "notify" | Type of MQTT publication for mic status ('notify' or 'login'). |
| `mic_pub_topic` | string | `homie/pi4_screen/...` | MQTT topic to publish microphone status/control to. |

### 5. Speaker Settings
Configures audio output devices.

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `speaker` | string | None | The name or identifier of the speaker device. |
| `speaker_volume` | float | 0.5 | Output volume level (0.0 to 1.0). |

### 6. STT (Speech-to-Text) Settings
Configures the remote STT service.

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `stt_host` | string | "bronco.local" | Hostname or IP of the STT service. |
| `stt_port` | integer | 5003 | Port of the STT service. |

### 7. Ollama (LLM) Settings
Configuration for the Ollama LLM integration.

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ollama_hosts` | list[string] | [] | List of Ollama server hostnames/IPs. |
| `ollama_port` | integer | 11434 | Port for the Ollama API. |
| `ollama_default_model` | string | "stablelm-zephyr:latest" | The key of the default model to use. |
| `ollama_models` | dict/object | None | Definitions of available models and their parameters. |

#### Model Parameters (within `ollama_models`)
- `name`: Actual model name in Ollama (e.g., "deepseek-r1:14b").
- `stream`: Boolean, whether to stream responses.
- `md_format`: Boolean, whether to use Markdown formatting.
- `delete_think_blocks`: Boolean, whether to remove `<think>` blocks from output.
- `prompt`: Filename of the prompt template to use.
- `use_audible_tag`: Boolean, whether to use audible tags in the output.

## Format Specifics

### TOML Structure
TOML files use sections to group settings:
- `[mqtt]`
- `[tts]`
- `[microphone]`
- `[speaker_section]`
- `[stt]`
- `[ollama]`

### JSON Structure
JSON files use a flat structure for top-level settings, with some nested objects for engine-specific configurations (like `glados` or `ollama_models`).
