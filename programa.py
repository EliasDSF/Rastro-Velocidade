#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import threading
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab

from motor_analise import analisar


COLHEDORAS = [
    "176003", "176004", "176005", "176008", "176009", "176011", "176012",
    "176013", "176014", "176015", "176016", "176017", "176018", "176019",
]


class Programa(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Rastro Analítico de Velocidade")
        self.geometry("1040x800")
        self.minsize(820, 650)
        self.configure(bg="#f3f7f4")
        self.arquivo: Path | None = None
        self.analisando = False
        base_local = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "RastroVelocidade"
        self.pasta_dados = base_local
        self.pasta_imagens = base_local / "imagens"
        self.arquivo_dados = base_local / "registros.json"
        self.pasta_imagens.mkdir(parents=True, exist_ok=True)
        self.banco = self.carregar_banco()

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("TLabel", background="#f3f7f4", font=("Segoe UI", 10))
        style.configure("Titulo.TLabel", font=("Segoe UI Semibold", 20), foreground="#075d35")
        style.configure("Resultado.TLabel", font=("Segoe UI Semibold", 12), foreground="#064e2d")

        topo = ttk.Frame(self, padding=16)
        topo.pack(fill="x")
        ttk.Label(topo, text="Rastro Analítico de Velocidade", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(
            topo,
            text="Cole com Ctrl+V ou selecione o print. A análise começa automaticamente.",
        ).pack(anchor="w", pady=(4, 0))

        botoes = ttk.Frame(self, padding=(16, 0, 16, 10))
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Selecionar imagem", command=self.selecionar).pack(side="left")
        ttk.Button(botoes, text="Colar imagem (Ctrl+V)", command=self.colar_imagem).pack(side="left", padx=8)
        self.botao_analisar = ttk.Button(botoes, text="Analisar novamente", command=self.iniciar_analise, state="disabled")
        self.botao_analisar.pack(side="left")
        self.status = ttk.Label(botoes, text="Aguardando uma imagem...")
        self.status.pack(side="left", padx=12)

        corpo = ttk.Frame(self, padding=(16, 0, 16, 16))
        corpo.pack(fill="both", expand=True)
        corpo.columnconfigure(0, weight=1)
        corpo.rowconfigure(1, weight=1)

        dados = ttk.Frame(corpo)
        dados.grid(row=0, column=0, sticky="ew")
        dados.columnconfigure(0, weight=1)
        dados.columnconfigure(1, weight=1)

        painel = ttk.LabelFrame(dados, text="Dados encontrados automaticamente", padding=14)
        painel.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        painel.columnconfigure(1, weight=1)
        self.campos: dict[str, tk.StringVar] = {}
        itens = [
            ("data", "Data"),
            ("inicio", "Hora inicial"),
            ("fim", "Hora final"),
            ("faixa", "Faixa de velocidade"),
            ("percentual", "Maior porcentagem"),
        ]
        for linha, (chave, titulo) in enumerate(itens):
            ttk.Label(painel, text=f"{titulo}:").grid(row=linha, column=0, sticky="w", pady=3, padx=(0, 8))
            variavel = tk.StringVar(value="—")
            self.campos[chave] = variavel
            ttk.Label(painel, textvariable=variavel, style="Resultado.TLabel").grid(row=linha, column=1, sticky="w")

        complementares = ttk.LabelFrame(dados, text="Dados complementares", padding=14)
        complementares.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        complementares.columnconfigure(1, weight=1)
        self.manuais: dict[str, tk.StringVar] = {}
        manuais = [
            ("frente", "Frente", "1"),
            ("campo", "Campo", "LAS VEGAS"),
            ("colhedora", "Colhedora", "176012"),
            ("lotes", "Lotes", "12, 14 e 15"),
            ("tch", "TCH estimado", "110"),
        ]
        for linha, (chave, titulo, exemplo) in enumerate(manuais):
            ttk.Label(complementares, text=f"{titulo}:").grid(row=linha, column=0, sticky="w", pady=3, padx=(0, 8))
            variavel = tk.StringVar(value=exemplo)
            self.manuais[chave] = variavel
            if chave == "frente":
                entrada = ttk.Combobox(
                    complementares, textvariable=variavel,
                    values=("1", "2", "3", "4"), state="readonly",
                )
                entrada.bind("<<ComboboxSelected>>", self.salvar_frente_atual)
            elif chave == "colhedora":
                entrada = ttk.Combobox(
                    complementares, textvariable=variavel,
                    values=COLHEDORAS, state="readonly",
                )
                entrada.bind("<<ComboboxSelected>>", self.mudar_colhedora)
            else:
                entrada = ttk.Entry(complementares, textvariable=variavel)
            entrada.grid(row=linha, column=1, sticky="ew", pady=3)
            variavel.trace_add("write", lambda *_: self.gerar_texto())

        mensagem = ttk.LabelFrame(corpo, text="Mensagem para WhatsApp", padding=12)
        mensagem.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        mensagem.columnconfigure(0, weight=1)
        mensagem.rowconfigure(0, weight=1)
        self.texto = tk.Text(mensagem, height=18, wrap="word", font=("Segoe UI", 12), padx=12, pady=12)
        self.texto.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Frame(mensagem)
        barra.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(barra, text="Copiar imagem", command=self.copiar_imagem).pack(side="left")
        ttk.Button(barra, text="Copiar texto", command=self.copiar_texto).pack(side="left", padx=8)
        ttk.Button(barra, text="Salvar na fila", command=self.salvar_na_fila).pack(side="left", padx=(8, 0))
        ttk.Button(barra, text="Ver 14 colhedoras", command=self.abrir_painel_fila).pack(side="left", padx=8)

        self.resultado_status = tk.StringVar(value="Aguardando análise")
        ttk.Label(corpo, textvariable=self.resultado_status, wraplength=900).grid(row=2, column=0, sticky="w", pady=(8, 0))

        self.bind_all("<Control-v>", self.atalho_colar)
        self.bind_all("<Control-V>", self.atalho_colar)
        self.mudar_colhedora()
        self.gerar_texto()

    def carregar_banco(self) -> dict:
        padrao = {
            "frentes": {numero: "" for numero in COLHEDORAS},
            "registros": {},
        }
        if not self.arquivo_dados.exists():
            return padrao
        try:
            dados = json.loads(self.arquivo_dados.read_text(encoding="utf-8"))
            dados.setdefault("frentes", {})
            dados.setdefault("registros", {})
            for numero in COLHEDORAS:
                dados["frentes"].setdefault(numero, "")
            return dados
        except Exception:
            return padrao

    def gravar_banco(self) -> None:
        temporario = self.arquivo_dados.with_suffix(".tmp")
        temporario.write_text(
            json.dumps(self.banco, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporario.replace(self.arquivo_dados)

    def mudar_colhedora(self, _evento=None) -> None:
        if not hasattr(self, "manuais") or "colhedora" not in self.manuais:
            return
        numero = self.manuais["colhedora"].get().strip()
        frente = self.banco.get("frentes", {}).get(numero, "")
        # Cada colhedora mantém sua própria frente. Se ainda não houver uma
        # associação, deixa em branco para evitar copiar a frente da anterior.
        self.manuais["frente"].set(frente or "")
        registro = self.banco.get("registros", {}).get(numero)
        if registro:
            for chave in ("campo", "lotes", "tch"):
                if registro.get(chave):
                    self.manuais[chave].set(registro[chave])
        self.gerar_texto()

    def salvar_frente_atual(self, _evento=None) -> None:
        numero = self.manuais["colhedora"].get().strip()
        frente = self.manuais["frente"].get().strip()
        if numero in COLHEDORAS and frente in {"1", "2", "3", "4"}:
            self.banco["frentes"][numero] = frente
            self.gravar_banco()
        self.gerar_texto()

    def salvar_na_fila(self) -> None:
        if not self.arquivo:
            messagebox.showinfo("Imagem necessária", "Selecione e analise uma imagem primeiro.")
            return
        if any(self.campos[chave].get() in {"—", "Revisar"} for chave in ("data", "inicio", "fim", "faixa", "percentual")):
            messagebox.showwarning("Dados incompletos", "Corrija os campos marcados como Revisar antes de salvar.")
            return
        numero = self.manuais["colhedora"].get().strip()
        frente = self.manuais["frente"].get().strip()
        if numero not in COLHEDORAS or frente not in {"1", "2", "3", "4"}:
            messagebox.showwarning("Colhedora e frente", "Selecione uma colhedora e uma frente de 1 a 4.")
            return

        destino = self.pasta_imagens / f"{numero}.png"
        Image.open(self.arquivo).convert("RGB").save(destino, format="PNG", optimize=True)
        self.banco["frentes"][numero] = frente
        self.banco["registros"][numero] = {
            "colhedora": numero,
            "frente": frente,
            "campo": self.manuais["campo"].get().strip(),
            "lotes": self.manuais["lotes"].get().strip(),
            "tch": self.manuais["tch"].get().strip(),
            "data": self.campos["data"].get(),
            "inicio": self.campos["inicio"].get(),
            "fim": self.campos["fim"].get(),
            "faixa": self.campos["faixa"].get(),
            "percentual": self.campos["percentual"].get(),
            "mensagem": self.texto.get("1.0", "end").strip(),
            "imagem": str(destino),
            "status": "Pronto",
        }
        self.gravar_banco()
        self.resultado_status.set(f"Colhedora {numero} salva na fila como Pronto.")
        messagebox.showinfo("Salvo", f"Imagem e texto da colhedora {numero} foram armazenados.")

    def abrir_painel_fila(self) -> None:
        janela = tk.Toplevel(self)
        janela.title("Fila das 14 colhedoras")
        janela.geometry("900x520")
        ttk.Label(
            janela,
            text="Dê dois cliques em uma colhedora para carregar seu registro.",
            padding=10,
        ).pack(anchor="w")
        colunas = ("colhedora", "frente", "campo", "data", "faixa", "percentual", "status")
        tabela = ttk.Treeview(janela, columns=colunas, show="headings")
        titulos = {
            "colhedora": "Colhedora", "frente": "Frente", "campo": "Campo",
            "data": "Data", "faixa": "Faixa", "percentual": "%", "status": "Status",
        }
        for coluna in colunas:
            tabela.heading(coluna, text=titulos[coluna])
            tabela.column(coluna, width=105 if coluna != "campo" else 150, anchor="center")
        for numero in COLHEDORAS:
            registro = self.banco["registros"].get(numero, {})
            tabela.insert("", "end", iid=numero, values=(
                numero,
                self.banco["frentes"].get(numero, "—") or "—",
                registro.get("campo", "—"), registro.get("data", "—"),
                registro.get("faixa", "—"), registro.get("percentual", "—"),
                registro.get("status", "Pendente"),
            ))
        tabela.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def carregar_selecionado(_evento=None):
            selecao = tabela.selection()
            if not selecao:
                return
            self.carregar_registro(selecao[0])
            janela.destroy()

        tabela.bind("<Double-1>", carregar_selecionado)
        ttk.Button(janela, text="Carregar selecionada", command=carregar_selecionado).pack(pady=(0, 10))

    def carregar_registro(self, numero: str) -> None:
        registro = self.banco["registros"].get(numero)
        self.manuais["colhedora"].set(numero)
        self.manuais["frente"].set(self.banco["frentes"].get(numero, ""))
        if not registro:
            self.resultado_status.set(f"Colhedora {numero} ainda está Pendente.")
            return
        for chave in ("campo", "lotes", "tch"):
            self.manuais[chave].set(registro.get(chave, ""))
        for chave in ("data", "inicio", "fim", "faixa", "percentual"):
            self.campos[chave].set(registro.get(chave, "Revisar"))
        self.arquivo = Path(registro["imagem"])
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", registro.get("mensagem", ""))
        self.botao_analisar.configure(state="normal")
        self.resultado_status.set(f"Registro da colhedora {numero} carregado: {registro.get('status', 'Pronto')}.")

    def atalho_colar(self, _evento=None):
        # Em campos de texto, mantém o Ctrl+V normal para editar dados.
        if isinstance(self.focus_get(), (tk.Entry, tk.Text, ttk.Entry)):
            return None
        self.colar_imagem()
        return "break"

    def selecionar(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Escolha o print completo",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp *.bmp"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.receber_imagem(Path(caminho))

    def colar_imagem(self) -> None:
        try:
            conteudo = ImageGrab.grabclipboard()
            if isinstance(conteudo, Image.Image):
                destino = Path(tempfile.gettempdir()) / "rastro_velocidade_colado.png"
                conteudo.convert("RGB").save(destino)
                self.receber_imagem(destino)
                return
            if isinstance(conteudo, list) and conteudo:
                caminho = Path(conteudo[0])
                if caminho.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                    self.receber_imagem(caminho)
                    return
            messagebox.showinfo("Colar imagem", "Não encontrei uma imagem copiada. Copie o print e pressione Ctrl+V novamente.")
        except Exception as erro:
            messagebox.showerror("Colar imagem", f"Não foi possível receber a imagem: {erro}")

    def receber_imagem(self, caminho: Path) -> None:
        self.arquivo = caminho
        self.status.configure(text=caminho.name)
        self.botao_analisar.configure(state="normal")
        self.resultado_status.set("Imagem recebida. Iniciando análise automática...")
        self.after(100, self.iniciar_analise)

    def iniciar_analise(self) -> None:
        if not self.arquivo or self.analisando:
            return
        self.analisando = True
        self.botao_analisar.configure(state="disabled")
        self.status.configure(text="Analisando, aguarde...")
        self.resultado_status.set("Lendo Intervalo de Datas e legenda Velocidade (km/h)...")
        threading.Thread(target=self.executar_analise, daemon=True).start()

    def executar_analise(self) -> None:
        try:
            resultado = analisar(self.arquivo)
            self.after(0, lambda: self.mostrar_resultado(resultado))
        except Exception as erro:
            mensagem_erro = str(erro)
            self.after(0, lambda mensagem=mensagem_erro: self.mostrar_erro(mensagem))

    def mostrar_resultado(self, resultado: dict) -> None:
        intervalo = resultado.get("intervalo") or {}
        velocidade = resultado.get("velocidade") or {}
        self.campos["data"].set(intervalo.get("data_inicio", "Revisar"))
        self.campos["inicio"].set(intervalo.get("hora_inicio", "Revisar"))
        self.campos["fim"].set(intervalo.get("hora_fim", "Revisar"))
        self.campos["faixa"].set(velocidade.get("faixa", "Revisar"))
        percentual = velocidade.get("percentual")
        self.campos["percentual"].set(
            f"{percentual:.2f}%".replace(".", ",") if isinstance(percentual, (int, float)) else "Revisar"
        )
        self.resultado_status.set(
            "Análise concluída com sucesso. Confira e copie a mensagem."
            if resultado.get("status") == "ok"
            else "Algum campo não ficou confiável. Confira os itens marcados como Revisar."
        )
        self.status.configure(text="Concluído")
        self.botao_analisar.configure(state="normal")
        self.analisando = False
        self.gerar_texto()

    def gerar_texto(self) -> None:
        if not hasattr(self, "texto"):
            return
        data = self.campos.get("data", tk.StringVar(value="—")).get()
        data_curta = "/".join(data.split("/")[:2]) if "/" in data else data
        inicio = self.campos.get("inicio", tk.StringVar(value="—")).get().replace(":", "h")
        fim = self.campos.get("fim", tk.StringVar(value="—")).get().replace(":", "h")
        faixa = self.campos.get("faixa", tk.StringVar(value="—")).get()
        percentual = self.campos.get("percentual", tk.StringVar(value="—")).get()
        try:
            valor_percentual = float(percentual.replace("%", "").replace(",", "."))
            emoji = "✅" if valor_percentual >= 90 else "⬆️"
        except ValueError:
            emoji = ""
        frente = self.manuais["frente"].get().strip()
        campo = self.manuais["campo"].get().strip()
        colhedora = self.manuais["colhedora"].get().strip()
        lotes = self.manuais["lotes"].get().strip()
        tch = self.manuais["tch"].get().strip()
        mensagem = (
            f"*FRENTE {frente} ---> Campo: {campo}*\n"
            f"Segue o rastro analítico de velocidade da *Colhedora {colhedora}*, "
            f"referente ao dia *{data_curta}, das {inicio} às {fim}*. "
            f"Está em atividade nos lotes *{lotes}*. *{percentual}* representa a velocidade "
            f"que mais permaneceu na escala entre *{faixa}*. {emoji}\n"
            f"*TCH ESTIMADO: {tch}.*"
        )
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", mensagem)

    def copiar_texto(self) -> None:
        mensagem = self.texto.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(mensagem)
        self.update()
        self.resultado_status.set("Texto copiado. Agora cole no campo de descrição da imagem.")

    def copiar_imagem(self) -> None:
        """Copia a imagem preparada como bitmap normal no Windows."""
        if not self.arquivo:
            messagebox.showinfo("Imagem necessária", "Selecione e analise uma imagem primeiro.")
            return
        try:
            if os.name != "nt":
                raise RuntimeError("A cópia direta da imagem está disponível na versão para Windows.")
            import ctypes

            imagem = self.preparar_imagem_copiada()
            buffer = BytesIO()
            Image.open(imagem).convert("RGB").save(buffer, format="BMP")
            dados = buffer.getvalue()[14:]  # CF_DIB não usa o cabeçalho de arquivo BMP.

            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            kernel32.GlobalAlloc.restype = ctypes.c_void_p
            kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
            user32.SetClipboardData.restype = ctypes.c_void_p
            user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
            memoria = kernel32.GlobalAlloc(0x0042, len(dados))
            if not memoria:
                raise RuntimeError("Não foi possível reservar memória para a imagem.")
            ponteiro = kernel32.GlobalLock(memoria)
            ctypes.memmove(ponteiro, dados, len(dados))
            kernel32.GlobalUnlock(memoria)

            if not user32.OpenClipboard(None):
                kernel32.GlobalFree(memoria)
                raise RuntimeError("A área de transferência está ocupada. Tente novamente.")
            try:
                user32.EmptyClipboard()
                if not user32.SetClipboardData(8, memoria):  # 8 = CF_DIB
                    kernel32.GlobalFree(memoria)
                    raise RuntimeError("O Windows não aceitou a imagem copiada.")
                memoria = None  # A área de transferência assume a propriedade.
            finally:
                user32.CloseClipboard()
            self.resultado_status.set("Imagem copiada como foto normal. Cole na conversa com Ctrl+V.")
        except Exception as erro:
            messagebox.showerror("Copiar imagem", f"Não foi possível copiar a imagem:\n\n{erro}")

    def preparar_imagem_copiada(self) -> Path:
        imagem = Image.open(self.arquivo).convert("RGB")
        largura, altura = imagem.size
        # Remove apenas o painel esquerdo; mantém mapa, rastro, barra superior e legenda.
        recorte = imagem.crop((round(largura * 0.20), 0, largura, altura)) if largura >= 900 else imagem
        destino = Path(tempfile.gettempdir()) / "rastro_velocidade_copiado.png"
        recorte.save(destino, format="PNG", optimize=True)
        return destino.resolve()

    def mostrar_erro(self, mensagem: str) -> None:
        self.status.configure(text="Erro na análise")
        self.resultado_status.set(mensagem)
        self.botao_analisar.configure(state="normal")
        self.analisando = False
        messagebox.showerror("Não foi possível analisar", mensagem)


if __name__ == "__main__":
    Programa().mainloop()
