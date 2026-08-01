# -*- coding: utf-8 -*-
"""
YUСT Семантический процессор v9.13
- Расширенные признаки (частоты слов, части речи, вариативность предложений)
- Двойное сравнение: по периодам и по философам
- Взвешенное косинусное сходство с нормализацией
- Осцилляции для глав
- Обновлённая кнопка пояснений (увеличенная)
- Экспорт JSON с именем исходного файла
- Увеличен вес частотных векторов (слова + биграммы) для точной идентификации
- Добавлены метрики аргументации, семантической многозначности и расширенного эмоционального спектра
- Исключены строковые и словарные поля из численных операций (нормализация и сравнение)
- Новые числовые признаки включены в сравнение
- Исправлена нормализация: собираются только числовые значения
- Добавлено кодирование строковых признаков (Argumentation_vector, Emotional_profile) для использования в сравнении
- Увеличены веса новых метрик (Isolation_index, Category_entropy, Skepticism, Dogmatism, Angst, Pathos, Argumentation_slope, Argumentation_code, Emotional_code) в 2 раза
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser
import os
import re
import json
import math
import numpy as np
from collections import Counter, defaultdict
import threading
import time
import winsound
import sys

# ------------------------------------------------------------------
# Вспомогательная функция для получения пути к ресурсам (работает и в EXE)
# ------------------------------------------------------------------
def resource_path(relative_path):
    """Возвращает абсолютный путь к файлу, корректно работающий
    как в режиме скрипта, так и в скомпилированном EXE (PyInstaller)."""
    try:
        # PyInstaller создаёт временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ------------------------------------------------------------------
# 1. Проверка наличия библиотек
# ------------------------------------------------------------------
HAS_PDFPLUMBER = False
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    print("pdfplumber не установлен. Установите: pip install pdfplumber")

HAS_PYMORPHY3 = False
try:
    import pymorphy3
    morph = pymorphy3.MorphAnalyzer()
    HAS_PYMORPHY3 = True
except ImportError:
    print("pymorphy3 не установлен. Лемматизация будет пропущена.")

HAS_RAZDEL = False
try:
    import razdel
    HAS_RAZDEL = True
except ImportError:
    print("razdel не установлен. Будет использован простой сегментатор предложений.")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import NMF
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False

# ------------------------------------------------------------------
# 2. Константы и словари
# ------------------------------------------------------------------
ABSTRACT_NOUNS = {
    'бытие', 'сущность', 'существование', 'сознание', 'познание', 'истина',
    'онтология', 'гносеология', 'диалектика', 'субъект', 'объект',
    'трансцендентное', 'имманентное', 'абсолют', 'идея', 'материя', 'дух',
    'разум', 'воля', 'свобода', 'необходимость', 'причинность', 'время',
    'пространство', 'закон', 'принцип', 'система', 'структура', 'метод',
    'критерий', 'рефлексия', 'интуиция', 'опыт', 'трансцендентальный',
    'феномен', 'ноумен', 'априорный', 'апостериорный', 'синтез', 'анализ',
    'суждение', 'умозаключение', 'логика', 'метафизика', 'этика', 'эстетика',
    'смысл', 'ценность', 'долг', 'справедливость', 'благо', 'зло',
    'счастье', 'страдание', 'любовь', 'смерть', 'жизнь', 'душа',
    'экзистенция', 'интенциональность', 'герменевтика', 'феноменология',
    'структурализм', 'постмодерн', 'деконструкция', 'субстанция', 'монада'
}

AGGRESSIVE_WORDS = {
    'агрессия', 'вражда', 'враг', 'уничтожить', 'сокрушить', 'разрушить', 'победить',
    'война', 'битва', 'удар', 'нападение', 'атака', 'ярость', 'гнев', 'злоба',
    'ненависть', 'презрение', 'превосходство', 'подавить', 'сломить', 'сокрушение',
    'бороться', 'против', 'конфликт', 'агрессивный', 'враждебный', 'яростный'
}

DEPRESSIVE_WORDS = {
    'тоска', 'печаль', 'грусть', 'скорбь', 'отчаяние', 'безнадёжность', 'пустота',
    'одиночество', 'смерть', 'тьма', 'мрак', 'страдание', 'боль', 'слёзы', 'плач',
    'уныние', 'депрессия', 'меланхолия', 'безысходность', 'тоскливый', 'унылый',
    'горе', 'трагедия', 'беда', 'несчастье', 'мука', 'тягость'
}

RHETORICAL_WORDS = {
    'риторика', 'красноречие', 'пафос', 'возвышенный', 'величественный', 'торжественный',
    'взывать', 'восклицать', 'риторический', 'антитеза', 'повтор', 'анафора',
    'эпифора', 'градация', 'инверсия', 'красноречивый', 'витийство', 'ораторский'
}

CERTAINTY_WORDS = {
    'несомненно', 'безусловно', 'очевидно', 'непременно', 'бесспорно', 'разумеется',
    'конечно', 'должен', 'обязан', 'необходимо', 'требуется', 'следует',
    'абсолютно', 'всецело', 'полностью', 'безусловный', 'неизбежно'
}

UNCERTAINTY_WORDS = {
    'возможно', 'вероятно', 'может быть', 'по-видимому', 'кажется', 'предположительно',
    'пожалуй', 'наверное', 'видимо', 'должно быть', 'возможно, что', 'по всей вероятности'
}

POSITIVE_WORDS = {
    'хороший', 'прекрасный', 'великий', 'светлый', 'радость', 'счастье', 'благо',
    'добро', 'гармония', 'совершенство', 'истина', 'красота', 'любовь', 'мир',
    'справедливость', 'свобода', 'равенство', 'братство', 'добродетель', 'мудрость'
}

NEGATIVE_WORDS = {
    'плохой', 'злой', 'тёмный', 'страх', 'ненависть', 'злоба', 'гнев', 'разрушение',
    'смерть', 'боль', 'страдание', 'отчаяние', 'беда', 'несчастье', 'преступление',
    'порок', 'несправедливость', 'тирания', 'насилие', 'ложь'
}

LOGICAL_MARKERS = ['следовательно', 'поэтому', 'таким образом', 'значит', 'итак',
                   'вытекает', 'следует', 'поскольку', 'постольку', 'вследствие',
                   'в силу', 'с одной стороны', 'с другой стороны', 'во-первых',
                   'во-вторых', 'в-третьих', 'отсюда', 'из этого следует']

MODAL_MARKERS = ['возможно', 'вероятно', 'кажется', 'предположительно', 'очевидно',
                 'несомненно', 'безусловно', 'может быть', 'по-видимому', 'должен',
                 'следует', 'необходимо', 'можно']

CAUSAL_MARKERS = ['потому что', 'так как', 'ибо', 'по причине', 'благодаря', 'ввиду']
CONTRAST_MARKERS = ['однако', 'но', 'зато', 'хотя', 'несмотря на', 'вопреки', 'тогда как']
CONJUNCTIONS = {'и', 'а', 'но', 'да', 'или', 'либо', 'то', 'что', 'чтобы', 'потому',
                'так', 'как', 'когда', 'если', 'хотя', 'пусть', 'лишь', 'только'}
PREPOSITIONS = {'в', 'на', 'с', 'по', 'к', 'у', 'о', 'за', 'из', 'от', 'до',
                'для', 'без', 'через', 'между', 'над', 'под', 'об', 'при', 'про'}
PRONOUNS = {'я', 'ты', 'он', 'она', 'оно', 'мы', 'вы', 'они', 'себя', 'свой',
            'этот', 'тот', 'весь', 'каждый', 'некоторый', 'другой', 'сам'}
PARTICLES = {'же', 'бы', 'ли', 'не', 'ни', 'да', 'нет', 'вот', 'вон', 'уж', 'всё'}

# ===== НОВЫЕ ЭМОЦИОНАЛЬНЫЕ СЛОВАРИ =====
SKEPTICISM_WORDS = {
    'сомнение', 'подозрение', 'критика', 'парадокс', 'ирония', 'скепсис',
    'сомнительный', 'спорный', 'противоречие', 'критический', 'релятивный',
    'неуверенность', 'колебание', 'относительность', 'субъективность'
}

DOGMATISM_WORDS = {
    'бесспорно', 'непоколебимо', 'абсолютно', 'неизбежно', 'категорически',
    'догма', 'истина', 'очевидность', 'самоочевидный', 'неопровержимый',
    'незыблемый', 'безусловный', 'единственно верный', 'окончательный'
}

ANGST_WORDS = {
    'смерть', 'страх', 'отчаяние', 'пустота', 'выбор', 'конечность', 'тревога',
    'одиночество', 'безысходность', 'экзистенция', 'брошенность', 'вина',
    'пограничный', 'ничто', 'абсурд', 'тоска', 'беспокойство', 'ужас'
}

PATHOS_WORDS = {
    'великий', 'возвышенный', 'торжественный', 'пафос', 'героический',
    'трагический', 'вдохновение', 'священный', 'вечный', 'судьба',
    'божественный', 'непоколебимый', 'могущественный', 'неизменный'
}

# ------------------------------------------------------------------
# 3. Класс FeatureExtractor (расширенный)
# ------------------------------------------------------------------
class FeatureExtractor:
    @staticmethod
    def compute_basic_features(text, use_lemmatization=False):
        if use_lemmatization and HAS_PYMORPHY3:
            words_raw = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', text.lower())
            words = []
            for w in words_raw:
                try:
                    parsed = morph.parse(w)[0]
                    lemma = parsed.normal_form
                    words.append(lemma)
                except:
                    words.append(w)
        else:
            words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', text.lower())

        if len(words) < 10:
            return None

        total_words = len(words)
        unique_words = len(set(words))
        ttr = unique_words / total_words if total_words > 0 else 0

        freq = Counter(words)
        freqs = list(freq.values())

        h_d = 0.0
        for cnt in freqs:
            p = cnt / total_words
            h_d -= p * math.log2(p)

        bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        bigram_freq = Counter(bigrams)
        total_bigrams = len(bigrams)
        h_i = 0.0
        if total_bigrams > 0:
            for cnt in bigram_freq.values():
                p = cnt / total_bigrams
                h_i -= p * math.log2(p)
        unique_bigrams = len(bigram_freq)
        if unique_bigrams > 1:
            max_h_i = math.log2(unique_bigrams)
            h_i_norm = h_i / max_h_i if max_h_i > 0 else 0
            h_i = min(2.0, h_i_norm * 1.5)
        else:
            h_i = 0.0

        k_eff = h_d / h_i if h_i > 0 else 0.0

        if len(freqs) > 5:
            sorted_freqs = sorted(freqs, reverse=True)
            log_ranks = np.log(np.arange(1, len(sorted_freqs) + 1))
            log_freqs = np.log(sorted_freqs)
            slope, _ = np.polyfit(log_ranks, log_freqs, 1)
            beta_zipf = abs(slope)
        else:
            beta_zipf = 0.0

        word_lengths = [len(w) for w in words]
        avg_word_len = np.mean(word_lengths) if word_lengths else 0
        std_word_len = np.std(word_lengths) if word_lengths else 0

        abstract_count = sum(1 for w in words if w in ABSTRACT_NOUNS)
        abstract_ratio = abstract_count / total_words if total_words > 0 else 0

        pronoun_count = sum(1 for w in words if w in PRONOUNS)
        pronoun_ratio = pronoun_count / total_words if total_words > 0 else 0

        conj_count = sum(1 for w in words if w in CONJUNCTIONS)
        prep_count = sum(1 for w in words if w in PREPOSITIONS)
        part_count = sum(1 for w in words if w in PARTICLES)

        text_lower = text.lower()
        log_count = sum(text_lower.count(m) for m in LOGICAL_MARKERS)
        modal_count = sum(text_lower.count(m) for m in MODAL_MARKERS)
        causal_count = sum(text_lower.count(m) for m in CAUSAL_MARKERS)
        contrast_count = sum(text_lower.count(m) for m in CONTRAST_MARKERS)

        exclam = text.count('!')
        quest = text.count('?')
        ellipsis = text.count('...')
        punct_marks = text.count(',') + text.count(';') + text.count(':')
        length_chars = len(text)
        if length_chars > 0:
            exclam_density = exclam / (length_chars / 1000)
            quest_density = quest / (length_chars / 1000)
            ellipsis_density = ellipsis / (length_chars / 1000)
            punct_density = punct_marks / (length_chars / 1000)
        else:
            exclam_density = quest_density = ellipsis_density = punct_density = 0

        sent_texts = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if sent_texts:
            sent_lengths = [len(re.findall(r'\b\w+\b', s)) for s in sent_texts]
            avg_sent_len = np.mean(sent_lengths)
            std_sent_len = np.std(sent_lengths) if len(sent_lengths) > 1 else 0
            sent_rhythm_var = std_sent_len / avg_sent_len if avg_sent_len > 0 else 0
            short_sent = sum(1 for l in sent_lengths if l < 5) / len(sent_lengths) if sent_lengths else 0
            long_sent = sum(1 for l in sent_lengths if l > 25) / len(sent_lengths) if sent_lengths else 0
            median_sent = np.median(sent_lengths)
            if len(sent_lengths) > 2:
                mean_sent = np.mean(sent_lengths)
                std_sent = np.std(sent_lengths) if np.std(sent_lengths) > 0 else 1
                skewness = np.mean(((sent_lengths - mean_sent) / std_sent) ** 3)
                kurtosis = np.mean(((sent_lengths - mean_sent) / std_sent) ** 4) - 3
            else:
                skewness = 0
                kurtosis = 0
        else:
            avg_sent_len = std_sent_len = sent_rhythm_var = short_sent = long_sent = 0
            median_sent = 0
            skewness = 0
            kurtosis = 0

        vowels = 'аеёиоуыэюя'
        syll_count = 0
        for w in words:
            syll_count += sum(1 for ch in w if ch in vowels)
        if total_words > 0 and len(sent_texts) > 0:
            readability = 206.835 - 1.3 * avg_sent_len - 60.1 * (syll_count / total_words)
        else:
            readability = 0

        aggressive_count = sum(1 for w in words if w in AGGRESSIVE_WORDS)
        aggressive_ratio = aggressive_count / total_words if total_words > 0 else 0
        depressive_count = sum(1 for w in words if w in DEPRESSIVE_WORDS)
        depressive_ratio = depressive_count / total_words if total_words > 0 else 0
        rhetorical_count = sum(1 for w in words if w in RHETORICAL_WORDS)
        rhetorical_ratio = rhetorical_count / total_words if total_words > 0 else 0
        certainty_count = sum(1 for w in words if w in CERTAINTY_WORDS)
        uncertainty_count = sum(1 for w in words if w in UNCERTAINTY_WORDS)
        if uncertainty_count > 0:
            certainty_ratio = certainty_count / uncertainty_count
        else:
            certainty_ratio = certainty_count / (total_words + 1)
        pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
        neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
        valence = (pos_count - neg_count) / (pos_count + neg_count + 1) if pos_count + neg_count > 0 else 0.0

        word_freq = FeatureExtractor._extract_word_frequencies(text, top_n=100)
        bigram_freq = FeatureExtractor._extract_bigram_frequencies(text, top_n=100)
        pos_ratios = FeatureExtractor._compute_pos_ratios(text)

        # ---- НОВЫЕ МЕТРИКИ ----
        grad = FeatureExtractor.compute_abstraction_gradient(text)
        argumentation_vector = grad['direction']
        argumentation_slope = grad['gradient']

        cat_density = FeatureExtractor.compute_categorical_density(text)
        isolation_index = cat_density['isolation_index']
        category_entropy = cat_density['category_entropy']

        emotional = FeatureExtractor.compute_emotional_spectrum(words)
        skepticism = emotional['skepticism']
        dogmatism = emotional['dogmatism']
        angst = emotional['angst']
        pathos = emotional['pathos']
        emotional_profile = emotional['emotional_profile']

        # Кодирование строковых признаков
        arg_map = {'deductive': 0, 'inductive': 1, 'dialectical': 2, 'neutral': 3}
        emo_map = {'neutral': 0, 'skepticism': 1, 'dogmatism': 2, 'angst': 3, 'pathos': 4}
        argumentation_code = arg_map.get(argumentation_vector, 3)
        emotional_code = emo_map.get(emotional_profile, 0)

        features = {
            'K_eff': k_eff,
            'TTR': ttr,
            'H_D': h_d,
            'H_I': h_i,
            'Beta_Zipf': beta_zipf,
            'Avg_word_len': avg_word_len,
            'Std_word_len': std_word_len,
            'Abstract_ratio': abstract_ratio,
            'Pronoun_ratio': pronoun_ratio,
            'Conj_ratio': conj_count / total_words if total_words > 0 else 0,
            'Prep_ratio': prep_count / total_words if total_words > 0 else 0,
            'Part_ratio': part_count / total_words if total_words > 0 else 0,
            'Log_marker_density': log_count / (length_chars / 1000) if length_chars > 0 else 0,
            'Modal_density': modal_count / (length_chars / 1000) if length_chars > 0 else 0,
            'Causal_density': causal_count / (length_chars / 1000) if length_chars > 0 else 0,
            'Contrast_density': contrast_count / (length_chars / 1000) if length_chars > 0 else 0,
            'Exclam_density': exclam_density,
            'Quest_density': quest_density,
            'Ellipsis_density': ellipsis_density,
            'Punct_density': punct_density,
            'Avg_sent_len': avg_sent_len,
            'Std_sent_len': std_sent_len,
            'Sent_rhythm_var': sent_rhythm_var,
            'Short_sent_ratio': short_sent,
            'Long_sent_ratio': long_sent,
            'Readability': readability,
            'Aggressive_ratio': aggressive_ratio,
            'Depressive_ratio': depressive_ratio,
            'Rhetorical_ratio': rhetorical_ratio,
            'Certainty_ratio': certainty_ratio,
            'Valence': valence,
            'Median_sent_len': median_sent,
            'Sent_skewness': skewness,
            'Sent_kurtosis': kurtosis,
            'word_freq': word_freq,
            'bigram_freq': bigram_freq,
            'pos_ratios': pos_ratios,
            # Новые метрики
            'Argumentation_vector': argumentation_vector,
            'Argumentation_slope': argumentation_slope,
            'Isolation_index': isolation_index,
            'Category_entropy': category_entropy,
            'Skepticism': skepticism,
            'Dogmatism': dogmatism,
            'Angst': angst,
            'Pathos': pathos,
            'Emotional_profile': emotional_profile,
            # Кодированные версии для численного сравнения
            'Argumentation_code': argumentation_code,
            'Emotional_code': emotional_code,
        }
        return features

    @staticmethod
    def _extract_word_frequencies(text, top_n=100):
        words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{3,}\b', text.lower())
        if not words:
            return {}
        freq = Counter(words)
        return dict(freq.most_common(top_n))

    @staticmethod
    def _extract_bigram_frequencies(text, top_n=100):
        words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{3,}\b', text.lower())
        if len(words) < 2:
            return {}
        bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        freq = Counter(bigrams)
        return dict(freq.most_common(top_n))

    @staticmethod
    def _compute_pos_ratios(text):
        if not HAS_PYMORPHY3:
            return {}
        words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]+\b', text)
        if not words:
            return {}
        pos_counts = defaultdict(int)
        total = 0
        for word in words:
            try:
                parsed = morph.parse(word)[0]
                pos = parsed.tag.POS
                if pos:
                    pos_counts[pos] += 1
                    total += 1
            except:
                continue
        if total == 0:
            return {}
        return {pos: count / total for pos, count in pos_counts.items()}

    @staticmethod
    def compute_lda_features(text, n_topics=10):
        if not HAS_SKLEARN:
            return None
        sents = re.split(r'[.!?]+', text)
        sents = [s.strip() for s in sents if len(s.split()) > 3]
        if len(sents) < 2:
            return None
        vectorizer = TfidfVectorizer(max_features=2000, stop_words=None, token_pattern=r'[а-яА-ЯёЁa-zA-Z]{3,}')
        try:
            X = vectorizer.fit_transform(sents)
        except:
            return None
        if X.shape[0] < 2 or X.shape[1] < 2:
            return None
        nmf = NMF(n_components=min(n_topics, X.shape[0]-1, X.shape[1]-1), init='random', random_state=42, max_iter=500)
        W = nmf.fit_transform(X)
        topic_weights = np.mean(W, axis=0)
        topic_weights = topic_weights / np.sum(topic_weights) if np.sum(topic_weights) > 0 else topic_weights
        return list(topic_weights)

    # ===== НОВЫЕ СТАТИЧЕСКИЕ МЕТОДЫ ДЛЯ РАСШИРЕННЫХ МЕТРИК =====
    @staticmethod
    def compute_abstraction_gradient(text, window_size=300, step=100):
        words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]+\b', text.lower())
        if len(words) < window_size:
            return {'gradient': 0, 'direction': 'neutral'}
        
        windows = []
        for start in range(0, len(words) - window_size + 1, step):
            window_words = words[start:start+window_size]
            windows.append(window_words)
        
        if len(windows) < 3:
            return {'gradient': 0, 'direction': 'neutral'}
        
        abstract_ratios = []
        for w in windows:
            total = len(w)
            if total == 0:
                continue
            abstract_count = sum(1 for word in w if word in ABSTRACT_NOUNS)
            abstract_ratios.append(abstract_count / total)
        
        if len(abstract_ratios) < 3:
            return {'gradient': 0, 'direction': 'neutral'}
        
        x = np.arange(len(abstract_ratios))
        slope, _ = np.polyfit(x, abstract_ratios, 1)
        
        if slope > 0.01:
            direction = 'inductive'
        elif slope < -0.01:
            direction = 'deductive'
        else:
            direction = 'dialectical'
        
        return {'gradient': slope, 'direction': direction}

    @staticmethod
    def compute_categorical_density(text):
        words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{3,}\b', text.lower())
        if not words:
            return {'isolation_index': 0, 'category_entropy': 0}
        
        unique_words = len(set(words))
        philosophical_terms = ABSTRACT_NOUNS
        
        non_phil_count = sum(1 for w in set(words) if w not in philosophical_terms)
        isolation_index = non_phil_count / unique_words if unique_words > 0 else 0
        
        freq = Counter(words)
        freqs = np.array(list(freq.values()))
        probs = freqs / np.sum(freqs)
        entropy = -np.sum(probs * np.log2(probs + 1e-9))
        max_entropy = np.log2(len(freq)) if len(freq) > 1 else 1
        category_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        return {
            'isolation_index': isolation_index,
            'category_entropy': category_entropy
        }

    @staticmethod
    def compute_emotional_spectrum(words):
        total_words = len(words)
        if total_words == 0:
            return {
                'skepticism': 0,
                'dogmatism': 0,
                'angst': 0,
                'pathos': 0,
                'emotional_profile': 'neutral'
            }
        
        skepticism_count = sum(1 for w in words if w in SKEPTICISM_WORDS)
        dogmatism_count = sum(1 for w in words if w in DOGMATISM_WORDS)
        angst_count = sum(1 for w in words if w in ANGST_WORDS)
        pathos_count = sum(1 for w in words if w in PATHOS_WORDS)
        
        skepticism = skepticism_count / total_words
        dogmatism = dogmatism_count / total_words
        angst = angst_count / total_words
        pathos = pathos_count / total_words
        
        scores = {
            'skepticism': skepticism,
            'dogmatism': dogmatism,
            'angst': angst,
            'pathos': pathos
        }
        if max(scores.values()) < 0.001:
            profile = 'neutral'
        else:
            profile = max(scores, key=scores.get)
        
        return {
            'skepticism': skepticism,
            'dogmatism': dogmatism,
            'angst': angst,
            'pathos': pathos,
            'emotional_profile': profile
        }

# ------------------------------------------------------------------
# 4. Класс сравнения с эталонными профилями (двойное сравнение)
# ------------------------------------------------------------------
class PhilosopherComparator:
    def __init__(self, profiles_path='profiles/profiles.json'):
        self.period_profiles = {}
        self.philosopher_profiles = {}
        self.profile_keys = []
        self.feature_means = {}
        self.feature_stds = {}
        self.feature_weights = {}
        self.load_profiles(profiles_path)
        self._compute_normalization()

    def load_profiles(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Исправлены ключи: в файле используются 'periods' и 'philosophers'
            self.period_profiles = data.get('periods', {})
            self.philosopher_profiles = data.get('philosophers', {})
            print(f"[DEBUG] Загружено периодных профилей: {len(self.period_profiles)}")
            print(f"[DEBUG] Загружено обобщённых профилей: {len(self.philosopher_profiles)}")
        except Exception as e:
            print(f"Ошибка загрузки профилей: {e}")
            self._create_dummy_profiles()

    def _create_dummy_profiles(self):
        philosophers = ['Лейбниц', 'Кант', 'Гегель', 'Маркс', 'Платон', 'Ницше', 'Спиноза', 'Декарт']
        periods = ['ранний', 'зрелый', 'поздний']
        dummy_feat = {k: np.random.uniform(0.1, 2.0) for k in ['K_eff', 'TTR', 'H_D', 'H_I', 'Beta_Zipf', 'Avg_word_len', 'Std_word_len', 'Abstract_ratio', 'Pronoun_ratio', 'Conj_ratio', 'Prep_ratio', 'Part_ratio', 'Log_marker_density', 'Modal_density', 'Causal_density', 'Contrast_density', 'Exclam_density', 'Quest_density', 'Ellipsis_density', 'Punct_density', 'Avg_sent_len', 'Std_sent_len', 'Sent_rhythm_var', 'Short_sent_ratio', 'Long_sent_ratio', 'Readability', 'Aggressive_ratio', 'Depressive_ratio', 'Rhetorical_ratio', 'Certainty_ratio', 'Valence', 'Median_sent_len', 'Sent_skewness', 'Sent_kurtosis']}
        for p in philosophers:
            for per in periods:
                key = f"{p}_{per}"
                self.period_profiles[key] = {'features': dummy_feat.copy()}
            self.philosopher_profiles[p] = {'features': dummy_feat.copy()}
        print("[DEBUG] Созданы тестовые профили.")

    def _compute_normalization(self):
        all_features = []
        for prof in self.period_profiles.values():
            all_features.append(prof.get('features', {}))
        if not all_features:
            return

        # Собираем все ключи из всех профилей
        all_keys = set()
        for f in all_features:
            all_keys.update(f.keys())
        
        # Для каждого ключа собираем только числовые значения
        for key in all_keys:
            vals = [f[key] for f in all_features if key in f and isinstance(f[key], (int, float))]
            if vals:
                self.feature_means[key] = np.mean(vals)
                self.feature_stds[key] = np.std(vals) if np.std(vals) > 0 else 1.0
                self.feature_weights[key] = 1.0 / (self.feature_stds[key] ** 2 + 1e-6)

        # ----- УВЕЛИЧЕНИЕ ВЕСОВ ДЛЯ НОВЫХ МЕТРИК -----
        new_keys = {
            'Isolation_index', 'Category_entropy',
            'Skepticism', 'Dogmatism', 'Angst', 'Pathos',
            'Argumentation_slope', 'Argumentation_code', 'Emotional_code'
        }
        for k in new_keys:
            if k in self.feature_weights:
                self.feature_weights[k] *= 2.0  # увеличиваем вес в 2 раза
        # -------------------------------------------------

        # Дополнительно вычисляем нормализацию для кодов, если их нет в профилях (но они уже должны быть)
        # Добавляем кодированные категориальные признаки, если они ещё не были добавлены
        arg_map = {'deductive': 0, 'inductive': 1, 'dialectical': 2, 'neutral': 3}
        emo_map = {'neutral': 0, 'skepticism': 1, 'dogmatism': 2, 'angst': 3, 'pathos': 4}
        # Если ключи 'Argumentation_code' и 'Emotional_code' уже есть в all_keys, они уже были обработаны выше
        # Если нет, вычисляем их на основе строковых полей
        if 'Argumentation_code' not in self.feature_means:
            arg_codes = []
            for prof in self.period_profiles.values():
                feat = prof.get('features', {})
                arg = feat.get('Argumentation_vector', 'neutral')
                arg_codes.append(arg_map.get(arg, 3))
            if arg_codes:
                self.feature_means['Argumentation_code'] = np.mean(arg_codes)
                self.feature_stds['Argumentation_code'] = np.std(arg_codes) if np.std(arg_codes) > 0 else 1.0
                self.feature_weights['Argumentation_code'] = 1.0 / (self.feature_stds['Argumentation_code'] ** 2 + 1e-6)
                self.feature_weights['Argumentation_code'] *= 2.0
        
        if 'Emotional_code' not in self.feature_means:
            emo_codes = []
            for prof in self.period_profiles.values():
                feat = prof.get('features', {})
                emo = feat.get('Emotional_profile', 'neutral')
                emo_codes.append(emo_map.get(emo, 0))
            if emo_codes:
                self.feature_means['Emotional_code'] = np.mean(emo_codes)
                self.feature_stds['Emotional_code'] = np.std(emo_codes) if np.std(emo_codes) > 0 else 1.0
                self.feature_weights['Emotional_code'] = 1.0 / (self.feature_stds['Emotional_code'] ** 2 + 1e-6)
                self.feature_weights['Emotional_code'] *= 2.0

        print(f"[DEBUG] Нормализация по {len(self.feature_means)} числовым признакам (включая коды).")

    def compare_period(self, text_features, use_oscillation=False, window_size=500, step=100):
        if not self.period_profiles:
            return {}
        # Исключаем строковые и словарные ключи из сравнения, но оставляем все числовые
        exclude = {'word_freq', 'bigram_freq', 'pos_ratios', 'topic_vector', '_raw_text', 'Argumentation_vector', 'Emotional_profile'}
        feat_dict = {k: v for k, v in text_features.items() 
                     if k not in exclude and isinstance(v, (int, float))}
        # Коды уже есть в text_features (если были добавлены в compute_basic_features)
        # Если их нет, добавим на лету
        if 'Argumentation_code' not in feat_dict:
            arg_map = {'deductive': 0, 'inductive': 1, 'dialectical': 2, 'neutral': 3}
            feat_dict['Argumentation_code'] = arg_map.get(text_features.get('Argumentation_vector', 'neutral'), 3)
        if 'Emotional_code' not in feat_dict:
            emo_map = {'neutral': 0, 'skepticism': 1, 'dogmatism': 2, 'angst': 3, 'pathos': 4}
            feat_dict['Emotional_code'] = emo_map.get(text_features.get('Emotional_profile', 'neutral'), 0)

        word_freq = text_features.get('word_freq', {})
        bigram_freq = text_features.get('bigram_freq', {})

        if use_oscillation:
            raw_text = text_features.get('_raw_text', '')
            if raw_text:
                words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', raw_text.lower())
                if words and len(words) > window_size:
                    windows = []
                    for start in range(0, len(words) - window_size + 1, step):
                        window_text = ' '.join(words[start:start+window_size])
                        windows.append(window_text)
                    if windows:
                        window_feats = []
                        for w in windows:
                            f = FeatureExtractor.compute_basic_features(w, use_lemmatization=False)
                            if f:
                                simple_f = {k: v for k, v in f.items() if k not in exclude}
                                window_feats.append(simple_f)
                        if window_feats:
                            avg_feat = {}
                            for key in feat_dict.keys():
                                vals = [f.get(key, 0) for f in window_feats if key in f]
                                if vals:
                                    avg_feat[key] = np.mean(vals)
                                else:
                                    avg_feat[key] = 0.0
                            feat_dict = avg_feat

        similarities = {}
        for key, prof in self.period_profiles.items():
            prof_feat = prof.get('features', {}).copy()
            # Добавляем коды для профиля, если их нет
            if 'Argumentation_code' not in prof_feat:
                arg_map = {'deductive': 0, 'inductive': 1, 'dialectical': 2, 'neutral': 3}
                prof_feat['Argumentation_code'] = arg_map.get(prof_feat.get('Argumentation_vector', 'neutral'), 3)
            if 'Emotional_code' not in prof_feat:
                emo_map = {'neutral': 0, 'skepticism': 1, 'dogmatism': 2, 'angst': 3, 'pathos': 4}
                prof_feat['Emotional_code'] = emo_map.get(prof_feat.get('Emotional_profile', 'neutral'), 0)

            vec1 = np.array([feat_dict.get(k, 0) for k in self.feature_means.keys()])
            vec2 = np.array([prof_feat.get(k, 0) for k in self.feature_means.keys()])
            means = np.array([self.feature_means[k] for k in self.feature_means.keys()])
            stds = np.array([self.feature_stds[k] for k in self.feature_means.keys()])
            stds[stds == 0] = 1.0
            vec1_z = (vec1 - means) / stds
            vec2_z = (vec2 - means) / stds
            weights = np.array([self.feature_weights[k] for k in self.feature_means.keys()])
            weighted_vec1 = vec1_z * weights
            weighted_vec2 = vec2_z * weights
            dot = np.dot(weighted_vec1, weighted_vec2)
            norm1 = np.linalg.norm(weighted_vec1)
            norm2 = np.linalg.norm(weighted_vec2)
            if norm1 > 0 and norm2 > 0:
                cos_sim = dot / (norm1 * norm2)
            else:
                cos_sim = 0
            similarity = max(0, cos_sim) * 100
            similarities[key] = round(similarity, 1)

        # Учёт частот слов (вес 0.4)
        if word_freq:
            for key, prof in self.period_profiles.items():
                prof_word_freq = prof.get('features', {}).get('word_freq', {})
                if prof_word_freq:
                    all_words = set(word_freq.keys()) | set(prof_word_freq.keys())
                    vec1 = np.array([word_freq.get(w, 0) for w in all_words])
                    vec2 = np.array([prof_word_freq.get(w, 0) for w in all_words])
                    if np.linalg.norm(vec1) > 0 and np.linalg.norm(vec2) > 0:
                        freq_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    else:
                        freq_sim = 0
                    if key in similarities:
                        similarities[key] = round(similarities[key] * 0.6 + freq_sim * 100 * 0.4, 1)

        # Учёт биграмм (вес 0.2)
        if bigram_freq:
            for key, prof in self.period_profiles.items():
                prof_bigram_freq = prof.get('features', {}).get('bigram_freq', {})
                if prof_bigram_freq:
                    all_bigrams = set(bigram_freq.keys()) | set(prof_bigram_freq.keys())
                    vec1 = np.array([bigram_freq.get(b, 0) for b in all_bigrams])
                    vec2 = np.array([prof_bigram_freq.get(b, 0) for b in all_bigrams])
                    if np.linalg.norm(vec1) > 0 and np.linalg.norm(vec2) > 0:
                        bigram_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    else:
                        bigram_sim = 0
                    if key in similarities:
                        similarities[key] = round(similarities[key] * 0.7 + bigram_sim * 100 * 0.2, 1)

        if not similarities:
            return {}
        total = sum(similarities.values())
        if total > 0:
            for key in similarities:
                similarities[key] = round(similarities[key] / total * 100, 1)
        return similarities

    def compare_philosopher(self, text_features, use_oscillation=False, window_size=500, step=100):
        if not self.philosopher_profiles:
            return {}
        exclude = {'word_freq', 'bigram_freq', 'pos_ratios', 'topic_vector', '_raw_text', 'Argumentation_vector', 'Emotional_profile'}
        feat_dict = {k: v for k, v in text_features.items() 
                     if k not in exclude and isinstance(v, (int, float))}
        if 'Argumentation_code' not in feat_dict:
            arg_map = {'deductive': 0, 'inductive': 1, 'dialectical': 2, 'neutral': 3}
            feat_dict['Argumentation_code'] = arg_map.get(text_features.get('Argumentation_vector', 'neutral'), 3)
        if 'Emotional_code' not in feat_dict:
            emo_map = {'neutral': 0, 'skepticism': 1, 'dogmatism': 2, 'angst': 3, 'pathos': 4}
            feat_dict['Emotional_code'] = emo_map.get(text_features.get('Emotional_profile', 'neutral'), 0)

        word_freq = text_features.get('word_freq', {})
        bigram_freq = text_features.get('bigram_freq', {})

        if use_oscillation:
            raw_text = text_features.get('_raw_text', '')
            if raw_text:
                words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', raw_text.lower())
                if words and len(words) > window_size:
                    windows = []
                    for start in range(0, len(words) - window_size + 1, step):
                        window_text = ' '.join(words[start:start+window_size])
                        windows.append(window_text)
                    if windows:
                        window_feats = []
                        for w in windows:
                            f = FeatureExtractor.compute_basic_features(w, use_lemmatization=False)
                            if f:
                                simple_f = {k: v for k, v in f.items() if k not in exclude}
                                window_feats.append(simple_f)
                        if window_feats:
                            avg_feat = {}
                            for key in feat_dict.keys():
                                vals = [f.get(key, 0) for f in window_feats if key in f]
                                if vals:
                                    avg_feat[key] = np.mean(vals)
                                else:
                                    avg_feat[key] = 0.0
                            feat_dict = avg_feat

        similarities = {}
        for key, prof in self.philosopher_profiles.items():
            prof_feat = prof.get('features', {}).copy()
            if 'Argumentation_code' not in prof_feat:
                arg_map = {'deductive': 0, 'inductive': 1, 'dialectical': 2, 'neutral': 3}
                prof_feat['Argumentation_code'] = arg_map.get(prof_feat.get('Argumentation_vector', 'neutral'), 3)
            if 'Emotional_code' not in prof_feat:
                emo_map = {'neutral': 0, 'skepticism': 1, 'dogmatism': 2, 'angst': 3, 'pathos': 4}
                prof_feat['Emotional_code'] = emo_map.get(prof_feat.get('Emotional_profile', 'neutral'), 0)

            vec1 = np.array([feat_dict.get(k, 0) for k in self.feature_means.keys()])
            vec2 = np.array([prof_feat.get(k, 0) for k in self.feature_means.keys()])
            means = np.array([self.feature_means[k] for k in self.feature_means.keys()])
            stds = np.array([self.feature_stds[k] for k in self.feature_means.keys()])
            stds[stds == 0] = 1.0
            vec1_z = (vec1 - means) / stds
            vec2_z = (vec2 - means) / stds
            weights = np.array([self.feature_weights[k] for k in self.feature_means.keys()])
            weighted_vec1 = vec1_z * weights
            weighted_vec2 = vec2_z * weights
            dot = np.dot(weighted_vec1, weighted_vec2)
            norm1 = np.linalg.norm(weighted_vec1)
            norm2 = np.linalg.norm(weighted_vec2)
            if norm1 > 0 and norm2 > 0:
                cos_sim = dot / (norm1 * norm2)
            else:
                cos_sim = 0
            similarity = max(0, cos_sim) * 100
            similarities[key] = round(similarity, 1)

        if word_freq:
            for key, prof in self.philosopher_profiles.items():
                prof_word_freq = prof.get('features', {}).get('word_freq', {})
                if prof_word_freq:
                    all_words = set(word_freq.keys()) | set(prof_word_freq.keys())
                    vec1 = np.array([word_freq.get(w, 0) for w in all_words])
                    vec2 = np.array([prof_word_freq.get(w, 0) for w in all_words])
                    if np.linalg.norm(vec1) > 0 and np.linalg.norm(vec2) > 0:
                        freq_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    else:
                        freq_sim = 0
                    if key in similarities:
                        similarities[key] = round(similarities[key] * 0.6 + freq_sim * 100 * 0.4, 1)

        if bigram_freq:
            for key, prof in self.philosopher_profiles.items():
                prof_bigram_freq = prof.get('features', {}).get('bigram_freq', {})
                if prof_bigram_freq:
                    all_bigrams = set(bigram_freq.keys()) | set(prof_bigram_freq.keys())
                    vec1 = np.array([bigram_freq.get(b, 0) for b in all_bigrams])
                    vec2 = np.array([prof_bigram_freq.get(b, 0) for b in all_bigrams])
                    if np.linalg.norm(vec1) > 0 and np.linalg.norm(vec2) > 0:
                        bigram_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    else:
                        bigram_sim = 0
                    if key in similarities:
                        similarities[key] = round(similarities[key] * 0.7 + bigram_sim * 100 * 0.2, 1)

        if not similarities:
            return {}
        total = sum(similarities.values())
        if total > 0:
            for key in similarities:
                similarities[key] = round(similarities[key] / total * 100, 1)
        return similarities

# ------------------------------------------------------------------
# 5. Аналитический навигатор O(1) – без изменений
# ------------------------------------------------------------------
class PureNavigator:
    def __init__(self):
        self.beta = 2.0 / 3.0
        self.kappa_c = 1.0 / 3.0
        self.q = (1.5) ** (1.0 / 3.0)
        self.period = 16.5
        self.offset = 80.0

    def navigate(self, text, max_steps=30):
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            return {"status": "ERROR", "message": "Текст слишком короткий"}

        total = len(sentences)
        current_pos = total // 2
        path = [current_pos]
        prev_pos = -1

        mu_non_sys = self.period / (math.log(self.q) * 382.0)

        for step_idx in range(max_steps):
            left = max(0, current_pos - 3)
            right = min(total, current_pos + 4)
            window_text = " ".join(sentences[left:right])

            words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{3,}\b', window_text.lower())
            if len(words) < 5:
                break

            counts = Counter(words)
            total_words = len(words)
            h_d = 0.0
            for cnt in counts.values():
                p = cnt / total_words
                h_d -= p * math.log2(p)

            unique_ratio = len(counts) / total_words
            avg_len = sum(len(w) for w in words) / total_words
            h_i = max(0.1, h_d * unique_ratio * avg_len / 5.0)

            ttr = len(counts) / total_words
            asymptotic = 1.0 / math.log(max(total_words, 2.0))
            delta_fluc = abs(ttr - asymptotic)

            K_eff = h_d / h_i if h_i > 0 else 1.0

            n_f = math.log(current_pos + 1) / math.log(self.q)
            phase = (math.pi / self.period) * (n_f - self.offset)
            sign_gate = 1 if math.sin(phase) >= 0 else -1

            error_attenuation = K_eff ** (-self.beta)
            step_magnitude = math.log(1.0 + mu_non_sys * delta_fluc)
            nav_step = sign_gate * self.kappa_c * error_attenuation * step_magnitude

            step_in_windows = int(round(nav_step * 150))
            if step_in_windows == 0:
                step_in_windows = 1 if nav_step > 0 else -1

            new_pos = current_pos + step_in_windows
            new_pos = max(0, min(total - 1, new_pos))

            if abs(new_pos - current_pos) < 2 and step_idx > 2:
                path.append(new_pos)
                current_pos = new_pos
                break

            if new_pos == current_pos or new_pos == prev_pos:
                break

            prev_pos = current_pos
            current_pos = new_pos
            path.append(current_pos)

            if len(set(path[-5:])) == 1 and len(path) > 5:
                break

        best_pos = current_pos
        left = max(0, best_pos - 3)
        right = min(total, best_pos + 4)
        best_text = " ".join(sentences[left:right])

        words_pk = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{3,}\b', best_text.lower())
        if words_pk:
            counts_pk = Counter(words_pk)
            total_pk = len(words_pk)
            h_d_pk = 0.0
            for cnt in counts_pk.values():
                p = cnt / total_pk
                h_d_pk -= p * math.log2(p)
            unique_ratio_pk = len(counts_pk) / total_pk
            avg_len_pk = sum(len(w) for w in words_pk) / total_pk
            h_i_pk = max(0.1, h_d_pk * unique_ratio_pk * avg_len_pk / 5.0)
            keff_pk = h_d_pk / h_i_pk if h_i_pk > 0 else 0.0
        else:
            keff_pk = 0.0

        n_f_best = math.log(best_pos + 1) / math.log(self.q)
        phase_info = self._detect_phase(n_f_best)

        return {
            "status": "FOUND",
            "position": best_pos,
            "keff": keff_pk,
            "text": best_text,
            "phase": phase_info,
            "total_windows": total,
            "path": path,
            "mode": "analytical"
        }

    def _detect_phase(self, n_f):
        mod = n_f % self.period
        theta = (math.pi / self.period) * (n_f - self.offset)
        abs_sin = abs(math.sin(theta))
        if abs_sin < 0.1:
            return {"type": "FIRST_ORDER", "desc": "Первый порядок (смена полярности)", "bidirectional": True}
        elif abs_sin > 0.9 and 7.0 <= mod <= 9.5:
            return {"type": "SECOND_ORDER", "desc": "Второй порядок (смысловая пустыня)", "bidirectional": True}
        elif 7.0 <= mod <= 9.0:
            return {"type": "TRANSITION_ZONE", "desc": "Переходная зона (реструктуризация)", "bidirectional": True}
        elif 0.0 <= mod <= 7.0:
            return {"type": "STABLE_SOURCE", "desc": "Стабильный узел (Source)", "bidirectional": False}
        elif 9.0 <= mod <= 16.5:
            return {"type": "STABLE_SINK", "desc": "Стабильный узел (Sink)", "bidirectional": False}
        return {"type": "UNKNOWN", "desc": "Неопределённая зона", "bidirectional": False}

# ------------------------------------------------------------------
# 6. Главное приложение (GUI) – v9.13
# ------------------------------------------------------------------
class YUCTApp:
    def __init__(self, root):
        self.root = root
        self.raw_text = ""
        self.source_name = ""
        self.source_base = ""
        # Используем resource_path для корректного доступа к profiles.json
        self.comparator = PhilosopherComparator(resource_path('profiles/profiles.json'))
        self.navigator = PureNavigator()
        self.last_report = {}
        self.chapter_mode = tk.StringVar(value="auto")
        self.use_lemmatization = tk.BooleanVar(value=True)
        self.is_loaded = False
        self.is_analyzing = False

        self.root.title("YUСT Семантический процессор v9.13")
        self.root.geometry("800x780")
        self.root.configure(bg="#f0f4f8")
        self.root.grid_rowconfigure(10, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        tk.Label(root, text="YUСT Семантический навигатор v9.13 – Полная философская аналитика",
                 font=("Arial", 12, "bold"), bg="#f0f4f8", fg="#1a365d").grid(row=0, column=0, pady=5, sticky="ew")

        load_frame = tk.Frame(root, bg="#f0f4f8")
        load_frame.grid(row=1, column=0, pady=5, sticky="ew")
        load_frame.grid_columnconfigure(0, weight=1)
        load_frame.grid_columnconfigure(1, weight=0)
        load_frame.grid_columnconfigure(2, weight=0)
        load_frame.grid_columnconfigure(3, weight=0)
        load_frame.grid_columnconfigure(4, weight=1)

        self.btn_load = tk.Button(load_frame, text="📂 Загрузить файл", command=self.load_file_threaded,
                                  font=("Arial", 9), bg="#4a5568", fg="white", padx=6, pady=4,
                                  relief="flat", borderwidth=0, highlightthickness=0)
        self.btn_load.grid(row=0, column=1, padx=4)

        self.entry_url = tk.Entry(load_frame, width=40, font=("Arial", 9))
        self.entry_url.grid(row=0, column=2, padx=4)

        self.btn_url = tk.Button(load_frame, text="🔗 Загрузить URL", command=self.load_url_threaded,
                                 font=("Arial", 9), bg="#4a5568", fg="white", padx=6, pady=4,
                                 relief="flat", borderwidth=0, highlightthickness=0)
        self.btn_url.grid(row=0, column=3, padx=4)

        self.load_progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.load_progress.grid(row=2, column=0, pady=3, sticky="ew")
        self.load_progress['value'] = 0

        self.lbl_file = tk.Label(root, text="", font=("Arial", 9, "italic"), bg="#f0f4f8", fg="#4a5568")
        self.lbl_file.grid(row=3, column=0, pady=2, sticky="ew")

        self.txt_preview = scrolledtext.ScrolledText(root, width=85, height=4, font=("Arial", 9), bg="#f8f9fa", fg="#2d3748", bd=1, relief="solid")
        self.txt_preview.grid(row=4, column=0, pady=3, padx=10, sticky="ew")
        self.txt_preview.insert(tk.END, "Превью загруженного текста появится здесь...")
        self.txt_preview.config(state=tk.DISABLED)

        settings_frame = tk.Frame(root, bg="#f0f4f8")
        settings_frame.grid(row=5, column=0, pady=3, sticky="ew")
        tk.Label(settings_frame, text="Режим глав:", bg="#f0f4f8", font=("Arial", 9)).pack(side="left", padx=4)
        self.chapter_menu = ttk.Combobox(settings_frame, textvariable=self.chapter_mode,
                                         values=["auto", "paragraphs", "fixed"], width=10, font=("Arial", 9))
        self.chapter_menu.pack(side="left", padx=4)
        tk.Checkbutton(settings_frame, text="Лемматизация", variable=self.use_lemmatization,
                       bg="#f0f4f8", font=("Arial", 9)).pack(side="left", padx=10)

        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        self.lbl_status = tk.Label(root, textvariable=self.status_var, font=("Arial", 9, "italic"),
                                   bg="#f0f4f8", fg="#4a5568")
        self.lbl_status.grid(row=6, column=0, pady=2, sticky="ew")

        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.grid(row=7, column=0, pady=3, sticky="ew")
        self.progress['value'] = 0

        btn_frame = tk.Frame(root, bg="#f0f4f8")
        btn_frame.grid(row=8, column=0, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=0)
        btn_frame.grid_columnconfigure(2, weight=0)
        btn_frame.grid_columnconfigure(3, weight=0)
        btn_frame.grid_columnconfigure(4, weight=0)
        btn_frame.grid_columnconfigure(5, weight=0)
        btn_frame.grid_columnconfigure(6, weight=1)

        btn_style = {"font": ("Arial", 9), "bg": "#4a5568", "fg": "white",
                     "padx": 6, "pady": 4, "relief": "flat", "borderwidth": 0, "highlightthickness": 0}

        self.btn_analyze = tk.Button(btn_frame, text="🔍 Анализ (с главами)", command=self.static_analysis_threaded, **btn_style)
        self.btn_analyze.grid(row=0, column=1, padx=4)
        self.btn_analyze.config(state=tk.DISABLED)

        self.btn_navigate = tk.Button(btn_frame, text="🧭 Навигация (O(1))", command=self.navigation_threaded, **btn_style)
        self.btn_navigate.grid(row=0, column=2, padx=4)
        self.btn_navigate.config(state=tk.DISABLED)

        self.btn_export = tk.Button(btn_frame, text="📤 Экспорт JSON", command=self.export_json, **btn_style)
        self.btn_export.grid(row=0, column=3, padx=4)

        self.btn_clear = tk.Button(btn_frame, text="🗑 Очистить", command=self.clear_output, **btn_style)
        self.btn_clear.grid(row=0, column=4, padx=4)

        self.btn_help = tk.Button(btn_frame, text="(i) Пояснения", command=self.show_help, **btn_style)
        self.btn_help.grid(row=0, column=5, padx=4)

        self.txt_output = scrolledtext.ScrolledText(root, width=88, height=20, font=("Courier New", 9),
                                                    bg="white", fg="#2d3748", bd=1, relief="solid")
        self.txt_output.grid(row=9, column=0, pady=5, padx=10, sticky="nsew")
        self.root.grid_rowconfigure(9, weight=1)

        footer_frame = tk.Frame(root, bg="#f0f4f8")
        footer_frame.grid(row=10, column=0, pady=5, sticky="ew")
        tk.Label(footer_frame, text="Специально для портала «Философский штурм» http://philosophystorm.ru/",
                 font=("Arial", 9, "bold"), bg="#f0f4f8", fg="#1a365d").pack()
        tk.Label(footer_frame, text="Проект распространяется под лицензией Creative Commons Attribution 4.0 International (CC BY 4.0).",
                 font=("Arial", 8), bg="#f0f4f8", fg="#718096").pack()

        self.beep_done = lambda: winsound.Beep(1000, 500)

    # ---------- Методы загрузки (без изменений) ----------
    def load_file_threaded(self):
        threading.Thread(target=self.load_file, daemon=True).start()

    def load_file(self):
        self.root.after(0, lambda: self.status_var.set("Загрузка файла..."))
        self.root.after(0, lambda: self.load_progress.config(value=0))
        self.root.after(0, lambda: self.btn_analyze.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_navigate.config(state=tk.DISABLED))

        file_path = filedialog.askopenfilename(
            filetypes=[("Все поддерживаемые", "*.txt *.pdf *.tex"),
                       ("Text files", "*.txt"),
                       ("PDF files", "*.pdf"),
                       ("LaTeX files", "*.tex")]
        )
        if not file_path:
            self.root.after(0, lambda: self.status_var.set("Готов"))
            self.root.after(0, lambda: self.load_progress.config(value=0))
            return

        self.source_base = os.path.splitext(os.path.basename(file_path))[0]
        self.root.after(0, lambda: self.lbl_file.config(text=f"Загрузка: {os.path.basename(file_path)}..."))
        self.root.after(0, lambda: self.load_progress.config(value=20))

        try:
            ext = os.path.splitext(file_path)[1].lower()
            text = ""
            if ext == '.pdf':
                if HAS_PDFPLUMBER:
                    try:
                        with pdfplumber.open(file_path) as pdf:
                            total_pages = len(pdf.pages)
                            for i, page in enumerate(pdf.pages):
                                page_text = page.extract_text()
                                if page_text:
                                    text += page_text + "\n"
                                progress = 20 + int(70 * (i+1) / total_pages)
                                self.root.after(0, lambda p=progress: self.load_progress.config(value=p))
                    except Exception as e:
                        messagebox.showerror("Ошибка", f"Не удалось прочитать PDF: {e}")
                        self.root.after(0, lambda: self.status_var.set("Готов"))
                        return
                else:
                    messagebox.showerror("Ошибка", "Установите pdfplumber: pip install pdfplumber")
                    self.root.after(0, lambda: self.status_var.set("Готов"))
                    return
            elif ext == '.tex':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        raw = f.read()
                except:
                    with open(file_path, 'r', encoding='cp1251') as f:
                        raw = f.read()
                if messagebox.askyesno("Очистка LaTeX", "Обнаружен .tex файл. Очистить от разметки?"):
                    text = self._clean_tex(raw)
                else:
                    text = raw
                self.root.after(0, lambda: self.load_progress.config(value=90))
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                except:
                    try:
                        with open(file_path, 'r', encoding='cp1251') as f:
                            text = f.read()
                    except:
                        with open(file_path, 'r', encoding='koi8-r') as f:
                            text = f.read()
                self.root.after(0, lambda: self.load_progress.config(value=90))

            if not text.strip():
                messagebox.showerror("Ошибка", "Не удалось извлечь текст из файла.")
                self.root.after(0, lambda: self.status_var.set("Готов"))
                self.root.after(0, lambda: self.load_progress.config(value=0))
                return

            self.raw_text = text
            self.source_name = os.path.basename(file_path)
            self.is_loaded = True

            word_count = len(re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', text))
            status_msg = f"Загружено: {self.source_name} ({len(text)} символов, ~{word_count} слов)"
            if word_count < 300:
                status_msg += " ⚠️ Очень мало!"
            elif word_count < 1000:
                status_msg += " ⚠️ Мало слов."
            else:
                status_msg += " ✅ Достаточно."

            self.root.after(0, lambda: self.lbl_file.config(text=status_msg))
            self.root.after(0, lambda: self.status_var.set("Текст загружен. Нажмите «Анализ»."))
            self.root.after(0, lambda: self.load_progress.config(value=100))

            preview_text = text[:2000] + ("..." if len(text)>2000 else "")
            self.root.after(0, lambda: self.txt_preview.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.txt_preview.delete(1.0, tk.END))
            self.root.after(0, lambda: self.txt_preview.insert(tk.END, preview_text))
            self.root.after(0, lambda: self.txt_preview.config(state=tk.DISABLED))

            self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_navigate.config(state=tk.NORMAL))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            self.root.after(0, lambda: self.status_var.set("Готов"))
            self.root.after(0, lambda: self.load_progress.config(value=0))

    def load_url_threaded(self):
        threading.Thread(target=self.load_url, daemon=True).start()

    def load_url(self):
        self.root.after(0, lambda: self.status_var.set("Загрузка URL..."))
        self.root.after(0, lambda: self.load_progress.config(value=0))
        self.root.after(0, lambda: self.btn_analyze.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_navigate.config(state=tk.DISABLED))

        url = self.entry_url.get().strip()
        if not url:
            messagebox.showwarning("Пустой URL", "Введите URL")
            self.root.after(0, lambda: self.status_var.set("Готов"))
            self.root.after(0, lambda: self.load_progress.config(value=0))
            return

        try:
            import urllib.request
            self.root.after(0, lambda: self.lbl_file.config(text=f"Загрузка URL: {url}..."))
            self.root.after(0, lambda: self.load_progress.config(value=20))

            response = urllib.request.urlopen(url, timeout=10)
            raw = response.read()
            if HAS_CHARDET:
                detected = chardet.detect(raw)
                encoding = detected['encoding'] if detected else 'utf-8'
            else:
                encoding = 'utf-8'
            text = raw.decode(encoding, errors='ignore')
            self.root.after(0, lambda: self.load_progress.config(value=90))

            self.raw_text = text
            self.source_name = url
            self.source_base = re.sub(r'[^a-zA-Z0-9а-яА-Я]', '_', url)[:50]
            self.is_loaded = True

            word_count = len(re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', text))
            status_msg = f"Загружено: {url} ({len(text)} символов, ~{word_count} слов)"
            if word_count < 300:
                status_msg += " ⚠️ Очень мало!"
            elif word_count < 1000:
                status_msg += " ⚠️ Мало слов."
            else:
                status_msg += " ✅ Достаточно."

            self.root.after(0, lambda: self.lbl_file.config(text=status_msg))
            self.root.after(0, lambda: self.status_var.set("URL загружен. Нажмите «Анализ»."))
            self.root.after(0, lambda: self.load_progress.config(value=100))

            preview_text = text[:2000] + ("..." if len(text)>2000 else "")
            self.root.after(0, lambda: self.txt_preview.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.txt_preview.delete(1.0, tk.END))
            self.root.after(0, lambda: self.txt_preview.insert(tk.END, preview_text))
            self.root.after(0, lambda: self.txt_preview.config(state=tk.DISABLED))

            self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_navigate.config(state=tk.NORMAL))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            self.root.after(0, lambda: self.status_var.set("Готов"))
            self.root.after(0, lambda: self.load_progress.config(value=0))

    @staticmethod
    def _clean_tex(text):
        text = re.sub(r'(?<!\\)%.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\\begin{equation\}.*?\\end{equation\}', '', text, flags=re.DOTALL)
        text = re.sub(r'\\begin{align\}.*?\\end{align\}', '', text, flags=re.DOTALL)
        text = re.sub(r'\$.*?\$', '', text, flags=re.DOTALL)
        text = re.sub(r'\\\[.*?\\\]', '', text, flags=re.DOTALL)
        text = re.sub(r'\\(section|subsection|subparagraph|part|chapter)\*?\{.*?\}', '', text)
        text = re.sub(r'\\(label|ref|eqref|cite|bibitem)\{.*?\}', '', text)
        text = re.sub(r'\\begin\{.*?\}', '', text)
        text = re.sub(r'\\end\{.*?\}', '', text)
        text = re.sub(r'\\.*?(\s|$)', ' ', text)
        text = re.sub(r'[{}]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def clear_output(self):
        self.txt_output.delete(1.0, tk.END)
        self.status_var.set("Отчёт очищен")

    # ---------- Статический анализ ----------
    def static_analysis_threaded(self):
        if not self.is_loaded or not self.raw_text:
            messagebox.showwarning("Нет текста", "Сначала загрузите текст")
            return
        if self.is_analyzing:
            return
        self.is_analyzing = True
        self.btn_analyze.config(state=tk.DISABLED)
        self.btn_navigate.config(state=tk.DISABLED)
        threading.Thread(target=self.static_analysis, daemon=True).start()

    def static_analysis(self):
        self.root.after(0, lambda: self.status_var.set("Статический анализ..."))
        self.root.after(0, lambda: self.progress.config(value=0))
        try:
            use_lemma = self.use_lemmatization.get()
            if use_lemma and not HAS_PYMORPHY3:
                self.root.after(0, lambda: messagebox.showwarning("Лемматизация", "pymorphy3 не установлен. Лемматизация отключена."))
                use_lemma = False

            full_features = FeatureExtractor.compute_basic_features(self.raw_text, use_lemmatization=use_lemma)
            if full_features is None:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", "Текст слишком короткий"))
                self.is_analyzing = False
                self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.btn_navigate.config(state=tk.NORMAL))
                return
            full_features['_raw_text'] = self.raw_text
            topic_vector = FeatureExtractor.compute_lda_features(self.raw_text)
            if topic_vector:
                full_features['topic_vector'] = topic_vector

            period_similarities = self.comparator.compare_period(full_features, use_oscillation=False)
            philosopher_similarities = self.comparator.compare_philosopher(full_features, use_oscillation=False)

            self.root.after(0, lambda: self.progress.config(value=30))

            mode = self.chapter_mode.get()
            chapters = self._split_into_chapters(self.raw_text, mode=mode, min_words=100)

            chapter_results = []
            total_chapters = len(chapters)
            for idx, ch in enumerate(chapters):
                title = ch['title']
                text = ch['text']
                if not text.strip():
                    continue
                features = FeatureExtractor.compute_basic_features(text, use_lemmatization=use_lemma)
                if features is None:
                    continue
                features['_raw_text'] = text
                word_count = len(re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', text))
                use_osc = word_count > 5000
                period_local = self.comparator.compare_period(features, use_oscillation=use_osc)
                philosopher_local = self.comparator.compare_philosopher(features, use_oscillation=use_osc)
                chapter_results.append({
                    'title': title,
                    'features': features,
                    'period_similarities': period_local,
                    'philosopher_similarities': philosopher_local,
                    'word_count': word_count
                })
                progress = 30 + int(60 * (idx+1) / total_chapters)
                self.root.after(0, lambda p=progress: self.progress.config(value=p))

            if not chapter_results:
                self.root.after(0, lambda: messagebox.showerror("Ошибка", "Не удалось проанализировать текст."))
                self.is_analyzing = False
                self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.btn_navigate.config(state=tk.NORMAL))
                return

            report = []
            report.append("═══════════════════════════════════════════════════════════════")
            report.append(" СТАТИСТИЧЕСКИЙ АНАЛИЗ (ПО ГЛАВАМ)")
            report.append("═══════════════════════════════════════════════════════════════")
            report.append(f"Размер текста: {len(self.raw_text)} символов")
            report.append(f"Источник: {self.source_name if self.source_name else 'ручной ввод'}")
            report.append(f"Режим разбивки: {self.chapter_mode.get()}, глав: {len(chapter_results)}")
            report.append("")

            for idx, ch in enumerate(chapter_results):
                report.append("───────────────────────────────────────────────────────────────")
                report.append(f"📖 ГЛАВА {idx+1}: {ch['title']} (слов: {ch['word_count']})")
                report.append("───────────────────────────────────────────────────────────────")
                f = ch['features']
                report.append(f"  K_eff: {f.get('K_eff',0):.2f}  |  TTR: {f.get('TTR',0):.3f}  |  Abstract_ratio: {f.get('Abstract_ratio',0):.4f}  |  Агрессия: {f.get('Aggressive_ratio',0):.4f}  |  Депрессия: {f.get('Depressive_ratio',0):.4f}  |  Красноречивость: {f.get('Rhetorical_ratio',0):.4f}")
                report.append(f"  Валентность: {f.get('Valence',0):.2f}  |  Уверенность: {f.get('Certainty_ratio',0):.2f}  |  Читаемость: {f.get('Readability',0):.1f}  |  H_I (связанность текста): {f.get('H_I',0):.2f}")

                # ---- НОВЫЙ БЛОК: ВЕКТОР АРГУМЕНТАЦИИ ----
                report.append("───────────────────────────────────────────────────────────────")
                report.append("🎯 ВЕКТОР АРГУМЕНТАЦИИ (Силлогизм)")
                report.append("───────────────────────────────────────────────────────────────")
                arg_vec = f.get('Argumentation_vector', 'unknown')
                arg_slope = f.get('Argumentation_slope', 0)
                direction_map = {
                    'deductive': 'Дедуктивный (от общего к частному)',
                    'inductive': 'Индуктивный (от частного к общему)',
                    'dialectical': 'Диалектический (тезис-антитезис-синтез)',
                    'neutral': 'Нейтральный'
                }
                report.append(f"  Тип аргументации: {direction_map.get(arg_vec, 'Не определён')}")
                report.append(f"  Градиент абстракции: {arg_slope:.3f}")

                # ---- НОВЫЙ БЛОК: СЕМАНТИЧЕСКАЯ МНОГОЗНАЧНОСТЬ ----
                report.append("───────────────────────────────────────────────────────────────")
                report.append("📚 СЕМАНТИЧЕСКАЯ МНОГОЗНАЧНОСТЬ")
                report.append("───────────────────────────────────────────────────────────────")
                report.append(f"  Индекс изолированности: {f.get('Isolation_index', 0):.3f} (выше — более авторский язык)")
                report.append(f"  Категориальная энтропия: {f.get('Category_entropy', 0):.3f} (ниже — фокус на одной категории)")

                # ---- НОВЫЙ БЛОК: ЭМОЦИОНАЛЬНЫЙ СПЕКТР ----
                report.append("───────────────────────────────────────────────────────────────")
                report.append("🎭 ЭМОЦИОНАЛЬНЫЙ СПЕКТР (когнитивные аффекты)")
                report.append("───────────────────────────────────────────────────────────────")
                report.append(f"  Скепсис: {f.get('Skepticism', 0):.3f} (вопросы, сомнения, критика)")
                report.append(f"  Догматизм: {f.get('Dogmatism', 0):.3f} (категоричность, уверенность)")
                report.append(f"  Экзистенциальная тревога: {f.get('Angst', 0):.3f} (Angst, страх, отчаяние)")
                report.append(f"  Пафос: {f.get('Pathos', 0):.3f} (возвышенность, риторика)")
                profile = f.get('Emotional_profile', 'neutral')
                profile_map = {
                    'skepticism': 'Скептический',
                    'dogmatism': 'Догматический',
                    'angst': 'Экзистенциальный',
                    'pathos': 'Пафосный',
                    'neutral': 'Нейтральный'
                }
                report.append(f"  Доминирующий профиль: {profile_map.get(profile, 'Не определён')}")

                # Локальные сравнения
                if ch['period_similarities']:
                    best_period = max(ch['period_similarities'], key=ch['period_similarities'].get)
                    best_period_score = ch['period_similarities'][best_period]
                    report.append(f"  🏆 Ближайший период: {best_period} ({best_period_score}%)")
                if ch['philosopher_similarities']:
                    best_phil = max(ch['philosopher_similarities'], key=ch['philosopher_similarities'].get)
                    best_phil_score = ch['philosopher_similarities'][best_phil]
                    report.append(f"  🧑 Ближайший философ: {best_phil} ({best_phil_score}%)")
                if not ch['period_similarities'] and not ch['philosopher_similarities']:
                    report.append("  (нет данных локального сравнения)")
                report.append("")

            # Сравнение для всего текста (по периодам)
            report.append("───────────────────────────────────────────────────────────────")
            report.append("🧠 СРАВНЕНИЕ С ЭТАЛОННЫМИ ПРОФИЛЯМИ (ПО ПЕРИОДАМ)")
            report.append("───────────────────────────────────────────────────────────────")
            if period_similarities:
                report.append("  Философ (период)  |  % сходства")
                report.append("  ------------------|-------------")
                by_philosopher = defaultdict(dict)
                for key, val in period_similarities.items():
                    parts = key.split('_')
                    if len(parts) >= 2:
                        phil = parts[0]
                        period = parts[1]
                        by_philosopher[phil][period] = val
                for phil, periods in sorted(by_philosopher.items()):
                    for period, score in sorted(periods.items(), key=lambda x: x[1], reverse=True):
                        label = f"{phil} ({period})"
                        report.append(f"  {label:<18} |   {score}%")
                best_period_full = max(period_similarities, key=period_similarities.get)
                best_period_score = period_similarities[best_period_full]
                report.append("")
                report.append(f"  🏆 Наиболее близкий период: {best_period_full} ({best_period_score}%)")
            else:
                report.append("  Нет данных сравнения по периодам.")
            report.append("")

            # Сравнение для всего текста (по философам)
            report.append("───────────────────────────────────────────────────────────────")
            report.append("🧑 СРАВНЕНИЕ С ЭТАЛОННЫМИ ПРОФИЛЯМИ (ПО ФИЛОСОФАМ)")
            report.append("───────────────────────────────────────────────────────────────")
            if philosopher_similarities:
                report.append("  Философ  |  % сходства")
                report.append("  ---------|-------------")
                for phil, score in sorted(philosopher_similarities.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"  {phil:<8} |   {score}%")
                best_phil_full = max(philosopher_similarities, key=philosopher_similarities.get)
                best_phil_score = philosopher_similarities[best_phil_full]
                report.append("")
                report.append(f"  🏆 Наиболее близкий философ: {best_phil_full} ({best_phil_score}%)")
            else:
                report.append("  Нет данных сравнения по философам.")
            report.append("")

            # Сводная таблица по периодам (усреднённая по главам)
            report.append("───────────────────────────────────────────────────────────────")
            report.append("📊 СВОДНАЯ ТАБЛИЦА (усреднённые проценты по главам)")
            report.append("───────────────────────────────────────────────────────────────")
            period_agg = defaultdict(list)
            phil_agg = defaultdict(list)
            for ch in chapter_results:
                for key, val in ch.get('period_similarities', {}).items():
                    period_agg[key].append(val)
                for key, val in ch.get('philosopher_similarities', {}).items():
                    phil_agg[key].append(val)

            if period_agg:
                avg_period = {k: round(np.mean(vals), 1) for k, vals in period_agg.items()}
                sorted_period = sorted(avg_period.items(), key=lambda x: x[1], reverse=True)[:10]
                report.append("  По периодам (топ-10):")
                for key, val in sorted_period:
                    report.append(f"    {key:<18} |   {val}%")
                report.append("")
            if phil_agg:
                avg_phil = {k: round(np.mean(vals), 1) for k, vals in phil_agg.items()}
                sorted_phil = sorted(avg_phil.items(), key=lambda x: x[1], reverse=True)[:10]
                report.append("  По философам (топ-10):")
                for key, val in sorted_phil:
                    report.append(f"    {key:<8} |   {val}%")
            else:
                report.append("  Нет данных для сводной таблицы.")
            report.append("")

            # Общие показатели
            report.append("───────────────────────────────────────────────────────────────")
            report.append("📊 ОБЩИЕ ПОКАЗАТЕЛИ (усреднённые по главам)")
            report.append("───────────────────────────────────────────────────────────────")
            total_words = sum(ch['word_count'] for ch in chapter_results)
            avg_features = {}
            for key in chapter_results[0]['features'].keys():
                if key in ['_raw_text', 'topic_vector', 'word_freq', 'bigram_freq', 'pos_ratios', 'Argumentation_vector', 'Emotional_profile']:
                    continue
                weighted_sum = 0.0
                for ch in chapter_results:
                    weighted_sum += ch['features'].get(key, 0) * ch['word_count']
                avg_features[key] = weighted_sum / total_words if total_words > 0 else 0

            metrics_table = [
                ("K_eff (средний)", avg_features.get('K_eff', 0)),
                ("TTR (средний)", avg_features.get('TTR', 0)),
                ("Abstract_ratio (средний)", avg_features.get('Abstract_ratio', 0)),
                ("Агрессия (средняя)", avg_features.get('Aggressive_ratio', 0)),
                ("Депрессия (средняя)", avg_features.get('Depressive_ratio', 0)),
                ("Красноречивость (средняя)", avg_features.get('Rhetorical_ratio', 0)),
                ("Валентность (средняя)", avg_features.get('Valence', 0)),
                ("Уверенность (средняя)", avg_features.get('Certainty_ratio', 0)),
                ("Читаемость (средняя)", avg_features.get('Readability', 0)),
                ("H_I (средняя)", avg_features.get('H_I', 0)),
            ]
            report.append("  Метрика               |  Значение")
            report.append("  ----------------------|-----------")
            for label, val in metrics_table:
                if isinstance(val, float):
                    report.append(f"  {label:<21} |   {val:.2f}" if val != int(val) else f"  {label:<21} |   {val:.0f}")
                else:
                    report.append(f"  {label:<21} |   {val}")

            genre_probs = self._classify_genre(avg_features)
            genre_label = {'scientific': 'Научный', 'philosophical': 'Философский',
                           'prose': 'Художественная проза', 'poetry': 'Поэзия',
                           'publicistic': 'Публицистика'}.get(genre_probs.get('dominant', 'unknown'), 'Не определён')
            report.append(f"  Жанр (по средним)     |   {genre_label}")

            ai_result = self._detect_ai(avg_features)
            report.append(f"  Вероятность ИИ        |   {ai_result['probability']}%")

            report.append("")
            report.append("───────────────────────────────────────────────────────────────")
            report.append("Специально для портала «Философский штурм»")
            report.append("https://github.com/Alexey-Yakushev-YUCT/verify-quant-philosophy/releases/")
            report.append("═══════════════════════════════════════════════════════════════")

            self.root.after(0, lambda: self.txt_output.delete(1.0, tk.END))
            self.root.after(0, lambda: self.txt_output.insert(tk.END, "\n".join(report)))
            self.root.after(0, lambda: self.status_var.set("Анализ завершён"))
            self.root.after(0, lambda: self.progress.config(value=100))
            self.root.after(0, self.beep_done)

            self.last_report['static'] = {
                'chapters': chapter_results,
                'average': avg_features,
                'genre': genre_probs,
                'ai': ai_result,
                'period_similarities': period_similarities,
                'philosopher_similarities': philosopher_similarities
            }
            self.is_analyzing = False
            self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_navigate.config(state=tk.NORMAL))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка анализа", str(e)))
            self.is_analyzing = False
            self.root.after(0, lambda: self.btn_analyze.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_navigate.config(state=tk.NORMAL))

    # ---------- Вспомогательные методы ----------
    def _split_into_chapters(self, text, mode='auto', min_words=100):
        if mode == 'auto':
            sections = []
            lines = text.split('\n')
            current_title = "Начало"
            current_text = []
            for line in lines:
                if re.match(r'(?:Глава|CHAPTER|Chapter|Part|PART|Раздел|§)\s*[0-9IVXLCDM]+', line, re.IGNORECASE):
                    if current_text:
                        sections.append({'title': current_title, 'text': '\n'.join(current_text)})
                        current_text = []
                    current_title = line.strip()[:100]
                else:
                    current_text.append(line)
            if current_text:
                sections.append({'title': current_title, 'text': '\n'.join(current_text)})
            if len(sections) <= 1:
                paragraphs = [p for p in text.split('\n\n') if p.strip()]
                if len(paragraphs) > 5:
                    chunk_size = max(3, len(paragraphs) // 10)
                    sections = []
                    for i in range(0, len(paragraphs), chunk_size):
                        chunk = '\n\n'.join(paragraphs[i:i+chunk_size])
                        sections.append({'title': f"Блок {i//chunk_size+1}", 'text': chunk})
                else:
                    sections = [{'title': 'Весь текст', 'text': text}]
        elif mode == 'paragraphs':
            paragraphs = [p for p in text.split('\n\n') if p.strip()]
            sections = [{'title': f"Параграф {i+1}", 'text': p} for i, p in enumerate(paragraphs)]
        elif mode == 'fixed':
            words = re.findall(r'\b\w+\b', text)
            chunk_size = 3000
            sections = []
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i+chunk_size])
                sections.append({'title': f"Фрагмент {i//chunk_size+1}", 'text': chunk})
        else:
            sections = [{'title': 'Весь текст', 'text': text}]
        merged = []
        for ch in sections:
            word_count = len(re.findall(r'\b[а-яА-ЯёЁa-zA-Z]{2,}\b', ch['text']))
            if word_count < min_words and merged:
                merged[-1]['text'] += "\n\n" + ch['text']
                merged[-1]['title'] += " / " + ch['title']
            else:
                merged.append(ch)
        return merged

    def _classify_genre(self, features):
        k_eff = features.get('K_eff', 0)
        ttr = features.get('TTR', 0)
        expr = features.get('Exclam_density', 0) + features.get('Quest_density', 0) * 0.8
        avg_sent = features.get('Avg_sent_len', 0)
        long_sent = features.get('Long_sent_ratio', 0)
        abstract = features.get('Abstract_ratio', 0)
        readability = features.get('Readability', 0)
        part_ratio = features.get('Part_ratio', 0)
        log_dens = features.get('Log_marker_density', 0)

        sci_score = 0.0
        if readability < 30 and avg_sent > 20 and long_sent > 0.3 and log_dens > 1.0:
            sci_score = 1.0
        elif readability < 40 and avg_sent > 18 and log_dens > 0.7:
            sci_score = 0.7
        else:
            sci_score = max(0, (30 - readability) / 30) * (avg_sent / 25) * min(1, log_dens / 1.5)

        phi_score = 0.0
        if abstract > 0.008 and readability < 45 and avg_sent > 18 and log_dens > 0.5:
            phi_score = 1.0
        elif abstract > 0.005 and readability < 50:
            phi_score = 0.7
        else:
            phi_score = min(1, abstract * 100) * (50 / (readability + 10))

        prose_score = 0.0
        if 0.3 < expr < 3.0 and 8 < avg_sent < 20 and abstract < 0.01 and readability > 40:
            prose_score = 1.0
        elif 0.2 < expr < 4.0 and avg_sent < 25:
            prose_score = 0.7
        else:
            prose_score = min(1, expr / 2.0) * (1 - abs(avg_sent - 14) / 14) * (1 - abstract * 50)

        poetry_score = 0.0
        if expr > 2.0 and avg_sent < 12 and abstract < 0.008:
            poetry_score = 0.8
        elif expr > 1.0 and avg_sent < 10:
            poetry_score = 0.5
        else:
            poetry_score = min(1, expr / 3.0) * (12 / (avg_sent + 1))

        pub_score = 0.0
        if 1.0 < expr < 5.0 and 10 < avg_sent < 22 and readability > 30 and part_ratio > 0.03:
            pub_score = 1.0
        elif 0.5 < expr < 6.0 and avg_sent > 12:
            pub_score = 0.6
        else:
            pub_score = min(1, expr / 3.0) * (avg_sent / 18) * min(1, part_ratio * 20)

        total = sci_score + phi_score + prose_score + poetry_score + pub_score
        if total == 0:
            return {'scientific': 0, 'philosophical': 0, 'prose': 0, 'poetry': 0, 'publicistic': 0, 'dominant': 'unknown'}
        probs = {
            'scientific': round(sci_score / total, 2),
            'philosophical': round(phi_score / total, 2),
            'prose': round(prose_score / total, 2),
            'poetry': round(poetry_score / total, 2),
            'publicistic': round(pub_score / total, 2)
        }
        probs['dominant'] = max(probs, key=probs.get)
        return probs

    def _detect_ai(self, features):
        score = 0.0
        reasons = []
        ttr = features.get('TTR', 0.5)
        if ttr > 0.75:
            score += 0.25
            reasons.append("Слишком высокое лексическое разнообразие (TTR > 0.75)")
        elif ttr < 0.25:
            score += 0.15
            reasons.append("Слишком низкое лексическое разнообразие (TTR < 0.25)")
        beta = features.get('Beta_Zipf', 1.0)
        if beta > 1.2:
            score += 0.20
            reasons.append("Аномальное распределение Ципфа (>1.2)")
        elif beta < 0.6:
            score += 0.20
            reasons.append("Аномальное распределение Ципфа (<0.6)")
        rhythm = features.get('Sent_rhythm_var', 0.5)
        if rhythm < 0.3:
            score += 0.20
            reasons.append("Слишком ровный ритм предложений (признак шаблонности)")
        punct = features.get('Punct_density', 15)
        if punct > 30:
            score += 0.15
            reasons.append("Избыточная пунктуация (возможно, искусственная)")
        readability = features.get('Readability', 50)
        abstract = features.get('Abstract_ratio', 0)
        if readability > 60 and abstract > 0.01:
            score += 0.10
            reasons.append("Простой язык при высокой абстракции (подозрительно)")
        avg_sent = features.get('Avg_sent_len', 15)
        if avg_sent < 8:
            score += 0.05
            reasons.append("Очень короткие предложения (примитивизация)")
        if avg_sent > 40:
            score += 0.05
            reasons.append("Очень длинные предложения (искусственное усложнение)")
        prob = min(1.0, score)
        if prob < 0.2:
            label = "С высокой вероятностью написан человеком"
        elif prob < 0.4:
            label = "Возможно, человек, но есть признаки шаблонности"
        elif prob < 0.6:
            label = "Средняя вероятность ИИ-генерации"
        elif prob < 0.8:
            label = "Высокая вероятность ИИ-генерации"
        else:
            label = "Почти наверняка сгенерирован ИИ"
        return {'probability': round(prob * 100, 1), 'label': label, 'reasons': reasons}

    # ---------- Навигация ----------
    def navigation_threaded(self):
        if not self.is_loaded or not self.raw_text:
            messagebox.showwarning("Нет текста", "Сначала загрузите текст")
            return
        threading.Thread(target=self.run_navigation, daemon=True).start()

    def run_navigation(self):
        self.root.after(0, lambda: self.status_var.set("Навигация (аналитический O(1))..."))
        self.root.after(0, lambda: self.progress.config(value=0))
        try:
            result = self.navigator.navigate(self.raw_text, max_steps=30)
            self.root.after(0, lambda: self.progress.config(value=100))
            if result['status'] == 'ERROR':
                self.root.after(0, lambda: messagebox.showerror("Ошибка", result['message']))
                return

            report = []
            report.append("═══════════════════════════════════════════════════════════════")
            report.append(" АНАЛИТИЧЕСКАЯ НАВИГАЦИЯ (O(1))")
            report.append("═══════════════════════════════════════════════════════════════")
            report.append(f"Всего окон: {result['total_windows']}")
            report.append(f"Позиция пика: {result['position']}")
            report.append(f"Локальный K_eff: {result['keff']:.3f}")
            phase = result['phase']
            report.append(f"Тип фазы: {phase['type']} – {phase['desc']}")
            report.append(f"Путь: {result['path']}")
            report.append("───────────────────────────────────────────────────────────────")
            report.append("📄 ТЕКСТ В ОКРЕСТНОСТИ ПИКА:")
            report.append(result['text'][:500] + ("..." if len(result['text'])>500 else ""))
            report.append("")
            report.append("───────────────────────────────────────────────────────────────")
            report.append("Специально для портала «Философский штурм»")
            report.append("Проект распространяется под лицензией Creative Commons Attribution 4.0 International (CC BY 4.0).")
            report.append("═══════════════════════════════════════════════════════════════")

            self.root.after(0, lambda: self.txt_output.delete(1.0, tk.END))
            self.root.after(0, lambda: self.txt_output.insert(tk.END, "\n".join(report)))
            self.root.after(0, lambda: self.status_var.set("Навигация завершена"))
            self.root.after(0, self.beep_done)

            self.last_report['navigation'] = result
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка навигации", str(e)))

    # ---------- Экспорт JSON ----------
    def export_json(self):
        if not self.last_report:
            messagebox.showwarning("Нет данных", "Сначала выполните анализ")
            return
        try:
            default_name = self.source_base if self.source_base else "report"
            default_name += ".json"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON", "*.json")],
                initialfile=default_name
            )
            if not file_path:
                return
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.last_report, f, ensure_ascii=False, indent=2, default=str)
            messagebox.showinfo("Экспорт", f"Отчёт сохранён в {file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    # ---------- Пояснения (увеличенная высота) ----------
    def show_help(self):
        help_text = (
            "🔹 YUСT v9.13 – количественная философия\n\n"
            "Основные метрики:\n"
        "• K_eff – координационная эффективность (структурированность, логическая плотность)\n"
        "  – высокое (>8): жёсткая архитектура мысли (Кант, Гегель, Спиноза)\n"
        "  – низкое (<4): фрагментарность, афористичность (Ницше, Кьеркегор)\n"
        "• TTR – лексическое разнообразие (Type-Token Ratio)\n"
        "  – высокий (>0.5): богатый словарь, образность (Ницше, Платон)\n"
        "  – низкий (<0.3): терминологическая монотонность (Кант, Гегель)\n"
        "• H_I – связанность текста (энтропия биграмм, максимум 2.0)\n"
        "  – близка к 2.0: максимальная связность, логические цепочки\n"
        "  – низкая: свободные переходы, ассоциативность\n"
        "• Abstract_ratio – доля абстрактной лексики (бытие, сущность, сознание)\n"
        "  – >1%: философский текст; >3%: высокая метафизическая плотность\n"
        "• Readability – индекс читаемости (Флеша-Кинкайда)\n"
        "  – <0: очень сложный текст (Кант, Гегель, Хайдеггер)\n"
        "  – 30–50: умеренная сложность (Ницше, Платон)\n"
        "  – >60: доступный язык (диалоги, публицистика)\n"
        "• Эмоции: агрессия, депрессия, красноречивость, уверенность, валентность\n"
        "  – валентность: от -1 (негатив) до +1 (позитив)\n"
        "  – уверенность: отношение категоричных слов к сомнительным\n"
        "• Вариативность синтаксиса: медиана, асимметрия, эксцесс длин предложений\n"
        "  – высокая асимметрия: неравномерный ритм (Ницше)\n"
        "  – низкий эксцесс: ровный стиль (Кант, Спиноза)\n"
        "• Частоты слов и биграмм – стилометрические маркеры (увеличен вес)\n"
        "  – Лейбниц: «монада», «субстанция», «предустановленная гармония»\n"
        "  – Кант: «чистый», «разум», «следовательно»\n"
        "  – Ницше: «жизнь», «воля», «власть», «но»\n"
        "• НОВОЕ: Вектор аргументации (тип логического движения)\n"
        "  – Дедуктивный – от общих принципов к частным выводам (Спиноза, Декарт)\n"
        "  – Индуктивный – от частных наблюдений к обобщениям (Юм, эмпирики)\n"
        "  – Диалектический – тезис → антитезис → синтез (Гегель, Лейбниц)\n"
        "  – градиент абстракции показывает направление движения мысли\n"
        "• НОВОЕ: Семантическая многозначность\n"
        "  – Индекс изолированности (0–1): высокий (>0.9) – уникальный терминологический мир (Лейбниц, Хайдеггер)\n"
        "  – Категориальная энтропия (0–1): низкая (<0.7) – фокус на одной-двух проблемах\n"
        "• НОВОЕ: Расширенный эмоциональный спектр (когнитивные аффекты)\n"
        "  – Скепсис – частота слов сомнения, критики (Юм, Кант)\n"
        "  – Догматизм – категоричность, уверенность (Спиноза, Декарт)\n"
        "  – Экзистенциальная тревога – страх, отчаяние, смерть (Кьеркегор, Хайдеггер)\n"
        "  – Пафос – возвышенность, риторика (Ницше, Платон)\n"
        "  – доминирующий профиль показывает общий эмоциональный тон\n"
        "• Дополнительные анализаторы:\n"
        "  – Цветовой анализ – плотность, валентность, разнообразие цветообозначений\n"
        "  – Индекс рифмы – для поэтических и афористичных текстов\n"
        "  – Индекс однородности – вариативность стиля по главам (1 – идеально однородно)\n"
        "  – Топологические синонимы – контекстуально близкие слова\n"
        "  – Элоквенс-скор – красноречивость ключевых слов\n"
        "• Сравнение выполняется на двух уровнях:\n"
        "  1. По периодам (24 профиля: 8 философов × 3 периода) – точное соответствие\n"
        "  2. По философам (8 обобщённых профилей) – общая принадлежность к школе\n"
        "• Для каждой главы – локальное сравнение с осцилляциями (при длине >5000 слов)\n"
        "  – осцилляции строят распределения метрик по окнам, улавливая динамику стиля\n\n"
        "Разработано на основе физической теории пространственно-числовой\n"
        "навигации YUCT. https://yuct.org/\n"
        "Проект распространяется под лицензией CC BY 4.0."
        )
        help_window = tk.Toplevel(self.root)
        help_window.title("Пояснения к метрикам")
        help_window.geometry("650x500")
        help_window.configure(bg="#f0f4f8")
        text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=("Arial", 10), bg="white", fg="#2d3748")
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, help_text)

# ------------------------------------------------------------------
# 7. Запуск
# ------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = YUCTApp(root)
    root.mainloop()