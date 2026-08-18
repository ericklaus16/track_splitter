import multiprocessing
import os
import sys
import threading
import json
import requests
import customtkinter as ctk
from tkinter import filedialog, messagebox
from core import download_youtube_audio, separate_audio

# Configuração de Versão e Auto-Update
CURRENT_VERSION = "v1.0.2"
GITHUB_REPO = "ericklaus16/track_splitter" 

# Configuração da aparência inicial
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TrackSplitterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Track Splitter Pro - {CURRENT_VERSION}")
        self.geometry("650x700")
        self.minsize(600, 600)
        self.resizable(True, True)

        # Variáveis
        self.input_type = ctk.StringVar(value="file")
        self.file_path = ctk.StringVar(value="")
        self.youtube_url = ctk.StringVar(value="")
        self.output_folder = ctk.StringVar(value="")
        self.stems_option = ctk.IntVar(value=2)
        
        self.create_widgets()
        
        # Iniciar verificação de update em segundo plano
        update_thread = threading.Thread(target=self.check_for_updates)
        update_thread.daemon = True
        update_thread.start()

    def create_widgets(self):
        # Título
        self.title_label = ctk.CTkLabel(self, text="Separador de Faixas (IA)", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        # Seleção de tipo (Arquivo ou YouTube)
        self.type_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.type_frame.pack(pady=10)
        
        self.radio_file = ctk.CTkRadioButton(self.type_frame, text="Arquivo MP3/WAV Local", variable=self.input_type, value="file", command=self.update_ui)
        self.radio_file.grid(row=0, column=0, padx=10)
        
        self.radio_yt = ctk.CTkRadioButton(self.type_frame, text="Link do YouTube", variable=self.input_type, value="youtube", command=self.update_ui)
        self.radio_yt.grid(row=0, column=1, padx=10)

        # Container para os inputs (Arquivo ou URL)
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(pady=10, padx=20, fill="x")

        # Input - File
        self.file_btn = ctk.CTkButton(self.input_frame, text="Selecionar Arquivo de Áudio", command=self.select_file)
        self.file_btn.pack(pady=10)
        
        self.file_lbl = ctk.CTkLabel(self.input_frame, textvariable=self.file_path, text_color="gray")
        self.file_lbl.pack(pady=(0, 10))

        # Input - YouTube (Inicialmente escondido)
        self.yt_entry = ctk.CTkEntry(self.input_frame, textvariable=self.youtube_url, placeholder_text="Cole o link do YouTube aqui...", width=400)
        
        # Opções de Separação
        self.options_frame = ctk.CTkFrame(self)
        self.options_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.options_frame, text="Tipo de Separação:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        self.radio_2stems = ctk.CTkRadioButton(self.options_frame, text="2 Faixas (Vocais + Instrumental)", variable=self.stems_option, value=2)
        self.radio_2stems.pack(pady=5)
        
        self.radio_4stems = ctk.CTkRadioButton(self.options_frame, text="4 Faixas (Vocais, Bateria, Baixo, Outros)", variable=self.stems_option, value=4)
        self.radio_4stems.pack(pady=5)

        self.radio_6stems = ctk.CTkRadioButton(self.options_frame, text="6 Faixas (Vocais, Bateria, Baixo, Guitarra, Piano, Outros)", variable=self.stems_option, value=6)
        self.radio_6stems.pack(pady=(5, 10))

        # Seleção de Destino
        self.dest_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dest_frame.pack(pady=10, padx=20, fill="x")
        
        self.dest_btn = ctk.CTkButton(self.dest_frame, text="Escolher Pasta de Destino", command=self.select_folder)
        self.dest_btn.pack(pady=5)
        
        self.dest_lbl = ctk.CTkLabel(self.dest_frame, textvariable=self.output_folder, text_color="gray")
        self.dest_lbl.pack()

        # Barra de progresso e Status
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(20, 5))
        
        self.status_label = ctk.CTkLabel(self, text="Aguardando...")
        self.status_label.pack(pady=5)

        # Botão Processar
        self.process_btn = ctk.CTkButton(self, text="Iniciar Separação", font=ctk.CTkFont(weight="bold", size=14), height=40, command=self.start_processing)
        self.process_btn.pack(pady=10)

        # Iniciar UI correta
        self.update_ui()

    def update_ui(self):
        if self.input_type.get() == "file":
            self.yt_entry.pack_forget()
            self.file_btn.pack(pady=10)
            self.file_lbl.pack(pady=(0, 10))
        else:
            self.file_btn.pack_forget()
            self.file_lbl.pack_forget()
            self.yt_entry.pack(pady=20, padx=20)

    def select_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac *.m4a")])
        if filepath:
            self.file_path.set(filepath)

    def select_folder(self):
        folderpath = filedialog.askdirectory()
        if folderpath:
            self.output_folder.set(folderpath)

    def update_progress(self, percent, text):
        # A Tkinter method that is thread-safe for simple variable updates
        self.progress_bar.set(percent)
        self.status_label.configure(text=text)
        self.update_idletasks()

    def process_thread(self):
        try:
            out_folder = self.output_folder.get()
            if not out_folder:
                raise Exception("Por favor, selecione uma pasta de destino.")

            input_file = ""
            if self.input_type.get() == "file":
                input_file = self.file_path.get()
                if not input_file:
                    raise Exception("Por favor, selecione um arquivo de áudio.")
            else:
                url = self.youtube_url.get()
                if not url:
                    raise Exception("Por favor, insira o link do YouTube.")
                self.update_progress(0.0, "Baixando do YouTube...")
                input_file = download_youtube_audio(url, out_folder, self.update_progress)

            stems = self.stems_option.get()
            
            self.update_progress(0.0, "Iniciando IA de separação de áudio...")
            final_folder = separate_audio(input_file, out_folder, stems, self.update_progress)
            
            self.update_progress(1.0, "Concluído com sucesso!")
            messagebox.showinfo("Sucesso", f"As faixas foram separadas e salvas em:\n{final_folder}")
            
        except Exception as e:
            self.update_progress(0.0, "Erro ocorrido.")
            messagebox.showerror("Erro", str(e))
        finally:
            self.process_btn.configure(state="normal")

    def start_processing(self):
        self.process_btn.configure(state="disabled")
        thread = threading.Thread(target=self.process_thread)
        thread.daemon = True
        thread.start()

    def check_for_updates(self):
        try:
            if GITHUB_REPO == "SEU_USUARIO/SEU_REPOSITORIO":
                return # Pula verificação se o repo não foi configurado

            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "")
                
                # Comparação super simples: se a tag online for diferente da atual, atualiza
                if latest_version and latest_version != CURRENT_VERSION:
                    assets = data.get("assets", [])
                    if assets:
                        # Pega o primeiro asset (geralmente o .exe)
                        download_url = assets[0].get("browser_download_url")
                        if download_url:
                            # Chama a interface na thread principal
                            self.after(2000, lambda: self.prompt_update(latest_version, download_url))
        except Exception as e:
            print("Erro ao checar atualizações:", e)

    def prompt_update(self, new_version, download_url):
        resposta = messagebox.askyesno("Atualização Disponível", f"A nova versão {new_version} está disponível!\n\nDeseja atualizar agora?")
        if resposta:
            self.update_progress(0.0, "Baixando atualização... Por favor, aguarde.")
            self.process_btn.configure(state="disabled")
            # Iniciar download em background
            threading.Thread(target=self.perform_update, args=(download_url,), daemon=True).start()

    def perform_update(self, download_url):
        try:
            import zipfile
            
            is_zip = download_url.lower().endswith('.zip')
            download_name = "update.zip" if is_zip else "update.exe"
            
            # Baixa o arquivo (pode ser .exe ou .zip)
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(download_name, "wb") as file:
                downloaded = 0
                for data in response.iter_content(chunk_size=4096):
                    file.write(data)
                    downloaded += len(data)
                    if total_size > 0:
                        self.update_progress(downloaded / total_size, "Baixando atualização...")
            
            self.update_progress(1.0, "Atualização baixada! Reiniciando...")
            
            # Se for um ZIP, descompacta ele para pegar o update.exe
            if is_zip:
                with zipfile.ZipFile(download_name, 'r') as zip_ref:
                    # Procura pelo arquivo .exe dentro do zip
                    file_list = zip_ref.namelist()
                    exe_file = next((f for f in file_list if f.endswith('.exe')), None)
                    if exe_file:
                        # Extrai e renomeia para update.exe
                        extracted_path = zip_ref.extract(exe_file)
                        if os.path.exists("update.exe"):
                            os.remove("update.exe")
                        os.rename(extracted_path, "update.exe")
                # Apaga o zip original
                os.remove(download_name)
            
            # Criar script BAT para substituir o .exe atual e reiniciar
            current_exe = sys.executable
            exe_name = os.path.basename(current_exe)
            
            # Script que espera 2 segundos, move o update.exe para o nome original, inicia e se deleta
            bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
move /y "update.exe" "{exe_name}"
start "" "{exe_name}"
del "%~f0"
"""
            with open("update.bat", "w") as bat_file:
                bat_file.write(bat_content)
                
            # Executa o BAT de forma assíncrona
            os.startfile("update.bat")
            
            # Fecha o aplicativo atual imediatamente
            os._exit(0)
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro de Atualização", f"Falha ao atualizar: {e}"))
            self.after(0, lambda: self.update_progress(0.0, "Erro na atualização."))
            self.after(0, lambda: self.process_btn.configure(state="normal"))

if __name__ == "__main__":
    # Importante para o PyInstaller não criar processos zumbis com o PyTorch no Windows
    multiprocessing.freeze_support()
    app = TrackSplitterApp()
    app.mainloop()
