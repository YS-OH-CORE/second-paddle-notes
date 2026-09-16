# Reporting alphabets and random-bit budgets in a finite causal audit

**Review edition 0.1.0 | 16 September 2026**

Research direction and problem framing: **Youngseok Oh**. Mathematical development, exposition and computation: **Zero (ChatGPT), with substantial AI assistance**. This is author-produced, computer-assisted mathematics, not a peer-reviewed or proof-assistant-certified result.

## Abstract

We consolidate a sequence of working results into one self-contained finite example. A causal reader samples three of six binary positions and may corrupt one current bit. An adversary knows the reporting rule but not the reporter's fresh random bits. Deterministic reports require four symbols for uniformly consistent repeated discrimination. Binary reports require four fresh fair bits under a per-execution cap, but only **15/8 bits under a worst-input conditional expected-cost bound**, using early stopping. The expected-cost conclusion combines the finite channel obstruction with classical optimal Bernoulli sampling. It does not survive a change to amortized accounting: every positive uniform-prefix average permits sparse informative rounds, and a zero limiting average is possible. The example separates transmitted symbols, private random bits and the time denominator. It is not a theorem about natural-language memory size, nor a claim of historical priority.

## 1. Read or reproduce without the private archive

The entire public dependency set is this note and `verify.py`. Python 3.10 or newer and its standard library suffice:

```sh
python -B -S verify.py > actual.json
python -c "import json
a = json.load(open('actual.json'))
e = json.load(open('expected.json'))
assert a == e
print('Exact finite results match')"
```

The checker makes no network, model or file-write calls. The shell redirection above creates `actual.json`; choose an unused filename to avoid replacing your own file. `expected.json` is a saved output, **not an input used to construct the claimed law sets or inequalities**. No API key, private archive, cached source data, optimization solver or package installation is required. The finite computation is part of the obstruction proof; the all-history and unbounded-tree arguments below are analytic.

## 2. Experiment, scope and information order

Choose three ordered, distinct positions uniformly from six binary labels with $k$ ones. Under hypothesis $P$, $k\in\{0,1\}$; under hypothesis $Q$, $k\in\{5,6\}$. Counts 2 through 4 are outside the testing promise. At each of the three steps a reader observes the current **true bit prefix** and either returns it or, at most once in the block, flips the current bit. It cannot observe future bits or an extra position-identity channel. A policy may depend on the fixed count and past blocks. Its private randomization is a mixture of deterministic causal policies selected without future sample information.

Let $\mathcal P,\mathcal Q$ be the resulting convex hulls of laws on $\Omega=\{000,001,010,011,100,101,110,111\}$. All vectors below use this order. The uncorrupted $k=1$ probabilities are $(3,1,1,0,1,0,0,0)/6$; $k=5$ is their bitwise reflection. The checker reconstructs these from the 120 ordered samples, rather than loading them as a certificate. A causal trigger tree yields 676 deterministic policies and 67 distinct laws on either side. Convex hulls are finite and compact.

Before each new block the reporting map is chosen from the public history and disclosed to the adversary. The next raw law must belong to the appropriate hull **conditional on every past**. The one-flip allowance renews each block. A deterministic map sends one symbol. A stochastic binary map sends one bit $Z$, with $\Pr(Z=1\mid Y=y)=g(y)$, using only fresh independent private fair bits after receiving $Y$.

Only public reports carry new source-dependent information forward. Unreported raw data, random seeds, unused random bits and hidden local state are not retained. Message length, execution duration and consumed-bit counts are not additional channels. All past reports and the public round number may be retained; **there is no fixed-total-memory restriction**. These assumptions are essential, not implementation details.

Write

$$C(g)=\min_{p\in\mathcal P}E_p g,\qquad S(g)=\max_{q\in\mathcal Q}E_qg.$$

A positive gap $C(g)-S(g)$ provides repeated discrimination under the conditional law assumption. It is not an empirical accuracy or a complete error-rate curve.

## 3. Four deterministic symbols are necessary and sufficient

Let $L=\{000,001,010,100\}$ and $H=\Omega\setminus L$. Under the extreme counts, every point mass on $L$ is in $\mathcal P$ and every point mass on $H$ is in $\mathcal Q$. Consequently positive separation requires $\min_L g>\max_H g$.

**Lemma 1 (three-level obstruction).** If $g$ has at most three distinct levels then $C(g)\le S(g)$.

**Proof.** Under strict separation, one of the two sides must be constant. Suppose $g|_L=u$, and write $v=g(011),w=g(101)$. The following are legal laws:

$$
p_B=(0,0,3,2,0,1,0,0)/6,\quad
q_1=(0,2,1,3,0,0,0,0)/6,\quad
q_2=(0,1,0,0,2,3,0,0)/6.
$$

They are realized by flipping at the first trigger in $\{00,010,100\}$ under $k=1$, and in $\{1,01\}$ or $\{01,11,101\}$ under $k=5$. The code checks these realizations. Then

$$C(g)\le (3u+2v+w)/6=E_{(2q_1+q_2)/3}g\le S(g).$$

If $g|_H$ is constant, apply this argument to $1-g(\bar y)$; reflection preserves the gap. This contradicts strict separation. $\square$

For any deterministic map $f$ with at most three symbols, disjoint projected hulls would admit a strict separating linear score $t\circ f$ with at most three levels, contradicting Lemma 1. Thus legal laws with equal projected distributions exist. Choose such laws separately at each public history. Equality of every next-report conditional law gives equality of all finite report histories and hence the complete report process. Any common stopping and decision rule preserves that equality. An always-deciding test cannot guarantee both errors below $1/2$.

Four levels suffice via

$$g_4=(11,11,12,0,11,0,3,0)/12,\quad C(g_4)=1/2,\quad S(g_4)=35/72.$$

Transmit its level deterministically. Testing the average against $71/144$ gives each error at most $\exp(-n/10368)$ by the bounded conditional-moment bound. The checker verifies the extrema by policy enumeration and a separately expressed backward recursion. This proves the alphabet threshold; it does not claim an efficient practical sample size.

## 4. The finite obstruction for three fair bits

A binary reporter with a hard cap of $b$ fair bits has a table in $\mathcal D_b^8$, where $\mathcal D_b=\{j/2^b:0\le j\le2^b\}$. Pad shorter leaves to depth $b$ to see this.

**Lemma 2 (finite exact obstruction).** No table with a uniform integer denominator $D\le8$ strictly separates these hulls.

**Proof with exhaustive finite step.** Suppose its integer numerators are $z_y\in\{0,\ldots,D\}$. No $Q$ law puts mass on 000 and no $P$ law puts mass on 111. Increasing $z_0$ to 8 and decreasing $z_7$ to 0 cannot reduce a positive gap. Point masses require every low-weight coordinate to exceed every high-weight coordinate. Put $t=\max(z_3,z_5,z_6)$. It suffices to examine

$$z=(8,a,b,u,c,v,w,0),\quad \max(u,v,w)=t,\quad 0\le u,v,w\le t<a,b,c\le8.$$

There are exactly

$$\sum_{t=0}^7((t+1)^3-t^3)(8-t)^3=19188$$

vectors. For every vector, `grid_exclusion` computes the minimum safe dot product and maximum unsafe dot product over the regenerated integer law rows. The largest difference is **zero**; the sum of differences is **-3214440**, using rows of mass 120. No floating-point tolerance or solver is used. The proved reduction and complete enumeration establish the lemma. Complementing $g$ excludes separation in the reverse direction as well. $\square$

The safe and unsafe attainable Bernoulli-mean intervals therefore intersect for every three-bit map. The same history-by-history construction yields identical entire report laws, including for publicly adaptive maps.

Four fair bits suffice with

$$g_{16}=(16,12,16,1,15,0,4,0)/16,\quad C(g_{16})=49/96,\quad S(g_{16})=47/96.$$

For completeness, nine uniform tickets suffice via $(9,7,9,0,8,0,2,0)/9$, with extrema $13/27$ and $25/54$. Nine tickets are not nine fair bits. Lemma 2 proves that this ticket count is minimal under its uniform-ticket contract.

## 5. Sharp conditional mean cost: 15/8

For a local algorithm let $T(y)$ count consumed fair bits. The budget is

$$\max_y E[T(y)\mid h,Y=y]\le B\quad\text{at every public history }h.$$

Since the union of the hulls contains a point mass at each outcome, the maximum over input outcomes also equals the worst over permitted raw laws at a fixed history. It does not equal an unconditional time-average budget.

**Classical ingredient.** The least fair-bit expectation for a known exact Bernoulli probability $p$ is zero at 0 and 1; it is $2-2^{1-d}$ for a reduced dyadic denominator $2^d$; and it is two for a nondyadic probability when its digits are computable or supplied exactly. See Kozen [1], Theorem 6. This is existing sampling theory, not a new theorem of this note.

One can check the lower bound directly: the output-zero and output-one masses terminated by depth $t$ are multiples of $2^{-t}$. Their sum is at most

$$2^{-t}\bigl(\lfloor2^tp\rfloor+\lfloor2^t(1-p)\rfloor\bigr).$$

Whenever $2^tp$ is nonintegral at least $2^{-t}$ remains unresolved. Summing the tails and using the binary interval sampler yields the formula. For rational probabilities the implementation uses integer arithmetic.

Thus a per-input expected budget below $15/8$ allows only $\mathcal D_3$ probabilities. Lemma 2 and the common-report-law argument make uniform discrimination impossible, even for adaptive reporters with unbounded local stopping times. This is a statement about feasible channel laws: a needlessly slow implementation can be replaced by a shorter one without changing its report distribution, but its timing trace need not be preserved.

At $B=15/8$, sample $g_{16}$ by stopping once the binary comparison is decided. For the eight inputs its optimal conditional means are

$$ (0,3/2,0,15/8,15/8,0,3/2,0). $$

All executions finish within four bits. The checker runs all 128 input/tape pairs. For $m$ informative reports, majority has each error at most

$$\rho^m,\qquad \rho=2\sqrt{(49/96)(47/96)}=\sqrt{2303}/48<1.$$

For example, under $P$, conditionally $\Pr(Z_i=1)\ge49/96$. For $\lambda=\log(49/47)$, the conditional exponential moment of $-(Z_i-1/2)$ is at most $\rho$. Iteration and Markov's inequality give the bound; reflection handles $Q$. Independence of the raw blocks is not required. Therefore the **minimum conditional expected budget for uniformly consistent discrimination is exactly $15/8$**.

The earlier central table $(21,16,21,1,20,0,5,0)/21$ has gap $2/63$ and needs conditional expectation two at each nontrivial coordinate. Its larger gap means that saving local random bits does not necessarily save total observations or total randomness. No global cost-optimality is claimed for $g_{16}$.

## 6. Why amortization changes the conclusion

Now count all raw blocks in the denominator, including uninformative ones. On multiples of $K$, use $g_{16}$; elsewhere report a known constant. A deterministic schedule does not add a new information channel. The expected total random-bit cost through $N$ is at most

$$\frac{15}{8}\lfloor N/K\rfloor.$$

Hence any positive uniform-prefix expected average budget is achievable by choosing $K$ sufficiently large, while the number of informative blocks diverges and the errors tend to zero. A zero budget at every finite prefix would force no random-bit use almost surely and is impossible by the deterministic obstruction.

Under the weaker requirement of **zero limiting expected average**, use informative blocks at $1,4,9,16,\ldots$. The cost divided by $N$ is at most $15\lfloor\sqrt N\rfloor/(8N)\to0$, while the error bound is $\rho^{\lfloor\sqrt N\rfloor}\to0$.

This is not free information: total random bits and raw observations grow without bound. The result trades calendar rounds or acquired blocks for the accounting rate. If uninformative blocks are not allowed in the denominator, or a latency/error-rate requirement is fixed, it is a different optimization problem.

## 7. Verification, provenance and limitations

This edition integrates earlier author working notes on reporting resources and conditional expected randomness. It does not count those inherited numerical results as discoveries made during publication. The original drafts remain unchanged in their owner's archive. The new checker is a standalone consolidation; it shares the model and parts of the earlier algorithmic structure, so its two calculation paths are not independent research replications.

The claims are deliberately narrower than the full archive. We do **not** include the exact four/five-symbol margin curve, sequential optimality at a fixed error level, the separate finite-state-machine bounds, or language-model correction performance as results established by this package. Those require their own evidence and comparisons. This publication also does not resolve any incomplete Lean build.

The important assumptions are the sampled-bit-only reader, one causal corruption, per-history hull membership, public map selection, fresh private coins, no residual private state, and no timing channel. This note provides no empirical evidence that real AI agents obey those assumptions. The scientific use is a checkable example of why communication, randomness and cost-conditioning contracts must not be conflated.

## 8. Focused questions for a reviewer

1. Does the trigger-tree enumeration fully capture the explicitly specified reader, without adding future information or omitting a permitted observation?
2. Is the denominator-eight reduction exhaustive? A positive integer gap from a permitted row and table would overturn the associated lower bound.
3. Does the common-law construction respect the quantifier order when reporting maps depend on the public history?
4. Does the local expected-cost statement omit a permitted random seed, retained state or timing observation? Such a change would alter the model rather than be silently covered by the theorem.
5. Is this exact finite example already implied by, or present in, robust quantization or inspection-game literature? Identify a precise reduction, theorem or counterexample.

A report should give the Python version, commit/file identity, command, raw result or failing assertion, and the affected mathematical step. Passing the checker is not acceptance of novelty or of all analytic arguments. There is no independent review yet attached to this edition.

## References and comparison boundaries

[1] Dexter Kozen. *Optimal Coin Flipping*. LNCS 8464, 407-426, 2014. Theorem 6, printed p.424. DOI: 10.1007/978-3-319-06880-0_21. [Author manuscript](https://www.cs.cornell.edu/kozen/Papers/Coinflip.pdf). The fair-coin expectation formula above is explicitly attributed to this prior result; we restate the argument needed for the finite corollary.

[2] Yan Wang and Yajun Mei. *Asymptotic Optimality Theory for Decentralized Sequential Multihypothesis Testing Problems*, 2011. [Author manuscript](https://arxiv.org/abs/1011.0228). Quantization, memory, feedback and randomization visibility are established topics. This note is not claiming their introduction.

[3] Fernando G. S. L. Brandao, Aram W. Harrow, James R. Lee and Yuval Peres. *Adversarial Hypothesis Testing and a Quantum Stein's Lemma for Restricted Measurements*. [Author manuscript](https://arxiv.org/abs/1308.6702). History-adaptive testing is prior theory. Our elementary conditional-moment proof is included instead of requiring an unstated transfer from its general results.

[4] Eeshan Modak, Neha Sangwan, Mayank Bakshi, Bikash Kumar Dey and Vinod M. Prabhakaran. *Hypothesis Testing for Adversarial Channels: Chernoff-Stein Exponents*. [Author manuscript](https://arxiv.org/abs/2304.14166). Private and shared randomness already lead to distinct adversarial testing regimes. Its transmitter-before-channel formulation is not automatically the reporter-after-corruption formulation here; an exact reduction remains a review question.

The focused literature comparison is not an exhaustive priority audit. No new general sampling method, Blackwell theorem or universal AI-memory law is claimed.
