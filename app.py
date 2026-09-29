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
import datetime
import numpy as np
import pandas as pd

# Try importing imageio_ffmpeg, fallback to system ffmpeg
try:
    import imageio_ffmpeg
    DEFAULT_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    DEFAULT_FFMPEG = "ffmpeg"

st.set_page_config(
    page_title="KET 听力智能录音工作台",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Aesthetic Studio Look
st.markdown("""
<style>
    /* Global Font & Background Styling */
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }
    
    /* Header Card */
    .studio-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #ffffff;
        padding: 24px 30px;
        border-radius: 16px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .studio-header h1 {
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 8px 0;
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
    .spec-badge.highlight {
        background: rgba(245, 158, 11, 0.15);
        border-color: rgba(245, 158, 11, 0.4);
        color: #fbbf24;
    }
    .spec-badge.green {
        background: rgba(16, 185, 129, 0.15);
        border-color: rgba(16, 185, 129, 0.4);
        color: #34d399;
    }

    /* Card Panels */
    .content-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 20px;
    }

    /* Button Styling */
    div.stButton > button:first-child {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    /* Tab Label Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 15px;
        font-weight: 600;
        padding: 10px 18px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Constants & Default Configurations
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

# Role Volume: 女人=2.0，女孩=1.0，其余均1.0
ROLE_VOL = {
    "Man_N": 1.0,
    "Man": 1.0,
    "Woman": 2.0,
    "Boy": 1.0,
    "Girl": 1.0
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
    st.markdown("""
    <div style="max-width: 460px; margin: 100px auto; padding: 36px; background: white; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; text-align: center;">
        <div style="font-size: 48px; margin-bottom: 12px;">🎙️</div>
        <h2 style="margin: 0 0 10px 0; color: #1e293b; font-weight: 700;">KET 听力录音工作台</h2>
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
            progress_cb(f"正在录制题干导语...", 0.1)
        q_pcm = await process_question_text(question_item[0], question_item[1], api_key, speed)
        full_pcm += q_pcm
        step_idx += 1

    dialogue_pcms = []
    for role, text in dialogue_items:
        step_idx += 1
        pct = 0.1 + 0.7 * (step_idx / max(1, total_steps))
        if progress_cb:
            progress_cb(f"正在录制角色 [{role}]...", pct)
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
        progress_cb("正在执行双遍母带对齐与缝合...", 0.9)

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

def generate_excel_template():
    """Generate an in-memory sample Excel template for users to download."""
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
        },
        {
            "文件名": "KET_BA_F17_PART4_3.mp3",
            "题目标题": "F17 Part 4 题3 (课堂作业)",
            "完整台词剧本": """Man_N|neutral|: <#6#>You will hear a teacher talking to her class. What should the students bring tomorrow?<#2#>
Woman|friendly|: Remember that tomorrow we will work on our science posters. Please make sure to bring your colored pens and a pair of scissors.<#2#>"""
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

# Sidebar Navigation
with st.sidebar:
    st.markdown("### 🎙️ 录音机与母带配置")
    api_key = st.text_input("MiniMax API Key", value=DEFAULT_API_KEY, type="password")
    speed = st.slider("录音语速 (Speed)", min_value=0.5, max_value=1.2, value=0.8, step=0.05,
                      help="剑桥官方 KET 听力标准语速建议保持 0.8x")
    
    st.markdown("---")
    st.markdown("#### 🔊 当前角色音量规格")
    st.markdown("""
    - 👩 **Woman (老师/妈妈)**: <span style="color:#d97706; font-weight:700;">2.0x (增强)</span>
    - 👧 **Girl (女孩)**: <span style="color:#2563eb; font-weight:700;">1.0x (标准)</span>
    - 👦 **Boy (男孩)**: <span style="color:#2563eb; font-weight:700;">1.0x (标准)</span>
    - 👨 **Man/Narrator (男声/旁白)**: <span style="color:#2563eb; font-weight:700;">1.0x (标准)</span>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### ⏱️ 数字无声对齐规范")
    st.caption("• 读题开头部物理静音: **6.0s** (`<#6#>`)")
    st.caption("• 角色交替气口间隔: **0.5s** (自动生成)")
    st.caption("• Now listen again 提示音前后: **各 1.5s**")
    st.caption("• 答题结尾缓冲静音: **2.0s** (`<#2#>`)")

    st.markdown("---")
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# Studio Header Banner
st.markdown("""
<div class="studio-header">
    <h1>🎙️ KET / PET 听力音频自动化母带工作台</h1>
    <p>自动化多角色母带合成 · 双遍结构无损对齐 · 绝对数字零底噪物理静音 · 女声防爆音强化标准</p>
    <div class="badge-container">
        <span class="spec-badge green">✓ MiniMax speech-2.6-hd</span>
        <span class="spec-badge highlight">★ 女人音量: 2.0x</span>
        <span class="spec-badge">女孩音量: 1.0x</span>
        <span class="spec-badge">男声音量: 1.0x</span>
        <span class="spec-badge">官方语速: 0.8x</span>
        <span class="spec-badge">双遍自动无缝复用</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_excel, tab_single, tab_batch, tab_help = st.tabs([
    "📊 Excel 批量导入生成",
    "📝 单题精细录制与试听",
    "📦 文本快速批量录制",
    "📖 语法与使用规范"
])

# ----------------- TAB 1: EXCEL BATCH PROCESSING -----------------
with tab_excel:
    st.subheader("📊 Excel 批量导入生成听力音频")
    st.caption("上传整理好的 Excel 文件，系统将自动解析每道题目的台词剧本，批量合成高保真 MP3，并提供打包 ZIP 下载。")

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        st.download_button(
            label="📥 下载标准 Excel 模板",
            data=generate_excel_template(),
            file_name="KET_听力题目导入模板.xlsx",
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
                        fname_val = f"KET_QUESTION_{idx+1}.mp3"
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

                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for idx, (fname, script_text) in enumerate(valid_tasks):
                            status_placeholder.markdown(f"**正在录制第 [{idx+1}/{len(valid_tasks)}] 题**: `{fname}` ...")
                            
                            def row_progress(msg, pct):
                                overall_pct = (idx + pct) / len(valid_tasks)
                                progress_bar.progress(min(0.99, overall_pct))

                            try:
                                mp3_bytes, dur = asyncio.run(
                                    build_audio_master(script_text, api_key, speed, now_listen_pcm, row_progress)
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
                    zip_filename = f"KET_听力批量生成_{now_str}.zip"

                    st.download_button(
                        label=f"📦 一键下载全部音频压缩包 ({zip_filename})",
                        data=zip_buffer,
                        file_name=zip_filename,
                        mime="application/zip",
                        use_container_width=True
                    )

                    # Show synthesis summary
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
        st.subheader("📝 单题台词编辑")
        script_input = st.text_area(
            "输入台词剧本",
            value=SAMPLE_TEXT,
            height=280,
            help="包含角色标识与 <#x#> 静音标记"
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

                try:
                    with st.spinner("正在合成并精密组装中，请稍候..."):
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

# ----------------- TAB 3: TEXT BATCH -----------------
with tab_batch:
    st.subheader("📦 文本批量录制（多题一键生成打包 ZIP）")
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

    batch_input = st.text_area("批量文本剧本输入框", value=BATCH_SAMPLE, height=350)

    if st.button("⚡ 批量极速生成全部音频", type="primary", use_container_width=True):
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
                    batch_status.markdown(f"**[{idx+1}/{len(blocks)}] 正在录制**: `{fname}` ...")
                    
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

# ----------------- TAB 4: HELP & DOCUMENTATION -----------------
with tab_help:
    st.subheader("💡 剧本格式与录音规范说明")
    st.markdown("""
### 1. 角色标识与音量规格
| 角色前缀 | 代表身份 | 对应音色 | 音量倍率 (Volume) | 规范说明 |
| :--- | :--- | :--- | :--- | :--- |
| **`Woman`** | 老师 / 妈妈 / 成年女性 | `clone_voice_narrator` | **2.0 (已增强)** | 增强女生成人声音穿透力，防过载限制 |
| **`Girl`** | 女学生 / 小女孩 | `ttv-voice-...-BvMx9oDR` | **1.0 (标准)** | 保持自然清晰童声 |
| **`Boy`** | 男学生 / 小男孩 | `ttv-voice-...-DQq2kiZd` | **1.0 (标准)** | 少年英式/通用口音 |
| **`Man`** / **`Man_N`** | 男声 / 爸爸 / 听力导语旁白 | `voice_1766653420_c08e99bd` | **1.0 (标准)** | 官方 Cambridge 稳重男中音 |

---

### 2. 停顿控制标记 (`<#秒数#>`)
* `<#6#>`：**物理零气流静音 6.0 秒**（用于题干前留给考生的审题阅读时间）。
* `<#2#>`：**物理零气流静音 2.0 秒**（用于题干播完后缓冲，以及全题双遍答题结束后的终点静音）。

---

### 3. 双遍母带全自动对齐工程
1. **题干导语**：自动解析 `<#6#>` 和 `<#2#>` 注入真实零字节静音。
2. **第一遍对话**：多角色依次发言，交替发言之间自动插入 **0.5s** 自然气口气流间隔。
3. **提示重听**：对话结束后留白 **1.5s** $\\rightarrow$ 播放剑桥官方纯正 `Now listen again` 原声 $\\rightarrow$ 留白 **1.5s**。
4. **第二遍对话**：100% 自动对齐复现第一遍对话，保证母带发音一致性。
5. **结束缓冲**：结尾自动添加 **2.0s** 数字静音收尾。
    """)
