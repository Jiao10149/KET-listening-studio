# 🎧 KET / PET 听力音频自动化工作台 (Cloud Deployment Guide)

## 快速免费云端部署步骤（2分钟完成）

### 推荐方式：部署到 Streamlit Community Cloud (永久免费、24小时公网在线)

1. **第一步：推送到 GitHub 仓库**
   - 登录 [GitHub](https://github.com/)，点击右上角 **New repository**，仓库名填 `ket-listening-studio`（设为 Public 或 Private 均可）。
   - 在本地终端运行以下命令完成推送：
     ```bash
     cd /Users/fengjiao/Documents/Antigravity/ket-listening-studio
     git remote add origin https://github.com/你的GitHub用户名/ket-listening-studio.git
     git branch -M main
     git push -u origin main
     ```

2. **第二步：一键上线**
   - 打开 [Streamlit Community Cloud](https://share.streamlit.io/)，用 GitHub 账号登录。
   - 点击 **Create app** $\rightarrow$ 选择你的仓库 `ket-listening-studio` $\rightarrow$ Main file 填 `app.py`。
   - 点击 **Deploy**！

3. **第三步：分享给异地同事**
   - 1分钟后部署完成，平台会生成一个专属的公网链接（如 `https://ket-listening-studio.streamlit.app`）。
   - 把链接和团队访问密码（默认：`ket2026`）发给异地同事，大家在各自电脑或手机浏览器打开就能直接用！

---

## 本地快速双击启动
在您自己的 Mac 桌面上，双击 **【启动听力录音工作台.command】** 即可在本地浏览器快速打开工作台。
