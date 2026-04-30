"""Rhino 8 Python script: one-click arch-lw runner with Eto progress dialog.

Install:
  1. Save this file to:
       macOS: ~/Library/Application Support/McNeel/Rhinoceros/8.0/scripts/
       Win:   %APPDATA%\\McNeel\\Rhinoceros\\8.0\\scripts\\
  2. In Rhino: Tools > Toolbar Layout > pick a toolbar > Edit > New Button.
     Left mouse macro:
       _-RunPythonScript "/full/path/to/arch_lw_button.py"
     Tooltip: "Apply arch-lw hierarchy"
  3. Optional: assign a 24x24 PNG icon.

Docs:
  https://developer.rhino3d.com/guides/rhinopython/python-rhino8/
  https://developer.rhino3d.com/api/RhinoCommon/html/N_Eto_Forms.htm
"""
# r: rhinoscriptsyntax
import os
import shutil
import subprocess
import threading
from pathlib import Path

import Rhino
import Eto.Forms as forms
import Eto.Drawing as drawing

DEFAULT_SUB = "apply-jsx"  # or "poche"
TIMEOUT_SEC = 30 * 60


def _cli():
    exe = "arch-lw.exe" if os.name == "nt" else "arch-lw"
    return shutil.which(exe)


def _open_external(path):
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(["open", "-a", "Adobe Illustrator", path])


class ProgressDialog(forms.Dialog[bool]):
    def __init__(self, title="arch-lw running…"):
        self.Title = title
        self.ClientSize = drawing.Size(560, 340)
        self.Resizable = True
        self.Padding = drawing.Padding(8)
        self.log = forms.TextArea(ReadOnly=True, Wrap=False)
        self.log.Font = drawing.Fonts.Monospace(10)
        self.bar = forms.ProgressBar(Indeterminate=True)
        self.close_btn = forms.Button(Text="Close", Enabled=False)
        self.close_btn.Click += lambda s, e: self.Close(True)
        layout = forms.DynamicLayout()
        layout.AddRow(self.bar)
        layout.AddRow(self.log)
        layout.AddRow(None, self.close_btn)
        self.Content = layout

    def append(self, text):
        Rhino.RhinoApp.InvokeOnUiThread(
            lambda: setattr(self.log, "Text", self.log.Text + text)
        )

    def finish(self, ok):
        Rhino.RhinoApp.InvokeOnUiThread(lambda: setattr(self.bar, "Indeterminate", False))
        Rhino.RhinoApp.InvokeOnUiThread(lambda: setattr(self.bar, "Value", 100 if ok else 0))
        Rhino.RhinoApp.InvokeOnUiThread(lambda: setattr(self.close_btn, "Enabled", True))


def _pick_pdf():
    dlg = forms.OpenFileDialog()
    dlg.Title = "Select exported .ai / .pdf"
    dlg.Filters.Add(forms.FileFilter("Illustrator / PDF", ".ai", ".pdf"))
    if dlg.ShowDialog(Rhino.UI.RhinoEtoApp.MainWindow) == forms.DialogResult.Ok:
        return dlg.FileName
    return None


def _run_cli_streaming(cli, src, dlg):
    out_path = str(Path(src).with_name(Path(src).stem + " HIERARCHY" + Path(src).suffix))
    cmd = [cli, DEFAULT_SUB, src, "--out", out_path]
    dlg.append("$ " + " ".join(cmd) + "\n\n")
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in proc.stdout:
            dlg.append(line)
        proc.wait(timeout=TIMEOUT_SEC)
        ok = proc.returncode == 0
        dlg.append("\n[exit {}]\n".format(proc.returncode))
        dlg.finish(ok)
        if ok:
            _open_external(out_path)
    except subprocess.TimeoutExpired:
        proc.kill()
        dlg.append("\n[timeout > {}s]\n".format(TIMEOUT_SEC))
        dlg.finish(False)
    except Exception as e:
        dlg.append("\n[error] {}: {}\n".format(type(e).__name__, e))
        dlg.finish(False)


def main():
    cli = _cli()
    if not cli:
        forms.MessageBox.Show(
            "arch-lw is not on PATH.\nInstall it and reopen Rhino.",
            "arch-lw missing", forms.MessageBoxButtons.OK,
            forms.MessageBoxType.Error,
        )
        return
    src = _pick_pdf()
    if not src:
        return
    dlg = ProgressDialog()
    threading.Thread(target=_run_cli_streaming,
                     args=(cli, src, dlg), daemon=True).start()
    dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)


if __name__ == "__main__":
    main()
