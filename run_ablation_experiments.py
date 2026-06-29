import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


EXPERIMENTS = [
    {
        "name": "image_only",
        "data_setting": "image_only",
        "use_ranking_loss": False,
    },
    {
        "name": "image_caption",
        "data_setting": "image_caption",
        "use_ranking_loss": False,
    },
    {
        "name": "image_caption_context",
        "data_setting": "image_caption_context",
        "use_ranking_loss": False,
    },
    {
        "name": "full_raw",
        "data_setting": "full_raw",
        "use_ranking_loss": False,
    },
    {
        "name": "full",
        "data_setting": "full",
        "use_ranking_loss": False,
    },
    {
        "name": "full_rank_w005",
        "data_setting": "full",
        "use_ranking_loss": True,
        "ranking_weight": 0.05,
        "ranking_margin": 0.05,
        "ranking_min_diff": 0.05,
    },
    {
        "name": "full_rank_w010",
        "data_setting": "full",
        "use_ranking_loss": True,
        "ranking_weight": 0.10,
        "ranking_margin": 0.05,
        "ranking_min_diff": 0.05,
    },
]


def run_cmd(cmd, cwd=None):
    print("\n" + "=" * 100)
    print("Running command:")
    print(" ".join(map(str, cmd)))
    print("=" * 100)

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    for line in process.stdout:
        print(line, end="")

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed with return code {process.returncode}: {' '.join(map(str, cmd))}"
        )


def read_json(path):
    path = Path(path)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def flatten_summary(setting, summary_json):
    row = {
        "setting": setting,
    }

    if not summary_json:
        return row

    mae_values = []
    mse_values = []
    spearman_values = []

    target_dims = [
        "clarity",
        "relevance",
        "informativeness",
        "structure",
    ]

    for dim in target_dims:
        metrics = summary_json.get(dim)

        if not isinstance(metrics, dict):
            continue

        mae = metrics.get("mae")
        mse = metrics.get("mse")
        spearman = metrics.get("spearman")

        row[f"{dim}_mae"] = mae
        row[f"{dim}_mse"] = mse
        row[f"{dim}_spearman"] = spearman

        if mae is not None:
            try:
                mae_values.append(float(mae))
            except Exception:
                pass

        if mse is not None:
            try:
                mse_values.append(float(mse))
            except Exception:
                pass

        if spearman is not None:
            try:
                spearman_values.append(float(spearman))
            except Exception:
                pass

    row["macro_mae"] = (
        sum(mae_values) / len(mae_values)
        if mae_values
        else None
    )

    row["macro_mse"] = (
        sum(mse_values) / len(mse_values)
        if mse_values
        else None
    )

    row["macro_spearman"] = (
        sum(spearman_values) / len(spearman_values)
        if spearman_values
        else None
    )

    return row


def write_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = []

    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(row)

    print(f"\nSaved summary CSV to: {output_path}")


def get_exp_value(exp, args, name):
    return exp.get(name, getattr(args, name))


def train_one_setting(
    setting_name,
    train_jsonl,
    val_jsonl,
    output_dir,
    args,
    exp,
    use_ranking_loss=False,
):
    cmd = [
        sys.executable,
        "train.py",
        "--train_jsonl", str(train_jsonl),
        "--val_jsonl", str(val_jsonl),
        "--output_dir", str(output_dir),

        "--batch_size", str(get_exp_value(exp, args, "batch_size")),
        "--epochs", str(get_exp_value(exp, args, "epochs")),
        "--lr", str(get_exp_value(exp, args, "lr")),
        "--weight_decay", str(get_exp_value(exp, args, "weight_decay")),
        "--max_text_length", str(get_exp_value(exp, args, "max_text_length")),
        "--num_workers", str(get_exp_value(exp, args, "num_workers")),
        "--seed", str(get_exp_value(exp, args, "seed")),

        "--proj_dim", str(get_exp_value(exp, args, "proj_dim")),
        "--cube_tokens", str(get_exp_value(exp, args, "cube_tokens")),
        "--cube_depth", str(get_exp_value(exp, args, "cube_depth")),
        "--mixing_expansion", str(get_exp_value(exp, args, "mixing_expansion")),
        "--dropout", str(get_exp_value(exp, args, "dropout")),
        "--cross_attention_heads", str(get_exp_value(exp, args, "cross_attention_heads")),
        "--cross_attention_layers", str(get_exp_value(exp, args, "cross_attention_layers")),
    ]

    if args.freeze_text_encoder:
        cmd.append("--freeze_text_encoder")

    if args.freeze_image_encoder:
        cmd.append("--freeze_image_encoder")

    if args.use_bidirectional_cross_attention:
        cmd.append("--use_bidirectional_cross_attention")

    if args.include_weak_labels:
        cmd.append("--include_weak_labels")

    if args.verify_images:
        cmd.append("--verify_images")

    if use_ranking_loss:
        cmd.extend([
            "--use_ranking_loss",
            "--ranking_weight", str(get_exp_value(exp, args, "ranking_weight")),
            "--ranking_margin", str(get_exp_value(exp, args, "ranking_margin")),
            "--ranking_min_diff", str(get_exp_value(exp, args, "ranking_min_diff")),
        ])

    run_cmd(cmd)


def predict_one_setting(
    setting_name,
    input_jsonl,
    checkpoint,
    output_jsonl,
    args,
):
    predict_batch_size = args.eval_batch_size or args.batch_size

    cmd = [
        sys.executable,
        "predict.py",
        "--checkpoint", str(checkpoint),
        "--input_jsonl", str(input_jsonl),
        "--output_jsonl", str(output_jsonl),
        "--batch_size", str(predict_batch_size),
        "--num_workers", str(args.num_workers),
        "--device", args.device,
    ]

    if args.include_weak_labels:
        cmd.append("--include_weak_labels")

    if args.verify_images:
        cmd.append("--verify_images")

    run_cmd(cmd)


def analyze_one_setting(pred_jsonl, output_dir):
    cmd = [
        sys.executable,
        "analyze_predictions.py",
        "--pred_jsonl", str(pred_jsonl),
        "--output_dir", str(output_dir),
    ]

    run_cmd(cmd)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_dir",
        required=True,
        help="Original data dir containing train.jsonl, val.jsonl, test.jsonl",
    )

    parser.add_argument("--ablation_data_dir", default="data/ablation")
    parser.add_argument("--runs_dir", default="runs/ablation")

    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--eval_batch_size", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--max_text_length", type=int, default=256)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--proj_dim", type=int, default=256)
    parser.add_argument("--cube_tokens", type=int, default=4)
    parser.add_argument("--cube_depth", type=int, default=3)
    parser.add_argument("--mixing_expansion", type=float, default=2.0)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--cross_attention_heads", type=int, default=4)
    parser.add_argument("--cross_attention_layers", type=int, default=1)

    parser.add_argument("--freeze_text_encoder", action="store_true")
    parser.add_argument("--freeze_image_encoder", action="store_true")
    parser.add_argument("--use_bidirectional_cross_attention", action="store_true")

    parser.add_argument("--ranking_weight", type=float, default=0.05)
    parser.add_argument("--ranking_margin", type=float, default=0.05)
    parser.add_argument("--ranking_min_diff", type=float, default=0.05)

    parser.add_argument("--include_weak_labels", action="store_true")
    parser.add_argument("--verify_images", action="store_true")
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu", "mps"],
    )

    parser.add_argument("--skip_make_data", action="store_true")
    parser.add_argument("--skip_train", action="store_true")
    parser.add_argument("--skip_predict", action="store_true")
    parser.add_argument("--skip_analyze", action="store_true")

    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Only run selected experiments, e.g. --only full full_rank_w005",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    ablation_data_dir = Path(args.ablation_data_dir)
    runs_dir = Path(args.runs_dir)

    if not args.skip_make_data:
        run_cmd([
            sys.executable,
            "make_ablation_jsonl.py",
            "--input_dir", str(input_dir),
            "--output_dir", str(ablation_data_dir),
        ])

    experiments = EXPERIMENTS

    if args.only:
        allowed = set(args.only)
        experiments = [
            exp for exp in EXPERIMENTS
            if exp["name"] in allowed
        ]

        if not experiments:
            raise ValueError(
                f"No experiments matched --only {args.only}. "
                f"Available experiments: {[exp['name'] for exp in EXPERIMENTS]}"
            )

    summary_rows = []

    for exp in experiments:
        name = exp["name"]
        data_setting = exp["data_setting"]
        use_ranking_loss = exp["use_ranking_loss"]

        print("\n" + "#" * 100)
        print(f"Experiment: {name}")
        print(f"Data setting: {data_setting}")
        print(f"Use ranking loss: {use_ranking_loss}")

        if use_ranking_loss:
            print(f"Ranking weight: {get_exp_value(exp, args, 'ranking_weight')}")
            print(f"Ranking margin: {get_exp_value(exp, args, 'ranking_margin')}")
            print(f"Ranking min diff: {get_exp_value(exp, args, 'ranking_min_diff')}")

        print(f"Batch size: {get_exp_value(exp, args, 'batch_size')}")
        print(f"Learning rate: {get_exp_value(exp, args, 'lr')}")
        print(f"Max text length: {get_exp_value(exp, args, 'max_text_length')}")
        print("#" * 100)

        data_dir = ablation_data_dir / data_setting
        run_dir = runs_dir / name
        analysis_dir = run_dir / "analysis"

        train_jsonl = data_dir / "train.jsonl"
        val_jsonl = data_dir / "val.jsonl"
        test_jsonl = data_dir / "test.jsonl"

        checkpoint = run_dir / "best.pt"
        pred_jsonl = run_dir / "test_predictions.jsonl"

        if not train_jsonl.exists():
            raise FileNotFoundError(f"Missing train file: {train_jsonl}")

        if not val_jsonl.exists():
            raise FileNotFoundError(f"Missing val file: {val_jsonl}")

        if not test_jsonl.exists():
            raise FileNotFoundError(f"Missing test file: {test_jsonl}")

        if not args.skip_train:
            train_one_setting(
                setting_name=name,
                train_jsonl=train_jsonl,
                val_jsonl=val_jsonl,
                output_dir=run_dir,
                args=args,
                exp=exp,
                use_ranking_loss=use_ranking_loss,
            )

        if not checkpoint.exists():
            raise FileNotFoundError(f"Missing checkpoint: {checkpoint}")

        if not args.skip_predict:
            predict_one_setting(
                setting_name=name,
                input_jsonl=test_jsonl,
                checkpoint=checkpoint,
                output_jsonl=pred_jsonl,
                args=args,
            )

        if not pred_jsonl.exists():
            raise FileNotFoundError(f"Missing prediction file: {pred_jsonl}")

        if not args.skip_analyze:
            analyze_one_setting(
                pred_jsonl=pred_jsonl,
                output_dir=analysis_dir,
            )

        summary_json = read_json(analysis_dir / "summary.json")

        row = flatten_summary(name, summary_json)
        row["data_setting"] = data_setting
        row["use_ranking_loss"] = use_ranking_loss
        row["ranking_weight"] = (
            get_exp_value(exp, args, "ranking_weight")
            if use_ranking_loss
            else 0.0
        )
        row["ranking_margin"] = (
            get_exp_value(exp, args, "ranking_margin")
            if use_ranking_loss
            else 0.0
        )
        row["ranking_min_diff"] = (
            get_exp_value(exp, args, "ranking_min_diff")
            if use_ranking_loss
            else 0.0
        )
        row["batch_size"] = get_exp_value(exp, args, "batch_size")
        row["lr"] = get_exp_value(exp, args, "lr")
        row["max_text_length"] = get_exp_value(exp, args, "max_text_length")
        row["checkpoint"] = str(checkpoint)
        row["prediction_file"] = str(pred_jsonl)

        summary_rows.append(row)

    write_csv(summary_rows, runs_dir / "ablation_summary.csv")

    print("\nAll ablation experiments finished.")
    print(f"Summary: {runs_dir / 'ablation_summary.csv'}")


if __name__ == "__main__":
    main()