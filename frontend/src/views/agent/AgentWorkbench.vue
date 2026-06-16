<template>
  <div ref="workbenchShellRef" class="agent-workbench" :class="{ 'debug-open': debugPanelOpen }" data-testid="agent-workbench-shell">
    <header class="workbench-header">
      <div class="workbench-title-block">
        <button type="button" class="icon-button" aria-label="返回 Agent 列表" @click="goBack">
          <span><ArrowLeftOutlined /></span>
        </button>
        <div class="agent-avatar" aria-hidden="true">A</div>
        <div class="header-name-block">
          <a-input
            v-if="editingHeaderName"
            v-model:value="form.name"
            class="header-name-input"
            placeholder="请输入 Agent 名称"
            @blur="editingHeaderName = false"
            @keyup.enter="editingHeaderName = false"
          />
          <button
            v-else
            type="button"
            class="header-name-button"
            aria-label="修改 Agent 名称"
            @click="editingHeaderName = true"
          >
            <h1>{{ form.name || headerTitle }}</h1>
            <span>✎</span>
          </button>
          <p>{{ isCreateMode ? '创建新的 Agent 工作台草稿' : `Agent #${agentId}` }}</p>
        </div>
        <span class="agent-mode-pill">单 Agent（自主规划模式）</span>
      </div>
      <div class="workbench-actions">
        <span class="save-state">草稿自动保存于</span>
        <span class="save-state-plain">{{ saveStateText }}</span>
        <button type="button" class="primary-action" :disabled="!canSave" @click="saveWorkbench">
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
        <button type="button" class="publish-action" @click="releaseDialogOpen = true">发布</button>
      </div>
    </header>

    <main ref="workbenchGridRef" class="workbench-grid" :class="{ 'debug-open': debugPanelOpen }">
      <section ref="personaColumnRef" class="persona-column" data-testid="agent-persona-column">
        <div class="column-header">
          <div>
            <h2>人设与回复逻辑</h2>
          </div>
          <div class="helper-toolbar">
            <button type="button" class="toolbar-icon-button" aria-label="Prompt 优化" title="Prompt 优化" @click="promptOptimizerOpen = true">
              <span aria-hidden="true"><BulbOutlined /></span>
            </button>
          </div>
        </div>

        <div class="editor-panel persona-editor" data-testid="agent-workbench-editor">
          <div v-if="backendError" class="backend-error" data-testid="agent-backend-error">
            {{ backendError }}
          </div>
          <div class="field-row prompt-row">
            <a-textarea
              v-model:value="form.systemPrompt"
              :rows="24"
              placeholder="定义 Agent 的角色、行为和约束..."
              class="prompt-editor"
            />
          </div>
        </div>
      </section>

      <section ref="orchestrationColumnRef" class="editor-area" data-testid="agent-orchestration-column">
        <div class="editor-toolbar">
          <div>
            <strong>编排</strong>
          </div>
        </div>

        <div v-if="runtimeMode.warnings.length" class="runtime-summary" data-testid="agent-runtime-summary">
          <strong>运行优先级提示</strong>
          <ul>
            <li v-for="warning in runtimeMode.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </div>

        <div v-if="backendError" class="backend-error" data-testid="agent-backend-error">
          {{ backendError }}
        </div>

        <ul v-if="readinessMessages.length" class="readiness-list" data-testid="agent-readiness-list">
          <li v-for="message in readinessMessages" :key="message">{{ message }}</li>
        </ul>

        <details class="orchestration-card module-card" open>
          <summary class="module-summary">
            <div>
              <strong>模型设置</strong>
              <span>当前 Agent 运行使用的模型与生成参数。</span>
            </div>
          </summary>
          <div class="field-row">
            <label>模型</label>
            <div>
              <a-select
                v-model:value="form.modelConfigId"
                placeholder="请选择模型"
                show-search
                :loading="modelsLoading"
                style="width: 100%;"
              >
                <a-select-opt-group
                  v-for="group in modelGroups"
                  :key="group.providerName"
                  :label="group.providerName"
                >
                  <a-select-option
                    v-for="model in group.models"
                    :key="model.modelConfigId"
                    :value="model.modelConfigId"
                  >
                    {{ model.modelName }}
                  </a-select-option>
                </a-select-opt-group>
              </a-select>
              <p v-if="fieldError('modelConfigId')" class="field-error">{{ fieldError('modelConfigId') }}</p>
            </div>
          </div>
          <div class="field-row">
            <label>生成随机性</label>
            <div class="inline-control">
              <a-slider v-model:value="form.temperature" :min="0" :max="1" :step="0.1" />
              <span>{{ form.temperature.toFixed(1) }}</span>
            </div>
          </div>
          <div class="field-row">
            <label>最大回复长度</label>
            <a-input-number v-model:value="form.maxTokens" :min="1" :max="32768" :step="256" />
          </div>
          <div class="field-row">
            <label>上下文轮数</label>
            <a-input-number v-model:value="form.maxContextTurns" :min="1" :max="100" />
          </div>
        </details>

        <details class="orchestration-card module-card" open>
          <summary class="module-summary">
            <div>
              <strong>对话体验</strong>
              <span>开场白和用户问题建议。</span>
            </div>
          </summary>
          <div class="field-row">
            <label>开场白</label>
            <a-textarea
              v-model:value="form.openingMessage"
              :rows="3"
              placeholder="进入对话后的第一句助手消息"
            />
          </div>
          <div class="field-row">
            <label>用户问题建议</label>
            <div class="suggested-editor">
              <div
                v-for="(_question, index) in form.suggestedQuestions"
                :key="index"
                class="suggested-row"
              >
                <a-input v-model:value="form.suggestedQuestions[index]" placeholder="输入猜你想问" />
                <button type="button" class="icon-button" aria-label="删除引导问题" @click="removeSuggestedQuestion(index)">
                  ×
                </button>
              </div>
              <button type="button" class="text-action" @click="addSuggestedQuestion">+ 添加引导问题</button>
            </div>
          </div>
        </details>

        <details class="context-panel orchestration-card module-card" data-testid="agent-context-panel" open>
          <summary class="module-summary">
            <div>
              <strong>记忆</strong>
              <span>变量和长期记忆的当前 MVP 配置。</span>
            </div>
          </summary>
          <section class="context-card">
            <div class="capability-card-header">
              <div>
                <strong>Agent 变量</strong>
                <span>变量默认值会参与每次 Agent 运行，Preview 可临时覆盖。</span>
              </div>
              <button type="button" class="text-action" @click="addVariable">+ 添加变量</button>
            </div>
            <div v-if="form.variables.length === 0" class="empty-hint">暂无变量，添加后可在 Preview 输入覆盖值。</div>
            <div v-else class="variable-list">
              <article v-for="(variable, index) in form.variables" :key="index" class="variable-row">
                <a-input v-model:value="variable.name" placeholder="变量名，如 customer_name" />
                <a-select v-model:value="variable.type" placeholder="类型" style="width: 7.5rem;">
                  <a-select-option value="string">string</a-select-option>
                  <a-select-option value="number">number</a-select-option>
                  <a-select-option value="boolean">boolean</a-select-option>
                  <a-select-option value="json">json</a-select-option>
                </a-select>
                <a-input v-model:value="variable.defaultValue" placeholder="默认值" />
                <a-checkbox v-model:checked="variable.required">必填</a-checkbox>
                <button type="button" class="icon-button" aria-label="删除变量" @click="removeVariable(index)">×</button>
                <a-input v-model:value="variable.description" class="variable-description" placeholder="描述" />
              </article>
            </div>
            <p v-if="fieldError('variables')" class="field-error">{{ fieldError('variables') }}</p>
          </section>

          <section class="context-card">
            <div class="capability-card-header">
              <div>
                <strong>Agent Memory</strong>
                <span>当前 MVP 为单 Agent durable memory，按 key/value 注入运行时上下文。</span>
              </div>
              <button type="button" class="text-action" @click="addMemoryRow">+ 添加记忆</button>
            </div>
            <div v-if="memoryRows.length === 0" class="empty-hint">暂无 memory。</div>
            <div v-else class="memory-list">
              <article v-for="(row, index) in memoryRows" :key="index" class="memory-row">
                <a-input v-model:value="row.key" placeholder="key，如 profile" @input="syncMemoryRows" />
                <a-input v-model:value="row.value" placeholder="value，如 prefers concise replies" @input="syncMemoryRows" />
                <button type="button" class="icon-button" aria-label="删除记忆" @click="removeMemoryRow(index)">×</button>
              </article>
            </div>
          </section>
        </details>

        <details class="capability-grid orchestration-card module-card" data-testid="agent-capability-cards" open>
          <summary class="module-summary">
            <div>
              <strong>技能</strong>
              <span>工具和工作流能力。</span>
            </div>
          </summary>
          <section class="capability-card">
            <div class="capability-card-header">
              <div>
                <strong>MCP 工具</strong>
                <span>{{ capabilitySummary.toolCount }} 个 Server 已绑定</span>
              </div>
              <button type="button" class="text-action" @click="router.push({ name: 'HifyMcp' })">管理</button>
            </div>
            <div v-if="mcpServers.length === 0" class="empty-hint">暂无启用的 MCP Server</div>
            <a-select
              v-else
              v-model:value="form.toolIds"
              class="capability-select"
              data-testid="agent-mcp-tool-select"
              allow-clear
              show-search
              mode="multiple"
              placeholder="搜索并选择 MCP Server"
              style="width: 100%;"
              :max-tag-count="2"
            >
              <a-select-option
                v-for="server in mcpServers"
                :key="server.id"
                :value="server.id"
              >
                <div class="capability-option">
                  <strong>{{ server.name }}</strong>
                  <span>{{ server.endpoint }}</span>
                </div>
              </a-select-option>
            </a-select>
          </section>

          <details class="capability-card advanced-tool-policy" data-testid="agent-tool-policy-panel">
            <summary class="capability-card-header">
              <div>
                <strong>高级工具策略</strong>
                <span>非 Coze 基础可见项；用于治理工具可用性、预设参数和超时。</span>
              </div>
              <span class="status-pill">{{ toolPolicyNames.length }} 个策略</span>
            </summary>
            <div v-if="toolPolicyNames.length === 0" class="empty-hint">绑定 MCP Server 后可配置工具策略。</div>
            <div v-else class="tool-policy-list">
              <article v-for="toolName in toolPolicyNames" :key="toolName" class="tool-policy-row">
                <header class="tool-policy-row-header">
                  <div class="tool-policy-title">
                    <strong>{{ toolName }}</strong>
                    <span>运行时实际约束该工具的调用、参数和超时。</span>
                  </div>
                  <a-switch v-model:checked="form.toolPolicies[toolName].enabled" checked-children="启用" un-checked-children="禁用" />
                </header>
                <div class="tool-policy-controls">
                  <label class="tool-policy-field">
                    <span>调用模式</span>
                    <a-select v-model:value="form.toolPolicies[toolName].callMode">
                      <a-select-option value="auto">auto</a-select-option>
                      <a-select-option value="required">required</a-select-option>
                    </a-select>
                  </label>
                  <label class="tool-policy-field">
                    <span>超时 ms</span>
                    <a-input-number v-model:value="form.toolPolicies[toolName].timeoutMs" :min="1" :max="120000" />
                  </label>
                </div>
                <label class="tool-policy-field tool-policy-presets">
                  <span>参数预设 JSON</span>
                  <a-input
                    v-model:value="toolPolicyPresetText[toolName]"
                    placeholder='如 {"orderId":"A-200"}'
                    @change="syncToolPolicyPreset(toolName)"
                  />
                </label>
              </article>
            </div>
          </details>

          <div class="capability-card-header sub-section-heading">
            <div>
              <strong>知识</strong>
              <span>文本、表格、照片知识的 MVP 映射为多知识库检索设置。</span>
            </div>
          </div>

          <section class="capability-card">
            <div class="capability-card-header">
              <div>
                <strong>知识库</strong>
                <span>{{ selectedKnowledgeBaseName }}</span>
              </div>
              <button
                type="button"
                class="text-action"
                :disabled="!form.knowledgeBaseId"
                @click="openKnowledgeBase"
              >
                打开
              </button>
            </div>
            <a-select
              v-model:value="form.knowledgeBaseIds"
              allow-clear
              show-search
              mode="multiple"
              placeholder="不绑定知识库"
              style="width: 100%;"
              :loading="capabilitiesLoading"
              @change="syncPrimaryKnowledgeBase"
            >
              <a-select-option v-for="kb in knowledgeBaseOptions" :key="kb.id" :value="kb.id">{{ kb.name }}</a-select-option>
            </a-select>
            <div class="retrieval-settings" data-testid="agent-retrieval-settings">
              <label>
                <span>检索方式</span>
                <a-select v-model:value="form.retrievalSettings.retrievalMode">
                  <a-select-option
                    v-for="option in retrievalModeOptions"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </a-select-option>
                </a-select>
              </label>
              <label>
                <span>返回条数</span>
                <a-input-number v-model:value="form.retrievalSettings.topK" :min="1" :max="20" />
              </label>
              <label>
                <span>最低命中分</span>
                <a-slider v-model:value="form.retrievalSettings.scoreThreshold" :min="0" :max="1" :step="0.05" />
              </label>
              <label>
                <span>结果重排</span>
                <a-switch v-model:checked="form.retrievalSettings.rerank" />
              </label>
              <label>
                <span>引用格式</span>
                <a-select v-model:value="form.retrievalSettings.citationStyle">
                  <a-select-option value="numbered">编号引用</a-select-option>
                  <a-select-option value="inline">行内引用</a-select-option>
                </a-select>
              </label>
            </div>
          </section>

          <section class="capability-card">
            <div class="capability-card-header">
              <div>
                <strong>工作流</strong>
                <span>{{ selectedWorkflowName }}</span>
              </div>
              <button
                type="button"
                class="text-action"
                :disabled="!form.workflowId"
                @click="openWorkflowCanvas"
              >
                打开画布
              </button>
            </div>
            <a-select
              v-model:value="form.workflowId"
              allow-clear
              show-search
              placeholder="不绑定工作流"
              style="width: 100%;"
              :loading="capabilitiesLoading"
            >
              <a-select-option v-for="workflow in workflowOptions" :key="workflow.id" :value="workflow.id">{{ workflow.name }}</a-select-option>
            </a-select>
          </section>
        </details>
      </section>

      <aside ref="previewColumnRef" class="preview-column" data-testid="agent-preview-debug-column">
      <div class="preview-area" data-testid="agent-workbench-preview">
        <div class="preview-header">
          <div class="preview-title-row">
            <strong>预览与调试</strong>
            <button
              type="button"
              class="toolbar-icon-button"
              aria-label="重置预览"
              :disabled="previewStatus === 'streaming'"
              @click="resetPreview"
            >
              <span aria-hidden="true"><ReloadOutlined /></span>
            </button>
          </div>
          <div class="preview-header-actions">
            <div v-if="previewTargetOptions.length > 1" data-testid="preview-target-select">
              <a-select v-model:value="previewTarget" size="small" :disabled="previewTargetOptions.length === 1">
                <a-select-option
                  v-for="option in previewTargetOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  <div class="preview-target-option">
                    <strong>{{ option.label }}</strong>
                    <span>{{ option.description }}</span>
                  </div>
                </a-select-option>
              </a-select>
            </div>
            <button
              type="button"
              class="toolbar-icon-button preview-debug-toggle"
              :class="{ active: debugPanelOpen }"
              :aria-label="debugPanelOpen ? '关闭调试详情' : '打开调试详情'"
              @click="toggleDebugDetail"
            >
              <span aria-hidden="true"><ToolOutlined /></span>
            </button>
          </div>
        </div>
        <div class="preview-body">
          <div v-if="previewMessages.length === 0" class="preview-empty">
            <div>
              <div
                v-if="previewGate.canSend && previewWelcome.openingMessage"
                class="preview-message assistant preview-opening-message"
                data-testid="agent-preview-opening-message"
              >
                {{ previewWelcome.openingMessage }}
              </div>
              <template v-else-if="!previewGate.canSend">
                <div class="preview-gate-message">{{ previewGate.reason }}</div>
              </template>
            </div>
            <div
              v-if="previewGate.canSend && previewWelcome.suggestedQuestions.length"
              class="preview-suggestions"
              data-testid="agent-preview-suggested-questions"
            >
                <button
                  v-for="question in previewWelcome.suggestedQuestions"
                  :key="question"
                  type="button"
                  class="suggestion-pill"
                  @click="sendSuggestedQuestion(question)"
                >
                  {{ question }}
                </button>
            </div>
            <div
              v-else-if="previewGate.canSend && !previewWelcome.openingMessage"
              class="preview-gate-message"
            >
              发送一条消息，使用已保存 Agent 状态进行预览。
            </div>
          </div>
          <div v-else class="preview-messages" data-testid="agent-preview-messages">
            <div
              v-for="message in previewMessages"
              :key="message.id"
              :class="['preview-message', message.role, { error: message.error }]"
            >
              {{ message.content || (message.loading ? '生成中...' : '') }}
            </div>
          </div>
        </div>
        <div class="preview-footer">
          <div v-if="form.variables.length" class="preview-variable-overrides" data-testid="agent-preview-variable-overrides">
            <label v-for="variable in form.variables" :key="variable.name">
              <span>{{ variable.name || '未命名变量' }}</span>
              <a-input
                v-model:value="previewVariableValues[variable.name]"
                size="small"
                :placeholder="String(variable.defaultValue ?? '默认值')"
              />
            </label>
          </div>
          <div class="preview-composer">
            <a-textarea
              v-model:value="previewInput"
              class="preview-composer-input"
              :auto-size="{ minRows: 2, maxRows: 5 }"
              placeholder="输入预览消息"
              :disabled="previewStatus === 'streaming' || previewStatus === 'creating'"
              @keydown.enter.exact.prevent="sendPreview"
            />
            <div class="preview-composer-toolbar">
              <button
                type="button"
                class="toolbar-icon-button preview-send-button"
                aria-label="发送预览消息"
                :disabled="!previewInput.trim() || !previewGate.canSend || previewStatus === 'streaming' || previewStatus === 'creating'"
                @click="sendPreview"
              >
                <span aria-hidden="true"><SendOutlined /></span>
              </button>
            </div>
          </div>
          <p class="preview-disclaimer">内容由 AI 生成，无法确保真实准确，仅供参考。</p>
          <p v-if="previewError" class="field-error">{{ previewError }}</p>
        </div>
      </div>
      </aside>

      <aside
        v-if="debugPanelOpen"
        ref="debugPanelRef"
        class="debug-detail-panel"
        data-testid="agent-debug-detail-panel"
        tabindex="-1"
      >
        <div class="debug-detail-header">
          <h2>调试详情</h2>
          <button type="button" class="debug-close" aria-label="关闭调试详情" @click="closeDebugDetail">×</button>
        </div>
        <div v-if="debugTrace" class="debug-filter-bar">
          <span class="debug-search">⌕</span>
          <span class="debug-keyword">{{ debugTrace.keyword }}</span>
        </div>
        <div v-if="debugTrace" class="debug-summary">
          <strong>耗时 {{ debugTrace.elapsedMs }}ms | 输入 {{ debugTrace.inputChars }} 字 / 输出 {{ debugTrace.outputChars }} 字</strong>
          <span class="debug-success">{{ debugTrace.status }}</span>
          <span class="debug-finish">{{ debugTrace.finishReason }}</span>
          <p>RunID：{{ debugTrace.runId }}</p>
          <p>请求发起时间：{{ debugTrace.startedAtText }} <span>首次响应耗时：{{ debugTrace.firstResponseMs }}ms</span></p>
          <p>服务端耗时：{{ debugTrace.latencyMs }}ms</p>
        </div>
        <div class="debug-tabs">
          <button type="button" :class="{ active: debugTab === 'tree' }" @click="debugTab = 'tree'">调用树</button>
          <button type="button" :class="{ active: debugTab === 'flame' }" @click="debugTab = 'flame'">火焰图</button>
        </div>
        <div v-if="debugTrace && debugTab === 'tree'" class="debug-call-tree">
          <article
            v-for="node in debugTrace.nodes"
            :key="node.id"
            :class="['debug-tree-node', { active: node.active, child: node.depth > 0 }]"
          >
            <span>{{ node.icon }}</span>
            <strong>{{ node.label }}</strong>
            <em>{{ node.detail }}</em>
          </article>
        </div>
        <div v-else-if="debugTrace" class="debug-flame-graph">
          <div class="flame-axis">
            <span v-for="tick in debugTrace.axisTicks" :key="tick">{{ tick }}ms</span>
          </div>
          <div
            v-for="lane in debugTrace.flameLanes"
            :key="lane.id"
            class="flame-lane"
            :style="{ marginLeft: `${lane.offsetPct}%`, width: `${lane.widthPct}%` }"
          >
            {{ lane.label }}
          </div>
        </div>
        <section v-if="debugTrace" class="debug-node-detail">
          <h3>节点详情</h3>
          <dl>
            <div><dt>类型</dt><dd>预览运行</dd></div>
            <div><dt>状态</dt><dd>{{ debugTrace.status }}</dd></div>
            <div><dt>模型</dt><dd>{{ selectedModelName }}</dd></div>
            <div><dt>整体耗时</dt><dd>{{ debugTrace.elapsedMs }}ms</dd></div>
            <div><dt>请求发起时间</dt><dd>{{ debugTrace.startedAtText }}</dd></div>
            <div><dt>服务端耗时</dt><dd>{{ debugTrace.latencyMs }}ms</dd></div>
            <div><dt>完成原因</dt><dd>{{ debugTrace.finishReason }}</dd></div>
            <div><dt>输入字符</dt><dd>{{ debugTrace.inputChars }}</dd></div>
            <div><dt>输出字符</dt><dd>{{ debugTrace.outputChars }}</dd></div>
          </dl>
        </section>
        <div v-else class="debug-empty-state">
          <strong>暂无调试运行数据</strong>
          <span>请先在预览面板发送一条消息，调试详情会展示真实请求、首包耗时、完成耗时和输出数据。</span>
        </div>
      </aside>
    </main>

    <a-modal v-model:open="promptOptimizerOpen" title="Prompt 优化" width="52rem" class="prompt-dialog">
      <div class="optimizer-panel" data-testid="agent-prompt-optimizer">
        <section class="context-card">
          <div class="capability-card-header">
            <div>
              <strong>Prompt 优化</strong>
              <span>调用当前 Agent 模型生成优化草稿，需手动应用到 System Prompt。</span>
            </div>
            <button
              type="button"
              class="primary-action"
              :disabled="isCreateMode || dirty || promptOptimizing"
              @click="generatePromptOptimization"
            >
              {{ promptOptimizing ? '生成中...' : '生成优化草稿' }}
            </button>
          </div>
          <a-textarea
            v-model:value="promptOptimizationInstruction"
            :rows="3"
            placeholder="输入优化要求"
          />
          <p v-if="isCreateMode" class="empty-hint">请先保存 Agent，再生成优化草稿。</p>
          <p v-else-if="dirty" class="empty-hint">当前配置有未保存更改，请先保存后再优化。</p>
          <p v-if="promptOptimizationError" class="field-error">{{ promptOptimizationError }}</p>
        </section>

        <section v-if="promptOptimizationProposal" class="context-card optimizer-result">
          <div class="optimizer-columns">
            <div>
              <strong>当前 Prompt</strong>
              <pre>{{ promptOptimizationProposal.originalPrompt || '(empty)' }}</pre>
            </div>
            <div>
              <strong>优化草稿</strong>
              <pre>{{ promptOptimizationProposal.optimizedPrompt }}</pre>
            </div>
          </div>
          <div class="optimizer-audit">
            <span>modelConfigId: {{ promptOptimizationProposal.audit.modelConfigId }}</span>
            <span>tokenEstimate: {{ promptOptimizationProposal.audit.tokenEstimate }}</span>
          </div>
          <button type="button" class="primary-action" @click="applyPromptOptimization">
            应用到 System Prompt
          </button>
        </section>
      </div>
    </a-modal>

    <a-modal v-model:open="releaseDialogOpen" title="发布" width="56rem" class="release-dialog">
      <div class="release-dialog-body">
        <section class="release-card" data-testid="agent-version-panel">
          <div class="release-card-header">
            <div>
              <strong>发布版本</strong>
              <span>发布前需要一个稳定版本快照；当前只保留版本创建和选定发布版本。</span>
            </div>
            <button
              type="button"
              class="primary-action"
              :disabled="isCreateMode || dirty || versionSaving"
              @click="createVersionSnapshot"
            >
              {{ versionSaving ? '创建中...' : '创建版本' }}
            </button>
          </div>
          <div v-if="versionsLoading" class="empty-hint">正在加载版本...</div>
          <div v-else-if="isCreateMode" class="empty-hint">请先保存 Agent，再创建版本。</div>
          <div v-else-if="dirty" class="empty-hint">当前配置有未保存更改，请保存后再创建版本。</div>
          <div v-else-if="!versions?.list.length" class="empty-hint">暂无版本，创建第一个版本后可发布。</div>
          <div v-else class="version-list">
            <article v-for="version in versions.list" :key="version.id" class="version-row">
              <div>
                <strong>v{{ version.versionNo }}</strong>
                <span>{{ version.name || '未命名版本' }}</span>
                <em>{{ version.createdAt }}</em>
              </div>
              <div class="version-row-actions">
                <span v-if="version.released" class="status-pill">已发布</span>
                <button
                  v-else
                  type="button"
                  class="secondary-action"
                  :disabled="versionReleasing"
                  @click="releaseVersionSnapshot(version.id)"
                >
                  发布版本
                </button>
              </div>
            </article>
          </div>
        </section>

        <details class="release-card advanced-release-card" data-testid="agent-evaluation-gate-panel">
          <summary class="release-card-header">
            <div>
              <strong>高级发布门禁</strong>
              <span>非发布主流程；需要评测治理时再打开。</span>
            </div>
          </summary>
          <div class="release-card-header">
            <div>
              <strong>Evaluation Gate</strong>
              <span>发布版本前检查选中的 Evaluation experiment 最新运行结果。</span>
            </div>
            <a-switch v-model:checked="form.evaluationGate.enabled" checked-children="启用" un-checked-children="关闭" />
          </div>
          <div class="evaluation-gate-grid">
            <label>
              <span>Experiment ID</span>
              <a-input-number v-model:value="form.evaluationGate.experimentId" :min="1" />
            </label>
            <label>
              <span>Required Pass Rate</span>
              <a-slider v-model:value="form.evaluationGate.requiredPassRate" :min="0" :max="1" :step="0.05" />
            </label>
          </div>
          <p class="empty-hint">
            当前 MVP 使用 Evaluation 最新 run 的 pass_rate 阻断 release/publish，报告打开与 rerun 入口沿用 Evaluation 路由。
          </p>
        </details>

        <section class="release-card" data-testid="agent-publish-panel">
          <div class="release-card-header">
            <div>
              <strong>发布渠道</strong>
              <span>当前只提供 API/channel shell，外部渠道适配器在后续 adapter spec 中落地。</span>
            </div>
            <button
              type="button"
              class="primary-action"
              :disabled="!releasedVersionId || publishing"
              @click="publishApiChannel"
            >
              {{ publishing ? '发布中...' : '发布到 API' }}
            </button>
          </div>
          <div v-if="!releasedVersionId" class="empty-hint">请先发布一个 Agent version，再开放 API 渠道。</div>
          <div v-else-if="publishesLoading" class="empty-hint">正在加载发布记录...</div>
          <div v-else-if="!publishes.length" class="empty-hint">暂无发布记录。</div>
          <div v-else class="version-list">
            <article v-for="record in publishes" :key="record.id" class="version-row">
              <div>
                <strong>{{ record.channelType }}</strong>
                <span>{{ record.status }}</span>
                <em>{{ record.endpoint }}</em>
              </div>
              <div class="version-row-actions">
                <button
                  v-if="record.status === 'PUBLISHED'"
                  type="button"
                  class="secondary-action"
                  :disabled="unpublishing"
                  @click="unpublishRecord(record.id)"
                >
                  取消发布
                </button>
              </div>
            </article>
          </div>
        </section>

        <details class="release-card advanced-release-card" data-testid="agent-access-panel">
          <summary class="release-card-header">
            <div>
              <strong>高级访问设置</strong>
              <span>非发布主流程；用于后续分享、目录和数据分析治理。</span>
            </div>
          </summary>
          <div class="access-grid">
            <label>
              <span>Access Mode</span>
              <a-select v-model:value="form.access.mode">
                <a-select-option value="PRIVATE">PRIVATE</a-select-option>
                <a-select-option value="TEAM">TEAM</a-select-option>
                <a-select-option value="PUBLIC">PUBLIC</a-select-option>
              </a-select>
            </label>
            <label>
              <span>Read-only</span>
              <a-switch v-model:checked="form.access.readonly" />
            </label>
            <label>
              <span>Share Enabled</span>
              <a-switch v-model:checked="form.sharing.enabled" />
            </label>
            <label>
              <span>Public Token</span>
              <a-input v-model:value="form.sharing.publicToken" placeholder="public token" />
            </label>
            <label>
              <span>Catalog Visible</span>
              <a-switch v-model:checked="form.catalog.visible" />
            </label>
            <label>
              <span>Catalog Category</span>
              <a-input v-model:value="form.catalog.category" placeholder="support" />
            </label>
          </div>
          <div class="access-analytics-heading">
            <strong>Analytics</strong>
            <span>使用量、延迟、错误与评测摘要。</span>
          </div>
          <div class="analytics-grid">
            <span>Usage: {{ form.analytics.usage || 0 }}</span>
            <span>Latency: {{ form.analytics.latencyMs || 0 }}ms</span>
            <span>Errors: {{ form.analytics.errors || 0 }}</span>
            <span>Evaluation: {{ form.evaluationGate.enabled ? 'gate enabled' : 'gate off' }}</span>
          </div>
        </details>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ArrowLeftOutlined, BulbOutlined, ReloadOutlined, SendOutlined, ToolOutlined } from '@ant-design/icons-vue'
import { message, Modal } from 'ant-design-vue'

import {
  bindAgentTools,
  createAgent,
  createAgentVersion,
  getAgentPreviewRunDebug,
  getAgentDetail,
  getAgentPublishes,
  getAgentVersions,
  getModelOptions,
  optimizeAgentPrompt,
  publishAgentVersion,
  releaseAgentVersion,
  unpublishAgentRecord,
  updateAgent,
} from '@/api/agent'
import type { AgentDetail, AgentPreviewRunDebugDetail, AgentPromptOptimization, AgentPublishRecord, AgentVersionList, ModelOption } from '@/api/agent'
import { createSession, deleteSession, streamMessage } from '@/api/chat'
import { listKb, type KnowledgeBase } from '@/api/knowledge'
import { getMcpServerList, type McpServerVO } from '@/api/mcp'
import { listChatflows, listWorkflows, type WorkflowListItem } from '@/api/workflow'
import {
  agentDetailToForm,
  buildPreviewVariableOverrides,
  buildPreviewWelcomeState,
  buildPreviewTargetOptions,
  buildWorkbenchReadinessMessages,
  cloneAgentForm,
  defaultAgentWorkbenchForm,
  formatWorkbenchBackendError,
  formToAgentCreatePayload,
  formToAgentUpdatePayload,
  groupModelOptions,
  isAgentFormDirty,
  resolvePreviewGate,
  resolveAgentRuntimeMode,
  resolveFlowCanvasRoute,
  summarizeAgentCapabilities,
  validateAgentWorkbenchForm,
  type AgentWorkbenchForm,
} from './agentWorkbench'
import { buildAgentPreviewDebugTrace } from './agentPreviewDebug'

const route = useRoute()
const router = useRouter()

type PreviewStatus = 'idle' | 'creating' | 'streaming' | 'done' | 'error'
type PreviewMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  loading?: boolean
  error?: boolean
  createdAt: number
  firstDeltaAt?: number
  completedAt?: number
  finishReason?: string
  latencyMs?: number
}
type DebugTab = 'tree' | 'flame'
const retrievalModeOptions = [
  { label: '智能推荐', value: 'auto' },
  { label: '综合匹配', value: 'hybrid' },
  { label: '语义理解', value: 'semantic' },
  { label: '关键词匹配', value: 'keyword' },
  { label: '仅问答库', value: 'faq' },
]

const editingHeaderName = ref(false)
const releaseDialogOpen = ref(false)
const promptOptimizerOpen = ref(false)
const debugPanelOpen = ref(false)
const debugTab = ref<DebugTab>('tree')
const loading = ref(false)
const saving = ref(false)
const modelsLoading = ref(false)
const capabilitiesLoading = ref(false)
const versionsLoading = ref(false)
const versionSaving = ref(false)
const versionReleasing = ref(false)
const publishesLoading = ref(false)
const publishing = ref(false)
const unpublishing = ref(false)
const detail = ref<AgentDetail | null>(null)
const versions = ref<AgentVersionList | null>(null)
const publishes = ref<AgentPublishRecord[]>([])
const form = ref<AgentWorkbenchForm>(defaultAgentWorkbenchForm())
const baseline = ref<AgentWorkbenchForm>(defaultAgentWorkbenchForm())
const modelOptions = ref<ModelOption[]>([])
const mcpServers = ref<McpServerVO[]>([])
const knowledgeBaseOptions = ref<KnowledgeBase[]>([])
const workflowOptions = ref<WorkflowListItem[]>([])
const previewInput = ref('')
const previewTarget = ref('draft')
const previewStatus = ref<PreviewStatus>('idle')
const previewSessionId = ref<number | null>(null)
const previewMessages = ref<PreviewMessage[]>([])
const previewError = ref('')
const previewRunDebugDetail = ref<AgentPreviewRunDebugDetail | null>(null)
const backendError = ref('')
const previewVariableValues = ref<Record<string, unknown>>({})
const memoryRows = ref<Array<{ key: string; value: string }>>([])
const toolPolicyPresetText = ref<Record<string, string>>({})
const promptOptimizationInstruction = ref('')
const promptOptimizationProposal = ref<AgentPromptOptimization | null>(null)
const promptOptimizationError = ref('')
const promptOptimizing = ref(false)
const workbenchShellRef = ref<HTMLElement | null>(null)
const workbenchGridRef = ref<HTMLElement | null>(null)
const personaColumnRef = ref<HTMLElement | null>(null)
const orchestrationColumnRef = ref<HTMLElement | null>(null)
const previewColumnRef = ref<HTMLElement | null>(null)
const debugPanelRef = ref<HTMLElement | null>(null)
let previewAbort: AbortController | null = null

const agentId = computed(() => Number(route.params.id || 0))
const isCreateMode = computed(() => route.path === '/agents/new')
const headerTitle = computed(() => detail.value?.name || (isCreateMode.value ? '新建 Agent' : 'Agent Workbench'))
const modelGroups = computed(() => groupModelOptions(modelOptions.value))
const selectedModelName = computed(() =>
  modelOptions.value.find((model) => model.modelConfigId === form.value.modelConfigId)?.modelName || '当前模型',
)
const validationErrors = computed(() => validateAgentWorkbenchForm(form.value))
const dirty = computed(() => isAgentFormDirty(form.value, baseline.value))
const canSave = computed(() => !loading.value && !saving.value && validationErrors.value.length === 0 && dirty.value)
const capabilitySummary = computed(() => summarizeAgentCapabilities(form.value))
const runtimeMode = computed(() => resolveAgentRuntimeMode(form.value))
const previewGate = computed(() => resolvePreviewGate({
  isCreateMode: isCreateMode.value,
  dirty: dirty.value,
  streaming: previewStatus.value === 'streaming' || previewStatus.value === 'creating',
}))
const previewWelcome = computed(() => buildPreviewWelcomeState(form.value))
const debugTrace = computed(() => {
  const previewTrace = buildAgentPreviewDebugTrace(previewRunDebugDetail.value)
  if (previewTrace) return previewTrace
  const latestAssistant = [...previewMessages.value].reverse().find((message) => message.role === 'assistant')
  const latestUser = [...previewMessages.value].reverse().find((message) => message.role === 'user')
  if (!latestAssistant || !latestUser) return null
  const startedAt = latestUser?.createdAt || latestAssistant?.createdAt
  const completedAt = latestAssistant?.completedAt || latestAssistant?.firstDeltaAt || Date.now()
  const elapsedMs = startedAt && completedAt ? Math.max(0, completedAt - startedAt) : 0
  const firstResponseMs = startedAt && latestAssistant?.firstDeltaAt ? Math.max(0, latestAssistant.firstDeltaAt - startedAt) : 0
  const llmOffset = elapsedMs > 0 ? Math.max(8, Math.min(92, Math.round((firstResponseMs / elapsedMs) * 100))) : 8
  const llmWidth = Math.max(8, 100 - llmOffset)
  return {
    keyword: latestUser.content || 'preview',
    elapsedMs,
    firstResponseMs,
    latencyMs: latestAssistant.latencyMs ?? elapsedMs,
    inputChars: latestUser.content.length,
    outputChars: latestAssistant.content.length,
    status: latestAssistant.error ? '失败' : latestAssistant.loading ? '运行中' : '成功',
    finishReason: latestAssistant.finishReason || (latestAssistant.loading ? 'streaming' : latestAssistant.error ? 'error' : 'stop'),
    runId: `preview-session-${previewSessionId.value ?? 'pending'}-${latestAssistant.id}`,
    startedAtText: formatDebugTime(startedAt),
    nodes: [
      { id: 'user', depth: 0, active: true, icon: '↪', label: '用户输入', detail: 'UserInput' },
      { id: 'llm', depth: 1, active: false, icon: '●', label: '调用 LLM', detail: selectedModelName.value },
    ],
    axisTicks: buildDebugAxisTicks(elapsedMs),
    flameLanes: [
      { id: 'user', label: '用户输入 UserInput', offsetPct: 0, widthPct: llmOffset },
      { id: 'llm', label: `调用 LLM ${selectedModelName.value}`, offsetPct: llmOffset, widthPct: llmWidth },
    ],
  }
})
const previewTargetOptions = computed(() => buildPreviewTargetOptions(versions.value))
const releasedVersionId = computed(() => versions.value?.releasedVersionId ?? null)
const readinessMessages = computed(() => buildWorkbenchReadinessMessages({
  modelCount: modelOptions.value.length,
  mcpServerCount: mcpServers.value.length,
  knowledgeBaseCount: knowledgeBaseOptions.value.length,
  workflowCount: workflowOptions.value.length,
}))
const selectedKnowledgeBaseName = computed(() =>
  form.value.knowledgeBaseIds.length
    ? `${form.value.knowledgeBaseIds.length} 个知识库`
    : '未绑定',
)
const selectedWorkflowName = computed(() =>
  workflowOptions.value.find((workflow) => workflow.id === form.value.workflowId)?.name || '未绑定',
)
const toolPolicyNames = computed(() => {
  if (!form.value.toolIds.length) return []
  ensureToolPolicy('lookup_order')
  return ['lookup_order']
})
const saveStateText = computed(() => {
  if (loading.value) return '正在载入...'
  if (saving.value) return '正在保存...'
  return dirty.value ? '未保存更改' : '已保存'
})

onMounted(async () => {
  await Promise.all([loadModelOptions(), loadCapabilityOptions()])
  if (isCreateMode.value || !agentId.value) {
    resetForm(defaultAgentWorkbenchForm())
    return
  }
  loading.value = true
  try {
    detail.value = await getAgentDetail(agentId.value)
    resetForm(agentDetailToForm(detail.value))
    await loadVersions()
    await loadPublishes()
    await applyPreviewRunDebugRoute()
  } catch {
    message.error('加载 Agent 工作台失败')
  } finally {
    loading.value = false
  }
})

onBeforeRouteLeave((_to, _from, next) => {
  if (!dirty.value) {
    next()
    return
  }
  Modal.confirm({
    title: '提示',
    content: '当前 Agent 配置有未保存更改，确定离开吗？',
    okText: '确认',
    cancelText: '取消',
    onOk: () => next(),
    onCancel: () => next(false),
  })
})

function goBack() {
  router.push({ name: 'HifyAgent' })
}

async function loadModelOptions() {
  modelsLoading.value = true
  try {
    modelOptions.value = await getModelOptions()
  } finally {
    modelsLoading.value = false
  }
}

async function loadCapabilityOptions() {
  capabilitiesLoading.value = true
  try {
    const [serverPage, knowledgePage, workflowPage, chatflowPage] = await Promise.all([
      getMcpServerList({ page: 1, pageSize: 100, enabled: 1 }),
      listKb({ page: 1, pageSize: 100 }),
      listWorkflows({ page: 1, pageSize: 100 }),
      listChatflows({ page: 1, pageSize: 100 }),
    ])
    mcpServers.value = serverPage.list
    knowledgeBaseOptions.value = knowledgePage.list.filter((kb) => kb.enabled === 1)
    workflowOptions.value = [...workflowPage.list, ...chatflowPage.list]
  } finally {
    capabilitiesLoading.value = false
  }
}

async function loadVersions() {
  if (isCreateMode.value || !agentId.value) {
    versions.value = null
    previewTarget.value = 'draft'
    return
  }
  versionsLoading.value = true
  try {
    versions.value = await getAgentVersions(agentId.value)
    if (!previewTargetOptions.value.some((option) => option.value === previewTarget.value)) {
      previewTarget.value = 'draft'
    }
  } finally {
    versionsLoading.value = false
  }
}

async function loadPublishes() {
  if (isCreateMode.value || !agentId.value) {
    publishes.value = []
    return
  }
  publishesLoading.value = true
  try {
    publishes.value = (await getAgentPublishes(agentId.value)).list
  } finally {
    publishesLoading.value = false
  }
}

function resetForm(next: AgentWorkbenchForm) {
  form.value = cloneAgentForm(next)
  baseline.value = cloneAgentForm(next)
  memoryRows.value = Object.entries(next.memory || {}).map(([key, value]) => ({ key, value: String(value ?? '') }))
  previewVariableValues.value = Object.fromEntries((next.variables || []).map((variable) => [variable.name, '']))
  toolPolicyPresetText.value = Object.fromEntries(
    Object.entries(next.toolPolicies || {}).map(([toolName, policy]) => [
      toolName,
      JSON.stringify(policy.argumentPresets || {}),
    ]),
  )
}

function fieldError(field: keyof AgentWorkbenchForm) {
  return validationErrors.value.find((error) => error.field === field)?.message || ''
}

function addSuggestedQuestion() {
  form.value.suggestedQuestions.push('')
}

function removeSuggestedQuestion(index: number) {
  form.value.suggestedQuestions.splice(index, 1)
}

function addVariable() {
  form.value.variables.push({
    name: '',
    type: 'string',
    defaultValue: '',
    required: false,
    description: '',
  })
}

function removeVariable(index: number) {
  form.value.variables.splice(index, 1)
}

function addMemoryRow() {
  memoryRows.value.push({ key: '', value: '' })
  syncMemoryRows()
}

function removeMemoryRow(index: number) {
  memoryRows.value.splice(index, 1)
  syncMemoryRows()
}

function syncMemoryRows() {
  const memory: Record<string, unknown> = {}
  for (const row of memoryRows.value) {
    const key = row.key.trim()
    if (!key) continue
    memory[key] = row.value
  }
  form.value.memory = memory
}

function ensureToolPolicy(toolName: string) {
  if (form.value.toolPolicies[toolName]) return
  form.value.toolPolicies[toolName] = {
    enabled: true,
    callMode: 'auto',
    argumentPresets: {},
    approvalRequired: false,
    timeoutMs: 30000,
    failureBehavior: 'return_error',
  }
  toolPolicyPresetText.value[toolName] = '{}'
}

function syncToolPolicyPreset(toolName: string) {
  ensureToolPolicy(toolName)
  try {
    const parsed = JSON.parse(toolPolicyPresetText.value[toolName] || '{}')
    form.value.toolPolicies[toolName].argumentPresets = parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed
      : {}
  } catch {
    form.value.toolPolicies[toolName].argumentPresets = {}
  }
}

function syncPrimaryKnowledgeBase() {
  form.value.knowledgeBaseId = form.value.knowledgeBaseIds[0] ?? null
}

async function generatePromptOptimization() {
  if (isCreateMode.value || dirty.value || !agentId.value) return
  promptOptimizationError.value = ''
  promptOptimizing.value = true
  try {
    promptOptimizationProposal.value = await optimizeAgentPrompt(agentId.value, promptOptimizationInstruction.value)
    message.success('优化草稿已生成')
  } catch (error: any) {
    promptOptimizationError.value = formatWorkbenchBackendError(error)
    message.error(promptOptimizationError.value)
  } finally {
    promptOptimizing.value = false
  }
}

function applyPromptOptimization() {
  if (!promptOptimizationProposal.value) return
  form.value.systemPrompt = promptOptimizationProposal.value.optimizedPrompt
  promptOptimizerOpen.value = false
  message.success('已应用到 System Prompt，请保存配置')
}

async function saveWorkbench() {
  if (!canSave.value) return
  saving.value = true
  backendError.value = ''
  try {
    if (isCreateMode.value) {
      const created = await createAgent(formToAgentCreatePayload(form.value))
      detail.value = created
      resetForm(agentDetailToForm(created))
      await router.replace({ name: 'HifyAgentWorkbench', params: { id: created.id } })
      await loadVersions()
      await loadPublishes()
      message.success('Agent 创建成功')
      return
    }
    const updated = await updateAgent(agentId.value, formToAgentUpdatePayload(form.value))
    await bindAgentTools(agentId.value, form.value.toolIds)
    const updatedWithTools = { ...updated, toolIds: [...form.value.toolIds] }
    detail.value = updatedWithTools
    resetForm(agentDetailToForm(updatedWithTools))
    await loadVersions()
    await loadPublishes()
    message.success('Agent 保存成功')
  } catch (error: any) {
    backendError.value = formatWorkbenchBackendError(error)
    message.error(backendError.value)
  } finally {
    saving.value = false
  }
}

async function createVersionSnapshot() {
  if (isCreateMode.value || dirty.value || !agentId.value) return
  versionSaving.value = true
  try {
    const version = await createAgentVersion(agentId.value, `Snapshot ${new Date().toLocaleString()}`)
    await loadVersions()
    previewTarget.value = `latest:${version.id}`
    message.success('版本已创建')
  } catch (error: any) {
    message.error(formatWorkbenchBackendError(error))
  } finally {
    versionSaving.value = false
  }
}

async function releaseVersionSnapshot(versionId: number) {
  if (!agentId.value) return
  versionReleasing.value = true
  try {
    const version = await releaseAgentVersion(agentId.value, versionId)
    await loadVersions()
    await loadPublishes()
    previewTarget.value = `released:${version.id}`
    message.success('版本已发布')
  } catch (error: any) {
    message.error(formatWorkbenchBackendError(error))
  } finally {
    versionReleasing.value = false
  }
}

async function publishApiChannel() {
  if (!agentId.value || !releasedVersionId.value) return
  publishing.value = true
  try {
    await publishAgentVersion(agentId.value, releasedVersionId.value, 'API')
    await loadPublishes()
    message.success('API 渠道已发布')
  } catch (error: any) {
    message.error(formatWorkbenchBackendError(error))
  } finally {
    publishing.value = false
  }
}

async function unpublishRecord(recordId: number) {
  if (!agentId.value) return
  unpublishing.value = true
  try {
    await unpublishAgentRecord(agentId.value, recordId)
    await loadPublishes()
    message.success('已取消发布')
  } catch (error: any) {
    message.error(formatWorkbenchBackendError(error))
  } finally {
    unpublishing.value = false
  }
}

function openKnowledgeBase() {
  if (!form.value.knowledgeBaseId) return
    router.push({ name: 'HifyKnowledgeDocuments', params: { kbId: form.value.knowledgeBaseId } })
}

function openWorkflowCanvas() {
  if (!form.value.workflowId) return
  const flow = workflowOptions.value.find((workflow) => workflow.id === form.value.workflowId)
    router.push(resolveFlowCanvasRoute({ id: form.value.workflowId, flowType: flow?.flowType }))
}

async function ensurePreviewSession() {
  if (previewSessionId.value) return previewSessionId.value
  previewStatus.value = 'creating'
  const session = await createSession(agentId.value)
  previewSessionId.value = session.id
  return session.id
}

function formatDebugTime(timestamp?: number) {
  if (!timestamp) return '暂无'
  return new Date(timestamp).toLocaleString('zh-CN', { hour12: false })
}

function buildDebugAxisTicks(elapsedMs: number) {
  const max = Math.max(1000, Math.ceil(elapsedMs / 1000) * 1000)
  const step = Math.max(200, Math.ceil(max / 5 / 100) * 100)
  return Array.from({ length: 5 }, (_item, index) => step * (index + 1))
}

function lockDebugDetailColumns() {
  const shell = workbenchShellRef.value
  const grid = workbenchGridRef.value
  const personaWidth = personaColumnRef.value?.getBoundingClientRect().width
  const orchestrationWidth = orchestrationColumnRef.value?.getBoundingClientRect().width
  const previewWidth = previewColumnRef.value?.getBoundingClientRect().width
  if (!grid || !personaWidth || !orchestrationWidth || !previewWidth) return
  for (const element of [shell, grid]) {
    if (!element) continue
    element.style.setProperty('--agent-persona-debug-width', `${Math.ceil(personaWidth)}px`)
    element.style.setProperty('--agent-orchestration-debug-width', `${Math.ceil(orchestrationWidth)}px`)
    element.style.setProperty('--agent-preview-debug-width', `${Math.ceil(previewWidth)}px`)
  }
}

async function toggleDebugDetail() {
  if (debugPanelOpen.value) {
    closeDebugDetail()
    return
  }
  lockDebugDetailColumns()
  debugTab.value = 'tree'
  debugPanelOpen.value = true
  await nextTick()
  debugPanelRef.value?.focus()
  debugPanelRef.value?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}

function closeDebugDetail() {
  debugPanelOpen.value = false
}

async function loadPreviewRunDebug(previewRunId: number) {
  if (!agentId.value || !previewRunId) return
  try {
    const detail = await getAgentPreviewRunDebug(agentId.value, previewRunId)
    previewRunDebugDetail.value = detail
    previewSessionId.value = detail.sessionId
    const now = Date.now()
    previewMessages.value = [
      {
        id: `u-${detail.input?.messageId || detail.sessionId}`,
        role: 'user',
        content: String(detail.input?.content || ''),
        createdAt: now - Math.max(0, detail.elapsedMs || 0),
      },
      {
        id: `a-${detail.output?.messageId || detail.sessionId}`,
        role: 'assistant',
        content: String(detail.output?.content || ''),
        createdAt: now - Math.max(0, detail.elapsedMs || 0),
        firstDeltaAt: now - Math.max(0, (detail.elapsedMs || 0) - (detail.firstResponseMs || 0)),
        completedAt: now,
        finishReason: detail.finishReason,
        latencyMs: detail.latencyMs,
      },
    ]
    previewStatus.value = 'done'
    lockDebugDetailColumns()
    debugTab.value = 'tree'
    debugPanelOpen.value = true
    await nextTick()
    debugPanelRef.value?.focus()
    debugPanelRef.value?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  } catch (error: any) {
    previewError.value = formatWorkbenchBackendError(error)
    message.error(previewError.value)
  }
}

async function applyPreviewRunDebugRoute() {
  if (route.query.debug !== '1') return
  const raw = Array.isArray(route.query.previewRunId) ? route.query.previewRunId[0] : route.query.previewRunId
  const previewRunId = Number(raw || 0)
  if (!previewRunId) return
  await loadPreviewRunDebug(previewRunId)
}

async function sendPreview() {
  const content = previewInput.value.trim()
  if (!content || !previewGate.value.canSend || !agentId.value) return
  previewError.value = ''
  previewRunDebugDetail.value = null
  previewInput.value = ''
  const createdAt = Date.now()
  const userMessage: PreviewMessage = { id: `u-${createdAt}`, role: 'user', content, createdAt }
  const assistantMessage: PreviewMessage = {
    id: `a-${createdAt}`,
    role: 'assistant',
    content: '',
    loading: true,
    createdAt,
  }
  previewMessages.value.push(userMessage, assistantMessage)
  try {
    const sessionId = await ensurePreviewSession()
    previewStatus.value = 'streaming'
    previewAbort = streamMessage(
      sessionId,
      content,
      (delta) => {
        if (!assistantMessage.firstDeltaAt) assistantMessage.firstDeltaAt = Date.now()
        assistantMessage.content += delta
        assistantMessage.loading = false
      },
      (finishReason, latencyMs) => {
        assistantMessage.loading = false
        assistantMessage.completedAt = Date.now()
        assistantMessage.finishReason = finishReason
        assistantMessage.latencyMs = latencyMs
        previewStatus.value = 'done'
        previewAbort = null
      },
      (message) => {
        assistantMessage.loading = false
        assistantMessage.error = true
        assistantMessage.content = message || '预览失败'
        assistantMessage.completedAt = Date.now()
        previewError.value = assistantMessage.content
        previewStatus.value = 'error'
        previewAbort = null
      },
      buildPreviewVariableOverrides(previewVariableValues.value),
    )
  } catch (error: any) {
    assistantMessage.loading = false
    assistantMessage.error = true
    assistantMessage.content = error?.message || '创建预览会话失败'
    assistantMessage.completedAt = Date.now()
    previewError.value = assistantMessage.content
    previewStatus.value = 'error'
  }
}

async function sendSuggestedQuestion(question: string) {
  if (!previewGate.value.canSend) return
  previewInput.value = question
  await sendPreview()
}

async function resetPreview() {
  previewAbort?.abort()
  previewAbort = null
  const sessionId = previewSessionId.value
  previewSessionId.value = null
  previewMessages.value = []
  previewInput.value = ''
  previewError.value = ''
  previewRunDebugDetail.value = null
  previewStatus.value = 'idle'
  if (sessionId) {
    try {
      await deleteSession(sessionId)
    } catch {
      // Best-effort cleanup; the next preview uses a fresh session.
    }
  }
}

watch(() => [route.query.previewRunId, route.query.debug], () => {
  void applyPreviewRunDebugRoute()
})
</script>

<style scoped>
.agent-workbench {
  min-height: calc(100vh - 2rem);
  padding: 1.125rem 1.25rem 1.375rem;
  overflow-x: auto;
  background: #f7f8fb;
  color: #1f2937;
}

.agent-workbench.debug-open {
  --agent-debug-total-width: calc(
    var(--agent-persona-debug-width, 22.5rem)
    + var(--agent-orchestration-debug-width, 26.5rem)
    + var(--agent-preview-debug-width, 21.75rem)
    + 24rem
    + 3rem
  );
}

.workbench-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.25rem;
  padding: 0.75rem 0 1.125rem;
  border-bottom: 1px solid #d9dee8;
}

.agent-workbench.debug-open .workbench-header {
  min-width: var(--agent-debug-total-width);
}

.workbench-title-block {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.header-name-block {
  min-width: 0;
}

.header-name-button {
  border: 0;
  padding: 0;
  margin: 0;
  background: transparent;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: #111827;
  cursor: pointer;
}

.header-name-button span {
  color: #6b7280;
  font-size: 1rem;
}

.header-name-input {
  width: min(18rem, 42vw);
}

.agent-avatar {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.625rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  font-weight: 700;
  background: linear-gradient(135deg, #f59e0b, #f97316);
  box-shadow: 0 0.25rem 0.75rem rgba(249, 115, 22, 0.24);
}

.agent-avatar.large {
  width: 4rem;
  height: 4rem;
  border-radius: 1rem;
  font-size: 1.625rem;
}

.agent-mode-pill {
  display: inline-flex;
  align-items: center;
  min-height: 1.75rem;
  padding: 0 0.625rem;
  border: 1px solid #d9dee8;
  border-radius: 0.5rem;
  background: #f8fafc;
  color: #334155;
  font-size: 0.8125rem;
}

.workbench-title-block h1 {
  margin: 0.125rem 0;
  font-size: 1.375rem;
  line-height: 1.25;
  font-weight: 650;
}

.workbench-title-block p {
  margin: 0;
  font-size: 0.8125rem;
  color: #64748b;
}

.icon-button,
.secondary-action,
.primary-action {
  border: 1px solid #cfd6e4;
  background: #fff;
  color: #1f2937;
  border-radius: 0.5rem;
  height: 2.125rem;
  padding: 0 0.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
}

.icon-button {
  width: 2.125rem;
  padding: 0;
}

.primary-action {
  min-width: 6rem;
  background: #16a34a;
  border-color: #16a34a;
  color: #fff;
}

.publish-action {
  min-width: 4rem;
  border: 1px solid #4f46e5;
  background: #4f46e5;
  color: #fff;
  border-radius: 0.5rem;
  height: 2.125rem;
  padding: 0 0.875rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.primary-action:disabled,
.secondary-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.workbench-actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-shrink: 0;
  white-space: nowrap;
}

.save-state {
  font-size: 0.75rem;
  color: #64748b;
  white-space: nowrap;
}

.save-state-plain {
  font-size: 0.75rem;
  color: #334155;
  white-space: nowrap;
}

.compact-section-nav {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: row;
  gap: 0.375rem;
  overflow-x: auto;
  padding: 0.25rem 0 0.75rem;
}

.compact-section-nav button {
  min-width: 6rem;
  white-space: nowrap;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(20rem, 25rem) minmax(22.5rem, 1fr) minmax(20rem, 24rem);
  gap: 1rem;
  padding-top: 1rem;
  align-items: stretch;
}

.workbench-grid.debug-open {
  min-width: var(--agent-debug-total-width);
  grid-template-columns:
    var(--agent-persona-debug-width, 22.5rem)
    var(--agent-orchestration-debug-width, 26.5rem)
    var(--agent-preview-debug-width, 21.75rem)
    minmax(23rem, 28rem);
}

.section-nav,
.editor-area,
.preview-area,
.persona-column,
.preview-column,
.debug-detail-panel {
  min-width: 0;
}

.section-nav {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.section-nav button {
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  color: #475569;
}

.section-nav button span,
.editor-toolbar strong,
.preview-header strong {
  display: block;
  font-size: 0.875rem;
  font-weight: 650;
}

.section-nav button em {
  display: block;
  margin-top: 0.1875rem;
  font-style: normal;
  font-size: 0.75rem;
  color: #8090a5;
}

.section-nav button.active {
  background: #fff;
  border-color: #d9dee8;
  color: #111827;
}

.section-nav.compact-section-nav {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 0.375rem;
  margin-top: 0.75rem;
  padding: 0.25rem 0 0.75rem;
  overflow-x: auto;
}

.section-nav.compact-section-nav button {
  flex: 0 0 auto;
  width: auto;
  min-width: 6rem;
}

.persona-column,
.editor-area,
.preview-area {
  background: #fff;
  border: 1px solid #d9dee8;
  border-radius: 0.5rem;
}

.persona-column,
.editor-area {
  max-height: calc(100vh - 7.75rem);
  overflow: auto;
}

.persona-column {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: calc(100vh - 7.75rem);
}

.preview-column {
  position: sticky;
  top: 0.75rem;
}

.debug-detail-panel {
  position: sticky;
  top: 0.75rem;
  align-self: start;
  min-width: 23rem;
  min-height: calc(100vh - 7.75rem);
  max-height: calc(100vh - 7.75rem);
  overflow: auto;
  background: #fff;
  border: 1px solid #d9dee8;
  border-radius: 0.5rem;
}

.debug-detail-panel:focus {
  outline: 0.125rem solid #c7d2fe;
  outline-offset: 0.125rem;
}

.preview-area {
  display: grid;
  grid-template-rows: auto minmax(18.75rem, 1fr) auto;
  min-height: calc(100vh - 7.75rem);
}

.column-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid #e6eaf1;
}

.column-header h2 {
  margin: 0;
  font-size: 1rem;
  line-height: 1.35;
  font-weight: 700;
  color: #111827;
}

.column-header p {
  margin: 0.1875rem 0 0;
  color: #64748b;
  font-size: 0.75rem;
}

.helper-toolbar {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.persona-editor {
  min-height: 0;
  padding: 1rem;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
}

.prompt-row,
.prompt-row :deep(.ant-input) {
  min-height: 0;
  height: 100%;
}

.prompt-template-strip {
  padding: 0 1rem 1rem;
}

.template-tabs {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.template-tabs span {
  color: #64748b;
  font-size: 0.8125rem;
}

.template-tabs .active {
  color: #4f46e5;
  font-weight: 650;
}

.template-card-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}

.template-card-row article {
  min-height: 5.25rem;
  padding: 0.75rem;
  border: 1px solid #e6eaf1;
  border-radius: 0.5rem;
  background: #f8fafc;
}

.template-card-row strong,
.template-card-row span {
  display: block;
}

.template-card-row strong {
  color: #111827;
  font-size: 0.8125rem;
}

.template-card-row span {
  margin-top: 0.375rem;
  color: #64748b;
  font-size: 0.75rem;
  line-height: 1.45;
}

.editor-toolbar,
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid #e6eaf1;
}

.runtime-summary {
  margin: 0.75rem 1rem 0;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  border-radius: 0.5rem;
  padding: 0.75rem;
  display: grid;
  gap: 0.375rem;
}

.runtime-summary strong {
  display: block;
  font-size: 0.8125rem;
  color: #1e293b;
}

.runtime-summary ul {
  margin: 0;
  padding-left: 1.125rem;
  color: #92400e;
  font-size: 0.75rem;
  line-height: 1.5;
}

.backend-error {
  margin: 0.75rem 1rem 0;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #991b1b;
  border-radius: 0.5rem;
  padding: 0.625rem 0.75rem;
  font-size: 0.8125rem;
}

.readiness-list {
  margin: 0.75rem 1rem 0;
  padding: 0.625rem 0.75rem 0.625rem 1.75rem;
  border: 1px solid #fed7aa;
  background: #fff7ed;
  color: #9a3412;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  line-height: 1.5;
}

.editor-toolbar p,
.preview-header span {
  margin: 0.1875rem 0 0;
  font-size: 0.75rem;
  color: #64748b;
}

.status-pill,
.mode-badge {
  font-size: 0.75rem;
  color: #166534;
  background: #dcfce7;
  border: 1px solid #bbf7d0;
  border-radius: 62.4375rem;
  padding: 0.25rem 0.5625rem;
}

.editor-panel {
  padding: 1rem;
  display: grid;
  gap: 0.875rem;
}

.orchestration-card {
  margin: 1rem;
  border: 1px solid #e6eaf1;
  border-radius: 0.5rem;
  padding: 0.875rem;
  display: grid;
  gap: 0.75rem;
  background: #fff;
}

.module-card {
  padding: 0;
  overflow: hidden;
}

.module-summary {
  cursor: pointer;
  list-style: none;
  padding: 0.875rem;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.module-summary > div {
  display: grid;
  gap: 0.1875rem;
  min-width: 0;
}

.module-summary strong,
.module-summary span {
  display: block;
}

.module-summary::-webkit-details-marker {
  display: none;
}

.module-summary::after {
  content: "⌄";
  flex-shrink: 0;
  color: #64748b;
  font-size: 1rem;
  transform: rotate(0deg);
  transition: transform 0.16s ease;
}

.module-card:not([open]) .module-summary::after {
  transform: rotate(-90deg);
}

.module-card > .field-row,
.module-card > .context-card,
.module-card > .capability-card,
.module-card > .capability-card-header:not(.sub-section-heading),
.module-card > .sub-section-heading,
.module-card > .retrieval-settings {
  margin-left: 0.875rem;
  margin-right: 0.875rem;
}

.module-card > :last-child {
  margin-bottom: 0.875rem;
}

.field-row {
  display: grid;
  grid-template-columns: 6.875rem 1fr;
  align-items: start;
  gap: 0.75rem;
}

.field-row label {
  color: #64748b;
  font-size: 0.8125rem;
  padding-top: 0.5625rem;
}

.field-error {
  margin: 0.3125rem 0 0;
  color: #dc2626;
  font-size: 0.75rem;
}

.prompt-editor :deep(textarea.ant-input) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8125rem;
}

.persona-editor .prompt-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  width: 100%;
  min-width: 0;
}

.persona-editor .prompt-editor,
.persona-editor .prompt-row :deep(.ant-input) {
  width: 100%;
  min-width: 0;
}

.persona-editor .prompt-row :deep(textarea.ant-input) {
  width: 100%;
  box-sizing: border-box;
}

.suggested-editor {
  display: grid;
  gap: 0.5rem;
}

.suggested-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2.125rem;
  gap: 0.5rem;
  align-items: center;
}

.inline-control {
  display: grid;
  grid-template-columns: minmax(10rem, 1fr) 2.625rem;
  align-items: center;
  gap: 0.75rem;
}

.inline-control span {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8125rem;
  color: #475569;
  text-align: right;
}

.capability-grid {
  padding: 0.875rem;
  display: grid;
  gap: 0.875rem;
}

.context-panel {
  padding: 0.875rem;
  display: grid;
  gap: 0.875rem;
}

.optimizer-panel {
  display: grid;
  gap: 0.875rem;
}

.access-panel {
  padding: 0.875rem;
  display: grid;
  gap: 0.875rem;
}

.version-panel {
  padding: 0.875rem;
}

.release-dialog-body {
  display: grid;
  gap: 0.875rem;
}

.capability-card,
.context-card,
.release-card {
  border: 1px solid #d9dee8;
  border-radius: 0.5rem;
  padding: 0.875rem;
  display: grid;
  gap: 0.75rem;
}

.capability-card-header,
.release-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.variable-list,
.memory-list {
  display: grid;
  gap: 0.625rem;
}

.variable-row {
  display: grid;
  grid-template-columns: minmax(8rem, 1fr) 7.5rem minmax(8rem, 1fr) 4.5rem 2.125rem;
  gap: 0.5rem;
  align-items: center;
}

.variable-description {
  grid-column: 1 / -1;
}

.memory-row {
  display: grid;
  grid-template-columns: minmax(7.5rem, 12rem) minmax(10rem, 1fr) 2.125rem;
  gap: 0.5rem;
  align-items: center;
}

.tool-policy-list {
  display: grid;
  gap: 0.75rem;
}

.tool-policy-row {
  min-width: 0;
  border: 1px solid #e6eaf1;
  border-radius: 0.5rem;
  background: #f8fafc;
  padding: 0.75rem;
  display: grid;
  gap: 0.75rem;
}

.tool-policy-row-header {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.tool-policy-title {
  min-width: 0;
}

.tool-policy-title strong {
  display: block;
  color: #111827;
  font-size: 0.8125rem;
}

.tool-policy-title span,
.tool-policy-field > span {
  display: block;
  color: #64748b;
  font-size: 0.75rem;
}

.tool-policy-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.625rem;
}

.tool-policy-field {
  min-width: 0;
  display: grid;
  gap: 0.375rem;
}

.tool-policy-field :deep(.ant-select),
.tool-policy-field :deep(.ant-input-number),
.tool-policy-field :deep(.ant-input) {
  width: 100%;
}

.tool-policy-presets {
  grid-column: 1 / -1;
}

.sub-section-heading {
  margin-top: 0.25rem;
  padding-top: 0.75rem;
  border-top: 1px solid #eef2f7;
}

.retrieval-settings {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.625rem;
}

.retrieval-settings label {
  display: grid;
  gap: 0.375rem;
}

.retrieval-settings span {
  color: #64748b;
  font-size: 0.75rem;
}

.optimizer-result {
  align-items: start;
}

.optimizer-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.optimizer-columns strong {
  display: block;
  margin-bottom: 0.375rem;
  color: #111827;
  font-size: 0.8125rem;
}

.optimizer-columns pre {
  min-height: 8rem;
  margin: 0;
  padding: 0.75rem;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid #e6eaf1;
  border-radius: 0.5rem;
  background: #f8fafc;
  color: #334155;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.optimizer-audit {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.optimizer-audit span {
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-full);
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.75rem;
}

.evaluation-gate-grid {
  display: grid;
  grid-template-columns: minmax(10rem, 14rem) minmax(12rem, 1fr);
  gap: 0.75rem;
}

.evaluation-gate-grid label {
  display: grid;
  gap: 0.375rem;
}

.evaluation-gate-grid span {
  color: #64748b;
  font-size: 0.75rem;
}

.access-grid,
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.access-grid label {
  display: grid;
  gap: 0.375rem;
}

.access-grid span,
.analytics-grid span {
  color: #475569;
  font-size: 0.8125rem;
}

.capability-card-header strong,
.release-card-header strong {
  display: block;
  font-size: 0.875rem;
  color: #111827;
}

.capability-card-header span,
.release-card-header span {
  display: block;
  margin-top: 0.1875rem;
  font-size: 0.75rem;
  color: #64748b;
}

.text-action {
  border: 0;
  background: transparent;
  color: #2563eb;
  font-size: 0.8125rem;
  padding: 0;
}

.text-action:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}

.capability-name {
  display: block;
  color: #1f2937;
  font-size: 0.8125rem;
}

.capability-select {
  min-width: 0;
}

.capability-option {
  display: grid;
  gap: 0.125rem;
  line-height: 1.25;
}

.capability-option strong {
  color: #111827;
  font-size: 0.8125rem;
}

.capability-option span {
  color: #64748b;
  font-size: 0.75rem;
}

.advanced-tool-policy,
.advanced-release-card {
  padding: 0;
}

.advanced-tool-policy > summary,
.advanced-release-card > summary {
  cursor: pointer;
  list-style: none;
}

.advanced-tool-policy > summary::-webkit-details-marker,
.advanced-release-card > summary::-webkit-details-marker {
  display: none;
}

.advanced-tool-policy > summary::after,
.advanced-release-card > summary::after {
  content: "⌄";
  color: #64748b;
  font-size: 1rem;
  transform: rotate(-90deg);
  transition: transform 0.16s ease;
}

.advanced-tool-policy[open] > summary::after,
.advanced-release-card[open] > summary::after {
  transform: rotate(0deg);
}

.advanced-tool-policy > .empty-hint,
.advanced-tool-policy > .tool-policy-list,
.advanced-release-card > .release-card-header,
.advanced-release-card > .evaluation-gate-grid,
.advanced-release-card > .empty-hint,
.advanced-release-card > .access-grid,
.advanced-release-card > .access-analytics-heading,
.advanced-release-card > .analytics-grid {
  margin-left: 0.75rem;
  margin-right: 0.75rem;
}

.empty-hint {
  color: #64748b;
  font-size: 0.8125rem;
  border: 1px dashed #cfd6e4;
  border-radius: 0.5rem;
  padding: 0.75rem;
  background: #f8fafc;
}

.version-list {
  display: grid;
  gap: 0.625rem;
}

.version-row {
  border: 1px solid #e6eaf1;
  border-radius: 0.5rem;
  padding: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.version-row strong,
.version-row span,
.version-row em {
  display: block;
}

.version-row strong {
  font-size: 0.875rem;
  color: #111827;
}

.version-row span {
  margin-top: 0.1875rem;
  font-size: 0.8125rem;
  color: #334155;
}

.version-row em {
  margin-top: 0.1875rem;
  font-style: normal;
  font-size: 0.75rem;
  color: #64748b;
}

.version-row-actions,
.preview-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.preview-title-row {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.toolbar-icon-button {
  width: 1.75rem;
  height: 1.75rem;
  border: 0;
  border-radius: 0.375rem;
  background: transparent;
  color: #445067;
  font-size: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.toolbar-icon-button:disabled {
  cursor: not-allowed;
  color: #a5b0c2;
  background: transparent;
}

.toolbar-icon-button:hover,
.preview-debug-toggle.active {
  background: #eef2ff;
  color: #4f46e5;
}

.preview-debug-toggle.active {
  box-shadow: inset 0 0 0 1px #c7d2fe;
}

.preview-target-option strong,
.preview-target-option span {
  display: block;
}

.preview-target-option span {
  color: #64748b;
  font-size: 0.75rem;
}

.preview-body {
  padding: 1rem 1rem 1rem 0.5rem;
  min-height: 26.25rem;
  display: flex;
  align-items: stretch;
}

.preview-message {
  width: fit-content;
  max-width: 100%;
  box-sizing: border-box;
  border: 1px solid #d9dee8;
  background: #f8fafc;
  color: #334155;
  border-radius: 0.5rem;
  padding: 0.75rem;
  font-size: 0.8125rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.preview-empty {
  align-self: stretch;
  width: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  align-content: stretch;
  gap: 0.625rem;
  max-width: 100%;
  color: #334155;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.preview-opening-message {
  max-width: min(100%, 20rem);
  white-space: pre-wrap;
}

.preview-gate-message {
  color: #64748b;
}

.preview-suggestions {
  align-self: end;
  justify-self: end;
  width: 100%;
  display: grid;
  gap: 0.5rem;
  justify-items: end;
  margin-top: auto;
}

.suggestion-pill {
  width: fit-content;
  border: 1px solid #cfd6e4;
  background: #fff;
  color: #1f2937;
  border-radius: 62.4375rem;
  min-height: 1.875rem;
  max-width: min(100%, 18rem);
  padding: 0.3125rem 0.625rem;
  font-size: 0.8125rem;
  text-align: left;
  overflow-wrap: anywhere;
}

.suggestion-pill:hover {
  border-color: #93c5fd;
  color: #1d4ed8;
}

.preview-messages {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.preview-message.user {
  align-self: flex-end;
  max-width: 85%;
  background: #eaf4ff;
  border-color: #bfdbfe;
  color: #1e3a8a;
}

.preview-message.assistant {
  align-self: flex-start;
  max-width: 88%;
}

.preview-message.error {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}

.preview-footer {
  border-top: 1px solid #e6eaf1;
  padding: 0.75rem;
  display: grid;
  gap: 0.625rem;
}

.preview-variable-overrides {
  display: grid;
  gap: 0.5rem;
  padding: 0.625rem;
  border: 1px solid #e6eaf1;
  border-radius: 0.5rem;
  background: #f8fafc;
}

.preview-variable-overrides label {
  display: grid;
  grid-template-columns: minmax(5rem, 7.5rem) minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
}

.preview-variable-overrides span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
  color: #475569;
}

.preview-composer {
  overflow: hidden;
  border: 1px solid #cfd6e4;
  border-radius: 0.625rem;
  background: #fff;
}

.preview-composer :deep(textarea.ant-input) {
  min-height: 4rem !important;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  resize: none;
}

.preview-composer-toolbar {
  min-height: 2.25rem;
  border-top: 0;
  padding: 0.25rem 0.375rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.preview-send-button {
  background: #dcfce7;
  color: #16a34a;
}

.preview-send-button:hover {
  background: #bbf7d0;
  color: #15803d;
}

.preview-send-button:disabled {
  background: #f1f5f9;
  color: #a5b0c2;
}

.preview-disclaimer {
  margin: 0.25rem 0 0;
  color: #94a3b8;
  font-size: 0.75rem;
  text-align: center;
}

.debug-detail-header {
  min-height: 4.5rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e6eaf1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.debug-detail-header h2 {
  margin: 0;
  color: #111827;
  font-size: 1.25rem;
  line-height: 1.25;
}

.debug-close {
  border: 0;
  background: transparent;
  color: #6b7280;
  font-size: 1.75rem;
  line-height: 1;
}

.debug-filter-bar {
  margin: 1rem 1.25rem;
  min-height: 2.75rem;
  border: 1px solid #d9dee8;
  border-radius: 0.625rem;
  display: grid;
  grid-template-columns: 2.5rem minmax(0, 1fr);
  align-items: center;
  overflow: hidden;
}

.debug-search {
  height: 100%;
  border: 0;
  border-right: 1px solid #e6eaf1;
  background: #fff;
  color: #111827;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.debug-keyword {
  justify-self: start;
  margin-left: 0.625rem;
  max-width: calc(100% - 0.75rem);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-radius: 0.5rem;
  background: #eef0f4;
  color: #334155;
  padding: 0.25rem 0.5rem;
  font-size: 0.8125rem;
}

.debug-summary {
  padding: 0 1.25rem 1rem;
  border-bottom: 1px solid #e6eaf1;
  color: #64748b;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 0.625rem;
  align-items: center;
}

.debug-summary strong {
  color: #111827;
  font-size: 1rem;
}

.debug-summary p {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 0.8125rem;
}

.debug-summary p span {
  margin-left: 1rem;
}

.debug-success {
  border-radius: 0.5rem;
  background: #dcfce7;
  color: #16a34a;
  padding: 0.25rem 0.5rem;
  font-size: 0.8125rem;
}

.debug-finish {
  border-radius: 0.5rem;
  background: #f1f5f9;
  color: #475569;
  padding: 0.25rem 0.5rem;
  font-size: 0.8125rem;
}

.debug-tabs {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1rem 1.25rem 0.625rem;
}

.debug-tabs button {
  border: 0;
  background: transparent;
  color: #374151;
  padding: 0;
  font-size: 1rem;
  font-weight: 700;
}

.debug-tabs button.active {
  color: #4f46e5;
}

.debug-call-tree,
.debug-flame-graph {
  min-height: 13rem;
  padding: 0.5rem 1.25rem 1.25rem;
  border-bottom: 1px solid #e6eaf1;
}

.debug-call-tree {
  display: grid;
  gap: 0.375rem;
  align-content: start;
}

.debug-tree-node {
  display: grid;
  grid-template-columns: 1.375rem auto minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
  color: #334155;
  font-size: 0.875rem;
}

.debug-tree-node.child {
  margin-left: 1.625rem;
}

.debug-tree-node span {
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 0.375rem;
  background: #4f46e5;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
}

.debug-tree-node.child span {
  background: #111827;
}

.debug-tree-node em {
  font-style: normal;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flame-axis {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  color: #94a3b8;
  font-size: 0.75rem;
  margin-bottom: 0.5rem;
}

.flame-lane {
  min-height: 2.25rem;
  border: 1px solid #c7d2fe;
  background: #c7d2fe;
  color: #334155;
  padding: 0.5rem;
  font-size: 0.8125rem;
  margin-top: 0.25rem;
}

.debug-node-detail {
  padding: 1rem 1.25rem 1.5rem;
}

.debug-node-detail h3 {
  margin: 0 0 0.875rem;
  font-size: 1rem;
  color: #111827;
}

.debug-node-detail dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.625rem 1rem;
}

.debug-node-detail div {
  min-width: 0;
}

.debug-node-detail dt {
  color: #94a3b8;
  font-size: 0.8125rem;
}

.debug-node-detail dd {
  margin: 0.1875rem 0 0;
  color: #334155;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.debug-empty-state {
  margin: 1rem 1.25rem;
  border: 1px dashed #cfd6e4;
  border-radius: 0.625rem;
  background: #f8fafc;
  padding: 1rem;
  display: grid;
  gap: 0.375rem;
}

.debug-empty-state strong {
  color: #111827;
  font-size: 0.9375rem;
}

.debug-empty-state span {
  color: #64748b;
  font-size: 0.8125rem;
  line-height: 1.5;
}

@media (max-width: 1180px) {
  .workbench-grid {
    grid-template-columns: 11.25rem minmax(22.5rem, 1fr);
  }

  .preview-area {
    grid-column: 2;
  }
}

@media (max-width: 760px) {
  .workbench-header,
  .workbench-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .preview-area {
    grid-column: auto;
  }

  .field-row {
    grid-template-columns: 1fr;
    gap: 0.375rem;
  }

  .variable-row,
  .memory-row,
  .tool-policy-row,
  .optimizer-columns,
  .retrieval-settings,
  .evaluation-gate-grid,
  .access-grid,
  .analytics-grid,
  .preview-variable-overrides label {
    grid-template-columns: 1fr;
  }
}
</style>
