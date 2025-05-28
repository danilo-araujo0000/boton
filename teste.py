import subprocess


def reiniciar():
    print("Reiniciando o processo...")
    # Usando barras duplas para escapar corretamente o caminho
    subprocess.Popen(["C:\\Botão_panico\\agendador_de_tarefas.exe"], shell=True)   
    
    
if __name__ == "__main__":
    reiniciar()
