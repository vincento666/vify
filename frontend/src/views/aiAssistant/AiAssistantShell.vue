<template>
  <section class="ai-shell" data-testid="ai-assistant-shell">
    <aside class="ai-shell__side" data-testid="ai-assistant-left-column-scroll">
      <div class="ai-shell__brand">
        <ThunderboltOutlined />
        <span>Hify AI 助手</span>
      </div>

      <button
        class="ai-new-session"
        type="button"
        data-testid="ai-assistant-new-session"
        aria-label="新建 AI 助手会话"
        @click="createConversation"
      >
        <PlusOutlined />
        <span>新建会话</span>
      </button>

      <section class="ai-session-list" data-testid="ai-assistant-session-list">
        <article
          v-for="session in sessions"
          :key="session.id"
          class="ai-session"
          :class="{ active: session.id === sessionId }"
          data-testid="ai-assistant-session-row"
        >
          <button class="ai-session__select" type="button" @click="selectSession(session.id)">
            <span class="ai-session__dot" :class="{ statusPulse: session.id === sessionId && sending }" />
            <span class="ai-session__content">
              <strong>{{ sessionDisplayTitle(session) }}</strong>
              <small>{{ statusLabel(session.status) }}</small>
            </span>
          </button>
          <a-button
            class="ai-session__delete"
            data-testid="ai-assistant-delete-session"
            size="small"
            type="text"
            danger
            aria-label="删除会话"
            @click.stop="deleteConversation(session.id)"
          >
            <template #icon><DeleteOutlined /></template>
          </a-button>
        </article>
      </section>
    </aside>

    <main class="ai-console" data-testid="ai-assistant-conversation-window">
      <header class="ai-console__top">
        <div>
          <h1>{{ sessionTitle }}</h1>
        </div>
        <div class="ai-console__actions">
          <router-link class="ai-usage-link" to="/ai-assistant/usage" data-testid="ai-assistant-usage-entry">
            <BarChartOutlined />
            Token 用量
          </router-link>
          <a-button
            data-testid="ai-assistant-clear-history"
            size="small"
            type="text"
            :disabled="!sessionId"
            @click="clearCurrentHistory"
          >
            <template #icon><ClearOutlined /></template>
            清空历史上下文
          </a-button>
        </div>
      </header>

      <section
        class="ai-stream"
        data-testid="ai-assistant-event-stream"
        data-testid-secondary="ai-assistant-center-column-scroll"
      >
        <div v-if="runThreads.length === 0" class="ai-empty">
          <ClockCircleOutlined />
          <span>空闲</span>
        </div>
        <template v-else>
          <template v-for="thread in runThreadsForView" :key="thread.run.id">
        <div
          v-if="runThreadUserMessage(thread)"
          class="ai-message ai-message--user"
          data-testid="ai-assistant-user-message"
        >
          <p>{{ runThreadUserMessage(thread) }}</p>
          <div class="ai-message__meta-row ai-message__meta-row--user">
            <span class="ai-message__actions">
              <a-button
                size="small"
                type="text"
                data-testid="ai-assistant-message-copy"
                aria-label="复制用户消息"
                @click="copyUserMessage(thread)"
              >
                <template #icon><CopyOutlined /></template>
              </a-button>
            </span>
            <span data-testid="ai-assistant-user-message-meta">{{ runThreadStartedAt(thread) }}</span>
          </div>
        </div>
        <AiAssistantActivityFeed
          :activities="runActivities(thread)"
          :expansion-overrides="activityExpansionOverrides"
          @toggle="toggleActivity"
        >
          <template #default="{ nowMs }">
            <template v-for="item in activityFeedItems(thread)" :key="item.id">
              <AiAssistantActivityRow
                v-if="item.kind === 'activity'"
                :activity="item.activity"
                :expanded="isActivityExpanded(item.activity)"
                :now-ms="nowMs"
                :progress="activityProgressForThread(item.activity, thread)"
                @toggle="toggleActivity(item.activity)"
              >
                <section class="ai-activity-event-list">
              <article
                v-for="eventItem in activityTimelineItemsForThread(item.activity, thread)"
                :key="eventItem.id"
                class="ai-event"
                :class="[`tone-${eventToneClass(eventItem, thread)}`, `kind-${eventItem.kind}`]"
                data-testid="ai-assistant-event-card"
              >
                <div class="ai-event__rail">
                  <span
                    class="ai-event__status-icon"
                    data-testid="ai-assistant-event-status-icon"
                    :class="`tone-${eventToneClass(eventItem, thread)}`"
                  >
                    <LoadingOutlined
                      v-if="isEventRunning(eventItem, thread)"
                      class="ai-event__spinner"
                      data-testid="ai-assistant-node-spinner"
                    />
                    <CheckCircleOutlined
                      v-else-if="isEventDone(eventItem, thread)"
                      data-testid="ai-assistant-event-completed-icon"
                    />
                    <component :is="eventStatusIcon(eventItem, thread)" v-else />
                  </span>
                </div>
                <div
                  class="ai-event__body"
                  :data-testid="eventItem.kind === 'model-thought' ? 'ai-assistant-thought-summary' : undefined"
                >
                  <button
                    class="ai-event__head"
                    type="button"
                    data-testid="ai-assistant-event-card-header"
                    :aria-expanded="isEventExpanded(eventItem.id)"
                    @click="toggleEventCard(eventItem.id)"
                  >
                    <strong class="ai-event__title-text">{{ eventItem.title }}</strong>
                    <CollapseChevron
                      class="ai-collapse-chevron"
                      aria-hidden="true"
                      :class="{ expanded: isEventExpanded(eventItem.id) }"
                    />
                  </button>
                  <div
                    v-if="isEventExpanded(eventItem.id)"
                    class="ai-event__details"
                    data-testid="ai-assistant-event-detail-panel"
                  >
                    <div
                      v-if="eventItem.toolInvocations?.length"
                      class="ai-tool-invocation-list"
                      data-testid="ai-assistant-tool-invocation-list"
                    >
                      <article
                        v-for="toolInvocation in eventItem.toolInvocations"
                        :key="toolInvocation.id"
                        class="ai-tool-invocation"
                        :class="`tone-${toolInvocation.tone}`"
                        data-testid="ai-assistant-tool-invocation"
                      >
                        <button
                          class="ai-tool-invocation__header"
                          :class="{ 'ai-tool-invocation__header--shell': toolInvocation.displayMode === 'shell' }"
                          type="button"
                          data-testid="ai-assistant-tool-invocation-header"
                          :aria-expanded="isToolInvocationExpanded(eventItem, toolInvocation)"
                          @click="toggleToolInvocation(eventItem, toolInvocation)"
                        >
                          <span
                            v-if="toolInvocation.displayMode !== 'shell'"
                            class="ai-tool-invocation__status"
                            :class="`tone-${toolInvocation.tone}`"
                          >
                            <LoadingOutlined v-if="toolInvocation.tone === 'running'" class="ai-event__spinner" />
                            <CheckCircleOutlined v-else-if="toolInvocation.tone === 'success'" />
                            <ExclamationCircleOutlined v-else-if="toolInvocation.tone === 'danger'" />
                            <ClockCircleOutlined v-else />
                          </span>
                          <strong>{{ toolInvocation.title }}</strong>
                          <small v-if="toolInvocation.subtitle">{{ toolInvocation.subtitle }}</small>
                          <span>{{ toolInvocation.statusText }}</span>
                          <CollapseChevron
                            class="ai-collapse-chevron"
                            aria-hidden="true"
                            :class="{ expanded: isToolInvocationExpanded(eventItem, toolInvocation) }"
                          />
                        </button>
                        <div
                          v-if="isToolInvocationExpanded(eventItem, toolInvocation) && toolInvocation.displayMode === 'shell'"
                          class="ai-shell-result"
                          data-testid="ai-assistant-shell-result"
                        >
                          <header class="ai-shell-result__header">
                            <span>Shell</span>
                            <a-button
                              class="ai-shell-result__copy"
                              size="small"
                              type="text"
                              aria-label="复制命令结果"
                              data-testid="ai-assistant-shell-result-copy"
                              @click.stop="copyToolInvocationResult(toolInvocation)"
                            >
                              <template #icon><CopyOutlined /></template>
                            </a-button>
                          </header>
                          <pre
                            class="ai-shell-result__output"
                            data-testid="ai-assistant-shell-result-output"
                          >{{ toolInvocationShellOutput(toolInvocation) }}</pre>
                          <footer class="ai-shell-result__footer" :class="`tone-${toolInvocation.tone}`">
                            <CheckCircleOutlined v-if="toolInvocation.tone === 'success'" />
                            <LoadingOutlined v-else-if="toolInvocation.tone === 'running'" class="ai-event__spinner" />
                            <ExclamationCircleOutlined v-else-if="toolInvocation.tone === 'danger'" />
                            <ClockCircleOutlined v-else />
                            <span>{{ toolInvocation.shellResultText || toolInvocation.statusText }}</span>
                          </footer>
                        </div>
                        <dl
                          v-else-if="isToolInvocationExpanded(eventItem, toolInvocation)"
                          class="ai-tool-invocation__details"
                          data-testid="ai-assistant-tool-invocation-details"
                        >
                          <div
                            v-for="row in toolInvocationRows(toolInvocation)"
                            :key="`${row.section}-${row.label}`"
                            class="ai-tool-invocation__row"
                          >
                            <dt>{{ row.section }} · {{ row.label }}</dt>
                            <dd>
                              <pre v-if="row.monospace">{{ row.value }}</pre>
                              <span v-else>{{ row.value }}</span>
                              <span
                                v-if="row.testId === 'ai-assistant-tool-detail-input'"
                                class="ai-event__detail-anchor"
                                data-testid="ai-assistant-tool-detail-input"
                              />
                              <span
                                v-if="row.testId === 'ai-assistant-tool-detail-output'"
                                class="ai-event__detail-anchor"
                                data-testid="ai-assistant-tool-detail-output"
                              />
                            </dd>
                          </div>
                        </dl>
                      </article>
                    </div>
                    <dl v-if="formatEventDetailRows(eventItem).length > 0" class="ai-event__detail-grid">
                      <div
                        v-for="row in formatEventDetailRows(eventItem)"
                        :key="row.label"
                        class="ai-event__detail-row"
                        data-testid="ai-assistant-event-detail-row"
                      >
                        <dt>{{ row.label }}</dt>
                        <dd>
                          <pre v-if="row.monospace">{{ row.value }}</pre>
                          <span v-else>{{ row.value }}</span>
                          <span
                            v-if="row.testId === 'ai-assistant-tool-detail-input'"
                            class="ai-event__detail-anchor"
                            data-testid="ai-assistant-tool-detail-input"
                          />
                          <span
                            v-if="row.testId === 'ai-assistant-tool-detail-output'"
                            class="ai-event__detail-anchor"
                            data-testid="ai-assistant-tool-detail-output"
                          />
                        </dd>
                      </div>
                    </dl>
                  </div>
                  <div v-if="shouldShowApprovalActions(eventItem, thread)" class="ai-event__actions">
                    <a-button
                      size="small"
                      type="primary"
                      data-testid="ai-assistant-approval-approve"
                      @click="approveTimelineItem(eventItem)"
                    >
                      批准
                    </a-button>
                    <a-button
                      size="small"
                      danger
                      data-testid="ai-assistant-approval-deny"
                      @click="denyTimelineItem(eventItem)"
                    >
                      拒绝
                    </a-button>
                  </div>
                </div>
              </article>
                </section>
              </AiAssistantActivityRow>
              <div
                v-else-if="item.kind === 'model-output'"
                class="ai-message ai-message--assistant"
                data-testid="ai-assistant-assistant-message"
              >
                <p>{{ item.item.summary }}</p>
              </div>
            </template>
          </template>
        </AiAssistantActivityFeed>
        <div
          v-if="runThreadFinalAnswer(thread)"
          class="ai-message ai-message--assistant ai-message--completion"
          data-testid="ai-assistant-run-final-answer"
        >
          <p>{{ runThreadFinalAnswer(thread) }}</p>
          <div class="ai-message__meta-row ai-message__meta-row--completion">
            <span class="ai-message__actions">
              <a-button
                size="small"
                type="text"
                data-testid="ai-assistant-completion-copy"
                aria-label="复制完成总结"
                @click="copyFinalAnswer(thread)"
              >
                <template #icon><CopyOutlined /></template>
              </a-button>
              <a-button
                size="small"
                type="text"
                data-testid="ai-assistant-completion-like"
                aria-label="点赞完成总结"
                :class="{ active: completionFeedback[thread.run.id] === 'like' }"
                @click="markFinalAnswerFeedback(thread.run.id, 'like')"
              >
                <template #icon><LikeOutlined /></template>
              </a-button>
              <a-button
                size="small"
                type="text"
                data-testid="ai-assistant-completion-dislike"
                aria-label="点踩完成总结"
                :class="{ active: completionFeedback[thread.run.id] === 'dislike' }"
                @click="markFinalAnswerFeedback(thread.run.id, 'dislike')"
              >
                <template #icon><DislikeOutlined /></template>
              </a-button>
            </span>
            <span data-testid="ai-assistant-completion-meta">已完成 · {{ runThreadCompletedAt(thread) }}</span>
          </div>
        </div>
          </template>
        </template>
      </section>

      <form class="ai-composer" data-testid="ai-assistant-composer" @submit.prevent="submit">
        <div class="ai-composer__body" data-testid="ai-assistant-composer-body">
          <a-textarea
            v-model:value="draft"
            class="ai-composer__input"
            :auto-size="{ minRows: 2, maxRows: 5 }"
            placeholder="输入给 AI 助手的消息"
          />
        </div>
        <div class="ai-composer__actions" data-testid="ai-assistant-composer-actions">
          <div class="ai-composer__left-actions">
            <a-dropdown :trigger="['click']">
              <a-button class="ai-composer__permission" data-testid="ai-assistant-permission-mode" type="text">
                <template #icon><SafetyCertificateOutlined /></template>
                {{ permissionModeLabel }}
                <DownOutlined />
              </a-button>
              <template #overlay>
                <a-menu @click="selectPermissionMode">
                  <a-menu-item key="ask_each_time">请求批准</a-menu-item>
                  <a-menu-item key="smart_approval">替我审批</a-menu-item>
                  <a-menu-item key="always_approve">完全访问权限</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
            <div class="ai-composer__model-config">
              <a-button
                class="ai-composer__icon-button"
                data-testid="ai-assistant-model-config-icon"
                type="text"
                aria-label="模型配置"
                @click="runtimeConfigExpanded = !runtimeConfigExpanded"
              >
                <template #icon><SettingOutlined /></template>
              </a-button>
              <section
                v-if="runtimeConfigExpanded"
                class="ai-composer__model-panel"
                data-testid="ai-assistant-model-config-panel"
              >
                <div class="ai-runtime" data-testid="ai-assistant-runtime-config">
                  <label class="ai-runtime__field">
                    <span>运行模式</span>
                    <a-select
                      v-model:value="runtimeConfig.modelMode"
                      class="ai-runtime__select"
                      :options="runtimeModeOptions"
                      data-testid="ai-assistant-runtime-mode"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>模型</span>
                    <a-select
                      v-model:value="runtimeConfig.modelName"
                      class="ai-runtime__select"
                      :options="modelOptions"
                      data-testid="ai-assistant-model-select"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>接口地址</span>
                    <a-input
                      v-model:value="runtimeConfig.baseUrl"
                      class="ai-runtime__input"
                      placeholder="https://openrouter.ai/api/v1"
                      data-testid="ai-assistant-model-base-url"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>临时密钥</span>
                    <a-input-password
                      v-model:value="runtimeConfig.apiKey"
                      class="ai-runtime__input"
                      placeholder="sk-..."
                      data-testid="ai-assistant-model-api-key"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>温度</span>
                    <a-input-number
                      v-model:value="runtimeConfig.temperature"
                      class="ai-runtime__input"
                      :min="0"
                      :max="2"
                      :step="0.05"
                      :precision="2"
                      data-testid="ai-assistant-model-temperature"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>输出上限</span>
                    <a-input-number
                      v-model:value="runtimeConfig.maxTokens"
                      class="ai-runtime__input"
                      :min="1"
                      :max="32768"
                      :step="128"
                      :precision="0"
                      data-testid="ai-assistant-model-max-tokens"
                    />
                  </label>
                  <div class="ai-runtime__meta">
                    <span>{{ runtimeConfig.modelMode === 'live' ? runtimeConfig.baseUrl : '本地确定性规划器' }}</span>
                    <span>实时事件流：已启用</span>
                  </div>
                </div>
              </section>
            </div>
          </div>
          <a-button
            class="ai-composer__send"
            data-testid="ai-assistant-send"
            type="primary"
            html-type="submit"
            :loading="sending"
            aria-label="发送"
          >
            <template #icon><SendOutlined /></template>
          </a-button>
        </div>
      </form>
    </main>

    <aside
      class="ai-inspector"
      data-testid="ai-assistant-run-inspector"
      data-testid-secondary="ai-assistant-right-column-scroll"
    >
      <header class="ai-inspector__header">
        <ClockCircleOutlined />
        <div>
          <strong>可观测性</strong>
          <small>{{ elapsedLabel }}</small>
        </div>
      </header>

      <section class="ai-inspector__section">
        <header>任务</header>
        <article
          v-for="task in inspector?.activeTasks || []"
          :key="task.id"
          class="ai-task"
          data-testid="ai-assistant-task-row"
        >
          <span
            class="ai-task__status"
            :class="statusClass(task.status)"
            data-testid="ai-assistant-task-status-icon"
          >
            <LoadingOutlined
              v-if="isRunningStatus(task.status)"
              class="ai-task__spinner"
              data-testid="ai-assistant-task-spinner"
            />
            <CheckCircleOutlined
              v-else-if="isDoneStatus(task.status)"
              class="ai-task__done"
              data-testid="ai-assistant-task-completed-icon"
            />
            <ExclamationCircleOutlined v-else-if="isDangerStatus(task.status)" />
            <ClockCircleOutlined v-else />
          </span>
          <div>
            <strong>{{ task.title }}</strong>
            <small>{{ taskMetaLabel(task) }}</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section" data-testid="ai-assistant-plan-panel">
        <header>计划</header>
        <article class="ai-plan">
          <div class="ai-plan__row">
            <span>策略</span>
            <strong data-testid="ai-assistant-planning-strategy">
              {{ planningStrategyLabel(inspector?.plan?.planningStrategy || inspector?.activeTasks?.[0]?.planningStrategy) }}
            </strong>
          </div>
          <div class="ai-plan__block" data-testid="ai-assistant-recognized-needs">
            <span>已识别需求</span>
            <p>{{ recognizedNeeds.join('；') || '等待识别' }}</p>
          </div>
          <ol class="ai-plan__steps">
            <li
              v-for="step in inspector?.plan?.steps || []"
              :key="step.id"
              class="ai-plan__step"
              data-testid="ai-assistant-planned-step"
            >
              <span class="ai-plan__step-status" :class="statusClass(step.status)" />
              <div>
                <strong>{{ step.title }}</strong>
                <small>{{ statusLabel(step.status) }}</small>
              </div>
            </li>
          </ol>
          <div class="ai-plan__block" data-testid="ai-assistant-active-step">
            <span>当前步骤</span>
            <p>{{ currentStep?.title || '暂无活动步骤' }}</p>
          </div>
          <div class="ai-plan__block" data-testid="ai-assistant-current-tool">
            <span>当前工具</span>
            <p>{{ currentStep?.toolName ? toolLabel(currentStep.toolName) : plannedToolsLabel }}</p>
          </div>
          <div class="ai-plan__block" data-testid="ai-assistant-final-result">
            <span>最终结果</span>
            <p>{{ inspector?.plan?.finalResult || inspector?.activeTasks?.[0]?.finalResult || '等待完成' }}</p>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>工具调用</header>
        <article
          v-for="toolCall in inspector?.toolCalls || []"
          :key="toolCall.id"
          class="ai-inspector-row"
          data-testid="ai-assistant-tool-call-row"
        >
          <ToolOutlined />
          <div>
            <strong>{{ toolLabel(toolCall.toolName) }}</strong>
            <small>{{ statusLabel(toolCall.status) }} / {{ toolCall.durationMs }} ms</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>待审批</header>
        <article
          v-for="approval in pendingApprovals"
          :key="approval.id"
          class="ai-approval"
          data-testid="ai-assistant-approval-row"
        >
          <div>
            <strong>{{ toolLabel(approval.toolName) }}</strong>
            <small>{{ riskLabel(approval.riskLevel) }} / {{ statusLabel(approval.status) }}</small>
          </div>
          <div v-if="isPendingApprovalStatus(approval.status)" class="ai-approval__actions">
            <a-button
              size="small"
              type="primary"
              data-testid="ai-assistant-approval-approve"
              @click="approve(approval.id)"
            >
              批准
            </a-button>
            <a-button
              size="small"
              danger
              data-testid="ai-assistant-approval-deny"
              @click="deny(approval.id)"
            >
              拒绝
            </a-button>
          </div>
        </article>
        <article
          v-for="approval in decidedApprovalRecords"
          :key="`history-${approval.id}`"
          class="ai-approval ai-approval--history"
          data-testid="ai-assistant-approval-history-row"
        >
          <div>
            <strong>{{ toolLabel(approval.toolName) }}</strong>
            <small>{{ riskLabel(approval.riskLevel) }} / {{ statusLabel(approval.status) }}</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>最近错误</header>
        <article
          v-for="error in inspector?.recentErrors || []"
          :key="error.id"
          class="ai-inspector-row danger"
          data-testid="ai-assistant-recent-error-row"
        >
          <ExclamationCircleOutlined />
          <div>
            <strong>{{ error.title }}</strong>
            <small>{{ error.summary }}</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>用量</header>
        <div class="ai-usage-grid">
          <span>输入 tokens</span>
          <strong>{{ inspector?.usage.inputTokens ?? 0 }}</strong>
          <span>输出 tokens</span>
          <strong>{{ inspector?.usage.outputTokens ?? 0 }}</strong>
          <span>总计 tokens</span>
          <strong>{{ inspector?.usage.totalTokens ?? 0 }}</strong>
          <span>耗时 ms</span>
          <strong>{{ inspector?.usage.elapsedMs ?? 0 }}</strong>
        </div>
      </section>

      <section
        v-if="inspector?.contextBudget || inspector?.memory"
        class="ai-inspector__section"
        data-testid="ai-assistant-context-budget"
      >
        <header>上下文</header>
        <div class="ai-usage-grid">
          <span>上下文使用</span>
          <strong>{{ contextUsageLabel }}</strong>
          <span>本轮压缩</span>
          <strong>{{ compactionRatioLabel }}</strong>
          <span>告警</span>
          <strong>{{ contextWarningLabel }}</strong>
          <span>压缩前压力</span>
          <strong>{{ rawContextUsageLabel }}</strong>
        </div>
        <div class="ai-plan__block">
          <span>Layer 占比</span>
          <ol class="ai-context-layers">
            <li v-for="layer in contextLayerRows" :key="layer.name">
              <strong>{{ layer.name }}</strong>
              <small>{{ layer.tokens }} tokens / {{ layer.sharePercent }}%</small>
            </li>
          </ol>
        </div>
        <div class="ai-plan__block">
          <span>已选上下文</span>
          <p>{{ selectedContextLayerLabel }}</p>
        </div>
        <div class="ai-plan__block">
          <span>已丢弃上下文</span>
          <p>{{ droppedContextLayerLabel }}</p>
        </div>
        <div class="ai-plan__block">
          <span>工作记忆</span>
          <p>{{ workingMemoryLabel }}</p>
        </div>
        <div class="ai-plan__block">
          <span>审计引用</span>
          <p>{{ contextAuditReferenceLabel }}</p>
        </div>
      </section>

      <section class="ai-inspector__section" data-testid="ai-assistant-inspector-timeline">
        <header>执行步骤</header>
        <ol class="ai-execution-steps">
          <li v-for="step in inspectorExecutionStepsForView" :key="step.id" data-testid="ai-assistant-execution-step">
            <span class="ai-execution-step__status" :class="statusClass(step.status)">
              <LoadingOutlined
                v-if="isInspectorEventRunning(step)"
                class="ai-execution-step__spinner"
                data-testid="ai-assistant-execution-step-spinner"
              />
              <CheckCircleOutlined
                v-else-if="isInspectorEventDone(step)"
                class="ai-execution-step__done"
                data-testid="ai-assistant-execution-step-done"
              />
              <ExclamationCircleOutlined v-else-if="step.status === 'FAILED' || step.status === 'DENIED'" />
              <ClockCircleOutlined v-else class="ai-execution-step__pending" />
            </span>
            <div>
              <strong>{{ step.title }}</strong>
              <small>{{ stepMetaLabel(step) }}</small>
            </div>
          </li>
        </ol>
      </section>
    </aside>
  </section>
</template>

<script setup lang="ts">
import {
  BarChartOutlined,
  CheckCircleOutlined,
  ClearOutlined,
  CopyOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  DislikeOutlined,
  DownOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  LikeOutlined,
  LoadingOutlined,
  PlusOutlined,
  RightOutlined as CollapseChevron,
  SafetyCertificateOutlined,
  SendOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  approveAiAssistantApproval,
  clearAiAssistantSessionHistory,
  createAiAssistantSession,
  deleteAiAssistantSession,
  denyAiAssistantApproval,
  getAiAssistantRunInspector,
  getAiAssistantRunSnapshot,
  listAiAssistantSessionRuns,
  listAiAssistantSessions,
  buildAiAssistantMessagePayload,
  startAiAssistantMessage,
  type AiAssistantEvent,
  type AiAssistantApproval,
  type AiAssistantApprovalMode,
  type AiAssistantRun,
  type AiAssistantRunInspector,
  type AiAssistantSession,
  type AiAssistantRuntimeConfig,
  type AiAssistantToolCall,
} from '@/api/aiAssistant'
import { openAiAssistantEventStream, type AiAssistantEventStream } from './aiAssistantEventStream'
import AiAssistantActivityFeed from './AiAssistantActivityFeed.vue'
import AiAssistantActivityRow from './AiAssistantActivityRow.vue'
import type { RunActivity } from './aiAssistantActivity'
import { activityProgress } from './aiAssistantActivityView'
import {
  buildAiAssistantTimeline,
  type AiAssistantTimelineItem,
  type AiAssistantToolInvocation,
  type AiAssistantToolInvocationRow,
} from './aiAssistantTimeline'
import { useAiAssistantActivityStream } from './useAiAssistantActivityStream'

interface AiAssistantRunThread {
  run: AiAssistantRun
  events: AiAssistantEvent[]
  inspector: AiAssistantRunInspector | null
  streamCursorLastSequence?: number
}

interface AiAssistantInspectorExecutionStep {
  id: string
  sequence: number
  title: string
  status: string
  summary?: string
}

const AI_ASSISTANT_RUNTIME_CONFIG_STORAGE_KEY = 'hify.ai-assistant.runtime-config'
const DEFAULT_RUNTIME_CONFIG: AiAssistantRuntimeConfig = {
  modelMode: 'deterministic',
  modelName: 'qwen/qwen3.6-27b',
  baseUrl: 'https://openrouter.ai/api/v1',
  apiKey: '',
  temperature: 0.2,
  maxTokens: 4096,
  streamEnabled: true,
}

const sessions = ref<AiAssistantSession[]>([])
const runs = ref<AiAssistantRun[]>([])
const runThreads = ref<AiAssistantRunThread[]>([])
const sessionId = ref<number | null>(null)
const sessionTitle = ref('Hify AI 助手')
const runId = ref<number | null>(null)
const runStatus = ref('IDLE')
const runtimeConfigExpanded = ref(false)
const runtimeConfig = ref<AiAssistantRuntimeConfig>(loadRuntimeConfig())
const permissionMode = ref<AiAssistantApprovalMode>('smart_approval')
const runtimeModeOptions = [
  { label: '本地确定性', value: 'deterministic' },
  { label: 'Live Qwen', value: 'live' },
]
const modelOptions = [
  { label: 'Qwen / qwen3.6-27B', value: 'qwen/qwen3.6-27b' },
  { label: 'Qwen / qwen3.5-14B', value: 'qwen/qwen3.5-14b' },
  { label: 'Qwen / qwen2.5-72B-Instruct', value: 'qwen/qwen2.5-72b-instruct' },
]
const draft = ref('')
const sending = ref(false)
const events = ref<AiAssistantEvent[]>([])
const inspector = ref<AiAssistantRunInspector | null>(null)
const expandedEventIds = ref<Set<string>>(new Set())
const expandedToolInvocationIds = ref<Set<string>>(new Set())
const completionFeedback = ref<Record<number, 'like' | 'dislike'>>({})
const {
  activityExpansionOverrides,
  activitiesForEvents,
  feedItemsForEvents,
  timelineItemsForActivity,
  isActivityExpanded,
  toggleActivity,
  resetActivityExpansionOverrides,
} = useAiAssistantActivityStream()
let activeEventStream: AiAssistantEventStream | null = null
let inspectorRefreshTimer: number | null = null

const pendingApprovals = computed(() => inspector.value?.approvalQueue ?? [])
const approvalRecords = computed(() => inspector.value?.approvalHistory ?? [])
const decidedApprovalRecords = computed(() => approvalRecords.value.filter((approval) => approval.status !== 'PENDING'))
const recognizedNeeds = computed(() => inspector.value?.plan?.recognizedNeeds ?? inspector.value?.activeTasks?.[0]?.recognizedNeeds ?? [])
const currentStep = computed(() => inspector.value?.plan?.currentStep ?? inspector.value?.activeTasks?.[0]?.currentStep ?? null)
const plannedTools = computed(() => inspector.value?.plan?.plannedTools ?? inspector.value?.activeTasks?.[0]?.plannedTools ?? [])
const plannedToolsLabel = computed(() =>
  plannedTools.value.length ? plannedTools.value.map((toolName) => toolLabel(toolName)).join(' / ') : '暂无工具',
)
const elapsedLabel = computed(() => `${Math.max(0, Math.round((inspector.value?.usage.elapsedMs ?? 0) / 100) / 10)}s`)
const contextBudget = computed(() => inspector.value?.contextBudget ?? null)
const contextUsageLabel = computed(() => {
  const usage = contextBudget.value?.usage
  if (!usage) return '0 / 0 · 0%'
  return `${formatTokenCount(usage.usedTokens)} / ${formatTokenCount(usage.maxTokens)} · ${usage.usagePercent}%`
})
const rawContextUsageLabel = computed(() => {
  const usage = contextBudget.value?.usage
  if (!usage?.rawTokens) return '无'
  return `${formatTokenCount(usage.rawTokens)} / ${formatTokenCount(usage.maxTokens)} · ${usage.rawUsagePercent ?? 0}%`
})
const compactionRatioLabel = computed(() => {
  const snapshot = contextBudget.value?.compactionSnapshot
  if (!snapshot) return '未压缩'
  return `${formatTokenCount(snapshot.rawTokens)} -> ${formatTokenCount(snapshot.summaryTokens)} · 节省 ${snapshot.savedPercent}%`
})
const contextWarningLabel = computed(() => {
  const level = contextBudget.value?.usage.warningLevel ?? 'ok'
  if (level === 'critical') return '必须压缩'
  if (level === 'warning') return '接近上限'
  return '正常'
})
const contextLayerRows = computed(() => contextBudget.value?.layers ?? [])
const selectedContextLayerLabel = computed(() =>
  contextBudget.value?.selectedLayers?.length
    ? contextBudget.value.selectedLayers.map((layer) => layer.name).join(' / ')
    : '暂无',
)
const droppedContextLayerLabel = computed(() =>
  contextBudget.value?.droppedLayers?.length
    ? contextBudget.value.droppedLayers.map((layer) => layer.name).join(' / ')
    : '无',
)
const workingMemoryLabel = computed(() => {
  const items = inspector.value?.memory?.workingMemory ?? []
  const activeItems = items.filter((item) => (item.status ?? 'active') === 'active')
  return activeItems.length ? activeItems.map((item) => `${item.key}: ${item.value}`).join('；') : '暂无'
})
const contextAuditReferenceLabel = computed(() => {
  const parts: string[] = []
  const summary = inspector.value?.memory?.sessionSummary
  if (summary?.hash) parts.push(`summary:${summary.hash.slice(0, 12)}`)
  const snapshot = contextBudget.value?.compactionSnapshot
  if (snapshot?.sourceMessageIds?.length) parts.push(`messages:${snapshot.sourceMessageIds.join(',')}`)
  if (snapshot?.sourceEventIds?.length) parts.push(`events:${snapshot.sourceEventIds.join(',')}`)
  const dropReasons = contextBudget.value?.dropReasons ?? []
  if (dropReasons.length) {
    parts.push(`drop:${dropReasons.map((item) => `${item.name}/${item.reason}`).join('|')}`)
  }
  const instructionSources = inspector.value?.memory?.instructionMemory ?? []
  if (instructionSources.length) {
    parts.push(`agents:${instructionSources.map((item) => shortPathLabel(item.path)).join('|')}`)
  }
  return parts.length ? parts.join('；') : '暂无'
})
const runThreadsForView = computed(() => runThreads.value.slice().sort((left, right) => left.run.id - right.run.id))
const currentRunEventsForView = computed(() => {
  const currentRunId = inspector.value?.run.id ?? runId.value
  if (!currentRunId) return []
  const thread = runThreads.value.find((item) => item.run.id === currentRunId)
  return (thread?.events ?? events.value).filter((event) => event.runId === currentRunId)
})
const inspectorExecutionStepsForView = computed(() =>
  buildInspectorExecutionSteps(inspector.value, currentRunEventsForView.value),
)
const permissionModeLabel = computed(() => permissionModeOptions[permissionMode.value])
const permissionModeOptions: Record<AiAssistantApprovalMode, string> = {
  ask_each_time: '请求批准',
  smart_approval: '替我审批',
  always_approve: '完全访问权限',
}

watch(runtimeConfig, (value) => persistRuntimeConfig(value), { deep: true })

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length === 0) {
    await createConversation()
    return
  }
  await selectSession(sessions.value[0].id)
})

onBeforeUnmount(() => {
  closeActiveEventStream()
  if (inspectorRefreshTimer !== null) window.clearTimeout(inspectorRefreshTimer)
})

async function loadSessions() {
  sessions.value = (await listAiAssistantSessions()).list
}

async function createConversation() {
  const session = await createAiAssistantSession()
  await loadSessions()
  await selectSession(session.id)
}

async function selectSession(nextSessionId: number) {
  closeActiveEventStream()
  const selected = sessions.value.find((session) => session.id === nextSessionId)
  sessionId.value = nextSessionId
  sessionTitle.value = selected ? sessionDisplayTitle(selected) : 'Hify AI 助手'
  await loadSessionRuns(nextSessionId)
}

async function loadSessionRuns(nextSessionId: number, preferredRunId?: number) {
  const sessionRuns = (await listAiAssistantSessionRuns(nextSessionId)).list
  runs.value = sessionRuns
  expandedEventIds.value = new Set()
  resetActivityExpansionOverrides()
  runThreads.value = await loadRunThreadRecords(sessionRuns)
  const orderedThreads = runThreadsForView.value
  const nextRunId = preferredRunId ?? orderedThreads[orderedThreads.length - 1]?.run.id
  if (!nextRunId) {
    closeActiveEventStream()
    runId.value = null
    runStatus.value = 'IDLE'
    events.value = []
    inspector.value = null
    return
  }
  setActiveRunThread(nextRunId)
  resumeRunEventStreamIfRunning(nextRunId)
}

async function loadRunInspector(nextRunId: number) {
  await refreshRunThread(nextRunId)
}

async function loadRunThreadRecords(sessionRuns: AiAssistantRun[]) {
  const records = await Promise.all(
    sessionRuns.map(async (run) => {
      const snapshot = await getAiAssistantRunSnapshot(run.id)
      return snapshotToRunThread(snapshot)
    }),
  )
  return records
}

async function refreshRunThread(nextRunId: number) {
  closeActiveEventStream()
  const snapshot = await getAiAssistantRunSnapshot(nextRunId)
  upsertRunThread(snapshotToRunThread(snapshot))
  setActiveRunThread(nextRunId)
  sending.value = snapshot.run.status === 'RUNNING'
}

function setActiveRunThread(nextRunId: number) {
  const thread = runThreads.value.find((item) => item.run.id === nextRunId)
  if (!thread) return
  runId.value = nextRunId
  events.value = thread.events
  inspector.value = thread.inspector
  runStatus.value = thread.inspector?.run.status ?? thread.run.status
}

function resumeRunEventStreamIfRunning(nextRunId: number) {
  const thread = runThreads.value.find((item) => item.run.id === nextRunId)
  const status = thread?.inspector?.run.status ?? thread?.run.status
  if (status === 'RUNNING') openRunEventStream(nextRunId)
}

async function clearCurrentHistory() {
  if (!sessionId.value) return
  closeActiveEventStream()
  await clearAiAssistantSessionHistory(sessionId.value)
  runs.value = []
  runThreads.value = []
  events.value = []
  inspector.value = null
  runId.value = null
  runStatus.value = 'IDLE'
  expandedEventIds.value = new Set()
  resetActivityExpansionOverrides()
  await loadSessions()
}

async function deleteConversation(targetSessionId: number) {
  closeActiveEventStream()
  const activeSessionId = sessionId.value
  await deleteAiAssistantSession(targetSessionId)
  await loadSessions()
  if (sessions.value.length === 0) return resetConversationAfterDelete()
  if (activeSessionId === targetSessionId || !sessions.value.some((session) => session.id === activeSessionId)) {
    await selectSession(sessions.value[0].id)
  }
}

async function resetConversationAfterDelete() {
  closeActiveEventStream()
  sessionId.value = null
  sessionTitle.value = 'Hify AI 助手'
  runs.value = []
  runThreads.value = []
  events.value = []
  inspector.value = null
  runId.value = null
  runStatus.value = 'IDLE'
  expandedEventIds.value = new Set()
  resetActivityExpansionOverrides()
  await createConversation()
}

async function submit() {
  const message = draft.value.trim()
  if (!message) return
  if (!sessionId.value) {
    await createConversation()
  }
  if (!sessionId.value) return
  sending.value = true
  runtimeConfigExpanded.value = false
  try {
    const result = await startAiAssistantMessage(
      sessionId.value,
      buildAiAssistantMessagePayload(message, runtimeConfig.value, `ui-${Date.now()}`, permissionMode.value),
    )
    draft.value = ''
    events.value = []
    inspector.value = null
    runId.value = result.runId
    expandedEventIds.value = new Set()
    resetActivityExpansionOverrides()
    runStatus.value = result.status
    await loadSessions()
    await refreshRuns(result.sessionId, result.runId)
    openRunEventStream(result.runId)
  } finally {
    if (!runId.value || runStatus.value !== 'RUNNING') sending.value = false
  }
}

async function refreshRuns(nextSessionId: number, preferredRunId: number) {
  runs.value = (await listAiAssistantSessionRuns(nextSessionId)).list
  const snapshot = await getAiAssistantRunSnapshot(preferredRunId)
  upsertRunThread(snapshotToRunThread(snapshot))
  setActiveRunThread(preferredRunId)
  sending.value = snapshot.run.status === 'RUNNING'
}

function openRunEventStream(nextRunId: number, afterSequence = lastSequenceForRun(nextRunId)) {
  closeActiveEventStream()
  activeEventStream = openAiAssistantEventStream(nextRunId, {
    afterSequence,
    onEvent: (event) => {
      mergeEvent(event)
      const nextStatus = runStatusFromEvent(event, runStatus.value)
      runStatus.value = nextStatus
      if (nextStatus === 'RUNNING') sending.value = true
      scheduleInspectorRefresh(nextRunId)
      if (isTerminalEvent(event)) {
        sending.value = false
        closeActiveEventStream()
      }
    },
  })
}

function snapshotToRunThread(snapshot: Awaited<ReturnType<typeof getAiAssistantRunSnapshot>>): AiAssistantRunThread {
  return {
    run: snapshot.inspector?.run ?? snapshot.run,
    events: snapshot.events,
    inspector: snapshot.inspector,
    streamCursorLastSequence: snapshot.streamCursor?.lastSequence ?? lastSequence(snapshot.events),
  }
}

function lastSequenceForRun(nextRunId: number) {
  const thread = runThreads.value.find((item) => item.run.id === nextRunId)
  if (typeof thread?.streamCursorLastSequence === 'number') return thread.streamCursorLastSequence
  const events = thread?.events ?? []
  return lastSequence(events)
}

function lastSequence(nextEvents: AiAssistantEvent[]) {
  return Math.max(0, ...nextEvents.map((event) => Number(event.sequence || 0)))
}

function mergeEvent(event: AiAssistantEvent) {
  const index = events.value.findIndex((item) => item.id === event.id)
  if (index >= 0) {
    events.value = events.value.map((item) => (item.id === event.id ? event : item))
  } else {
    events.value = [...events.value, event].sort((left, right) => left.sequence - right.sequence)
  }
  mergeEventIntoRunThread(event)
}

function scheduleInspectorRefresh(nextRunId: number) {
  if (inspectorRefreshTimer !== null) return
  inspectorRefreshTimer = window.setTimeout(async () => {
    inspectorRefreshTimer = null
    const runInspector = await getAiAssistantRunInspector(nextRunId)
    inspector.value = runInspector
    runStatus.value = runInspector.run.status
    sending.value = runInspector.run.status === 'RUNNING'
    upsertRunThread({
      run: runInspector.run,
      events: events.value,
      inspector: runInspector,
    })
  }, 350)
}

function upsertRunThread(thread: AiAssistantRunThread) {
  const index = runThreads.value.findIndex((item) => item.run.id === thread.run.id)
  if (index >= 0) {
    runThreads.value = runThreads.value.map((item) => (item.run.id === thread.run.id ? thread : item))
    return
  }
  runThreads.value = [...runThreads.value, thread]
}

function mergeEventIntoRunThread(event: AiAssistantEvent) {
  const currentThread = runThreads.value.find((thread) => thread.run.id === event.runId)
  const nextRun = currentThread?.run ?? {
    id: event.runId,
    sessionId: event.sessionId,
    status: runStatusFromEvent(event, runStatus.value),
    input: { message: draft.value },
    result: {},
  }
  const nextEvents = [...(currentThread?.events ?? [])]
  const index = nextEvents.findIndex((item) => item.id === event.id)
  if (index >= 0) nextEvents[index] = event
  else nextEvents.push(event)
  upsertRunThread({
    run: { ...nextRun, status: runStatusFromEvent(event, nextRun.status) },
    events: nextEvents.sort((left, right) => left.sequence - right.sequence),
    inspector: currentThread?.inspector ?? null,
    streamCursorLastSequence: Math.max(currentThread?.streamCursorLastSequence ?? 0, Number(event.sequence || 0)),
  })
}

function runStatusFromEvent(event: AiAssistantEvent, fallback: string) {
  if (event.type === 'run.completed') return 'COMPLETED'
  if (event.type === 'run.failed') return 'FAILED'
  if (event.type === 'run.cancelled') return 'CANCELLED'
  if (event.type === 'approval.required') return 'WAITING_APPROVAL'
  if (event.type === 'run.started' || event.type === 'run.worker_started') return 'RUNNING'
  return fallback
}

function closeActiveEventStream() {
  activeEventStream?.close()
  activeEventStream = null
}

function isTerminalEvent(event: AiAssistantEvent) {
  return ['run.completed', 'run.failed', 'run.cancelled', 'approval.required', 'sandbox.denied'].includes(event.type)
}

async function approve(approvalId: number) {
  await approveAiAssistantApproval(approvalId, { actorId: 'operator-ui' })
  if (runId.value) await loadRunInspector(runId.value)
}

async function deny(approvalId: number) {
  await denyAiAssistantApproval(approvalId, { actorId: 'operator-ui', reason: '界面拒绝' })
  if (runId.value) await loadRunInspector(runId.value)
}

function loadRuntimeConfig(): AiAssistantRuntimeConfig {
  if (typeof window === 'undefined') return { ...DEFAULT_RUNTIME_CONFIG }
  try {
    const stored = window.sessionStorage.getItem(AI_ASSISTANT_RUNTIME_CONFIG_STORAGE_KEY)
    if (!stored) return { ...DEFAULT_RUNTIME_CONFIG }
    return { ...DEFAULT_RUNTIME_CONFIG, ...JSON.parse(stored) }
  } catch {
    return { ...DEFAULT_RUNTIME_CONFIG }
  }
}

function persistRuntimeConfig(value: AiAssistantRuntimeConfig) {
  if (typeof window === 'undefined') return
  window.sessionStorage.setItem(AI_ASSISTANT_RUNTIME_CONFIG_STORAGE_KEY, JSON.stringify(value))
}

function selectPermissionMode(event: { key: string | number }) {
  const key = String(event.key)
  if (isApprovalMode(key)) permissionMode.value = key
}

function isApprovalMode(value: string): value is AiAssistantApprovalMode {
  return value === 'ask_each_time' || value === 'smart_approval' || value === 'always_approve'
}

function timelineForThread(thread: AiAssistantRunThread) {
  return buildAiAssistantTimeline(thread.events)
}

function runThreadUserMessage(thread: AiAssistantRunThread) {
  const message = thread.run.input?.message
  return typeof message === 'string' ? message.trim() : ''
}

function timelineForThreadEcho(thread: AiAssistantRunThread) {
  return timelineForThread(thread).filter((item) => !isFinalAnswerItem(item))
}

function runActivities(thread: AiAssistantRunThread) {
  return activitiesForEvents(thread.events)
}

function activityFeedItems(thread: AiAssistantRunThread) {
  return feedItemsForEvents(thread.events)
}

function activityTimelineItemsForThread(activity: RunActivity, thread: AiAssistantRunThread) {
  return timelineItemsForActivity(activity, thread.events)
}

function activityProgressForThread(activity: RunActivity, thread: AiAssistantRunThread) {
  return activityProgress(activity, thread.inspector?.plan?.steps ?? [])
}

function isFinalAnswerItem(item: AiAssistantTimelineItem) {
  return item.kind === 'model-output' && (item.phase === 'final_answer' || item.source === 'harness_final_answer')
}

function runThreadFinalAnswer(thread: AiAssistantRunThread) {
  const status = thread.inspector?.run.status ?? thread.run.status
  if (!['COMPLETED', 'APPROVED'].includes(status)) return ''
  const resultAnswer = finalAnswerFromRun(thread.inspector?.run ?? thread.run)
  if (resultAnswer) return resultAnswer
  return timelineForThread(thread)
    .filter(isFinalAnswerItem)
    .map((item) => item.summary.trim())
    .filter(Boolean)
    .join('\n\n')
}

function finalAnswerFromRun(run: AiAssistantRun) {
  const answer = run.result?.finalAnswer
  return typeof answer === 'string' ? answer.trim() : ''
}

function copyFinalAnswer(thread: AiAssistantRunThread) {
  const answer = runThreadFinalAnswer(thread)
  if (!answer || typeof navigator === 'undefined' || !navigator.clipboard?.writeText) return
  void navigator.clipboard.writeText(answer)
}

function copyUserMessage(thread: AiAssistantRunThread) {
  const message = runThreadUserMessage(thread)
  if (!message || typeof navigator === 'undefined' || !navigator.clipboard?.writeText) return
  void navigator.clipboard.writeText(message)
}

function copyToolInvocationResult(invocation: AiAssistantToolInvocation) {
  const text = invocation.shellCopyText || toolInvocationShellOutput(invocation)
  if (!text || typeof navigator === 'undefined' || !navigator.clipboard?.writeText) return
  void navigator.clipboard.writeText(text)
}

function toolInvocationShellOutput(invocation: AiAssistantToolInvocation) {
  return [`$ ${invocation.shellCommand || invocation.title}`.trim(), invocation.shellOutput].filter(Boolean).join('\n\n')
}

function markFinalAnswerFeedback(targetRunId: number, value: 'like' | 'dislike') {
  completionFeedback.value = { ...completionFeedback.value, [targetRunId]: value }
}

function runThreadStartedAt(thread: AiAssistantRunThread) {
  return formatMessageTime(thread.run.startedAt || thread.events[0]?.createdAt || '')
}

function runThreadCompletedAt(thread: AiAssistantRunThread) {
  return formatMessageTime(thread.run.completedAt || thread.events[thread.events.length - 1]?.createdAt || '')
}

function formatMessageTime(value: string | null | undefined) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatTokenCount(value: number | null | undefined) {
  const count = Math.max(0, Math.round(Number(value || 0)))
  if (count >= 1000) return `${Math.round(count / 100) / 10}k`
  return String(count)
}

function shortPathLabel(value: string | null | undefined) {
  const path = String(value || '').trim()
  if (!path) return 'unknown'
  const parts = path.split('/').filter(Boolean)
  return parts.slice(-2).join('/')
}

function taskMetaLabel(task: { phase: string; currentTool?: string | null }) {
  const currentTool = task.currentTool ? ` / ${toolLabel(task.currentTool)}` : ''
  const stepCount = inspectorExecutionStepsForView.value.length
  return `${task.phase}${currentTool} / ${stepCount} 个执行步骤`
}

function planningStrategyLabel(strategy: string | null | undefined) {
  const labels: Record<string, string> = {
    auto_lightweight: '自动轻量规划',
    deliberate: '深度规划',
    plan_only: '只规划',
  }
  return labels[String(strategy || 'auto_lightweight')] || String(strategy || 'auto_lightweight')
}

function isCurrentInspectorStep(step: AiAssistantInspectorExecutionStep) {
  const steps = inspectorExecutionStepsForView.value
  const activeStep = steps.find((item) => !isTerminalInspectorStepStatus(item.status))
  return step.id === (activeStep?.id ?? steps[steps.length - 1]?.id)
}

function isInspectorEventRunning(step: AiAssistantInspectorExecutionStep) {
  const runIsActive = inspector.value?.run.status === 'RUNNING'
  if (!runIsActive) return false
  return step.status === 'RUNNING' || step.status === 'STREAMING' || isCurrentInspectorStep(step)
}

function isInspectorEventDone(step: AiAssistantInspectorExecutionStep) {
  return !isInspectorEventRunning(step) && isDoneInspectorStepStatus(step.status)
}

function isTerminalInspectorStepStatus(status: string) {
  return isDoneInspectorStepStatus(status) || isDangerStatus(status)
}

function isDoneInspectorStepStatus(status: string) {
  return isDoneStatus(status)
}

function buildInspectorExecutionSteps(
  runInspector: AiAssistantRunInspector | null,
  currentRunEvents: AiAssistantEvent[],
): AiAssistantInspectorExecutionStep[] {
  if (!runInspector) return []
  const runScopedEvents = currentRunEvents.filter((event) => event.runId === runInspector.run.id)
  const plannedToolNames = plannedToolNamesFromCurrentRun(runScopedEvents)
  const steps: AiAssistantInspectorExecutionStep[] = []
  const approvals = dedupeApprovals([...(runInspector.approvalHistory ?? []), ...(runInspector.approvalQueue ?? [])])
  const toolCallsByName = groupToolCallsByName(runInspector.toolCalls ?? [])
  const plannedNames =
    plannedToolNames.length > 0 ? plannedToolNames : (runInspector.toolCalls ?? []).map((toolCall) => toolCall.toolName)

  for (const toolName of plannedNames) {
    const toolCall = toolCallsByName.get(toolName)?.shift()
    steps.push(toolCall ? toolCallExecutionStep(toolCall, steps.length + 1) : plannedToolExecutionStep(runInspector.run.id, toolName, steps.length + 1))
    const approval = approvals.find((record) => record.toolName === toolName)
    if (approval) steps.push(approvalExecutionStep(approval, steps.length + 1))
  }

  for (const remainingCalls of toolCallsByName.values()) {
    for (const toolCall of remainingCalls) {
      steps.push(toolCallExecutionStep(toolCall, steps.length + 1))
    }
  }

  for (const approval of approvals) {
    if (!steps.some((step) => step.id === `approval-${approval.id}`)) {
      steps.push(approvalExecutionStep(approval, steps.length + 1))
    }
  }

  return normalizeCurrentRunExecutionSteps(steps, runInspector.run.status)
}

function toolCallExecutionStep(toolCall: AiAssistantToolCall, sequence: number): AiAssistantInspectorExecutionStep {
  return {
    id: `tool-${toolCall.id}`,
    sequence,
    title: toolLabel(toolCall.toolName),
    status: toolCall.status,
    summary: `工具调用 / ${toolCall.durationMs} ms`,
  }
}

function approvalExecutionStep(approval: AiAssistantApproval, sequence: number): AiAssistantInspectorExecutionStep {
  return {
    id: `approval-${approval.id}`,
    sequence,
    title: `${toolLabel(approval.toolName)}审批`,
    status: approval.status,
    summary: riskLabel(approval.riskLevel),
  }
}

function plannedToolExecutionStep(runIdValue: number, toolName: string, sequence: number): AiAssistantInspectorExecutionStep {
  return {
    id: `planned-${runIdValue}-${sequence}-${toolName}`,
    sequence,
    title: toolLabel(toolName),
    status: 'PENDING',
    summary: '模型已编排',
  }
}

function plannedToolNamesFromCurrentRun(runScopedEvents: AiAssistantEvent[]) {
  const plannedNames: string[] = []
  const taskPlanningEvents = runScopedEvents.filter((event) => event.type === 'task.updated')
  const fallbackPlanningEvents = runScopedEvents.filter((event) => event.type === 'model.tool_call_decision')
  const planningEvents = (taskPlanningEvents.length > 0 ? taskPlanningEvents : fallbackPlanningEvents)
    .sort((left, right) => left.sequence - right.sequence)

  for (const event of planningEvents) {
    const toolNames = event.payload?.toolNames
    if (!Array.isArray(toolNames)) continue
    for (const toolName of toolNames) {
      if (typeof toolName === 'string' && toolName.trim()) plannedNames.push(toolName)
    }
  }
  return plannedNames
}

function groupToolCallsByName(toolCalls: AiAssistantToolCall[]) {
  const grouped = new Map<string, AiAssistantToolCall[]>()
  for (const toolCall of toolCalls) {
    const calls = grouped.get(toolCall.toolName) ?? []
    calls.push(toolCall)
    grouped.set(toolCall.toolName, calls)
  }
  return grouped
}

function normalizeCurrentRunExecutionSteps(steps: AiAssistantInspectorExecutionStep[], status: string) {
  if (steps.length === 0) return []
  if (status === 'COMPLETED' || status === 'APPROVED') {
    return steps.map((step) => (isTerminalInspectorStepStatus(step.status) ? step : { ...step, status: 'COMPLETED' }))
  }
  if (status !== 'RUNNING') return steps
  let markedRunning = false
  return steps.map((step) => {
    if (isTerminalInspectorStepStatus(step.status)) return step
    if (markedRunning) return step
    markedRunning = true
    return { ...step, status: 'RUNNING' }
  })
}

function stepMetaLabel(step: AiAssistantInspectorExecutionStep) {
  return step.summary ? `${statusLabel(step.status)} / ${step.summary}` : statusLabel(step.status)
}

function dedupeApprovals(approvals: AiAssistantApproval[]) {
  const seen = new Set<number>()
  return approvals.filter((approval) => {
    if (seen.has(approval.id)) return false
    seen.add(approval.id)
    return true
  })
}

function isRunThreadRunning(thread: AiAssistantRunThread) {
  return (thread.inspector?.run.status ?? thread.run.status) === 'RUNNING'
}

function sessionDisplayTitle(session: AiAssistantSession) {
  const title = session.title?.trim()
  if (!title || title === 'AI Assistant' || title === 'Hify AI 助手') return `会话 #${session.id}`
  return title
}

function statusLabel(status: string) {
  return (
    {
      IDLE: '空闲',
      ACTIVE: '活跃',
      OK: '已完成',
      RUNNING: '执行中',
      COMPLETED: '已完成',
      WAITING_APPROVAL: '等待审批',
      PENDING: '待处理',
      APPROVED: '已批准',
      DENIED: '已拒绝',
      FAILED: '失败',
      BLOCKED: '已阻断',
      NOT_FOUND: '未找到',
    }[status] ?? status
  )
}

function toolLabel(toolName: string) {
  return (
    {
      echo_context: '上下文回显',
      update_customer_profile: '客户资料变更',
      run_shell: 'Shell 执行',
      customer_assistant_subagent_bridge: '客服助手子任务桥接',
      read_workspace_file: '读取工作区文件',
      write_workspace_file: '写入工作区文件',
      invoke_skill: '使用技能',
      search_knowledge_base: '知识库检索',
    }[toolName] ?? toolName
  )
}

function riskLabel(riskLevel: string) {
  return (
    {
      READ: '只读',
      LOW_WRITE: '低风险写入',
      BUSINESS_WRITE: '业务写入',
      DESTRUCTIVE: '破坏性操作',
      EXTERNAL_SIDE_EFFECT: '外部副作用',
    }[riskLevel] ?? riskLevel
  )
}

function statusClass(status: string) {
  return {
    'status-done': isDoneStatus(status),
    'status-waiting': status === 'WAITING_APPROVAL' || status === 'PENDING',
    'status-danger': isDangerStatus(status),
    'status-running': isRunningStatus(status),
  }
}

function isRunningStatus(status: string) {
  return status === 'RUNNING' || status === 'STREAMING'
}

function isDoneStatus(status: string) {
  return status === 'COMPLETED' || status === 'APPROVED' || status === 'OK'
}

function isDangerStatus(status: string) {
  return status === 'DENIED' || status === 'FAILED'
}

function eventStatusIcon(item: AiAssistantTimelineItem, _thread: AiAssistantRunThread) {
  const { kind, tone } = item
  if (tone === 'danger') return ExclamationCircleOutlined
  if (kind === 'file') return EditOutlined
  if (kind === 'tool' || kind === 'tool-output') return ToolOutlined
  return ClockCircleOutlined
}

function toggleEventCard(itemId: string) {
  const next = new Set(expandedEventIds.value)
  if (next.has(itemId)) next.delete(itemId)
  else next.add(itemId)
  expandedEventIds.value = next
}

function isEventExpanded(itemId: string) {
  return expandedEventIds.value.has(itemId)
}

function toolInvocationKey(item: AiAssistantTimelineItem, invocation: AiAssistantToolInvocation) {
  return `${item.id}:${invocation.id}`
}

function toggleToolInvocation(item: AiAssistantTimelineItem, invocation: AiAssistantToolInvocation) {
  const key = toolInvocationKey(item, invocation)
  const next = new Set(expandedToolInvocationIds.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedToolInvocationIds.value = next
}

function isToolInvocationExpanded(item: AiAssistantTimelineItem, invocation: AiAssistantToolInvocation) {
  return expandedToolInvocationIds.value.has(toolInvocationKey(item, invocation))
}

function toolInvocationRows(invocation: AiAssistantToolInvocation) {
  return [
    ...markToolInvocationRows(invocation.inputRows, '输入', 'ai-assistant-tool-detail-input'),
    ...markToolInvocationRows(invocation.outputRows, '输出', 'ai-assistant-tool-detail-output'),
  ]
}

function markToolInvocationRows(
  rows: AiAssistantToolInvocationRow[],
  section: '输入' | '输出',
  testId: string,
) {
  return rows.map((row) => ({ ...row, section, testId: row.testId ?? testId }))
}

function formatEventDetailRows(item: AiAssistantTimelineItem) {
  return item.details
}

function shouldShowApprovalActions(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  if (item.kind !== 'approval' || !item.approvalId || item.tone !== 'waiting') return false
  const status = approvalStatusForTimelineItem(item, thread)
  return !status || isPendingApprovalStatus(status)
}

function approvalStatusForTimelineItem(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  const records = [
    ...(thread.inspector?.approvalQueue ?? []),
    ...(thread.inspector?.approvalHistory ?? []),
  ]
  return records.find((approval) => approval.id === item.approvalId)?.status
}

function isPendingApprovalStatus(status: string) {
  return status === 'PENDING' || status === 'WAITING_APPROVAL'
}

function approveTimelineItem(item: AiAssistantTimelineItem) {
  if (item.approvalId) return approve(item.approvalId)
}

function denyTimelineItem(item: AiAssistantTimelineItem) {
  if (item.approvalId) return deny(item.approvalId)
}

function isEventRunning(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  if (!isRunThreadRunning(thread)) return false
  const timeline = timelineForThreadEcho(thread)
  return item.id === timeline[timeline.length - 1]?.id && item.tone === 'running'
}

function isEventDone(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  return !isEventRunning(item, thread) && item.tone !== 'waiting' && item.tone !== 'danger'
}

function eventToneClass(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  if (isEventRunning(item, thread)) return 'running'
  if (isEventDone(item, thread)) return 'success'
  return item.tone
}
</script>

<style scoped>
.ai-shell {
  --ai-icon-button-size: 1.875rem;
  --ai-icon-button-radius: 0.375rem;
  --ai-icon-glyph-size: 0.875rem;
  height: calc(100vh - var(--header-height, 3.5rem) - 3rem);
  max-height: calc(100vh - var(--header-height, 3.5rem) - 3rem);
  box-sizing: border-box;
  min-height: 0;
  display: grid;
  grid-template-columns: 15rem minmax(0, 1fr) 18rem;
  grid-template-rows: minmax(0, 1fr);
  gap: 0;
  padding: 0;
  background: var(--color-bg-page, #f8f9fc);
  color: var(--color-text-primary, #0f1117);
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-lg, 0.5rem);
  overflow: hidden;
}

.ai-shell__side,
.ai-inspector,
.ai-console {
  min-width: 0;
  min-height: 0;
  background: var(--color-bg-surface, #ffffff);
  box-shadow: none;
}

.ai-shell__side,
.ai-inspector {
  padding: 0.75rem;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}

.ai-shell__brand,
.ai-new-session,
.ai-session,
.ai-session__select,
.ai-console__top,
.ai-console__actions,
.ai-event__head,
.ai-inspector__header,
.ai-inspector-row,
.ai-task,
.ai-approval {
  display: flex;
  align-items: center;
}

.ai-shell__brand {
  gap: 0.5rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
}

.ai-shell :deep(.ant-btn),
.ai-shell :deep(.ant-input),
.ai-shell :deep(.ant-input-number),
.ai-shell :deep(.ant-select),
.ai-shell :deep(.ant-select-selector),
.ai-shell :deep(.ant-tag) {
  border: 0;
  box-shadow: none;
}

.ai-shell :deep(.ant-btn .anticon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--ai-icon-glyph-size);
  line-height: 1;
}

.ai-shell :deep(.ant-btn-icon-only),
.ai-session__delete,
.ai-message__actions :deep(.ant-btn),
.ai-composer__icon-button,
.ai-composer__send {
  width: var(--ai-icon-button-size);
  min-width: var(--ai-icon-button-size);
  height: var(--ai-icon-button-size);
  padding: 0;
  border-radius: var(--ai-icon-button-radius);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.ai-shell :deep(.ant-select-selector),
.ai-shell :deep(.ant-input),
.ai-shell :deep(.ant-input-number) {
  background: var(--color-bg-page, #f8f9fc);
  border-radius: var(--radius-md, 0.375rem);
}

.ai-shell :deep(.ant-input-number-input-wrap),
.ai-shell :deep(.ant-select-selection-item),
.ai-shell :deep(.ant-select-selection-placeholder) {
  border: 0;
  box-shadow: none;
}

.ai-shell :deep(.ant-input:focus),
.ai-shell :deep(.ant-input-focused) {
  box-shadow: 0 0 0 0.125rem rgba(79, 70, 229, 0.16);
}

.ai-new-session,
.ai-session__select {
  width: 100%;
  gap: 0.5rem;
  color: inherit;
  text-align: left;
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-new-session {
  justify-content: center;
  padding: 0.5625rem;
  margin-bottom: 0.75rem;
  background: var(--color-bg-selected, #eef2ff);
  color: var(--color-primary-600, #4f46e5);
}

.ai-session-list,
.ai-inspector__section {
  display: flex;
  gap: 0.5rem;
}

.ai-session-list,
.ai-inspector__section {
  flex-direction: column;
}

.ai-inspector__section header {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.ai-session__select {
  padding: 0.625rem;
  background: var(--color-bg-surface, #ffffff);
}

.ai-session {
  min-width: 0;
  gap: 0.25rem;
  border-radius: var(--radius-md, 0.375rem);
  background: var(--color-bg-surface, #ffffff);
}

.ai-session__select {
  min-width: 0;
  flex: 1;
  padding-right: 0.25rem;
  border: 0;
  border-radius: calc(var(--radius-md, 0.375rem) - 0.0625rem);
}

.ai-session__delete {
  flex: 0 0 auto;
  margin-right: 0.25rem;
}

.ai-session.active {
  background: var(--color-bg-selected, #eef2ff);
}

.ai-session.active .ai-session__select {
  background: var(--color-bg-selected, #eef2ff);
}

.ai-session__content {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-session__content strong,
.ai-task strong,
.ai-inspector-row strong,
.ai-approval strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-session__content small,
.ai-task small,
.ai-inspector-row small,
.ai-approval small,
.ai-inspector__header small {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-session__dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--color-text-tertiary, #8b92a8);
  display: inline-block;
  flex: 0 0 auto;
}

.ai-session__dot {
  background: var(--color-success-500, #10b981);
}

.ai-console {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.ai-console__top {
  justify-content: space-between;
  gap: 0.625rem;
  padding: 0.625rem;
}

.ai-console__actions {
  gap: 0.35rem;
  flex: 0 0 auto;
}

.ai-usage-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.5rem;
  border-radius: 0.4rem;
  color: var(--color-text-secondary, #4b5268);
  background: var(--color-bg-subtle, #f4f5f7);
}

.ai-console__top h1 {
  margin: 0;
  font-size: 1rem;
}

.ai-console__top p {
  margin: 0.25rem 0 0;
  color: var(--color-text-secondary, #4b5268);
}

.ai-runtime {
  display: grid;
  gap: 0.625rem;
  padding: 0.75rem;
}

.ai-runtime__field {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
}

.ai-runtime__field span {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
  font-weight: 600;
}

.ai-runtime__select,
.ai-runtime__input {
  width: 100%;
}

.ai-runtime__meta {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
  color: var(--color-text-secondary, #4b5268);
  font-size: 0.75rem;
}

.ai-runtime__meta span:last-child {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-stream {
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  padding: 0.625rem 0.375rem 0.625rem 0.625rem;
}

.ai-empty {
  min-height: 18rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-message {
  display: grid;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: 0;
}

.ai-message p {
  margin: 0;
  line-height: 1.6;
  white-space: pre-wrap;
}

.ai-message--user {
  justify-items: end;
  color: var(--color-text-primary, #0f1117);
}

.ai-message--user p {
  padding: 0.625rem 0.75rem;
  background: var(--color-bg-selected, #eef2ff);
  border: 0;
  border-radius: var(--radius-lg, 0.5rem);
}

.ai-message--assistant {
  color: var(--color-text-primary, #0f1117);
}

.ai-message--user p,
.ai-message--assistant p {
  max-width: min(42rem, 100%);
}

.ai-message__meta-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  max-width: min(42rem, 100%);
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
}

.ai-message__meta-row--user {
  justify-content: flex-end;
  opacity: 0;
  transition: opacity 0.16s ease;
}

.ai-message__meta-row--completion {
  justify-content: space-between;
}

.ai-message__actions {
  opacity: 0;
  transition: opacity 0.16s ease;
  display: flex;
  gap: 0.375rem;
  justify-content: flex-start;
}

.ai-message:hover .ai-message__actions,
.ai-message:focus-within .ai-message__actions,
.ai-message--user:hover .ai-message__meta-row--user,
.ai-message--user:focus-within .ai-message__meta-row--user {
  opacity: 1;
}

.ai-message__actions :deep(.ant-btn) {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-message__actions :deep(.ant-btn:hover),
.ai-message__actions :deep(.ant-btn.active) {
  color: var(--color-text-secondary, #4b5268);
}

.ai-collapse-chevron {
  width: 0.75rem;
  height: 0.75rem;
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.625rem;
  transform: rotate(0deg);
  transition: transform 0.16s ease;
}

.ai-collapse-chevron.expanded {
  transform: rotate(90deg);
}

.ai-event__spinner {
  color: var(--color-primary-600, #4f46e5);
  animation: ai-spin 0.9s linear infinite;
}

.ai-event__title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-activity-event-list {
  display: grid;
  gap: 0;
  padding: 0.25rem 0 0.125rem;
  padding-left: 0.75rem;
}

.ai-event {
  display: grid;
  grid-template-columns: 1rem minmax(0, 1fr);
  gap: 0.5rem;
  margin: 0;
}

.ai-event:not(:last-child) {
  padding-bottom: 0.875rem;
}

.ai-event__rail {
  position: relative;
  display: flex;
  justify-content: center;
  padding-top: 0.25rem;
}

.ai-event:not(:last-child) .ai-event__rail::after {
  content: '';
  position: absolute;
  top: 1.375rem;
  bottom: -0.875rem;
  width: 0.0625rem;
  background: var(--color-border-default, #e3e6ef);
}

.ai-event__status-icon,
.ai-event__spinner {
  position: relative;
  z-index: 1;
  font-size: 0.875rem;
}

.ai-event__status-icon {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-surface, #ffffff);
  color: var(--color-border-strong, #c7ccd8);
}

.ai-event__body {
  display: grid;
  gap: 0.5rem;
  padding: 0 0 0.625rem;
  background: transparent;
  border-radius: 0;
}

.ai-model-output {
  display: grid;
  gap: 0.25rem;
}

.ai-model-output p {
  margin: 0;
  color: var(--color-text-primary, #0f1117);
  line-height: 1.6;
  white-space: pre-wrap;
}

.ai-event__summary {
  margin: 0;
  color: var(--color-text-secondary, #4b5268);
  line-height: 1.55;
}

.ai-event__head {
  width: 100%;
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr);
  gap: 0.5rem;
  align-items: center;
  font-weight: 700;
  color: inherit;
  background: transparent;
  border: 0;
  cursor: pointer;
  text-align: left;
}

.ai-event__details {
  display: grid;
  gap: 0.5rem;
}

.ai-event__detail-grid {
  display: grid;
  gap: 0.5rem;
  margin: 0;
}

.ai-event__detail-row {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: 0.625rem;
  padding: 0.625rem;
  background: var(--color-bg-page, #f8f9fc);
  border-radius: var(--radius-md, 0.375rem);
}

.ai-event__detail-anchor {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
}

.ai-event__detail-row dt {
  color: var(--color-text-tertiary, #8b92a8);
  font-weight: 700;
}

.ai-event__detail-row dd {
  min-width: 0;
  margin: 0;
  color: var(--color-text-secondary, #4b5268);
}

.ai-event__detail-row pre {
  max-height: 14rem;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 0.75rem;
  line-height: 1.45;
}

.ai-tool-invocation-list {
  display: grid;
  gap: 0.5rem;
}

.ai-tool-invocation {
  display: grid;
  gap: 0.375rem;
  box-shadow: inset 0 0.0625rem 0 var(--color-border-default, #e3e6ef);
  padding-top: 0.5rem;
}

.ai-tool-invocation:first-child {
  box-shadow: none;
  padding-top: 0;
}

.ai-tool-invocation__header {
  width: 100%;
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto auto;
  gap: 0.5rem;
  align-items: center;
  padding: 0.25rem 0;
  color: inherit;
  background: transparent;
  border: 0;
  cursor: pointer;
  text-align: left;
}

.ai-tool-invocation__header--shell {
  grid-template-columns: minmax(0, 1fr) auto auto;
  padding-left: 0;
}

.ai-tool-invocation__header strong,
.ai-tool-invocation__header small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-tool-invocation__header small,
.ai-tool-invocation__header span {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-tool-invocation__status {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-border-strong, #c7ccd8);
}

.ai-tool-invocation__status.tone-running {
  color: var(--color-primary-600, #4f46e5);
}

.ai-tool-invocation__status.tone-success {
  color: var(--color-success-500, #10b981);
}

.ai-tool-invocation__status.tone-danger {
  color: var(--color-danger-500, #ef4444);
}

.ai-tool-invocation__details {
  display: grid;
  gap: 0.375rem;
  margin: 0;
  padding: 0 0 0.375rem 1.5rem;
}

.ai-shell-result {
  position: relative;
  display: grid;
  gap: 0.625rem;
  margin-left: 0;
  padding: 0.75rem;
  background: var(--color-bg-page, #f8f9fc);
  border-radius: var(--radius-md, 0.375rem);
}

.ai-shell-result__header,
.ai-shell-result__footer {
  display: flex;
  align-items: center;
}

.ai-shell-result__header {
  justify-content: space-between;
  min-height: 1.875rem;
  color: var(--color-text-secondary, #4b5268);
  font-weight: 600;
}

.ai-shell-result__copy {
  opacity: 0;
  transition: opacity 0.16s ease;
}

.ai-shell-result:hover .ai-shell-result__copy,
.ai-shell-result:focus-within .ai-shell-result__copy {
  opacity: 1;
}

.ai-shell-result__output {
  max-height: 16rem;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  color: var(--color-text-primary, #0f1117);
  font-size: 0.8125rem;
  line-height: 1.55;
}

.ai-shell-result__footer {
  justify-content: flex-end;
  gap: 0.375rem;
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.8125rem;
}

.ai-shell-result__footer.tone-success {
  color: var(--color-success-600, #059669);
}

.ai-shell-result__footer.tone-running {
  color: var(--color-primary-600, #4f46e5);
}

.ai-shell-result__footer.tone-danger {
  color: var(--color-danger-600, #dc2626);
}

.ai-tool-invocation__row {
  display: grid;
  grid-template-columns: 6rem minmax(0, 1fr);
  gap: 0.625rem;
}

.ai-tool-invocation__row dt {
  color: var(--color-text-tertiary, #8b92a8);
  font-weight: 700;
}

.ai-tool-invocation__row dd {
  min-width: 0;
  margin: 0;
  color: var(--color-text-secondary, #4b5268);
}

.ai-tool-invocation__row pre {
  max-height: 10rem;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 0.75rem;
  line-height: 1.45;
}

.ai-event__actions,
.ai-approval__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.625rem;
}

.tone-danger,
.ai-inspector-row.danger {
  color: var(--color-danger-600, #dc2626);
}

.ai-composer {
  display: grid;
  grid-template-rows: auto auto;
  gap: 0.375rem;
  padding: 0.625rem 0.625rem;
  background: var(--color-bg-surface, #ffffff);
}

.ai-composer__body {
  min-width: 0;
}

.ai-composer__input {
  border-radius: 0.5rem;
}

.ai-composer__actions,
.ai-composer__left-actions {
  display: flex;
  align-items: center;
}

.ai-composer__actions {
  justify-content: space-between;
  gap: 0.625rem;
}

.ai-composer__left-actions {
  min-width: 0;
  gap: 0.25rem;
}

.ai-composer__model-config {
  position: relative;
  display: inline-flex;
}

.ai-composer__model-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 0.5rem);
  z-index: 20;
  width: min(26rem, calc(100vw - 3rem));
  background: var(--color-bg-surface, #ffffff);
  border-radius: var(--radius-lg, 0.5rem);
  box-shadow: var(--shadow-lg, 0 1rem 2rem rgba(15, 17, 23, 0.14));
}

.ai-composer__icon-button,
.ai-composer__permission {
  min-width: var(--ai-icon-button-size);
  height: var(--ai-icon-button-size);
  border-radius: var(--ai-icon-button-radius);
}

.ai-composer__permission {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  max-width: 12rem;
  color: var(--color-text-secondary, #4b5268);
}

.ai-composer__send {
  width: var(--ai-icon-button-size);
  height: var(--ai-icon-button-size);
  border-radius: var(--ai-icon-button-radius);
}

.ai-inspector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  overflow-x: hidden;
}

.ai-inspector__header {
  gap: 0.75rem;
  padding: 0.625rem;
  background: transparent;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-task,
.ai-inspector-row,
.ai-approval {
  gap: 0.625rem;
  padding: 0.625rem;
  background: var(--color-bg-surface, #ffffff);
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-task > div,
.ai-inspector-row > div,
.ai-approval > div {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-task__status {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary, #8b92a8);
  flex: 0 0 auto;
}

.ai-task__status.status-running {
  color: var(--color-primary-600, #4f46e5);
}

.ai-task__status.status-done {
  color: var(--color-success-500, #10b981);
}

.ai-task__status.status-danger {
  color: var(--color-danger-500, #ef4444);
}

.ai-task__status.status-waiting {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-task__spinner {
  animation: ai-spin 0.9s linear infinite;
}

.ai-task__done {
  color: var(--color-success-500, #10b981);
}

.ai-plan {
  display: grid;
  gap: 0.625rem;
}

.ai-plan__row,
.ai-plan__block,
.ai-plan__step {
  min-width: 0;
  padding: 0.625rem;
  background: var(--color-bg-surface, #ffffff);
  border-radius: var(--radius-md, 0.375rem);
}

.ai-plan__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.625rem;
}

.ai-plan__block {
  display: grid;
  gap: 0.25rem;
}

.ai-plan__row span,
.ai-plan__block span,
.ai-plan__step small {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
}

.ai-plan__row strong,
.ai-plan__block p,
.ai-plan__step strong {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
}

.ai-plan__steps {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ai-plan__step {
  display: grid;
  grid-template-columns: 0.625rem minmax(0, 1fr);
  align-items: center;
  gap: 0.625rem;
}

.ai-plan__step > div {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-plan__step-status {
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 999rem;
  background: var(--color-text-tertiary, #8b92a8);
}

.ai-plan__step-status.status-running {
  background: var(--color-primary-600, #4f46e5);
}

.ai-plan__step-status.status-done {
  background: var(--color-success-500, #10b981);
}

.ai-plan__step-status.status-danger {
  background: var(--color-danger-500, #ef4444);
}

.ai-approval {
  align-items: flex-start;
  flex-direction: column;
}

.ai-usage-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.375rem 0.75rem;
  padding: 0.625rem;
  background: var(--color-bg-page, #f8f9fc);
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-usage-grid span {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-context-layers {
  display: grid;
  gap: 0.25rem;
  margin: 0.375rem 0 0;
  padding: 0;
  list-style: none;
}

.ai-context-layers li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  min-width: 0;
}

.ai-context-layers strong,
.ai-context-layers small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-context-layers small {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-execution-steps {
  display: grid;
  gap: 0.375rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ai-execution-steps li {
  display: grid;
  grid-template-columns: 1.75rem minmax(0, 1fr);
  gap: 0.5rem;
  align-items: start;
  font-size: 0.75rem;
  color: var(--color-text-secondary, #4b5268);
}

.ai-execution-step__status {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--color-border-strong, #c7ccd8);
}

.ai-execution-step__status.status-running {
  background: transparent;
  color: var(--color-primary-600, #4f46e5);
}

.ai-execution-step__status.status-done {
  background: transparent;
  color: var(--color-success-500, #10b981);
}

.ai-execution-step__status.status-waiting {
  background: transparent;
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-execution-step__status.status-danger {
  background: transparent;
  color: var(--color-danger-500, #ef4444);
}

.ai-execution-step__spinner {
  animation: ai-spin 0.9s linear infinite;
}

.ai-execution-step__done {
  color: var(--color-success-500, #10b981);
}

.ai-execution-step__pending {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-execution-steps span {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-execution-steps div {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-execution-steps strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-execution-steps small {
  color: var(--color-text-tertiary, #8b92a8);
}

.statusPulse {
  animation: ai-pulse 1.2s ease-in-out infinite;
}

@keyframes ai-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes ai-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.35);
  }
  100% {
    box-shadow: 0 0 0 0.625rem rgba(99, 102, 241, 0);
  }
}

@media (max-width: 70rem) {
  .ai-shell {
    grid-template-columns: 12rem minmax(22rem, 1fr) 16rem;
    gap: 0;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .ai-composer__model-panel {
    right: auto;
    left: 0;
    width: min(22rem, calc(100vw - 2rem));
  }
}
</style>
