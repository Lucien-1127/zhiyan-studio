"""Composite a presenter on an immutable RGB plate; measure the protected region after encoding."""

import json
import subprocess
from contextlib import contextmanager

import numpy as np
from PIL import Image


def ffmpeg(*args):
    return ["ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-filter_threads", "1", *map(str, args)]


def probe(path):
    return json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]))


def plate_and_mask(plate_path, mask_path):
    with Image.open(plate_path) as image, Image.open(mask_path) as matte:
        if image.size != matte.size or any(n % 2 for n in image.size):
            raise ValueError("底圖與遮罩須同尺寸；MP4 交付的長寬須為偶數。")
        plate = np.asarray(image.convert("RGB"))
        mask = np.asarray(matte.convert("L"))
    if not np.any(mask == 0) or not np.any(mask > 0):
        raise ValueError("遮罩須同時保留純黑背景和可動的主播區域。")
    return plate, mask


@contextmanager
def frames(path, width, height, fmt, filters=None):
    stream = next(s for s in probe(path)["streams"] if s["codec_type"] == "video")
    if (stream["width"], stream["height"]) != (width, height):
        raise ValueError("影片與底圖座標不符，請先將前景與遮罩對齊同一畫布。")
    channels = 4 if fmt == "rgba" else 3
    cmd = ffmpeg("-noautorotate", "-i", path, "-map", "0:v:0", "-an")
    if filters:
        cmd.extend(["-vf", filters])
    cmd.extend(["-fps_mode", "passthrough", "-pix_fmt", fmt, "-f", "rawvideo", "-threads", "1", "pipe:1"])
    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as reader:
        def sequence():
            frame_bytes = width * height * channels
            while data := reader.stdout.read(frame_bytes):
                if len(data) != frame_bytes:
                    raise ValueError("解碼輸出的影格不完整。")
                yield np.frombuffer(data, dtype=np.uint8).reshape(height, width, channels)
            if reader.wait():
                raise ValueError("FFmpeg 解碼失敗。")
        try:
            yield sequence()
        finally:
            reader.stdout.close()
            if reader.poll() is None:
                reader.terminate()


def composite(plate_path, mask_path, motion_path, output, mode, fps):
    plate, matte = plate_and_mask(plate_path, mask_path)
    h, w = matte.shape
    # RGB colorkey supplies the foreground alpha. The fixed matte caps its spatial extent.
    filters = f"fps={fps},format=rgba"
    if mode == "chroma":
        filters += ",colorkey=color=0x00ff00:similarity=0.20:blend=0.08"
    elif mode != "mask":
        raise ValueError("mode 須為 chroma 或 mask。")
    cmd = ffmpeg("-f", "rawvideo", "-pix_fmt", "rgb24", "-video_size", f"{w}x{h}",
                 "-framerate", fps, "-i", "pipe:0", "-an", "-c:v", "ffv1", "-pix_fmt", "bgr0", output)
    frame_count = 0
    changed_inside = False
    plate32 = plate.astype(np.uint32)
    matte32 = matte.astype(np.uint32)
    with frames(motion_path, w, h, "rgba", filters) as decoded, subprocess.Popen(cmd, stdin=subprocess.PIPE) as encoder:
        try:
            for fg in decoded:
                alpha = ((fg[:, :, 3].astype(np.uint32) * matte32 + 127) // 255)[:, :, None]
                pixels = ((fg[:, :, :3] * alpha + plate32 * (255 - alpha) + 127) // 255).astype(np.uint8)
                changed_inside |= bool(np.any(pixels != plate))
                encoder.stdin.write(pixels.tobytes())
                frame_count += 1
        finally:
            encoder.stdin.close()
        if encoder.wait():
            raise ValueError("FFmpeg 無損母帶寫入失敗。")
    if not frame_count or not changed_inside:
        raise ValueError("沒有可見的前景，請核對色鍵、遮罩及來源。")
    return frame_count


def verify(path, plate_path, mask_path):
    plate, matte = plate_and_mask(plate_path, mask_path)
    h, w = matte.shape
    outside = matte == 0
    reference = plate[outside].astype(np.int16)
    count = 0
    changed = max_error = peak_mae = peak_flicker = 0
    previous = None
    with frames(path, w, h, "rgb24") as decoded:
        for frame in decoded:
            current = frame[outside].astype(np.int16)
            error = np.abs(current - reference)
            changed += int(np.count_nonzero(np.any(error, axis=1)))
            max_error = max(max_error, int(error.max()))
            peak_mae = max(peak_mae, float(error.mean()))
            if previous is not None:
                peak_flicker = max(peak_flicker, float(np.abs(current - previous).mean()))
            previous = current
            count += 1
    if not count:
        raise ValueError("驗收影片沒有可讀取的影格。")
    return {"frames": count, "protected_pixels_per_frame": int(outside.sum()), "changed_pixel_samples": changed,
            "max_channel_error": max_error, "worst_frame_mean_error": peak_mae, "worst_temporal_mean_error": peak_flicker}


def deliver(plate, mask, motion, voice, directory, mode, fps, expected_frames, color_limit, flicker_limit):
    master, mp4 = directory / "master.mkv", directory / "short.mp4"
    count = composite(plate, mask, motion, master, mode, fps)
    if abs(count - expected_frames) > 1:
        raise ValueError(f"動態素材為 {count} 格，與企劃要求的 {expected_frames} 格不符。")
    lossless = verify(master, plate, mask)
    if lossless["changed_pixel_samples"] or lossless["frames"] != count:
        raise ValueError(f"無損母帶驗收失敗：{lossless}")
    voice_info = probe(voice)
    if not any(s["codec_type"] == "audio" for s in voice_info["streams"]):
        raise ValueError("配音檔沒有音軌。")
    if float(voice_info["format"]["duration"]) > count / fps + 1 / fps:
        raise ValueError("配音長於畫面；請縮短旁白或延長動態素材。")
    subprocess.run(ffmpeg("-i", master, "-i", voice, "-map", "0:v:0", "-map", "1:a:0",
                          "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-af", "apad",
                          "-t", str(count / fps), "-c:a", "aac", "-movflags", "+faststart", mp4), check=True)
    compressed = verify(mp4, plate, mask)
    if (compressed["frames"] != count or compressed["worst_frame_mean_error"] > color_limit
            or compressed["worst_temporal_mean_error"] > flicker_limit):
        raise ValueError(f"交付檔背景偏差超標：{compressed}")
    if not any(s["codec_type"] == "audio" for s in probe(mp4)["streams"]):
        raise ValueError("交付檔缺少音軌。")
    return {"master": lossless, "delivery": compressed, "max_mean_color_error": color_limit,
            "max_mean_flicker": flicker_limit}
