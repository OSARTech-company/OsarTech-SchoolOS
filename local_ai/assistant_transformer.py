import json
import os
from collections import Counter

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
except Exception:
    torch = None
    nn = None
    optim = None
    DataLoader = None
    Dataset = object


def torch_ready():
    return torch is not None and nn is not None and optim is not None

_NN_MODULE_BASE = nn.Module if nn is not None else object


def _normalize(text):
    value = str(text or '').strip().lower()
    out = []
    prev_space = False
    for ch in value:
        if ('a' <= ch <= 'z') or ('0' <= ch <= '9'):
            out.append(ch)
            prev_space = False
        else:
            if not prev_space:
                out.append(' ')
            prev_space = True
    return ' '.join(''.join(out).split())


def _tokens(role, source_page, text):
    base = _normalize(text)
    role_tok = f"role_{_normalize(role).replace(' ', '_')}" or "role_unknown"
    page_tok = _normalize(source_page).replace('/', '_').replace(' ', '_')
    if not page_tok:
        page_tok = "page_any"
    else:
        page_tok = f"page_{page_tok}"
    rows = [role_tok, page_tok]
    rows.extend(base.split())
    return rows


def build_vocab(samples, max_size=12000, min_freq=1):
    counter = Counter()
    for s in (samples or []):
        toks = _tokens(s.get('role', ''), s.get('source_page', ''), s.get('text', ''))
        counter.update(toks)
    vocab = {"<pad>": 0, "<unk>": 1}
    for token, freq in counter.most_common():
        if len(vocab) >= max_size:
            break
        if int(freq) < int(min_freq):
            continue
        if token not in vocab:
            vocab[token] = len(vocab)
    return vocab


def encode_sample(sample, vocab, max_len=64):
    toks = _tokens(sample.get('role', ''), sample.get('source_page', ''), sample.get('text', ''))
    ids = [vocab.get(t, 1) for t in toks][:max_len]
    if len(ids) < max_len:
        ids += [0] * (max_len - len(ids))
    mask = [1 if x != 0 else 0 for x in ids]
    return ids, mask


class AssistantDataset(Dataset):
    def __init__(self, samples, vocab, label_to_idx, max_len=64):
        self.samples = list(samples or [])
        self.vocab = vocab
        self.label_to_idx = label_to_idx
        self.max_len = max_len

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        row = self.samples[idx]
        ids, mask = encode_sample(row, self.vocab, max_len=self.max_len)
        label_idx = self.label_to_idx[row.get('label')]
        return (
            torch.tensor(ids, dtype=torch.long),
            torch.tensor(mask, dtype=torch.float32),
            torch.tensor(label_idx, dtype=torch.long),
        )


class TinyTransformerClassifier(_NN_MODULE_BASE):
    def __init__(self, vocab_size, num_labels, d_model=96, nhead=4, num_layers=2, ff_dim=192, max_len=64, dropout=0.12):
        if not torch_ready():
            raise RuntimeError('PyTorch is not installed.')
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model, padding_idx=0)
        self.position = nn.Embedding(max_len, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True,
            activation='gelu',
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(d_model, num_labels)

    def forward(self, input_ids, attention_mask):
        bsz, seq_len = input_ids.shape
        pos = torch.arange(seq_len, device=input_ids.device).unsqueeze(0).expand(bsz, seq_len)
        x = self.embedding(input_ids) + self.position(pos)
        src_key_padding_mask = (attention_mask == 0)
        x = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        mask = attention_mask.unsqueeze(-1)
        pooled = (x * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1.0)
        logits = self.classifier(self.dropout(pooled))
        return logits


def train_transformer(
    samples,
    artifact_dir,
    epochs=12,
    batch_size=32,
    lr=1.5e-3,
    max_len=64,
    d_model=96,
    nhead=2,
    num_layers=1,
    ff_dim=128,
):
    if not torch_ready():
        raise RuntimeError("PyTorch is not installed. Install torch locally to train the transformer.")
    rows = [s for s in (samples or []) if s.get('text') and s.get('label')]
    if len(rows) < 30:
        raise RuntimeError("Not enough training samples. Add more assistant examples first.")

    labels = sorted({str(s.get('label')) for s in rows})
    label_to_idx = {lb: i for i, lb in enumerate(labels)}
    idx_to_label = {i: lb for lb, i in label_to_idx.items()}
    vocab = build_vocab(rows, max_size=12000, min_freq=1)

    ds = AssistantDataset(rows, vocab=vocab, label_to_idx=label_to_idx, max_len=max_len)
    dl = DataLoader(ds, batch_size=max(8, int(batch_size)), shuffle=True)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = TinyTransformerClassifier(
        vocab_size=len(vocab),
        num_labels=len(labels),
        d_model=int(d_model),
        nhead=max(1, int(nhead)),
        num_layers=max(1, int(num_layers)),
        ff_dim=max(64, int(ff_dim)),
        max_len=int(max_len),
    ).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=float(lr))

    model.train()
    for _ in range(max(1, int(epochs))):
        for input_ids, masks, y in dl:
            input_ids = input_ids.to(device)
            masks = masks.to(device)
            y = y.to(device)
            optimizer.zero_grad()
            logits = model(input_ids, masks)
            loss = criterion(logits, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

    # Build response mapping per label for runtime output.
    label_meta = {}
    for s in rows:
        lb = str(s.get('label'))
        if lb in label_meta:
            continue
        label_meta[lb] = {
            "role": str(s.get('role') or '').strip(),
            "source_page": str(s.get('source_page') or '').strip(),
            "answer": str(s.get('answer') or '').strip(),
            "steps": [str(x).strip() for x in (s.get('steps') or []) if str(x).strip()][:6],
        }

    os.makedirs(artifact_dir, exist_ok=True)
    model_path = os.path.join(artifact_dir, 'assistant_transformer.pt')
    meta_path = os.path.join(artifact_dir, 'assistant_transformer_meta.json')

    torch.save({
        "state_dict": model.state_dict(),
        "config": {
            "vocab_size": len(vocab),
            "num_labels": len(labels),
            "d_model": int(d_model),
            "nhead": max(1, int(nhead)),
            "num_layers": max(1, int(num_layers)),
            "ff_dim": max(64, int(ff_dim)),
            "max_len": int(max_len),
        },
    }, model_path)
    with open(meta_path, 'w', encoding='utf-8') as fh:
        json.dump({
            "vocab": vocab,
            "label_to_idx": label_to_idx,
            "idx_to_label": {str(k): v for k, v in idx_to_label.items()},
            "label_meta": label_meta,
            "trained_samples": len(rows),
        }, fh, ensure_ascii=False)

    return {
        "model_path": model_path,
        "meta_path": meta_path,
        "trained_samples": len(rows),
        "labels": len(labels),
        "vocab_size": len(vocab),
        "device": str(device),
    }


def load_transformer(artifact_dir, device=None):
    if not torch_ready():
        raise RuntimeError("PyTorch is not installed.")
    model_path = os.path.join(artifact_dir, 'assistant_transformer.pt')
    meta_path = os.path.join(artifact_dir, 'assistant_transformer_meta.json')
    if not (os.path.exists(model_path) and os.path.exists(meta_path)):
        raise RuntimeError("Transformer artifacts not found. Train first.")
    with open(meta_path, 'r', encoding='utf-8') as fh:
        meta = json.load(fh)
    ckpt = torch.load(model_path, map_location='cpu')
    cfg = ckpt.get("config") or {}
    model = TinyTransformerClassifier(
        vocab_size=int(cfg.get("vocab_size", 2)),
        num_labels=int(cfg.get("num_labels", 2)),
        d_model=int(cfg.get("d_model", 96)),
        nhead=int(cfg.get("nhead", 4)),
        num_layers=int(cfg.get("num_layers", 2)),
        ff_dim=int(cfg.get("ff_dim", 192)),
        max_len=int(cfg.get("max_len", 64)),
    )
    model.load_state_dict(ckpt.get("state_dict") or {})
    dev = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
    model = model.to(dev)
    model.eval()
    return model, meta, dev


def predict_transformer(model, meta, device, role, question, source_page='', top_k=3):
    vocab = meta.get("vocab") or {}
    idx_to_label = {int(k): v for k, v in (meta.get("idx_to_label") or {}).items()}
    label_meta = meta.get("label_meta") or {}
    max_len = int(((model.position.num_embeddings) if hasattr(model, 'position') else 64))
    sample = {"role": role, "source_page": source_page, "text": question}
    ids, mask = encode_sample(sample, vocab=vocab, max_len=max_len)
    with torch.no_grad():
        x_ids = torch.tensor([ids], dtype=torch.long, device=device)
        x_mask = torch.tensor([mask], dtype=torch.float32, device=device)
        logits = model(x_ids, x_mask)
        probs = torch.softmax(logits, dim=-1).squeeze(0)
        k = max(1, min(int(top_k), int(probs.shape[0])))
        vals, inds = torch.topk(probs, k=k)
    out = []
    for prob, idx in zip(vals.tolist(), inds.tolist()):
        label = idx_to_label.get(int(idx), '')
        meta_row = label_meta.get(label) or {}
        out.append({
            "label": label,
            "confidence": float(prob),
            "role": str(meta_row.get("role") or ''),
            "source_page": str(meta_row.get("source_page") or ''),
            "answer": str(meta_row.get("answer") or ''),
            "steps": [str(s).strip() for s in (meta_row.get("steps") or []) if str(s).strip()][:6],
        })
    return out
