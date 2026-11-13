"""
S5-02: Đo precision/recall của detector (Pix2Text MFD).
S5-03: Đo OCR accuracy (exact match, edit distance, BLEU).

Cách dùng (chạy trong container backend):
    docker compose exec backend python scripts/evaluate_metrics.py

Yêu cầu: có dữ liệu submitted (latex_final là đáp án chuẩn đã review thủ công).
Nếu chưa có submitted formulas, script in cảnh báo và thoát.
"""

import os
import sys
import json
from collections import defaultdict
from difflib import SequenceMatcher

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DB_URL", "postgresql://math2latex_user:math2latex_pass@db:5432/math2latex")


def connect():
    engine = create_engine(DB_URL)
    return engine.connect()


def get_submitted_formulas(conn):
    """Get all submitted formulas with both latex_raw and latex_final."""
    result = conn.execute(text("""
        SELECT f.id, f.document_id, f.page_number, f.status,
               f.latex_raw, f.latex_final, f.confidence,
               f.x_min, f.y_min, f.x_max, f.y_max,
               d.filename
        FROM formula_entries f
        JOIN documents d ON f.document_id = d.id
        WHERE f.status = 'submitted'
          AND f.latex_raw IS NOT NULL
          AND f.latex_final IS NOT NULL
        ORDER BY d.filename, f.page_number, f.y_min
    """))
    return [dict(row._mapping) for row in result]


def get_all_formulas_by_document(conn):
    """Get formula counts by document for detector stats."""
    result = conn.execute(text("""
        SELECT d.id AS document_id, d.filename, d.page_count,
               COUNT(f.id) AS detected_count,
               COUNT(CASE WHEN f.status = 'submitted' THEN 1 END) AS submitted_count
        FROM documents d
        LEFT JOIN formula_entries f ON d.id = f.document_id
        GROUP BY d.id
        ORDER BY d.filename
    """))
    return [dict(row._mapping) for row in result]


# ---------- OCR Metrics ----------

def normalize_latex(s):
    """Basic LaTeX normalization: strip whitespace, remove $ wrappers."""
    s = s.strip()
    if s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    # Normalize common whitespace patterns
    s = " ".join(s.split())
    return s


def exact_match(raw, final):
    return 1.0 if normalize_latex(raw) == normalize_latex(final) else 0.0


def edit_distance(raw, final):
    """Character-level edit distance (Levenshtein) between normalized strings."""
    a = normalize_latex(raw)
    b = normalize_latex(final)
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j], prev = min(dp[j] + 1, dp[j - 1] + 1, prev + cost), dp[j]
    return dp[m]


def edit_similarity(raw, final):
    """1 - (edit_distance / max_len), between 0 and 1."""
    a = normalize_latex(raw)
    b = normalize_latex(final)
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1.0 - edit_distance(raw, final) / max_len


def sequence_match_ratio(raw, final):
    """SequenceMatcher ratio (similar to BLEU-like overlap)."""
    return SequenceMatcher(None, normalize_latex(raw), normalize_latex(final)).ratio()


def compute_ocr_metrics(formulas):
    """Compute OCR metrics over a list of submitted formulas."""
    if not formulas:
        return None

    total = len(formulas)
    exact = sum(exact_match(f["latex_raw"], f["latex_final"]) for f in formulas)
    edit_sims = [edit_similarity(f["latex_raw"], f["latex_final"]) for f in formulas]
    seq_ratios = [sequence_match_ratio(f["latex_raw"], f["latex_final"]) for f in formulas]

    return {
        "total_formulas": total,
        "exact_match_count": int(exact),
        "exact_match_rate": round(exact / total, 4),
        "avg_edit_similarity": round(sum(edit_sims) / total, 4),
        "avg_sequence_ratio": round(sum(seq_ratios) / total, 4),
        "min_edit_similarity": round(min(edit_sims), 4),
        "max_edit_similarity": round(max(edit_sims), 4),
    }


def compute_per_document_metrics(formulas):
    """Group metrics by document."""
    by_doc = defaultdict(list)
    for f in formulas:
        by_doc[f["filename"]].append(f)

    results = {}
    for filename, doc_formulas in by_doc.items():
        results[filename] = compute_ocr_metrics(doc_formulas)
    return results


def print_ocr_errors(formulas, threshold=0.8, max_show=20):
    """Print formulas where OCR raw significantly differs from ground truth."""
    errors = []
    for f in formulas:
        sim = edit_similarity(f["latex_raw"], f["latex_final"])
        if sim < threshold:
            errors.append((sim, f))
    errors.sort(key=lambda x: x[0])

    if not errors:
        print(f"\n  Không có công thức nào có edit similarity < {threshold}")
        return

    print(f"\n  {len(errors)} công thức có edit similarity < {threshold} (hiện tối đa {max_show}):")
    for sim, f in errors[:max_show]:
        print(f"\n    [{f['filename']} trang {f['page_number']}] sim={sim:.2f}")
        print(f"      raw:   {f['latex_raw'][:120]}")
        print(f"      final: {f['latex_final'][:120]}")


def main():
    print("=" * 60)
    print("  Math2Latex — Đánh giá chất lượng (S5-02, S5-03)")
    print("=" * 60)

    conn = connect()

    # --- S5-02: Detector stats ---
    print("\n--- DETECTOR STATS (S5-02) ---\n")
    docs = get_all_formulas_by_document(conn)
    if not docs:
        print("  Không có document nào trong database.")
    else:
        print(f"  {'Filename':<50} {'Pages':>5} {'Detected':>8} {'Submitted':>9}")
        print("  " + "-" * 75)
        for d in docs:
            print(f"  {d['filename']:<50} {d['page_count'] or '-':>5} {d['detected_count']:>8} {d['submitted_count']:>9}")
        print()
        total_detected = sum(d["detected_count"] for d in docs)
        total_submitted = sum(d["submitted_count"] for d in docs)
        print(f"  Tổng: {len(docs)} document, {total_detected} vùng detected, {total_submitted} submitted")
        print()
        print("  LƯU Ý: Precision/Recall cần bbox ground truth thủ công (chưa có).")
        print("  Chỉ có thể đo tỉ lệ submitted/detected = proxy cho 'vùng hữu ích'.")
        if total_detected > 0:
            print(f"  Tỉ lệ submitted/detected: {total_submitted}/{total_detected} = {total_submitted/total_detected:.2%}")

    # --- S5-03: OCR metrics ---
    print("\n--- OCR METRICS (S5-03) ---\n")
    formulas = get_submitted_formulas(conn)
    if not formulas:
        print("  Chưa có công thức submitted (latex_raw + latex_final).")
        print("  Cần review thủ công và Submit để tạo ground truth.")
        conn.close()
        return

    overall = compute_ocr_metrics(formulas)
    print(f"  Tổng số công thức đánh giá: {overall['total_formulas']}")
    print(f"  Exact match:                {overall['exact_match_count']}/{overall['total_formulas']} ({overall['exact_match_rate']:.2%})")
    print(f"  Avg edit similarity:        {overall['avg_edit_similarity']:.4f}")
    print(f"  Avg sequence ratio:         {overall['avg_sequence_ratio']:.4f}")
    print(f"  Min/Max edit similarity:    {overall['min_edit_similarity']:.4f} / {overall['max_edit_similarity']:.4f}")

    per_doc = compute_per_document_metrics(formulas)
    if len(per_doc) > 1:
        print("\n  --- Per-document ---")
        for filename, metrics in per_doc.items():
            print(f"\n  {filename}:")
            print(f"    N={metrics['total_formulas']}, exact={metrics['exact_match_rate']:.2%}, "
                  f"edit_sim={metrics['avg_edit_similarity']:.4f}, seq_ratio={metrics['avg_sequence_ratio']:.4f}")

    # --- S5-05: Examples of OCR errors ---
    print("\n--- VÍ DỤ OCR SAI (S5-05) ---")
    print_ocr_errors(formulas)

    # Export results
    results = {
        "overall": overall,
        "per_document": per_doc,
        "detector_docs": [
            {"filename": d["filename"], "pages": d["page_count"],
             "detected": d["detected_count"], "submitted": d["submitted_count"]}
            for d in docs
        ],
    }
    output_path = os.path.join(os.path.dirname(__file__), "..", "evaluation_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  Kết quả đã lưu: {output_path}")

    conn.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

