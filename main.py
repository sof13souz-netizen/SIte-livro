from flask import Flask, render_template, redirect, request, flash, url_for, session, send_file
import fdb
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF
app = Flask(__name__)

app.config['SECRET_KEY'] = 'chave_secreta_da_turma_b'

host = "localhost"
database = r"C:\Users\Aluno\Downloads\BANCOSOFIA\BANCO.FDB"

user = "sysdba"
password = "sysdba"

con = fdb.connect(
    host=host,
    database=database,
    user=user,
    password=password
)

def validar_senha(senha):
    min_caractere = False
    min_upper = False
    min_lower = False
    min_num = False
    min_caractere_esp = False

    if len(senha) >= 8:
        min_caractere = True

    for caractere in senha:
        if caractere.isalpha() and caractere == caractere.upper():
            min_upper = True
        if caractere.isalpha() and caractere == caractere.lower():
            min_lower = True
        if caractere.isdigit():
            min_num = True
        if not caractere.isalpha() and not caractere.isdigit():
            min_caractere_esp = True

    if min_caractere == True and min_upper == True and min_lower == True and min_num == True and min_caractere_esp == True:
        validacao = True
        return (validacao)
    else:
        validacao = False
        return (validacao)


@app.route("/")
def index():
    return render_template("login.html")


@app.route("/home")
def home():

    cursor = con.cursor()

    cursor.execute("""
        SELECT id_livros,
               titulo,
               autor,
               ano_publicado
        FROM livros
        ORDER BY id_livros
    """)

    livros = cursor.fetchall()

    cursor.close()

    return render_template("livros.html", livros=livros)


@app.route('/novo')
def novo():

    if 'id_usuario' not in session:
        flash('Pecisa estar logado')
        return redirect(url_for('login'))
    else: return render_template('novo.html')


@app.route('/criar', methods=['POST'])
def criar():

    titulo = request.form['titulo']
    autor = request.form['autor']
    ano_publicado = request.form['ano_publicado']

    cursor = con.cursor()

    try:

        cursor.execute("""
            SELECT 1
            FROM livros
            WHERE titulo = ?
        """, (titulo,))

        if cursor.fetchone():

            flash("Esse livro já existe no banco!")

            return redirect(url_for('novo'))

        cursor.execute("""
            INSERT INTO livros
            (titulo, autor, ano_publicado)
            VALUES (?, ?, ?) RETURNING ID_LIVROS
        """, (titulo, autor, ano_publicado))


        id_livros = cursor.fetchone()[0]
        con.commit()

        arquivo = request.files['imagem'] #pega o caminho e salva
        arquivo.save(f'uploads/capa{id_livros}.jpg')  #pega o caminho e salva

        flash("Livro adicionado com sucesso!")

        return redirect(url_for('home'))

    except Exception as e:

        flash(f"Ocorreu um erro: {e}")

        con.rollback()

        return redirect(url_for('novo'))

    finally:

        cursor.close()


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):

    cursor = con.cursor()

    try:

        cursor.execute("""
            SELECT id_livros,
                   titulo,
                   autor,
                   ano_publicado
            FROM livros
            WHERE id_livros = ?
        """, (id,))

        livro = cursor.fetchone()

        if not livro:

            flash("Livro não encontrado!")

            return redirect(url_for('home'))

        if request.method == 'POST':

            titulo = request.form['titulo']
            autor = request.form['autor']
            ano_publicado = request.form['ano_publicado']

            cursor.execute("""
                UPDATE livros
                SET titulo = ?,
                    autor = ?,
                    ano_publicado = ?
                WHERE id_livros = ?
            """, (titulo, autor, ano_publicado, id))

            con.commit()

            flash("Livro editado com sucesso!")

            return redirect(url_for('home'))

        return render_template('editar.html', livro=livro)

    except Exception as e:

        flash(f"Ocorreu um erro: {e}")

        con.rollback()

        return redirect(url_for('home'))

    finally:

        cursor.close()


@app.route('/confirmar_delete/<int:id>')
def confirmar_delete(id):

    cursor = con.cursor()

    cursor.execute("""
        SELECT id_livros,
               titulo,
               autor,
               ano_publicado
        FROM livros
        WHERE id_livros = ?
    """, (id,))

    livro = cursor.fetchone()

    cursor.close()

    return render_template(
        'confirmar_delete.html',
        livro=livro
    )


@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):

    cursor = con.cursor()

    try:

        cursor.execute("""
            DELETE FROM livros
            WHERE id_livros = ?
        """, (id,))

        con.commit()

        flash("Livro excluído com sucesso!")

        return redirect(url_for('home'))

    except Exception as e:

        flash(f"Ocorreu um erro: {e}")

        con.rollback()

        return redirect(url_for('home'))

    finally:

        cursor.close()


@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar_usuario():

    if request.method == 'POST':

        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        if validar_senha(senha) == False:
            flash("A senha não atende os requisitos, tente novamente!")
            return render_template('cadastrar_usuario.html')

        cursor = con.cursor()



        try:

            cursor.execute("""
                SELECT id_usuario
                FROM usuario
                WHERE email = ?
            """, (email,))

            usuario = cursor.fetchone()

            if usuario:

                flash("Esse e-mail já está cadastrado!")
                return redirect(url_for('cadastrar_usuario'))

            senha = generate_password_hash(senha)

            cursor.execute("""
                INSERT INTO usuario
                (nome, email, senha)
                VALUES (?, ?, ?)
            """, (nome, email, senha))

            con.commit()

            flash("Usuário cadastrado com sucesso!")

            return redirect(url_for('index'))

        except Exception as e:

            flash(f"Ocorreu um erro: {e}")
            con.rollback()
            return redirect(url_for('cadastrar_usuario'))

        finally:
            cursor.close()

    return render_template('cadastrar_usuario.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'GET':
        return render_template('login.html')

    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']

    tentativas_usuarios = session.get('tentativas_usuarios', {})
    bloqueados = session.get('usuarios_bloqueados', [])

    if email in bloqueados:
        flash('Este usuário está bloqueado por 3 tentativas incorretas!', 'error')
        return redirect(url_for('index'))

    cursor = con.cursor()

    try:

        cursor.execute("""
            SELECT id_usuario, senha
            FROM usuario
            WHERE nome = ?
            AND email = ?
        """, (nome, email))

        usuario = cursor.fetchone()

        if usuario and check_password_hash(usuario[1], senha):

            session['id_usuario'] = usuario[0]

            tentativas_usuarios[email] = 0

            session['tentativas_usuarios'] = tentativas_usuarios
            session.modified = True

            return redirect(url_for('home'))

        else:

            tentativas = tentativas_usuarios.get(email, 0) + 1
            tentativas_usuarios[email] = tentativas

            if tentativas >= 3:

                if email not in bloqueados:
                    bloqueados.append(email)

                session['usuarios_bloqueados'] = bloqueados

                flash(
                    "Você errou a senha 3 vezes. Este usuário foi bloqueado!",
                    "error"
                )

            else:

                flash(
                    f"Nome, e-mail ou senha incorretos! Tentativa {tentativas} de 3.",
                    "error"
                )

            session['tentativas_usuarios'] = tentativas_usuarios
            session.modified = True

            return redirect(url_for('index'))

    except Exception as e:

        flash(f"Ocorreu um erro: {e}", "error")
        return redirect(url_for('index'))

    finally:

        cursor.close()


@app.route('/logout')
def logout():
    session.pop('id_usuario', None)
    return redirect(url_for('index'))


@app.route('/livros/relatorio', methods=['GET'])
def relatorio():

    cursor = con.cursor()

    cursor.execute(""" SELECT id_livros, 
    titulo, 
    autor, 
    ano_publicado
    FROM livros
    """)

    livros = cursor.fetchall()
    cursor.close()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(200, 10, "Relatório de Livros", ln=True, align='C')

    pdf.ln(5)  # Espaço entre o título e a linha
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())  # Linha abaixo do título
    pdf.ln(5)  # Espaço após a linha

    pdf.set_font("Arial", size=12)

    for livro in livros:
        pdf.cell(
            200,
            10,
            f"ID: {livro[0]} - {livro[1]} - {livro[2]} - {livro[3]}",
            ln=True
        )

    contador_livros = len(livros)

    pdf.ln(10)  # Espaço antes do contador

    pdf.set_font("Arial", style='B', size=12)

    pdf.cell(
        200,
        10,
        f"Total de livros cadastrados: {contador_livros}",
        ln=True,
        align='C'
    )

    pdf_path = "relatorio_livros.pdf"

    pdf.output(pdf_path)

    return send_file(
        pdf_path,
        as_attachment=True,
        mimetype='application/pdf'
    )

if __name__ == "__main__":
    app.run(debug=True)