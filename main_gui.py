媒体归类工具 GUI版
- 自动区分照片/视频，按 YYYY-MM-DD 文件夹归类
- 照片：优先读取 EXIF 原始拍摄时间（支持 HEIC 苹果照片），无EXIF则按文件修改时间归类
- 视频：按文件修改时间归类（零外部依赖，无需额外工具）
- 默认复制文件，不移动原始素材，安全防误删
"""
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import pillow_heif
import shutil
import datetime
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# 注册HEIC/HEIF支持（苹果照片），使Pillow能读取其EXIF拍摄时间
pillow_heif.register_heif_opener()

# ===================== 媒体配置常量 =====================
PHOTO_SUFFIX = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff", ".bmp"}
VIDEO_SUFFIX = {".mp4", ".mov", ".mkv", ".avi"}

# ===================== 界面主题色 =====================
COLOR_BG = "#EEF2F7"          # 窗口背景（浅灰蓝）
COLOR_CARD = "#FFFFFF"        # 卡片背景（白）
COLOR_PRIMARY = "#1E88E5"     # 主色（蓝）
COLOR_PRIMARY_DARK = "#1565C0"
COLOR_PRIMARY_LIGHT = "#E3F2FD"
COLOR_GREEN = "#2E9E5B"       # 开始按钮绿
COLOR_GREEN_DARK = "#23804A"
COLOR_TEXT = "#263238"        # 主文字
COLOR_TEXT_SUB = "#78909C"    # 次要文字
COLOR_BORDER = "#D9E2EC"     # 边框


def find_icon_path():
    """查找icon.ico：源码运行读同目录；打包运行读解压目录"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        cand = Path(sys._MEIPASS) / "icon.ico"
    else:
        cand = Path(__file__).parent / "icon.ico"
    return str(cand) if cand.exists() else ""


def get_image_exif_datetime(img_path: Path):
    """
    读取图片EXIF原始拍摄时间 DateTimeOriginal
    返回 YYYY-MM-DD，读取失败/无EXIF返回 None
    """
    try:
        with Image.open(img_path) as im:
            exif_data = im.getexif()
            if not exif_data:
                return None
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == "DateTimeOriginal":
                    # EXIF 格式示例：2026:10:10 14:30:20
                    date_part = value.split(" ")[0]
                    return date_part.replace(":", "-")
    except Exception:
        pass
    return None


def get_file_mtime_date(file_path):
    """兜底：获取文件修改时间，返回 YYYY-MM-DD"""
    file_path = Path(file_path)
    mtime = file_path.stat().st_mtime
    dt = datetime.datetime.fromtimestamp(mtime)
    return dt.strftime("%Y-%m-%d")


class MediaSorterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("媒体归类工具｜照片视频按年月日自动分类")
        self.root.geometry("780x660")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        # 窗口图标
        icon_path = find_icon_path()
        if icon_path:
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # 变量
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.preview_mode = tk.BooleanVar(value=True)
        self.recursive = tk.BooleanVar(value=True)
        self.log_content = []  # 缓存全部日志文本，用于保存txt

        # 字体
        F_TITLE = ("Microsoft YaHei UI", 17, "bold")
        F_SUB = ("Microsoft YaHei UI", 10)
        F_BODY = ("Microsoft YaHei UI", 10)
        F_BTN = ("Microsoft YaHei UI", 11, "bold")
        F_LOG = ("Consolas", 9)

        # ========== 顶部横幅 ==========
        banner = tk.Frame(root, bg=COLOR_PRIMARY, height=64)
        banner.pack(fill=tk.X)
        banner.pack_propagate(False)
        tk.Label(banner, text="媒体归类工具", bg=COLOR_PRIMARY, fg="#FFFFFF",
                 font=F_TITLE).pack(side=tk.LEFT, padx=(20, 8), pady=14)
        tk.Label(banner, text="照片视频 · 按年月日自动分类", bg=COLOR_PRIMARY,
                 fg="#BBDEFB", font=F_SUB).pack(side=tk.LEFT, pady=16)

        # ========== 主内容区 ==========
        main = tk.Frame(root, bg=COLOR_BG, padx=24, pady=18)
        main.pack(fill=tk.BOTH, expand=True)

        # ---------- 输入卡片 ----------
        card = tk.Frame(main, bg=COLOR_CARD, highlightthickness=1,
                        highlightbackground=COLOR_BORDER, highlightcolor=COLOR_BORDER)
        card.pack(fill=tk.X, pady=(0, 14))

        # 源目录行
        row1 = tk.Frame(card, bg=COLOR_CARD)
        row1.pack(fill=tk.X, padx=16, pady=(16, 8))
        tk.Label(row1, text="📂 源媒体文件夹", bg=COLOR_CARD, fg=COLOR_TEXT,
                 font=F_BODY, width=12, anchor="w").pack(side=tk.LEFT)
        self.entry_src = tk.Entry(row1, textvariable=self.src_dir, bg="#FAFBFD",
                                  fg=COLOR_TEXT, relief="solid", bd=1,
                                  highlightthickness=0, font=F_BODY)
        self.entry_src.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        tk.Button(row1, text="浏览…", command=self.select_src, font=F_BODY,
                  bg=COLOR_PRIMARY_LIGHT, fg=COLOR_PRIMARY_DARK,
                  activebackground="#D6E9FB", activeforeground=COLOR_PRIMARY_DARK,
                  relief="flat", bd=0, padx=14, pady=4, cursor="hand2"
                  ).pack(side=tk.LEFT, padx=(10, 0))

        # 输出目录行
        row2 = tk.Frame(card, bg=COLOR_CARD)
        row2.pack(fill=tk.X, padx=16, pady=(0, 16))
        tk.Label(row2, text="📁 输出归类文件夹", bg=COLOR_CARD, fg=COLOR_TEXT,
                 font=F_BODY, width=12, anchor="w").pack(side=tk.LEFT)
        tk.Entry(row2, textvariable=self.dst_dir, bg="#FAFBFD", fg=COLOR_TEXT,
                 relief="solid", bd=1, highlightthickness=0, font=F_BODY
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        tk.Button(row2, text="浏览…", command=self.select_dst, font=F_BODY,
                  bg=COLOR_PRIMARY_LIGHT, fg=COLOR_PRIMARY_DARK,
                  activebackground="#D6E9FB", activeforeground=COLOR_PRIMARY_DARK,
                  relief="flat", bd=0, padx=14, pady=4, cursor="hand2"
                  ).pack(side=tk.LEFT, padx=(10, 0))

        # ---------- 选项行 ----------
        opt_card = tk.Frame(main, bg=COLOR_CARD, highlightthickness=1,
                            highlightbackground=COLOR_BORDER)
        opt_card.pack(fill=tk.X, pady=(0, 14))
        self.chk_preview = tk.Checkbutton(
            opt_card, text="预览模式（只输出日志，不复制文件）",
            variable=self.preview_mode, bg=COLOR_CARD, fg=COLOR_TEXT,
            activebackground=COLOR_CARD, activeforeground=COLOR_TEXT,
            selectcolor=COLOR_CARD, font=F_BODY, anchor="w"
        )
        self.chk_preview.pack(side=tk.LEFT, padx=16, pady=10)
        self.chk_recursive = tk.Checkbutton(
            opt_card, text="递归扫描子文件夹",
            variable=self.recursive, bg=COLOR_CARD, fg=COLOR_TEXT,
            activebackground=COLOR_CARD, activeforeground=COLOR_TEXT,
            selectcolor=COLOR_CARD, font=F_BODY, anchor="w"
        )
        self.chk_recursive.pack(side=tk.LEFT, padx=8, pady=10)

        # ---------- 开始按钮 ----------
        self.start_btn = tk.Button(
            main, text="▶  开始归类", command=self.start_sort,
            bg=COLOR_GREEN, fg="#FFFFFF", font=F_BTN,
            activebackground=COLOR_GREEN_DARK, activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=40, pady=12, cursor="hand2"
        )
        self.start_btn.pack(fill=tk.X, pady=(0, 14))

        # ---------- 进度区 ----------
        prog_row = tk.Frame(main, bg=COLOR_BG)
        prog_row.pack(fill=tk.X, pady=(0, 10))
        tk.Label(prog_row, text="📊 处理进度", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=F_BODY).pack(side=tk.LEFT)
        self.progress_var = tk.DoubleVar(value=0.0)
        style = ttk.Style()
        try:
            style.theme_use("clam")
            style.configure("PBar.Horizontal.TProgressbar",
                            troughcolor="#E3EAF1", background=COLOR_PRIMARY,
                            bordercolor=COLOR_BORDER, lightcolor=COLOR_PRIMARY,
                            darkcolor=COLOR_PRIMARY)
        except Exception:
            pass
        self.progress_bar = ttk.Progressbar(
            prog_row, variable=self.progress_var, maximum=100,
            style="PBar.Horizontal.TProgressbar", length=500
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.progress_label = tk.Label(prog_row, text="0%", bg=COLOR_BG,
                                       fg=COLOR_TEXT_SUB, font=("Consolas", 9))
        self.progress_label.pack(side=tk.LEFT, padx=(8, 0))

        # ---------- 日志区 ----------
        tk.Label(main, text="📜 运行日志", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=F_BODY).pack(anchor="w", pady=(0, 6))
        log_frame = tk.Frame(main, bg=COLOR_CARD, highlightthickness=1,
                             highlightbackground=COLOR_BORDER)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=12, width=88,
            font=F_LOG, bg="#FAFBFD", fg=COLOR_TEXT,
            relief="flat", bd=0, wrap="word"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # ---------- 底部状态栏 ----------
        status = tk.Frame(root, bg="#E2E8F0", height=26)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)
        tk.Label(status, text="零外部依赖 · 复制模式安全（不移动原文件） · 日志自动保存",
                 bg="#E2E8F0", fg=COLOR_TEXT_SUB,
                 font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=14, pady=4)

        # 启动提示
        self._show_startup_hint()

    # ---------------- 日志 ----------------
    def log(self, msg: str):
        """写入日志：同时存入内存缓存 + 界面文本框"""
        self.log_content.append(str(msg))
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, str(msg) + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def _show_startup_hint(self):
        self.log_text.config(state=tk.NORMAL)
        hint = ("使用说明：照片优先EXIF拍摄时间，无EXIF按文件修改时间归类；"
                "视频按文件修改时间归类。\n建议先用预览模式核对，确认后再正式复制。\n")
        self.log_text.insert(tk.END, hint)
        self.log_text.config(state=tk.DISABLED)

    def save_log_to_file(self, output_folder: Path):
        """将本次日志保存到输出目录 sort_log.txt"""
        log_file = output_folder / "sort_log.txt"
        try:
            full_text = "\n".join(self.log_content)
            log_file.write_text(full_text, encoding="utf-8")
            self.log(f"\n✅ 日志已保存至：{log_file.resolve()}")
        except Exception as e:
            self.log(f"\n❌ 日志保存失败：{str(e)}")

    # ---------------- 交互 ----------------
    def select_src(self):
        path = filedialog.askdirectory(title="选择存放照片视频的源文件夹")
        if path:
            self.src_dir.set(path)

    def select_dst(self):
        path = filedialog.askdirectory(title="选择归类结果输出文件夹")
        if path:
            self.dst_dir.set(path)

    # ---------------- 核心流程 ----------------
    def start_sort(self):
        src_str = self.src_dir.get().strip()
        dst_str = self.dst_dir.get().strip()
        preview = self.preview_mode.get()
        recursive = self.recursive.get()

        if not src_str or not dst_str:
            messagebox.showerror("错误", "请先选择源文件夹和输出文件夹！")
            return
        src = Path(src_str)
        if not src.exists():
            messagebox.showerror("错误", "源文件夹不存在！")
            return

        # 重置界面状态
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_content.clear()
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        self.start_btn.config(state=tk.DISABLED, bg="#9E9E9E")

        self.log("===== 第一步：预扫描，统计媒体文件数量 =====")
        self.root.update()

        target_root = Path(dst_str)
        # 排除输出目录内的归类产物（输出目录位于源目录内部时，避免重复扫描已归类文件）
        exclude_dirs = [target_root / "photo", target_root / "video"]

        # 预扫描收集所有媒体文件，并统计非媒体文件数量
        media_file_list = []
        total_files = 0
        file_iter = src.rglob("*") if recursive else src.iterdir()
        for f in file_iter:
            if not f.is_file():
                continue
            if any(ed in f.parents for ed in exclude_dirs):
                continue
            total_files += 1
            suffix = f.suffix.lower()
            if suffix in PHOTO_SUFFIX or suffix in VIDEO_SUFFIX:
                media_file_list.append(f)

        total_media = len(media_file_list)
        non_media = total_files - total_media
        self.log(f"扫描文件总数：{total_files}，其中媒体文件：{total_media} 个，非媒体文件：{non_media} 个（已忽略）")
        if total_media == 0:
            self.log("未找到任何图片/视频文件！")
            self.save_log_to_file(Path(dst_str))
            self.start_btn.config(state=tk.NORMAL, bg=COLOR_GREEN,
                                  activebackground=COLOR_GREEN_DARK)
            messagebox.showwarning("提示", "未扫描到支持的照片/视频！")
            return

        self.log("===== 第二步：开始处理媒体 =====")
        self.log(f"源目录：{src_str}")
        self.log(f"输出目录：{dst_str}")
        self.log(f"预览模式：{preview}")
        self.log(f"递归扫描：{recursive}")
        self.log("时间规则：照片优先EXIF拍摄时间，无EXIF按文件修改时间；视频按文件修改时间")

        target_root.mkdir(exist_ok=True)

        ok_cnt = 0
        skip_cnt = 0

        for idx, f in enumerate(media_file_list):
            suffix = f.suffix.lower()

            if suffix in PHOTO_SUFFIX:
                media_type = "photo"
                date_str = get_image_exif_datetime(f)
                if date_str is None:
                    # 无EXIF（截图/聊天传输图片常见）：修改时间即真实拍摄时间，按修改时间归类
                    date_str = get_file_mtime_date(f)
                    target_sub = target_root / media_type / date_str
                    note = "【无EXIF，按修改时间】"
                else:
                    target_sub = target_root / media_type / date_str
                    note = ""
            else:
                # 视频：按文件修改时间归类到具体日期
                media_type = "video"
                date_str = get_file_mtime_date(f)
                target_sub = target_root / media_type / date_str
                note = "【视频按文件修改时间】"

            target_sub.mkdir(parents=True, exist_ok=True)
            dest = target_sub / f.name
            if dest.exists():
                skip_cnt += 1
                self.log(f"[跳过] {f.name} 目标文件已存在")
            else:
                if preview:
                    self.log(f"[预览] {media_type:6s} | {f.name} → {target_sub.relative_to(target_root)} {note}")
                else:
                    shutil.copy2(f, dest)
                    ok_cnt += 1
                    self.log(f"[复制] {media_type:6s} | {f.name} → {target_sub.relative_to(target_root)} {note}")

            # 更新进度条
            progress_pct = (idx + 1) / total_media * 100
            self.progress_var.set(progress_pct)
            self.progress_label.config(text=f"{int(progress_pct)}%")
            self.root.update()

        self.log("\n===== 任务完成 =====")
        self.log(f"扫描媒体总数：{total_media}")
        self.log(f"成功复制：{ok_cnt}")
        self.log(f"跳过文件：{skip_cnt}")
        if preview:
            self.log("⚠️ 当前是预览模式，没有实际复制文件！取消勾选预览模式再执行！")

        # 保存日志文件
        self.save_log_to_file(target_root)

        self.start_btn.config(state=tk.NORMAL, bg=COLOR_GREEN,
                              activebackground=COLOR_GREEN_DARK)
        messagebox.showinfo("完成", "媒体归类任务执行完毕！\n日志已自动保存到输出目录 sort_log.txt")


if __name__ == "__main__":
    root = tk.Tk()
    app = MediaSorterGUI(root)
    root.mainloop()
