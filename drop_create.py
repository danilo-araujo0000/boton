#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from flask import Flask
from database.models import db
from config import Config

def main():
    """Script para recriar todas as tabelas do banco de dados"""
    print("Recriando tabelas do banco de dados...")
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.get_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        # Excluir todas as tabelas existentes
        print("Excluindo tabelas existentes...")
        db.drop_all()
        
        # Criar tabelas novamente
        print("Criando tabelas...")
        db.create_all()
        
        print("Tabelas recriadas com sucesso!")

if __name__ == "__main__":
    main() 