# Sistema de Botão de Pânico

Sistema completo para gerenciamento de alertas de emergência através de botões de pânico distribuídos.

## Estrutura do Projeto

```
├── env_config/           # Configurações de ambiente
│   └── env_settings.env  # Variáveis de ambiente
├── logs_data/            # Arquivos de log
├── src/                  # Código-fonte principal
│   ├── app.py            # Aplicação web administrativa
│   ├── client.py         # Cliente (botão de pânico)
│   ├── config.py         # Configurações gerais
│   ├── receptor.py       # Receptor de alertas
│   └── server.py         # Servidor principal
├── static/               # Arquivos estáticos
│   ├── css/              # Folhas de estilo
│   ├── js/               # JavaScript
│   └── ico/              # Ícones
├── templates/            # Templates HTML
├── main.py               # Ponto de entrada principal
└── README.md             # Este arquivo
```

## Componentes do Sistema

O sistema é dividido em quatro componentes principais:

1. **Servidor Principal** (`server.py`): 
   - Gerencia conexões com clientes e receptores
   - Encaminha alertas dos clientes para os receptores

2. **Aplicação Web** (`app.py`): 
   - Interface de administração
   - Gerencia salas, clientes mestres e visualiza logs

3. **Receptor** (`receptor.py`): 
   - Recebe e exibe alertas
   - Modo GUI e terminal disponíveis

4. **Cliente** (`client.py`): 
   - Botão de pânico que envia alertas
   - Interface gráfica com atalho de teclado

## Requisitos

- Python 3.7+
- MySQL/MariaDB
- Pacotes Python (ver `requirements.txt`)


## Execução

O sistema utiliza um ponto de entrada principal (`main.py`) para iniciar os diferentes componentes:

- **Servidor**:
  ```
  python main.py server
  ```

- **Aplicação Web**:
  ```
  python main.py app
  ```

- **Receptor** (modo terminal):
  ```
  python main.py receptor
  ```

- **Receptor** (modo GUI):
  ```
  python main.py receptor --gui
  ```

- **Cliente** (botão de pânico):
  ```
  python main.py client
  ```

## Configuração

A configuração principal é feita através do arquivo `env_config/env_settings.env`, que contém:

- Configurações de banco de dados
- Endereços IP e portas
- Parâmetros de segurança
- Configurações de log

Para reconfigurar o sistema, execute:
```
python main.py setup
```

## Acesso à Interface Web

Após iniciar a aplicação web, acesse:

```
http://localhost:5000
```

Credenciais padrão:
- Usuário: admin@example.com
- Senha: admin123

## Logs

Os arquivos de log são armazenados no diretório `logs_data/`:

- `servidor.log`: Logs do servidor principal
- `admin.log`: Logs da aplicação web
- `receptor.log`: Logs do receptor
- `cliente.log`: Logs do cliente 