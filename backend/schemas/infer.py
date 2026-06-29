from pydantic import BaseModel


class TestPredictStartRequest(BaseModel):
    checkpoint: str
    input_jsonl: str
    output_dir: str
    output_filename: str = 'test_predictions.jsonl'
    batch_size: int = 4
    num_workers: int = 0
    verify_images: bool = True
    include_weak_labels: bool = False
    device: str = 'auto'
