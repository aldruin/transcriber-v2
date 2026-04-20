"""
ui/app.py — Janela principal do Meeting Transcriber v2 usando customtkinter.

Responsabilidades:
- Orquestrar todos os módulos (captura, transcrição, diarização)
- Gerenciar estado da aplicação (parado / transcrevendo)
- Atualizar a UI de forma thread-safe (via root.after)
- Salvar transcrição em arquivo
- Permitir renomear falantes em tempo real (Diarização dinâmica)
"""

import threading
import tkinter as tk
from datetime import datetime
import customtkinter as ctk

import numpy as np

from audio.capture             import VoiceCapture
from transcription.transcriber import Transcriber
from diarization                import DiarizationEngine
from ui.widgets                 import COLORS, LevelMeter, ActionButton, StatusLabel, WaveformCanvas
from ui.profile_window          import ProfileWindow
from ui.settings_window         import SettingsWindow, load_settings
from config import (
    DEVICE_SISTEMA,
    DEVICE_MICROFONE,
    VAD_THRESHOLD_SISTEMA,
    VAD_THRESHOLD_MICROFONE,
    OUTPUT_DIR,
)


def _load_runtime_settings() -> dict:
    """
    Retorna as configurações de dispositivo/threshold em uso.
    Prioridade: settings.json salvo pelo usuário > config.py.
    """
    saved = load_settings()
    return {
        "device_sistema":   saved.get("device_sistema",   DEVICE_SISTEMA),
        "device_microfone": saved.get("device_microfone", DEVICE_MICROFONE),
        "thresh_sistema":   saved.get("thresh_sistema",   VAD_THRESHOLD_SISTEMA),
        "thresh_microfone": saved.get("thresh_microfone", VAD_THRESHOLD_MICROFONE),
    }


class TranscriberApp(ctk.CTk):
    """
    Controlador principal da aplicação usando CustomTkinter.
    """

    def __init__(self):
        super().__init__()
        
        self.title("Meeting Transcriber v2")
        self.geometry("1000x750")
        self.configure(fg_color=COLORS["bg"])

        # Estado
        self._running  = False
        self._paused   = False
        self._mic_on   = True
        self._stop_evt = threading.Event()
        self._file     = None
        
        # Mapeamento de nomes de falantes da sessão (para renomeação dinâmica)
        # "Falante_1" -> "João"
        self._speaker_map = {}

        # Configurações em runtime (dispositivos + thresholds)
        self._cfg = _load_runtime_settings()

        # Módulos
        self._diarization = DiarizationEngine()
        self._transcriber = Transcriber(
            on_result=self._on_transcription,
            on_ready=self._on_model_ready,
            on_error=self._on_transcription_error,
            diarization=self._diarization, # <-- Passado aqui
        )

        self._build_ui()
        self._transcriber.load_async()
        self._tick_meters()

    def run(self):
        self.mainloop()

    # ── Construção da UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        BG, PANEL = COLORS["bg"], COLORS["panel"]
        FG, SUB   = COLORS["fg"], COLORS["subtext"]

        # ── Sidebar (Controles) ───────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=PANEL, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(
            self.sidebar, text="🎙 Meeting\nTranscriber",
            text_color=FG, font=("Segoe UI", 20, "bold"),
            justify="left"
        ).pack(padx=20, pady=(30, 20), anchor="w")

        self._status_label = StatusLabel(self.sidebar)
        self._status_label.pack(padx=20, pady=(0, 30), anchor="w")

        self._btn_start = ActionButton(
            self.sidebar, text="▶  Iniciar",
            color=COLORS["green"],
            command=self.start,
            state="disabled",
        )
        self._btn_start.pack(padx=20, pady=5, fill="x")

        self._btn_stop = ActionButton(
            self.sidebar, text="⏹  Parar",
            color=COLORS["red"],
            command=self.stop,
            state="disabled",
        )
        self._btn_stop.pack(padx=20, pady=5, fill="x")

        self._btn_pause = ActionButton(
            self.sidebar, text="⏸  Pausar",
            color=COLORS["orange"],
            command=self.toggle_pause,
            state="disabled",
        )
        self._btn_pause.pack(padx=20, pady=5, fill="x")

        self._btn_mic = ActionButton(
            self.sidebar, text="🎤  Mic ON",
            color=COLORS["green"],
            command=self.toggle_mic,
            state="disabled",
        )
        self._btn_mic.pack(padx=20, pady=5, fill="x")

        ctk.CTkFrame(self.sidebar, height=2, fg_color=COLORS["surface"]).pack(fill="x", padx=20, pady=15)

        ActionButton(
            self.sidebar, text="⚙️  Configurações",
            color=COLORS["surface"], fg=FG,
            command=self._open_settings,
        ).pack(padx=20, pady=5, fill="x")

        ActionButton(
            self.sidebar, text="👤  Perfis de Voz",
            color=COLORS["surface"], fg=FG,
            command=self._open_profiles,
        ).pack(padx=20, pady=5, fill="x")

        self.sidebar_spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_spacer.pack(fill="both", expand=True)

        ActionButton(
            self.sidebar, text="✕  Sair",
            color=COLORS["surface"], fg=COLORS["red"],
            command=self._quit,
        ).pack(padx=20, pady=20, fill="x")

        # ── Main Content ──────────────────────────────────────────────────────
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # Top Bar: Waveform + Meters
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color=PANEL, corner_radius=12)
        self.top_bar.pack(fill="x", pady=(0, 15))

        self.meters_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.meters_frame.pack(side="left", padx=20, pady=15)

        self._meter_sistema = LevelMeter(
            self.meters_frame,
            label="🔊 Sistema",
            label_color=COLORS["blue"],
            threshold=self._cfg["thresh_sistema"],
        )
        self._meter_sistema.pack(anchor="w")

        self._meter_microfone = LevelMeter(
            self.meters_frame,
            label="🎤 Microfone",
            label_color=COLORS["green"],
            threshold=self._cfg["thresh_microfone"],
        )
        self._meter_microfone.pack(anchor="w", pady=(4, 0))

        # Waveform Visualizer
        self._waveform = WaveformCanvas(self.top_bar, width=350, height=60)
        self._waveform.pack(side="right", padx=20, pady=15)

        # Text Area
        self.txt_container = ctk.CTkFrame(self.main_container, fg_color=PANEL, corner_radius=12)
        self.txt_container.pack(fill="both", expand=True)

        self._txt = tk.Text(
            self.txt_container,
            wrap="word",
            bg=PANEL, fg=FG,
            font=("Segoe UI", 11),
            relief="flat",
            insertbackground=FG,
            selectbackground=COLORS["surface"],
            padx=20, pady=20,
            borderwidth=0,
            highlightthickness=0
        )
        self._txt.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = ctk.CTkScrollbar(self.txt_container, command=self._txt.yview)
        self.scrollbar.pack(side="right", fill="y", padx=2, pady=2)
        self._txt.configure(yscrollcommand=self.scrollbar.set)
        self._txt.configure(state="disabled")

        # Tags de estilo
        self._txt.tag_config("sistema",   foreground=COLORS["blue"], font=("Segoe UI", 11, "bold"))
        self._txt.tag_config("microfone", foreground=COLORS["green"], font=("Segoe UI", 11, "bold"))
        self._txt.tag_config("info",      foreground=SUB, font=("Segoe UI", 10, "italic"))
        self._txt.tag_config("erro",      foreground=COLORS["red"])
        self._txt.tag_config("timestamp", foreground=SUB, font=("Consolas", 10))
        self._txt.tag_config("speaker",   foreground=COLORS["yellow"], underline=True)
        
        # Binding para renomeação (Etapa 4)
        self._txt.tag_bind("speaker", "<Button-1>", self._on_speaker_click)

        # Footer Info
        self.footer = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.footer.pack(fill="x", pady=(10, 0))

        self._lbl_devices = ctk.CTkLabel(
            self.footer, text=self._devices_info(),
            text_color=SUB, font=("Segoe UI", 11),
        )
        self._lbl_devices.pack(side="left")

        self._lbl_file = ctk.CTkLabel(
            self.footer, text="",
            text_color=SUB, font=("Segoe UI", 11),
        )
        self._lbl_file.pack(side="right")

    # ── Helpers de info ───────────────────────────────────────────────────────

    def _devices_info(self) -> str:
        import sounddevice as sd
        try:
            sis = sd.query_devices(self._cfg["device_sistema"])["name"]
            mic = sd.query_devices(self._cfg["device_microfone"])["name"]
            return f"🔊 {sis[:25]}...  |  🎤 {mic[:25]}..."
        except Exception:
            return "Dispositivos não configurados"

    # ── Medidores e Waveform ──────────────────────────────────────────────────

    def _tick_meters(self) -> None:
        self.after(100, self._tick_meters)

    def on_level(self, label: str, rms: float) -> None:
        self.after(0, self._update_meter, label, rms)

    def _update_meter(self, label: str, rms: float) -> None:
        if "Sistema" in label:
            self._meter_sistema.update_level(rms)
            # Sistema tem prioridade no waveform se estiver ativo
            if rms > self._cfg["thresh_sistema"]:
                self._waveform.push_data(rms)
        else:
            self._meter_microfone.update_level(rms)
            # Se sistema estiver em silêncio, mostra microfone
            if rms > self._cfg["thresh_microfone"]:
                self._waveform.push_data(rms)

    # ── Controles principais ──────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running  = True
        self._stop_evt = threading.Event()
        self._speaker_map = {} # Reseta mapa de renomeação na sessão

        # Reinicia sessão de diarização (Falante_1, Falante_2... do zero)
        self._diarization.reset_session()

        # Cria arquivo de saída
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = OUTPUT_DIR / f"reuniao_{ts}.txt"
        self._file = open(path, "w", encoding="utf-8")
        self._file.write(
            f"Reunião iniciada em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        )
        self._file.write("=" * 60 + "\n\n")
        self._lbl_file.configure(text=f"💾 {path.name}")

        self._append_info(f"── Iniciado {datetime.now().strftime('%H:%M:%S')} ──")
        self._status_label.working("Transcrevendo")

        self._btn_start.set_inactive()
        self._btn_stop.set_active()
        self._btn_pause.set_active()
        self._btn_mic.set_active()

        # Inicia transcrição
        self._transcriber.start()

        # Captura sistema
        cap_sistema = VoiceCapture(
            device_idx=self._cfg["device_sistema"],
            label="🔊 Sistema",
            energy_threshold=self._cfg["thresh_sistema"],
            on_chunk=self._on_audio_chunk,
            stop_event=self._stop_evt,
            on_level=self.on_level,
        )

        # Captura microfone
        cap_microfone = VoiceCapture(
            device_idx=self._cfg["device_microfone"],
            label="🎤 Microfone",
            energy_threshold=self._cfg["thresh_microfone"],
            on_chunk=self._on_audio_chunk,
            stop_event=self._stop_evt,
            on_level=self.on_level,
            enabled_fn=lambda: self._mic_on,
        )

        threading.Thread(target=cap_sistema.run,   daemon=True).start()
        threading.Thread(target=cap_microfone.run, daemon=True).start()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._paused  = False
        self._stop_evt.set()
        self._transcriber.stop()

        if self._file:
            self._file.write(
                f"\n\nReunião encerrada em "
                f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            )
            self._file.close()
            self._file = None

        self._append_info(f"── Encerrado {datetime.now().strftime('%H:%M:%S')} ──")
        self._status_label.ready("Parado")

        self._btn_start.set_active()
        self._btn_stop.set_inactive()
        self._btn_pause.set_inactive(text="⏸  Pausar")
        self._btn_mic.set_inactive()

    def toggle_pause(self) -> None:
        if not self._running:
            return
            
        self._paused = not self._paused
        if self._paused:
            self._status_label.set("Pausado", COLORS["orange"])
            self._btn_pause.set_active(text="▶  Retomar", color=COLORS["green"])
            self._append_info(f"── Pausado em {datetime.now().strftime('%H:%M:%S')} ──")
        else:
            self._status_label.working("Transcrevendo")
            self._btn_pause.set_active(text="⏸  Pausar", color=COLORS["orange"])
            self._append_info(f"── Retomado em {datetime.now().strftime('%H:%M:%S')} ──")

    def toggle_mic(self) -> None:
        self._mic_on = not self._mic_on
        if self._mic_on:
            self._btn_mic.set_active(text="🎤  Mic ON",  color=COLORS["green"])
        else:
            self._btn_mic.set_active(text="🔇  Mic OFF", color=COLORS["surface"])

    def _open_settings(self) -> None:
        if self._running:
            self._append("⚠ Pare a gravação antes de alterar as configurações.\n", "erro")
            return
        SettingsWindow(self, on_apply=self._on_settings_applied)

    def _on_settings_applied(self, sis_idx, mic_idx, thresh_sis, thresh_mic) -> None:
        self._cfg["device_sistema"]   = sis_idx
        self._cfg["device_microfone"] = mic_idx
        self._cfg["thresh_sistema"]   = thresh_sis
        self._cfg["thresh_microfone"] = thresh_mic

        self._meter_sistema.update_threshold(thresh_sis)
        self._meter_microfone.update_threshold(thresh_mic)
        self._lbl_devices.configure(text=self._devices_info())
        self._append_info("✅ Configurações aplicadas com sucesso.")

    def _open_profiles(self) -> None:
        ProfileWindow(self, self._diarization)

    def _quit(self) -> None:
        self.stop()
        self.after(300, self.destroy)

    # ── Callbacks de áudio e transcrição ─────────────────────────────────────

    def _on_audio_chunk(self, audio: np.ndarray, timestamp: float, label: str) -> None:
        if self._paused:
            return
            
        # Envia o áudio direto para a fila. A diarização agora será feita 
        # dentro da thread do Transcriber para não bloquear a captura nem a UI.
        self._transcriber.enqueue(audio, timestamp, label)

    def _on_transcription(self, timestamp: float, channel: str, speaker: str | None, text: str) -> None:
        self.after(0, self._append_transcription, timestamp, channel, speaker, text)

    def _on_model_ready(self) -> None:
        self.after(0, self._on_ready_ui)

    def _on_ready_ui(self) -> None:
        self._append_info("Modelo carregado ✓  —  Clique em Iniciar.")
        self._status_label.ready("Pronto")
        self._btn_start.set_active()

    def _on_transcription_error(self, error: Exception) -> None:
        self.after(0, self._append, f"Erro: {error}\n", "erro")

    # ── Helpers de UI (Transcrições) ──────────────────────────────────────────

    def _append_info(self, text: str) -> None:
        self._append(f"{text}\n", "info")

    def _append_transcription(self, timestamp: float, channel: str, speaker: str | None, text: str) -> None:
        ts = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        tag_canal = "microfone" if "Microfone" in channel else "sistema"
        
        self._txt.configure(state="normal")
        
        # Timestamp
        self._txt.insert("end", f"[{ts}] ", "timestamp")
        
        # Canal
        self._txt.insert("end", f"{channel} ", tag_canal)
        
        # Falante (se houver)
        if speaker:
            # Se já foi renomeado nesta sessão, usa o novo nome
            display_name = self._speaker_map.get(speaker, speaker)
            # Criamos uma tag única por falante para renomeação em massa posterior
            speaker_tag = f"spk_{speaker.replace(' ', '_')}"
            self._txt.insert("end", f"[{display_name}]", ("speaker", speaker_tag))
            
        self._txt.insert("end", f": {text}\n")
        self._txt.see("end")
        self._txt.configure(state="disabled")

        # Salva no arquivo
        if self._file:
            spk_str = f" [{self._speaker_map.get(speaker, speaker)}]" if speaker else ""
            self._file.write(f"[{ts}] {channel}{spk_str}: {text}\n")
            self._file.flush()

    def _append(self, text: str, tag: str = "") -> None:
        self._txt.configure(state="normal")
        self._txt.insert("end", text, tag)
        self._txt.see("end")
        self._txt.configure(state="disabled")

    # ── Renomeação Dinâmica (Etapa 4) ─────────────────────────────────────────

    def _on_speaker_click(self, event):
        """Abre prompt para renomear falante ao clicar no nome."""
        # Encontra a tag do falante sob o clique
        index = self._txt.index(f"@{event.x},{event.y}")
        tags = self._txt.tag_names(index)
        
        speaker_tag = next((t for t in tags if t.startswith("spk_")), None)
        if not speaker_tag:
            return
            
        # O nome original está codificado na tag: spk_Falante_1 -> Falante_1
        original_name = speaker_tag[4:].replace("_", " ")
        current_name = self._speaker_map.get(original_name, original_name)
        
        new_name = ctk.CTkInputDialog(
            text=f"Renomear '{current_name}' para:",
            title="Diarização Dinâmica"
        ).get_input()
        
        if new_name and new_name.strip():
            self._rename_speaker(original_name, new_name.strip())

    def _rename_speaker(self, original_name: str, new_name: str):
        """Atualiza o nome do falante na UI e no mapa da sessão."""
        self._speaker_map[original_name] = new_name
        
        # Se for um falante anônimo da sessão (ex: Falante_1), 
        # "promove" ele a perfil permanente no banco de dados.
        if original_name.startswith("Falante_"):
            if self._diarization.save_session_speaker(original_name, new_name):
                self._append_info(f"👤 Perfil de voz '{new_name}' salvo permanentemente.")
        
        # Atualização em massa na área de texto
        # Busca todas as ocorrências da tag speaker_tag e substitui o texto
        speaker_tag = f"spk_{original_name.replace(' ', '_')}"
        
        self._txt.configure(state="normal")
        
        # Esta é uma operação complexa em Tkinter. Vamos iterar sobre os ranges da tag.
        ranges = self._txt.tag_ranges(speaker_tag)
        # Itera de trás para frente para não invalidar os índices ao substituir
        for i in range(len(ranges)-2, -1, -2):
            start = ranges[i]
            end = ranges[i+1]
            self._txt.delete(start, end)
            self._txt.insert(start, f"[{new_name}]", ("speaker", speaker_tag))
            
        self._txt.configure(state="disabled")
        self._append_info(f"👤 '{original_name}' renomeado para '{new_name}'")
