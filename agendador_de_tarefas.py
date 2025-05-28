# esse script abre e fecha o receptor, para evitar que o receptor seja aberto indefinidamente

import subprocess
import time

def abrir_receptor():

    try:
        subprocess.Popen(["C:\\Botão_panico\\Receptor.exe"], shell=True)
    except:
        pass

def fechar_receptor():
    try:
        subprocess.run(["taskkill", "/IM", "Receptor.exe", "/F"], shell=True)
    except:
        pass

def exec_tarefa():
   fechar_receptor()
   time.sleep(10)
   abrir_receptor()





if __name__ == "__main__":
   exec_tarefa()
   
# comando para criar o executavel: pyinstaller --onefile  --icon=C:\Botão_panico\icons\calendario.png agendador_de_tarefas.py    