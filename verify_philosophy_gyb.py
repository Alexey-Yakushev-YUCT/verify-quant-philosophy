# -*- coding: utf-8 -*-
"""
verify_philosophy_gyb_v8.1_no_scipy.py - Семантический процессор YUCT с анализом по разделам,
философской плотностью, сравнением с эталонными философскими стилями и сводной статистикой
(без зависимости от scipy)
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser
import os
import re
import math
import numpy as np
from collections import Counter, defaultdict
import threading
import time
import winsound
from concurrent.futures import ThreadPoolExecutor
import json

# =============================================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: косинусное расстояние (заменяет scipy.spatial.distance.cosine)
# =============================================================================
def cosine_distance(a, b):
    """
    Вычисляет косинусное расстояние между двумя векторами a и b.
    Возвращает 0 для одинаковых векторов, 1 для противоположных.
    """
    if len(a) != len(b):
        raise ValueError("Векторы должны быть одинаковой длины")
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(x*x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    dot = sum(x*y for x, y in zip(a, b))
    return 1.0 - dot / (norm_a * norm_b)

# =============================================================================
# БЛОК 1: КООРДИНАТНОЕ КОДИРОВАНИЕ (без изменений)
# =============================================================================
class YUCTLinguisticGrid:
    def __init__(self):
        self.BASE_OFFSET = 1000000000
        self.P_MODULUS = 101
        self.char_to_coord = {}
        self.char_to_coord[' '] = self.BASE_OFFSET + 0
        ru_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        for idx, char in enumerate(ru_alphabet, start=1):
            self.char_to_coord[char] = self.BASE_OFFSET + idx
        en_alphabet = "abcdefghijklmnopqrstuvwxyz"
        for idx, char in enumerate(en_alphabet, start=34):
            self.char_to_coord[char] = self.BASE_OFFSET + idx
        digits = "0123456789"
        for idx, char in enumerate(digits, start=61):
            self.char_to_coord[char] = self.BASE_OFFSET + idx

    def text_to_coordinate_stream(self, text: str) -> list:
        stream = []
        clean_text = ""
        for char in text.lower():
            if char in self.char_to_coord:
                clean_text += char
            elif char in ".,!?\"'()[]{}<>:-;\n\r\t":
                clean_text += " "
        clean_text = re.sub(r'\s+', ' ', clean_text)
        for char in clean_text:
            stream.append(self.char_to_coord[char])
        return stream

    def extract_ngram_invariants(self, coord_stream: list, n: int = 3) -> list:
        invariants = []
        if len(coord_stream) < n:
            return invariants
        for i in range(len(coord_stream) - n + 1):
            window = coord_stream[i:i+n]
            hash_invariant = 0
            for idx, coord_val in enumerate(window):
                power = n - 1 - idx
                hash_invariant += coord_val * (self.P_MODULUS ** power)
            invariants.append(hash_invariant)
        return invariants

# =============================================================================
# БЛОК 2: СЕМАНТИЧЕСКИЙ ФИЛЬТР
# =============================================================================
class YUCTSemanticFilter:
    def __init__(self, grid_core):
        self.grid = grid_core
        self.KC = 1 / 3
        self.BETA = 2 / 3

    def analyze_text_words(self, raw_text: str) -> dict:
        clean_stream = self.grid.text_to_coordinate_stream(raw_text)
        words_coords = []
        current_word = []
        for coord in clean_stream:
            if coord == 1000000000:
                if current_word:
                    words_coords.append(current_word)
                    current_word = []
            else:
                current_word.append(coord)
        if current_word:
            words_coords.append(current_word)
        if not words_coords:
            return {}

        all_trigrams = self.grid.extract_ngram_invariants(clean_stream, n=3)
        trigram_frequencies = Counter(all_trigrams)
        total_trigrams = len(all_trigrams)

        sorted_trigrams = sorted(trigram_frequencies.items(), key=lambda x: x[1], reverse=True)
        trigram_yuct_weights = {}
        for rank, (tg_inv, freq) in enumerate(sorted_trigrams, start=1):
            p_i = freq / total_trigrams if total_trigrams > 0 else 0
            h_i = -p_i * math.log2(p_i) if p_i > 0 else 0
            if rank <= 5:
                rank_penalty = 0.01
            else:
                rank_penalty = self.KC * (rank ** (-self.BETA))
            trigram_yuct_weights[tg_inv] = h_i * rank_penalty

        word_registry = {}
        for word_coord in words_coords:
            l_word = len(word_coord)
            if l_word < 3:
                continue
            word_str = ""
            for c in word_coord:
                for ch, val in self.grid.char_to_coord.items():
                    if val == c:
                        word_str += ch
                        break
            word_trigrams = self.grid.extract_ngram_invariants(word_coord, n=3)
            if not word_trigrams:
                continue
            local_weights_sum = sum(trigram_yuct_weights.get(tg, 0) for tg in word_trigrams)
            w_link = local_weights_sum / l_word

            if word_str not in word_registry:
                word_registry[word_str] = {
                    "coords": word_coord,
                    "length": l_word,
                    "w_link": w_link,
                    "count": 1
                }
            else:
                word_registry[word_str]["count"] += 1

        for word_str, data in word_registry.items():
            freq_factor = math.log2(data["count"] + 1) if data["count"] < 50 else 1.0 / (data["count"] / 10)
            data["eloquence_score"] = data["w_link"] * freq_factor

        return word_registry

# =============================================================================
# БЛОК 3: КОНТЕКСТНАЯ ТОПОЛОГИЯ
# =============================================================================
class YUCTContextTopology:
    def __init__(self, grid_core, semantic_filter):
        self.grid = grid_core
        self.filter = semantic_filter
        self.GRAVITY_RADIUS = 4

    def build_context_profiles(self, raw_text: str, word_registry: dict) -> dict:
        words_raw = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]+\b', raw_text.lower())
        valid_words_sequence = [w for w in words_raw if w in word_registry]
        context_profiles = defaultdict(lambda: defaultdict(int))
        for i, center_word in enumerate(valid_words_sequence):
            start = max(0, i - self.GRAVITY_RADIUS)
            end = min(len(valid_words_sequence), i + self.GRAVITY_RADIUS + 1)
            for j in range(start, end):
                if i == j:
                    continue
                neighbor = valid_words_sequence[j]
                context_profiles[center_word][neighbor] += 1
        normalized_profiles = {}
        for word, neighbors in context_profiles.items():
            total = sum(neighbors.values())
            if total > 0:
                normalized_profiles[word] = {n: count / total for n, count in neighbors.items()}
        return normalized_profiles

    def find_topological_synonyms(self, normalized_profiles: dict, threshold: float = 0.4) -> list:
        synonym_pairs = []
        words = list(normalized_profiles.keys())
        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                w1, w2 = words[i], words[j]
                profile1, profile2 = normalized_profiles[w1], normalized_profiles[w2]
                all_neighbors = set(profile1.keys()).union(set(profile2.keys()))
                total_distance = 0.0
                for neighbor in all_neighbors:
                    p1 = profile1.get(neighbor, 0.0)
                    p2 = profile2.get(neighbor, 0.0)
                    total_distance += abs(p1 - p2)
                similarity = 1.0 - (total_distance / 2.0)
                if similarity >= threshold:
                    synonym_pairs.append({
                        "word1": w1,
                        "word2": w2,
                        "similarity": round(similarity, 4)
                    })
        return sorted(synonym_pairs, key=lambda x: x["similarity"], reverse=True)

# =============================================================================
# БЛОК 4: ФАЗОВЫЙ ДЕТЕКТОР + РАСШИРЕННЫЙ АНАЛИЗ (v8.1)
# =============================================================================
class YUCTPhaseDetector:
    def __init__(self):
        self.KC = 1 / 3
        self.BETA_THEORETICAL = 2 / 3

    def calculate_phase_metrics(self, word_registry: dict, normalized_profiles: dict) -> dict:
        if not word_registry or not normalized_profiles:
            return {"K_eff": 1.0, "Phase": "Хаос / Неструктурированный шум", "Confidence": 0.0,
                    "Genre_Verdict": "Неопределённо", "Beta_Empirical": 0.0,
                    "Avg_Word_Length": 0.0, "Lattice_Connectivity": 0.0}

        word_lengths = [data["length"] for data in word_registry.values()]
        avg_length = np.mean(word_lengths) if word_lengths else 0
        length_variance = np.var(word_lengths) if word_lengths else 0

        frequencies = sorted([data["count"] for data in word_registry.values()], reverse=True)
        total_words_count = sum(frequencies)

        if len(frequencies) > 5:
            log_ranks = np.log(np.arange(1, len(frequencies) + 1))
            log_freqs = np.log(frequencies)
            slope, _ = np.polyfit(log_ranks, log_freqs, 1)
            beta_empirical = abs(slope)
        else:
            beta_empirical = 1.0

        profile_densities = [len(profile) for profile in normalized_profiles.values()]
        avg_connectivity = np.mean(profile_densities) if profile_densities else 0

        deviation_from_ideal_beta = abs(beta_empirical - self.BETA_THEORETICAL)
        k_eff = (avg_length * avg_connectivity) / (1.0 + deviation_from_ideal_beta * 10)
        k_eff = max(0.5, min(25.0, k_eff / 2.0))

        if k_eff < 2.0:
            phase = "L1-L2. Деконструкция / Анекдот (Взрывная энтропия, короткие циклы)"
            genre_verdict = "Разговорный стиль / Анекдот / Экспрессивный шум"
        elif 2.0 <= k_eff < 5.0:
            phase = "L3-L4. Релятивизм / Эклектика (Подвижная решетка)"
            genre_verdict = "Публицистика / Живой диалог / Эссе"
        elif 5.0 <= k_eff < 10.0:
            phase = "L5-L6. Эмпирика / Академическая метафизика (Стабильные узлы)"
            genre_verdict = "Художественная проза / Научпоп / Повествование"
        elif 10.0 <= k_eff < 18.0:
            phase = "L7-L8. Критика / Структурный Синтез (Высокая жесткость)"
            genre_verdict = "Поэма / Высокий стиль / Философский трактат"
        else:
            phase = "L9-L10. Аксиоматическая координация / Монолитный смысловой центр"
            genre_verdict = "Художественный или философский текст с предельной смысловой концентрацией"

        return {
            "K_eff": round(k_eff, 2),
            "Phase": phase,
            "Genre_Verdict": genre_verdict,
            "Beta_Empirical": round(beta_empirical, 4),
            "Avg_Word_Length": round(avg_length, 2),
            "Lattice_Connectivity": round(avg_connectivity, 2)
        }

    @staticmethod
    def get_recommendations(metrics: dict) -> str:
        rec = []
        k_eff = metrics["K_eff"]
        beta = metrics["Beta_Empirical"]
        avg_len = metrics["Avg_Word_Length"]
        connectivity = metrics["Lattice_Connectivity"]

        if k_eff < 3.0:
            rec.append("▪️ Текст имеет низкую координационную эффективность. Попробуйте выделить 1–3 главных тезиса и последовательно их раскрывать.")
        elif k_eff < 7.0:
            rec.append("▪️ Умеренная координация. Усильте логические переходы между частями, избегайте необоснованных отступлений.")
        elif k_eff < 12.0:
            rec.append("▪️ Хорошая координация. Для усиления эффекта можно ещё больше сжать аксиоматическую базу – сведите ключевые идеи к минимуму.")
        else:
            rec.append("▪️ Текст обладает высокой координационной эффективностью. Это говорит о монолитности смысловой структуры.")

        if beta > 0.7:
            rec.append("▪️ Распределение слов смещено в сторону частых повторов (высокий показатель Ципфа). Разнообразьте лексику, чтобы избежать монотонности.")
        elif beta < 0.5:
            rec.append("▪️ Распределение слов необычно равномерное (низкий показатель Ципфа). Это может быть признаком искусственной конструкции – добавьте естественных смысловых акцентов.")

        if avg_len < 4.0:
            rec.append("▪️ Средняя длина слова мала. Возможно, текст излишне упрощён; попробуйте использовать более точную терминологию.")
        elif avg_len > 8.0:
            rec.append("▪️ Средняя длина слова велика. Текст может быть перегружен сложными терминами; проверьте, не теряется ли доступность.")

        if connectivity < 5.0:
            rec.append("▪️ Низкая плотность контекстных связей. Укрепите взаимосвязи между понятиями – чаще возвращайтесь к ключевым терминам.")
        elif connectivity > 15.0:
            rec.append("▪️ Очень высокая плотность связей – текст может быть излишне «зациклен» на одних и тех же понятиях. Попробуйте ввести новые смысловые оттенки.")

        if not rec:
            rec.append("✅ Структура текста близка к оптимальной. Сохраняйте этот баланс.")
        return "\n".join(rec)

class YUCTExtendedAnalyzer:
    def __init__(self):
        self.color_dict = self._build_color_dict()
        self.philosophical_terms = self._build_philosophical_terms()

    def _build_color_dict(self):
        colors = {
            'красный': ('warm', 0.8), 'алый': ('warm', 0.9), 'багровый': ('warm', 0.6),
            'оранжевый': ('warm', 0.7), 'жёлтый': ('warm', 0.6), 'золотой': ('warm', 0.8),
            'розовый': ('warm', 0.5), 'персиковый': ('warm', 0.6),
            'синий': ('cool', -0.3), 'голубой': ('cool', -0.1), 'лазурный': ('cool', 0.0),
            'фиолетовый': ('cool', -0.2), 'лиловый': ('cool', -0.1),
            'зелёный': ('cool', 0.0), 'изумрудный': ('cool', 0.3), 'салатовый': ('cool', 0.4),
            'белый': ('neutral', 0.0), 'серый': ('neutral', -0.2), 'чёрный': ('neutral', -0.4),
            'коричневый': ('neutral', -0.1), 'бежевый': ('neutral', 0.0),
            'бордовый': ('warm', 0.4), 'вишнёвый': ('warm', 0.5), 'малиновый': ('warm', 0.7),
            'бирюзовый': ('cool', 0.1), 'сиреневый': ('cool', 0.0),
        }
        return colors

    def _build_philosophical_terms(self):
        abstract = [
            'бытие', 'сущность', 'существование', 'сознание', 'познание', 'истина',
            'онтология', 'гносеология', 'диалектика', 'субъект', 'объект',
            'трансцендентное', 'имманентное', 'абсолют', 'идея', 'материя', 'дух',
            'разум', 'воля', 'свобода', 'необходимость', 'причинность', 'время',
            'пространство', 'закон', 'принцип', 'система', 'структура', 'метод',
            'критерий', 'рефлексия', 'интуиция', 'опыт', 'трансцендентальный',
            'феномен', 'ноумен', 'априорный', 'апостериорный', 'синтез', 'анализ',
            'суждение', 'умозаключение', 'логика', 'метафизика', 'этика', 'эстетика'
        ]
        logical = [
            'следовательно', 'поэтому', 'таким образом', 'значит', 'итак',
            'вытекает', 'следует', 'поскольку', 'постольку', 'вследствие',
            'в силу', 'с одной стороны', 'с другой стороны', 'во-первых', 'во-вторых',
            'в-третьих', 'отсюда', 'из этого следует'
        ]
        impersonal = [
            'можно сказать', 'следует отметить', 'необходимо подчеркнуть',
            'очевидно', 'представляется', 'не вызывает сомнений',
            'требует рассмотрения', 'заслуживает внимания', 'важно отметить',
            'стоит рассмотреть', 'целесообразно выделить', 'обратим внимание',
            'следует признать', 'нельзя не заметить', 'несомненно'
        ]
        return {'abstract': abstract, 'logical': logical, 'impersonal': impersonal}

    def compute_philosophical_density(self, text: str) -> float:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]+\b', text.lower())
        if not words:
            return 0.0
        total = len(words)
        word_set = set(words)
        unique_abstract = sum(1 for w in word_set if w in self.philosophical_terms['abstract'])
        unique_logical = sum(1 for w in word_set if w in self.philosophical_terms['logical'])
        text_lower = text.lower()
        phrase_count = sum(text_lower.count(phrase) for phrase in self.philosophical_terms['impersonal'])
        if not word_set:
            return 0.0
        phi = (unique_abstract + unique_logical) / len(word_set)
        phrase_bonus = min(1.0, phrase_count / (total * 0.01)) * 0.1
        phi += phrase_bonus
        return min(phi, 1.0)

    def analyze_punctuation(self, text: str) -> dict:
        exclam_count = text.count('!')
        quest_count = text.count('?')
        ellipsis_count = text.count('...')
        combos = {
            '!?': text.count('!?'),
            '?!': text.count('?!'),
            '...!': text.count('...!'),
            '...?': text.count('...?'),
            '!!': text.count('!!'),
            '??': text.count('??'),
        }
        weights = {
            '!': 1.0,
            '?': 0.8,
            '...': 0.5,
            '!?': 2.0,
            '?!': 2.0,
            '...!': 1.5,
            '...?': 1.2,
            '!!': 2.5,
            '??': 1.8,
        }
        total_weight = 0.0
        for symbol, cnt in combos.items():
            if symbol in weights:
                total_weight += cnt * weights[symbol]
        total_weight += exclam_count * weights['!']
        total_weight += quest_count * weights['?']
        total_weight += ellipsis_count * weights['...']
        length = max(1, len(text))
        expr_per_1000 = total_weight / (length / 1000.0)
        return {
            'exclam': exclam_count,
            'quest': quest_count,
            'ellipsis': ellipsis_count,
            'combos': combos,
            'total_weight': total_weight,
            'expr_per_1000': round(expr_per_1000, 2),
        }

    def analyze_sentence_length(self, text: str) -> dict:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
        if not sentences:
            return {'avg': 0, 'std': 0, 'short_ratio': 0, 'long_ratio': 0, 'count': 0}
        lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
        avg = np.mean(lengths)
        std = np.std(lengths) if len(lengths) > 1 else 0
        short = sum(1 for l in lengths if l < 5) / len(lengths)
        long = sum(1 for l in lengths if l > 25) / len(lengths)
        return {
            'avg': round(avg, 1),
            'std': round(std, 1),
            'short_ratio': round(short * 100, 1),
            'long_ratio': round(long * 100, 1),
            'count': len(lengths)
        }

    def detect_rhyme(self, text: str) -> dict:
        lines = text.split('\n')
        line_endings = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            words = re.findall(r'\b\w+\b', line)
            if words:
                last_word = words[-1].lower()
                if len(last_word) >= 3:
                    ending = last_word[-3:]
                else:
                    ending = last_word
                line_endings.append(ending)
        if len(line_endings) < 2:
            return {'rhyme_score': 0, 'pairs': 0, 'unique_endings': len(set(line_endings)), 'total_lines': len(line_endings)}
        endings_count = Counter(line_endings)
        pairs = 0
        for cnt in endings_count.values():
            if cnt >= 2:
                pairs += cnt * (cnt - 1) // 2
        total_possible = len(line_endings) * (len(line_endings) - 1) // 2
        rhyme_score = pairs / total_possible if total_possible > 0 else 0
        return {
            'rhyme_score': round(rhyme_score, 3),
            'pairs': pairs,
            'unique_endings': len(endings_count),
            'total_lines': len(line_endings)
        }

    def analyze_colors(self, text: str) -> dict:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]+\b', text.lower())
        color_mentions = []
        for word in words:
            if word in self.color_dict:
                color_mentions.append((word, self.color_dict[word]))
        total_words = len(words)
        if total_words == 0:
            return {
                'color_density': 0,
                'color_valence': 0,
                'color_diversity': 0,
                'warm_count': 0,
                'cool_count': 0,
                'neutral_count': 0
            }
        warm = sum(1 for _, (grp, _) in color_mentions if grp == 'warm')
        cool = sum(1 for _, (grp, _) in color_mentions if grp == 'cool')
        neutral = sum(1 for _, (grp, _) in color_mentions if grp == 'neutral')
        valence = sum(val for _, (_, val) in color_mentions) / len(color_mentions) if color_mentions else 0
        unique_colors = len(set(word for word, _ in color_mentions))
        diversity = unique_colors / len(color_mentions) if color_mentions else 0
        return {
            'color_density': round(len(color_mentions) / total_words, 4),
            'color_valence': round(valence, 3),
            'color_diversity': round(diversity, 3),
            'warm_count': warm,
            'cool_count': cool,
            'neutral_count': neutral
        }

    def classify_genre(self, punctuation: dict, sent_len: dict, rhyme: dict, k_eff: float, phi: float = 0.0) -> dict:
        expr = punctuation['expr_per_1000']
        avg_len = sent_len['avg']
        short_ratio = sent_len['short_ratio']
        long_ratio = sent_len['long_ratio']
        rhyme_score = rhyme['rhyme_score']

        # Научный
        sci_score = 0.0
        if expr < 0.5 and avg_len > 18 and long_ratio > 20:
            sci_score = 1.0
        elif expr < 1.0 and avg_len > 15:
            sci_score = 0.7
        else:
            sci_score = max(0, 1.0 - expr / 3.0) * (avg_len / 25.0 if avg_len > 0 else 0)

        # Художественная проза
        prose_score = 0.0
        if 0.5 < expr < 3.0 and 8 < avg_len < 20 and rhyme_score < 0.2:
            prose_score = 1.0
        elif expr > 0.3 and avg_len > 5:
            prose_score = 0.7
        else:
            prose_score = min(1, expr / 2.0) * (1 - abs(avg_len - 14) / 14)

        # Поэзия
        poetry_score = 0.0
        if rhyme_score > 0.3 and avg_len < 10 and expr > 1.0:
            poetry_score = 1.0
        elif rhyme_score > 0.2 and avg_len < 12:
            poetry_score = 0.8
        else:
            poetry_score = rhyme_score * 2.0 * (1 / (avg_len + 1)) * min(1, expr / 1.5)

        # Публицистика
        pub_score = 0.0
        if 1.0 < expr < 4.0 and 10 < avg_len < 22 and rhyme_score < 0.15:
            pub_score = 1.0
        elif expr > 0.5 and avg_len > 10:
            pub_score = 0.6
        else:
            pub_score = min(1, expr / 2.5) * (avg_len / 18.0 if avg_len > 0 else 0)

        # Философский
        phi_score = 0.0
        if phi > 0.15 and expr < 1.5 and avg_len > 20 and rhyme_score < 0.1:
            phi_score = 1.0
        elif phi > 0.1 and avg_len > 15:
            phi_score = 0.7
        else:
            phi_score = phi * 2.0 * (avg_len / 20.0 if avg_len > 0 else 0) * (1 - expr / 5.0)

        total = sci_score + prose_score + poetry_score + pub_score + phi_score
        if total == 0:
            return {'scientific': 0, 'prose': 0, 'poetry': 0, 'publicistic': 0, 'philosophical': 0, 'dominant': 'unknown'}
        probs = {
            'scientific': round(sci_score / total, 2),
            'prose': round(prose_score / total, 2),
            'poetry': round(poetry_score / total, 2),
            'publicistic': round(pub_score / total, 2),
            'philosophical': round(phi_score / total, 2)
        }
        probs['dominant'] = max(probs, key=probs.get)
        return probs

    def get_style_recommendations(self, genre_probs: dict, punctuation: dict, sent_len: dict, rhyme: dict, k_eff: float, phi: float) -> str:
        rec = []
        dominant = genre_probs['dominant']
        if punctuation['expr_per_1000'] > 3.0 and dominant != 'poetry':
            rec.append("▪️ Высокая экспрессивность (восклицания/вопросы). В научных текстах это может быть избыточно; в художественных – допустимо, но проверьте, не перегружает ли это смысл.")
        if punctuation['expr_per_1000'] < 0.5 and dominant in ['prose', 'poetry']:
            rec.append("▪️ Низкая экспрессивность. Для художественного текста полезно добавить эмоциональные акценты (вопросы, восклицания), чтобы усилить воздействие.")

        if sent_len['avg'] > 25 and dominant != 'scientific':
            rec.append("▪️ Очень длинные предложения. Для художественного текста разбейте их на более короткие для улучшения читаемости.")
        elif sent_len['avg'] < 8 and dominant == 'scientific':
            rec.append("▪️ Предложения короткие для научного стиля. Возможно, текст излишне упрощён; попробуйте развить мысль более развёрнуто.")

        if rhyme['rhyme_score'] > 0.2 and dominant != 'poetry':
            rec.append("▪️ Обнаружены повторяющиеся окончания (рифма). В прозе это может быть стилистическим приёмом, но если не задумано, стоит проверить, не монотонен ли ритм.")
        elif rhyme['rhyme_score'] < 0.1 and dominant == 'poetry':
            rec.append("▪️ Низкая рифма в стихотворном тексте. Попробуйте усилить рифмовку в ключевых местах.")

        if dominant == 'scientific':
            if k_eff < 5.0:
                rec.append("▪️ У научного текста низкая координационная эффективность. Усильте связь между тезисами и аргументами, избегайте отступлений.")
            else:
                rec.append("▪️ Хорошая координационная структура. Научный текст логичен. Проверьте только эмоциональный фон – он не должен перевешивать содержание.")
        elif dominant == 'prose':
            if k_eff > 15.0:
                rec.append("▪️ Высокая смысловая концентрация. Хорошо для философской прозы, но следите, чтобы не потерялась художественность.")
            else:
                rec.append("▪️ Проза гармонична. Можно поиграть с ритмом, варьируя длину предложений.")
        elif dominant == 'poetry':
            rec.append("▪️ Стихотворный текст. Оцените рифму и ритм; если они слишком регулярны, добавьте разнообразия.")
        elif dominant == 'publicistic':
            rec.append("▪️ Публицистический стиль. Хорошо сочетает экспрессию и логику. Следите, чтобы аргументы не тонули в эмоциях.")
        elif dominant == 'philosophical':
            if phi < 0.1:
                rec.append("▪️ Текст претендует на философский, но философская плотность низка. Введите больше абстрактных понятий и логических связок.")
            else:
                rec.append("▪️ Философский текст. Сохраняйте баланс между глубиной и доступностью. Избегайте излишней экспрессии.")

        if not rec:
            rec.append("✅ Текст сбалансирован по всем параметрам.")
        return "\n".join(rec)


# =============================================================================
# НОВЫЙ МОДУЛЬ: СРАВНЕНИЕ С ЭТАЛОННЫМИ ФИЛОСОФСКИМИ СТИЛЯМИ (v8.1)
# =============================================================================
class PhilosophicalStyleComparator:
    def __init__(self):
        # Эталонные профили философов (на основе обобщённых данных)
        # Ключи: K_eff, TTR, sent_avg, sent_std, expr, PHI
        self.profiles = {
            'Платон':      {'K_eff': 19,  'TTR': 0.55, 'sent_avg': 18, 'sent_std': 8,  'expr': 1.5, 'PHI': 0.18},
            'Аристотель':  {'K_eff': 16,  'TTR': 0.50, 'sent_avg': 22, 'sent_std': 10, 'expr': 0.8, 'PHI': 0.22},
            'Кант':        {'K_eff': 12,  'TTR': 0.45, 'sent_avg': 30, 'sent_std': 12, 'expr': 0.5, 'PHI': 0.35},
            'Гегель':      {'K_eff': 18,  'TTR': 0.48, 'sent_avg': 28, 'sent_std': 14, 'expr': 0.6, 'PHI': 0.40},
            'Ницше':       {'K_eff': 8,   'TTR': 0.52, 'sent_avg': 12, 'sent_std': 8,  'expr': 3.5, 'PHI': 0.12},
            'Витгенштейн': {'K_eff': 7,   'TTR': 0.38, 'sent_avg': 14, 'sent_std': 6,  'expr': 0.4, 'PHI': 0.08},
            'Хайдеггер':   {'K_eff': 9,   'TTR': 0.42, 'sent_avg': 25, 'sent_std': 10, 'expr': 0.7, 'PHI': 0.28},
            'Юм':          {'K_eff': 13,  'TTR': 0.48, 'sent_avg': 20, 'sent_std': 9,  'expr': 0.9, 'PHI': 0.15},
            'Декарт':      {'K_eff': 12,  'TTR': 0.44, 'sent_avg': 24, 'sent_std': 11, 'expr': 0.6, 'PHI': 0.20},
            'Спиноза':     {'K_eff': 20,  'TTR': 0.40, 'sent_avg': 26, 'sent_std': 13, 'expr': 0.3, 'PHI': 0.45},
            'Кьеркегор':   {'K_eff': 7,   'TTR': 0.50, 'sent_avg': 15, 'sent_std': 7,  'expr': 2.5, 'PHI': 0.14},
            'Шопенгауэр':  {'K_eff': 11,  'TTR': 0.46, 'sent_avg': 22, 'sent_std': 10, 'expr': 1.2, 'PHI': 0.30},
        }
        self.metric_keys = ['K_eff', 'TTR', 'sent_avg', 'sent_std', 'expr', 'PHI']

    def compare(self, metrics: dict) -> dict:
        """
        Принимает словарь метрик текста (с теми же ключами).
        Возвращает словарь с процентами сходства, доминирующим стилем и индексом смешанности.
        """
        # Проверяем наличие всех ключей
        for key in self.metric_keys:
            if key not in metrics:
                metrics[key] = 0.0

        # Нормализация: вычисляем среднее и std по эталонам для каждой метрики
        means = {}
        stds = {}
        for key in self.metric_keys:
            vals = [p[key] for p in self.profiles.values()]
            means[key] = np.mean(vals)
            stds[key] = np.std(vals) if np.std(vals) > 0 else 1.0

        # Вектор текста (z-оценки)
        text_vec = [(metrics[key] - means[key]) / stds[key] for key in self.metric_keys]

        # Векторы эталонов
        profiles_vec = {}
        for name, profile in self.profiles.items():
            profiles_vec[name] = [(profile[key] - means[key]) / stds[key] for key in self.metric_keys]

        # Косинусное расстояние и сходство (используем ручную функцию)
        similarities = {}
        for name, vec in profiles_vec.items():
            dist = cosine_distance(text_vec, vec)  # 0 = идентичны, 1 = противоположны
            sim = max(0, 1 - dist)                # преобразуем в сходство
            similarities[name] = round(sim * 100, 1)

        # Нормализуем проценты, чтобы сумма была 100
        total = sum(similarities.values())
        if total > 0:
            for name in similarities:
                similarities[name] = round(similarities[name] / total * 100, 1)

        # Индекс смешанности: 1 - (максимальный процент / 100)
        max_sim = max(similarities.values())
        mixing_index = round(1 - max_sim / 100, 2)

        dominant = max(similarities, key=similarities.get)
        return {
            'similarities': similarities,
            'dominant': dominant,
            'mixing_index': mixing_index
        }


# =============================================================================
# БЛОК 5: СЕМАНТИЧЕСКАЯ НАВИГАЦИЯ (без изменений)
# =============================================================================
class YUCTSemanticNavigator:
    def __init__(self, grid, filter_obj, topology, detector, analyzer, ai_detector):
        self.grid = grid
        self.filter = filter_obj
        self.topology = topology
        self.detector = detector
        self.analyzer = analyzer
        self.ai_detector = ai_detector
        self.Q = (3/2) ** (1/3)
        self.PERIOD = 16.5
        self.OFFSET = 80.0
        self.BETA = 2/3
        self.KC = 1/3
        self.stop_flag = False

        self.phase_descriptions = {
            "FIRST_ORDER": "Первый порядок: смена полярности смысла. Текст меняет базовую логику (например, от утверждения к отрицанию).",
            "SECOND_ORDER": "Второй порядок: зона максимальной амплитуды – смысловая пустыня или переломный момент, где связи ослабевают.",
            "TRANSITION_ZONE": "Переходная зона: реструктуризация поля, разрыв прежних связей и формирование новых.",
            "STABLE_SOURCE": "Стабильный узел (Source): текст устойчив, смысл исходит из одного центра.",
            "STABLE_SINK": "Стабильный узел (Sink): текст устойчив, смысл стягивается к одному центру.",
            "UNKNOWN": "Неопределённая зона – требуется дополнительный анализ."
        }

    def compute_coord_depth(self, position: int) -> float:
        if position < 1:
            position = 1
        return math.log(position) / math.log(self.Q)

    def compute_phase(self, n_f: float) -> float:
        return (math.pi / self.PERIOD) * (n_f - self.OFFSET)

    def detect_phase_transition(self, n_f: float) -> dict:
        mod = n_f % self.PERIOD
        theta = self.compute_phase(n_f)
        abs_sin = abs(math.sin(theta))
        if abs_sin < 0.1:
            return {"type": "FIRST_ORDER", "desc": "Первый порядок (смена полярности)", "bidirectional": True, "amplitude": 1.0}
        elif abs_sin > 0.9 and 7.0 <= mod <= 9.5:
            return {"type": "SECOND_ORDER", "desc": "Второй порядок (смысловая пустыня)", "bidirectional": True, "amplitude": 2.0}
        elif 7.0 <= mod <= 9.0:
            return {"type": "TRANSITION_ZONE", "desc": "Переходная зона (реструктуризация)", "bidirectional": True, "amplitude": 1.5}
        elif 0.0 <= mod <= 7.0:
            return {"type": "STABLE_SOURCE", "desc": "Стабильный узел (Source)", "bidirectional": False, "amplitude": 0.8}
        elif 9.0 <= mod <= 16.5:
            return {"type": "STABLE_SINK", "desc": "Стабильный узел (Sink)", "bidirectional": False, "amplitude": 0.8}
        return {"type": "UNKNOWN", "desc": "Неопределённая зона", "bidirectional": False, "amplitude": 0.5}

    def compute_local_keff(self, text_window: str, global_metrics: dict = None, position: int = 0, total_windows: int = 1) -> float:
        if len(text_window.strip()) < 10:
            return 0.0
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]{3,}\b', text_window.lower())
        if len(words) < 3:
            return 0.0
        counts = Counter(words)
        total = len(words)
        h_d = 0.0
        for cnt in counts.values():
            p = cnt / total
            h_d -= p * math.log2(p)
        unique_ratio = len(counts) / total
        h_i = max(0.1, min(2.0, h_d * unique_ratio * 1.5))
        if h_i == 0:
            return 0.0
        k_eff = h_d / h_i
        if global_metrics:
            local_duplication = 1.0 - unique_ratio
            global_duplication = global_metrics.get('duplication', 0.5)
            if local_duplication > global_duplication * 1.2:
                k_eff *= 1.2
            elif local_duplication < global_duplication * 0.8:
                k_eff *= 0.8
            avg_sent_len = global_metrics.get('avg_sent_len', 20)
            if total > avg_sent_len * 1.5:
                k_eff *= 1.1
            elif total < avg_sent_len * 0.7:
                k_eff *= 0.9
            center_factor = 1.0 - abs(position / total_windows - 0.5) * 0.4
            k_eff *= center_factor
        return k_eff

    def search_half(self, sentences, start, end, global_metrics, progress_callback=None, half_index=0):
        best_keff = 0.0
        best_pos = start
        best_window_text = ""
        phase_info = None
        total_windows = len(sentences)
        window_sizes = [1, 2, 3, 5, 7]
        step = 2 if total_windows > 2000 else 1
        positions = list(range(start, end, step))
        total_positions = len(positions)

        for idx, pos in enumerate(positions):
            if self.stop_flag:
                break
            best_local_keff = 0.0
            best_local_text = ""
            for wsize in window_sizes:
                left = max(0, pos - wsize)
                right = min(total_windows, pos + wsize + 1)
                window_text = " ".join(sentences[left:right])
                word_count = len(re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]{3,}\b', window_text))
                if word_count < 3:
                    continue
                local_keff = self.compute_local_keff(window_text, global_metrics, pos, total_windows)
                if word_count < 5:
                    local_keff *= 0.7
                elif word_count > 50:
                    local_keff *= 0.9
                if local_keff > best_local_keff:
                    best_local_keff = local_keff
                    best_local_text = window_text
            if best_local_keff > best_keff:
                best_keff = best_local_keff
                best_pos = pos
                best_window_text = best_local_text
                n_f = self.compute_coord_depth(pos + 1)
                phase_info = self.detect_phase_transition(n_f)
            if progress_callback and idx % 20 == 0:
                progress_callback(int((idx + 1) / total_positions * 100))
        return {
            "position": best_pos,
            "keff": best_keff,
            "text": best_window_text,
            "phase": phase_info
        }

    def navigate(self, text: str, global_metrics: dict = None, progress_callback=None) -> dict:
        self.stop_flag = False
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            return {"status": "ERROR", "message": "Текст слишком короткий или неразборчивый"}
        total_windows = len(sentences)
        middle = total_windows // 2
        overlap = max(5, int(total_windows * 0.05))
        half1_end = min(total_windows, middle + overlap)
        half2_start = max(0, middle - overlap)
        progress1 = None
        progress2 = None
        if progress_callback:
            progress1 = lambda p: progress_callback(int(p * 0.5), "Поток 1")
            progress2 = lambda p: progress_callback(50 + int(p * 0.5), "Поток 2")
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(self.search_half, sentences, 0, half1_end, global_metrics, progress1, 1)
            future2 = executor.submit(self.search_half, sentences, half2_start, total_windows, global_metrics, progress2, 2)
            result1 = future1.result()
            result2 = future2.result()
        if self.stop_flag:
            return {"status": "CANCELLED", "message": "Расчёт прерван пользователем"}
        if result1['keff'] >= result2['keff']:
            best = result1
        else:
            best = result2
        if best['keff'] == 0.0:
            best['keff'] = 0.5
            best['text'] = "Не найден"
        return {
            "status": "FOUND" if best['keff'] > 2.0 else "PARTIAL",
            "position": best['position'],
            "keff": best['keff'],
            "text": best['text'],
            "phase": best['phase'] if best['phase'] else {"type": "UNKNOWN", "desc": "Не определена"},
            "total_windows": total_windows
        }

    def stop(self):
        self.stop_flag = True


# =============================================================================
# БЛОК 6: МОДУЛЬ АНАЛИЗА ПО РАЗДЕЛАМ (без изменений)
# =============================================================================
class YUCTSectionAnalyzer:
    def __init__(self, analyzer, ai_detector):
        self.analyzer = analyzer
        self.ai_detector = ai_detector

    def split_text(self, text: str, mode: str = 'paragraphs', n: int = 10) -> list:
        if mode == 'paragraphs':
            sections = re.split(r'\n\s*\n', text)
            sections = [s.strip() for s in sections if s.strip()]
            if len(sections) < 2:
                sections = [s.strip() for s in text.split('\n') if s.strip()]
            return sections
        elif mode == 'chapters':
            sections = re.split(r'(?:Глава|CHAPTER|Chapter)\s+\d+[.:-]?\s*', text)
            sections = [s.strip() for s in sections if s.strip()]
            if len(sections) < 2:
                return [text.strip()]
            return sections
        elif mode == 'fixed':
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            sections = []
            for i in range(0, len(sentences), n):
                section = ' '.join(sentences[i:i+n])
                if section.strip():
                    sections.append(section)
            return sections
        else:
            return [text.strip()]

    def analyze_sections(self, text: str, mode: str = 'paragraphs', n: int = 10) -> dict:
        sections_text = self.split_text(text, mode, n)
        if not sections_text:
            return {'sections': [], 'summary': {}}
        results = []
        for idx, sec in enumerate(sections_text):
            local_keff = self._estimate_local_keff(sec)
            sent_len = self.analyzer.analyze_sentence_length(sec)
            punct = self.analyzer.analyze_punctuation(sec)
            rhyme = self.analyzer.detect_rhyme(sec)
            phi = self.analyzer.compute_philosophical_density(sec)
            ai_result = self.ai_detector.detect(sec, expr_per_1000=punct['expr_per_1000'])
            results.append({
                'index': idx,
                'range': f"{mode} {idx+1}",
                'keff': round(local_keff, 2),
                'sent_avg': sent_len['avg'],
                'expr': punct['expr_per_1000'],
                'ai_prob': ai_result['ai_probability'],
                'phi': round(phi, 3)
            })
        if not results:
            return {'sections': [], 'summary': {}}
        keys = ['keff', 'sent_avg', 'expr', 'ai_prob', 'phi']
        summary = {}
        for key in keys:
            values = [r[key] for r in results]
            summary[f'{key}_avg'] = round(np.mean(values), 2)
            summary[f'{key}_std'] = round(np.std(values), 2) if len(values) > 1 else 0
            summary[f'{key}_min'] = round(min(values), 2)
            summary[f'{key}_max'] = round(max(values), 2)
        if len(results) > 1:
            variances = [np.var([r[key] for r in results]) for key in keys]
            ranges = [summary[f'{key}_max'] - summary[f'{key}_min'] for key in keys]
            norm_var = []
            for var, rng in zip(variances, ranges):
                if rng > 0:
                    norm_var.append(var / (rng ** 2))
                else:
                    norm_var.append(0)
            uniformity = 1 - min(1, sum(norm_var) / len(norm_var))
            summary['uniformity'] = round(uniformity, 3)
        else:
            summary['uniformity'] = 1.0
        return {'sections': results, 'summary': summary}

    def _estimate_local_keff(self, text: str) -> float:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]{3,}\b', text.lower())
        if len(words) < 3:
            return 0.0
        counts = Counter(words)
        total = len(words)
        h_d = 0.0
        for cnt in counts.values():
            p = cnt / total
            h_d -= p * math.log2(p)
        unique_ratio = len(counts) / total
        h_i = max(0.1, min(2.0, h_d * unique_ratio * 1.5))
        if h_i == 0:
            return 0.0
        return h_d / h_i


# =============================================================================
# МОДУЛЬ ДЕТЕКЦИИ ИИ (без изменений)
# =============================================================================
class YUCTAIDetector:
    def __init__(self):
        self.thresholds = {
            'ttr': (0.5, 0.7),
            'sent_std': (2.5, 8.0),
            'top_bigram_ratio': (0.0, 0.15),
            'expr_per_1000': (0.5, 5.0),
            'rare_word_ratio': (0.02, 0.15),
            'avg_word_len': (4.0, 6.5),
        }

    def compute_ttr(self, text: str) -> float:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]+\b', text.lower())
        if not words:
            return 0.0
        return len(set(words)) / len(words)

    def compute_sent_std(self, text: str) -> float:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
        if len(sentences) < 2:
            return 0.0
        lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
        return np.std(lengths)

    def compute_top_bigram_ratio(self, text: str) -> float:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]+\b', text.lower())
        if len(words) < 2:
            return 0.0
        bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        if not bigrams:
            return 0.0
        counter = Counter(bigrams)
        top_freq = counter.most_common(5)
        top_sum = sum(freq for _, freq in top_freq)
        return top_sum / len(bigrams)

    def compute_rare_word_ratio(self, text: str) -> float:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]+\b', text.lower())
        if not words:
            return 0.0
        freq = Counter(words)
        total = len(words)
        rare = sum(1 for w, cnt in freq.items() if cnt < total/10000)
        return rare / len(freq) if freq else 0.0

    def compute_avg_word_len(self, text: str) -> float:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]+\b', text)
        if not words:
            return 0.0
        return sum(len(w) for w in words) / len(words)

    def detect(self, text: str, expr_per_1000: float = None) -> dict:
        ttr = self.compute_ttr(text)
        sent_std = self.compute_sent_std(text)
        top_bigram_ratio = self.compute_top_bigram_ratio(text)
        rare_word_ratio = self.compute_rare_word_ratio(text)
        avg_word_len = self.compute_avg_word_len(text)
        if expr_per_1000 is None:
            expr_per_1000 = text.count('!') + text.count('?') + text.count('...') * 0.5
            expr_per_1000 = expr_per_1000 / (len(text)/1000) if len(text) > 0 else 0

        ttr_score = 0.0
        if ttr < self.thresholds['ttr'][0]:
            ttr_score = 1.0
        elif ttr > self.thresholds['ttr'][1]:
            ttr_score = 0.0
        else:
            ttr_score = (self.thresholds['ttr'][1] - ttr) / (self.thresholds['ttr'][1] - self.thresholds['ttr'][0])

        sent_std_score = 0.0
        if sent_std < 2.0:
            sent_std_score = 1.0
        elif sent_std > self.thresholds['sent_std'][1]:
            sent_std_score = 0.0
        else:
            sent_std_score = (self.thresholds['sent_std'][1] - sent_std) / (self.thresholds['sent_std'][1] - 1.0)

        bigram_score = 0.0
        if top_bigram_ratio > self.thresholds['top_bigram_ratio'][1]:
            bigram_score = 1.0
        elif top_bigram_ratio < 0.01:
            bigram_score = 0.0
        else:
            bigram_score = (top_bigram_ratio - 0.01) / (self.thresholds['top_bigram_ratio'][1] - 0.01)

        expr_score = 0.0
        if expr_per_1000 < 0.3:
            expr_score = 1.0
        elif expr_per_1000 > 3.0:
            expr_score = 0.0
        else:
            expr_score = (3.0 - expr_per_1000) / 2.7

        rare_score = 0.0
        if rare_word_ratio < 0.01:
            rare_score = 1.0
        elif rare_word_ratio > 0.15:
            rare_score = 0.0
        else:
            rare_score = (0.15 - rare_word_ratio) / 0.14

        len_score = 0.0
        if avg_word_len < 4.0:
            len_score = 1.0
        elif avg_word_len > 6.5:
            len_score = 0.0
        else:
            len_score = (6.5 - avg_word_len) / 2.5

        weights = {
            'ttr': 0.25,
            'sent_std': 0.20,
            'top_bigram': 0.20,
            'expr': 0.10,
            'rare': 0.15,
            'avg_len': 0.10
        }
        total_score = (
            ttr_score * weights['ttr'] +
            sent_std_score * weights['sent_std'] +
            bigram_score * weights['top_bigram'] +
            expr_score * weights['expr'] +
            rare_score * weights['rare'] +
            len_score * weights['avg_len']
        )
        total_score = max(0.0, min(1.0, total_score))

        return {
            'ttr': round(ttr, 3),
            'sent_std': round(sent_std, 2),
            'top_bigram_ratio': round(top_bigram_ratio, 4),
            'rare_word_ratio': round(rare_word_ratio, 4),
            'avg_word_len': round(avg_word_len, 2),
            'expr_per_1000': round(expr_per_1000, 2),
            'ai_probability': round(total_score, 2),
            'ai_label': 'Вероятно ИИ' if total_score > 0.6 else ('Смешанный' if total_score > 0.3 else 'Вероятно человек')
        }


# =============================================================================
# ГЛАВНОЕ ПРИЛОЖЕНИЕ (обновлено для v8.1 без scipy)
# =============================================================================
class YUCTApp:
    def __init__(self, root):
        self.root = root
        self.raw_text = ""
        self.source_name = ""
        self.global_metrics = {}
        self.navigator = None
        self.running = False
        self.stop_flag = False
        self.section_mode = tk.StringVar(value="paragraphs")
        self.section_n = tk.IntVar(value=10)

        self.root.title("YUСT Семантический процессор с навигацией v8.1 (без scipy)")
        self.root.geometry("1020x1150")
        self.root.configure(bg="#f0f4f8")
        self.root.grid_rowconfigure(8, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        tk.Label(root, text="YUСT Семантический навигатор (v8.1 - +стилевое сравнение, без scipy)", font=("Arial", 14, "bold"),
                 bg="#f0f4f8", fg="#1a365d").grid(row=0, column=0, pady=5, sticky="ew")

        self.btn_load = tk.Button(root, text="📂 Загрузить текст (.txt, .pdf)", command=self.load_file_threaded,
                                  font=("Arial", 11, "bold"), bg="#2b6cb0", fg="white", padx=10, pady=5, relief="flat")
        self.btn_load.grid(row=1, column=0, pady=5, sticky="ew")

        self.txt_manual = scrolledtext.ScrolledText(root, width=85, height=6, font=("Arial", 10))
        self.txt_manual.grid(row=2, column=0, pady=5, padx=15, sticky="ew")

        settings_frame = tk.Frame(root, bg="#f0f4f8")
        settings_frame.grid(row=3, column=0, pady=5, sticky="ew")
        tk.Label(settings_frame, text="Режим разбивки:", bg="#f0f4f8").pack(side="left", padx=5)
        mode_menu = ttk.Combobox(settings_frame, textvariable=self.section_mode, values=["paragraphs", "chapters", "fixed"], width=12)
        mode_menu.pack(side="left", padx=5)
        tk.Label(settings_frame, text="N (для fixed):", bg="#f0f4f8").pack(side="left", padx=5)
        spin_n = tk.Spinbox(settings_frame, from_=1, to=50, textvariable=self.section_n, width=5)
        spin_n.pack(side="left", padx=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        self.lbl_status = tk.Label(root, textvariable=self.status_var, font=("Arial", 9, "italic"),
                                   bg="#f0f4f8", fg="#4a5568")
        self.lbl_status.grid(row=4, column=0, pady=2, sticky="ew")

        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.grid(row=5, column=0, pady=5, sticky="ew")

        btn_frame = tk.Frame(root, bg="#f0f4f8")
        btn_frame.grid(row=6, column=0, pady=5, sticky="ew")

        self.btn_analyze = tk.Button(btn_frame, text="🔍 Статический анализ всего текста", command=self.static_analysis_threaded,
                                     font=("Arial", 10, "bold"), bg="#38a169", fg="white", padx=8, pady=5, relief="flat")
        self.btn_analyze.pack(side="left", padx=5)

        self.btn_navigate = tk.Button(btn_frame, text="🧭 Навигация по смысловым пикам", command=self.navigation_threaded,
                                      font=("Arial", 10, "bold"), bg="#d69e2e", fg="white", padx=8, pady=5, relief="flat")
        self.btn_navigate.pack(side="left", padx=5)

        self.btn_stop = tk.Button(btn_frame, text="⏹ Сброс / Остановить", command=self.stop_operation,
                                  font=("Arial", 10, "bold"), bg="#e53e3e", fg="white", padx=8, pady=5, relief="flat")
        self.btn_stop.pack(side="left", padx=5)

        self.btn_export = tk.Button(btn_frame, text="📤 Экспорт JSON", command=self.export_json,
                                    font=("Arial", 10, "bold"), bg="#805ad5", fg="white", padx=8, pady=5, relief="flat")
        self.btn_export.pack(side="left", padx=5)

        self.txt_output = scrolledtext.ScrolledText(root, width=88, height=22, font=("Courier New", 9),
                                                    bg="white", fg="#2d3748", bd=1, relief="solid")
        self.txt_output.grid(row=7, column=0, pady=5, padx=15, sticky="nsew")
        self.root.grid_rowconfigure(7, weight=1)

        tk.Label(root, text="Специально для портала «Философский штурм»", font=("Arial", 9),
                 bg="#f0f4f8", fg="#718096").grid(row=8, column=0, pady=2, sticky="ew")
        self.lbl_link = tk.Label(root, text="yuct.org", font=("Arial", 10, "underline"),
                                 bg="#f0f4f8", fg="#2b6cb0", cursor="hand2")
        self.lbl_link.grid(row=9, column=0, pady=5, sticky="ew")
        self.lbl_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://yuct.org"))

        self.beep_done = lambda: winsound.Beep(1000, 500)
        self.last_report = {}

    def update_status(self, msg, progress_val=None):
        self.status_var.set(msg)
        if progress_val is not None:
            self.progress['value'] = progress_val
        self.root.update_idletasks()

    def set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.btn_load.config(state=state)
        self.btn_analyze.config(state=state)
        self.btn_navigate.config(state=state)
        self.btn_export.config(state=state)
        self.btn_stop.config(state="normal")

    def load_file_threaded(self):
        if self.running:
            messagebox.showwarning("Занято", "Сначала дождитесь завершения текущей операции.")
            return
        threading.Thread(target=self.load_file, daemon=True).start()

    def load_file(self):
        self.running = True
        self.set_buttons_enabled(False)
        self.update_status("Выбор файла...")
        path = filedialog.askopenfilename(filetypes=[("Supported", "*.txt *.pdf"), ("Text", "*.txt"), ("PDF", "*.pdf")])
        if not path:
            self.running = False
            self.set_buttons_enabled(True)
            self.update_status("Готов")
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            self.update_status(f"Загрузка {os.path.basename(path)}...", 0)
            if ext == ".txt":
                with open(path, 'r', encoding='utf-8') as f:
                    self.raw_text = f.read()
            elif ext == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(path)
                    total_pages = len(reader.pages)
                    text_layers = []
                    for i, page in enumerate(reader.pages):
                        if self.stop_flag:
                            break
                        if i % 10 == 0:
                            self.update_status(f"Извлечение PDF: страница {i+1}/{total_pages}", int((i+1)/total_pages*100))
                        t = page.extract_text()
                        if t:
                            text_layers.append(t)
                    self.raw_text = "\n".join(text_layers)
                except ImportError:
                    messagebox.showerror("Ошибка", "Для PDF установите библиотеку: pip install pypdf")
                    self.running = False
                    self.set_buttons_enabled(True)
                    self.update_status("Готов")
                    return
            self.source_name = os.path.basename(path)
            self.txt_manual.delete(1.0, tk.END)
            self.txt_manual.insert(tk.END, self.raw_text[:2000] + "\n[... обрезано для отображения]")
            self.update_status(f"Загружено {len(self.raw_text)} символов", 100)
            messagebox.showinfo("Успех", f"Загружено {len(self.raw_text)} символов")
            self.beep_done()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{str(e)}")
            self.update_status("Ошибка загрузки")
        finally:
            self.running = False
            self.stop_flag = False
            self.set_buttons_enabled(True)

    def get_text(self):
        if self.raw_text:
            return self.raw_text
        text = self.txt_manual.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("Нет данных", "Загрузите файл или введите текст.")
        return text

    def compute_global_metrics(self, text: str) -> dict:
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        if not sentences:
            return {}
        word_counts = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
        avg_sent_len = np.mean(word_counts) if word_counts else 20
        all_words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9]+\b', text.lower())
        unique_count = len(set(all_words))
        total_words = len(all_words)
        duplication = 1.0 - (unique_count / total_words) if total_words > 0 else 0.5
        return {
            'avg_sent_len': avg_sent_len,
            'duplication': duplication,
            'total_words': total_words,
            'unique_words': unique_count
        }

    def stop_operation(self):
        if self.running:
            self.stop_flag = True
            if self.navigator:
                self.navigator.stop()
            self.update_status("Остановка... (дождитесь завершения)")
            self.btn_stop.config(state="disabled")
        else:
            self.txt_output.delete(1.0, tk.END)
            self.txt_output.insert(tk.END, "Интерфейс сброшен.\n")
            self.update_status("Готов", 0)
            self.progress['value'] = 0

    def export_json(self):
        if not self.last_report:
            messagebox.showwarning("Нет данных", "Сначала выполните анализ.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.last_report, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Успех", f"JSON сохранён в {file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить JSON: {str(e)}")

    def static_analysis_threaded(self):
        if self.running:
            messagebox.showwarning("Занято", "Сначала дождитесь завершения текущей операции.")
            return
        threading.Thread(target=self.static_analysis, daemon=True).start()

    def static_analysis(self):
        self.running = True
        self.stop_flag = False
        self.set_buttons_enabled(False)
        text = self.get_text()
        if not text:
            self.running = False
            self.set_buttons_enabled(True)
            return
        self.update_status("Запуск статического анализа...", 0)
        try:
            grid = YUCTLinguisticGrid()
            filter_obj = YUCTSemanticFilter(grid)
            topology = YUCTContextTopology(grid, filter_obj)
            analyzer = YUCTExtendedAnalyzer()
            detector = YUCTPhaseDetector()
            ai_detector = YUCTAIDetector()
            section_analyzer = YUCTSectionAnalyzer(analyzer, ai_detector)
            style_comparator = PhilosophicalStyleComparator()

            if self.stop_flag:
                raise InterruptedError("Прервано пользователем")

            # 1. Основной анализ
            self.update_status("Анализ слов...", 10)
            word_reg = filter_obj.analyze_text_words(text)
            if self.stop_flag:
                raise InterruptedError("Прервано пользователем")
            self.update_status("Построение контекстных профилей...", 30)
            profiles = topology.build_context_profiles(text, word_reg)
            if self.stop_flag:
                raise InterruptedError("Прервано пользователем")
            self.update_status("Вычисление фазовых метрик...", 50)
            phase_report = detector.calculate_phase_metrics(word_reg, profiles)
            synonyms = topology.find_topological_synonyms(profiles, threshold=0.4)
            recommendations = detector.get_recommendations(phase_report)

            # 2. Анализ стиля
            self.update_status("Пунктуационный анализ...", 55)
            punct = analyzer.analyze_punctuation(text)
            self.update_status("Анализ длины предложений...", 60)
            sent_len = analyzer.analyze_sentence_length(text)
            self.update_status("Обнаружение рифмы...", 65)
            rhyme = analyzer.detect_rhyme(text)
            self.update_status("Анализ цветов...", 70)
            color = analyzer.analyze_colors(text)
            self.update_status("Вычисление философской плотности...", 72)
            phi = analyzer.compute_philosophical_density(text)

            # 3. Жанровая классификация (с PHI)
            self.update_status("Жанровая классификация...", 75)
            genre_probs = analyzer.classify_genre(punct, sent_len, rhyme, phase_report['K_eff'], phi)
            style_rec = analyzer.get_style_recommendations(genre_probs, punct, sent_len, rhyme, phase_report['K_eff'], phi)

            # 4. AI-детектор
            self.update_status("Детекция ИИ...", 80)
            ai_result = ai_detector.detect(text, expr_per_1000=punct['expr_per_1000'])

            # 5. Анализ по разделам
            self.update_status("Анализ по разделам...", 83)
            mode = self.section_mode.get()
            n = self.section_n.get()
            section_result = section_analyzer.analyze_sections(text, mode=mode, n=n)

            # 6. Сравнение с эталонными философскими стилями
            self.update_status("Сравнение с эталонными философами...", 86)
            style_metrics = {
                'K_eff': phase_report['K_eff'],
                'TTR': ai_result['ttr'],
                'sent_avg': sent_len['avg'],
                'sent_std': sent_len['std'],
                'expr': punct['expr_per_1000'],
                'PHI': phi
            }
            style_comparison = style_comparator.compare(style_metrics)

            self.global_metrics = self.compute_global_metrics(text)

            # Формирование отчёта
            self.update_status("Формирование отчёта...", 90)
            out = []
            out.append("="*80)
            out.append("           СТАТИЧЕСКИЙ ОТЧЁТ YUCT (весь текст) — v8.1")
            out.append("="*80)
            out.append(f"Источник: {self.source_name if self.source_name else 'Введённый текст'}")
            out.append(f"Объём текста: {len(text)} символов")
            out.append("-"*80)
            out.append(f"Координационная эффективность K_eff      : {phase_report['K_eff']}")
            out.append(f"Эмпирический показатель Ципфа (Beta)     : {phase_report['Beta_Empirical']}")
            out.append(f"Средняя длина слова (букв)               : {phase_report['Avg_Word_Length']}")
            out.append(f"Плотность контекстных связей             : {phase_report['Lattice_Connectivity']}")
            out.append(f"Фазовый статус                           : {phase_report['Phase']}")
            out.append(f"Жанровый вердикт                         : {phase_report['Genre_Verdict']}")
            out.append("-"*80)
            out.append("📊 ГЛОБАЛЬНЫЕ МЕТРИКИ ДЛЯ НАВИГАЦИИ:")
            out.append(f"  Средняя длина предложения (слов): {self.global_metrics.get('avg_sent_len', 'N/A'):.1f}")
            out.append(f"  Коэффициент дублирования: {self.global_metrics.get('duplication', 'N/A'):.3f}")
            out.append(f"  Всего слов: {self.global_metrics.get('total_words', 'N/A')}")
            out.append(f"  Уникальных слов: {self.global_metrics.get('unique_words', 'N/A')}")
            out.append("-"*80)
            out.append("🎭 АНАЛИЗ ЭКСПРЕССИВНОСТИ И СТИЛЯ:")
            out.append(f"  Восклицательных знаков (!): {punct['exclam']}")
            out.append(f"  Вопросительных знаков (?): {punct['quest']}")
            out.append(f"  Многоточий (...): {punct['ellipsis']}")
            out.append(f"  Коэффициент экспрессивности (на 1000 символов): {punct['expr_per_1000']}")
            out.append(f"  Средняя длина предложения (слова): {sent_len['avg']} (std: {sent_len['std']})")
            out.append(f"  Доля коротких предложений (<5 слов): {sent_len['short_ratio']}%")
            out.append(f"  Доля длинных предложений (>25 слов): {sent_len['long_ratio']}%")
            out.append(f"  Индекс рифмы (0-1): {rhyme['rhyme_score']} (на основе {rhyme['total_lines']} строк)")
            out.append("-"*80)
            out.append("🎨 АНАЛИЗ ЦВЕТОВ:")
            out.append(f"  Плотность упоминаний цветов: {color['color_density']}")
            out.append(f"  Средняя валентность цвета: {color['color_valence']}")
            out.append(f"  Разнообразие цветов: {color['color_diversity']}")
            out.append(f"  Тёплых: {color['warm_count']}, Холодных: {color['cool_count']}, Нейтральных: {color['neutral_count']}")
            out.append("-"*80)
            out.append("📚 ЖАНРОВАЯ КЛАССИФИКАЦИЯ:")
            out.append(f"  Научный: {genre_probs['scientific']*100:.1f}%")
            out.append(f"  Художественная проза: {genre_probs['prose']*100:.1f}%")
            out.append(f"  Поэзия: {genre_probs['poetry']*100:.1f}%")
            out.append(f"  Публицистика: {genre_probs['publicistic']*100:.1f}%")
            out.append(f"  Философский: {genre_probs['philosophical']*100:.1f}%")
            out.append(f"  Доминирующий жанр: {genre_probs['dominant']}")
            out.append("-"*80)
            out.append("🧠 СТИЛИСТИЧЕСКОЕ СРАВНЕНИЕ С ЭТАЛОННЫМИ ФИЛОСОФАМИ:")
            sorted_styles = sorted(style_comparison['similarities'].items(), key=lambda x: x[1], reverse=True)
            for name, perc in sorted_styles:
                out.append(f"  {name}: {perc}%")
            out.append(f"  Индекс смешанности: {style_comparison['mixing_index']:.2f} (чем выше, тем более смешанный стиль)")
            out.append(f"  Наиболее близкий философский стиль: {style_comparison['dominant']}")
            out.append("  (Сравнение основано на предварительных эталонных профилях)")
            out.append("-"*80)
            out.append("🤖 ДЕТЕКЦИЯ ИИ-ТЕКСТА:")
            out.append(f"  TTR (лексическое разнообразие): {ai_result['ttr']}")
            out.append(f"  Стандартное отклонение длины предложений: {ai_result['sent_std']}")
            out.append(f"  Доля топ-5 биграмм: {ai_result['top_bigram_ratio']}")
            out.append(f"  Доля редких слов: {ai_result['rare_word_ratio']}")
            out.append(f"  Средняя длина слова: {ai_result['avg_word_len']}")
            out.append(f"  Экспрессивность (на 1000): {ai_result['expr_per_1000']}")
            out.append(f"  ⚡ Вероятность ИИ-генерации: {ai_result['ai_probability']*100:.0f}%")
            out.append(f"  Маркировка: {ai_result['ai_label']}")
            out.append("-"*80)

            # Таблица по разделам
            if section_result['sections']:
                out.append("📊 АНАЛИЗ ПО РАЗДЕЛАМ (режим: {})".format(mode))
                header = "┌─────┬─────────────────────┬──────────┬────────────┬─────────────┬───────────────┬──────────────┐"
                out.append(header)
                out.append("│ №   │ Диапазон            │ K_eff    │ Сред. длина│ Экспрессив- │ Вероятность   │ Философская  │")
                out.append("│     │                     │ локальный│ предложения│ ность       │ ИИ (локальн.) │ плотность    │")
                out.append("├─────┼─────────────────────┼──────────┼────────────┼─────────────┼───────────────┼──────────────┤")
                for sec in section_result['sections']:
                    idx = f"{sec['index']+1:>3}"
                    rng = sec['range'][:19].ljust(19) if len(sec['range']) > 19 else sec['range'].ljust(19)
                    keff = f"{sec['keff']:>8.2f}"
                    sent = f"{sec['sent_avg']:>10.1f}"
                    expr = f"{sec['expr']:>11.2f}"
                    ai = f"{sec['ai_prob']*100:>10.0f}%"
                    phi_val = f"{sec['phi']:>12.3f}"
                    out.append(f"│ {idx} │ {rng} │ {keff} │ {sent} │ {expr} │ {ai} │ {phi_val} │")
                summary = section_result['summary']
                out.append("├─────┼─────────────────────┼──────────┼────────────┼─────────────┼───────────────┼──────────────┤")
                avg_line = f"│ AVG │ (среднее)          │ {summary['keff_avg']:>8.2f} │ {summary['sent_avg_avg']:>10.1f} │ {summary['expr_avg']:>11.2f} │ {summary['ai_prob_avg']*100:>10.0f}% │ {summary['phi_avg']:>12.3f} │"
                std_line = f"│ STD │ (отклонение)       │ {summary['keff_std']:>8.2f} │ {summary['sent_avg_std']:>10.1f} │ {summary['expr_std']:>11.2f} │ {summary['ai_prob_std']*100:>10.0f}% │ {summary['phi_std']:>12.3f} │"
                min_line = f"│ MIN │ (минимум)          │ {summary['keff_min']:>8.2f} │ {summary['sent_avg_min']:>10.1f} │ {summary['expr_min']:>11.2f} │ {summary['ai_prob_min']*100:>10.0f}% │ {summary['phi_min']:>12.3f} │"
                max_line = f"│ MAX │ (максимум)         │ {summary['keff_max']:>8.2f} │ {summary['sent_avg_max']:>10.1f} │ {summary['expr_max']:>11.2f} │ {summary['ai_prob_max']*100:>10.0f}% │ {summary['phi_max']:>12.3f} │"
                out.append(avg_line)
                out.append(std_line)
                out.append(min_line)
                out.append(max_line)
                out.append("└─────┴─────────────────────┴──────────┴────────────┴─────────────┴───────────────┴──────────────┘")
                out.append("")
                out.append(f"📊 СТИЛИСТИЧЕСКАЯ ВАРИАТИВНОСТЬ:")
                out.append(f"  Индекс однородности: {summary['uniformity']:.3f} (1 = идеально однородно)")
                if summary['uniformity'] > 0.8:
                    out.append("  Вывод: текст очень однороден → вероятно один автор или ИИ.")
                elif summary['uniformity'] > 0.5:
                    out.append("  Вывод: текст умеренно-вариативный → вероятнее человек или коллектив.")
                else:
                    out.append("  Вывод: текст сильно разнороден → вероятно коллективная работа или смена стилей.")
            else:
                out.append("📊 АНАЛИЗ ПО РАЗДЕЛАМ: недостаточно данных для разбивки.")

            out.append("-"*80)
            out.append("🔝 Топ-5 красноречивых слов:")
            top_words = sorted(word_reg.items(), key=lambda x: x[1]["eloquence_score"], reverse=True)[:5]
            for w, data in top_words:
                out.append(f"  {w:>12} | вес: {data['eloquence_score']:.4f} | частота: {data['count']}")
            if synonyms:
                out.append("-"*80)
                out.append("🔗 Обнаруженные контекстные синонимы:")
                for pair in synonyms[:5]:
                    out.append(f"  {pair['word1']} ≡ {pair['word2']} (сходство {pair['similarity']*100:.1f}%)")
            out.append("-"*80)
            out.append("💡 РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ ТЕКСТА (с учётом жанра):")
            out.append(style_rec)
            out.append("="*80)
            out.append("https://github.com/Alexey-Yakushev-YUCT/verify-quant-philosophy")

            self.txt_output.delete(1.0, tk.END)
            self.txt_output.insert(tk.END, "\n".join(out))

            # Сохраняем отчёт для JSON
            self.last_report = {
                "meta": {
                    "source": self.source_name,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "8.1"
                },
                "global": {
                    "K_eff": phase_report['K_eff'],
                    "Phase": phase_report['Phase'],
                    "Genre": genre_probs['dominant'],
                    "AI_Probability": ai_result['ai_probability'],
                    "AI_Label": ai_result['ai_label']
                },
                "metrics": {
                    "ttr": ai_result['ttr'],
                    "sent_avg": sent_len['avg'],
                    "sent_std": sent_len['std'],
                    "expr_per_1000": punct['expr_per_1000'],
                    "color_density": color['color_density'],
                    "color_valence": color['color_valence'],
                    "rhyme_score": rhyme['rhyme_score'],
                    "duplication": self.global_metrics.get('duplication', 0.5),
                    "phi": phi
                },
                "sections": section_result['sections'],
                "stylistic_variation": {
                    "uniformity_score": section_result['summary'].get('uniformity', 0),
                    "K_eff_variance": section_result['summary'].get('keff_std', 0)**2,
                    "sent_avg_variance": section_result['summary'].get('sent_avg_std', 0)**2,
                    "expr_variance": section_result['summary'].get('expr_std', 0)**2,
                },
                "style_comparison": {
                    "similarities": style_comparison['similarities'],
                    "dominant": style_comparison['dominant'],
                    "mixing_index": style_comparison['mixing_index']
                }
            }

            self.update_status("Статический анализ завершён", 100)
            self.beep_done()
        except InterruptedError:
            self.update_status("Операция прервана", 0)
            self.txt_output.insert(tk.END, "\n⚠️ Операция была прервана пользователем.\n")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Статический анализ не удался:\n{str(e)}")
            self.update_status("Ошибка анализа")
        finally:
            self.running = False
            self.stop_flag = False
            self.set_buttons_enabled(True)
            self.btn_stop.config(state="normal")

    def navigation_threaded(self):
        if self.running:
            messagebox.showwarning("Занято", "Сначала дождитесь завершения текущей операции.")
            return
        threading.Thread(target=self.run_navigation, daemon=True).start()

    def run_navigation(self):
        self.running = True
        self.stop_flag = False
        self.set_buttons_enabled(False)
        text = self.get_text()
        if not text:
            self.running = False
            self.set_buttons_enabled(True)
            return
        self.update_status("Запуск навигации (два потока)...", 0)
        try:
            grid = YUCTLinguisticGrid()
            filter_obj = YUCTSemanticFilter(grid)
            topology = YUCTContextTopology(grid, filter_obj)
            detector = YUCTPhaseDetector()
            analyzer = YUCTExtendedAnalyzer()
            ai_detector = YUCTAIDetector()
            self.navigator = YUCTSemanticNavigator(grid, filter_obj, topology, detector, analyzer, ai_detector)

            if not self.global_metrics:
                self.global_metrics = self.compute_global_metrics(text)

            def progress_callback(val, msg):
                if self.stop_flag:
                    self.navigator.stop()
                self.update_status(f"{msg}: {val}%", val)

            result = self.navigator.navigate(text, global_metrics=self.global_metrics, progress_callback=progress_callback)
            self.update_status("Формирование отчёта...", 90)

            if result['status'] == "CANCELLED":
                self.txt_output.delete(1.0, tk.END)
                self.txt_output.insert(tk.END, "⚠️ Навигация была прервана пользователем.\n")
                self.update_status("Навигация прервана", 0)
                return

            phase_type = result['phase']['type'] if result['phase'] else "UNKNOWN"
            phase_explanation = self.navigator.phase_descriptions.get(phase_type, "Нет пояснения.")

            punct_peak = analyzer.analyze_punctuation(result['text'])
            sent_len_peak = analyzer.analyze_sentence_length(result['text'])
            rhyme_peak = analyzer.detect_rhyme(result['text'])
            color_peak = analyzer.analyze_colors(result['text'])
            phi_peak = analyzer.compute_philosophical_density(result['text'])
            ai_peak = ai_detector.detect(result['text'], expr_per_1000=punct_peak['expr_per_1000'])

            out = []
            out.append("="*80)
            out.append("           ОТЧЁТ СЕМАНТИЧЕСКОЙ НАВИГАЦИИ YUCT (двухпоточный)")
            out.append("="*80)
            out.append(f"Источник: {self.source_name if self.source_name else 'Введённый текст'}")
            out.append(f"Всего окон (предложений): {result.get('total_windows', 0)}")
            out.append(f"Использованы глобальные метрики: {'Да' if self.global_metrics else 'Нет'}")
            out.append("-"*80)
            out.append(f"Статус: {result['status']}")
            if result['status'] != "ERROR":
                out.append(f"Найденная позиция (окно #{result['position']})")
                out.append(f"Локальная координационная эффективность K_eff: {result['keff']:.4f}")
                out.append(f"Фазовый переход: {result['phase']['type']} - {result['phase']['desc']}")
                out.append(f"Двунаправленный поиск: {'Да' if result['phase']['bidirectional'] else 'Нет'}")
                out.append("-"*80)
                out.append("🔍 ПОЯСНЕНИЕ ФАЗОВОГО ПЕРЕХОДА:")
                out.append(f"  {phase_explanation}")
                out.append("-"*80)
                out.append("📊 ЛОКАЛЬНЫЙ СТИЛИСТИЧЕСКИЙ АНАЛИЗ ПИКА:")
                out.append(f"  Экспрессивность (на 1000 символов): {punct_peak['expr_per_1000']}")
                out.append(f"  Средняя длина предложения (слова): {sent_len_peak['avg']}")
                out.append(f"  Индекс рифмы: {rhyme_peak['rhyme_score']}")
                out.append(f"  Плотность цветов: {color_peak['color_density']}")
                out.append(f"  Философская плотность: {phi_peak:.3f}")
                out.append(f"  Вероятность ИИ (локально): {ai_peak['ai_probability']*100:.0f}%")
                out.append("-"*80)
                out.append("🔹 Фрагмент-пик (первые 500 символов):")
                out.append(result['text'][:500] + "...")
                out.append("-"*80)
                out.append("💡 Рекомендация: для более точного анализа выполните статический анализ.")
            else:
                out.append(f"Ошибка: {result.get('message', 'Неизвестная ошибка')}")
            out.append("="*80)
            out.append("https://github.com/Alexey-Yakushev-YUCT/verify-quant-philosophy")

            self.txt_output.delete(1.0, tk.END)
            self.txt_output.insert(tk.END, "\n".join(out))
            self.update_status("Навигация завершена", 100)
            self.beep_done()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Навигация не удалась:\n{str(e)}")
            self.update_status("Ошибка навигации")
        finally:
            self.running = False
            self.stop_flag = False
            self.navigator = None
            self.set_buttons_enabled(True)
            self.btn_stop.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = YUCTApp(root)
    root.mainloop()
