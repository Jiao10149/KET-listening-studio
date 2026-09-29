# -*- coding: utf-8 -*-
"""
KET & PET Listening Audio Studio (Web Application)
Automated Multi-Role Synthesis, Double-Pass Alignment, and Zero-Airflow Master Engineering.
"""

import streamlit as st
import asyncio
import websockets
import json
import ssl
import wave
import os
import io
import re
import zipfile
import subprocess
import numpy as np

# Try importing imageio_ffmpeg, fallback to system ffmpeg
try:
    import imageio_ffmpeg
    DEFAULT_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    DEFAULT_FFMPEG = "ffmpeg"

st.set_page_config(
    page_title="KET 听力录音工作台",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants & Default Configurations (Reads securely from Streamlit Secrets or Environment)
DEFAULT_API_KEY = st.secrets.get("MINIMAX_API_KEY", os.environ.get("MINIMAX_API_KEY", "sk-api-KDxzkUn1rETYdUFlI2sKMwO4pZbJUSkNJQaiK0vIe4H8Bp85IKDu-P-w-cEM0jo2PTQQtw79jQE9-3WQ1y36aN5FkM_NcbrwU11_uYbj8e6A70UzLhWlYSI"))
DEFAULT_PASSWORD = st.secrets.get("ACCESS_PASSWORD", os.environ.get("ACCESS_PASSWORD", "ket2026"))
DEFAULT_MODEL = "speech-2.6-hd"
SAMPLE_RATE = 32000

VOICE_CONFIG = {
    "Man_N": "voice_1766653420_c08e99bd",
    "Man": "voice_1766653420_c08e99bd",
    "Woman": "clone_voice_narrator",
    "Boy": "ttv-voice-2025082420154325-DQq2kiZd",
    "Girl": "ttv-voice-2025092610302125-BvMx9oDR"
}

ROLE_VOL = {
    "Man_N": 1.0,
    "Man": 1.0,
    "Woman": 2.0,
    "Boy": 1.0,
    "Girl": 2.0
}

PAUSE_PATTERN = re.compile(r'<#(\d+(?:\.\d+)?)#>')
LINE_PATTERN = re.compile(r'^\s*([A-Za-z0-9_]+)(?:\|[^|]*\|)?\s*:\s*(.*)$')

# Password Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.get("password_input") == DEFAULT_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.error("密码错误，请向管理员获取访问密码")

if not st.session_state.authenticated:
    st.title("🎙️ KET 听力录音工作台 (Team Studio)")
    st.info("欢迎使用团队专属听力录音系统，请输入团队访问密码以继续。")
    st.text_input("访问密码", type="password", key="password_input", on_change=check_password)
    st.stop()

# Helper Functions
def get_now_listen_again_pcm(asset_path):
    """Load and resample now_listen_again cue audio to 32kHz mono PCM."""
    if not os.path.exists(asset_path):
        return None
    temp_wav = "/tmp/web_nla.wav"
    subprocess.run([
        DEFAULT_FFMPEG, "-y",
        "-i", asset_path,
        "-ar", str(SAMPLE_RATE),
        "-ac", "1",
        temp_wav
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    with wave.open(temp_wav, "rb") as w:
        frames = w.readframes(w.getnframes())
    if os.path.exists(temp_wav):
        os.remove(temp_wav)

    samples = np.frombuffer(frames, dtype=np.int16)
    th = 200
    speech_indices = np.where(np.abs(samples) > th)[0]
    if len(speech_indices) > 0:
        start_idx = max(0, speech_indices[0] - int(SAMPLE_RATE * 0.05))
        end_idx = min(len(samples), speech_indices[-1] + int(SAMPLE_RATE * 0.08))
        speech_samples = samples[start_idx:end_idx]
    else:
        speech_samples = samples

    return apply_edge_fade(speech_samples.tobytes(), fade_ms=5)

def apply_edge_fade(pcm_bytes, fade_ms=5):
    """Apply micro fade-in/fade-out to eliminate edge clicks, with soft peak limiting."""
    if len(pcm_bytes) < 4:
        return pcm_bytes
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).copy()
    max_val = np.max(np.abs(samples))
    if max_val > 31000:
        samples = (samples.astype(np.float64) * (31000.0 / max_val)).astype(np.int16)

    fade_len = int(SAMPLE_RATE * fade_ms / 1000)
    if len(samples) > fade_len * 2:
        fade_in = np.linspace(0.0, 1.0, fade_len)
        fade_out = np.linspace(1.0, 0.0, fade_len)
        samples[:fade_len] = (samples[:fade_len] * fade_in).astype(np.int16)
        samples[-fade_len:] = (samples[-fade_len:] * fade_out).astype(np.int16)
    return samples.tobytes()

def create_silence_pcm(seconds):
    """Generate exact digital silence PCM bytes."""
    return b'\x00' * int(SAMPLE_RATE * 2 * seconds)

async def synthesize_speech_segment(text, role, api_key, speed, vol_override=None, retries=3):
    """Synthesize speech using MiniMax WebSocket API."""
    voice_id = VOICE_CONFIG.get(role, VOICE_CONFIG["Man_N"])
    vol = vol_override if vol_override is not None else ROLE_VOL.get(role, 1.0)
    url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
    headers = {"Authorization": f"Bearer {api_key}"}

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(1, retries + 1):
        try:
            async with websockets.connect(url, additional_headers=headers, ssl=ssl_ctx) as ws:
                conn_resp = json.loads(await ws.recv())
                if conn_resp.get("event") != "connected_success":
                    continue

                start_msg = {
                    "event": "task_start",
                    "model": DEFAULT_MODEL,
                    "voice_setting": {
                        "voice_id": voice_id,
                        "speed": speed,
                        "vol": vol,
                        "pitch": 0,
                        "english_normalization": True
                    },
                    "audio_setting": {
                        "sample_rate": SAMPLE_RATE,
                        "bitrate": 128000,
                        "format": "pcm",
                        "channel": 1
                    }
                }
                await ws.send(json.dumps(start_msg))
                start_resp = json.loads(await ws.recv())
                if start_resp.get("event") != "task_started":
                    continue

                await ws.send(json.dumps({
                    "event": "task_continue",
                    "text": text
                }))

                audio_data = b""
                while True:
                    pkt_raw = await ws.recv()
                    pkt = json.loads(pkt_raw)
                    if "data" in pkt and "audio" in pkt["data"] and pkt["data"]["audio"]:
                        audio_data += bytes.fromhex(pkt["data"]["audio"])
                    if pkt.get("is_final"):
                        break

                try:
                    await ws.send(json.dumps({"event": "task_finish"}))
                except Exception:
                    pass

                return apply_edge_fade(audio_data, fade_ms=5)
        except Exception:
            await asyncio.sleep(1.0)

    raise RuntimeError(f"合成失败: {text}")

async def process_question_text(role, question_text, api_key, speed):
    parts = PAUSE_PATTERN.split(question_text)
    pcm = b""
    for idx, part in enumerate(parts):
        if idx % 2 == 0:
            sub = part.strip()
            if sub:
                pcm += await synthesize_speech_segment(sub, role, api_key, speed)
        else:
            sec = float(part)
            pcm += create_silence_pcm(sec)
    return pcm

async def build_audio_master(raw_script, api_key, speed, now_listen_pcm, progress_cb=None):
    """Parse raw script, synthesize elements, and assemble master PCM."""
    lines = [l.strip() for l in raw_script.strip().splitlines() if l.strip()]
    if not lines:
        raise ValueError("输入剧本为空，请提供有效对话内容。")

    parsed_lines = []
    for line in lines:
        m = LINE_PATTERN.match(line)
        if m:
            parsed_lines.append((m.group(1), m.group(2).strip()))
        else:
            parsed_lines.append(("Narrator", line))

    question_item = None
    dialogue_items = []

    # If first line contains pause tags or is Man_N, treat as question/prompt
    first_role, first_text = parsed_lines[0]
    if "<#" in first_text or first_role in ["Man_N", "Narrator"]:
        question_item = (first_role, first_text)
        dialogue_items = parsed_lines[1:]
    else:
        dialogue_items = parsed_lines

    total_steps = (1 if question_item else 0) + len(dialogue_items)
    step_idx = 0

    full_pcm = b""
    if question_item:
        if progress_cb:
            progress_cb(f"正在录制题干/导语: {question_item[1][:30]}...", 0.1)
        q_pcm = await process_question_text(question_item[0], question_item[1], api_key, speed)
        full_pcm += q_pcm
        step_idx += 1

    dialogue_pcms = []
    for role, text in dialogue_items:
        step_idx += 1
        pct = 0.1 + 0.7 * (step_idx / total_steps)
        if progress_cb:
            progress_cb(f"正在录制角色 [{role}]: {text[:30]}...", pct)
        pcm = await synthesize_speech_segment(text, role, api_key, speed)
        dialogue_pcms.append(pcm)

    # Build dialogue block with 0.5s turn pauses
    dialogue_block = b""
    for i, pcm in enumerate(dialogue_pcms):
        dialogue_block += pcm
        if i < len(dialogue_pcms) - 1:
            dialogue_block += create_silence_pcm(0.5)

    # Assemble master track:
    # Pass 1 + 1.5s + Now listen again + 1.5s + Pass 2 + 2.0s
    if progress_cb:
        progress_cb("正在执行双遍对齐与母带无损缝合...", 0.9)

    full_pcm += dialogue_block
    full_pcm += create_silence_pcm(1.5)
    if now_listen_pcm:
        full_pcm += now_listen_pcm
    full_pcm += create_silence_pcm(1.5)
    full_pcm += dialogue_block
    full_pcm += create_silence_pcm(2.0)

    # Convert PCM to MP3
    temp_wav = "/tmp/temp_master.wav"
    temp_mp3 = "/tmp/temp_master.mp3"

    with wave.open(temp_wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(full_pcm)

    cmd = [
        DEFAULT_FFMPEG, "-y",
        "-i", temp_wav,
        "-b:a", "192k",
        "-ar", str(SAMPLE_RATE),
        temp_mp3
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    with open(temp_mp3, "rb") as f:
        mp3_bytes = f.read()

    duration_sec = len(full_pcm) / (SAMPLE_RATE * 2)

    for p in [temp_wav, temp_mp3]:
        if os.path.exists(p):
            os.remove(p)

    return mp3_bytes, duration_sec

# Sidebar Navigation
with st.sidebar:
    st.header("⚙️ 系统录制配置")
    api_key = st.text_input("MiniMax API Key", value=DEFAULT_API_KEY, type="password")
    speed = st.slider("录音语速 (Speed)", min_value=0.5, max_value=1.2, value=0.8, step=0.05)
    
    st.markdown("---")
    st.markdown("**固定角色音量规范**：")
    st.caption("• 女声 (Girl / Woman): **2.0**")
    st.caption("• 男声 / 旁白 (Man / Boy): **1.0**")
    st.caption("• 读题开头部静音: **6.0s**")
    st.caption("• 对话交替气口: **0.5s**")
    st.caption("• Now listen again 前后: **各 1.5s**")
    st.caption("• 答题结尾缓冲: **2.0s**")

    st.markdown("---")
    if st.button("退出登录"):
        st.session_state.authenticated = False
        st.rerun()

# Locate Now listen again asset
ASSET_PATH = os.path.join(os.path.dirname(__file__), "assets", "now_listen_again.mp3")
now_listen_pcm = get_now_listen_again_pcm(ASSET_PATH)

# Main UI Tabs
st.title("🎧 KET / PET 听力音频自动化工作台")
st.caption("多角色无缝拼接 · 双遍自动复现 · 绝对物理数字真静音 · 女声防爆音强化")

tab_single, tab_batch, tab_help = st.tabs(["📝 单题精细录制", "📦 多题批量录制", "📖 语法与格式说明"])

SAMPLE_TEXT = """Man_N|neutral|: <#6#>You will hear two friends talking about their weekend plans. What did the boy decide to do on Saturday?<#2#>
Girl|friendly|: Are you coming on the cinema trip with our class this Saturday, Kevin?
Boy|calm|: I wanted to see that new film, but my cousin is visiting us. We bought tickets for the basketball game at the sports centre.
Girl|happy|: Oh, have a wonderful time there!<#2#>"""

with tab_single:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("输入听力台词剧本")
        script_input = st.text_area(
            "台词内容",
            value=SAMPLE_TEXT,
            height=260,
            help="支持包含角色标记与 <#x#> 停顿标记"
        )
        file_name = st.text_input("导出文件名", value="KET_BA_LISTENING_PART1_1.mp3")
        
        if st.button("🚀 开始一键合成音频", type="primary", use_container_width=True):
            if not script_input.strip():
                st.error("请输入有效的台词剧本！")
            else:
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def update_progress(msg, val):
                    status_text.text(msg)
                    progress_bar.progress(val)

                try:
                    with st.spinner("正在生成并精密组装中，请稍候..."):
                        mp3_data, dur = asyncio.run(
                            build_audio_master(script_input, api_key, speed, now_listen_pcm, update_progress)
                        )
                    progress_bar.progress(1.0)
                    status_text.success(f"🎉 录制完成！总时长: {dur:.2f} 秒，文件大小: {len(mp3_data)/1024:.1f} KB")

                    with col_r:
                        st.subheader("🎵 在线试听与下载")
                        st.audio(mp3_data, format="audio/mp3")
                        st.download_button(
                            label=f"📥 立即下载 {file_name}",
                            data=mp3_data,
                            file_name=file_name,
                            mime="audio/mp3",
                            use_container_width=True
                        )
                except Exception as e:
                    status_text.error(f"合成过程出错: {e}")

with tab_batch:
    st.subheader("批量录制（多题一键生成打包 ZIP）")
    st.markdown("将多道题目用 **三个横线 `---`** 分隔开，每题第一行可以写 `# 文件名.mp3` 指定文件名：")

    BATCH_SAMPLE = """# KET_BA_F17_LISTENING_PART4_1.mp3
Man_N|neutral|: <#6#>You will hear two friends talking about their weekend plans. What did the boy decide to do on Saturday?<#2#>
Girl|friendly|: Are you coming on the cinema trip with our class this Saturday, Kevin?
Boy|calm|: I wanted to see that new film, but my cousin is visiting us. We bought tickets for the basketball game at the sports centre.
Girl|happy|: Oh, have a wonderful time there!<#2#>

---

# KET_BA_F17_LISTENING_PART4_2.mp3
Man_N|neutral|: <#6#>You will hear a girl talking to her father about cycling. Why does the girl want to cycle tomorrow instead of today?<#2#>
Girl|calm|: Dad, the weather report says it will rain heavily this afternoon. Can we go cycling along the river tomorrow morning?
Man|friendly|: Tomorrow morning will be sunny and dry. But don't you have your piano practice then?
Girl|happy|: My teacher moved it to Sunday, so tomorrow morning is completely free!<#2#>"""

    batch_input = st.text_area("批量题目输入框", value=BATCH_SAMPLE, height=350)

    if st.button("⚡ 批量极速生成全部音频", type="primary"):
        blocks = [b.strip() for b in batch_input.split("---") if b.strip()]
        if not blocks:
            st.error("没有检测到有效题目！")
        else:
            zip_buffer = io.BytesIO()
            batch_progress = st.progress(0.0)
            batch_status = st.empty()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, block in enumerate(blocks):
                    lines = block.splitlines()
                    fname = f"KET_LISTENING_{idx+1}.mp3"
                    script_lines = []
                    for l in lines:
                        if l.strip().startswith("#") and l.strip().endswith(".mp3"):
                            fname = l.strip().replace("#", "").strip()
                        else:
                            script_lines.append(l)

                    script_content = "\n".join(script_lines)
                    batch_status.text(f"[{idx+1}/{len(blocks)}] 正在录制: {fname}...")
                    
                    try:
                        mp3_data, dur = asyncio.run(
                            build_audio_master(script_content, api_key, speed, now_listen_pcm)
                        )
                        zip_file.writestr(fname, mp3_data)
                    except Exception as e:
                        st.error(f"题目 {fname} 合成失败: {e}")
                    
                    batch_progress.progress((idx + 1) / len(blocks))

            batch_status.success(f"🎉 批量生成完毕！共完成 {len(blocks)} 个音频。")
            zip_buffer.seek(0)
            st.download_button(
                label="📦 一键打包下载全部音频 (ZIP 压缩包)",
                data=zip_buffer,
                file_name="KET_听力音频批量导出.zip",
                mime="application/zip",
                use_container_width=True
            )

with tab_help:
    st.subheader("💡 剧本格式与标记说明")
    st.markdown("""
### 1. 角色标识支持
* `Man_N|...|:` 或 `Man:` - 男声 / 旁白 / 爸爸（音量 1.0）
* `Boy|...|:` - 男孩（音量 1.0）
* `Girl|...|:` - 女孩（音量 2.0，女声强化）
* `Woman|...|:` - 老师 / 妈妈 / 成年女性（音量 2.0，女声强化）

### 2. 停顿标记
* `<#6#>` - 物理数字静音 6.0 秒（用于题干前阅读审题）
* `<#2#>` - 物理数字静音 2.0 秒（用于题干后缓冲或全篇答题结尾）

### 3. 自动化流程说明
* 系统自动在第 1 遍播放完毕后插入 `1.5s` 静音 $\rightarrow$ `Now listen again` $\rightarrow$ `1.5s` 静音。
* 系统自动在每个说话人交替之间保留 `0.5s` 自然对话气口。
* 系统自动在第二遍重听复用第一遍的无损语音，保证 100% 发音一致性。
    """)
