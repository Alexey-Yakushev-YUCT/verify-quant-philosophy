# YUCT Quantitative Semantic Interpreter

This repository provides open-source tools to verify, reproduce, and practically apply the experimental frameworks of Yakushev Unified Coordination Theory (YUCT) to philosophical, scientific, and authorial texts.

## 🧠 About the Project

The tool implements word-frequency algorithms and Shannon's information theory to evaluate the coordination efficiency of cognitive systems ($K_{eff} = H(D)/H(I)$). The software is fully deterministic, containing no hidden variables or manual tuning weights. It measures syntactic and semantic text density, steering humanitarian audit toward verifiable science.

## 📊 Psycho-Ontological Classification of Authors

Based on the coordination efficiency metric ($K_{eff}$) extracted from the author's speech corpus, the framework scans the individual's cognitive architecture, allowing personality ranking for cognitive assessment:

1. **Range $K_{eff} < 2$ — Chaotic Type (Coordination Crisis)**
   * **Cognitive Essence:** Fragmented, de-structured thinking. Lacks a stable conceptual framework. A stream of consciousness without a logical core.
   * **Professional Selection:** Unsuitable for systematic, managerial, or analytical work. A distress signal indicating exhaustion or a cognitive crisis.

2. **Range $2 \le K_{eff} < 5$ — Associative-Emotional Type (Poets & Polemicists)**
   * **Cognitive Essence:** Dominated by imagery perception, high synonymic redundancy, and metaphorical noise. Logical strictness yields to stylistic eloquence and emotional resonance (Nietzsche, Kierkegaard, publicistic essays).
   * **Professional Selection:** Ideal for creative industries, arts, PR, copywriting, and visionary team leadership. Not recommended for drafting rigid regulations.

3. **Range $5 \le K_{eff} < 10$ — Systemic-Analytical Type (Engineers & Administrators)**
   * **Cognitive Essence:** Developed, stable logical structure. Pronounced and disciplined authorial stance. Ability to compress data, eliminating "verbal fluff" (academic monographs, dissertations, Appendix H2 text structure).
   * **Professional Selection:** Perfect executive managers, architects of corporate systems, high-level analysts, authors of state programs and legal codes.

4. **Range $10 \le K_{eff} < 20$ — Conceptual-Monumental Type (Strategists)**
   * **Cognitive Essence:** Ultimate concentration of meanings. Axiomatic basis is maximally compressed. Ability to coordinate vast arrays of knowledge around a single axis (level of Kant, Hegel). High mental autonomy.
   * **Professional Selection:** Strategic leaders, authors of breakthrough scientific paradigms, chief designers, and civilizational visionaries.

5. **Range $K_{eff} \ge 20$ — Formal Meta-Systems**
   * **Cognitive Essence:** Pure logic and mathematics, completely cleared of subjective or emotional noise (level of the core YUCT matrix). On small text volumes (under 1000 words), it may indicate a statistical "Parmenides anomaly".

## ⚠️ Preventive Ethics (Appendix Σ Imperatives)

Objective selection and classification of individuals based on their linguistic footprint carry fundamental social risks. This project adheres to strict ethical imperatives:
* **Safeguarding Individuality:** The tool is not a Procrustean bed. A low or average $K_{eff}$ does not mean intellectual inferiority — it measures the price (in logical redundancy) an author pays for their unique artistic voice. Creative irrationality has a sovereign right to exist.
* **Parity and Transparency:** The detection algorithm is open and falsifiable. We categorically oppose the use of such metrics for covert, unannounced corporate or state profiling. Everyone has the right to test their own text and view their cognitive profile.

## 🛠️ Quick Start

### 1. Install Dependencies
To enable full support for links and PDF parsing, install the required packages:
```bash
pip install requests beautifulsoup4 pypdf numpy
```

### 2. Run the Quantitative Semantic Interpreter
```bash
python verify_philosophy.py
```
The program will launch a Graphical User Interface (GUI), allowing you to select a local `.txt` or `.pdf` file, or paste a URL link to any online article. The comprehensive report with core metrics and full psycho-ontological diagnosis will be generated automatically.
