"""
Simulated Variational Quantum Circuit (VQC) Regressor for Marine Fuel Consumption Prediction.
Simulates a 4-to-6 qubit parameterized quantum circuit (angle encoding + variational ansatz + Pauli-Z readout)
on classical hardware. Clearly marked as simulated quantum-inspired.
"""

from typing import List, Dict, Any, Optional
import math
import numpy as np
from sklearn.decomposition import PCA
from scipy.optimize import minimize


class SimulatedVQCRegressor:
    """
    High-fidelity statevector simulator of a Variational Quantum Circuit (VQC) regressor:
    - Qubits: n_qubits (default 4)
    - Feature encoding: PCA compression + Angle encoding (Ry rotations)
    - Variational Ansatz: Parameterized Ry & Rz rotations with circular CNOT entanglement
    - Measurement: Expectation value of Pauli-Z operators <Z_i> on each qubit
    - Readout: Classical linear combination with bias
    """

    LABEL = "Quantum-Inspired Simulated Variational Circuit (Statevector)"

    def __init__(
        self,
        n_qubits: int = 4,
        n_layers: int = 2,
        max_iter: int = 100,
        seed: int = 42,
    ):
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.max_iter = max_iter
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        self.pca = PCA(n_components=n_qubits, random_state=seed)
        self.dim = 2 ** n_qubits

        # Variational parameters shape: layers x qubits x 2 (Ry and Rz angles)
        self.n_var_params = n_layers * n_qubits * 2
        # Readout weights: n_qubits weights + 1 bias
        self.total_trainable_params = self.n_var_params + self.n_qubits + 1

        self.weights: Optional[np.ndarray] = None
        self.training_loss_history: List[float] = []

    def _ry_matrix(self, theta: float) -> np.ndarray:
        c = math.cos(theta / 2.0)
        s = math.sin(theta / 2.0)
        return np.array([[c, -s], [s, c]], dtype=np.complex128)

    def _rz_matrix(self, theta: float) -> np.ndarray:
        return np.array(
            [[np.exp(-1j * theta / 2.0), 0], [0, np.exp(1j * theta / 2.0)]],
            dtype=np.complex128,
        )

    def _apply_single_qubit_gate(
        self, state: np.ndarray, gate: np.ndarray, target_qubit: int
    ) -> np.ndarray:
        """Apply a 2x2 unitary gate to target_qubit in statevector."""
        # Reshape state into tensor of rank n_qubits (each index dimension 2)
        shape = [2] * self.n_qubits
        tensor = state.reshape(shape)
        # Move target axis to front, matrix multiply, move back
        tensor = np.moveaxis(tensor, target_qubit, 0)
        tensor = np.tensordot(gate, tensor, axes=(1, 0))
        tensor = np.moveaxis(tensor, 0, target_qubit)
        return tensor.reshape(-1)

    def _apply_cnot(self, state: np.ndarray, control: int, target: int) -> np.ndarray:
        """Apply 2-qubit CNOT gate."""
        shape = [2] * self.n_qubits
        tensor = state.reshape(shape)
        # Index slice where control is |1>: flip target index
        idx_c1 = [slice(None)] * self.n_qubits
        idx_c1[control] = 1
        sub_tensor = tensor[tuple(idx_c1)]
        # Flip target
        idx_t_flip = [slice(None)] * (self.n_qubits - 1)
        target_in_sub = target if target < control else target - 1
        tensor[tuple(idx_c1)] = np.flip(sub_tensor, axis=target_in_sub)
        return tensor.reshape(-1)

    def _simulate_circuit(
        self, x_angles: np.ndarray, var_params: np.ndarray
    ) -> np.ndarray:
        """
        Simulate quantum circuit for single feature vector x_angles.
        Returns vector of expectation values [<Z_0>, <Z_1>, ..., <Z_{N-1}>].
        """
        # Initial ground state |00...0>
        state = np.zeros(self.dim, dtype=np.complex128)
        state[0] = 1.0 + 0j

        # 1. Angle encoding: Ry(arctan(x_i) * 2)
        for q in range(self.n_qubits):
            gate = self._ry_matrix(x_angles[q])
            state = self._apply_single_qubit_gate(state, gate, q)

        # 2. Variational Ansatz layers
        param_idx = 0
        for l in range(self.n_layers):
            # Parameterized rotations Ry and Rz
            for q in range(self.n_qubits):
                theta_y = var_params[param_idx]
                theta_z = var_params[param_idx + 1]
                param_idx += 2

                state = self._apply_single_qubit_gate(state, self._ry_matrix(theta_y), q)
                state = self._apply_single_qubit_gate(state, self._rz_matrix(theta_z), q)

            # Circular CNOT entanglement
            for q in range(self.n_qubits):
                next_q = (q + 1) % self.n_qubits
                state = self._apply_cnot(state, q, next_q)

        # 3. Measurement: Pauli-Z expectation values
        expectations = np.zeros(self.n_qubits, dtype=np.float64)
        prob = np.abs(state) ** 2

        # Reshape to sum probabilities where qubit is |0> minus where it is |1>
        prob_tensor = prob.reshape([2] * self.n_qubits)
        for q in range(self.n_qubits):
            idx0 = [slice(None)] * self.n_qubits
            idx0[q] = 0
            p0 = np.sum(prob_tensor[tuple(idx0)])

            idx1 = [slice(None)] * self.n_qubits
            idx1[q] = 1
            p1 = np.sum(prob_tensor[tuple(idx1)])
            expectations[q] = float(p0 - p1)

        return expectations

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SimulatedVQCRegressor":
        """Fit PCA and optimize circuit variational angles + readout weights."""
        X_reduced = self.pca.fit_transform(X)
        # Scale to [-pi, pi]
        x_norm = np.clip(X_reduced, -3.0, 3.0) / 3.0 * math.pi

        # Initialize parameters
        init_params = self.rng.normal(0.0, 0.25, size=self.total_trainable_params)

        # Subsample for VQC training efficiency if dataset is large
        max_samples = 400
        if len(y) > max_samples:
            idx = self.rng.choice(len(y), size=max_samples, replace=False)
            x_train = x_norm[idx]
            y_train = y[idx]
        else:
            x_train = x_norm
            y_train = y

        def loss_fn(params: np.ndarray) -> float:
            var_params = params[: self.n_var_params]
            readout_w = params[self.n_var_params : self.n_var_params + self.n_qubits]
            bias = params[-1]

            preds = []
            for i in range(len(y_train)):
                exp_vals = self._simulate_circuit(x_train[i], var_params)
                y_hat = np.dot(readout_w, exp_vals) + bias
                preds.append(y_hat)

            preds = np.array(preds)
            mse = float(np.mean((preds - y_train) ** 2))
            # L2 regularization
            reg = 0.001 * float(np.sum(params ** 2))
            return mse + reg

        print(f"Optimizing simulated VQC on {self.n_qubits} qubits...")
        res = minimize(
            loss_fn,
            init_params,
            method="L-BFGS-B",
            options={"maxiter": self.max_iter, "disp": False},
        )
        self.weights = res.x
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict target values using the trained VQC circuit."""
        if self.weights is None:
            raise ValueError("VQC model has not been trained.")

        X_reduced = self.pca.transform(X)
        x_norm = np.clip(X_reduced, -3.0, 3.0) / 3.0 * math.pi

        var_params = self.weights[: self.n_var_params]
        readout_w = self.weights[self.n_var_params : self.n_var_params + self.n_qubits]
        bias = self.weights[-1]

        preds = np.zeros(len(X), dtype=np.float64)
        for i in range(len(X)):
            exp_vals = self._simulate_circuit(x_norm[i], var_params)
            preds[i] = float(np.dot(readout_w, exp_vals) + bias)

        return preds
