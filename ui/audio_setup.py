"""
ui/audio_setup.py — Utilitários para auto-detecção e validação de dispositivos de áudio.

Responsabilidades:
- Detectar automaticamente Stereo Mix e Microfone
- Validar se Stereo Mix está ativo (Windows)
- Fazer testes de áudio
"""

import platform
import sounddevice as sd
import numpy as np
import threading
import time


class AudioDeviceDetector:
    """Detecta e classifica dispositivos de áudio automaticamente."""
    
    @staticmethod
    def get_all_input_devices() -> list[dict]:
        """Retorna todos os dispositivos de entrada com metadados."""
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                devices.append({
                    "index": i,
                    "name": dev["name"],
                    "sr": int(dev["default_samplerate"]),
                    "ch": dev["max_input_channels"],
                })
        return devices
    
    @staticmethod
    def classify_device(device_name: str) -> str:
        """
        Classifica um dispositivo como 'stereo_mix', 'microphone' ou 'unknown'.
        """
        nome = device_name.lower()
        
        # Stereo Mix
        stereo_keywords = ['stereo mix', 'mistura', 'what u hear', 'loopback', 'mixed output']
        if any(kw in nome for kw in stereo_keywords):
            return "stereo_mix"
        
        # Microfone
        mic_keywords = ['mic', 'microfone', 'microphone', 'input', 'gravador']
        if any(kw in nome for kw in mic_keywords):
            return "microphone"
        
        return "unknown"
    
    @staticmethod
    def detect_stereo_mix() -> int | None:
        """
        Tenta detectar qual dispositivo é Stereo Mix.
        Retorna o índice ou None se não encontrado.
        """
        for dev in AudioDeviceDetector.get_all_input_devices():
            if AudioDeviceDetector.classify_device(dev["name"]) == "stereo_mix":
                return dev["index"]
        return None
    
    @staticmethod
    def detect_microphone() -> int | None:
        """
        Tenta detectar qual dispositivo é Microfone.
        Retorna o índice ou None se não encontrado.
        """
        for dev in AudioDeviceDetector.get_all_input_devices():
            if AudioDeviceDetector.classify_device(dev["name"]) == "microphone":
                return dev["index"]
        return None
    
    @staticmethod
    def auto_detect() -> tuple[int | None, int | None]:
        """
        Detecta automaticamente os índices de Stereo Mix e Microfone.
        Retorna (stereo_mix_idx, microphone_idx).
        """
        return (
            AudioDeviceDetector.detect_stereo_mix(),
            AudioDeviceDetector.detect_microphone(),
        )


class AudioValidator:
    """Valida e testa dispositivos de áudio."""
    
    @staticmethod
    def is_stereo_mix_active_windows() -> bool | None:
        """
        Verifica se Stereo Mix está ativa no Windows.
        Retorna True se ativa, False se inativa, None se não detectado.
        """
        if platform.system() != "Windows":
            return None
        
        stereo_mix_idx = AudioDeviceDetector.detect_stereo_mix()
        if stereo_mix_idx is None:
            return False
        
        try:
            dev = sd.query_devices(stereo_mix_idx)
            # Se conseguir acessar, está ativa
            return dev["max_input_channels"] > 0
        except Exception:
            return False
    
    @staticmethod
    def test_device_audio(device_idx: int, duration_sec: float = 2.0) -> float | None:
        """
        Testa se um dispositivo consegue capturar áudio e retorna RMS médio.
        Retorna o RMS médio ou None se falhar.
        """
        try:
            dev = sd.query_devices(device_idx)
            channels = dev["max_input_channels"]
            sr = int(dev["default_samplerate"])
            
            if channels <= 0:
                return None
            
            rms_values = []
            
            def callback(indata, frames, t, status):
                mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
                rms = float(np.sqrt(np.mean(mono ** 2)))
                rms_values.append(rms)
            
            with sd.InputStream(
                device=device_idx,
                channels=channels,
                samplerate=sr,
                callback=callback,
                blocksize=int(sr * 0.05),
            ):
                time.sleep(duration_sec)
            
            if rms_values:
                return float(np.mean(rms_values))
            return None
        
        except Exception:
            return None
    
    @staticmethod
    def test_device_async(
        device_idx: int,
        duration_sec: float,
        on_update: callable,
        on_complete: callable,
    ) -> threading.Thread:
        """
        Testa dispositivo de forma assíncrona.
        
        on_update(rms: float) — chamado a cada frame
        on_complete(rms_medio: float | None) — chamado ao fim
        """
        def worker():
            try:
                dev = sd.query_devices(device_idx)
                channels = dev["max_input_channels"]
                sr = int(dev["default_samplerate"])
                
                if channels <= 0:
                    on_complete(None)
                    return
                
                rms_values = []
                stop_evt = threading.Event()
                
                def callback(indata, frames, t, status):
                    mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
                    rms = float(np.sqrt(np.mean(mono ** 2)))
                    rms_values.append(rms)
                    on_update(rms)
                
                with sd.InputStream(
                    device=device_idx,
                    channels=channels,
                    samplerate=sr,
                    callback=callback,
                    blocksize=int(sr * 0.05),
                ):
                    time.sleep(duration_sec)
                
                rms_medio = float(np.mean(rms_values)) if rms_values else None
                on_complete(rms_medio)
            
            except Exception as e:
                on_complete(None)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread
