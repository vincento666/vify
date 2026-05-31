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

## Example Dialogue

Dev: "Should this support ticket router be a Workflow or Chatflow?"

Domain expert: "If it only classifies a submitted ticket and returns a result, it is a Workflow. If it reads the current conversation, remembers prior replies, and writes back to the same conversation, it is a Chatflow."

Dev: "Where does CHANNEL_ID belong?"

Domain expert: "It is a Channel Variable for Chatflow. It should be visible in the Chatflow canvas variable panel, not mixed into every ordinary Workflow."

Dev: "Should we solve multi-task switching now?"

Domain expert: "No. First ship Workflow and Chatflow as separate resources with a shared canvas. Task Stack is a later conversational capability, not baseline Chatflow."
