import subprocess
import sys
import os

def build():
    print("--- Iniciando processo de Build (EXE) ---")
    
    # 1. Instalar/Garantir dependências
    print("Instalando/Atualizando dependências necessárias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "customtkinter", "faster-whisper", "resemblyzer", "sounddevice"])
    
    # 1.1 Remover o pacote 'typing' (conflito com PyInstaller no Python 3.10+)
    print("Removendo pacotes obsoletos (typing)...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "typing"], capture_output=True)
    
    # 2. Limpar pastas de build anteriores
    print("Limpando ambiente...")
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            import shutil
            shutil.rmtree(folder)
            
    # 3. Executar o PyInstaller usando o arquivo .spec
    print("Executando PyInstaller (isso pode levar alguns minutos)...")
    try:
        subprocess.check_call(["pyinstaller", "--noconfirm", "app.spec"])
        print("\n" + "="*50)
        print("SUCESSO! O executável foi gerado na pasta 'dist/'.")
        print("Arquivo: MeetingTranscriberV2.exe")
        print("="*50)
    except subprocess.CalledProcessError as e:
        print(f"\nERRO: Ocorreu um problema durante o build: {e}")

if __name__ == "__main__":
    build()
