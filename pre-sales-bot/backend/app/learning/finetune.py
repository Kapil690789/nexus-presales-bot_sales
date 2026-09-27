from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from backend.app.core.platform import get_platform
from backend.app.core.settings import ROOT
from backend.app.learning.pairs import positive_pairs
from backend.app.rag.embeddings import BASE_MODEL, embedding_backend
from backend.app.rag.ingest import ingest_tenant
from backend.app.tenants.loader import TenantNotFound, ensure_tenant_row


def finetune_tenant(db: Session, slug: str) -> dict:
    platform = get_platform()
    try:
        tenant = ensure_tenant_row(db, slug)
    except TenantNotFound:
        return {"ok": False, "reason": "unknown_tenant", "tenant": slug}
    pairs = positive_pairs(db, tenant.id)
    required = platform.finetune_min_positives
    if len(pairs) < required:
        return {
            "ok": False,
            "reason": "not_enough_pairs",
            "tenant": slug,
            "positives": len(pairs),
            "required": required,
        }
    if embedding_backend() == "hash":
        return {
            "ok": False,
            "reason": "hash_embedder_cannot_finetune",
            "tenant": slug,
            "positives": len(pairs),
            "required": required,
        }
    out_dir = ROOT / "models" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    base = tenant.embedding_model if tenant.embedding_model.startswith("finetuned:") else ""
    source = str(ROOT / "models" / slug) if base and (ROOT / "models" / slug).is_dir() else BASE_MODEL
    _train(pairs, source, out_dir)
    tenant.embedding_model = f"finetuned:{slug}"
    db.commit()
    ingest_tenant(db, tenant)
    return {"ok": True, "tenant": slug, "model": tenant.embedding_model, "positives": len(pairs)}


def _train(pairs: list[tuple[str, str]], source: str, out_dir) -> None:
    from datasets import Dataset
    from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer, SentenceTransformerTrainingArguments
    from sentence_transformers.losses import MultipleNegativesRankingLoss

    model = SentenceTransformer(source)
    dataset = Dataset.from_dict({"anchor": [item[0] for item in pairs], "positive": [item[1] for item in pairs]})
    loss = MultipleNegativesRankingLoss(model)
    args = SentenceTransformerTrainingArguments(
        output_dir=str(out_dir),
        num_train_epochs=1,
        per_device_train_batch_size=min(8, max(2, len(pairs))),
        learning_rate=2e-5,
        warmup_ratio=0.1,
        save_strategy="no",
        logging_steps=10,
    )
    trainer = SentenceTransformerTrainer(model=model, args=args, train_dataset=dataset, loss=loss)
    trainer.train()
    model.save(str(out_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune a tenant embedding model on saved query-chunk pairs.")
    parser.add_argument("--tenant", required=True)
    args = parser.parse_args()
    from backend.app.models.db import SessionLocal, init_db

    init_db()
    with SessionLocal() as db:
        print(finetune_tenant(db, args.tenant))


if __name__ == "__main__":
    main()
