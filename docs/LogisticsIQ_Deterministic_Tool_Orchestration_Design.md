# LogisticsIQ: Moving to Deterministic Tool Orchestration

**Status:** Proposed architectural change\
**Project:** LogisticsIQ -- AI-Powered Logistics Decision Intelligence
Platform\
**Phase:** Phase 4 -- Intelligence\
**Scope:** Reliable execution of transportation-cost prediction and
warehouse-scheduling capabilities

## 1. Executive summary

LogisticsIQ currently uses a LangGraph ReAct-style agent backed by
Ollama/Qwen3. The agent receives a natural-language request, decides
whether to call one or more tools, and generates a response.

The individual tool flows have been demonstrated:

-   A warehouse-scheduling request resulted in a call to the Phase 3
    optimization API.
-   A transportation-cost request resulted in a call to the Phase 2
    prediction API.

A later combined request asked the agent to perform both operations. It
returned a detailed cost estimate, dock schedule, and operational
recommendation, but the expected Phase 2 and Phase 3 backend requests
were not visible in the Uvicorn logs.

The response also repeated a cost figure from an earlier test. Since the
downstream calls were not observed, neither result could be verified as
a fresh output from the LightGBM model or CP-SAT solver.

This exposes a reliability limitation: **an LLM can generate a plausible
answer without executing the tools required to substantiate it.**

The proposed change is to move from relying solely on model-selected
tool calls to an **application-controlled orchestration workflow**. The
application will identify required operations, validate inputs, execute
the relevant APIs, verify their results, and only then ask the LLM to
explain those results.

The LLM remains responsible for natural-language understanding, input
extraction, clarification, and explanation. It will no longer be the
sole authority responsible for deciding whether mandatory business
operations actually execute.

## 2. Background and current architecture

LogisticsIQ combines predictive machine learning, mathematical
optimization, and conversational AI.

  -----------------------------------------------------------------------
  Capability              Implementation          Responsibility
  ----------------------- ----------------------- -----------------------
  Transportation cost     Phase 2 -- LightGBM     Estimate cost from
  prediction                                      shipment features

  Warehouse scheduling    Phase 3 -- OR-Tools     Propose a dock schedule
                          CP-SAT                  

  Conversational          Phase 4 -- LangGraph +  Interpret requests and
  intelligence            Ollama/Qwen3            communicate results

  API layer               FastAPI                 Expose prediction,
                                                  optimization, and
                                                  intelligence endpoints
  -----------------------------------------------------------------------

### 2.1 Existing request flow

1.  FastAPI receives `POST /api/v1/intelligence/query`.
2.  The intelligence route invokes the LangGraph agent.
3.  The LLM receives the conversation and available tool descriptions.
4.  The LLM decides whether to call a tool or respond directly.
5.  If selected, a tool calls the relevant internal FastAPI endpoint.
6.  The tool result is returned to the agent.
7.  The LLM generates a natural-language response.

Available tools:

-   `predict_transportation_cost` calls
    `POST /api/v1/predictions/transportation-cost`.
-   `optimize_warehouse_schedule` calls
    `POST /api/v1/optimization/warehouse-schedule`.

The existing separation between tools and backend APIs is useful. The
prediction and optimization services can be tested independently and
reused by other application components.

### 2.2 Current design limitation

In a ReAct-style workflow, the model generally controls whether to
invoke a tool. Tool descriptions and system-prompt instructions
influence that decision, but they do not enforce execution.

For example, a prompt may instruct the model to use the prediction tool
whenever a user asks for a cost estimate. That instruction is guidance,
not an application-level guarantee. The model may still generate a final
response without making the required tool call.

## 3. Observed issue: Combined request did not demonstrate tool execution

### 3.1 Test scenario

A combined request asked LogisticsIQ to:

1.  Estimate transportation cost using the Phase 2 LightGBM model.
2.  Treat the shipment as an incoming warehouse load.
3.  Optimize its dock assignment using the Phase 3 OR-Tools API.
4.  Present both results and an operational recommendation.

The request included shipment features and load details.

### 3.2 Expected behaviour

The expected backend activity was:

``` text
POST /api/v1/intelligence/query
POST /api/v1/predictions/transportation-cost
POST /api/v1/optimization/warehouse-schedule
```

Both capability APIs should execute before LogisticsIQ presents their
results.

### 3.3 Actual observation

The agent returned a detailed answer containing a transportation-cost
figure, a dock assignment and processing interval, claims about waiting
time and dock utilization, and an operational recommendation.

However, the expected prediction and optimization requests were not
visible in the Uvicorn logs during this test. The answer also repeated
the same cost figure that had appeared in an earlier individual
prediction test.

The correct conclusion is not that Phase 2 or Phase 3 is broken. Both
APIs had worked independently, and each tool had been invoked
successfully in separate agent tests. The combined test did not
demonstrate reliable execution of both required tools.

### 3.4 Why this is a reliability issue

A natural-language answer is not evidence that a backend operation
occurred.

Without observing and validating the API response:

-   A transportation-cost figure cannot be claimed as a fresh LightGBM
    prediction.
-   A dock assignment cannot be claimed as the output of the CP-SAT
    optimizer.
-   Recommendations may be based on model-generated assumptions rather
    than verified system results.
-   Users may interpret a proposed schedule as solver-validated when it
    was not.

## 4. Architectural cause

The current design delegates two responsibilities to the LLM:

1.  Interpreting what the user wants.
2.  Deciding whether the application should execute the required
    business operation.

These responsibilities should be separated.

### 4.1 LLM output is probabilistic

LLMs generate responses based on learned patterns, prompts, conversation
context, and available tool interfaces. Tool-calling support does not
guarantee that every relevant request results in a tool call.

The model may decide it has enough context to answer, overlook one of
several required tool calls, or produce a plausible answer directly.

### 4.2 Prompt-only enforcement is insufficient

Stronger instructions such as "always call both tools" may improve
behaviour, but they do not provide a deterministic guarantee. A
production system should enforce mandatory operations in application
code and verify their outcomes.

### 4.3 Conversation history can contaminate operational answers

The repeated cost figure illustrates why previous assistant responses
must not be treated as current tool results.

Conversation history can help interpret follow-up questions, but a new
prediction or optimization request should execute against the current
inputs unless the application explicitly implements and validates a
cache policy.

### 4.4 Plausible answers can hide missing execution

The response was detailed and internally plausible. That makes the issue
particularly important: users may not notice that the underlying model
or solver was never called.

LogisticsIQ must distinguish between: - An LLM-generated explanation. -
A verified prediction returned by Phase 2. - A verified schedule
returned by Phase 3.

## 5. Proposed architecture: Application-controlled orchestration

The proposed design introduces an explicit orchestration layer between
natural-language understanding and backend execution. Application logic,
rather than the LLM alone, determines and enforces which required
operations must run.

``` text
                         User
                           |
                           v
                 Intelligence API
                           |
                           v
                Request Understanding
                    (LLM / Parser)
                           |
                           v
                 Intent & Input Extraction
                           |
                           v
                  Input Validation
                     /         \
                    /           \
             Missing data?     Valid inputs
                  |                |
                  v                v
             Clarification    Orchestrator
                                  |
                       +----------+----------+
                       |                     |
                       v                     v
                Prediction Task       Optimization Task
                       |                     |
                       v                     v
                 Phase 2 API            Phase 3 API
                 LightGBM               OR-Tools CP-SAT
                       |                     |
                       v                     v
                 Prediction Result     Schedule Result
                       |                     |
                       +----------+----------+
                                  |
                                  v
                         Result Validation
                                  |
                                  v
                       Response Generation
                              (LLM)
                                  |
                                  v
                            User Response
```

Independent operations may execute sequentially or concurrently,
provided dependencies and failure handling are explicit.

### 5.1 Responsibilities

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Intelligence API                    Receive and validate the user
                                      request

  Request understanding               Interpret natural language and
                                      extract structured inputs

  Intent identification               Determine which business
                                      capabilities are requested

  Input validation                    Check required fields, types,
                                      ranges, and domain constraints

  Orchestrator                        Enforce execution of every required
                                      operation

  Phase 2 API                         Return the actual
                                      transportation-cost prediction

  Phase 3 API                         Return the actual warehouse
                                      optimization result

  Result validation                   Confirm which operations succeeded
                                      and validate response structure

  Response generation                 Explain verified results and
                                      disclose failures or limitations
  -----------------------------------------------------------------------

The LLM remains part of the workflow, but it cannot silently skip an
operation that the application has determined is mandatory.

## 6. Target execution behaviour

### 6.1 Transportation prediction

Example: "Estimate the transportation cost for a 500 km shipment
weighing 2,000 kg."

Expected workflow:

1.  Identify the transportation prediction intent.
2.  Extract all required model features.
3.  Identify missing features.
4.  Ask for missing information rather than inventing values.
5.  Validate the feature set.
6.  Invoke the Phase 2 prediction API.
7.  Validate the API response.
8.  Generate an explanation using the returned prediction.

### 6.2 Warehouse optimization

Example: "Optimize the warehouse schedule for these incoming loads using
three docks."

Expected workflow:

1.  Identify the warehouse optimization intent.
2.  Extract load information and warehouse constraints.
3.  Check that required load fields are available.
4.  Ask for missing information.
5.  Validate scheduling inputs.
6.  Invoke the Phase 3 optimization API.
7.  Validate the solver response and status.
8.  Explain the proposed schedule using the actual API result.

### 6.3 Combined prediction and optimization

Example: "Estimate the transportation cost for this shipment and
optimize its warehouse dock schedule."

Expected workflow:

1.  Identify both required operations.
2.  Extract and validate prediction inputs.
3.  Extract and validate scheduling inputs.
4.  If either operation lacks required information, ask for
    clarification before execution, unless partial execution is an
    explicitly supported product behaviour.
5.  Execute the Phase 2 prediction API.
6.  Execute the Phase 3 optimization API.
7.  Verify both results independently.
8.  Generate a combined response that clearly separates prediction and
    optimization results.

A successful prediction must not be treated as evidence that
optimization succeeded, or vice versa.

### 6.4 Independent versus dependent operations

The initial combined workflow contains two independent calculations:
transportation-cost prediction and warehouse dock scheduling.

The predicted transportation cost does not currently influence the
CP-SAT scheduling objective. The application must not imply that the
optimizer used the cost prediction unless a future design explicitly
adds that dependency.

## 7. Reliability and safety requirements

### 7.1 Mandatory execution

If a request requires a capability and its inputs are valid, the
orchestrator must invoke the corresponding backend API. The LLM must not
replace a required API result with an invented answer.

### 7.2 No fabricated results

If a backend operation has not succeeded, the final response must not
present a prediction or schedule as though it came from the
corresponding model or solver.

-   Do not display a transportation-cost estimate if the prediction API
    failed.
-   Do not display dock assignments if the optimization API failed.
-   Do not reuse a previous conversation's prediction as a new
    prediction.

### 7.3 Explicit result provenance

Each result should retain enough information to identify its origin:

-   Capability name.
-   Backend endpoint or operation.
-   Execution status.
-   Validated result payload.
-   Relevant request inputs.
-   Error details when execution fails.

Where useful, add a request or correlation ID to trace the user request
through the intelligence endpoint and downstream APIs.

### 7.4 Partial failure handling

The combined workflow must define what happens when only one operation
succeeds.

  -----------------------------------------------------------------------
  Prediction API          Optimization API        Expected response
  ----------------------- ----------------------- -----------------------
  Success                 Success                 Present both verified
                                                  results

  Success                 Failure                 Present verified
                                                  prediction and clearly
                                                  report optimization
                                                  failure

  Failure                 Success                 Present verified
                                                  schedule and clearly
                                                  report prediction
                                                  failure

  Failure                 Failure                 Report that neither
                                                  operation completed
                                                  successfully
  -----------------------------------------------------------------------

A partial success must never be represented as complete success.

### 7.5 Input validation

Validation should happen before backend execution.

Examples: - Required prediction features must be present. - Numeric
inputs must have appropriate types and valid ranges. - Month must be
within the supported range. - Each load must contain required scheduling
fields. - Dock count and scheduling horizon must be valid. - Missing or
invalid values must trigger clarification or a validation error.

The backend APIs remain the final authority for their own domain
validation.

### 7.6 Timeouts and retries

Use explicit timeouts and carefully controlled retry behaviour.

-   Do not retry indefinitely.
-   Avoid retries that may cause duplicate side effects.
-   Prediction and optimization are computational operations, but retry
    policies should still be bounded.
-   Return a clear failure status when a downstream API is unavailable
    or times out.

### 7.7 Human approval and operational boundaries

Warehouse optimization currently produces a proposed schedule. It does
not execute physical warehouse actions.

LogisticsIQ must distinguish: - Predicted transportation costs from
actual invoice costs. - Proposed schedules from executed schedules. -
Recommendations from approved operational decisions.

Any future capability that changes real warehouse operations must have
explicit authorization, validation, and appropriate human approval.

## 8. Implementation plan

The change should be incremental to preserve completed Phase 1, Phase 2,
and Phase 3 work.

### Step 1: Review the current LangGraph workflow

Inspect: - `app/agent/graph.py` - `app/agent/tools.py` -
`app/agent/config.py` - `app/api/routes/intelligence.py`

Identify where the current ReAct agent makes tool-selection decisions
and how tool results are returned.

### Step 2: Introduce explicit intent representation

Define a structured representation of requested capabilities, for
example:

``` json
{
  "intents": [
    "transportation_cost_prediction",
    "warehouse_schedule_optimization"
  ]
}
```

Validate the intent representation before execution. Also represent
missing inputs and unsupported requests rather than silently filling
them with defaults.

### Step 3: Extract structured inputs

Use the LLM or deterministic parsing to extract inputs for each
capability.

Prediction inputs must map to the actual Phase 2 request schema.
Scheduling inputs must map to the actual Phase 3 request schema. Treat
the backend Pydantic models as the source of truth for payload
compatibility.

### Step 4: Validate before execution

Check whether all required fields are present and valid. If required
information is missing, return a clarification response without claiming
the operation was completed.

### Step 5: Implement the orchestrator

Create an application-controlled workflow that:

1.  Receives validated intent and inputs.
2.  Invokes every required capability.
3.  Captures each result and execution status.
4.  Handles partial failures.
5.  Passes only verified results to response generation.

The orchestrator may use LangGraph nodes for these stages. Mandatory
execution must be controlled by the workflow, not left solely to an
unconstrained model decision.

### Step 6: Separate execution from explanation

The LLM should receive verified tool outputs and generate a business
explanation. It should not invent missing outputs or infer unsupported
model explanations.

For example, if the prediction service does not return SHAP values or
feature attribution, the LLM must not present feature contributions as
though they were calculated by the model.

### Step 7: Add observability

Log: - Incoming request ID. - Detected intents. - Validation outcome. -
Required tool names. - Tool invocation start and completion. - Backend
status codes. - Execution duration. - Success or failure status.

Avoid logging secrets or unnecessary sensitive shipment information.

## 9. Testing strategy and acceptance criteria

The redesigned architecture should be accepted only after these
scenarios pass.

  -----------------------------------------------------------------------
  Test                    Scenario                Expected behaviour
  ----------------------- ----------------------- -----------------------
  T01                     General informational   Respond without calling
                          question                prediction or
                                                  optimization APIs

  T02                     Prediction request with Ask for missing
                          missing inputs          information; do not
                                                  fabricate values

  T03                     Valid prediction        Phase 2 API is invoked
                          request                 and its result is used

  T04                     Optimization request    Ask for missing
                          with missing load       information
                          fields                  

  T05                     Valid optimization      Phase 3 API is invoked
                          request                 and its result is used

  T06                     Combined request with   Both APIs are invoked
                          complete inputs         

  T07                     Combined request,       Report prediction
                          prediction API fails    failure; do not invent
                                                  a cost

  T08                     Combined request,       Report optimization
                          optimization API fails  failure; do not invent
                                                  a schedule

  T09                     Both APIs fail          Report that neither
                                                  operation completed

  T10                     Repeated request in an  Execute a fresh
                          existing thread         operation unless a
                                                  deliberate, validated
                                                  cache policy applies

  T11                     Model produces          Do not present
                          unsupported explanation unsupported claims as
                                                  verified model or
                                                  solver output

  T12                     General question        Distinguish historical
                          referencing previous    conversation context
                          results                 from newly executed
                                                  calculations
  -----------------------------------------------------------------------

### Critical acceptance criteria

1.  A valid combined request invokes both required backend APIs.
2.  API execution is visible in logs or structured traces.
3.  The final response uses actual API results.
4.  A failed operation cannot be represented as successful.
5.  Missing inputs trigger clarification rather than invented defaults.
6.  Previous conversation outputs cannot silently substitute for fresh
    predictions or schedules.
7.  Existing Phase 2 and Phase 3 endpoints continue to work
    independently.

## 10. Impact on existing project components

  -----------------------------------------------------------------------
  Component                           Expected impact
  ----------------------------------- -----------------------------------
  Phase 1 -- Platform foundation      No functional change

  Phase 2 -- Transportation           No model change; API reused
  prediction                          

  Phase 3 -- Warehouse optimization   No solver change; API reused

  Phase 4 -- Intelligence route       May need request/response workflow
                                      adjustments

  `app/agent/graph.py`                Main area of workflow redesign

  `app/agent/tools.py`                Existing tools can be reused and
                                      hardened

  `app/agent/config.py`               No major change expected

  Tests                               Add orchestration, failure, and
                                      provenance tests

  Documentation                       Update architecture and technical
                                      decisions
  -----------------------------------------------------------------------

The existing public intelligence endpoint can remain:

``` text
POST /api/v1/intelligence/query
```

The request contract can also remain unchanged initially:

``` json
{
  "message": "Estimate cost and optimize the warehouse schedule.",
  "thread_id": null
}
```

This preserves the API interface while the internal orchestration
architecture changes.

## 11. Alternatives considered

### Alternative A: Strengthen the system prompt

**Description:** Add stronger instructions telling Qwen3 to invoke all
relevant tools.

**Advantages:** - Very little code change. - Quick to test. - Retains
the current ReAct architecture.

**Disadvantages:** - Does not guarantee tool execution. - Behaviour
remains dependent on model decisions. - Difficult to enforce partial
failure handling. - Does not provide deterministic execution guarantees.

**Decision:** Not sufficient as the primary reliability solution. Prompt
improvements can still be supporting guidance.

### Alternative B: Continue using unconstrained ReAct tool selection

**Description:** Keep the current architecture and rely on the model to
select one or multiple tools.

**Advantages:** - Flexible. - Suitable for exploratory agent
workflows. - Simple for open-ended questions.

**Disadvantages:** - Mandatory business operations may be skipped. -
Combined tool execution can be inconsistent. - Harder to enforce
execution contracts and provenance.

**Decision:** Retain only where autonomous tool selection is appropriate
and execution is not mandatory.

### Alternative C: Application-controlled orchestration

**Description:** Use the LLM for request understanding and response
generation, while application logic enforces mandatory tool execution.

**Advantages:** - Predictable execution. - Clear validation
boundaries. - Better error handling. - Easier to test. - Better
observability and traceability. - Reduced risk of fabricated operational
results.

**Disadvantages:** - Requires explicit workflow and state management. -
More implementation and testing effort. - Requires clear intent and
input schemas.

**Decision:** Recommended for LogisticsIQ's core prediction and
optimization operations.

## 12. Expected outcome

After implementation, LogisticsIQ should operate as a reliable
decision-support application rather than relying entirely on an LLM's
autonomous tool-selection behaviour.

Target responsibilities:

-   **LLM:** Understand user requests, extract information, ask
    clarifying questions, and explain verified results.
-   **Application orchestrator:** Enforce execution, validate inputs,
    manage workflow state, and handle failures.
-   **Phase 2 ML service:** Produce transportation-cost predictions.
-   **Phase 3 optimization service:** Produce warehouse scheduling
    results.
-   **Observability layer:** Provide evidence of which operations ran
    and whether they succeeded.

> **The LLM may decide how to explain a result, but the application must
> control whether a required business operation has actually executed.**

This change improves the reliability, testability, and production
readiness of LogisticsIQ while preserving the existing predictive ML and
optimization engines.
