import subprocess
import re

def hi(p):
    """
    Возвращает только чистый вывод команд bins/tcachebins/... без мусора.
    """
    gdb_script = '''
    set pagination off
    bins
    detach
    quit
    '''

    # Запускаем GDB, передаём скрипт через stdin, читаем stdout
    result = subprocess.run(
        ['gdb', '-q', p.executable, str(p.pid)],
        input=gdb_script.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    output = result.stdout.decode(errors='ignore')

    # Удаляем всё до последнего появления bins/tcachebins
    bins_output_match = re.search(r'(tcachebins|bins|fastbins|smallbins|largebins|unsortedbin)[\s\S]*', output)
    if not bins_output_match:
        return "No bin output found"

    bins_output = bins_output_match.group(0)

    clean_lines = []
    for line in bins_output.splitlines():
        line = re.sub(r'\x01|\x02', '', line)  # управляющие символы
        line = line.strip()
        if not line:
            continue
        if line.startswith('pwndbg>'):
            continue
        if 'pwndbg' in line:
            continue
        if line.startswith('[Inferior'):
            continue
        clean_lines.append(line)
    print('\n'.join(clean_lines))
