import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser
import os
import io

# Попытка импорта внешних библиотек
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB = True
except ImportError:
    HAS_WEB = False

try:
    import pypdf
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# База данных локализации
LOCALIZATION = {
    "Русский": {
        "title": "Количественный анализ текстов по методологии YUCT",
        "btn_load": "Выбрать файл (.txt, .pdf)",
        "btn_url": "Анализировать URL",
        "lbl_url": "Вставьте ссылку (URL) для анализа:",
        "no_file": "Источник не выбран",
        "loaded": "Загружен",
        "words": "слов",
        "footer": "Специально для портала «Философский штурм»",
        "link": "Официальный сайт теории: yuct.org",
        "err_title": "Ошибка",
        "err_read": "Не удалось прочитать файл.\nУбедитесь в корректности формата.\nДетали: ",
        "err_lib_pdf": "Для чтения PDF установите библиотеку: pip install pypdf",
        "err_lib_web": "Для анализа URL установите: pip install requests beautifulsoup4",
        "err_url_fail": "Не удалось скачать текст по ссылке. Проверьте сеть или URL.",
        "warn_size": "\n⚠️ ВНИМАНИЕ: Размер текста менее 1000 слов!\nВозможна аномалия Парменида (искусственное завышение K_eff).\n",
        "rep_header": "=== ОТЧЕТ О КООРДИНАЦИОННОЙ ЭФФЕКТИВНОСТИ СИСТЕМЫ ===",
        "rep_src": "Источник данных",
        "rep_volume": "Объем чистой мысли",
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
        "btn_load": "Select File (.txt, .pdf)",
        "btn_url": "Analyze URL",
        "lbl_url": "Paste link (URL) for analysis:",
        "no_file": "No source selected",
        "loaded": "Loaded",
        "words": "words",
        "footer": "Specially for 'Philosophical Assault' Portal",
        "link": "Official Website: yuct.org",
        "err_title": "Error",
        "err_read": "Failed to read file.\nEnsure format validity.\nDetails: ",
        "err_lib_pdf": "To read PDF install library: pip install pypdf",
        "err_lib_web": "To analyze URL install: pip install requests beautifulsoup4",
        "err_url_fail": "Failed to fetch text from URL. Check network or address.",
        "warn_size": "\n⚠️ WARNING: Text size is under 1000 words!\nParmenides anomaly possible (artificially inflated K_eff).\n",
        "rep_header": "=== SYSTEM COORDINATION EFFICIENCY REPORT ===",
        "rep_src": "Data Source",
        "rep_volume": "Pure Thought Volume",
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
    }
}

def calculate_yuct_metrics(h_d, h_i, lang="Русский", alpha=0.1):
    """Математический движок YUCT."""
    kc = 1 / 3
    # Проверка на случай отсутствия языка в базе (фолбэк на Английский)
    safe_lang = lang if lang in LOCALIZATION else "English"
    ph = LOCALIZATION[safe_lang]["phases"]
    if h_i == 0:
        return {"K_eff": float('inf'), "Epsilon": 0.0, "Bell_S": round(2 + 2 * np.sqrt(2) - 2, 4), "Phase": ph["formal"]}
        
    k_eff = h_d / h_i
    epsilon = kc * alpha * (k_eff ** (-2/3))
    bell_s = 2 + (2 * np.sqrt(2) - 2) * (1 - 2 * kc * alpha * (k_eff ** (-2/3)))
    
    if k_eff < 2: phase = ph["absurd"]
    elif 2 <= k_eff < 5: phase = ph["relativism"]
    elif 5 <= k_eff < 10: phase = ph["system"]
    elif 10 <= k_eff < 20: phase = ph["critical"]
    else: phase = ph["formal"]
        
    return {
        "K_eff": round(k_eff, 2),
        "Epsilon": round(epsilon, 6),
        "Bell_S": round(bell_s, 4),
        "Phase": phase
    }

def process_text_and_estimate_entropy(text):
    """Семантический частотный процессор YUCT."""
    words = [w.lower().strip(".,!?\"'()[]{}<>:-;") for w in text.split()]
    words = [w for w in words if len(w) > 2]
    
    if not words:
        return 0, 0
        
    total_words = len(words)
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
        
    h_d = 0
    for count in word_counts.values():
        p = count / total_words
        h_d -= p * np.log2(p)
        
    unique_ratio = len(word_counts) / total_words
    h_i = max(0.1, min(2.0, h_d * unique_ratio * 1.5))
    
    return round(h_d, 2), round(h_i, 2)

class YUCTAnalzerApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = "Русский"
        self.raw_text_content = ""
        self.current_source_name = ""
        
        self.root.title("YUCT Quantitative Philosophy Analyzer v1.3")
        self.root.geometry("690x680")
        self.root.configure(bg="#f0f4f8")
        
        # Языковая панель
        lang_frame = tk.Frame(root, bg="#f0f4f8")
        lang_frame.pack(anchor="ne", padx=15, pady=5)
        
        # Ограничиваем список основными языками для краткости GUI
        gui_langs = ["Русский", "English"]
        self.combo_lang = ttk.Combobox(lang_frame, values=gui_langs, state="readonly", width=15)
        self.combo_lang.set("Русский")
        self.combo_lang.pack()
        self.combo_lang.bind("<<ComboboxSelected>>", self.change_language)
        
        self.lbl_title = tk.Label(root, text="", font=("Arial", 14, "bold"), bg="#f0f4f8", fg="#1a365d")
        self.lbl_title.pack(pady=5)
        
        # Блок локальных файлов
        self.btn_load = tk.Button(root, text="", command=self.load_file,
                                  font=("Arial", 11, "bold"), bg="#2b6cb0", fg="white", 
                                  padx=10, pady=5, relief="flat")
        self.btn_load.pack(pady=5)
        
        # Разделитель
        tk.Frame(root, height=1, width=600, bg="#cbd5e0").pack(pady=10)
        
        # Блок URL веб-анализа
        self.lbl_url_prompt = tk.Label(root, text="", font=("Arial", 10), bg="#f0f4f8", fg="#2d3748")
        self.lbl_url_prompt.pack()
        
        url_frame = tk.Frame(root, bg="#f0f4f8")
        url_frame.pack(pady=5)
        
        self.entry_url = tk.Entry(url_frame, width=50, font=("Arial", 10))
        self.entry_url.pack(side="left", padx=5)
        
        self.btn_url = tk.Button(url_frame, text="", command=self.load_url,
                                 font=("Arial", 10, "bold"), bg="#319795", fg="white", 
                                 padx=5, relief="flat")
        self.btn_url.pack(side="left")
        
        # Информационная строка
        self.lbl_file = tk.Label(root, text="", font=("Arial", 10, "italic"), bg="#f0f4f8", fg="#4a5568")
        self.lbl_file.pack(pady=5)
        
        self.txt_output = scrolledtext.ScrolledText(root, width=80, height=16, font=("Courier New", 10),
                                                    bg="white", fg="#2d3748", bd=1, relief="solid")
        self.txt_output.pack(pady=5, padx=15)
        
        self.lbl_footer = tk.Label(root, text="", font=("Arial", 9), bg="#f0f4f8", fg="#718096")
        self.lbl_footer.pack(pady=2)

        self.lbl_link = tk.Label(root, text="", font=("Arial", 10, "underline"), bg="#f0f4f8", fg="#2b6cb0", cursor="hand2")
        self.lbl_link.pack(side="bottom", pady=5)
        self.lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://yuct.org"))
        
        self.update_ui_strings()

    def update_ui_strings(self):
        lang_data = LOCALIZATION[self.current_lang]
        self.lbl_title.configure(text=lang_data["title"])
        self.btn_load.configure(text=lang_data["btn_load"])
        self.lbl_url_prompt.configure(text=lang_data["lbl_url"])
        self.btn_url.configure(text=lang_data["btn_url"])
        self.lbl_footer.configure(text=lang_data["footer"])
        self.lbl_link.configure(text=lang_data["link"])
        
        if not self.raw_text_content:
            self.lbl_file.configure(text=lang_data["no_file"], font=("Arial", 10, "italic"), fg="#4a5568")
        else:
            words_count = len(self.raw_text_content.split())
            self.lbl_file.configure(text=f"{lang_data['loaded']}: {self.current_source_name} ({words_count} {lang_data['words']})", 
                                    font=("Arial", 10, "bold"), fg="#2f855a")

    def change_language(self, event=None):
        self.current_lang = self.combo_lang.get()
        self.update_ui_strings()
        if self.raw_text_content:
            self.generate_report()

    def load_file(self):
        lang_data = LOCALIZATION[self.current_lang]
        file_path = filedialog.askopenfilename(filetypes=[("Supported files", "*.txt *.pdf"), ("Text", "*.txt"), ("PDF", "*.pdf")])
        if not file_path:
            return
            
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".txt":
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.raw_text_content = f.read()
            elif ext == ".pdf":
                if not HAS_PDF:
                    messagebox.showwarning(lang_data["err_title"], lang_data["err_lib_pdf"])
                    return
                # Парсинг слоев PDF
                reader = pypdf.PdfReader(file_path)
                text_layers = []
                for page in reader.pages:
                    t_layer = page.extract_text()
                    if t_layer:
                        text_layers.append(t_layer)
                self.raw_text_content = "\n".join(text_layers)
            self.current_source_name = os.path.basename(file_path)
            self.update_ui_strings()
            self.generate_report()
        except Exception as e:
            messagebox.showerror(lang_data["err_title"], f"{lang_data['err_read']}{str(e)}")

    def load_url(self):
        lang_data = LOCALIZATION[self.current_lang]
        url = self.entry_url.get().strip()
        if not url:
            return
            
        if not HAS_WEB:
            messagebox.showwarning(lang_data["err_title"], lang_data["err_lib_web"])
            return
            
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                messagebox.showerror(lang_data["err_title"], lang_data["err_url_fail"])
                return
                
            # ИСПРАВЛЕНИЕ: Проверяем, не является ли ссылка PDF-файлом
            if url.lower().endswith('.pdf') or "application/pdf" in response.headers.get('Content-Type', ''):
                if not HAS_PDF:
                    messagebox.showwarning(lang_data["err_title"], lang_data["err_lib_pdf"])
                    return
                # Читаем бинарный поток PDF из сети без сохранения на диск
                pdf_file = io.BytesIO(response.content)
                reader = pypdf.PdfReader(pdf_file)
                text_layers = []
                for page in reader.pages:
                    t_layer = page.extract_text()
                    if t_layer:
                        text_layers.append(t_layer)
                self.raw_text_content = "\n".join(text_layers)
            else:
                # Обычная обработка HTML веб-страниц
                soup = BeautifulSoup(response.text, 'html.parser')
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                self.raw_text_content = soup.get_text()
                
            self.current_source_name = url[:40] + "..." if len(url) > 40 else url
            self.update_ui_strings()
            self.generate_report()
            
        except Exception as e:
            messagebox.showerror(lang_data["err_title"], f"{lang_data['err_url_fail']}\nDetails: {str(e)}")

    def generate_report(self):
        lang_data = LOCALIZATION[self.current_lang]
        words_count = len(self.raw_text_content.split())
        h_d, h_i = process_text_and_estimate_entropy(self.raw_text_content)
        metrics = calculate_yuct_metrics(h_d, h_i, lang=self.current_lang)
        self.txt_output.delete(1.0, tk.END)
        self.txt_output.insert(tk.END, f"{lang_data['rep_header']}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_src']}: {self.current_source_name}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_volume']}: {words_count} {lang_data['words']}\n")
        self.txt_output.insert(tk.END, f"---------------------------------------------------\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_hd']}:  {h_d} bit\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_hi']}:  {h_i} bit\n")
        self.txt_output.insert(tk.END, f"---------------------------------------------------\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_keff']}:    {metrics['K_eff']}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_eps']}: {metrics['Epsilon']}\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_bell']}: {metrics['Bell_S']} ({lang_data['rep_max']}: 2.8284)\n")
        self.txt_output.insert(tk.END, f"---------------------------------------------------\n")
        self.txt_output.insert(tk.END, f"{lang_data['rep_phase']}: {metrics['Phase'].upper()}\n")
        self.txt_output.insert(tk.END, f"===================================================\n")
        if words_count < 1000:
            self.txt_output.insert(tk.END, lang_data["warn_size"])

if __name__ == "__main__":
    root = tk.Tk()
    app = YUCTAnalzerApp(root)
    root.mainloop()
