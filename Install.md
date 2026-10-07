# Installation and Setup Instructions

This document provides instructions for installing and setting up the mqttaudio project using the provided Makefile.

## Prerequisites

Before installing, ensure you have:

1. **System Requirements:**
   - Linux system (tested on Ubuntu/Debian-based systems)
   - `make` utility installed
   - `uv` Python package manager installed
   - Python 3.11 or later available on the system
   - `portaudio19-dev` development package installed

2. **Permissions:**
   - Sudo access for creating directories and systemd services
   - Write permissions to the target installation directory (`/usr/local/lib/mqttaudio`)

To install the required packages, run:

```bash
sudo apt update
sudo apt install make portaudio19-dev uv
```

## Installation Steps

### 1. Clone or Copy Project Files

First, you'll need to get the project files:
```bash
# If cloning from a repository
git clone <repository-url>
cd mqttaudio

# Or copy your existing files to the directory
```

### 2. Set Up Environment Variables (Optional)

The Makefile uses several environment variables that can be customized:

```bash
export PRJ=mqttaudio          # Project name
export DESTDIR=/usr/local/lib/${PRJ}  # Installation directory
export SRCDIR=$HOME/Projects/iot/${PRJ} # Source code directory  
export NODE=$(hostname)       # Hostname for configuration file
```

### 3. Run Make Install

To install the application:

```bash
make install
```

This will:
- Create necessary directories
- Copy all source files to the destination directory
- Set up the Python virtual environment
- Configure systemd service (if needed)

### 4. Update Configuration Files

After installation, you may need to customize configuration files:
```bash
# Edit the node-specific configuration
sudo nano /usr/local/lib/mqttaudio/$(hostname).toml

# Modify launch script if necessary  
sudo nano /usr/local/lib/mqttaudio/mqttaudio.sh
```

### 5. Start the Service (if applicable)

If your project includes a systemd service:

```bash
make start
```

## Makefile Targets

The Makefile provides several useful targets:

| Target      | Description                              |
|-------------|------------------------------------------|
| `install`   | Full installation including virtual env  |
| `update`    | Update only changed files                |
| `start`     | Start the systemd service                |
| `stop`      | Stop the systemd service                 |
| `clean`     | Stop service and remove installed files  |
| `distclean` | Clean plus remove Python virtual env     |

## Usage

### Updating the Application

To update only files that have changed:

```bash
make update
```

This leverages the incremental update capability, so only modified files will be copied.

### Cleaning Up

To completely remove the installation:

```bash
make distclean
```

This stops the service and removes all installed files including the virtual environment.

## Troubleshooting

### Python Version Issues
If you encounter Python version errors:
1. Install a compatible Python version using your system's package manager  
2. Or install a specific version using `uv managed python install <version>`
3. The Makefile now automatically uses available Python versions instead of requiring a specific one

### Permission Issues
If permission errors occur, ensure you have proper sudo access and the correct ownership for the installation directory.