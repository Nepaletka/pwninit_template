#!/bin/zsh

TEMPLATE=~/.config/pwninit-template.py

if [[ -f "$TEMPLATE" ]]; then
  echo -n "[*] Template already exists! Rewrite? [y/N]: "
  read answer
  if [[ "$answer" != "y" ]]; then
    echo "[*] Aborted."
    exit 0
  fi
fi

echo "[*] Creating config..."
cp ./pwninit-template.py "$TEMPLATE"

echo '[*] Adding pwninit() function to ~/.zshrc...'
if ! grep -q 'pwninit()' ~/.zshrc; then
  cat << 'EOF' >> ~/.zshrc

pwninit() {
  if [ -z "$1" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: pwninit <binary-name>"
    echo "Example: pwninit chall"
    echo
    echo "Wrapper for the pwninit command using custom template path and binary name."
    return 0
  fi

  command pwninit --template-path ~/.config/pwninit-template.py --template-bin-name "$1"
}

EOF
  echo "[*] Function added."
else
  echo "[*] Function already exists in ~/.zshrc"
fi

source ~/.zshrc
echo "[*] Done. Please restart your terminal or run 'source ~/.zshrc' from within Zsh."
