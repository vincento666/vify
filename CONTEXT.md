# Hify Workflow Context

Hify workflow context names the business objects used to build deterministic and conversational automation flows.

## Language

**Workflow**:
A deterministic flow for one-shot or repeatable business tasks. A Workflow is edited from the Workflow list and does not treat conversation state as its default concern.
_Avoid_: Chatflow, raw DAG

**Chatflow**:
A conversational flow that uses workflow-style node orchestration while carrying conversation-related inputs and variables. A Chatflow is edited from the Chatflow list and is expected to know which conversation, channel, and user context it is running within.
_Avoid_: Workflow when the flow depends on conversation state

**Flow Type**:
The business category that separates Workflow from Chatflow while allowing both to use the same canvas language. A Flow Type is visible in product navigation and resource lists.
_Avoid_: hidden technical flag

**Execution Substrate**:
The domain-neutral Module that owns durable background job lifecycle, including enqueue, claim, lease, heartbeat, retry, DLQ, cancellation fencing, handler registration, and standalone worker composition. Workflow, Chatflow, and AI Assistant use it through their own Adapters; it does not know their domain semantics.
_Avoid_: Workflow worker, Agent queue

**Agent Harness**:
The shared deep Module that owns domain-neutral Agent turn execution invariants: bounded ReAct progression, planning state, tool invocation governance, context and memory assembly, permission and approval transitions, checkpoints, cancellation, and standard execution events. AI Assistant and Customer Assistant supply product and business Adapters instead of implementing separate harness loops.
_Avoid_: AI Assistant service, generic Agent God Module, Customer Assistant worker loop

**Agent Execution**:
The shared Module for parent/child Agent run identity, lifecycle status, durable references, correlation, and provider Interfaces. Agent Harness uses it for child execution while AI Assistant and Customer Assistant provide child-provider Adapters; it does not own the ReAct loop or business-task semantics.
_Avoid_: generic Agent engine, sub-agent bridge payload

**Execution Activity**:
A user-visible projection of durable execution events into one stable phase, tool, Skill, approval, or child-Agent lifecycle item. It is a read model for the product shell, not a second execution ledger.
_Avoid_: raw event card, hidden reasoning

**Workflow List**:
The entry point for managing Workflow resources. It is a sibling of Chatflow List, not a combined mixed list.
_Avoid_: All flows list

**Chatflow List**:
The entry point for managing Chatflow resources. It is a sibling of Workflow List, not a filter on Workflow List in user language.
_Avoid_: Workflow filter

**Canvas**:
The visual editing surface where a flow is assembled from nodes and edges. A Canvas belongs to either a Workflow or a Chatflow.
_Avoid_: JSON editor, raw graph

**Node**:
The smallest business step in a flow. Each Node exposes readable inputs, configuration, outputs, and run status.
_Avoid_: backend task, executor

**Edge**:
The control-flow connection between two nodes. Data movement is expressed through variable references, not by treating every edge as a data pipe.
_Avoid_: data link

**Variable**:
A named value available to nodes while a flow runs. Variables may be provided externally, produced by nodes, or stored at a global, conversation, or user scope.
_Avoid_: raw path

**System Variable**:
A platform-provided variable that Chatflow can read without the user creating it. System Variables describe the current input, conversation, user, channel, message, time, files, or dialogue round.
_Avoid_: manually configured variable

**Global Variable**:
A variable shared across runs or resources at the product level.
_Avoid_: env var

**Conversation Variable**:
A variable tied to one conversation and used by Chatflow to preserve conversation state.
_Avoid_: session field

**User Variable**:
A variable tied to one user and used by Chatflow to preserve user-level context across conversations.
_Avoid_: profile column

**Channel Variable**:
A variable provided by the external channel where a Chatflow is invoked, such as a channel identifier.
_Avoid_: connector metadata

**Conversation Identity Variable**:
A variable that identifies the active conversation for a Chatflow, such as a conversation identifier or conversation name.
_Avoid_: internal chat id

**Task Stack**:
A future conversation capability that can remember suspended tasks across intent switches. It is not part of the first Chatflow canvas replica.
_Avoid_: interrupt resume

**Chat History Awareness**:
A Chatflow node option that lets a node read recent conversation history while making an LLM-driven decision or extraction. It is separate from Global Variable.
_Avoid_: global context when meaning history

**Message Node**:
A Chatflow node that sends or emits content and then continues the flow without waiting for a user reply.
_Avoid_: Question Node, Dify Output Node

**Question Node**:
A Chatflow node that asks the user for an answer and waits before continuing. It can produce an answer variable and branch by option/default.
_Avoid_: Message Node, Answer Node

**Human Input Node**:
A node that pauses the flow for explicit human-provided input or approval. It is not responsible for automatic information extraction from conversation text.
_Avoid_: Information Collection Node

**Information Collection Node**:
A Chatflow node that uses conversation input and optional chat history to extract required fields, ask for missing fields, merge new answers with collected state, and finish when required information is complete.
_Avoid_: one-shot input form, Human Input Node

**Intent Recognition Node**:
A branch node that uses LLM-driven semantic understanding to choose one configured intent path plus a default path.
_Avoid_: rule-only condition

**Variable Assignment Node**:
A node that writes an existing value into a selected variable scope. It does not parse JSON by itself.
_Avoid_: JSON parsing node

**JSON Parse Node**:
A node that converts a JSON string or JSON-like text from an LLM, API, or code output into structured fields that downstream nodes and Variable Assignment Node can use.
_Avoid_: Variable Assignment Node

**Unified Resource**:
A callable or referenceable product resource that a flow node can attach to, such as a Knowledge Base, MCP Tool, or another Workflow/Chatflow. Unified Resource describes how the author selects the resource; each resource type still has its own runtime contract.
_Avoid_: plugin only, skill only

**Coze Skill Vocabulary**:
Coze uses "resources" broadly for workflows, plugins, databases, knowledge bases, and variables. Coze Chatflow/Agent skill UI includes Knowledge, Plugin, Workflow, and Imageflow, while triggered-skill analytics emphasize plugins and workflows. In Hify, "skill" is a UI affordance; runtime behavior must still be typed by resource kind.
_Avoid_: one runtime path for every skill

**Knowledge Resource**:
A Knowledge Base selected as a resource for retrieval. In the first LLM skill/resource slice it can be invoked before the LLM call and appended as model context.
_Avoid_: tool call

**Tool Resource**:
An MCP tool or MCP server tool selected as a callable resource. Tool Resource execution requires tool schema serialization, tool-call parsing, execution, and a second LLM round.
_Avoid_: knowledge context

**Subworkflow Resource**:
A Workflow or Chatflow selected for explicit nested execution. It must guard against recursion, define input/output mapping, and record nested run evidence.
_Avoid_: implicit intent switch

**LLM Resource Context**:
Retrieved or executed resource results inserted into an LLM node's prompt/messages as context. Knowledge Resource can use this in the current basic phase; Tool Resource and Subworkflow Resource need later runtime slices.
_Avoid_: raw hidden prompt magic

## Example Dialogue

Dev: "Should this support ticket router be a Workflow or Chatflow?"

Domain expert: "If it only classifies a submitted ticket and returns a result, it is a Workflow. If it reads the current conversation, remembers prior replies, and writes back to the same conversation, it is a Chatflow."

Dev: "Where does CHANNEL_ID belong?"

Domain expert: "It is a Channel Variable for Chatflow. It should be visible in the Chatflow canvas variable panel, not mixed into every ordinary Workflow."

Dev: "Should we solve multi-task switching now?"

Domain expert: "No. First ship Workflow and Chatflow as separate resources with a shared canvas. Task Stack is a later conversational capability, not baseline Chatflow."

Dev: "Is collecting missing shipping info a Human Input Node?"

Domain expert: "No. If the flow can extract fields from the conversation and ask only for missing fields, it is an Information Collection Node. Human Input is for explicit pause and manual input or approval."

Dev: "Can the LLM node skill area call tools, knowledge, and subworkflows?"

Domain expert: "Treat them as Unified Resources in the UI. Knowledge can be retrieved and added to LLM Resource Context first. Tools and subworkflows need explicit runtime contracts before they are actually executed."
