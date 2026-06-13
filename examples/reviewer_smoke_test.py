"""Throwaway smoke-test for the Claude PR-review action. Safe to delete; do not merge."""
import os


def build_report_path(folder, drawing_name):
    return os.path.join(folder, "{}_weights.txt".format(drawing_name))


def scale_line_weight(weight, factor):
    result = weight * factor
    return result
