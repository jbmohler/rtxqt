import os
import sys
import subprocess
import PySide6


def get_qrc_compiler():
    base_name = "pyside6-rcc"
    if sys.platform.lower().startswith("win"):
        base_name += ".exe"
    qrc_compiler = os.path.join(PySide6.__path__[0], base_name)
    if not os.path.exists(qrc_compiler):
        qrc_compiler = base_name
    return qrc_compiler


RCC = get_qrc_compiler()
PY3 = sys.version > "3"

ROOTED = [
    ("lmssystem/lmsicons.qrc", "lmsicons.py"),
    ("apputils/rtxassets.qrc", "rtxassets.py"),
    ("apputils/widgets/icons.qrc", "icons.py"),
    ("contacts/gui/icons.qrc", "icons.py"),
    ("client/qt/icons.qrc", "icons.py"),
]

ROOTTUPLE = [p[0].rsplit("/", 1) + [p[1]] for p in ROOTED]

for R in ROOTTUPLE:
    path = R[0].replace("/", os.path.sep)
    qrc_file = os.path.join(path, R[1])
    py_file = os.path.join(path, R[2])
    print(R)
    print([RCC, qrc_file, "-o", py_file])
    rccprocess = subprocess.Popen([RCC, qrc_file, "-o", py_file])
    rccprocess.wait()
    # os.system(r'{RCC} {PATH}\{IN} -py3 -o {PATH}\{OUT}'.format(RCC=RCC, PATH=R[0], IN=R[1], OUT=R[2]))
