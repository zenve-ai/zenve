#!/usr/bin/env sh
set -e

REPO="zenve-ai/zenve"
INSTALL_DIR="/usr/local/bin"
BIN_NAME="zenve"

# Detect OS
OS=$(uname -s)
ARCH=$(uname -m)

case "$OS" in
  Linux)
    case "$ARCH" in
      x86_64) ASSET="zenve-linux-x86_64" ;;
      *) echo "Unsupported architecture: $ARCH" && exit 1 ;;
    esac
    ;;
  Darwin)
    case "$ARCH" in
      arm64) ASSET="zenve-macos-arm64" ;;
      x86_64) echo "Intel Macs are not supported. Please use an Apple Silicon Mac (M1/M2/M3)." && exit 1 ;;
      *) echo "Unsupported architecture: $ARCH" && exit 1 ;;
    esac
    ;;
  *)
    echo "Unsupported OS: $OS"
    echo "For Windows, download zenve-windows-x86_64.exe from:"
    echo "  https://github.com/$REPO/releases/latest"
    exit 1
    ;;
esac

# Resolve version
VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  VERSION=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep '"tag_name"' \
    | cut -d'"' -f4)
fi

if [ -z "$VERSION" ]; then
  echo "Could not determine latest version. Pass a version explicitly:"
  echo "  curl -fsSL .../install.sh | sh -s v1.0.0"
  exit 1
fi

URL="https://github.com/$REPO/releases/download/$VERSION/$ASSET"
TMP=$(mktemp)

echo "Installing zenve $VERSION ($ASSET)..."
curl -fsSL "$URL" -o "$TMP"
chmod +x "$TMP"

DEST="$INSTALL_DIR/$BIN_NAME"

if [ -w "$INSTALL_DIR" ]; then
  mv "$TMP" "$DEST"
else
  echo "Writing to $INSTALL_DIR requires sudo..."
  sudo mv "$TMP" "$DEST"
fi

echo ""
echo "zenve installed to $DEST"
"$DEST" --version
