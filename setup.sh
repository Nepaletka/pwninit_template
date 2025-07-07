#!/bin/zsh

TEMPLATE=~/.config/pwninit-templates
LIBS=~/.config/pwninit-libs

# === Confirm overwrite ===
if [[ -d "$TEMPLATE" ]]; then
  echo -n "[*] Templates already exists! Rewrite? [y/N]: "
  read answer
  if [[ "$answer" != "y" ]]; then
    echo "[*] Aborted."
    exit 0
  fi
fi

echo "[*] Creating config..."
cp -r ./pwninit-templates/* "$TEMPLATE"
cp -r ./libs/* "$LIBS"

# === Add pwninit() to .zshrc ===
echo '[*] Adding pwninit() function to ~/.zshrc...'
sed -i '/^pwninit() {/,/^}/d' ~/.zshrc
sed -i ':a;/^[[:space:]]*$/{$d;N;ba}' ~/.zshrc
cat << 'EOF' >> ~/.zshrc

pwninit() {
  local TEMPLATE_PATH=~/.config/pwninit-templates/default_template.py
  local LIBS_PATH=~/.config/pwninit-libs
  local BINARY_NAME=""
  local SHOW_HELP=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --heap)
        TEMPLATE_PATH=~/.config/pwninit-templates/heap_template.py
        shift
        ;;
      -h|--help)
        SHOW_HELP=true
        shift
        ;;
      -*)
        echo "Unknown option: $1"
        return 1
        ;;
      *)
        BINARY_NAME="$1"
        shift
        ;;
    esac
  done

  if [[ "$SHOW_HELP" = true || -z "$BINARY_NAME" ]]; then
    echo "Usage: pwninit [--heap] <binary-name>"
    echo "Example: pwninit --heap chall"
    echo
    echo "Wrapper for the pwninit command using custom template path and binary name."
    return 0
  fi
  command cp -r "$LIBS_PATH"/*  ./libs
  command pwninit --template-path "$TEMPLATE_PATH" --template-bin-name "$BINARY_NAME"
}

EOF
  echo "[*] Function added."

# === Reload shell ===
source ~/.zshrc
echo "[*] Done. Please restart your terminal or run 'source ~/.zshrc'."
