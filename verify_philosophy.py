import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import webbrowser  # Добавлено для открытия ссылок в браузере
import os

def calculate_yuct_metrics(h_d, h_i, alpha=0.1):
    """Математический движок YUCT."""
    kc = 1 / 3
    if h_i == 0:
        return {"K_eff": float('inf'), "Epsilon": 0.0, "Bell_S": round(2 + 2 * np.sqrt(2) - 2, 4), "Phase": "Формальная система"}
        
    k_eff = h_d / h_i
    epsilon = kc * alpha * (k_eff ** (-2/3))
    bell_s = 2 + (2 * np.sqrt(2) - 2) * (1 - 2 * kc * alpha * (k_eff ** (-2/3)))
    
    if k_eff < 2: phase = "Нигилизм / Абсурд"
    elif 2 <= k_eff < 5: phase = "Скептицизм / Релятивизм"
    elif 5 <= k_eff < 10: phase = "Метафизика / Системная философия"
    elif 10 <= k_eff < 20: phase = "Критическая философия"
    else: phase = "Формальная система"
        
    return {
        "K_eff": round(k_eff, 2),
        "Epsilon": round(epsilon, 6),
        "Bell_S": round(bell_s, 4),
        "Phase": phase
    }

def process_text_and_estimate_entropy(text):
    """Эмуляция семантического процессора YUCT."""
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
        self.root.title("YUCT Quantitative Philosophy Analyzer v1.1")
        self.root.geometry("650x580")  # Немного увеличили высоту окна для ссылки
        self.root.configure(bg="#f0f4f8")
        
        # Заголовок
        title_label = tk.Label(root, text="Количественный анализ текстов по методологии YUCT", 
                               font=("Arial", 14, "bold"), bg="#f0f4f8", fg="#1a365d")
        title_label.pack(pady=15)
        
        # Кнопка выбора файла
        self.btn_load = tk.Button(root, text="Выбрать файл (.txt)", command=self.load_file,
                                  font=("Arial", 11, "bold"), bg="#2b6cb0", fg="white", 
                                  padx=10, pady=5, relief="flat")
        self.btn_load.pack(pady=10)
        
        # Информационная панель файла
        self.lbl_file = tk.Label(root, text="Файл не выбран", font=("Arial", 10, "italic"), bg="#f0f4f8", fg="#4a5568")
        self.lbl_file.pack()
        
        # Текстовое поле вывода результатов
        self.txt_output = scrolledtext.ScrolledText(root, width=75, height=18, font=("Courier New", 10),
                                                    bg="white", fg="#2d3748", bd=1, relief="solid")
        self.txt_output.pack(pady=15, padx=15)
        
        # Дисклеймер
        lbl_footer = tk.Label(root, text="Специально для портала «Философский штурм»", 
                              font=("Arial", 9), bg="#f0f4f8", fg="#718096")
        lbl_footer.pack(pady=2)

        # ДОБАВЛЕННЫЙ БЛОК: Кликабельная ссылка на официальный сайт
        self.lbl_link = tk.Label(root, text="Официальный сайт теории: yuct.org", 
                                 font=("Arial", 10, "underline"), bg="#f0f4f8", fg="#2b6cb0", cursor="hand2")
        self.lbl_link.pack(side="bottom", pady=10)
        # Привязываем событие клика мыши к функции открытия сайта
        self.lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://yuct.org/"))

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_name = os.path.basename(file_path)
            words_count = len(content.split())
            self.lbl_file.configure(text=f"Загружен: {file_name} ({words_count} слов)", font=("Arial", 10, "bold"), fg="#2f855a")
            
            h_d, h_i = process_text_and_estimate_entropy(content)
            metrics = calculate_yuct_metrics(h_d, h_i)
            
            self.txt_output.delete(1.0, tk.END)
            self.txt_output.insert(tk.END, f"=== ОТЧЕТ О КООРДИНАЦИОННОЙ ЭФФЕКТИВНОСТИ СИСТЕМЫ ===\n")
            self.txt_output.insert(tk.END, f"Анализируемый файл: {file_name}\n")
            self.txt_output.insert(tk.END, f"Объем выборки:     {words_count} слов\n")
            self.txt_output.insert(tk.END, f"---------------------------------------------------\n")
            self.txt_output.insert(tk.END, f"Энтропия словаря H(D):  {h_d} бит\n")
            self.txt_output.insert(tk.END, f"Энтропия индекса H(I):  {h_i} бит\n")
            self.txt_output.insert(tk.END, f"---------------------------------------------------\n")
            self.txt_output.insert(tk.END, f"Эффективность K_eff:    {metrics['K_eff']}\n")
            self.txt_output.insert(tk.END, f"Внутренняя ошибка (eps): {metrics['Epsilon']}\n")
            self.txt_output.insert(tk.END, f"Когерентность Белла (S): {metrics['Bell_S']} (макс: 2.8284)\n")
            self.txt_output.insert(tk.END, f"---------------------------------------------------\n")
            self.txt_output.insert(tk.END, f"ФАЗОВЫЙ СТАТУС: {metrics['Phase'].upper()}\n")
            self.txt_output.insert(tk.END, f"===================================================\n")
            
            if words_count < 1000:
                self.txt_output.insert(tk.END, f"\n⚠️ ВНИМАНИЕ: Размер текста менее 1000 слов!\n")
                self.txt_output.insert(tk.END, f"Возможна аномалия Парменида (искусственное завышение K_eff).\n")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл.\nУбедитесь, что кодировка файла UTF-8.\nДетали: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = YUCTAnalzerApp(root)
    root.mainloop()
