"""Run one six-stage presenter short in a workspace. CLI targets Linux, WSL and Hermes."""

import argparse
import fcntl
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError

from background import deliver
import providers


STAGES = {
    "research": ("sources","tavily","perplexity"),
    "script": ("extract","cineagent"),
    "visual": ("fixture","provided","cineagent"),
    "motion": ("fixture","provided","cineagent","liveportrait"),
    "voice": ("fixture-flite","piper","recording"),
    "edit": ("ffmpeg",),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def validate(job):
    if job.get("version") != 1 or job.get("kind") not in ("fixture","production") or not job.get("topic"):
        raise ValueError("需要 version 1、kind（fixture／production）與題材。")
    chosen = job["providers"]
    if set(chosen) != set(STAGES) or any(chosen[k] not in v for k,v in STAGES.items()):
        raise ValueError(f"六階段必須各選一個支援的執行器：{STAGES}")
    if job["kind"] == "production" and any(v.startswith("fixture") for v in chosen.values()):
        raise ValueError("production 案件不可使用測試素材執行器。")
    if job["kind"] == "fixture" and (chosen["research"] != "sources" or "cineagent" in chosen.values()):
        raise ValueError("fixture 使用本機來源與執行器。需呼叫遠端供應商時選擇 production。")
    required = set()
    if chosen["visual"] != "fixture":
        required.update(("plate","mask"))
    for stage_name, provider, filename in [("visual","provided","presenter"),("motion","provided","motion"),
                                           ("motion","liveportrait","driving"),("voice","recording","recording"),
                                           ("voice","piper","voice_model")]:
        if chosen[stage_name] == provider:
            required.add(filename)
    missing = required.difference(job.get("files",{}))
    if missing:
        raise ValueError(f"任務未指定必要的來源檔：{', '.join(sorted(missing))}")
    if job["mode"] not in ("chroma","mask") or job.get("fit_motion", "exact") not in ("exact","contain"):
        raise ValueError("選擇 chroma／mask 與 exact／contain 對齊方式。")
    if chosen["motion"] == "cineagent" and (chosen["visual"] != "cineagent" or job["seconds"] not in (5,10,15)):
        raise ValueError("CineAgent 圖生影要接先前生成的遠端影像；鏡長 5、10 或 15 秒。")
    if chosen["motion"] == "liveportrait" and (job["mode"] != "mask" or job.get("fit_motion","exact") != "exact"):
        raise ValueError("LivePortrait 使用原畫布與 mask；先將底圖、原片及遮罩對齊。")
    if type(job["fps"]) is not int or not 1 <= job["fps"] <= 120 or type(job["seconds"]) is not int or not 1 <= job["seconds"] <= 180:
        raise ValueError("fps、seconds 需為支援範圍內的整數（1–120 格／秒，1–180 秒）。")
    for key in ("max_mean_color_error","max_mean_flicker"):
        value = job["delivery_limits"][key]
        if type(value) not in (float,int) or not math.isfinite(value) or not 0 <= value <= 255:
            raise ValueError(f"成品容差 {key} 需要 0～255 的有限數值。")


def stage(name, job, work, inputs):
    def data(key):
        return read(work / f"{key}.json")
    if name == "research":
        return providers.research(job)
    if name == "script":
        return providers.script(job, data("research")["sources"])
    if name == "visual":
        return providers.visual(job, data("script"), work, inputs)
    if name == "motion":
        return providers.motion(job, data("visual"), data("script"), work, inputs)
    if name == "voice":
        return providers.voice(job, data("script"), work, inputs)
    if name == "edit":
        limits = job["delivery_limits"]
        result = deliver(work/"plate.png",work/"mask.png",work/"motion.mkv",work/"voice.wav",
                         work,job["mode"],job["fps"],job["fps"]*job["seconds"],
                         limits["max_mean_color_error"],limits["max_mean_flicker"])
        return {"files": ["master.mkv","short.mp4"], "verification": result}
    raise ValueError(name)


def run(args):
    job_path = args.job.resolve()
    job = read(job_path)
    validate(job)
    inputs = {key: (job_path.parent / value).resolve() for key, value in job.get("files",{}).items()}
    # Include changes to licensed source footage, masks and voice in the identity of a run.
    signature = {"job": digest(job_path), "inputs": {k: digest(v) for k,v in inputs.items()}}
    work = args.work.resolve()
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (work / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("此目錄已有執行中的任務。") from None
        log = work / "state.json"
        if not log.exists() and any(p.name != ".lock" for p in work.iterdir()):
            raise ValueError("初次執行請指定空目錄。")
        state = read(log) if log.exists() else {"version":1, "kind":job["kind"], "signature":signature, "stages":{}}
        if state["signature"] != signature:
            raise ValueError("任務或來源檔已變更，請選另一個工作目錄，保留原版證據。")
        for name in STAGES:
            prev = state["stages"].get(name,{})
            if prev.get("status") == "done":
                for filename, sha in prev["sha256"].items():
                    if not (work/filename).is_file() or digest(work/filename) != sha:
                        raise ValueError(f"{name} 交接產物變動：{filename}；還原或另開目錄。")
                print(f"{name}: reused", flush=True)
            else:
                if prev and args.retry != name:
                    raise ValueError(f"{name} 上次未完成。核對現有產物／供應商訂單後，可加 --retry {name}。")
                state["stages"][name] = {"provider":job["providers"][name],"status":"running"}
                write(log,state)
                try:
                    result = stage(name,job,work,inputs)
                    output = work / f"{name}.json"
                    write(output,result)
                    hashes = {f:digest(work/f) for f in [output.name,*result.get("files",[])]}
                    state["stages"][name].update(status="done",sha256=hashes)
                    write(log,state)
                except Exception as exc:
                    state["stages"][name].update(status="blocked",error=type(exc).__name__)
                    write(log,state)
                    raise
                print(f"{name}: done", flush=True)
            if args.stop_after == name:
                break


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("job",type=Path)
    p.add_argument("work",type=Path)
    p.add_argument("--retry",choices=STAGES)
    p.add_argument("--stop-after",choices=STAGES)
    try:
        run(p.parse_args())
    except HTTPError as exc:
        print(f"遠端服務回傳 HTTP {exc.code}，請核對服務權限或工作狀態。",file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"短影音任務中止：{exc}",file=sys.stderr)
        sys.exit(1)
