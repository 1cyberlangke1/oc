# -*- coding: utf-8 -*-
"""
二次元角色语音工业级生成与推理套件 (Qwen3-TTS & VoxCPM 2.0)
支持模型权重智能寻路、国内 ModelScope / HuggingFace 极速自动下载与环境自检
"""
import os
import sys
import time
import argparse
import subprocess

# 1. 严格 CPU 多线程优化设置，保障宿主操作系统流畅
os.environ["OMP_NUM_THREADS"] = "8"
os.environ["MKL_NUM_THREADS"] = "8"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output", "voice")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 模型仓库映射信息 (ModelScope / HuggingFace)
MODEL_REGISTRY = {
    "qwen_voicedesign": {
        "name": "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "ms_id": "qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "hf_id": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "candidates": [
            os.path.join(MODELS_DIR, "qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign", "snapshots", "master"),
            os.path.join(MODELS_DIR, "qwen--Qwen3-TTS-12Hz-1.7B-VoiceDesign"),
            os.path.join(MODELS_DIR, "Qwen3-TTS-12Hz-1.7B-VoiceDesign"),
        ],
        "key_file": "config.json"
    },
    "qwen_base": {
        "name": "Qwen3-TTS-12Hz-1.7B-Base",
        "ms_id": "qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "hf_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "candidates": [
            os.path.join(MODELS_DIR, "qwen--Qwen3-TTS-12Hz-1.7B-Base", "snapshots", "master"),
            os.path.join(MODELS_DIR, "qwen--Qwen3-TTS-12Hz-1.7B-Base"),
            os.path.join(MODELS_DIR, "Qwen3-TTS-12Hz-1.7B-Base"),
        ],
        "key_file": "config.json"
    },
    "voxcpm2": {
        "name": "VoxCPM2",
        "ms_id": "OpenBMB/VoxCPM2",
        "hf_id": "openbmb/VoxCPM2",
        "candidates": [
            os.path.join(MODELS_DIR, "openbmb--VoxCPM2"),
            os.path.join(MODELS_DIR, "models--openbmb--VoxCPM2"),
            os.path.join(MODELS_DIR, "VoxCPM2"),
        ],
        "key_file": "audiovae.pth"
    }
}

# =========================================================================
# 模块 0：环境自检与模型权重智能获取
# =========================================================================
def ensure_dependencies():
    """检测基础依赖包，如缺失则提示或辅助安装"""
    required_packages = {
        "torch": "torch",
        "soundfile": "soundfile",
        "transformers": "transformers",
        "modelscope": "modelscope"
    }
    missing = []
    for mod, pkg in required_packages.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"⚠️ 检测到缺失基础依赖: {', '.join(missing)}")
        print("⏳ 正在尝试自动安装依赖 (pip install)...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ 依赖安装完成！\n")
        except Exception as e:
            print(f"❌ 自动安装依赖失败，请手动运行: pip install {' '.join(missing)}\n")

def get_model_path(model_key: str) -> str:
    """智能查找本地模型，若未找到则自动调用 ModelScope / HuggingFace 下载"""
    if model_key not in MODEL_REGISTRY:
        raise ValueError(f"未知模型标识: {model_key}")
    
    meta = MODEL_REGISTRY[model_key]
    key_file = meta["key_file"]
    
    # 1. 优先检索现有本地目录
    for cand in meta["candidates"]:
        if os.path.exists(cand):
            # 验证关键文件是否存在
            if os.path.exists(os.path.join(cand, key_file)):
                return cand
            # 针对 snapshots 结构递归查找
            snapshots_dir = os.path.join(cand, "snapshots")
            if os.path.exists(snapshots_dir):
                for sub in os.listdir(snapshots_dir):
                    sub_p = os.path.join(snapshots_dir, sub)
                    if os.path.exists(os.path.join(sub_p, key_file)):
                        return sub_p

    # 2. 本地不存在时，启动自动下载
    print(f"\n📥 本地未检测到模型权重 [{meta['name']}]，准备自动下载...")
    download_dest = os.path.join(MODELS_DIR, meta["name"])
    os.makedirs(download_dest, exist_ok=True)
    
    # 首选 ModelScope (国内秒级极速下载)
    try:
        print(f"🚀 正在连接 ModelScope 魔搭社区拉取 [{meta['ms_id']}] ...")
        from modelscope import snapshot_download
        model_path = snapshot_download(meta["ms_id"], cache_dir=MODELS_DIR)
        print(f"✅ ModelScope 下载成功: {model_path}\n")
        return model_path
    except Exception as e_ms:
        print(f"⚠️ ModelScope 下载失败 ({e_ms})，尝试通过 HuggingFace 拉取...")
    
    # 备选 Hugging Face
    try:
        from huggingface_hub import snapshot_download
        model_path = snapshot_download(repo_id=meta["hf_id"], local_dir=download_dest)
        print(f"✅ HuggingFace 下载成功: {model_path}\n")
        return model_path
    except Exception as e_hf:
        raise RuntimeError(f"❌ 自动下载模型 [{meta['name']}] 失败: {e_hf}\n请检查网络连接或手动下载至 {download_dest}")

# =========================================================================
# 引擎 1：Qwen3-TTS 1.7B VoiceDesign (纯文字自然语言设计音色与情绪)
# =========================================================================
def run_qwen3_voicedesign(text: str, instruct: str, output_file: str):
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    
    torch.set_num_threads(8)
    qwen_dir = get_model_path("qwen_voicedesign")
    
    print("\n" + "=" * 65)
    print("👑 [引擎 1] Qwen3-TTS 1.7B VoiceDesign (纯文字音色与情绪设计)")
    print(f"💬 台词: {text}")
    print(f"📝 提示词: {instruct}")
    print(f"📁 模型路径: {qwen_dir}")
    print("=" * 65)
    
    t0 = time.time()
    model = Qwen3TTSModel.from_pretrained(qwen_dir, device_map="cpu", dtype=torch.float32)
    print(f"✅ 模型加载耗时: {time.time() - t0:.2f}s")
    
    t1 = time.time()
    wavs, sr = model.generate_voice_design(
        text=text,
        instruct=instruct,
        language="Chinese",
        temperature=0.88,
        top_p=0.92,
        repetition_penalty=1.12
    )
    t_cost = time.time() - t1
    sf.write(output_file, wavs[0], sr)
    dur = len(wavs[0]) / sr
    print(f"🎉 生成完毕! 推理耗时: {t_cost:.2f}s | 音频时长: {dur:.2f}s | 保存至: {output_file}")
    return output_file

# =========================================================================
# 引擎 2：Qwen3-TTS 1.7B Base (零样本克隆 ＋ 支持 Instruct 情感控制)
# =========================================================================
def run_qwen3_clone(text: str, ref_audio: str, ref_text: str, output_file: str, instruct: str = None):
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    
    torch.set_num_threads(8)
    qwen_base_dir = get_model_path("qwen_base")
    
    print("\n" + "=" * 65)
    print("🧬 [引擎 2] Qwen3-TTS 1.7B Base (零样本声音克隆 ＋ 情感潜空间控制)")
    print(f"💬 台词: {text}")
    print(f"🎵 参考音频: {ref_audio}")
    print(f"📝 参考文本: {ref_text}")
    if instruct:
        print(f"🎭 情感 Instruct: {instruct}")
    print(f"📁 模型路径: {qwen_base_dir}")
    print("=" * 65)
    
    t0 = time.time()
    model = Qwen3TTSModel.from_pretrained(qwen_base_dir, device_map="cpu", dtype=torch.float32)
    print(f"✅ 模型加载耗时: {time.time() - t0:.2f}s")
    
    t1 = time.time()
    if instruct:
        prompt_items = model.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=ref_text, x_vector_only_mode=False)
        voice_clone_prompt_dict = model._prompt_items_to_voice_clone_prompt(prompt_items)
        input_ids = model._tokenize_texts([model._build_assistant_text(text)])
        ref_tok = model._tokenize_texts([model._build_ref_text(ref_text)])[0]
        instruct_tok = model._tokenize_texts([model._build_instruct_text(instruct)])[0]
        
        gen_kwargs = model._merge_generate_kwargs(temperature=0.88, top_p=0.92, repetition_penalty=1.12)
        talker_codes_list, _ = model.model.generate(
            input_ids=input_ids,
            ref_ids=[ref_tok],
            instruct_ids=[instruct_tok],
            voice_clone_prompt=voice_clone_prompt_dict,
            languages=["Chinese"],
            non_streaming_mode=True,
            **gen_kwargs
        )
        ref_code = voice_clone_prompt_dict["ref_code"][0]
        codes = talker_codes_list[0]
        codes_with_ref = torch.cat([ref_code.to(codes.device), codes], dim=0)
        wavs_all, sr = model.model.speech_tokenizer.decode([{"audio_codes": codes_with_ref}])
        ref_len = int(ref_code.shape[0])
        total_len = int(codes_with_ref.shape[0])
        cut = int(ref_len / max(total_len, 1) * wavs_all[0].shape[0])
        final_wav = wavs_all[0][cut:]
    else:
        wavs, sr = model.generate_voice_clone(
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            language="Chinese",
            temperature=0.88,
            top_p=0.92,
            repetition_penalty=1.12
        )
        final_wav = wavs[0]
        
    t_cost = time.time() - t1
    sf.write(output_file, final_wav, sr)
    dur = len(final_wav) / sr
    print(f"🎉 生成完毕! 推理耗时: {t_cost:.2f}s | 音频时长: {dur:.2f}s | 保存至: {output_file}")
    return output_file

# =========================================================================
# 引擎 3：VoxCPM 2.0 (2B 连续扩散 48kHz 可控克隆)
# =========================================================================
def run_voxcpm(text: str, ref_audio: str, ref_text: str, output_file: str, cfg: float = 2.0):
    import soundfile as sf
    from voxcpm import VoxCPM
    
    local_model_path = get_model_path("voxcpm2")
    
    print("\n" + "=" * 65)
    print("🌟 [引擎 3] VoxCPM 2.0 (2B 连续扩散 48kHz 可控克隆)")
    print(f"💬 台词: {text}")
    print(f"🎵 参考音频: {ref_audio}")
    print(f"🎛️ CFG 引导强度: {cfg}")
    print(f"📁 模型路径: {local_model_path}")
    print("=" * 65)
    
    t0 = time.time()
    model = VoxCPM.from_pretrained(
        hf_model_id=local_model_path,
        device="cpu",
        load_denoiser=False,
        optimize=False
    )
    print(f"✅ VoxCPM2 加载耗时: {time.time() - t0:.2f}s")
    
    t1 = time.time()
    wav = model.generate(
        text=text,
        reference_wav_path=ref_audio,
        prompt_wav_path=ref_audio,
        prompt_text=ref_text,
        cfg_value=cfg,
        inference_timesteps=10
    )
    
    sf.write(output_file, wav, 48000)
    t_cost = time.time() - t1
    dur = len(wav) / 48000
    print(f"🎉 生成完毕! 推理耗时: {t_cost:.2f}s | 音频时长: {dur:.2f}s | 保存至: {output_file}")
    return output_file

# =========================================================================
# 主命令行入口
# =========================================================================
def main():
    ensure_dependencies()
    
    parser = argparse.ArgumentParser(description="二次元角色语音工业级生成工具 (Qwen3-TTS & VoxCPM 2.0)")
    parser.add_argument("--engine", choices=["voicedesign", "clone", "voxcpm", "all"], default="voicedesign", help="选择推理引擎")
    parser.add_argument("--text", default="主人，欢迎回家~ 今天在外面辛苦了呢，千千已经为您放好洗澡水了哦", help="需要合成的台词")
    parser.add_argument("--prompt", default="22岁年轻温柔的大姐姐女声，中音清甜温润，语速轻柔舒缓，带着满满的治愈感与温暖微笑，吐字圆润清晰，句尾带有轻柔的气声。", help="VoiceDesign 音色自然语言设定")
    parser.add_argument("--ref", default=None, help="克隆参考音频路径")
    parser.add_argument("--ref-text", default="主人，欢迎回家~ 今天在外面辛苦了呢，千千已经为您放好洗澡水了哦", help="参考音频台词")
    parser.add_argument("--instruct", default=None, help="克隆模式下的额外情感指令")
    parser.add_argument("--cfg", default=2.0, type=float, help="VoxCPM2 CFG 引导强度")
    parser.add_argument("--output", default=None, help="指定输出音频路径")
    args = parser.parse_args()

    default_ref = os.path.join(PROJECT_ROOT, "character", "狐娘千千", "voice", "chichi_base_voice.wav")
    ref_audio = args.ref if args.ref else default_ref

    if args.engine in ["voicedesign", "all"]:
        vd_out = args.output if args.output else os.path.join(OUTPUT_DIR, "01_qwen3_voicedesign.wav")
        run_qwen3_voicedesign(args.text, args.prompt, vd_out)

    if args.engine in ["clone", "all"]:
        clone_out = args.output if args.output else os.path.join(OUTPUT_DIR, "02_qwen3_voice_clone.wav")
        run_qwen3_clone(args.text, ref_audio, args.ref_text, clone_out, instruct=args.instruct)

    if args.engine in ["voxcpm", "all"]:
        vox_out = args.output if args.output else os.path.join(OUTPUT_DIR, "03_voxcpm2_output.wav")
        run_voxcpm(args.text, ref_audio, args.ref_text, vox_out, cfg=args.cfg)

    print("\n" + "=" * 65)
    print("🏆 音频生成完毕！请在 output/voice/ 目录验听！")

if __name__ == "__main__":
    main()
