import os
import subprocess
import yt_dlp
import re

def download_youtube_audio(url, output_folder, progress_callback=None):
    """
    Downloads audio from a YouTube URL and returns the downloaded file path.
    """
    def my_hook(d):
        if d['status'] == 'downloading' and progress_callback:
            # Parse percentage
            p = d.get('_percent_str', '0.0%')
            p = re.sub(r'\x1b\[[0-9;]*m', '', p) # remove ANSI codes
            try:
                percent = float(p.strip('%'))
                progress_callback(percent / 100.0, f"Baixando YouTube: {p}")
            except:
                pass
        elif d['status'] == 'finished' and progress_callback:
            progress_callback(1.0, "Download concluído! Processando áudio...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [my_hook],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True, # Garante que apenas o vídeo principal seja baixado, ignorando playlists
        'extractor_args': {'youtube': ['player_client=default,tv,ios']}, # Contorna o bloqueio 403 do YouTube
        'geo_bypass': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        # O yt-dlp sanitiza caracteres inválidos no Windows (como | / ?). 
        # Precisamos pegar o nome real gerado e trocar a extensão para mp3 (pós-processador)
        original_filename = ydl.prepare_filename(info_dict)
        filepath = os.path.splitext(original_filename)[0] + '.mp3'
        return filepath


def separate_audio(input_file, output_folder, stems=2, progress_callback=None):
    """
    Separates audio into stems using demucs via its python module directly.
    stems can be 2, 4 or 6.
    """
    from demucs.separate import main as demucs_main
    
    if progress_callback:
        progress_callback(0.0, "Carregando modelo de IA (Isso pode demorar um pouco)...")
        
    model_name = "htdemucs"
    if stems == 6:
        model_name = "htdemucs_6s"

    args = ["-n", model_name, "-o", output_folder]
    
    if stems == 2:
        args.extend(["--two-stems", "vocals"])
        
    args.append(input_file)
    
    if progress_callback:
        progress_callback(0.0, "Processando áudio com Demucs (IA)... 0%")

    import sys
    import re
    
    class TqdmInterceptor:
        def __init__(self, callback):
            self.original_stderr = sys.stderr
            self.callback = callback
            self.buffer = ""

        def write(self, text):
            self.original_stderr.write(text)
            self.buffer += text
            if '\r' in self.buffer or '\n' in self.buffer:
                parts = self.buffer.replace('\r', '\n').split('\n')
                for part in parts:
                    if '%' in part:
                        try:
                            match = re.search(r'(\d+)%', part)
                            if match:
                                percent = int(match.group(1))
                                self.callback(percent / 100.0, f"Processando IA (Demucs): {percent}%")
                        except:
                            pass
                self.buffer = parts[-1]

        def flush(self):
            self.original_stderr.flush()

    # Intercepta o sys.stderr temporariamente para ler o progresso
    interceptor = None
    if progress_callback:
        interceptor = TqdmInterceptor(progress_callback)
        sys.stderr = interceptor

    try:
        # Call demucs main
        demucs_main(args)
    finally:
        # Restaura o stderr original
        if interceptor:
            sys.stderr = interceptor.original_stderr
    
    # Após o demucs terminar, ele cria: output_folder / model_name / base_name / faixas.wav
    # Queremos mover para: output_folder / base_name / faixas.wav
    import shutil
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    demucs_out_dir = os.path.join(output_folder, model_name, base_name)
    final_dir = os.path.join(output_folder, base_name)
    
    # Se a pasta final já existir (de um processamento anterior), removemos para substituir
    if os.path.exists(final_dir):
        shutil.rmtree(final_dir)
        
    # Movemos a pasta de dentro do modelo para a raiz do destino
    if os.path.exists(demucs_out_dir):
        shutil.move(demucs_out_dir, final_dir)
        
        # Tentamos apagar a pasta do modelo (htdemucs) se estiver vazia
        try:
            os.rmdir(os.path.join(output_folder, model_name))
        except OSError:
            pass # A pasta não está vazia, ignoramos
    else:
        # Fallback caso o demucs mude o comportamento
        final_dir = demucs_out_dir

    if progress_callback:
        progress_callback(1.0, "Separação concluída!")
    
    return final_dir

