"""Run both mask paths plus interruption, data-integrity and missing-source regression checks."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from background import verify


HERE = Path(__file__).parent.resolve()


def invoke(job, out, *options, success=True):
    run = subprocess.run([sys.executable,str(HERE / "run.py"),str(job),str(out),*options],
                         env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},capture_output=True,text=True)
    if (run.returncode == 0) != success:
        raise AssertionError(run.stdout+run.stderr)
    return run.stdout+run.stderr


with tempfile.TemporaryDirectory(prefix="studio-video-acceptance-") as tmp:
    base = Path(tmp)
    for mode in ("chroma","mask"):
        job = json.loads((HERE / "job.example.json").read_text())
        job["mode"] = mode
        path, out = base/(mode+".json"),base/mode
        path.write_text(json.dumps(job))
        assert "voice: done" not in invoke(path,out,"--stop-after","motion")
        assert "motion: reused" in invoke(path,out)
        assert invoke(path,out).count(": reused") == 6
        report = json.loads((out/"edit.json").read_text())["verification"]
        master, compressed = report["master"],report["delivery"]
        assert master["frames"] == compressed["frames"] == 36
        assert master["protected_pixels_per_frame"] == 9984 and master["changed_pixel_samples"] == 0
        assert verify(out/"motion.mkv",out/"plate.png",out/"mask.png")["worst_temporal_mean_error"] > 0
        print(mode,json.dumps(report,ensure_ascii=False))
        (out/"script.json").write_text("{}")
        assert "交接產物變動" in invoke(path,out,success=False)

    job["sources"] = []
    failed_job, failed_out = base/"empty-sources.json",base/"failed"
    failed_job.write_text(json.dumps(job))
    assert "沒有附標題" in invoke(failed_job,failed_out,success=False)
    assert "--retry research" in invoke(failed_job,failed_out,success=False)
    assert "沒有附標題" in invoke(failed_job,failed_out,"--retry","research",success=False)
    state = json.loads((failed_out/"state.json").read_text())["stages"]
    assert set(state) == {"research"} and state["research"]["status"] == "blocked"
    print("通過兩種合成、六階段 JSON 續跑、外部像素擾動、產物竄改與缺來源停止。")
