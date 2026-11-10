from app.models import FormulaEntry


def build_latex_export(formulas: list[FormulaEntry]) -> str:
    """Nội dung .tex từ các công thức đã Submit. Chỉ dùng latex_final, không bao giờ latex_raw."""
    parts = ["% Math2Latex export - submitted formulas only"]
    for index, formula in enumerate(formulas, start=1):
        parts.append(f"\n% Page {formula.page_number} - formula {index}\n\\[\n{formula.latex_final or ''}\n\\]")
    return "\n".join(parts) + "\n"
