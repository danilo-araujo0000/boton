import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import threading
from lixo.servidor import main  # Importa a função principal do servidor

class ServidorServico(win32serviceutil.ServiceFramework):
    _svc_name_ = "Servidor violeta"
    _svc_display_name_ = "Servidor violeta"
    _svc_description_ = "Servidor que gerencia  os processos do botao do panico"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.is_running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        self.run()

def run(self):
    # Informe ao Windows que o serviço foi iniciado
    servicemanager.LogMsg(
        servicemanager.EVENTLOG_INFORMATION_TYPE,
        servicemanager.PYS_SERVICE_STARTED,
        (self._svc_name_, "")
    )
    try:
        # Inicie o servidor em uma thread separada
        threading.Thread(target=main, daemon=True).start()
        while self.is_running:
            win32event.WaitForSingleObject(self.stop_event, 5000)
    except Exception as e:
        servicemanager.LogErrorMsg(str(e))  # Log de erros para debug
        self.is_running = False


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(ServidorServico)
