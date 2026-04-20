"""
diarization/profiles.py — Perfis de voz persistentes.

Responsabilidades:
- Salvar/carregar perfis de voz em ~/.meeting_transcriber/voice_profiles.json
- Identificar um falante por similaridade com perfis conhecidos
- Gerenciar falantes anônimos da sessão atual (Falante_1, Falante_2...)
- Permitir renomear falantes anônimos após identificação

Formato do arquivo JSON:
{
    "profiles": {
        "uuid": {
            "name": "Márcio",
            "embedding": [0.12, -0.34, ...],   ← lista de 256 floats
            "created_at": "2026-04-09T14:30:00",
            "updated_at": "2026-04-09T14:30:00"
        }
    }
}
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from .embedder import cosine_similarity
from config import (
    PROFILES_DIR,
    PROFILES_FILE,
    DIARIZATION_SIMILARITY_THRESHOLD,
    DIARIZATION_MAX_SPEAKERS,
)


class VoiceProfile:
    """Representa um único perfil de voz (pessoa conhecida ou anônima)."""

    def __init__(
        self,
        profile_id: str,
        name: str,
        embedding: np.ndarray,
        created_at: str | None = None,
        updated_at: str | None = None,
    ):
        self.profile_id = profile_id
        self.name       = name
        self.embedding  = embedding
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "name":       self.name,
            "embedding":  self.embedding.tolist(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, profile_id: str, data: dict) -> "VoiceProfile":
        return cls(
            profile_id=profile_id,
            name=data["name"],
            embedding=np.array(data["embedding"], dtype=np.float32),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class ProfileManager:
    """
    Gerencia perfis de voz persistentes e identificação de falantes.

    Uso típico:
        manager = ProfileManager()
        name = manager.identify(embedding)   # "Márcio" ou "Falante_1"
        manager.save_profile("Márcio", embedding)
    """

    def __init__(self):
        self._profiles: dict[str, VoiceProfile] = {}
        # Falantes anônimos da sessão atual (não persistem entre sessões)
        # label -> {"embedding": np.ndarray, "count": int}
        self._session_profiles: dict[str, dict] = {}
        self._speaker_counter = 0

        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    # ── Persistência ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Carrega perfis do arquivo JSON. Silencioso se o arquivo não existe."""
        if not PROFILES_FILE.exists():
            return
        try:
            data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
            for pid, pdata in data.get("profiles", {}).items():
                self._profiles[pid] = VoiceProfile.from_dict(pid, pdata)
        except Exception as exc:
            print(f"[ProfileManager] Erro ao carregar perfis: {exc}")

    def _save(self) -> None:
        """Persiste os perfis conhecidos em disco."""
        try:
            data = {
                "profiles": {
                    pid: p.to_dict()
                    for pid, p in self._profiles.items()
                }
            }
            PROFILES_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[ProfileManager] Erro ao salvar perfis: {exc}")

    # ── Identificação ─────────────────────────────────────────────────────────

    def identify(self, embedding: np.ndarray) -> str:
        """
        Identifica um falante pelo embedding de voz.

        Ordem de busca:
        1. Perfis conhecidos (persistidos) — retorna o nome cadastrado
        2. Falantes anônimos da sessão — retorna "Falante_N" consistente
        3. Novo anônimo — cria "Falante_N+1" e registra na sessão

        Args:
            embedding: Array float32 de 256 dimensões.

        Returns:
            Nome do falante (ex: "Márcio", "Falante_1").
        """
        # 1. Busca entre perfis conhecidos
        best_name, best_score = self._match_known(embedding)
        if best_score >= DIARIZATION_SIMILARITY_THRESHOLD:
            return best_name

        # 2. Busca entre falantes anônimos da sessão
        session_name, session_score = self._match_session(embedding)
        if session_score >= DIARIZATION_SIMILARITY_THRESHOLD:
            # Refina o embedding do falante da sessão com média móvel
            self._update_session_speaker(session_name, embedding)
            return session_name

        # 3. Novo falante anônimo
        return self._register_session_speaker(embedding)

    def _match_known(self, embedding: np.ndarray) -> tuple[str, float]:
        """Retorna (nome, similaridade) do perfil conhecido mais próximo."""
        best_name  = ""
        best_score = -1.0
        for profile in self._profiles.values():
            score = cosine_similarity(embedding, profile.embedding)
            if score > best_score:
                best_score = score
                best_name  = profile.name
        return best_name, best_score

    def _match_session(self, embedding: np.ndarray) -> tuple[str, float]:
        """Retorna (rótulo, similaridade) do falante anônimo de sessão mais próximo."""
        best_label = ""
        best_score = -1.0
        for label, data in self._session_profiles.items():
            score = cosine_similarity(embedding, data["embedding"])
            if score > best_score:
                best_score = score
                best_label = label
        return best_label, best_score

    def _update_session_speaker(self, label: str, embedding: np.ndarray) -> None:
        """
        Atualiza o centroid do falante da sessão usando média ponderada.
        Isso torna o perfil mais robusto à medida que ouvimos mais áudio da pessoa.
        """
        if label not in self._session_profiles:
            return
        
        data = self._session_profiles[label]
        old_emb = data["embedding"]
        count = data["count"]
        
        # Média ponderada (limitamos o peso para não saturar em sessões longas)
        # Max count 50 para manter flexibilidade caso o ambiente mude
        new_count = min(count + 1, 50)
        
        # Novo embedding é a média entre o antigo e o novo
        # (old * count + new) / (count + 1)
        new_emb = (old_emb * count + embedding) / (count + 1)
        
        # Normaliza o embedding (essencial para cosine similarity)
        norm = np.linalg.norm(new_emb)
        if norm > 1e-8:
            new_emb = new_emb / norm
            
        data["embedding"] = new_emb
        data["count"] = new_count

    def _register_session_speaker(self, embedding: np.ndarray) -> str:
        """Cria um novo rótulo anônimo para a sessão atual."""
        if self._speaker_counter >= DIARIZATION_MAX_SPEAKERS:
            # Limite atingido — atribui ao mais similar disponível
            label, _ = self._match_session(embedding)
            return label or "Falante_?"

        self._speaker_counter += 1
        label = f"Falante_{self._speaker_counter}"
        self._session_profiles[label] = {
            "embedding": embedding,
            "count": 1
        }
        return label

    # ── Gestão de perfis ──────────────────────────────────────────────────────

    def save_profile(self, name: str, embedding: np.ndarray) -> str:
        """
        Salva um novo perfil de voz (ou atualiza se o nome já existir).

        Args:
            name:      Nome do falante (ex: "Márcio").
            embedding: Embedding de 256 dimensões.

        Returns:
            ID do perfil criado/atualizado.
        """
        # Verifica se já existe um perfil com esse nome
        existing = self._find_by_name(name)
        if existing:
            existing.embedding  = embedding
            existing.updated_at = datetime.now().isoformat()
            self._save()
            return existing.profile_id

        pid = str(uuid.uuid4())
        self._profiles[pid] = VoiceProfile(pid, name, embedding)
        self._save()
        return pid

    def delete_profile(self, name: str) -> bool:
        """
        Remove um perfil pelo nome.

        Returns:
            True se removido, False se não encontrado.
        """
        profile = self._find_by_name(name)
        if not profile:
            return False
        del self._profiles[profile.profile_id]
        self._save()
        return True

    def list_profiles(self) -> list[str]:
        """Retorna os nomes de todos os perfis conhecidos."""
        return [p.name for p in self._profiles.values()]

    def _find_by_name(self, name: str) -> VoiceProfile | None:
        for profile in self._profiles.values():
            if profile.name.lower() == name.lower():
                return profile
        return None

    def reset_session(self) -> None:
        """Limpa os falantes anônimos da sessão (chamado ao iniciar nova gravação)."""
        self._session_profiles = {}
        self._speaker_counter   = 0

    def promote_session_speaker(self, session_label: str, new_name: str) -> bool:
        """
        Promove um falante anônimo da sessão ("Falante_1") a um perfil permanente.
        Pega o embedding acumulado até agora e salva como um novo perfil de voz.

        Returns:
            True se promovido com sucesso.
        """
        if session_label not in self._session_profiles:
            return False
            
        embedding = self._session_profiles[session_label]["embedding"]
        self.save_profile(new_name, embedding)
        
        # Remove da sessão para não dar conflito (agora ele é um perfil conhecido)
        del self._session_profiles[session_label]
        return True
