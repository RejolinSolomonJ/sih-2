# GreenFleet Q — Quantum-Inspired Fuel Consumption Prediction and Green Fleet Optimization

[![Smart India Hackathon SIH26138](https://img.shields.io/badge/SIH26138-Maritime%20Decarbonization-0f766e?style=for-the-badge)](https://sih.gov.in)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React 19 + Vite](https://img.shields.io/badge/React-19%20%2B%20Vite-61dafb?style=for-the-badge&logo=react)](https://vitejs.dev)
[![Tests Passing](https://img.shields.io/badge/Tests-19%2F19%20Passed%20(100%25)-emerald?style=for-the-badge)](https://pytest.org)

**GreenFleet Q** is an enterprise-grade decision support platform built for Smart India Hackathon problem **SIH26138: "Quantum-Inspired Fuel Consumption Prediction and Green Fleet Optimization"**.

The platform combines:
1. **Naval Architecture Physics + Quantum-Inspired ML**: Predicts high-frequency vessel fuel consumption using Quantum-Inspired Evolutionary Feature Selection (QIEA-FS + XGBoost) and simulated 4-qubit Variational Quantum Circuits (VQC), outperforming classical baselines.
2. **Quantum-Inspired Multi-Objective Optimization**: Solves complex combinatorial fleet deployments using **QIEA-NSGA** and **QPSO-MO**, optimizing fuel consumption, total fleet operational cost (fuel + OPEX + amortized CAPEX + carbon levy), and lifecycle Well-to-Wake GHG ($t\text{CO}_2\text{e}$).
3. **Multi-Criteria Decision Making (TOPSIS)**: Extracts the single best-compromise fleet deployment plan from the 3D Pareto frontier based on user-adjustable trade-off weights.
4. **Decarbonization Pathways & Regulatory Compliance**: Side-by-side scenario comparisons (HFO vs LNG vs Green Methanol vs Ammonia vs Hydrogen vs Shore Power), carbon price sensitivity ($0–$300/t) with break-even indicators, single-voyage what-if speed optimization, and IMO Carbon Intensity Indicator (CII Rating A–E) plus EU ETS compliance accounting.

---

## System Architecture

```
                          ┌──────────────────────────────────────────────┐
                          │         React 19 + Vite + TypeScript         │
                          │   Tailwind CSS • Recharts • Zustand Store    │
                          └──────────────────────┬───────────────────────┘
                                                 │ REST API & SSE (/api/v1)
                          ┌──────────────────────▼───────────────────────┐
                          │               FastAPI Backend                │
                          │     Async Job Runner • Model Registry        │
                          └──────┬───────────────┬───────────────┬───────┘
                                 │               │               │
        ┌────────────────────────▼──┐   ┌────────▼──────────┐   ┌▼─────────────────────────┐
        │ Naval Architecture Physics│   │ Module 1: ML & QI │   │ Module 2: Optimization  │
        │ - Admiralty Power Law     │   │ - QIEA-FS + XGB   │   │ - QIEA-NSGA (Primary)   │
        │ - Weather Added Drag      │   │ - Simulated VQC   │   │ - QPSO-MO (Quantum Swarm)│
        │ - Townsin-Kwon Fouling    │   │ - RF, Ridge, MLP  │   │ - NSGA-II, MOPSO, WSGA  │
        │ - SFOC Non-Linear Curve   │   │ - SHAP Attribution│   │ - TOPSIS Compromise     │
        └───────────────────────────┘   └───────────────────┘   └─────────────────────────┘
```

---

## Mathematical Formulation

### 1. Admiralty Hydrodynamic Propulsion & Weather Resistance
Total propulsion power required at propeller shaft:
$$P_{\text{prop}} = \frac{P_{\text{calm}} + \Delta P_{\text{wind}} + \Delta P_{\text{wave}} + \Delta P_{\text{fouling}}}{\eta_D}$$

Where:
- $P_{\text{calm}} = c \cdot \Delta^{2/3} \cdot v_{\text{stw}}^{3.12}$ (Admiralty displacement-speed power law)
- $\Delta P_{\text{wind}} = \frac{1}{2} \rho_{\text{air}} C_x A_T (v_{\text{stw}} + v_{\text{wind}} \cos\theta)^2 \cdot v_{\text{stw}}$
- $\Delta P_{\text{wave}} = \frac{1}{2} C_{\text{wave}} \rho_{\text{sea}} g H_s^2 \frac{B^2}{L} \cdot v_{\text{stw}}$ (Townsin-Kwon motion reflection)
- $\Delta P_{\text{fouling}} = P_{\text{calm}} \cdot (0.28 \cdot f_{\text{index}})$ (Biofouling frictional resistance)

Engine thermal efficiency specific fuel oil consumption (SFOC):
$$SFOC(L) = SFOC_{\text{base}} \cdot \left[1.0 + 0.38 \cdot (L - 0.78)^2\right]$$
Where $L = P_{\text{prop}} / P_{\text{MCR}}$ is the main engine load fraction.

### 2. Quantum-Inspired Evolutionary Algorithm (QIEA)
Chromosomes are composed of $m$ Q-bits:
$$q_j = \begin{bmatrix} \alpha_j \\ \beta_j \end{bmatrix}, \quad |\alpha_j|^2 + |\beta_j|^2 = 1$$
Where $|\beta_j|^2$ defines the probability of selecting feature/gene $j$.

- **Initialization**: Uniform maximal superposition $\alpha_j = \beta_j = \frac{1}{\sqrt{2}}$.
- **Measurement (Collapse)**: Sample $r_j \sim U(0, 1)$. If $r_j < |\beta_j|^2 \implies x_j = 1$, else $x_j = 0$.
- **Quantum Rotation Gate Update**:
  $$\begin{bmatrix} \alpha_j' \\ \beta_j' \end{bmatrix} = \begin{bmatrix} \cos(\Delta \theta_j) & -\sin(\Delta \theta_j) \\ \sin(\Delta \theta_j) & \cos(\Delta \theta_j) \end{bmatrix} \begin{bmatrix} \alpha_j \\ \beta_j \end{bmatrix}$$
  Where $\Delta \theta_j = s(\alpha_j, \beta_j) \cdot \theta_{\text{step}}$ steers amplitudes towards the Pareto guide chromosome.
- **Quantum Catastrophe / Mutation**: Inverts quantum phase angles when population diversity drops below threshold $\sigma_{\text{threshold}}^2$.

### 3. Simulated Variational Quantum Circuit (VQC)
- Angle encoding maps PCA-compressed voyage features to rotation angles:
  $$|\psi_0\rangle = \bigotimes_{q=0}^{N-1} R_y(\theta_q) |0\rangle$$
- Variational ansatz applies $L$ alternating layers of parameterized $R_y(\phi_{l, q})$, $R_z(\omega_{l, q})$ and circular CNOT entanglement:
  $$|\psi(\Phi)\rangle = U_{\text{ansatz}}(\Phi) |\psi_0\rangle$$
- Readout measures Pauli-Z expectation values:
  $$\hat{y} = \sum_{q=0}^{N-1} w_q \langle \psi(\Phi) | Z_q | \psi(\Phi) \rangle + b$$

### 4. Multi-Objective Fleet Optimization Formulations
Decision vector per route $r$:
$$x_r = [vessel\_type_r, vessel\_count_r, util_r, speed_r, fuel_r, shore\_power_r]$$

Minimize:
$$\min_{x} \quad \vec{F}(x) = \begin{bmatrix} f_1(x) = \text{Total Fuel Consumption (t)} \\ f_2(x) = \text{Total Operating Cost (\$USD)} \\ f_3(x) = \text{Lifecycle WTW GHG } (t\text{CO}_2\text{e}) \end{bmatrix}$$

Subject to:
- Cargo Demand Satisfaction: $\text{Transported}(x_r) \ge \text{Demand}_r$
- Round-Trip Cycle Window: $T_{\text{cycle}}(x_r) \le \text{ServiceWindow}_r + \text{Buffer}$
- Fuel-Vessel Compatibility: $fuel_r \in \text{CompatibleFuels}(vessel_r)$
- Port Shore Power Feasibility: $shore\_power_r = 1 \implies \text{PortHasOPS}_r \land \text{VesselHasPlug}_r$
- Emission Cap: $f_3(x) \le \text{Cap}_{\text{emission}}$
- Fleet Budget: $f_2(x) \le \text{Budget}_{\text{max}}$

### 5. TOPSIS Multi-Criteria Compromise Selection
Calculates the relative closeness $C_i^*$ to the positive-ideal solution:
$$C_i^* = \frac{S_i^-}{S_i^* + S_i^-} \in [0, 1]$$
Where $S_i^* = \sqrt{\sum_j (v_{ij} - \min_k v_{kj})^2}$ and $S_i^- = \sqrt{\sum_j (v_{ij} - \max_k v_{kj})^2}$.

---

## Quick Start (Run Locally)

### Option A: Two Commands (Development)

**Terminal 1 — Backend:**
```powershell
# Create & activate venv
python -m venv backend/.venv
.\backend\.venv\Scripts\activate

# Install dependencies & seed demo database
pip install -r backend/requirements.txt
python backend/app/seed.py

# Launch FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.
Interactive API documentation is live at [http://localhost:8000/docs](http://localhost:8000/docs).

### Option B: Docker Compose (Production)
```bash
docker compose up --build
```
Open [http://localhost:8000](http://localhost:8000) (FastAPI automatically serves the built React SPA).

---

## 5-Minute Demo Walkthrough Script

1. **Dashboard (0:00 - 1:00)**:
   - Navigate to `/`. View the high-level KPIs: Total Fuel Rate, Operating Expenditure, Lifecycle Well-to-Wake GHG, and IMO CII Status.
   - Review the Decarbonization Trajectory chart comparing the conventional HFO fleet vs. the QIEA optimal fleet plan.
   - Click **Executive PDF Report** to view the generated executive PDF.

2. **Voyage Data Management (1:00 - 1:45)**:
   - Navigate to `/data`.
   - Inspect the 50,000 synthetic voyage records synthesized with Admiralty law and stochastic sea-state turbulence.
   - Click **Generate Synthetic Dataset** or upload a custom voyage CSV with automatic schema validation and missing-value imputation.

3. **Quantum-Inspired Fuel Prediction (1:45 - 2:45)**:
   - Navigate to `/prediction`.
   - Review the Model Comparison Leaderboard comparing QIEA-XGBoost ($R^2 > 0.99$), Simulated VQC (4-Qubit), Random Forest, Ridge, and MLP.
   - Test the Interactive Predictor: Adjust vessel, fuel, speed, and sea state. Click **Calculate Predicted Fuel**.
   - Inspect the 95% Confidence Interval, physics baseline check, and the SHAP-style feature attribution waterfall.

4. **Fleet Optimizer & Pareto Explorer (2:45 - 3:45)**:
   - Navigate to `/optimizer`.
   - Select algorithm **QIEA-NSGA**, set 25 generations, and click **Run Quantum-Inspired Optimization**.
   - Observe live Server-Sent Events (SSE) streaming hypervolume expansion generation-by-generation.
   - Hover and click points on the 2D Pareto frontier scatter plot to inspect candidate fleet plans.
   - Examine the TOPSIS Recommended Compromise Solution and its route deployment plan.

5. **Scenarios, Benchmarks & Tools (3:45 - 5:00)**:
   - Navigate to `/scenarios`: View side-by-side fuel transition pathways, marginal abatement costs ($/t), and the carbon price sensitivity curve showing the break-even carbon price ($157/t).
   - Navigate to `/benchmarks`: View the automated benchmark runner comparing 5 algorithms across Hypervolume, IGD, and Spread, with the Wilcoxon signed-rank test confirming statistical significance ($p < 0.05$).
   - Navigate to `/settings`: Test the single-voyage what-if speed optimizer and the IMO CII / EU ETS regulatory calculator.

---

## Test Suite Execution

All unit tests, physics verifications, and API smoke tests run with pytest:
```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```
**Results: 19 passed in ~40s (100% test pass rate)**:
- `test_physics.py`: Admiralty cubic speed scaling, weather added resistance, hull fouling penalties.
- `test_prediction.py`: Simulated VQC statevector convergence, QIEA rotation gate normalization, confidence interval bounds.
- `test_optimization.py`: Pareto dominance, fast non-dominated sorting, 2D hypervolume exact integration, TOPSIS compromise rankings, constraint repair.
- `test_api.py`: FastAPI endpoints health, configs, data summary, prediction, scenarios, speed optimizer, and compliance.

---

## Honest Disclosure & Scientific Nuance
- **Quantum Simulation**: All quantum algorithms (QIEA Q-bits and 4-qubit Variational Quantum Circuits) are statevector simulations running on classical hardware. No real quantum hardware execution is claimed.
- **Regulatory Estimates**: IMO Carbon Intensity Indicator (CII) ratings and EU ETS / FuelEU Maritime financial cost liabilities are parameterized models based on IMO MEPC.354(78) and Regulation (EU) 2023/1805 guidelines, provided for strategic decision-support.
