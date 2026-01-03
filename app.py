from flask import Flask, render_template, request, redirect, url_for
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from datetime import datetime
import sqlite3
import os
import re

# ==================================================
# APP
# ==================================================
app = Flask(__name__)

# ==================================================
# CAMINHOS
# ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "avaliacoes.db")
PASTA_RELATORIOS = os.path.join(BASE_DIR, "relatorios")
os.makedirs(PASTA_RELATORIOS, exist_ok=True)

# ==================================================
# CONTROLE SIMPLES DE SESSÃO
# ==================================================
empresa_id_atual = None

# ==================================================
# BANCO DE DADOS
# ==================================================
def conectar_db():
    return sqlite3.connect(DB_NAME)

def criar_tabelas():
    conn = conectar_db()
    c = conn.cursor()

    # Tabelas
    c.execute("""
        CREATE TABLE IF NOT EXISTS empresa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS dimensao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS pergunta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dimensao_id INTEGER NOT NULL,
            texto TEXT NOT NULL,
            invertida INTEGER DEFAULT 0,
            UNIQUE(dimensao_id, texto),
            FOREIGN KEY(dimensao_id) REFERENCES dimensao(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS participante (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            data TEXT,
            FOREIGN KEY(empresa_id) REFERENCES empresa(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS resposta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participante_id INTEGER,
            pergunta_id INTEGER,
            valor INTEGER,
            FOREIGN KEY(participante_id) REFERENCES participante(id),
            FOREIGN KEY(pergunta_id) REFERENCES pergunta(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS relatorio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            caminho_pdf TEXT,
            data TEXT
        )
    """)
    conn.commit()
    conn.close()

# ==================================================
# MIGRAÇÃO DE PERGUNTAS
# ==================================================
def migrar_perguntas():
    conn = conectar_db()
    c = conn.cursor()

    # Dimensão
    c.execute("INSERT OR IGNORE INTO dimensao (nome) VALUES (?)", ("Demandas de Trabalho",))
    c.execute("SELECT id FROM dimensao WHERE nome = ?", ("Demandas de Trabalho",))
    dimensao_id = c.fetchone()[0]

    perguntas = [
        # 1A)
        ("Você atrasa a entrega do seu trabalho?", 4, True),
        # 1B)
        ("O tempo para realizar as suas tarefas no trabalho é suficiente?", 4, True),
        # 2A)
        ("É necessário manter um ritmo acelerado no trabalho?", 4, True),
        # 2B)
        ("Você trabalha em ritmo acelerado ao longo de toda jornada?", 4, True),
        # 3A)
        ("Seu trabalho coloca você em situações emocionalmente desgastantes?", 4, True),
        # 3B)
        ("Você tem que lidar com os problemas pessoais de outras pessoas como parte do seu trabalho?", 4, True),
        # 4A)
        ("Você tem um alto grau de influência nas decisões sobre o seu trabalho?", 4, False),
        # 4B)
        ("Você pode interferir na quantidade de trabalho atribuída a você?", 4, False),
        # 5A)
        ("Você tem a possibilidade de aprender coisas novas através do seu trabalho?", 4, False),
        # 5B)
        ("Seu trabalho exige que você tome iniciativas?", 4, False),
        # 6A)
        ("Seu trabalho é significativo?", 4, False),
        # 6B)
        ("Você sente que o trabalho que faz é importante?", 4, False),
        # 7A)
        ("Você sente que o seu local de trabalho é muito importante para você?", 4, False),
        # 7B)
        ("Você recomendaria a um amigo que se candidatasse a uma vaga no seu local de trabalho?", 4, False),
        # 8A)
        ("Você é informado antecipadamente sobre decisões importantes ou mudanças?", 4, False),
        # 8B)
        ("Você recebe toda a informação necessária para fazer bem o seu trabalho?", 4, False),
        # 9A)
        ("O seu trabalho é reconhecido e valorizado pelos seus superiores?", 4, False),
        # 9B)
        ("Você é tratado de forma justa no seu local de trabalho?", 4, False),
        # 10A)
        ("O seu trabalho tem objetivos claros?", 4, False),
        # 10B)
        ("Você sabe exatamente o que se espera de você no trabalho?", 4, False),
        # 11A)
        ("Seu superior imediato dá alta prioridade à satisfação com o trabalho?", 4, False),
        # 11B)
        ("Seu superior imediato é bom no planejamento do trabalho?", 4, False),
        # 12A)
        ("Com que frequência seu superior imediato ouve seus problemas?", 4, False),
        # 12B)
        ("Com que frequência você recebe ajuda do seu superior imediato?", 4, False),
        # 13)
        ("Qual o seu nível de satisfação com o trabalho como um todo?", 3, False),
        
        #As próximas duas perguntas são sobre a forma como o seu trabalho afeta a sua vida particular e familiar.
        # 14A)
        ("Seu trabalho afeta negativamente sua vida particular por consumir muita energia?", 3, True),
        # 14B)
        ("Seu trabalho afeta negativamente sua vida particular por ocupar muito tempo?", 3, True),

        # As próximas quatro perguntas não são sobre o seu próprio trabalho, mas sobre a empresa em que você trabalha.
        # 15A)
        ("Você pode confiar nas informações que vêm dos seus superiores?", 4, False),
        # 15B)
        ("Os superiores confiam que os funcionários farão bem o trabalho?", 4, False),
        # 16A)
        ("Os conflitos são resolvidos de forma justa?", 4, False),
        # 16B)
        ("O trabalho é distribuído de forma justa?", 4, False),
        

        #As próximas cinco perguntas são sobre a sua própria saúde e bem-estar. Por favor, tente não
# distinguir entre sintomas que são causados pelo trabalho e sintomas que se devem a outras
# causas. Descreva como você está no geral.
# As perguntas são sobre a sua saúde e bem-estar nas últimas quatro semanas:
        ("Em geral, como você avalia sua saúde?", 4, False), #17)
        ("Com que frequência você se sente fisicamente esgotado?", 4, True), #18A)
        ("Com que frequência você se sente emocionalmente esgotado?", 4, True), #18B)
        ("Com que frequência você se sente estressado?", 4, True), #19A)
        ("Com que frequência você se sente irritado?", 4, True), #19B)

        # Violência e assédio
        ("Você foi exposto a atenção sexual indesejada no seu local de trabalho durante os últimos 12 meses?", 4, True), #20)
# Se sim, de quem? (Você pode assinalar mais de uma opção)
# ( ) Colegas ( ) Gerente, supervisor ( ) Subordinados ( ) Clientes, fregueses, pacientes

        ("Você foi exposto a ameaças de violência no seu local de trabalho nos últimos 12 meses?", 4, True), #21)
# Se sim, de quem? (Você pode assinalar mais de uma opção)
# ( ) Colegas ( ) Gerente, supervisor ( ) Subordinados ( ) Clientes, fregueses, pacientes

        ("Você foi exposto a violência física em seu local de trabalho durante os últimos 12 meses?", 4, True), #22)
# Se sim, de quem? (Você pode assinalar mais de uma opção)
# ( ) Colegas ( ) Gerente, supervisor ( ) Subordinados ( ) Clientes, fregueses, pacientes


# “Bullying” significa que uma pessoa é repetidamente exposta a tratamento desagradável ou
# degradante, do qual a vítima tem dificuldade para se defender.
        ("Você foi exposto a “bullying” no seu local de trabalho nos últimos 12 meses", 4, True) #23)
#        Se sim, de quem? (Você pode assinalar mais de uma opção)
# ( ) Colegas ( ) Gerente, supervisor ( ) Subordinados ( ) Clientes, fregueses, pacientes
    ]

    for texto, valor_maximo, invertida in perguntas:
        c.execute("""
            INSERT OR IGNORE INTO pergunta (dimensao_id, texto, invertida)
            VALUES (?, ?, ?)
        """, (dimensao_id, texto, int(invertida)))  # 0/1

    conn.commit()
    conn.close()


# No Python: lista de opções por pergunta
opcoes_pergunta = {
    1: ["Sempre", "Frequentemente", "Às vezes", "Raramente", "Nunca"],
    2: ["Em grande parte", "Em boa parte", "De certa forma", "Um pouco", "Muito pouco"],
    3: ["Muito satisfeito", "Satisfeito", "Insatisfeito", "Muito insatisfeito"],
    4: ["Sim, com certeza", "Sim, até certo ponto", "Sim, mas muito pouco", "Não, realmente não"],
    5: ["Excelente", "Muito boa", "Boa", "Razoável", "Ruim"],
    6: ["Sim, diariamente", "Sim, semanalmente", "Sim, mensalmente", "Sim, poucas vezes", "Não"]
    # ... e assim por diante
    # QUE DESGRAÇA TEM UMA CONDIÇÃO "SE SIM" FAZ O L!!!!!!!!!!
}

# Inicializa banco e perguntas
criar_tabelas()
migrar_perguntas()

# ==================================================
# FUNÇÕES AUXILIARES
# ==================================================
def nome_seguro(texto):
    """Nome seguro para gerar arquivos"""
    return re.sub(r"[^\w\-]", "_", texto.strip().lower())

def calcular_medias_copsoq(respostas_por_dimensao):
    """Calcula média por dimensão"""
    resultados = {}
    for dimensao, respostas in respostas_por_dimensao.items():
        medias_individuais = [sum(r) / len(r) for r in respostas]
        resultados[dimensao] = round(sum(medias_individuais) / len(medias_individuais), 2)
    return resultados

def classificar_risco(media):
    """Classificação por média"""
    if media <= 2.33:
        return "🟢 Situação Favorável"
    elif media <= 3.66:
        return "🟡 Risco Intermediário"
    else:
        return "🔴 Risco para a Saúde"

def gerar_pdf(empresa, total, resultados):
    """Gera PDF com relatório"""
    nome_limpo = nome_seguro(empresa)
    data = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(PASTA_RELATORIOS, f"relatorio_{nome_limpo}_{data}.pdf")

    estilos = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("Relatório Técnico – Avaliação Psicossocial", estilos["Title"]))
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"<b>Empresa:</b> {empresa}", estilos["Normal"]))
    elementos.append(Paragraph(f"<b>Participantes:</b> {total}", estilos["Normal"]))
    elementos.append(Paragraph(f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos["Normal"]))
    elementos.append(Spacer(1, 20))

    for dim, media in resultados.items():
        elementos.append(Paragraph(dim, estilos["Heading2"]))
        elementos.append(Paragraph(f"Média: {media}", estilos["Normal"]))
        elementos.append(Paragraph(f"Classificação: {classificar_risco(media)}", estilos["Normal"]))
        elementos.append(Spacer(1, 15))

    SimpleDocTemplate(caminho, pagesize=A4).build(elementos)
    return caminho

# ==================================================
# ROTAS
# ==================================================
@app.route("/", methods=["GET", "POST"])
def empresa():
    global empresa_id_atual
    if request.method == "POST":
        nome = request.form["empresa"]
        conn = conectar_db()
        c = conn.cursor()
        c.execute("INSERT INTO empresa (nome, data) VALUES (?, ?)",
                  (nome, datetime.now().strftime("%Y-%m-%d %H:%M")))
        empresa_id_atual = c.lastrowid
        conn.commit()
        conn.close()
        return redirect(url_for("questionario"))
    return render_template("empresa.html")

@app.route("/questionario", methods=["GET", "POST"])
def questionario():
    if request.method == "POST":
        conn = conectar_db()
        c = conn.cursor()
        c.execute("INSERT INTO participante (empresa_id, data) VALUES (?, ?)",
                  (empresa_id_atual, datetime.now().strftime("%Y-%m-%d %H:%M")))
        participante_id = c.lastrowid

        for campo, valor in request.form.items():
            if campo.startswith("pergunta_"):
                pergunta_id = int(campo.replace("pergunta_", ""))
                c.execute("INSERT INTO resposta (participante_id, pergunta_id, valor) VALUES (?, ?, ?)",
                          (participante_id, pergunta_id, int(valor)))

        conn.commit()
        conn.close()
        return redirect(url_for("continuar"))

    conn = conectar_db()
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.texto, p.invertida, d.nome
        FROM pergunta p
        JOIN dimensao d ON p.dimensao_id = d.id
        ORDER BY d.id, p.id
    """)
    perguntas = c.fetchall()
    conn.close()
    return render_template("questionario.html", perguntas=perguntas)

@app.route("/continuar")
def continuar():
    conn = conectar_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM participante WHERE empresa_id = ?", (empresa_id_atual,))
    total = c.fetchone()[0]
    conn.close()
    return render_template("continuar.html", total=total)

@app.route("/novo")
def novo():
    return redirect(url_for("questionario"))

@app.route("/finalizar")
def finalizar():
    conn = conectar_db()
    c = conn.cursor()
    c.execute("""
        SELECT d.nome, r.valor, pa.id, p.invertida
        FROM resposta r
        JOIN pergunta p ON r.pergunta_id = p.id
        JOIN dimensao d ON p.dimensao_id = d.id
        JOIN participante pa ON r.participante_id = pa.id
        WHERE pa.empresa_id = ?
    """, (empresa_id_atual,))
    dados = c.fetchall()
    c.execute("SELECT nome FROM empresa WHERE id = ?", (empresa_id_atual,))
    empresa_nome = c.fetchone()[0]
    conn.close()

    ESCALA_MAX = 4  # Escala máxima usada para inversão

    respostas_por_dimensao = {}
    for dim, valor, participante, invertida in dados:
        respostas_por_dimensao.setdefault(dim, {})
        respostas_por_dimensao[dim].setdefault(participante, [])
        if invertida:
            valor = ESCALA_MAX - valor  # Aplica inversão corretamente
        respostas_por_dimensao[dim][participante].append(valor)

    respostas_formatadas = {dim: list(part.values()) for dim, part in respostas_por_dimensao.items()}
    medias = calcular_medias_copsoq(respostas_formatadas)
    caminho_pdf = gerar_pdf(empresa_nome, len(set(p for _, _, p, _ in dados)), medias)

    conn = conectar_db()
    c = conn.cursor()
    c.execute("INSERT INTO relatorio (empresa_id, caminho_pdf, data) VALUES (?, ?, ?)",
              (empresa_id_atual, caminho_pdf, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    return render_template("encerramento.html")

# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":
    app.run(debug=True)