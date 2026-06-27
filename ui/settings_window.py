"""
ui/settings_window.py — Janela de configurações de áudio usando customtkinter.
"""

import threading
import time
import tkinter as tk
import customtkinter as ctk

import numpy as np
import sounddevice as sd

from ui.widgets import COLORS, ActionButton
import settings


def list_input_devices() -> list[dict]:
    """Retorna todos os dispositivos com canais de entrada disponíveis."""
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append({
                "index": i,
                "name":  dev["name"],
                "sr":    int(dev["default_samplerate"]),
                "ch":    dev["max_input_channels"],
            })
    return devices


class SettingsWindow(ctk.CTkToplevel):
    """
    Janela modal de configurações de áudio usando CustomTkinter.
    """

    def __init__(self, parent, on_apply):
        super().__init__(parent)
        self.on_apply    = on_apply
        self._devices    = list_input_devices()
        self._previewing = False
        self._stop_prev  = threading.Event()

        self.title("Configurações de Áudio")
        self.geometry("580x700")
        self.configure(fg_color=COLORS["bg"])
        
        # Faz a janela ser modal
        self.after(10, self.grab_set)

        # Carrega configurações salvas
        saved = settings.load()

        self._saved_sis_idx    = saved.get("device_sistema")
        self._saved_mic_idx    = saved.get("device_microfone")
        self._saved_thresh_sis = saved.get("thresh_sistema")
        self._saved_thresh_mic = saved.get("thresh_microfone")

        # Container principal com scroll para garantir que tudo apareça
        self.scroll_container = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent", 
            width=550, 
            height=680,
            label_text="Ajustes de Dispositivos e Sensibilidade",
            label_font=("Segoe UI", 13, "bold"),
            label_text_color=COLORS["fg"]
        )
        self.scroll_container.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_ui()

    def _build_ui(self) -> None:
        BG, PANEL = COLORS["bg"], COLORS["panel"]
        FG, SUB   = COLORS["fg"], COLORS["subtext"]

        ctk.CTkLabel(
            self.scroll_container,
            text="Calibre os thresholds VAD enquanto ouve/fala.",
            text_color=SUB, font=("Segoe UI", 12), justify="center",
        ).pack(pady=(0, 20))

        # ── Sistema (sempre automático: loopback, sem seleção de device) ──────
        self._build_system_section(saved_thresh=self._saved_thresh_sis)

        ctk.CTkFrame(self.scroll_container, fg_color=COLORS["surface"], height=1).pack(fill="x", padx=30, pady=20)

        # ── Microfone ─────────────────────────────────────────────────────────
        self._build_channel_section(
            label="🎤 Microfone",
            color=COLORS["green"],
            attr_prefix="mic",
            saved_idx=self._saved_mic_idx,
            saved_thresh=self._saved_thresh_mic,
        )

        ctk.CTkFrame(self.scroll_container, fg_color=COLORS["surface"], height=1).pack(fill="x", padx=30, pady=20)

        # ── Modelo Whisper ───────────────────────────────────────────────────
        self._build_whisper_section()

        ctk.CTkFrame(self.scroll_container, fg_color=COLORS["surface"], height=1).pack(fill="x", padx=30, pady=20)

        # ── Botões ────────────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        btn_frame.pack(pady=(10, 30))

        ActionButton(
            btn_frame, text="✅  Salvar e aplicar",
            color=COLORS["green"],
            command=self._apply,
        ).pack(side="left", padx=10)

        ActionButton(
            btn_frame, text="✕  Cancelar",
            color=COLORS["surface"], fg=FG,
            command=self._cancel,
        ).pack(side="left", padx=10)

    # ── Seção Modelo Whisper ──────────────────────────────────────────────────

    _WHISPER_MODELS = [
        ("tiny",     "tiny     ·  75 MB · qualidade básica · CPU rápido"),
        ("base",     "base     · 142 MB · qualidade ok · CPU rápido"),
        ("small",    "small    · 466 MB · qualidade boa · CPU médio"),
        ("medium",   "medium   · 1.5 GB · qualidade muito boa (recomendado)"),
        ("large-v3", "large-v3 ·   3 GB · qualidade excelente · GPU recomendada"),
    ]

    def _build_whisper_section(self) -> None:
        FG, SUB = COLORS["fg"], COLORS["subtext"]

        frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        frame.pack(fill="x", padx=30)

        ctk.CTkLabel(
            frame, text="🧠 Modelo de Transcrição (Whisper)",
            text_color=COLORS["yellow"], font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame,
            text=(
                "Modelos maiores transcrevem melhor mas usam mais CPU/RAM.\n"
                "Em CPU sem GPU, espere alguns segundos por frase.\n"
                "Trocar dispara download na próxima inicialização."
            ),
            text_color=SUB, font=("Segoe UI", 10), justify="left",
        ).pack(anchor="w", pady=(4, 8))

        saved_model = settings.get("whisper_model") or "medium"
        labels   = [lbl for _, lbl in self._WHISPER_MODELS]
        by_label = {lbl: name for name, lbl in self._WHISPER_MODELS}
        by_name  = {name: lbl for name, lbl in self._WHISPER_MODELS}

        self._whisper_combo = ctk.CTkOptionMenu(
            frame,
            values=labels,
            fg_color=COLORS["surface"],
            button_color=COLORS["surface"],
            button_hover_color=COLORS["panel"],
            text_color=FG,
            width=400,
        )
        self._whisper_combo.set(by_name.get(saved_model, by_name["medium"]))
        self._whisper_combo.pack(anchor="w", pady=(4, 0))
        self._whisper_label_to_name = by_label

    def _build_system_section(self, saved_thresh: float) -> None:
        """
        Seção do áudio do sistema. NÃO há seleção de dispositivo: a captura é
        sempre automática (loopback do que o usuário escuta). Mantém apenas o
        threshold, que alimenta o medidor visual da tela principal.
        """
        FG, SUB = COLORS["fg"], COLORS["subtext"]
        color = COLORS["blue"]

        frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        frame.pack(fill="x", padx=30)

        ctk.CTkLabel(
            frame, text="🔊 Áudio do Sistema (automático)",
            text_color=color, font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame,
            text=(
                "Capturado automaticamente via loopback — o que sai pelos seus "
                "fones/alto-falantes. Não há dispositivo para escolher."
            ),
            text_color=SUB, font=("Segoe UI", 10), justify="left", wraplength=480,
        ).pack(anchor="w", pady=(4, 8))

        thresh_frame = ctk.CTkFrame(frame, fg_color="transparent")
        thresh_frame.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(
            thresh_frame, text="Threshold do medidor:",
            text_color=FG, font=("Segoe UI", 12),
        ).pack(side="left")

        thresh_label = ctk.CTkLabel(
            thresh_frame, text=f"{saved_thresh:.5f}",
            text_color=color, font=("Consolas", 12), width=80,
        )
        thresh_label.pack(side="right")

        def on_slider(val):
            thresh_label.configure(text=f"{float(val) / 10_000:.5f}")

        slider = ctk.CTkSlider(
            frame, from_=0.5, to=50, number_of_steps=99,
            button_color=color, button_hover_color=self._adjust_color(color, 0.8),
            progress_color=color, command=on_slider, width=400,
        )
        slider.set(saved_thresh * 10_000)
        slider.pack(anchor="w", pady=(5, 0))

        self._sis_slider = slider

    def _build_channel_section(
        self,
        label: str,
        color: str,
        attr_prefix: str,
        saved_idx,
        saved_thresh: float,
    ) -> None:
        BG, FG, SUB = COLORS["bg"], COLORS["fg"], COLORS["subtext"]

        frame = ctk.CTkFrame(self.scroll_container, fg_color="transparent")
        frame.pack(fill="x", padx=30)

        # Título do canal
        ctk.CTkLabel(
            frame, text=label,
            text_color=color, font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")

        # Dropdown de dispositivos
        dev_names = [f"[{d['index']}] {d['name']}" for d in self._devices]
        
        default_sel = dev_names[0] if dev_names else "Nenhum dispositivo encontrado"
        if saved_idx is not None:
            for name in dev_names:
                if name.startswith(f"[{saved_idx}]"):
                    default_sel = name
                    break

        combo = ctk.CTkOptionMenu(
            frame,
            values=dev_names,
            fg_color=COLORS["surface"],
            button_color=COLORS["surface"],
            button_hover_color=COLORS["panel"],
            text_color=FG,
            width=400,
        )
        combo.set(default_sel)
        combo.pack(anchor="w", pady=(8, 0))

        # Threshold Control
        thresh_frame = ctk.CTkFrame(frame, fg_color="transparent")
        thresh_frame.pack(fill="x", pady=(12, 0))

        ctk.CTkLabel(
            thresh_frame, text="Threshold VAD:",
            text_color=FG, font=("Segoe UI", 12),
        ).pack(side="left")

        thresh_label = ctk.CTkLabel(
            thresh_frame,
            text=f"{saved_thresh:.5f}",
            text_color=color,
            font=("Consolas", 12), width=80,
        )
        thresh_label.pack(side="right")

        def on_slider(val):
            real = float(val) / 10_000
            thresh_label.configure(text=f"{real:.5f}")

        slider = ctk.CTkSlider(
            frame,
            from_=0.5, to=50,
            number_of_steps=99,
            button_color=color,
            button_hover_color=self._adjust_color(color, 0.8),
            progress_color=color,
            command=on_slider,
            width=400,
        )
        slider.set(saved_thresh * 10_000)
        slider.pack(anchor="w", pady=(5, 0))

        # Preview Bar
        prev_frame = ctk.CTkFrame(frame, fg_color="transparent")
        prev_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            prev_frame, text="Nível atual:",
            text_color=SUB, font=("Segoe UI", 11),
        ).pack(side="left", padx=(0, 10))

        canvas = tk.Canvas(
            prev_frame, width=300, height=8,
            bg=COLORS["surface"], highlightthickness=0,
            borderwidth=0
        )
        canvas.pack(side="left")

        # Botão preview
        btn_preview = ActionButton(
            frame,
            text="▶  Testar Nível",
            color=COLORS["accent"], fg="white",
            command=lambda p=attr_prefix: self._toggle_preview(p),
            width=120,
            height=28,
        )
        btn_preview.pack(anchor="w", pady=(10, 0))

        # Salva referências
        setattr(self, f"_{attr_prefix}_combo",     combo)
        setattr(self, f"_{attr_prefix}_slider",    slider)
        setattr(self, f"_{attr_prefix}_canvas",    canvas)
        setattr(self, f"_{attr_prefix}_rms_lbl",   thresh_label) 
        setattr(self, f"_{attr_prefix}_color",     color)
        setattr(self, f"_{attr_prefix}_preview_btn", btn_preview)

    def _adjust_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(max(0, min(255, int(c * factor))) for c in rgb)
        return '#%02x%02x%02x' % new_rgb

    def _toggle_preview(self, prefix: str) -> None:
        btn = getattr(self, f"_{prefix}_preview_btn")

        if self._previewing:
            self._stop_prev.set()
            self._previewing = False
            btn.configure(text="▶  Testar Nível", fg_color=COLORS["accent"])
            return

        self._stop_prev = threading.Event()
        self._previewing = True
        btn.configure(text="⏹  Parar Teste", fg_color=COLORS["yellow"])

        threading.Thread(target=self._run_preview, args=(prefix,), daemon=True).start()

    def _run_preview(self, prefix: str) -> None:
        combo = getattr(self, f"_{prefix}_combo")
        selected = combo.get()

        try:
            dev_idx = int(selected.split("]")[0].replace("[", "").strip())
            dev = sd.query_devices(dev_idx)
            ch = dev["max_input_channels"]
            sr = int(dev["default_samplerate"])
            hop = int(sr * 0.05)

            def cb(indata, frames, t, status):
                mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
                rms  = float(np.sqrt(np.mean(mono ** 2)))
                self.after(0, self._update_preview_bar, prefix, rms)

            with sd.InputStream(device=dev_idx, channels=ch, samplerate=sr, callback=cb, blocksize=hop):
                while not self._stop_prev.is_set():
                    time.sleep(0.05)
        except Exception as exc:
            print(f"Erro preview: {exc}")
        finally:
            self.after(0, self._reset_preview_btn, prefix)

    def _reset_preview_btn(self, prefix):
        btn = getattr(self, f"_{prefix}_preview_btn")
        btn.configure(text="▶  Testar Nível", fg_color=COLORS["accent"])
        self._previewing = False

    def _update_preview_bar(self, prefix: str, rms: float) -> None:
        canvas = getattr(self, f"_{prefix}_canvas")
        color  = getattr(self, f"_{prefix}_color")
        slider = getattr(self, f"_{prefix}_slider")

        canvas.delete("bar")
        x = int(min(rms / 0.05, 1.0) * 300)
        if x > 0:
            canvas.create_rectangle(0, 0, x, 8, fill=color, outline="", tags="bar")

        # Threshold line
        tx = int(min((slider.get() / 10_000) / 0.05, 1.0) * 300)
        canvas.create_line(tx, 0, tx, 8, fill=COLORS["yellow"], width=1, dash=(3, 2), tags="bar")

    def _apply(self) -> None:
        self._stop_prev.set()

        def get_idx(p):
            s = getattr(self, f"_{p}_combo").get()
            return int(s.split("]")[0].replace("[", "").strip())

        try:
            sis_idx = None  # áudio do sistema é sempre automático (loopback)
            mic_idx = get_idx("mic")
            thresh_sis = self._sis_slider.get() / 10_000
            thresh_mic = self._mic_slider.get() / 10_000

            chosen_label = self._whisper_combo.get()
            chosen_model = self._whisper_label_to_name.get(chosen_label, "small")
            previous_model = settings.get("whisper_model") or "small"

            settings.save({
                "device_sistema":    sis_idx,
                "device_microfone":  mic_idx,
                "thresh_sistema":    thresh_sis,
                "thresh_microfone":  thresh_mic,
                "whisper_model":     chosen_model,
            })

            if self.on_apply:
                self.on_apply(sis_idx, mic_idx, thresh_sis, thresh_mic)

            if chosen_model != previous_model:
                from tkinter import messagebox
                messagebox.showinfo(
                    "Modelo alterado",
                    f"Modelo trocado de '{previous_model}' para '{chosen_model}'.\n"
                    "Reinicie o app para que o novo modelo seja carregado.",
                    parent=self,
                )

            self.destroy()
        except Exception as e:
            print(f"Erro ao salvar: {e}")

    def _cancel(self) -> None:
        self._stop_prev.set()
        self.destroy()
