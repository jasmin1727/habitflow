#!/usr/bin/env bash
# ==============================================================================
# HabitFlow — Minimal Monochrome Habit & Streak Dashboard
# Official Installation Script for Linux
# ==============================================================================

set -e

# ANSI Color Codes
CLR_RESET="\033[0m"
CLR_BOLD="\033[1m"
CLR_DIM="\033[2m"
CLR_WHITE="\033[1;37m"
CLR_GREEN="\033[1;32m"
CLR_CYAN="\033[1;36m"
CLR_YELLOW="\033[1;33m"
CLR_RED="\033[1;31m"

print_banner() {
    clear 2>/dev/null || true
    echo -e "${CLR_WHITE}"
    echo "       ╭─────────────────────────────────╮"
    echo "       │   ┏━━━━━━━━━━━━━━━━━━━━━━━━━┓   │"
    echo "       │   ┃   ██                    ┃   │"
    echo "       │   ┃     ██        ██        ┃   │"
    echo "       │   ┃       ██    ██          ┃   │"
    echo "       │   ┃         ████            ┃   │"
    echo "       │   ┃          ██             ┃   │"
    echo "       │   ┗━━━━━━━━━━━━━━━━━━━━━━━━━┛   │"
    echo "       ╰─────────────────────────────────╯"
    echo ""
    echo "   ██╗  ██╗ █████╗ ██████╗ ██╗████████╗███████╗██╗      ██████╗ ██╗    ██╗"
    echo "   ██║  ██║██╔══██╗██╔══██╗██║╚══██╔══╝██╔════╝██║     ██╔═══██╗██║    ██║"
    echo "   ███████║███████║██████╔╝██║   ██║   █████╗  ██║     ██║   ██║██║ █╗ ██║"
    echo "   ██╔══██║██╔══██║██╔══██╗██║   ██║   ██╔══╝  ██║     ██║   ██║██║███╗██║"
    echo "   ██║  ██║██║  ██║██████╔╝██║   ██║   ██║     ███████╗╚██████╔╝╚███╔███╔╝"
    echo "   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝   ╚═╝   ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝"
    echo -e "              ${CLR_DIM}Minimal Monochrome Habit & Streak OS${CLR_RESET}"
    echo ""
}

log_step() {
    echo -e " ${CLR_CYAN}➜${CLR_RESET} ${CLR_BOLD}$1${CLR_RESET}"
}

log_success() {
    echo -e " ${CLR_GREEN}✔${CLR_RESET} $1"
}

log_warn() {
    echo -e " ${CLR_YELLOW}⚠${CLR_RESET} $1"
}

log_error() {
    echo -e " ${CLR_RED}✖${CLR_RESET} $1"
}

# Determine script directory
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
INSTALL_DIR="${HOME}/.local/share/habitflow/app"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
REPO_URL="https://github.com/jasmin1727/habitflow.git"
TEMP_DIR=""

cleanup() {
    if [ -n "${TEMP_DIR}" ] && [ -d "${TEMP_DIR}" ]; then
        rm -rf "${TEMP_DIR}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

print_banner

# Step 1: Detect Operating System
log_step "Checking system environment..."
if [[ "$OSTYPE" != "linux"* ]]; then
    log_error "HabitFlow currently natively targets Linux. Windows and macOS support are in development."
    exit 1
fi
log_success "Linux platform detected: $(uname -s) $(uname -m)"

# Step 2: Check Python 3
log_step "Verifying Python 3 runtime..."
if ! command -v python3 &>/dev/null; then
    log_error "Python 3 is required but not found. Please install Python 3.10 or higher."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
log_success "Found Python version: ${PY_VERSION}"

# Step 3: Check SQLite3
log_step "Checking SQLite database engine..."
if ! command -v sqlite3 &>/dev/null && ! python3 -c "import sqlite3" &>/dev/null; then
    log_error "SQLite3 is required. Please install sqlite3."
    exit 1
fi
log_success "SQLite 3 verified"

# Step 4: Verify WebKitGTK
log_step "Verifying WebKitGTK system library..."
if python3 -c "import gi; gi.require_version('WebKit2', '4.1'); from gi.repository import WebKit2" &>/dev/null; then
    log_success "WebKit2 GTK 4.1 library is present"
else
    log_warn "WebKit2 GTK 4.1 was not detected via PyGObject."
    echo -e "   ${CLR_DIM}If the app fails to start, install WebKitGTK with:${CLR_RESET}"
    echo -e "   ${CLR_BOLD}Arch/Manjaro:${CLR_RESET} sudo pacman -S webkit2gtk-4.1"
    echo -e "   ${CLR_BOLD}Ubuntu/Debian:${CLR_RESET} sudo apt install libwebkit2gtk-4.1-0 gir1.2-webkit2-4.1"
    echo -e "   ${CLR_BOLD}Fedora:${CLR_RESET} sudo dnf install webkit2gtk4.1"
    echo ""
fi

# Step 5: Prepare directories
log_step "Configuring target directories..."
mkdir -p "${INSTALL_DIR}"
mkdir -p "${BIN_DIR}"
mkdir -p "${DESKTOP_DIR}"
mkdir -p "${HOME}/.local/share/habitflow"
log_success "Directories verified"

# Step 5.5: Fetch Source if Executing Remotely (e.g., piped via curl)
if [ -z "${SOURCE_DIR}" ] || [ ! -f "${SOURCE_DIR}/app.py" ]; then
    log_step "Fetching HabitFlow source from GitHub (${REPO_URL})..."
    TEMP_DIR="$(mktemp -d)"
    if command -v git &>/dev/null; then
        git clone --depth 1 "${REPO_URL}" "${TEMP_DIR}/habitflow" --quiet
        SOURCE_DIR="${TEMP_DIR}/habitflow"
    else
        log_step "Downloading release archive..."
        curl -fsSL "https://github.com/jasmin1727/habitflow/archive/refs/heads/main.tar.gz" -o "${TEMP_DIR}/habitflow.tar.gz"
        tar -xzf "${TEMP_DIR}/habitflow.tar.gz" -C "${TEMP_DIR}"
        SOURCE_DIR="${TEMP_DIR}/habitflow-main"
    fi
    log_success "Source files successfully retrieved"
fi

# Step 6: Deploy Application Files
log_step "Deploying application assets and scripts..."
rsync -a --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='website' "${SOURCE_DIR}/" "${INSTALL_DIR}/" 2>/dev/null || {
    cp -r "${SOURCE_DIR}/"* "${INSTALL_DIR}/"
    rm -rf "${INSTALL_DIR}/.git" "${INSTALL_DIR}/.venv" "${INSTALL_DIR}/__pycache__" 2>/dev/null || true
}
chmod +x "${INSTALL_DIR}/app.py"
chmod +x "${INSTALL_DIR}/run.sh"
log_success "Application files deployed to ${INSTALL_DIR}"

# Step 7: Setup Virtual Environment
log_step "Setting up Python virtual environment..."
VENV_PATH="${INSTALL_DIR}/.venv"
if [ ! -d "${VENV_PATH}" ]; then
    python3 -m venv --system-site-packages "${VENV_PATH}"
fi

"${VENV_PATH}/bin/pip" install --upgrade pip --quiet
"${VENV_PATH}/bin/pip" install pywebview bottle --quiet
log_success "Virtual environment configured with pywebview"

# Step 8: Initialize SQLite Database
log_step "Initializing local SQLite database..."
"${VENV_PATH}/bin/python" -c "import sys; sys.path.insert(0, '${INSTALL_DIR}'); import database; database.init_db()"
log_success "SQLite database ready at ~/.local/share/habitflow/habitflow.db"

# Step 9: Install Desktop Launcher (.desktop)
log_step "Registering desktop application menu entry..."
cat > "${DESKTOP_DIR}/habitflow.desktop" <<EOF
[Desktop Entry]
Name=HabitFlow
Comment=Minimal Monochrome Habit & Streak Dashboard
Exec=${INSTALL_DIR}/run.sh
Icon=${INSTALL_DIR}/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;Office;
StartupWMClass=HabitFlow
Keywords=habit;tracker;routine;streak;discipline;
EOF

chmod +x "${DESKTOP_DIR}/habitflow.desktop"
update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
log_success "Desktop menu shortcut registered"

# Step 10: Create global CLI command
log_step "Creating global CLI executable..."
cat > "${BIN_DIR}/habitflow" <<EOF
#!/usr/bin/env bash
exec "${INSTALL_DIR}/run.sh" "\$@"
EOF
chmod +x "${BIN_DIR}/habitflow"
log_success "Global executable created at ~/.local/bin/habitflow"

# Ensure ~/.local/bin is mentioned if not in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    log_warn "~/.local/bin is not in your current PATH. Add 'export PATH=\"\$HOME/.local/bin:\$PATH\"' to your ~/.bashrc or ~/.zshrc."
fi

# Summary
echo ""
echo -e "${CLR_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CLR_RESET}"
echo -e " ${CLR_BOLD}${CLR_WHITE}HabitFlow Desktop App has been successfully installed!${CLR_RESET}"
echo -e "${CLR_GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CLR_RESET}"
echo ""
echo -e " ${CLR_BOLD}Quick Launch Methods:${CLR_RESET}"
echo -e "  1. Launch from terminal:       ${CLR_CYAN}habitflow${CLR_RESET} or ${CLR_CYAN}${INSTALL_DIR}/run.sh${CLR_RESET}"
echo -e "  2. Launch from app launcher:   Search for ${CLR_CYAN}HabitFlow${CLR_RESET} in your Application Menu / Rofi / Wofi"
echo ""
echo -e " ${CLR_BOLD}Database Storage:${CLR_RESET}"
echo -e "  ~/.local/share/habitflow/habitflow.db"
echo ""
echo -e " ${CLR_DIM}Enjoy your quiet, consistent habit building!${CLR_RESET}"
echo ""
