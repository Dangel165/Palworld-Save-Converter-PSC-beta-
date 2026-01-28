import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import shutil
import glob
import re
import json
import time 
import uuid
import threading
import logging
import gc
import sys
from datetime import timedelta

# --- 라이브러리 경로 추가 ---
import site
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

# 모든 site-packages 추가
for path in site.getsitepackages():
    if path not in sys.path:
        sys.path.insert(0, path)

# --- 설정 파일 경로 ---
CONFIG_FILE = 'config.json'

# ========================================================
# [라이브러리 호환성 패치 - 강화 버전]
# ========================================================
GvasFile = None
CustomEncoder = None
palworld_type_map = {}

print("[DEBUG] Attempting to load palworld-save-tools...")

# 디버그 로그 파일 생성
debug_log = open('debug_library_load.log', 'w', encoding='utf-8')

def debug_print(msg):
    print(msg)
    debug_log.write(msg + '\n')
    debug_log.flush()

# GvasFile 로드 시도
try:
    from palworld_save_tools.gvas import GvasFile
    debug_print("[DEBUG] GvasFile loaded from palworld_save_tools.gvas")
except ImportError as e:
    debug_print(f"[DEBUG] Failed to load from palworld_save_tools.gvas: {e}")
    try:
        from palworld_save_tools.lib.gvas import GvasFile
        debug_print("[DEBUG] GvasFile loaded from palworld_save_tools.lib.gvas")
    except ImportError as e2:
        debug_print(f"[DEBUG] Failed to load from palworld_save_tools.lib.gvas: {e2}")

# CustomEncoder 로드 시도
try:
    from palworld_save_tools.json_tools import CustomEncoder
    debug_print("[DEBUG] CustomEncoder loaded")
except ImportError as e:
    debug_print(f"[DEBUG] Failed to load CustomEncoder: {e}")
    try:
        from palworld_save_tools.lib.json_tools import CustomEncoder
        debug_print("[DEBUG] CustomEncoder loaded from lib")
    except ImportError as e2:
        debug_print(f"[DEBUG] Failed to load CustomEncoder from lib: {e2}")

# Type map 로드 시도
try:
    from palworld_save_tools.paltypes import PALWORLD_CUSTOM_PROPERTIES as palworld_type_map
    debug_print("[DEBUG] PALWORLD_CUSTOM_PROPERTIES loaded")
except ImportError as e:
    debug_print(f"[DEBUG] Failed to load PALWORLD_CUSTOM_PROPERTIES: {e}")
    try:
        from palworld_save_tools.lib.paltypes import PALWORLD_CUSTOM_PROPERTIES as palworld_type_map
        debug_print("[DEBUG] PALWORLD_CUSTOM_PROPERTIES loaded from lib")
    except ImportError as e2:
        debug_print(f"[DEBUG] Failed to load from lib: {e2}")
        try:
            from palworld_save_tools.paltypes import palworld_gvas_data as palworld_type_map
            debug_print("[DEBUG] palworld_gvas_data loaded")
        except ImportError as e3:
            debug_print(f"[DEBUG] Failed to load palworld_gvas_data: {e3}")

debug_print(f"[DEBUG] Library status: GvasFile={GvasFile is not None}, CustomEncoder={CustomEncoder is not None}, type_map={bool(palworld_type_map)}")
debug_log.close() 

# 싱글 플레이어 호스트 고정 ID
SINGLE_HOST_ID = "00000000000000000000000000000001"

class PalworldMigratorApp:
    def __init__(self, master):
        self.master = master
        master.title("팰월드 세이브 양방향 변환기")
        
        # --- [최종 확장] 창 크기 정의 (1000x1000) ---
        self.window_width = 1000 
        self.window_height = 1000 
        
        master.resizable(False, False) # 크기 조절 방지

        self.mode = tk.IntVar(value=1)
        
        self.src_level_path = tk.StringVar()
        self.src_player_path = tk.StringVar()
        self.tgt_level_path = tk.StringVar()
        
        self.local_root = tk.StringVar()
        self.server_root = tk.StringVar()
        self.selected_world_id = tk.StringVar(value="-")
        
        self.src_player_uid = tk.StringVar(value="-")
        self.tgt_player_uid = tk.StringVar(value="-")
        
        self.log_dir = tk.StringVar()
        self.backup_root_dir = tk.StringVar()
        
        self.player_name = tk.StringVar(value="-")
        self.player_level = tk.StringVar(value="-")
        self.player_time = tk.StringVar(value="-")
        self.player_cache = {} 

        self.is_library_ready = (GvasFile is not None) and (CustomEncoder is not None) and (palworld_type_map != {})
        
        self.load_recent_paths()
        self.initialize_logging()
        
        try:
            self.setup_ui(master)
        except Exception as e:
            logging.error(f"UI 설정 오류: {e}", exc_info=True)
            messagebox.showerror("UI 오류", f"UI를 설정하는 중 오류가 발생했습니다: {e}")
        
        master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 라이브러리 로드 실패 시 경고
        if not self.is_library_ready:
            error_msg = "핵심 라이브러리 로드 실패:\n\n"
            if GvasFile is None:
                error_msg += "❌ GvasFile 로드 실패\n"
            if CustomEncoder is None:
                error_msg += "❌ CustomEncoder 로드 실패\n"
            if palworld_type_map == {}:
                error_msg += "❌ palworld_type_map 로드 실패\n"
            error_msg += "\n해결 방법:\n"
            error_msg += "1. pip uninstall palworld-save-tools\n"
            error_msg += "2. pip install palworld-save-tools\n"
            error_msg += "3. Python 버전 확인 (3.7 이상)\n"
            error_msg += "4. 프로그램 재시작\n\n"
            error_msg += "여전히 오류가 발생하면:\n"
            error_msg += "- 명령 프롬프트에서 다음 실행:\n"
            error_msg += "  pip install --force-reinstall palworld-save-tools"
            messagebox.showerror("라이브러리 오류", error_msg)
            logging.error(f"Library load failed: GvasFile={GvasFile}, CustomEncoder={CustomEncoder}, type_map={bool(palworld_type_map)}")

    def recenter_window(self):
        """창을 화면 중앙에 다시 배치하고, 쏠림 방지를 위해 강제 업데이트합니다."""
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        
        # 1. 계산
        x = (screen_width // 2) - (self.window_width // 2)
        y = (screen_height // 2) - (self.window_height // 2)
        
        # 2. 위치 설정
        self.master.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')
        
        # --- [강화된 쏠림 방지] 화면 업데이트 강제 ---
        self.master.update_idletasks()

    def on_closing(self):
        self.save_recent_paths()
        self.master.destroy()

    def initialize_logging(self):
        log_path = self.log_dir.get()
        if not log_path or not os.path.isdir(log_path):
            log_path = os.getcwd()
            self.log_dir.set(log_path)
        
        log_file = os.path.join(log_path, 'migration.log')
        
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)
            
        try:
            os.makedirs(log_path, exist_ok=True)
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                encoding='utf-8',
                filemode='a'
            )
            logging.info("--- Program Start (Logging Initialized) ---")
        except Exception as e:
            print(f"로그 파일 초기화 실패: {e}. 기본 로깅을 사용합니다.")
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filemode='a')

    def load_recent_paths(self):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.src_level_path.set(config.get('src_level_path', ''))
                self.src_player_path.set(config.get('src_player_path', ''))
                self.tgt_level_path.set(config.get('tgt_level_path', ''))
                self.log_dir.set(config.get('log_dir', os.getcwd()))
                self.backup_root_dir.set(config.get('backup_root_dir', '')) 
        except (FileNotFoundError, json.JSONDecodeError):
            self.log_dir.set(os.getcwd())

    def save_recent_paths(self):
        config = {
            'src_level_path': self.src_level_path.get(),
            'src_player_path': self.src_player_path.get(),
            'tgt_level_path': self.tgt_level_path.get(),
            'log_dir': self.log_dir.get(),
            'backup_root_dir': self.backup_root_dir.get()
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logging.warning(f"Failed to save configuration: {e}")

    def setup_ui(self, master):
        try:
            # 메뉴바 생성
            menubar = tk.Menu(master)
            master.config(menu=menubar)
            
            # 도움말 메뉴
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="도움말", menu=help_menu)
            help_menu.add_command(label="사용 가이드", command=self.show_guide)
            help_menu.add_command(label="FAQ", command=self.show_faq)
            help_menu.add_separator()
            help_menu.add_command(label="정보", command=self.show_about)
            
            main_frame = tk.Frame(master, padx=20, pady=20)
            main_frame.pack(fill='both', expand=True)

            tk.Label(main_frame, text="팰월드 세이브 변환기", font=('Helvetica', 18, 'bold'), fg="#2c3e50").grid(row=0, column=0, columnspan=3, pady=10)

            tk.Label(main_frame, text="작업 모드 선택", font=('Helvetica', 11, 'bold')).grid(row=1, column=0, sticky='w', pady=(10, 0))
            mode_frame = tk.Frame(main_frame, highlightbackground="gray", highlightthickness=1)
            mode_frame.grid(row=2, column=0, columnspan=3, sticky='ew', pady=5, ipady=5)
            
            tk.Radiobutton(mode_frame, text="싱글 → 서버", variable=self.mode, value=1, command=self.reset_uids).pack(side='left', padx=20)
            tk.Radiobutton(mode_frame, text="서버 → 싱글", variable=self.mode, value=2, command=self.reset_uids).pack(side='left', padx=20)
            
            # --- 입력 필드 너비 85로 확장 ---
            tk.Label(main_frame, text="1. 원본 Level.sav 파일:", font=('Helvetica', 10, 'bold')).grid(row=3, column=0, sticky='w', pady=5)
            entry1 = tk.Entry(main_frame, textvariable=self.src_level_path, width=85)
            entry1.grid(row=3, column=1, padx=5)
            tk.Button(main_frame, text="파일 찾기", command=lambda: self.browse_file(self.src_level_path, "*.sav")).grid(row=3, column=2)
            self.create_tooltip(entry1, "변환할 원본 월드의 Level.sav 파일을 선택하세요")

            tk.Label(main_frame, text="2. 원본 Player.sav 파일:", font=('Helvetica', 10, 'bold')).grid(row=4, column=0, sticky='w', pady=5)
            entry2 = tk.Entry(main_frame, textvariable=self.src_player_path, width=85)
            entry2.grid(row=4, column=1, padx=5)
            tk.Button(main_frame, text="파일 찾기", command=lambda: self.browse_file(self.src_player_path, "*.sav")).grid(row=4, column=2)
            self.create_tooltip(entry2, "변환할 캐릭터의 Player.sav 파일을 선택하세요")

            tk.Label(main_frame, text="3. 대상 Level.sav 파일:", font=('Helvetica', 10, 'bold')).grid(row=5, column=0, sticky='w', pady=5)
            entry3 = tk.Entry(main_frame, textvariable=self.tgt_level_path, width=85)
            entry3.grid(row=5, column=1, padx=5)
            tk.Button(main_frame, text="파일 찾기", command=lambda: self.browse_file(self.tgt_level_path, "*.sav")).grid(row=5, column=2)
            self.create_tooltip(entry3, "변환 대상 월드의 Level.sav 파일을 선택하세요")
            
            tk.Label(main_frame, text="4. 로그 파일 저장 폴더:", font=('Helvetica', 10, 'bold')).grid(row=6, column=0, sticky='w', pady=5)
            entry4 = tk.Entry(main_frame, textvariable=self.log_dir, width=85)
            entry4.grid(row=6, column=1, padx=5)
            tk.Button(main_frame, text="폴더 찾기", command=lambda: self.browse_directory(self.log_dir, self.initialize_logging)).grid(row=6, column=2)
            self.create_tooltip(entry4, "변환 로그가 저장될 폴더를 선택하세요")

            tk.Label(main_frame, text="5. 백업 파일 저장 루트 폴더:", font=('Helvetica', 10, 'bold')).grid(row=7, column=0, sticky='w', pady=5)
            entry5 = tk.Entry(main_frame, textvariable=self.backup_root_dir, width=85)
            entry5.grid(row=7, column=1, padx=5)
            tk.Button(main_frame, text="폴더 찾기", command=lambda: self.browse_directory(self.backup_root_dir)).grid(row=7, column=2)
            self.create_tooltip(entry5, "백업 파일이 저장될 루트 폴더를 선택하세요 (선택사항)")

            tk.Button(main_frame, text="6. 파일 경로 기반 정보 자동 감지 (필수)", command=self.detect_info, bg='#ecf0f1', font=('Helvetica', 10), height=2).grid(row=8, column=0, columnspan=3, pady=15)

            info_frame = tk.LabelFrame(main_frame, text="변환 대상 및 정보", padx=10, pady=10, font=('Helvetica', 10, 'bold'))
            info_frame.grid(row=9, column=0, columnspan=3, sticky='ew')

            tk.Label(info_frame, text="추론된 월드 ID:").grid(row=0, column=0, sticky='w')
            tk.Label(info_frame, textvariable=self.selected_world_id, fg='purple', font=('Consolas', 10)).grid(row=0, column=1, columnspan=2, sticky='w', pady=(0, 5), padx=5)

            tk.Label(info_frame, text="선택된 캐릭터 ID (From):", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky='w', pady=(5, 5))
            tk.Label(info_frame, textvariable=self.src_player_uid, fg='blue', font=('Consolas', 10)).grid(row=1, column=1, columnspan=2, sticky='w', pady=(5, 5))

            tk.Label(info_frame, text="적용될 대상 ID (To):").grid(row=2, column=0, sticky='w', pady=(5, 5))
            tk.Label(info_frame, textvariable=self.tgt_player_uid, fg='green', font=('Consolas', 10)).grid(row=2, column=1, columnspan=2, sticky='w', pady=(5, 5))
            
            detail_frame = tk.LabelFrame(info_frame, text="선택된 캐릭터 상세 정보", padx=10, pady=10, font=('Helvetica', 9))
            detail_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=(10, 0))
            
            tk.Label(detail_frame, text="이름:", font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky='w', padx=5)
            tk.Label(detail_frame, textvariable=self.player_name, fg='navy').grid(row=0, column=1, sticky='w', padx=5)
            
            tk.Label(detail_frame, text="레벨:", font=('Helvetica', 9, 'bold')).grid(row=0, column=2, sticky='w', padx=15)
            tk.Label(detail_frame, textvariable=self.player_level, fg='navy').grid(row=0, column=3, sticky='w', padx=5)
            
            tk.Label(detail_frame, text="최종 수정 시간:", font=('Helvetica', 9, 'bold')).grid(row=0, column=4, sticky='w', padx=15)
            tk.Label(detail_frame, textvariable=self.player_time, fg='navy').grid(row=0, column=5, sticky='w', padx=5)

            tk.Label(main_frame, text="⚠️ 주의: 데이터 손실 방지를 위해 게임/서버를 반드시 종료하세요. (로그 파일 생성)", fg='red').grid(row=10, column=0, columnspan=3, pady=(10, 0))
            
            self.run_btn = tk.Button(main_frame, text="🚀 7. 변환 시작 (안전 모드)", command=self.start_thread, 
                    bg='#27ae60', fg='white', font=('Helvetica', 14, 'bold'), height=2)
            self.run_btn.grid(row=11, column=0, columnspan=3, pady=10)

            # --- 진행 표시줄 너비 800으로 확장 ---
            self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=800, mode="determinate")
            self.progress.grid(row=12, column=0, columnspan=3, pady=5)

            creator_frame = tk.LabelFrame(main_frame, text="제작자 정보", padx=10, pady=5, font=('Helvetica', 9))
            creator_frame.grid(row=13, column=0, columnspan=3, sticky='ew', pady=(10, 5))

            tk.Label(creator_frame, text="제작자: Dangel", 
                    font=('Helvetica', 9, 'bold')).pack(pady=1, anchor='w')

            self.status_label = tk.Label(main_frame, text="준비됨", relief=tk.SUNKEN, anchor='w', bg="#ffffff")
            self.status_label.grid(row=14, column=0, columnspan=3, sticky='ew', pady=10)
            
        except Exception as e:
            logging.error(f"UI 요소 생성 오류: {e}", exc_info=True)
            raise

    def browse_directory(self, var, callback=None):
        path = filedialog.askdirectory(title="폴더 선택")
        if path:
            var.set(path)
            if callback:
                callback() 

    def browse_file(self, var, filetypes_str):
        file_path = filedialog.askopenfilename(
            title="파일 선택",
            filetypes=[(f"Palworld Save Files ({filetypes_str})", filetypes_str)]
        )
        if file_path:
            var.set(file_path)

    def create_tooltip(self, widget, text):
        """마우스 오버 시 도움말 표시"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=('Arial', 9))
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def read_player_sav_info(self, sav_path):
        """
        플레이어 .sav 파일에서 이름 및 레벨 정보를 추출합니다.
        (Gvas 로딩 오류와 필드 추출 오류를 분리하여 처리)
        """
        uid_raw = os.path.basename(sav_path).replace('.sav', '')
        info = {'name': '❌ 파싱 시작 오류', 'level': '오류', 'time_mtime': os.path.getmtime(sav_path), 'uid': uid_raw.upper()}
        
        # 1. 파일명 유효성 검사
        if not re.match(r'^[0-9A-Fa-f]{32}$', uid_raw):
            info['name'] = '유효하지 않은 파일명'
            return info

        try:
            with open(sav_path, 'rb') as f:
                data = f.read()
            
            # --- 2. GvasFile 읽기 시도 (핵심 로딩) ---
            gvas_file = GvasFile.read(data, palworld_type_map)
            root_props = gvas_file.properties
            info['name'] = '정보 추출 실패'
            info['level'] = '정보 추출 실패'
            
            # 3. 정보 추출 (필드별 예외 처리)
            try:
                # 이름 추출
                name_entry = root_props.get('PlayerName')
                if name_entry and isinstance(name_entry, dict):
                    name_raw = name_entry.get('value', {}).get('value')
                else:
                    name_raw = name_entry
                
                final_name = '알 수 없는 플레이어'
                if name_raw is not None:
                    if isinstance(name_raw, bytes):
                        decoded_name = name_raw.decode('utf-8', errors='ignore').strip('\x00')
                        final_name = decoded_name.strip() if decoded_name.strip() else '이름 없음'
                    elif isinstance(name_raw, str):
                        final_name = name_raw.strip()
                    else:
                        final_name = str(name_raw).strip()
                info['name'] = final_name

                # 레벨 추출
                level_data = root_props.get('SaveData', {}).get('value', {}).get('PlayerCharacterSaveData', {}).get('value', {}).get('Level')
                player_level = '-'
                if level_data and isinstance(level_data, dict) and 'value' in level_data:
                    player_level = str(level_data['value'])
                info['level'] = player_level
            
            except Exception as e:
                # 필드 추출만 실패한 경우 (Gvas 로딩은 성공)
                logging.warning(f"Field extraction failed for {sav_path}: {e}")
                info['name'] = f"필드 추출 실패: {type(e).__name__}"
                info['level'] = '추출 실패'

            del gvas_file 
            gc.collect()
            
        except Exception as e:
            # GvasFile.read 자체에서 오류 발생 시 (파일 구조 문제)
            logging.error(f"FATAL GVAS READ ERROR for {sav_path}: {e}", exc_info=True)
            info['name'] = f"❌ 치명적 GVAS 로딩 오류: {type(e).__name__}"
            info['level'] = '오류'
        
        return info

    def reset_uids(self, preserve_mode=False):
        self.player_cache = {}
        self.local_root.set("-")
        self.server_root.set("-")
        self.selected_world_id.set("-")
        self.src_player_uid.set("-")
        self.tgt_player_uid.set("-")
        self.player_name.set("-")
        self.player_level.set("-")
        self.player_time.set("-")
        if not preserve_mode:
            self.update_status("모드가 변경되었습니다. '정보 자동 감지'를 다시 눌러주세요.")

    def update_status(self, msg, color='black'):
        self.status_label.config(text=f" {msg}", fg=color)
        logging.info(msg)

    def update_progress(self, value):
        self.progress['value'] = value
        self.master.update_idletasks()

    def show_guide(self):
        """사용 가이드 표시"""
        guide_text = """
팰월드 세이브 변환기 - 사용 가이드
=====================================

[1단계] 파일 경로 설정
- 원본 Level.sav: 변환할 원본 월드의 Level.sav 파일
- 원본 Player.sav: 변환할 캐릭터의 Player.sav 파일
- 대상 Level.sav: 변환 대상 월드의 Level.sav 파일

[2단계] 정보 자동 감지
- "파일 경로 기반 정보 자동 감지" 버튼 클릭
- 월드 ID와 캐릭터 정보가 자동으로 감지됨
- 캐릭터 이름, 레벨, 수정 시간 확인

[3단계] 변환 모드 선택
- 싱글 → 서버: 싱글 플레이 세이브를 서버 세이브로 변환
- 서버 → 싱글: 서버 세이브를 싱글 플레이 세이브로 변환

[4단계] 변환 시작
- "변환 시작" 버튼 클릭
- 진행 상황을 진행 표시줄로 모니터링
- 완료 메시지 확인

⚠️ 중요 주의사항:
- 변환 전 게임/서버를 반드시 종료하세요
- 충분한 저장 공간을 확보하세요
- 백업이 자동으로 생성됩니다
- 로그 파일을 확인하여 오류를 파악하세요
        """
        self.show_info_window("사용 가이드", guide_text)

    def show_faq(self):
        """FAQ 표시"""
        faq_text = """
자주 묻는 질문 (FAQ)
====================

Q1: 변환 중에 게임을 시작해도 되나요?
A: 아니요. 변환 중에는 게임/서버를 실행하지 마세요.
   파일이 손상될 수 있습니다.

Q2: 변환에 실패했을 때 어떻게 하나요?
A: 백업 폴더에서 원본 파일을 복구할 수 있습니다.
   로그 파일(migration.log)을 확인하여 오류를 파악하세요.

Q3: 백업 파일은 어디에 저장되나요?
A: 기본적으로 월드 폴더의 Backup 폴더에 저장됩니다.
   커스텀 백업 경로를 설정할 수도 있습니다.

Q4: 변환 후 캐릭터 데이터가 손상되었어요.
A: 백업에서 복구하세요. 로그 파일을 확인하여
   문제를 파악하고 다시 시도하세요.

Q5: 여러 캐릭터를 변환할 수 있나요?
A: 네. 각 캐릭터마다 변환을 반복하면 됩니다.
   각 변환마다 백업이 생성됩니다.

Q6: 변환 속도가 느려요.
A: 파일 크기가 크면 시간이 걸릴 수 있습니다.
   진행 표시줄을 확인하세요.

Q7: 관리자 권한이 필요한가요?
A: 파일 쓰기 권한이 필요합니다.
   필요시 관리자 권한으로 실행하세요.

Q8: 어떤 팰월드 버전을 지원하나요?
A: 최신 버전의 palworld-save-tools를 사용합니다.
   라이브러리를 최신으로 업데이트하세요.
        """
        self.show_info_window("FAQ", faq_text)

    def show_about(self):
        """정보 표시"""
        about_text = """
팰월드 세이브 양방향 변환기
===========================

버전: 1.0.0
라이선스: MIT

제작자: Dangel

주요 기능:
✓ 싱글 ↔ 서버 양방향 변환
✓ 자동 정보 감지
✓ 안전한 백업 시스템
✓ 상세한 로깅
✓ 진행 상황 모니터링

필수 라이브러리:
- palworld-save-tools (0.24.0+)
- Python 3.7+
- Tkinter

설치 방법:
pip install palworld-save-tools

문제 해결:
- 로그 파일(migration.log) 확인
- 게임/서버 완전 종료 확인
- 파일 권한 확인
- 저장 공간 확인

지원:
GitHub: https://github.com/KuraFire/palworld-save-tools
        """
        self.show_info_window("정보", about_text)

    def show_info_window(self, title, text):
        """정보 창 표시"""
        info_window = tk.Toplevel(self.master)
        info_window.title(title)
        info_window.geometry("600x500")
        
        # 텍스트 위젯
        text_frame = tk.Frame(info_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        text_widget = tk.Text(text_frame, wrap='word', yscrollcommand=scrollbar.set, font=('Consolas', 10))
        text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=text_widget.yview)
        
        text_widget.insert('1.0', text)
        text_widget.config(state='disabled')
        
        # 닫기 버튼
        button_frame = tk.Frame(info_window)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(button_frame, text="닫기", command=info_window.destroy, width=20).pack()


    def detect_info(self):
        src_level_path = self.src_level_path.get()
        src_player_path = self.src_player_path.get()
        tgt_level_path = self.tgt_level_path.get()
        mode = self.mode.get()

        if not os.path.exists(src_level_path) or not os.path.exists(src_player_path) or not os.path.exists(tgt_level_path):
            self.update_status("경로가 올바르지 않거나 파일이 존재하지 않습니다.", 'red')
            return
        
        if not src_player_path.endswith('.sav'):
             self.update_status("원본 Player.sav 파일명이 유효하지 않습니다.", 'red')
             return

        self.update_status("파일 경로를 기반으로 월드 정보 및 ID 추론 중...", 'black')
        
        try:
            world_dir = os.path.dirname(src_level_path)
            world_id = os.path.basename(world_dir)
            
            if not re.match(r'^[0-9A-Fa-f]{32}$', world_id):
                self.update_status(f"추론된 월드 폴더 이름('{world_id}')이 유효한 32자리 UUID가 아닙니다. 경로를 확인하세요.", 'red')
                return

            self.selected_world_id.set(world_id)
            src_uid = os.path.basename(src_player_path).replace('.sav', '').upper()
            self.src_player_uid.set(src_uid)
            
            tgt_world_dir = os.path.dirname(tgt_level_path)
            src_root_dir = os.path.dirname(world_dir)
            tgt_root_dir = os.path.dirname(tgt_world_dir)

            if mode == 1:
                self.local_root.set(src_root_dir)
                self.server_root.set(tgt_root_dir)
                
                tgt_player_dir = os.path.join(tgt_world_dir, 'Players')
                new_files = [f for f in glob.glob(os.path.join(tgt_player_dir, '*.sav'))
                            if re.match(r'^[0-9A-Fa-f]{32}\.sav$', os.path.basename(f))]
                
                if new_files:
                    tgt_id = os.path.basename(max(new_files, key=os.path.getmtime)).replace('.sav', '').upper()
                    self.tgt_player_uid.set(tgt_id)
                else:
                    self.update_status(f"경고: 대상 서버 월드({world_id[:8]}...)에 플레이어 파일이 없습니다. 새 캐릭터를 생성했는지 확인하세요.", 'orange')

            else:
                self.server_root.set(src_root_dir)
                self.local_root.set(tgt_root_dir)
                self.tgt_player_uid.set(SINGLE_HOST_ID)

            self.player_cache = {}
            if os.path.exists(src_player_path):
                info = self.read_player_sav_info(src_player_path)
                info['path'] = src_player_path
                info['uid'] = src_uid
                self.player_cache[src_uid] = info
                
                self.player_name.set(info.get('name', '알 수 없음'))
                self.player_level.set(info.get('level', '-'))
                time_str = info.get('time_mtime', '-')
                self.player_time.set(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time_str)) if time_str != '-' else '-')
                
                if '❌' in info.get('name', '') or '오류' in info.get('level', ''):
                     self.update_status(f"⚠️ 정보 감지 완료. 그러나 캐릭터 파일 파싱 오류 발생: {info['name']}. 로그 파일을 확인하세요.", 'red')
                else:
                     self.update_status(f"✅ 정보 감지 완료. 월드 ID: {world_id[:8]}... 캐릭터: {info['name']} (Lv.{info['level']}). '변환 시작'을 누르세요.", 'blue')
            else:
                self.update_status(f"캐릭터 파일({src_player_path})을 찾을 수 없습니다.", 'red')
                self.reset_uids(preserve_mode=True)
            
        except Exception as e:
            self.update_status(f"정보 감지 중 치명적 오류 발생: {type(e).__name__} - {e}", 'red')
            logging.error(f"Detect Error: {e}", exc_info=True)
            
    def start_thread(self): 
        if not self.is_library_ready:
            messagebox.showwarning("경고", "라이브러리 로드 실패\n\n명령 프롬프트를 열고 다음을 실행하세요:\n\npip install --force-reinstall palworld-save-tools\n\n그 후 프로그램을 다시 시작하세요.")
            return

        selected_world = self.selected_world_id.get()
        if selected_world == "-" or not selected_world or not os.path.exists(self.tgt_level_path.get()):
            messagebox.showwarning("경고", "먼저 '정보 자동 감지'를 완료하고 유효한 Level.sav 경로를 확인해주세요.")
            return

        selected_uid = self.src_player_uid.get()
        if selected_uid == "-" or not selected_uid:
            messagebox.showwarning("경고", "먼저 '정보 자동 감지'를 완료하고 변환할 캐릭터 파일을 지정했는지 확인해주세요.")
            return
        
        if '❌' in self.player_name.get() or '오류' in self.player_level.get():
             if not messagebox.askyesno("경고", f"경고: 원본 캐릭터 파일 파싱에 오류가 있었습니다. ({self.player_name.get()})\n\n변환 자체는 ID 치환으로 이루어지므로 작동할 가능성은 있으나, 데이터 손상 가능성이 있습니다. 계속 진행하시겠습니까?"):
                 return

        msg = f"다음 변환을 진행하시겠습니까?\n\n월드 ID: {selected_world[:8]}...\nFROM (원본): {self.player_name.get()} (Lv.{self.player_level.get()})\nTO (대상): {self.tgt_player_uid.get()}\n\n⚠️ 게임/서버가 종료되었는지 다시 한번 확인하세요."
        if not messagebox.askyesno("최종 확인", msg):
            return
        
        self.run_btn.config(state=tk.DISABLED)
        self.update_progress(0)
        
        t = threading.Thread(target=self.process_migration_safe)
        t.start()

    def process_migration_safe(self):
        try:
            self.process_migration_logic()
            self.update_status("🎉 모든 작업이 성공적으로 완료되었습니다!", 'blue')
            messagebox.showinfo("성공", "작업 완료!\n게임을 시작하셔도 됩니다.")
        except FileNotFoundError as e:
            self.update_status(f"❌ 파일 없음 오류: {e}", 'red')
            messagebox.showerror("파일 오류", f"필수 파일이 존재하지 않습니다. 경로 또는 파일 이름을 확인하세요.\n로그 파일(migration.log)을 확인하세요.\n\n내용: {e}")
        except PermissionError as e:
            self.update_status(f"❌ 접근 권한 오류: {e}", 'red')
            messagebox.showerror("권한 오류", f"파일에 접근하거나 쓸 수 없습니다. 관리자 권한으로 실행하거나, 게임/서버를 완전히 종료했는지 확인하세요.\n로그 파일(migration.log)을 확인하세요.\n\n내용: {e}")
        except (json.JSONDecodeError, TypeError) as e:
            self.update_status(f"❌ 데이터 손상 오류: {e}", 'red')
            messagebox.showerror("데이터 오류", f"세이브 파일 내부 데이터 구조에 문제가 있습니다. Level.sav 파일이 손상되었을 수 있습니다.\n로그 파일(migration.log)을 확인하세요.\n\n내용: {e}")
        except Exception as e:
            self.update_status(f"❌ 알 수 없는 오류 발생: {type(e).__name__} - {e}", 'red')
            logging.error(f"Migration Failed: {e}", exc_info=True)
            messagebox.showerror("알 수 없는 오류", f"작업 중 예상치 못한 오류가 발생했습니다.\n로그 파일(migration.log)을 확인하세요.\n\n내용: {e}")
        finally:
            self.run_btn.config(state=tk.NORMAL)
            self.update_progress(100)
            gc.collect()
            
            # --- [최종 수정] 쏠림 방지: 팝업이 닫힌 후 100ms 뒤 재배치 ---
            self.master.after(100, self.recenter_window)


    def process_migration_logic(self):
        if not self.is_library_ready: 
            raise Exception("핵심 변환 라이브러리(palworld-save-tools)가 로드되지 않았습니다.")
        
        source_sav = self.src_player_path.get()
        level_sav_path = self.tgt_level_path.get()
        
        world_id = self.selected_world_id.get() 
        src_id = self.src_player_uid.get()
        tgt_id = self.tgt_player_uid.get()
        mode = self.mode.get()

        working_dir = os.path.dirname(level_sav_path)
        target_sav_path = os.path.join(working_dir, 'Players', f"{tgt_id}.sav")
        
        self.update_progress(10)
        self.update_status("작업 경로 설정 및 파일 유효성 검사 중...", 'black')

        if mode == 2:
            self.update_status("월드 설정/메타데이터 일치를 위해 LevelMeta/WorldOption/LocalData 복사 중...", 'orange')
            src_world_dir = os.path.dirname(self.src_level_path.get())
            for filename in ['LevelMeta.sav', 'WorldOption.sav', 'LocalData.sav']:
                src_path = os.path.join(src_world_dir, filename)
                if os.path.exists(src_path):
                    shutil.copy2(src_path, working_dir)
                
        if not os.path.exists(level_sav_path): 
            raise FileNotFoundError(f"대상 Level.sav 파일 없음: {level_sav_path}")
        if not os.path.exists(source_sav): 
            raise FileNotFoundError(f"원본 캐릭터 파일 없음: {source_sav}")

        self.update_progress(30)
        self.update_status("데이터 백업 중 (안전 제일)...", 'orange')

        timestamp = str(int(time.time()))
        custom_backup_root = self.backup_root_dir.get()

        if custom_backup_root and os.path.isdir(custom_backup_root):
            backup_base = os.path.join(custom_backup_root, world_id)
        else:
            backup_base = working_dir
        
        backup_dir = os.path.join(backup_base, 'Backup', f'SafeBackup_{timestamp}')
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(level_sav_path, backup_dir)
            if os.path.exists(target_sav_path):
                shutil.copy2(target_sav_path, backup_dir)
        except PermissionError as e:
            raise PermissionError(f"백업 폴더({backup_dir})를 생성하거나 파일 복사 권한이 없습니다. 관리자 권한을 확인하세요.")
        
        if not os.path.exists(os.path.join(backup_dir, 'Level.sav')):
            raise Exception("백업 실패! 작업을 중단합니다. 저장 공간을 확인하세요.")
        
        logging.info(f"백업 완료. 경로: {backup_dir}")

        self.update_progress(50)
        self.update_status("캐릭터 파일 이식 중...", 'orange')

        try:
            os.makedirs(os.path.dirname(target_sav_path), exist_ok=True)
            shutil.copy2(source_sav, target_sav_path)
        except PermissionError as e:
            raise PermissionError(f"캐릭터 파일({target_sav_path})에 쓸 수 없습니다. 게임/서버를 종료했는지 확인하세요.")

        self.update_progress(60)
        self.update_status("Level.sav 파싱 중 (메모리 사용량 증가 주의)...", 'orange')

        try:
            with open(level_sav_path, 'rb') as f:
                data = f.read()
            
            gvas_file = GvasFile.read(data, palworld_type_map)
            
        except Exception as e:
            raise Exception(f"Level.sav 파일을 읽거나 Gvas 구조로 파싱하는 데 실패했습니다. 데이터 손상 가능성: {e}")

        del data 
        gc.collect()

        self.update_progress(70)
        self.update_status("ID 데이터 교체 및 직렬화 중...", 'orange')

        try:
            gvas_dict = gvas_file.dump()
            
            if CustomEncoder:
                json_str = json.dumps(gvas_dict, cls=CustomEncoder)
            else:
                def default_serializer(obj):
                    if isinstance(obj, (uuid.UUID, bytes)): 
                        return str(obj)
                    raise TypeError(f"Type {type(obj)} not serializable")
                json_str = json.dumps(gvas_dict, default=default_serializer)
            
            del gvas_dict
            gc.collect()

            self.update_status(f"ID 치환 중 ({src_id[:8]} -> {tgt_id[:8]})...", 'orange')
            modified_json_str = json_str.replace(src_id.lower(), tgt_id.lower())
            
            del json_str
            gc.collect()

            self.update_progress(85)
            self.update_status("변경된 데이터 역직렬화 및 Level.sav 저장 중...", 'orange')
            
            modified_dict = json.loads(modified_json_str)
            del modified_json_str
            gc.collect()

            new_gvas_file = GvasFile.load(modified_dict, palworld_type_map)
            new_data = new_gvas_file.write(palworld_type_map)

        except (json.JSONDecodeError, TypeError) as e:
            raise json.JSONDecodeError(f"데이터 직렬화/역직렬화 오류 발생. Level.sav 데이터 구조 문제일 수 있습니다: {e}", doc="", pos=0)
        except Exception as e:
            raise Exception(f"ID 변환 및 저장 파일 생성 중 오류: {e}")

        try:
            with open(level_sav_path, 'wb') as f:
                f.write(new_data)
        except PermissionError as e:
            raise PermissionError(f"Level.sav 파일({level_sav_path})에 최종 데이터를 쓸 수 없습니다. 게임/서버를 종료했는지 확인하세요.")
            
        self.update_progress(100)


if __name__ == "__main__":
    try:
        # DPI 설정 (관리자 권한 없이)
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        
        # GUI 생성
        root = tk.Tk()
        app = PalworldMigratorApp(root)
        
        # 초기 윈도우 중앙 배치 및 크기 설정
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        x = (screen_width // 2) - (app.window_width // 2)
        y = (screen_height // 2) - (app.window_height // 2)
        
        root.geometry(f'{app.window_width}x{app.window_height}+{x}+{y}')
        
        # 메인 루프 시작
        root.mainloop()
        
    except Exception as e:
        logging.error(f"GUI 시작 오류: {e}", exc_info=True)
        print(f"오류: {e}")
