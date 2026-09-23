                                              Language Agent Tree Search Unifies Reasoning, Acting, and Planning in
                                                                       Language Models


                                                    Andy Zhou 1 2 Kai Yan 1 Michal Shlapentokh-Rothman 1 Haohan Wang 1 Yu-Xiong Wang 1


                                                                  Abstract
                                             While language models (LMs) have shown po-
arXiv:2310.04406v3 [cs.AI] 6 Jun 2024




                                             tential across a range of decision-making tasks,
                                             their reliance on simple acting processes limits
                                             their broad deployment as autonomous agents. In
                                             this paper, we introduce Language Agent Tree
                                             Search (LATS) – the first general framework that
                                             synergizes the capabilities of LMs in reasoning,
                                             acting, and planning. By leveraging the in-context
                                                                                                                 Figure 1. Overview of LATS. Serving as a unified framework,
                                             learning ability of LMs, we integrate Monte Carlo
                                                                                                                 LATS leverages an external environment and an MCTS-based
                                             Tree Search into LATS to enable LMs as agents,
                                                                                                                 search algorithm to improve reasoning and decision-making.
                                             along with LM-powered value functions and
                                             self-reflections for proficient exploration and en-                 and Jennings, 1995) have been of longstanding interest in
                                             hanced decision-making. A key feature of our ap-                    the field of artificial intelligence. While this has tradition-
                                             proach is the incorporation of an environment for                   ally been studied in reinforcement learning, the recent rise
                                             external feedback, which offers a more deliberate                   of language models (LMs) (Brown et al., 2020; Chowdh-
                                             and adaptive problem-solving mechanism that sur-                    ery et al., 2023; Touvron et al., 2023; OpenAI, 2023) with
                                             passes the constraints of existing techniques. Our                  strong reasoning and general adaptability offers an alter-
                                             experimental evaluation across diverse domains,                     native paradigm. Not only have LMs excelled in standard
                                             including programming, interactive question-                        natural language processing (NLP) tasks such as summariza-
                                             answering (QA), web navigation, and math, val-                      tion (Nallapati et al., 2016) and language inference (Bow-
                                             idates the effectiveness and generality of LATS                     man et al., 2015), but they have also been adapted to an
                                             in decision-making while maintaining compet-                        increasingly diverse set of tasks that often require advanced
                                             itive or improved reasoning performance. No-                        common-sense reasoning or quantitative skills (Cobbe et al.,
                                             tably, LATS achieves state-of-the-art pass@1 ac-                    2021; Saparov and He, 2023). In addition, LMs are capable
                                             curacy (92.7%) for programming on HumanEval                         of performing in complex environments that involve knowl-
                                             with GPT-4 and demonstrates gradient-free per-                      edge and reasoning, such as web navigation (Yao et al.,
                                             formance (average score of 75.9) comparable to                      2022; Deng et al., 2023), tool-use (Schick et al., 2023), and
                                             gradient-based fine-tuning for web navigation on                    open-ended games (Fan et al., 2022).
                                             WebShop with GPT-3.5. Code can be found                             Reasoning and acting abilities have been further improved
                                             at https://github.com/lapisrocks/                                   by prompting techniques that augment LMs with feedback
                                             LanguageAgentTreeSearch.                                            or observations from an external environment, as exempli-
                                                                                                                 fied by ReAct (Yao et al., 2023b) and other work (Gao et al.,
                                                                                                                 2023; Shinn et al., 2023). This eliminates the need to rely en-
                                        1. Introduction                                                          tirely on the base abilities of LMs, enhancing them through
                                        General autonomous agents capable of reasoning and                       external tools or semantic feedback. Despite such strengths,
                                        decision-making in a variety of environments (Wooldridge                 these methods are reflexive and fall short of humans’ deliber-
                                                                                                                 ate and thoughtful decision-making characteristics to solve
                                           1
                                             University of Illinois Urbana-Champaign. 2 Lapis Labs. Corre-       problems (Sloman, 1996; Evans, 2010). In particular, they
                                        spondence to: Andy Zhou <andyz3@illinois.edu>.                           fail to consider multiple reasoning paths or to plan ahead.
                                        Proceedings of the 41 st International Conference on Machine             Recent search-guided LM work (Xie et al., 2023; Yao et al.,
                                        Learning, Vienna, Austria. PMLR 235, 2024. Copyright 2024 by             2023a; Hao et al., 2023) addresses this issue by searching
                                        the author(s).                                                           over multiple reasoning chains. While enabling planning,

                                                                                                             1
                  Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

such methods operate in isolation, lacking the incorporation          2. Related Work
of external feedback that can improve reasoning.                      LMs for reasoning. For LMs, reasoning involves decom-
                                                                      posing complex inputs into sequential intermediate steps
To overcome these challenges, we propose Language Agent
                                                                      towards a final answer (Cobbe et al., 2021), demonstrated
Tree Search (LATS) – a unified framework for decision-
                                                                      with chain-of-thought (CoT) prompting (Wei et al., 2022)
making and reasoning with language models. As illustrated
                                                                      and its variants (Wei et al., 2022; Kojima et al., 2022; Wang
in Fig. 1, LATS synergizes LM reasoning, acting, and plan-
                                                                      et al., 2022). However, these methods, which create chains
ning strategies by expanding ReAct (Yao et al., 2023b) into a
                                                                      autoregressively in a single step, often suffer from error
search over a combinatorial space of possible reasoning and
                                                                      propagation as the number of steps increases (Guo et al.,
acting steps. This effort is nontrivial – adapting search algo-
                                                                      2018; Chen et al., 2023b), due to compound errors. Various
rithms to language agents and shifting from non-interactive
                                                                      advancements aim to mitigate this issue; some approaches,
tasks to interactive ones requires a substantial novel design
                                                                      such as self-consistency (Wang et al., 2022), employ ma-
on nodes, prompts, and search algorithms. In particular,
                                                                      jority voting over sampled chains, while others focus on
nodes and prompts must effectively store and retrieve ex-
                                                                      multi-step decomposition, such as least-to-most prompt-
ternal feedback, with the search algorithm incorporating
                                                                      ing (Zhou et al., 2022). Recently, CoT has been improved
this information into useful heuristics for value assignment.
                                                                      with search algorithms (Yao et al., 2023a; Hao et al., 2023;
Indeed, our empirical evaluation, as demonstrated on Hot-
                                                                      Besta et al., 2023) that can sample trajectories more effec-
PotQA (Yang et al., 2018) in Sec. 5.1, reveals that a simple
                                                                      tively. Tree-of-thought (ToT) prompting (Yao et al., 2023a)
combination of existing methods is inadequate, even failing
                                                                      uses DFS or BFS-based (depth/breadth-first) search guided
to surpass internal reasoning performance, despite having
                                                                      by an LM-generated heuristic, while reasoning via planning
access to the ground truth answer from the environment.
                                                                      (RAP) (Hao et al., 2023) uses MCTS with rollouts simu-
Our key insight underpinning LATS is adapting Monte Carlo             lated by LMs. However, they rely solely on LM internal
Tree Search (MCTS), inspired by its success in model-based            knowledge and cannot adapt to useful external feedback.
reinforcement learning (Silver et al., 2017) and the obser-           LMs for acting. The strong reasoning and common-sense
vation that many LM tasks allow reverting to earlier steps,           abilities of LMs have been further adapted for decision-
to language agents, repurposing pretrained LMs as agents              making or acting tasks as a policy model in interactive
with LM-powered value functions and self-reflections for              environments. In robotics, LMs have been employed as
cleverer exploration. Leveraging the general capabilities             high-level controllers of control policies (Ahn et al., 2022;
and in-context learning abilities of modern LMs, we use               Huang et al., 2022; Driess et al., 2023). Similar work (Baker
language as an interface between each component, allowing             et al., 2022; Wang et al., 2023) has also adapted LM agents
LATS to adapt planning to environmental conditions with-              to complex multimodal games such as Minecraft (Guss et al.,
out additional training. To the best of our knowledge, LATS           2019; Fan et al., 2022). LMs are particularly useful in text-
is the first framework that incorporates reasoning, acting,           based environments (Liu et al., 2018; Shridhar et al., 2020;
and planning to enhance LM performance. Notably, LATS                 Liu et al., 2024), where acting-based prompting techniques
doubles the performance of ReAct (Yao et al., 2023b) on               such as ReAct (Yao et al., 2023b) have seen success. Sim-
HotPotQA (Yang et al., 2018) and raises the average score             ilar to CoT, ReAct is limited by its simplicity and cannot
by 22.1 on WebShop (Yao et al., 2022) with GPT-3.5. When              effectively adapt to environment conditions. Many exten-
used with GPT-4, LATS achieves a 92.7 Pass@1 rate on                  sions have been proposed to address this issue, including
HumanEval (Chen et al., 2021), setting the state of the art.          self-refine (Madaan et al., 2023) and Reflexion (Shinn et al.,
                                                                      2023), which use self-improvement to enhance reasoning
Our contributions are the following: 1) We introduce LATS,
                                                                      and decision-making, and AdaPlanner (Sun et al., 2023),
a framework based on Monte Carlo Tree Search to construct
                                                                      which incorporates both positive and negative feedback.
the best trajectory from sampled actions, enabling more flex-
                                                                      However, these methods focus on refining an individual tra-
ible and adaptive problem-solving compared with reflexive
                                                                      jectory and do not consider alternative choices at each step.
prompting methods. 2) We propose a novel value function
                                                                      In addition, recent work (Huang et al., 2024) has suggested
that guides the search process and incorporates successful
                                                                      that LMs cannot self-correct their internal reasoning, mak-
heuristics such as self-refinement and self-consistency. 3)
                                                                      ing it critical to use external feedback. Alternatively, to pure
By integrating external feedback and self-reflection, LATS
                                                                      decision-making environments, the reasoning and practical
enhances model sensibility and enables agents to learn from
                                                                      abilities of LMs have been enhanced by providing access
experience, surpassing reasoning-based search methods.
                                                                      to external tools, such as APIs, search engines, calculators,
Through experiments across diverse domains, including pro-
                                                                      and other models (Schick et al., 2023; Shen et al., 2023;
gramming, interactive question-answering (QA), web navi-
                                                                      Surı́s et al., 2023). We summarize prior work in Tab. 1.
gation, and math, we demonstrate the versatility of LATS
for enhancing autonomous reasoning and decision-making.               Tree-based search. Tree-based search, where multiple

                                                                  2
                    Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

              Approach                                  Reasoning        Acting     Planning        Self-         External
                                                                                                  Reflection      Memory
              CoT (Wei et al., 2022)                         ✓              ×           ×              ×              ×
              ReAct (Yao et al., 2023b)                      ✓              ✓           ×              ×              ×
              ToT (Yao et al., 2023a)                        ✓              ×           ✓              ✓              ✓
              RAP (Hao et al., 2023)                         ✓              ×           ✓              ×              ✓
              Self-Refine (Madaan et al., 2023)              ✓              ×           ×              ✓              ×
              Beam Search (Xie et al., 2023)                 ✓              ×           ×              ✓              ×
              Reflexion (Shinn et al., 2023)                 ✓              ✓           ×              ✓              ✓
              LATS (Ours)                                    ✓              ✓           ✓              ✓              ✓

Table 1. Summary of related work on reasoning, acting, and planning. LATS is the first work incorporating designs from all three domains,
allowing broad applicability in all corresponding tasks. We refer to reasoning as LM internal reasoning, acting as external decision-making,
planning as the use of a search algorithm, self-reflection as the use of LM-generated feedback, and external memory as storing past text
context for future updates of the solution.

branches of outcomes are explored during search, is widely               The LM decodes text autoregressively, i.e., without other
used in many planning algorithms (Swiechowski et al., 2021;              inputs, the probability for an LM to generate a sequence y
                                                                                               Qlx
LaValle, 1998) and reinforcement learning (RL) (Hafner                   is given by pθ (x) = i=1     pθ (x[i]|x[1 . . . i − 1]). Usually,
et al., 2019; Du et al., 2023; Wu et al., 2023) algorithms for           to improve reasoning, prompts are provided along with the
its good exploration-exploitation trade-off. Note that though            input x, which are specific instructions or few-shot input-
tree-based search necessitates an environment model that                 output examples. We denote the generic process where an
can expand from an arbitrary state (Vodopivec et al., 2017),             input promptIO (x) is transformed into an output y by LM:
often requiring extra training in RL (Hafner et al., 2023),              y ∼ pθ (promptIO (x)).
such a problem does not exist for most LM tasks. This is
because we can conveniently revert to any state by setting               Chain-of-thought (CoT) prompting (Wei et al., 2022)
the input to be the context and the corresponding previous               caters to scenarios where the direct mapping from x to y is
output from the LM for many tasks. Thus, we operate on the               intricate, e.g., when x is from a mathematical query or chal-
tree-based framework and use MCTS (Swiechowski et al.,                   lenging question. It hinges on creating thoughts z1 , . . . , zl
2021) to fully unlock the potential of LMs. In addition, we              that act as stepping stones between x and y; each thought zi
avoid the cost of training a value function over language                is a language sequence. To employ CoT prompting, thoughts
descriptions by leveraging the in-context learning (Brown                are extracted sequentially as zi ∼ pCoT θ     (x, z1···i−1 ), with
et al., 2020) abilities of LMs. Concurrent work (Liu et al.,             the final output being y ∼ pCoT
                                                                                                       θ   (x, z1···l ).
2023) also explores combining search algorithms with LM                  Tree-of-thought (ToT) prompting (Yao et al., 2023a) ex-
agents but uses an off-the-shelf search algorithm, which                 tends CoT prompting by exploring multiple reasoning paths
may not be optimal for LMs. Finally, following Yao et al.                over thoughts. It frames problems as a search over a tree,
(2023a) and Hao et al. (2023), we note that we use planning              where each node s = [x, z1·i ] represents a partial solution
and search algorithms interchangeably in this paper.                     state comprising the original input x and the thought se-
                                                                         quence z1···i . Thoughts zi are generated by proposal or
3. Preliminaries                                                         sampling with CoT zi ∼ pCoT  θ   (x, z1···i−1 ). Search algo-
                                                                         rithms like depth-first (DFS) or breadth-first (BFS) search
3.1. Problem Setting and Prompting                                       are used to systematically explore the tree, guided by heuris-
                                                                         tics based on LM evaluations V (s) of each state.
We first define our problem and outline a few established
methods that leverage language models for reasoning or                   ReAct (Yao et al., 2023b) extends language models to
decision-making. In LM reasoning or decision making,                     tasks where the mapping from x to y is enhanced by or
we are given an input x in natural language and a pre-                   requires interactions with an external environment, such
trained language model pθ (x) parameterized by θ; our goal               as a game or API. This technique constructs an action
is to generate a final output y ∼ pθ (x) that corresponds                space Â = A ∪ Z that adds permissible actions a ∈ A
to the answer (reasoning) or completes the task (decision-               to the reasoning traces z ∈ Z from CoT. Observations o
making). Both x and y are language sequences, which are                  from the environment are used to improve both reasoning
comprised of a list of tokens (the basic elements of natural             and acting. To solve problems with ReAct, after each ob-
language, often words), denoted as x = (x[1], . . . , x[lx ])            servation, actions are generated from pθ sequentially as
and y = (y[1], . . . , y[ly ]) where lx and ly are the length.           ai ∼ pReAct
                                                                                θ     (x, o1···i−1 , a1···i−1 ), with the final output be-


                                                                     3
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

ing y ∼ pReAct
           θ     (x, o1···l , a1···l ). In this paper, consistent        any step by simply copy-pasting historical text input. Such
with other LM agent methods such as ReAct and Reflexion                  a special property is the key motivation of our work.
(Shinn et al., 2023), we focus on decision-making tasks
where reverting between iterations is feasible.                          4. Unifying Reasoning, Acting, and Planning
While the previously described prompting techniques im-
                                                                         4.1. LM Agent
prove LM performance on reasoning tasks, they falter on
difficult tasks that involve multifaceted decision-making                Depending on the base prompting framework design, LATS
due to several shortcomings: 1) Flexibility: Base prompting              supports sequential reasoning or decision-making tasks. At
designs (CoT or ReAct) autoregressively sample from the                  time step t, an agent receives an observation ot ∈ O from
LM, neglecting potential alternative continuations from spe-             the environment and takes an action at ∈ A following some
cific states. 2) Sensibility: Reasoning-based methods (CoT,              policy π(at |x, o1···t−1 , a1···t−1 ). We initialize the agent
RAP (Hao et al., 2023), or ToT) rely solely on the inter-                with pθ to leverage the useful language representations of
nal representations of the LM and cannot consider external               an LM as a base decision-maker. We follow the ReAct in-
observations. This dependency risks fact hallucination and               stantiation, in which the action space Â = A ∪ Z consists
error propagation while setting a performance ceiling. 3)                of both the space of permissible actions A and the language
Adaptability: Current planning strategies (RAP or ToT) use               space of reasoning traces Z. Actions directly affect the envi-
simple search algorithms such as BFS or cannot leverage                  ronment and result in observation, while thoughts are used
environmental feedback to improve planning. Additionally,                to formalize decisions by organizing information, planning
the agent is static and cannot reuse previous experience or              future actions, or injecting internal knowledge. The exact
learn from trial and error. While RAP also adopts MCTS, it               instantiation of the action space depends on the particular
is constrained to tasks where the LM can become a world                  environment – for decision-making tasks actions might con-
model and accurately predict states. These shortcomings                  sist of commands on a website, while for reasoning tasks
limit the ability of LMs to be deployed as general problem-              the action space might be limited to a few external tools or
solving agents and form the motivation for LATS.                         APIs. In environments without feedback, such as reasoning
                                                                         tasks, we use CoT as the base prompting framework.
3.2. Monte Carlo Tree Search (MCTS)
                                                                         Instead of greedily decoding one trajectory or solution, we
Monte Carlo Tree Search (MCTS) is a heuristic search al-                 sample n actions from pθ using the current state. This is
gorithm that is proved successful on many decision-making                based on the intuition that for complex decision-making
environments, such as Atari (Ye et al., 2021) and Go (Silver             tasks, there is likely to be a range of potential trajectories or
et al., 2016). MCTS builds a decision tree where every node              reasoning paths that are correct (Evans, 2010). Sampling a
in the tree is a state and edge is an action. MCTS runs for k            diverse set of candidates at each step mitigates the stochastic
episodes; for each episode, it starts from the root (i.e., initial       nature of LM text generation and enables greater exploration
state) and iteratively conducts two steps to expand the tree:            in both the decision-making and reasoning space. We wrap
1) Expansion, where multiple children states s are explored              pθ within our proposed search algorithm to deliberately
from the current parent state p by sampling n actions, and 2)            construct the best trajectory from sampled actions.
Selection, where the children with the highest UCT (Upper
Confidence bounds applied to Trees) (Kocsis and Szepesvári,             4.2. LATS
2006) value is selected for expansion by the next iteration.
                                                                         The main component of LATS is a search algorithm that
The UCT of a child state s is calculated as follows:
                                      s                                  controls the problem-solving process with planning. To find
                                          ln N (p)                       the most promising trajectory and systemically balance ex-
               U CT (s) = V (s) + w                ,          (1)
                                           N (s)                         ploration with exploitation, we adopt a variant of MCTS that
where N (s) is the number of visits to a node s, V (s) is the            frames decision-making as a tree search, in which each node
value function (expected return) from the subtree of s, w is             s = [x, a1···i , o1···i ] represents a state comprising the origi-
the exploration weight, and p is the parent node of s. When              nal input x, action sequence a1·i , and observation sequence
the end of an episode is reached, a backpropagation is car-              o1·i , where i is a token in the text sequence.
ried out: the return r is used for updating every V (s) along            Our main technical contribution is adapting MCTS to lan-
the path with the formula V (s) = Vold (s)(N (s)−1)+r
                                           N (s)      , where            guage agents. LATS repurposes pθ as an agent, state evalua-
Vold (s) is the old value function. Normally, the major short-           tor, and feedback generator, leveraging the useful language
coming of MCTS is that it requires an environment model to               representations of modern LMs to facilitate planning. While
undo previous steps and form a searching tree, which could               standard MCTS and RAP (Hao et al., 2023) rely on internal
be a strong assumption. However, this limitation does not                dynamics models to facilitate simulation, LATS uses envi-
exist for many LM tasks, as we can conveniently reset to                 ronment interaction and does not require a world model. As

                                                                     4
                    Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models




Figure 2. Overview of the six operations in LATS. A node is selected, expanded, evaluated, then simulated until a terminal node is reached,
and then the resulting value is backpropagated. If the trajectory fails, a reflection is generated and used as additional context for future
trials. These operations are performed in succession until the budget is reached or the task is successful.

depicted in Fig. 2, LATS consists of a series of operations               as it is difficult for LMs to improve their responses with-
– selection, expansion, evaluation, simulation, backpropa-                out external feedback (Huang et al., 2024). Additionally,
gation, and reflection – performed in succession until the                to further improve value assignment, we introduce an ad-
task is successfully completed or a computational limit is                ditional heuristic based on self-consistency (Wang et al.,
reached after sampling k trajectories. The full pseudocode                2022), in which actions sampled multiple times at the same
of LATS can be found in Sec. A in the Appendix.                           state tend to be more accurate. This results in the overall
                                                                          value function:
Selection. In the first operation, the algorithm identifies
a segment of the current tree most suitable for subsequent                             V (s) = λ ∗ LM(s) + (1 − λ) ∗ SC(s),                (2)
expansion. Starting from the root node, denoted as the initial            where λ is a hyperparameter. Notably, our method offers
state s0 , a child node is selected at each tree level until a leaf       enhanced flexibility over programmed heuristics (Campbell
node is reached. To balance exploration and exploitation,                 et al., 2002) and greater efficiency than learned heuristics
we use the UCT algorithm as shown in Eq. 1.                               (Silver et al., 2017).
Expansion. After selecting a node, the second operation                   Simulation. The fourth operation expands the currently se-
expands the tree by sampling n actions from pθ , as described             lected node until a terminal state is reached. At each depth
in the prior section. The environment receives each action                level, we sample and evaluate nodes with the same opera-
and returns corresponding feedback as an observation. This                tions but prioritize nodes of the highest value. Reaching a
results in n new child nodes added to the tree. This tree is              terminal state provides objective feedback on the correct-
stored in an external long-term memory structure.                         ness of a trajectory. If the task is completed successfully,
                                                                          then LATS terminates the search. If the solution is partially
Evaluation. The third operation assigns a scalar value to                 successful or unsuccessful, then we perform two additional
each new child node for selection and backpropagation.                    operations as described below. The success of a trajectory is
This value effectively quantifies the agent’s progress in task            determined by the design of the specific environment, such
completion, serving as a heuristic to steer the search algo-              as finalizing a purchase in web navigation environments.
rithm towards the most promising regions of the tree. As
LATS does not involve training, we propose a novel value                  Backpropagation. This operation updates the values of the
function for this setting based on two components: (1) a                  tree based on the outcome of a trajectory. For each node
self-generated LM score and (2) a self-consistency score.                 s0 , s1 , . . . , sl in the trajectory from root (initial state s0 )
                                                                          of the searching tree to leaf (terminal state sl ), its value is
Inspired by ToT, we repurpose pθ into a value function by                 updated to reflect the outcome of the simulation by N (si ) =
prompting it to reason about a given state. To obtain a scalar            N (si−1 ) + 1 and V (si ) = V (si−1N)N(s(si )i−1 )+r , where r is the
value, we instruct pθ to end its reasoning trace with a score
                                                                          reward. These updated values are used in the UCT formula
indicating the correctness of the trajectory. Our key distinc-
                                                                          (Eq. 1) to guide the selection of the next node.
tion from ToT is that we obtain this value after obtaining
the environmental feedback, improving value assignment.                   Reflection. In addition to the environmental feedback, we
This also enables scaling to more challenging environments,               leverage self-reflection to further refine the decision-making

                                                                      5
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

      Prompt Method                  HotpotQA (EM) ↑                        Prompt Method                    HotpotQA (EM) ↑
      Base LM                              0.32                             ReAct (Yao et al., 2023b)              0.32
      CoT (Wei et al., 2022)               0.34                             ReAct (best of k)                      0.38
      CoT - SC (Wang et al., 2022)         0.38                             Reflexion (Shinn et al., 2023)         0.51
      ToT (Yao et al., 2023a)              0.55                             ToT (ReAct)                            0.39
      RAP (Hao et al., 2023)               0.60                             RAP (ReAct)                            0.54
      RAP (n = 10)                         0.60                             LATS (ReAct)                           0.63
      LATS (CoT)                           0.62                             LATS (n = 3)                           0.58
                                                                            LATS (n = 10)                          0.65
Table 2. GPT-3.5 reasoning-based prompting results on HotpotQA.             LATS (CoT + ReAct)                     0.71
LATS achieves the highest exact match (EM) for reasoning. We
sample n = 5 nodes during expansion and k = 50 trajectories.          Table 3. GPT-3.5 acting-based prompting results on HotpotQA.
                                                                      LATS achieves the highest exact match (EM) for acting. We
                                                                      sample n = 5 nodes and use k = 50 trajectories. We also evaluate
                                                                      sampling ReAct k times and using both CoT and ReAct base
                                                                      prompting designs for LATS, which achieves the best performance.
                                                                      Note that LATS outperforms ToT and RAP with ReAct prompting,
                                                                      which are the simple adaptations of search algorithms to decision-
process (Shinn et al., 2023; Madaan et al., 2023). Upon               making.
encountering an unsuccessful terminal node, pθ is prompted
with the trajectory and final reward to provide a verbal self-
reflection that summarizes the errors in the reasoning or
                                                                      5.1. HotPotQA
acting process and proposes superior alternatives. We store
both failed trajectories and corresponding reflections in the         For a task that can be approached with both reasoning-based
memory. In subsequent iterations, these are integrated as             and acting-based strategies, we consider HotPotQA (Yang
additional context to the agent and value function, refining          et al., 2018), a multi-hop question-answering benchmark
both through in-context learning. This imparts a semantic             that requires retrieval over two or more Wikipedia passages.
gradient signal more useful than a scalar value, enabling             For the action space, in addition to LM thoughts, we follow
the agent to learn from trial and error without the cost of           the setup from Yao et al. (2023b), which provides the agent
expensive optimization such as reinforcement learning.                with API calls to search and retrieve information. The output
                                                                      of these API calls and self-generated reflections form the
Discussion. Conceptually, LATS has several notable advan-
                                                                      observation space. Note that consistent with previous work
tages as a general framework for reasoning and decision-
                                                                      (Yao et al., 2023b; Shinn et al., 2023), we use an oracle
making with LM agents. (1) Generality: LATS supports
                                                                      setup for HotPotQA, in which the environment provides
both reasoning and decision-making tasks by defining a
                                                                      feedback about the answer’s correctness upon receiving an
shared space of thoughts and actions. (2) Deliberation:
                                                                      answer. This enables a fair comparison between our method
Leveraging MCTS and LM value function in LATS en-
                                                                      and baselines in scenarios where the quality of feedback is
sures a principled search that selects options with high value
                                                                      high, allowing us to focus our evaluation on how well the
while exploring promising alternatives. (3) Adaptability:
                                                                      agent incorporates external feedback. We use a subset of
Incorporating external feedback through observations and
                                                                      100 questions and three few-shot examples for each method.
self-reflection in LATS enables greater adaptation during
                                                                      For ToT, we use DFS as the base search algorithm. For all
problem-solving. (4) Flexibility: LATS can accommodate
                                                                      methods that involve sampling, including LATS, we sample
different scenarios, environments, and resource stipulations
                                                                      k = 50 trajectories. More details are in Appendix Sec. D.
by modifying state design and tree dimensions. (5) Modu-
larity: The base LM agent, reflection generator, and value            We evaluate internal reasoning strategies by removing ac-
function can be independently altered and adapted to indi-            tions and observations from the context, corresponding to
vidual LM properties.                                                 CoT (Wei et al., 2022) and its variants, CoT-SC (Wang et al.,
                                                                      2022), ToT (Yao et al., 2023a), and RAP (Hao et al., 2023).
5. Experiments                                                        These methods rely solely on the agent’s existing knowledge
                                                                      to answer the question. We further consider acting-based
To demonstrate the general applicability of LATS, we eval-            methods ReAct, Reflexion, and LATS, which augment the
uate our method on a variety of domains that require rea-             agent with the interactive API environment and primarily
soning and acting: programming (Chen et al., 2021; Austin             evaluate its information retrieval abilities. We also design
et al., 2022), HotPotQA (Yang et al., 2018), WebShop (Yao             a simple integration of search algorithms with LM agents,
et al., 2022), and Game of 24 (Yao et al., 2023a).                    extending ToT and RAP with ReAct prompting to handle

                                                                  6
                    Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

     Prompt Method                    Model     Pass@1 ↑                        Prompt Method                    Pass@1 ↑
     CoT (Wei et al., 2022)           GPT-3.5     46.9                          CoT (Wei et al., 2022)             54.9
     ReAct (Yao et al., 2023b)        GPT-3.5     56.9                          ReAct (Wei et al., 2022)           67.0
     Reflexion (Shinn et al., 2023)   GPT-3.5     68.1                          Reflexion (Shinn et al., 2023)     70.0
     ToT (Yao et al., 2023a)          GPT-3.5     54.4                          ToT (Yao et al., 2023a)            65.8
     RAP (Hao et al., 2023)           GPT-3.5     63.1                          RAP (Hao et al., 2023)             71.4
     LATS (ReAct)                     GPT-3.5     83.8                          LATS (ReAct)                       81.1
     Base LM                          GPT-4       80.1
                                                                     Table 5. GPT-3.5 Pass@1 accuracy on MBPP. Prompting with
     Reflexion                        GPT-4       91.0
                                                                     LATS achieves the highest performance. We sample 5 solutions
     LATS (ReAct)                     GPT-4       92.7               during expansion for 8 iterations.

Table 4. GPT-3.5 and GPT-4 Pass@1 accuracy on HumanEval.
Prompting with LATS achieves the best performance. We sample
5 solutions during expansion for 8 iterations.

                                                                     5.2. Programming
                                                                     To demonstrate the importance of external observations
                                                                     for complex reasoning tasks, we evaluate the baselines
external observations. In addition, while LATS is designed           and LATS on programming with HumanEval (Chen et al.,
for scenarios where external feedback can enhance reason-            2021)1 and MBPP (Austin et al., 2022). Both datasets mea-
ing, we also implement a reasoning-only version with CoT             sure the correctness of synthesized programs in Python from
as the base prompting framework. Moreover, we combine                natural language docstrings. We use individual solutions
internal and external reasoning in LATS by first prompting           as the action space and test suite and compiler feedback as
with a CoT-based prompt and then switching to a ReAct-               the external observation. We follow Chen et al. (2023a) and
based prompt upon failure. This is closer to how humans              use an LM to generate a synthetic test suite of syntactically
might approach this task by using tools to retrieve additional       valid “assert” statements for each question. For each step,
information only when the answer is not already known.               the solution is evaluated on this test suite, and the results,
Results. We observe in Tab. 2 and Tab. 3 that both in-               including successful and failed tests and compiler output,
ternal reasoning and external retrieval strategies perform           are added to the context as an observation.
well on HotPotQA. Due to their large-scale training corpus,          For this task, the reasoning and acting baselines share an
modern LMs already encode factual knowledge and can                  action space, but acting methods are able to incorporate
often directly answer the question correctly. While CoT can          observations as additional context. For LATS, since each
slightly enhance performance on questions requiring rea-             action corresponds to a complete solution, we skip the sim-
soning, larger gains are observed with search methods ToT            ulation step of LATS and directly use the percentage of
and RAP (Tab. 2, Row 4, 5), which can sample and explore             passed tests as the backpropagated reward. We use k = 8
more outputs. We observe similar results for acting-based            iterations, set the number of generated tests at 4, and sam-
methods. LATS surpasses ReAct, even when sampling the                ple n = 5 solutions during expansion. After the search is
same number of trajectories, by expanding more nodes with            completed, we select the solution with the highest value and
principled search. This is demonstrated when modifying               evaluate it on the real test suite for the pass@1 accuracy
n, the number of nodes expanded during each iteration. In-           evaluation. More details can be found in Appendix Sec. D.
creasing n can consistently improve performance, although
at greater computational and inference costs. LATS also              Results. Tab. 4 and Tab. 5 show that both search and seman-
outperforms RAP on internal reasoning, but has higher per-           tic feedback are crucial for better performance. Despite not
formance on the decision-making setting of HotPotQA than             using observations, ToT and RAP are competitive with Re-
the reasoning setting. Contrary to LATS, the ReAct versions          flexion. LATS has the highest performance on both datasets.
of ToT and RAP (Tab. 3, Row 4, 5) perform even worse than            RAP uses a search algorithm similar to LATS, which reveals
the reasoning-only setting of HotPotQA, which indicates              the importance of external feedback for difficult reasoning
that the acting-based setting is more challenging and adap-          tasks such as programming. With GPT-4, using LATS sets
tation of search algorithms to decision-making scenarios             the state of the art for HumanEval, validating that LATS can
is non-trivial. Combining internal and external reasoning            be used with more advanced LMs for higher performance.
in LATS results in the highest performance, indicating the              1
                                                                          Some baselines use 161 questions from HumanEval. We
importance of external feedback in augmenting reasoning              use all 164 questions for LATS and find minimal performance
even in tasks where the base LM can already perform.                 differences, so we report baselines for both settings.

                                                                 7
                    Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

                  Method                   Score ↑   SR ↑             Prompt Method                    Game of 24 (Success Rate) ↑
         ReAct (Yao et al., 2023b)          53.8     28.0             CoT (Wei et al., 2022)                      0.08
           ReAct (best of k)                59.1     32.0             Reflexion (Shinn et al., 2023)              0.12
        Reflexion (Shinn et al., 2023)      64.2     35.0             ToT (Yao et al., 2023a)                     0.20
             LATS (ReAct)                   75.9     38.0             RAP (Hao et al., 2023)                      0.40
                                                                      LATS (CoT)                                  0.44
             IL (Yao et al., 2022)          59.9     29.1
          IL+RL (Yao et al., 2022)          62.4     28.7
                                                                     Table 7. Results on Game of 24 with GPT-3.5. We sample n = 5
       Fine-tuning (Furuta et al., 2024)    67.5     45.0
                                                                     nodes and k = 30 trajectories.
                   Expert                   82.1     59.6
                                                                           Prompt Method                    HotPotQA (EM) ↑
Table 6. Score and success rate (SR) on WebShop. Results are
organized into prompting, RL-based training, and human perfor-             ToT (ReAct)                            0.39
mance. For the same number of iterations, LATS improves both               RAP (ReAct)                            0.54
score and SR and surpasses RL-based training.                              LATS (No LM Heuristic)                 0.37
                                                                           LATS (DFS)                             0.42
                                                                           LATS (No Reflection)                   0.58
5.3. WebShop                                                               LATS (ReAct)                           0.63

For a complex decision-making environment with practi-               Table 8. Ablation results on LATS and baseline variants in Hot-
cal applications, we consider WebShop (Yao et al., 2022),            PotQA. We use ReAct as the base prompt and sample n = 5
an online shopping environment composed of a website                 children and k = 50 trajectories. LATS requires every component
with 1.18M real-world products and 12k human instructions.           and operation for optimal performance.
Agents must navigate a website through a variety of com-
mands to purchase an item matching a user specification.
We use the preconstructed action space of search and click           shown in Tab. 8). More ablations for token consumption on
commands and browser feedback and reflections for the                HotPotQA are in Tab. 9 in Appendix Sec. C.
observation. The performance is gauged using two metrics:            Reasoning on Game of 24. To show how LATS can be
an average score, reflecting the percentage of user-specified        applied to purely internal reasoning tasks, we additionally
attributes met by the selected product, and a success rate,          evaluate on Game of 24 (Yao et al., 2023a), a mathematical
indicating the frequency with which the chosen product ful-          reasoning task where the agent must construct 24 out of a
fills all given conditions. We compare against acting-based          set of numbers and basic operations. We use CoT as the
prompting methods and RL-based approaches. We evaluate               base prompting design and employ the same operations as
on 50 instructions, expand n = 5 children for LATS, and set          in other settings. We find in Tab. 7 that LATS outperforms
k = 30 for LATS, ReAct (best of k), and Reflexion. More              previous methods proposed specifically for reasoning. This
details and prompts are in Appendix Sec. D and Sec. G.               is due to our proposed value function, which incorporates
Results. We find in Tab. 6 that GPT-3.5 with ReAct is                self-consistency as an additional heuristic.
competitive to imitation learning (IL) and can exceed re-            Self-reflection. LATS uses self-reflection to provide addi-
inforcement learning techniques with stronger prompting              tional semantic signals for the agent. In Tab. 8 (Row 5, 6),
strategies. Sampling k = 30 trajectories with ReAct and              we observe a 0.05 performance drop when self-reflection
Reflexion results in a similar performance, suggesting the se-       is removed from LATS, validating its usefulness. This is a
mantic feedback is not as helpful in complex environments            smaller gain than the 0.19 gain that Reflexion has over Re-
like WebShop. Similar to Shinn et al. (2023), we find that           Act as shown in Tab. 3, suggesting overlap between the ques-
generated reflections are often generic and do not provide           tions where an answer can be improved by self-reflection
useful feedback, resulting in a tendency for the agent to            and search. This variant outperforms RAP (ReAct), reflect-
become stuck in local minima. However, using LATS in-                ing our improvements to MCTS.
deed results in a noticeable improvement, indicating a more
effective exploration for the same number of iterations.             Search algorithm. MCTS is a more principled search algo-
                                                                     rithm than variants like A* (Zhuang et al., 2023) or DFS and
                                                                     is the basis for observed performance gains. We observe
5.4. Ablation Study and Additional Analysis
                                                                     the effects of using DFS, and incorporate the LM-based
We further test the reasoning ability of LATS on Game of 24,         heuristic used in ToT in which branches with low values are
and also conduct additional experiments on HotPotQA to               pruned. This removes the selection and backpropagation
demonstrate the effect of each component of LATS (results            operations, and we observe a 0.21 drop in performance in

                                                                 8
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

                           Method                 Performance ↑       Sample complexity ↓   Token Consumption ↓
                    ReAct (Best k = 250)               0.42                  O(k)                    -
                   CoT-SC (n = 1, k = 250)             0.40                  O(k)                    -
                    LATS (n = 1, k = 50)               0.48                  O(k)                    -
                  ToT (ReAct, n = 5, k = 50)           0.49                 O(kn)                 210, 215
                  RAP (ReAct, n = 5, k = 50)           0.54                 O(kn)                 176, 500
                    LATS (n = 5, k = 50)               0.63                 O(kn)                 173, 290

Table 9. Performance, sample complexity of different methods, average number of nodes expanded, and token consumption upon success
by methods with tree-based search. n is the number of children nodes expanded at every step and k is the number of trajectories. LATS
has the same sample complexity as other methods with tree-based search and expands less nodes upon success, which indicates lower
token cost.


       Method       k    HotPotQA ↑       # of Nodes ↓                RAP and 12.12 fewer nodes than ToT. These findings un-
                                                                      derscore our improvements to MCTS and adaptation to LM
       ToT         10        0.34             33.97                   agents, resulting in a more principled and efficient search
       RAP         10        0.44             31.53                   mechanism.
       LATS        10        0.44             28.42
       ToT         30        0.39             47.54
                                                                      6. Conclusion
       RAP         30        0.50             37.71
       LATS        30        0.52             34.12                   This work introduces Language Agent Tree Search (LATS),
       ToT         50        0.49             84.05                   the first framework to unify reasoning, acting, and plan-
       RAP         50        0.54             70.60                   ning for enhanced LM problem-solving. LATS addresses
       LATS        50        0.61             66.65                   key limitations of prior prompting techniques by deliber-
                                                                      ately constructing trajectories with search algorithms, in-
Table 10. Comparison of the cost of different methods on Hot-         corporating external feedback, and enabling agents to learn
PotQA. LATS achieves the highest accuracy and the lowest av-          from experience. Our evaluation demonstrates the ability
erage number of nodes/states required for success at various k        of LATS to harness LM capabilities for various decision-
trajectories sampled.                                                 making tasks while maintaining its reasoning ability without
                                                                      additional training. The proposed synergies between search,
Tab. 8 (Row 4) when sampling the same number of nodes                 interaction, and reflection offer a versatile approach to au-
but outperforms ToT (ReAct). Despite also benefiting from             tonomous decision-making, highlighting the potential of
ground-truth feedback, LATS uses it better than ToT and               LMs as generalist agents.
RAP and can outperform these methods. We also find in
                                                                      Limitations and future directions. LATS has two main
Tab. 8 (Row 3) that LM scoring, the main component of our
                                                                      limitations that should be considered before its application.
value function, is crucial for leveraging external feedback
                                                                      First, it has a higher computational cost compared to simpler
and strong performance.
                                                                      prompting methods like ReAct or Reflexion, which may
Sample complexity and token consumption. One pos-                     limit its practicality in certain situations. Second, LATS
sible concern of LATS is that the tree-structured search              assumes the ability to revert to earlier states in decision-
might consume much more tokens than existing methods.                 making environments, which may not be universally ap-
To further study the computational cost of LATS compared              plicable in all possible environments. Despite these limi-
to prior methods, we examine the sample complexity (i.e.,             tations, it is worth noting that LATS still achieves better
asymptotic token cost) of all methods considered in this              performance and efficiency compared to similar methods,
paper and count the average number of nodes expanded                  and the number of nodes expanded at each step provides a
by our method and other tree-structured methods (ToT and              trade-off between performance and efficiency. Additionally,
RAP) upon successful search on HotPotQA. We present the               we expect inference-time compute costs to decrease over
results in Tab. 9 and Tab. 10, which show that our method             time, thereby increasing the usefulness of LATS and other
has the same sample complexity as other tree-based search             “System-2” LM approaches. Finally, the reversion prop-
methods and requires fewer overall tokens and states. The             erty is feasible in many real-world applications, opening up
token cost gap will be even larger when taking failed trajec-         new opportunities in the LM decision-making community.
tories into account, since our method has a higher success            Future directions include scaling LATS to more complex
rate and reaches the computational budget limit less often.           environments or multi-agent frameworks and improving ef-
This is also true when sampling a smaller number of trajec-           ficiency to reduce costs. A more detailed discussion about
tories; on average, LATS requires 3.55 fewer nodes than               the limitations of LATS can be found in Appendix Sec. B.

                                                                  9
                 Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

Impact Statement                                                       stenberger, Lukas Gianinazzi, Joanna Gajda, Tomasz
                                                                       Lehmann, Michal Podstawski, Hubert Niewiadomski, Pi-
LATS is a framework that enhances LM performance                       otr Nyczyk, and Torsten Hoefler. Graph of thoughts:
through interactions with an environment. This improve-                Solving elaborate problems with large language models.
ment in autonomous decision-making may facilitate harm-                arXiv:2308.09687, 2023.
ful uses of LMs. On the other hand, LATS enhances in-
terpretability and the potential for greater alignment, as it        Samuel R Bowman, Gabor Angeli, Christopher Potts, and
involves high-level linguistic reasoning and actions through           Christopher D Manning. A large annotated corpus for
several rounds of decision-making and reflection rather than           learning natural language inference. In EMNLP, 2015.
relying on autoregressive generation. Finally, enhancing the
capabilities of LM agents may raise security risks, such as          Tom B. Brown, Benjamin Mann, Nick Ryder, Melanie
executing malware. We encourage further research to fully              Subbiah, Jared Kaplan, Prafulla Dhariwal, Arvind Nee-
understand and mitigate the risks of LMs.                              lakantan, Pranav Shyam, Girish Sastry, Amanda Askell,
                                                                       Sandhini Agarwal, Ariel Herbert-Voss, Gretchen Krueger,
                                                                       Tom Henighan, Rewon Child, Aditya Ramesh, Daniel M.
Acknowledgements                                                       Ziegler, Jeffrey Wu, Clemens Winter, Christopher Hesse,
We thank Daniel Campos for useful feedback on earlier ver-             Mark Chen, Eric Sigler, Mateusz Litwin, Scott Gray,
sions of this paper. This work was supported in part by NSF            Benjamin Chess, Jack Clark, Christopher Berner, Sam
Grant 2106825, NIFA Award 2020-67021-32799, the Jump                   McCandlish, Alec Radford, Ilya Sutskever, and Dario
ARCHES endowment through the Health Care Engineering                   Amodei. Language models are few-shot learners. In
Systems Center at Illinois and the OSF Foundation, and the             NeurIPS, 2020.
IBM-Illinois Discovery Accelerator Institute. This work              Murray Campbell, A Joseph Hoane Jr, and Feng-hsiung
used NVIDIA GPUs at NCSA Delta through allocations                    Hsu. Deep blue. Artificial intelligence, 2002.
CIS220014, CIS230012, and CIS230218 from the ACCESS
program.                                                             Bei Chen, Fengji Zhang, Anh Nguyen, Daoguang Zan, Zeqi
                                                                       Lin, Jian-Guang Lou, and Weizhu Chen. CodeT: Code
                                                                       generation with generated tests. In ICLR, 2023a.
References
Michael Ahn, Anthony Brohan, Noah Brown, Yevgen Cheb-                Mark Chen, Jerry Tworek, Heewoo Jun, Qiming Yuan,
 otar, Omar Cortes, Byron David, Chelsea Finn, Chuyuan                Henrique Ponde, Jared Kaplan, Harrison Edwards, Yura
 Fu, Keerthana Gopalakrishnan, Karol Hausman, Alex                    Burda, Nicholas Joseph, Greg Brockman, Alex Ray,
 Herzog, Daniel Ho, Jasmine Hsu, Julian Ibarz, Brian                  Raul Puri, Gretchen Krueger, Michael Petrov, Heidy
 Ichter, Alex Irpan, Eric Jang, Rosario Jauregui Ruano,               Khlaaf, Girish Sastry, Pamela Mishkin, Brooke Chan,
 Kyle Jeffrey, Sally Jesmonth, Nikhil J Joshi, Ryan Julian,           Scott Gray, Nick Ryder, Mikhail Pavlov, Alethea Power,
 Dmitry Kalashnikov, Yuheng Kuang, Kuang-Huei Lee,                    Lukasz Kaiser, Mohammad Bavarian, Clemens Winter,
 Sergey Levine, Yao Lu, Linda Luu, Carolina Parada, Peter             Philippe Tillet, Felipe Petroski Such, David W. Cum-
 Pastor, Jornell Quiambao, Kanishka Rao, Jarek Retting-               mings, Matthias Plappert, Fotios Chantzis, Elizabeth
 house, Diego Reyes, Pierre Sermanet, Nicolas Sievers,                Barnes, Ariel Herbert-Voss, William H. Guss, Alex
 Clayton Tan, Alexander Toshev, Vincent Vanhoucke, Fei                Nichol, Igor Babuschkin, Suchir Balaji, Shantanu Jain,
 Xia, Ted Xiao, Peng Xu, Sichun Xu, Mengyuan Yan, and                 Andrew Carr, Jan Leike, Joshua Achiam, Vedant Misra,
 Andy Zeng. Do as I can, not as I say: Grounding language             Evan Morikawa, Alec Radford, Matthew M. Knight,
 in robotic affordances. In CoRL, 2022.                               Miles Brundage, Mira Murati, Katie Mayer, Peter Welin-
                                                                      der, Bob McGrew, Dario Amodei, Sam McCandlish, Ilya
Jacob Austin, Augustus Odena, Maxwell Nye, Maarten                    Sutskever, and Wojciech Zaremba. Evaluating large lan-
  Bosma, Henryk Michalewski, David Dohan, Ellen Jiang,                guage models trained on code. arXiv:2107.03374, 2021.
  Carrie Cai, Michael Terry, Quoc Le, and Charles Sut-
  ton. Program synthesis with large language models. In              Wenhu Chen, Xueguang Ma, Xinyi Wang, and William W.
  NeurIPS, 2022.                                                      Cohen. Program of thoughts prompting: disentangling
                                                                      computation from reasoning for numerical reasoning
Bowen Baker, Ilge Akkaya, Peter Zhokhov, Joost Huizinga,              tasks. TMLR, 2023b. ISSN 2835-8856.
  Jie Tang, Adrien Ecoffet, Brandon Houghton, Raul
  Sampedro, and Jeff Clune. Video pretraining (VPT):                 Aakanksha Chowdhery, Sharan Narang, Jacob Devlin,
  Learning to act by watching unlabeled online videos. In              Maarten Bosma, Gaurav Mishra, Adam Roberts, Paul
  NeurIPS, 2022.                                                       Barham, Hyung Won Chung, Charles Sutton, Sebas-
                                                                       tian Gehrmann, Parker Schuh, Kensen Shi, Sasha
Maciej Besta, Nils Blach, Ales Kubicek, Robert Ger-                    Tsvyashchenko, Joshua Maynez, Abhishek Rao, Parker

                                                                10
                 Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

  Barnes, Yi Tay, Noam Shazeer, Vinodkumar Prabhakaran,             Luyu Gao, Aman Madaan, Shuyan Zhou, Uri Alon, Pengfei
  Emily Reif, Nan Du, Ben Hutchinson, Reiner Pope,                    Liu, Yiming Yang, Jamie Callan, and Graham Neubig.
  James Bradbury, Jacob Austin, Michael Isard, Guy Gur-               PAL: Program-aided language models. In ICML, 2023.
  Ari, Pengcheng Yin, Toju Duke, Anselm Levskaya, San-
  jay Ghemawat, Sunipa Dev, Henryk Michalewski, Xavier              Jiaxian Guo, Sidi Lu, Han Cai, Weinan Zhang, Yong Yu, and
  Garcia, Vedant Misra, Kevin Robinson, Liam Fedus,                    Jun Wang. Long text generation via adversarial training
  Denny Zhou, Daphne Ippolito, David Luan, Hyeontaek                   with leaked information. In AAAI, 2018.
  Lim, Barret Zoph, Alexander Spiridonov, Ryan Sepa-                William H. Guss, Brandon Houghton, Nicholay Topin,
  ssi, David Dohan, Shivani Agrawal, Mark Omernick,                  Phillip Wang, Cayden Codel, Manuela Veloso, and Rus-
  Andrew M. Dai, Thanumalayan Sankaranarayana Pillai,                lan Salakhutdinov. MineRL: A large-scale dataset of
  Marie Pellat, Aitor Lewkowycz, Erica Moreira, Rewon                Minecraft demonstrations. In IJCAI, 2019.
  Child, Oleksandr Polozov, Katherine Lee, Zongwei Zhou,
  Xuezhi Wang, Brennan Saeta, Mark Diaz, Orhan Firat,               Danijar Hafner, Timothy Lillicrap, Ian Fischer, Ruben Ville-
  Michele Catasta, Jason Wei, Kathy Meier-Hellstern, Dou-             gas, David Ha, Honglak Lee, and James Davidson. Learn-
  glas Eck, Jeff Dean, Slav Petrov, and Noah Fiedel. PaLM:            ing latent dynamics for planning from pixels. In ICML,
  Scaling language modeling with pathways. JMLR, 24                   2019.
  (240):1–113, 2023.
                                                                    Danijar Hafner, Jurgis Pasukonis, Jimmy Ba, and Timo-
Karl Cobbe, Vineet Kosaraju, Mohammad Bavarian, Mark                  thy Lillicrap. Mastering diverse domains through world
  Chen, Heewoo Jun, Lukasz Kaiser, Matthias Plappert,                 models. arXiv:2301.04104, 2023.
  Jerry Tworek, Jacob Hilton, Reiichiro Nakano, Christo-
  pher Hesse, and John Schulman. Training verifiers to              Shibo Hao, Yi Gu, Haodi Ma, Joshua Jiahua Hong, Zhen
  solve math word problems. arXiv:2110.14168, 2021.                   Wang, Daisy Zhe Wang, and Zhiting Hu. Reasoning
                                                                      with language model is planning with world model. In
Xiang Deng, Yu Gu, Boyuan Zheng, Shijie Chen, Samuel                  EMNLP, 2023.
  Stevens, Boshi Wang, Huan Sun, and Yu Su. Mind2Web:
  Towards a generalist agent for the web. In NeurIPS                Jie Huang, Xinyun Chen, Swaroop Mishra, Huaixiu Steven
  Datasets and Benchmarks Track, 2023.                                 Zheng, Adams Wei Yu, Xinying Song, and Denny Zhou.
                                                                       Large language models cannot self-correct reasoning yet.
Danny Driess, Fei Xia, Mehdi S. M. Sajjadi, Corey Lynch,               In ICLR, 2024.
  Aakanksha Chowdhery, Brian Ichter, Ayzaan Wahid,
  Jonathan Tompson, Quan Vuong, Tianhe Yu, Wenlong                  Wenlong Huang, F. Xia, Ted Xiao, Harris Chan, Jacky
  Huang, Yevgen Chebotar, Pierre Sermanet, Daniel Duck-              Liang, Peter R. Florence, Andy Zeng, Jonathan Tompson,
  worth, Sergey Levine, Vincent Vanhoucke, Karol Haus-               Igor Mordatch, Yevgen Chebotar, Pierre Sermanet, Noah
  man, Marc Toussaint, Klaus Greff, Andy Zeng, Igor Mor-             Brown, Tomas Jackson, Linda Luu, Sergey Levine, Karol
  datch, and Pete Florence. PaLM-E: An embodied multi-               Hausman, and Brian Ichter. Inner monologue: Embodied
  modal language model. In ICML, 2023.                               reasoning through planning with language models. In
                                                                     CoRL, 2022.
Yilun Du, Mengjiao Yang, Bo Dai, Hanjun Dai, Ofir
  Nachum, Joshua B. Tenenbaum, Dale Schuurmans, and                 Levente Kocsis and Csaba Szepesvári. Bandit based monte-
  Pieter Abbeel. Learning universal policies via text-guided          carlo planning. In ECML, 2006.
  video generation. In NeurIPS, 2023.
                                                                    Takeshi Kojima, Shixiang Shane Gu, Machel Reid, Yutaka
Jonathan St BT Evans. Intuition and reasoning: A dual-                Matsuo, and Yusuke Iwasawa. Large language models
  process perspective. Psychological Inquiry, pages 313 –             are zero-shot reasoners. In NeurIPS, 2022.
  326, 2010.
                                                                    Steven M. LaValle. Rapidly-exploring random trees : A
Linxi Fan, Guanzhi Wang, Yunfan Jiang, Ajay Mandlekar,                new tool for path planning. The Annual Research Report,
  Yuncong Yang, Haoyi Zhu, Andrew Tang, De-An Huang,                  1998.
  Yuke Zhu, and Anima Anandkumar. MineDojo: Building
  open-ended embodied agents with internet-scale knowl-             Evan Zheran Liu, Kelvin Guu, Panupong Pasupat, Tianlin
  edge. In NeurIPS Datasets and Benchmarks Track, 2022.               Shi, and Percy Liang. Reinforcement learning on web
                                                                      interfaces using workflow-guided exploration. In ICLR,
Hiroki Furuta, Ofir Nachum, Kuang-Huei Lee, Yutaka Mat-               2018.
  suo, Shixiang Shane Gu, and Izzeddin Gur. Multimodal
  web navigation with instruction-finetuned foundation              Xiao Liu, Hao Yu, Hanchen Zhang, Yifan Xu, Xuanyu
  models. In ICLR, 2024.                                              Lei, Hanyu Lai, Yu Gu, Hangliang Ding, Kaiwen Men,

                                                               11
                 Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

  Kejuan Yang, Shudan Zhang, Xiang Deng, Aohan Zeng,                 David Silver, Aja Huang, Chris J. Maddison, Arthur Guez,
  Zhengxiao Du, Chenhui Zhang, Sheng Shen, Tianjun                     L. Sifre, George van den Driessche, Julian Schrittwieser,
  Zhang, Yu Su, Huan Sun, Minlie Huang, Yuxiao Dong,                   Ioannis Antonoglou, Vedavyas Panneershelvam, Marc
  and Jie Tang. AgentBench: Evaluating LLMs as agents.                 Lanctot, Sander Dieleman, Dominik Grewe, John Nham,
  In ICLR, 2024.                                                       Nal Kalchbrenner, Ilya Sutskever, Timothy P. Lillicrap,
                                                                       Madeleine Leach, Koray Kavukcuoglu, Thore Graepel,
Zhihan Liu, Hao Hu, Shenao Zhang, Hongyi Guo, Shuqi
                                                                       and Demis Hassabis. Mastering the game of Go with deep
  Ke, Boyi Liu, and Zhaoran Wang. Reason for fu-
                                                                       neural networks and tree search. Nature, 529:484–489,
  ture, act for now: A principled framework for au-
                                                                       2016.
  tonomous LLM agents with provable sample efficiency.
  arXiv:2309.17382, 2023.                                            David Silver, Aja Huang, Chris J. Maddison, Arthur Guez,
Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hal-                  L. Sifre, George van den Driessche, Julian Schrittwieser,
 linan, Luyu Gao, Sarah Wiegreffe, Uri Alon, Nouha                     Ioannis Antonoglou, Vedavyas Panneershelvam, Marc
 Dziri, Shrimai Prabhumoye, Yiming Yang, Shashank                      Lanctot, Sander Dieleman, Dominik Grewe, John Nham,
 Gupta, Bodhisattwa Prasad Majumder, Katherine Her-                    Nal Kalchbrenner, Ilya Sutskever, Timothy P. Lillicrap,
 mann, Sean Welleck, Amir Yazdanbakhsh, and Peter                      Madeleine Leach, Koray Kavukcuoglu, Thore Graepel,
 Clark. Self-refine: Iterative refinement with self-feedback.          and Demis Hassabis. Mastering chess and Shogi by self-
 In NeurIPS, 2023.                                                     play with a general reinforcement learning algorithm.
                                                                       arXiv:1712.01815, 2017.
Ramesh Nallapati, Bowen Zhou, Cicero dos Santos, Caglar
  Gulcehre, and Bing Xiang. Abstractive text summariza-              Steven A. Sloman. The empirical case for two systems of
  tion using sequence-to-sequence RNNs and beyond. In                  reasoning. Psychological Bulletin, 119:3–22, 1996.
  Special Interest Group on Natural Language Learning,
                                                                     Haotian Sun, Yuchen Zhuang, Lingkai Kong, Bo Dai, and
  2016.
                                                                       Chao Zhang. AdaPlanner: Adaptive planning from feed-
OpenAI. GPT-4 technical report. arXiv:2303.08774, 2023.                back with language models. In NeurIPS, 2023.
Yujia Qin, Shihao Liang, Yining Ye, Kunlun Zhu, Lan                  Dı́dac Surı́s, Sachit Menon, and Carl Vondrick. ViperGPT:
  Yan, Yaxi Lu, Yankai Lin, Xin Cong, Xiangru Tang, Bill                Visual inference via Python execution for reasoning. In
  Qian, Sihan Zhao, Runchu Tian, Ruobing Xie, Jie Zhou,                 ICCV, 2023.
  Mark Gerstein, Dahai Li, Zhiyuan Liu, and Maosong Sun.
  ToolLLM: Facilitating large language models to master              Maciej Swiechowski, Konrad Godlewski, Bartosz Sawicki,
  16000+ real-world APIs. In ICLR, 2024.                              and Jacek Ma’ndziuk. Monte Carlo tree search: A re-
                                                                      view of recent modifications and applications. Artificial
Abulhair Saparov and He He. Language models are greedy
                                                                      Intelligence Review, 56:2497–2562, 2021.
  reasoners: A systematic formal analysis of chain-of-
  thought. In ICLR, 2023.                                            Hugo Touvron, Louis Martin, Kevin R. Stone, Peter Al-
Timo Schick, Jane Dwivedi-Yu, Roberto Dessı̀, Roberta                  bert, Amjad Almahairi, Yasmine Babaei, Nikolay Bash-
  Raileanu, Maria Lomeli, Luke Zettlemoyer, Nicola Can-                lykov, Soumya Batra, Prajjwal Bhargava, Shruti Bhos-
  cedda, and Thomas Scialom. Toolformer: Language                      ale, Daniel M. Bikel, Lukas Blecher, Cristian Cantón
  models can teach themselves to use tools. In NeurIPS,                Ferrer, Moya Chen, Guillem Cucurull, David Esiobu,
  2023.                                                               Jude Fernandes, Jeremy Fu, Wenyin Fu, Brian Fuller,
                                                                       Cynthia Gao, Vedanuj Goswami, Naman Goyal, An-
Yongliang Shen, Kaitao Song, Xu Tan, Dongsheng Li,                     thony S. Hartshorn, Saghar Hosseini, Rui Hou, Hakan
  Weiming Lu, and Yueting Zhuang. HuggingGPT: Solving                  Inan, Marcin Kardas, Viktor Kerkez, Madian Khabsa, Is-
  AI tasks with ChatGPT and its friends in Hugging Face.               abel M. Kloumann, A. V. Korenev, Punit Singh Koura,
  In NeurIPS, 2023.                                                    Marie-Anne Lachaux, Thibaut Lavril, Jenya Lee, Diana
                                                                       Liskovich, Yinghai Lu, Yuning Mao, Xavier Martinet,
Noah Shinn, Federico Cassano, Beck Labash, Ashwin
                                                                      Todor Mihaylov, Pushkar Mishra, Igor Molybog, Yixin
  Gopinath, Karthik Narasimhan, and Shunyu Yao. Reflex-
                                                                       Nie, Andrew Poulton, Jeremy Reizenstein, Rashi Rungta,
  ion: Language agents with verbal reinforcement learning.
                                                                       Kalyan Saladi, Alan Schelten, Ruan Silva, Eric Michael
  In NeurIPS, 2023.
                                                                       Smith, R. Subramanian, Xia Tan, Binh Tang, Ross
Mohit Shridhar, Xingdi Yuan, Marc-Alexandre Côté,                   Taylor, Adina Williams, Jian Xiang Kuan, Puxin Xu,
 Yonatan Bisk, Adam Trischler, and Matthew Hausknecht.                 Zhengxu Yan, Iliyan Zarov, Yuchen Zhang, Angela Fan,
 ALFWorld: Aligning text and embodied environments                     Melanie Kambadur, Sharan Narang, Aurelien Rodriguez,
 for interactive learning. In ICLR, 2020.                              Robert Stojnic, Sergey Edunov, and Thomas Scialom.

                                                                12
                 Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

  Llama 2: Open foundation and fine-tuned chat models.            Denny Zhou, Nathanael Schärli, Le Hou, Jason Wei, Nathan
  arXiv:2307.09288, 2023.                                           Scales, Xuezhi Wang, Dale Schuurmans, Olivier Bous-
                                                                    quet, Quoc Le, and Ed Chi. Least-to-most prompting
Tom Vodopivec, Spyridon Samothrakis, and Branko Ster.               enables complex reasoning in large language models. In
  On Monte Carlo tree search and reinforcement learning.            ICLR, 2022.
  Journal of Artificial Intelligence Research, 60:881–936,
  2017.                                                           Yuchen Zhuang, Xiang Chen, Tong Yu, Saayan Mitra, Victor
                                                                    Bursztyn, Ryan A. Rossi, Somdeb Sarkhel, and Chao
Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar,
                                                                    Zhang. ToolChain*: Efficient action space navigation in
  Chaowei Xiao, Yuke Zhu, Linxi Fan, and Anima Anand-
                                                                    large language models with A* search. In ICLR, 2023.
  kumar. Voyager: An open-ended embodied agent with
  large language models. arXiv:2305.16291, 2023.
Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le,
  Ed Chi, and Denny Zhou. Self-consistency improves
  chain of thought reasoning in language models. In ICLR,
  2022.
Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten
  Bosma, Ed Chi, Quoc Le, and Denny Zhou. Chain of
  thought prompting elicits reasoning in large language
  models. In NeurIPS, 2022.
Michael Wooldridge and Nicholas R Jennings. Intelligent
 agents: Theory and practice. The Knowledge Engineering
 Review, 10:115 – 152, 1995.
Philipp Wu, Alejandro Escontrela, Danijar Hafner, Pieter
  Abbeel, and Ken Goldberg. Daydreamer: World models
  for physical robot learning. In CoRL, 2023.
Yuxi Xie, Kenji Kawaguchi, Yiran Zhao, Xu Zhao, Min-
  Yen Kan, Junxian He, and Qizhe Xie. Decomposition
  enhances reasoning via self-evaluation guided decoding.
  arXiv:2305.00633, 2023.
Zhilin Yang, Peng Qi, Saizheng Zhang, Yoshua Bengio,
  William W Cohen, Ruslan Salakhutdinov, and Christo-
  pher D Manning. HotpotQA: A dataset for diverse, ex-
  plainable multi-hop question answering. In EMNLP,
  2018.
Shunyu Yao, Howard Chen, John Yang, and Karthik R
  Narasimhan. WebShop: Towards scalable real-world web
  interaction with grounded language agents. In NeurIPS,
  2022.
Shunyu Yao, Dian Yu, Jeffrey Zhao, Izhak Shafran,
  Thomas L. Griffiths, Yuan Cao, and Karthik Narasimhan.
  Tree of thoughts: deliberate problem solving with large
  language models. In NeurIPS, 2023a.
Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran,
  Karthik Narasimhan, and Yuan Cao. ReAct: Synergizing
  reasoning and acting in language models. In ICLR, 2023b.
Weirui Ye, Shaohuai Liu, Thanard Kurutach, Pieter Abbeel,
 and Yang Gao. Mastering Atari games with limited data.
 In NeurIPS, 2021.

                                                             13
                  Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

Appendix of LATS                                                      noting that this is cheaper than the inference cost associ-
                                                                      ated with using LMs as world models, as in previous search
The appendix is organized as follows. First in Sec. A, we             approaches (Hao et al., 2023; Liu et al., 2023).
show the pseudocode of our proposed algorithm, LATS. In
Sec. B, we provide further discussion of the limitations of           Assumption of environment reversion in decision-
our method. In Sec. C, we present additional experimental             making. Since our method is based on Monte Carlo
results. In Sec. D, we specify the environment details in our         Tree Search and is model-free, one limitation of LATS on
experiments. Finally, we list our prompts used for the three          decision-making tasks is that it requires the agent to be
environments in Sec. E (HotPotQA), Sec. F (Programming),              able to revert to earlier states in the environments. How-
and Sec. G (WebShop), respectively.                                   ever, this reversion property is feasible in many real-world
                                                                      environments and applications (despite being not univer-
                                                                      sally applicable in all possible environments), including
A. LATS Pseudocode                                                    programming (HumanEval (Chen et al., 2021)), web search
Alg. 1 shows the pseudocode of our algorithm LATS. Nodes              (WebShop (Yao et al., 2022)), text-based manipulation tasks
are stored explicitly in the memory. Unless otherwise speci-          (Alfworld (Shridhar et al., 2020)), and LMs with tool use
fied, in all experiments, we set the number of sampled nodes          (ToolBench (Qin et al., 2024)). Therefore, we believe that
to n = 5 and the exploration weight to w = 1. We use                  leveraging the reversion property is not a shortcoming but
a self-consistency weight of λ = 0.5 for HotPotQA and                 rather a feature that has not been explicitly given notice
Game of 24, and λ = 0.8 for Programming and WebShop.                  by the LM decision-making community – it opens up new
                                                                      opportunities in the emerging LM agent community.
B. More Discussion on Limitations                                     Additionally, the benchmarks we use in this paper are rel-
                                                                      atively simple and focused on decision-making compared
As stated in Sec. 6, LATS has two main limitations:                   to the complexity of real-world interactive environments.
Computational cost. Although LATS can improve rea-                    Moreover, some environments might not easily support roll-
soning and decision-making, this arrives at a higher com-             backs to previous states. However, the design of LATS is
putational cost relative to simpler prompting methods like            flexible and can be adjusted to various resource constraints.
ReAct or Reflexion. However, the following facts serve as             Using planning-based prompting methods like LATS in
mitigations to this issue:                                            environments like Minecraft (Fan et al., 2022) and more rea-
                                                                      soning benchmarks would be interesting avenues for future
                                                                      work.
   • Asymptotically, our method has the same sample com-
     plexity as ToT (Yao et al., 2023a) and RAP (Hao et al.,
     2023), but achieves better performance, expands fewer            C. Additional Ablations
     nodes, and uses fewer tokens on average upon success.
                                                                      In this section, we ablate various designs of LATS. Ex-
     This suggests that our method is not only stronger
                                                                      periments are conducted on HotPotQA with a maximum
     in problem-solving but also has higher efficiency. A
                                                                      of k = 50 trajectories and sampling size of n = 5 and
     full analysis of the cost can be found in Tab. 9 in Ap-
                                                                      HumanEval with a maximum of k = 8 trajectories and sam-
     pendix C.
                                                                      pling size of n = 5. The result for HotPotQA is shown in
                                                                      Tab. 8 and HumanEval in Fig. 3.
   • The number of nodes n expanded at every step provides
     a natural trade-off between performance and efficiency.          Exploration weight. We find that there is lower perfor-
     In fact, setting n = 1 makes the method as efficient             mance on HotPotQA when the exploration weight w in the
     as ReAct (Yao et al., 2023b) with multiple trials or             selection formula is decreased to 0.5, suggesting that this
     CoT-SC (Wang et al., 2022).                                      reduces the effectiveness of the search. Increasing w to 2.0
                                                                      does not lead to a performance improvement, but we tend
In general, we recommend using LATS for difficult tasks               to observe faster convergence. The optimal setting depends
like programming or for situations where performance is               on the particular environment and complexity of the state
prioritized over efficiency in practice. We hope that contin-         space.
ued advancements in LMs will reduce costs and increase                Depth. In our main experiments we use a maximum depth
the applicability of LATS.                                            of d = 7 on HotPotQA for all methods, following previous
Additionally, there exists a minor cost from querying the en-         work (Yao et al., 2023b). We ablate the effect on LATS after
vironment, which we find to be trivial for the environments           reducing it to d = 4. This results in only a slight drop in
we study. Most LM-based environments involve API-based                performance. We find that most questions can be answered
tools, which are inexpensive and fast to use. It is also worth        within four steps, and using a greater number of steps tends

                                                                 14
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

Algorithm 1 LATS(s, pθ , pV , pref , d, k, n, w, a, b)
      Require: Initial state s, action generator pθ , value function pV , reflection generator pref , number of generated actions n,
        depth limit L, number of roll-outs K, context c, exploration weight w, and value function weight λ
        Initialize action space A, observation space O
        Initialize the state-action value function pV : S × A 7→ R and visit counter N : S 7→ N to one
        for k ← 0, . . . , K − 1 do
            for t ← 0, . . . , L − 1 do
                 if st not terminal then                                                                 ▷ Expansion & Simulation
                      for i ← 1, . . . , n do
                                      (i)
                           Sample at ∼ pθ (st )
                                 (i)                    (i)          (i) (i) (i) (i)      (i)  (i)
                           Get ot from environment, st+1 ← (ct , ot , at ), ct+1 ← (ot , at )
                                        (i)         (i)                      (i)
                           Evaluate Vt ∼ λ ∗ pV (st ) + (1 − λ) ∗ SC(st )                                              ▷ Evaluation
                                          (i)
                           V (st ) ← Vt
                                  (i)
                           Add st to children
                      end for
                 end if
                 if st is terminal then                                                                                ▷ Reflection
                      Get r from environment
                      if r not success then
                           reflection ← pref (ct )
                           c ← reflection
                      end if
                 end if                       h      q               i
                                                          ln N (st )
                 at ← arg maxa∈e(st ) V (st ) + w N         (st+1 )
                                                                                                                        ▷ Selection
                Get corresponding ot from memory, st+1 ← (ct , ot , at ), ct+1 ← (ot , at )
                N (st+1 ) ← N (st+1 ) + 1
                if at is an output action then break
            end for
            T ← the actual number of steps
            for t ← T − 1, . . . , 0 do                                                                         ▷ Backpropagation
                V (st ) ← V (st )(N (st )−1)+r
                                  N (st )
            end for
         end for


to force the agent into local minima and rarely improves                based question-answer pairs crafted by crowdworkers to
success.                                                                be diverse, multi-hop, and explainable. Questions cover a
                                                                        range of types like entities, locations, dates, and comparison
LM value function. The LM value function scores states
                                                                        of shared properties between two entities. Crowdworkers
based on expected future reward. Without this heuristic,
                                                                        also provide supporting facts from the documents that justify
the only signal to guide search would be from environment
                                                                        the answer. We use the HotPotQA benchmark setting with
rewards for completed trajectories, which are scarce and
                                                                        all the Wikipedia paragraphs to test retrieval. We use a ran-
often binary. When we remove the evaluation operation, we
                                                                        domly selected subset of 100 questions for our experiments
observe a dramatic 0.26 drop in performance.
                                                                        and a maximum depth limit of 6. Fig. 4 illustrates how
Performance over time. To see the effects of increasing                 ReAct and LATS work on an example task of HotPotQA,
the number of trajectories sampled, we change k to different            and gives a qualitative example on how LATS outperforms
values. We conduct this experiment on HumanEval, which                  ReAct on the task. For value function hyperparameters, we
has a more noticeable difference due to sampling less tra-              use λ = 0.5 for the LM score and self-consistency score.
jectories. The results are shown in Fig. 3, in which LATS
                                                                        Action Space. We adopt the Wikipedia web API proposed
scales better with more iterations than Reflexion.
                                                                        in Yao et al. (2023b), with three types of actions to support
                                                                        interactive information retrieval:
D. Environment Details
                                                                        (1) search[entity], which returns the first 5 sentences
D.1. HotPotQA                                                           from the corresponding entity wiki page if it exists,
                                                                        or else suggests top-5 similar entities from the Wikipedia
HotPotQA (Yang et al., 2018) is a question-answering
                                                                        search engine,
dataset that requires reasoning over multiple supporting
documents to answer questions. It contains 113k Wikipedia-              (2) lookup[string], which returns the next sentence in


                                                                   15
                  Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

                                                                        if any sample passes all tests. We use all 164 problems for
       Prompt Method            HotpotQA (EM) ↑                         our experiments and a maximum depth limit of 8. For the
                                                                        three questions without sample test cases, we write our own.
    LATS (w = 0.5)                      0.55                            For value function hyperparameters, we use λ = 0.8 for the
    LATS (w = 2.0)                      0.63                            LM score and self-consistency score. For GPT-3.5 we use
     LATS (d = 4)                       0.58                            six internal tests, while for GPT-4 we use four internal tests.
      LATS (CoT)                        0.62
 LATS (No LM Heuristic)                 0.37                            The Mostly Basic Programming Problems (MBPP) (Austin
  LATS (w = 1.0, d = 7)                 0.63                            et al., 2022) benchmark contains 974 short Python functions
                                                                        designed to evaluate program synthesis techniques. The
Table 11. Ablation results on LATS and baseline variants in Hot-        dataset was constructed by crowdsourcing from workers
PotQA measured by Exact Match (EM). We test different depth d,          with basic Python knowledge. Each data point consists of
exploration factor w, and versions of LATS using CoT and without        a natural language description of a programming task, a
the LM value function. We sample n = 5 and k = 50 trajectories.         reference solution implementation, and three test cases for
                                                                        functional correctness. The natural language prompts are
                                                                        typically short, one-sentence descriptions. Solutions cover
                                                                        common programming constructs including mathematical
                                                                        operations, list processing, string manipulation, and usage
                                                                        of the Python standard library. On average, solutions are 6.8
                                                                        lines of code. The dataset is also supplemented with an ad-
                                                                        ditional set of 426 problems that were manually verified for
                                                                        unambiguous specifications, standard function signatures,
                                                                        and accurate test cases. We use a randomly selected subset
                                                                        of 397 problems for our experiments. For value function
                                                                        hyperparameters, we use λ = 0.8 for the LM score and
                                                                        self-consistency score.

                                                                        D.3. WebShop
                                                                        WebShop (Yao et al., 2022) is an interactive web-based
Figure 3. Performance over successive iterations on HumanEval           environment designed to evaluate agents on grounded
with GPT-3.5.                                                           language understanding and decision-making. It simulates
                                                                        an e-commerce shopping task by providing agents with
                                                                        over 1 million real-world products scraped from Amazon,
                                                                        spanning 5 categories and 113 subcategories. These
the page containing string,
                                                                        products contain rich linguistic information, with an
(3) finish[answer], which finishes the current task with                average text length of 262 words and a vocabulary size
answer.                                                                 of 224k. In addition, there are over 800k unique product
                                                                        options available for customization. The environment
These API calls and free-form thoughts form the action
                                                                        renders webpages in two modes: HTML mode provides
space for this environment.
                                                                        pixel-level observations with interactive elements, while
                                                                        simple mode converts the raw HTML into a structured text
D.2. Programming                                                        observation more amenable for training agents. The action
The HumanEval dataset (Chen et al., 2021) is a collection               space consists of query searches and button clicks, which
of 164 handwritten programming problems introduced to                   transition between 4-page types: search, results, item, and
evaluate the functional correctness of models for synthe-               item detail. Instructions are crowdsourced natural language
sizing programs from natural language descriptions. Each                specifying product attributes and options, with a total of 12k
problem includes a function signature, docstring descrip-               collected. Automatic rewards are computed by comparing
tion, reference implementation, and multiple unit tests, with           the product purchased by the agent against the attributes
an average of 7.7 tests per problem. The programming                    and options specified in the instruction, using both lexical
tasks assess comprehension of natural language, reasoning,              matching and semantic similarity metrics.
algorithms, and basic mathematics, at a difficulty level com-
parable to simple software interview questions. Pass rates              There are two evaluation metrics used in WebShop: (1) Task
are evaluated with the pass@k metric, where k samples are               Score defined as (100 × avg. reward), which captures the
generated per problem and a problem is considered solved

                                                                   16
                  Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models




Figure 4. Example trajectories on HotPotQA for ReAct (left) and LATS (right). LATS can sample more actions and avoid failure from
previous mistakes by evaluating states with an LM to guide the search toward promising areas of the tree.

   Type         Argument           State → Next State                   Prompt Method             Game of 24 (Success Rate) ↑
   search       [Query]            Search → Results                     LATS (CoT, λ = 1)                      0.40
   choose       Back to search     ∗ → Search                           LATS (CoT)                             0.44
   choose       Prev/Next page     Results → Results
   choose       [Product title]    Results → Item                    Table 13. Ablations on λ in Game of 24 with GPT-3.5. λ = 0.5
   choose       [Option]           Item → Item                       used in the main paper outperforms λ = 1, equivalent to removing
   choose       Desc/Overview      Item → Item-Detail                self-consistency, which indicates that the self-consistency score
   choose       Previous           Item-Detail → Item                improves the performance of LATS.
   choose       Buy                Item → Episode End
                                                                     correct equation that equals 24 and uses each input number
             Table 12. Action space of WebShop.
                                                                     only once. We report success rate over 50 games. We use
                                                                     k = 30 iterations and a maximum depth limit of 5. For value
                                                                     function hyperparameters, we use λ = 0.5 for the LM score
average reward obtained across episodes; and (2) Success             and self-consistency score. Tab. 13 shows the performance
Rate (SR) defined as the portion of instructions where r = 1.        comparison between λ = 0.5 and λ = 1, which validates
The reward is calculated based on the number of attributes           our design of self-consistency term.
satisfied by the selected item. We use 50 environments for
our experiments and a maximum depth limit of 15. For                 E. HotPotQA Prompts
value function hyperparameters, we use λ = 0.8 for the LM
score and self-consistency score.                                    E.1. Base Acting Prompt
                                                                     Solve a question answering task with interleaving Thought,
D.4. Game of 24                                                      Action, Observation steps. Thought can reason about the
                                                                     current situation, and Action can be three types:
Game of 24 is a mathematical reasoning challenge where
the goal is to use basic arithmetic operations to construct          (1) Search[entity], which searches the exact entity on
24 out of 4 numbers. We follow the setup from Yao et al.             Wikipedia and returns the first paragraph if it exists. If
(2023a), where we measure success if the agent produces a            not, it will return some similar entities to search.

                                                                17
                 Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

(2) Lookup[keyword], which returns the next sentence con-           with either Action or an indexed Thought
taining keyword in the current passage.
                                                                    Here are some examples:
(3) Finish[answer], which returns the answer and finishes
                                                                    Question: What is the elevation range for the area that the
the task.
                                                                    eastern sector of the Colorado orogeny extends into?
After each observation, provide the next Thought and next
                                                                    Let’s think step by step.
Action.
                                                                    Thought 1: The eastern sector of Colorado orogeny extends
Here are some examples:
                                                                    into the High Plains.
Question: Which magazine was started first Arthur’s Maga-
                                                                    Thought 2: High Plains rise in elevation from around 1,800
zine or First for Women?
                                                                    to 7,000 ft
Thought 1: I need to search Arthur’s Magazine and First for
                                                                    Thought 3: The answer is 1,800 to 7,000 ft.
Women, and find which was started first.
                                                                    Action: Finish[1,800 to 7,000 ft]
Action 1: Search[Arthur’s Magazine]
                                                                    (examples)
Observation 1: Arthur’s Magazine was an American literary
periodical published in Philadelphia in the 19th century.           Previous trial: (trajectories)
Edited by Timothy Shay Arthur, it featured work by Edgar
                                                                    (input)
A. Poe, J.H. Ingraham, Sarah Josepha Hale, Thomas G.
Spear, and others.[1][2] In May 1846 it was merged into
Godey’s Lady’s Book.[3]                                             E.3. Value Function Prompt

Thought 2: Arthur’s Magazine was started in 1844. I need            Analyze the trajectories of a solution to a question answering
to search First for Women next.                                     task. The trajectories are labeled by environmental Obser-
                                                                    vations about the situation, Thoughts that can reason about
Action 2: Search[First for Women]                                   the current situation, and Actions that can be three types:
Observation 2: First for Women is a woman’s magazine                (1) Search[entity], which searches the exact entity on
published by Bauer Media Group in the USA.[1] The mag-              Wikipedia and returns the first paragraph if it exists. If
azine was started in 1989. It is based in Englewood Cliffs,         not, it will return some similar entities to search.
New Jersey.[2] In 2011 the circulation of the magazine was
1,310,696 copies.[3]                                                (2) Lookup[keyword], which returns the next sentence con-
                                                                    taining keyword in the current passage.
Thought 3: First for Women was started in 1989. 1844
(Arthur’s Magazine) < 1989 (First for Women), so Arthur’s           (3) Finish[answer], which returns the answer and finishes
Magazine was started first.                                         the task.

Action 3: Finish[Arthur’s Magazine]                                 Given a question and a trajectory, evaluate its correctness
                                                                    and provide your reasoning and analysis in detail. Focus
(examples)                                                          on the latest thought, action, and observation. Incomplete
You have attempted to answer the following question before          trajectories can be correct if the thoughts and actions so
and failed. The following reflection(s) give a plan to avoid        far are correct, even if the answer is not found yet. Do not
failing to answer the question in the same way you did              generate additional thoughts or actions. Then at the last line
previously. Use them to improve your strategy of correctly          conclude “Thus the correctness score is s”, where s is an
answering the given question.                                       integer from 1 to 10.

(trajectories)                                                      Question: Which magazine was started first Arthur’s Maga-
                                                                    zine or First for Women?
(input)
                                                                    Thought 1: I need to search Arthur’s Magazine and First for
                                                                    Women, and find which was started first.
E.2. Base Reasoning Prompt
                                                                    Action 1: Search[Arthur’s Magazine]
Solve a question answering task by having a Thought, then
Finish with your answer. Thought can reason about the               Observation 1: Arthur’s Magazine was an American literary
current situation. Finish[answer] returns the answer and            periodical published in Philadelphia in the 19th century.
finishes the task. You will be given context that you should        Edited by Timothy Shay Arthur, it featured work by Edgar
use to help you answer the question. Start your response            A. Poe, J.H. Ingraham, Sarah Josepha Hale, Thomas G.


                                                               18
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

Spear, and others.[1][2] In May 1846 it was merged into               making this the best action.
Godey’s Lady’s Book.[3]
                                                                      Thus the correctness score is 10
This trajectory is correct as it is reasonable to search for
                                                                      (other examples)
the first magazine provided in the question. It is also better
to have simple searches corresponding to a single entity,             (failed trajectories)
making this the best action.
                                                                      (context)
Thus the correctness score is 10
(other examples)                                                      F. Programming Prompts
(failed trajectories)                                                 F.1. HumanEval function implementation example
(context)                                                             Sample function signature:

E.4. Reflection Prompt
                                                                      d e f minSubArraySum ( nums ) :
Analyze the trajectories of a solution to a question-                       Given an a r r a y o f i n t e g e r s nums ,
answering task. The trajectories are labeled by environ-                    f i n d t h e minimum sum o f any
mental Observations about the situation, Thoughts that can                  non − empty sub − a r r a y o f nums .
reason about the current situation, and Actions that can be                 Example
three types:                                                                minSubArraySum ( [ − 1 , −2 , − 3 ] ) == −6
(1) Search[entity], which searches the exact entity on
Wikipedia and returns the first paragraph if it exists. If            Sample function body implementation:
not, it will return some similar entities to search.
(2) Lookup[keyword], which returns the next sentence con-                   min sum = f l o a t ( ’ i n f ’ )
taining keyword in the current passage.                                     f o r i i n r a n g e ( l e n ( nums ) ) :
                                                                                    current sum = 0
(3) Finish[answer], which returns the answer and finishes                           f o r j i n r a n g e ( i , l e n ( nums ) ) :
the task.                                                                                 c u r r e n t s u m += nums [ j ]
Given a question and a trajectory, evaluate its correctness                               i f c u r r e n t s u m < min sum :
and provide your reasoning and analysis in detail. Focus                                          min sum = c u r r e n t s u m
on the latest thought, action, and observation. Incomplete                  r e t u r n min sum
trajectories can be correct if the thoughts and actions so
far are correct, even if the answer is not found yet. Do not
                                                                      F.2. Base Acting/Reasoning Prompt
generate additional thoughts or actions. Then at the last line
conclude “Thus the correctness score is s”, where s is an             You are an AI Python assistant. You will be given your
integer from 1 to 10.                                                 previous implementation of a function, a series of unit tests
                                                                      results, and your self-reflection on your previous implemen-
Question: Which magazine was started first Arthur’s Maga-
                                                                      tation. Write your full implementation (restate the function
zine or First for Women?
                                                                      signature).
Thought 1: I need to search Arthur’s Magazine and First for
                                                                      Example 1:
Women, and find which was started first.
                                                                      [previous impl]:
Action 1: Search[Arthur’s Magazine]
Observation 1: Arthur’s Magazine was an American literary             d e f add ( a : i n t , b : i n t ) −> i n t :
periodical published in Philadelphia in the 19th century.                   ‘ ‘ Given i n t e g e r s a and b ,
Edited by Timothy Shay Arthur, it featured work by Edgar                    r e t u r n t h e t o t a l v a l u e o f a and b . ’ ’
A. Poe, J.H. Ingraham, Sarah Josepha Hale, Thomas G.                        return a − b
Spear, and others.[1][2] In May 1846 it was merged into
Godey’s Lady’s Book.[3]                                               [unit test results from previous impl]:

This trajectory is correct as it is reasonable to search for          Tested passed:
the first magazine provided in the question. It is also better        Tests failed:
to have simple searches corresponding to a single entity,
                                                                      assert add(1, 2) == 3 # output: -1

                                                                 19
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

assert add(1, 2) == 4 # output: -1                                   This will ensure that the function returns the correct output
                                                                     for the given input.
[reflection on previous impl]:
The implementation failed the test cases where the input             F.4. Test Case Generation Prompt
integers are 1 and 2. The issue arises because the code does
not add the two integers together, but instead subtracts the         You are an AI coding assistant that can write unique, diverse,
second integer from the first. To fix this issue, we should          and intuitive unit tests for functions given the signature and
change the operator from ‘-’ to ‘+’ in the return statement.         docstring.
This will ensure that the function returns the correct output        (input)
for the given input.
[improved impl]:                                                     G. WebShop Prompts
d e f add ( a : i n t , b : i n t ) −> i n t :                       G.1. Acting Prompt
      ‘‘
                                                                     Webshop
      Given i n t e g e r s a and b ,
      r e t u r n t h e t o t a l v a l u e o f a and b .            Instruction:
      ’’
                                                                     i would like a 3 ounce bottle of bright citrus deodorant for
      return a + b
                                                                     sensitive skin, and price lower than 50.00 dollars
                                                                     [Search]
F.3. Reflection Prompt
You are a Python programming assistant. You will be given            Action: search[3 ounce bright citrus deodorant sensitive
a function implementation and a series of unit test results.         skin]
Your goal is to write a few sentences to explain why your
implementation is wrong, as indicated by the tests. You              Observation:
will need this as guidance when you try again later. Only            [Back to Search]
provide the few sentence description in your answer, not the
implementation. You will be given a few examples by the              Page 1 (Total results: 50)
user.                                                                [Next ] [B078GWRC1J]
Example 1:                                                           Bright Citrus Deodorant by Earth Mama — Natural and Safe
[previous impl]:                                                     for Sensitive Skin, Pregnancy and Breastfeeding, Contains
                                                                     Organic Calendula 3-Ounce
      d e f add ( a : i n t , b : i n t ) −> i n t :
                                                                $10.99
            ‘‘
            Given i n t e g e r s a and b ,                     [B078GTKVXY]
            r e t u r n t h e t o t a l v a l u e o f a and b .
                                                                Ginger Fresh Deodorant by Earth Mama — Natural and Safe
            ’’
                                                                for Sensitive Skin, Pregnancy and Breastfeeding, Contains
      return a − b
                                                                Organic Calendula 3-Ounce
[unit test results from previous impl]:                              $10.99
Tested passed:                                                       [B08KBVJ4XN]
Tests failed:                                                        Barrel and Oak - Aluminum-Free Deodorant, Deodorant
                                                                     for Men, Essential Oil-Based Scent, 24-Hour Odor Protec-
assert add(1, 2) == 3 # output: -1                                   tion, Cedar & Patchouli Blend, Gentle on Sensitive Skin
assert add(1, 2) == 4 # output: -1                                   (Mountain Sage, 2.7 oz, 2-Pack)
[reflection on previous impl]:                                       $15.95
The implementation failed the test cases where the input
integers are 1 and 2. The issue arises because the code does         Action: think[B078GWRC1J and B078GTKVXY are
not add the two integers together, but instead subtracts the         bright citrus deodorant less then 50 dollars. I can check
second integer from the first. To fix this issue, we should          B078GWRC1J first.]
change the operator from ‘-’ to ‘+’ in the return statement.

                                                                20
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

Observation: OK.                                                       i am looking for dairy free and apple variety pack of chips,
                                                                       and price lower than 30.00 dollars
Action: click[B078GWRC1J]                                              [Search]
Observation:
                                                                       Action: search[dairy free and apple variety pack of chips]
[Back to Search]
                                                                       Observation:
[Prev]
                                                                       [Back to Search]
scent [assorted scents][bright citrus][calming laven-
der][ginger fresh][simply non-scents] size [travel set (4-             Page 1 (Total results: 50)
pack)][3 ounce (pack of 1)][3-ounce (2-pack)] Bright Citrus
                                                                       [Next]
Deodorant by Earth Mama — Natural and Safe for Sensi-
tive Skin, Pregnancy and Breastfeeding, Contains Organic               [B07HRFJWP8]
Calendula 3-Ounce
                                                                       Enjoy Life Foods Soft Baked Ovals, Breakfast Bars, Nut
Price: $10.99                                                          Free Bars, Soy Free, Dairy Free, Non GMO, Gluten Free,
                                                                       Vegan, Variety Pack, 4 Boxes (20 Bars Total)
Rating: N.A.
                                                                       $100.0
[Description]
                                                                       [B01KMHY5PG]
[Features]
                                                                       Enjoy Life Soft Baked Chewy Bars, Variety Pack, Nut Free
[Reviews]
                                                                       Bars, Soy Free, Dairy Free, Gluten Free, 6 Boxes (30 Total
[Buy Now]                                                              Bars)
                                                                       $21.49
Action: think[For 3 ounce bottle of bright citrus deodorant
                                                                       [B008D2X8C4]
for sensitive skin, the item has options ‘bright citrus’ and ‘3
ounce (pack of 1)’ and seems good to buy.]                             Enjoy Life Lentil Chips Variety Pack, Dairy Free Chips, Soy
                                                                       Free, Nut Free, Non GMO, Vegan, Gluten Free, 24 Bags
Observation: OK.
                                                                       (0.8 oz)
                                                                       $100.0
Action: click[bright citrus]
Observation: You have clicked bright citrus.
                                                                       Action: think[The first two items are not what I want. The
                                                                       third item is the dairy free and apple variety pack of chips I
Action: click[3 ounce (pack of 1)]                                     want.]
Observation: You have clicked 3 ounce (pack of 1).                     Observation: OK.


Action: click[Buy Now]                                                 Action: click[B008D2X8C4]
                                                                       Observation:
G.2. Value Function Prompt
                                                                       [Back to Search]
Given an item to purchase and a trajectory that aims to buy
an item that exactly matches the specification, which cor-             [Prev]
responds to the ideal score of 1.0, analyze the following              flavor name [dill and sour cream][garlic & parmesan][light
trajectory, then at the last line conclude, “Thus the correct-         sea salt][margherita pizza][thai chili lime][variety pack] size
ness score is s”, where s is an integer from 1 to 10.                  [0.8 ounce (pack of 24)][4 ounce (pack of 12)]
Here are some examples                                                 Price: $100.0
                                                                       Rating: N.A.
Webshop
                                                                       [Description]
Instruction:
                                                                       [Features]

                                                                  21
                  Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

[Reviews]                                                             (20 Bars Total) $100.0 [B01KMHY5PG] Enjoy Life Soft
                                                                      Baked Chewy Bars, Variety Pack, Nut Free Bars, Soy Free,
[Buy Now]
                                                                      Dairy Free, Gluten Free, 6 Boxes (30 Total Bars) $21.49
                                                                      [B008D2X8C4] Enjoy Life Lentil Chips Variety Pack, Dairy
Action: think[The item has options ‘variety pack’ and ‘0.8            Free Chips, Soy Free, Nut Free, Non GMO, Vegan, Gluten
ounce (pack of 24)’ and seems good to buy.]                           Free, 24 Bags (0.8 oz) $100.0
Observation: OK.                                                      Action: think[The first two items are not what I want. The
                                                                      third item is the dairy free and apple variety pack of chips I
                                                                      want.] Observation: OK.
Action: click[variety pack]
                                                                      Action: click[B008D2X8C4] Observation: [Back to Search]
Observation: You have clicked variety pack.
                                                                      [< Prev] flavor name [dill and sour cream][garlic & parme-
                                                                      san][light sea salt][margherita pizza][thai chili lime][variety
Action: click[0.8 ounce (pack of 24)]                                 pack] size [0.8 ounce (pack of 24)][4 ounce (pack of 12)]
                                                                      Price: $100.0 Rating: N.A. [Description] [Features] [Re-
Observation: You have clicked 0.8 ounce (pack of 24).
                                                                      views] [Buy Now]
                                                                      Action: think[The item has options ‘variety pack’ and ‘0.8
Action: click[Buy Now]
                                                                      ounce (pack of 24)’ and seems good to buy.] Observation:
                                                                      OK.
Reflection: In this attempt, I was unsuccessful. I acciden-
                                                                      Action: click[variety pack] Observation: You have clicked
tally bought a product that was $100, which is more than my
                                                                      variety pack.
budget of $30. Either way, the initial search results were not
good. Next time, I will do search[“variety pack of chip”;]            Action: click[0.8 ounce (pack of 24)] Observation: You
and then check if the results meet the dairy free and the $30         have clicked 0.8 ounce (pack of 24).
budget constraints. I will continue to refine my searches so
                                                                      Action: click[Buy Now]
that I can find more products.
                                                                      STATUS: FAIL
Thus the correctness score is 5
                                                                      Reflection: In this attempt, I was unsuccessful. I acciden-
                                                                      tally bought a product that was $100, which is more than my
(input)
                                                                      budget of $30. Either way, the initial search results were not
                                                                      good. Next time, I will do search[“variety pack of chips”]
G.3. Reflection Prompt                                                and then check if the results meet the dairy free and the $30
You are an advanced reasoning agent that can improve based            budget constraints. I will continue to refine my searches so
on self-reflection. You will be given a previous reasoning            that I can find more products.
trial in which you were given access to a shopping website            Previous Trial Instruction: i need gluten free vegetarian
and a specific type of item to buy. You were given access             smoked peppered bacon - 4 ounce (pack of 2), and price
to relevant context and an item to purchase. You were un-             lower than 40.00 dollars [Search]
successful in buying the correct item either because you did
not find an item meeting all of the required specifications           Action: search[gluten free vegetarian smoked peppered ba-
or because you did not select the correct item. The ideal             con 4 ounce pack of 2] Observation: [Back to Search] Page
score is 1.0, and anything less is incorrect. In a few sen-           1 (Total results: 50) [Next >] [B06Y96MXJV] Smoked
tences, Diagnose a possible reason for failure and devise a           Bacon Sea Salt 3-Pack: Smoked Bacon Chipotle, Smoked
new, concise, high-level plan that aims to mitigate the same          Bacon and Onion, Smoked Peppered Bacon - All-Natural
failure. Use complete sentences. Here are some examples:              Sea Salts Slowly Smoked Over Alderwood - No Gluten, No
                                                                      MSG, Non-GMO (12 total oz.) $29.99 [B06Y96N1KG]
Previous Trial Instruction: i am looking for dairy free and           Spicy Hot Pepper Sea Salt 3-Pack: Ghost Pepper, Jalapeno,
apple variety pack of chips, and price lower than 30.00               Habanero - All Natural, Delicious Blends of Peppers & Sea
dollars [Search]                                                      Salt - Gluten-Free, Kosher, No MSG, Non-GMO (12 total
Action: search[dairy free and apple variety pack of chips]            oz.) $29.99 [B07GJTKYJQ] Louisville Vegan Jerky - 5
Observation: [Back to Search] Page 1 (Total results: 50)              Flavor Variety Pack, Non-GMO Soy Protein, Gluten-Free
[Next >] [B07HRFJWP8] Enjoy Life Foods Soft Baked                     (Black Pepper, Buffalo Dill, Pepperoni, Maple Bacon, and
Ovals, Breakfast Bars, Nut Free Bars, Soy Free, Dairy Free,           Carolina BBQ, 3 Ounces) $42.99
Non GMO, Gluten Free, Vegan, Variety Pack, 4 Boxes

                                                                 22
                   Language Agent Tree Search Unifies Reasoning, Acting, and Planning in Language Models

Action: think[The first two items are not what I want. The
third item is not what I want, but it is the closest one.]
Observation: OK.
Action: click[B07GJTKYJQ] Observation: [Back to
Search] [< Prev] Louisville Vegan Jerky - 5 Flavor Variety
Pack, Non-GMO Soy Protein, Gluten-Free (Black Pepper,
Buffalo Dill, Pepperoni, Maple Bacon, and Carolina BBQ,
3 Ounces) Price: $42.99 Rating: N.A. [Description] [Fea-
tures] [Reviews] [Buy Now]
Action: think[The price is too high and it is not what I want.]
Observation: OK.
Action: click[< Prev] Observation: [Back to Search] Page
1 (Total results: 50) [Next >] [B06Y96MXJV] Smoked
Bacon Sea Salt 3-Pack: Smoked Bacon Chipotle, Smoked
Bacon and Onion, Smoked Peppered Bacon - All-Natural
Sea Salts Slowly Smoked Over Alderwood - No Gluten,
No MSG, Non-GMO (12 total oz.) 29.99 [B06Y96N1KG]
Spicy Hot Pepper Sea Salt 3-Pack: Ghost Pepper, Jalapeno,
Habanero - All Natural, Delicious Blends of Peppers &
Sea Salt - Gluten-Free, Kosher, No MSG, Non-GMO (12
total oz.) 29.99 [B07GJTKYJQ] Louisville Vegan Jerky - 5
Flavor Variety Pack, Non-GMO Soy Protein, Gluten-Free
(Black Pepper, Buffalo Dill, Pepperoni, Maple Bacon, and
Carolina BBQ, 3 Ounces) 42.99
Action: think[The first two items are not what I want.]
Observation: OK.
Action: click[Next >] Observation: Invalid action!
Action: think[I need to refine my search.] Observation: OK.
Action: click[< Back to Search] Observation: Invalid ac-
tion!
Action: click[Back to Search]
STATUS: FAIL
Reflection: In this attempt, I was unsuccessful. The initial
search results were not the products that I was looking for.
Next time, I will do search[“vegetarian bacon”] for a broader
search. I will check that the new results will fulfill the gluten
free and 4 ounce pack of 2 constraints. I will continue to
refine my searches so that I can find more products.
Previous trial: trajectory Reflection:”’




                                                                    23
