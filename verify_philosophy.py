# -*- coding: utf-8 -*-
"""
Нормализованная версия скрипта YUCT Quantitative Philosophy Analyzer
Автор: Alexey V. Yakushev
Версия: 1.2 (нормализована)
Описание: Приложение для количественного анализа философских текстов
          по методологии Yakushev Unified Coordination Theory (YUCT).
          Вычисляет координационную эффективность K_eff, философскую ошибку,
          когерентность Белла и определяет фазовый статус системы.
"""

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser
import os

# =====================================================================
# БАЗА ДАННЫХ ЛОКАЛИЗАЦИИ (интерфейс + отчёты)
# =====================================================================
LOCALIZATION = {
    "Русский": {
        "title": "Количественный анализ текстов по методологии YUCT",
        "btn_load": "Выбрать файл (.txt)",
        "no_file": "Файл не выбран",
        "loaded": "Загружен",
        "words": "слов",
        "footer": "Специально для портала «Философский штурм»",
        "link": "Официальный сайт теории: yuct.org",
        "err_title": "Ошибка",
        "err_read": "Не удалось прочитать файл.\nУбедитесь, что кодировка UTF-8.\nДетали: ",
        "warn_size": "\n⚠️ ВНИМАНИЕ: Размер текста менее 1000 слов!\nВозможна аномалия Парменида (искусственное завышение K_eff).\n",
        "rep_header": "=== ОТЧЕТ О КООРДИНАЦИОННОЙ ЭФФЕКТИВНОСТИ СИСТЕМЫ ===",
        "rep_file": "Анализируемый файл",
        "rep_volume": "Объем выборки",
        "rep_hd": "Энтропия словаря H(D)",
        "rep_hi": "Энтропия индекса H(I)",
        "rep_keff": "Эффективность K_eff",
        "rep_eps": "Внутренняя ошибка (eps)",
        "rep_bell": "Когерентность Белла (S)",
        "rep_max": "макс",
        "rep_phase": "ФАЗОВЫЙ СТАТУС",
        "phases": {
            "absurd": "Нигилизм / Абсурд",
            "relativism": "Скептицизм / Релятивизм",
            "system": "Метафизика / Системная философия",
            "critical": "Критическая философия",
            "formal": "Формальная система"
        }
    },
    "English": {
        "title": "YUCT Quantitative Text Analysis Framework",
        "btn_load": "Select File (.txt)",
        "no_file": "No file selected",
        "loaded": "Loaded",
        "words": "words",
        "footer": "Specially for 'Philosophical Assault' Portal",
        "link": "Official Website: yuct.org",
        "err_title": "Error",
        "err_read": "Failed to read file.\nEnsure UTF-8 encoding.\nDetails: ",
        "warn_size": "\n⚠️ WARNING: Text size is under 1000 words!\nParmenides anomaly possible (artificially inflated K_eff).\n",
        "rep_header": "=== SYSTEM COORDINATION EFFICIENCY REPORT ===",
        "rep_file": "Analyzed File",
        "rep_volume": "Sample Volume",
        "rep_hd": "Dictionary Entropy H(D)",
        "rep_hi": "Index Entropy H(I)",
        "rep_keff": "Efficiency K_eff",
        "rep_eps": "Internal Error (eps)",
        "rep_bell": "Bell Coherence (S)",
        "rep_max": "max",
        "rep_phase": "PHASE STATUS",
        "phases": {
            "absurd": "Nihilism / Absurd",
            "relativism": "Skepticism / Relativism",
            "system": "Metaphysics / Systematic Philosophy",
            "critical": "Critical Philosophy",
            "formal": "Formal System"
        }
    },
    "Deutsch (Wissenschaftlich)": {
        "title": "Quantitative Textanalyse nach der YUCT-Methodik",
        "btn_load": "Datei auswählen (.txt)",
        "no_file": "Keine Datei ausgewählt",
        "loaded": "Geladen",
        "words": "Wörter",
        "footer": "Spezialisiert für das Portal 'Philosophischer Sturm'",
        "link": "Offizielle Website: yuct.org",
        "err_title": "Fehler",
        "err_read": "Datei konnte nicht gelesen werden.\nPrüfen Sie die UTF-8-Kodierung.\nDetails: ",
        "warn_size": "\n⚠️ WARNUNG: Textgröße unter 1000 Wörtern!\nParmenides-Anomalie möglich (künstlich erhöhter K_eff).\n",
        "rep_header": "=== BERICHT ÜBER DIE KOORDINATIONSEFFIZIENZ DES SYSTEMS ===",
        "rep_file": "Analysierte Datei",
        "rep_volume": "Stichprobenumfang",
        "rep_hd": "Wörterbuchentropie H(D)",
        "rep_hi": "Indexentropie H(I)",
        "rep_keff": "Effizienz K_eff",
        "rep_eps": "Interner Fehler (eps)",
        "rep_bell": "Bell-Kohärenz (S)",
        "rep_max": "max",
        "rep_phase": "PHASENSTATUS",
        "phases": {
            "absurd": "Nihilismus / Absurdität",
            "relativism": "Skeptizismus / Relativismus",
            "system": "Metaphysik / Systemische Philosophie",
            "critical": "Kritische Philosophie",
            "formal": "Formales System"
        }
    },
    "中文 (Chinese)": {
        "title": "基于 YUCT 方法论的文本量化分析系统",
        "btn_load": "选择文件 (.txt)",
        "no_file": "未选择文件",
        "loaded": "已加载",
        "words": "词",
        "footer": "专为“哲学风暴”门户网站打造",
        "link": "官方网站: yuct.org",
        "err_title": "错误",
        "err_read": "无法读取文件。\n请确保使用 UTF-8 编码。\n详情: ",
        "warn_size": "\n⚠️ 警告：文本量少于 1000 词！\n可能出现巴门尼德反常（K_eff 人为夸大）。\n",
        "rep_header": "=== 系统协调效率报告 ===",
        "rep_file": "分析文件",
        "rep_volume": "样本容量",
        "rep_hd": "词典熵 H(D)",
        "rep_hi": "索引熵 H(I)",
        "rep_keff": "协调效率 K_eff",
        "rep_eps": "内部误差 (eps)",
        "rep_bell": "贝尔相干性 (S)",
        "rep_max": "最大值",
        "rep_phase": "相态分类",
        "phases": {
            "absurd": "虚无主义 / 荒谬",
            "relativism": "怀疑主义 / 相对主义",
            "system": "形而上学 / 系统哲学",
            "critical": "批判哲学",
            "formal": "形式系统"
        }
    },
    "العربية (Arabic)": {
        "title": "نظام التحليل الكمي للنصوص وفق منهجية YUCT",
        "btn_load": "اختر ملفاً (.txt)",
        "no_file": "لم يتم اختيار ملف",
        "loaded": "تم تحميل",
        "words": "كلمة",
        "footer": "خصيصاً لبوابة 'العاصفة الفلسفية'",
        "link": "الموقع الرسمي: yuct.org",
        "err_title": "خطأ",
        "err_read": "فشل في قراءة الملف.\nتأكد من ترميز UTF-8.\nتفاصيل: ",
        "warn_size": "\n⚠️ تحذير: حجم النص أقل من 1000 كلمة!\nاحتمال حدوث مفارقة بارمينيدس (تضخم مصطنع لـ K_eff).\n",
        "rep_header": "=== تقرير كفاءة التنسيق للنظام ===",
        "rep_file": "الملف المحلل",
        "rep_volume": "حجم العينة",
        "rep_hd": "أنتروبيا القاموس H(D)",
        "rep_hi": "أنتروبيا المؤشر H(I)",
        "rep_keff": "الكفاءة K_eff",
        "rep_eps": "الخطأ الداخلي (eps)",
        "rep_bell": "ترابط بيل (S)",
        "rep_max": "الأقصى",
        "rep_phase": "حالة الطور",
        "phases": {
            "absurd": "العدمية / العبثية",
            "relativism": "الشكية / النسبية",
            "system": "الميتافيزيقا / الفلسفة النظامية",
            "critical": "الفلسفة النقدية",
            "formal": "النظام الصوري"
        }
    },
    "日本語 (Japanese)": {
        "title": "YUCT方法論に基づくテキスト量化分析システム",
        "btn_load": "ファイルを選択 (.txt)",
        "no_file": "ファイルが選択されていません",
        "loaded": "読み込み完了",
        "words": "語",
        "footer": "「哲学の嵐」ポータル専用",
        "link": "公式サイト: yuct.org",
        "err_title": "エラー",
        "err_read": "ファイルを読み込めませんでした。\nUTF-8エンコードを確認してください。\n詳細: ",
        "warn_size": "\n⚠️ 注意：テキストが1000語未満です！\nパルメニデス異常（K_effの人工的インフレ）の可能性があります。\n",
        "rep_header": "=== システム協調効率レポート ===",
        "rep_file": "分析ファイル",
        "rep_volume": "サンプル容量",
        "rep_hd": "辞書エントロピー H(D)",
        "rep_hi": "インデックスエントロピー H(I)",
        "rep_keff": "協調効率 K_eff",
        "rep_eps": "内部誤差 (eps)",
        "rep_bell": "ベルコヒーレンス (S)",
        "rep_max": "最大",
        "rep_phase": "相ステータス",
        "phases": {
            "absurd": "ニヒリズム / 不条理",
            "relativism": "懐疑主義 / 相対主義",
            "system": "形而上学 / 体系的哲学",
            "critical": "批判哲学",
            "formal": "形式システム"
        }
    },
    "한국어 (Korean)": {
        "title": "YUCT 방법론 기반 텍스트 양적 분석 시스템",
        "btn_load": "파일 선택 (.txt)",
        "no_file": "파일이 선택되지 않았습니다",
        "loaded": "로드됨",
        "words": "단어",
        "footer": "「철학적 폭풍」 포털 전용",
        "link": "공식 웹사이트: yuct.org",
        "err_title": "오류",
        "err_read": "파일을 읽지 못했습니다.\nUTF-8 인코딩을 확인하십시오.\n상세 정보: ",
        "warn_size": "\n⚠️ 경고: 텍스트 크기가 1000단어 미만입니다!\n파르메니데스 변칙(K_eff의 인위적 과장)이 발생할 수 있습니다.\n",
        "rep_header": "=== 시스템 조정 효율성 보고서 ===",
        "rep_file": "분석 파일",
        "rep_volume": "샘플 용량",
        "rep_hd": "사전 엔트로피 H(D)",
        "rep_hi": "인덱스 엔트로피 H(I)",
        "rep_keff": "조정 효율성 K_eff",
        "rep_eps": "내부 오차 (eps)",
        "rep_bell": "벨 코히어런스 (S)",
        "rep_max": "최대",
        "rep_phase": "상태 단계",
        "phases": {
            "absurd": "허무주의 / 부조리",
            "relativism": "회의주의 / 상대주의",
            "system": "형이상학 / 체계적 철학",
            "critical": "비판 철학",
            "formal": "형식 체계"
        }
    }
}


# =====================================================================
# МАТЕМАТИЧЕСКОЕ ЯДРО YUCT
# =====================================================================
def calculate_yuct_metrics(h_d, h_i, lang="Русский", alpha=0.1):
    """
    Вычисляет ключевые метрики YUCT по заданным энтропиям словаря и индекса.
    
    Параметры:
        h_d (float): энтропия словаря H(D)
        h_i (float): энтропия индекса H(I)
        lang (str): ключ языка для локализации фаз
        alpha (float): системная константа (по умолчанию 0.1)
    
    Возвращает:
        dict: словарь с K_eff, Epsilon, Bell_S, Phase
    """
    kc = 1.0 / 3.0
    phases = LOCALIZATION[lang]["phases"]
    
    # Защита от деления на ноль
    if h_i == 0:
        return {
            "K_eff": float('inf'),
            "Epsilon": 0.0,
            "Bell_S": round(2 + 2 * np.sqrt(2) - 2, 4),
            "Phase": phases["formal"]
        }
    
    k_eff = h_d / h_i
    epsilon = kc * alpha * (k_eff ** (-2.0 / 3.0))
    bell_s = 2 + (2 * np.sqrt(2) - 2) * (1 - 2 * kc * alpha * (k_eff ** (-2.0 / 3.0)))
    
    # Определение фазового статуса
    if k_eff < 2:
        phase = phases["absurd"]
    elif k_eff < 5:
        phase = phases["relativism"]
    elif k_eff < 10:
        phase = phases["system"]
    elif k_eff < 20:
        phase = phases["critical"]
    else:
        phase = phases["formal"]
    
    return {
        "K_eff": round(k_eff, 2),
        "Epsilon": round(epsilon, 6),
        "Bell_S": round(bell_s, 4),
        "Phase": phase
    }


def process_text_and_estimate_entropy(text):
    """
    Семантический процессор: извлекает частотный словарь и вычисляет
    энтропию словаря H(D), а также эмпирическую оценку H(I).
    
    Параметры:
        text (str): исходный текст
    
    Возвращает:
        tuple: (H_D, H_I) — округлённые до 2 знаков значения
    """
    # Очистка и токенизация
    words = [w.lower().strip(".,!?\"'()[]{}<>:-;") for w in text.split()]
    words = [w for w in words if len(w) > 2]
    
    if not words:
        return 0.0, 0.0
    
    total = len(words)
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    
    # Вычисление H(D) по Шеннону
    h_d = 0.0
    for cnt in counts.values():
        p = cnt / total
        h_d -= p * np.log2(p)
    
    # Эвристическая оценка H(I) на основе уникальности и энтропии
    unique_ratio = len(counts) / total
    h_i = max(0.1, min(2.0, h_d * unique_ratio * 1.5))
    
    return round(h_d, 2), round(h_i, 2)


# =====================================================================
# ГРАФИЧЕСКОЕ ПРИЛОЖЕНИЕ (Tkinter)
# =====================================================================
class YUCTAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = "Русский"
        self.raw_text_content = ""
        self.current_file_name = ""
        
        # Настройка окна
        self.root.title("YUCT Quantitative Philosophy Analyzer v1.2")
        self.root.geometry("670x620")
        self.root.configure(bg="#f0f4f8")
        
        # Выбор языка
        lang_frame = tk.Frame(root, bg="#f0f4f8")
        lang_frame.pack(anchor="ne", padx=15, pady=5)
        self.combo_lang = ttk.Combobox(
            lang_frame,
            values=list(LOCALIZATION.keys()),
            state="readonly",
            width=25
        )
        self.combo_lang.set(self.current_lang)
        self.combo_lang.pack()
        self.combo_lang.bind("<<ComboboxSelected>>", self.change_language)
        
        # Заголовок
        self.lbl_title = tk.Label(
            root,
            text="",
            font=("Arial", 14, "bold"),
            bg="#f0f4f8",
            fg="#1a365d"
        )
        self.lbl_title.pack(pady=10)
        
        # Кнопка загрузки файла
        self.btn_load = tk.Button(
            root,
            text="",
            command=self.load_file,
            font=("Arial", 11, "bold"),
            bg="#2b6cb0",
            fg="white",
            padx=10,
            pady=5,
            relief="flat"
        )
        self.btn_load.pack(pady=5)
        
        # Информация о загруженном файле
        self.lbl_file = tk.Label(
            root,
            text="",
            font=("Arial", 10, "italic"),
            bg="#f0f4f8",
            fg="#4a5568"
        )
        self.lbl_file.pack(pady=5)
        
        # Поле вывода отчёта
        self.txt_output = scrolledtext.ScrolledText(
            root,
            width=78,
            height=18,
            font=("Courier New", 10),
            bg="white",
            fg="#2d3748",
            bd=1,
            relief="solid"
        )
        self.txt_output.pack(pady=10, padx=15)
        
        # Нижний колонтитул
        self.lbl_footer = tk.Label(
            root,
            text="",
            font=("Arial", 9),
            bg="#f0f4f8",
            fg="#718096"
        )
        self.lbl_footer.pack(pady=2)
        
        # Ссылка на сайт
        self.lbl_link = tk.Label(
            root,
            text="",
            font=("Arial", 10, "underline"),
            bg="#f0f4f8",
            fg="#2b6cb0",
            cursor="hand2"
        )
        self.lbl_link.pack(side="bottom", pady=10)
        self.lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://yuct.org"))
        
        # Первоначальное обновление текста интерфейса
        self.update_ui_strings()
    
    def update_ui_strings(self):
        """Обновляет все текстовые элементы в соответствии с выбранным языком."""
        lang_data = LOCALIZATION[self.current_lang]
        
        self.lbl_title.configure(text=lang_data["title"])
        self.btn_load.configure(text=lang_data["btn_load"])
        self.lbl_footer.configure(text=lang_data["footer"])
        self.lbl_link.configure(text=lang_data["link"])
        
        if not self.raw_text_content:
            self.lbl_file.configure(
                text=lang_data["no_file"],
                font=("Arial", 10, "italic"),
                fg="#4a5568"
            )
        else:
            words_count = len(self.raw_text_content.split())
            self.lbl_file.configure(
                text=f"{lang_data['loaded']}: {self.current_file_name} ({words_count} {lang_data['words']})",
                font=("Arial", 10, "bold"),
                fg="#2f855a"
            )
    
    def change_language(self, event=None):
        """Обработчик смены языка."""
        self.current_lang = self.combo_lang.get()
        self.update_ui_strings()
        if self.raw_text_content:
            self.generate_report()
    
    def load_file(self):
        """Загрузка текстового файла и запуск анализа."""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.raw_text_content = f.read()
            self.current_file_name = os.path.basename(file_path)
            self.update_ui_strings()
            self.generate_report()
        except Exception as e:
            lang_data = LOCALIZATION[self.current_lang]
            messagebox.showerror(
                lang_data["err_title"],
                f"{lang_data['err_read']}{str(e)}"
            )
    
    def generate_report(self):
        """Формирует и выводит отчёт в текстовое поле."""
        lang_data = LOCALIZATION[self.current_lang]
        words_count = len(self.raw_text_content.split())
        h_d, h_i = process_text_and_estimate_entropy(self.raw_text_content)
        metrics = calculate_yuct_metrics(h_d, h_i, lang=self.current_lang)
        
        # Очистка и заполнение
        self.txt_output.delete(1.0, tk.END)
        self.txt_output.insert(tk.END, f"{lang_data['rep_header']}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_file']}: {self.current_file_name}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_volume']}:   {words_count} {lang_data['words']}\n")
        self.txt_output.insert(tk.END, "---------------------------------------------------\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_hd']}:  {h_d} bit\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_hi']}:  {h_i} bit\n")
        self.txt_output.insert(tk.END, "---------------------------------------------------\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_keff']}:    {metrics['K_eff']}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_eps']}: {metrics['Epsilon']}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_bell']}: {metrics['Bell_S']} ({lang_data['rep_max']}: 2.8284)\n")
        self.txt_output.insert(tk.END, "---------------------------------------------------\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_phase']}: {metrics['Phase'].upper()}\n")
        self.txt_output.insert(tk.END, "===================================================\n")
        
        # Предупреждение о малом объёме текста
        if words_count < 1000:
            self.txt_output.insert(tk.END, lang_data["warn_size"])


# =====================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =====================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = YUCTAnalyzerApp(root)
    root.mainloop()
