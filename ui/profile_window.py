"""
ui/profile_window.py — Janela de gerenciamento de perfis de voz usando customtkinter.
"""

import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

import numpy as np
import sounddevice as sd

from audio.resampler import resample, normalize_amplitude
from ui.widgets import COLORS, ActionButton
from ui.settings_window import load_settings
from config import DEVICE_MICROFONE, TARGET_SR

# Duração da gravação de referência
RECORD_SECONDS = 4


def _get_mic_device() -> int:
    """Retorna o índice do microfone: settings.json > config.py."""
    saved = load_settings()
    return saved.get("device_microfone", DEVICE_MICROFONE)


class ProfileWindow(ctk.CTkToplevel):
    """
    Janela de gerenciamento de perfis de voz usando CustomTkinter.
    """

    def __init__(self, parent, engine):
        super().__init__(parent)
        self.engine = engine

        self.title("Perfis de Voz")
        self.geometry("500x620")
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)
        
        # Faz a janela ser modal
        self.after(10, self.grab_set)

        self._recording   = False
        self._stop_rec    = threading.Event()
        self._audio_buf   : list[np.ndarray] = []
        self._countdown   = 0

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        BG, PANEL = COLORS["bg"], COLORS["panel"]
        FG, SUB   = COLORS["fg"], COLORS["subtext"]

        ctk.CTkLabel(
            self, text="👤 Perfis de Voz",
            text_color=FG, font=("Segoe UI", 18, "bold"),
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            self,
            text="Perfis salvos são identificados automaticamente\nem gravações futuras.",
            text_color=SUB, font=("Segoe UI", 12), justify="center",
        ).pack(pady=(0, 20))

        # ── Lista de perfis ───────────────────────────────────────────────────
        self.list_container = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        self.list_container.pack(fill="both", expand=True, padx=30, pady=(0, 15))

        self._listbox = tk.Listbox(
            self.list_container,
            bg=PANEL, fg=FG,
            font=("Segoe UI", 12),
            relief="flat", bd=0,
            highlightthickness=0,
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["bg"],
            activestyle="none",
        )
        self._listbox.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        
        self.scrollbar = ctk.CTkScrollbar(self.list_container, command=self._listbox.yview)
        self.scrollbar.pack(side="right", fill="y", padx=2, pady=2)
        self._listbox.configure(yscrollcommand=self.scrollbar.set)

        ActionButton(
            self, text="🗑  Deletar Perfil Selecionado",
            color=COLORS["red"], fg="white",
            command=self._delete_selected,
        ).pack(pady=(0, 20))

        ctk.CTkFrame(self, fg_color=COLORS["surface"], height=1).pack(fill="x", padx=30, pady=10)

        # ── Cadastro ──────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Cadastrar novo perfil",
            text_color=FG, font=("Segoe UI", 14, "bold"),
        ).pack(pady=(10, 5))

        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.pack(pady=5)

        ctk.CTkLabel(
            name_frame, text="Nome:",
            text_color=FG, font=("Segoe UI", 12),
        ).pack(side="left", padx=(0, 10))

        self._name_var = tk.StringVar()
        self._entry_name = ctk.CTkEntry(
            name_frame,
            textvariable=self._name_var,
            fg_color=COLORS["surface"],
            text_color=FG,
            border_width=0,
            width=200,
            height=32
        )
        self._entry_name.pack(side="left")

        # Nível de áudio
        self.level_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.level_frame.pack(pady=(10, 0))

        ctk.CTkLabel(
            self.level_frame, text="Sinal:",
            text_color=SUB, font=("Segoe UI", 11),
        ).pack(side="left", padx=(0, 10))

        self._level_canvas = tk.Canvas(
            self.level_frame, width=250, height=8,
            bg=COLORS["surface"], highlightthickness=0,
            borderwidth=0
        )
        self._level_canvas.pack(side="left")

        # Botão de gravação
        self._btn_record = ActionButton(
            self,
            text=f"⏺  Gravar {RECORD_SECONDS}s de voz",
            color=COLORS["accent"], fg="white",
            command=self._toggle_recording,
            width=260
        )
        self._btn_record.pack(pady=(15, 5))

        # Status / countdown
        self._lbl_status = ctk.CTkLabel(
            self, text="",
            text_color=COLORS["yellow"],
            font=("Segoe UI", 12, "bold"),
        )
        self._lbl_status.pack(pady=(0, 20))

    def _refresh_list(self) -> None:
        self._listbox.delete(0, "end")
        profiles = self.engine.list_profiles()
        if profiles:
            for name in profiles:
                self._listbox.insert("end", f"  {name}")
        else:
            self._listbox.insert("end", "  (nenhum perfil cadastrado)")

    def _delete_selected(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return

        name = self._listbox.get(sel[0]).strip()
        if not name or name.startswith("("):
            return

        if messagebox.askyesno("Confirmar", f"Deletar o perfil '{name}'?", parent=self):
            self.engine.delete_profile(name)
            self._refresh_list()

    def _toggle_recording(self) -> None:
        if self._recording:
            self._stop_rec.set()
            return

        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Atenção", "Digite um nome antes de gravar.", parent=self)
            return

        self._recording = True
        self._stop_rec  = threading.Event()
        self._audio_buf = []

        self._btn_record.configure(text="⏹  Cancelar gravação", fg_color=COLORS["red"])
        self._lbl_status.configure(text=f"🔴  Gravando... {RECORD_SECONDS}s", text_color=COLORS["red"])

        threading.Thread(target=self._record_voice, args=(name,), daemon=True).start()

    def _record_voice(self, name: str) -> None:
        dev_idx = _get_mic_device()
        try:
            dev_info = sd.query_devices(dev_idx)
            native_sr = int(dev_info["default_samplerate"])
            channels  = dev_info["max_input_channels"]
            hop       = int(native_sr * 0.05)
            total_frames  = int(native_sr * RECORD_SECONDS)
            frames_so_far = 0

            def callback(indata, frames, t, status):
                nonlocal frames_so_far
                if self._stop_rec.is_set(): raise sd.CallbackStop()
                mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
                self._audio_buf.append(mono.copy())
                frames_so_far += len(mono)
                rms = float(np.sqrt(np.mean(mono ** 2)))
                remaining = max(0, RECORD_SECONDS - frames_so_far / native_sr)
                self.after(0, self._update_recording_ui, rms, remaining)
                if frames_so_far >= total_frames: raise sd.CallbackStop()

            with sd.InputStream(device=dev_idx, channels=channels, samplerate=native_sr, callback=callback, blocksize=hop):
                while not self._stop_rec.is_set() and frames_so_far < total_frames:
                    import time
                    time.sleep(0.05)
        except Exception as exc:
            self.after(0, self._on_record_error, str(exc))
            return

        if self._stop_rec.is_set() or not self._audio_buf:
            self.after(0, self._on_record_cancelled)
            return

        self.after(0, self._lbl_status.configure, {"text": "⏳ Processando...", "text_color": COLORS["yellow"]})
        try:
            raw = np.concatenate(self._audio_buf).astype(np.float32)
            resampled = resample(raw, native_sr)
            success = self.engine.register(name, normalize_amplitude(resampled))
            self.after(0, self._on_record_done, name, success)
        except Exception as exc:
            self.after(0, self._on_record_error, str(exc))

    def _update_recording_ui(self, rms: float, remaining: float) -> None:
        self._level_canvas.delete("all")
        x = int(min(rms / 0.05, 1.0) * 250)
        if x > 0:
            self._level_canvas.create_rectangle(0, 0, x, 8, fill=COLORS["red"], outline="", tags="bar")
        secs = int(remaining) + 1
        self._lbl_status.configure(text=f"🔴  Gravando... {secs}s restantes")

    def _on_record_done(self, name: str, success: bool) -> None:
        self._recording = False
        self._level_canvas.delete("all")
        self._btn_record.configure(text=f"⏺  Gravar {RECORD_SECONDS}s de voz", fg_color=COLORS["accent"])
        if success:
            self._lbl_status.configure(text=f"✅  Perfil '{name}' salvo!", text_color=COLORS["green"])
            self._name_var.set("")
            self._refresh_list()
        else:
            self._lbl_status.configure(text="✗ Voz não reconhecida.", text_color=COLORS["red"])

    def _on_record_cancelled(self) -> None:
        self._recording = False
        self._level_canvas.delete("all")
        self._btn_record.configure(text=f"⏺  Gravar {RECORD_SECONDS}s de voz", fg_color=COLORS["accent"])
        self._lbl_status.configure(text="Cancelado.", text_color=SUB)

    def _on_record_error(self, error: str) -> None:
        self._recording = False
        self._level_canvas.delete("all")
        self._btn_record.configure(text=f"⏺  Gravar {RECORD_SECONDS}s de voz", fg_color=COLORS["accent"])
        self._lbl_status.configure(text=f"✗ Erro: {error}", text_color=COLORS["red"])
