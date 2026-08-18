import os
import subprocess
import sys

def main():
    print("Iniciando o processo de Build do Track Splitter...")
    print("Isso pode demorar alguns minutos dependendo do tamanho das bibliotecas (PyTorch/Demucs).")
    
    # Comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "TrackSplitter",
        "--collect-all", "customtkinter",
        "--collect-all", "demucs",
        "--collect-all", "torch",
        "--collect-all", "torchaudio",
        "app.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "="*50)
        print("Build concluído com sucesso!")
        print("O executável está na pasta 'dist/TrackSplitter'")
        print("Você pode zipar essa pasta e enviar para o seu irmão.")
        print("="*50)
    except subprocess.CalledProcessError as e:
        print(f"Erro durante o build: {e}")

if __name__ == "__main__":
    main()
