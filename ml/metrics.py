"""Per-class precision/recall/F1, confusion matrix and markdown tables (no accuracy-only reporting, rubric D8)."""
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from ml.data import CATEGORIES


def per_class(y_true: list[str], y_pred: list[str]) -> dict:
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=CATEGORIES, zero_division=0)
    classes = {c: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])}
               for i, c in enumerate(CATEGORIES)}
    present = [c for c in CATEGORIES if classes[c]["support"] > 0]
    return {"classes": classes, "macro_f1": sum(classes[c]["f1"] for c in present) / len(present),
            "accuracy": sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true), "n": len(y_true),
            "confusion": confusion_matrix(y_true, y_pred, labels=CATEGORIES).tolist()}


def table(results: dict[str, dict]) -> str:
    """One row per class, precision/recall per method, plus support, macro-F1 and accuracy rows."""
    names = list(results)
    head = "| class | support | " + " | ".join(f"{n} P | {n} R" for n in names) + " |"
    lines = [head, "|" + "---|" * (2 + 2 * len(names))]
    first = results[names[0]]["classes"]
    for c in CATEGORIES:
        cells = " | ".join(f"{results[n]['classes'][c]['precision']:.2f} | {results[n]['classes'][c]['recall']:.2f}" for n in names)
        lines.append(f"| {c} | {first[c]['support']} | {cells} |")
    lines.append("| **macro-F1** | | " + " | ".join(f"{results[n]['macro_f1']:.3f} | " for n in names) + " |")
    lines.append("| **accuracy** | | " + " | ".join(f"{results[n]['accuracy']:.3f} | " for n in names) + " |")
    return "\n".join(lines)


def confusion_md(conf: list[list[int]]) -> str:
    short = [c[:8] for c in CATEGORIES]
    lines = ["| true \\ pred | " + " | ".join(short) + " |", "|" + "---|" * (len(CATEGORIES) + 1)]
    lines += [f"| {CATEGORIES[i]} | " + " | ".join(str(v) for v in row) + " |" for i, row in enumerate(conf)]
    return "\n".join(lines)
