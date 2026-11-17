# Response Lab

My RAG chatbot found the right passages, but the answers were sometimes too long, cited only a number, or added a dose that was not in the guideline. This project fixes that on purpose. First I wrote a benchmark that says what a good response looks like. Then I tried six prompt versions and measured each one against it.

The five guidelines in `guidelines/` are made up for learning. This is not medical advice.

<!-- add a screenshot of the running app here, e.g. ![app](screenshot.png) -->

## What I did

1. **Benchmark.** 35 questions with the expected facts, the expected source (document and page), a word limit, and traps that must not appear. The rules are in `benchmark/RESPONSE_STANDARD.md`.
2. **Prompt versions.** Six system prompts, each adding one idea (table below).
3. **Citations with section and page.** The model writes `[2: Medicines > First choice, p. 2]`. Code checks it against the passage header. A wrong section or page is fixed or dropped, so the sources shown under an answer are always real.
4. **Less hallucination.** Fixed refusal sentence, refuse when the exact detail is missing, and a code check that stops any number that is not in the cited passages.
5. **Evaluation.** Every version is scored on the same questions with rule-based checks.

## The benchmark questions

| Type | Count | What it tests |
| --- | --- | --- |
| fact | 9 | one fact, such as a number or a drug |
| multi | 8 | several facts, lists and tables |
| lay | 3 | everyday wording |
| emergency | 3 | the emergency step must come first |
| trap | 6 | the guideline covers the topic but not the detail (a dose, a length of treatment) |
| outside | 6 | the guideline does not cover it at all |

## The prompt versions

| Version | What it adds |
| --- | --- |
| v0 Plain | one line, no rules |
| v1 Previous prompt | the prompt my chatbot used before |
| v2 Grounded | fixed refusal sentence, refuse when the detail is missing, copy numbers exactly |
| v3 Concise | direct answer first, 3 short sentences, plain words, no meta talk |
| v4 Section and page | citations carry the section and page |
| v5 Final | emergency rule, two examples, and the code guard |

Only the system prompt changes. The passages and the question are sent the same way every time. An extractive row (copied sentences, no model) is added for comparison.

## How a response is scored

| Check | Passes when |
| --- | --- |
| Key facts included | every expected fact is in the answer |
| Refuses only when it should | refuses what the guideline cannot answer, answers what it can |
| No made-up facts | no number outside the passages, none of the trap answers |
| Every sentence cited | at least 80% of sentences carry a valid [n] |
| Right source cited | a cited passage is on the expected page of the expected document |
| Short enough | within the word limit |
| Emergency step first | emergency questions start with the emergency step |
| Plain style | no "the passages", "the context", "as an AI" |
| Section and page correct | only for v4 and v5: the written section and page match the passage header |

A response passes only if every check that applies to it passes.

## The guard (v5)

- A reference with the wrong section or page is moved to the passage it names, or dropped.
- No valid citation left: the extractive answer is used instead.
- A number that is not in the cited passages: the extractive answer is used instead.
- Sentences without a citation are removed when other sentences are cited.
- An emergency notice is added in front when the question needs one.
- Citations are renumbered `[1] [2]` and the source list shows document, section and page.

## Folder structure

```
response_lab/
  app.py                    Streamlit app
  run_benchmark.py          runs the benchmark in the terminal
  requirements.txt
  .env                      my Groq key (not on GitHub)
  .streamlit/config.toml    theme
  benchmark/
    response_benchmark.json 35 questions with expected facts and sources
    RESPONSE_STANDARD.md    what a good response looks like
  gen/
    prompts.py              the six system prompts
    system.py               builds the context, calls the model, caches answers
    guard.py                citation, reference and number checks
    checks.py               the scoring rules
    runner.py               runs prompts over the benchmark and summarises
    findings.py  report.py  summary lines and markdown report
    llm.py  kbase.py        Groq call with retries, document reading and search
  components/               one file per tab, sidebar, styles
  guidelines/  tools/       example PDFs and the script that makes them
  ingest/  kb/  rag/        reader, chunker and embeddings from the RAG project
  results/                  saved model answers and reports
  tests/
```

## Run it (Windows, VS Code)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Open `.env`, replace `your_key_here` with your Groq key, then:

```powershell
streamlit run app.py
```

Terminal version, saves `results\report.md`:

```powershell
python run_benchmark.py
python run_benchmark.py --prompts v1 v5 extractive
python run_benchmark.py --limit 10
```

The first full run calls the model 210 times (6 prompts x 35 questions), spaced out to stay under the rate limit, so it takes about 10 minutes. Answers are saved in `results/llm_cache.json`. Running again with the same prompts is instant.

## Tabs

- **Try it:** ask any question with any prompt version. See the answer, the sources, what the guard did, the raw model output and the passages sent. Benchmark questions also show the checks.
- **Benchmark:** the standard and the 35 questions.
- **Compare prompts:** run the versions and compare scores, by question type, with the failing questions.
- **Examples:** one question, every version side by side.
- **Prompts:** the text of each prompt and what changed.
- **Findings:** summary lines from the run and a report to download.

## Tests

```powershell
python -m pytest
```

They use a fake model, so no key is needed.

## My results

Setup: 35 benchmark questions (23 should be answered, 12 should be refused), openai/gpt-oss-120b through Groq, MiniLM embeddings, top 4 passages, retrieval gate off so the prompt is what gets tested.

**Prompt comparison**

| Prompt | Pass rate | Score | Key facts | No made-up facts | Cited | Right source | Short | Refuses right | Words |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v0 Plain | 0% | 55% | 61% | 80% | 0% | 0% | 57% | 66% | 69 |
| v1 Previous prompt | 57% | 90% | 78% | 97% | 57% | 70% | 100% | 97% | 21 |
| v2 Grounded | 57% | 88% | 83% | 94% | 43% | 70% | 100% | 97% | 20 |
| v3 Concise | 66% | 93% | 74% | 100% | 70% | 96% | 100% | 97% | 18 |
| v4 Section and page | 71% | 95% | 83% | 100% | 78% | 100% | 100% | 97% | 18 |
| v5 Final | 71% | 95% | 61% | 100% | 100% | 100% | 100% | 97% | 16 |
| Extractive (no model) | 40% | 81% | 70% | 100% | 91% | 96% | 71% | 69% | 37 |

**Section and page written by the model**

| Prompt | Correct |
| --- | --- |
| v4 Section and page | 91% |
| v5 Final | 91% |

**By question type (v5 Final)**

| Type | Questions | Pass rate |
| --- | --- | --- |
| fact | 9 | 100% |
| outside | 6 | 100% |
| trap | 6 | 83% |
| lay | 3 | 67% |
| emergency | 3 | 33% |
| multi | 8 | 25% |

**What the guard did on v5:** 17 kept as written, 11 refused, 5 cleaned (sentences without a citation removed), 2 sent back to the extractive answer.

**What I noticed**

- The pass rate went from 0% with the plain prompt to 71% with the final one. The average score went from 55% to 95%.
- The biggest jump was Plain to Previous prompt (+57%). Just telling the model to use only the passages, cite them and refuse fixed most problems.
- Made-up facts went from 20% of answers to 0%. Correct refusals went from 0% to 92% (11 of 12), and no good question was refused.
- Answers got much shorter: 69 words on average with the plain prompt, 16 with the final one.
- Citations improved the most. The right source was cited in 0% of plain answers and 100% of final answers. Asking for the section and page took v3 from 70% cited to 78% in v4, and the guard took it to 100%.
- The model wrote the section and page correctly in 91% of its answers. The other 9% were fixed or dropped by the guard, so the sources shown are always real.
- The short-answer rule in v3 cost some facts (key facts fell from 83% to 74%).
- The final version has the same pass rate as v4 (71%), but its key facts fell from 83% to 61%. In 5 of the 6 failed multi-fact questions, the guard had removed sentences that had no citation. Lists with one citation for several lines lost their uncited lines.
- Still failing on v5: R10, R12, R13, R14, R15, R16 (multi-fact), R19 (everyday wording), R22 and R23 (emergency) all missed key facts. R25 (the starting dose of metformin) got an answer instead of a refusal.
- The old extractive answer never made anything up, but it passed only 40% of the questions. It missed facts, was too long, and refused only 69% of the time it should.

**Next fix:** stop the guard removing list lines, or make the model cite every list line, so multi-fact answers keep their facts.

**Limitations**

- Only 35 questions, written by me against five short guidelines.
- The checks are rules, so a fact written in different words can be missed.
- Model answers change slightly between runs. The saved answers keep the comparison fair.
- The guard checks references, numbers and citation marks. It cannot tell if a cited sentence really supports the claim.
