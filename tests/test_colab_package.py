import zipfile
from pathlib import Path
import nbformat
from scripts.build_colab_notebook import build_colab_artifacts


def test_build_colab_artifacts_creates_valid_thin_notebook_and_complete_zip(tmp_path: Path):
    nb_path = tmp_path / "finance_ml_colab.ipynb"
    zip_path = tmp_path / "finance_ml_colab_package.zip"
    build_colab_artifacts(nb_path, zip_path)

    nb = nbformat.read(nb_path, as_version=4)
    nbformat.validate(nb)
    full_source = "\n".join(c.source for c in nb.cells if c.cell_type == "code")
    assert "finance_ml" in full_source
    assert "requirements-ml.txt" in full_source
    assert "--unlock-test" not in "\n".join(
        line for line in full_source.splitlines() if not line.strip().startswith("#")
    )

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "pyproject.toml" in names
        assert "requirements-ml.txt" in names
        assert "configs/default.yaml" in names
        assert any(n.startswith("src/finance_ml/") for n in names)
