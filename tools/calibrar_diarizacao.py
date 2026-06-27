"""
tools/calibrar_diarizacao.py — Mede/calibra a diarização com áudio real.

A diarização usa o resemblyzer (embeddings de voz) e um threshold de
similaridade (`DIARIZATION_SIMILARITY_THRESHOLD` em config.py). Threshold alto
demais super-segmenta (1 pessoa vira vários "Falante_N"); baixo demais funde
pessoas diferentes. Este script mede onde está o ponto certo para o SEU áudio.

Uso:
    # Mede super-segmentação (grave UMA pessoa; ideal = 1 falante):
    python tools/calibrar_diarizacao.py uma_pessoa.wav

    # Mede separação entre DUAS pessoas (intra vs inter):
    python tools/calibrar_diarizacao.py pessoa_A.wav pessoa_B.wav

Dica: grave ~30–60s de fala por pessoa, WAV mono. Você pode capturar direto do
app (ele salva .txt, não áudio — então use um gravador simples, ou o Gravador
de Voz do Windows) e exportar como WAV.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
from resemblyzer import preprocess_wav
from silero_vad import load_silero_vad, get_speech_timestamps
from diarization.embedder import extract_embedding, cosine_similarity
import config

SR = 16_000
THRESHOLDS = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]


def embs_of(path: str, vad, min_sec: float = 0.8) -> list[np.ndarray]:
    wav = preprocess_wav(Path(path))
    ts = get_speech_timestamps(torch.from_numpy(wav), vad, sampling_rate=SR)
    out = []
    for t in ts:
        seg = wav[t["start"]:t["end"]]
        if len(seg) >= int(min_sec * SR):
            e = extract_embedding(seg.astype(np.float32))
            if e is not None:
                out.append(e)
    return out


def pair_sims(a, b=None) -> np.ndarray:
    if b is None:
        return np.array([
            cosine_similarity(a[i], a[j])
            for i in range(len(a)) for j in range(i + 1, len(a))
        ])
    return np.array([cosine_similarity(x, y) for x in a for y in b])


def greedy_clusters(embs, thresh: float) -> int:
    """Replica a lógica greedy do ProfileManager (centroid + média móvel)."""
    cents: list[list] = []
    for e in embs:
        bi, bs = -1, -1.0
        for i, (c, _) in enumerate(cents):
            s = cosine_similarity(e, c)
            if s > bs:
                bs, bi = s, i
        if bs >= thresh:
            c, n = cents[bi]
            nc = (c * n + e) / (n + 1)
            nn = np.linalg.norm(nc)
            cents[bi] = [nc / nn if nn > 1e-8 else nc, min(n + 1, 50)]
        else:
            cents.append([e, 1])
    return len(cents)


def mode_one(path: str, vad) -> None:
    print(f"[modo 1 pessoa] {path}")
    embs = embs_of(path, vad)
    print(f"trechos de fala (>=0.8s): {len(embs)}")
    if len(embs) < 2:
        print("Áudio muito curto para calibrar.")
        return
    sims = pair_sims(embs)
    print(
        f"similaridade da MESMA pessoa: media={sims.mean():.3f} "
        f"p10={np.percentile(sims,10):.3f} min={sims.min():.3f}"
    )
    print(f"threshold atual no config: {config.DIARIZATION_SIMILARITY_THRESHOLD}")
    print("threshold -> nº de falantes (ideal = 1):")
    for th in THRESHOLDS:
        print(f"  {th:.2f} -> {greedy_clusters(embs, th)}")


def mode_two(pa: str, pb: str, vad) -> None:
    print(f"[modo 2 pessoas] A={pa}  B={pb}")
    A, B = embs_of(pa, vad), embs_of(pb, vad)
    print(f"trechos: A={len(A)} B={len(B)}")
    if len(A) < 2 or len(B) < 2:
        print("Áudio muito curto para calibrar.")
        return
    intra = np.concatenate([pair_sims(A), pair_sims(B)])
    inter = pair_sims(A, B)
    print(f"INTRA (mesma pessoa): media={intra.mean():.3f} p10={np.percentile(intra,10):.3f} min={intra.min():.3f}")
    print(f"INTER (pessoas dif.): media={inter.mean():.3f} p90={np.percentile(inter,90):.3f} max={inter.max():.3f}")
    print(f"threshold atual no config: {config.DIARIZATION_SIMILARITY_THRESHOLD}")
    print("threshold -> mantem 'mesma pessoa' junta | funde 'pessoas diferentes':")
    for th in THRESHOLDS:
        print(f"  {th:.2f} -> {(intra >= th).mean()*100:5.1f}% | {(inter >= th).mean()*100:5.1f}%")


def main() -> None:
    args = sys.argv[1:]
    if len(args) not in (1, 2):
        print(__doc__)
        sys.exit(1)
    vad = load_silero_vad()
    if len(args) == 1:
        mode_one(args[0], vad)
    else:
        mode_two(args[0], args[1], vad)


if __name__ == "__main__":
    main()
