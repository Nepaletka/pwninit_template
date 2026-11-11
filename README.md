# pwninit_template

Шаблоны pwntools для Linux x86/x86-64 тасков на Mac: программа работает через
QEMU в `orb`, pwndbg открывается в панели Ghostty. tmux не обязателен.

## Установка на macOS

Нужны [Homebrew](https://brew.sh), Ghostty 1.3+ и настроенный `ssh orb`.
Установщик добавит недостающий Ghostty, если приложения ещё нет.

```sh
git clone -b codex/orb-pwntools-debug https://github.com/Nepaletka/pwninit_template.git
cd pwninit_template
./install-macos.sh
source ~/.zshrc
ssh -t orb 'sudo apt install -y qemu-user'
```

Устанавливаются Homebrew Python, Rust, зависимости сборки pwninit, patchelf,
pwndbg и pwntools в отдельном venv. pwninit собирается через Cargo в каталог
настроек проекта. Системный Python и конфиг Ghostty не меняются.

Повторный запуск обновляет шаблоны и сохраняет один блок подключения в `.zshrc`.
Перед первым изменением создаётся `.zshrc.pwninit.bak`. Установщик не выполняет
`.zshrc` сам: команду `source` нужно выполнить в своём терминале.

## Использование в Ghostty

```sh
pwninit chall
pwnpy solve.py GDB
```

```sh
pwninit --heap chall
pwnpy solve.py
```

`pwnpy` использует Python с установленным pwntools. `GDB` запускает отладчик;
без этого флага программа работает через QEMU с обычным pwntools I/O.
`DEBUG` включает подробный лог pwntools. Можно передать upstream pwninit
дополнительные опции, например `pwninit chall --libc libc.so.6 --ld ld.so`.

Если зависимости уже установлены, для установки только шаблонов и shell-команд:

```sh
./setup.sh
```

На Mac также доступно `./install-macos.sh --skip-deps`. Этот режим использует
текущий Python и существующий pwninit; он не создаёт окружение с зависимостями.

Подробнее: [отладка, библиотеки и очистка](docs/orb-debugging.md).
