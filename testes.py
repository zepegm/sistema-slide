import subprocess
import os
import signal
import psutil

def kill_existing_process(script_name):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        #print(f"Encerrando o processo existente de PID {proc.pid} - {proc.name}")

        try:
            print(proc.info['cmdline'])
            if script_name in proc.info['cmdline']:
                print(f"Encerrando o processo existente de PID {proc.pid} - {proc.name}")
                #os.kill(proc.pid, signal.SIGTERM)
                break
        except:
            pass
    else:
        print("Nenhum processo existente foi encontrado.")

def start_new_process(script_path):
    # Executa o seu script.
    subprocess.run(['python', script_path])

# Substitua 'nome_do_seu_script.py' pelo nome do seu script
kill_existing_process('app.py')

# Substitua 'caminho_para_o_seu_script.py' pelo caminho do seu script
#start_new_process('caminho_para_o_seu_script.py')
