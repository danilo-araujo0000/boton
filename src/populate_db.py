import mysql.connector

conn = mysql.connector.connect(
    host='172.19.0.76',
    user='apps',
    password='996639078',
    database='botao_panico'
)

cursor = conn.cursor()



def populate_db():
    query = """
    INSERT INTO receptores (ip_receptor, nome_receptor) VALUES ('172.19.200.1', 'danilo_sti');
    """
    cursor.execute(query)
    conn.commit()
    conn.close()



populate_db()