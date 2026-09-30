# -*- coding: utf-8 -*-
"""
KET & Universal Listening Audio Studio (Web Application)
Automated Multi-Role Synthesis, Dynamic Voice ID & Emotion Engine,
Double-Pass/Single-Pass Alignment, and Zero-Airflow Master Engineering.
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
import datetime
import urllib.request
import numpy as np
import pandas as pd

# Try importing imageio_ffmpeg, fallback to system ffmpeg
try:
    import imageio_ffmpeg
    DEFAULT_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    DEFAULT_FFMPEG = "ffmpeg"

st.set_page_config(
    page_title="KET / 通用听力智能录音工作台",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Aesthetic Modern Studio Look
st.markdown("""
<style>
    /* Global Container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1320px;
    }
    
    /* Header Card */
    .studio-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        padding: 24px 30px;
        border-radius: 16px;
        margin-bottom: 22px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.25), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .studio-header h1 {
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 6px 0;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .studio-header p {
        color: #94a3b8;
        font-size: 14px;
        margin: 0;
    }

    /* Badges */
    .badge-container {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 14px;
    }
    .spec-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #e2e8f0;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }
    .spec-badge.ket-locked {
        background: rgba(16, 185, 129, 0.15);
        border-color: rgba(16, 185, 129, 0.4);
        color: #34d399;
        font-weight: 600;
    }
    .spec-badge.custom-mode {
        background: rgba(168, 85, 247, 0.15);
        border-color: rgba(168, 85, 247, 0.4);
        color: #c084fc;
        font-weight: 600;
    }
    .spec-badge.highlight {
        background: rgba(245, 158, 11, 0.15);
        border-color: rgba(245, 158, 11, 0.4);
        color: #fbbf24;
    }

    /* Toolbar Quick Pill */
    .tag-pill {
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        color: #334155;
        padding: 2px 8px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 12px;
        margin: 2px;
    }

    /* Tab Label Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 14.5px;
        font-weight: 600;
        padding: 9px 18px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Constants & Default Configurations
try:
    DEFAULT_API_KEY = st.secrets.get("MINIMAX_API_KEY", "sk-api-KDxzkUn1rETYdUFlI2sKMwO4pZbJUSkNJQaiK0vIe4H8Bp85IKDu-P-w-cEM0jo2PTQQtw79jQE9-3WQ1y36aN5FkM_NcbrwU11_uYbj8e6A70UzLhWlYSI")
except Exception:
    DEFAULT_API_KEY = os.environ.get("MINIMAX_API_KEY", "sk-api-KDxzkUn1rETYdUFlI2sKMwO4pZbJUSkNJQaiK0vIe4H8Bp85IKDu-P-w-cEM0jo2PTQQtw79jQE9-3WQ1y36aN5FkM_NcbrwU11_uYbj8e6A70UzLhWlYSI")

try:
    DEFAULT_PASSWORD = st.secrets.get("ACCESS_PASSWORD", "ket2026")
except Exception:
    DEFAULT_PASSWORD = os.environ.get("ACCESS_PASSWORD", "ket2026")
SAMPLE_RATE = 32000

# Standard KET Fixed Specifications (Locked)
KET_DEFAULT_MODEL = "speech-2.6-hd"
KET_VOICES = {
    "Woman": {"voice_id": "clone_voice_narrator", "vol": 2.0, "pitch": 0, "name": "Woman (老师/妈妈/女声 - 音量 2.0)"},
    "Girl": {"voice_id": "ttv-voice-2025092610302125-BvMx9oDR", "vol": 1.0, "pitch": 0, "name": "Girl (女学生 - 音量 1.0)"},
    "Boy": {"voice_id": "ttv-voice-2025082420154325-DQq2kiZd", "vol": 1.0, "pitch": 0, "name": "Boy (男学生 - 音量 1.0)"},
    "Man_N": {"voice_id": "voice_1766653420_c08e99bd", "vol": 1.0, "pitch": 0, "name": "Man_N (旁白导语 - 音量 1.0)"},
    "Man": {"voice_id": "voice_1766653420_c08e99bd", "vol": 1.0, "pitch": 0, "name": "Man (成年男声/爸爸 - 音量 1.0)"}
}

# Supported Emotions in MiniMax
EMOTION_MAP = {
    "neutral": "neutral",
    "happy": "happy",
    "friendly": "happy",
    "calm": "calm",
    "sad": "sad",
    "angry": "angry",
    "fearful": "fearful",
    "disgusted": "disgusted",
    "surprised": "surprised",
    "whisper": "whisper",
    "fluent": "fluent"
}

PAUSE_PATTERN = re.compile(r'<#(\d+(?:\.\d+)?)#>')
LINE_PATTERN = re.compile(r'^\s*([A-Za-z0-9_]+)(?:\|([^|]*)\|)?\s*:\s*(.*)$')

# Session State for Custom Roles & Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "custom_roles" not in st.session_state:
    st.session_state.custom_roles = {
        "Woman": {"voice_id": "clone_voice_narrator", "vol": 2.0, "pitch": 0, "desc": "老师/成年女性"},
        "Girl": {"voice_id": "ttv-voice-2025092610302125-BvMx9oDR", "vol": 1.0, "pitch": 0, "desc": "女孩"},
        "Boy": {"voice_id": "ttv-voice-2025082420154325-DQq2kiZd", "vol": 1.0, "pitch": 0, "desc": "男孩"},
        "Man_N": {"voice_id": "voice_1766653420_c08e99bd", "vol": 1.0, "pitch": 0, "desc": "导语旁白"},
        "Man": {"voice_id": "voice_1766653420_c08e99bd", "vol": 1.0, "pitch": 0, "desc": "爸爸/成年男性"},
        "Teacher": {"voice_id": "clone_voice_narrator", "vol": 2.0, "pitch": 0, "desc": "授课教师"}
    }

def check_password():
    if st.session_state.get("password_input") == DEFAULT_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.error("密码错误，请向管理员获取访问密码")

if not st.session_state.authenticated:
    st.markdown("""
    <div style="max-width: 460px; margin: 100px auto; padding: 36px; background: white; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; text-align: center;">
        <div style="font-size: 48px; margin-bottom: 12px;">🎙️</div>
        <h2 style="margin: 0 0 10px 0; color: #1e293b; font-weight: 700;">听力智能录音工作台</h2>
        <p style="color: #64748b; font-size: 14px; margin-bottom: 24px;">团队内部专用生产系统 · 请输入授权密码继续</p>
    </div>
    """, unsafe_allow_html=True)
    with st.container():
        _, col_mid, _ = st.columns([1, 1.2, 1])
        with col_mid:
            st.text_input("访问密码", type="password", key="password_input", on_change=check_password)
            st.caption("提示：如需获取密码请联系录音棚管理员。")
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
    """Generate exact digital silence PCM bytes (Zero-Airflow)."""
    return b'\x00' * int(SAMPLE_RATE * 2 * seconds)

def synthesize_speech_http(text, role, api_key, speed, model_name, voice_map, emotion_override=None, timeout=30):
    """Synchronous HTTP REST API for MiniMax speech generation (Official t2a_v2)."""
    role_conf = voice_map.get(role, voice_map.get("Man_N", {
        "voice_id": "voice_1766653420_c08e99bd",
        "vol": 1.0,
        "pitch": 0
    }))
    voice_id = role_conf.get("voice_id", "voice_1766653420_c08e99bd")
    vol = role_conf.get("vol", 1.0)
    pitch = role_conf.get("pitch", 0)

    url = "https://api.minimaxi.com/v1/t2a_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    voice_setting = {
        "voice_id": voice_id,
        "speed": speed,
        "vol": vol,
        "pitch": pitch,
        "english_normalization": True
    }
    if emotion_override:
        norm_emotion = EMOTION_MAP.get(emotion_override.lower(), emotion_override.lower())
        voice_setting["emotion"] = norm_emotion

    payload = {
        "model": model_name,
        "text": text,
        "stream": False,
        "voice_setting": voice_setting,
        "audio_setting": {
            "sample_rate": SAMPLE_RATE,
            "bitrate": 128000,
            "format": "pcm",
            "channel": 1
        }
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        base_resp = res.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            raise RuntimeError(base_resp.get("status_msg", "MiniMax接口调用失败"))
        data = res.get("data") or {}
        audio_hex = data.get("audio") or ""
        if not audio_hex:
            raise RuntimeError("MiniMax未返回音频数据")
        return apply_edge_fade(bytes.fromhex(audio_hex), fade_ms=5)

async def synthesize_speech_segment(text, role, api_key, speed, model_name, voice_map, emotion_override=None, retries=3):
    """Synthesize speech using official HTTP REST API (primary) with WebSocket fallback."""
    last_err = "未知原因"
    loop = asyncio.get_running_loop()

    # Engine 1: HTTP REST (Stateless, high reliability, no websocket teardown issues)
    for attempt in range(1, retries + 1):
        try:
            return await loop.run_in_executor(
                None,
                synthesize_speech_http,
                text, role, api_key, speed, model_name, voice_map, emotion_override, 30
            )
        except Exception as e:
            last_err = str(e)
            await asyncio.sleep(attempt * 1.0)

    # Engine 2: WebSocket Fallback
    ws_url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
    headers = {"Authorization": f"Bearer {api_key}"}
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    role_conf = voice_map.get(role, voice_map.get("Man_N", {"voice_id": "voice_1766653420_c08e99bd", "vol": 1.0, "pitch": 0}))
    voice_id = role_conf.get("voice_id", "voice_1766653420_c08e99bd")
    vol = role_conf.get("vol", 1.0)
    pitch = role_conf.get("pitch", 0)

    try:
        async with websockets.connect(ws_url, additional_headers=headers, ssl=ssl_ctx, open_timeout=15) as ws:
            conn_raw = await asyncio.wait_for(ws.recv(), timeout=15)
            conn_resp = json.loads(conn_raw)
            if conn_resp.get("event") == "connected_success":
                voice_setting = {
                    "voice_id": voice_id,
                    "speed": speed,
                    "vol": vol,
                    "pitch": pitch,
                    "english_normalization": True
                }
                if emotion_override:
                    voice_setting["emotion"] = EMOTION_MAP.get(emotion_override.lower(), emotion_override.lower())

                start_msg = {
                    "event": "task_start",
                    "model": model_name,
                    "voice_setting": voice_setting,
                    "audio_setting": {"sample_rate": SAMPLE_RATE, "bitrate": 128000, "format": "pcm", "channel": 1}
                }
                await ws.send(json.dumps(start_msg))
                start_raw = await asyncio.wait_for(ws.recv(), timeout=15)
                start_resp = json.loads(start_raw)
                if start_resp.get("event") == "task_started":
                    await ws.send(json.dumps({"event": "task_continue", "text": text}))
                    audio_data = b""
                    while True:
                        pkt_raw = await asyncio.wait_for(ws.recv(), timeout=20)
                        pkt = json.loads(pkt_raw)
                        if "base_resp" in pkt and pkt["base_resp"].get("status_code", 0) != 0:
                            last_err = pkt["base_resp"].get("status_msg", "合成流报错")
                            break
                        if "data" in pkt and "audio" in pkt["data"] and pkt["data"]["audio"]:
                            audio_data += bytes.fromhex(pkt["data"]["audio"])
                        if pkt.get("is_final"):
                            break
                    try:
                        await ws.send(json.dumps({"event": "task_finish"}))
                    except Exception:
                        pass
                    if audio_data:
                        return apply_edge_fade(audio_data, fade_ms=5)
    except Exception as e:
        last_err = str(e)

    raise RuntimeError(f"合成失败: [{role}] {text} (服务端返回: {last_err})")

async def process_question_text(role, question_text, emotion, api_key, speed, model_name, voice_map):
    parts = PAUSE_PATTERN.split(question_text)
    pcm = b""
    for idx, part in enumerate(parts):
        if idx % 2 == 0:
            sub = part.strip()
            if sub:
                await asyncio.sleep(0.2)
                pcm += await synthesize_speech_segment(sub, role, api_key, speed, model_name, voice_map, emotion)
        else:
            sec = float(part)
            pcm += create_silence_pcm(sec)
    return pcm

async def build_audio_master(raw_script, api_key, speed, model_name, voice_map, is_double_pass,
                             now_listen_pcm, turn_pause=0.5, end_pause=2.0, progress_cb=None):
    """Parse raw script, synthesize elements, and assemble master PCM with flexible structure."""
    lines = [l.strip() for l in raw_script.strip().splitlines() if l.strip()]
    if not lines:
        raise ValueError("输入剧本为空，请提供有效对话内容。")

    parsed_lines = []
    for line in lines:
        m = LINE_PATTERN.match(line)
        if m:
            role = m.group(1).strip()
            emotion = m.group(2).strip() if m.group(2) else None
            text = m.group(3).strip()
            parsed_lines.append((role, emotion, text))
        else:
            parsed_lines.append(("Narrator", None, line))

    question_item = None
    dialogue_items = []

    # If first line contains pause tags or role is Man_N/Narrator, treat as question/prompt
    first_role, first_emotion, first_text = parsed_lines[0]
    if "<#" in first_text or first_role in ["Man_N", "Narrator"]:
        question_item = (first_role, first_emotion, first_text)
        dialogue_items = parsed_lines[1:]
    else:
        dialogue_items = parsed_lines

    total_steps = (1 if question_item else 0) + len(dialogue_items)
    step_idx = 0

    full_pcm = b""
    if question_item:
        if progress_cb:
            progress_cb("正在录制题干导语...", 0.1)
        q_pcm = await process_question_text(question_item[0], question_item[2], question_item[1],
                                            api_key, speed, model_name, voice_map)
        full_pcm += q_pcm
        step_idx += 1

    dialogue_pcms = []
    for role, emotion, text in dialogue_items:
        step_idx += 1
        pct = 0.1 + 0.7 * (step_idx / max(1, total_steps))
        emo_tag = f" ({emotion})" if emotion else ""
        if progress_cb:
            progress_cb(f"正在录制角色 [{role}{emo_tag}]...", pct)
        await asyncio.sleep(0.3)
        pcm = await synthesize_speech_segment(text, role, api_key, speed, model_name, voice_map, emotion)
        dialogue_pcms.append(pcm)

    # Build dialogue block with turn pauses
    dialogue_block = b""
    for i, pcm in enumerate(dialogue_pcms):
        dialogue_block += pcm
        if i < len(dialogue_pcms) - 1:
            dialogue_block += create_silence_pcm(turn_pause)

    # Assemble master track: Pass 1 + [Now listen again + Pass 2 if double pass] + end pause
    if progress_cb:
        progress_cb("正在执行母带拼接与无损对齐...", 0.9)

    full_pcm += dialogue_block

    if is_double_pass:
        full_pcm += create_silence_pcm(1.5)
        if now_listen_pcm:
            full_pcm += now_listen_pcm
        full_pcm += create_silence_pcm(1.5)
        full_pcm += dialogue_block

    full_pcm += create_silence_pcm(end_pause)

    # Convert PCM to MP3
    temp_wav = f"/tmp/temp_master_{os.getpid()}.wav"
    temp_mp3 = f"/tmp/temp_master_{os.getpid()}.mp3"

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

def generate_excel_template(mode="KET"):
    """Generate an in-memory sample Excel template for users to download."""
    if mode == "KET":
        data = [
            {
                "文件名": "KET_BA_F17_PART4_1.mp3",
                "题目标题": "F17 Part 4 题1 (周末活动)",
                "完整台词剧本": """Man_N|neutral|: <#6#>You will hear two friends talking about their weekend plans. What did the boy decide to do on Saturday?<#2#>
Girl|friendly|: Are you coming on the cinema trip with our class this Saturday, Kevin?
Boy|calm|: I wanted to see that new film, but my cousin is visiting us. We bought tickets for the basketball game at the sports centre.
Girl|happy|: Oh, have a wonderful time there!<#2#>"""
            },
            {
                "文件名": "KET_BA_F17_PART4_2.mp3",
                "题目标题": "F17 Part 4 题2 (骑行计划)",
                "完整台词剧本": """Man_N|neutral|: <#6#>You will hear a girl talking to her father about cycling. Why does the girl want to cycle tomorrow instead of today?<#2#>
Girl|calm|: Dad, the weather report says it will rain heavily this afternoon. Can we go cycling along the river tomorrow morning?
Man|friendly|: Tomorrow morning will be sunny and dry. But don't you have your piano practice then?
Girl|happy|: My teacher moved it to Sunday, so tomorrow morning is completely free!<#2#>"""
            }
        ]
    else:
        data = [
            {
                "文件名": "EXAM_LISTENING_01.mp3",
                "题目标题": "情景对话 1 (问路与介绍)",
                "完整台词剧本": """Man_N|neutral|: Listen to the conversation between a tourist and a guide.<#2#>
Tourist|surprised|: Excuse me, is the science museum open today?
Guide|friendly|: Yes, it is open until six o'clock this evening!
Tourist|happy|: Thank you very much! (laughs)<#2#>"""
            }
        ]
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="听力题目配置表")
    buffer.seek(0)
    return buffer.getvalue()

# Locate Now listen again asset
ASSET_PATH = os.path.join(os.path.dirname(__file__), "assets", "now_listen_again.mp3")
now_listen_pcm = get_now_listen_again_pcm(ASSET_PATH)

# ================= SIDEBAR & WORKBENCH MODES =================
with st.sidebar:
    st.markdown("### 🎛️ 录音棚模式选择")
    app_mode = st.radio(
        "工作模式：",
        ["🎯 剑桥 KET 官方标准（锁定区）", "🎛️ 通用高级调音模式（全能自由区）"],
        index=0,
        help="【KET 标准】锁定官方参数与音量防呆防错；【通用模式】解锁模型切换、自定义音色ID、情绪与单双遍自由配置"
    )

    api_key = st.text_input("MiniMax API Key", value=DEFAULT_API_KEY, type="password")

    st.markdown("---")

    # Mode-based Parameters
    if "KET" in app_mode:
        selected_model = KET_DEFAULT_MODEL
        speed = 0.8
        is_double_pass = True
        use_nla = True
        active_voice_map = {k: {"voice_id": v["voice_id"], "vol": v["vol"], "pitch": v["pitch"]} for k, v in KET_VOICES.items()}
        turn_pause = 0.5
        end_pause = 2.0

        st.markdown("#### 🔒 KET 官方规范已锁定")
        st.success("✓ 剑桥官方标准参数锁定中（防呆防错）")
        st.caption("• 引擎模型: **speech-2.6-hd**")
        st.caption("• 官方语速: **0.8x**")
        st.caption("• 播放结构: **双遍对齐 + Now listen again**")
        st.caption("• 女人 (Woman): **2.0x 增强音量**")
        st.caption("• 女孩 (Girl): **1.0x 标准音量**")
        st.caption("• 男声 / 男孩: **1.0x 标准音量**")
        st.caption("• 审题静音: **6.0s** (`<#6#>`) | 结尾: **2.0s**")

    else:
        st.markdown("#### ⚙️ MiniMax 引擎与参数设置")
        selected_model = st.selectbox(
            "选择 MiniMax 语音模型：",
            ["speech-2.6-hd", "speech-2.8-hd", "speech-2.6-turbo", "speech-2.8-turbo"],
            index=0,
            help="speech-2.6-hd: 极致音质与韵律(推荐)；speech-2.8-hd: 最新旗舰架构；turbo: 超低延迟快速出样"
        )
        speed = st.slider("全局语速 (Speed)", min_value=0.5, max_value=1.5, value=0.85, step=0.05)

        st.markdown("#### ⏱️ 母带播放结构设置")
        pass_mode = st.radio("播放遍数：", ["双遍复读 (Double-Pass)", "单遍播放 (Single-Pass)"], index=0)
        is_double_pass = (pass_mode == "双遍复读 (Double-Pass)")
        use_nla = st.checkbox("复读间插入 'Now listen again' 提示音", value=True) if is_double_pass else False
        turn_pause = st.slider("角色交替气口间隔 (秒)", min_value=0.1, max_value=1.5, value=0.5, step=0.1)
        end_pause = st.slider("答题结尾缓冲静音 (秒)", min_value=0.5, max_value=4.0, value=2.0, step=0.5)

        active_voice_map = {k: {"voice_id": v["voice_id"], "vol": v["vol"], "pitch": v["pitch"]} for k, v in st.session_state.custom_roles.items()}

    st.markdown("---")
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ================= MAIN UI HEADER BANNER =================
is_ket_mode = "KET" in app_mode
badge_mode_html = (
    '<span class="spec-badge ket-locked">🔒 剑桥 KET 官方标准锁定区</span>'
    if is_ket_mode else
    '<span class="spec-badge custom-mode">🎛️ 通用高级调音模式 (模型/音色ID/情绪已解锁)</span>'
)

st.markdown(f"""
<div class="studio-header">
    <h1>🎙️ KET & 通用听力音频自动化工作台</h1>
    <p>剑桥标准母带对齐 · 自由自定义音色与情绪 · 绝对数字零底噪物理静音 · Excel 批量极速生成</p>
    <div class="badge-container">
        {badge_mode_html}
        <span class="spec-badge">模型: {selected_model}</span>
        <span class="spec-badge">语速: {speed}x</span>
        <span class="spec-badge highlight">女人音量: 2.0x</span>
        <span class="spec-badge">女孩音量: 1.0x</span>
        <span class="spec-badge">{"双遍对齐" if is_double_pass else "单遍播放"}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Custom Role Manager Expander in Custom Mode
if not is_ket_mode:
    with st.expander("🎭 角色声线库与自定义音色 ID 管理台 (点击展开/配置)", expanded=False):
        st.caption("您可以自由为角色绑定 MiniMax 官方音色 ID，或粘贴团队在 MiniMax 控制台自建复刻的专属声音 ID。")

        col_c1, col_c2 = st.columns([3, 2])
        with col_c1:
            st.markdown("##### 当前已配置的角色清单：")
            for role_name, conf in list(st.session_state.custom_roles.items()):
                c1, c2, c3, c4 = st.columns([1.2, 2.2, 1.2, 0.8])
                with c1:
                    st.write(f"**{role_name}** ({conf.get('desc', '')})")
                with c2:
                    new_vid = st.text_input(f"Voice ID", value=conf['voice_id'], key=f"vid_{role_name}", label_visibility="collapsed")
                    st.session_state.custom_roles[role_name]['voice_id'] = new_vid
                with c3:
                    new_vol = st.number_input(f"Vol", min_value=0.1, max_value=5.0, value=float(conf['vol']), step=0.1, key=f"vol_{role_name}", label_visibility="collapsed")
                    st.session_state.custom_roles[role_name]['vol'] = new_vol
                with c4:
                    if st.button("🗑️", key=f"del_{role_name}", help=f"删除角色 {role_name}"):
                        if len(st.session_state.custom_roles) > 1:
                            del st.session_state.custom_roles[role_name]
                            st.rerun()

        with col_c2:
            st.markdown("##### ➕ 新增自定义角色：")
            with st.form("add_role_form"):
                add_name = st.text_input("角色代码 (如 Teacher / Doctor / Grandpa)", placeholder="Doctor")
                add_desc = st.text_input("中文说明", placeholder="医生")
                add_vid = st.text_input("音色 ID (Voice ID)", value="voice_1766653420_c08e99bd", help="可填写官方音色ID或复刻声音ID")
                add_vol = st.slider("音量倍率 (Volume)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
                add_pitch = st.slider("音调微调 (Pitch)", min_value=-12, max_value=12, value=0, step=1)
                
                if st.form_submit_button("✅ 确认添加角色"):
                    if add_name.strip():
                        st.session_state.custom_roles[add_name.strip()] = {
                            "voice_id": add_vid.strip(),
                            "vol": float(add_vol),
                            "pitch": int(add_pitch),
                            "desc": add_desc.strip()
                        }
                        st.success(f"已添加角色 [{add_name}]！")
                        st.rerun()

# Tabs
tab_excel, tab_single, tab_batch, tab_help = st.tabs([
    "📊 Excel 批量导入生成",
    "📝 单题精细录制与试听",
    "📦 文本快速批量录制",
    "📖 语法与音色速查"
])

# Quick tag helper banner (MiniMax Style)
def render_quick_tags_bar():
    st.markdown("""
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 13px;">
        <span style="color: #64748b; font-weight: 600; margin-right: 8px;">快捷语法参考 (复制即用)：</span><br>
        <span style="color:#475569; font-weight:500;">🎭 情绪：</span>
        <span class="tag-pill">|happy|</span>
        <span class="tag-pill">|calm|</span>
        <span class="tag-pill">|sad|</span>
        <span class="tag-pill">|friendly|</span>
        <span class="tag-pill">|surprised|</span>
        <span class="tag-pill">|whisper|</span>
        <span style="color:#475569; font-weight:500; margin-left: 10px;">💬 语气词：</span>
        <span class="tag-pill">(laughs)</span>
        <span class="tag-pill">(chuckle)</span>
        <span class="tag-pill">(sighs)</span>
        <span class="tag-pill">(breath)</span>
        <span class="tag-pill">(gasps)</span>
        <span style="color:#475569; font-weight:500; margin-left: 10px;">⏱️ 静音：</span>
        <span class="tag-pill">&lt;#6#&gt;</span>
        <span class="tag-pill">&lt;#2#&gt;</span>
        <span class="tag-pill">&lt;#0.5#&gt;</span>
    </div>
    """, unsafe_allow_html=True)

# ----------------- TAB 1: EXCEL BATCH PROCESSING -----------------
with tab_excel:
    st.subheader("📊 Excel 批量导入生成听力音频")
    mode_label = "剑桥 KET 官方标准" if is_ket_mode else f"通用模式 ({selected_model})"
    st.caption(f"当前运行模式：**{mode_label}**。上传 Excel 文件，系统自动解析剧本并批量生成完整母带。")

    col_btn1, col_btn2 = st.columns([1.2, 3])
    with col_btn1:
        st.download_button(
            label="📥 下载标准 Excel 模板",
            data=generate_excel_template("KET" if is_ket_mode else "CUSTOM"),
            file_name="KET_听力题目导入模板.xlsx" if is_ket_mode else "通用听力题目导入模板.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col_btn2:
        st.info("💡 建议首次使用先下载模板查看格式。表格支持单行包含整道题完整剧本，或包含文件名与剧本列。")

    uploaded_file = st.file_uploader("选择或拖拽 Excel 文件 (.xlsx, .xls)", type=["xlsx", "xls"], key="excel_uploader")

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success(f"成功读取表格！共检测到 **{len(df)}** 行数据。")
            
            with st.expander("👀 查看表格预览 (前 5 行)", expanded=True):
                st.dataframe(df.head(5), use_container_width=True)

            columns = list(df.columns)
            
            # Smart default column detection
            default_fname_col = next((c for c in columns if any(k in str(c).lower() for k in ["文件", "file", "id", "题号", "编号"])), columns[0])
            default_script_col = next((c for c in columns if any(k in str(c).lower() for k in ["剧本", "台词", "内容", "script", "text", "dialogue"])), columns[-1])

            st.markdown("#### 🎯 字段映射配置")
            col_map1, col_map2 = st.columns(2)
            with col_map1:
                selected_fname_col = st.selectbox("选择【导出文件名 / 题号】所在列：", columns, index=columns.index(default_fname_col))
            with col_map2:
                selected_script_col = st.selectbox("选择【完整台词剧本】所在列：", columns, index=columns.index(default_script_col))

            # Filter valid rows
            valid_tasks = []
            for idx, row in df.iterrows():
                fname_val = str(row.get(selected_fname_col, "")).strip()
                script_val = str(row.get(selected_script_col, "")).strip()
                if script_val and script_val.lower() != "nan":
                    if not fname_val or fname_val.lower() == "nan":
                        fname_val = f"QUESTION_{idx+1}.mp3"
                    if not fname_val.lower().endswith(".mp3"):
                        fname_val += ".mp3"
                    valid_tasks.append((fname_val, script_val))

            st.write(f"已识别到 **{len(valid_tasks)}** 个有效待录制题目。")

            if st.button("🚀 开始批量合成所有 Excel 题目", type="primary", use_container_width=True):
                if not valid_tasks:
                    st.error("没有检测到包含有效剧本内容的行，请检查选择的列！")
                else:
                    progress_bar = st.progress(0.0)
                    status_placeholder = st.empty()
                    zip_buffer = io.BytesIO()
                    results = []

                    actual_nla = now_listen_pcm if (is_double_pass and use_nla) else None

                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for idx, (fname, script_text) in enumerate(valid_tasks):
                            status_placeholder.markdown(f"**正在录制第 [{idx+1}/{len(valid_tasks)}] 题**: `{fname}` ...")
                            
                            def row_progress(msg, pct):
                                overall_pct = (idx + pct) / len(valid_tasks)
                                progress_bar.progress(min(0.99, overall_pct))

                            try:
                                mp3_bytes, dur = asyncio.run(
                                    build_audio_master(
                                        script_text, api_key, speed, selected_model,
                                        active_voice_map, is_double_pass, actual_nla,
                                        turn_pause, end_pause, row_progress
                                    )
                                )
                                zip_file.writestr(fname, mp3_bytes)
                                results.append({
                                    "文件名": fname,
                                    "状态": "✅ 成功",
                                    "时长(秒)": f"{dur:.2f}s",
                                    "大小(KB)": f"{len(mp3_bytes)/1024:.1f}KB",
                                    "mp3_bytes": mp3_bytes
                                })
                            except Exception as e:
                                results.append({
                                    "文件名": fname,
                                    "状态": f"❌ 失败: {str(e)}",
                                    "时长(秒)": "-",
                                    "大小(KB)": "-",
                                    "mp3_bytes": None
                                })
                            
                            progress_bar.progress((idx + 1) / len(valid_tasks))

                    progress_bar.progress(1.0)
                    status_placeholder.success(f"🎉 全部处理完成！共生成 {len([r for r in results if r['mp3_bytes']])} 个音频文件。")

                    # ZIP Download Button
                    zip_buffer.seek(0)
                    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    zip_filename = f"听力音频批量导出_{now_str}.zip"

                    st.download_button(
                        label=f"📦 一键下载全部音频压缩包 ({zip_filename})",
                        data=zip_buffer,
                        file_name=zip_filename,
                        mime="application/zip",
                        use_container_width=True
                    )

                    # Summary table
                    st.markdown("#### 📋 生成结果清单")
                    summary_df = pd.DataFrame([{k: v for k, v in r.items() if k != 'mp3_bytes'} for r in results])
                    st.dataframe(summary_df, use_container_width=True)

                    # Audio previews for generated items
                    with st.expander("🎧 在线试听已生成的音频 (预览前 5 首)", expanded=True):
                        successful_items = [r for r in results if r['mp3_bytes'] is not None][:5]
                        for item in successful_items:
                            col_a, col_b = st.columns([1, 2])
                            with col_a:
                                st.write(f"**{item['文件名']}** ({item['时长(秒)']})")
                            with col_b:
                                st.audio(item['mp3_bytes'], format="audio/mp3")

        except Exception as e:
            st.error(f"读取 Excel 文件失败: {e}")

# ----------------- TAB 2: SINGLE QUESTION STUDIO -----------------
SAMPLE_TEXT = """Man_N|neutral|: <#6#>You will hear two friends talking about their weekend plans. What did the boy decide to do on Saturday?<#2#>
Girl|friendly|: Are you coming on the cinema trip with our class this Saturday, Kevin?
Boy|calm|: I wanted to see that new film, but my cousin is visiting us. We bought tickets for the basketball game at the sports centre.
Girl|happy|: Oh, have a wonderful time there!<#2#>"""

with tab_single:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.subheader("📝 单题台词编辑与试听")
        render_quick_tags_bar()

        script_input = st.text_area(
            "输入台词剧本",
            value=SAMPLE_TEXT,
            height=280,
            help="支持角色标识、情绪标记（如 |happy|）与停顿标记（如 <#6#>）"
        )
        file_name = st.text_input("导出文件名", value="KET_BA_LISTENING_PART1_1.mp3")
        
        if st.button("🚀 开始一键合成母带音频", type="primary", use_container_width=True):
            if not script_input.strip():
                st.error("请输入有效的台词剧本！")
            else:
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def update_progress(msg, val):
                    status_text.text(msg)
                    progress_bar.progress(val)

                actual_nla = now_listen_pcm if (is_double_pass and use_nla) else None

                try:
                    with st.spinner("正在合成并精密组装中，请稍候..."):
                        mp3_data, dur = asyncio.run(
                            build_audio_master(
                                script_input, api_key, speed, selected_model,
                                active_voice_map, is_double_pass, actual_nla,
                                turn_pause, end_pause, update_progress
                            )
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

# ----------------- TAB 3: TEXT BATCH -----------------
with tab_batch:
    st.subheader("📦 文本批量录制（多题一键生成打包 ZIP）")
    render_quick_tags_bar()
    st.markdown("将多道题目用 **三个横线 `---`** 分隔开，每题第一行可以写 `# 文件名.mp3` 指定导出文件名：")

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

    batch_input = st.text_area("批量文本剧本输入框", value=BATCH_SAMPLE, height=340)

    if st.button("⚡ 批量极速生成全部音频", type="primary", use_container_width=True):
        blocks = [b.strip() for b in batch_input.split("---") if b.strip()]
        if not blocks:
            st.error("没有检测到有效题目！")
        else:
            zip_buffer = io.BytesIO()
            batch_progress = st.progress(0.0)
            batch_status = st.empty()

            actual_nla = now_listen_pcm if (is_double_pass and use_nla) else None

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, block in enumerate(blocks):
                    lines = block.splitlines()
                    fname = f"LISTENING_{idx+1}.mp3"
                    script_lines = []
                    for l in lines:
                        if l.strip().startswith("#") and l.strip().endswith(".mp3"):
                            fname = l.strip().replace("#", "").strip()
                        else:
                            script_lines.append(l)

                    script_content = "\n".join(script_lines)
                    batch_status.markdown(f"**[{idx+1}/{len(blocks)}] 正在录制**: `{fname}` ...")
                    
                    try:
                        mp3_data, dur = asyncio.run(
                            build_audio_master(
                                script_content, api_key, speed, selected_model,
                                active_voice_map, is_double_pass, actual_nla,
                                turn_pause, end_pause
                            )
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
                file_name="听力音频批量导出.zip",
                mime="application/zip",
                use_container_width=True
            )

# ----------------- TAB 4: HELP & DOCUMENTATION -----------------
with tab_help:
    st.subheader("💡 剧本格式、情绪与音色速查手册")
    st.markdown("""
### 1. 台词剧本语法规范
* **标准格式**：`角色名|情绪|: 台词文本` 或 `角色名: 台词文本`
* **情绪标签支持**：
  * `|happy|` 或 `|friendly|`：开心愉悦、热情友好
  * `|calm|`：沉着平静、自然对话
  * `|sad|`：悲伤低落
  * `|angry|`：生气严肃
  * `|surprised|`：惊讶惊奇
  * `|whisper|`：悄悄话低语（仅 Speech 2.6 系列模型生效）
* **语气词标签（直接写在台词文本中）**：
  * `(laughs)` 笑声，`(chuckle)` 轻笑，`(coughs)` 咳嗽，`(sighs)` 叹气，`(breath)` 换气，`(gasps)` 倒吸气

---

### 2. KET 官方标准模式的角色与音量规范
| 角色前缀 | 代表身份 | 对应音色 ID | 音量倍率 (Volume) | 规范说明 |
| :--- | :--- | :--- | :--- | :--- |
| **`Woman`** | 老师 / 妈妈 / 成年女性 | `clone_voice_narrator` | **2.0 (已增强)** | 增强女生成人声音穿透力，防过载限制 |
| **`Girl`** | 女学生 / 小女孩 | `ttv-voice-...-BvMx9oDR` | **1.0 (标准)** | 保持自然清晰童声 |
| **`Boy`** | 男学生 / 小男孩 | `ttv-voice-...-DQq2kiZd` | **1.0 (标准)** | 少年英式/通用口音 |
| **`Man`** / **`Man_N`** | 男声 / 爸爸 / 听力导语旁白 | `voice_1766653420_c08e99bd` | **1.0 (标准)** | 官方 Cambridge 稳重男中音 |

---

### 3. 通用模式自由度说明
* 可在左侧边栏切换至【通用高级调音模式】；
* 自由切换 MiniMax 模型：`speech-2.6-hd`（高韵律推荐）、`speech-2.8-hd`（最新旗舰）、`turbo`（低延迟测试）；
* 自由添加新角色（如 `Doctor`, `Tourist`, `Grandpa` 等），并直接填入任意自定义 MiniMax `voice_id`；
* 自由切换单遍朗读或双遍复读。
    """)
