# pwninit_template

Шаблоны pwntools для Linux x86/x86-64 тасков на Mac: программа работает через
QEMU в `orb`, pwndbg открывается в панели Ghostty. tmux не обязателен.

## Установка на macOS

Нужны [Homebrew](https://brew.sh), Ghostty 1.3+ и настроенный `ssh orb`.
Установщик добавит недостающий Ghostty, если приложения ещё нет.

```sh
git clone -b codex/orb-pwntools-debug https://github.com/Nepaletka/pwninit_template.git
cd pwninit_template
./install-macos.sh --shell fish
source ~/.config/fish/conf.d/pwninit.fish
ssh -t orb 'sudo apt install -y qemu-user'
```

Устанавливаются Homebrew Python 3.13, CMake, Rust, зависимости сборки pwninit, patchelf,
pwndbg и pwntools в отдельном venv. pwninit собирается через Cargo в каталог
настроек проекта. Системный Python и конфиг Ghostty не меняются.

В fish функции устанавливаются в `~/.config/fish/conf.d/pwninit.fish`. Для zsh
используй `./install-macos.sh --shell zsh`, затем `source ~/.zshrc`. Без `--shell`
установщик определяет fish/zsh по родительскому процессу и `$SHELL`.

Повторный запуск не дублирует настройки. Перед первым изменением существующего
файла сохраняется backup с суффиксом `.pwninit.bak`. Установщик сам не выполняет
shell-конфиги: команду `source` нужно выполнить в своём терминале.

Окружение Python 3.13 создаётся в `~/.config/pwninit-env-py313`. Старое
`pwninit-env` (в том числе неудачная установка на Python 3.15) не переиспользуется
и не удаляется. На Apple Silicon Unicorn может собираться из исходников, поэтому
CMake обязателен.

## Если у тебя только исходник C

Компилируй внутри Linux VM. Обычный `gcc` на macOS создаёт Mach-O, а здесь нужен
Linux ELF:

```sh
scp test.c orb:/tmp/test.c
ssh orb 'gcc -g3 -O0 -fno-omit-frame-pointer /tmp/test.c -o /tmp/chall'
scp orb:/tmp/chall ./chall
file chall
```

В выводе `file` должно быть `ELF`, а не `Mach-O`. Затем:

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
