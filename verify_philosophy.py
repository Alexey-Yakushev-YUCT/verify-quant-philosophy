import numpy as np

def calculate_yuct_metrics(h_d, h_i, alpha=0.1):
    """
    Calculates Keff, Epsilon, and Bell's S according to Yakushev Unified Coordination Theory (YUCT).
    """
    kc = 1 / 3
    if h_i == 0:
        return {"K_eff": float('inf'), "Epsilon": 0.0, "Bell_S": round(2 + 2 * np.sqrt(2) - 2, 4)}
        
    k_eff = h_d / h_i
    epsilon = kc * alpha * (k_eff ** (-2/3))
    bell_s = 2 + (2 * np.sqrt(2) - 2) * (1 - 2 * kc * alpha * (k_eff ** (-2/3)))
    
    # Phase determination
    if k_eff < 2: phase = "Nihilism / Absurd"
    elif 2 <= k_eff < 5: phase = "Skepticism / Relativism"
    elif 5 <= k_eff < 10: phase = "Metaphysics / Systematic Philosophy"
    elif 10 <= k_eff < 20: phase = "Critical Philosophy"
    else: phase = "Formal System"
        
    return {
        "K_eff": round(k_eff, 2),
        "Epsilon": round(epsilon, 6),
        "Bell_S": round(bell_s, 4),
        "Phase": phase
    }

if __name__ == "__main__":
    print("--- YUCT Mathematical Verification Tool ---")
    # Verification of Kant from the experiment: H(D)=8.5, H(I)=0.85
    kant = calculate_yuct_metrics(8.5, 0.85)
    print(f"Kant verification (Expected K_eff=10.0, Bell_S=2.8161):")
    print(kant)
