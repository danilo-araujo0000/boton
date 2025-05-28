#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Botão de Pânico - Ponto de entrada principal
Este script permite iniciar facilmente qualquer componente do sistema
"""

import sys
import os
import argparse
from importlib import import_module

def main():
    """Função principal para iniciar os componentes do sistema"""
    parser = argparse.ArgumentParser(description='Sistema de Botão de Pânico')
    
    # Comandos principais
    parser.add_argument('comando', choices=['server', 'app', 'receptor', 'client', 'setup'],
                       help='Componente a ser executado (server=servidor, app=admin, receptor=cliente mestre, client=botão, setup=configuração)')
    
    # Argumentos opcionais
    parser.add_argument('--debug', action='store_true',
                       help='Iniciar em modo de depuração com mais logs')
    parser.add_argument('--gui', action='store_true',
                       help='Forçar interface gráfica (para receptor)')
    
    args = parser.parse_args()
    
    # Adicionar pasta do projeto ao path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Executar o componente selecionado
    try:
        if args.comando == 'server':
            # Iniciar servidor
            from src.server import ServidorBotaoPanico
            print("Iniciando Servidor do Botão de Pânico...")
            servidor = ServidorBotaoPanico()
            servidor.iniciar()
            
        elif args.comando == 'app':
            # Iniciar aplicação web de administração
            from src.app import app
            print("Iniciando Aplicação de Administração...")
            
            # Criar tabelas se não existirem
            with app.app_context():
                from src.app import db, Usuario
                from datetime import datetime
                from werkzeug.security import generate_password_hash
                
                db.create_all()
                
                # Verificar se existe um usuário admin
                admin = Usuario.query.filter_by(email='admin@example.com').first()
                if not admin:
                    admin = Usuario(
                        nome='Administrador',
                        email='admin@example.com',
                        admin=True,
                        ativo=True,
                        data_criacao=datetime.utcnow()
                    )
                    admin.set_senha('admin123')
                    db.session.add(admin)
                    db.session.commit()
                    print("Usuário admin padrão criado")
            
            # Iniciar aplicação
            from src.config import Config
            app.run(host=Config().FLASK_HOST, port=Config().FLASK_PORT, debug=args.debug)
            
        elif args.comando == 'receptor':
            # Iniciar receptor de alertas
            print("Iniciando Receptor de Alertas...")
            
            # Se --gui for especificado, força modo GUI
            # Se --debug for especificado sem --gui, modo GUI é ativado pelo debug
            gui_mode = args.gui or args.debug
            
            # Criar um array de args para o script do receptor
            receptor_args = []
            if gui_mode:
                receptor_args.append('--debug')
            
            # Reimplementando a chamada para receptor.py
            from src.receptor import main as receptor_main
            
            # Ajustar sys.argv para o script do receptor
            old_argv = sys.argv
            sys.argv = [old_argv[0]] + receptor_args
            
            # Executar main do receptor
            receptor_main()
            
            # Restaurar sys.argv
            sys.argv = old_argv
            
        elif args.comando == 'client':
            # Iniciar cliente (botão de pânico)
            print("Iniciando Cliente do Botão de Pânico...")
            from src.client import main as client_main
            client_main()
            
        elif args.comando == 'setup':
            # Configuração inicial do sistema
            print("Configurando o Sistema de Botão de Pânico...")
            setup_sistema()
            
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário.")
        return 1
    except Exception as e:
        print(f"\nErro ao executar {args.comando}: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

def setup_sistema():
    """Configuração inicial do sistema"""
    print("===== Configuração do Sistema de Botão de Pânico =====")
    print("Este assistente irá ajudá-lo a configurar o sistema.")
    
    # Verificar diretórios
    for diretorio in ['env_config', 'logs_data', 'static', 'templates']:
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), diretorio)
        if not os.path.exists(caminho):
            print(f"Criando diretório: {diretorio}")
            os.makedirs(caminho, exist_ok=True)
    
    # Configurações do banco de dados
    print("\n--- Configuração do Banco de Dados ---")
    db_name = input("Nome do banco de dados [dbinit]: ") or "dbinit"
    db_host = input("Host do banco de dados [localhost]: ") or "localhost"
    db_user = input("Usuário do banco de dados [root]: ") or "root"
    db_pass = input("Senha do banco de dados: ")
    db_port = input("Porta do banco de dados [3306]: ") or "3306"
    
    # Configurações do servidor
    print("\n--- Configuração do Servidor ---")
    server_host = input("Host do servidor (0.0.0.0 para todas interfaces) [0.0.0.0]: ") or "0.0.0.0"
    server_port = input("Porta do servidor [13579]: ") or "13579"
    
    # Configurações da aplicação web
    print("\n--- Configuração da Aplicação Web ---")
    flask_host = input("Host da aplicação web [0.0.0.0]: ") or "0.0.0.0"
    flask_port = input("Porta da aplicação web [5000]: ") or "5000"
    
    # Criar arquivo .env
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'env_config', 'env_settings.env')
    
    with open(env_file, 'w') as f:
        f.write(f"""# Configurações do Banco de Dados
DATABASE_NAME={db_name}
DATABASE_HOST={db_host}
DATABASE_USER={db_user}
DATABASE_PASSWORD={db_pass}
DATABASE_PORT={db_port}

# Configurações do Servidor
SERVER_HOST={server_host}
SERVER_PORT={server_port}

# Configurações do WebSocket
WEBSOCKET_HOST={server_host}
WEBSOCKET_PORT={server_port}

# Configurações do Flask Admin
FLASK_HOST={flask_host}
FLASK_PORT={flask_port}
SECRET_KEY=chave-secreta-super-segura-botao-panico-2024

# Configurações de Logs
LOG_LEVEL=INFO

# Configurações de Segurança
BCRYPT_LOG_ROUNDS=12

# Configurações de Reconexão
RECONNECT_DELAY=5
MAX_RECONNECT_ATTEMPTS=10
""")
    
    print(f"\nConfigurações salvas em: {env_file}")
    
    # Criar tabelas do banco de dados
    print("\nCriando tabelas no banco de dados...")
    try:
        # Importar app e db
        from src.app import app, db
        
        with app.app_context():
            db.create_all()
            
            # Criar usuário admin padrão
            from src.app import Usuario
            from datetime import datetime
            
            admin = Usuario.query.filter_by(email='admin@example.com').first()
            if not admin:
                admin_senha = input("\nDigite uma senha para o usuário admin [admin123]: ") or "admin123"
                admin = Usuario(
                    nome='Administrador',
                    email='admin@example.com',
                    admin=True,
                    ativo=True,
                    data_criacao=datetime.utcnow()
                )
                admin.set_senha(admin_senha)
                db.session.add(admin)
                db.session.commit()
                print("Usuário admin criado com sucesso!")
            
        print("Banco de dados configurado com sucesso!")
    
    except Exception as e:
        print(f"Erro ao configurar banco de dados: {e}")
        print("Você pode tentar criar o banco de dados manualmente e executar novamente.")
    
    print("\n=== Configuração concluída! ===")
    print("Para iniciar o servidor: python main.py server")
    print("Para iniciar a aplicação web: python main.py app")
    print("Para iniciar um receptor: python main.py receptor")
    print("Para iniciar um cliente: python main.py client")

if __name__ == "__main__":
    sys.exit(main()) 