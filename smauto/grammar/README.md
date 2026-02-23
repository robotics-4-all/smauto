# SmAuto Formal Semantics

This document provides a comprehensive formal specification of the SmAuto Domain Specific Language (DSL). It defines the language's syntax and semantics using standard formal methods, including Abstract Syntax, Type Systems, Structural Operational Semantics (SOS), Denotational Semantics, and Axiomatic Semantics.

## 1. Abstract Syntax

The abstract syntax defines the essential structure of SmAuto programs, abstracting away from concrete parsing details.

### 1.1 Syntactic Domains

| Domain              | Symbol | Description                                       |
| :------------------ | :----- | :------------------------------------------------ |
| $\text{Model}$      | $M$    | The entire SmAuto model                           |
| $\text{Broker}$     | $B$    | Communication brokers (MQTT, AMQP, Redis)         |
| $\text{Entity}$     | $E$    | Smart entities (Sensors, Actuators)               |
| $\text{Automation}$ | $A$    | Automation rules                                  |
| $\text{Attribute}$  | $Attr$ | Entity attributes                                 |
| $\text{Type}$       | $\tau$ | Data types (int, float, bool, string, list, dict) |
| $\text{Value}$      | $v$    | Concrete values                                   |
| $\text{Expression}$ | $e$    | Expressions evaluating to values                  |
| $\text{Condition}$  | $C$    | Boolean expressions                               |
| $\text{Action}$     | $Act$  | State-changing operations                         |
| $\text{Identifier}$ | $x$    | Variable/Entity names                             |

### 1.2 Abstract Production Rules

$$
\begin{aligned}
M &::= \langle \mathcal{B}, \mathcal{E}, \mathcal{A} \rangle \\
\mathcal{B} &::= \{ B_1, \dots, B_n \} \\
\mathcal{E} &::= \{ E_1, \dots, E_m \} \\
\mathcal{A} &::= \{ A_1, \dots, A_k \} \\
\\
E &::= \text{Entity}(x, \tau_{entity}, B, \{Attr\}) \\
Attr &::= \text{Attribute}(x, \tau, v_{default}, \text{Gen}, \text{Noise}) \\
\\
A &::= \text{Automation}(x, C, \{Act\}, \text{enabled}, \text{continuous}, \text{freq}) \\
\\
C &::= C_1 \land C_2 \mid C_1 \lor C_2 \mid \neg C \\
  &\mid e_1 \ \text{op}_{rel} \ e_2 \mid e \in \text{Range}(n_1, n_2) \\
\\
e &::= v \mid x.a \mid \text{Math}(e_1, \text{op}_{math}, e_2) \mid \text{Agg}(x.a, \text{window}) \\
\text{Agg} &::= \text{mean} \mid \text{std} \mid \text{min} \mid \text{max} \\
\\
Act &::= x.a \leftarrow e
\end{aligned}
$$

## 2. Type System

The type system ensures that operations are performed on compatible types. We define a typing relation $\Gamma \vdash e : \tau$, where $\Gamma$ is the typing environment.

### 2.1 Types

$$ \tau ::= \text{int} \mid \text{float} \mid \text{bool} \mid \text{string} \mid \text{list}\langle\tau\rangle \mid \text{dict}\langle\tau, \tau\rangle \mid \text{time} $$

### 2.2 Typing Environment

$\Gamma$ maps identifiers (entities and their attributes) to types.
$$ \Gamma(E.a) = \tau $$

### 2.3 Typing Rules

**Literals:**
$$ \frac{}{\Gamma \vdash n : \text{int}} (n \in \mathbb{Z}) \quad \frac{}{\Gamma \vdash r : \text{float}} (r \in \mathbb{R}) \quad \frac{}{\Gamma \vdash b : \text{bool}} (b \in \{true, false\}) $$

**Attribute Access:**
$$ \frac{\Gamma(E) = \text{Entity} \quad (a : \tau) \in E.attributes}{\Gamma \vdash E.a : \tau} $$

**Arithmetic Operations:**
$$ \frac{\Gamma \vdash e_1 : \text{int} \quad \Gamma \vdash e_2 : \text{int}}{\Gamma \vdash e_1 + e_2 : \text{int}} \quad \frac{\Gamma \vdash e_1 : \text{float} \quad \Gamma \vdash e_2 : \text{float}}{\Gamma \vdash e_1 + e_2 : \text{float}} $$

**Comparison:**
$$ \frac{\Gamma \vdash e_1 : \tau \quad \Gamma \vdash e_2 : \tau \quad \tau \in \{\text{int}, \text{float}\}}{\Gamma \vdash e_1 < e_2 : \text{bool}} $$

**Action Validity:**
$$ \frac{\Gamma \vdash E.a : \tau \quad \Gamma \vdash e : \tau}{\Gamma \vdash (E.a \leftarrow e) : \text{Action}} $$

## 3. Structural Operational Semantics (SOS)

We define the semantics of SmAuto as a transition system. Since SmAuto is a reactive system interacting with a message broker, the state includes both the internal memory and the state of the broker (abstracted).

### 3.1 System Configuration

A configuration is a tuple $\langle \sigma, \mu \rangle$, where:
- $\sigma : \text{Entity} \times \text{Attribute} \to \text{Value}$ is the store (current values of all attributes).
- $\mu$ represents the message broker state (queue of pending messages).

### 3.2 Evaluation Relations

**Expressions:** $\langle e, \sigma \rangle \to v$

$$ \frac{\sigma(E.a) = v}{\langle E.a, \sigma \rangle \to v} $$

**Aggregations:** (Requires history $\mathcal{H}$)
$$ \frac{\mathcal{H}(E.a) = [v_1, \dots, v_n]}{\langle \text{mean}(E.a), \sigma, \mathcal{H} \rangle \to \frac{1}{n}\sum v_i} $$

### 3.3 Transition Rules

**Action Execution:**
Executing an action updates the local state and conceptually publishes a message.

$$ \frac{\langle e, \sigma \rangle \to v}{\langle E.a \leftarrow e, \sigma \rangle \xrightarrow{pub(E.a, v)} \sigma[E.a \mapsto v]} $$

**Automation Triggering:**
An automation $A$ fires if its condition $C$ evaluates to true.

$$ \frac{\langle C, \sigma \rangle \to true}{\langle \text{Automation}(C, \{Act_1, \dots, Act_n\}), \sigma \rangle \to \langle Act_1; \dots; Act_n, \sigma \rangle} $$

**Sequence:**
$$ \frac{\langle Act_1, \sigma \rangle \to \sigma' \quad \langle Act_2, \sigma' \rangle \to \sigma''}{\langle Act_1; Act_2, \sigma \rangle \to \sigma''} $$

**Global Step (Event Loop):**
The system evolves when new messages arrive (updating sensors) or when automations fire.

1.  **Sensor Update:**
    $$ \frac{\text{incoming}(E_{sensor}.a, v)}{\langle \sigma \rangle \xrightarrow{recv} \sigma[E_{sensor}.a \mapsto v]} $$

2.  **Automation Cycle:**
    $$ \frac{\forall A \in \mathcal{A}, \langle A, \sigma \rangle \to \sigma'}{\langle \sigma \rangle \xrightarrow{auto} \sigma'} $$

## 4. Denotational Semantics

For a reactive system, denotational semantics is best described using **Trace Semantics**.

### 4.1 Semantic Domains

- $\mathbb{V}$: Domain of values
- $\Sigma$: State space ($\text{Entity} \to \text{Attribute} \to \mathbb{V}$)
- $\mathcal{T}$: Domain of traces (sequences of states) $\Sigma^\infty$

### 4.2 Meaning Functions

The meaning of a Model $\mathcal{M}$ is a set of valid traces.

$$ \mathcal{M}[\![ M ]\!] \subseteq \Sigma^\infty $$

A trace $\tau = \sigma_0, \sigma_1, \dots$ is valid if for all $i$:
1.  $\sigma_{i+1}$ is reachable from $\sigma_i$ via sensor updates or automation executions.
2.  If $\exists A \in \mathcal{A}$ such that $\mathcal{C}[\![ A.condition ]\!](\sigma_i) = true$, then $\sigma_{i+1}$ must reflect the effects of $A.actions$.

**Continuous vs. One-shot:**
- If $A.continuous = true$: The automation fires in every state where $C$ holds.
- If $A.continuous = false$: The automation fires only when $C$ transitions from $false$ to $true$ (edge-triggered).

$$
\text{Trigger}(A, \sigma_i, \sigma_{i-1}) =
\begin{cases}
\mathcal{C}[\![ C ]\!](\sigma_i) & \text{if } A.continuous \\
\mathcal{C}[\![ C ]\!](\sigma_i) \land \neg \mathcal{C}[\![ C ]\!](\sigma_{i-1}) & \text{if } \neg A.continuous
\end{cases}
$$

## 5. Axiomatic Semantics & Hoare Logic

We extend Hoare Logic to reason about the correctness of automations.

### 5.1 Triples

$$ \{ P \} \ A \ \{ Q \} $$
"If property $P$ holds in the state before automation $A$ triggers, then $Q$ holds after $A$ executes."

### 5.2 Rules

**The Automation Rule:**

$$
\frac{\{ C \land P \} \ \text{Actions} \ \{ Q \} \quad \{ \neg C \land P \} \ \text{skip} \ \{ P \}}{\{ P \} \ \text{Automation}(C, \text{Actions}) \ \{ Q \lor P \}}
$$

This rule states that if the condition $C$ is met, the actions ensure $Q$. If not, the state remains $P$.

### 5.3 Safety Properties (Invariants)

To prove a safety property $I$ (e.g., "Temperature < 100"), we must show that all automations preserve $I$.

$$ \forall A \in \mathcal{A}, \ \{ I \} \ A \ \{ I \} $$

**Example Proof:**
Invariant $I \equiv \text{heater.on} \implies \text{temp} < 30$.
Automation:
```
Automation SafetyCutoff
    condition: temp >= 30
    actions: heater.on: false
end
```
Proof:
1.  **Case 1 ($C$ is true):** $\text{temp} \ge 30$.
    Action: $\text{heater.on} \leftarrow false$.
    Post-state: $\text{heater.on} = false$.
    Does $I$ hold? $false \implies \dots$ is always true. $\checkmark$

2.  **Case 2 ($C$ is false):** $\text{temp} < 30$.
    Action: skip.
    Post-state: $\text{temp} < 30$.
    Does $I$ hold? $\text{heater.on} \implies true$ is always true. $\checkmark$

Thus, the automation preserves the invariant.

## 6. Value Generators Semantics

Value generators produce streams of values for virtual entities.

$$ \mathcal{G} : \text{Generator} \to (\text{Time} \to \mathbb{V}) $$

- **Constant:** $\mathcal{G}[\![ \text{constant}(k) ]\!](t) = k$
- **Linear:** $\mathcal{G}[\![ \text{linear}(m, c) ]\!](t) = m \cdot t + c$
- **Gaussian:** $\mathcal{G}[\![ \text{gaussian}(\mu, \sigma) ]\!](t) \sim \mathcal{N}(\mu, \sigma)$ (Probabilistic)

The state of a virtual entity at time $t$ is determined by sampling the generator:
$$ \sigma_t(E.a) = \mathcal{G}[\![ E.a.generator ]\!](t) + \text{Noise}(t) $$