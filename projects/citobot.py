"""
Citobot - polished local LM Studio chatbot with Sidebar, Token Meter, Selectable Text, Prompt Queueing, Meaningful Filenames, Thread Guards, and Clean Scroll Behavior
Requirements: python -m pip install requests
Run: python citobot.py

LM Studio OpenAI-compatible server defaults to http://localhost:1235/v1.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
import os
import re
import requests

# ------------------------------ Theme & Paths --------------------------------
BG = "#100b18"
PANEL = "#1b1226"
PANEL_2 = "#241631"
BORDER = "#382448"
PURPLE = "#8b5cf6"
PURPLE_HOVER = "#a78bfa"
LAVENDER = "#e9ddff"
MUTED = "#b7a6ca"
USER_BUBBLE = "#492878"
AI_BUBBLE = "#21182d"
ERROR_BUBBLE = "#3b1726"
GREEN = "#86efac"

# Custom saved chat history path
HISTORY_DIR = r"C:\Users\cito\Documents\Cline\projects\Citobot Chats"


class Citobot:
    def __init__(self, root):
        self.root = root
        self.root.title("Citobot")
        self.root.geometry("1250x800")
        self.root.minsize(950, 650)
        self.root.configure(bg=BG)

        self.api_url = "http://localhost:1235/v1"
        self.history = []
        self.prompt_queue = []
        self.current_filename = None
        self.busy = False
        self.request_token = 0
        
        self.model_var = tk.StringVar(value="Loading models…")
        self.temperature_var = tk.DoubleVar(value=0.7)
        self.max_tokens_var = tk.IntVar(value=8192)
        self.status_var = tk.StringVar(value="Connecting to LM Studio…")
        self.token_count_var = tk.StringVar(value="Tokens: 0")
        self.queue_status_var = tk.StringVar(value="")
        self._bubble_widgets = []

        os.makedirs(HISTORY_DIR, exist_ok=True)

        self._configure_styles()
        self._build_layout()
        self.root.after(350, self.refresh_models)
        self.refresh_saved_chats_list()

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Citobot.TCombobox",
            fieldbackground=PANEL_2,
            background=PURPLE,
            foreground=LAVENDER,
            arrowcolor=LAVENDER,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(8, 7),
        )
        style.map(
            "Citobot.TCombobox",
            fieldbackground=[("readonly", PANEL_2), ("!disabled", PANEL_2)],
            foreground=[("readonly", LAVENDER), ("!disabled", LAVENDER)],
            selectbackground=[("readonly", PANEL_2)],
            selectforeground=[("readonly", LAVENDER)],
        )
        style.configure(
            "Citobot.TButton",
            background=PURPLE,
            foreground="white",
            borderwidth=0,
            padding=(12, 9),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Citobot.TButton",
            background=[("active", PURPLE_HOVER), ("disabled", "#49365d")],
            foreground=[("disabled", "#b7a6ca")],
        )
        style.configure(
            "Secondary.TButton",
            background=PANEL_2,
            foreground=LAVENDER,
            borderwidth=1,
            padding=(10, 8),
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Secondary.TButton", background=[("active", BORDER)])

        style.configure(
            "Action.TButton",
            background="#2d1f3d",
            foreground=LAVENDER,
            borderwidth=0,
            padding=(6, 4),
            font=("Segoe UI", 8),
        )
        style.map("Action.TButton", background=[("active", PURPLE)])

    def _build_layout(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        # ---------------- Header ----------------
        header = tk.Frame(self.root, bg=PANEL, height=78)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        brand_area = tk.Frame(header, bg=PANEL)
        brand_area.pack(side="left", padx=22, pady=12)
        tk.Label(
            brand_area, text="✦  CITOBOT", bg=PANEL, fg=LAVENDER,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand_area, text="This shit is not ChatGPT",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(1, 0))

        status_area = tk.Frame(header, bg=PANEL)
        status_area.pack(side="right", padx=22)
        self.status_dot = tk.Label(
            status_area, text="●", bg=PANEL, fg="#fbbf24",
            font=("Segoe UI", 10)
        )
        self.status_dot.pack(side="left", padx=(0, 7))
        tk.Label(
            status_area, textvariable=self.status_var, bg=PANEL,
            fg=MUTED, font=("Segoe UI", 9)
        ).pack(side="left")

        # ---------------- Toolbar ----------------
        toolbar = tk.Frame(self.root, bg=PANEL_2, padx=16, pady=11)
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)

        self._label(toolbar, "MODEL").grid(row=0, column=0, sticky="w", padx=(0, 9))
        self.model_combo = ttk.Combobox(
            toolbar, textvariable=self.model_var, state="readonly",
            style="Citobot.TCombobox", width=28
        )
        self.model_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.model_combo.configure(font=("Segoe UI", 10))

        ttk.Button(
            toolbar, text="↻ Refresh", style="Secondary.TButton",
            command=self.refresh_models
        ).grid(row=0, column=2, padx=(0, 15))

        temp_frame = tk.Frame(toolbar, bg=PANEL_2)
        temp_frame.grid(row=0, column=3, padx=(0, 15))
        self._label(temp_frame, "TEMP:").pack(side="left", padx=(0, 4))
        self.temp_val_label = tk.Label(
            temp_frame, textvariable=self.temperature_var, bg=PANEL_2, fg=PURPLE_HOVER,
            font=("Segoe UI", 9, "bold"), width=3
        )
        self.temp_val_label.pack(side="left", padx=(0, 4))
        self.temp_scale = tk.Scale(
            temp_frame, from_=0.0, to=2.0, resolution=0.1,
            variable=self.temperature_var, orient="horizontal",
            length=90, bg=PANEL_2, fg=LAVENDER, troughcolor="#382448",
            activebackground=PURPLE_HOVER, highlightthickness=0,
            bd=0, sliderrelief="flat", showvalue=False
        )
        self.temp_scale.pack(side="left")

        self._label(toolbar, "TOKENS").grid(row=0, column=4, sticky="w", padx=(0, 7))
        self.token_spin = tk.Spinbox(
            toolbar, from_=256, to=32768, increment=1024,
            textvariable=self.max_tokens_var, width=7,
            bg=PANEL, fg=LAVENDER, insertbackground=LAVENDER,
            buttonbackground=PURPLE, relief="flat",
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=PURPLE, font=("Segoe UI", 10)
        )
        self.token_spin.grid(row=0, column=5, sticky="w", padx=(0, 15))

        self.token_meter_label = tk.Label(
            toolbar, textvariable=self.token_count_var, bg=PANEL, fg=GREEN,
            font=("Segoe UI", 9, "bold"), padx=8, relief="flat"
        )
        self.token_meter_label.grid(row=0, column=6, sticky="e")

        # ---------------- Sidebar for Saved Chats ----------------
        sidebar_frame = tk.Frame(self.root, bg=PANEL, width=220, padx=10, pady=10)
        sidebar_frame.grid(row=2, column=0, sticky="nsew")
        sidebar_frame.grid_propagate(False)
        sidebar_frame.grid_rowconfigure(1, weight=1)
        sidebar_frame.grid_columnconfigure(0, weight=1)

        tk.Label(
            sidebar_frame, text="SAVED CHATS", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.chats_listbox = tk.Listbox(
            sidebar_frame, bg=PANEL_2, fg=LAVENDER, selectbackground=USER_BUBBLE,
            selectforeground=LAVENDER, relief="flat", bd=0, font=("Segoe UI", 9),
            exportselection=False,
            highlightthickness=1, highlightbackground=BORDER
        )
        self.chats_listbox.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        self.chats_listbox.bind("<<ListboxSelect>>", self.load_selected_chat)

        sidebar_btn_frame = tk.Frame(sidebar_frame, bg=PANEL)
        sidebar_btn_frame.grid(row=2, column=0, sticky="ew")
        
        ttk.Button(
            sidebar_btn_frame, text="+ New Chat", style="Secondary.TButton",
            command=self.new_chat
        ).pack(fill="x", pady=(0, 4))
        
        ttk.Button(
            sidebar_btn_frame, text="🗑 Delete Chat", style="Secondary.TButton",
            command=self.delete_current_chat
        ).pack(fill="x")

        # ---------------- Conversation region ----------------
        conversation_shell = tk.Frame(self.root, bg=BG, padx=16, pady=14)
        conversation_shell.grid(row=2, column=1, sticky="nsew")
        conversation_shell.grid_rowconfigure(0, weight=1)
        conversation_shell.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            conversation_shell, bg=BG, bd=0, highlightthickness=0
        )
        self.scrollbar = ttk.Scrollbar(
            conversation_shell, orient="vertical", command=self.canvas.yview
        )
        self.messages_frame = tk.Frame(self.canvas, bg=BG)
        self.messages_window = self.canvas.create_window(
            (0, 0), window=self.messages_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.messages_frame.bind("<Configure>", self._on_messages_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._add_message(
            "assistant",
            "Hey! I’m Citobot, running locally through LM Studio. What would you like to work on?"
        )

        # ---------------- Composer ----------------
        composer_outer = tk.Frame(self.root, bg=PANEL, padx=16, pady=12)
        composer_outer.grid(row=3, column=1, sticky="ew")
        composer_outer.grid_columnconfigure(0, weight=1)
        composer_outer.grid_rowconfigure(0, minsize=82)

        composer = tk.Frame(
            composer_outer, bg=PANEL_2, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=PURPLE
        )
        composer.grid(row=0, column=0, sticky="ew")
        composer.grid_columnconfigure(0, weight=1)

        self.message_input = tk.Text(
            composer, height=3, wrap="word", undo=True,
            bg=PANEL_2, fg=LAVENDER, insertbackground=LAVENDER,
            selectbackground=USER_BUBBLE, relief="flat", bd=0,
            padx=13, pady=12, font=("Segoe UI", 11),
            highlightthickness=0
        )
        self.message_input.grid(row=0, column=0, sticky="nsew", padx=(3, 0), pady=3)
        self.message_input.bind("<Return>", self._enter_to_send)
        self.message_input.bind("<Shift-Return>", self._shift_enter)
        self.message_input.bind("<Control-Return>", self._enter_to_send)

        self.send_button = tk.Button(
            composer, text="SEND  ➤", command=self.send_message,
            bg=PURPLE, fg="white", activebackground=PURPLE_HOVER,
            activeforeground="white", relief="flat", bd=0,
            font=("Segoe UI", 10, "bold"), padx=20, pady=14,
            cursor="hand2", width=11
        )
        self.send_button.grid(row=0, column=1, sticky="ns", padx=7, pady=7)

        helper = tk.Frame(composer_outer, bg=PANEL)
        helper.grid(row=1, column=0, sticky="ew", pady=(7, 0))
        tk.Label(
            helper, text="Enter to send  ·  Shift+Enter for a new line",
            bg=PANEL, fg="#8e7aa5", font=("Segoe UI", 8)
        ).pack(side="left")
        
        self.typing_var = tk.StringVar(value="")
        tk.Label(
            helper, textvariable=self.typing_var,
            bg=PANEL, fg=PURPLE_HOVER, font=("Segoe UI", 8)
        ).pack(side="right")
        
        tk.Label(
            helper, textvariable=self.queue_status_var,
            bg=PANEL, fg=GREEN, font=("Segoe UI", 8, "bold")
        ).pack(side="right", padx=(0, 12))

        # ---------------- Footer ----------------
        footer = tk.Frame(self.root, bg=BG, padx=16)
        footer.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Button(
            footer, text="Clear conversation", style="Secondary.TButton",
            command=self.clear_chat
        ).pack(side="left")
        tk.Label(
            footer,
            text="LOCAL INFERENCE  •  YOUR PROMPTS STAY ON YOUR MACHINE",
            bg=BG, fg="#79668c", font=("Segoe UI", 8)
        ).pack(side="right")

        self.message_input.focus_set()

    @staticmethod
    def _label(parent, text):
        return tk.Label(
            parent, text=text, bg=PANEL_2, fg=MUTED,
            font=("Segoe UI", 8, "bold")
        )

    def _on_messages_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.messages_window, width=event.width)

    def _on_mousewheel(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        if widget and (widget == self.canvas or str(widget).startswith(str(self.messages_frame))):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _scroll_to_message(self, widget_outer):
        # Scrolls just enough to bring the top of the newly added message into clear view
        self.root.update_idletasks()
        try:
            widget_outer.update_idletasks()
            y_pos = widget_outer.winfo_y()
            total_height = self.messages_frame.winfo_height()
            if total_height > 0:
                fraction = max(0.0, min(1.0, y_pos / total_height))
                self.canvas.yview_moveto(fraction)
        except Exception:
            self.canvas.yview_moveto(1.0)

    def _update_token_meter(self):
        total_chars = sum(len(m.get("content", "")) for m in self.history)
        est_tokens = total_chars // 4
        self.token_count_var.set(f"Tokens: ~{est_tokens}")

    def _update_queue_label(self):
        q_len = len(self.prompt_queue)
        if q_len > 0:
            self.queue_status_var.set(f"Queued prompts: {q_len} (Will auto-send)")
        else:
            self.queue_status_var.set("")

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._set_status("Copied to clipboard!", GREEN)

    def _download_text_file(self, text, default_name="code_snippet.txt"):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("All Files", "*.*"), ("Text Files", "*.txt"), ("Python Files", "*.py")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self._set_status(f"Saved to {os.path.basename(file_path)}", GREEN)
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {e}")

    def _create_selectable_text(self, parent, content, bg_color, fg_color, font_tuple, padx=12, pady=6):
        lines = content.split('\n')
        approx_lines = sum(max(1, len(l) // 75) for l in lines) + len(lines) - 1
        
        text_widget = tk.Text(
            parent, bg=bg_color, fg=fg_color, font=font_tuple,
            wrap="word", relief="flat", bd=0, highlightthickness=0,
            height=max(1, approx_lines), padx=padx, pady=pady,
            selectbackground=PURPLE, selectforeground="white"
        )
        text_widget.insert("1.0", content)
        text_widget.configure(state="disabled")
        return text_widget

    def _add_message(self, role, content, error=False):
        outer = tk.Frame(self.messages_frame, bg=BG)
        outer.pack(fill="x", pady=(5, 10), padx=6)

        is_user = role == "user"
        bubble_bg = ERROR_BUBBLE if error else (USER_BUBBLE if is_user else AI_BUBBLE)
        name = "YOU" if is_user else ("CITOBOT  ·  ERROR" if error else "CITOBOT")
        name_color = "#fca5a5" if error else (PURPLE_HOVER if is_user else GREEN)
        time_text = datetime.now().strftime("%I:%M %p")

        side = "right" if is_user else "left"
        bubble = tk.Frame(
            outer, bg=bubble_bg, highlightthickness=1,
            highlightbackground=(BORDER if not is_user else "#65439a")
        )
        bubble.pack(side=side, anchor="e" if is_user else "w", padx=(60, 0) if is_user else (0, 60))

        header = tk.Frame(bubble, bg=bubble_bg)
        header.pack(fill="x", padx=12, pady=(9, 3))
        tk.Label(
            header, text=name, bg=bubble_bg, fg=name_color,
            font=("Segoe UI", 8, "bold")
        ).pack(side="left")
        
        if not is_user and not error:
            action_frame = tk.Frame(header, bg=bubble_bg)
            action_frame.pack(side="right")
            
            copy_btn = ttk.Button(
                action_frame, text="📋 Copy", style="Action.TButton",
                command=lambda c=content: self._copy_to_clipboard(c)
            )
            copy_btn.pack(side="left", padx=(0, 4))

        tk.Label(
            header, text=time_text, bg=bubble_bg, fg="#9582a8",
            font=("Segoe UI", 8)
        ).pack(side="right", padx=(12, 0))

        code_pattern = re.compile(r"```([a-zA-Z]*)\n(.*?)```", re.DOTALL)
        matches = list(code_pattern.finditer(content))

        if matches and not is_user:
            last_idx = 0
            for match in matches:
                start, end = match.span()
                if start > last_idx:
                    text_chunk = content[last_idx:start].strip()
                    if text_chunk:
                        txt_widget = self._create_selectable_text(
                            bubble, text_chunk, bubble_bg, LAVENDER, ("Segoe UI", 10)
                        )
                        txt_widget.pack(fill="x", padx=0, pady=2)

                lang = match.group(1) or "code"
                code_text = match.group(2).strip()

                code_box = tk.Frame(bubble, bg="#161022", highlightthickness=1, highlightbackground=BORDER)
                code_box.pack(fill="x", padx=12, pady=6)

                code_header = tk.Frame(code_box, bg="#1f1630")
                code_header.pack(fill="x", padx=1, pady=1)
                tk.Label(
                    code_header, text=lang.upper(), bg="#1f1630", fg=MUTED,
                    font=("Segoe UI", 8, "bold")
                ).pack(side="left", padx=8, pady=4)

                btn_container = tk.Frame(code_header, bg="#1f1630")
                btn_container.pack(side="right", padx=4, pady=2)

                ttk.Button(
                    btn_container, text="📋 Copy", style="Action.TButton",
                    command=lambda ct=code_text: self._copy_to_clipboard(ct)
                ).pack(side="left", padx=(0, 4))

                ttk.Button(
                    btn_container, text="💾 Download", style="Action.TButton",
                    command=lambda ct=code_text, lg=lang: self._download_text_file(ct, f"snippet.{lg if lg else 'txt'}")
                ).pack(side="left")

                code_widget = self._create_selectable_text(
                    code_box, code_text, "#161022", "#86efac", ("Consolas", 10), padx=12, pady=8
                )
                code_widget.pack(fill="x")

                last_idx = end

            if last_idx < len(content):
                rem_text = content[last_idx:].strip()
                if rem_text:
                    txt_widget = self._create_selectable_text(
                        bubble, rem_text, bubble_bg, LAVENDER, ("Segoe UI", 10)
                    )
                    txt_widget.pack(fill="x", padx=0, pady=2)
        else:
            body = self._create_selectable_text(
                bubble, content, bubble_bg, "#ffdddd" if error else LAVENDER, ("Segoe UI", 10)
            )
            body.pack(fill="x")

        # Scroll to top of this new message block rather than forcing halfway down
        self._scroll_to_message(outer)
        self._update_token_meter()

    # ---------------- Chat Persistence & Meaningful Filenames ----------------
    def _get_filename_from_prompt(self, prompt):
        clean = re.sub(r'[^\w\s]', '', prompt.lower())
        words = clean.split()[:5]
        if not words:
            return "new_chat.json"
        return "_".join(words) + ".json"

    def save_current_chat(self, target_filepath=None, target_history=None):
        history_to_save = target_history if target_history is not None else self.history
        if not history_to_save:
            return
        
        first_user_msg = next((m["content"] for m in history_to_save if m["role"] == "user"), "new_chat")
        
        if target_filepath is None:
            new_filename = self._get_filename_from_prompt(first_user_msg)
            target_path = os.path.join(HISTORY_DIR, new_filename)

            if self.current_filename and self.current_filename != target_path and os.path.exists(self.current_filename):
                try:
                    os.remove(self.current_filename)
                except Exception:
                    pass

            self.current_filename = target_path
        else:
            target_path = target_filepath

        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "preview": first_user_msg[:35] + "...",
            "history": history_to_save
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.refresh_saved_chats_list()

    def refresh_saved_chats_list(self):
        self.chats_listbox.delete(0, tk.END)
        if not os.path.exists(HISTORY_DIR):
            return
        self._sidebar_files = []
        files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
        for f in files:
            filepath = os.path.join(HISTORY_DIR, f)
            try:
                with open(filepath, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    display_text = f"{data.get('preview', f)}"
                    self.chats_listbox.insert(tk.END, display_text)
                    self._sidebar_files.append(filepath)
            except Exception:
                pass

    def load_selected_chat(self, event):
        selection = self.chats_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        if hasattr(self, "_sidebar_files") and idx < len(self._sidebar_files):
            filepath = self._sidebar_files[idx]
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    self.request_token += 1
                    self.busy = False
                    self.send_button.configure(state="normal", text="SEND  ➤", bg=PURPLE)
                    self.typing_var.set("")
                    
                    self.current_filename = filepath
                    self.history = data.get("history", [])
                    self.prompt_queue.clear()
                    self._update_queue_label()
                    
                    for child in self.messages_frame.winfo_children():
                        child.destroy()
                    
                    for msg in self.history:
                        self._add_message(msg["role"], msg["content"])
                    self._set_status("Loaded saved chat", GREEN)
            except Exception as e:
                messagebox.showerror("Error", f"Could not load chat: {e}")

    def new_chat(self):
        self.request_token += 1
        
        if self.history:
            self.save_current_chat()
            
        self.history = []
        self.prompt_queue = []
        self._update_queue_label()
        self.current_filename = None
        self.busy = False
        self.send_button.configure(state="normal", text="SEND  ➤", bg=PURPLE)
        self.typing_var.set("")

        for child in self.messages_frame.winfo_children():
            child.destroy()
        self._add_message("assistant", "Started a new chat session. What's on your mind?")
        self._update_token_meter()

    def delete_current_chat(self):
        self.request_token += 1
        filepath = None
        selection = self.chats_listbox.curselection()
        
        if selection and hasattr(self, "_sidebar_files") and selection[0] < len(self._sidebar_files):
            filepath = self._sidebar_files[selection[0]]
        elif self.current_filename and os.path.exists(self.current_filename):
            filepath = self.current_filename

        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {e}")

        self.history = []
        self.prompt_queue = []
        self._update_queue_label()
        self.current_filename = None
        self.busy = False
        self.send_button.configure(state="normal", text="SEND  ➤", bg=PURPLE)
        self.typing_var.set("")

        for child in self.messages_frame.winfo_children():
            child.destroy()
        self._add_message("assistant", "Chat deleted. What shall we talk about next?")
        self.refresh_saved_chats_list()
        self._set_status("Chat deleted", MUTED)
        self._update_token_meter()

    # ---------------- Models / API ---------------------------------

    def refresh_models(self):
        self.status_var.set("Checking LM Studio…")
        self.status_dot.configure(fg="#fbbf24")

        def worker():
            try:
                response = requests.get(f"{self.api_url}/models", timeout=10)
                response.raise_for_status()
                data = response.json()
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                self.root.after(0, lambda: self._models_loaded(models))
            except Exception as exc:
                message = str(exc)
                self.root.after(0, lambda msg=message: self._set_status(f"LM Studio unavailable: {msg}", "#f87171"))

        threading.Thread(target=worker, daemon=True).start()

    def _models_loaded(self, models):
        if not models:
            self.model_combo["values"] = []
            self.model_var.set("No model loaded")
            self._set_status("No loaded model found in LM Studio", "#fbbf24")
            return

        previous = self.model_var.get()
        self.model_combo["values"] = models
        self.model_var.set(previous if previous in models else models[0])
        self._set_status("Connected to LM Studio", GREEN)

    def _set_status(self, message, color=MUTED):
        self.status_var.set(message)
        self.status_dot.configure(fg=color)

    def _enter_to_send(self, event):
        self.send_message()
        return "break"

    def _shift_enter(self, event):
        self.message_input.insert("insert", "\n")
        return "break"

    def send_message(self):
        prompt = self.message_input.get("1.0", "end-1c").strip()
        if not prompt:
            return

        if self.busy:
            self.prompt_queue.append(prompt)
            self.message_input.delete("1.0", "end")
            self._update_queue_label()
            self._set_status(f"Queued prompt ({len(self.prompt_queue)} in line)", PURPLE_HOVER)
            return

        model = self.model_var.get()
        if not model or model == "No model loaded" or model.startswith("Loading"):
            messagebox.showwarning(
                "No model selected",
                "Load a model in LM Studio, then press Refresh."
            )
            return

        try:
            temperature = float(self.temperature_var.get())
            max_tokens = int(self.max_tokens_var.get())
            max_tokens = max(256, min(32768, max_tokens))
        except (ValueError, tk.TclError):
            messagebox.showwarning("Invalid settings", "Check the temperature and output token values.")
            return

        self.message_input.delete("1.0", "end")
        self.history.append({"role": "user", "content": prompt})
        self._add_message("user", prompt)
        self.save_current_chat()

        self.busy = True
        self.send_button.configure(state="disabled", text="WORKING…", bg="#49365d")
        self.typing_var.set("Citobot is thinking…")
        self._set_status("Generating response…", PURPLE_HOVER)

        self.request_token += 1
        active_token = self.request_token
        active_file = self.current_filename

        thread = threading.Thread(
            target=self._request_response,
            args=(model, temperature, max_tokens, list(self.history[-30:]), active_token, active_file),
            daemon=True
        )
        thread.start()

    def _request_response(self, model, temperature, max_tokens, history_snapshot, token_id, file_id):
        response_text = None
        error_text = None
        try:
            messages = [{
                "role": "system",
                "content": (
                    "You are Citobot, a helpful, thoughtful local AI assistant. "
                    "Answer conversationally and clearly. Use Markdown when useful."
                )
            }]
            messages.extend(history_snapshot)

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }

            response = requests.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                timeout=(10, 300)
            )
            if not response.ok:
                try:
                    details = response.json()
                except ValueError:
                    details = response.text
                raise RuntimeError(f"HTTP {response.status_code}: {details}")

            result = response.json()
            response_text = result["choices"][0]["message"]["content"]
            if not isinstance(response_text, str):
                response_text = str(response_text)
            response_text = response_text.strip()
            if not response_text:
                response_text = "(The model returned an empty response.)"

        except requests.exceptions.ConnectionError:
            error_text = (
                "Could not connect to LM Studio. Verify that its local server is running "
                "at http://localhost:1235 and that the model is loaded."
            )
        except requests.exceptions.Timeout:
            error_text = (
                "The request timed out. A large model or long output may need more time; "
                "check LM Studio's server logs."
            )
        except Exception as exc:
            error_text = f"Request failed: {exc}"

        self.root.after(0, lambda: self._finish_response(response_text, error_text, history_snapshot, token_id, file_id))

    def _finish_response(self, response_text, error_text, history_snapshot, token_id, file_id):
        if token_id == self.request_token:
            if response_text is not None:
                self.history.append({"role": "assistant", "content": response_text})
                self._add_message("assistant", response_text)
                self.save_current_chat()
                self._set_status("Connected · Ready", GREEN)
            elif error_text:
                self._add_message("assistant", error_text, error=True)
                self._set_status("Request error", "#f87171")

            self.busy = False
            self.send_button.configure(state="normal", text="SEND  ➤", bg=PURPLE)
            self.typing_var.set("")
            self.message_input.focus_set()

            if self.prompt_queue:
                next_prompt = self.prompt_queue.pop(0)
                self._update_queue_label()
                self.message_input.insert("1.0", next_prompt)
                self.send_message()
        else:
            if response_text is not None and file_id:
                history_snapshot.append({"role": "assistant", "content": response_text})
                self.save_current_chat(target_filepath=file_id, target_history=history_snapshot)

    def clear_chat(self):
        if self.busy:
            messagebox.showinfo("Please wait", "Citobot is still generating a response.")
            return
        if not messagebox.askyesno("Clear conversation", "Clear all messages from this chat?"):
            return

        self.history.clear()
        self.prompt_queue.clear()
        self._update_queue_label()
        for child in self.messages_frame.winfo_children():
            child.destroy()
        self._add_message("assistant", "Conversation cleared. What shall we talk about next?")
        self._set_status("Connected · Chat cleared", GREEN)
        self.save_current_chat()


def main():
    root = tk.Tk()
    app = Citobot(root)
    root.mainloop()


if __name__ == "__main__":
    main()