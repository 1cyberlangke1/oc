"""
二次元表情包高清超分放大与 WebP 极速压缩工具
- 算法引擎：Real-CUGAN (ncnn-vulkan)
- 硬件支持：CPU (默认/安全模式) / GPU (Vulkan 加速)
- 目标：将 character/ 目录下的所有表情包统一超分放大到 1024x1024 并转为高质量极小体积 .webp，默认自动清理原图
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from realcugan_ncnn_py import Realcugan


def process_images(
    target_dir: Path,
    device: str = "cpu",
    target_size: int = 1024,
    webp_quality: int = 85,
    model_name: str = "models-se",
    delete_original: bool = True,
):
    """
    遍历指定目录，对所有表情包执行超分放大并转存为 WebP 格式，默认自动清除原图。

    输入:
        target_dir: 搜索图片的根目录 (如 character/)
        device: 'cpu' 或 'gpu'
        target_size: 目标尺寸宽和高 (默认 1024)
        webp_quality: WebP 压缩质量 1-100 (默认 85)
        model_name: Real-CUGAN 模型名 ('models-se' / 'models-pro')
        delete_original: 转换成功后是否删除原图片文件 (默认 True 自动清理)
    """
    gpuid = -1 if device.lower() == "cpu" else 0
    print(f"[*] 初始化 Real-CUGAN 引擎 (Device: {device.upper()}, gpuid: {gpuid}, Model: {model_name})...")

    cugan = Realcugan(
        gpuid=gpuid,
        scale=2,
        noise=-1,
        model=model_name,
        num_threads=4,
    )

    image_extensions = {".png", ".jpg", ".jpeg", ".bmp"}
    all_images = [
        p for p in target_dir.rglob("*")
        if p.suffix.lower() in image_extensions and p.suffix.lower() != ".webp"
    ]

    if not all_images:
        print(f"[!] 在 {target_dir} 中未找到需要处理的原图片文件。")
        return

    print(f"[*] 找到 {len(all_images)} 张图片待处理：")
    total_original_bytes = 0
    total_new_bytes = 0

    for idx, img_path in enumerate(all_images, start=1):
        rel_path = img_path.relative_to(target_dir.parent if target_dir.parent.exists() else target_dir)
        orig_size_kb = img_path.stat().st_size / 1024
        total_original_bytes += img_path.stat().st_size

        print(f"\n[{idx}/{len(all_images)}] 处理中: {rel_path} ({orig_size_kb:.1f} KB)...")
        start_time = time.time()

        try:
            with Image.open(img_path) as img:
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    img_rgba = img.convert("RGBA")
                    r, g, b, a = img_rgba.split()
                    rgb_img = Image.merge("RGB", (r, g, b))

                    upscaled_rgb = cugan.process_pil(rgb_img)
                    upscaled_a = a.resize(upscaled_rgb.size, resample=Image.Resampling.LANCZOS)
                    upscaled_pil = Image.merge("RGBA", (*upscaled_rgb.split(), upscaled_a))
                else:
                    img_rgb = img.convert("RGB")
                    upscaled_pil = cugan.process_pil(img_rgb)

                # 自适应背景色（采样四角中位数）
                arr = np.array(upscaled_pil.convert("RGBA"))
                corners = [arr[0, 0, :3], arr[0, -1, :3], arr[-1, 0, :3], arr[-1, -1, :3]]
                bg_rgb = np.median(corners, axis=0).astype(int)
                bg = tuple(bg_rgb.tolist()) + (255,)

                # 基于背景色做自适应容差掩码（容差 12）
                tol = 12
                mask = ~(
                    (np.abs(arr[:, :, 0].astype(int) - bg_rgb[0]) <= tol) &
                    (np.abs(arr[:, :, 1].astype(int) - bg_rgb[1]) <= tol) &
                    (np.abs(arr[:, :, 2].astype(int) - bg_rgb[2]) <= tol)
                )
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                if rows.any() and cols.any():
                    rmin, rmax = np.where(rows)[0][[0, -1]]
                    cmin, cmax = np.where(cols)[0][[0, -1]]
                    pad = 20
                    rmin = max(0, rmin - pad)
                    rmax = min(arr.shape[0], rmax + pad)
                    cmin = max(0, cmin - pad)
                    cmax = min(arr.shape[1], cmax + pad)
                    upscaled_pil = upscaled_pil.crop((cmin, rmin, cmax, rmax))

                # 补背景色填成正方形（保持比例不压扁，颜色与原图一致）
                w, h = upscaled_pil.size
                square_size = max(w, h)
                square = Image.new("RGBA", (square_size, square_size), bg)
                square.paste(upscaled_pil, ((square_size - w) // 2, (square_size - h) // 2))

                # 缩放到目标尺寸
                final_pil = square.resize(
                    (target_size, target_size),
                    resample=Image.Resampling.LANCZOS,
                )

                out_path = img_path.with_suffix(".webp")
                final_pil.save(
                    out_path,
                    format="WEBP",
                    quality=webp_quality,
                    method=6,
                )

            new_size_kb = out_path.stat().st_size / 1024
            total_new_bytes += out_path.stat().st_size
            elapsed = time.time() - start_time
            saved_percent = (1 - (new_size_kb / orig_size_kb)) * 100

            print(f"    -> 成功生成: {out_path.name} | 尺寸: {final_pil.size} | 体积: {new_size_kb:.1f} KB (节省 {saved_percent:.1f}%) | 耗时: {elapsed:.2f}s")

            if delete_original and out_path.exists() and img_path.suffix.lower() != ".webp":
                img_path.unlink()
                print(f"    -> 已自动清理原图: {img_path.name}")

        except Exception as e:
            print(f"    [X] 处理失败 {img_path.name}: {e}", file=sys.stderr)

    orig_total_mb = total_original_bytes / (1024 * 1024)
    new_total_mb = total_new_bytes / (1024 * 1024)
    overall_saved = (1 - (total_new_bytes / total_original_bytes)) * 100 if total_original_bytes else 0

    print("\n" + "=" * 50)
    print(f"[*] 全部处理与自动清理完成！")
    print(f"[*] 原始总体积: {orig_total_mb:.2f} MB")
    print(f"[*] WebP 总体积: {new_total_mb:.2f} MB (总体节省 {overall_saved:.1f}% 空间)")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="二次元表情包超分放大与 WebP 转换工具（默认自动清理原图）")
    parser.add_argument("--dir", type=str, default="character", help="目标图片目录 (默认 character)")
    parser.add_argument("--device", type=str, choices=["cpu", "gpu"], default="cpu", help="计算设备 (默认 cpu)")
    parser.add_argument("--size", type=int, default=1024, help="目标尺寸宽和高 (默认 1024)")
    parser.add_argument("--quality", type=int, default=85, help="WebP 质量 1-100 (默认 85)")
    parser.add_argument("--keep-original", action="store_true", help="保留原图文件 (默认会自动删除原图)")

    args = parser.parse_args()
    process_images(
        target_dir=Path(args.dir),
        device=args.device,
        target_size=args.size,
        webp_quality=args.quality,
        delete_original=not args.keep_original,
    )
