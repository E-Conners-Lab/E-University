#!/bin/bash
# Secure pyATS runner - loads credentials from macOS Keychain
cd "$(dirname "$0")"

export DEVICE_USERNAME=$(security find-generic-password -s "euniv-username" -w 2>/dev/null)
export DEVICE_PASSWORD=$(security find-generic-password -s "euniv-password" -w 2>/dev/null)
export DEVICE_ENABLE_PASSWORD=$(security find-generic-password -s "euniv-enable" -w 2>/dev/null)

if [ -z "$DEVICE_PASSWORD" ]; then
    echo "Error: Credentials not found in Keychain. Run:"
    echo "  security add-generic-password -a \"\$USER\" -s \"euniv-username\" -w \"your-username\""
    echo "  security add-generic-password -a \"\$USER\" -s \"euniv-password\" -w \"your-password\""
    echo "  security add-generic-password -a \"\$USER\" -s \"euniv-enable\" -w \"your-enable-password\""
    exit 1
fi

pyats run job "$@"
