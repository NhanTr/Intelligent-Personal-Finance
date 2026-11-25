"""Builds the thin Google Colab notebook (.ipynb) and companion source bundle (.zip)."""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile
import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


def _create_colab_notebook() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            "# Intelligent Personal Finance DSS — Pipeline Huấn luyện & Đánh giá Học máy (Nhân — N1–N4)\n\n"
            "Notebook **mỏng (thin wrapper)** gọi trực tiếp package chuẩn `finance_ml` để đảm bảo **không lệch đặc trưng (zero train-serving skew)** "
            "và **khớp phiên bản thư viện** với FastAPI backend của Khoa."
        ),
        new_code_cell(
            "# Cell 1: Mount Google Drive, giải nén mã nguồn finance_ml & khóa phiên bản thư viện\n"
            "import os, shutil, subprocess, sys, zipfile\n"
            "from pathlib import Path\n\n"
            "IN_COLAB = 'google.colab' in sys.modules\n"
            "if IN_COLAB:\n"
            "    from google.colab import drive\n"
            "    drive.mount('/content/drive')\n"
            "    DRIVE_DIR = Path('/content/drive/MyDrive/PTHTTM_Nhan_ML_Colab')\n"
            "    WORK_DIR = Path('/content/finance_ml_work')\n"
            "    if WORK_DIR.exists():\n"
            "        shutil.rmtree(WORK_DIR)\n"
            "    WORK_DIR.mkdir(parents=True, exist_ok=True)\n"
            "    with zipfile.ZipFile(DRIVE_DIR / 'finance_ml_colab_package.zip') as zf:\n"
            "        zf.extractall(WORK_DIR)\n"
            "    os.chdir(WORK_DIR)\n"
            "    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '-r', 'requirements-ml.txt'])\n"
            "    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '-e', '.'])\n"
            "else:\n"
            "    DRIVE_DIR = Path('./artifacts/colab_drive_preview')\n"
            "    DRIVE_DIR.mkdir(parents=True, exist_ok=True)\n\n"
            "import numpy as np, pandas as pd, sklearn\n"
            "gpu_check = subprocess.run(['nvidia-smi', '-L'], capture_output=True, text=True)\n"
            "print('GPU Runtime:', gpu_check.stdout.strip() if gpu_check.returncode == 0 else 'CPU Runtime (Lưu ý: các thuật toán scikit-learn thực thi trên CPU)')\n"
            "print(f'Pinned versions -> Python {sys.version.split()[0]}, scikit-learn {sklearn.__version__}, pandas {pd.__version__}, numpy {np.__version__}')"
        ),
        new_code_cell(
            "# Cell 2: Sinh dữ liệu mô phỏng VND (seed=42) & hiển thị biểu đồ EDA\n"
            "import subprocess, sys\n"
            "from IPython.display import Image, Markdown, display\n\n"
            "subprocess.check_call([sys.executable, 'scripts/generate_data.py'])\n"
            "# Nếu bạn đặt thêm daily_household_transactions.csv trên Drive, tự động copy vào data/raw/\n"
            "kaggle_on_drive = DRIVE_DIR / 'daily_household_transactions.csv'\n"
            "if kaggle_on_drive.exists():\n"
            "    Path('data/raw').mkdir(parents=True, exist_ok=True)\n"
            "    shutil.copy2(kaggle_on_drive, Path('data/raw/daily_household_transactions.csv'))\n"
            "subprocess.check_call([sys.executable, 'scripts/prepare_public_data.py'])\n"
            "subprocess.check_call([sys.executable, 'scripts/run_eda.py', '--dataset', 'synthetic'])\n\n"
            "for fig_name in ['daily_spending_trend.png', 'category_share.png', 'amount_log_distribution.png']:\n"
            "    display(Image(filename=f'artifacts/synthetic/figures/{fig_name}'))"
        ),
        new_code_cell(
            "# Cell 3: Huấn luyện mô hình F3 (Baseline, LinearRegression, RandomForestRegressor) & Đánh giá Validation + Rolling CV\n"
            "import json, subprocess, sys\n"
            "from IPython.display import Image, display\n\n"
            "subprocess.check_call([sys.executable, 'scripts/train.py', '--dataset', 'synthetic', '--version', 'v1.0.0'])\n"
            "subprocess.check_call([sys.executable, 'scripts/evaluate.py', '--dataset', 'synthetic'])\n\n"
            "val_metrics = json.loads(Path('artifacts/synthetic/metrics/validation_metrics.json').read_text(encoding='utf-8'))\n"
            "print('Selected F3 Model on Validation:', val_metrics['selected_forecast_model'])\n"
            "display(pd.DataFrame(val_metrics['forecast_validation']).T[['mae_vnd', 'rmse_vnd', 'n_samples', 'improvement_vs_baseline_pct', 'meets_10pct_target']])\n"
            "display(Image(filename='artifacts/synthetic/figures/forecast_val_comparison.png'))"
        ),
        new_code_cell(
            "# Cell 4: Kết quả F4 (Isolation Forest), Lý do cảnh báo tiếng Việt & Benchmark chèn bất thường mô phỏng\n"
            "import json\n"
            "from IPython.display import Image, display\n\n"
            "print('F4 Validation Alert Summary:', json.dumps(val_metrics['anomaly_validation'], indent=2, ensure_ascii=False))\n"
            "inj = json.loads(Path('artifacts/synthetic/metrics/synthetic_anomaly_eval.json').read_text(encoding='utf-8'))\n"
            "print('Synthetic Injection Benchmark (tách riêng):', json.dumps(inj, indent=2, ensure_ascii=False))\n"
            "display(Image(filename='artifacts/synthetic/figures/anomaly_score_distribution.png'))\n\n"
            "review_df = pd.read_csv('artifacts/synthetic/anomaly_manual_review_validation.csv')\n"
            "display(review_df.head(10))"
        ),
        new_code_cell(
            "# Cell 5: Xuất Bundle mô hình (.joblib + metadata.json), Báo cáo & CSV rà soát về Google Drive\n"
            "# Lưu ý: Tập TEST vẫn được GIỮ KHÓA theo quy tắc 2A để bảo toàn tính độc lập.\n"
            "out_drive = DRIVE_DIR / 'outputs'\n"
            "out_drive.mkdir(parents=True, exist_ok=True)\n"
            "shutil.copytree('artifacts/synthetic', out_drive / 'synthetic', dirs_exist_ok=True)\n"
            "shutil.copy2('docs/eda_report.md', out_drive / 'eda_report.md')\n"
            "shutil.copy2('docs/model_card.md', out_drive / 'model_card.md')\n"
            "print('Đã lưu toàn bộ model bundle, biểu đồ và báo cáo sang:', out_drive)\n\n"
            "# CHỈ BỎ COMMENT DÒNG DƯỚI ĐÂY ĐÚNG 1 LẦN KHI ĐÃ CHỐT CẤU HÌNH CUỐI CÙNG VỚI KHOA (NGÀY 14):\n"
            "# subprocess.check_call([sys.executable, 'scripts/evaluate.py', '--dataset', 'synthetic', '--unlock-test', '--reason', 'One-shot final test evaluation'])"
        ),
        new_code_cell(
            "# Cell 6 (Demo): Kiểm tra trực tiếp 1 giao dịch cụ thể (giống luồng UI nhấp vào giao dịch -> FastAPI gọi detect_anomalies)\n"
            "import json\n"
            "from datetime import date\n"
            "from finance_ml.inference.loader import ModelBundleLoader\n"
            "from finance_ml.inference.predictor import detect_anomalies, predict_next_7d\n\n"
            "bundle = ModelBundleLoader(Path('artifacts/models/active.json')).load()\n"
            "tx_df = pd.read_csv('data/processed/synthetic/transactions.csv')\n\n"
            "# Thử thêm 1 giao dịch đột biến 9.5 triệu VND ở danh mục shopping cho user_001 để xem model chấm điểm & giải thích\n"
            "test_tx = pd.DataFrame([{\n"
            "    'transaction_id': 'demo_check_001',\n"
            "    'user_id': 'user_001',\n"
            "    'timestamp': '2026-09-15T21:30:00+07:00',\n"
            "    'type': 'expense',\n"
            "    'amount_vnd': 9500000.0,\n"
            "    'category': 'shopping',\n"
            "    'is_internal_transfer': False,\n"
            "    'note': 'Thử kiểm tra giao dịch bất thường'\n"
            "}])\n"
            "combined = pd.concat([tx_df, test_tx], ignore_index=True)\n\n"
            "res_f4 = detect_anomalies(combined, user_id='user_001', bundle=bundle, target_transaction_ids=['demo_check_001'])\n"
            "print('=== KẾT QUẢ KIỂM TRA 1 GIAO DỊCH (F4) ===')\n"
            "print(json.dumps(res_f4.model_dump(mode='json'), indent=2, ensure_ascii=False))\n\n"
            "res_f3 = predict_next_7d(tx_df, user_id='user_001', as_of_date=date(2026, 9, 15), bundle=bundle)\n"
            "print('\\n=== KẾT QUẢ DỰ BÁO 7 NGÀY TỚI (F3) ===')\n"
            "print(json.dumps(res_f3.model_dump(mode='json'), indent=2, ensure_ascii=False))"
        ),
    ]

    nb = new_notebook(
        cells=cells,
        metadata={
            "colab": {"name": "finance_ml_colab.ipynb", "provenance": [], "gpuType": "T4"},
            "accelerator": "GPU",
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
    )
    nbformat.validate(nb)
    return nb


def build_colab_artifacts(
    notebook_path: Path = Path("notebooks/finance_ml_colab.ipynb"),
    zip_path: Path = Path("artifacts/colab/finance_ml_colab_package.zip"),
    root_dir: Path = Path("."),
) -> None:
    notebook_path = Path(notebook_path)
    zip_path = Path(zip_path)
    root_dir = Path(root_dir)

    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    nb = _create_colab_notebook()
    nbformat.write(nb, notebook_path)

    include_files: list[Path] = [
        root_dir / "pyproject.toml",
        root_dir / "requirements-ml.txt",
        root_dir / "README.md",
    ]
    for folder in ("configs", "src", "scripts", "contracts"):
        base = root_dir / folder
        if base.exists():
            for p in sorted(base.rglob("*")):
                if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc"):
                    include_files.append(p)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in include_files:
            if file_path.exists():
                zf.write(file_path, arcname=str(file_path.relative_to(root_dir)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build thin Google Colab notebook and source zip package.")
    parser.add_argument("--notebook", type=Path, default=Path("notebooks/finance_ml_colab.ipynb"))
    parser.add_argument("--zip", type=Path, default=Path("artifacts/colab/finance_ml_colab_package.zip"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    build_colab_artifacts(args.notebook, args.zip, args.root)
    print(f"Created Colab notebook: {args.notebook}")
    print(f"Created Colab package:  {args.zip}")


if __name__ == "__main__":
    main()
