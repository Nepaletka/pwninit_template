# Отладка через OrbStack и Ghostty

## Установка

В fish запусти `./install-macos.sh --shell fish`, затем
`source ~/.config/fish/conf.d/pwninit.fish`. В zsh используй `--shell zsh` и
`source ~/.zshrc`. Без флага выбирается оболочка родительского процесса или `$SHELL`.
Нужны Homebrew и настроенный alias `ssh orb`. Установщик ставит локальные
инструменты; QEMU устанавливается внутри VM отдельно:

```sh
ssh -t orb 'sudo apt install -y qemu-user'
```

Установщик устанавливает Python 3.13 и CMake, затем создаёт отдельный venv
`pwninit-env-py313` с pwntools. Старое окружение Python 3.15 остаётся нетронутым. `pwnpy` запускает этот
Python, а `pwninit` вызывает собранный upstream pwninit с нужным шаблоном.
Можно задать `--config-dir /path`, `--zshrc /path` или `--fish-config /path`.
Учитываются `XDG_CONFIG_HOME` и `ZDOTDIR`. Fish получает отдельный conf.d-файл;
`.zshrc` при выборе fish не меняется. В zsh заменяются сгенерированный блок и
старая функция pwninit; прочие настройки сохраняются. Первоначальный файл
сохраняется рядом с суффиксом `.pwninit.bak`.

На Mac утилита Linux `eu-unstrip` недоступна: upstream pwninit может вывести
предупреждение при попытке добавить debug symbols к libc. Для этого шага можно
использовать pwninit/elfutils внутри Linux VM; передача готовых libc/loader в
отладчик от этого не зависит.

## Компиляция на VM

```sh
pwncompile test.c -o chall
pwninit chall
pwnpy solve.py GDB
```

Команда pwncompile доступна в fish и zsh после обновления shell-интеграции.
`./setup.sh --shell fish --keep-templates` обновляет команды, сохраняя
пользовательские шаблоны. Затем выполни напечатанную команду source.

Сборка использует GCC в `orb`, временный каталог для одного исходника и флаги
`-m64 -g3 -O0 -fno-omit-frame-pointer`. Имя без расширения используется как
выходной файл в текущем каталоге, если `-o` не задан. `--cc g++` выбирает C++;
`--host` меняет SSH alias. Флаги после `--` добавляются к GCC, например
`pwncompile test.c -o chall -- -m32` (в VM нужен multilib).

При ошибке GCC файл результата на Mac не заменяется. Перед заменой проверяется
ELF-заголовок. Отладочные пути перенаправляются к локальному исходнику на Mac.
Заголовки и другие исходники проекта автоматически не загружаются.

## Запуск

В Ghostty 1.3+ достаточно:

```sh
pwninit chall
pwnpy solve.py GDB
```

При первом AppleScript-вызове macOS может запросить Automation-доступ к Ghostty.
Отладчик открывается в правой панели. Если открытого окна нет, создаётся окно.
Существующие настройки и горячие клавиши Ghostty не меняются.

Без `GDB` запускается только программа через QEMU. `DEBUG` включает подробные
логи pwntools. Шаблон с `GDB` останавливается на `main`; введи `continue` в
pwndbg для продолжения. У stripped-бинаря без main замени вызов на `debug(p)`
или укажи подходящий breakpoint.

Существующие task-каталоги содержат собственную копию `libs/debug.py`: её нужно
обновить отдельно. В старом solve.py убери обязательный `context.terminal` с
tmux/gnome-terminal и замени запуск на:

```python
p = orb_process(exe, gdb_enabled=bool(args.GDB))
if args.GDB:
    debug(p, 'break main\ncontinue')
```

`debug(p)` вызывается до первого send/recv: QEMU ждёт подключения.
`sendline`, `recvuntil`, `interactive` и сокращения шаблона работают с тем же p.
Для принудительного выбора Ghostty есть `debug(p, terminal='ghostty')`.
Чтобы использовать tmux, явно установи `context.terminal = ['tmux', 'splitw', '-h']`.

## libc и loader

Сгенерированные upstream pwninit ELF-привязки используются в шаблонах напрямую.
При наличии привязок libc/ld они автоматически передаются в orb_process.
Вручную это выглядит так:

```python
p = orb_process(
    exe,
    gdb_enabled=bool(args.GDB),
    files=['libc.so.6'],
    loader='ld-linux-x86-64.so.2',
)
```

Используй имя loader из своего таска. Файлы загружаются только из явно заданного
списка; symlink разыменовываются с сохранением исходного имени. Имена файлов
сохраняются, подкаталоги не переносятся. Совпадающие имена разных файлов запрещены.
Название libc должно совпадать с тем, что ищет загрузчик, обычно `libc.so.6`.

QEMU получает отдельный interpreter prefix с loader по исходному PT_INTERP,
поэтому абсолютный interpreter path в `_patched` работает внутри VM без
изменения ELF и базы PIE. `LD_LIBRARY_PATH=.` выбирает загруженную libc.
Дополнительные зависимости и данные передаются через `files`.

Параметры: `host='orb'`, `port=1234`, `argv=[...]`, `env={...}`.
Поддерживаются Linux amd64 и i386; для i386 нужны соответствующие 32-битные
loader и библиотеки. i386 отдельно не тестировался.

## Ввод/вывод и очистка

SSH работает без PTY и без отключения stdin: байты NUL/0xff проходят без
изменений. stderr выводится отдельно от pwntools tube. Pipes не отключают
буферизацию libc: если таск не сбрасывает prompt, ожидание sendlineafter может
потребовать настройки буферизации в самой программе.

При p.close() и обычном завершении Python удаляется каталог сессии, закрывается
SSH-туннель и завершаются записанный QEMU-процесс и pwndbg из созданной панели
Ghostty. Перед завершением процессы проверяются на принадлежность этой сессии.
VM OrbStack продолжает работать. При SIGKILL, потере связи, fork или смене cwd
программой очистка может потребоваться вручную.

Для параллельных запусков выбирай разные значения port: один и тот же порт
должен быть свободен на Mac и в VM. Это отладка твоей VM; remote(host, port)
сам по себе не предоставляет доступ к отладчику чужого CTF-сервиса.

## Проверки

```sh
python3 -m unittest discover -s tests -v
```

Тесты проверяют повторную установку, сохранение `.zshrc` и backup, работу
функций в настоящем fish, пути с пробелами/кавычками, выбор Python 3.13 и CMake,
отклонение Mach-O, heap-шаблон, аргументы upstream pwninit и генерацию solve.py.
Также проверяются доступность pwncompile в обеих оболочках, сохранение своих
шаблонов, очистка после ошибки GCC и сохранение предыдущего бинарника.
Homebrew/Cargo-команды в unit-тесте заменены mock: зависимости на компьютере
не устанавливаются при запуске тестов.

Дополнительно проверен полный цикл на подключённом orb и Ghostty 1.3.1:
брейкпоинт в main, бинарный обмен с NUL/0xff, loader/libc через symlink и
завершение отладчика с удалением каталога сессии. Для pwncompile проверена реальная
сборка через fish/SSH: пробелы и кавычки в путях, дополнительные флаги, x86-64 ELF,
отображение локального исходника в GDB и исполнение полученного файла в QEMU.

Справка: [Ghostty AppleScript](https://ghostty.org/docs/features/applescript),
[OrbStack debugging](https://docs.orbstack.dev/machines/#debugging-with-gdb-lldb),
[pwninit](https://github.com/io12/pwninit).
