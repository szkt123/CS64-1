from pydantic import BaseModel


class TrainStartRequest(BaseModel):
    train_jsonl: str
    val_jsonl: str
    output_dir: str
    batch_size: int = 4
    epochs: int = 5
    lr: float = 2e-5
    weight_decay: float = 1e-4
    dropout: float = 0.1
    proj_dim: int = 256
    cube_tokens: int = 4
    cube_depth: int = 3
    mixing_expansion: float = 2.0
    max_text_length: int = 256
    text_model_name: str = 'allenai/scibert_scivocab_uncased'
    image_model_name: str = 'openai/clip-vit-base-patch32'
    seed: int = 42
    verify_images: bool = True
    include_weak_labels: bool = False
    use_ranking_loss: bool = True
    ranking_weight: float = 0.2
    freeze_text_encoder: bool = False
    freeze_image_encoder: bool = False
    save_every_epoch: bool = False
    num_workers: int = 0
    log_every: int = 10
    emit_every: int = 1
    cross_attention_heads: int = 4
    cross_attention_layers: int = 1
    use_bidirectional_cross_attention: bool = False


TrainRequest = TrainStartRequest
