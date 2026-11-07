import sqlite3
from pathlib import Path
from datetime import date
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "smartravel.db"
UPLOAD_DIR = APP_DIR / "fotos_roupas"
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="SmarTravel", page_icon="✈️", layout="wide")

def conectar():
    return sqlite3.connect(DB_PATH)

def preparar_banco():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS viagem (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                destino TEXT, pais TEXT, partida TEXT, retorno TEXT,
                moeda TEXT, orcamento REAL, companhia TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL, valor REAL NOT NULL,
                tipo TEXT NOT NULL, data TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS bagagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL, peso REAL NOT NULL, categoria TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS roupas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL, categoria TEXT, cor TEXT, foto TEXT
            )
        """)

def carregar_viagem():
    with conectar() as con:
        return con.execute("SELECT destino, pais, partida, retorno, moeda, orcamento, companhia FROM viagem WHERE id=1").fetchone()

def salvar_viagem(destino, pais, partida, retorno, moeda, orcamento, companhia):
    with conectar() as con:
        con.execute("""
            INSERT INTO viagem (id, destino, pais, partida, retorno, moeda, orcamento, companhia)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
            destino=excluded.destino, pais=excluded.pais, partida=excluded.partida,
            retorno=excluded.retorno, moeda=excluded.moeda, orcamento=excluded.orcamento,
            companhia=excluded.companhia
        """, (destino, pais, str(partida), str(retorno), moeda, orcamento, companhia))

def ler_tabela(sql, params=()):
    with conectar() as con:
        return con.execute(sql, params).fetchall()

def dinheiro(v, moeda):
    return f"{moeda} {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

preparar_banco()
viagem = carregar_viagem()

st.title("✈️ SmarTravel")
st.caption("Organize sua viagem em um só lugar. Preencha os campos e clique em salvar para registrar suas informações.")
st.sidebar.title("Menu")
pagina = st.sidebar.radio("O que deseja organizar?", [
    "Visão geral", "Dados da viagem", "Orçamento", "Bagagem", "Roupas e looks"
])

moeda_atual = viagem[4] if viagem else "USD"
orcamento_atual = float(viagem[5]) if viagem and viagem[5] is not None else 0.0
gastos = ler_tabela("SELECT id, descricao, valor, tipo, data FROM gastos ORDER BY id DESC")
total_gastos = sum(float(g[2]) for g in gastos if g[3] == "Despesa")
saldo = orcamento_atual - total_gastos
itens = ler_tabela("SELECT id, item, peso, categoria FROM bagagem ORDER BY id DESC")
peso_total = sum(float(i[2]) for i in itens)

if pagina == "Visão geral":
    st.header("Resumo da sua viagem")
    if viagem:
        st.subheader(f"Destino: {viagem[0] or 'Não informado'} — {viagem[1] or 'País não informado'}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Orçamento inicial", dinheiro(orcamento_atual, moeda_atual))
        c2.metric("Gastos registrados", dinheiro(total_gastos, moeda_atual))
        c3.metric("Saldo disponível", dinheiro(saldo, moeda_atual))
        st.write(f"Datas: {viagem[2] or 'Não informada'} até {viagem[3] or 'Não informada'}")
        st.write(f"Companhia aérea: {viagem[6] or 'Não informada'}")
        if orcamento_atual > 0 and saldo < orcamento_atual / 2:
            st.warning("Atenção: mais da metade do orçamento já foi utilizada.")
        if saldo < 0:
            st.error("Seus gastos ultrapassaram o orçamento!")
    else:
        st.info("Comece pela página **Dados da viagem** e preencha o formulário.")
    st.divider()
    a, b = st.columns(2)
    a.metric("Itens na bagagem", len(itens))
    b.metric("Peso total cadastrado", f"{peso_total:.2f} kg")
    st.caption("As informações são salvas em um banco de dados local (smartravel.db).")

elif pagina == "Dados da viagem":
    st.header("Dados da viagem")
    st.write("Digite as informações abaixo e clique em **Salvar viagem**.")
    with st.form("form_viagem"):
        destino = st.text_input("Cidade ou destino", value=viagem[0] if viagem and viagem[0] else "", placeholder="Ex.: Lisboa")
        pais = st.text_input("País", value=viagem[1] if viagem and viagem[1] else "", placeholder="Ex.: Portugal")
        c1, c2 = st.columns(2)
        partida_default = date.fromisoformat(viagem[2]) if viagem and viagem[2] else date.today()
        retorno_default = date.fromisoformat(viagem[3]) if viagem and viagem[3] else date.today()
        partida = c1.date_input("Data de ida", value=partida_default, format="DD/MM/YYYY")
        retorno = c2.date_input("Data de volta", value=retorno_default, format="DD/MM/YYYY")
        c3, c4 = st.columns(2)
        moeda = c3.selectbox("Moeda do orçamento", ["USD", "BRL", "EUR"], index=["USD", "BRL", "EUR"].index(moeda_atual) if moeda_atual in ["USD", "BRL", "EUR"] else 0)
        orcamento = c4.number_input("Orçamento inicial", min_value=0.0, value=orcamento_atual, step=50.0)
        companhia = st.text_input("Companhia aérea (opcional)", value=viagem[6] if viagem and viagem[6] else "", placeholder="Ex.: LATAM")
        enviado = st.form_submit_button("Salvar viagem")
        if enviado:
            if not destino.strip() or not pais.strip():
                st.error("Preencha pelo menos o destino e o país.")
            elif retorno < partida:
                st.error("A data de volta não pode ser anterior à data de ida.")
            else:
                salvar_viagem(destino.strip(), pais.strip(), partida, retorno, moeda, orcamento, companhia.strip())
                st.success("Viagem salva! Seus dados ficarão registrados neste computador.")
                st.rerun()

elif pagina == "Orçamento":
    st.header("Orçamento")
    st.write("Registre compras, despesas ou depósitos.")
    with st.form("form_gasto", clear_on_submit=True):
        descricao = st.text_input("Descrição", placeholder="Ex.: Passagem, hotel, alimentação")
        c1, c2 = st.columns(2)
        valor = c1.number_input("Valor", min_value=0.01, value=10.0, step=5.0)
        tipo = c2.selectbox("Tipo de movimentação", ["Despesa", "Depósito"])
        data_gasto = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
        enviar = st.form_submit_button("Adicionar movimentação")
        if enviar:
            if descricao.strip():
                with conectar() as con:
                    con.execute("INSERT INTO gastos (descricao, valor, tipo, data) VALUES (?, ?, ?, ?)",
                                (descricao.strip(), valor, tipo, str(data_gasto)))
                st.success("Movimentação registrada!")
                st.rerun()
            else:
                st.error("Digite uma descrição.")
    depositos = sum(float(g[2]) for g in gastos if g[3] == "Depósito")
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Orçamento inicial", dinheiro(orcamento_atual, moeda_atual))
    c2.metric("Depósitos", dinheiro(depositos, moeda_atual))
    c3.metric("Despesas", dinheiro(total_gastos, moeda_atual))
    saldo_real = orcamento_atual + depositos - total_gastos
    st.metric("Saldo considerando depósitos", dinheiro(saldo_real, moeda_atual))
    if orcamento_atual > 0 and saldo_real < orcamento_atual / 2:
        st.warning("Atenção: seu saldo está abaixo da metade do orçamento inicial.")
    if saldo_real < 0:
        st.error("Atenção: suas despesas ultrapassaram o orçamento disponível.")
    st.subheader("Movimentações registradas")
    if gastos:
        for gid, desc, val, typ, dt in gastos:
            col1, col2, col3 = st.columns([4, 2, 1])
            col1.write(f"**{desc}** · {dt} · {typ}")
            col2.write(dinheiro(float(val), moeda_atual))
            if col3.button("Excluir", key=f"gasto_{gid}"):
                with conectar() as con:
                    con.execute("DELETE FROM gastos WHERE id=?", (gid,))
                st.rerun()
    else:
        st.info("Nenhuma movimentação cadastrada ainda.")

elif pagina == "Bagagem":
    st.header("Minha bagagem")
    st.write("Cadastre os itens e o peso estimado de cada um.")
    limite = st.number_input("Limite de peso da bagagem (kg)", min_value=0.0, value=23.0, step=1.0)
    st.caption("Informe o limite permitido pela sua companhia aérea. Ele varia conforme a passagem.")
    with st.form("form_bagagem", clear_on_submit=True):
        item = st.text_input("Nome do item", placeholder="Ex.: Calça jeans")
        c1, c2 = st.columns(2)
        peso = c1.number_input("Peso estimado (kg)", min_value=0.01, value=0.5, step=0.1)
        categoria = c2.selectbox("Categoria", ["Roupas", "Calçados", "Higiene", "Eletrônicos", "Documentos", "Outros"])
        enviar = st.form_submit_button("Adicionar à bagagem")
        if enviar:
            if item.strip():
                with conectar() as con:
                    con.execute("INSERT INTO bagagem (item, peso, categoria) VALUES (?, ?, ?)", (item.strip(), peso, categoria))
                st.success("Item adicionado!")
                st.rerun()
            else:
                st.error("Digite o nome do item.")
    st.divider()
    st.metric("Peso cadastrado", f"{peso_total:.2f} kg", f"Limite: {limite:.2f} kg")
    if peso_total > limite:
        st.error(f"Sua bagagem ultrapassou o limite em {peso_total-limite:.2f} kg.")
    else:
        st.success(f"Você ainda pode adicionar {limite-peso_total:.2f} kg.")
    for iid, nome, kg, cat in itens:
        c1, c2, c3 = st.columns([4, 2, 1])
        c1.write(f"**{nome}** · {cat}")
        c2.write(f"{float(kg):.2f} kg")
        if c3.button("Excluir", key=f"item_{iid}"):
            with conectar() as con:
                con.execute("DELETE FROM bagagem WHERE id=?", (iid,))
            st.rerun()

elif pagina == "Roupas e looks":
    st.header("Roupas e looks")
    st.write("Cadastre peças de roupa. Você pode anexar uma foto para consultar depois.")
    with st.form("form_roupa", clear_on_submit=True):
        nome = st.text_input("Nome da peça", placeholder="Ex.: Camiseta branca")
        c1, c2 = st.columns(2)
        categoria = c1.selectbox("Categoria", ["Camiseta", "Calça", "Short", "Vestido", "Saia", "Casaco", "Calçado", "Acessório", "Outro"])
        cor = c2.text_input("Cor", placeholder="Ex.: Branco")
        foto = st.file_uploader("Foto da peça (opcional)", type=["png", "jpg", "jpeg"])
        enviar = st.form_submit_button("Salvar peça")
        if enviar:
            if not nome.strip():
                st.error("Digite o nome da peça.")
            else:
                caminho = ""
                if foto:
                    nome_seguro = f"{date.today().isoformat()}_{foto.name.replace(' ', '_')}"
                    destino = UPLOAD_DIR / nome_seguro
                    destino.write_bytes(foto.getvalue())
                    caminho = str(destino)
                with conectar() as con:
                    con.execute("INSERT INTO roupas (nome, categoria, cor, foto) VALUES (?, ?, ?, ?)",
                                (nome.strip(), categoria, cor.strip(), caminho))
                st.success("Peça cadastrada!")
                st.rerun()
    roupas = ler_tabela("SELECT id, nome, categoria, cor, foto FROM roupas ORDER BY id DESC")
    st.divider()
    st.subheader("Peças cadastradas")
    if roupas:
        for rid, nome, cat, cor, foto_path in roupas:
            c1, c2 = st.columns([1, 4])
            if foto_path and Path(foto_path).exists():
                c1.image(foto_path, width=130)
            else:
                c1.write("Sem foto")
            c2.write(f"{nome}")
            c2.write(f"{cat} · {cor or 'Cor não informada'}")
            if c2.button("Excluir peça", key=f"roupa_{rid}"):
                with conectar() as con:
                    con.execute("DELETE FROM roupas WHERE id=?", (rid,))
                st.rerun()
    else:
        st.info("Nenhuma peça cadastrada ainda.")

st.divider()
st.caption("SmarTravel · Sua viagem começa aqui!")
