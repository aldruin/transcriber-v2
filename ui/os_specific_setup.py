"""
ui/os_specific_setup.py — Detecção de SO e instruções específicas para configuração de áudio.

Responsabilidades:
- Detectar sistema operacional
- Fornecer instruções específicas por SO
- Mensagens de aviso/educacionais
"""

import platform
import sys


class OSDetector:
    """Detecta o sistema operacional em uso."""
    
    @staticmethod
    def get_os() -> str:
        """
        Retorna: 'windows', 'linux', 'macos', ou 'unknown'
        """
        system = platform.system()
        if system == "Windows":
            return "windows"
        elif system == "Linux":
            return "linux"
        elif system == "Darwin":
            return "macos"
        return "unknown"
    
    @staticmethod
    def get_os_display_name() -> str:
        """Retorna nome amigável do SO."""
        os_type = OSDetector.get_os()
        names = {
            "windows": "Windows",
            "linux": "Linux",
            "macos": "macOS",
            "unknown": "Sistema Operacional Desconhecido",
        }
        return names.get(os_type, "Desconhecido")


class AudioSetupInstructions:
    """Fornece instruções específicas por SO para ativar Stereo Mix."""
    
    @staticmethod
    def get_stereo_mix_warning() -> dict:
        """
        Retorna um dicionário com aviso sobre Stereo Mix.
        
        Formato:
        {
            "title": "Título do aviso",
            "message": "Mensagem principal",
            "steps": ["passo 1", "passo 2", ...],
            "note": "Nota adicional",
            "link": "URL opcional"
        }
        """
        os_type = OSDetector.get_os()
        
        if os_type == "windows":
            return AudioSetupInstructions._windows_stereo_mix()
        elif os_type == "linux":
            return AudioSetupInstructions._linux_loopback()
        elif os_type == "macos":
            return AudioSetupInstructions._macos_loopback()
        else:
            return AudioSetupInstructions._generic_loopback()
    
    @staticmethod
    def _windows_stereo_mix() -> dict:
        """
        Mensagem para Windows quando o loopback automático não inicia. A captura
        do áudio do sistema é automática (WASAPI loopback); só falha se não há
        saída de áudio ativa. NÃO orientamos mais ativar Stereo Mix.
        """
        return {
            "title": "🔊 Áudio do sistema indisponível (Windows)",
            "os": "windows",
            "message": "A captura do áudio do sistema é automática (loopback WASAPI), mas não encontrei uma saída de áudio ativa para capturar.",
            "steps": [
                "1. Conecte fones de ouvido ou alto-falantes",
                "2. Clique no 🔊 volume (canto inferior direito) e confirme um dispositivo de saída ativo e definido como padrão",
                "3. Toque algo (música/vídeo) para garantir que há áudio saindo",
                "4. Reabra o app — a detecção é automática",
            ],
            "note": "✅ Não é preciso ativar Stereo Mix nem instalar cabo virtual no Windows.",
            "alternatives": [],
            "link": "",
        }
    
    @staticmethod
    def _linux_loopback() -> dict:
        """Instruções para Linux - Configurar PulseAudio/PipeWire loopback."""
        return {
            "title": "🐧 Configurar Loopback (Linux)",
            "os": "linux",
            "message": "No Linux, você precisa criar um dispositivo 'loopback' para capturar áudio do sistema.",
            "steps": [
                "🔧 Opção 1: Via PulseAudio (mais comum)",
                "   Execute no terminal:",
                "   pactl load-module module-loopback latency_msec=1",
                "",
                "🔧 Opção 2: Via PipeWire (sistemas modernos)",
                "   Use seu gerenciador de áudio (pavucontrol ou gnome-control-center)",
                "   Acesse: Gravação → Crie um sink loopback",
                "",
                "🔧 Opção 3: Interface gráfica",
                "   Instale: sudo apt install pavucontrol",
                "   Execute: pavucontrol",
                "   Vá para 'Gravação' e configure loopback",
            ],
            "note": "📝 Depois de configurar, o dispositivo deve aparecer na lista abaixo.",
            "alternatives": [
                "💡 Se não funcionar, tente criar um novo source via pulseaudio-control",
            ],
            "link": "https://wiki.archlinux.org/title/PulseAudio",
        }
    
    @staticmethod
    def _macos_loopback() -> dict:
        """Instruções para macOS - Usar BlackHole ou SoundFlower."""
        return {
            "title": "🍎 Configurar Loopback (macOS)",
            "os": "macos",
            "message": "No macOS, você precisa de um software virtual para capturar áudio do sistema.",
            "steps": [
                "🎵 Opção 1: BlackHole (recomendado - gratuito)",
                "   1. Instale via Homebrew:",
                "      brew install blackhole-2ch",
                "   2. Abra Áudio MIDI Setup",
                "   3. Crie um 'Aggregate Device'",
                "   4. Adicione 'BlackHole' como entrada",
                "",
                "🎵 Opção 2: Soundflower (alternativa)",
                "   1. Baixe em: https://github.com/mattingalls/Soundflower/releases",
                "   2. Instale e reinicie",
                "   3. Configure em Preferências de Som",
            ],
            "note": "⚠️ Após instalar, talvez precise reiniciar o app para que o novo dispositivo apareça.",
            "alternatives": [
                "💡 Links: BlackHole → https://github.com/ExistentialAudio/BlackHole",
            ],
            "link": "https://github.com/ExistentialAudio/BlackHole",
        }
    
    @staticmethod
    def _generic_loopback() -> dict:
        """Instrução genérica para SO desconhecido."""
        return {
            "title": "⚠️ Sistema Operacional Desconhecido",
            "os": "unknown",
            "message": "Não conseguimos detectar seu sistema operacional. Por favor, consulte a documentação para instruções sobre como habilitar captura de áudio do sistema.",
            "steps": [
                "Consulte: SETUP-GUIDE.md na pasta do projeto",
            ],
            "note": "Se o problema persistir, abra uma issue no GitHub.",
            "link": "https://github.com/aldruin/transcriber-v2/issues",
        }
    
    @staticmethod
    def get_microphone_selection_tip() -> str:
        """Retorna dica sobre seleção de microfone."""
        return """
💡 DICA: Selecionando o Microfone
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Escolha o dispositivo com o maior número de canais:
  • 2 canais (estéreo) = Melhor qualidade ⭐
  • 1 canal (mono) = Aceitável
  
Dica: Procure por termos como:
  • "HD" ou "High Definition" = Melhor qualidade
  • "Array" = Pode ser menos preciso
  • O primeiro na lista geralmente é o padrão (bom)
"""
    
    @staticmethod
    def get_stereo_mix_selection_tip() -> str:
        """Retorna dica sobre seleção de Stereo Mix."""
        return """
💡 DICA: Selecionando o Stereo Mix
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Procure por um dispositivo com um destes nomes:
  • "Stereo Mix" = Exato! ✅
  • "Mistura Estéreo" = Em português
  • "What U Hear" = Alguns drivers
  • "Loopback" (Linux/macOS)
  • "Sink Monitor" (PulseAudio)
  
⚠️ Se não encontrar nenhum, siga as instruções acima.
"""


class DeviceAnalyzer:
    """Analisa e classifica dispositivos de áudio."""
    
    @staticmethod
    def classify_device(device_name: str) -> str:
        """
        Classifica um dispositivo como 'stereo_mix', 'microphone', ou 'other'.
        Não faz auto-select, apenas classifica para ajudar o usuário.
        """
        nome = device_name.lower()
        
        # Stereo Mix / Loopback
        stereo_keywords = [
            'stereo mix',
            'mistura',
            'what u hear',
            'loopback',
            'sink monitor',
            'monitor of',
            'mixed output',
        ]
        if any(kw in nome for kw in stereo_keywords):
            return "stereo_mix"
        
        # Microfone
        mic_keywords = [
            'mic',
            'microfone',
            'microphone',
            'input',
            'gravador',
            'builtin',
            'line in',
        ]
        if any(kw in nome for kw in mic_keywords):
            return "microphone"
        
        return "other"
    
    @staticmethod
    def get_device_quality_score(device: dict) -> int:
        """
        Analisa qualidade de um dispositivo (0-100).
        Usa: canais, sample rate.
        NÃO faz auto-select, apenas pontuação informativa.
        """
        score = 50  # Base
        
        # Canais: mais canais = melhor
        ch = device.get("ch", 1)
        if ch >= 2:
            score += 20
        if ch >= 4:
            score += 10
        
        # Sample rate: 48kHz ou mais é melhor
        sr = device.get("sr", 44100)
        if sr >= 48000:
            score += 20
        if sr >= 96000:
            score += 10
        
        return min(score, 100)
    
    @staticmethod
    def format_device_info(device: dict) -> str:
        """
        Formata informações de um dispositivo para exibição.
        Exemplo: "[0] Microfone Realtek (2ch, 48kHz) - Qualidade: ⭐⭐⭐"
        """
        idx = device.get("index", 0)
        name = device.get("name", "Desconhecido")
        ch = device.get("ch", 1)
        sr = device.get("sr", 44100)
        
        quality = DeviceAnalyzer.get_device_quality_score(device)
        stars = "⭐" * (quality // 25) if quality > 0 else "✗"
        
        return f"[{idx}] {name} ({ch}ch, {sr}Hz) - {stars}"
