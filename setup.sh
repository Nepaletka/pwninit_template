#!/bin/zsh

TEMPLATE=~/.config/pwninit-template.py

if [[ -f "$TEMPLATE" ]]; then
  echo -n "[*] Template already exists! Rewrite? [Y/N]: "
  read answer
  if [[ "$answer" != "Y" ]]; then
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
  command pwninit --template-path ~/.config/pwninit-template.py --template-bin-name "$1"
}
EOF
  echo "[*] Function added."
else
  echo "[*] Function already exists in ~/.zshrc"
fi

source ~/.zshrc
echo "[*] Done. Please restart your terminal or run 'source ~/.zshrc' from within Zsh."
