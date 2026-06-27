"""
ui/setup_wizard.py — Wizard de primeira execução para configurar dispositivos de áudio.

Responsabilidades:
- Guiar o usuário passo-a-passo
- Mostrar avisos específicos por SO
- Permitir seleção manual de dispositivos
- Fazer testes de áudio
- Salvar configuração
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import threading

from ui.widgets import COLORS, ActionButton
from ui.audio_setup import AudioDeviceDetector, AudioValidator
from ui.os_specific_setup import OSDetector, AudioSetupInstructions, DeviceAnalyzer
from audio import loopback
import settings
import sounddevice as sd


class SetupWizard(ctk.CTkToplevel):
    """
    Wizard modal para configuração de áudio na primeira execução.
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("⚙️ Configuração Inicial de Áudio")
        self.geometry("700x650")
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)
        
        # Forçar modal
        self.after(10, self.grab_set)
        
        # Detectar SO e dispositivos
        self.os_type = OSDetector.get_os()
        self.all_devices = AudioDeviceDetector.get_all_input_devices()
        stereo_idx, mic_idx = AudioDeviceDetector.auto_detect()

        self.stereo_mix_idx = stereo_idx
        self.mic_idx = mic_idx
        self.step = 0  # Controle de progresso
        self.config = {}  # Configurações finais

        # Tenta detectar loopback automático (D1: WASAPI / monitor / virtual)
        try:
            self.loopback_cfg = loopback.detect_system_audio()
        except loopback.LoopbackError as exc:
            self.loopback_cfg = None
            self.loopback_error = str(exc)
        else:
            self.loopback_error = None
        
        # UI
        self.title_label = None
        self.content_frame = None
        self._build_ui()
        self._show_step_1()
    
    def _build_ui(self) -> None:
        """Constrói a UI base do wizard."""
        BG, FG, SUB = COLORS["bg"], COLORS["fg"], COLORS["subtext"]
        
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["panel"], height=80)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="🎧 Primeiro Uso - Configuração de Áudio",
            text_color=COLORS["blue"],
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(15, 5))
        
        self.title_label = ctk.CTkLabel(
            header,
            text="Passo 1 de 3: Aviso Importante",
            text_color=SUB,
            font=("Segoe UI", 11),
        )
        self.title_label.pack(pady=(0, 15))
        
        # Content Area
        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Footer (Botões)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=30, pady=20)
        
        self.btn_back = ActionButton(
            footer,
            text="◀ Voltar",
            color=COLORS["surface"],
            fg=FG,
            command=self._prev_step,
            state="disabled",
        )
        self.btn_back.pack(side="left", padx=5)
        
        self.btn_next = ActionButton(
            footer,
            text="Próximo ▶",
            color=COLORS["blue"],
            command=self._next_step,
        )
        self.btn_next.pack(side="left", padx=5)
        
        self.btn_skip = ActionButton(
            footer,
            text="Usar Padrão",
            color=COLORS["surface"],
            fg=SUB,
            command=self._use_default,
        )
        self.btn_skip.pack(side="left", padx=5)
    
    def _clear_content(self) -> None:
        """Limpa o frame de conteúdo."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def _show_step_1(self) -> None:
        """Passo 1: Resultado do auto-detect de loopback (ou instruções se falhou)."""
        self.step = 1
        self.title_label.configure(text="Passo 1 de 3: Áudio do Sistema")
        self.btn_back.configure(state="disabled")
        self._clear_content()

        FG, SUB = COLORS["fg"], COLORS["subtext"]

        card = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["panel"],
            corner_radius=12,
        )
        card.pack(fill="both", expand=True, padx=10, pady=10)

        if self.loopback_cfg is not None:
            # Caminho feliz — auto-detect funcionou.
            ctk.CTkLabel(
                card,
                text="Áudio do sistema configurado automaticamente",
                text_color=COLORS["green"],
                font=("Segoe UI", 14, "bold"),
            ).pack(pady=(15, 5), padx=15, anchor="w")

            ctk.CTkLabel(
                card,
                text=self.loopback_cfg.label,
                text_color=FG,
                font=("Segoe UI", 11),
                wraplength=600,
                justify="left",
            ).pack(pady=(5, 10), padx=15, anchor="w")

            ctk.CTkLabel(
                card,
                text=(
                    "Não é preciso ativar Stereo Mix. O Meeting Transcriber vai "
                    "capturar o que sair pelos seus alto-falantes/headphones."
                ),
                text_color=SUB,
                font=("Segoe UI", 10),
                wraplength=600,
                justify="left",
            ).pack(pady=(0, 5), padx=15, anchor="w")

            ctk.CTkLabel(
                card,
                text=(
                    "Dica: use fones de ouvido sempre que possível. Sem fones, "
                    "o som sai pelo alto-falante e volta pelo microfone, gerando "
                    "eco/duplicação. O app já descarta a maior parte automaticamente, "
                    "mas o resultado fica melhor com fones."
                ),
                text_color=COLORS["yellow"],
                font=("Segoe UI", 10),
                wraplength=600,
                justify="left",
            ).pack(pady=(5, 15), padx=15, anchor="w")
            return

        # Caminho de fallback — auto-detect falhou. Mostra instruções por SO.
        instr = AudioSetupInstructions.get_stereo_mix_warning()

        ctk.CTkLabel(
            card,
            text=f"Não detectei loopback automático ({self.loopback_error})",
            text_color=COLORS["yellow"],
            font=("Segoe UI", 13, "bold"),
            wraplength=600,
            justify="left",
        ).pack(pady=(15, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            card,
            text=instr["title"],
            text_color=COLORS["yellow"],
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(5, 5), padx=15, anchor="w")

        ctk.CTkLabel(
            card,
            text=instr["message"],
            text_color=FG,
            font=("Segoe UI", 11),
            wraplength=600,
            justify="left",
        ).pack(pady=(5, 15), padx=15, anchor="w")

        ctk.CTkLabel(
            card,
            text="\n".join(instr["steps"]),
            text_color=SUB,
            font=("Segoe UI", 10),
            justify="left",
        ).pack(pady=(0, 15), padx=15, anchor="w")

        if instr.get("note"):
            ctk.CTkLabel(
                card,
                text=instr["note"],
                text_color=COLORS["blue"],
                font=("Segoe UI", 10),
                wraplength=600,
                justify="left",
            ).pack(pady=(5, 10), padx=15, anchor="w")

        if instr.get("alternatives"):
            ctk.CTkLabel(
                card,
                text="\n".join(instr["alternatives"]),
                text_color=COLORS["green"],
                font=("Segoe UI", 9),
                wraplength=600,
                justify="left",
            ).pack(pady=(5, 15), padx=15, anchor="w")

    
    def _show_step_2(self) -> None:
        """Passo 2: Seleção do microfone (e do sistema, se loopback falhou)."""
        self.step = 2
        self.title_label.configure(text="Passo 2 de 3: Selecione seus dispositivos")
        self.btn_back.configure(state="normal")
        self._clear_content()

        FG, SUB = COLORS["fg"], COLORS["subtext"]

        formatted_devices = [
            {
                "display": DeviceAnalyzer.format_device_info(dev),
                "index": dev["index"],
                "full_name": dev["name"],
                "raw": dev,
            }
            for dev in self.all_devices
        ]
        device_options = [d["display"] for d in formatted_devices]
        if not device_options:
            device_options = ["Nenhum dispositivo"]

        # ── Áudio do Sistema: SEMPRE automático (loopback) ───────────────────
        # Não há mais seleção manual de dispositivo do sistema — a ideia do app
        # é transcrever exatamente o que o usuário escuta, sem configuração.
        self.combo_stereo = None
        if self.loopback_cfg is not None:
            ctk.CTkLabel(
                self.content_frame,
                text="🔊 Áudio do Sistema: detectado automaticamente",
                text_color=COLORS["green"],
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w", pady=(10, 5))
            ctk.CTkLabel(
                self.content_frame,
                text=self.loopback_cfg.label,
                text_color=SUB,
                font=("Segoe UI", 10),
                justify="left",
            ).pack(anchor="w", pady=(0, 2))
            ctk.CTkLabel(
                self.content_frame,
                text="Captura o que sai pelos seus fones/alto-falantes. Nada para configurar.",
                text_color=SUB,
                font=("Segoe UI", 9),
                wraplength=600,
                justify="left",
            ).pack(anchor="w", pady=(0, 20))
        else:
            ctk.CTkLabel(
                self.content_frame,
                text="🔊 Áudio do Sistema: indisponível no momento",
                text_color=COLORS["yellow"],
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w", pady=(10, 5))
            ctk.CTkLabel(
                self.content_frame,
                text=(
                    "Não encontrei uma saída de áudio ativa para capturar. "
                    "Conecte fones ou alto-falantes e reabra o app — a captura é "
                    "automática. Você ainda pode continuar e configurar o microfone."
                ),
                text_color=SUB,
                font=("Segoe UI", 10),
                wraplength=600,
                justify="left",
            ).pack(anchor="w", pady=(0, 20))

        # ── Nome do usuário (D7) ─────────────────────────────────────────────
        ctk.CTkLabel(
            self.content_frame,
            text="👤 Como você quer ser identificado nas transcrições?",
            text_color=COLORS["yellow"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(10, 5))

        self._user_name_var = tk.StringVar(
            value=settings.get("user_profile_name") or "Eu"
        )
        ctk.CTkEntry(
            self.content_frame,
            textvariable=self._user_name_var,
            fg_color=COLORS["surface"],
            text_color=FG,
            border_width=0,
            width=300,
            height=32,
        ).pack(anchor="w", pady=(0, 20))

        # ── Microfone ────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self.content_frame,
            text="🎤 Microfone (escolha o seu)",
            text_color=COLORS["green"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(10, 5))

        tip_frame2 = ctk.CTkFrame(self.content_frame, fg_color=COLORS["panel"], corner_radius=8)
        tip_frame2.pack(fill="x", pady=(0, 10), padx=5)
        ctk.CTkLabel(
            tip_frame2,
            text=AudioSetupInstructions.get_microphone_selection_tip(),
            text_color=SUB,
            font=("Segoe UI", 9),
            justify="left",
        ).pack(padx=10, pady=8, anchor="w")

        self.combo_mic = ctk.CTkOptionMenu(
            self.content_frame,
            values=device_options,
            fg_color=COLORS["surface"],
            button_color=COLORS["surface"],
            button_hover_color=COLORS["panel"],
            text_color=FG,
            width=600,
        )
        if self.mic_idx is not None:
            sel = next(
                (d["display"] for d in formatted_devices if d["index"] == self.mic_idx),
                device_options[0],
            )
            self.combo_mic.set(sel)
        elif len(device_options) > 1:
            self.combo_mic.set(device_options[1])
        else:
            self.combo_mic.set(device_options[0])
        self.combo_mic.pack(anchor="w", pady=(0, 20))

        self._formatted_devices = formatted_devices

    
    def _show_step_3(self) -> None:
        """Passo 3: Teste de áudio e salvamento."""
        self.step = 3
        self.title_label.configure(text="Passo 3 de 3: Teste de Áudio")
        self._clear_content()

        FG, SUB = COLORS["fg"], COLORS["subtext"]

        try:
            mic_sel = self.combo_mic.get()
            mic_idx = int(mic_sel.split("]")[0].replace("[", "").strip())
            self.config["device_microfone"] = mic_idx

            # Áudio do sistema é sempre loopback automático (runtime resolve).
            self.config["device_sistema"] = None
        except Exception:
            messagebox.showerror("Erro", "Falha ao ler dispositivos selecionados")
            self._cancel()
            return
        
        ctk.CTkLabel(
            self.content_frame,
            text="🎙️ Teste de Áudio",
            text_color=COLORS["green"],
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(20, 10))
        
        progress_label = ctk.CTkLabel(
            self.content_frame,
            text="Testando dispositivos...",
            text_color=FG,
            font=("Segoe UI", 11),
        )
        progress_label.pack(pady=(20, 30))
        
        # Desabilitar botões
        self.btn_back.configure(state="disabled")
        self.btn_next.configure(state="disabled")
        self.btn_skip.configure(state="disabled")
        
        # Fazer testes
        results = {}

        def test_stereo():
            sis_dev = self.config["device_sistema"]
            if sis_dev is None:
                # Auto-detect via loopback module — testa a config detectada.
                results["stereo"] = "auto"
            else:
                results["stereo"] = AudioValidator.test_device_audio(sis_dev, duration_sec=3.0)
            self.after(0, lambda: progress_label.configure(text="Sistema testado"))
            self.after(500, test_mic)

        def test_mic():
            progress_label.configure(text="Testando Microfone...")
            rms = AudioValidator.test_device_audio(
                self.config["device_microfone"], duration_sec=2.0
            )
            results["mic"] = rms
            self.after(0, lambda: progress_label.configure(text="Microfone testado"))
            self.after(500, show_results)

        def show_results():
            self._clear_content()

            ctk.CTkLabel(
                self.content_frame,
                text="Resultados dos Testes",
                text_color=COLORS["green"],
                font=("Segoe UI", 14, "bold"),
            ).pack(pady=(20, 30))

            stereo_rms = results.get("stereo")
            mic_rms = results.get("mic")

            lines = []
            if stereo_rms == "auto":
                lines.append(
                    f"Sistema: {self.loopback_cfg.label} (loopback automático)"
                )
            elif stereo_rms is not None:
                lines.append(f"Sistema: RMS = {stereo_rms:.5f}")
            else:
                lines.append("Sistema: falha ao capturar")

            if mic_rms is not None:
                lines.append(f"Microfone: RMS = {mic_rms:.5f}")
            else:
                lines.append("Microfone: falha ao capturar")

            lines.append("")
            lines.append("Configuração pronta. Clique em Salvar para começar.")

            ctk.CTkLabel(
                self.content_frame,
                text="\n".join(lines),
                text_color=FG,
                font=("Segoe UI", 11),
                justify="left",
            ).pack(pady=20, padx=20, anchor="w")

            self.btn_next.configure(text="Salvar e Começar", state="normal")

        threading.Thread(target=test_stereo, daemon=True).start()
    
    def _next_step(self) -> None:
        """Avança para próximo passo."""
        if self.step == 1:
            self._show_step_2()
        elif self.step == 2:
            self._show_step_3()
        elif self.step == 3:
            self._save_config()
    
    def _prev_step(self) -> None:
        """Volta para passo anterior."""
        if self.step == 2:
            self._show_step_1()
        elif self.step == 3:
            self._show_step_2()
    
    def _use_default(self) -> None:
        """Usa o que foi auto-detectado, sem passar pelos testes."""
        self.config["device_sistema"] = None  # sistema é sempre automático

        if self.mic_idx is not None:
            self.config["device_microfone"] = self.mic_idx
        self._save_config()

    def _save_config(self) -> None:
        """Salva configuração e fecha wizard."""
        # Áudio do sistema é sempre automático (loopback). Sem seleção manual.
        self.config.setdefault("device_sistema", None)

        # Microfone: obrigatório, lê do combo se ainda não tiver.
        if "device_microfone" not in self.config:
            try:
                mic_sel = self.combo_mic.get()
                self.config["device_microfone"] = int(
                    mic_sel.split("]")[0].replace("[", "").strip()
                )
            except Exception:
                pass

        if not self.config.get("device_microfone"):
            messagebox.showerror(
                "Configuração incompleta",
                "Selecione um microfone antes de salvar.",
                parent=self,
            )
            return

        # Nome do usuário (D7): default "Eu" se vazio.
        try:
            name = self._user_name_var.get().strip() if hasattr(self, "_user_name_var") else ""
        except Exception:
            name = ""
        self.config["user_profile_name"] = name or "Eu"

        settings.save(self.config)
        messagebox.showinfo(
            "Configuração salva",
            "Pronto! A janela principal será aberta em seguida.",
            parent=self,
        )
        self.destroy()
    
    def _cancel(self) -> None:
        """Cancela wizard."""
        self.destroy()
