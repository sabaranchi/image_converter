import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image
import logging
from tkinterdnd2 import DND_FILES, TkinterDnD
import json

# ログ設定
logging.basicConfig(filename='conversion.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

DEFAULT_FORMAT = 'jpg'

# 拡張子ごとの変換可能形式
conversion_map = {
    'png': ['jpg', 'webp', 'bmp', 'avif'],
    'bmp': ['jpg', 'png', 'webp', 'avif'],
    'webp': ['jpg', 'png', 'avif'],
    'tiff': ['jpg', 'png', 'avif'],
    'jpeg': ['png', 'webp', 'avif'],
    'jpg': ['png', 'webp', 'avif'],
    'avif': ['jpg', 'png'],
    'heic': ['jpg', 'png'],
    'ico': ['png', 'jpg'],
    'tga': ['jpg', 'png']
}

format_map = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
    'bmp': 'BMP',
    'tiff': 'TIFF',
    'avif': 'AVIF',
    'ico': 'ICO',
    'tga': 'TGA'
}

SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.avif', '.heic', '.ico', '.tga')

def save_config(config):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"output_dir": "", "quality": 85, "conversion_rules": {}}

class ImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("画像形式変換ツール")
        self.root.geometry("400x350")
        self.root.minsize(400, 350)
        self.image_paths = []
        
        # tkinter 変数を定義する
        self.src_format = tk.StringVar()
        self.dst_format = tk.StringVar()
        self.quality = tk.IntVar(value=85)
        self.output_dir = tk.StringVar()

        # 設定ファイルを読み込んで tkinter 変数に反映
        self.config = load_config()
        self.output_dir.set(self.config.get("output_dir", ""))
        self.quality.set(self.config.get("quality", 85))
        self.conversion_rules = self.config.get("conversion_rules", {})

        self.create_widgets()
        self.root.bind("<Escape>", lambda event: self.root.quit())

    def create_widgets(self):
        # ドラッグ＆ドロップ領域
        drop_frame = tk.LabelFrame(self.root, text="画像をドロップ", padx=10, pady=10)
        drop_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.drop_area = tk.Listbox(drop_frame, height=6)
        self.drop_area.pack(fill="both", expand=True)

        # ドラッグ＆ドロップ対応
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind('<<Drop>>', self.handle_drop)

        # 中央揃え用のラッパーフレーム
        center_frame = tk.Frame(self.root)
        center_frame.pack(pady=10)

        file_frame = tk.Frame(center_frame)
        file_frame.pack(pady=5)
        # ファイル追加ボタン
        tk.Button(file_frame, text="画像を追加", command=self.add_files).pack(side="left", padx=8)
        #変換ルール編集
        tk.Button(file_frame, text="変換ルール編集", command=self.open_rule_editor).pack(side="left", padx=5)

        # 品質スライダー
        quality_frame = tk.Frame(center_frame)
        quality_frame.pack(pady=5)
        tk.Label(quality_frame, text="品質（JPEG/WebP）:").pack(side="left", padx=5)
        # スライダーの保存は「動作終了後」に限定
        def on_quality_release(event):
            self.save_current_config()

        slider = tk.Scale(quality_frame, from_=10, to=100, orient="horizontal", variable=self.quality, length=150)
        slider.pack(side="left")
        slider.bind("<ButtonRelease-1>", on_quality_release)  # マウスボタン離したときに保存

        # 保存先フォルダ
        output_frame = tk.Frame(center_frame)
        output_frame.pack(pady=5, fill="x")
        tk.Label(output_frame, text="保存先:").pack(side="left", padx=5)
        tk.Label(output_frame, textvariable=self.output_dir, anchor="w", width=30, wraplength=300).pack(side="left", padx=5)
        tk.Button(output_frame, text="選択", command=self.select_output_dir).pack(side="left")
        
        # 実行ボタン
        tk.Button(self.root, text="変換実行", command=self.convert_images).pack(pady=10)

        # 変更元形式が選択されたら変更先形式を更新
        self.src_format.trace_add("write", self.update_dst_options)

    # GUIで変換ルールを編集
    def open_rule_editor(self):
        editor = tk.Toplevel(self.root)
        editor.title("変換ルール編集")
        editor.geometry("260x320")
        editor.minsize(260, 320)
        # root の位置を取得して、少し上に表示
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        editor.geometry(f"+{root_x}+{root_y}")

        tree = ttk.Treeview(editor, columns=("src", "dst"), show="headings", selectmode="browse")
        tree.heading("src", text="変更元")
        tree.heading("dst", text="変更先")
        tree.column("src", width=150)
        tree.column("dst", width=150)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # 初期表示
        for src, dst in self.conversion_rules.items():
            tree.insert("", "end", values=(src, dst))

        # 入力欄（プルダウン式）
        input_frame = tk.Frame(editor)
        input_frame.pack(pady=5)

        tk.Label(input_frame, text="変更元:").grid(row=0, column=0)
        src_combo = ttk.Combobox(input_frame, values=list(conversion_map.keys()), width=10, state="readonly")
        src_combo.grid(row=0, column=1)

        tk.Label(input_frame, text="変更先:").grid(row=0, column=2)
        dst_combo = ttk.Combobox(input_frame, values=[], width=10, state="readonly")
        dst_combo.grid(row=0, column=3)

        # 変更元が選ばれたら、対応する変更先候補を表示
        def update_dst_options(*args):
            src = src_combo.get().lower()
            dst_options = conversion_map.get(src, [DEFAULT_FORMAT])
            dst_combo['values'] = dst_options
            if dst_options:
                dst_combo.set(dst_options[0])

        src_combo.bind("<<ComboboxSelected>>", update_dst_options)

        # ボタン群
        btn_frame = tk.Frame(editor)
        btn_frame.pack(pady=5)

        def add_rule():
            src = src_combo.get().strip().lower()
            dst = dst_combo.get().strip().lower()
            if src and dst:
                self.conversion_rules[src] = dst
                tree.insert("", "end", values=(src, dst))
                src_combo.delete(0, tk.END)
                dst_combo.delete(0, tk.END)
                self.save_current_config()


        def delete_rule():
            selected = tree.selection()
            if selected:
                values = tree.item(selected[0], "values")
                src = values[0]
                if src in self.conversion_rules:
                    del self.conversion_rules[src]
                tree.delete(selected[0])
                self.save_current_config()

        tk.Button(btn_frame, text="＋追加", command=add_rule).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="−削除", command=delete_rule).grid(row=0, column=1, padx=5)

    def save_current_config(self):
        config = {
            "output_dir": self.output_dir.get(),
            "quality": self.quality.get(),
            "conversion_rules": self.conversion_rules
        }
        save_config(config)

    def handle_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        for f in files:
            if os.path.isfile(f) and f.lower().endswith(SUPPORTED_EXTENSIONS):
                if f not in self.image_paths:
                    self.image_paths.append(f)
                    self.drop_area.insert(tk.END, os.path.basename(f))
                    
    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.avif *.heic *.ico *.tga")])
        for f in files:
            if os.path.isfile(f) and f.lower().endswith(SUPPORTED_EXTENSIONS):
                if f not in self.image_paths:
                    self.image_paths.append(f)
                    self.drop_area.insert(tk.END, os.path.basename(f))

    def select_output_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)
            self.save_current_config()

    def update_dst_options(self, *args):
        src = self.src_format.get().lower()
        options = conversion_map.get(src, [DEFAULT_FORMAT])
        self.dst_menu['values'] = options
        if options:
            self.dst_format.set(options[0])

    def convert_images(self):
        if not self.image_paths:
            messagebox.showerror("エラー", "画像が選択されていません")
            return
        if not self.output_dir.get():
            messagebox.showerror("エラー", "保存先フォルダが選択されていません")
            return

        src_ext = self.src_format.get().lower() if self.src_format.get() else None
        dst_ext = self.dst_format.get().lower() if self.dst_format.get() else DEFAULT_FORMAT

        rules = self.conversion_rules
        for path in self.image_paths:
            try:
                ext = os.path.splitext(path)[1][1:].lower()
                dst_ext = rules.get(ext, DEFAULT_FORMAT)
                format_name = format_map.get(dst_ext, dst_ext.upper())

                base_name = os.path.splitext(os.path.basename(path))[0]
                dst_path = os.path.join(self.output_dir.get(), f"{base_name}.{dst_ext}")

                with Image.open(path) as img:
                    img = img.convert("RGB")
                    save_kwargs = {}
                    if dst_ext in ['jpg', 'jpeg', 'webp']:
                        save_kwargs['quality'] = self.quality.get()
                        save_kwargs['optimize'] = True
                    img.save(dst_path, format_name, **save_kwargs)

                logging.info(f"✅ {path} → {dst_path}")
            except Exception as e:
                logging.error(f"❌ {path} の変換に失敗: {e}")

        messagebox.showinfo("完了", "変換が完了しました")


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ImageConverterApp(root)
    root.mainloop()