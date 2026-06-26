<template>
  <div
    class="workflow-canvas-page"
    :class="[
      responsiveCanvasLayout.className,
      {
        'chatflow-mode': isChatflowMode,
        'debug-dock-open': debugDockOpen,
        'has-right-panel': rightSidePanelOpen,
        'has-node-test-drawer': nodeTestDrawerOpen,
      },
    ]"
    :data-layout-phase="responsiveCanvasLayout.phase"
  >
    <div class="canvas-topbar">
      <div class="canvas-title-wrap">
        <a-button type="text" class="back-button" @click="router.push(listRoute)">
          <ArrowLeft aria-hidden="true" />
        </a-button>
        <div class="flow-icon"><Share /></div>
        <div>
          <div class="title-row">
            <a-input
              v-if="flowTitleEditing"
              v-model:value="flowTitleDraft"
              class="title-input"
              maxlength="100"
              :placeholder="isChatflowMode ? 'Chatflow 名称' : '工作流名称'"
              @blur="commitFlowTitleEdit"
              @keydown.enter.prevent="commitFlowTitleEdit"
              @keydown.esc.prevent="cancelFlowTitleEdit"
            />
            <button
              v-else
              type="button"
              class="title-display-button"
              :class="{ placeholder: !form.name.trim() }"
              aria-label="编辑画布名称"
              @click="startFlowTitleEdit"
            >
              {{ flowTitleDisplay }}
            </button>
            <span class="flow-info">i</span>
          </div>
          <div class="save-state">{{ saveState }}</div>
        </div>
      </div>
      <div class="canvas-mode-tabs" role="tablist" aria-label="canvas lifecycle">
        <button
          v-for="tab in composerLifecycleTabs"
          :key="tab.key"
          :class="{ active: canvasTab === tab.key }"
          type="button"
          @click="selectCanvasTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="canvas-actions">
        <a-button @click="openTestPanel">{{ isChatflowMode ? '对话试运行' : '试运行' }}</a-button>
        <a-button @click="openDebugDetails">调试详情</a-button>
        <a-button type="primary" ghost @click="openPublishDialog">发布</a-button>
        <a-button :loading="saving" type="primary" @click="saveCanvas">保存</a-button>
      </div>
    </div>

    <section
      class="canvas-workbench"
      :class="{ 'resource-collapsed': resourcePanelCollapsed || canvasTab !== 'compose' }"
      data-testid="workflow-canvas"
    >
      <button
        v-if="canvasTab === 'compose' && resourcePanelCollapsed"
        class="resource-panel-toggle"
        type="button"
        aria-label="展开侧栏"
        @click="resourcePanelCollapsed = !resourcePanelCollapsed"
      >
        <ArrowRight aria-hidden="true" />
      </button>

      <aside v-if="!resourcePanelCollapsed && canvasTab === 'compose'" class="canvas-resource-panel" data-testid="canvas-resource-panel">
        <div class="resource-header">
          <div class="resource-header-main">
            <strong>{{ isChatflowMode ? '对话设置' : '画布概览' }}</strong>
            <div class="resource-header-actions">
              <button
                v-if="isChatflowMode"
                type="button"
                class="resource-header-icon-button"
                aria-label="对话历史策略"
                @click="chatflowHistorySettingsOpen = !chatflowHistorySettingsOpen"
              >
                <SettingsIcon aria-hidden="true" />
              </button>
              <button
                type="button"
                class="resource-header-icon-button"
                aria-label="折叠侧栏"
                @click="resourcePanelCollapsed = true"
              >
                <ArrowLeft aria-hidden="true" />
              </button>
            </div>
          </div>
          <div
            v-if="isChatflowMode && chatflowHistorySettingsOpen"
            class="chatflow-history-settings-popover"
            data-testid="chatflow-history-settings-popover"
          >
            <div class="chatflow-history-settings-header">
              <strong>对话历史策略</strong>
              <button type="button" aria-label="关闭对话历史策略" @click="chatflowHistorySettingsOpen = false">
                <XIcon aria-hidden="true" />
              </button>
            </div>
            <label class="chatflow-history-setting-field">
              <span>对话轮数保留</span>
              <div class="chatflow-history-slider-control">
                <input
                  v-model.number="chatflowHistoryRetentionRounds"
                  aria-label="对话轮数保留滑块"
                  class="model-parameter-slider chatflow-history-slider"
                  type="range"
                  min="0"
                  max="20"
                  step="1"
                  :style="chatflowHistorySliderStyle"
                  @input="setChatflowHistoryRetentionRounds(($event.target as HTMLInputElement).value)"
                />
                <input
                  :value="chatflowHistoryRetentionRounds"
                  aria-label="对话轮数保留数值"
                  class="chatflow-history-number-input"
                  type="number"
                  min="0"
                  max="20"
                  step="1"
                  @input="setChatflowHistoryRetentionRounds(($event.target as HTMLInputElement).value)"
                />
              </div>
            </label>
            <p>0 表示不注入历史；节点会话历史开启后默认跟随该全局策略。</p>
          </div>
        </div>

        <template v-if="isChatflowMode">
          <section class="resource-section">
            <h4>开场白</h4>
            <a-textarea v-model:value="openingText" :rows="3" placeholder="欢迎语" @input="markGraphDirty" />
          </section>
          <section class="resource-section" data-testid="chatflow-guide-question-settings">
            <h4>引导问题</h4>
            <div v-for="(_question, index) in guideQuestions" :key="index" class="question-row">
              <input
                v-model="guideQuestions[index]"
                :aria-label="`引导问题 ${index + 1}`"
                placeholder="输入猜你想问"
                @input="markGraphDirty"
              />
              <button type="button" :aria-label="`删除引导问题 ${index + 1}`" @click="removeGuideQuestion(index)">
                <XIcon aria-hidden="true" />
              </button>
            </div>
            <button type="button" class="resource-action" aria-label="新增引导问题" @click="addGuideQuestion">
              <LucidePlus aria-hidden="true" />
              <span>新增引导问题</span>
            </button>
          </section>
          <section class="resource-section chatflow-memory-panel" data-testid="chatflow-variable-panel">
            <div class="resource-section-heading">
              <h4>记忆</h4>
              <small>
                会话变量 {{ chatflowConversationVariableCount }} · 用户变量 {{ chatflowUserVariableCount }}
              </small>
            </div>
            <div
              v-for="scope in chatflowVariableScopes"
              :key="scope.title"
              class="chatflow-variable-scope"
              :data-testid="`chatflow-variable-scope-${scope.scope}`"
            >
              <div class="chatflow-variable-scope-header">
                <button
                  type="button"
                  class="section-title chatflow-variable-scope-toggle"
                  :aria-expanded="scope.open"
                  @click="toggleChatflowVariableScope(scope.scope)"
                >
                  <ChevronDownIcon v-if="scope.open" aria-hidden="true" />
                  <ChevronRightIcon v-else aria-hidden="true" />
                  <strong>{{ scope.title }}</strong>
                  <em>{{ scope.items.length }}</em>
                </button>
                <button
                  v-if="scope.open"
                  type="button"
                  class="section-icon-button chatflow-variable-add-button"
                  :aria-label="`新增${scope.title}`"
                  @click="addChatflowScopedVariable(scope.scope)"
                >
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <p v-if="scope.open" class="chatflow-variable-scope-description">{{ scope.description }}</p>
              <div v-if="scope.open" class="resource-items chatflow-variable-table">
                <div class="chatflow-variable-table-head" aria-hidden="true">
                  <span>变量 key</span>
                  <span>变量显示名</span>
                  <span>操作</span>
                </div>
                <div
                  v-for="(item, itemIndex) in scope.items"
                  :key="item.reference"
                  class="resource-variable-row"
                  data-testid="chatflow-resource-variable"
                >
                  <span v-if="item.readonly" class="chatflow-variable-key">{{ item.key }}</span>
                  <input
                    v-else
                    class="chatflow-variable-key"
                    :aria-label="`${scope.title} key`"
                    :value="item.key"
                    @input="updateChatflowScopedVariable(scope.scope, itemIndex, 'name', ($event.target as HTMLInputElement).value)"
                  />
                  <span v-if="item.readonly" class="chatflow-variable-name">
                    <strong>{{ item.label }}</strong>
                    <code>{{ item.reference }}</code>
                  </span>
                  <input
                    v-else
                    class="chatflow-variable-name chatflow-variable-label-input"
                    :aria-label="`${scope.title}显示名`"
                    :value="item.label"
                    @input="updateChatflowScopedVariable(scope.scope, itemIndex, 'label', ($event.target as HTMLInputElement).value)"
                  />
                  <span class="chatflow-variable-actions" :aria-label="item.readonly ? '只读系统变量' : '自定义变量操作'">
                    <i class="chatflow-variable-switch" aria-hidden="true"></i>
                    <button type="button" :aria-label="`配置 ${item.key}`" :disabled="item.readonly">
                      <SettingsIcon aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      :aria-label="`删除 ${item.key}`"
                      :disabled="item.readonly"
                      @click="removeChatflowScopedVariable(scope.scope, itemIndex)"
                    >
                      <XIcon aria-hidden="true" />
                    </button>
                  </span>
                </div>
              </div>
            </div>
          </section>
        </template>

        <template v-else>
          <section class="resource-section" data-testid="workflow-overview-panel">
            <h4>画布</h4>
            <dl class="resource-stats">
              <div>
                <dt>节点</dt>
                <dd>{{ graph.nodes.length }}</dd>
              </div>
              <div>
                <dt>连线</dt>
                <dd>{{ graph.edges.length }}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>{{ workflowStatus }}</dd>
              </div>
            </dl>
          </section>
          <section class="resource-section">
            <h4>选中节点</h4>
            <div class="selected-node-summary">
              <strong>{{ selectedNode?.name || '未选择' }}</strong>
              <span>{{ selectedNode?.nodeKey || '-' }}</span>
            </div>
          </section>
        </template>
      </aside>

      <section v-if="canvasTab === 'open'" class="canvas-open-surface" data-testid="workflow-open-surface">
        <div class="open-surface-header">
          <div>
            <strong>开放</strong>
            <span>{{ isChatflowMode ? 'Chatflow 渠道与 Open API' : 'Workflow Open API' }}</span>
          </div>
          <code>{{ openApiEndpoint }}</code>
        </div>

        <div class="open-surface-grid">
          <section class="open-surface-section">
            <div class="section-title"><span>⌄</span> Open API</div>
            <dl class="ops-field-list">
              <div>
                <dt>Method</dt>
                <dd>POST</dd>
              </div>
              <div>
                <dt>Endpoint</dt>
                <dd><code>{{ openApiEndpoint }}</code></dd>
              </div>
            </dl>
            <pre class="ops-code">{{ openApiSample }}</pre>
          </section>

          <section v-if="isChatflowMode" class="open-surface-section channel-shell-section" data-testid="chatflow-channel-shells">
            <div class="section-title"><span>⌄</span> 渠道</div>
            <p v-if="chatflowChannelsLoading" class="resource-empty-state">正在加载渠道...</p>
            <div v-else class="channel-shell-grid">
              <article
                v-for="channel in chatflowChannelRows"
                :key="channel.id"
                class="channel-shell-card"
                :class="{ disabled: channel.disabled }"
              >
                <div>
                  <strong>{{ channel.name }}</strong>
                  <span>{{ channel.id }}</span>
                </div>
                <em>{{ channel.status }}</em>
                <p class="channel-capabilities">{{ channel.capabilities }}</p>
                <p v-if="channel.normalizedInputFields.length" class="channel-fields">
                  {{ channel.normalizedInputFields.join(' · ') }}
                </p>
                <p v-if="channel.hasConfigSchema" class="channel-schema">Schema ready</p>
                <p v-if="channel.reason">{{ channel.reason }}</p>
              </article>
            </div>
          </section>
        </div>
      </section>

      <div
        v-else
        ref="canvasStageRef"
        class="canvas-stage-shell"
        tabindex="0"
        @keydown="handleCanvasKeydown"
      >
      <VueFlow
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        class="coze-flow"
        :default-viewport="{ x: 0, y: 0, zoom: 1 }"
        :min-zoom="CANVAS_ZOOM_MIN"
        :max-zoom="CANVAS_ZOOM_MAX"
        :nodes-draggable="true"
        :pan-on-drag="operationMode === 'mouse'"
        :pan-on-scroll="operationMode === 'trackpad'"
        :pan-on-scroll-speed="CANVAS_TRACKPAD_PAN_SPEED"
        :pan-on-scroll-mode="PanOnScrollMode.Free"
        :zoom-on-scroll="operationMode === 'mouse'"
        :zoom-on-pinch="operationMode === 'trackpad'"
        :pane-click-distance="CANVAS_PANE_CLICK_DISTANCE"
        :connection-radius="CANVAS_CONNECTION_RADIUS"
        :delete-key-code="null"
        fit-view-on-init
        @viewport-change="handleViewportChange"
        @connect="handleConnect"
        @connect-start="handleConnectStart"
        @connect-end="handleConnectEnd"
        @edge-click="handleEdgeClick"
        @edge-mouse-enter="handleEdgeMouseEnter"
        @edge-mouse-leave="handleEdgeMouseLeave"
        @node-drag-stop="handleNodeDragStop"
        @node-click="handleNodeClick"
        @pane-click="handlePaneClick"
      >
        <template #edge-coze="edgeProps">
          <BaseEdge
            :id="edgeProps.id"
            :path="cozeEdgePath(edgeProps)[0]"
            :marker-end="edgeProps.markerEnd"
            :interaction-width="24"
            :class="[
              'coze-edge-path',
              runPathEdgeClasses(edgeProps.id),
              {
                'edge-hovered': isEdgeHovered(edgeProps),
                'edge-selected': isEdgeSelected(edgeProps),
              },
            ]"
          />
          <EdgeLabelRenderer>
            <button
              v-show="hoveredEdgeId === edgeProps.id || selectedEdgeId === edgeProps.id || edgeInsertPaletteId === edgeProps.id"
              type="button"
              class="edge-insert-button"
              data-testid="edge-insert-button"
              aria-label="在线上插入节点"
              :style="edgeInsertButtonStyle(cozeEdgePath(edgeProps))"
              @click.stop="openEdgeInsertPalette(edgeProps.id)"
              @mouseenter="hoveredEdgeId = edgeProps.id"
              @mouseleave="clearEdgeHover(edgeProps.id)"
            >
              <LucidePlus aria-hidden="true" />
            </button>
            <div
              v-if="edgeInsertPaletteId === edgeProps.id"
              class="edge-insert-palette"
              data-testid="edge-insert-palette"
              :style="edgeInsertPaletteStyle(cozeEdgePath(edgeProps))"
              @click.stop
              @mouseenter="hoveredEdgeId = edgeProps.id"
              @mouseleave="clearEdgeHover(edgeProps.id)"
            >
              <a-input v-model:value="nodePaletteSearch" size="large" placeholder="搜索节点、插件、工作流" />
              <div v-for="group in filteredNodePaletteGroups" :key="`edge-${group.title}`" class="edge-insert-palette-group">
                <strong>{{ group.title }}</strong>
                <div class="edge-node-palette-grid">
                  <button
                    v-for="entry in group.items"
                    :key="entry.type"
                    type="button"
                    :aria-label="entry.label"
                    :disabled="entry.disabled"
                    @click="insertNodeOnEdge(entry.type, edgeProps.id, edgeInsertPosition(cozeEdgePath(edgeProps)))"
                  >
                    <span class="palette-icon" :class="`icon-${entry.type.toLowerCase()}`">
                      <component :is="nodeIcon(entry.type)" />
                    </span>
                    <span>{{ entry.label }}</span>
                  </button>
                </div>
              </div>
            </div>
          </EdgeLabelRenderer>
        </template>
        <template #node-coze="nodeProps">
          <div
            class="coze-node"
            :class="[
              `node-${nodeProps.data.type.toLowerCase()}`,
              nodeProps.data.runStatus ? `run-${String(nodeProps.data.runStatus).toLowerCase()}` : '',
              { selected: selectedNodeKey === nodeProps.data.nodeKey },
            ]"
            @mouseenter="handleNodeMouseEnter(nodeProps.data.nodeKey)"
            @mouseleave="handleNodeMouseLeave(nodeProps.data.nodeKey)"
          >
            <Handle
              v-if="nodeProps.data.type !== 'START'"
              type="target"
              :position="Position.Left"
              :class="[
                'node-port target-port',
                { 'connection-preview': isConnectionPreviewPort(nodeProps.data.nodeKey, 'target') },
              ]"
              :data-node-key="nodeProps.data.nodeKey"
              data-port-type="target"
              data-handle-id=""
            />
            <div class="node-header">
              <div class="node-type-icon" :class="`icon-${nodeProps.data.type.toLowerCase()}`">
                <component :is="nodeIcon(nodeProps.data.type)" />
              </div>
              <div class="node-title-run">
                <div class="node-title">{{ nodeProps.data.name }}</div>
                <span
                  v-if="nodeProps.data.runStatus"
                  class="node-run-status"
                  :class="`status-${String(nodeProps.data.runStatus).toLowerCase()}`"
                  data-testid="node-run-status"
                  role="status"
                  :aria-label="`节点运行状态：${nodeProps.data.runStatusLabel}`"
                >
                  <span class="node-run-status-icon" aria-hidden="true"></span>
                  {{ nodeProps.data.runStatusLabel }}
                  <small v-if="nodeProps.data.runElapsedLabel">{{ nodeProps.data.runElapsedLabel }}</small>
                </span>
              </div>
              <div
                v-if="!isFixedNode(nodeProps.data)"
                class="node-card-actions"
                :class="{ 'menu-open': nodeCardMenuKey === nodeProps.data.nodeKey }"
                @click.stop
                @pointerdown.stop
              >
                <button
                  v-if="canRunSingleNodeTest(nodeProps.data)"
                  type="button"
                  aria-label="试运行当前节点"
                  title="试运行当前节点"
                  @click="openNodeCardTest(nodeProps.data.nodeKey)"
                >
                  <PlayIcon aria-hidden="true" />
                </button>
                <div
                  class="node-card-menu-wrap"
                  @mouseenter="openNodeCardMenu(nodeProps.data.nodeKey)"
                  @mouseleave="scheduleCloseNodeCardMenu(nodeProps.data.nodeKey)"
                >
                  <button
                    type="button"
                    aria-label="更多操作"
                    title="更多操作"
                    :aria-expanded="nodeCardMenuKey === nodeProps.data.nodeKey"
                    @click.prevent.stop
                  >
                    <MoreHorizontalIcon aria-hidden="true" />
                  </button>
                  <div
                    v-if="nodeCardMenuKey === nodeProps.data.nodeKey"
                    class="node-card-menu"
                    data-testid="node-card-menu"
                    role="menu"
                  >
                    <button type="button" role="menuitem" :disabled="!canRenameNode(nodeProps.data)" @click="startNodeRename(nodeProps.data.nodeKey)">重命名</button>
                    <button type="button" role="menuitem" :disabled="isFixedNode(nodeProps.data)" @click="duplicateNode(nodeProps.data.nodeKey)">
                      <CopyIcon aria-hidden="true" />
                      创建副本
                    </button>
                    <button type="button" role="menuitem" :disabled="isFixedNode(nodeProps.data)" @click="removeNodeFromMenu(nodeProps.data.nodeKey)">
                      <Trash2 aria-hidden="true" />
                      删除
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div
              v-if="isBranchNodeType(nodeProps.data.type)"
              class="condition-node-branches"
              data-testid="condition-node-branches"
            >
              <div
                v-for="branch in nodeProps.data.conditionBranches"
                :key="`branch-block-${branch.handleId}`"
                class="condition-node-branch"
                data-testid="condition-branch-block"
              >
                <span class="condition-node-branch-kind">{{ branch.kind }}</span>
                <strong>{{ branch.label }}</strong>
              </div>
            </div>
            <div v-else-if="nodeProps.data.type !== 'VARIABLE_AGGREGATION'" class="node-line" :class="{ 'start-input-line': nodeProps.data.type === 'START' }">
              <span>{{ nodeProps.data.type === 'START' ? '输出' : '输入' }}</span>
              <template v-if="nodeProps.data.type === 'START'">
                <div class="node-variable-shell">
                  <div
                    class="node-variable-list"
                    data-testid="start-variable-list"
                    :aria-label="startVariableTooltip(nodeProps.data.outputVariables)"
                    tabindex="0"
                  >
                    <em
                      v-for="value in startVisibleVariables(nodeProps.data.outputVariables)"
                      :key="value"
                      class="node-variable-badge"
                    >
                      <span>str.</span>{{ value }}
                    </em>
                    <span
                      v-if="startHasHiddenVariables(nodeProps.data.outputVariables)"
                      class="node-variable-more"
                      data-testid="start-variable-more"
                    >
                      ...
                    </span>
                  </div>
                  <div
                    v-if="startHasHiddenVariables(nodeProps.data.outputVariables)"
                    class="node-variable-popover"
                    data-testid="start-variable-popover"
                    role="tooltip"
                  >
                    <em
                      v-for="value in nodeProps.data.outputVariables"
                      :key="`popover-${value}`"
                      class="node-variable-popover-badge"
                    >
                      <span>str.</span>{{ value }}
                    </em>
                  </div>
                </div>
              </template>
              <template v-else-if="nodeProps.data.type === 'END'">
                <div class="node-variable-shell">
                  <div
                    class="node-variable-list"
                    :aria-label="nodeVariableTooltip(nodeProps.data.inputVariables)"
                    tabindex="0"
                  >
                    <em
                      v-for="value in nodeVisibleVariables(nodeProps.data.inputVariables)"
                      :key="value"
                      class="node-variable-badge"
                    >
                      <span>str.</span>{{ value }}
                    </em>
                    <span
                      v-if="nodeHasHiddenVariables(nodeProps.data.inputVariables)"
                      class="node-variable-more"
                    >
                      ...
                    </span>
                  </div>
                  <div
                    v-if="nodeHasHiddenVariables(nodeProps.data.inputVariables)"
                    class="node-variable-popover"
                    role="tooltip"
                  >
                    <em
                      v-for="value in nodeProps.data.inputVariables"
                      :key="`popover-output-${value}`"
                      class="node-variable-popover-badge"
                    >
                      <span>str.</span>{{ value }}
                    </em>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="node-variable-shell">
                  <div
                    class="node-variable-list"
                    :aria-label="nodeVariableTooltip(nodeProps.data.inputVariables)"
                    tabindex="0"
                  >
                    <em
                      v-for="value in nodeVisibleVariables(nodeProps.data.inputVariables)"
                      :key="value"
                      class="node-variable-badge"
                    >
                      <span>str.</span>{{ value }}
                    </em>
                    <span
                      v-if="nodeHasHiddenVariables(nodeProps.data.inputVariables)"
                      class="node-variable-more"
                    >
                      ...
                    </span>
                    <strong v-if="!nodeProps.data.inputVariables.length">未配置输入</strong>
                  </div>
                  <div
                    v-if="nodeHasHiddenVariables(nodeProps.data.inputVariables)"
                    class="node-variable-popover"
                    role="tooltip"
                  >
                    <em
                      v-for="value in nodeProps.data.inputVariables"
                      :key="`popover-input-${value}`"
                      class="node-variable-popover-badge"
                    >
                      <span>str.</span>{{ value }}
                    </em>
                  </div>
                </div>
              </template>
            </div>
            <div v-if="nodeProps.data.type !== 'START' && nodeProps.data.type !== 'END' && !isBranchNodeType(nodeProps.data.type)" class="node-line">
              <span>输出</span>
              <div class="node-variable-shell">
                <div
                  class="node-variable-list"
                  :aria-label="nodeVariableTooltip(nodeProps.data.outputVariables)"
                  tabindex="0"
                >
                  <em
                    v-for="value in nodeVisibleVariables(nodeProps.data.outputVariables)"
                    :key="value"
                    class="node-variable-badge"
                  >
                    <span>str.</span>{{ value }}
                  </em>
                  <span
                    v-if="nodeHasHiddenVariables(nodeProps.data.outputVariables)"
                    class="node-variable-more"
                  >
                    ...
                  </span>
                </div>
                <div
                  v-if="nodeHasHiddenVariables(nodeProps.data.outputVariables)"
                  class="node-variable-popover"
                  role="tooltip"
                >
                  <em
                    v-for="value in nodeProps.data.outputVariables"
                    :key="`popover-output-${value}`"
                    class="node-variable-popover-badge"
                  >
                    <span>str.</span>{{ value }}
                  </em>
                </div>
              </div>
            </div>
            <template v-if="isBranchNodeType(nodeProps.data.type)">
              <Handle
                v-for="branch in nodeProps.data.conditionBranches"
                :id="branch.handleId"
                :key="branch.handleId"
                type="source"
                :position="Position.Right"
                :class="[
                  'node-port source-port condition-source-port',
                  { 'connection-preview': isConnectionPreviewPort(nodeProps.data.nodeKey, 'source', branch.handleId) },
                ]"
                data-testid="condition-source-port"
                :data-node-key="nodeProps.data.nodeKey"
                data-port-type="source"
                :data-handle-id="branch.handleId"
                :data-branch-label="branch.label"
                :aria-label="`${branch.kind}${branch.label}`"
                :style="{ top: branch.top }"
              />
            </template>
            <Handle
              v-else-if="nodeProps.data.type !== 'END'"
              type="source"
              :position="Position.Right"
              :class="[
                'node-port source-port',
                { 'connection-preview': isConnectionPreviewPort(nodeProps.data.nodeKey, 'source') },
              ]"
              :data-node-key="nodeProps.data.nodeKey"
              data-port-type="source"
              data-handle-id=""
            />
          </div>
        </template>
      </VueFlow>

      <aside v-if="selectedNode && selectedSchema" class="node-config-panel" data-testid="node-config-panel">
        <div class="config-header">
          <div class="node-type-icon" :class="`icon-${selectedNode.type.toLowerCase()}`">
            <component :is="nodeIcon(selectedNode.type)" />
          </div>
          <div class="config-title-block">
            <div v-if="nodeTitleEditing" class="config-title-editor">
              <input
                ref="nodeTitleEditInputRef"
                v-model="nodeTitleDraft"
                aria-label="节点名称"
                maxlength="80"
                @blur="commitNodeTitleEdit"
                @keydown.enter.prevent="commitNodeTitleEdit"
                @keydown.esc.prevent="cancelNodeTitleEdit"
              />
              <button type="button" aria-label="确认节点名称" @mousedown.prevent @click="commitNodeTitleEdit">
                <CheckIcon aria-hidden="true" />
              </button>
              <button type="button" aria-label="取消节点名称" @mousedown.prevent @click="cancelNodeTitleEdit">
                <XIcon aria-hidden="true" />
              </button>
            </div>
            <button
              v-else-if="canRenameSelectedNode"
              type="button"
              class="config-title-button"
              aria-label="编辑节点名称"
              @click="startSelectedNodeTitleEdit"
            >
              <span class="config-title-heading">{{ selectedConfigPanelTitle() }}</span>
            </button>
            <h3 v-else>{{ selectedConfigPanelTitle() }}</h3>
          </div>
          <div v-if="canTestSelectedNode" class="config-header-actions">
            <button type="button" aria-label="试运行当前节点" title="试运行当前节点" @click="openSelectedNodeTest">
              <PlayIcon aria-hidden="true" />
            </button>
          </div>
          <button type="button" aria-label="关闭配置" @click="selectedNodeKey = ''">
            <XIcon aria-hidden="true" />
          </button>
        </div>

        <section v-if="selectedNode.type === 'LLM'" class="config-section llm-mode-section">
          <div class="llm-mode-switch" data-testid="llm-mode-section">
            <button type="button" class="active">单次</button>
            <button type="button" disabled>批处理</button>
          </div>
        </section>

        <section v-if="selectedNode.type === 'END'" class="config-section end-return-mode-section" data-testid="end-return-mode-section">
          <div class="end-response-editor" data-testid="end-response-editor">
            <div class="end-return-mode" data-testid="end-return-mode" role="group" aria-label="结束返回模式">
              <button
                type="button"
                :class="{ active: endReturnMode() === 'text' }"
                @click="setEndReturnMode('text')"
              >
                返回文本
              </button>
              <button
                type="button"
                :class="{ active: endReturnMode() === 'variables' }"
                @click="setEndReturnMode('variables')"
              >
                返回变量
              </button>
            </div>
          </div>
        </section>

        <section
          v-if="selectedNode.type === 'LLM'"
          class="config-section"
          :class="{ collapsed: isConfigSectionCollapsed('模型'), 'picker-open': modelPickerOpen }"
          data-testid="llm-model-section"
        >
          <div class="section-title config-section-title-row">
            <button
              type="button"
              class="config-section-toggle"
              :aria-expanded="!isConfigSectionCollapsed('模型')"
              :aria-controls="configSectionContentId('模型')"
              @click="toggleConfigSection('模型')"
            >
              <span class="section-chevron" aria-hidden="true">›</span>
              <strong>模型</strong>
            </button>
            <button type="button" class="section-icon-button" aria-label="模型设置" @click.stop="toggleModelParameterPanel">
              <SettingsIcon aria-hidden="true" />
            </button>
          </div>
          <div
            v-show="!isConfigSectionCollapsed('模型')"
            :id="configSectionContentId('模型')"
            class="config-section-content"
          >
          <button
            type="button"
            class="model-display-trigger"
            data-testid="llm-model-display"
            @click="toggleModelSelector"
          >
            <span>{{ llmModelDisplayName }}</span>
            <small>点击切换模型</small>
          </button>
          <div v-if="modelPickerOpen" class="model-picker-shell" data-testid="llm-model-selector">
            <div class="model-picker-header">
              <strong>模型选择</strong>
              <span>{{ filteredLlmModelOptions.length }} 个结果</span>
            </div>
            <div class="model-search-row">
              <a-input
                v-model:value="llmModelSearch"
                placeholder="搜索模型或供应商"
                allow-clear
                @keydown.enter.prevent="applyLlmModelSearch"
              />
              <button type="button" aria-label="搜索模型" @click="applyLlmModelSearch">
                搜索
              </button>
            </div>
            <div class="model-option-list">
              <button
                v-for="option in filteredLlmModelOptions"
                :key="option.modelConfigId || option.value"
                type="button"
                class="model-option-card"
                data-testid="llm-model-option"
                :class="{ unavailable: !option.enabled }"
                :disabled="!option.enabled"
                @click="selectLlmModel(option)"
              >
                <span
                  class="model-provider-icon"
                  :data-provider-icon="option.providerIconKey"
                  data-testid="llm-model-provider-icon"
                  aria-hidden="true"
                >
                  <img
                    v-if="modelProviderLogoSrc(option.providerIconKey)"
                    :src="modelProviderLogoSrc(option.providerIconKey)"
                    alt=""
                    loading="lazy"
                  >
                  <span v-else>{{ modelProviderIconText(option.providerIconKey) }}</span>
                </span>
                <span class="model-option-copy">
                  <span class="model-option-heading">
                    <span class="model-option-name">{{ option.label }}</span>
                    <span class="model-provider-tag" data-testid="llm-model-provider-tag">{{ option.providerType }}</span>
                  </span>
                  <span class="model-option-description" data-testid="llm-model-description">{{ option.description }}</span>
                </span>
              </button>
            </div>
            <p v-if="filteredLlmModelOptions.length === 0" class="model-picker-empty">没有匹配的模型</p>
          </div>
          <div v-if="modelParameterPanelOpen" class="model-parameter-panel" data-testid="llm-model-parameter-panel">
            <div class="model-parameter-header">
              <strong>模型参数</strong>
              <button type="button" aria-label="关闭模型参数" @click="modelParameterPanelOpen = false">
                <XIcon aria-hidden="true" />
              </button>
            </div>
            <div class="model-parameter-grid">
              <label
                v-for="field in llmModelParameterFields"
                :key="field.key"
                class="model-parameter-field"
                :class="{ 'model-parameter-field--number': field.type === 'number' }"
              >
                <span>{{ field.label }}</span>
                <div
                  v-if="field.type === 'number'"
                  class="model-parameter-slider-control"
                  :data-testid="`model-parameter-${field.key}`"
                >
                  <input
                    class="model-parameter-slider"
                    data-testid="model-parameter-slider"
                    type="range"
                    :min="field.min ?? 0"
                    :max="field.max ?? 100000"
                    :step="field.step ?? 1"
                    :value="modelParameterNumberValue(field)"
                    :style="modelParameterSliderStyle(field)"
                    @input="setModelParameterNumberValue(field.key, ($event.target as HTMLInputElement).value)"
                  />
                  <a-input-number
                    class="model-parameter-number-input"
                    data-testid="model-parameter-number-input"
                    :value="modelParameterNumberValue(field)"
                    :min="field.min ?? 0"
                    :max="field.max ?? 100000"
                    :step="field.step ?? 1"
                    @update:value="setModelParameterNumberValue(field.key, $event ?? modelParameterDefault(field.key))"
                  />
                </div>
                <a-select :virtual="false"
                  v-else-if="field.type === 'select'"
                  :value="fieldValue(field.key) || field.options?.[0]"
                  @update:value="setFieldValue(field.key, $event)"
                >
                  <a-select-option v-for="option in field.options || []" :key="option" :value="option" >{{ selectOptionLabel(field.key, option) }}</a-select-option>
                </a-select>
                <a-textarea
                  v-else
                  :value="String(fieldValue(field.key) || '')"
                  :placeholder="field.placeholder"
                  :rows="3"
                  @update:value="setFieldValue(field.key, $event)"
                />
              </label>
            </div>
          </div>
          </div>
        </section>

        <section
          v-if="selectedNode.type === 'LLM'"
          class="config-section"
          :class="{ collapsed: isConfigSectionCollapsed('技能'), 'picker-open': resourcePickerOpen }"
          data-testid="llm-resource-section"
        >
          <div class="section-title config-section-title-row">
            <button
              type="button"
              class="config-section-toggle"
              :aria-expanded="!isConfigSectionCollapsed('技能')"
              :aria-controls="configSectionContentId('技能')"
              @click="toggleConfigSection('技能')"
            >
              <span class="section-chevron" aria-hidden="true">›</span>
              <strong>技能</strong>
            </button>
            <button type="button" class="section-icon-button" aria-label="添加资源" @click.stop="resourcePickerOpen = !resourcePickerOpen">
              <LucidePlus aria-hidden="true" />
            </button>
          </div>
          <div
            v-show="!isConfigSectionCollapsed('技能')"
            :id="configSectionContentId('技能')"
            class="config-section-content"
          >
          <div class="llm-resource-fields llm-tool-settings" data-testid="llm-tool-settings">
            <label>
              工具选择
              <a-select :virtual="false"
                :value="fieldValue('toolChoiceMode') || 'auto'"
                aria-label="工具选择"
                @update:value="setFieldValue('toolChoiceMode', $event)"
              >
                <a-select-option value="auto">auto</a-select-option>
                <a-select-option value="required">required</a-select-option>
                <a-select-option value="disabled">disabled</a-select-option>
              </a-select>
            </label>
            <label>
              最大调用轮次
              <a-input-number
                :value="Number(fieldValue('maxToolRounds') || 1)"
                :min="1"
                :max="3"
                :step="1"
                aria-label="最大调用轮次"
                @update:value="setFieldValue('maxToolRounds', $event ?? 1)"
              />
            </label>
            <label>
              工具结果
              <a-select :virtual="false"
                :value="fieldValue('toolResultMode') || 'append'"
                aria-label="工具结果"
                @update:value="setFieldValue('toolResultMode', $event)"
              >
                <a-select-option value="append">append</a-select-option>
                <a-select-option value="separate">separate</a-select-option>
              </a-select>
            </label>
          </div>
          <div v-if="!llmResources().length" class="resource-empty-state">暂未配置技能</div>
          <div v-else class="llm-resource-list" data-testid="llm-resource-list">
            <article
              v-for="(resource, index) in llmResources()"
              :key="`${resource.type}-${index}`"
              class="llm-resource-card"
            >
              <div class="llm-resource-card-header">
                <div>
                  <strong>{{ llmResourceLabel(resource) }}</strong>
                  <span>{{ llmResourceStatus(resource) }}</span>
                </div>
                <button type="button" aria-label="移除资源" @click="removeLlmResource(index)">
                  <Trash2 aria-hidden="true" />
                </button>
              </div>
              <div v-if="normalizeLlmResourceType(resource) === 'KNOWLEDGE_BASE'" class="llm-resource-fields">
                <label>
                  知识库 ID
                  <a-input
                    :value="String(resource.knowledgeBaseId || resource.id || '')"
                    aria-label="知识库 ID"
                    placeholder="1"
                    @update:value="updateLlmResource(index, { knowledgeBaseId: $event })"
                  />
                </label>
                <label>
                  检索问题
                  <a-input
                    :value="String(resource.query || '')"
                    aria-label="检索问题"
                    placeholder="{{start.USER_INPUT}}"
                    @update:value="updateLlmResource(index, { query: $event })"
                  />
                </label>
                <label>
                  召回数量
                  <a-input
                    :value="String(resource.topK || 3)"
                    aria-label="召回数量"
                    placeholder="3"
                    @update:value="updateLlmResource(index, { topK: Number($event) || 3 })"
                  />
                </label>
              </div>
            </article>
          </div>
          <div v-if="resourcePickerOpen" class="resource-picker-shell" data-testid="llm-skill-picker">
            <div class="llm-skill-type-tabs" data-testid="llm-skill-type-tabs" role="tablist" aria-label="技能资源类型">
              <button
                v-for="tab in llmSkillTabs"
                :key="tab.value"
                type="button"
                role="tab"
                :aria-selected="activeLlmSkillTab === tab.value"
                :class="{ active: activeLlmSkillTab === tab.value }"
                @click="activeLlmSkillTab = tab.value"
              >
                {{ tab.label }}
              </button>
            </div>
            <a-input
              v-model:value="llmSkillSearch"
              class="llm-skill-search"
              size="small"
              placeholder="搜索技能"
            />
            <div class="llm-skill-resource-list" data-testid="llm-skill-resource-list">
              <button
                v-for="resource in filteredLlmSkillResources"
                :key="resource.key"
                type="button"
                :disabled="resource.disabled"
                :class="{ unavailable: resource.disabled }"
                @click="selectLlmSkillResource(resource)"
              >
                <span>{{ resource.name }}</span>
                <small>{{ resource.description }}</small>
              </button>
              <p v-if="!filteredLlmSkillResources.length" class="resource-empty-state">暂无匹配技能</p>
            </div>
          </div>
          </div>
        </section>

        <section
          v-for="section in visibleConfigSections"
          :key="section.title"
          class="config-section"
          :class="{ collapsed: isConfigSectionCollapsed(section.title) }"
          :data-testid="configSectionTestId(section.title)"
        >
          <div class="section-title config-section-title-row">
            <button
              type="button"
              class="config-section-toggle"
              :aria-expanded="!isConfigSectionCollapsed(section.title)"
              :aria-controls="configSectionContentId(section.title)"
              @click="toggleConfigSection(section.title)"
            >
              <span class="section-chevron" aria-hidden="true">›</span>
              <strong>{{ section.title }}</strong>
            </button>
            <label
              v-if="isChatflowMode && selectedNode.type === 'LLM' && (section.title === '输入' || section.title === '输入参数')"
              class="history-toggle"
              @click.stop
            >
              <input
                type="checkbox"
                :checked="Boolean(fieldValue('includeHistory'))"
                aria-label="会话历史"
                @change="setHistoryEnabled"
              />
              会话历史
            </label>
            <button
              v-if="hasConditionBranchField(section)"
              type="button"
              class="section-icon-button"
              aria-label="添加条件分支"
              title="添加条件分支"
              @click.stop="addConditionBranch"
            >
              <LucidePlus aria-hidden="true" />
            </button>
          </div>
          <div
            v-show="!isConfigSectionCollapsed(section.title)"
            :id="configSectionContentId(section.title)"
            class="config-section-content"
          >
          <div v-for="field in section.fields" :key="field.key" class="config-field">
            <div v-if="shouldShowConfigFieldLabel(field.type)" class="field-label-row">
              <label>{{ field.label }}</label>
            </div>
            <div v-if="field.type === 'readonly'" class="readonly-values">
              <a-tag
                v-for="value in readonlyValues(field.key)"
                :key="value"
                size="small"
              >
                {{ value }}
              </a-tag>
            </div>
            <div
              v-else-if="field.type === 'end-response'"
              class="end-response-editor"
              data-testid="end-response-editor"
            >
              <div class="end-return-mode" data-testid="end-return-mode" role="group" aria-label="结束返回模式">
                <button
                  type="button"
                  :class="{ active: endReturnMode() === 'text' }"
                  @click="setEndReturnMode('text')"
                >
                  返回文本
                </button>
                <button
                  type="button"
                  :class="{ active: endReturnMode() === 'variables' }"
                  @click="setEndReturnMode('variables')"
                >
                  返回变量
                </button>
              </div>
              <div class="end-output-format-row">
                <label>输出格式</label>
                <a-select :virtual="false"
                  :value="outputFormatValue()"
                  aria-label="输出格式"
                  @update:value="setOutputFormat"
                >
                  <a-select-option
                    v-for="option in outputFormatOptions"
                    :key="option"

                    :value="option"
                  >{{ option }}</a-select-option>
                </a-select>
              </div>
              <template v-if="endReturnMode() === 'text'">
                <div class="end-response-heading">
                  <label>响应内容</label>
                </div>
                <a-textarea
                  class="end-response-textarea"
                  :value="String(fieldValue('output') || '')"
                  aria-label="响应内容"
                  placeholder="返回给调用方的文本，可使用变量引用"
                  :rows="5"
                  @update:value="handleVariableFieldInput('output', $event)"
                />
                <div
                  v-if="activeVariableField === 'output'"
                  class="inline-variable-suggestion-popover end-variable-popover"
                  data-testid="variable-picker"
                  data-picker-kind="inline"
                >
                  <a-input v-model:value="variableSearch" size="small" placeholder="搜索变量" />
                  <div class="inline-variable-list" data-testid="inline-variable-list">
                    <button
                      v-for="option in inlineVariableOptions"
                      :key="`${option.groupKey}:${option.item.reference}`"
                      type="button"
                      class="inline-variable-option"
                      data-testid="variable-option"
                      @click="insertVariable('output', option.item.reference)"
                    >
                      <span class="variable-option-main">
                        <strong>{{ option.item.variable }}</strong>
                      </span>
                      <span class="variable-type-badge">{{ variableListTypeLabel(option.item.type) }}</span>
                    </button>
                    <p v-if="inlineVariableOptions.length === 0" class="variable-empty">暂无可引用变量</p>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="output-column-row">
                  <span>输出变量</span>
                  <span>变量类型</span>
                  <button type="button" class="output-row-icon" aria-label="添加输出变量" @click="addOutputParameter">
                    <LucidePlus aria-hidden="true" />
                  </button>
                </div>
                <div
                  v-for="(row, index) in outputParameterRows()"
                  :key="`${index}-${row.name}-${row.type}`"
                  class="output-parameter-row"
                  data-testid="output-parameter-row"
                >
                  <a-input
                    :value="row.name"
                    aria-label="输出变量名"
                    placeholder="变量名"
                    @update:value="setOutputParameterName(index, $event)"
                  />
                  <a-select :virtual="false"
                    :value="row.type"
                    aria-label="输出变量类型"
                    @update:value="setOutputParameterType(index, $event)"
                  >
                    <a-select-option
                      v-for="option in outputParameterTypeOptions"
                      :key="option"

                      :value="option"
                    >{{ outputParameterTypeLabel(option) }}</a-select-option>
                  </a-select>
                  <button
                    type="button"
                    class="output-row-icon"
                    aria-label="删除输出变量"
                    :disabled="outputParameterRows().length <= 1"
                    @click="removeOutputParameter(index)"
                  >
                    <XIcon aria-hidden="true" />
                  </button>
                </div>
                <ul v-if="outputParameterErrors().length" class="output-parameter-errors">
                  <li v-for="error in outputParameterErrors()" :key="error">{{ error }}</li>
                </ul>
              </template>
            </div>
            <div
              v-else-if="field.type === 'condition-branches'"
              class="condition-branch-editor"
              data-testid="condition-branch-editor"
            >
              <article
                v-for="(branch, branchIndex) in conditionBranches()"
                :key="`${branchIndex}-${branch.key}`"
                class="condition-branch-card"
                data-testid="condition-branch-card"
              >
                <div class="condition-branch-header">
                  <span class="condition-drag-handle" aria-hidden="true">⋮⋮</span>
                  <span class="condition-branch-kind">{{ conditionBranchKindLabel(branchIndex) }}</span>
                  <span class="condition-branch-priority">优先级 {{ branchIndex + 1 }}</span>
                  <button
                    v-if="editingConditionBranchNameIndex !== branchIndex"
                    type="button"
                    class="condition-branch-title"
                    data-testid="condition-branch-title"
                    :aria-label="`编辑分支名称 ${branch.name}`"
                    @click="startConditionBranchNameEdit(branchIndex)"
                  >
                    <strong>{{ branch.name }}</strong>
                  </button>
                  <a-input
                    v-else
                    :value="branch.name"
                    aria-label="分支名称"
                    class="condition-branch-name-input"
                    placeholder="点击填写分支名称"
                    @update:value="setConditionBranchName(branchIndex, $event)"
                    @blur="stopConditionBranchNameEdit"
                    @keydown.enter="stopConditionBranchNameEdit"
                    @keydown.esc="stopConditionBranchNameEdit"
                  />
                  <button type="button" class="output-row-icon" aria-label="删除分支" @click="removeConditionBranch(branchIndex)">
                    <XIcon aria-hidden="true" />
                  </button>
                </div>
                <div
                  v-for="(condition, conditionIndex) in branch.conditions"
                  :key="`${conditionIndex}-${condition.operator}`"
                  class="condition-row"
                  data-testid="condition-row"
                >
                  <div
                    v-if="conditionIndex > 0"
                    class="condition-logic-toggle"
                    role="group"
                    aria-label="条件连接关系"
                  >
                    <button
                      type="button"
                      :class="{ active: branch.logic === 'AND' }"
                      @click="setConditionBranchLogic(branchIndex, 'AND')"
                    >
                      且
                    </button>
                    <button
                      type="button"
                      :class="{ active: branch.logic === 'OR' }"
                      @click="setConditionBranchLogic(branchIndex, 'OR')"
                    >
                      或
                    </button>
                  </div>
                  <div class="condition-value-cell condition-left-cell">
                    <div class="condition-variable-select condition-operand-control" data-testid="condition-operand-control">
                      <button
                        type="button"
                        class="condition-variable-select-button"
                        aria-label="选择左值变量"
                        @click="openConditionVariablePicker(branchIndex, conditionIndex, 'left', $event)"
                      >
                        <input class="reference-value-proxy" aria-label="条件左值" :value="condition.left.value" readonly tabindex="-1" />
                        <template v-if="condition.left.valueMode === 'reference' && inputReferenceSelection(condition.left.value)">
                          <span class="condition-variable-select-main" data-testid="condition-variable-chip">
                            <strong>{{ inputReferenceSelection(condition.left.value)!.item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableTypeLabel(inputReferenceSelection(condition.left.value)!.item.type) }}</span>
                        </template>
                        <span v-else class="condition-variable-select-placeholder">选择变量</span>
                        <ChevronDownIcon class="condition-variable-select-arrow" data-testid="condition-variable-select-arrow" aria-hidden="true" />
                      </button>
                      <button
                        v-if="condition.left.valueMode === 'reference' && inputReferenceSelection(condition.left.value)"
                        type="button"
                        class="input-variable-clear condition-variable-select-clear"
                        aria-label="清除左值变量引用"
                        @click.stop="clearConditionOperandReference(branchIndex, conditionIndex, 'left')"
                      >
                        <span aria-hidden="true">×</span>
                      </button>
                    </div>
                    <div
                      v-if="isConditionVariablePickerOpen(branchIndex, conditionIndex, 'left')"
                      class="variable-popover coze-variable-source-popover input-variable-popover condition-variable-popover"
                      data-testid="condition-variable-picker"
                    >
                      <a-input v-model:value="conditionVariableSearch" placeholder="搜索变量" allow-clear />
                      <div class="variable-source-list coze-variable-source-list" data-testid="condition-variable-source-list">
                        <button
                          v-for="group in filteredConditionVariableGroups"
                          :key="variableGroupKey(group)"
                          type="button"
                          class="variable-source-item coze-variable-source-item"
                          :class="{ active: activeConditionVariableGroupKey === variableGroupKey(group) }"
                          data-testid="condition-variable-source-item"
                          @mouseenter="activateConditionVariableGroup(group, $event)"
                          @click="activateConditionVariableGroup(group, $event)"
                        >
                          <span class="variable-source-copy">
                            <strong>{{ group.title }}</strong>
                          </span>
                          <span v-if="group.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                        </button>
                      </div>
                      <div
                        v-if="activeConditionVariableGroup"
                        class="variable-flyout"
                        :data-placement="variableFlyoutPlacement"
                        data-testid="condition-variable-flyout"
                      >
                        <div class="variable-item-list" data-testid="condition-variable-item-list">
                          <button
                            v-for="item in activeConditionVariableGroup.items"
                            :key="item.reference"
                            type="button"
                            class="variable-option"
                            data-testid="condition-variable-option"
                            @click="insertConditionVariableReference(item.reference)"
                          >
                            <span class="variable-option-main">
                              <strong>{{ item.variable }}</strong>
                            </span>
                            <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                          </button>
                          <p v-if="activeConditionVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <a-select :virtual="false"
                    class="condition-operator-select"
                    :value="condition.operator"
                    aria-label="条件操作符"
                    @update:value="setConditionRowValue(branchIndex, conditionIndex, 'operator', $event)"
                  >
                    <a-select-option
                      v-for="option in conditionOperatorOptionsForCondition(condition)"
                      :key="option.value"

                      :value="option.value"
                    >{{ option.label }}</a-select-option>
                  </a-select>
                  <div class="condition-value-cell condition-right-cell">
                    <div class="variable-value-combo condition-operand-control condition-comparison-value-control" data-testid="condition-operand-control">
                      <span
                        class="condition-right-type-prefix"
                        data-testid="condition-right-type-prefix"
                      >
                        {{ conditionOperandCompactTypeLabel(condition.left) }}
                      </span>
                      <div class="variable-value-main">
                        <div
                          v-if="condition.right.valueMode === 'reference' && inputReferenceSelection(condition.right.value)"
                          class="input-variable-chip condition-variable-chip"
                          data-testid="condition-variable-chip"
                        >
                          <input class="reference-value-proxy" aria-label="条件右值" :value="condition.right.value" readonly tabindex="-1" />
                          <span class="input-variable-chip-main">
                            <strong>{{ inputReferenceSelection(condition.right.value)!.item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableTypeLabel(inputReferenceSelection(condition.right.value)!.item.type) }}</span>
                          <button
                            type="button"
                            class="input-variable-clear"
                            aria-label="清除右值变量引用"
                            @click.stop="clearConditionOperandReference(branchIndex, conditionIndex, 'right')"
                          >
                            <span aria-hidden="true">×</span>
                          </button>
                        </div>
                        <a-input
                          v-else
                          :value="condition.right.value"
                          aria-label="条件右值"
                          :placeholder="conditionRightOperandPlaceholder(condition.operator)"
                          :disabled="isConditionRightOperandDisabled(condition.operator)"
                          @update:value="handleConditionOperandInput(branchIndex, conditionIndex, 'right', $event)"
                        />
                      </div>
                      <button
                        type="button"
                        class="variable-picker-trigger"
                        aria-label="选择右值变量"
                        :disabled="isConditionRightOperandDisabled(condition.operator)"
                        @click="openConditionVariablePicker(branchIndex, conditionIndex, 'right', $event)"
                      >
                        <Connection aria-hidden="true" />
                      </button>
                    </div>
                    <div
                      v-if="isConditionVariablePickerOpen(branchIndex, conditionIndex, 'right')"
                      class="variable-popover coze-variable-source-popover input-variable-popover condition-variable-popover"
                      data-testid="condition-variable-picker"
                    >
                      <a-input v-model:value="conditionVariableSearch" placeholder="搜索变量" allow-clear />
                      <div class="variable-source-list coze-variable-source-list" data-testid="condition-variable-source-list">
                        <button
                          v-for="group in filteredConditionVariableGroups"
                          :key="variableGroupKey(group)"
                          type="button"
                          class="variable-source-item coze-variable-source-item"
                          :class="{ active: activeConditionVariableGroupKey === variableGroupKey(group) }"
                          data-testid="condition-variable-source-item"
                          @mouseenter="activateConditionVariableGroup(group, $event)"
                          @click="activateConditionVariableGroup(group, $event)"
                        >
                          <span class="variable-source-copy">
                            <strong>{{ group.title }}</strong>
                          </span>
                          <span v-if="group.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                        </button>
                      </div>
                      <div
                        v-if="activeConditionVariableGroup"
                        class="variable-flyout"
                        :data-placement="variableFlyoutPlacement"
                        data-testid="condition-variable-flyout"
                      >
                        <div class="variable-item-list" data-testid="condition-variable-item-list">
                          <button
                            v-for="item in activeConditionVariableGroup.items"
                            :key="item.reference"
                            type="button"
                            class="variable-option"
                            data-testid="condition-variable-option"
                            @click="insertConditionVariableReference(item.reference)"
                          >
                            <span class="variable-option-main">
                              <strong>{{ item.variable }}</strong>
                            </span>
                            <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                          </button>
                          <p v-if="activeConditionVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <button type="button" class="output-row-icon condition-delete-button" aria-label="删除条件" @click="removeConditionRow(branchIndex, conditionIndex)">
                    <XIcon aria-hidden="true" />
                  </button>
                </div>
                <button type="button" class="input-add-button condition-add-button" @click="addConditionRow(branchIndex)">
                  <LucidePlus aria-hidden="true" />
                  <span>添加条件</span>
                </button>
              </article>
              <div class="condition-default-row" data-testid="condition-default-card">
                <span class="condition-branch-kind">否则</span>
                <button
                  v-if="!editingConditionDefaultName"
                  type="button"
                  class="condition-branch-title condition-default-title"
                  data-testid="condition-default-title"
                  :aria-label="`编辑否则分支名称 ${conditionDefaultBranchName(selectedNode.config)}`"
                  @click="startConditionDefaultNameEdit"
                >
                  <strong>{{ conditionDefaultBranchName(selectedNode.config) }}</strong>
                </button>
                <a-input
                  v-else
                  :value="conditionDefaultBranchName(selectedNode.config)"
                  aria-label="否则分支名称"
                  placeholder="点击填写默认分支名称"
                  @update:value="setConditionDefaultBranchName($event)"
                  @blur="stopConditionDefaultNameEdit"
                  @keydown.enter="stopConditionDefaultNameEdit"
                  @keydown.esc="stopConditionDefaultNameEdit"
                />
              </div>
            </div>
            <div
              v-else-if="field.type === 'question-options'"
              class="secondary-row-editor question-option-editor"
              data-testid="question-option-editor"
            >
              <div class="secondary-row-header question-option-header">
                <span>选项文案</span>
                <span>选项值</span>
                <button type="button" class="output-row-icon" aria-label="添加回答选项" @click="addQuestionOption">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in questionOptionRows()"
                :key="`${index}-${row.label}-${row.value}`"
                class="secondary-row question-option-row"
                data-testid="question-option-row"
              >
                <a-input
                  :value="row.label"
                  aria-label="选项文案"
                  placeholder="例如 是"
                  @update:value="setQuestionOptionLabel(index, $event)"
                />
                <a-input
                  :value="row.value"
                  aria-label="选项值"
                  placeholder="例如 yes"
                  @update:value="setQuestionOptionValue(index, $event)"
                />
                <button type="button" class="output-row-icon" aria-label="删除回答选项" @click="removeQuestionOption(index)">
                  <XIcon aria-hidden="true" />
                </button>
              </div>
              <p v-if="questionOptionRows().length === 0" class="secondary-empty">选择「选项」答案类型后，可在这里添加按钮选项。</p>
            </div>
            <div
              v-else-if="field.type === 'collection-fields'"
              class="secondary-row-editor collection-field-editor"
              data-testid="collection-field-editor"
            >
              <div class="secondary-row-header collection-field-header">
                <span>字段名</span>
                <span>类型</span>
                <span>必填</span>
                <span>说明</span>
                <span>写入</span>
                <button type="button" class="output-row-icon" aria-label="添加收集字段" @click="addCollectionField">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in collectionFieldRows()"
                :key="`${index}-${row.name}-${row.type}-${row.required}`"
                class="secondary-row collection-field-row"
                data-testid="collection-field-row"
              >
                <a-input
                  :value="row.name"
                  aria-label="收集字段名"
                  placeholder="phone"
                  @update:value="setCollectionFieldName(index, $event)"
                />
                <a-select :virtual="false"
                  :value="row.type"
                  aria-label="收集字段类型"
                  @update:value="setCollectionFieldType(index, $event)"
                >
                  <a-select-option
                    v-for="option in outputParameterTypeOptions"
                    :key="option"

                    :value="option"
                  >{{ variableTypeLabel(option) }}</a-select-option>
                </a-select>
                <label class="start-required-toggle">
                  <input
                    type="checkbox"
                    aria-label="收集字段必填"
                    :checked="row.required"
                    @change="setCollectionFieldRequired(index, ($event.target as HTMLInputElement).checked)"
                  />
                </label>
                <a-input
                  :value="row.description"
                  aria-label="收集字段说明"
                  placeholder="字段说明"
                  @update:value="setCollectionFieldDescription(index, $event)"
                />
                <div class="collection-target-cell">
                  <a-select :virtual="false"
                    :value="row.targetScope"
                    aria-label="收集字段写入范围"
                    @update:value="setCollectionFieldTargetScope(index, $event)"
                  >
                    <a-select-option value="flow" >flow</a-select-option>
                    <a-select-option value="conversation" >conversation</a-select-option>
                    <a-select-option value="user" >user</a-select-option>
                    <a-select-option value="channel" >channel</a-select-option>
                    <a-select-option value="global" >global</a-select-option>
                  </a-select>
                  <a-input
                    :value="row.targetVariable"
                    aria-label="收集字段目标变量"
                    placeholder="变量名"
                    @update:value="setCollectionFieldTargetVariable(index, $event)"
                  />
                </div>
                <button type="button" class="output-row-icon" aria-label="删除收集字段" @click="removeCollectionField(index)">
                  <XIcon aria-hidden="true" />
                </button>
              </div>
            </div>
            <div
              v-else-if="field.type === 'intent-rows'"
              class="secondary-row-editor intent-row-editor"
              data-testid="intent-row-editor"
            >
              <div class="secondary-row-header intent-row-header">
                <span>名称</span>
                <span>描述</span>
                <span>示例</span>
                <button type="button" class="output-row-icon" aria-label="添加意图" @click="addIntentRow">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in intentRows()"
                :key="`${index}-${row.key}-${row.branch}`"
                class="secondary-row intent-row"
                data-testid="intent-row"
                @dragover.prevent
                @drop="dropIntentRow(index, $event)"
              >
                <button
                  type="button"
                  class="intent-drag-handle"
                  aria-label="拖拽意图排序"
                  draggable="true"
                  @dragstart="startIntentRowDrag(index, $event)"
                  @dragend="endIntentRowDrag"
                >
                  ⋮⋮
                </button>
                <div class="intent-row-fields">
                  <a-input
                    class="intent-name-field"
                    :value="row.name"
                    aria-label="意图名称"
                    placeholder="退款"
                    @update:value="setIntentName(index, $event)"
                  />
                  <a-input
                    class="intent-description-field"
                    :value="row.description"
                    aria-label="意图描述"
                    placeholder="请输入用户意图的描述，如售后问题等"
                    @update:value="setIntentDescription(index, $event)"
                  />
                  <a-textarea
                    class="intent-examples-field"
                    :value="row.examples.join('\n')"
                    aria-label="意图示例"
                    :maxlength="300"
                    :rows="3"
                    placeholder="每行一个例句"
                    @update:value="setIntentExamples(index, $event)"
                  />
                </div>
                <button type="button" class="output-row-icon" aria-label="删除意图" @click="removeIntentRow(index)">
                  <XIcon aria-hidden="true" />
                </button>
              </div>
            </div>
            <div
              v-else-if="field.type === 'start-variables'"
              class="start-variable-editor"
              data-testid="start-variable-editor"
            >
              <div class="start-variable-header" data-testid="start-variable-header">
                <span>变量名</span>
                <span>变量类型</span>
                <span>必填</span>
                <button type="button" class="output-row-icon" aria-label="添加开始变量" @click="addStartVariable">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in startVariableRows()"
                :key="`${index}-${row.name}-${row.type}-${row.required}`"
                class="start-variable-row"
                :class="{ 'built-in': row.builtIn }"
                data-testid="start-variable-row"
              >
                <a-input
                  :value="row.name"
                  aria-label="开始变量名"
                  placeholder="变量名"
                  :disabled="row.builtIn"
                  @update:value="setStartVariableName(index, $event)"
                />
                <a-select :virtual="false"
                  :value="row.type"
                  aria-label="开始变量类型"
                  :disabled="row.builtIn"
                  @update:value="setStartVariableType(index, $event)"
                >
                  <a-select-option
                    v-for="option in outputParameterTypeOptions"
                    :key="option"

                    :value="option"
                  >{{ variableTypeLabel(option) }}</a-select-option>
                </a-select>
                <label class="start-required-toggle">
                  <input
                    type="checkbox"
                    aria-label="开始变量必填"
                    :checked="row.required && !row.builtIn"
                    :disabled="row.builtIn"
                    @change="setStartVariableRequired(index, ($event.target as HTMLInputElement).checked)"
                  />
                </label>
                <button
                  type="button"
                  class="output-row-icon"
                  aria-label="删除开始变量"
                  :disabled="row.builtIn || startVariableRows().length <= 1"
                  @click="removeStartVariable(index)"
                >
                  <XIcon aria-hidden="true" />
                </button>
              </div>
            </div>
            <div
              v-else-if="field.type === 'input-parameters'"
              class="input-parameter-editor"
              data-testid="input-parameter-editor"
            >
              <div class="input-parameter-toolbar">
                <span>变量名</span>
                <span>变量类型</span>
                <span>变量值</span>
                <button type="button" class="output-row-icon" aria-label="添加输入变量" @click="addInputParameter">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in inputParameterRows()"
                :key="`${index}-${row.name}-${row.type}-${row.valueMode}`"
                class="input-parameter-row"
                data-testid="input-parameter-row"
              >
                <a-input
                  :value="row.name"
                  aria-label="输入变量名"
                  placeholder="变量名"
                  @update:value="setInputParameterName(index, $event)"
                />
                <a-select :virtual="false"
                  :value="row.type"
                  aria-label="输入变量类型"
                  @update:value="setInputParameterType(index, $event)"
                >
                  <a-select-option
                    v-for="option in outputParameterTypeOptions"
                    :key="option"

                    :value="option"
                  >{{ variableTypeLabel(option) }}</a-select-option>
                </a-select>
                <div class="input-value-cell">
                  <div class="variable-value-combo" data-testid="input-variable-value-control">
                    <div class="variable-value-main">
                      <div
                        v-if="row.valueMode === 'reference' && inputReferenceSelection(String(row.value || ''))"
                        class="input-variable-chip"
                        data-testid="input-variable-chip"
                        role="button"
                        tabindex="0"
                        aria-label="输入变量引用"
                      >
                        <input
                          class="reference-value-proxy"
                          aria-label="输入引用变量"
                          :value="String(row.value || '')"
                          readonly
                          tabindex="-1"
                        />
                        <span class="input-variable-chip-main">
                          <strong>{{ inputReferenceSelection(String(row.value || ''))!.item.variable }}</strong>
                        </span>
                        <span class="variable-type-badge">{{ variableTypeLabel(inputReferenceSelection(String(row.value || ''))!.item.type) }}</span>
                        <button
                          type="button"
                          class="input-variable-clear"
                          aria-label="清除输入变量引用"
                          @click.stop="clearInputParameterReference(index)"
                        >
                          <span aria-hidden="true">×</span>
                        </button>
                      </div>
                      <select
                        v-else-if="row.type === 'boolean'"
                        class="variable-literal-select"
                        data-testid="input-variable-literal-input"
                        aria-label="输入变量值"
                        :value="String(row.value === true)"
                        @change="setInputParameterValue(index, ($event.target as HTMLSelectElement).value === 'true')"
                      >
                        <option value="true">true</option>
                        <option value="false">false</option>
                      </select>
                      <textarea
                        v-else-if="row.type === 'object' || row.type === 'array'"
                        class="variable-literal-input variable-literal-textarea"
                        data-testid="input-variable-literal-input"
                        aria-label="输入变量值"
                        :value="String(row.value ?? '')"
                        placeholder="输入或引用参数值"
                        rows="1"
                        @input="setInputParameterValue(index, ($event.target as HTMLTextAreaElement).value)"
                      ></textarea>
                      <input
                        v-else
                        class="variable-literal-input"
                        data-testid="input-variable-literal-input"
                        :type="row.type === 'number' ? 'number' : 'text'"
                        aria-label="输入变量值"
                        :value="String(row.value ?? '')"
                        placeholder="输入或引用参数值"
                        @input="setInputParameterValue(index, ($event.target as HTMLInputElement).value)"
                      />
                    </div>
                    <button
                      type="button"
                      class="variable-picker-trigger"
                      aria-label="选择输入变量"
                      @click="openInputVariablePicker(index, $event)"
                    >
                      <Connection aria-hidden="true" />
                    </button>
                  </div>
                  <div
                    v-if="activeInputParameterIndex === index"
                    class="variable-popover coze-variable-source-popover input-variable-popover"
                    data-testid="input-variable-picker"
                  >
                    <a-input v-model:value="inputVariableSearch" size="small" placeholder="搜索变量" />
                    <div class="variable-source-list coze-variable-source-list" data-testid="input-variable-source-list">
                      <button
                        v-for="group in filteredInputVariableGroups"
                        :key="variableGroupKey(group)"
                        type="button"
                        class="variable-source-item coze-variable-source-item"
                        :class="{ active: activeInputVariableGroupKey === variableGroupKey(group) }"
                        data-testid="input-variable-source-item"
                        @mouseenter="activateInputVariableGroup(group, $event)"
                        @click="activateInputVariableGroup(group, $event)"
                      >
                        <span class="variable-source-copy">
                          <strong>{{ group.title }}</strong>
                        </span>
                        <span v-if="group.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                      </button>
                    </div>
                    <div
                      v-if="activeInputVariableGroup"
                      class="variable-flyout"
                      :data-placement="variableFlyoutPlacement"
                      data-testid="input-variable-flyout"
                    >
                      <div class="variable-item-list" data-testid="input-variable-item-list">
                        <button
                          v-for="item in activeInputVariableGroup.items"
                          :key="item.reference"
                          type="button"
                          class="variable-option"
                          data-testid="input-variable-option"
                          @click="insertInputParameterReference(index, item.reference)"
                        >
                          <span class="variable-option-main">
                            <strong>{{ item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                        </button>
                        <p v-if="activeInputVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                      </div>
                    </div>
                  </div>
                </div>
                <button type="button" class="output-row-icon" aria-label="删除输入变量" @click="removeInputParameter(index)">
                  <XIcon aria-hidden="true" />
                </button>
              </div>
              <ul v-if="inputParameterErrors().length" class="output-parameter-errors">
                <li v-for="error in inputParameterErrors()" :key="error">{{ error }}</li>
              </ul>
            </div>
            <div
              v-else-if="field.type === 'output-parameters'"
              class="output-parameter-editor"
              data-testid="output-parameter-editor"
            >
              <div v-if="shouldShowOutputFormat()" class="output-format-row">
                <label>输出格式</label>
                <a-select :virtual="false"
                  :value="outputFormatValue()"
                  aria-label="输出格式"
                  @update:value="setOutputFormat"
                >
                  <a-select-option
                    v-for="option in outputFormatOptions"
                    :key="option"

                    :value="option"
                  >{{ option }}</a-select-option>
                </a-select>
              </div>
              <div
                class="output-column-row"
                :class="{ 'end-output-column-row': shouldEditOutputParameterValue() }"
              >
                <span>输出变量</span>
                <span>变量类型</span>
                <span v-if="shouldEditOutputParameterValue()">变量值</span>
                <button type="button" class="output-row-icon" aria-label="添加输出变量" @click="addOutputParameter">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in outputParameterRows()"
                :key="`${index}-${row.name}-${row.type}-${row.valueMode}-${row.value}`"
                class="output-parameter-row"
                :class="{ 'end-output-parameter-row': shouldEditOutputParameterValue() }"
                data-testid="output-parameter-row"
              >
                <a-input
                  :value="row.name"
                  aria-label="输出变量名"
                  placeholder="变量名"
                  @update:value="setOutputParameterName(index, $event)"
                />
                <a-select :virtual="false"
                  :value="row.type"
                  aria-label="输出变量类型"
                  @update:value="setOutputParameterType(index, $event)"
                >
                  <a-select-option
                    v-for="option in outputParameterTypeOptions"
                    :key="option"

                    :value="option"
                  >{{ outputParameterTypeLabel(option) }}</a-select-option>
                </a-select>
                <div v-if="shouldEditOutputParameterValue()" class="input-value-cell output-value-cell">
                  <div class="variable-value-combo" data-testid="output-variable-value-control">
                    <div class="variable-value-main">
                      <div
                        v-if="outputParameterValueMode(row) === 'reference' && outputReferenceSelection(outputParameterValue(row))"
                        class="input-variable-chip"
                        data-testid="output-variable-chip"
                        role="button"
                        tabindex="0"
                        aria-label="输出变量值引用"
                      >
                        <input
                          class="reference-value-proxy"
                          aria-label="输出变量值"
                          :value="outputParameterValue(row)"
                          readonly
                          tabindex="-1"
                        />
                        <span class="input-variable-chip-main">
                          <strong>{{ outputReferenceSelection(outputParameterValue(row))!.item.variable }}</strong>
                        </span>
                        <span class="variable-type-badge">{{ variableTypeLabel(outputReferenceSelection(outputParameterValue(row))!.item.type) }}</span>
                        <button
                          type="button"
                          class="input-variable-clear"
                          aria-label="清除输出变量值引用"
                          @click.stop="clearOutputParameterReference(index)"
                        >
                          <span aria-hidden="true">×</span>
                        </button>
                      </div>
                      <input
                        v-else
                        class="variable-literal-input"
                        data-testid="output-variable-literal-input"
                        aria-label="输出变量值"
                        :value="outputParameterValue(row)"
                        placeholder="输入或引用变量值"
                        @input="setOutputParameterValue(index, ($event.target as HTMLInputElement).value)"
                      />
                    </div>
                    <button
                      type="button"
                      class="variable-picker-trigger"
                      aria-label="选择输出变量值"
                      @click="openOutputVariablePicker(index, $event)"
                    >
                      <Connection aria-hidden="true" />
                    </button>
                  </div>
                  <div
                    v-if="activeOutputParameterIndex === index"
                    class="variable-popover coze-variable-source-popover input-variable-popover"
                    data-testid="output-variable-picker"
                  >
                    <a-input v-model:value="outputVariableSearch" size="small" placeholder="搜索变量" />
                    <div class="variable-source-list coze-variable-source-list" data-testid="output-variable-source-list">
                      <button
                        v-for="group in filteredOutputVariableGroups"
                        :key="variableGroupKey(group)"
                        type="button"
                        class="variable-source-item coze-variable-source-item"
                        :class="{ active: activeOutputVariableGroupKey === variableGroupKey(group) }"
                        data-testid="output-variable-source-item"
                        @mouseenter="activateOutputVariableGroup(group, $event)"
                        @click="activateOutputVariableGroup(group, $event)"
                      >
                        <span class="variable-source-copy">
                          <strong>{{ group.title }}</strong>
                        </span>
                        <span v-if="group.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                      </button>
                    </div>
                    <div
                      v-if="activeOutputVariableGroup"
                      class="variable-flyout"
                      :data-placement="variableFlyoutPlacement"
                      data-testid="output-variable-flyout"
                    >
                      <div class="variable-item-list" data-testid="output-variable-item-list">
                        <button
                          v-for="item in activeOutputVariableGroup.items"
                          :key="item.reference"
                          type="button"
                          class="variable-option"
                          data-testid="output-variable-option"
                          @click="insertOutputParameterReference(index, item.reference)"
                        >
                          <span class="variable-option-main">
                            <strong>{{ item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                        </button>
                        <p v-if="activeOutputVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                      </div>
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  class="output-row-icon"
                  aria-label="删除输出变量"
                  :disabled="!canRemoveOutputParameter()"
                  @click="removeOutputParameter(index)"
                >
                  <XIcon aria-hidden="true" />
                </button>
              </div>
              <ul v-if="outputParameterErrors().length" class="output-parameter-errors">
                <li v-for="error in outputParameterErrors()" :key="error">{{ error }}</li>
              </ul>
            </div>
            <div
              v-else-if="field.type === 'aggregation-output-summary'"
              class="aggregation-output-summary"
              data-testid="aggregation-output-summary"
            >
              <div
                v-for="row in aggregationOutputSummaryRows()"
                :key="row.name"
                class="aggregation-output-row"
                data-testid="aggregation-output-row"
              >
                <strong>{{ row.name }}</strong>
                <span class="variable-type-badge">{{ variableListTypeLabel(row.type) }}</span>
              </div>
            </div>
            <div
              v-else-if="field.type === 'end-answer-content'"
              class="end-answer-content-editor"
              data-testid="end-answer-content-editor"
            >
              <template v-if="endReturnMode() === 'text'">
                <div class="end-response-heading">
                  <label>回答内容</label>
                  <div class="end-response-actions">
                    <label class="end-stream-switch">
                      <span>流式输出</span>
                      <a-switch
                        :checked="switchFieldValue('streamOutput')"
                        aria-label="流式输出"
                        @update:checked="setSwitchFieldValue('streamOutput', $event)"
                      />
                    </label>
                  </div>
                </div>
                <a-textarea
                  class="end-response-textarea"
                  :value="String(fieldValue('output') || '')"
                  aria-label="回答内容"
                  placeholder="返回给调用方的文本，可使用变量引用"
                  :rows="5"
                  @update:value="handleVariableFieldInput('output', $event)"
                />
                <div
                  v-if="activeVariableField === 'output'"
                  class="inline-variable-suggestion-popover end-variable-popover"
                  data-testid="variable-picker"
                  data-picker-kind="inline"
                >
                  <a-input v-model:value="variableSearch" size="small" placeholder="搜索变量" />
                  <div class="inline-variable-list" data-testid="inline-variable-list">
                    <button
                      v-for="option in inlineVariableOptions"
                      :key="`${option.groupKey}:${option.item.reference}`"
                      type="button"
                      class="inline-variable-option"
                      data-testid="variable-option"
                      @click="insertVariable('output', option.item.reference)"
                    >
                      <span class="variable-option-main">
                        <strong>{{ option.item.variable }}</strong>
                      </span>
                      <span class="variable-type-badge">{{ variableListTypeLabel(option.item.type) }}</span>
                    </button>
                    <p v-if="inlineVariableOptions.length === 0" class="variable-empty">暂无可引用变量</p>
                  </div>
                </div>
              </template>
            </div>
            <label
              v-else-if="field.type === 'switch'"
              class="switch-field-row"
            >
              <span>{{ field.label }}</span>
              <a-switch
                :checked="switchFieldValue(field.key)"
                :aria-label="field.label"
                @update:checked="setSwitchFieldValue(field.key, $event)"
              />
            </label>
            <a-textarea
              v-else-if="field.type === 'textarea'"
              :value="fieldValue(field.key)"
              :placeholder="field.placeholder"
              :rows="5"
              @update:value="handleVariableFieldInput(field.key, $event)"
            />
            <div
              v-else-if="field.type === 'code-editor'"
              class="code-editor-field"
              data-testid="code-editor-field"
            >
              <div class="code-editor-toolbar">
                <span>{{ codeTemplateLanguageLabel() }}</span>
                <button type="button" class="soft-icon-button" @click="insertCodeTemplate">
                  插入基础模板
                </button>
              </div>
              <a-textarea
                class="code-editor-input"
                :value="fieldValue(field.key)"
                :placeholder="field.placeholder"
                :rows="12"
                @update:value="setFieldValue(field.key, $event)"
              />
            </div>
            <a-input-number
              v-else-if="field.type === 'number'"
              :value="Number(fieldValue(field.key) || 0)"
              :min="field.min ?? 0"
              :max="field.max ?? 100000"
              :step="field.step ?? 1"
              @update:value="setFieldValue(field.key, $event)"
            />
            <div
              v-else-if="field.type === 'resource-adapter-badge'"
              class="resource-adapter-badge"
              data-testid="resource-adapter-badge"
            >
              <span>{{ selectedResourceAdapterLabel() }}</span>
              <small>{{ selectedResourceStatusText() }}</small>
            </div>
            <div
              v-else-if="field.type === 'schema-input-mappings'"
              class="schema-input-mapping-editor"
              data-testid="schema-input-mapping-editor"
            >
              <div class="schema-input-mapping-header">
                <span>参数名</span>
                <span>参数类型</span>
                <span>参数值</span>
              </div>
              <div
                v-for="(row, index) in schemaInputMappingRows()"
                :key="`${index}-${row.name}-${row.type}`"
                class="schema-input-mapping-row"
                data-testid="schema-input-mapping-row"
              >
                <div class="schema-param-name">
                  <strong>{{ row.name }}</strong>
                  <small v-if="row.required">必填</small>
                </div>
                <span class="variable-type-badge">{{ variableTypeLabel(row.type) }}</span>
                <div class="input-value-cell">
                  <div v-if="row.valueMode === 'reference'" class="input-reference-control">
                    <button
                      v-if="!inputReferenceSelection(String(row.value || ''))"
                      type="button"
                      class="input-variable-empty"
                      data-testid="schema-input-variable-empty"
                      aria-label="选择参数引用变量"
                      @click="openSchemaInputVariablePicker(index, $event)"
                    >
                      <input
                        class="reference-value-proxy"
                        aria-label="参数引用变量"
                        :value="String(row.value || '')"
                        readonly
                        tabindex="-1"
                      />
                      <span>选择变量</span>
                      <Connection aria-hidden="true" />
                    </button>
                    <div
                      v-else
                      class="input-variable-chip"
                      data-testid="schema-input-variable-chip"
                      role="button"
                      tabindex="0"
                      aria-label="参数变量引用"
                      @click="openSchemaInputVariablePicker(index, $event)"
                      @keydown.enter.prevent="openSchemaInputVariablePicker(index)"
                      @keydown.space.prevent="openSchemaInputVariablePicker(index)"
                    >
                      <input
                        class="reference-value-proxy"
                        aria-label="参数引用变量"
                        :value="String(row.value || '')"
                        readonly
                        tabindex="-1"
                      />
                      <span class="input-variable-chip-main">
                        <strong>{{ inputReferenceSelection(String(row.value || ''))!.item.variable }}</strong>
                      </span>
                      <span class="variable-type-badge">{{ variableTypeLabel(inputReferenceSelection(String(row.value || ''))!.item.type) }}</span>
                      <button
                        type="button"
                        class="input-variable-clear"
                        aria-label="清除参数变量引用"
                        @click.stop="clearSchemaInputMappingReference(index)"
                      >
                        <span aria-hidden="true">×</span>
                      </button>
                    </div>
                  </div>
                  <a-input-number
                    v-else-if="row.type === 'number'"
                    :value="Number(row.value || 0)"
                    aria-label="参数值"
                    @update:value="setSchemaInputMappingValue(index, $event)"
                  />
                  <a-select :virtual="false"
                    v-else-if="row.type === 'boolean'"
                    :value="String(row.value === true)"
                    aria-label="参数值"
                    @update:value="setSchemaInputMappingValue(index, $event === 'true')"
                  >
                    <a-select-option value="true" >true</a-select-option>
                    <a-select-option value="false" >false</a-select-option>
                  </a-select>
                  <a-input
                    v-else
                    :value="String(row.value ?? '')"
                    :type="row.type === 'object' || row.type === 'array' ? 'textarea' : 'text'"
                    :rows="2"
                    :placeholder="row.description || '输入或引用参数值'"
                    aria-label="参数值"
                    @update:value="setSchemaInputMappingValue(index, $event)"
                  />
                  <button
                    v-if="row.valueMode !== 'reference'"
                    type="button"
                    class="input-reference-shortcut output-row-icon"
                    aria-label="选择参数引用变量"
                    @click="openSchemaInputVariablePicker(index, $event)"
                  >
                    <Connection aria-hidden="true" />
                  </button>
                  <div
                    v-if="activeSchemaInputMappingIndex === index"
                    class="variable-popover coze-variable-source-popover input-variable-popover"
                    data-testid="schema-input-variable-picker"
                  >
                    <a-input v-model:value="schemaVariableSearch" size="small" placeholder="搜索变量" />
                    <div class="variable-source-list coze-variable-source-list" data-testid="schema-input-variable-source-list">
                      <button
                        v-for="group in filteredSchemaVariableGroups"
                        :key="variableGroupKey(group)"
                        type="button"
                        class="variable-source-item coze-variable-source-item"
                        :class="{ active: activeSchemaVariableGroupKey === variableGroupKey(group) }"
                        data-testid="schema-input-variable-source-item"
                        @mouseenter="activateSchemaVariableGroup(group, $event)"
                        @click="activateSchemaVariableGroup(group, $event)"
                      >
                        <span class="variable-source-copy">
                          <strong>{{ group.title }}</strong>
                        </span>
                        <span v-if="group.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                      </button>
                    </div>
                    <div
                      v-if="activeSchemaVariableGroup"
                      class="variable-flyout"
                      :data-placement="variableFlyoutPlacement"
                      data-testid="schema-input-variable-flyout"
                    >
                      <div class="variable-item-list" data-testid="schema-input-variable-item-list">
                        <button
                          v-for="item in activeSchemaVariableGroup.items"
                          :key="item.reference"
                          type="button"
                          class="variable-option"
                          data-testid="schema-input-variable-option"
                          @click="insertSchemaInputMappingReference(index, item.reference)"
                        >
                          <span class="variable-option-main">
                            <strong>{{ item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                        </button>
                        <p v-if="activeSchemaVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-if="schemaInputMappingRows().length === 0" class="secondary-empty">
                选择资源后，将按资源输入 Schema 生成参数行。
              </p>
            </div>
            <dl
              v-else-if="field.type === 'legacy-resource-debug'"
              class="legacy-resource-debug"
              data-testid="legacy-resource-debug"
            >
              <div v-for="row in legacyResourceDebugRows()" :key="row.label">
                <dt>{{ row.label }}</dt>
                <dd>{{ row.value }}</dd>
              </div>
              <p v-if="legacyResourceDebugRows().length === 0" class="secondary-empty">暂无兼容数据</p>
            </dl>
            <div
              v-else-if="field.type === 'json-field-mappings'"
              class="structured-row-editor"
              data-testid="json-field-mapping-editor"
            >
              <div class="json-field-mapping-header">
                <span>输出变量</span>
                <span>JSONPath</span>
                <span>变量类型</span>
                <button type="button" class="output-row-icon" aria-label="添加字段映射" @click="addJsonFieldMapping">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in jsonFieldMappingRows()"
                :key="`${index}-${row.name}-${row.path}`"
                class="json-field-mapping-row"
                data-testid="json-field-mapping-row"
              >
                <a-input
                  :value="row.name"
                  aria-label="映射输出变量"
                  placeholder="order_id"
                  @update:value="setJsonFieldMappingName(index, $event)"
                />
                <a-input
                  :value="row.path"
                  aria-label="JSONPath"
                  placeholder="$.order.id"
                  @update:value="setJsonFieldMappingPath(index, $event)"
                />
                <a-select :virtual="false"
                  :value="row.type"
                  aria-label="字段变量类型"
                  @update:value="setJsonFieldMappingType(index, $event)"
                >
                  <a-select-option
                    v-for="option in outputParameterTypeOptions"
                    :key="option"

                    :value="option"
                  >{{ variableTypeLabel(option) }}</a-select-option>
                </a-select>
                <button type="button" class="output-row-icon" aria-label="删除字段映射" @click="removeJsonFieldMapping(index)">
                  <XIcon aria-hidden="true" />
                </button>
              </div>
              <p v-if="jsonFieldMappingRows().length === 0" class="secondary-empty">
                添加字段后，将从 JSON 来源中按路径提取输出变量。
              </p>
            </div>
            <div
              v-else-if="field.type === 'aggregation-groups'"
              class="aggregation-group-editor"
              data-testid="aggregation-group-editor"
            >
              <article
                v-for="(group, groupIndex) in aggregationGroupRows()"
                :key="groupIndex"
                class="aggregation-group-card"
                data-testid="aggregation-group-card"
              >
                <header class="aggregation-group-header">
                  <span class="aggregation-group-title">
                    <input
                      v-if="editingAggregationGroupNameIndex === groupIndex"
                      class="aggregation-group-name-input"
                      data-testid="aggregation-group-name-editor"
                      :value="aggregationGroupNameDraft"
                      aria-label="聚合分组名"
                      placeholder="Group1"
                      @input="aggregationGroupNameDraft = ($event.target as HTMLInputElement).value"
                      @keydown.enter.prevent="commitAggregationGroupNameEdit(groupIndex)"
                      @keydown.escape.prevent="cancelAggregationGroupNameEdit"
                      @blur="commitAggregationGroupNameEdit(groupIndex)"
                    />
                    <button
                      v-else
                      type="button"
                      class="aggregation-group-name-display"
                      data-testid="aggregation-group-name-display"
                      :aria-label="`编辑聚合分组名 ${group.name}`"
                      @click="beginAggregationGroupNameEdit(groupIndex, group.name)"
                    >
                      {{ group.name }}
                    </button>
                    <span class="variable-type-badge aggregation-group-type">{{ variableListTypeLabel(aggregationGroupResolvedType(group)) }}</span>
                    <span v-if="group.variables.some((item) => item.valueMode === 'reference' || String(item.value || '').trim())" class="aggregation-group-info" aria-label="变量聚合分组说明">i</span>
                  </span>
                  <button
                    type="button"
                    class="output-row-icon"
                    aria-label="删除聚合分组"
                    :disabled="aggregationGroupRows().length <= 1"
                    @click="removeAggregationGroup(groupIndex)"
                  >
                    <XIcon aria-hidden="true" />
                  </button>
                </header>
                <div class="aggregation-group-variable-list">
                  <div
                    v-for="(variable, variableIndex) in group.variables"
                    :key="`${groupIndex}-${variableIndex}-${variable.valueMode}`"
                    class="aggregation-group-variable-row"
                    data-testid="aggregation-group-variable-row"
                  >
                    <span class="aggregation-row-handle" aria-hidden="true">⋮⋮</span>
                    <div class="input-value-cell">
                      <div class="variable-value-combo structured-value-control" data-testid="structured-value-control">
                        <div class="variable-value-main">
                          <div
                            v-if="variable.valueMode === 'reference' && inputReferenceSelection(String(variable.value || ''))"
                            class="input-variable-chip"
                            data-testid="aggregation-variable-chip"
                          >
                            <input class="reference-value-proxy" aria-label="聚合引用变量" :value="String(variable.value || '')" readonly tabindex="-1" />
                            <span class="input-variable-chip-main">
                              <strong>{{ inputReferenceSelection(String(variable.value || ''))!.item.variable }}</strong>
                            </span>
                            <span class="variable-type-badge">{{ variableListTypeLabel(inputReferenceSelection(String(variable.value || ''))!.item.type) }}</span>
                            <button
                              type="button"
                              class="input-variable-clear"
                              aria-label="清除聚合变量引用"
                              @click.stop="clearAggregationGroupVariableReference(groupIndex, variableIndex)"
                            >
                              <span aria-hidden="true">×</span>
                            </button>
                          </div>
                          <input
                            v-else
                            class="variable-literal-input"
                            data-testid="aggregation-variable-literal-input"
                            type="text"
                            aria-label="聚合变量值"
                            :value="String(variable.value ?? '')"
                            placeholder="输入或引用变量"
                            @input="setAggregationGroupVariableValue(groupIndex, variableIndex, ($event.target as HTMLInputElement).value)"
                          />
                        </div>
                        <button
                          type="button"
                          class="variable-picker-trigger"
                          aria-label="选择聚合变量"
                          @click="openStructuredVariablePicker(`aggregation:${groupIndex}:${variableIndex}`, $event)"
                        >
                          <Connection aria-hidden="true" />
                        </button>
                      </div>
                      <div
                        v-if="activeStructuredVariableTarget === `aggregation:${groupIndex}:${variableIndex}`"
                        class="variable-popover coze-variable-source-popover input-variable-popover"
                        data-testid="structured-variable-picker"
                      >
                        <a-input v-model:value="structuredVariableSearch" size="small" placeholder="搜索变量" />
                        <div class="variable-source-list coze-variable-source-list" data-testid="structured-variable-source-list">
                          <button
                            v-for="sourceGroup in filteredStructuredVariableGroups"
                            :key="variableGroupKey(sourceGroup)"
                            type="button"
                            class="variable-source-item coze-variable-source-item"
                            :class="{ active: activeStructuredVariableGroupKey === variableGroupKey(sourceGroup) }"
                            data-testid="structured-variable-source-item"
                            @mouseenter="activateStructuredVariableGroup(sourceGroup, $event)"
                            @click="activateStructuredVariableGroup(sourceGroup, $event)"
                          >
                            <span class="variable-source-copy">
                              <strong>{{ sourceGroup.title }}</strong>
                            </span>
                            <span v-if="sourceGroup.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                          </button>
                        </div>
                        <div
                          v-if="activeStructuredVariableGroup"
                          class="variable-flyout"
                          :data-placement="variableFlyoutPlacement"
                          data-testid="structured-variable-flyout"
                        >
                          <div class="variable-item-list" data-testid="structured-variable-item-list">
                            <button
                              v-for="item in activeStructuredVariableGroup.items"
                              :key="item.reference"
                              type="button"
                              class="variable-option"
                              data-testid="structured-variable-option"
                              @click="insertStructuredVariableReference(`aggregation:${groupIndex}:${variableIndex}`, item.reference)"
                            >
                              <span class="variable-option-main">
                                <strong>{{ item.variable }}</strong>
                              </span>
                              <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                            </button>
                            <p v-if="activeStructuredVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                          </div>
                        </div>
                      </div>
                    </div>
                    <button type="button" class="output-row-icon" aria-label="删除聚合变量" @click="removeAggregationGroupVariable(groupIndex, variableIndex)">
                      <XIcon aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </article>
              <button type="button" class="aggregation-add-group" aria-label="新增分组" @click="addAggregationGroup">
                <LucidePlus aria-hidden="true" />
                新增分组
              </button>
            </div>
            <div
              v-else-if="field.type === 'aggregation-sources'"
              class="structured-row-editor"
              data-testid="aggregation-source-editor"
            >
              <div class="aggregation-source-header">
                <span>来源名</span>
                <span>来源值</span>
                <button type="button" class="output-row-icon" aria-label="添加聚合来源" @click="addAggregationSource">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in aggregationSourceRows()"
                :key="`${index}-${row.name}-${row.valueMode}`"
                class="aggregation-source-row"
                data-testid="aggregation-source-row"
              >
                <a-input
                  :value="row.name"
                  aria-label="聚合来源名"
                  placeholder="primary"
                  @update:value="setAggregationSourceName(index, $event)"
                />
                <div class="input-value-cell">
                  <div class="variable-value-combo structured-value-control" data-testid="structured-value-control">
                    <div class="variable-value-main">
                      <div
                        v-if="row.valueMode === 'reference' && inputReferenceSelection(String(row.value || ''))"
                        class="input-variable-chip"
                        data-testid="aggregation-variable-chip"
                      >
                        <input class="reference-value-proxy" aria-label="聚合引用变量" :value="String(row.value || '')" readonly tabindex="-1" />
                        <span class="input-variable-chip-main">
                          <strong>{{ inputReferenceSelection(String(row.value || ''))!.item.variable }}</strong>
                        </span>
                        <span class="variable-type-badge">{{ variableTypeLabel(inputReferenceSelection(String(row.value || ''))!.item.type) }}</span>
                        <button type="button" class="input-variable-clear" aria-label="清除聚合来源变量引用" @click.stop="clearAggregationSourceReference(index)">
                          <span aria-hidden="true">×</span>
                        </button>
                      </div>
                      <input
                        v-else
                        class="variable-literal-input"
                        data-testid="aggregation-variable-literal-input"
                        type="text"
                        aria-label="聚合来源值"
                        :value="String(row.value ?? '')"
                        placeholder="输入或引用来源值"
                        @input="setAggregationSourceValue(index, ($event.target as HTMLInputElement).value)"
                      />
                    </div>
                    <button
                      type="button"
                      class="variable-picker-trigger"
                      aria-label="选择聚合来源变量"
                      @click="openStructuredVariablePicker(`aggregation:${index}`, $event)"
                    >
                      <Connection aria-hidden="true" />
                    </button>
                  </div>
                  <div
                    v-if="activeStructuredVariableTarget === `aggregation:${index}`"
                    class="variable-popover coze-variable-source-popover input-variable-popover"
                    data-testid="structured-variable-picker"
                  >
                    <a-input v-model:value="structuredVariableSearch" size="small" placeholder="搜索变量" />
                    <div class="variable-source-list coze-variable-source-list" data-testid="structured-variable-source-list">
                      <button
                        v-for="group in filteredStructuredVariableGroups"
                        :key="variableGroupKey(group)"
                        type="button"
                        class="variable-source-item coze-variable-source-item"
                        :class="{ active: activeStructuredVariableGroupKey === variableGroupKey(group) }"
                        data-testid="structured-variable-source-item"
                        @mouseenter="activateStructuredVariableGroup(group, $event)"
                        @click="activateStructuredVariableGroup(group, $event)"
                      >
                        <span class="variable-source-copy">
                          <strong>{{ group.title }}</strong>
                        </span>
                        <span v-if="group.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                      </button>
                    </div>
                    <div
                      v-if="activeStructuredVariableGroup"
                      class="variable-flyout"
                      :data-placement="variableFlyoutPlacement"
                      data-testid="structured-variable-flyout"
                    >
                      <div class="variable-item-list" data-testid="structured-variable-item-list">
                        <button
                          v-for="item in activeStructuredVariableGroup.items"
                          :key="item.reference"
                          type="button"
                          class="variable-option"
                          data-testid="structured-variable-option"
                          @click="insertStructuredVariableReference(`aggregation:${index}`, item.reference)"
                        >
                          <span class="variable-option-main">
                            <strong>{{ item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                        </button>
                        <p v-if="activeStructuredVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                      </div>
                    </div>
                  </div>
                </div>
                <button type="button" class="output-row-icon" aria-label="删除聚合来源" @click="removeAggregationSource(index)">
                  <XIcon aria-hidden="true" />
                </button>
              </div>
            </div>
            <div
              v-else-if="field.type === 'variable-assignment'"
              class="variable-assignment-editor"
              data-testid="variable-assignment-editor"
            >
              <div class="variable-assignment-header">
                <span>变量名称</span>
                <span>值</span>
              </div>
              <div class="variable-assignment-row" data-testid="variable-assignment-row">
                <div class="input-value-cell assignment-target-cell">
                  <div class="variable-value-combo assignment-target-control" data-testid="assignment-target-control">
                    <div class="variable-value-main">
                      <input
                        class="variable-literal-input"
                        data-testid="assignment-target-input"
                        type="text"
                        aria-label="变量名称"
                        :value="variableAssignmentTargetReference()"
                        placeholder="选择写入变量"
                        readonly
                        @click="openVariableAssignmentTargetPicker($event)"
                      />
                    </div>
                    <button
                      type="button"
                      class="variable-picker-trigger"
                      aria-label="选择写入变量"
                      @click="openVariableAssignmentTargetPicker($event)"
                    >
                      <Connection aria-hidden="true" />
                    </button>
                  </div>
                  <div
                    v-if="activeVariableAssignmentTargetPicker"
                    class="variable-popover coze-variable-source-popover input-variable-popover"
                    data-testid="assignment-target-picker"
                  >
                    <a-input v-model:value="variableAssignmentTargetSearch" size="small" placeholder="搜索变量" />
                    <div class="variable-source-list coze-variable-source-list" data-testid="assignment-target-source-list">
                      <button
                        v-for="group in filteredVariableAssignmentTargetGroups"
                        :key="group.key"
                        type="button"
                        class="variable-source-item coze-variable-source-item"
                        :class="{ active: activeVariableAssignmentTargetGroupKey === group.key }"
                        data-testid="assignment-target-source-item"
                        @mouseenter="activateVariableAssignmentTargetGroup(group, $event)"
                        @click="activateVariableAssignmentTargetGroup(group, $event)"
                      >
                        <span class="variable-source-copy">
                          <strong>{{ group.title }}</strong>
                        </span>
                        <span v-if="group.items.length > 0" class="variable-source-arrow" aria-hidden="true">›</span>
                      </button>
                    </div>
                    <div
                      v-if="activeVariableAssignmentTargetGroup"
                      class="variable-flyout"
                      :data-placement="variableFlyoutPlacement"
                      data-testid="assignment-target-flyout"
                    >
                      <div class="variable-item-list" data-testid="assignment-target-item-list">
                        <button
                          v-for="item in activeVariableAssignmentTargetGroup.items"
                          :key="item.reference"
                          type="button"
                          class="variable-option"
                          data-testid="assignment-target-option"
                          @click="selectVariableAssignmentTarget(item)"
                        >
                          <span class="variable-option-main">
                            <strong>{{ item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                        </button>
                        <p v-if="activeVariableAssignmentTargetGroup.items.length === 0" class="variable-empty">暂无可写变量</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="input-value-cell assignment-value-cell">
                  <div class="variable-value-combo assignment-value-control" data-testid="assignment-value-control">
                    <div class="variable-value-main">
                      <div
                        v-if="variableAssignmentSourceType() === 'reference' && inputReferenceSelection(String(fieldValue('source') || ''))"
                        class="input-variable-chip"
                        data-testid="assignment-variable-chip"
                      >
                        <input class="reference-value-proxy" aria-label="赋值引用变量" :value="String(fieldValue('source') || '')" readonly tabindex="-1" />
                        <span class="input-variable-chip-main">
                          <strong>{{ inputReferenceSelection(String(fieldValue('source') || ''))!.item.variable }}</strong>
                        </span>
                        <span class="variable-type-badge">{{ variableTypeLabel(inputReferenceSelection(String(fieldValue('source') || ''))!.item.type) }}</span>
                        <button type="button" class="input-variable-clear" aria-label="清除赋值内容变量引用" @click.stop="clearVariableAssignmentReference">
                          <span aria-hidden="true">×</span>
                        </button>
                      </div>
                      <input
                        v-else
                        class="variable-literal-input"
                        data-testid="assignment-variable-literal-input"
                        type="text"
                        aria-label="赋值内容"
                        :value="String(fieldValue('source') ?? '')"
                        placeholder="输入或引用参数值"
                        @input="setVariableAssignmentSourceValue(($event.target as HTMLInputElement).value)"
                      />
                    </div>
                    <button
                      type="button"
                      class="variable-picker-trigger"
                      aria-label="选择赋值内容变量"
                      @click="openStructuredVariablePicker('assignment', $event)"
                    >
                      <Connection aria-hidden="true" />
                    </button>
                  </div>
                  <div
                    v-if="activeStructuredVariableTarget === 'assignment'"
                    class="variable-popover coze-variable-source-popover input-variable-popover"
                    data-testid="structured-variable-picker"
                  >
                    <a-input v-model:value="structuredVariableSearch" size="small" placeholder="搜索变量" />
                    <div class="variable-source-list coze-variable-source-list" data-testid="structured-variable-source-list">
                      <button
                        v-for="group in filteredStructuredVariableGroups"
                        :key="variableGroupKey(group)"
                        type="button"
                        class="variable-source-item coze-variable-source-item"
                        :class="{ active: activeStructuredVariableGroupKey === variableGroupKey(group) }"
                        data-testid="structured-variable-source-item"
                        @mouseenter="activateStructuredVariableGroup(group, $event)"
                        @click="activateStructuredVariableGroup(group, $event)"
                      >
                        <span class="variable-source-copy">
                          <strong>{{ group.title }}</strong>
                        </span>
                        <span v-if="group.items.length > 0" class="variable-source-arrow" data-testid="variable-source-arrow" aria-hidden="true">›</span>
                      </button>
                    </div>
                    <div
                      v-if="activeStructuredVariableGroup"
                      class="variable-flyout"
                      :data-placement="variableFlyoutPlacement"
                      data-testid="structured-variable-flyout"
                    >
                      <div class="variable-item-list" data-testid="structured-variable-item-list">
                        <button
                          v-for="item in activeStructuredVariableGroup.items"
                          :key="item.reference"
                          type="button"
                          class="variable-option"
                          data-testid="structured-variable-option"
                          @click="insertStructuredVariableReference('assignment', item.reference)"
                        >
                          <span class="variable-option-main">
                            <strong>{{ item.variable }}</strong>
                          </span>
                          <span class="variable-type-badge">{{ variableListTypeLabel(item.type) }}</span>
                        </button>
                        <p v-if="activeStructuredVariableGroup.items.length === 0" class="variable-empty">暂无可引用变量</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div
              v-else-if="field.type === 'human-input-schema'"
              class="structured-row-editor"
              data-testid="human-input-schema-editor"
            >
              <div class="human-input-schema-header">
                <span>字段名</span>
                <span>类型</span>
                <span>必填</span>
                <span>说明</span>
                <button type="button" class="output-row-icon" aria-label="添加人工输入字段" @click="addHumanInputSchemaField">
                  <LucidePlus aria-hidden="true" />
                </button>
              </div>
              <div
                v-for="(row, index) in humanInputSchemaRows()"
                :key="`${index}-${row.name}-${row.type}`"
                class="human-input-schema-row"
                data-testid="human-input-schema-row"
              >
                <a-input :value="row.name" aria-label="人工输入字段名" placeholder="approved" @update:value="setHumanInputSchemaName(index, $event)" />
                <a-select :virtual="false" :value="row.type" aria-label="人工输入字段类型" @update:value="setHumanInputSchemaType(index, $event)">
                  <a-select-option v-for="option in outputParameterTypeOptions" :key="option" :value="option" >{{ variableTypeLabel(option) }}</a-select-option>
                </a-select>
                <a-switch :checked="row.required" aria-label="人工输入字段必填" @update:checked="setHumanInputSchemaRequired(index, $event)" />
                <a-input :value="row.description" aria-label="人工输入字段说明" placeholder="字段说明" @update:value="setHumanInputSchemaDescription(index, $event)" />
                <button type="button" class="output-row-icon" aria-label="删除人工输入字段" @click="removeHumanInputSchemaField(index)">
                  <XIcon aria-hidden="true" />
                </button>
              </div>
              <p v-if="humanInputSchemaRows().length === 0" class="secondary-empty">
                添加字段后，人工处理者将按结构提交恢复数据。
              </p>
            </div>
            <a-select :virtual="false"
              v-else-if="field.type === 'resource-select'"
              :value="String(fieldValue(field.key) || '')"
              show-search
              data-testid="tool-call-resource-select"
              :placeholder="field.placeholder"
              @update:value="selectWorkflowResource(field, $event)"
            >
              <a-select-option
                v-for="resource in workflowResourceOptions(field.resourceTypes || [])"
                :key="resource.resourceId"

                :value="resource.resourceId"
                :disabled="!isResourceSelectable(resource)"
              >
                <span class="tool-resource-option">
                  <strong>{{ resource.displayName }}</strong>
                  <small>{{ resource.resourceType }} · {{ resource.resourceId }} · {{ resourceStatusLabel(resource) }}</small>
                </span>
              </a-select-option>
            </a-select>
            <a-select :virtual="false"
              v-else-if="field.type === 'select'"
              :value="fieldValue(field.key) || field.options?.[0]"
              @update:value="setFieldValue(field.key, $event)"
            >
              <a-select-option v-for="option in field.options || []" :key="option" :value="option" >{{ selectOptionLabel(field.key, option) }}</a-select-option>
            </a-select>
            <a-input
              v-else
              :value="fieldValue(field.key)"
              :placeholder="field.placeholder"
              @update:value="handleVariableFieldInput(field.key, $event)"
            />
            <div
              v-if="activeVariableField === field.key"
              class="inline-variable-suggestion-popover"
              data-testid="variable-picker"
              data-picker-kind="inline"
            >
              <a-input v-model:value="variableSearch" size="small" placeholder="搜索变量" />
              <div class="inline-variable-list" data-testid="inline-variable-list">
                <button
                  v-for="option in inlineVariableOptions"
                  :key="`${option.groupKey}:${option.item.reference}`"
                  type="button"
                  class="inline-variable-option"
                  data-testid="variable-option"
                  @click="insertVariable(field.key, option.item.reference)"
                >
                  <span class="variable-option-main">
                    <strong>{{ option.item.variable }}</strong>
                  </span>
                  <span class="variable-type-badge">{{ variableListTypeLabel(option.item.type) }}</span>
                </button>
                <p v-if="inlineVariableOptions.length === 0" class="variable-empty">暂无可引用变量</p>
              </div>
            </div>
          </div>
          </div>
        </section>

        <section
          v-if="isApiOrToolGovernanceNode()"
          class="config-section"
          data-testid="resource-governance-section"
        >
          <div class="section-title">
            <span>G</span>
            调用治理
          </div>
          <div class="llm-resource-fields" data-testid="resource-governance-fields">
            <label v-if="selectedNode.type === 'API_CALL'">
              认证策略
              <a-select :virtual="false"
                :value="String(fieldValue('authMode') || 'none')"
                aria-label="认证策略"
                @update:value="setFieldValue('authMode', $event)"
              >
                <a-select-option value="none">none</a-select-option>
                <a-select-option value="bearer">bearer</a-select-option>
                <a-select-option value="api_key">api_key</a-select-option>
                <a-select-option value="basic">basic</a-select-option>
              </a-select>
            </label>
            <label>
              超时毫秒
              <a-input-number
                :value="resourceGovernanceNumberValue('timeoutMs', 'timeout')"
                :min="100"
                :max="120000"
                :step="100"
                aria-label="超时毫秒"
                @update:value="setResourceGovernanceNumber('timeoutMs', $event ?? 0)"
              />
            </label>
            <label>
              重试次数
              <a-input-number
                :value="resourceGovernanceNumberValue('retryCount')"
                :min="0"
                :max="5"
                :step="1"
                aria-label="重试次数"
                @update:value="setResourceGovernanceNumber('retryCount', $event ?? 0)"
              />
            </label>
            <label>
              错误行为
              <a-select :virtual="false"
                :value="String(fieldValue('errorBehavior') || 'fail')"
                aria-label="错误行为"
                @update:value="setFieldValue('errorBehavior', $event)"
              >
                <a-select-option value="fail">fail</a-select-option>
                <a-select-option value="continue">continue</a-select-option>
                <a-select-option value="branch">branch</a-select-option>
              </a-select>
            </label>
            <label>
              输出 Schema
              <a-textarea
                :value="resourceOutputSchemaText()"
                aria-label="输出 Schema"
                :rows="3"
                placeholder='{"type":"object","properties":{"result":{"type":"string"}}}'
                @update:value="setResourceOutputSchema"
              />
            </label>
            <label>
              敏感 Header
              <a-input
                :value="resourceSensitiveHeadersText()"
                aria-label="敏感 Header"
                placeholder="Authorization, X-API-Key"
                @update:value="setResourceSensitiveHeaders"
              />
            </label>
          </div>
        </section>
      </aside>

      <aside v-if="nodeTestDrawerOpen && nodeTestTarget" class="node-test-drawer" data-testid="node-test-drawer">
        <div class="node-test-header">
          <div class="node-test-header-title">
            <h3>试运行</h3>
            <span>{{ nodeTestTarget.name || nodeTestTarget.nodeKey }}</span>
          </div>
          <button type="button" class="node-test-log-action" @click="openRunLogPanel">
            查看日志
          </button>
          <button type="button" class="node-test-close-button" aria-label="关闭节点试运行" @click="closeSelectedNodeTest">
            <XIcon aria-hidden="true" />
          </button>
        </div>

        <div v-if="nodeTestRunning" class="node-test-running">
          <div class="node-test-spinner"></div>
          <strong>试运行进行中...</strong>
        </div>

        <template v-else>
          <section class="config-section">
            <div class="node-test-section-title">
              <strong>试运行输入</strong>
            </div>
            <div class="node-test-input-list">
              <label v-for="row in nodeTestInputs" :key="row.name" class="node-test-input-row">
                <span>
                  {{ row.name }}
                  <em>{{ row.type }}</em>
                </span>
                <a-textarea
                  v-if="row.type === 'json'"
                  :auto-size="{ minRows: 3, maxRows: 8 }"
                  :value="row.value"
                  :placeholder="row.name"
                  @update:value="setNodeTestInput(row.name, $event)"
                />
                <a-input
                  v-else
                  :value="row.value"
                  :placeholder="row.name"
                  @update:value="setNodeTestInput(row.name, $event)"
                />
              </label>
            </div>
          </section>

          <section v-if="nodeTestError" class="config-section">
            <div class="node-test-status failure">FAILED</div>
            <p class="node-test-error">{{ nodeTestError }}</p>
          </section>

          <section v-if="nodeTestResult" class="config-section node-test-result">
            <div class="node-test-status success">
              SUCCEEDED
              <span>{{ nodeTestResult.elapsedMs || 0 }}ms</span>
            </div>
            <div class="node-test-readable-result">
              <h4>运行结果</h4>
              <article class="node-test-readable-block">
                <div class="node-test-readable-heading">
                  <strong>输入</strong>
                  <button type="button" aria-label="复制输入" @click="copyNodeTestReadableValue(nodeTestResult.input)">
                    <CopyIcon aria-hidden="true" />
                  </button>
                </div>
                <div class="node-test-readable-card">
                  <div v-for="row in nodeTestInputReadableRows" :key="row.key" class="node-test-readable-row">
                    <span>{{ row.key }}</span>
                    <em>{{ row.value }}</em>
                  </div>
                </div>
              </article>
              <article class="node-test-readable-block">
                <div class="node-test-readable-heading">
                  <strong>推理内容</strong>
                  <button type="button" aria-label="复制推理内容" @click="copyNodeTestReadableValue(nodeTestReasoning)">
                    <CopyIcon aria-hidden="true" />
                  </button>
                </div>
                <div class="node-test-readable-card node-test-readable-text">{{ nodeTestReasoning }}</div>
              </article>
              <article class="node-test-readable-block">
                <div class="node-test-readable-heading">
                  <strong>技能调用</strong>
                </div>
                <div class="node-test-readable-card node-test-readable-text">{{ nodeTestSkillCalls }}</div>
              </article>
              <article class="node-test-readable-block">
                <div class="node-test-readable-heading">
                  <strong>输出</strong>
                  <button type="button" aria-label="复制输出" @click="copyNodeTestReadableValue(nodeTestResult.output)">
                    <CopyIcon aria-hidden="true" />
                  </button>
                </div>
                <div class="node-test-readable-card">
                  <div v-for="row in nodeTestOutputReadableRows" :key="row.key" class="node-test-readable-row">
                    <span>{{ row.key }}</span>
                    <em>{{ row.value }}</em>
                  </div>
                </div>
              </article>
            </div>
          </section>
        </template>

        <div class="node-test-footer">
          <button
            type="button"
            :class="nodeTestRunning ? 'stop' : 'run'"
            @click="nodeTestRunning ? undefined : runSelectedNodeTest()"
          >
            {{ nodeTestRunning ? '停止' : '运行' }}
          </button>
        </div>
      </aside>

      <aside v-if="testPanelOpen" class="test-run-panel" :class="{ 'chatflow-run-panel': isChatflowMode }" data-testid="test-run-panel">
        <div v-if="!isChatflowMode" class="node-test-header test-run-header">
          <div class="node-test-header-title">
            <h3>试运行</h3>
          </div>
          <button type="button" class="node-test-log-action" @click="openRunLogPanel">
            查看日志
          </button>
          <button type="button" class="node-test-close-button" aria-label="关闭试运行" @click="testPanelOpen = false">
            <XIcon aria-hidden="true" />
          </button>
        </div>
        <div v-else class="config-header chatflow-run-header">
          <div class="node-type-icon icon-start"><Finished /></div>
          <div class="chatflow-run-header-title">
            <h3>对话试运行</h3>
          </div>
          <div class="chatflow-run-header-actions">
            <button
              type="button"
              class="chatflow-run-header-button"
              :class="{ active: chatflowRunSettingsOpen }"
              data-testid="chatflow-run-fields-toggle"
              aria-label="对话设置"
              :aria-expanded="chatflowRunSettingsOpen"
              @click="chatflowRunSettingsOpen = !chatflowRunSettingsOpen"
            >
              <span>对话设置</span>
              <ChevronDownIcon aria-hidden="true" />
            </button>
            <button
              type="button"
              class="chatflow-run-header-icon"
              aria-label="重置会话"
              :disabled="running"
              @click="resetChatflowTrialSession"
            >
              <BroomIcon aria-hidden="true" />
            </button>
            <button type="button" class="chatflow-run-header-icon" aria-label="关闭试运行" @click="testPanelOpen = false">
              <XIcon aria-hidden="true" />
            </button>
          </div>
          <div
            v-if="chatflowRunSettingsOpen"
            class="chatflow-run-settings-popover"
            data-testid="chatflow-run-settings-popover"
          >
            <div class="chatflow-run-settings-summary">{{ testProfile.conversationId }} / {{ testProfile.userId }} / {{ testProfile.channel }}</div>
            <div class="chatflow-profile-grid">
              <div class="run-input-field compact">
                <label>会话 ID（sys.conversation_id）</label>
                <a-input v-model:value="testProfile.conversationId" placeholder="conversation_id" />
              </div>
              <div class="run-input-field compact">
                <label>用户 ID（sys.user_id）</label>
                <a-input v-model:value="testProfile.userId" placeholder="user_id" />
              </div>
              <div class="run-input-field compact">
                <label>渠道（sys.channel）</label>
                <a-select :virtual="false" v-model:value="testProfile.channel" placeholder="channel">
                  <a-select-option value="web" >web</a-select-option>
                  <a-select-option value="api" >api</a-select-option>
                  <a-select-option value="feishu" >feishu</a-select-option>
                  <a-select-option value="dingtalk" >dingtalk</a-select-option>
                </a-select>
              </div>
              <div class="run-input-field compact">
                <label>渠道 ID（sys.channel_id）</label>
                <a-input v-model:value="testProfile.channelId" placeholder="channel_id" />
              </div>
            </div>
          </div>
        </div>

        <template v-if="isChatflowMode">
          <section v-if="validationErrors.length" class="config-section">
            <div class="section-title validation-title"><span>!</span> 校验失败</div>
            <ul class="validation-list">
              <li v-for="error in validationErrors" :key="error">{{ error }}</li>
            </ul>
          </section>

          <section class="chatflow-run-chat-window" data-testid="chatflow-run-chat-window">
            <div class="chatflow-message-list" data-testid="chatflow-run-messages">
              <template v-if="chatflowTrialMessages.length === 0">
                <div
                  v-if="chatflowWelcome.openingMessage"
                  class="message-bubble assistant opening"
                  data-testid="chatflow-opening-message"
                >
                  {{ chatflowWelcome.openingMessage }}
                </div>
                <div
                  v-if="chatflowWelcome.suggestedQuestions.length"
                  class="chatflow-suggested-questions"
                  data-testid="chatflow-suggested-questions"
                >
                  <div class="chatflow-suggested-title">猜你想问</div>
                  <div class="chatflow-guide-list">
                    <button
                      v-for="question in chatflowWelcome.suggestedQuestions"
                      :key="question"
                      type="button"
                      data-testid="chatflow-guide-question"
                      @click="applyGuideQuestion(question)"
                    >
                      {{ question }}
                    </button>
                  </div>
                </div>
                <div
                  v-if="!chatflowWelcome.openingMessage && !chatflowWelcome.suggestedQuestions.length"
                  class="chatflow-empty-message"
                >
                  发送一条消息，使用当前 Chatflow 草稿试运行。
                </div>
              </template>
              <template v-else>
                <div
                  v-for="message in chatflowTrialMessages"
                  :key="message.id"
                  :class="['message-bubble', message.role, { loading: message.loading, error: message.error }]"
                  :data-testid="message.role === 'user' ? 'chatflow-user-message' : 'chatflow-assistant-message'"
                >
                  <span
                    v-if="message.loading"
                    class="chatflow-loading-dots"
                    data-testid="chatflow-assistant-loading"
                    aria-label="等待回复"
                  >
                    <i aria-hidden="true"></i>
                    <i aria-hidden="true"></i>
                    <i aria-hidden="true"></i>
                  </span>
                  <span v-else :data-testid="message.streaming ? 'chatflow-typewriter-message' : undefined">
                    {{ message.content }}
                    <span v-if="message.streaming" class="typewriter-caret" aria-hidden="true"></span>
                  </span>
                </div>
              </template>
            </div>

            <div v-if="testResult" class="chatflow-run-meta">
              <span class="run-status" :class="{ success: testResult.status === 'SUCCEEDED' }">{{ testResult.status }}</span>
              <span v-if="testResult.runId">Run #{{ testResult.runId }}</span>
            </div>

            <section
              v-if="chatflowSessionState?.status === 'waiting'"
              class="chatflow-resume-card"
              data-testid="chatflow-run-resume-card"
            >
              <div class="debug-section-title">
                <strong>等待用户输入</strong>
                <span>{{ chatflowCheckpoint?.pendingNodeKey || chatflowWaitingEvent?.nodeKey || 'pending' }}</span>
              </div>
              <div
                v-for="field in chatflowResumeFields"
                :key="field.key"
                class="resume-field-row"
              >
                <label>{{ field.label }}</label>
                <input
                  :aria-label="field.label"
                  :placeholder="field.placeholder"
                  :value="chatflowResumeValues[field.key] || ''"
                  @input="setChatflowResumeField(field.key, ($event.target as HTMLInputElement).value)"
                />
              </div>
              <button
                type="button"
                class="resume-submit-button"
                :disabled="chatflowResumeSubmitting"
                @click="submitChatflowResume"
              >
                {{ chatflowResumeSubmitting ? '继续中...' : '提交回复继续' }}
              </button>
            </section>

            <div class="chatflow-composer">
              <div class="chatflow-composer-shell" data-testid="chatflow-composer-shell">
                <div class="chatflow-composer-editor" data-testid="chatflow-composer-editor">
                  <a-textarea
                    v-model:value="testInput"
                    class="chatflow-composer-input"
                    data-testid="chatflow-run-message-input"
                    :auto-size="{ minRows: 2, maxRows: 6 }"
                    placeholder="发送消息"
                    :disabled="running"
                    @keydown.enter.exact.prevent="sendChatflowMessage"
                  />
                </div>
                <div class="chatflow-composer-actions" data-testid="chatflow-composer-actions">
                  <button
                    type="button"
                    class="chatflow-upload-button"
                    aria-label="上传文件"
                  >
                    <LucidePlus aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    class="chatflow-send-button"
                    aria-label="发送消息"
                    :disabled="running || !testInput.trim()"
                    @click="sendChatflowMessage"
                  >
                    <Promotion aria-hidden="true" />
                  </button>
                </div>
              </div>
            </div>
          </section>
        </template>

        <template v-else>
          <section class="config-section">
            <div class="node-test-section-title">
              <strong>试运行输入</strong>
            </div>
            <div class="run-input-field">
              <label>用户消息（userMessage / USER_INPUT）</label>
              <a-textarea
                v-model:value="testInput"
                :rows="4"
                placeholder="输入 userMessage"
              />
            </div>
          </section>

          <section v-if="validationErrors.length" class="config-section">
            <div class="section-title validation-title"><span>!</span> 校验失败</div>
            <ul class="validation-list">
              <li v-for="error in validationErrors" :key="error">{{ error }}</li>
            </ul>
          </section>

          <section v-if="testResult" class="config-section">
            <div class="section-title"><span>✓</span> 运行结果</div>
            <div class="run-summary">
              <span class="run-status" :class="{ success: testResult.status === 'SUCCEEDED' }">{{ testResult.status }}</span>
              <span v-if="testResult.runId">Run #{{ testResult.runId }}</span>
            </div>
            <div class="workflow-result-card" data-testid="workflow-run-output">
              <div v-for="row in runOutputRows" :key="row.key" class="workflow-result-row">
                <span>{{ row.key }}</span>
                <strong>{{ row.value }}</strong>
              </div>
              <div v-if="runOutputRows.length === 0" class="workflow-result-empty">暂无输出</div>
            </div>
          </section>

          <div class="node-test-footer test-run-actions">
            <button type="button" class="run" :disabled="running" @click="runCanvasTest">
              {{ running ? '运行中...' : '运行' }}
            </button>
          </div>
        </template>
      </aside>

      <aside v-if="debugDockOpen" class="workflow-debug-dock" data-testid="workflow-debug-dock">
        <div class="debug-dock-header">
          <div class="debug-dock-title">
            <strong>调试详情</strong>
            <span v-if="lastTestRunId">当前运行 #{{ lastTestRunId }} · {{ lastTestRunStatus || 'RUNNING' }}</span>
          </div>
          <div class="debug-dock-actions">
            <button
              v-if="canCancelRuntimeV2Run"
              type="button"
              class="debug-cancel-run-button"
              data-testid="debug-runtime-v2-cancel"
              aria-label="取消运行"
              :disabled="runtimeV2Cancelling"
              :title="runtimeV2Cancelling ? '正在取消运行' : '取消当前运行'"
              @click="cancelCurrentRuntimeV2Run"
            >
              <StopIcon aria-hidden="true" />
              <span>{{ runtimeV2Cancelling ? '取消中' : '取消运行' }}</span>
            </button>
            <button
              v-if="lastTestRunId"
              type="button"
              class="debug-observe-link"
              data-testid="debug-observe-link"
              @click="openObserveRunDetail"
            >
              查看运行详情
            </button>
            <button type="button" aria-label="关闭调试工具" class="debug-close-button" @click="closeDebugDock">
              <XIcon aria-hidden="true" />
            </button>
          </div>
        </div>
        <div class="debug-dock-tabs">
          <button type="button" :class="{ active: debugDockTab === 'errors' }" @click="debugDockTab = 'errors'">错误列表</button>
          <button type="button" :class="{ active: debugDockTab === 'debug' }" @click="debugDockTab = 'debug'">调试</button>
        </div>
        <div v-if="debugDockTab === 'errors'" class="debug-dock-body debug-error-panel" data-testid="debug-error-panel">
          <div class="debug-error-summary">
            <strong>错误列表</strong>
            <span>{{ debugDockErrors.length }} 项</span>
          </div>
          <div v-if="debugDockErrors.length" class="debug-error-list-card">
            <article v-for="error in debugDockErrors" :key="error" class="debug-error-item">
              <span aria-hidden="true">!</span>
              <p>{{ error }}</p>
            </article>
          </div>
          <div v-else class="debug-error-empty-card">
            <span aria-hidden="true">✓</span>
            <strong>暂无错误</strong>
            <small>当前画布没有校验错误</small>
          </div>
        </div>
        <div v-else-if="isChatflowMode" class="debug-dock-body chatflow-runtime-debug trace-detail-layout">
          <section class="chatflow-run-summary trace-summary-card" data-testid="chatflow-run-summary">
            <div class="debug-section-title">
              <strong>{{ chatflowRunDebugSummary.runLabel }}</strong>
              <span>{{ chatflowRunDebugLoading ? '加载中' : chatflowRunDebugSummary.statusLabel }}</span>
            </div>
            <p>{{ chatflowRunDebugSummary.sessionLabel }}</p>
            <p>{{ chatflowRunDebugSummary.nodeCountLabel }}</p>
          </section>

          <section
            v-if="chatflowDebugStreamPreview.content"
            class="chatflow-debug-stream-preview trace-summary-card"
            data-testid="chatflow-debug-stream-preview"
          >
            <div class="debug-section-title">
              <strong>流式输出</strong>
              <span>{{ chatflowDebugStreamPreview.streaming ? '生成中' : '已完成' }}</span>
            </div>
            <p>
              {{ chatflowDebugStreamPreview.content }}
              <span v-if="chatflowDebugStreamPreview.streaming" class="typewriter-caret" aria-hidden="true"></span>
            </p>
            <small v-if="chatflowDebugStreamPreview.chunks.length">{{ chatflowDebugStreamPreview.chunks.length }} chunks</small>
          </section>

          <section
            v-if="chatflowSessionState?.status === 'waiting'"
            class="chatflow-waiting-state"
            data-testid="chatflow-waiting-state"
          >
            <div class="debug-section-title">
              <strong>等待用户输入</strong>
              <span>{{ chatflowCheckpoint?.pendingNodeKey || chatflowWaitingEvent?.nodeKey || 'pending' }}</span>
            </div>
            <p>
              请按下方表单补充信息，提交后会继续当前会话。
            </p>
            <div
              v-for="field in chatflowResumeFields"
              :key="field.key"
              class="resume-field-row"
            >
              <label>{{ field.label }}</label>
              <input
                :aria-label="field.label"
                :placeholder="field.placeholder"
                :value="chatflowResumeValues[field.key] || ''"
                @input="setChatflowResumeField(field.key, ($event.target as HTMLInputElement).value)"
              />
            </div>
            <button
              type="button"
              class="resume-submit-button"
              :disabled="chatflowResumeSubmitting"
              @click="submitChatflowResume"
            >
              {{ chatflowResumeSubmitting ? '继续中...' : '提交回复继续' }}
            </button>
          </section>

          <div class="trace-detail-grid">
          <section class="trace-main-card coze-call-tree-card" data-testid="chatflow-run-call-tree">
            <div class="debug-section-title">
              <strong>调用树</strong>
              <span>{{ chatflowRunCallTreeRows.length }} 节点</span>
            </div>
            <ol v-if="chatflowRunCallTreeRows.length" class="workflow-call-tree">
              <li v-for="node in chatflowRunCallTreeRows" :key="node.detailKey">
                <button
                  type="button"
                  class="workflow-call-tree-node workflow-call-tree-branch"
                  :class="[`depth-${debugCallTreeDepth(node.nodeKey)}`, { active: selectedDebugNodeKey === node.detailKey }]"
                  @click="selectDebugNode(node.detailKey)"
                >
                  <strong>{{ node.nodeKey }}</strong>
                  <small>
                    {{ node.nodeType }}
                    <span class="workflow-call-status" :class="`status-${node.status.toLowerCase()}`">{{ debugStatusLabel(node.status) }}</span>
                    {{ node.elapsedMs }}ms
                  </small>
                </button>
              </li>
            </ol>
            <p v-else>暂无节点执行记录</p>
          </section>

          <section class="workflow-node-detail-section trace-node-detail-card coze-detail-card" data-testid="chatflow-run-node-details">
            <div class="debug-section-title coze-detail-header">
              <strong>详情</strong>
              <label>
                <span class="sr-only">调试详情视图</span>
                <select v-model="debugTraceDetailMode" aria-label="调试详情视图">
                  <option value="flame">火焰图</option>
                  <option value="node">节点详情</option>
                </select>
              </label>
            </div>
            <div
              v-if="debugTraceDetailMode === 'flame'"
              class="trace-main-card coze-flame-card"
              data-testid="chatflow-run-flamegraph"
            >
              <div class="debug-section-title">
                <strong>火焰图</strong>
                <span>{{ chatflowRunFlamegraphRows.length }} 段</span>
              </div>
              <div v-if="chatflowRunFlamegraphRows.length" class="workflow-flamegraph">
                <div class="workflow-flame-scrollbar" aria-hidden="true">
                  <span></span>
                </div>
                <div class="workflow-flame-axis" aria-hidden="true">
                  <span>0</span>
                  <span>2000</span>
                  <span>4000</span>
                  <span>6000</span>
                  <span>8000</span>
                </div>
                <div class="workflow-flame-lanes">
                  <div
                    v-for="(row, index) in chatflowRunFlamegraphRows"
                    :key="row.detailKey"
                    class="workflow-flame-row"
                    :style="flamegraphRowStyle(row, chatflowRunFlamegraphRows, index)"
                  >
                    <button type="button" class="workflow-flame-bar" @click="selectDebugNode(row.detailKey)">
                      {{ row.label }} · {{ row.durationMs }}ms
                    </button>
                  </div>
                </div>
              </div>
              <p v-else>暂无时间线</p>
            </div>
            <div class="coze-selected-node-detail">
            <div class="debug-section-title">
              <strong>节点详情</strong>
              <span>{{ activeChatflowDebugNode?.nodeKey || '未选择' }}</span>
            </div>
            <div v-if="activeChatflowDebugNode" class="workflow-node-detail-list">
              <article>
                <div>
                  <strong>{{ activeChatflowDebugNode.nodeKey }}</strong>
                  <small>{{ activeChatflowDebugNode.nodeType }} · {{ activeChatflowDebugNode.status }}</small>
                </div>
                <div class="workflow-node-evidence-row" data-testid="workflow-node-evidence-row">
                  {{ formatWorkflowNodeEvidence(activeChatflowDebugNode) }}
                </div>
                <strong>输入</strong>
                <pre>{{ formatWorkflowDebugValue(debugNodeInputs(activeChatflowDebugNode)) }}</pre>
                <strong>输出</strong>
                <pre>{{ formatWorkflowDebugValue(debugNodeOutputs(activeChatflowDebugNode)) }}</pre>
                <p v-if="activeChatflowDebugNode.error">{{ activeChatflowDebugNode.error }}</p>
              </article>
            </div>
            <p v-else>暂无节点详情</p>
            </div>
          </section>
          </div>

          <details class="trace-advanced-card" data-testid="chatflow-debug-advanced">
            <summary>高级运行上下文</summary>
            <section class="chatflow-timeline-section" data-testid="chatflow-event-timeline">
              <div class="debug-section-title">
                <strong>事件时间线</strong>
                <span>{{ chatflowDebugLoading ? '加载中' : `${chatflowTimelineRows.length} 条` }}</span>
              </div>
              <ol v-if="chatflowTimelineRows.length" class="chatflow-timeline-list">
                <li v-for="event in chatflowTimelineRows" :key="`${event.sequence}-${event.id}`">
                  <span class="timeline-sequence">#{{ event.sequence }}</span>
                  <strong>{{ event.label }}</strong>
                  <small>{{ event.meta }}</small>
                  <p v-if="event.content">{{ event.content }}</p>
                </li>
              </ol>
              <p v-else>暂无事件</p>
            </section>

            <section class="chatflow-variable-section" data-testid="chatflow-debug-variables">
              <div class="debug-section-title">
                <strong>作用域变量</strong>
                <span>{{ chatflowVariableRows.length }} 项</span>
              </div>
              <div v-if="chatflowVariableRows.length" class="chatflow-variable-list">
                <div v-for="row in chatflowVariableRows" :key="`${row.scope}.${row.name}`">
                  <code>{{ row.scope }}.{{ row.name }}</code>
                  <span>{{ row.value }}</span>
                </div>
              </div>
              <p v-else>暂无变量</p>
            </section>
          </details>
        </div>
        <div v-else class="debug-dock-body workflow-runtime-debug trace-detail-layout" data-testid="workflow-run-debug-detail">
          <section class="workflow-run-summary trace-summary-card">
            <div class="debug-section-title">
              <strong>{{ workflowRunDebugSummary.runLabel }}</strong>
              <span>{{ workflowRunDebugLoading ? '加载中' : workflowRunDebugSummary.statusLabel }}</span>
            </div>
            <dl class="workflow-run-metrics">
              <div>
                <dt>耗时</dt>
                <dd>{{ workflowRunDebugSummary.elapsedLabel }}</dd>
              </div>
              <div>
                <dt>节点</dt>
                <dd>{{ workflowRunDebugSummary.nodeCountLabel }}</dd>
              </div>
            </dl>
            <div class="workflow-run-io">
              <strong>输入</strong>
              <pre>{{ formatWorkflowDebugValue(workflowRunDebugDetail?.input || {}) }}</pre>
              <strong>输出</strong>
              <pre>{{ formatWorkflowDebugValue(workflowRunDebugDetail?.output || lastRunOutput || {}) }}</pre>
            </div>
          </section>

          <div class="trace-detail-grid">
          <section class="trace-main-card coze-call-tree-card" data-testid="workflow-run-call-tree">
            <div class="debug-section-title">
              <strong>调用树</strong>
              <span>{{ workflowRunCallTreeRows.length }} 节点</span>
            </div>
            <ol v-if="workflowRunCallTreeRows.length" class="workflow-call-tree">
              <li v-for="node in workflowRunCallTreeRows" :key="node.detailKey">
                <button
                  type="button"
                  class="workflow-call-tree-node workflow-call-tree-branch"
                  :class="[`depth-${debugCallTreeDepth(node.nodeKey)}`, { active: selectedDebugNodeKey === node.detailKey }]"
                  @click="selectDebugNode(node.detailKey)"
                >
                  <strong>{{ node.nodeKey }}</strong>
                  <small>
                    {{ node.nodeType }}
                    <span class="workflow-call-status" :class="`status-${node.status.toLowerCase()}`">{{ debugStatusLabel(node.status) }}</span>
                    {{ node.elapsedMs }}ms
                  </small>
                </button>
              </li>
            </ol>
            <p v-else>暂无节点执行记录</p>
          </section>

          <section class="workflow-node-detail-section trace-node-detail-card coze-detail-card" data-testid="workflow-run-node-details">
            <div class="debug-section-title coze-detail-header">
              <strong>详情</strong>
              <label>
                <span class="sr-only">调试详情视图</span>
                <select v-model="debugTraceDetailMode" aria-label="调试详情视图">
                  <option value="flame">火焰图</option>
                  <option value="node">节点详情</option>
                </select>
              </label>
            </div>
            <div
              v-if="debugTraceDetailMode === 'flame'"
              class="trace-main-card coze-flame-card"
              data-testid="workflow-run-flamegraph"
            >
              <div class="debug-section-title">
                <strong>火焰图</strong>
                <span>{{ workflowRunFlamegraphRows.length }} 段</span>
              </div>
              <div v-if="workflowRunFlamegraphRows.length" class="workflow-flamegraph">
                <div class="workflow-flame-scrollbar" aria-hidden="true">
                  <span></span>
                </div>
                <div class="workflow-flame-axis" aria-hidden="true">
                  <span>0</span>
                  <span>2000</span>
                  <span>4000</span>
                  <span>6000</span>
                  <span>8000</span>
                </div>
                <div class="workflow-flame-lanes">
                  <div
                    v-for="(row, index) in workflowRunFlamegraphRows"
                    :key="row.detailKey"
                    class="workflow-flame-row"
                    :style="flamegraphRowStyle(row, workflowRunFlamegraphRows, index)"
                  >
                    <button type="button" class="workflow-flame-bar" @click="selectDebugNode(row.detailKey)">
                      {{ row.label }} · {{ row.durationMs }}ms
                    </button>
                  </div>
                </div>
              </div>
              <p v-else>暂无时间线</p>
            </div>
            <div class="coze-selected-node-detail">
            <div class="debug-section-title">
              <strong>节点详情</strong>
              <span>{{ activeWorkflowDebugNode?.nodeKey || '未选择' }}</span>
            </div>
            <div v-if="activeWorkflowDebugNode" class="workflow-node-detail-list">
              <article>
                <div>
                  <strong>{{ activeWorkflowDebugNode.nodeKey }}</strong>
                  <small>{{ activeWorkflowDebugNode.nodeType }} · {{ activeWorkflowDebugNode.status }}</small>
                </div>
                <div class="workflow-node-evidence-row" data-testid="workflow-node-evidence-row">
                  {{ formatWorkflowNodeEvidence(activeWorkflowDebugNode) }}
                </div>
                <div
                  v-for="eventEvidence in formatWorkflowNodeEventEvidence(activeWorkflowDebugNode)"
                  :key="eventEvidence.key"
                  class="workflow-node-runtime-event-evidence"
                  data-testid="workflow-node-runtime-event-evidence"
                >
                  <strong>{{ eventEvidence.sequenceLabel }} {{ eventEvidence.eventType }}</strong>
                  <span>{{ eventEvidence.status }}</span>
                  <p v-if="eventEvidence.detail">{{ eventEvidence.detail }}</p>
                </div>
                <div
                  v-if="formatWorkflowLlmFallbackEvidence(activeWorkflowDebugNode)"
                  class="workflow-node-fallback-evidence"
                  data-testid="workflow-node-fallback-evidence"
                >
                  {{ formatWorkflowLlmFallbackEvidence(activeWorkflowDebugNode) }}
                </div>
                <strong>输入</strong>
                <pre>{{ formatWorkflowDebugValue(debugNodeInputs(activeWorkflowDebugNode)) }}</pre>
                <strong>输出</strong>
                <pre>{{ formatWorkflowDebugValue(debugNodeOutputs(activeWorkflowDebugNode)) }}</pre>
                <p v-if="activeWorkflowDebugNode.error">{{ activeWorkflowDebugNode.error }}</p>
              </article>
            </div>
            <p v-else>暂无节点详情</p>
            </div>
          </section>
          </div>
        </div>
      </aside>

      <div v-if="paletteOpen" class="node-palette" data-testid="bottom-node-palette">
        <a-input v-model:value="nodePaletteSearch" size="small" placeholder="搜索节点、插件、工作流" />
        <div v-for="group in filteredNodePaletteGroups" :key="group.title" class="node-palette-group">
          <strong>{{ group.title }}</strong>
          <div class="node-palette-grid">
            <button
              v-for="entry in group.items"
              :key="entry.type"
              type="button"
              :aria-label="entry.label"
              :disabled="entry.disabled"
              @click="addNode(entry.type)"
            >
              <span class="palette-icon" :class="`icon-${entry.type.toLowerCase()}`">
                <component :is="nodeIcon(entry.type)" />
              </span>
              <span>{{ entry.label }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="canvas-toolbar" data-testid="canvas-bottom-toolbar">
        <button type="button" aria-label="缩小显示比例" :disabled="canvasZoom <= CANVAS_ZOOM_MIN" @click="decreaseCanvasZoom">
          <LucideMinus aria-hidden="true" />
        </button>
        <button type="button" aria-label="放大显示比例" :disabled="canvasZoom >= CANVAS_ZOOM_MAX" @click="increaseCanvasZoom">
          <LucidePlus aria-hidden="true" />
        </button>
        <div class="toolbar-zoom-wrap">
          <button
            type="button"
            class="toolbar-zoom"
            :aria-label="`缩放 ${canvasZoomLabel}`"
            @click="zoomMenuOpen = !zoomMenuOpen"
          >
            {{ canvasZoomLabel }}
          </button>
          <div v-if="zoomMenuOpen" class="canvas-zoom-menu" data-testid="canvas-zoom-menu" role="menu">
            <button
              v-for="preset in CANVAS_ZOOM_PRESETS"
              :key="preset"
              type="button"
              :class="{ active: isZoomPresetActive(preset) }"
              role="menuitem"
              @click="applyCanvasZoom(preset)"
            >
              {{ formatCanvasZoomLabel(preset) }}
            </button>
          </div>
        </div>
        <button type="button" aria-label="自动布局" title="自动布局" @click="autoLayoutCanvas">
          <LayoutDashboardIcon aria-hidden="true" />
        </button>
        <button type="button" :aria-label="operationModeLabel" :title="operationModeLabel" @click="toggleOperationMode">
          <HandIcon v-if="operationMode === 'trackpad'" aria-hidden="true" />
          <MousePointerIcon v-else aria-hidden="true" />
        </button>
        <button class="toolbar-add-node" type="button" aria-label="添加节点" @click="paletteOpen = !paletteOpen">
          <LucidePlus aria-hidden="true" />
          <span>添加节点</span>
        </button>
        <button type="button" aria-label="调试工具" title="调试工具" @click="toggleDebugDock">
          <WrenchIcon aria-hidden="true" />
        </button>
        <button class="toolbar-run" type="button" aria-label="试运行" @click="openTestPanel">
          <PlayIcon aria-hidden="true" />
          <span>试运行</span>
        </button>
      </div>
      </div>
    </section>

    <a-modal
      v-model:open="publishDialogOpen"
      class="workflow-publish-dialog"
      title="发布"
      width="42rem"
      :footer="null"
      :keyboard="true"
      @cancel="publishDialogOpen = false"
    >
      <div class="publish-dialog-body" data-testid="workflow-publish-dialog">
        <section class="publish-dialog-section">
          <div class="section-title"><span>⌄</span> 发布检查</div>
          <dl class="ops-field-list">
            <div>
              <dt>画布校验</dt>
              <dd>{{ publishValidationErrors.length ? '未通过' : '已通过' }}</dd>
            </div>
            <div>
              <dt>最近试运行</dt>
              <dd>{{ lastTestRunStatus || '未运行' }}</dd>
            </div>
            <div>
              <dt>当前状态</dt>
              <dd>{{ workflowStatus }}</dd>
            </div>
          </dl>
          <ul v-if="publishGate.reasons.length" class="validation-list publish-reasons">
            <li v-for="reason in publishGate.reasons" :key="reason">{{ reason }}</li>
          </ul>
        </section>

        <section class="publish-dialog-section">
          <div class="section-title"><span>⌄</span> 版本信息</div>
          <label class="publish-version-field">
            <span>版本名称</span>
            <input :value="nextPublishVersionName" readonly />
          </label>
          <label class="publish-version-field">
            <span>版本说明</span>
            <textarea :value="publishNotes" readonly rows="3"></textarea>
          </label>
        </section>

        <section class="publish-dialog-section version-list" data-testid="workflow-version-list">
          <div class="section-title"><span>⌄</span> 版本</div>
          <p v-if="workflowVersionsLoading" class="resource-empty-state">正在加载版本...</p>
          <p v-else-if="!workflowVersionRows.length" class="resource-empty-state">暂无发布版本</p>
          <template v-else>
            <article v-for="version in workflowVersionRows" :key="version.id" class="version-row">
              <div>
                <strong>{{ version.label }}</strong>
                <span>{{ version.createdAt }}</span>
              </div>
              <em>{{ version.status }}</em>
              <button
                type="button"
                data-testid="workflow-version-run"
                :disabled="targetedPublishedRunLoadingId === version.id"
                @click="runPublishedVersion(version.id)"
              >
                测试运行
              </button>
              <button
                type="button"
                data-testid="workflow-version-run-v2"
                :disabled="targetedRuntimeV2RunLoadingId === version.id"
                @click="runPublishedVersionWithRuntimeV2(version.id)"
              >
                实时测试
              </button>
              <button
                v-if="version.canRollback"
                type="button"
                :disabled="rollingBackVersionId === version.id"
                @click="rollbackVersion(version.id)"
              >
                回滚
              </button>
            </article>
          </template>
          <p v-if="targetedPublishedRunResult" class="targeted-published-run-result">
            运行版本 v{{ targetedPublishedRunResult.version }}
            · Run #{{ targetedPublishedRunResult.runId }}
            · {{ targetedPublishedRunResult.status }}
            · versionId {{ targetedPublishedRunResult.versionId }}
          </p>
          <p
            v-if="targetedRuntimeV2RunResult"
            class="targeted-runtime-v2-run-result"
            data-testid="workflow-version-run-v2-result"
          >
            实时运行版本 v{{ targetedRuntimeV2RunResult.version }}
            · Run #{{ targetedRuntimeV2RunResult.runId }}
            · {{ targetedRuntimeV2RunResult.status }}
            · versionId {{ targetedRuntimeV2RunResult.versionId }}
          </p>
        </section>

        <div class="publish-actions">
          <a-button @click="publishDialogOpen = false">取消</a-button>
          <a-button
            :disabled="!publishGate.allowed"
            :loading="publishing"
            type="primary"
            @click="publishWorkflow"
          >
            确认发布
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeft,
  ArrowRight,
  BarChart3 as DataAnalysis,
  BrushCleaning as BroomIcon,
  Cable as Connection,
  Check as CheckIcon,
  ChevronDown as ChevronDownIcon,
  ChevronRight as ChevronRightIcon,
  CircleCheck as Finished,
  Copy as CopyIcon,
  Cpu,
  Hand as HandIcon,
  LayoutDashboard as LayoutDashboardIcon,
  MessageCircle as ChatDotRound,
  MessageSquare as ChatLineRound,
  Minus as LucideMinus,
  MoreHorizontal as MoreHorizontalIcon,
  MousePointer2 as MousePointerIcon,
  Play as PlayIcon,
  Plus as LucidePlus,
  Send as Promotion,
  Settings as SettingsIcon,
  Share2 as Share,
  SlidersHorizontal as Operation,
  Square as StopIcon,
  Trash2,
  User,
  Wrench as Tools,
  Wrench as WrenchIcon,
  X as XIcon,
} from 'lucide-vue-next'
import { BaseEdge, EdgeLabelRenderer, Handle, MarkerType, PanOnScrollMode, Position, VueFlow, getBezierPath, useVueFlow, type Edge, type Node } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

import {
  createChatflow,
  createWorkflow,
  cancelRuntimeV2Run,
  getChatflow,
  getChatflowRunDebug,
  getChatflowSession,
  getRuntimeV2Run,
  getWorkflow,
  getWorkflowRunDebug,
  listChatflowChannels,
  listChatflowRunEvents,
  listChatflowVersions,
  listRuntimeV2Events,
  listRuntimeV2Nodes,
  listWorkflowVersions,
  publishChatflowVersion,
  publishWorkflowVersion,
  resumeRuntimeV2Run,
  rollbackChatflowVersion,
  rollbackWorkflowVersion,
  resumeChatflowRun,
  runChatflowLegacy,
  runChatflowV2,
  runChatflowNode,
  runPublishedChatflow,
  runPublishedWorkflow,
  runWorkflow,
  runWorkflowV2,
  runWorkflowNode,
  updateChatflow,
  updateWorkflow,
  listWorkflowResources,
  type WorkflowDetail,
} from '@/api/workflow'
import { getProviderList, type ProviderVO } from '@/api/provider'
import anthropicLogoUrl from '@/assets/provider-logos/anthropic.svg?url'
import azureLogoUrl from '@/assets/provider-logos/azure.svg?url'
import compatibleLogoUrl from '@/assets/provider-logos/compatible.svg?url'
import geminiLogoUrl from '@/assets/provider-logos/gemini.svg?url'
import ollamaLogoUrl from '@/assets/provider-logos/ollama.svg?url'
import openaiLogoUrl from '@/assets/provider-logos/openai.svg?url'
import { computeVariableFlyoutPosition } from './floatingPanelGeometry'
import { buildLlmModelOptions, llmModelSelectionFields, type LlmModelOption } from './llmModelOptions'
import {
  buildChatflowResumeFields,
  flattenChatflowVariables,
  formatChatflowTimeline,
  type ChatflowResumeField,
} from './chatflowDebugTimeline'
import {
  CANVAS_CONNECTION_RADIUS,
  CANVAS_ENDPOINT_PREVIEW_RADIUS,
  CANVAS_PANE_CLICK_DISTANCE,
  CANVAS_TRACKPAD_PAN_SPEED,
  CANVAS_ZOOM_ANIMATION_MS,
  CANVAS_ZOOM_MAX,
  CANVAS_ZOOM_MIN,
  CANVAS_ZOOM_PRESETS,
  clampCanvasZoom,
  formatCanvasZoomLabel,
  nextCanvasZoom,
  normalizeCanvasOperationMode,
  operationModeTitle,
  type CanvasOperationMode,
} from './canvasControls'
import { resolveCanvasResponsiveLayout } from './canvasResponsiveLayout'
import { buildChatflowRunInput } from './chatflowRunProfile'
import { buildChatflowStreamPreview, buildChatflowWelcomeState, formatChatflowAssistantText } from './chatflowTrialRun'
import {
  composerCanvasTabs,
  resolveComposerSurfaceAction,
  type ComposerCanvasTab,
  type ComposerSurfaceAction,
} from './composerSurfaceState'
import {
  buildChatflowRunCallTree,
  buildChatflowRunFlamegraph,
  chatflowRunNodeDetails as buildChatflowRunNodeDetails,
  projectRuntimeV2ChatflowSessionState,
  summarizeChatflowRunDebug,
  withChatflowSessionState,
  type ChatflowRunDebugDetail,
} from './chatflowRunDebug'
import { buildChatflowVariableScopes, type ChatflowVariableDefinition, type ChatflowVariableScope } from './chatflowVariables'
import {
  buildChatflowChannelRows,
  buildChatflowOpenShell,
  buildWorkflowVersionRows,
  evaluateChatflowPublishGate,
  type ChatflowChannelRow,
  type ChatflowChannelShell,
  type WorkflowVersionLike,
  type WorkflowVersionRow,
} from './chatflowPublish'
import {
  addWorkflowNode,
  autoLayoutWorkflowGraph,
  connectWorkflowNodes,
  createDefaultChatflowGraph,
  createDefaultWorkflowGraph,
  deleteWorkflowEdge,
  deleteWorkflowNode,
  hydrateWorkflowGraph,
  insertWorkflowNodeOnEdge,
  moveWorkflowNode,
  renameWorkflowNode,
  serializeWorkflowGraph,
  type WorkflowCanvasGraph,
  type WorkflowCanvasNode,
  type WorkflowCanvasNodeType,
} from './flowGraph'
import {
  OUTPUT_FORMAT_OPTIONS,
  OUTPUT_PARAMETER_TYPE_OPTIONS,
  applyNodeConfigPatch,
  compactVariableTypeLabel,
  getNodeConfigSchema,
  normalizeAggregationGroups,
  normalizeAggregationSources,
  normalizeCollectionFields,
  normalizeHumanInputSchema,
  normalizeInputConfig,
  normalizeIntentRows,
  normalizeJsonFieldMappings,
  normalizeOutputConfig,
  normalizeQuestionOptions,
  normalizeStartVariables,
  validateInputParameters,
  validateOutputParameters,
  type AggregationSource,
  type AggregationGroup,
  type AggregationGroupVariable,
  type CollectionField,
  type HumanInputSchemaField,
  type IntentRow,
  type InputParameter,
  type InputParameterType,
  type InputValueMode,
  type JsonFieldMapping,
  type OutputFormat,
  type OutputParameter,
  type OutputParameterType,
  type QuestionOption,
  type StartVariable,
} from './nodeConfig'
import { buildNodeTestInputs, canRunSingleNodeTest, nodeTestInputPayload, type NodeTestInputRow } from './nodeTestFixtures'
import { buildNodePaletteGroups, filterNodePaletteGroups, type NodePaletteEntry } from './nodePalette'
import { isResourceSelectable, resourceStatusLabel, type WorkflowResource } from './resourceRegistry'
import { deriveRunPathEdgeClasses } from './runPathEdges'
import { completeVariableBraceTrigger, insertInlineVariableReference, localizeInlineVariableReference } from './inlineVariableText'
import { buildInlineVariableCatalog, buildVariableCatalog, type VariableCatalogGroup, type VariableCatalogType, type VariableDefinition } from './variableCatalog'
import { evaluateWorkflowPublishGate } from './workflowPublish'
import { mergeWorkflowValidationErrors, validateWorkflowGraph } from './workflowValidation'
import { buildChatflowRunDebugLink, buildWorkflowRunDebugLink } from '@/router/runDebugDeepLinks'
import {
  applyRuntimeV2EventsToDebugDetail,
  applyRuntimeV2NodesToDebugDetail,
  createRuntimeV2DebugDetail,
  isRuntimeV2TerminalStatus,
  mergeRuntimeV2RunToDebugDetail,
  openRuntimeV2DebugEventObserver,
  resolveRunLogAction,
  type RuntimeV2DebugEventObserver,
  type RuntimeV2Event,
  type RuntimeV2Node,
  type RuntimeV2StartRef,
} from './runtimeV2Debug'
import {
  buildWorkflowRunCallTree,
  buildWorkflowRunFlamegraph,
  formatWorkflowLlmFallbackEvidence,
  formatWorkflowNodeEvidence,
  formatWorkflowNodeEventEvidence,
  formatWorkflowDebugValue,
  summarizeWorkflowRunDebug,
  workflowRunNodeDetailKey,
  type WorkflowRunDebugDetail,
  type WorkflowRunFlamegraphRow,
  type WorkflowRunNodeDetail,
} from './workflowRunDebug'

type CanvasTab = ComposerCanvasTab
type ChatflowScopeState = ChatflowVariableScope & { open: boolean }
type ChatflowVariableScopeKey = ChatflowVariableScope['scope']
type ChatflowTrialMessage = {
  id: number
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
  loading?: boolean
  error?: boolean
}
type ChatflowSessionState = {
  sessionId: string
  status: string
  variables?: Record<string, any>
  expiresAt?: string | null
  waitingEvent?: Record<string, any> | null
  checkpoint?: Record<string, any> | null
}
type DebugDockTab = 'errors' | 'debug'
type DebugTraceDetailMode = 'node' | 'flame'
type ViewportRect = {
  top: number
  left: number
  right: number
  bottom: number
  width: number
  height: number
}
type LlmResourceType = 'KNOWLEDGE_BASE' | 'MCP_TOOL' | 'API_TOOL' | 'SUBWORKFLOW' | 'AGENT' | 'UNKNOWN'
type LlmSkillTabValue = Exclude<LlmResourceType, 'UNKNOWN'>
type LlmSkillChoice = {
  key: string
  type: LlmSkillTabValue
  name: string
  description: string
  disabled?: boolean
  registryResource?: WorkflowResource
}
type LlmResource = {
  type?: string
  resourceType?: string
  id?: string | number
  resourceId?: string | number
  knowledgeBaseId?: string | number
  name?: string
  query?: string
  topK?: string | number
  enabled?: boolean
}
type ConditionOperator = 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'greater_than' | 'greater_or_equal'
  | 'less_than' | 'less_or_equal' | 'length_greater_than' | 'length_greater_or_equal' | 'length_less_than'
  | 'length_less_or_equal' | 'is_empty' | 'is_not_empty' | 'is_true' | 'is_false'
type ConditionOperand = {
  valueMode: InputValueMode
  value: string
}
type ConditionRow = {
  left: ConditionOperand
  operator: ConditionOperator
  right: ConditionOperand
}
type ConditionBranch = {
  key: string
  name: string
  logic: 'AND' | 'OR'
  conditions: ConditionRow[]
}
type ConditionSourceHandle = {
  key: string
  kind: string
  label: string
  handleId: string
  condition: string | null
  top: string
}
type SchemaInputMappingRow = {
  name: string
  type: InputParameterType
  required: boolean
  description: string
  valueMode: InputValueMode
  value: string | number | boolean
}
type VariableAssignmentTargetOption = {
  scope: string
  scopeLabel: string
  variable: string
  label: string
  reference: string
  type: VariableCatalogType
}
type VariableAssignmentTargetGroup = {
  key: string
  title: string
  items: VariableAssignmentTargetOption[]
}
type PaletteEntry = {
  type: NodePaletteEntry['type']
  label: NodePaletteEntry['label']
  searchTerms?: NodePaletteEntry['searchTerms']
  disabled?: NodePaletteEntry['disabled']
}
const START_VARIABLE_LINE_BUDGET = 350
const START_VARIABLE_BADGE_BASE_WIDTH = 24
const START_VARIABLE_CHAR_WIDTH = 7.2
const START_VARIABLE_GAP = 8
const START_VARIABLE_MORE_WIDTH = 38

const route = useRoute()
const router = useRouter()
const { fitView, getViewport, zoomTo } = useVueFlow()
const isChatflowMode = computed(() => route.path.startsWith('/chatflows'))
const flowId = computed(() => Number(route.params.id || 0))
const workflowId = flowId
const isEditing = computed(() => flowId.value > 0)
const listRoute = computed<RouteLocationRaw>(() => ({
  name: isChatflowMode.value ? 'HifyChatflows' : 'HifyWorkflows',
}))
const canvasRoute = (id: number | string): RouteLocationRaw => ({
  name: isChatflowMode.value ? 'HifyChatflowsCanvas' : 'HifyWorkflowsCanvas',
  params: { id },
})

const graph = ref<WorkflowCanvasGraph>(createDefaultGraph())
const form = ref(defaultForm())
const saving = ref(false)
const canvasDirty = ref(false)
const running = ref(false)
const nodeTestRunning = ref(false)
const optimisticRunNodeKeys = ref<Set<string>>(new Set())
const loading = ref(false)
const canvasTab = ref<CanvasTab>('compose')
const composerLifecycleTabs = composerCanvasTabs()
const canvasStageRef = ref<HTMLElement | null>(null)
const canvasViewportWidth = ref(typeof window === 'undefined' ? 1600 : window.innerWidth)
const responsiveCanvasLayout = computed(() =>
  resolveCanvasResponsiveLayout({ viewportWidth: canvasViewportWidth.value, rem: rootRemSize() }),
)
const selectedNodeKey = ref('')
const selectedEdgeId = ref('')
const hoveredEdgeId = ref('')
const hoveredNodeKey = ref('')
const edgeInsertPaletteId = ref('')
const connectionPreviewPortKey = ref('')
const connectionPreviewStart = ref<{ nodeId: string; handleType: 'source' | 'target' } | null>(null)
const editingConditionBranchNameIndex = ref<number | null>(null)
const editingConditionDefaultName = ref(false)
const editingAggregationGroupNameIndex = ref<number | null>(null)
const aggregationGroupNameDraft = ref('')
const paletteOpen = ref(false)
const nodePaletteSearch = ref('')
const resourcePanelCollapsed = ref(false)
const operationMode = ref<CanvasOperationMode>(normalizeCanvasOperationMode(localStorage.getItem('hify.canvas.operationMode')))
const canvasZoom = ref(1)
const zoomMenuOpen = ref(false)
const debugDockOpen = ref(false)
const debugDockTab = ref<DebugDockTab>('errors')
const debugTraceDetailMode = ref<DebugTraceDetailMode>('flame')
const selectedDebugNodeKey = ref('')
const modelPickerOpen = ref(false)
const modelParameterPanelOpen = ref(false)
const llmModelSearch = ref('')
const llmModelSearchTerm = ref('')
const llmProviderModelOptions = ref<LlmModelOption[]>([])
const resourcePickerOpen = ref(false)
const activeLlmSkillTab = ref<LlmSkillTabValue>('KNOWLEDGE_BASE')
const llmSkillSearch = ref('')
const workflowResources = ref<WorkflowResource[]>([])
const activeVariableField = ref('')
const variableSearch = ref('')
const activeInputParameterIndex = ref<number | null>(null)
const activeInputVariableGroupKey = ref('')
const inputVariableSearch = ref('')
const activeOutputParameterIndex = ref<number | null>(null)
const activeOutputVariableGroupKey = ref('')
const outputVariableSearch = ref('')
const activeSchemaInputMappingIndex = ref<number | null>(null)
const activeSchemaVariableGroupKey = ref('')
const schemaVariableSearch = ref('')
const activeStructuredVariableTarget = ref('')
const activeStructuredVariableGroupKey = ref('')
const structuredVariableSearch = ref('')
const activeVariableAssignmentTargetPicker = ref(false)
const activeVariableAssignmentTargetGroupKey = ref('')
const variableAssignmentTargetSearch = ref('')
const activeConditionVariableTarget = ref('')
const activeConditionVariableGroupKey = ref('')
const conditionVariableSearch = ref('')
const intentDragSourceIndex = ref<number | null>(null)
const variableFlyoutPlacement = ref<'left' | 'right'>('left')
const collapsedConfigSections = ref<Set<string>>(new Set())
const lastSavedAt = ref('')
const flowTitleEditing = ref(false)
const flowTitleDraft = ref('')
const testPanelOpen = ref(false)
const testInput = ref('hello')
const testResult = ref<Record<string, any> | null>(null)
const chatflowRunSettingsOpen = ref(false)
const chatflowTrialMessages = ref<ChatflowTrialMessage[]>([])
const chatflowSessionState = ref<ChatflowSessionState | null>(null)
const chatflowRunEvents = ref<any[]>([])
const chatflowResumeValues = ref<Record<string, string>>({})
const chatflowDebugLoading = ref(false)
const chatflowRunDebugLoading = ref(false)
const chatflowResumeSubmitting = ref(false)
const nodeTestDrawerOpen = ref(false)
const nodeTestTargetKey = ref('')
const nodeTestInputs = ref<NodeTestInputRow[]>([])
const nodeTestResult = ref<Record<string, any> | null>(null)
const nodeTestError = ref('')
const validationErrors = ref<string[]>([])
const publishDialogOpen = ref(false)
const publishing = ref(false)
const chatflowChannelsLoading = ref(false)
const chatflowChannels = ref<ChatflowChannelShell[]>([])
const workflowVersionsLoading = ref(false)
const workflowVersions = ref<WorkflowVersionLike[]>([])
const rollingBackVersionId = ref(0)
const targetedPublishedRunLoadingId = ref(0)
const targetedPublishedRunResult = ref<Record<string, any> | null>(null)
const targetedRuntimeV2RunLoadingId = ref(0)
const targetedRuntimeV2RunResult = ref<Record<string, any> | null>(null)
const workflowStatus = ref('DRAFT')
const lastTestRunStatus = ref('')
const lastTestRunId = ref(0)
const lastRunOutput = ref<Record<string, any> | null>(null)
const lastTestRunGraphSnapshot = ref('')
const workflowRunDebugDetail = ref<WorkflowRunDebugDetail | null>(null)
const chatflowRunDebugDetail = ref<ChatflowRunDebugDetail | null>(null)
const workflowRunDebugLoading = ref(false)
const runtimeV2Cancelling = ref(false)
const dirtySinceTestRun = ref(true)
const RUNTIME_V2_POLL_DELAY_MS = 350
const RUNTIME_V2_MAX_POLLS = 180
const RUNTIME_V2_CANCELLABLE_STATUSES = new Set(['RUNNING', 'INTERRUPTED'])
const openingText = ref('你好，我可以帮你处理订单、售后和产品咨询。')
const guideQuestions = ref(['查订单进度', '申请退款', '咨询发票'])
const chatflowHistorySettingsOpen = ref(false)
const chatflowHistoryRetentionRounds = ref(3)
const testProfile = ref({
  conversationId: 'conv-demo',
  userId: 'user-demo',
  channel: 'web',
  channelId: 'web-preview',
  round: 1,
})
const chatflowVariableScopes = ref<ChatflowScopeState[]>(
  buildChatflowVariableScopes().map((scope) => ({ ...scope, open: false })),
)
const chatflowConversationVariableCount = computed(() =>
  chatflowVariableScopes.value
    .filter((scope) => scope.scope === 'conversation')
    .reduce((total, scope) => total + scope.items.length, 0),
)
const chatflowUserVariableCount = computed(() =>
  chatflowVariableScopes.value
    .filter((scope) => scope.scope === 'user')
    .reduce((total, scope) => total + scope.items.length, 0),
)
const chatflowCatalogVariableDefinitions = computed<Partial<Record<'conversation' | 'user', VariableDefinition[]>>>(() => ({
  conversation: chatflowCustomVariableDefinitions('conversation'),
  user: chatflowCustomVariableDefinitions('user'),
}))
const chatflowHistorySliderStyle = computed(() => {
  const percent = Math.round((chatflowHistoryRetentionRounds.value / 20) * 100)
  return {
    background: `linear-gradient(to right, #5b5ef6 ${percent}%, #e8ebf5 ${percent}% 100%)`,
  }
})
let requestedCanvasZoom = 1
let programmaticZoomSerial = 0
let canvasLayoutRefitTimer = 0
let canvasLayoutSettledRefitTimer = 0

const nodePaletteGroups = computed<Array<{ title: string; items: PaletteEntry[] }>>(() =>
  buildNodePaletteGroups(isChatflowMode.value ? 'chatflow' : 'workflow'),
)

const outputFormatOptions = OUTPUT_FORMAT_OPTIONS
const outputParameterTypeOptions = OUTPUT_PARAMETER_TYPE_OPTIONS
const llmHiddenSchemaSections = new Set(['技能调用', '模型参数'])
const llmSkillTabs: Array<{ value: LlmSkillTabValue; label: string }> = [
  { value: 'KNOWLEDGE_BASE', label: '知识库' },
  { value: 'MCP_TOOL', label: 'MCP 工具' },
  { value: 'API_TOOL', label: 'API 工具' },
  { value: 'SUBWORKFLOW', label: '工作流' },
  { value: 'AGENT', label: '智能体' },
]
const fallbackLlmModelOptions: LlmModelOption[] = [
  {
    provider: 'OpenRouter',
    providerType: 'OPENAI_COMPATIBLE',
    providerIconKey: 'qwen',
    value: 'qwen/qwen3.5-9b',
    label: 'qwen/qwen3.5-9b',
    description: '通义千问系列模型，适合中文理解、推理和工具调用。',
    enabled: false,
  },
  {
    provider: 'OpenRouter',
    providerType: 'OPENAI_COMPATIBLE',
    providerIconKey: 'deepseek',
    value: 'deepseek/deepseek-v4-flash',
    label: 'deepseek/deepseek-v4-flash',
    description: 'DeepSeek 系列模型，适合推理、代码和通用对话。',
    enabled: false,
  },
  {
    provider: 'OpenRouter',
    providerType: 'OPENAI_COMPATIBLE',
    providerIconKey: 'mimo',
    value: 'xiaomi/mimo-v2-flash',
    label: 'xiaomi/mimo-v2-flash',
    description: '小米 MiMo 系列模型，适合轻量快速的通用任务。',
    enabled: false,
  },
]
const llmModelOptions = computed(() =>
  llmProviderModelOptions.value.length ? llmProviderModelOptions.value : fallbackLlmModelOptions,
)
const llmModelParameterFields = [
  { key: 'temperature', label: '温度', type: 'number', min: 0, max: 2, step: 0.01, placeholder: '0.7' },
  { key: 'maxTokens', label: '最大输出 Token', type: 'number', min: 1, max: 200000, step: 1, placeholder: '2048' },
  { key: 'topP', label: 'Top P', type: 'number', min: 0, max: 1, step: 0.01, placeholder: '1' },
  { key: 'frequencyPenalty', label: '频率惩罚', type: 'number', min: -2, max: 2, step: 0.01, placeholder: '0' },
  { key: 'presencePenalty', label: '存在惩罚', type: 'number', min: -2, max: 2, step: 0.01, placeholder: '0' },
  { key: 'responseFormat', label: '响应格式', type: 'select', options: ['文本', 'JSON'] },
  { key: 'stopSequences', label: '停止词', type: 'textarea', placeholder: '每行一个停止词' },
  { key: 'seed', label: '随机种子', type: 'number', min: 0, max: 2147483647, step: 1, placeholder: '可选' },
]
const llmModelParameterDefaults: Record<string, number> = {
  temperature: 0.7,
  maxTokens: 2048,
  topP: 1,
  frequencyPenalty: 0,
  presencePenalty: 0,
  seed: 0,
}
type ConditionOperatorOption = { label: string; value: ConditionOperator }
const conditionOperatorOptions: ConditionOperatorOption[] = [
  { label: '等于', value: 'equals' },
  { label: '不等于', value: 'not_equals' },
  { label: '包含', value: 'contains' },
  { label: '不包含', value: 'not_contains' },
  { label: '大于', value: 'greater_than' },
  { label: '大于等于', value: 'greater_or_equal' },
  { label: '小于', value: 'less_than' },
  { label: '小于等于', value: 'less_or_equal' },
  { label: '长度大于', value: 'length_greater_than' },
  { label: '长度大于等于', value: 'length_greater_or_equal' },
  { label: '长度小于', value: 'length_less_than' },
  { label: '长度小于等于', value: 'length_less_or_equal' },
  { label: '为空', value: 'is_empty' },
  { label: '不为空', value: 'is_not_empty' },
  { label: '为真', value: 'is_true' },
  { label: '为假', value: 'is_false' },
]
const conditionOperatorOptionByValue = new Map(conditionOperatorOptions.map((option) => [option.value, option]))
const conditionStringOperatorValues: ConditionOperator[] = [
  'equals',
  'not_equals',
  'contains',
  'not_contains',
  'length_greater_than',
  'length_greater_or_equal',
  'length_less_than',
  'length_less_or_equal',
  'is_empty',
  'is_not_empty',
]
const conditionNumberOperatorValues: ConditionOperator[] = [
  'equals',
  'not_equals',
  'greater_than',
  'greater_or_equal',
  'less_than',
  'less_or_equal',
  'is_empty',
  'is_not_empty',
]
const conditionBooleanOperatorValues: ConditionOperator[] = ['equals', 'not_equals', 'is_empty', 'is_not_empty', 'is_true', 'is_false']
const conditionObjectOperatorValues: ConditionOperator[] = ['contains', 'not_contains', 'is_empty', 'is_not_empty']
const conditionArrayOperatorValues: ConditionOperator[] = [
  'contains',
  'not_contains',
  'length_greater_than',
  'length_greater_or_equal',
  'length_less_than',
  'length_less_or_equal',
  'is_empty',
  'is_not_empty',
]

const icons = {
  START: markRaw(Connection),
  LLM: markRaw(Cpu),
  CONDITION: markRaw(Operation),
  KNOWLEDGE: markRaw(DataAnalysis),
  API_CALL: markRaw(Share),
  TOOL_CALL: markRaw(Tools),
  EXECUTE_WORKFLOW: markRaw(Connection),
  AGENT_CALL: markRaw(User),
  TRANSFER_TO_HUMAN: markRaw(User),
  CODE: markRaw(Tools),
  TEXT_PROCESS: markRaw(Operation),
  JSON_PARSE: markRaw(DataAnalysis),
  VARIABLE_AGGREGATION: markRaw(Operation),
  VARIABLE_ASSIGN: markRaw(Connection),
  INTENT_RECOGNITION: markRaw(Operation),
  MESSAGE: markRaw(ChatDotRound),
  QUESTION: markRaw(ChatLineRound),
  HUMAN_INPUT: markRaw(User),
  INFORMATION_COLLECTION: markRaw(DataAnalysis),
  END: markRaw(Finished),
}

function createDefaultGraph() {
  return isChatflowMode.value ? createDefaultChatflowGraph() : createDefaultWorkflowGraph()
}

function defaultForm() {
  return isChatflowMode.value
    ? { name: '', description: '通过画布创建的 Chatflow' }
    : { name: '', description: '通过画布创建的工作流' }
}

const saveState = computed(() => {
  if (loading.value) return '正在载入...'
  if (saving.value) return '保存中...'
  if (canvasDirty.value) return '未保存更改'
  return lastSavedAt.value ? `已保存 ${lastSavedAt.value}` : '草稿未保存'
})
const flowTitleDisplay = computed(() =>
  form.value.name.trim() || (isChatflowMode.value ? '未命名对话流' : '未命名工作流'),
)

const selectedNode = computed(() => graph.value.nodes.find((node) => node.nodeKey === selectedNodeKey.value))
const selectedSchema = computed(() => selectedNode.value ? getNodeConfigSchema(selectedNode.value.type) : null)
const nodeCardMenuKey = ref('')
let nodeCardMenuCloseTimer: ReturnType<typeof window.setTimeout> | null = null
const nodeTitleEditing = ref(false)
const nodeTitleDraft = ref('')
const nodeTitleEditInputRef = ref<HTMLInputElement | null>(null)
const visibleConfigSections = computed(() => {
  const sections = selectedSchema.value?.sections || []
  if (selectedNode.value?.type === 'END' && endReturnMode() === 'variables') {
    return sections.filter((section) => section.title !== '回答内容')
  }
  if (selectedNode.value?.type !== 'LLM') return sections
  return sections.filter((section) => !llmHiddenSchemaSections.has(section.title))
})
const rightSidePanelOpen = computed(() => Boolean((selectedNode.value && selectedSchema.value) || testPanelOpen.value))
const canTestSelectedNode = computed(() => canRunSingleNodeTest(selectedNode.value))
const canRenameSelectedNode = computed(() => canRenameNode(selectedNode.value))
const nodeTestTarget = computed(() => graph.value.nodes.find((node) => node.nodeKey === nodeTestTargetKey.value))
function isBranchNodeType(type: string) {
  return type === 'CONDITION' || type === 'INTENT_RECOGNITION'
}
function selectedConfigPanelTitle() {
  if (!selectedNode.value || !selectedSchema.value) return ''
  return selectedNode.value.name || selectedSchema.value.title
}
const variableGroups = computed(() => selectedNode.value
  ? buildVariableCatalog(graph.value, selectedNode.value.nodeKey, {
    flowType: isChatflowMode.value ? 'CHATFLOW' : 'WORKFLOW',
    globalVariables: isChatflowMode.value ? chatflowCatalogVariableDefinitions.value : undefined,
  })
  : [])
const inlineVariableGroups = computed(() => selectedNode.value
  ? buildInlineVariableCatalog(graph.value, selectedNode.value.nodeKey, {
    flowType: isChatflowMode.value ? 'CHATFLOW' : 'WORKFLOW',
    globalVariables: isChatflowMode.value ? chatflowCatalogVariableDefinitions.value : undefined,
  })
  : [])
const selectedLlmModelOption = computed(() => {
  const selectedModelConfigId = Number(fieldValue('modelConfigId') || 0)
  const selectedModel = String(fieldValue('model') || '')
  return llmModelOptions.value.find((option) => selectedModelConfigId && option.modelConfigId === selectedModelConfigId)
    || llmModelOptions.value.find((option) => selectedModel && option.value === selectedModel)
    || null
})
const llmModelDisplayName = computed(() => selectedLlmModelOption.value?.label || String(fieldValue('model') || '请选择模型'))
const filteredLlmModelOptions = computed(() => {
  const keyword = llmModelSearchTerm.value.trim().toLowerCase()
  if (!keyword) return llmModelOptions.value
  return llmModelOptions.value.filter((option) =>
    `${option.provider} ${option.providerType} ${option.label} ${option.value}`.toLowerCase().includes(keyword),
  )
})
const modelProviderLogoUrls: Record<string, string> = {
  openai: openaiLogoUrl,
  anthropic: anthropicLogoUrl,
  gemini: geminiLogoUrl,
  azure: azureLogoUrl,
  ollama: ollamaLogoUrl,
  compatible: compatibleLogoUrl,
}
function modelProviderLogoSrc(iconKey: string) {
  return modelProviderLogoUrls[iconKey] || ''
}
function modelProviderIconText(iconKey: string) {
  const labels: Record<string, string> = {
    qwen: 'Q',
    mimo: 'Mi',
    openai: 'AI',
    anthropic: 'A',
    gemini: 'G',
    azure: 'Az',
    ollama: 'Ol',
    deepseek: 'DS',
    openrouter: 'OR',
    doubao: '豆',
    compatible: 'AI',
  }
  return labels[iconKey] || 'AI'
}
const filteredLlmSkillResources = computed(() => {
  const keyword = llmSkillSearch.value.trim().toLowerCase()
  return llmSkillChoicesForTab(activeLlmSkillTab.value)
    .filter((resource) =>
      !keyword || `${resource.name} ${resource.description}`.toLowerCase().includes(keyword),
    )
    .slice(0, 20)
})

const labelHiddenConfigFieldTypes = new Set([
  'output-parameters',
  'aggregation-output-summary',
  'input-parameters',
  'condition-branches',
  'switch',
  'end-response',
  'end-answer-content',
  'question-options',
  'collection-fields',
  'intent-rows',
  'resource-adapter-badge',
  'schema-input-mappings',
  'legacy-resource-debug',
  'json-field-mappings',
  'aggregation-groups',
  'aggregation-sources',
  'variable-assignment',
  'human-input-schema',
])

function shouldShowConfigFieldLabel(fieldType: string) {
  return !labelHiddenConfigFieldTypes.has(fieldType)
}

function hasConditionBranchField(section: { fields: Array<{ type: string }> }) {
  return section.fields.some((field) => field.type === 'condition-branches')
}

function configSectionKey(title: string) {
  return `${selectedNode.value?.nodeKey || 'none'}:${title}`
}

function configSectionDomSlug(title: string) {
  return `${selectedNode.value?.nodeKey || 'none'}-${title}`.replace(/[^\w\u4e00-\u9fa5-]+/g, '-')
}

function configSectionTestId(title: string) {
  return `config-section-${title}`
}

function configSectionContentId(title: string) {
  return `config-section-content-${configSectionDomSlug(title)}`
}

function isConfigSectionCollapsed(title: string) {
  return collapsedConfigSections.value.has(configSectionKey(title))
}

function toggleConfigSection(title: string) {
  const key = configSectionKey(title)
  const next = new Set(collapsedConfigSections.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  collapsedConfigSections.value = next
}

function markCanvasUnsaved() {
  canvasDirty.value = true
}

function startFlowTitleEdit() {
  flowTitleDraft.value = form.value.name
  flowTitleEditing.value = true
  void nextTick(() => {
    const input = document.querySelector('.title-input input') as HTMLInputElement | null
    input?.focus()
    input?.select()
  })
}

function commitFlowTitleEdit() {
  if (!flowTitleEditing.value) return
  const nextName = flowTitleDraft.value.trim()
  if (nextName !== form.value.name) {
    form.value = { ...form.value, name: nextName }
    markCanvasUnsaved()
  }
  flowTitleEditing.value = false
}

function cancelFlowTitleEdit() {
  flowTitleDraft.value = form.value.name
  flowTitleEditing.value = false
}
const operationModeLabel = computed(() => operationModeTitle(operationMode.value))
const canvasZoomLabel = computed(() => formatCanvasZoomLabel(canvasZoom.value))
type NodeTestReadableRow = { key: string; value: string }
const nodeTestReasoning = computed(() => {
  if (!nodeTestResult.value) return '暂无推理内容'
  const values = Object.values(nodeTestResult.value.output || {})
  return values.length ? String(values[0]) : '暂无推理内容'
})
const nodeTestSkillCalls = computed(() => {
  const output = nodeTestResult.value?.output || {}
  const toolCalls = output.toolCalls
  if (Array.isArray(toolCalls) && toolCalls.length) {
    return toolCalls
      .map((call) => `${call.toolName || call.name}: ${call.success ? '成功' : '失败'}`)
      .join('；')
  }
  const resources = nodeTestTarget.value?.type === 'LLM' ? (nodeTestTarget.value.config.resources || []) : []
  return Array.isArray(resources) && resources.length ? `${resources.length} 个资源参与` : '无'
})
const nodeTestInputReadableRows = computed(() => readableNodeTestRows(nodeTestResult.value?.input || {}))
const nodeTestOutputReadableRows = computed(() => readableNodeTestRows(nodeTestResult.value?.output || {}))
const filteredNodePaletteGroups = computed(() => {
  return filterNodePaletteGroups(nodePaletteGroups.value, nodePaletteSearch.value)
})
const publishValidationErrors = computed(() => validateWorkflowGraph(graph.value).errors)
const debugDockErrors = computed(() => mergeWorkflowValidationErrors(validationErrors.value, publishValidationErrors.value))
const effectiveDirtySinceTestRun = computed(() =>
  dirtySinceTestRun.value && lastTestRunGraphSnapshot.value !== currentGraphSnapshot(),
)
const publishGate = computed(() =>
  isChatflowMode.value
    ? evaluateChatflowPublishGate({
      lastRunStatus: lastTestRunStatus.value,
      dirtySinceTestRun: effectiveDirtySinceTestRun.value,
    })
    : evaluateWorkflowPublishGate({
      validationErrors: publishValidationErrors.value,
      lastTestRunStatus: lastTestRunStatus.value,
      dirtySinceTestRun: effectiveDirtySinceTestRun.value,
    }),
)
const openApiEndpoint = computed(() =>
  isChatflowMode.value
    ? buildChatflowOpenShell({ chatflowId: workflowId.value, channel: testProfile.value.channel }).endpoint
    : `/api/v1/workflows/${workflowId.value || '{workflowId}'}/runs`,
)
const openApiSample = computed(() => JSON.stringify({
  input: isChatflowMode.value
    ? buildChatflowRunInput({ message: testInput.value, ...testProfile.value, historyRetentionRounds: chatflowHistoryRetentionRounds.value })
    : {
      userMessage: testInput.value,
      USER_INPUT: testInput.value,
    },
}, null, 2))
const chatflowChannelRows = computed<ChatflowChannelRow[]>(() => buildChatflowChannelRows(chatflowChannels.value))
const workflowVersionRows = computed<WorkflowVersionRow[]>(() => buildWorkflowVersionRows(workflowVersions.value))
const nextPublishVersionName = computed(() => `v${workflowVersionRows.value.length + 1}`)
const publishNotes = computed(() => {
  const runStatus = lastTestRunStatus.value || '未运行'
  return `${isChatflowMode.value ? 'Chatflow' : 'Workflow'} 草稿发布，最近试运行：${runStatus}`
})
const chatflowWelcome = computed(() => buildChatflowWelcomeState(
  isChatflowMode.value ? openingText.value : '',
  isChatflowMode.value ? guideQuestions.value : [],
))
const chatflowTimelineRows = computed(() => formatChatflowTimeline(chatflowRunEvents.value))
const chatflowRunStreamEvents = computed(() => {
  const resultEvents = testResult.value?.streamEvents
  if (Array.isArray(resultEvents) && resultEvents.length) return resultEvents
  const debugEvents = chatflowRunDebugDetail.value?.streamEvents
  return Array.isArray(debugEvents) ? debugEvents : []
})
const chatflowDebugStreamPreview = computed(() =>
  buildChatflowStreamPreview(
    chatflowRunStreamEvents.value,
    (testResult.value?.output || chatflowRunDebugDetail.value?.output || lastRunOutput.value || {}) as Record<string, unknown>,
  ),
)
const chatflowVariableRows = computed(() => flattenChatflowVariables(chatflowSessionState.value?.variables || {}))
const chatflowWaitingEvent = computed(() => chatflowSessionState.value?.waitingEvent || null)
const chatflowCheckpoint = computed(() => chatflowSessionState.value?.checkpoint || null)
const chatflowRunDebugSummary = computed(() => summarizeChatflowRunDebug(chatflowRunDebugDetail.value || {
  runId: lastTestRunId.value,
  status: lastTestRunStatus.value,
  session: chatflowSessionState.value || undefined,
  nodeDetails: [],
}))
const chatflowRunCallTreeRows = computed(() => buildChatflowRunCallTree(chatflowRunDebugDetail.value))
const chatflowRunFlamegraphRows = computed(() => buildChatflowRunFlamegraph(chatflowRunDebugDetail.value))
const chatflowRunNodeDetails = computed(() => buildChatflowRunNodeDetails(chatflowRunDebugDetail.value))
const activeChatflowDebugNode = computed(() => selectedRunNodeDetail(chatflowRunNodeDetails.value))
const workflowRunDebugSummary = computed(() => summarizeWorkflowRunDebug(workflowRunDebugDetail.value || {
  runId: lastTestRunId.value,
  status: lastTestRunStatus.value,
  elapsedMs: 0,
  nodeDetails: [],
}))
const workflowRunCallTreeRows = computed(() => buildWorkflowRunCallTree(workflowRunDebugDetail.value))
const workflowRunFlamegraphRows = computed(() => buildWorkflowRunFlamegraph(workflowRunDebugDetail.value))
const workflowRunNodeDetails = computed(() => workflowRunDebugDetail.value?.nodeDetails || [])
const activeWorkflowDebugNode = computed(() => selectedRunNodeDetail(workflowRunNodeDetails.value))
const activeRunNodeDetails = computed(() => isChatflowMode.value ? chatflowRunNodeDetails.value : workflowRunNodeDetails.value)
const canCancelRuntimeV2Run = computed(() => {
  const runId = Number(lastTestRunId.value || 0)
  const runtimeVersion = String(testResult.value?.runtimeVersion || '').trim().toLowerCase()
  const status = String(lastTestRunStatus.value || testResult.value?.status || '').trim().toUpperCase()
  return runId > 0 && runtimeVersion === 'v2' && RUNTIME_V2_CANCELLABLE_STATUSES.has(status)
})
const runPathEdgeClassesById = computed(() => deriveRunPathEdgeClasses(graph.value.edges, activeRunNodeDetails.value))
const nodeRunStateByKey = computed(() => {
  const map = new Map<string, WorkflowRunNodeDetail>()
  activeRunNodeDetails.value.forEach((node) => {
    const key = String(node.nodeKey || '')
    if (key) map.set(key, node)
  })
  optimisticRunNodeKeys.value.forEach((key) => {
    if (!map.has(key)) {
      map.set(key, {
        nodeKey: key,
        status: 'RUNNING',
        elapsedMs: 0,
      })
    }
  })
  return map
})

function runPathEdgeClasses(edgeId: string) {
  return runPathEdgeClassesById.value.get(edgeId) || []
}
const chatflowResumeFields = computed<ChatflowResumeField[]>(() =>
  buildChatflowResumeFields((chatflowWaitingEvent.value?.payload || chatflowCheckpoint.value?.resumeSchema || {}) as Record<string, any>),
)
const runOutputRows = computed(() => {
  const output = testResult.value?.output || {}
  return Object.entries(output).map(([key, value]) => ({
    key,
    value: formatRunOutputValue(value),
  }))
})
const filteredVariableGroups = computed(() => {
  const keyword = variableSearch.value.trim().toLowerCase()
  if (!keyword) return inlineVariableGroups.value
  return inlineVariableGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.label} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
const inlineVariableOptions = computed(() =>
  filteredVariableGroups.value.flatMap((group) =>
    group.items.map((item) => ({
      group,
      groupKey: variableGroupKey(group),
      item,
    })),
  ).slice(0, 24),
)
const filteredInputVariableGroups = computed(() => {
  const keyword = inputVariableSearch.value.trim().toLowerCase()
  if (!keyword) return variableGroups.value
  return variableGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.label} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
const activeInputVariableGroup = computed(() => {
  const groups = filteredInputVariableGroups.value
  if (groups.length === 0 || !activeInputVariableGroupKey.value) return null
  return groups.find((group) => variableGroupKey(group) === activeInputVariableGroupKey.value) || null
})
const filteredOutputVariableGroups = computed(() => {
  const keyword = outputVariableSearch.value.trim().toLowerCase()
  if (!keyword) return variableGroups.value
  return variableGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.label} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
const activeOutputVariableGroup = computed(() => {
  const groups = filteredOutputVariableGroups.value
  if (groups.length === 0 || !activeOutputVariableGroupKey.value) return null
  return groups.find((group) => variableGroupKey(group) === activeOutputVariableGroupKey.value) || null
})
const filteredSchemaVariableGroups = computed(() => {
  const keyword = schemaVariableSearch.value.trim().toLowerCase()
  if (!keyword) return variableGroups.value
  return variableGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.label} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
const activeSchemaVariableGroup = computed(() => {
  const groups = filteredSchemaVariableGroups.value
  if (groups.length === 0 || !activeSchemaVariableGroupKey.value) return null
  return groups.find((group) => variableGroupKey(group) === activeSchemaVariableGroupKey.value) || null
})
const variableAssignmentTargetGroups = computed<VariableAssignmentTargetGroup[]>(() => buildVariableAssignmentTargetGroups())
const filteredVariableAssignmentTargetGroups = computed(() => {
  const keyword = variableAssignmentTargetSearch.value.trim().toLowerCase()
  if (!keyword) return variableAssignmentTargetGroups.value
  return variableAssignmentTargetGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.scopeLabel} ${item.variable} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
const activeVariableAssignmentTargetGroup = computed(() => {
  const groups = filteredVariableAssignmentTargetGroups.value
  if (groups.length === 0 || !activeVariableAssignmentTargetGroupKey.value) return null
  return groups.find((group) => group.key === activeVariableAssignmentTargetGroupKey.value) || null
})
const filteredStructuredVariableGroups = computed(() => {
  const keyword = structuredVariableSearch.value.trim().toLowerCase()
  if (!keyword) return variableGroups.value
  return variableGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.label} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
const activeStructuredVariableGroup = computed(() => {
  const groups = filteredStructuredVariableGroups.value
  if (groups.length === 0 || !activeStructuredVariableGroupKey.value) return null
  return groups.find((group) => variableGroupKey(group) === activeStructuredVariableGroupKey.value) || null
})
const filteredConditionVariableGroups = computed(() => {
  const keyword = conditionVariableSearch.value.trim().toLowerCase()
  if (!keyword) return variableGroups.value
  return variableGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.label} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})
const activeConditionVariableGroup = computed(() => {
  const groups = filteredConditionVariableGroups.value
  if (groups.length === 0 || !activeConditionVariableGroupKey.value) return null
  return groups.find((group) => variableGroupKey(group) === activeConditionVariableGroupKey.value) || null
})

const flowNodes = computed<Node[]>({
  get() {
    return graph.value.nodes.map((node) => ({
      id: node.nodeKey,
      type: 'coze',
      position: node.position,
      data: {
        nodeKey: node.nodeKey,
        type: node.type,
        name: node.name,
        outputVariable: primaryOutputVariable(node.config),
        inputVariables: nodeInputVariableNames(node),
        outputVariables: nodeOutputVariableNames(node),
        conditionBranches: branchSourceHandles(node.type, node.config),
        runStatus: nodeRunStatus(node.nodeKey),
        runStatusLabel: nodeRunStatusLabel(node.nodeKey),
        runElapsedLabel: nodeRunElapsedLabel(node.nodeKey),
      },
      draggable: true,
    }))
  },
  set(nextNodes) {
    const nodePositions = new Map(nextNodes.map((node) => [node.id, node.position]))
    let changed = false
    const nextGraphNodes = graph.value.nodes.map((node) => {
      const position = nodePositions.get(node.nodeKey)
      if (!position) return node
      if (node.position.x !== position.x || node.position.y !== position.y) changed = true
      return position ? { ...node, position } : node
    })
    if (!changed) return
    graph.value = {
      ...graph.value,
      nodes: nextGraphNodes,
    }
    markGraphDirty()
  },
})

const flowEdges = computed<Edge[]>({
  get() {
    return graph.value.edges.map((edge) => ({
      id: edge.id,
      source: edge.sourceNodeKey,
      target: edge.targetNodeKey,
      type: 'coze',
      sourceHandle: edgeSourceHandle(edge),
      selected: selectedEdgeId.value === edge.id,
      markerEnd: MarkerType.ArrowClosed,
      data: {
        condition: edge.condition,
      },
    }))
  },
  set(nextEdges) {
    const nextEdgeSignature = nextEdges
      .map((edge) => `${edge.id}:${edge.source}->${edge.target}`)
      .sort()
      .join('|')
    const currentEdgeSignature = graph.value.edges
      .map((edge) => `${edge.id}:${edge.sourceNodeKey}->${edge.targetNodeKey}`)
      .sort()
      .join('|')
    if (nextEdgeSignature === currentEdgeSignature) return
    const currentConditions = new Map(
      graph.value.edges.map((edge) => [edge.id, edge.condition]),
    )
    graph.value = {
      ...graph.value,
      edges: nextEdges.map((edge) => ({
        id: edge.id,
        sourceNodeKey: edge.source,
        targetNodeKey: edge.target,
        condition: currentConditions.has(edge.id)
          ? currentConditions.get(edge.id) ?? null
          : conditionFromSourceHandle(edge.source, edge.sourceHandle as string | null | undefined),
      })),
    }
    markGraphDirty()
  },
})

function nodeIcon(type: WorkflowCanvasNodeType) {
  return icons[type]
}

function cozeEdgePath(edgeProps: any) {
  return getBezierPath({
    sourceX: edgeProps.sourceX,
    sourceY: edgeProps.sourceY,
    sourcePosition: edgeProps.sourcePosition,
    targetX: edgeProps.targetX,
    targetY: edgeProps.targetY,
    targetPosition: edgeProps.targetPosition,
  })
}

function edgeInsertButtonStyle(path: ReturnType<typeof getBezierPath>) {
  const [, labelX, labelY] = path
  return {
    transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
  }
}

function edgeInsertPaletteStyle(path: ReturnType<typeof getBezierPath>) {
  const [, labelX, labelY] = path
  const inverseZoom = 1 / Math.max(CANVAS_ZOOM_MIN, canvasZoom.value || 1)
  return {
    transform: `translate(1.75rem, -50%) translate(${labelX}px, ${labelY}px) scale(${inverseZoom})`,
    transformOrigin: '0 50%',
  }
}

function edgeInsertPosition(path: ReturnType<typeof getBezierPath>) {
  const [, labelX, labelY] = path
  return {
    x: Math.max(80, labelX - 210),
    y: Math.max(40, labelY - 52),
  }
}

function edgeConnectsNode(edge: { source?: string; target?: string }, nodeKey: string) {
  return Boolean(nodeKey && (edge.source === nodeKey || edge.target === nodeKey))
}

function isEdgeSelected(edge: { id?: string; source?: string; target?: string }) {
  return selectedEdgeId.value === edge.id || edgeConnectsNode(edge, selectedNodeKey.value)
}

function isEdgeHovered(edge: { id?: string; source?: string; target?: string }) {
  if (isEdgeSelected(edge)) return false
  return hoveredEdgeId.value === edge.id
    || edgeInsertPaletteId.value === edge.id
    || edgeConnectsNode(edge, hoveredNodeKey.value)
}

function primaryOutputVariable(config: Record<string, any>) {
  return normalizeOutputConfig(config).parameters[0]?.name || 'output'
}

function nodeInputVariableNames(node: WorkflowCanvasNode) {
  if (node.type === 'START') return []
  const inputs = normalizeInputConfig(node.config).parameters
    .map((parameter) => parameter.name.trim())
    .filter(Boolean)
  if (node.type === 'END' && inputs.length === 0) {
    return [String(node.config.outputVariable || 'output')]
  }
  return inputs
}

function nodeOutputVariableNames(node: WorkflowCanvasNode) {
  if (node.type === 'START') {
    return Array.isArray(node.config.outputVariables) ? node.config.outputVariables.map(String) : []
  }
  const outputs = normalizeOutputConfig(node.config).parameters
    .map((parameter) => parameter.name.trim())
    .filter(Boolean)
  if (outputs.length > 0) return outputs
  if (node.type === 'CONDITION') return [String(node.config.outputVariable || 'route')]
  return [String(node.config.outputVariable || 'output')]
}

function startVariableTooltip(values: string[]) {
  return nodeVariableTooltip(values)
}

function nodeVariableTooltip(values: string[]) {
  if (!values.length) return '无变量'
  return values.map((value) => `str.${value}`).join(' · ')
}

function estimateStartVariableBadgeWidth(value: string) {
  return Math.min(170, Math.ceil(`str.${value}`.length * START_VARIABLE_CHAR_WIDTH + START_VARIABLE_BADGE_BASE_WIDTH))
}

function startVisibleVariables(values: string[]) {
  return nodeVisibleVariables(values)
}

function nodeVisibleVariables(values: string[]) {
  const visible: string[] = []
  let usedWidth = 0
  for (let index = 0; index < values.length; index += 1) {
    const width = estimateStartVariableBadgeWidth(values[index])
    const nextWidth = usedWidth + (visible.length ? START_VARIABLE_GAP : 0) + width
    const hiddenAfterThis = values.length - index - 1
    const reserveMoreWidth = hiddenAfterThis > 0
      ? START_VARIABLE_GAP + START_VARIABLE_MORE_WIDTH
      : 0
    if (visible.length > 0 && nextWidth + reserveMoreWidth > START_VARIABLE_LINE_BUDGET) break
    visible.push(values[index])
    usedWidth = nextWidth
  }
  return visible
}

function startHasHiddenVariables(values: string[]) {
  return nodeHasHiddenVariables(values)
}

function nodeHasHiddenVariables(values: string[]) {
  return nodeVisibleVariables(values).length < values.length
}

function formatRunOutputValue(value: unknown) {
  if (value === null || value === undefined) return '空'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function debugStatusLabel(status: string | undefined) {
  const normalized = String(status || '').toUpperCase()
  return {
    SUCCEEDED: '成功',
    COMPLETED: '成功',
    RUNNING: '运行中',
    FAILED: '失败',
    INTERRUPTED: '等待输入',
    WAITING: '等待输入',
    PENDING: '等待',
    SKIPPED: '跳过',
  }[normalized] || normalized || '未知'
}

function nodeRunStatus(nodeKey: string) {
  return String(nodeRunStateByKey.value.get(nodeKey)?.status || '')
}

function nodeRunStatusLabel(nodeKey: string) {
  const status = nodeRunStatus(nodeKey)
  return status ? debugStatusLabel(status) : ''
}

function nodeRunElapsedLabel(nodeKey: string) {
  const detail = nodeRunStateByKey.value.get(nodeKey)
  if (!detail) return ''
  const elapsed = Number(detail.elapsedMs || 0)
  return `${elapsed}ms`
}

function debugCallTreeDepth(nodeKey: string) {
  void nodeKey
  return 0
}

function selectedRunNodeDetail(nodes: WorkflowRunNodeDetail[]): WorkflowRunNodeDetail | null {
  if (!nodes.length) return null
  const selected = nodes.find((node, index) => workflowRunNodeDetailKey(node, index) === selectedDebugNodeKey.value)
  return selected || nodes[0]
}

function selectDebugNode(detailKey: string) {
  selectedDebugNodeKey.value = detailKey
}

function ensureSelectedDebugNode(nodes: WorkflowRunNodeDetail[]) {
  debugTraceDetailMode.value = 'flame'
  if (!nodes.length) {
    selectedDebugNodeKey.value = ''
    return
  }
  const stillExists = nodes.some((node, index) => workflowRunNodeDetailKey(node, index) === selectedDebugNodeKey.value)
  if (!stillExists) selectedDebugNodeKey.value = workflowRunNodeDetailKey(nodes[0], 0)
}

function debugNodeInputs(node: WorkflowRunNodeDetail | Record<string, any>) {
  return (node as any).inputs || (node as any).input || (node as any).renderedInput || {}
}

function debugNodeOutputs(node: WorkflowRunNodeDetail | Record<string, any>) {
  return (node as any).outputs || (node as any).output || {}
}

async function toggleDebugDock() {
  debugDockOpen.value = !debugDockOpen.value
  paletteOpen.value = false
  edgeInsertPaletteId.value = ''
  if (!debugDockOpen.value) return
  debugTraceDetailMode.value = 'flame'
  if (!lastTestRunId.value) return
  debugDockTab.value = 'debug'
  if (isChatflowMode.value) {
    await loadChatflowDebugState(workflowId.value, testResult.value || { runId: lastTestRunId.value })
  } else {
    await loadWorkflowRunDebugDetail(lastTestRunId.value)
  }
}

function closeDebugDock() {
  debugDockOpen.value = false
  paletteOpen.value = false
  edgeInsertPaletteId.value = ''
}

function handleViewportChange(viewport: { zoom?: number }) {
  if (programmaticZoomSerial > 0) return
  if (typeof viewport.zoom === 'number') {
    requestedCanvasZoom = clampCanvasZoom(viewport.zoom)
    canvasZoom.value = requestedCanvasZoom
  }
}

function requestCanvasLayoutRefit() {
  if (typeof window === 'undefined' || canvasTab.value !== 'compose') return
  window.clearTimeout(canvasLayoutRefitTimer)
  window.clearTimeout(canvasLayoutSettledRefitTimer)
  const refitCanvas = async () => {
    if (canvasTab.value !== 'compose' || flowNodes.value.length === 0) return
    await fitView({ padding: canvasFitViewPadding(), duration: CANVAS_ZOOM_ANIMATION_MS })
    requestedCanvasZoom = clampCanvasZoom(getViewport().zoom || requestedCanvasZoom)
    canvasZoom.value = requestedCanvasZoom
  }
  void nextTick(() => {
    window.clearTimeout(canvasLayoutRefitTimer)
    window.clearTimeout(canvasLayoutSettledRefitTimer)
    canvasLayoutRefitTimer = window.setTimeout(() => {
      void refitCanvas()
    }, 60)
    canvasLayoutSettledRefitTimer = window.setTimeout(() => {
      void refitCanvas()
    }, 260)
  })
}

function canvasFitViewPadding() {
  return 0.18
}

function isZoomPresetActive(preset: number) {
  return Math.abs(canvasZoom.value - preset) < 0.01
}

async function applyCanvasZoom(zoom: number) {
  const targetZoom = clampCanvasZoom(zoom)
  const requestId = programmaticZoomSerial + 1
  programmaticZoomSerial = requestId
  requestedCanvasZoom = targetZoom
  canvasZoom.value = targetZoom
  zoomMenuOpen.value = false
  await zoomTo(targetZoom, { duration: CANVAS_ZOOM_ANIMATION_MS })
  if (requestId === programmaticZoomSerial) {
    requestedCanvasZoom = clampCanvasZoom(getViewport().zoom || targetZoom)
    canvasZoom.value = requestedCanvasZoom
    programmaticZoomSerial = 0
  }
}

function increaseCanvasZoom() {
  void applyCanvasZoom(nextCanvasZoom(requestedCanvasZoom, 'in'))
}

function decreaseCanvasZoom() {
  void applyCanvasZoom(nextCanvasZoom(requestedCanvasZoom, 'out'))
}

function flamegraphRowStyle(row: WorkflowRunFlamegraphRow, rows: WorkflowRunFlamegraphRow[], index: number): Record<string, string> {
  const maxEndMs = rows.reduce((max, item) => Math.max(max, Number(item.startMs || 0) + Number(item.durationMs || 0)), 0)
  const syntheticTotal = Math.max(rows.length, 1)
  const total = maxEndMs > 0 ? maxEndMs : syntheticTotal
  const startUnit = maxEndMs > 0 ? Number(row.startMs || 0) : index
  const durationUnit = maxEndMs > 0 ? Number(row.durationMs || 0) : 1
  const left = Math.min(82, Math.max(0, (startUnit / total) * 82))
  const rawWidth = (durationUnit / total) * 86
  const readableWidth = Math.max(maxEndMs > 0 && Number(row.durationMs || 0) > 0 ? 18 : 30, rawWidth)
  const width = Math.min(Math.max(12, 96 - left), readableWidth)
  return {
    '--flame-left': `${left}%`,
    '--flame-width': `${width}%`,
  }
}

function readableNodeTestValue(value: unknown) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function readableNodeTestRows(value: unknown): NodeTestReadableRow[] {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const rows = Object.entries(value as Record<string, unknown>)
    if (rows.length) {
      return rows.map(([key, rowValue]) => ({
        key,
        value: readableNodeTestValue(rowValue),
      }))
    }
  }
  return [{ key: 'value', value: readableNodeTestValue(value) }]
}

async function copyNodeTestReadableValue(value: unknown) {
  if (!navigator.clipboard) return
  await navigator.clipboard.writeText(readableNodeTestValue(value))
  message.success('已复制')
}

function buildResumePayload(fields: ChatflowResumeField[], values: Record<string, string>) {
  const payload: Record<string, any> = {}
  for (const field of fields) {
    const raw = values[field.key] ?? ''
    if (field.key === 'approved') {
      payload[field.key] = ['true', '1', 'yes', 'y', '是', '同意'].includes(raw.trim().toLowerCase())
      continue
    }
    if (field.key === 'payload') {
      payload[field.key] = parseResumePayloadValue(raw)
      continue
    }
    payload[field.key] = raw
  }
  return payload
}

function parseResumePayloadValue(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return value
  }
}

function addNode(type: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>) {
  const offset = graph.value.nodes.length * 32
  graph.value = addWorkflowNode(graph.value, type, { x: 360 + offset, y: 260 + offset })
  paletteOpen.value = false
  edgeInsertPaletteId.value = ''
  nodePaletteSearch.value = ''
  markGraphDirty()
}

function cloneNodeConfig(config: Record<string, any> = {}) {
  return JSON.parse(JSON.stringify(config)) as Record<string, any>
}

function isFixedNode(node?: WorkflowCanvasNode | null) {
  return node?.type === 'START' || node?.type === 'END' || node?.nodeKey === 'start' || node?.nodeKey === 'end'
}

function canRenameNode(node?: WorkflowCanvasNode | null) {
  return Boolean(node && !isFixedNode(node))
}

function clearNodeCardMenuCloseTimer() {
  if (nodeCardMenuCloseTimer === null) return
  window.clearTimeout(nodeCardMenuCloseTimer)
  nodeCardMenuCloseTimer = null
}

function openNodeCardMenu(nodeKey: string) {
  clearNodeCardMenuCloseTimer()
  nodeCardMenuKey.value = nodeKey
  paletteOpen.value = false
  edgeInsertPaletteId.value = ''
}

function scheduleCloseNodeCardMenu(nodeKey: string) {
  clearNodeCardMenuCloseTimer()
  nodeCardMenuCloseTimer = window.setTimeout(() => {
    if (nodeCardMenuKey.value === nodeKey) nodeCardMenuKey.value = ''
    nodeCardMenuCloseTimer = null
  }, 120)
}

function startSelectedNodeTitleEdit() {
  if (!selectedNode.value || !canRenameNode(selectedNode.value)) return
  nodeTitleDraft.value = selectedNode.value.name || selectedConfigPanelTitle()
  nodeTitleEditing.value = true
  void nextTick(() => nodeTitleEditInputRef.value?.focus())
}

function startNodeRename(nodeKey: string) {
  const node = graph.value.nodes.find((item) => item.nodeKey === nodeKey)
  if (!canRenameNode(node)) return
  selectedNodeKey.value = nodeKey
  nodeCardMenuKey.value = ''
  void nextTick(startSelectedNodeTitleEdit)
}

function commitNodeTitleEdit() {
  if (!selectedNode.value || !nodeTitleEditing.value) return
  const nextName = nodeTitleDraft.value.trim()
  nodeTitleEditing.value = false
  if (!nextName || nextName === selectedNode.value.name) return
  graph.value = renameWorkflowNode(graph.value, selectedNode.value.nodeKey, nextName)
  markGraphDirty()
}

function cancelNodeTitleEdit() {
  nodeTitleEditing.value = false
  nodeTitleDraft.value = selectedNode.value?.name || ''
}

function duplicateNode(nodeKey: string) {
  const source = graph.value.nodes.find((node) => node.nodeKey === nodeKey)
  if (!source || isFixedNode(source)) return
  const position = { x: source.position.x + 64, y: source.position.y + 64 }
  const graphWithNode = addWorkflowNode(graph.value, source.type as Exclude<WorkflowCanvasNodeType, 'START' | 'END'>, position)
  const inserted = graphWithNode.nodes[graphWithNode.nodes.length - 1]
  const config = cloneNodeConfig(source.config)
  config.ui = {
    ...(config.ui || {}),
    position,
  }
  graph.value = {
    nodes: graphWithNode.nodes.map((node) =>
      node.nodeKey === inserted.nodeKey
        ? { ...inserted, name: `${source.name || inserted.name} 副本`, config, position }
        : node,
    ),
    edges: graphWithNode.edges,
  }
  selectedNodeKey.value = inserted.nodeKey
  nodeCardMenuKey.value = ''
  markGraphDirty()
}

function insertNodeOnEdge(
  type: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>,
  edgeId: string,
  position: { x: number; y: number },
) {
  graph.value = insertWorkflowNodeOnEdge(graph.value, type, edgeId, position)
  const insertedNode = graph.value.nodes[graph.value.nodes.length - 1]
  selectedNodeKey.value = insertedNode?.nodeKey || ''
  selectedEdgeId.value = ''
  hoveredEdgeId.value = ''
  hoveredNodeKey.value = ''
  edgeInsertPaletteId.value = ''
  nodePaletteSearch.value = ''
  markGraphDirty()
}

function removeEdge(edgeId: string) {
  graph.value = deleteWorkflowEdge(graph.value, edgeId)
  if (selectedEdgeId.value === edgeId) selectedEdgeId.value = ''
  if (hoveredEdgeId.value === edgeId) hoveredEdgeId.value = ''
  if (edgeInsertPaletteId.value === edgeId) edgeInsertPaletteId.value = ''
  markGraphDirty()
}

function openEdgeInsertPalette(edgeId: string) {
  if (edgeInsertPaletteId.value === edgeId) {
    clearEdgeInteractionState()
    nodePaletteSearch.value = ''
    void nextTick(() => canvasStageRef.value?.focus())
    return
  }
  selectedEdgeId.value = edgeId
  hoveredEdgeId.value = edgeId
  edgeInsertPaletteId.value = edgeId
  paletteOpen.value = false
  selectedNodeKey.value = ''
  void nextTick(() => canvasStageRef.value?.focus())
}

function toggleOperationMode() {
  operationMode.value = operationMode.value === 'mouse' ? 'trackpad' : 'mouse'
  localStorage.setItem('hify.canvas.operationMode', operationMode.value)
}

function removeNode(nodeKey: string) {
  graph.value = deleteWorkflowNode(graph.value, nodeKey)
  if (selectedNodeKey.value === nodeKey) selectedNodeKey.value = ''
  if (nodeCardMenuKey.value === nodeKey) nodeCardMenuKey.value = ''
  markGraphDirty()
}

function removeNodeFromMenu(nodeKey: string) {
  removeNode(nodeKey)
  nodeCardMenuKey.value = ''
}

function canKeyboardDeleteNode() {
  return Boolean(selectedNode.value && selectedNode.value.type !== 'START' && selectedNode.value.type !== 'END')
}

function isEditableTarget(target: EventTarget | null) {
  const element = target instanceof HTMLElement ? target : null
  if (!element) return false
  return Boolean(element.closest('input, textarea, select, [contenteditable="true"], .ant-input, .ant-select, .ant-input-number, .ant-switch'))
}

function handleCanvasKeydown(event: KeyboardEvent) {
  if (!['Backspace', 'Delete'].includes(event.key)) return
  if (isEditableTarget(event.target)) return
  if (selectedEdgeId.value) {
    event.preventDefault()
    removeEdge(selectedEdgeId.value)
    return
  }
  if (!canKeyboardDeleteNode()) return
  event.preventDefault()
  removeNode(selectedNode.value!.nodeKey)
}

function closeVariablePickers() {
  activeVariableField.value = ''
  activeInputParameterIndex.value = null
  activeInputVariableGroupKey.value = ''
  activeOutputParameterIndex.value = null
  activeOutputVariableGroupKey.value = ''
  activeSchemaInputMappingIndex.value = null
  activeSchemaVariableGroupKey.value = ''
  activeStructuredVariableTarget.value = ''
  activeStructuredVariableGroupKey.value = ''
  activeVariableAssignmentTargetPicker.value = false
  activeVariableAssignmentTargetGroupKey.value = ''
  activeConditionVariableTarget.value = ''
  activeConditionVariableGroupKey.value = ''
  variableSearch.value = ''
  inputVariableSearch.value = ''
  outputVariableSearch.value = ''
  schemaVariableSearch.value = ''
  structuredVariableSearch.value = ''
  variableAssignmentTargetSearch.value = ''
  conditionVariableSearch.value = ''
}

function rootRemSize() {
  if (typeof window === 'undefined') return 16
  const parsed = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 16
}

function refreshCanvasResponsiveLayout() {
  if (typeof window === 'undefined') return
  canvasViewportWidth.value = window.innerWidth
}

function rectSnapshot(element: Element): ViewportRect {
  const rect = element.getBoundingClientRect()
  return {
    top: rect.top,
    left: rect.left,
    right: rect.right,
    bottom: rect.bottom,
    width: rect.width,
    height: rect.height,
  }
}

function variablePickerAnchorElement(target?: EventTarget | null) {
  const targetElement = target instanceof HTMLElement ? target : null
  const activeElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
  return targetElement?.closest('.variable-value-combo, .input-value-cell, .condition-value-cell')
    || activeElement?.closest('.variable-value-combo, .input-value-cell, .condition-value-cell')
    || targetElement
    || activeElement
    || document.querySelector('[data-testid="node-config-panel"]')
}

function refreshVariablePickerAnchor(target?: EventTarget | null) {
  if (typeof window === 'undefined') return
  const anchorElement = variablePickerAnchorElement(target)
  if (!anchorElement) return
  const rect = rectSnapshot(anchorElement)
  const rem = rootRemSize()
  const width = rect.width > 0 ? rect.width : 10 * rem
  const maxHeight = 24 * rem
  const gap = 0.375 * rem
  const padding = 1 * rem
  const left = Math.min(Math.max(rect.left, padding), Math.max(padding, window.innerWidth - width - padding))
  const maxTop = Math.max(padding, window.innerHeight - maxHeight - padding)
  const top = Math.min(Math.max(rect.bottom + gap, padding), maxTop)

  document.documentElement.style.setProperty('--workflow-variable-picker-left', `${left / rem}rem`)
  document.documentElement.style.setProperty('--workflow-variable-picker-top', `${top / rem}rem`)
  document.documentElement.style.setProperty('--workflow-variable-picker-width', `${width / rem}rem`)
}

function refreshVariableFlyoutAnchor(target: EventTarget | null) {
  if (typeof window === 'undefined' || !(target instanceof HTMLElement)) return
  const rect = rectSnapshot(target)
  const rem = rootRemSize()
  const width = 16 * rem
  const maxHeight = 19 * rem
  const gap = 0.5 * rem
  const padding = 0.75 * rem
  const panelRect = document.querySelector('[data-testid="node-config-panel"]')?.getBoundingClientRect()
  const sourcePanel = target.closest('.variable-popover')
  const position = computeVariableFlyoutPosition({
    triggerRect: rect,
    sourcePanelRect: sourcePanel ? rectSnapshot(sourcePanel) : null,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    flyoutWidth: width,
    flyoutMaxHeight: maxHeight,
    gap,
    padding,
    rem,
    avoidPanelLeft: panelRect?.left ?? null,
  })
  variableFlyoutPlacement.value = position.placement
  document.documentElement.style.setProperty('--workflow-variable-flyout-left', `${position.left / rem}rem`)
  document.documentElement.style.setProperty('--workflow-variable-flyout-top', `${position.top / rem}rem`)
}

function activeTextControl() {
  const element = document.activeElement
  return element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement ? element : null
}

function textControlCaretRect(control: HTMLInputElement | HTMLTextAreaElement) {
  const rect = control.getBoundingClientRect()
  const style = window.getComputedStyle(control)
  const mirror = document.createElement('div')
  const marker = document.createElement('span')
  const selectionStart = control.selectionStart ?? control.value.length
  const rem = rootRemSize()
  const mirrorProperties = [
    'box-sizing',
    'font-family',
    'font-size',
    'font-weight',
    'font-style',
    'letter-spacing',
    'line-height',
    'padding-top',
    'padding-right',
    'padding-bottom',
    'padding-left',
    'border-top-width',
    'border-right-width',
    'border-bottom-width',
    'border-left-width',
    'text-transform',
    'text-indent',
  ]

  mirrorProperties.forEach((property) => {
    mirror.style.setProperty(property, style.getPropertyValue(property))
  })
  mirror.style.position = 'fixed'
  mirror.style.left = `${rect.left / rem}rem`
  mirror.style.top = `${rect.top / rem}rem`
  mirror.style.width = `${rect.width / rem}rem`
  mirror.style.minHeight = `${rect.height / rem}rem`
  mirror.style.visibility = 'hidden'
  mirror.style.pointerEvents = 'none'
  mirror.style.whiteSpace = control instanceof HTMLTextAreaElement ? 'pre-wrap' : 'pre'
  mirror.style.overflowWrap = 'break-word'
  mirror.style.overflow = 'hidden'
  mirror.textContent = control.value.slice(0, selectionStart)
  marker.textContent = '\u200b'
  mirror.appendChild(marker)
  document.body.appendChild(mirror)
  const markerRect = marker.getBoundingClientRect()
  document.body.removeChild(mirror)

  return {
    left: markerRect.left - control.scrollLeft,
    top: markerRect.top - control.scrollTop,
    bottom: markerRect.bottom - control.scrollTop,
  }
}

function refreshInlineVariableSuggestionAnchor() {
  if (typeof window === 'undefined') return
  const control = activeTextControl()
  if (!control) return
  const controlRect = control.getBoundingClientRect()
  const caretRect = textControlCaretRect(control)
  const rem = rootRemSize()
  const padding = 1 * rem
  const maxWidth = 30 * rem
  const availableWidth = Math.max(12 * rem, controlRect.width - 2 * rem)
  const minWidth = Math.min(18 * rem, availableWidth)
  const width = Math.max(minWidth, Math.min(maxWidth, availableWidth))
  const left = Math.min(
    Math.max(caretRect.left - 0.5 * rem, controlRect.left + 0.5 * rem),
    Math.max(controlRect.left + 0.5 * rem, controlRect.right - width - 0.5 * rem),
  )
  const top = Math.min(
    Math.max(caretRect.bottom + 0.375 * rem, controlRect.top + 2 * rem),
    Math.max(padding, window.innerHeight - 16 * rem),
  )

  document.documentElement.style.setProperty('--workflow-inline-variable-picker-left', `${left / rem}rem`)
  document.documentElement.style.setProperty('--workflow-inline-variable-picker-top', `${top / rem}rem`)
  document.documentElement.style.setProperty('--workflow-inline-variable-picker-width', `${width / rem}rem`)
}

function handleGlobalVariableKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    event.stopPropagation()
    void saveCanvas()
    return
  }
  if (event.key !== 'Escape') return
  if (publishDialogOpen.value) {
    event.stopPropagation()
    publishDialogOpen.value = false
    return
  }
  if (!hasOpenVariablePicker()) return

  event.stopPropagation()
  closeVariablePickers()
}

function hasOpenVariablePicker() {
  return Boolean(
    activeVariableField.value ||
    activeInputParameterIndex.value !== null ||
    activeOutputParameterIndex.value !== null ||
    activeSchemaInputMappingIndex.value !== null ||
    activeStructuredVariableTarget.value ||
    activeVariableAssignmentTargetPicker.value ||
    activeConditionVariableTarget.value,
  )
}

function isVariablePickerInternalTarget(target: EventTarget | null) {
  const element = target instanceof Element ? target : null
  if (!element) return false
  return Boolean(element.closest([
    '.variable-popover',
    '.variable-flyout',
    '.inline-variable-suggestion-popover',
    '.variable-picker-trigger',
    '.input-variable-chip',
    '.variable-value-combo',
    '.condition-value-cell',
    '.input-value-cell',
  ].join(',')))
}

function handleGlobalVariablePointerDown(event: PointerEvent) {
  if (!hasOpenVariablePicker()) return
  if (isVariablePickerInternalTarget(event.target)) return
  closeVariablePickers()
}

function hasEdgeInteractionState() {
  return Boolean(selectedEdgeId.value || hoveredEdgeId.value || edgeInsertPaletteId.value)
}

function isEdgeInteractionTarget(target: EventTarget | null) {
  const element = target instanceof Element ? target : null
  if (!element) return false
  return Boolean(element.closest([
    '.vue-flow__edge',
    '.vue-flow__edge-interaction',
    '.edge-insert-button',
    '.edge-insert-palette',
  ].join(',')))
}

function isEdgeInteractionPoint(event: PointerEvent | MouseEvent) {
  const element = document.elementFromPoint(event.clientX, event.clientY)
  return isEdgeInteractionTarget(element || event.target)
}

function clearEdgeInteractionState() {
  selectedEdgeId.value = ''
  hoveredEdgeId.value = ''
  edgeInsertPaletteId.value = ''
}

function handleGlobalEdgePointerDown(event: PointerEvent) {
  if (!hasEdgeInteractionState()) return
  if (isEdgeInteractionTarget(event.target)) return
  clearEdgeInteractionState()
}

function nodePortKey(nodeKey: string, portType: 'source' | 'target', handleId: string | null = '') {
  return `${nodeKey}:${portType}:${handleId || ''}`
}

function isConnectionPreviewPort(nodeKey: string, portType: 'source' | 'target', handleId: string | null = '') {
  return connectionPreviewPortKey.value === nodePortKey(nodeKey, portType, handleId)
}

function clearConnectionPreview() {
  connectionPreviewPortKey.value = ''
  connectionPreviewStart.value = null
}

function handleConnectStart(event: any) {
  const handleType = event?.handleType === 'target' ? 'target' : 'source'
  connectionPreviewStart.value = {
    nodeId: String(event?.nodeId || ''),
    handleType,
  }
  connectionPreviewPortKey.value = ''
}

function handleConnectEnd() {
  clearConnectionPreview()
}

function handleGlobalConnectionPointerMove(event: PointerEvent | MouseEvent) {
  if (hoveredEdgeId.value && !edgeInsertPaletteId.value && !isEdgeInteractionPoint(event)) {
    hoveredEdgeId.value = ''
  }
  if (!connectionPreviewStart.value) return

  const expectedPortType = connectionPreviewStart.value.handleType === 'source' ? 'target' : 'source'
  const ports = Array.from(document.querySelectorAll<HTMLElement>(`.node-port.${expectedPortType}-port`))
  let nearestKey = ''
  let nearestDistance = Number.POSITIVE_INFINITY

  ports.forEach((port) => {
    const nodeKey = port.dataset.nodeKey || ''
    if (!nodeKey || nodeKey === connectionPreviewStart.value?.nodeId) return
    const rect = port.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const distance = Math.hypot(centerX - event.clientX, centerY - event.clientY)
    if (distance > CANVAS_ENDPOINT_PREVIEW_RADIUS || distance >= nearestDistance) return
    nearestDistance = distance
    nearestKey = nodePortKey(nodeKey, expectedPortType, port.dataset.handleId || '')
  })

  connectionPreviewPortKey.value = nearestKey
}

function handleConnect(connection: any) {
  clearConnectionPreview()
  graph.value = connectWorkflowNodes(
    graph.value,
    connection.source,
    connection.target,
    conditionFromSourceHandle(connection.source, connection.sourceHandle),
  )
  markGraphDirty()
}

function handleEdgeClick(event: any) {
  selectedEdgeId.value = event?.edge?.id || ''
  hoveredEdgeId.value = ''
  hoveredNodeKey.value = ''
  selectedNodeKey.value = ''
  edgeInsertPaletteId.value = ''
  void nextTick(() => canvasStageRef.value?.focus())
}

function handleEdgeMouseEnter(event: any) {
  hoveredEdgeId.value = event?.edge?.id || ''
}

function clearEdgeHover(edgeId: string) {
  if (!edgeId) return
  if (edgeInsertPaletteId.value === edgeId) return
  if (hoveredEdgeId.value === edgeId) hoveredEdgeId.value = ''
}

function handleEdgeMouseLeave(event: any) {
  const edgeId = event?.edge?.id || ''
  clearEdgeHover(edgeId)
}

function handleNodeDragStop(event: any) {
  if (!event?.node?.id || !event.node.position) return
  graph.value = moveWorkflowNode(graph.value, event.node.id, event.node.position)
  markGraphDirty()
}

function handleNodeClick(event: any) {
  selectedNodeKey.value = event?.node?.id || ''
  testPanelOpen.value = false
  nodeTestDrawerOpen.value = false
  selectedEdgeId.value = ''
  hoveredEdgeId.value = ''
  hoveredNodeKey.value = ''
  edgeInsertPaletteId.value = ''
  editingConditionBranchNameIndex.value = null
  editingConditionDefaultName.value = false
  activeVariableField.value = ''
  activeInputParameterIndex.value = null
  activeInputVariableGroupKey.value = ''
  activeOutputParameterIndex.value = null
  activeOutputVariableGroupKey.value = ''
  activeSchemaInputMappingIndex.value = null
  activeSchemaVariableGroupKey.value = ''
  activeStructuredVariableTarget.value = ''
  activeStructuredVariableGroupKey.value = ''
  variableSearch.value = ''
  inputVariableSearch.value = ''
  outputVariableSearch.value = ''
  schemaVariableSearch.value = ''
  structuredVariableSearch.value = ''
  modelPickerOpen.value = false
  modelParameterPanelOpen.value = false
  resourcePickerOpen.value = false
  llmSkillSearch.value = ''
  void nextTick(() => canvasStageRef.value?.focus())
}

function handleNodeMouseEnter(nodeKey: string) {
  hoveredNodeKey.value = nodeKey || ''
}

function handleNodeMouseLeave(nodeKey: string) {
  if (hoveredNodeKey.value === nodeKey) hoveredNodeKey.value = ''
}

function handlePaneClick() {
  selectedNodeKey.value = ''
  selectedEdgeId.value = ''
  hoveredEdgeId.value = ''
  hoveredNodeKey.value = ''
  edgeInsertPaletteId.value = ''
  editingConditionBranchNameIndex.value = null
  editingConditionDefaultName.value = false
  paletteOpen.value = false
  closeVariablePickers()
  modelPickerOpen.value = false
  modelParameterPanelOpen.value = false
  resourcePickerOpen.value = false
  activeSchemaInputMappingIndex.value = null
  activeSchemaVariableGroupKey.value = ''
  schemaVariableSearch.value = ''
  activeStructuredVariableTarget.value = ''
  activeStructuredVariableGroupKey.value = ''
  structuredVariableSearch.value = ''
  llmSkillSearch.value = ''
}

function updateSelectedNode(patch: { name?: string; config?: Record<string, any> }) {
  if (!selectedNode.value) return
  graph.value = {
    ...graph.value,
    nodes: graph.value.nodes.map((node) =>
      node.nodeKey === selectedNode.value?.nodeKey ? applyNodeConfigPatch(node, patch) : node,
    ),
  }
  markGraphDirty()
}

function fieldValue(key: string) {
  if (!selectedNode.value) return ''
  if (key === 'name') return selectedNode.value.name
  const value = selectedNode.value.config[key] as any
  if (Array.isArray(value) || (value && typeof value === 'object')) {
    return JSON.stringify(value, null, 2)
  }
  return value
}

function modelParameterDefault(key: string) {
  return llmModelParameterDefaults[key] ?? 0
}

function modelParameterNumberValue(field: { key: string; min?: number; max?: number }) {
  const fallback = modelParameterDefault(field.key)
  const raw = Number(fieldValue(field.key) || fallback)
  if (!Number.isFinite(raw)) return fallback
  const min = field.min ?? 0
  const max = field.max ?? 100000
  return Math.min(Math.max(raw, min), max)
}

function modelParameterFillPercent(field: { key: string; min?: number; max?: number }) {
  const min = field.min ?? 0
  const max = field.max ?? 100000
  if (max <= min) return 0
  return Math.round(((modelParameterNumberValue(field) - min) / (max - min)) * 100)
}

function modelParameterSliderStyle(field: { key: string; min?: number; max?: number }) {
  const percent = modelParameterFillPercent(field)
  return {
    background: `linear-gradient(to right, #5b5ef6 ${percent}%, #e8ebf5 ${percent}% 100%)`,
  }
}

function setModelParameterNumberValue(key: string, value: string | number) {
  const parsed = Number(value)
  setFieldValue(key, Number.isFinite(parsed) ? parsed : 0)
}

function toggleModelSelector() {
  modelPickerOpen.value = !modelPickerOpen.value
  if (modelPickerOpen.value) {
    modelParameterPanelOpen.value = false
    applyLlmModelSearch()
  }
}

function toggleModelParameterPanel() {
  modelParameterPanelOpen.value = !modelParameterPanelOpen.value
  if (modelParameterPanelOpen.value) modelPickerOpen.value = false
}

function applyLlmModelSearch() {
  llmModelSearchTerm.value = llmModelSearch.value
}

function selectLlmModel(option: LlmModelOption) {
  const fields = llmModelSelectionFields(option)
  setFieldValue('model', fields.model)
  if (fields.modelConfigId) setFieldValue('modelConfigId', fields.modelConfigId)
  if (fields.providerId) setFieldValue('providerId', fields.providerId)
  modelPickerOpen.value = false
}

function startVariableRows() {
  return selectedNode.value ? normalizeStartVariables(selectedNode.value.config) : []
}

function persistStartVariables(variables: StartVariable[]) {
  const normalizedVariables = variables
    .map((item) => ({
      name: item.name.trim(),
      type: outputParameterTypeOptions.includes(item.type) ? item.type : 'string',
      required: item.builtIn ? false : item.required !== false,
      builtIn: item.builtIn === true,
    }))
    .filter((item) => item.name.length > 0)
  updateSelectedNode({
    config: {
      startVariables: normalizedVariables,
      outputVariables: normalizedVariables.map((item) => item.name),
    },
  })
}

function nextStartVariableName(variables: StartVariable[]) {
  let index = variables.length + 1
  let name = `input_${index}`
  const names = new Set(variables.map((item) => item.name))
  while (names.has(name)) {
    index += 1
    name = `input_${index}`
  }
  return name
}

function addStartVariable() {
  const variables = startVariableRows()
  persistStartVariables([
    ...variables,
    { name: nextStartVariableName(variables), type: 'string', required: false, builtIn: false },
  ])
}

function updateStartVariable(index: number, patch: Partial<StartVariable>) {
  const variables = startVariableRows()
  if (!variables[index]) return
  if (variables[index].builtIn) return
  persistStartVariables(variables.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item))
}

function setStartVariableName(index: number, value: string) {
  updateStartVariable(index, { name: value })
}

function setStartVariableType(index: number, value: string) {
  const type = (outputParameterTypeOptions.includes(value as InputParameterType) ? value : 'string') as InputParameterType
  updateStartVariable(index, { type })
}

function setStartVariableRequired(index: number, required: boolean) {
  updateStartVariable(index, { required })
}

function removeStartVariable(index: number) {
  const variables = startVariableRows()
  if (variables.length <= 1 || variables[index]?.builtIn) return
  persistStartVariables(variables.filter((_, itemIndex) => itemIndex !== index))
}

function inputParameterRows() {
  return selectedNode.value ? normalizeInputConfig(selectedNode.value.config).parameters : []
}

function persistInputParameters(parameters: InputParameter[]) {
  updateSelectedNode({ config: { inputParameters: parameters } })
}

function nextInputParameterName(parameters: InputParameter[]) {
  let index = parameters.length + 1
  let name = `input_${index}`
  const names = new Set(parameters.map((item) => item.name))
  while (names.has(name)) {
    index += 1
    name = `input_${index}`
  }
  return name
}

function addInputParameter() {
  const parameters = inputParameterRows()
  persistInputParameters([
    ...parameters,
    { name: nextInputParameterName(parameters), type: 'string', valueMode: 'literal', value: '' },
  ])
}

function updateInputParameter(index: number, patch: Partial<InputParameter>) {
  const parameters = inputParameterRows()
  if (!parameters[index]) return
  const next = parameters.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item)
  persistInputParameters(next)
}

function setInputParameterName(index: number, value: string) {
  updateInputParameter(index, { name: value })
}

function setInputParameterType(index: number, value: string) {
  const type = (outputParameterTypeOptions.includes(value as InputParameterType) ? value : 'string') as InputParameterType
  const row = inputParameterRows()[index]
  updateInputParameter(index, {
    type,
    value: row?.valueMode === 'literal' ? defaultLiteralValue(type) : row?.value || '',
  })
}

function setInputParameterValue(index: number, value: string | number | boolean | null | undefined) {
  updateInputParameter(index, { valueMode: 'literal', value: value ?? '' })
}

function defaultLiteralValue(type: InputParameterType) {
  if (type === 'number') return 0
  if (type === 'boolean') return false
  if (type === 'array') return '[]'
  if (type === 'object') return '{}'
  return ''
}

function inferDirectVariableValueMode(value: unknown, explicitMode: unknown): InputValueMode {
  if (explicitMode === 'literal') return 'literal'
  const text = String(value ?? '').trim()
  if (explicitMode === 'reference') return text ? 'reference' : 'literal'
  return text.includes('{{') ? 'reference' : 'literal'
}

function removeInputParameter(index: number) {
  const parameters = inputParameterRows().filter((_, itemIndex) => itemIndex !== index)
  persistInputParameters(parameters)
  if (activeInputParameterIndex.value === index) {
    activeInputParameterIndex.value = null
    activeInputVariableGroupKey.value = ''
    inputVariableSearch.value = ''
  }
}

function inputParameterErrors() {
  return validateInputParameters(inputParameterRows())
}

function questionOptionRows(): QuestionOption[] {
  return selectedNode.value ? normalizeQuestionOptions(selectedNode.value.config) : []
}

function persistQuestionOptions(options: QuestionOption[]) {
  updateSelectedNode({ config: { options } })
}

function addQuestionOption() {
  const rows = questionOptionRows()
  persistQuestionOptions([
    ...rows,
    { label: `选项 ${rows.length + 1}`, value: `option_${rows.length + 1}` },
  ])
  if (fieldValue('answerType') !== 'option') setFieldValue('answerType', 'option')
}

function updateQuestionOption(index: number, patch: Partial<QuestionOption>) {
  const rows = questionOptionRows()
  if (!rows[index]) return
  persistQuestionOptions(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
}

function setQuestionOptionLabel(index: number, value: string | number) {
  updateQuestionOption(index, { label: String(value) })
}

function setQuestionOptionValue(index: number, value: string | number) {
  updateQuestionOption(index, { value: String(value) })
}

function removeQuestionOption(index: number) {
  persistQuestionOptions(questionOptionRows().filter((_, rowIndex) => rowIndex !== index))
}

function collectionFieldRows(): CollectionField[] {
  return selectedNode.value ? normalizeCollectionFields(selectedNode.value.config) : []
}

function persistCollectionFields(fields: CollectionField[]) {
  updateSelectedNode({ config: { fields } })
}

function addCollectionField() {
  const rows = collectionFieldRows()
  persistCollectionFields([
    ...rows,
    {
      name: `field_${rows.length + 1}`,
      type: 'string',
      required: true,
      description: '',
      targetScope: 'flow',
      targetVariable: `field_${rows.length + 1}`,
    },
  ])
}

function updateCollectionField(index: number, patch: Partial<CollectionField>) {
  const rows = collectionFieldRows()
  if (!rows[index]) return
  persistCollectionFields(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
}

function setCollectionFieldName(index: number, value: string | number) {
  const row = collectionFieldRows()[index]
  const name = String(value)
  updateCollectionField(index, {
    name,
    targetVariable: !row?.targetVariable || row.targetVariable === row.name ? name : row.targetVariable,
  })
}

function setCollectionFieldType(index: number, value: string) {
  const type = (outputParameterTypeOptions.includes(value as InputParameterType) ? value : 'string') as InputParameterType
  updateCollectionField(index, { type })
}

function setCollectionFieldRequired(index: number, required: boolean) {
  updateCollectionField(index, { required })
}

function setCollectionFieldDescription(index: number, value: string | number) {
  updateCollectionField(index, { description: String(value) })
}

function setCollectionFieldTargetScope(index: number, value: string) {
  updateCollectionField(index, { targetScope: value || 'flow' })
}

function setCollectionFieldTargetVariable(index: number, value: string | number) {
  updateCollectionField(index, { targetVariable: String(value) })
}

function removeCollectionField(index: number) {
  persistCollectionFields(collectionFieldRows().filter((_, rowIndex) => rowIndex !== index))
}

function intentRows(): IntentRow[] {
  return selectedNode.value ? normalizeIntentRows(selectedNode.value.config) : []
}

function persistIntentRows(rows: IntentRow[]) {
  updateSelectedNode({ config: { intents: rows } })
}

function startIntentRowDrag(index: number, event: DragEvent) {
  intentDragSourceIndex.value = index
  event.dataTransfer?.setData('text/plain', String(index))
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

function endIntentRowDrag() {
  intentDragSourceIndex.value = null
}

function dropIntentRow(targetIndex: number, event: DragEvent) {
  const rawSource = event.dataTransfer?.getData('text/plain')
  const sourceIndex = Number(rawSource || intentDragSourceIndex.value)
  intentDragSourceIndex.value = null
  const rows = intentRows()
  if (!Number.isInteger(sourceIndex) || sourceIndex < 0 || sourceIndex >= rows.length || sourceIndex === targetIndex) return
  const nextRows = [...rows]
  const [moved] = nextRows.splice(sourceIndex, 1)
  nextRows.splice(targetIndex, 0, moved)
  persistIntentRows(nextRows)
}

function addIntentRow() {
  const rows = intentRows()
  persistIntentRows([
    ...rows,
    {
      key: `intent_${rows.length + 1}`,
      name: `意图 ${rows.length + 1}`,
      description: '',
      examples: [],
      branch: `intent_${rows.length + 1}`,
    },
  ])
}

function updateIntentRow(index: number, patch: Partial<IntentRow>) {
  const rows = intentRows()
  if (!rows[index]) return
  persistIntentRows(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
}

function setIntentName(index: number, value: string | number) {
  updateIntentRow(index, { name: String(value) })
}

function setIntentDescription(index: number, value: string | number) {
  updateIntentRow(index, { description: String(value) })
}

function setIntentExamples(index: number, value: string | number) {
  updateIntentRow(index, {
    examples: String(value)
      .slice(0, 300)
      .split('\n')
      .map((item) => item.trim())
      .filter((item) => item.length > 0),
  })
}

function removeIntentRow(index: number) {
  const rows = intentRows()
  if (rows.length <= 1) return
  persistIntentRows(rows.filter((_, rowIndex) => rowIndex !== index))
}

function setFieldValue(key: string, value: string | number | null | undefined) {
  if (!selectedNode.value) return
  if (key === 'name') {
    updateSelectedNode({ name: String(value || '') })
    return
  }
  const parsed = parseStructuredFieldValue(key, value ?? '')
  const patch: Record<string, any> = { [key]: parsed }
  if (selectedNode.value.type === 'API_CALL' && key === 'timeout') {
    patch.timeoutMs = Number(parsed || 0) * 1000
  }
  updateSelectedNode({ config: patch })
}

function codeTemplateLanguageLabel() {
  return String(fieldValue('language') || 'python') === 'javascript' ? 'JavaScript' : 'Python'
}

function insertCodeTemplate() {
  const language = String(fieldValue('language') || 'python')
  const template = language === 'javascript'
    ? [
        'exports.main = async (args) => {',
        '  return {',
        "    output: args.input ?? ''",
        '  }',
        '}',
      ].join('\n')
    : [
        'def main(args):',
        '    return {',
        "        'output': args.get('input', '')",
        "}",
      ].join('\n')
  setFieldValue('code', template)
}

function switchFieldValue(key: string) {
  const value = fieldValue(key)
  return value === true || value === 'true' || value === 'enabled'
}

function setSwitchFieldValue(key: string, value: boolean) {
  if (['includeHistory', 'writeToConversation'].includes(key)) {
    setFieldValue(key, value ? 'true' : 'false')
    return
  }
  setFieldValue(key, value ? 'enabled' : 'disabled')
}

function normalizeWorkflowResourceType(type: string) {
  return String(type || '').trim().toUpperCase().replace(/-/g, '_')
}

function workflowResourceOptions(resourceTypes: string[] = []) {
  const allowed = new Set(resourceTypes.map(normalizeWorkflowResourceType).filter((type) => type.length > 0))
  return workflowResources.value.filter((resource) => {
    const type = normalizeWorkflowResourceType(resource.resourceType)
    if (allowed.size === 0) return true
    if (allowed.has(type)) return true
    if (allowed.has('API_RESOURCE') && type === 'API_TOOL') return true
    return false
  })
}

function selectedWorkflowResource() {
  const resourceId = String(selectedNode.value?.config.resourceId || '')
  return workflowResources.value.find((item) => item.resourceId === resourceId) || null
}

function selectedResourceAdapterLabel() {
  const resource = selectedWorkflowResource()
  const type = normalizeWorkflowResourceType(String(resource?.resourceType || selectedNode.value?.config.resourceType || 'UNKNOWN'))
  if (type === 'MCP_TOOL') return 'MCP'
  if (type === 'API_TOOL' || type === 'API_RESOURCE') return 'API'
  if (type === 'INTERNAL_TOOL') return 'Internal'
  if (type === 'SUBWORKFLOW') return 'Subworkflow'
  if (type === 'AGENT') return 'Agent'
  if (type === 'KNOWLEDGE_BASE') return 'Knowledge'
  return '未选择资源'
}

function selectedResourceStatusText() {
  const resource = selectedWorkflowResource()
  if (!resource) return '选择资源后显示适配器和运行状态'
  return `${resource.displayName} · ${resourceStatusLabel(resource)}`
}

function legacyResourceDebugRows() {
  const node = selectedNode.value
  if (!node) return []
  const config = node.config || {}
  const keysByType: Record<string, Array<[string, string]>> = {
    TOOL_CALL: [
      ['资源 ID', 'resourceId'],
      ['资源类型', 'resourceType'],
      ['工具名称', 'toolName'],
      ['MCP Server IDs', 'serverIds'],
      ['输入映射', 'inputMappings'],
      ['超时毫秒', 'timeoutMs'],
      ['重试次数', 'retryCount'],
      ['错误行为', 'errorBehavior'],
    ],
    KNOWLEDGE: [
      ['资源 ID', 'resourceId'],
      ['知识库 ID', 'knowledgeBaseId'],
    ],
    EXECUTE_WORKFLOW: [
      ['资源 ID', 'resourceId'],
      ['目标工作流 ID', 'targetWorkflowId'],
      ['输入映射', 'inputMappings'],
      ['输出映射', 'outputMappings'],
      ['超时毫秒', 'timeoutMs'],
      ['最大嵌套深度', 'maxDepth'],
    ],
    AGENT_CALL: [
      ['资源 ID', 'resourceId'],
      ['目标智能体 ID', 'targetAgentId'],
      ['输入映射', 'inputMappings'],
      ['输出映射', 'outputMappings'],
      ['超时毫秒', 'timeoutMs'],
      ['最大嵌套深度', 'maxDepth'],
    ],
  }
  return (keysByType[node.type] || [])
    .map(([label, key]) => ({ label, value: formatLegacyDebugValue(config[key]) }))
    .filter((row) => row.value.length > 0)
}

function formatLegacyDebugValue(value: unknown) {
  if (value === undefined || value === null || value === '') return ''
  if (Array.isArray(value) || typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function isApiOrToolGovernanceNode() {
  return selectedNode.value?.type === 'API_CALL' || selectedNode.value?.type === 'TOOL_CALL'
}

function resourceGovernanceNumberValue(primaryKey: string, fallbackKey = '') {
  const primary = selectedNode.value?.config[primaryKey]
  if (Number(primary) > 0 || primaryKey === 'retryCount') return Number(primary || 0)
  const fallback = fallbackKey ? selectedNode.value?.config[fallbackKey] : 0
  if (primaryKey === 'timeoutMs' && Number(fallback) > 0) return Number(fallback) * 1000
  return Number(fallback || 0)
}

function setResourceGovernanceNumber(key: string, value: number | string) {
  const next = Number(value || 0)
  const patch: Record<string, any> = { [key]: next }
  if (selectedNode.value?.type === 'API_CALL' && key === 'timeoutMs') {
    patch.timeout = next > 0 ? Math.round(next / 1000) : 0
  }
  updateSelectedNode({ config: patch })
}

function resourceOutputSchemaText() {
  const schema = selectedNode.value?.config.outputSchema
  if (schema === undefined || schema === null || schema === '') return ''
  return typeof schema === 'string' ? schema : JSON.stringify(schema)
}

function setResourceOutputSchema(value: string | number) {
  const text = String(value || '').trim()
  updateSelectedNode({ config: { outputSchema: parseJsonObjectOrText(text) } })
}

function resourceSensitiveHeadersText() {
  const headers = selectedNode.value?.config.sensitiveHeaders
  if (Array.isArray(headers)) return headers.join(', ')
  return String(headers || '')
}

function setResourceSensitiveHeaders(value: string | number) {
  const headers = String(value || '')
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
  updateSelectedNode({ config: { sensitiveHeaders: headers } })
}

function parseJsonObjectOrText(text: string) {
  if (!text) return ''
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function resourceGovernanceDefaults(resource: WorkflowResource, defaults: Record<string, any>) {
  const config = selectedNode.value?.config || {}
  const metadata = resource.metadata || {}
  const patch: Record<string, any> = {}
  for (const [key, value] of Object.entries(defaults)) {
    patch[key] = config[key] ?? metadata[key] ?? value
  }
  patch.outputSchema = config.outputSchema ?? resource.outputSchema ?? metadata.outputSchema ?? {}
  patch.sensitiveHeaders = config.sensitiveHeaders ?? metadata.sensitiveHeaders ?? []
  return patch
}

function selectWorkflowResource(field: { key: string; resourceTypes?: string[] }, resourceId: string) {
  const resource = workflowResources.value.find((item) => item.resourceId === resourceId)
  if (!resource) {
    setFieldValue(field.key, resourceId)
    return
  }
  const resourceType = normalizeWorkflowResourceType(resource.resourceType)
  const metadata = resource.metadata || {}
  const serverId = Number(metadata.serverId || resource.resourceId.match(/^mcp:(\d+)/)?.[1] || 0)
  const toolName = String(metadata.toolName || resource.displayName || '')
  const patch: Record<string, any> = {
    [field.key]: resource.resourceId,
    resourceId: resource.resourceId,
    resourceType,
  }
  if (selectedNode.value?.type === 'API_CALL') {
    Object.assign(patch, resourceGovernanceDefaults(resource, {
      authMode: 'none',
      timeoutMs: 30000,
      retryCount: 0,
      errorBehavior: 'fail',
    }))
  }
  if (selectedNode.value?.type === 'TOOL_CALL') {
    patch.toolName = toolName
    patch.serverIds = resourceType === 'MCP_TOOL' && serverId > 0 ? [serverId] : []
    Object.assign(patch, resourceGovernanceDefaults(resource, {
      timeoutMs: 30000,
      retryCount: 0,
      errorBehavior: 'fail',
    }))
  }
  if (selectedNode.value?.type === 'KNOWLEDGE') {
    patch.knowledgeBaseId = metadata.knowledgeBaseId || metadata.id || resource.resourceId
  }
  if (selectedNode.value?.type === 'EXECUTE_WORKFLOW') {
    patch.targetWorkflowId = metadata.workflowId || metadata.id || String(resource.resourceId).replace(/^workflow:/, '')
  }
  if (selectedNode.value?.type === 'AGENT_CALL') {
    patch.targetAgentId = metadata.agentId || metadata.id || String(resource.resourceId).replace(/^agent:/, '')
  }
  updateSelectedNode({ config: patch })
}

function jsonSchemaTypeToInputType(value: unknown): InputParameterType {
  const type = Array.isArray(value) ? String(value[0] || '') : String(value || '')
  if (type === 'integer') return 'number'
  if (outputParameterTypeOptions.includes(type as InputParameterType)) return type as InputParameterType
  return 'string'
}

function currentInputMappings() {
  const raw = selectedNode.value?.config.inputMappings
  if (Array.isArray(raw)) return raw
  if (typeof raw !== 'string' || !raw.trim()) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function schemaInputMappingRows(): SchemaInputMappingRow[] {
  const resource = selectedWorkflowResource()
  const existing = currentInputMappings()
  const existingByName = new Map(existing.map((item: any) => [String(item?.name || ''), item]))
  const schema = resource?.inputSchema || {}
  const properties = schema && typeof schema === 'object' && !Array.isArray(schema)
    ? (schema as any).properties
    : null
  const required = new Set(Array.isArray((schema as any).required) ? (schema as any).required.map((item: unknown) => String(item)) : [])

  if (properties && typeof properties === 'object') {
    return Object.entries(properties).map(([name, definition]) => {
      const existingRow = existingByName.get(name) as any
      const type = jsonSchemaTypeToInputType((definition as any)?.type)
      const valueMode = inferDirectVariableValueMode(existingRow?.value, existingRow?.valueMode)
      return {
        name,
        type,
        required: required.has(name),
        description: String((definition as any)?.description || ''),
        valueMode,
        value: existingRow?.value ?? (valueMode === 'literal' ? defaultLiteralValue(type) : ''),
      }
    })
  }

  return existing
    .map((item: any) => {
      const type = jsonSchemaTypeToInputType(item?.type)
      const valueMode = inferDirectVariableValueMode(item?.value, item?.valueMode)
      return {
        name: String(item?.name || '').trim(),
        type,
        required: item?.required === true,
        description: String(item?.description || ''),
        valueMode,
        value: item?.value ?? (valueMode === 'literal' ? defaultLiteralValue(type) : ''),
      }
    })
    .filter((item: SchemaInputMappingRow) => item.name.length > 0)
}

function persistSchemaInputMappings(rows: SchemaInputMappingRow[]) {
  updateSelectedNode({
    config: {
      inputMappings: rows.map((row) => ({
        name: row.name,
        type: row.type,
        required: row.required,
        description: row.description,
        valueMode: row.valueMode,
        value: row.value,
      })),
    },
  })
}

function setSchemaInputMappingValue(index: number, value: string | number | boolean | null | undefined) {
  const rows = schemaInputMappingRows()
  if (!rows[index]) return
  rows[index] = { ...rows[index], valueMode: 'literal', value: value ?? '' }
  persistSchemaInputMappings(rows)
}

function openSchemaInputVariablePicker(index: number, event?: Event) {
  refreshVariablePickerAnchor(event?.currentTarget)
  activeSchemaInputMappingIndex.value = activeSchemaInputMappingIndex.value === index ? null : index
  schemaVariableSearch.value = ''
  activeSchemaVariableGroupKey.value = ''
}

function openStructuredVariablePicker(target: string, event?: Event) {
  refreshVariablePickerAnchor(event?.currentTarget)
  activeStructuredVariableTarget.value = activeStructuredVariableTarget.value === target ? '' : target
  structuredVariableSearch.value = ''
  activeStructuredVariableGroupKey.value = ''
}

function jsonFieldMappingRows(): JsonFieldMapping[] {
  if (!selectedNode.value) return []
  const rows = normalizeJsonFieldMappings(selectedNode.value.config)
  if (rows.length > 0) return rows
  return suggestedJsonFieldMappingsFromSource()
}

function suggestedJsonFieldMappingsFromSource(): JsonFieldMapping[] {
  const source = String(selectedNode.value?.config.source || '')
  const match = source.match(/{{\s*([^.{}\s]+)\.[^{}]+\s*}}/)
  if (!match) return []
  const upstream = graph.value.nodes.find((node) => node.nodeKey === match[1])
  if (!upstream) return []
  return normalizeOutputConfig(upstream.config).parameters.map((parameter) => ({
    name: parameter.name,
    path: `$.${parameter.name}`,
    type: parameter.type,
  }))
}

function persistJsonFieldMappings(rows: JsonFieldMapping[]) {
  updateSelectedNode({ config: { fieldMap: rows } })
}

function addJsonFieldMapping() {
  const rows = jsonFieldMappingRows()
  persistJsonFieldMappings([...rows, { name: `field_${rows.length + 1}`, path: '$.', type: 'string' }])
}

function updateJsonFieldMapping(index: number, patch: Partial<JsonFieldMapping>) {
  const rows = jsonFieldMappingRows()
  if (!rows[index]) return
  persistJsonFieldMappings(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
}

function setJsonFieldMappingName(index: number, value: string | number) {
  updateJsonFieldMapping(index, { name: String(value) })
}

function setJsonFieldMappingPath(index: number, value: string | number) {
  updateJsonFieldMapping(index, { path: String(value) })
}

function setJsonFieldMappingType(index: number, value: string) {
  const type = (outputParameterTypeOptions.includes(value as InputParameterType) ? value : 'string') as InputParameterType
  updateJsonFieldMapping(index, { type })
}

function removeJsonFieldMapping(index: number) {
  persistJsonFieldMappings(jsonFieldMappingRows().filter((_, rowIndex) => rowIndex !== index))
}

function aggregationSourceRows(): AggregationSource[] {
  return selectedNode.value ? normalizeAggregationSources(selectedNode.value.config) : []
}

function aggregationGroupRows(): AggregationGroup[] {
  return selectedNode.value ? normalizeAggregationGroups(selectedNode.value.config) : []
}

function aggregationOutputTypeFromVariableType(type: VariableCatalogType | null | undefined): OutputParameterType {
  return outputParameterTypeOptions.includes(type as OutputParameterType) ? type as OutputParameterType : 'string'
}

function aggregationGroupResolvedType(group: AggregationGroup): OutputParameterType {
  const selectedVariableType = group.variables
    .map((variable) => inputReferenceSelection(String(variable.value || ''))?.item.type)
    .find((type): type is VariableCatalogType => Boolean(type))
  return aggregationOutputTypeFromVariableType(selectedVariableType || group.type)
}

function aggregationGroupsForPersist(groups: AggregationGroup[]) {
  return groups.map((group) => ({ ...group, type: aggregationGroupResolvedType(group) }))
}

function aggregationOutputParameters(groups: AggregationGroup[]) {
  return groups.map((group) => ({
    name: group.name || 'Group1',
    type: aggregationGroupResolvedType(group),
  }))
}

function aggregationOutputSummaryRows() {
  return aggregationOutputParameters(aggregationGroupRows())
}

function persistAggregationGroups(groups: AggregationGroup[]) {
  const typedGroups = aggregationGroupsForPersist(groups)
  updateSelectedNode({
    config: {
      strategy: 'first_non_empty',
      groups: typedGroups,
      outputParameters: aggregationOutputParameters(typedGroups),
    },
  })
}

function addAggregationGroup() {
  const groups = aggregationGroupRows()
  persistAggregationGroups([
    ...groups,
    { name: `Group${groups.length + 1}`, type: 'string', variables: [{ valueMode: 'literal', value: '' }] },
  ])
}

function updateAggregationGroup(groupIndex: number, patch: Partial<AggregationGroup>) {
  const groups = aggregationGroupRows()
  if (!groups[groupIndex]) return
  persistAggregationGroups(groups.map((group, index) => index === groupIndex ? { ...group, ...patch } : group))
}

function setAggregationGroupName(groupIndex: number, value: string | number) {
  const fallback = `Group${groupIndex + 1}`
  updateAggregationGroup(groupIndex, { name: String(value || fallback).trim() || fallback })
}

function beginAggregationGroupNameEdit(groupIndex: number, name: string) {
  editingAggregationGroupNameIndex.value = groupIndex
  aggregationGroupNameDraft.value = name
}

function commitAggregationGroupNameEdit(groupIndex: number) {
  if (editingAggregationGroupNameIndex.value !== groupIndex) return
  setAggregationGroupName(groupIndex, aggregationGroupNameDraft.value)
  editingAggregationGroupNameIndex.value = null
  aggregationGroupNameDraft.value = ''
}

function cancelAggregationGroupNameEdit() {
  editingAggregationGroupNameIndex.value = null
  aggregationGroupNameDraft.value = ''
}

function removeAggregationGroup(groupIndex: number) {
  const groups = aggregationGroupRows()
  if (groups.length <= 1) return
  persistAggregationGroups(groups.filter((_, index) => index !== groupIndex))
  if (activeStructuredVariableTarget.value.startsWith(`aggregation:${groupIndex}:`)) {
    activeStructuredVariableTarget.value = ''
    activeStructuredVariableGroupKey.value = ''
    structuredVariableSearch.value = ''
  }
}

function updateAggregationGroupVariable(groupIndex: number, variableIndex: number, patch: Partial<AggregationGroupVariable>) {
  const groups = aggregationGroupRows()
  const group = groups[groupIndex]
  if (!group || !group.variables[variableIndex]) return
  const variables = group.variables.map((variable, index) => index === variableIndex ? { ...variable, ...patch } : variable)
  persistAggregationGroups(groups.map((item, index) => index === groupIndex ? { ...item, variables } : item))
}

function setAggregationGroupVariableValue(groupIndex: number, variableIndex: number, value: string | number | boolean | null | undefined) {
  updateAggregationGroupVariable(groupIndex, variableIndex, { valueMode: 'literal', value: value ?? '' })
}

function clearAggregationGroupVariableReference(groupIndex: number, variableIndex: number) {
  updateAggregationGroupVariable(groupIndex, variableIndex, { valueMode: 'literal', value: '' })
}

function removeAggregationGroupVariable(groupIndex: number, variableIndex: number) {
  const groups = aggregationGroupRows()
  const group = groups[groupIndex]
  if (!group) return
  const nextVariables = group.variables.filter((_, index) => index !== variableIndex)
  persistAggregationGroups(groups.map((item, index) => index === groupIndex
    ? { ...item, variables: nextVariables.length > 0 ? nextVariables : [{ valueMode: 'literal', value: '' }] }
    : item))
  if (activeStructuredVariableTarget.value === `aggregation:${groupIndex}:${variableIndex}`) {
    activeStructuredVariableTarget.value = ''
    activeStructuredVariableGroupKey.value = ''
    structuredVariableSearch.value = ''
  }
}

function persistAggregationSources(rows: AggregationSource[]) {
  updateSelectedNode({ config: { sources: rows } })
}

function addAggregationSource() {
  const rows = aggregationSourceRows()
  persistAggregationSources([...rows, { name: `source_${rows.length + 1}`, valueMode: 'literal', value: '' }])
}

function updateAggregationSource(index: number, patch: Partial<AggregationSource>) {
  const rows = aggregationSourceRows()
  if (!rows[index]) return
  persistAggregationSources(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
}

function setAggregationSourceName(index: number, value: string | number) {
  updateAggregationSource(index, { name: String(value) })
}

function setAggregationSourceValue(index: number, value: string | number | boolean | null | undefined) {
  updateAggregationSource(index, { valueMode: 'literal', value: value ?? '' })
}

function clearAggregationSourceReference(index: number) {
  updateAggregationSource(index, { valueMode: 'literal', value: '' })
}

function removeAggregationSource(index: number) {
  persistAggregationSources(aggregationSourceRows().filter((_, rowIndex) => rowIndex !== index))
  if (activeStructuredVariableTarget.value === `aggregation:${index}`) {
    activeStructuredVariableTarget.value = ''
    activeStructuredVariableGroupKey.value = ''
    structuredVariableSearch.value = ''
  }
}

function variableAssignmentValueMode(): InputValueMode | 'operation' {
  const explicit = fieldValue('sourceValueMode')
  if (explicit === 'operation') return 'operation'
  return inferDirectVariableValueMode(fieldValue('source'), explicit)
}

function variableAssignmentSourceType(): 'reference' | 'input' {
  return variableAssignmentValueMode() === 'reference' ? 'reference' : 'input'
}

function variableAssignmentTargetReference() {
  const scope = String(fieldValue('targetScope') || (isChatflowMode.value ? 'conversation' : 'flow')).trim()
  const variable = String(fieldValue('targetVariable') || '').trim()
  if (!variable) return ''
  const reference = `${normalizeAssignmentTargetScope(scope)}.${variable}`
  return variableAssignmentTargetGroups.value.some((group) =>
    group.items.some((item) => item.reference === reference),
  )
    ? reference
    : ''
}

function clearVariableAssignmentReference() {
  updateSelectedNode({ config: { sourceValueMode: 'literal', source: '' } })
}

function setVariableAssignmentSourceValue(value: string | number) {
  updateSelectedNode({ config: { sourceValueMode: 'literal', source: String(value) } })
}

function normalizeAssignmentTargetScope(scope: string) {
  const normalized = String(scope || '').trim().toLowerCase()
  if (normalized === 'app') return 'global'
  if (['flow', 'conversation', 'user', 'global', 'channel'].includes(normalized)) return normalized
  return isChatflowMode.value ? 'conversation' : 'flow'
}

function variableAssignmentScopeLabel(scope: string) {
  const labels: Record<string, string> = {
    flow: '流程变量',
    conversation: '会话变量',
    user: '用户变量',
    global: '应用变量',
    channel: '渠道变量',
  }
  return labels[normalizeAssignmentTargetScope(scope)] || '变量'
}

function makeVariableAssignmentTarget(scope: string, variable: string, type: VariableCatalogType = 'string'): VariableAssignmentTargetOption | null {
  const normalizedScope = normalizeAssignmentTargetScope(scope)
  const name = String(variable || '').trim()
  if (!name) return null
  return {
    scope: normalizedScope,
    scopeLabel: variableAssignmentScopeLabel(normalizedScope),
    variable: name,
    label: name,
    reference: `${normalizedScope}.${name}`,
    type,
  }
}

function buildVariableAssignmentTargetGroups(): VariableAssignmentTargetGroup[] {
  const byScope = new Map<string, VariableAssignmentTargetOption[]>()
  const add = (scope: string, variable: string, type: VariableCatalogType = 'string') => {
    const item = makeVariableAssignmentTarget(scope, variable, type)
    if (!item) return
    const items = byScope.get(item.scope) || []
    if (!items.some((candidate) => candidate.reference === item.reference)) {
      items.push(item)
      byScope.set(item.scope, items)
    }
  }

  graph.value.nodes.forEach((node) => {
    if (node.type === 'INFORMATION_COLLECTION') {
      normalizeCollectionFields(node.config).forEach((field) => {
        add(field.targetScope, field.targetVariable || field.name, field.type)
      })
    }
  })

  const order = isChatflowMode.value
    ? ['conversation', 'user', 'global', 'channel', 'flow']
    : ['flow', 'global', 'user', 'conversation', 'channel']
  return order
    .map((scope) => ({
      key: scope,
      title: variableAssignmentScopeLabel(scope),
      items: byScope.get(scope) || [],
    }))
    .filter((group) => group.items.length > 0)
}

function openVariableAssignmentTargetPicker(event?: Event) {
  event?.preventDefault()
  event?.stopPropagation()
  const shouldOpen = !activeVariableAssignmentTargetPicker.value
  closeVariablePickers()
  if (!shouldOpen) return
  refreshVariablePickerAnchor(event?.currentTarget)
  activeVariableAssignmentTargetPicker.value = true
  variableAssignmentTargetSearch.value = ''
  activeVariableAssignmentTargetGroupKey.value = ''
}

function activateVariableAssignmentTargetGroup(group: VariableAssignmentTargetGroup, event: MouseEvent) {
  activeVariableAssignmentTargetGroupKey.value = group.key
  refreshVariableFlyoutAnchor(event.currentTarget)
}

function selectVariableAssignmentTarget(item: VariableAssignmentTargetOption) {
  updateSelectedNode({ config: { targetScope: item.scope, targetVariable: item.variable } })
  activeVariableAssignmentTargetPicker.value = false
  activeVariableAssignmentTargetGroupKey.value = ''
  variableAssignmentTargetSearch.value = ''
}

function humanInputSchemaRows(): HumanInputSchemaField[] {
  return selectedNode.value ? normalizeHumanInputSchema(selectedNode.value.config) : []
}

function persistHumanInputSchema(rows: HumanInputSchemaField[]) {
  updateSelectedNode({ config: { inputSchema: rows } })
}

function addHumanInputSchemaField() {
  const rows = humanInputSchemaRows()
  persistHumanInputSchema([...rows, { name: `field_${rows.length + 1}`, type: 'string', required: true, description: '' }])
}

function updateHumanInputSchemaField(index: number, patch: Partial<HumanInputSchemaField>) {
  const rows = humanInputSchemaRows()
  if (!rows[index]) return
  persistHumanInputSchema(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
}

function setHumanInputSchemaName(index: number, value: string | number) {
  updateHumanInputSchemaField(index, { name: String(value) })
}

function setHumanInputSchemaType(index: number, value: string) {
  const type = (outputParameterTypeOptions.includes(value as InputParameterType) ? value : 'string') as InputParameterType
  updateHumanInputSchemaField(index, { type })
}

function setHumanInputSchemaRequired(index: number, required: boolean) {
  updateHumanInputSchemaField(index, { required })
}

function setHumanInputSchemaDescription(index: number, value: string | number) {
  updateHumanInputSchemaField(index, { description: String(value) })
}

function removeHumanInputSchemaField(index: number) {
  persistHumanInputSchema(humanInputSchemaRows().filter((_, rowIndex) => rowIndex !== index))
}

function parseStructuredFieldValue(key: string, value: string | number) {
  if (!['serverIds', 'inputMappings', 'outputMappings', 'headers', 'fields', 'intents', 'options', 'fieldMap', 'sources', 'inputSchema'].includes(key)) return value
  if (typeof value !== 'string') return value
  const trimmed = value.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return value
  }
}

function conditionBranches(): ConditionBranch[] {
  const raw = selectedNode.value?.config.conditionBranches
  if (!Array.isArray(raw) || raw.length === 0) {
    return [{
      key: 'branch_1',
      name: '分支 1',
      logic: 'AND',
      conditions: [{
        left: normalizeConditionOperand('{{start.USER_INPUT}}'),
        operator: 'equals',
        right: normalizeConditionOperand(''),
      }],
    }]
  }
  return raw.map((branch, index) => ({
    key: String(branch?.key || branch?.id || `branch_${index + 1}`),
    name: normalizeConditionBranchName(branch, index),
    logic: String(branch?.logic || 'AND').toUpperCase() === 'OR' ? 'OR' : 'AND',
    conditions: Array.isArray(branch?.conditions) && branch.conditions.length > 0
      ? branch.conditions.map((condition: any) => {
        const operator = normalizeConditionOperator(condition?.operator)
        return {
          left: normalizeConditionOperand(condition?.left || condition?.field || ''),
          operator,
          right: isConditionRightOperandDisabled(operator)
            ? normalizeConditionOperand('')
            : normalizeConditionOperand(condition?.right ?? condition?.value ?? ''),
        }
      })
      : [{
        left: normalizeConditionOperand('{{start.USER_INPUT}}'),
        operator: 'equals',
        right: normalizeConditionOperand(''),
      }],
  }))
}

function normalizeConditionBranchName(branch: any, index: number) {
  const explicit = String(branch?.name || branch?.title || branch?.label || '').trim()
  if (explicit) return explicit
  const key = String(branch?.key || branch?.id || '').trim()
  if (key && !/^branch_\d+$/.test(key)) return key
  return `分支 ${index + 1}`
}

function normalizeConditionOperand(value: unknown): ConditionOperand {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const raw = value as Record<string, unknown>
    const text = String(raw.value ?? raw.reference ?? raw.literal ?? '')
    return { valueMode: inferDirectVariableValueMode(text, raw.valueMode || raw.mode), value: text }
  }
  const text = String(value ?? '')
  return { valueMode: inferDirectVariableValueMode(text, undefined), value: text }
}

function normalizeConditionOperator(value: unknown): ConditionOperator {
  const raw = String(value || 'equals') as ConditionOperator
  return conditionOperatorOptions.some((option) => option.value === raw) ? raw : 'equals'
}

function conditionOperatorOptionsFromValues(values: ConditionOperator[]): ConditionOperatorOption[] {
  return values
    .map((value) => conditionOperatorOptionByValue.get(value))
    .filter((option): option is ConditionOperatorOption => Boolean(option))
}

function conditionOperatorOptionsForType(type: VariableCatalogType | null): ConditionOperatorOption[] {
  if (!type) return []
  if (type === 'number') return conditionOperatorOptionsFromValues(conditionNumberOperatorValues)
  if (type === 'boolean') return conditionOperatorOptionsFromValues(conditionBooleanOperatorValues)
  if (type === 'object') return conditionOperatorOptionsFromValues(conditionObjectOperatorValues)
  if (type === 'array') return conditionOperatorOptionsFromValues(conditionArrayOperatorValues)
  return conditionOperatorOptionsFromValues(conditionStringOperatorValues)
}

function conditionOperandVariableType(operand: ConditionOperand): VariableCatalogType | null {
  const selection = inputReferenceSelection(operand.value)
  if (selection) return selection.item.type
  return String(operand.value || '').trim() ? 'string' : null
}

function conditionOperandCompactTypeLabel(operand: ConditionOperand) {
  return conditionOperandVariableType(operand) ? variableTypeLabel(conditionOperandVariableType(operand)!) : 'str.'
}

function conditionOperatorOptionsForCondition(condition: ConditionRow): ConditionOperatorOption[] {
  return conditionOperatorOptionsForType(conditionOperandVariableType(condition.left))
}

function defaultConditionOperatorForType(type: VariableCatalogType | null): ConditionOperator {
  return conditionOperatorOptionsForType(type)[0]?.value || 'equals'
}

function isConditionOperatorAllowedForType(operator: ConditionOperator, type: VariableCatalogType | null) {
  return conditionOperatorOptionsForType(type).some((option) => option.value === operator)
}

function isConditionRightOperandDisabled(operator: ConditionOperator) {
  return ['is_empty', 'is_not_empty', 'is_true', 'is_false'].includes(operator)
}

function conditionRightOperandPlaceholder(operator: ConditionOperator) {
  return isConditionRightOperandDisabled(operator) ? '无需填写右值' : '输入或引用参数值'
}

function nextConditionRowValue(condition: ConditionRow, field: keyof ConditionRow, value: string | number): ConditionRow {
  if (field === 'operator') {
    const operator = normalizeConditionOperator(value)
    return {
      ...condition,
      operator,
      right: isConditionRightOperandDisabled(operator) ? normalizeConditionOperand('') : condition.right,
    }
  }

  const nextCondition = { ...condition, [field]: normalizeConditionOperand(value) }
  if (field !== 'left') return nextCondition

  const previousType = conditionOperandVariableType(condition.left)
  const nextType = conditionOperandVariableType(nextCondition.left)
  const operator = isConditionOperatorAllowedForType(nextCondition.operator, nextType)
    ? nextCondition.operator
    : defaultConditionOperatorForType(nextType)
  return {
    ...nextCondition,
    operator,
    right: previousType === nextType && !isConditionRightOperandDisabled(operator)
      ? nextCondition.right
      : normalizeConditionOperand(''),
  }
}

function persistConditionBranches(branches: ConditionBranch[]) {
  updateSelectedNode({ config: { conditionBranches: branches } })
}

function conditionHandleId(key: string) {
  return `condition-${key.replace(/[^a-zA-Z0-9_-]/g, '_') || 'default'}`
}

function conditionHandleTop(index: number) {
  return `${(5.3125 + index * 3.125).toFixed(4)}rem`
}

function normalizeConditionBranchesFromConfig(config: Record<string, any> = {}) {
  const raw = config.conditionBranches
  if (!Array.isArray(raw) || raw.length === 0) return [{ key: 'branch_1', name: '分支 1' }]
  return raw
    .map((branch, index) => ({
      key: String(branch?.key || branch?.id || `branch_${index + 1}`),
      name: normalizeConditionBranchName(branch, index),
    }))
    .filter((branch) => branch.key.trim().length > 0)
}

function conditionDefaultBranchKey(config: Record<string, any> = {}) {
  return String(config.defaultBranch || 'default').trim() || 'default'
}

function conditionDefaultBranchName(config: Record<string, any> = {}) {
  return String(config.defaultBranchName || config.defaultBranchLabel || '').trim() || '默认分支'
}

function conditionBranchKindLabel(index: number) {
  return index === 0 ? '如果' : '否则如果'
}

function conditionSourceHandles(config: Record<string, any> = {}): ConditionSourceHandle[] {
  const branches = normalizeConditionBranchesFromConfig(config)
  const defaultKey = conditionDefaultBranchKey(config)
  const rows: Array<Omit<ConditionSourceHandle, 'handleId' | 'top'>> = [
    ...branches.map((branch, index) => ({
      key: branch.key,
      kind: conditionBranchKindLabel(index),
      label: branch.name,
      condition: branch.key,
    })),
    { key: defaultKey, kind: '否则', label: conditionDefaultBranchName(config), condition: null },
  ]
  return rows.map((row, index) => ({
    ...row,
    handleId: conditionHandleId(row.key),
    top: conditionHandleTop(index),
  }))
}

function intentDefaultBranchKey(config: Record<string, any> = {}) {
  return String(config.defaultIntent || 'default').trim() || 'default'
}

function intentDefaultBranchName() {
  return '其他意图'
}

function intentSourceHandles(config: Record<string, any> = {}): ConditionSourceHandle[] {
  const defaultKey = intentDefaultBranchKey(config)
  const intents = normalizeIntentRows(config).filter((intent) => intent.key !== defaultKey)
  const rows: Array<Omit<ConditionSourceHandle, 'handleId' | 'top'>> = [
    ...intents.map((intent) => ({
      key: intent.key,
      kind: '意图',
      label: intent.name || intent.key,
      condition: intent.key,
    })),
    { key: defaultKey, kind: '兜底', label: intentDefaultBranchName(), condition: null },
  ]
  return rows.map((row, index) => ({
    ...row,
    handleId: conditionHandleId(row.key),
    top: conditionHandleTop(index),
  }))
}

function branchSourceHandles(type: string, config: Record<string, any> = {}) {
  if (type === 'CONDITION') return conditionSourceHandles(config)
  if (type === 'INTENT_RECOGNITION') return intentSourceHandles(config)
  return []
}

function branchNodeByKey(nodeKey: string | null | undefined) {
  if (!nodeKey) return null
  return graph.value.nodes.find((node) => node.nodeKey === nodeKey && isBranchNodeType(node.type)) || null
}

function edgeSourceHandle(edge: { sourceNodeKey: string; condition: string | null }) {
  const sourceNode = branchNodeByKey(edge.sourceNodeKey)
  if (!sourceNode) return undefined
  const edgeCondition = edge.condition ?? null
  return branchSourceHandles(sourceNode.type, sourceNode.config).find((item) => item.condition === edgeCondition)?.handleId
}

function conditionFromSourceHandle(sourceNodeKey: string | null | undefined, sourceHandle: string | null | undefined) {
  const sourceNode = branchNodeByKey(sourceNodeKey)
  if (!sourceNode || !sourceHandle) return null
  return branchSourceHandles(sourceNode.type, sourceNode.config).find((item) => item.handleId === sourceHandle)?.condition ?? null
}

function setConditionBranchName(branchIndex: number, value: string | number) {
  persistConditionBranches(conditionBranches().map((branch, index) =>
    index === branchIndex ? { ...branch, name: String(value) } : branch,
  ))
}

function startConditionBranchNameEdit(branchIndex: number) {
  editingConditionBranchNameIndex.value = branchIndex
  editingConditionDefaultName.value = false
}

function stopConditionBranchNameEdit() {
  editingConditionBranchNameIndex.value = null
}

function setConditionDefaultBranchName(value: string | number) {
  updateSelectedNode({ config: { defaultBranchName: String(value) } })
}

function startConditionDefaultNameEdit() {
  editingConditionDefaultName.value = true
  editingConditionBranchNameIndex.value = null
}

function stopConditionDefaultNameEdit() {
  editingConditionDefaultName.value = false
}

function setConditionBranchLogic(branchIndex: number, value: string) {
  persistConditionBranches(conditionBranches().map((branch, index) =>
    index === branchIndex ? { ...branch, logic: value === 'OR' ? 'OR' : 'AND' } : branch,
  ))
}

function setConditionRowValue(
  branchIndex: number,
  conditionIndex: number,
  field: keyof ConditionRow,
  value: string | number,
) {
  persistConditionBranches(conditionBranches().map((branch, index) => {
    if (index !== branchIndex) return branch
    return {
      ...branch,
      conditions: branch.conditions.map((condition, rowIndex) =>
        rowIndex === conditionIndex
          ? nextConditionRowValue(condition, field, value)
          : condition,
      ),
    }
  }))
}

function setConditionOperandValue(
  branchIndex: number,
  conditionIndex: number,
  side: 'left' | 'right',
  value: string,
) {
  setConditionRowValue(branchIndex, conditionIndex, side, value)
}

function conditionVariableTarget(branchIndex: number, conditionIndex: number, side: 'left' | 'right') {
  return `condition:${branchIndex}:${conditionIndex}:${side}`
}

function parseConditionVariableTarget(target: string): { branchIndex: number; conditionIndex: number; side: 'left' | 'right' } | null {
  const [, branchIndex, conditionIndex, side] = target.split(':')
  if (side !== 'left' && side !== 'right') return null
  const parsedBranchIndex = Number(branchIndex)
  const parsedConditionIndex = Number(conditionIndex)
  if (!Number.isInteger(parsedBranchIndex) || !Number.isInteger(parsedConditionIndex)) return null
  return { branchIndex: parsedBranchIndex, conditionIndex: parsedConditionIndex, side }
}

function isConditionVariablePickerOpen(branchIndex: number, conditionIndex: number, side: 'left' | 'right') {
  return activeConditionVariableTarget.value === conditionVariableTarget(branchIndex, conditionIndex, side)
}

function openConditionVariablePicker(branchIndex: number, conditionIndex: number, side: 'left' | 'right', event?: Event) {
  const row = conditionBranches()[branchIndex]?.conditions[conditionIndex]
  if (side === 'right' && row && isConditionRightOperandDisabled(row.operator)) return
  refreshVariablePickerAnchor(event?.currentTarget)
  activeConditionVariableTarget.value = conditionVariableTarget(branchIndex, conditionIndex, side)
  conditionVariableSearch.value = ''
  activeConditionVariableGroupKey.value = ''
}

function handleConditionOperandInput(
  branchIndex: number,
  conditionIndex: number,
  side: 'left' | 'right',
  value: string | number | null | undefined,
) {
  const nextValue = String(value ?? '')
  const row = conditionBranches()[branchIndex]?.conditions[conditionIndex]
  const previousValue = row ? String(row[side].value ?? '') : ''
  const trigger = completeVariableBraceTrigger(nextValue, previousValue)
  if (trigger.opened) {
    setConditionOperandValue(branchIndex, conditionIndex, side, trigger.value)
    openConditionVariablePicker(branchIndex, conditionIndex, side)
    setActiveTextControlCaret(trigger.caret)
    return
  }
  setConditionOperandValue(branchIndex, conditionIndex, side, trigger.value)
}

function clearConditionOperandReference(
  branchIndex: number,
  conditionIndex: number,
  side: 'left' | 'right',
) {
  setConditionOperandValue(branchIndex, conditionIndex, side, '')
}

function insertConditionVariableReference(reference: string) {
  const target = parseConditionVariableTarget(activeConditionVariableTarget.value)
  if (!target) return
  const row = conditionBranches()[target.branchIndex]?.conditions[target.conditionIndex]
  const currentValue = row ? row[target.side].value : ''
  setConditionOperandValue(
    target.branchIndex,
    target.conditionIndex,
    target.side,
    insertInlineVariableReference(currentValue, reference),
  )
  activeConditionVariableTarget.value = ''
  activeConditionVariableGroupKey.value = ''
  conditionVariableSearch.value = ''
}

function addConditionBranch() {
  const branches = conditionBranches()
  persistConditionBranches([
    ...branches,
    {
      key: `branch_${branches.length + 1}`,
      name: `分支 ${branches.length + 1}`,
      logic: 'AND',
      conditions: [{
        left: normalizeConditionOperand('{{start.USER_INPUT}}'),
        operator: 'equals',
        right: normalizeConditionOperand(''),
      }],
    },
  ])
}

function removeConditionBranch(branchIndex: number) {
  const branches = conditionBranches()
  if (branches.length <= 1) return
  persistConditionBranches(branches.filter((_, index) => index !== branchIndex))
}

function addConditionRow(branchIndex: number) {
  persistConditionBranches(conditionBranches().map((branch, index) =>
    index === branchIndex
      ? {
        ...branch,
        conditions: [
          ...branch.conditions,
          { left: normalizeConditionOperand(''), operator: 'equals', right: normalizeConditionOperand('') },
        ],
      }
      : branch,
  ))
}

function removeConditionRow(branchIndex: number, conditionIndex: number) {
  persistConditionBranches(conditionBranches().map((branch, index) => {
    if (index !== branchIndex || branch.conditions.length <= 1) return branch
    return { ...branch, conditions: branch.conditions.filter((_, rowIndex) => rowIndex !== conditionIndex) }
  }))
}

function setHistoryEnabled(event: Event) {
  const target = event.target as HTMLInputElement | null
  setFieldValue('includeHistory', target?.checked ? 'true' : '')
}

function normalizeLlmSkillTabType(type: string): LlmSkillTabValue | null {
  const normalized = type.trim().toUpperCase().replace(/-/g, '_')
  if (['KNOWLEDGE', 'KNOWLEDGE_BASE', 'KNOWLEDGE_BASES', 'KNOWLEDGEBASE'].includes(normalized)) return 'KNOWLEDGE_BASE'
  if (['MCP', 'MCP_TOOL', 'MCP_TOOLS', 'MCP_SERVER', 'MCP_SERVER_TOOL', 'INTERNAL_TOOL', 'TOOL'].includes(normalized)) return 'MCP_TOOL'
  if (['API', 'API_TOOL', 'API_RESOURCE'].includes(normalized)) return 'API_TOOL'
  if (['SUBWORKFLOW', 'SUB_WORKFLOW', 'WORKFLOW'].includes(normalized)) return 'SUBWORKFLOW'
  if (['AGENT', 'AGENT_CALL'].includes(normalized)) return 'AGENT'
  return null
}

function llmSkillChoicesForTab(tab: LlmSkillTabValue): LlmSkillChoice[] {
  if (tab === 'KNOWLEDGE_BASE') {
    return [{
      key: 'knowledge-default',
      type: 'KNOWLEDGE_BASE',
      name: '知识库检索',
      description: '可运行 · 注入 LLM 上下文',
    }]
  }
  const registryChoices = workflowResources.value
    .filter((resource) => normalizeLlmSkillTabType(resource.resourceType) === tab)
    .map((resource) => ({
      key: resource.resourceId,
      type: tab,
      name: resource.displayName,
      description: `${resource.resourceType} · ${resourceStatusLabel(resource)}`,
      disabled: !isResourceSelectable(resource),
      registryResource: resource,
    }))
  if (registryChoices.length) return registryChoices
  const fallback: Record<LlmSkillTabValue, LlmSkillChoice> = {
    KNOWLEDGE_BASE: {
      key: 'knowledge-default',
      type: 'KNOWLEDGE_BASE',
      name: '知识库检索',
      description: '可运行 · 注入 LLM 上下文',
    },
    MCP_TOOL: {
      key: 'mcp-placeholder',
      type: 'MCP_TOOL',
      name: 'MCP 工具',
      description: '暂无可用工具 · 请先配置 MCP Server',
      disabled: true,
    },
    API_TOOL: {
      key: 'api-tool-placeholder',
      type: 'API_TOOL',
      name: 'API 工具',
      description: '暂无可用 API 工具 · 请先创建 Tool',
      disabled: true,
    },
    SUBWORKFLOW: {
      key: 'subworkflow-placeholder',
      type: 'SUBWORKFLOW',
      name: '工作流',
      description: '暂无可用子工作流',
      disabled: true,
    },
    AGENT: {
      key: 'agent-placeholder',
      type: 'AGENT',
      name: '智能体',
      description: '暂无可用智能体资源',
      disabled: true,
    },
  }
  return [fallback[tab]]
}

function llmResources(): LlmResource[] {
  if (!selectedNode.value || selectedNode.value.type !== 'LLM') return []
  const resources = selectedNode.value.config.resources
  return Array.isArray(resources) ? resources.filter((item): item is LlmResource => Boolean(item && typeof item === 'object')) : []
}

function persistLlmResources(resources: LlmResource[]) {
  if (!selectedNode.value || selectedNode.value.type !== 'LLM') return
  updateSelectedNode({ config: { resources } })
}

function normalizeLlmResourceType(resource: LlmResource): LlmResourceType {
  const type = String(resource.type || resource.resourceType || '').trim().toUpperCase().replace(/-/g, '_')
  if (['KNOWLEDGE', 'KNOWLEDGE_BASE', 'KNOWLEDGE_BASES', 'KNOWLEDGEBASE'].includes(type)) return 'KNOWLEDGE_BASE'
  if (['MCP', 'MCP_TOOL', 'MCP_TOOLS', 'MCP_SERVER', 'MCP_SERVER_TOOL', 'TOOL'].includes(type)) return 'MCP_TOOL'
  if (['API', 'API_TOOL', 'API_RESOURCE'].includes(type)) return 'API_TOOL'
  if (['SUBWORKFLOW', 'SUB_WORKFLOW', 'WORKFLOW'].includes(type)) return 'SUBWORKFLOW'
  if (['AGENT', 'AGENT_CALL'].includes(type)) return 'AGENT'
  return 'UNKNOWN'
}

function llmResourceLabel(resource: LlmResource) {
  const type = normalizeLlmResourceType(resource)
  if (type === 'KNOWLEDGE_BASE') return resource.name || '知识库检索'
  if (type === 'MCP_TOOL') return resource.name || 'MCP 工具'
  if (type === 'API_TOOL') return resource.name || 'API 工具'
  if (type === 'SUBWORKFLOW') return resource.name || '子工作流'
  if (type === 'AGENT') return resource.name || '智能体'
  return resource.name || '未知资源'
}

function llmResourceStatus(resource: LlmResource) {
  const type = normalizeLlmResourceType(resource)
  if (type === 'KNOWLEDGE_BASE') return '运行时会检索并注入模型上下文'
  if (type === 'MCP_TOOL') return '当前不可运行，运行时会被拦截'
  if (type === 'API_TOOL') return '当前等待 Spec 024 API 工具接入'
  if (type === 'SUBWORKFLOW') return '当前不可运行，运行时会被拦截'
  if (type === 'AGENT') return '当前等待智能体资源接入'
  return '未知类型，运行时会被拦截'
}

function addLlmKnowledgeResource() {
  const resources = llmResources()
  persistLlmResources([
    ...resources,
    {
      type: 'KNOWLEDGE_BASE',
      knowledgeBaseId: '',
      query: '{{start.USER_INPUT}}',
      topK: 3,
      enabled: true,
    },
  ])
  resourcePickerOpen.value = false
}

function selectLlmSkillResource(resource: LlmSkillChoice) {
  if (resource.disabled) return
  if (resource.type === 'KNOWLEDGE_BASE') {
    addLlmKnowledgeResource()
    return
  }
  persistLlmResources([
    ...llmResources(),
    {
      type: resource.type,
      resourceType: resource.type,
      resourceId: resource.registryResource?.resourceId || resource.key,
      name: resource.name,
      enabled: true,
    },
  ])
  resourcePickerOpen.value = false
  llmSkillSearch.value = ''
}

function updateLlmResource(index: number, patch: Partial<LlmResource>) {
  const resources = llmResources()
  if (!resources[index]) return
  persistLlmResources(resources.map((resource, itemIndex) => itemIndex === index ? { ...resource, ...patch } : resource))
}

function removeLlmResource(index: number) {
  persistLlmResources(llmResources().filter((_, itemIndex) => itemIndex !== index))
}

function canUseVariable(key: string) {
  return [
    'systemPrompt',
    'prompt',
    'query',
    'inputSource',
    'endpoint',
    'headers',
    'body',
    'output',
    'content',
    'template',
    'source',
    'pattern',
    'replacement',
  ].includes(key)
}

function handleVariableFieldInput(key: string, value: string | number | null | undefined) {
  const nextValue = String(value ?? '')
  const previousValue = String(fieldValue(key) ?? '')
  if (!canUseVariable(key)) {
    setFieldValue(key, nextValue)
    return
  }

  const trigger = completeVariableBraceTrigger(nextValue, previousValue)
  if (trigger.opened) {
    setFieldValue(key, trigger.value)
    openInlineVariablePicker(key)
    setActiveTextControlCaret(trigger.caret)
    return
  }

  setFieldValue(key, trigger.value)
  if (activeVariableField.value === key && !trigger.value.includes('{{')) {
    activeVariableField.value = ''
    variableSearch.value = ''
  }
}

function openInlineVariablePicker(key: string) {
  activeVariableField.value = key
  variableSearch.value = ''
  void nextTick(refreshInlineVariableSuggestionAnchor)
}

function setActiveTextControlCaret(caret: number | null) {
  if (caret === null) return
  void nextTick(() => {
    const element = document.activeElement
    if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
      element.setSelectionRange(caret, caret)
      refreshInlineVariableSuggestionAnchor()
    }
  })
}

function variableGroupKey(group: VariableCatalogGroup) {
  return `${group.scope}:${group.sourceKey}:${group.sourceLabel}`
}

function setActiveInputVariableGroup(group: VariableCatalogGroup) {
  activeInputVariableGroupKey.value = variableGroupKey(group)
}

function activateInputVariableGroup(group: VariableCatalogGroup, event: MouseEvent) {
  setActiveInputVariableGroup(group)
  refreshVariableFlyoutAnchor(event.currentTarget)
}

function setActiveOutputVariableGroup(group: VariableCatalogGroup) {
  activeOutputVariableGroupKey.value = variableGroupKey(group)
}

function activateOutputVariableGroup(group: VariableCatalogGroup, event: MouseEvent) {
  setActiveOutputVariableGroup(group)
  refreshVariableFlyoutAnchor(event.currentTarget)
}

function setActiveSchemaVariableGroup(group: VariableCatalogGroup) {
  activeSchemaVariableGroupKey.value = variableGroupKey(group)
}

function activateSchemaVariableGroup(group: VariableCatalogGroup, event: MouseEvent) {
  setActiveSchemaVariableGroup(group)
  refreshVariableFlyoutAnchor(event.currentTarget)
}

function setActiveStructuredVariableGroup(group: VariableCatalogGroup) {
  activeStructuredVariableGroupKey.value = variableGroupKey(group)
}

function activateStructuredVariableGroup(group: VariableCatalogGroup, event: MouseEvent) {
  setActiveStructuredVariableGroup(group)
  refreshVariableFlyoutAnchor(event.currentTarget)
}

function setActiveConditionVariableGroup(group: VariableCatalogGroup) {
  activeConditionVariableGroupKey.value = variableGroupKey(group)
}

function activateConditionVariableGroup(group: VariableCatalogGroup, event: MouseEvent) {
  setActiveConditionVariableGroup(group)
  refreshVariableFlyoutAnchor(event.currentTarget)
}

function inputReferenceSelection(reference: string) {
  const normalizedReference = reference.trim()
  if (!normalizedReference) return null
  for (const group of variableGroups.value) {
    const item = group.items.find((candidate) => candidate.reference === normalizedReference)
    if (item) return { group, item }
  }
  return null
}

function outputReferenceSelection(reference: string) {
  return inputReferenceSelection(reference)
}

function openInputVariablePicker(index: number, event?: Event) {
  refreshVariablePickerAnchor(event?.currentTarget)
  activeInputParameterIndex.value = activeInputParameterIndex.value === index ? null : index
  inputVariableSearch.value = ''
  activeInputVariableGroupKey.value = ''
}

function openOutputVariablePicker(index: number, event?: Event) {
  refreshVariablePickerAnchor(event?.currentTarget)
  activeOutputParameterIndex.value = activeOutputParameterIndex.value === index ? null : index
  outputVariableSearch.value = ''
  activeOutputVariableGroupKey.value = ''
}

function variableTypeLabel(type: VariableCatalogType) {
  return compactVariableTypeLabel(type)
}

function selectOptionLabel(key: string, option: string) {
  if (key === 'strategy' && option === 'first_non_empty') return '返回每个分组中第一个非空的值'
  if (key === 'language') {
    const labels: Record<string, string> = {
      python: 'Python',
      javascript: 'JavaScript',
    }
    return labels[option] ?? option
  }
  if (key === 'retrievalMode') {
    const labels: Record<string, string> = {
      auto: '智能推荐',
      hybrid: '综合匹配',
      semantic: '语义理解',
      keyword: '关键词匹配',
      faq: '仅问答库',
    }
    return labels[option] ?? option
  }
  return option
}

function variableListTypeLabel(type: VariableCatalogType) {
  const labels: Record<VariableCatalogType, string> = {
    string: 'String',
    number: 'Number',
    boolean: 'Boolean',
    object: 'Object',
    array: 'Array',
    file: 'File',
  }
  return labels[type] ?? String(type)
}

function insertVariable(key: string, reference: string) {
  const currentValue = String(fieldValue(key) || '')
  const normalizedReference = localizeInlineVariableReference(
    reference,
    selectedNode.value?.nodeKey || '',
    selectedNode.value?.type !== 'END',
  )
  const nextValue = canUseVariable(key)
    ? insertInlineVariableReference(currentValue, normalizedReference)
    : currentValue ? `${currentValue} ${normalizedReference}` : normalizedReference
  setFieldValue(key, nextValue)
  activeVariableField.value = ''
  variableSearch.value = ''
}

function insertInputParameterReference(index: number, reference: string) {
  updateInputParameter(index, { valueMode: 'reference', value: reference })
  activeInputParameterIndex.value = null
  activeInputVariableGroupKey.value = ''
  inputVariableSearch.value = ''
}

function insertOutputParameterReference(index: number, reference: string) {
  updateOutputParameter(index, { valueMode: 'reference', value: reference })
  activeOutputParameterIndex.value = null
  activeOutputVariableGroupKey.value = ''
  outputVariableSearch.value = ''
}

function clearInputParameterReference(index: number) {
  updateInputParameter(index, { valueMode: 'literal', value: '' })
}

function clearOutputParameterReference(index: number) {
  updateOutputParameter(index, { valueMode: 'literal', value: '' })
}

function insertSchemaInputMappingReference(index: number, reference: string) {
  const rows = schemaInputMappingRows()
  if (!rows[index]) return
  rows[index] = { ...rows[index], valueMode: 'reference', value: reference }
  persistSchemaInputMappings(rows)
  activeSchemaInputMappingIndex.value = null
  activeSchemaVariableGroupKey.value = ''
  schemaVariableSearch.value = ''
}

function clearSchemaInputMappingReference(index: number) {
  const rows = schemaInputMappingRows()
  if (!rows[index]) return
  rows[index] = { ...rows[index], valueMode: 'literal', value: '' }
  persistSchemaInputMappings(rows)
}

function insertStructuredVariableReference(target: string, reference: string) {
  if (target === 'assignment') {
    updateSelectedNode({ config: { sourceValueMode: 'reference', source: reference } })
  } else if (target.startsWith('aggregation:')) {
    const [, groupIndexText, variableIndexText] = target.split(':')
    const groupIndex = Number(groupIndexText)
    const variableIndex = Number(variableIndexText)
    if (Number.isInteger(groupIndex) && Number.isInteger(variableIndex)) {
      updateAggregationGroupVariable(groupIndex, variableIndex, { valueMode: 'reference', value: reference })
    } else if (Number.isInteger(groupIndex)) {
      updateAggregationSource(groupIndex, { valueMode: 'reference', value: reference })
    }
  }
  activeStructuredVariableTarget.value = ''
  activeStructuredVariableGroupKey.value = ''
  structuredVariableSearch.value = ''
}

function addGuideQuestion() {
  guideQuestions.value = [...guideQuestions.value, '']
  markGraphDirty()
}

function removeGuideQuestion(index: number) {
  guideQuestions.value = guideQuestions.value.filter((_item, itemIndex) => itemIndex !== index)
  markGraphDirty()
}

function chatflowScopeStateFromConfig(
  config: Record<string, any> = {},
  openState: Partial<Record<ChatflowVariableScopeKey, boolean>> = {},
): ChatflowScopeState[] {
  return buildChatflowVariableScopes({
    conversationVariables: chatflowVariableDefinitionsFromConfig(config.conversationVariables),
    userVariables: chatflowVariableDefinitionsFromConfig(config.userVariables),
  }).map((scope) => ({ ...scope, open: Boolean(openState[scope.scope]) }))
}

function chatflowVariableDefinitionsFromConfig(value: unknown): ChatflowVariableDefinition[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item): ChatflowVariableDefinition | null => {
      const raw = item && typeof item === 'object' ? item as Record<string, unknown> : {}
      const name = String(raw.name || raw.key || '').trim()
      if (!name) return null
      return {
        name,
        label: String(raw.label || name).trim(),
        type: String(raw.type || 'string').trim() || 'string',
      }
    })
    .filter((item): item is ChatflowVariableDefinition => item !== null)
}

function chatflowVariableScope(scope: ChatflowVariableScopeKey) {
  return chatflowVariableScopes.value.find((item) => item.scope === scope)
}

function toggleChatflowVariableScope(scope: ChatflowVariableScopeKey) {
  chatflowVariableScopes.value = chatflowVariableScopes.value.map((item) =>
    item.scope === scope ? { ...item, open: !item.open } : item,
  )
}

function chatflowCustomVariableDefinitions(scope: ChatflowVariableScopeKey): VariableDefinition[] {
  return (chatflowVariableScope(scope)?.items || [])
    .filter((item) => !item.readonly && item.name.trim())
    .map((item) => ({ name: item.name.trim(), type: item.type as VariableCatalogType }))
}

function chatflowCustomVariableConfig(scope: ChatflowVariableScopeKey): ChatflowVariableDefinition[] {
  return (chatflowVariableScope(scope)?.items || [])
    .filter((item) => !item.readonly && item.name.trim())
    .map((item) => ({ name: item.name.trim(), label: item.label.trim() || item.name.trim(), type: item.type || 'string' }))
}

function nextChatflowVariableName(scope: ChatflowVariableScopeKey) {
  const prefix = scope === 'conversation' ? 'conversation_var' : 'user_var'
  const existing = new Set((chatflowVariableScope(scope)?.items || []).map((item) => item.name))
  let index = 1
  let name = `${prefix}_${index}`
  while (existing.has(name)) {
    index += 1
    name = `${prefix}_${index}`
  }
  return name
}

function makeChatflowScopedVariable(scope: ChatflowVariableScopeKey, name: string, label = name, type = 'string') {
  const safeName = String(name || nextChatflowVariableName(scope)).trim() || nextChatflowVariableName(scope)
  const safeLabel = String(label || safeName).trim() || safeName
  return {
    key: safeName,
    label: safeLabel,
    name: safeName,
    type,
    reference: `{{${scope}.${safeName}}}`,
    readonly: false,
  }
}

function addChatflowScopedVariable(scope: ChatflowVariableScopeKey) {
  const name = nextChatflowVariableName(scope)
  chatflowVariableScopes.value = chatflowVariableScopes.value.map((item) =>
    item.scope === scope
      ? { ...item, open: true, items: [...item.items, makeChatflowScopedVariable(scope, name)] }
      : item,
  )
  markGraphDirty()
}

function updateChatflowScopedVariable(
  scope: ChatflowVariableScopeKey,
  itemIndex: number,
  field: 'name' | 'label',
  value: string,
) {
  chatflowVariableScopes.value = chatflowVariableScopes.value.map((item) => {
    if (item.scope !== scope || !item.items[itemIndex] || item.items[itemIndex].readonly) return item
    const nextItems = item.items.map((variable, index) => {
      if (index !== itemIndex) return variable
      const nextName = field === 'name' ? String(value || '').trim() : variable.name
      const nextLabel = field === 'label' ? String(value || '').trim() : variable.label
      return makeChatflowScopedVariable(scope, nextName || variable.name, nextLabel || variable.label, variable.type)
    })
    return { ...item, items: nextItems }
  })
  markGraphDirty()
}

function removeChatflowScopedVariable(scope: ChatflowVariableScopeKey, itemIndex: number) {
  chatflowVariableScopes.value = chatflowVariableScopes.value.map((item) =>
    item.scope === scope
      ? { ...item, items: item.items.filter((variable, index) => variable.readonly || index !== itemIndex) }
      : item,
  )
  markGraphDirty()
}

function setChatflowHistoryRetentionRounds(value: string | number) {
  const numeric = Number(value)
  chatflowHistoryRetentionRounds.value = Math.max(0, Math.min(20, Number.isFinite(numeric) ? Math.round(numeric) : 3))
  markGraphDirty()
}

async function applyGuideQuestion(question: string) {
  testInput.value = question
  if (isChatflowMode.value) {
    await sendChatflowMessage()
  }
}

async function sendChatflowMessage() {
  if (running.value || !testInput.value.trim()) return
  await runCanvasTest()
}

function resetChatflowTrialSession() {
  chatflowTrialMessages.value = []
  testResult.value = null
  lastRunOutput.value = null
  lastTestRunStatus.value = ''
  lastTestRunId.value = 0
  testProfile.value.round = 1
  resetChatflowDebugState()
}

function resetChatflowConversationSettings() {
  openingText.value = '你好，我可以帮你处理订单、售后和产品咨询。'
  guideQuestions.value = ['查订单进度', '申请退款', '咨询发票']
  chatflowHistoryRetentionRounds.value = 3
  chatflowHistorySettingsOpen.value = false
  chatflowVariableScopes.value = chatflowScopeStateFromConfig()
}

function syncChatflowSettingsFromGraph() {
  if (!isChatflowMode.value) return
  const startConfig = graph.value.nodes.find((node) => node.nodeKey === 'start')?.config || {}
  openingText.value = String(startConfig.openingText || '你好，我可以帮你处理订单、售后和产品咨询。')
  guideQuestions.value = Array.isArray(startConfig.guideQuestions)
    ? startConfig.guideQuestions.map(String)
    : ['查订单进度', '申请退款', '咨询发票']
  const retention = Number(startConfig.historyRetentionRounds ?? 3)
  chatflowHistoryRetentionRounds.value = Math.max(0, Math.min(20, Number.isFinite(retention) ? Math.round(retention) : 3))
  const openState = Object.fromEntries(chatflowVariableScopes.value.map((scope) => [scope.scope, scope.open]))
  chatflowVariableScopes.value = chatflowScopeStateFromConfig(startConfig, openState)
}

function graphForPersistence() {
  if (!isChatflowMode.value) return graph.value
  return {
    ...graph.value,
    nodes: graph.value.nodes.map((node) =>
      node.nodeKey === 'start'
        ? {
          ...node,
          config: {
            ...node.config,
            openingText: openingText.value,
            guideQuestions: guideQuestions.value.map((item) => item.trim()).filter(Boolean),
            historyRetentionRounds: chatflowHistoryRetentionRounds.value,
            conversationVariables: chatflowCustomVariableConfig('conversation'),
            userVariables: chatflowCustomVariableConfig('user'),
          },
        }
        : node,
    ),
  }
}

function currentGraphSnapshot() {
  return JSON.stringify(serializeWorkflowGraph(graphForPersistence()))
}

function readonlyValues(key: string) {
  if (!selectedNode.value) return []
  const value = selectedNode.value.config[key]
  if (Array.isArray(value)) return value.map(String)
  return value ? [String(value)] : []
}

function selectedOutputConfig() {
  return normalizeOutputConfig(selectedNode.value?.config || {}, {
    respectExplicitEmpty: selectedNode.value?.type === 'END',
  })
}

function outputFormatValue() {
  return selectedOutputConfig().format
}

function shouldShowOutputFormat() {
  return true
}

function outputParameterRows() {
  return selectedOutputConfig().parameters
}

function outputParameterTypeLabel(type: OutputParameterType) {
  return variableTypeLabel(type)
}

function shouldEditOutputParameterValue() {
  return selectedNode.value?.type === 'END'
}

function outputParameterValueMode(row: OutputParameter) {
  return row.valueMode || 'literal'
}

function outputParameterValue(row: OutputParameter) {
  return String(row.value ?? '')
}

function endReturnMode() {
  const value = selectedNode.value?.config.returnMode
  return value === 'variables' || value === '返回变量' ? 'variables' : 'text'
}

function setEndReturnMode(mode: 'text' | 'variables') {
  updateSelectedNode({ config: { returnMode: mode } })
}

function persistOutputParameters(format: OutputFormat, parameters: OutputParameter[]) {
  const normalizedParameters = parameters.map((item) => ({
    name: item.name.trim(),
    type: item.type,
    ...(shouldEditOutputParameterValue()
      ? {
        valueMode: outputParameterValueMode(item),
        value: item.value ?? '',
      }
      : {}),
  }))
  updateSelectedNode({
    config: {
      outputFormat: format,
      outputParameters: normalizedParameters,
      outputVariable: normalizedParameters[0]?.name || '',
    },
  })
}

function setOutputFormat(value: string) {
  persistOutputParameters(value as OutputFormat, outputParameterRows())
}

function setOutputParameterName(index: number, value: string | number) {
  const rows = outputParameterRows().map((row, rowIndex) =>
    rowIndex === index ? { ...row, name: String(value) } : row,
  )
  persistOutputParameters(outputFormatValue(), rows)
}

function setOutputParameterType(index: number, value: string) {
  const type = outputParameterTypeOptions.includes(value as OutputParameterType) ? value as OutputParameterType : 'string'
  const rows = outputParameterRows().map((row, rowIndex) =>
    rowIndex === index ? { ...row, type } : row,
  )
  persistOutputParameters(outputFormatValue(), rows)
}

function updateOutputParameter(index: number, patch: Partial<OutputParameter>) {
  const rows = outputParameterRows()
  if (!rows[index]) return
  persistOutputParameters(outputFormatValue(), rows.map((row, rowIndex) =>
    rowIndex === index ? { ...row, ...patch } : row,
  ))
}

function setOutputParameterValue(index: number, value: string | number | boolean | null | undefined) {
  updateOutputParameter(index, { valueMode: 'literal', value: value ?? '' })
}

function nextOutputParameterName() {
  const names = new Set(outputParameterRows().map((row) => row.name))
  if (!names.size) return 'output'
  let index = outputParameterRows().length + 1
  let name = `output_${index}`
  while (names.has(name)) {
    index += 1
    name = `output_${index}`
  }
  return name
}

function addOutputParameter() {
  persistOutputParameters(outputFormatValue(), [
    ...outputParameterRows(),
    {
      name: nextOutputParameterName(),
      type: 'string',
      ...(shouldEditOutputParameterValue() ? { valueMode: 'literal' as const, value: '' } : {}),
    },
  ])
}

function removeOutputParameter(index: number) {
  const rows = outputParameterRows()
  if (rows.length <= 1 && selectedNode.value?.type !== 'END') return
  persistOutputParameters(outputFormatValue(), rows.filter((_row, rowIndex) => rowIndex !== index))
  if (activeOutputParameterIndex.value === index) {
    activeOutputParameterIndex.value = null
    activeOutputVariableGroupKey.value = ''
    outputVariableSearch.value = ''
  }
}

function canRemoveOutputParameter() {
  return selectedNode.value?.type === 'END' || outputParameterRows().length > 1
}

function outputParameterErrors() {
  return validateOutputParameters(outputParameterRows())
}

function autoLayoutCanvas() {
  graph.value = autoLayoutWorkflowGraph(graph.value)
  markGraphDirty()
}

async function loadLlmProviderModels() {
  const pageSize = 100
  const providers: ProviderVO[] = []
  let page = 1
  let total = 0
  try {
    do {
      const response = await getProviderList({ page, pageSize, enabled: true })
      providers.push(...(response.list || []))
      total = Number(response.total || providers.length)
      page += 1
    } while (providers.length < total && page <= 50)
    llmProviderModelOptions.value = buildLlmModelOptions(providers)
  } catch {
    llmProviderModelOptions.value = []
  }
}

async function loadWorkflowResourceRegistry() {
  try {
    const result = await listWorkflowResources({ flowType: isChatflowMode.value ? 'CHATFLOW' : 'WORKFLOW' })
    workflowResources.value = Array.isArray(result.list) ? result.list as WorkflowResource[] : []
  } catch {
    workflowResources.value = []
  }
}

async function loadWorkflow() {
  await loadWorkflowResourceRegistry()
  if (!isEditing.value) {
    graph.value = createDefaultGraph()
    form.value = defaultForm()
    resetChatflowConversationSettings()
    workflowStatus.value = 'DRAFT'
    lastSavedAt.value = ''
    canvasDirty.value = false
    dirtySinceTestRun.value = true
    // On the create entry the canvas has no name yet, so render the title input directly
    // instead of hiding it behind the display button. This keeps the placeholder reachable
    // for users (and E2E) without an extra click.
    flowTitleDraft.value = ''
    flowTitleEditing.value = true
    requestCanvasLayoutRefit()
    return
  }
  loading.value = true
  try {
    const detail = (await (isChatflowMode.value ? getChatflow(workflowId.value) : getWorkflow(workflowId.value))) as WorkflowDetail
    form.value = { name: detail.name, description: detail.description || '' }
    workflowStatus.value = detail.status
    graph.value = hydrateWorkflowGraph(detail.nodes, detail.edges)
    syncChatflowSettingsFromGraph()
    lastSavedAt.value = formatClock(new Date(detail.updatedAt))
    canvasDirty.value = false
    if (!running.value) dirtySinceTestRun.value = true
    await applyWorkflowRunDebugRoute()
    await applyChatflowRunDebugRoute()
    requestCanvasLayoutRefit()
  } finally {
    loading.value = false
  }
}

async function saveCanvas(options: { silent?: boolean } = {}) {
  commitFlowTitleEdit()
  if (!form.value.name.trim()) {
    message.warning(isChatflowMode.value ? '请输入 Chatflow 名称' : '请输入工作流名称')
    return
  }
  const payload = serializeWorkflowGraph(graphForPersistence())
  saving.value = true
  try {
    if (isEditing.value) {
      const update = isChatflowMode.value ? updateChatflow : updateWorkflow
      await update(workflowId.value, {
        name: form.value.name,
        description: form.value.description,
        nodes: payload.nodes,
        edges: payload.edges,
      })
      if (!options.silent) message.success('画布已保存')
      lastSavedAt.value = formatClock(new Date())
      canvasDirty.value = false
      return workflowId.value
    } else {
      const create = isChatflowMode.value ? createChatflow : createWorkflow
      const created = await create({
        name: form.value.name,
        description: form.value.description,
        nodes: payload.nodes,
        edges: payload.edges,
      }) as WorkflowDetail
      if (!options.silent) message.success(isChatflowMode.value ? 'Chatflow 创建成功' : '工作流创建成功')
      await router.replace(canvasRoute(created.id))
      lastSavedAt.value = formatClock(new Date())
      canvasDirty.value = false
      return created.id
    }
  } catch (e: any) {
    message.error(e?.message || '保存失败')
    return 0
  } finally {
    saving.value = false
  }
}

function openTestPanel() {
  const validation = validateWorkflowGraph(graph.value)
  validationErrors.value = validation.errors
  if (!validation.valid) {
    testPanelOpen.value = false
    nodeTestDrawerOpen.value = false
    publishDialogOpen.value = false
    selectedNodeKey.value = ''
    debugDockOpen.value = true
    debugDockTab.value = 'errors'
    return
  }
  applyComposerSurfaceAction('compose')
  testPanelOpen.value = true
  nodeTestDrawerOpen.value = false
  publishDialogOpen.value = false
  selectedNodeKey.value = ''
  testResult.value = null
  resetChatflowDebugState()
}

function openSelectedNodeTest() {
  const node = selectedNode.value
  if (!node || !canRunSingleNodeTest(node)) return
  openNodeTest(node)
}

function openNodeCardTest(nodeKey: string) {
  const node = graph.value.nodes.find((item) => item.nodeKey === nodeKey)
  if (!node || !canRunSingleNodeTest(node)) return
  selectedNodeKey.value = nodeKey
  nodeCardMenuKey.value = ''
  openNodeTest(node)
}

function openNodeTest(node: WorkflowCanvasNode) {
  applyComposerSurfaceAction('compose')
  nodeTestTargetKey.value = node.nodeKey
  nodeTestDrawerOpen.value = true
  testPanelOpen.value = false
  publishDialogOpen.value = false
  nodeTestResult.value = null
  nodeTestError.value = ''
  nodeTestInputs.value = buildNodeTestInputs(node, {
    isChatflowMode: isChatflowMode.value,
    defaultMessage: testInput.value || 'hello',
  })
}

function closeSelectedNodeTest() {
  nodeTestDrawerOpen.value = false
  nodeTestRunning.value = false
  nodeTestError.value = ''
}

function setNodeTestInput(name: string, value: string) {
  nodeTestInputs.value = nodeTestInputs.value.map((row) => row.name === name ? { ...row, value } : row)
}

function openRunLogPanel() {
  const action = resolveRunLogAction(lastTestRunId.value, testResult.value?.runtimeVersion)
  if (action.shouldOpenRunDetail) {
    openObserveRunDetail()
    return
  }
  debugDockOpen.value = true
  debugDockTab.value = 'debug'
}

async function runSelectedNodeTest() {
  const target = nodeTestTarget.value
  if (!target || !canRunSingleNodeTest(target)) return
  ensureCanvasNameForRun()
  const id = await saveCanvas({ silent: true })
  if (!id) return
  nodeTestRunning.value = true
  nodeTestResult.value = null
  nodeTestError.value = ''
  try {
    nodeTestResult.value = await (isChatflowMode.value
      ? runChatflowNode(id, target.nodeKey, nodeTestInputPayload(nodeTestInputs.value))
      : runWorkflowNode(id, target.nodeKey, nodeTestInputPayload(nodeTestInputs.value))) as any
  } catch (e: any) {
    nodeTestError.value = e?.message || '节点试运行失败'
  } finally {
    nodeTestRunning.value = false
  }
}

function currentComposerSurfaceState() {
  return {
    canvasTab: canvasTab.value,
    debugDockOpen: debugDockOpen.value,
    debugDockTab: debugDockTab.value,
    publishDialogOpen: publishDialogOpen.value,
    rightPanelOpen: rightSidePanelOpen.value,
  }
}

function applyComposerSurfaceAction(action: ComposerSurfaceAction) {
  const next = resolveComposerSurfaceAction(currentComposerSurfaceState(), action)
  canvasTab.value = next.canvasTab
  debugDockOpen.value = next.debugDockOpen
  debugDockTab.value = next.debugDockTab
  publishDialogOpen.value = next.publishDialogOpen
}

function selectCanvasTab(tab: CanvasTab) {
  if (tab === 'open') {
    openOpenSurface()
    return
  }
  applyComposerSurfaceAction('compose')
}

function openOpenSurface() {
  applyComposerSurfaceAction('open')
  testPanelOpen.value = false
  nodeTestDrawerOpen.value = false
  selectedNodeKey.value = ''
  if (isChatflowMode.value) {
    void loadChatflowChannels()
  }
}

function openPublishDialog() {
  applyComposerSurfaceAction('publish')
  testPanelOpen.value = false
  nodeTestDrawerOpen.value = false
  selectedNodeKey.value = ''
  void loadWorkflowVersions()
}

function openDebugDetails() {
  applyComposerSurfaceAction('debug')
  publishDialogOpen.value = false
  if (!lastTestRunId.value) return
  if (isChatflowMode.value) {
    void loadChatflowRunDebugDetail(lastTestRunId.value)
  } else {
    void loadWorkflowRunDebugDetail(lastTestRunId.value)
  }
}

function openObserveRunDetail() {
  const action = resolveRunLogAction(lastTestRunId.value, testResult.value?.runtimeVersion)
  if (!action.shouldOpenRunDetail) return
  debugDockOpen.value = true
  debugDockTab.value = 'debug'
  if (isChatflowMode.value) {
    const link = buildChatflowRunDebugLink(workflowId.value, { runId: lastTestRunId.value }) as Record<string, any>
    void router.push({ ...link, query: { ...(link.query || {}), ...action.runtimeQuery } })
    if (testResult.value?.runtimeVersion === 'v2') {
      void loadRuntimeV2DebugDetail(lastTestRunId.value, 'CHATFLOW')
    } else {
      void loadChatflowRunDebugDetail(lastTestRunId.value)
    }
  } else {
    const link = buildWorkflowRunDebugLink(workflowId.value, { runId: lastTestRunId.value }) as Record<string, any>
    void router.push({ ...link, query: { ...(link.query || {}), ...action.runtimeQuery } })
    if (testResult.value?.runtimeVersion === 'v2') {
      void loadRuntimeV2DebugDetail(lastTestRunId.value, 'WORKFLOW')
    } else {
      void loadWorkflowRunDebugDetail(lastTestRunId.value)
    }
  }
}

async function loadRuntimeV2DebugDetail(runId: number, ownerType: 'WORKFLOW' | 'CHATFLOW') {
  const [run, eventPage, nodePage] = await Promise.all([
    getRuntimeV2Run(runId) as Promise<RuntimeV2StartRef>,
    listRuntimeV2Events(runId, { afterSequence: 0 }) as Promise<{ list: RuntimeV2Event[]; total: number }>,
    listRuntimeV2Nodes(runId) as Promise<{ list: RuntimeV2Node[]; total: number }>,
  ])
  let detail = createRuntimeV2DebugDetail({
    ...run,
    runId,
    ownerType: run.ownerType || ownerType,
  })
  detail = mergeRuntimeV2RunToDebugDetail(
    applyRuntimeV2NodesToDebugDetail(
      applyRuntimeV2EventsToDebugDetail(detail, eventPage.list || []),
      nodePage.list || [],
    ),
    run,
  )
  if (ownerType === 'CHATFLOW') {
    chatflowRunEvents.value = eventPage.list || []
  }
  setRuntimeV2DebugDetail(ownerType, detail)
  updateRuntimeV2RunState(ownerType, detail, run)
  if (!isRuntimeV2TerminalStatus(detail.status)) {
    void observeRuntimeV2Run(ownerType, run)
  }
}

async function loadWorkflowRunDebugDetail(runId: number) {
  if (!workflowId.value || !runId || isChatflowMode.value) return
  workflowRunDebugLoading.value = true
  try {
    if (route.query.runtime === 'v2') {
      try {
        await loadRuntimeV2DebugDetail(runId, 'WORKFLOW')
        return
      } catch {
        // Compatibility fallback: older runs still use the legacy debug detail route.
      }
    }
    const detail = await getWorkflowRunDebug(workflowId.value, runId) as WorkflowRunDebugDetail
    workflowRunDebugDetail.value = detail
    ensureSelectedDebugNode(detail.nodeDetails || [])
    lastTestRunId.value = Number(detail.runId || runId)
    lastTestRunStatus.value = String(detail.status || '')
    lastRunOutput.value = detail.output || null
    testResult.value = {
      runId: detail.runId,
      status: detail.status,
      output: detail.output || {},
    }
  } catch (e: any) {
    validationErrors.value = [e?.message || '加载运行详情失败']
  } finally {
    workflowRunDebugLoading.value = false
  }
}

async function applyWorkflowRunDebugRoute() {
  if (isChatflowMode.value || route.query.debug !== '1') return
  const queryRunId = Array.isArray(route.query.runId) ? route.query.runId[0] : route.query.runId
  const queryExecuteId = Array.isArray(route.query.executeId) ? route.query.executeId[0] : route.query.executeId
  const runId = Number(queryRunId || queryExecuteId || 0)
  if (!runId) return
  debugDockOpen.value = true
  debugDockTab.value = 'debug'
  lastTestRunId.value = runId
  await loadWorkflowRunDebugDetail(runId)
}

async function loadChatflowRunDebugDetail(runId: number) {
  if (!workflowId.value || !runId || !isChatflowMode.value) return
  chatflowRunDebugLoading.value = true
  try {
    if (route.query.runtime === 'v2') {
      try {
        await loadRuntimeV2DebugDetail(runId, 'CHATFLOW')
        return
      } catch {
        // Compatibility fallback: older runs still use the legacy debug detail route.
      }
    }
    const detail = await getChatflowRunDebug(workflowId.value, runId) as ChatflowRunDebugDetail
    chatflowRunDebugDetail.value = detail
    ensureSelectedDebugNode(detail.nodeDetails || [])
    lastTestRunId.value = Number(detail.runId || runId)
    lastTestRunStatus.value = String(detail.status || '')
    lastRunOutput.value = detail.output || null
    chatflowRunEvents.value = detail.events || []
    chatflowSessionState.value = {
      ...(detail.session || {}),
      sessionId: String(detail.session?.sessionId || ''),
      status: String(detail.session?.status || ''),
      variables: detail.variables || {},
      currentRunId: Number(detail.session?.currentRunId || detail.runId || runId),
      waitingEvent: detail.waitingEvent || null,
      checkpoint: detail.checkpoint || null,
    } as ChatflowSessionState
    testResult.value = {
      runId: detail.runId,
      status: detail.status,
      output: detail.output || {},
      sessionId: detail.session?.sessionId,
      sessionStatus: detail.session?.status,
      streamEvents: detail.streamEvents || [],
    }
  } catch (e: any) {
    validationErrors.value = [e?.message || '加载 Chatflow 运行详情失败']
  } finally {
    chatflowRunDebugLoading.value = false
  }
}

async function applyChatflowRunDebugRoute() {
  if (!isChatflowMode.value || route.query.debug !== '1') return
  const queryRunId = Array.isArray(route.query.runId) ? route.query.runId[0] : route.query.runId
  const queryExecuteId = Array.isArray(route.query.executeId) ? route.query.executeId[0] : route.query.executeId
  const runId = Number(queryRunId || queryExecuteId || 0)
  if (!runId) return
  debugDockOpen.value = true
  debugDockTab.value = 'debug'
  lastTestRunId.value = runId
  await loadChatflowRunDebugDetail(runId)
}

async function loadChatflowChannels() {
  if (!workflowId.value) {
    chatflowChannels.value = []
    return
  }
  chatflowChannelsLoading.value = true
  try {
    const response = await listChatflowChannels(workflowId.value)
    chatflowChannels.value = response.list || []
  } catch {
    chatflowChannels.value = []
  } finally {
    chatflowChannelsLoading.value = false
  }
}

async function runCanvasTestWithRuntimeV2(
  id: number,
  input: Record<string, any>,
): Promise<Record<string, any> | null> {
  const ownerType = isChatflowMode.value ? 'CHATFLOW' : 'WORKFLOW'
  let started: RuntimeV2StartRef
  try {
    started = await (isChatflowMode.value
      ? runChatflowV2(id, input, runtimeV2IdempotencyKey(ownerType, id), undefined, { silentError: true })
      : runWorkflowV2(id, input, runtimeV2IdempotencyKey(ownerType, id), undefined, { silentError: true })) as RuntimeV2StartRef
  } catch {
    return null
  }

  const detail = createRuntimeV2DebugDetail({
    ...started,
    ownerType: started.ownerType || ownerType,
    ownerId: started.ownerId || id,
  })
  setRuntimeV2DebugDetail(ownerType, detail)
  updateRuntimeV2RunState(ownerType, detail, started)
  return observeRuntimeV2Run(ownerType, started)
}

async function observeRuntimeV2Run(
  ownerType: string,
  started: RuntimeV2StartRef,
): Promise<Record<string, any>> {
  const runId = Number(started.runId || 0)
  if (!runId) return runtimeV2ResultPayload(createRuntimeV2DebugDetail(started), started)

  let detail = currentRuntimeV2DebugDetail(ownerType) || createRuntimeV2DebugDetail(started)
  let latestRun: RuntimeV2StartRef = started
  let streamObserver: RuntimeV2DebugEventObserver | null = null
  const applyRuntimeV2EventBatch = (events: RuntimeV2Event[]) => {
    if (!events.length) return
    if (ownerType === 'CHATFLOW') {
      appendChatflowRuntimeV2Events(events)
    }
    detail = applyRuntimeV2EventsToDebugDetail(detail, events)
    setRuntimeV2DebugDetail(ownerType, detail)
    updateRuntimeV2RunState(ownerType, detail, latestRun)
    if (isRuntimeV2TerminalStatus(detail.status)) streamObserver?.close()
  }

  streamObserver = openRuntimeV2DebugEventObserver({
    started,
    listRuntimeV2Events: (targetRunId, params) => listRuntimeV2Events(targetRunId, params) as Promise<{ list: RuntimeV2Event[]; total: number }>,
    onEvents: applyRuntimeV2EventBatch,
  })
  const observer = streamObserver

  try {
    for (let attempt = 0; attempt < RUNTIME_V2_MAX_POLLS; attempt += 1) {
      const [eventPage, nodePage, run] = await Promise.all([
        listRuntimeV2Events(runId, { afterSequence: observer.lastSequence() }),
        listRuntimeV2Nodes(runId),
        getRuntimeV2Run(runId),
      ])
      const events = observer.markEventsApplied((eventPage.list || []) as RuntimeV2Event[])
      const nodes = (nodePage.list || []) as RuntimeV2Node[]
      applyRuntimeV2EventBatch(events)
      latestRun = run as RuntimeV2StartRef
      detail = mergeRuntimeV2RunToDebugDetail(
        applyRuntimeV2NodesToDebugDetail(detail, nodes),
        latestRun,
      )
      setRuntimeV2DebugDetail(ownerType, detail)
      updateRuntimeV2RunState(ownerType, detail, latestRun)
      if (isRuntimeV2TerminalStatus(detail.status)) return runtimeV2ResultPayload(detail, latestRun)
      await waitRuntimeV2PollDelay()
    }

    return runtimeV2ResultPayload(detail, latestRun)
  } finally {
    observer.close()
  }
}

async function cancelCurrentRuntimeV2Run() {
  const runId = Number(lastTestRunId.value || 0)
  if (!runId || !canCancelRuntimeV2Run.value || runtimeV2Cancelling.value) return
  const ownerType = isChatflowMode.value ? 'CHATFLOW' : 'WORKFLOW'
  runtimeV2Cancelling.value = true
  try {
    const cancelled = await cancelRuntimeV2Run(runId) as RuntimeV2StartRef
    const current = currentRuntimeV2DebugDetail(ownerType) || createRuntimeV2DebugDetail({
      runId,
      ownerType,
      ownerId: workflowId.value,
      status: lastTestRunStatus.value || 'RUNNING',
    })
    const detail = mergeRuntimeV2RunToDebugDetail(current, {
      ...cancelled,
      runId: Number(cancelled.runId || runId),
      ownerType: cancelled.ownerType || ownerType,
      ownerId: cancelled.ownerId || workflowId.value,
    })
    setRuntimeV2DebugDetail(ownerType, detail)
    updateRuntimeV2RunState(ownerType, detail, cancelled)
    await loadRuntimeV2DebugDetail(runId, ownerType)
    message.success('已取消运行')
  } catch (e: any) {
    message.error(e?.message || '取消运行失败')
  } finally {
    runtimeV2Cancelling.value = false
  }
}

function setRuntimeV2DebugDetail(ownerType: string, detail: WorkflowRunDebugDetail) {
  if (ownerType === 'CHATFLOW') {
    chatflowRunDebugDetail.value = detail as ChatflowRunDebugDetail
    ensureSelectedDebugNode(detail.nodeDetails || [])
  } else {
    workflowRunDebugDetail.value = detail
    ensureSelectedDebugNode(detail.nodeDetails || [])
  }
}

function appendChatflowRuntimeV2Events(events: RuntimeV2Event[]) {
  if (!events.length) return
  const merged = new Map<string, any>()
  for (const event of chatflowRunEvents.value || []) {
    merged.set(runtimeV2EventKey(event), event)
  }
  for (const event of events) {
    merged.set(runtimeV2EventKey(event), event)
  }
  chatflowRunEvents.value = Array.from(merged.values()).sort(
    (left, right) => Number(left.sequence || 0) - Number(right.sequence || 0),
  )
}

function runtimeV2EventKey(event: any) {
  return [
    Number(event.sequence || 0),
    String(event.id || ''),
    String(event.type || ''),
    String(event.nodeId || event.nodeKey || ''),
  ].join(':')
}

function currentRuntimeV2DebugDetail(ownerType: string): WorkflowRunDebugDetail | null {
  return ownerType === 'CHATFLOW' ? chatflowRunDebugDetail.value : workflowRunDebugDetail.value
}

function updateRuntimeV2RunState(
  ownerType: string,
  detail: WorkflowRunDebugDetail,
  run: RuntimeV2StartRef,
) {
  const payload = runtimeV2ResultPayload(detail, run)
  testResult.value = payload
  lastTestRunId.value = Number(detail.runId || run.runId || 0)
  lastTestRunStatus.value = String(detail.status || run.status || '')
  lastRunOutput.value = detail.output || run.output || null
  if (ownerType === 'CHATFLOW') {
    const nextSession = projectRuntimeV2ChatflowSessionState(
      run as Record<string, any>,
      detail.status || run.status,
      chatflowSessionState.value || null,
    ) as ChatflowSessionState
    chatflowSessionState.value = nextSession
    chatflowRunDebugDetail.value = withChatflowSessionState(
      (chatflowRunDebugDetail.value || detail) as ChatflowRunDebugDetail,
      nextSession,
    )
  }
}

function runtimeV2ResultPayload(
  detail: WorkflowRunDebugDetail,
  run: RuntimeV2StartRef,
): Record<string, any> {
  return {
    ...run,
    runId: Number(detail.runId || run.runId || 0),
    ownerType: detail.ownerType || run.ownerType,
    status: String(detail.status || run.status || ''),
    output: detail.output || run.output || {},
    error: detail.error || run.error || '',
    runtimeVersion: 'v2',
  }
}

function runtimeV2IdempotencyKey(ownerType: string, id: number) {
  return `canvas-debug-${ownerType.toLowerCase()}-${id}-${Date.now()}`
}

function waitRuntimeV2PollDelay() {
  return new Promise((resolve) => window.setTimeout(resolve, RUNTIME_V2_POLL_DELAY_MS))
}

async function runCanvasTest() {
  const runMessage = testInput.value.trim()
  if (isChatflowMode.value && !runMessage) {
    validationErrors.value = ['请输入消息']
    return
  }
  const validation = validateWorkflowGraph(graph.value)
  validationErrors.value = validation.errors
  testResult.value = null
  if (!validation.valid) return

  let pendingAssistantMessageId = 0
  if (isChatflowMode.value) {
    const messageId = Date.now()
    pendingAssistantMessageId = messageId + 1
    chatflowTrialMessages.value = [
      ...chatflowTrialMessages.value,
      { id: messageId, role: 'user', content: runMessage },
      { id: pendingAssistantMessageId, role: 'assistant', content: '', loading: true },
    ]
    testInput.value = ''
  }
  optimisticRunNodeKeys.value = new Set(graph.value.nodes.map((node) => node.nodeKey))
  running.value = true
  try {
    ensureCanvasNameForRun()
    const id = await saveCanvas({ silent: true })
    if (!id) throw new Error('保存画布失败')

    const runInput = isChatflowMode.value
      ? buildChatflowRunInput({ message: runMessage, ...testProfile.value, historyRetentionRounds: chatflowHistoryRetentionRounds.value })
      : {
        userMessage: testInput.value,
        USER_INPUT: testInput.value,
      }
    const runtimeV2Result = await runCanvasTestWithRuntimeV2(id, runInput)
    const result = runtimeV2Result || (await (isChatflowMode.value
      ? runChatflowLegacy(id, runInput)
      : runWorkflow(id, runInput)) as any)
    testResult.value = result
    lastTestRunStatus.value = String(result?.status || '')
    lastTestRunId.value = Number(result?.runId || 0)
    lastRunOutput.value = result?.output || null
    if (!isChatflowMode.value && lastTestRunId.value) {
      if (result?.runtimeVersion === 'v2') {
        await loadRuntimeV2DebugDetail(lastTestRunId.value, 'WORKFLOW')
      } else {
        await loadWorkflowRunDebugDetail(lastTestRunId.value)
      }
    }
    dirtySinceTestRun.value = false
    lastTestRunGraphSnapshot.value = currentGraphSnapshot()
    if (isChatflowMode.value) {
      const streamPreview = buildChatflowStreamPreview(result?.streamEvents, result?.output)
      const assistantMessage = {
        id: pendingAssistantMessageId || Date.now(),
        role: 'assistant',
        content: formatChatflowAssistantText(result?.output, streamPreview),
        streaming: false,
      } as ChatflowTrialMessage
      if (pendingAssistantMessageId) {
        chatflowTrialMessages.value = chatflowTrialMessages.value.map((message) =>
          message.id === pendingAssistantMessageId ? assistantMessage : message,
        )
      } else {
        chatflowTrialMessages.value = [...chatflowTrialMessages.value, assistantMessage]
      }
      testProfile.value.round += 1
      if (debugDockOpen.value && result?.runtimeVersion !== 'v2') {
        debugDockTab.value = 'debug'
        await loadChatflowDebugState(id, result)
      }
    } else if (debugDockOpen.value && debugDockTab.value === 'debug' && lastTestRunId.value && result?.runtimeVersion !== 'v2') {
      await loadWorkflowRunDebugDetail(lastTestRunId.value)
    }
  } catch (e: any) {
    lastTestRunStatus.value = 'FAILED'
    validationErrors.value = [e?.message || '运行失败']
    if (isChatflowMode.value && pendingAssistantMessageId) {
      chatflowTrialMessages.value = chatflowTrialMessages.value.map((message) =>
        message.id === pendingAssistantMessageId
          ? {
              id: pendingAssistantMessageId,
              role: 'assistant',
              content: e?.message || '运行失败',
              error: true,
            }
          : message,
      )
    }
  } finally {
    running.value = false
    optimisticRunNodeKeys.value = new Set()
  }
}

function ensureCanvasNameForRun() {
  if (form.value.name.trim()) return
  const prefix = isChatflowMode.value ? 'Chatflow 试运行' : '工作流试运行'
  form.value = {
    ...form.value,
    name: `${prefix} ${formatClock(new Date())}`,
  }
  markCanvasUnsaved()
}

function resetChatflowDebugState() {
  chatflowSessionState.value = null
  chatflowRunEvents.value = []
  chatflowRunDebugDetail.value = null
  chatflowResumeValues.value = {}
  chatflowDebugLoading.value = false
  chatflowRunDebugLoading.value = false
  chatflowResumeSubmitting.value = false
}

async function loadChatflowDebugState(id: number, result: Record<string, any> | null) {
  if (!isChatflowMode.value || !result) return
  const sessionId = String(result.sessionId || '')
  const runId = Number(result.runId || 0)
  if (!sessionId || !runId) return
  chatflowDebugLoading.value = true
  try {
    const [detail, session, events] = await Promise.all([
      getChatflowRunDebug(id, runId) as Promise<ChatflowRunDebugDetail>,
      getChatflowSession(id, sessionId) as Promise<ChatflowSessionState>,
      listChatflowRunEvents(id, runId) as Promise<{ list: any[]; total: number }>,
    ])
    chatflowRunDebugDetail.value = detail
    chatflowSessionState.value = session
    chatflowRunEvents.value = events.list || []
    ensureSelectedDebugNode(detail.nodeDetails || [])
    chatflowResumeValues.value = Object.fromEntries(
      buildChatflowResumeFields((session.waitingEvent?.payload || session.checkpoint?.resumeSchema || {}) as Record<string, any>)
        .map((field) => [field.key, '']),
    )
  } catch (e: any) {
    validationErrors.value = [e?.message || '加载调试状态失败']
  } finally {
    chatflowDebugLoading.value = false
  }
}

function setChatflowResumeField(key: string, value: string) {
  chatflowResumeValues.value = { ...chatflowResumeValues.value, [key]: value }
}

async function submitChatflowResume() {
  if (!isChatflowMode.value || !testResult.value) return
  const id = workflowId.value
  const runId = Number(testResult.value.runId || 0)
  const eventId = Number(chatflowWaitingEvent.value?.id || chatflowCheckpoint.value?.eventId || 0)
  const resumeData = buildResumePayload(chatflowResumeFields.value, chatflowResumeValues.value)
  const runtimeVersion = String(testResult.value.runtimeVersion || '')
  if (!id || !runId || (runtimeVersion !== 'v2' && !eventId)) return
  chatflowResumeSubmitting.value = true
  try {
    const resumed = runtimeVersion === 'v2'
      ? await resumeRuntimeV2Run(runId, {
        resumeData,
        idempotencyKey: runtimeV2IdempotencyKey('CHATFLOW', id),
      }) as Record<string, any>
      : await resumeChatflowRun(id, runId, {
        eventId,
        resumeData,
      }) as Record<string, any>
    testResult.value = resumed
    lastTestRunStatus.value = String(resumed.status || '')
    lastTestRunId.value = Number(resumed.runId || 0)
    lastRunOutput.value = resumed.output || null
    appendChatflowResumeMessages(resumeData, resumed)
    if (runtimeVersion === 'v2') {
      testResult.value = { ...resumed, runtimeVersion: 'v2' }
      await loadRuntimeV2DebugDetail(runId, 'CHATFLOW')
    } else {
      await loadChatflowDebugState(id, resumed)
    }
  } catch (e: any) {
    validationErrors.value = [e?.message || '继续执行失败']
  } finally {
    chatflowResumeSubmitting.value = false
  }
}

function appendChatflowResumeMessages(resumeData: Record<string, any>, result: Record<string, any>) {
  const answer = Object.values(resumeData)
    .map((value) => String(value ?? '').trim())
    .filter(Boolean)
    .join(' ')
  const content = formatChatflowAssistantText(
    result?.output,
    buildChatflowStreamPreview(result?.streamEvents, result?.output),
  )
  const timestamp = Date.now()
  chatflowTrialMessages.value = [
    ...chatflowTrialMessages.value,
    ...(answer ? [{ id: timestamp, role: 'user' as const, content: answer }] : []),
    { id: timestamp + 1, role: 'assistant' as const, content, streaming: false },
  ]
}

async function publishWorkflow() {
  if (!publishGate.value.allowed) {
    message.warning(publishGate.value.reasons[0] || '发布检查未通过')
    return
  }

  const id = await saveCanvas()
  if (!id) return

  publishing.value = true
  try {
    const publish = isChatflowMode.value ? publishChatflowVersion : publishWorkflowVersion
    await publish(id)
    workflowStatus.value = 'PUBLISHED'
    await loadWorkflowVersions()
    message.success(isChatflowMode.value ? 'Chatflow 已发布' : '工作流已发布')
  } catch (e: any) {
    message.error(e?.message || '发布失败')
  } finally {
    publishing.value = false
  }
}

async function loadWorkflowVersions() {
  if (!workflowId.value) {
    workflowVersions.value = []
    return
  }
  workflowVersionsLoading.value = true
  try {
    const listVersions = isChatflowMode.value ? listChatflowVersions : listWorkflowVersions
    const response = await listVersions(workflowId.value)
    workflowVersions.value = response.list || []
  } catch {
    workflowVersions.value = []
  } finally {
    workflowVersionsLoading.value = false
  }
}

async function rollbackVersion(versionId: number) {
  if (!workflowId.value) return
  rollingBackVersionId.value = versionId
  try {
    const rollback = isChatflowMode.value ? rollbackChatflowVersion : rollbackWorkflowVersion
    await rollback(workflowId.value, versionId)
    await loadWorkflowVersions()
    message.success('已回滚到选中版本')
  } catch (e: any) {
    message.error(e?.message || '回滚失败')
  } finally {
    rollingBackVersionId.value = 0
  }
}

async function runPublishedVersion(versionId: number) {
  if (!workflowId.value) return
  targetedPublishedRunLoadingId.value = versionId
  targetedPublishedRunResult.value = null
  try {
    const runner = isChatflowMode.value ? runPublishedChatflow : runPublishedWorkflow
    targetedPublishedRunResult.value = await runner(workflowId.value, publishedVersionRunInput(), versionId) as Record<string, any>
    message.success('已运行发布版本')
  } catch (e: any) {
    message.error(e?.message || '运行发布版本失败')
  } finally {
    targetedPublishedRunLoadingId.value = 0
  }
}

async function runPublishedVersionWithRuntimeV2(versionId: number) {
  if (!workflowId.value) return
  const ownerType = isChatflowMode.value ? 'CHATFLOW' : 'WORKFLOW'
  targetedRuntimeV2RunLoadingId.value = versionId
  targetedRuntimeV2RunResult.value = null
  try {
    const runner = isChatflowMode.value ? runChatflowV2 : runWorkflowV2
    const started = await runner(
      workflowId.value,
      publishedVersionRunInput(),
      runtimeV2IdempotencyKey(ownerType, workflowId.value),
      versionId,
    ) as Record<string, any>
    targetedRuntimeV2RunResult.value = {
      ...started,
      debugRef: started.debugRef || started.eventsRef || started.resultRef || '',
    }
    message.success('已启动实时版本测试')
  } catch (e: any) {
    message.error(e?.message || '实时版本测试失败')
  } finally {
    targetedRuntimeV2RunLoadingId.value = 0
  }
}

function publishedVersionRunInput() {
  if (isChatflowMode.value) {
    return buildChatflowRunInput({
      message: testInput.value.trim() || 'hello',
      ...testProfile.value,
      historyRetentionRounds: chatflowHistoryRetentionRounds.value,
    })
  }
  return {
    userMessage: testInput.value,
    USER_INPUT: testInput.value,
  }
}

function markGraphDirty() {
  markCanvasUnsaved()
  dirtySinceTestRun.value = true
  lastTestRunStatus.value = ''
  lastTestRunId.value = 0
  lastRunOutput.value = null
  lastTestRunGraphSnapshot.value = ''
  workflowRunDebugDetail.value = null
  resetChatflowDebugState()
}

function formatClock(value: Date) {
  return `${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}:${String(value.getSeconds()).padStart(2, '0')}`
}

watch(() => [route.path, route.params.id], loadWorkflow)
watch(() => [route.query.runId, route.query.executeId, route.query.debug, route.query.runtime], () => {
  void applyWorkflowRunDebugRoute()
  void applyChatflowRunDebugRoute()
})
watch(
  () => canvasTab.value,
  requestCanvasLayoutRefit,
)
onMounted(() => {
  refreshCanvasResponsiveLayout()
  window.addEventListener('resize', refreshCanvasResponsiveLayout)
  window.addEventListener('keydown', handleGlobalVariableKeydown)
  document.addEventListener('pointerdown', handleGlobalVariablePointerDown, true)
  document.addEventListener('pointerdown', handleGlobalEdgePointerDown, true)
  document.addEventListener('pointermove', handleGlobalConnectionPointerMove, true)
  document.addEventListener('mousemove', handleGlobalConnectionPointerMove, true)
  void loadLlmProviderModels()
  void loadWorkflow()
})
onUnmounted(() => {
  window.clearTimeout(canvasLayoutRefitTimer)
  window.clearTimeout(canvasLayoutSettledRefitTimer)
  window.removeEventListener('resize', refreshCanvasResponsiveLayout)
  window.removeEventListener('keydown', handleGlobalVariableKeydown)
  document.removeEventListener('pointerdown', handleGlobalVariablePointerDown, true)
  document.removeEventListener('pointerdown', handleGlobalEdgePointerDown, true)
  document.removeEventListener('pointermove', handleGlobalConnectionPointerMove, true)
  document.removeEventListener('mousemove', handleGlobalConnectionPointerMove, true)
})
</script>

<style scoped>
.workflow-canvas-page {
  --workflow-panel-gap: 0.625rem;
  --debug-dock-gap: var(--workflow-panel-gap);
  --debug-dock-min-width: 42rem;
  --debug-dock-min-height: 18rem;
  --debug-dock-height: 21rem;
  --workflow-side-panel-width: 34rem;
  --workflow-side-panel-gap: var(--workflow-panel-gap);
  --workflow-panel-peek-width: 2.5rem;
  --workflow-resource-panel-width: 20rem;
  --workflow-left-rail-min-width: 17.5rem;
  --workflow-stage-min-width: 44rem;
  --workflow-node-test-panel-width: 23.75rem;
  --workflow-node-test-panel-gap: var(--workflow-panel-gap);
  --workflow-right-panel-reserve: calc(var(--workflow-side-panel-width) + var(--workflow-side-panel-gap) + var(--debug-dock-gap));
  --workflow-node-test-reserve: calc(
    var(--workflow-side-panel-width) +
    var(--workflow-side-panel-gap) +
    var(--workflow-node-test-panel-width) +
    var(--workflow-node-test-panel-gap) +
    var(--debug-dock-gap)
  );
  height: 100vh;
  min-height: 45rem;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f6f7fb;
}

.canvas-topbar {
  height: 4.625rem;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.375rem;
  border-bottom: 1px solid #dfe3ee;
  background: #fff;
  box-shadow: 0 1px 0 rgba(34, 41, 63, 0.04);
}

.canvas-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.back-button {
  width: 1.75rem;
  padding: 0;
  color: #445067;
}

.back-button svg,
.resource-panel-toggle svg {
  width: 1rem;
  height: 1rem;
  stroke-width: 1.75;
}

.flow-icon,
.node-type-icon,
.palette-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: inherit;
}

.flow-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.625rem;
  border: 1px solid rgba(14, 165, 169, 0.24);
  background: #e9fbfb;
  color: #0f8b8d;
}

.flow-icon svg,
.node-type-icon svg,
.palette-icon svg {
  width: 1rem;
  height: 1rem;
  stroke-width: 1.875;
}

.flow-icon svg {
  width: 1.25rem;
  height: 1.25rem;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.title-input {
  width: 13.75rem;
}

.title-display-button {
  max-width: 24rem;
  min-height: 1.875rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #22273a;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.3;
  text-align: left;
  cursor: text;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title-display-button.placeholder {
  color: #8b93a7;
}

.title-input :deep(.ant-input) {
  box-shadow: none;
  padding: 0;
  background: transparent;
}

.title-input :deep(.ant-input) {
  height: 1.875rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #22273a;
}

.flow-info {
  width: 1.125rem;
  height: 1.125rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #9aa3b5;
  border-radius: 50%;
  font-size: 0.75rem;
  color: #596273;
}

.save-state {
  width: fit-content;
  margin-top: 0.125rem;
  padding: 0.125rem 0.5rem;
  border-radius: 0.3125rem;
  background: #eef0f8;
  font-size: 0.75rem;
  color: #616a7f;
}

.canvas-mode-tabs {
  height: 2.375rem;
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(4.625rem, 1fr));
  align-items: center;
  padding: 0.1875rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.5625rem;
  background: #f6f7fb;
}

.canvas-mode-tabs button {
  height: 1.875rem;
  border: 0;
  border-radius: 0.4375rem;
  background: transparent;
  color: #6a7284;
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
}

.canvas-mode-tabs button.active {
  background: #fff;
  color: #3339d8;
  box-shadow: 0 0.125rem 0.5rem rgba(44, 51, 84, 0.08);
}

.canvas-actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.workflow-canvas-page.canvas-layout-stage-shelved .canvas-mode-tabs,
.workflow-canvas-page.canvas-layout-stage-shelved .canvas-actions,
.workflow-canvas-page.canvas-layout-left-rail .canvas-mode-tabs,
.workflow-canvas-page.canvas-layout-left-rail .canvas-actions {
  display: none;
}

.canvas-workbench {
  position: relative;
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: var(--workflow-resource-panel-width) minmax(0, 1fr);
  overflow: hidden;
  background: #f8f9fc;
  transition: grid-template-columns 0.18s ease;
}

.canvas-workbench.resource-collapsed {
  grid-template-columns: 0 minmax(0, 1fr);
}

.canvas-open-surface {
  grid-column: 2;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  overflow: auto;
  background: #f8f9fc;
}

.open-surface-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #dde3ef;
  border-radius: 0.5rem;
  background: #fff;
}

.open-surface-header strong,
.open-surface-header span {
  display: block;
}

.open-surface-header strong {
  color: #242b3d;
  font-size: 1rem;
}

.open-surface-header span {
  margin-top: 0.25rem;
  color: #717b91;
  font-size: 0.8125rem;
}

.open-surface-header code {
  max-width: 34rem;
  padding: 0.375rem 0.5rem;
  border-radius: 0.375rem;
  background: #f3f5fb;
  color: #4c52df;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
  overflow-wrap: anywhere;
}

.open-surface-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
}

.open-surface-section,
.publish-dialog-section {
  padding: 1rem;
  border: 1px solid #dde3ef;
  border-radius: 0.5rem;
  background: #fff;
}

.resource-panel-toggle {
  position: absolute;
  top: 1rem;
  left: var(--workflow-resource-panel-width);
  z-index: 12;
  width: 1.875rem;
  height: 1.875rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dfe3ee;
  border-radius: 0.5rem;
  background: #f7f8fc;
  color: #596273;
  box-shadow: 0 0.375rem 1rem rgba(34, 41, 63, 0.08);
  cursor: pointer;
  opacity: 0.82;
  transition: opacity 0.16s ease, left 0.18s ease, background 0.16s ease;
}

.resource-panel-toggle:hover,
.resource-panel-toggle:focus-visible {
  background: #fff;
  opacity: 1;
}

.canvas-workbench.resource-collapsed .resource-panel-toggle {
  left: 0;
}

.canvas-resource-panel {
  min-height: 0;
  padding: 1rem 0.75rem;
  border-right: 1px solid #dfe3ee;
  overflow-y: auto;
  background: #fff;
}

.resource-header {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0 0.25rem 0.75rem;
  border-bottom: 1px solid #edf0f6;
}

.resource-header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.resource-header-main > strong {
  min-width: 0;
}

.resource-header strong {
  color: #252b3d;
  font-size: 0.9375rem;
}

.resource-header-actions {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.375rem;
}

.resource-header-icon-button {
  width: 1.875rem;
  height: 1.875rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e1e5ef;
  border-radius: 0.5rem;
  background: #f7f8fc;
  color: #5f687a;
  cursor: pointer;
}

.resource-header-icon-button svg {
  width: 0.875rem;
  height: 0.875rem;
  stroke-width: 1.9;
}

.chatflow-history-settings-popover {
  position: absolute;
  top: 2.25rem;
  left: 0.25rem;
  right: 0.25rem;
  z-index: 16;
  padding: 0.875rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 0.875rem 2.25rem rgba(34, 41, 63, 0.14);
}

.chatflow-history-settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.chatflow-history-settings-header button {
  width: 1.625rem;
  height: 1.625rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e1e5ef;
  border-radius: 0.4375rem;
  background: #f7f8fc;
  color: #6f7789;
  cursor: pointer;
}

.chatflow-history-settings-header svg {
  width: 0.8125rem;
  height: 0.8125rem;
}

.chatflow-history-setting-field {
  display: grid;
  gap: 0.5rem;
  color: #30364a;
  font-size: 0.8125rem;
  font-weight: 800;
}

.chatflow-history-slider-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 3.75rem;
  gap: 0.5rem;
  align-items: center;
}

.chatflow-history-slider {
  min-width: 0;
}

.chatflow-history-number-input {
  width: 3.75rem;
  height: 2rem;
  padding: 0 0.375rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.5rem;
  color: #30364a;
  font-size: 0.8125rem;
  font-weight: 800;
}

.chatflow-history-settings-popover p {
  margin: 0.625rem 0 0;
  color: #8b94a8;
  font-size: 0.75rem;
  line-height: 1.45;
}

.resource-header span {
  color: #8b94a8;
  font-size: 0.75rem;
}

.resource-section {
  padding: 0.875rem 0.25rem 0;
}

.resource-section h4 {
  margin: 0 0 0.5rem;
  color: #70798d;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.resource-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.resource-section-heading h4 {
  margin: 0;
}

.resource-section-heading small {
  color: #9aa3b6;
  font-size: 0.6875rem;
  font-weight: 700;
  text-align: right;
}

.chatflow-variable-scope {
  margin-top: 0.625rem;
  border-top: 0.0625rem solid #edf0f6;
  padding-top: 0.625rem;
}

.chatflow-variable-scope-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chatflow-variable-scope-toggle {
  flex: 1;
  min-width: 0;
  margin-bottom: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.chatflow-variable-scope-toggle svg {
  width: 0.875rem;
  height: 0.875rem;
  color: #6f778a;
}

.chatflow-variable-scope-toggle strong {
  font-size: 0.9375rem;
}

.chatflow-variable-scope-toggle em {
  margin-left: 0.25rem;
  padding: 0.0625rem 0.375rem;
  border-radius: 999rem;
  background: #f0f2ff;
  color: #5f61ff;
  font-size: 0.6875rem;
  font-style: normal;
  font-weight: 900;
}

.chatflow-variable-add-button {
  flex: 0 0 auto;
  margin-left: auto;
}

.chatflow-variable-scope-description {
  margin: 0.5rem 0 0;
  color: #70798d;
  font-size: 0.75rem;
  line-height: 1.5;
}

.question-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1.75rem;
  gap: 0.375rem;
  margin-bottom: 0.375rem;
}

.question-row input {
  min-width: 0;
  height: 1.875rem;
  padding: 0 0.5rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.4375rem;
  outline: none;
  color: #30364a;
}

.question-row button,
.resource-action {
  border: 1px solid #dfe3ee;
  border-radius: 0.4375rem;
  background: #f7f8fc;
  color: #5f687a;
  cursor: pointer;
}

.resource-action {
  width: 100%;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  font-weight: 700;
}

.question-row button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.question-row button svg,
.resource-action svg {
  width: 0.875rem;
  height: 0.875rem;
  stroke-width: 1.9;
}

.resource-group {
  margin-bottom: 0.5rem;
}

.resource-group > button,
.resource-variable-row {
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5625rem 0.625rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.5rem;
  background: #fff;
  color: #30364a;
  cursor: pointer;
}

.resource-group > button {
  position: relative;
  flex-direction: column;
  padding-right: 2.375rem;
}

.resource-group-title {
  width: 100%;
  display: inline-flex;
  align-items: center;
  gap: 0.3125rem;
}

.resource-group-title svg {
  width: 0.8125rem;
  height: 0.8125rem;
  color: #7e879c;
  stroke-width: 2;
}

.resource-group-title strong {
  color: #30364a;
  font-size: 0.8125rem;
}

.resource-group small,
.resource-variable-row code,
.resource-variable-row em {
  color: #8b94a8;
  font-size: 0.6875rem;
}

.resource-group > button[aria-expanded='true'] {
  border-color: #d8def4;
  background: #f7f8ff;
}

.resource-group-count {
  position: absolute;
  top: 0.5625rem;
  right: 0.625rem;
  min-width: 1.25rem;
  height: 1.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.3125rem;
  border-radius: 999rem;
  background: #f0f2ff;
  color: #5f61ff;
  font-size: 0.6875rem;
  font-style: normal;
  font-weight: 900;
}

.resource-items {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-top: 0.375rem;
}

.resource-variable-row {
  flex-direction: column;
  cursor: default;
}

.chatflow-variable-table {
  padding: 0.5rem;
  border: 1px solid #e2e6f2;
  border-radius: 0.625rem;
  background: #fff;
  overflow-x: auto;
}

.chatflow-variable-table-head,
.chatflow-variable-table .resource-variable-row {
  min-width: 18rem;
  display: grid;
  grid-template-columns: minmax(5.25rem, 1fr) minmax(5.25rem, 1fr) 5.25rem;
  gap: 0.375rem;
  align-items: center;
}

.chatflow-variable-table-head {
  padding: 0 0.25rem 0.375rem;
  color: #8a94aa;
  font-size: 0.6875rem;
  font-weight: 800;
}

.chatflow-variable-table .resource-variable-row {
  min-height: 2rem;
  padding: 0.25rem;
  border: 0;
  border-radius: 0.375rem;
  background: transparent;
}

.chatflow-variable-table .resource-variable-row:hover {
  background: #f6f7fb;
}

.resource-variable-row span {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.125rem;
}

.resource-variable-row strong {
  color: #30364a;
  font-size: 0.75rem;
}

.chatflow-variable-key {
  min-width: 0;
  box-sizing: border-box;
  width: 100%;
  height: 1.875rem;
  display: inline-flex;
  align-items: center;
  padding: 0 0.5rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.4375rem;
  background: #fff;
  color: #30364a;
  font-size: 0.75rem;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  outline: none;
}

.chatflow-variable-name {
  min-width: 0;
  box-sizing: border-box;
  width: 100%;
  height: 1.875rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem;
  padding: 0 0.5rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.4375rem;
  background: #fff;
}

.chatflow-variable-label-input {
  display: block;
  color: #30364a;
  font-size: 0.75rem;
  font-weight: 700;
  outline: none;
}

.chatflow-variable-name strong {
  overflow: hidden;
  color: #30364a;
  font-size: 0.75rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chatflow-variable-name code {
  display: none;
}

.chatflow-variable-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
  flex-wrap: nowrap;
}

.chatflow-variable-table .resource-variable-row .chatflow-variable-key {
  display: inline-flex;
}

.chatflow-variable-table .resource-variable-row .chatflow-variable-name {
  display: flex;
}

.chatflow-variable-table .resource-variable-row .chatflow-variable-actions {
  display: inline-flex;
  grid-template-columns: none;
}

.chatflow-variable-actions button,
.chatflow-user-variable-card button {
  width: 1.5rem;
  height: 1.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e1e5ef;
  border-radius: 0.4375rem;
  background: #f7f8fc;
  color: #8b94a8;
}

.chatflow-variable-actions button:disabled,
.chatflow-user-variable-card button:disabled {
  cursor: not-allowed;
  opacity: 0.64;
}

.chatflow-variable-actions svg,
.chatflow-user-variable-card svg {
  width: 0.8125rem;
  height: 0.8125rem;
  stroke-width: 1.9;
}

.chatflow-variable-switch {
  width: 1.75rem;
  height: 1rem;
  border-radius: 999rem;
  background: #3f6cff;
  position: relative;
  box-shadow: inset 0 0 0 0.0625rem rgba(63, 108, 255, 0.16);
}

.chatflow-variable-switch::after {
  content: '';
  position: absolute;
  top: 0.125rem;
  right: 0.125rem;
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 999rem;
  background: #fff;
}

.chatflow-user-variable-card {
  margin-top: 0.625rem;
  padding: 0.625rem;
  border: 1px solid #e2e6f2;
  border-radius: 0.625rem;
  background: #fbfcff;
}

.chatflow-user-variable-card div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
}

.chatflow-user-variable-card strong {
  color: #30364a;
  font-size: 0.8125rem;
}

.chatflow-user-variable-card p {
  margin: 0;
  color: #70798d;
  font-size: 0.75rem;
  line-height: 1.5;
}

.resource-variable-row code {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-variable-row em {
  align-self: flex-start;
  padding: 0.125rem 0.375rem;
  border-radius: 0.375rem;
  background: #f0f2f7;
  font-style: normal;
  font-weight: 700;
}

.resource-group > button:hover {
  border-color: #cdd3f7;
  background: #f5f6ff;
}

.resource-stats {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.5rem;
  margin: 0;
}

.resource-stats div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 2.125rem;
  padding: 0 0.625rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.5rem;
  background: #f8f9fc;
}

.resource-stats dt {
  color: #70798d;
  font-size: 0.75rem;
  font-weight: 700;
}

.resource-stats dd {
  margin: 0;
  color: #30364a;
  font-size: 0.8125rem;
  font-weight: 800;
}

.selected-node-summary {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.625rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.5rem;
  background: #fff;
}

.selected-node-summary strong {
  color: #30364a;
  font-size: 0.8125rem;
}

.selected-node-summary span {
  color: #8b94a8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
}

.canvas-stage-shell {
  grid-column: 2;
  position: relative;
  width: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.canvas-stage-shell:focus {
  outline: none;
}

.workflow-canvas-page.has-right-panel .canvas-stage-shell {
  width: 100%;
}

.workflow-canvas-page.has-node-test-drawer .canvas-stage-shell {
  width: 100%;
}

.workflow-canvas-page.canvas-layout-stage-shelved .canvas-workbench {
  grid-template-columns: var(--workflow-resource-panel-width) var(--workflow-stage-min-width);
}

.workflow-canvas-page.canvas-layout-stage-shelved .canvas-stage-shell {
  width: var(--workflow-stage-min-width);
  min-width: var(--workflow-stage-min-width);
  overflow: hidden;
}

.workflow-canvas-page.canvas-layout-left-rail .canvas-workbench {
  grid-template-columns: minmax(var(--workflow-left-rail-min-width), var(--workflow-resource-panel-width)) var(--workflow-stage-min-width);
}

.workflow-canvas-page.canvas-layout-left-rail .canvas-resource-panel {
  min-width: var(--workflow-left-rail-min-width);
}

.workflow-canvas-page.canvas-layout-left-rail .canvas-stage-shell {
  width: var(--workflow-stage-min-width);
  min-width: var(--workflow-stage-min-width);
  overflow: hidden;
}

.coze-flow {
  width: 100%;
  height: 100%;
  background-color: #f8f9fc;
  background-image: radial-gradient(#bac0ce 0.075rem, transparent 0.075rem);
  background-size: 1.5rem 1.5rem;
  transition: width 0.18s ease;
}

.coze-flow :deep(.vue-flow__node) {
  width: auto;
  overflow: visible;
  visibility: visible !important;
  pointer-events: all;
}

.coze-flow :deep(.vue-flow__edges) {
  z-index: 1;
}

.coze-flow :deep(.vue-flow__nodes) {
  z-index: 2;
}

.coze-flow :deep(.vue-flow__node:hover),
.coze-flow :deep(.vue-flow__node:focus-within) {
  z-index: 120 !important;
}

.coze-flow :deep(.vue-flow__edge-path) {
  stroke: #5a5cf6;
  stroke-width: 2;
  cursor: pointer;
  transition:
    stroke 0.16s ease,
    stroke-width 0.16s ease,
    filter 0.16s ease;
}

.coze-flow :deep(.vue-flow__edge-interaction) {
  cursor: pointer;
}

.canvas-stage-shell:has(.node-variable-shell:hover) .coze-flow :deep(.vue-flow__pane),
.canvas-stage-shell:has(.node-variable-shell:focus-within) .coze-flow :deep(.vue-flow__pane) {
  pointer-events: none;
}

.coze-flow :deep(.coze-edge-path.edge-hovered) {
  stroke: #34c7f3;
  filter: drop-shadow(0 0.1875rem 0.375rem rgba(52, 199, 243, 0.2));
}

.coze-flow :deep(.coze-edge-path.edge-succeeded) {
  stroke: #7c8cff;
}

.coze-flow :deep(.coze-edge-path.edge-active-branch) {
  stroke: #22c55e;
  filter: drop-shadow(0 0.1875rem 0.375rem rgba(34, 197, 94, 0.18));
}

.coze-flow :deep(.coze-edge-path.edge-inactive-branch) {
  opacity: 0.38;
}

.coze-flow :deep(.coze-edge-path.edge-running) {
  stroke: #34c7f3;
  stroke-dasharray: 0.75rem 0.45rem;
  animation: coze-edge-running-dash 0.85s linear infinite;
  filter: drop-shadow(0 0.1875rem 0.5rem rgba(52, 199, 243, 0.28));
}

.coze-flow :deep(.coze-edge-path.edge-selected) {
  stroke: #24bde8;
  stroke-width: 3;
  filter: drop-shadow(0 0.25rem 0.5rem rgba(36, 189, 232, 0.24));
}

@keyframes coze-edge-running-dash {
  to {
    stroke-dashoffset: -1.2rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .coze-flow :deep(.coze-edge-path.edge-running) {
    animation: none;
  }
}

.edge-insert-button {
  position: absolute;
  z-index: 130;
  width: 2.5rem;
  height: 2.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.1875rem solid #fff;
  border-radius: 62.4375rem;
  background: #34c7f3;
  color: #fff;
  box-shadow: 0 0.375rem 0.875rem rgba(35, 183, 226, 0.28);
  cursor: pointer;
  pointer-events: all;
}

.edge-insert-button svg {
  font-size: 1.25rem;
}

.edge-insert-palette {
  position: absolute;
  z-index: 150;
  width: min(16rem, calc(100vw - 2rem));
  max-height: min(22rem, calc(100vh - 4rem));
  padding: 0.5rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.625rem;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 0.875rem 2rem rgba(34, 41, 63, 0.18);
  overflow-y: auto;
  pointer-events: all;
}

.edge-insert-palette :deep(.ant-input) {
  min-height: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: #fbfcff;
}

.edge-insert-palette :deep(.ant-input) {
  font-size: 0.8125rem;
}

.edge-insert-palette-group {
  margin-top: 0.5rem;
}

.edge-insert-palette-group > strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #8b93a7;
  font-size: 0.75rem;
}

.edge-insert-palette-group > div {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.125rem 0.25rem;
}

.edge-insert-palette button {
  min-width: 0;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0 0.375rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #2f3648;
  font-size: 0.8125rem;
  font-weight: 650;
  text-align: left;
  cursor: pointer;
}

.edge-insert-palette button:hover {
  background: #f0f2fa;
}

.coze-node {
  position: relative;
  width: 26.25rem;
  min-height: 6.5rem;
  padding: 1.125rem;
  border: 1px solid #d9deec;
  border-radius: 0.625rem;
  background: linear-gradient(180deg, #fff, #fbfcff);
  box-shadow: 0 0.625rem 1.75rem rgba(36, 45, 67, 0.08);
  color: #30364a;
  cursor: grab;
  user-select: none;
  overflow: visible;
}

.coze-node.node-start {
  height: 7.5rem;
  overflow: visible;
}

.coze-node.node-condition {
  width: 27.5rem;
  min-height: 12rem;
  background: linear-gradient(180deg, #f4fbfb, #fff);
}

.coze-node.node-condition .node-header {
  margin-bottom: 0.875rem;
}

.coze-node:active {
  cursor: grabbing;
}

.coze-node.selected {
  border-color: #6667f6;
  box-shadow:
    inset 0 0 0 0.0625rem rgba(102, 103, 246, 0.42),
    0 0 0 0.125rem rgba(102, 103, 246, 0.18),
    0 0.625rem 1.75rem rgba(36, 45, 67, 0.08);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.125rem;
  position: relative;
}

.node-type-icon {
  width: 2rem;
  height: 2rem;
  flex: 0 0 auto;
  border: 1px solid rgba(85, 88, 232, 0.18);
  border-radius: 0.5rem;
  background: #eef0ff;
  color: #5558e8;
}

.icon-start,
.icon-end,
.icon-llm {
  border-color: rgba(85, 88, 232, 0.18);
  background: #eef0ff;
  color: #5558e8;
}

.icon-condition {
  border-color: rgba(245, 158, 11, 0.22);
  background: #fff7e8;
  color: #d97706;
}

.icon-knowledge {
  border-color: rgba(233, 80, 133, 0.2);
  background: #fff0f6;
  color: #d6336c;
}

.icon-api_call {
  border-color: rgba(18, 181, 176, 0.2);
  background: #e9fbfb;
  color: #0f8b8d;
}

.icon-tool_call {
  border-color: rgba(147, 51, 234, 0.18);
  background: #f5edff;
  color: #9333ea;
}

.icon-execute_workflow {
  border-color: rgba(34, 197, 94, 0.2);
  background: #ecfdf5;
  color: #16a34a;
}

.icon-agent_call {
  border-color: rgba(14, 165, 233, 0.2);
  background: #eef8ff;
  color: #0284c7;
}

.icon-code {
  border-color: rgba(71, 85, 105, 0.18);
  background: #f1f5f9;
  color: #475569;
}

.icon-text_process {
  border-color: rgba(15, 139, 141, 0.2);
  background: #e9fbfb;
  color: #0f8b8d;
}

.icon-json_parse {
  border-color: rgba(124, 58, 237, 0.18);
  background: #f3edff;
  color: #7c3aed;
}

.icon-variable_aggregation {
  border-color: rgba(245, 158, 11, 0.22);
  background: #fff7e8;
  color: #d97706;
}

.icon-variable_assign {
  border-color: rgba(37, 99, 235, 0.18);
  background: #eef5ff;
  color: #2563eb;
}

.icon-intent_recognition {
  border-color: rgba(139, 92, 246, 0.18);
  background: #f3edff;
  color: #7c3aed;
}

.icon-message {
  border-color: rgba(6, 182, 212, 0.2);
  background: #ecfeff;
  color: #0891b2;
}

.icon-question {
  border-color: rgba(16, 185, 129, 0.2);
  background: #ecfdf5;
  color: #059669;
}

.icon-human_input {
  border-color: rgba(100, 116, 139, 0.18);
  background: #f1f5f9;
  color: #64748b;
}

.icon-information_collection {
  border-color: rgba(22, 163, 74, 0.2);
  background: #ecfdf5;
  color: #16a34a;
}

.icon-transfer_to_human {
  border-color: rgba(249, 115, 22, 0.22);
  background: #fff7ed;
  color: #ea580c;
}

.node-title-run {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.node-title {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 2rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-card-actions {
  flex: 0 0 auto;
  position: relative;
  z-index: 16;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease;
}

.coze-node:hover .node-card-actions,
.coze-node.selected .node-card-actions,
.node-card-actions.menu-open {
  opacity: 1;
  pointer-events: auto;
}

.node-card-actions button {
  width: 1.75rem;
  height: 1.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 0.375rem;
  background: transparent;
  color: #252b3d;
  cursor: pointer;
}

.node-card-actions button:hover,
.node-card-actions button:focus,
.node-card-actions button:active,
.node-card-actions button[aria-expanded='true'] {
  border: 0;
  outline: none;
  background: transparent;
  box-shadow: none;
  color: #252b3d;
}

.node-card-actions button:disabled {
  color: #c1c7d4;
  cursor: not-allowed;
}

.node-card-actions svg {
  width: 1rem;
  height: 1rem;
  stroke-width: 2;
}

.node-card-menu-wrap {
  position: relative;
}

.node-card-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  z-index: 80;
  min-width: 9rem;
  padding: 0.5rem;
  border: 0.0625rem solid #e4e8f4;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 1rem 2.5rem rgba(37, 43, 61, 0.14);
}

.node-card-menu button {
  width: 100%;
  height: 2.25rem;
  justify-content: flex-start;
  gap: 0.5rem;
  padding: 0 0.75rem;
  border-radius: 0.5rem;
  color: #252b3d;
  font-size: 0.875rem;
  text-align: left;
  white-space: nowrap;
}

.node-card-menu button:hover:not(:disabled) {
  background: #f3f5fb;
  color: #5558e8;
}

.node-card-menu button svg {
  width: 0.875rem;
  height: 0.875rem;
}

.node-run-status {
  flex: 0 0 auto;
  max-width: 7.7rem;
  height: 1.4rem;
  display: inline-flex;
  align-items: center;
  gap: 0.2625rem;
  padding: 0 0.4375rem;
  border-radius: 999rem;
  background: #eef1f7;
  color: #667085;
  font-size: 0.6125rem;
  font-weight: 800;
  line-height: 1.4rem;
  white-space: nowrap;
}

.node-run-status-icon {
  width: 0.7rem;
  height: 0.7rem;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rem;
  background: currentColor;
  color: inherit;
}

.node-run-status.status-succeeded .node-run-status-icon::before,
.node-run-status.status-completed .node-run-status-icon::before {
  color: #fff;
  font-size: 0.525rem;
  font-weight: 900;
  line-height: 1;
  content: "✓";
}

.node-run-status.status-failed .node-run-status-icon::before {
  color: #fff;
  font-size: 0.525rem;
  font-weight: 900;
  line-height: 1;
  content: "!";
}

.node-run-status.status-interrupted .node-run-status-icon::before,
.node-run-status.status-waiting .node-run-status-icon::before {
  width: 0.2625rem;
  height: 0.2625rem;
  border-radius: 999rem;
  background: #fff;
  content: "";
}

.node-run-status.status-running .node-run-status-icon {
  background: transparent;
  border: 0.0875rem solid currentColor;
  border-top-color: transparent;
  animation: node-run-spin 0.8s linear infinite;
}

.node-run-status small {
  color: inherit;
  font-size: 0.525rem;
  font-weight: 800;
}

.node-run-status.status-succeeded,
.node-run-status.status-completed {
  background: #dcf8e8;
  color: #159947;
}

.node-run-status.status-failed {
  background: #ffe7e7;
  color: #d93042;
}

.node-run-status.status-interrupted,
.node-run-status.status-waiting {
  background: #fff3d7;
  color: #b56b00;
}

.node-run-status.status-running {
  background: #e7edff;
  color: #4f5cf5;
}

.coze-node.run-succeeded {
  border-color: #bbefcd;
  box-shadow: 0 0.5rem 1.5rem rgba(36, 45, 67, 0.07), 0 0 0 0.0625rem rgba(21, 153, 71, 0.16);
}

.coze-node.run-running {
  border-color: #b9c3ff;
  box-shadow: 0 0.5rem 1.5rem rgba(36, 45, 67, 0.07), 0 0 0 0.125rem rgba(79, 92, 245, 0.16);
}

.coze-node.run-failed {
  border-color: #ffc3c8;
  box-shadow: 0 0.5rem 1.5rem rgba(36, 45, 67, 0.07), 0 0 0 0.0625rem rgba(217, 48, 66, 0.16);
}

@keyframes node-run-spin {
  to {
    transform: rotate(360deg);
  }
}

.node-line {
  display: flex;
  align-items: center;
  min-width: 0;
  min-height: 1.875rem;
  gap: 0.5rem;
  overflow: hidden;
  color: #9aa2b4;
  font-size: 0.9375rem;
  font-weight: 600;
}

.node-line.start-input-line {
  overflow: visible;
}

.node-variable-shell {
  position: relative;
  flex: 1;
  min-width: 0;
}

.node-variable-list {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
  white-space: nowrap;
}

.node-variable-list:focus {
  outline: none;
}

.node-line em,
.node-variable-badge {
  max-width: 10.625rem;
  overflow: hidden;
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  background: #eef1f7;
  color: #3e4558;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-variable-badge span,
.node-variable-popover-badge span {
  color: #a9afbd;
}

.node-variable-badge {
  flex: 0 1 auto;
}

.node-variable-more {
  flex: 0 0 auto;
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  background: #eef1f7;
  color: #3e4558;
  font-size: 0.9375rem;
  font-weight: 700;
  line-height: 1.4;
}

.node-variable-popover {
  position: absolute;
  top: -2.5rem;
  left: -0.625rem;
  z-index: 160;
  width: max-content;
  max-width: min(26rem, calc(100vw - 3rem));
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem 0.75rem;
  visibility: hidden;
  opacity: 0;
  padding: 0.75rem;
  border: 1px solid #e0e4ef;
  border-radius: 0.625rem;
  background: #fff;
  box-shadow: 0 0.875rem 2.125rem rgba(35, 43, 60, 0.16);
  pointer-events: auto;
  transition: opacity 0.12s ease, visibility 0.12s ease;
}

.node-variable-popover::before {
  position: absolute;
  top: -0.625rem;
  left: 0;
  width: 100%;
  height: 0.625rem;
  content: "";
}

.node-variable-shell:hover .node-variable-popover,
.node-variable-shell:focus-within .node-variable-popover {
  visibility: visible;
  opacity: 1;
}

.node-variable-popover .node-variable-popover-badge {
  max-width: none;
  overflow: visible;
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  background: #eef1f7;
  color: #3e4558;
  font-style: normal;
  text-overflow: clip;
  white-space: nowrap;
}

.node-line em.orange {
  background: #fff0e4;
  color: #f57b16;
}

.node-variable-more.orange,
.node-variable-popover .node-variable-popover-badge.orange {
  background: #fff0e4;
  color: #f57b16;
}

.node-line strong {
  color: #b4bac8;
  font-weight: 500;
}

.condition-node-branches {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-right: 1.125rem;
}

.condition-node-branch {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  align-items: center;
  gap: 0.625rem;
  min-height: 2.625rem;
}

.condition-node-branch-kind {
  color: #a2aabd;
  font-size: 0.9375rem;
  font-weight: 800;
  text-align: right;
}

.condition-node-branch strong {
  min-width: 0;
  overflow: hidden;
  padding: 0.5625rem 0.75rem;
  border: 1px solid #d8deeb;
  border-radius: 0.375rem;
  background: #fff;
  color: #30364a;
  font-size: 0.875rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-port {
  --node-port-scale: 1;
  --node-port-bg: #6b6ff7;
  --node-port-shadow: none;
  --node-port-dot-size: 1rem;
  --node-port-hit-size: 3rem;
  width: var(--node-port-dot-size);
  height: var(--node-port-dot-size);
  border: 0;
  background: transparent;
  transform-origin: center;
  transition:
    box-shadow 0.14s ease,
    background 0.14s ease;
}

.node-port::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: var(--node-port-hit-size);
  height: var(--node-port-hit-size);
  border-radius: 999rem;
  transform: translate(-50%, -50%);
}

.node-port::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: var(--node-port-dot-size);
  height: var(--node-port-dot-size);
  border: 0.125rem solid #fff;
  border-radius: 999rem;
  background: var(--node-port-bg);
  box-shadow: var(--node-port-shadow);
  pointer-events: none;
  transform: translate(-50%, -50%) scale(var(--node-port-scale));
  transform-origin: center;
  transition:
    transform 0.14s ease,
    box-shadow 0.14s ease,
    background 0.14s ease;
}

.source-port {
  right: calc(var(--node-port-dot-size) / -2);
  transform: translateY(-50%);
}

.target-port {
  left: calc(var(--node-port-dot-size) / -2);
  transform: translateY(-50%);
}

.condition-source-port {
  z-index: 5;
}

.coze-node:hover .node-port {
  --node-port-scale: 1;
  --node-port-shadow: 0 0 0 0.25rem rgba(107, 111, 247, 0.12);
}

.coze-node.selected .node-port {
  --node-port-scale: 1;
  --node-port-shadow: 0 0 0 0.25rem rgba(107, 111, 247, 0.12);
}

.coze-node .node-port:hover,
.coze-node .node-port.connecting,
.coze-node .node-port.valid,
.coze-node .node-port.connection-preview,
.coze-node .node-port.vue-flow__handle-connecting,
.coze-node .node-port.vue-flow__handle-valid {
  --node-port-scale: 1.2;
  --node-port-bg: #5558f6;
  --node-port-shadow: 0 0 0 0.3125rem rgba(85, 88, 246, 0.16);
  z-index: 4;
}

.node-palette {
  position: absolute;
  left: 50%;
  bottom: 4.5rem;
  z-index: 10;
  width: min(16rem, calc(100vw - 2rem));
  max-height: min(22rem, calc(100vh - 8rem));
  padding: 0.5rem;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.625rem;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 0.875rem 2rem rgba(34, 41, 63, 0.18);
  overflow-y: auto;
  transform: translateX(-50%);
}

.node-palette :deep(.ant-input) {
  min-height: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: #fbfcff;
}

.node-palette :deep(.ant-input) {
  font-size: 0.8125rem;
}

.workflow-debug-dock {
  position: fixed;
  left: var(--debug-dock-gap);
  right: var(--debug-dock-gap);
  bottom: var(--debug-dock-gap);
  z-index: 35;
  width: auto;
  min-width: var(--debug-dock-min-width);
  height: var(--debug-dock-height);
  min-height: var(--debug-dock-min-height);
  display: flex;
  flex-direction: column;
  border: 1px solid #dfe3ee;
  border-radius: 0.625rem;
  background: #fff;
  box-shadow: 0 0.625rem 1.75rem rgba(34, 41, 63, 0.14);
  overflow: hidden;
}

.workflow-canvas-page.has-right-panel .workflow-debug-dock {
  right: var(--workflow-right-panel-reserve);
}

.workflow-canvas-page.has-node-test-drawer.has-right-panel .workflow-debug-dock {
  right: var(--workflow-node-test-reserve);
}

.workflow-canvas-page.has-node-test-drawer:not(.has-right-panel) .workflow-debug-dock {
  right: calc(var(--workflow-node-test-panel-width) + var(--workflow-node-test-panel-gap) + var(--debug-dock-gap));
}

.workflow-canvas-page.canvas-layout-right-shelved.has-right-panel .workflow-debug-dock {
  right: calc(var(--workflow-panel-peek-width) + var(--debug-dock-gap));
}

.workflow-canvas-page.canvas-layout-right-shelved.has-node-test-drawer.has-right-panel .workflow-debug-dock {
  right: calc(
    var(--workflow-panel-peek-width) +
    var(--workflow-panel-peek-width) +
    var(--workflow-node-test-panel-gap) +
    var(--debug-dock-gap)
  );
}

.workflow-canvas-page.canvas-layout-right-shelved.has-node-test-drawer:not(.has-right-panel) .workflow-debug-dock {
  right: calc(var(--workflow-panel-peek-width) + var(--debug-dock-gap));
}

.workflow-canvas-page.canvas-layout-stage-shelved .workflow-debug-dock,
.workflow-canvas-page.canvas-layout-left-rail .workflow-debug-dock {
  right: auto;
  width: var(--debug-dock-min-width);
}

.debug-dock-header {
  min-height: 3.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0 1.25rem;
  border-bottom: 1px solid #edf0f6;
  background: #fbfcff;
}

.debug-dock-title {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
}

.debug-dock-title strong {
  color: #202538;
  font-size: 1rem;
  line-height: 1.4;
}

.debug-dock-title span {
  color: #7c8498;
  font-size: 0.75rem;
  font-weight: 800;
}

.debug-dock-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.debug-dock-actions button {
  width: 1.875rem;
  height: 1.875rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(226, 232, 240, 0.96);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.96);
  color: #475569;
  cursor: pointer;
  transition:
    background-color 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;
}

.debug-dock-actions button:hover {
  border-color: #bfdbfe;
  background: #f8fbff;
  color: #0f172a;
}

.debug-dock-actions .debug-observe-link {
  width: auto;
  padding: 0 0.625rem;
  color: #5558e8;
  font-weight: 800;
}

.debug-dock-actions .debug-cancel-run-button {
  width: auto;
  gap: 0.375rem;
  padding: 0 0.625rem;
  color: #b42318;
  font-weight: 800;
}

.debug-dock-actions .debug-cancel-run-button:hover:not(:disabled) {
  border-color: #fecaca;
  background: #fff5f5;
  color: #981b1b;
}

.debug-dock-actions .debug-cancel-run-button:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.debug-close-button {
  font-size: 1.125rem;
  line-height: 1;
}

.debug-dock-tabs {
  display: flex;
  gap: 0.375rem;
  padding: 0.625rem 1.25rem;
  border-bottom: 1px solid #edf0f6;
}

.debug-dock-tabs button {
  height: 1.75rem;
  padding: 0 0.75rem;
  border: 0;
  border-radius: 0.4375rem;
  background: transparent;
  color: #6f778a;
  font-weight: 800;
}

.debug-dock-tabs button.active {
  background: #eef0ff;
  color: #5558e8;
}

.debug-dock-body {
  flex: 1;
  min-height: 0;
  padding: 0.875rem 1rem 1rem;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  color: #30364a;
  font-size: 0.8125rem;
}

.debug-dock-body.split {
  display: grid;
  grid-template-columns: 11.25rem minmax(0, 1fr);
  gap: 0.75rem;
}

.debug-error-panel {
  background: #fbfcff;
}

.debug-error-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.debug-error-summary strong {
  color: #202538;
  font-size: 0.9375rem;
}

.debug-error-summary span {
  display: inline-flex;
  align-items: center;
  height: 1.5rem;
  padding: 0 0.5rem;
  border-radius: 62.4375rem;
  background: #eef0ff;
  color: #5558e8;
  font-size: 0.75rem;
  font-weight: 900;
}

.debug-error-list-card,
.debug-error-empty-card {
  border: 1px solid #e4e8f2;
  border-radius: 0.625rem;
  background: #fff;
  box-shadow: 0 0.25rem 0.875rem rgba(34, 41, 63, 0.06);
}

.debug-error-list-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.debug-error-item {
  display: grid;
  grid-template-columns: 1.5rem minmax(0, 1fr);
  gap: 0.625rem;
  align-items: start;
  padding: 0.75rem;
  border-bottom: 1px solid #edf0f6;
}

.debug-error-item:last-child {
  border-bottom: 0;
}

.debug-error-item span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.4375rem;
  background: #fff1f1;
  color: #d83434;
  font-size: 0.75rem;
  font-weight: 900;
}

.debug-error-item p {
  margin: 0;
  color: #30364a;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.debug-error-empty-card {
  min-height: 8.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  color: #8b93a7;
}

.debug-error-empty-card span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.625rem;
  background: #effbf3;
  color: #18a058;
  font-size: 1rem;
  font-weight: 900;
}

.debug-error-empty-card strong {
  color: #31384c;
  font-size: 0.9375rem;
}

.debug-error-empty-card small {
  color: #9aa2b4;
  font-size: 0.75rem;
}

.chatflow-runtime-debug {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-content: start;
  gap: 0.75rem;
}

.chatflow-runtime-debug section,
.workflow-runtime-debug section {
  min-width: 0;
  padding: 0.75rem;
  border: 1px solid #edf0f6;
  border-radius: 0.625rem;
  background: #fbfcff;
}

.workflow-runtime-debug {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-content: start;
  gap: 0.875rem;
}

.trace-detail-layout {
  min-width: 0;
}

.trace-summary-card,
.trace-main-card,
.trace-node-detail-card {
  grid-column: 1 / -1;
}

.trace-summary-card {
  background: #fff;
}

.trace-summary-card p {
  margin: 0.25rem 0 0;
}

.trace-detail-grid {
  grid-column: 1 / -1;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(13rem, 0.36fr) minmax(24rem, 1fr);
  gap: 0.75rem;
  align-items: stretch;
}

.trace-detail-grid .trace-main-card,
.trace-detail-grid .trace-node-detail-card {
  grid-column: auto;
}

.trace-main-card {
  min-height: 8.5rem;
  max-height: 12rem;
  overflow: auto;
}

.coze-call-tree-card {
  max-height: none;
  min-height: 13.5rem;
  background: #fff;
}

.coze-detail-card {
  min-height: 13.5rem;
  display: grid;
  align-content: start;
  gap: 0.75rem;
  background: #fff;
}

.coze-detail-header {
  align-items: center;
}

.coze-detail-header select {
  height: 1.875rem;
  min-width: 6.75rem;
  border: 1px solid #dbe0ec;
  border-radius: 0.5rem;
  background: #fff;
  color: #4c5265;
  font-weight: 800;
}

.coze-flame-card {
  max-height: none;
  overflow: visible;
  padding: 0;
  border: 0;
  background: transparent;
}

.coze-selected-node-detail {
  display: grid;
  gap: 0.5rem;
}

.trace-node-detail-card {
  min-height: 8rem;
}

.trace-advanced-card {
  grid-column: 1 / -1;
  min-width: 0;
  border: 1px solid #edf0f6;
  border-radius: 0.625rem;
  background: #fbfcff;
}

.trace-advanced-card summary {
  padding: 0.75rem;
  color: #5558e8;
  font-weight: 900;
  cursor: pointer;
}

.trace-advanced-card[open] {
  padding-bottom: 0.75rem;
}

.trace-advanced-card[open] summary {
  border-bottom: 1px solid #edf0f6;
}

.trace-advanced-card section {
  margin: 0.75rem;
}

.workflow-run-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin: 0 0 0.75rem;
}

.workflow-run-metrics div {
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: #fff;
}

.workflow-run-metrics dt {
  color: #7c8498;
  font-size: 0.75rem;
}

.workflow-run-metrics dd {
  margin: 0.125rem 0 0;
  color: #30364a;
  font-weight: 900;
}

.workflow-run-io {
  display: grid;
  gap: 0.375rem;
}

.workflow-run-io pre,
.workflow-node-detail-list pre {
  max-height: 5.5rem;
  margin: 0;
  overflow: auto;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: #fff;
  color: #30364a;
  white-space: pre-wrap;
}

.workflow-call-tree {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.workflow-call-tree li {
  position: relative;
  min-width: 0;
}

.workflow-call-tree-node {
  position: relative;
  width: 100%;
  min-width: 0;
  display: grid;
  gap: 0.0625rem;
  padding: 0.375rem 0.5rem;
  border: 0;
  border-radius: 0.375rem;
  background: transparent;
  color: #30364a;
  text-align: left;
  cursor: pointer;
}

.workflow-call-tree-node strong {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
  color: #252b3d;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-call-tree-node strong::before {
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
  display: inline-flex;
  border: 1px solid rgba(85, 88, 232, 0.18);
  border-radius: 0.3125rem;
  background: #eef0ff;
  box-shadow: inset 0 0 0 0.1875rem #fff;
  content: "";
}

.workflow-call-tree-node.depth-1 {
  width: calc(100% - 1.25rem);
  margin-left: 1.25rem;
}

.workflow-call-tree-node.depth-2 {
  width: calc(100% - 2.5rem);
  margin-left: 2.5rem;
}

.workflow-call-tree-node.depth-3 {
  width: calc(100% - 3.75rem);
  margin-left: 3.75rem;
}

.workflow-call-tree-node.depth-4 {
  width: calc(100% - 5rem);
  margin-left: 5rem;
}

.workflow-call-tree-node.depth-5 {
  width: calc(100% - 6.25rem);
  margin-left: 6.25rem;
}

.workflow-call-tree-node.depth-6 {
  width: calc(100% - 7.5rem);
  margin-left: 7.5rem;
}

.workflow-call-tree-branch:not(.depth-0)::before {
  position: absolute;
  left: -0.8125rem;
  top: -0.25rem;
  width: 0.625rem;
  height: 1.25rem;
  border-left: 1px solid #cfd5df;
  border-bottom: 1px solid #cfd5df;
  border-bottom-left-radius: 0.25rem;
  content: "";
}

.workflow-call-tree-node.active,
.workflow-call-tree-node:hover {
  background: #f4f6ff;
  color: #242a42;
}

.workflow-call-tree small,
.workflow-node-detail-list small {
  color: #7c8498;
}

.workflow-call-tree small {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.workflow-call-status {
  display: inline-flex;
  align-items: center;
  padding: 0.0625rem 0.375rem;
  border-radius: 999rem;
  background: #eef1f7;
  color: #667085;
  font-size: 0.6875rem;
  font-weight: 900;
}

.workflow-call-status.status-succeeded {
  background: #dcf8e8;
  color: #159947;
}

.workflow-call-status.status-failed {
  background: #ffe7e7;
  color: #d93042;
}

.workflow-call-status.status-interrupted {
  background: #fff3d7;
  color: #b56b00;
}

.workflow-call-status.status-running {
  background: #e7edff;
  color: #4f5cf5;
}

.workflow-flamegraph {
  display: grid;
  gap: 0;
  min-width: 0;
  overflow-x: auto;
  overflow-y: visible;
  padding: 0.625rem 0.75rem 0.75rem;
  border: 1px solid #e6e9f4;
  border-radius: 0.5rem;
  background: #fff;
}

.workflow-flame-scrollbar {
  position: relative;
  min-width: 30rem;
  height: 1.5rem;
  margin-bottom: 0.25rem;
  border: 1px solid #c7ccee;
  border-radius: 0.375rem;
  background: #eef0ff;
}

.workflow-flame-scrollbar::before,
.workflow-flame-scrollbar::after {
  position: absolute;
  top: -0.0625rem;
  width: 0.625rem;
  height: calc(100% + 0.125rem);
  border: 1px solid #aeb7d6;
  border-radius: 0.3125rem;
  background: #fff;
  content: "";
}

.workflow-flame-scrollbar::before {
  left: -0.0625rem;
}

.workflow-flame-scrollbar::after {
  right: -0.0625rem;
}

.workflow-flame-scrollbar span {
  position: absolute;
  inset: 0.1875rem 0.625rem;
  border-radius: 0.25rem;
  background: #dfe3ff;
}

.workflow-flame-axis {
  min-width: 30rem;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding: 0.125rem 0.25rem 0.5rem;
  border-bottom: 1px solid #e6e9f4;
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
  text-align: center;
}

.workflow-flame-lanes {
  min-width: 30rem;
  display: grid;
  gap: 0.375rem;
  padding: 0.625rem 0;
  background:
    repeating-linear-gradient(
      to right,
      transparent 0,
      transparent 19%,
      rgba(174, 181, 205, 0.34) 19%,
      rgba(174, 181, 205, 0.34) calc(19% + 1px),
      transparent calc(19% + 1px),
      transparent 20%
    );
}

.workflow-flame-row {
  min-height: 2.25rem;
  display: grid;
  grid-template-columns: minmax(0, var(--flame-left, 0%)) minmax(8rem, var(--flame-width, 80%)) minmax(0, 1fr);
  align-items: center;
}

.workflow-flame-bar {
  grid-column: 2;
  min-width: 0;
  overflow: hidden;
  padding: 0.5rem 0.625rem;
  border: 1px solid #d4e8f2;
  border-radius: 0.1875rem;
  background: #e8f7fc;
  color: #30364a;
  font-weight: 800;
  text-overflow: ellipsis;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
}

.workflow-flame-bar:hover,
.workflow-flame-bar:focus-visible {
  border-color: #5558e8;
  outline: none;
  box-shadow: 0 0 0 2px rgba(85, 88, 232, 0.12);
}

.workflow-node-detail-list {
  display: grid;
  gap: 0.625rem;
}

.workflow-node-detail-list article {
  display: grid;
  gap: 0.375rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid #edf0f6;
}

.workflow-node-evidence-row {
  width: fit-content;
  max-width: 100%;
  padding: 0.25rem 0.5rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.375rem;
  background: #f7f9fc;
  color: #4c556b;
  font-size: 0.75rem;
  font-weight: 800;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.debug-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.625rem;
}

.debug-section-title span {
  color: #7c8498;
  font-size: 0.75rem;
  font-weight: 700;
}

.chatflow-waiting-state p,
.chatflow-timeline-section p,
.chatflow-variable-section p {
  margin: 0.25rem 0 0;
  color: #7c8498;
}

.resume-field-row {
  display: grid;
  gap: 0.375rem;
  margin-top: 0.625rem;
}

.resume-field-row label {
  color: #5d667a;
  font-size: 0.75rem;
  font-weight: 800;
}

.resume-field-row input {
  height: 2rem;
  min-width: 0;
  padding: 0 0.625rem;
  border: 1px solid #d7dcea;
  border-radius: 0.5rem;
  background: #fff;
  color: #30364a;
  outline: none;
}

.resume-submit-button {
  height: 2rem;
  margin-top: 0.625rem;
  padding: 0 0.875rem;
  border: 0;
  border-radius: 0.5rem;
  background: #5558e8;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.resume-submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chatflow-timeline-list {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.chatflow-timeline-list li {
  display: grid;
  gap: 0.125rem;
  padding-left: 0.75rem;
  border-left: 0.125rem solid #cfd5ff;
}

.timeline-sequence {
  color: #5558e8;
  font-size: 0.75rem;
  font-weight: 900;
}

.chatflow-timeline-list small {
  color: #7c8498;
}

.chatflow-variable-list {
  display: grid;
  gap: 0.375rem;
}

.chatflow-variable-list div {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(8rem, 0.85fr) minmax(0, 1fr);
  gap: 0.5rem;
  align-items: center;
}

.chatflow-variable-list code {
  overflow: hidden;
  color: #5558e8;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chatflow-variable-list span {
  overflow: hidden;
  color: #30364a;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-config-panel {
  position: absolute;
  grid-column: 1 / -1;
  justify-self: end;
  top: var(--debug-dock-gap);
  right: var(--debug-dock-gap);
  bottom: var(--debug-dock-gap);
  z-index: 20;
  width: var(--workflow-side-panel-width);
  display: flex;
  flex-direction: column;
  border: 1px solid #dfe3ee;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 1rem 2.75rem rgba(34, 41, 63, 0.16);
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.test-run-panel,
.ops-panel {
  position: absolute;
  grid-column: 1 / -1;
  justify-self: end;
  top: var(--debug-dock-gap);
  right: var(--debug-dock-gap);
  bottom: var(--debug-dock-gap);
  z-index: 60;
  width: var(--workflow-side-panel-width);
  display: flex;
  flex-direction: column;
  border: 1px solid #dfe3ee;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 1rem 2.75rem rgba(34, 41, 63, 0.16);
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.node-test-drawer {
  position: absolute;
  top: var(--debug-dock-gap);
  right: calc(var(--workflow-side-panel-gap) + var(--workflow-side-panel-width) + var(--workflow-node-test-panel-gap));
  bottom: var(--debug-dock-gap);
  z-index: 70;
  width: var(--workflow-node-test-panel-width);
  display: flex;
  flex-direction: column;
  border: 1px solid #dfe3ee;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 1rem 2.75rem rgba(34, 41, 63, 0.16);
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.workflow-canvas-page.has-node-test-drawer:not(.has-right-panel) .node-test-drawer {
  right: var(--debug-dock-gap);
}

.workflow-canvas-page.canvas-layout-right-anchored .node-config-panel {
  right: var(--debug-dock-gap);
}

.workflow-canvas-page.canvas-layout-right-anchored .test-run-panel {
  right: var(--debug-dock-gap);
}

.workflow-canvas-page.canvas-layout-right-anchored .ops-panel {
  right: var(--debug-dock-gap);
}

.workflow-canvas-page.canvas-layout-right-shelved .node-config-panel {
  right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)));
}

.workflow-canvas-page.canvas-layout-right-shelved .test-run-panel {
  right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)));
}

.workflow-canvas-page.canvas-layout-right-shelved .ops-panel {
  right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)));
}

.workflow-canvas-page.canvas-layout-right-shelved .node-test-drawer {
  right: calc(var(--workflow-panel-peek-width) + var(--workflow-node-test-panel-gap));
}

.workflow-canvas-page.canvas-layout-stage-shelved .node-config-panel,
.workflow-canvas-page.canvas-layout-stage-shelved .test-run-panel,
.workflow-canvas-page.canvas-layout-stage-shelved .ops-panel,
.workflow-canvas-page.canvas-layout-left-rail .node-config-panel,
.workflow-canvas-page.canvas-layout-left-rail .test-run-panel,
.workflow-canvas-page.canvas-layout-left-rail .ops-panel {
  position: fixed;
  top: calc(4.625rem + var(--debug-dock-gap));
  right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)));
  bottom: var(--debug-dock-gap);
}

.workflow-canvas-page.canvas-layout-stage-shelved .node-test-drawer,
.workflow-canvas-page.canvas-layout-left-rail .node-test-drawer {
  right: calc(-1 * (var(--workflow-node-test-panel-width) - var(--workflow-panel-peek-width)));
}

.node-test-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 0.5rem;
  align-items: center;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid #edf0f6;
}

.node-test-header-title {
  min-width: 0;
}

.node-test-header h3 {
  margin: 0;
  color: #252b3a;
  font-size: 1rem;
}

.node-test-header span {
  color: #858da1;
  font-size: 0.75rem;
}

.node-test-log-action {
  height: 2rem;
  padding: 0 0.625rem;
  border: 0;
  border-radius: 0.4375rem;
  background: transparent;
  color: #252b3a;
  font-size: 0.9375rem;
  font-weight: 800;
  cursor: pointer;
}

.node-test-close-button {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0.4375rem;
  background: transparent;
  color: #252b3a;
  cursor: pointer;
}

.node-test-close-button svg {
  width: 1rem;
  height: 1rem;
}

.ghost-action {
  min-height: 1.75rem;
  padding: 0 0.5rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.4375rem;
  background: #f8f9fc;
  color: #687189;
  font-size: 0.75rem;
  font-weight: 700;
}

.node-test-section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.node-test-section-title strong {
  margin-right: auto;
  color: #31384c;
  font-size: 0.875rem;
}

.node-test-input-list {
  display: grid;
  gap: 0.625rem;
}

.node-test-input-row {
  display: grid;
  gap: 0.375rem;
}

.node-test-input-row span {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  color: #596174;
  font-size: 0.75rem;
  font-weight: 800;
}

.node-test-input-row em {
  padding: 0.125rem 0.375rem;
  border-radius: 0.375rem;
  background: #eef1f8;
  color: #7b8498;
  font-size: 0.6875rem;
  font-style: normal;
}

.node-test-running {
  min-height: 16.25rem;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 0.875rem;
  color: #4d55e8;
}

.node-test-spinner {
  width: 2.125rem;
  height: 2.125rem;
  border: 0.1875rem solid #e0e4ff;
  border-top-color: #565bf6;
  border-radius: 62.4375rem;
  animation: node-test-spin 0.8s linear infinite;
}

@keyframes node-test-spin {
  to {
    transform: rotate(360deg);
  }
}

.node-test-status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  width: fit-content;
  padding: 0.25rem 0.5rem;
  border-radius: 62.4375rem;
  font-size: 0.75rem;
  font-weight: 900;
}

.node-test-status.success {
  background: #e9f9ef;
  color: #16833a;
}

.node-test-status.failure {
  background: #fdecec;
  color: #d83434;
}

.node-test-error {
  color: #d83434;
  font-size: 0.8125rem;
}

.node-test-readable-result {
  display: grid;
  gap: 1rem;
  margin-top: 0.875rem;
}

.node-test-readable-result h4 {
  margin: 0;
  color: #252b3a;
  font-size: 1rem;
  font-weight: 900;
}

.node-test-readable-block {
  display: grid;
  gap: 0.5rem;
}

.node-test-readable-heading {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  min-width: 0;
}

.node-test-readable-heading strong {
  color: #252b3a;
  font-size: 0.9375rem;
  font-weight: 900;
}

.node-test-readable-heading button {
  width: 1.375rem;
  height: 1.375rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0.375rem;
  background: transparent;
  color: #596174;
  cursor: pointer;
}

.node-test-readable-heading button:hover {
  background: #eef1fb;
  color: #4f46ff;
}

.node-test-readable-heading svg {
  width: 0.875rem;
  height: 0.875rem;
}

.node-test-readable-card {
  max-height: 12rem;
  overflow: auto;
  padding: 0.75rem;
  border: 0.0625rem solid #dfe4ef;
  border-radius: 0.625rem;
  background: #fff;
  color: #252b3a;
  font-size: 0.875rem;
  line-height: 1.6;
}

.node-test-readable-row {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 0.375rem;
  align-items: start;
}

.node-test-readable-row + .node-test-readable-row {
  margin-top: 0.375rem;
}

.node-test-readable-row span {
  color: #4f46ff;
  font-weight: 800;
}

.node-test-readable-row span::after {
  content: ':';
  margin-left: 0.25rem;
  color: #4f46ff;
}

.node-test-readable-row em,
.node-test-readable-text {
  min-width: 0;
  color: #252b3a;
  font-style: normal;
  white-space: pre-wrap;
  word-break: break-word;
}

.node-test-footer {
  margin-top: auto;
  padding: 0.75rem 1rem;
  border-top: 1px solid #edf0f6;
}

.node-test-footer button {
  width: 100%;
  height: 2.375rem;
  border: 0;
  border-radius: 0.5625rem;
  color: #fff;
  font-weight: 900;
}

.node-test-footer button.run {
  background: #22c55e;
}

.node-test-footer button.stop {
  background: #8d95a8;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  position: sticky;
  top: 0;
  z-index: 4;
  padding: 1rem;
  border-bottom: 1px solid #edf0f6;
  background: #fff;
}

.config-header h3 {
  margin: 0;
  font-size: 1.0625rem;
  line-height: 1.3;
  color: #252b3d;
}

.config-title-block {
  flex: 1;
  min-width: 0;
}

.config-title-button {
  width: auto !important;
  height: auto !important;
  margin-left: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  color: #252b3d !important;
  justify-content: flex-start !important;
}

.config-title-heading {
  font-size: 1.0625rem;
  font-weight: 700;
  line-height: 1.3;
  color: #252b3d;
}

.config-header .config-title-heading {
  font-size: 1.0625rem;
  color: #252b3d;
}

.config-title-editor {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.config-title-editor input {
  width: min(16rem, 100%);
  height: 2rem;
  padding: 0 0.625rem;
  border: 0.0625rem solid #5558e8;
  border-radius: 0.5rem;
  color: #252b3d;
  font-size: 1rem;
  font-weight: 700;
  outline: none;
}

.config-header .config-title-editor button {
  width: 1.75rem;
  height: 1.75rem;
  margin-left: 0;
}

.config-header span {
  font-size: 0.75rem;
  color: #8b94a8;
}

.config-header button {
  width: 2rem;
  height: 2rem;
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.0625rem solid #e1e6f3;
  border-radius: 0.4375rem;
  background: #f1f3f8;
  color: #687287;
  font-size: 0.875rem;
  cursor: pointer;
  transition:
    background-color 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;
}

.config-header button:hover,
.section-icon-button:hover,
.output-row-icon:hover:not(:disabled) {
  border-color: #cfd6ea;
  background: #f8faff;
  color: #3f4658;
}

.config-header button svg,
.section-icon-button svg,
.output-row-icon svg,
.debug-cancel-run-button svg,
.debug-close-button svg {
  width: 0.875rem;
  height: 0.875rem;
  stroke-width: 1.75;
}

.config-header-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.config-header-actions + button {
  margin-left: 0;
}

.config-header-actions button,
.section-icon-button {
  width: 2rem;
  height: 2rem;
  margin-left: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.0625rem solid #e1e6f3;
  border-radius: 0.4375rem;
  background: #f1f3f8;
  color: #687287;
  font-size: 0.875rem;
}

.config-section {
  position: relative;
  overflow: visible;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid #edf0f6;
}

.config-section.picker-open {
  z-index: 8;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: #31384c;
}

.section-title span {
  color: #6f778a;
}

.config-section-title-row {
  justify-content: space-between;
}

.config-section.collapsed .section-title {
  margin-bottom: 0;
}

.config-section-toggle {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #31384c;
  cursor: pointer;
}

.config-section-toggle strong {
  font-size: 0.875rem;
  line-height: 1.35;
}

.section-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
  color: #6f778a;
  font-size: 1rem;
  line-height: 1;
  transform: rotate(90deg);
  transition: transform 0.16s ease;
}

.config-section-toggle[aria-expanded='false'] .section-chevron {
  transform: rotate(0deg);
}

.config-section-content {
  position: relative;
  min-width: 0;
  overflow: visible;
}

.config-field {
  margin-bottom: 0.75rem;
}

.config-field:last-child {
  margin-bottom: 0;
}

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.375rem;
}

.config-field label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: #828b9f;
}

.variable-trigger {
  height: 1.5rem;
  padding: 0 0.5rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.375rem;
  background: #f7f8fc;
  color: #5b5ef6;
  font-size: 0.75rem;
  font-weight: 700;
  cursor: pointer;
}

.variable-popover {
  position: fixed;
  z-index: 120;
  top: var(--workflow-variable-picker-top, 8rem);
  left: var(--workflow-variable-picker-left, 24rem);
  box-sizing: border-box;
  width: var(--workflow-variable-picker-width, 33rem);
  max-width: calc(100% - 2rem);
  margin-top: 0;
  padding: 0.75rem;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.875rem;
  background: #fff;
  box-shadow: 0 1.25rem 3.5rem rgba(35, 42, 72, 0.18);
}

.variable-popover::after {
  content: '';
  position: absolute;
  top: 2rem;
  right: -0.375rem;
  width: 0.75rem;
  height: 0.75rem;
  border-top: 0.0625rem solid #dfe3ee;
  border-right: 0.0625rem solid #dfe3ee;
  background: #fff;
  transform: rotate(45deg);
}

.variable-popover :deep(.ant-input) {
  min-height: 2.5rem;
  border-radius: 0.75rem;
  background: #f9fafc;
}

.inline-variable-suggestion-popover {
  position: fixed;
  box-sizing: border-box;
  z-index: 140;
  top: var(--workflow-inline-variable-picker-top, 8rem);
  left: var(--workflow-inline-variable-picker-left, 24rem);
  width: var(--workflow-inline-variable-picker-width, 24rem);
  max-width: calc(100% - 2rem);
  padding: 0.75rem;
  border: 0.0625rem solid #edf0f7;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 1rem 2.25rem rgba(35, 42, 72, 0.18);
}

.inline-variable-suggestion-popover :deep(.ant-input) {
  min-height: 2.5rem;
  padding: 0 0.75rem;
  border-radius: 0.5rem;
  background: #f0f1f4;
  box-shadow: none;
}

.inline-variable-suggestion-popover :deep(.ant-input) {
  color: #30364a;
  font-size: 1rem;
}

.inline-variable-list {
  max-height: 12rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 0.5rem;
  overflow-y: auto;
}

.inline-variable-option {
  width: 100%;
  min-height: 2.5rem;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: flex-start;
  padding: 0.375rem 0.5rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #30364a;
  text-align: left;
  cursor: pointer;
}

.inline-variable-option:hover,
.inline-variable-option:focus-visible {
  background: #f4f6fb;
  outline: 0;
}

.inline-variable-option .variable-option-main {
  width: auto;
  min-width: max-content;
  max-width: none;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
}

.inline-variable-option .variable-option-main strong {
  max-width: none;
  display: inline-block;
  overflow: visible;
  white-space: nowrap;
  text-overflow: clip;
  font-size: 0.875rem;
}

.inline-variable-option .variable-type-badge {
  width: auto;
  min-width: 0;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
}

.variable-source-list,
.variable-item-list {
  min-width: 0;
  padding: 0.5rem;
  border: 0.0625rem solid #edf0f7;
  border-radius: 0.75rem;
  background: #f7f8fb;
}

.variable-source-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.variable-source-item {
  width: 100%;
  min-height: 3rem;
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) auto;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem;
  border: 0;
  border-radius: 0.625rem;
  background: transparent;
  color: #30364a;
  text-align: left;
  cursor: pointer;
}

.variable-source-item:hover,
.variable-source-item.active {
  background: #fff;
  box-shadow: 0 0.5rem 1.125rem rgba(34, 41, 63, 0.08);
}

.variable-source-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.0625rem;
}

.variable-source-copy strong,
.variable-option-main strong {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 0.75rem;
}

.variable-item-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: #fff;
  max-height: 17.5rem;
  overflow: auto;
}

.coze-variable-source-popover {
  width: var(--workflow-variable-picker-width, 16rem);
  max-width: calc(100% - 2rem);
  margin-top: 0.75rem;
  padding: 0.5rem;
  border-color: #e4e8f2;
  border-radius: 0.625rem;
  box-shadow: 0 0.75rem 1.75rem rgba(30, 41, 59, 0.14);
}

.coze-variable-source-popover::after {
  display: none;
}

.coze-variable-source-popover :deep(.ant-input) {
  min-height: 2.25rem;
  border-radius: 0.5rem;
  background: #f7f8fb;
}

.coze-variable-source-list {
  max-height: 14rem;
  margin-top: 0.5rem;
  padding: 0.25rem;
  border: 0;
  background: transparent;
  overflow-y: auto;
}

.coze-variable-source-item {
  min-height: 2.25rem;
  grid-template-columns: minmax(0, 1fr) auto;
  padding: 0.3125rem 0.5rem;
  border-radius: 0.5rem;
}

.variable-source-arrow {
  color: #8a93a8;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1;
}

.coze-variable-source-item.active,
.coze-variable-source-item:hover,
.coze-variable-source-item:focus-visible {
  background: #f1f3f8;
  box-shadow: none;
  outline: 0;
}

.variable-flyout {
  position: fixed;
  z-index: 150;
  top: var(--workflow-variable-flyout-top, 8rem);
  left: var(--workflow-variable-flyout-left, 24rem);
  width: 16rem;
  max-width: calc(100% - 1.5rem);
  max-height: 19rem;
  padding: 0.5rem;
  border: 0.0625rem solid #e4e8f2;
  border-radius: 0.625rem;
  background: #fff;
  box-shadow: 0 0.75rem 1.75rem rgba(30, 41, 59, 0.14);
}

.variable-flyout[data-placement='left']::after,
.variable-flyout[data-placement='right']::after {
  display: none;
  content: none;
}

.variable-flyout .variable-item-list {
  max-height: 14rem;
  padding: 0.125rem;
  border: 0;
  background: transparent;
}

.variable-flyout .variable-option {
  min-height: 2.5rem;
  border-radius: 0.5rem;
}

.section-title .section-icon-button {
  margin-left: auto;
}

.history-toggle {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.3125rem;
  color: #5f687d;
  font-size: 0.75rem;
  font-weight: 800;
  cursor: pointer;
}

.history-toggle input {
  width: 0.875rem;
  height: 0.875rem;
  accent-color: #565bf6;
}

.llm-mode-section {
  padding-bottom: 0.25rem;
}

.llm-mode-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.25rem;
  padding: 0.25rem;
  border-radius: 0.625rem;
  background: #f4f5fa;
}

.llm-mode-switch button {
  height: 1.875rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #6f778a;
  font-weight: 800;
}

.llm-mode-switch button.active {
  background: #fff;
  color: #5558e8;
  box-shadow: 0 0.1875rem 0.625rem rgba(34, 41, 63, 0.08);
}

.model-display-trigger {
  width: 100%;
  min-height: 2.625rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #dce2f1;
  border-radius: 0.625rem;
  background: #f8f9fc;
  color: #30364a;
  text-align: left;
  cursor: pointer;
}

.model-display-trigger span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 800;
}

.model-display-trigger small {
  flex: none;
  color: #8b93a7;
  font-size: 0.75rem;
}

.model-picker-shell,
.resource-picker-shell,
.model-parameter-panel {
  margin-top: 0.625rem;
  padding: 0.625rem;
  border: 1px solid #e4e8f2;
  border-radius: 0.625rem;
  background: #fff;
  box-shadow: 0 0.625rem 1.75rem rgba(34, 41, 63, 0.1);
}

.model-picker-shell,
.resource-picker-shell {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 0.375rem);
  z-index: 32;
  max-height: 19rem;
  margin-top: 0;
  overflow: auto;
}

.model-picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
}

.model-search-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 4rem;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.625rem;
}

.model-search-row button {
  height: 2.25rem;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.5rem;
  background: #f7f8ff;
  color: #5558e8;
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
}

.model-picker-empty {
  margin: 0.75rem 0 0;
  padding: 0.875rem;
  border-radius: 0.625rem;
  background: #f8f9fc;
  color: #8b93a7;
  text-align: center;
}

.model-parameter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.625rem;
}

.model-parameter-header button {
  width: 1.75rem;
  height: 1.75rem;
  border: 1px solid #e2e6f1;
  border-radius: 0.5rem;
  background: #f8f9fc;
  color: #6f778a;
}

.model-parameter-grid {
  display: grid;
  gap: 0.625rem;
}

.model-parameter-field {
  display: grid;
  grid-template-columns: minmax(5.75rem, 0.65fr) minmax(0, 1.35fr);
  align-items: center;
  gap: 0.625rem;
  color: #687188;
  font-size: 0.8125rem;
  font-weight: 800;
}

.model-parameter-field--number {
  grid-template-columns: minmax(0, 1fr);
  align-items: stretch;
  gap: 0.375rem;
}

.model-parameter-slider-control {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(8rem, 1fr) 5.75rem;
  gap: 0.5rem;
  align-items: center;
}

.model-parameter-slider {
  width: 100%;
  height: 0.375rem;
  border: 0;
  border-radius: 999rem;
  appearance: none;
  cursor: pointer;
}

.model-parameter-slider::-webkit-slider-thumb {
  width: 1rem;
  height: 1rem;
  border: 0.1875rem solid #fff;
  border-radius: 999rem;
  appearance: none;
  background: #5b5ef6;
  box-shadow: 0 0.125rem 0.375rem rgba(47, 51, 143, 0.24);
}

.model-parameter-slider::-moz-range-thumb {
  width: 1rem;
  height: 1rem;
  border: 0.1875rem solid #fff;
  border-radius: 999rem;
  background: #5b5ef6;
  box-shadow: 0 0.125rem 0.375rem rgba(47, 51, 143, 0.24);
}

.model-parameter-slider:focus-visible {
  outline: 0.125rem solid rgba(91, 94, 246, 0.2);
  outline-offset: 0.25rem;
}

.model-parameter-number-input {
  width: 5.75rem;
}

.model-parameter-number-input :deep(.ant-input) {
  min-height: 2.25rem;
  padding-left: 0.25rem;
  padding-right: 1.375rem;
  border-radius: 0.5rem;
  background: #fff;
}

.model-parameter-number-input :deep(.ant-input) {
  padding: 0;
  text-align: left;
  font-size: 0.8125rem;
  font-weight: 800;
}

.model-parameter-number-input :deep(.ant-input-number-handler-up),
.model-parameter-number-input :deep(.ant-input-number-handler-down) {
  right: 0;
  width: 1.125rem;
}

.model-option-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-top: 0.5rem;
}

.model-option-card {
  display: grid;
  grid-template-columns: 2.75rem minmax(0, 1fr);
  align-items: start;
  gap: 0.75rem;
  min-height: 4.75rem;
  padding: 0.625rem 0.75rem;
  border: 0;
  border-bottom: 0.0625rem solid #edf0f7;
  border-radius: 0.625rem;
  background: transparent;
  color: #30364a;
  text-align: left;
}

.model-option-card:hover:not(:disabled) {
  background: #f3f5ff;
}

.model-option-card:focus-visible {
  outline: 0.125rem solid rgba(85, 88, 246, 0.2);
  outline-offset: 0.125rem;
}

.model-provider-icon {
  width: 2.75rem;
  height: 2.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.0625rem solid #e1e6f2;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: inset 0 0 0 0.0625rem rgba(255, 255, 255, 0.8);
}

.model-provider-icon img {
  width: 2rem;
  height: 2rem;
  display: block;
  border-radius: 0.625rem;
  object-fit: contain;
}

.model-provider-icon span {
  width: 1.75rem;
  height: 1.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rem;
  color: #fff;
  font-size: 0.6875rem;
  font-weight: 900;
  line-height: 1;
}

.model-provider-icon[data-provider-icon='openai'] span {
  background: #111827;
}

.model-provider-icon[data-provider-icon='anthropic'] span {
  background: linear-gradient(135deg, #c8a77a, #5c4a34);
}

.model-provider-icon[data-provider-icon='gemini'] span {
  background: linear-gradient(135deg, #4285f4, #a142f4 48%, #34a853);
}

.model-provider-icon[data-provider-icon='azure'] span {
  background: linear-gradient(135deg, #0078d4, #50a7f0);
}

.model-provider-icon[data-provider-icon='ollama'] span {
  background: linear-gradient(135deg, #1f2937, #64748b);
}

.model-provider-icon[data-provider-icon='deepseek'] span {
  background: linear-gradient(135deg, #2563eb, #22d3ee);
}

.model-provider-icon[data-provider-icon='openrouter'] span {
  background: linear-gradient(135deg, #7c3aed, #38bdf8);
}

.model-provider-icon[data-provider-icon='doubao'] span {
  background: linear-gradient(135deg, #8b5cf6 0%, #4355ff 45%, #23d3a6 100%);
}

.model-provider-icon[data-provider-icon='compatible'] span {
  background: linear-gradient(135deg, #5561f5, #9b5cf6);
}

.model-option-copy {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
  align-content: start;
  justify-items: start;
}

.model-option-heading {
  min-width: 0;
  max-width: 100%;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.model-option-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #2e3346;
  font-weight: 800;
  line-height: 1.35;
}

.workflow-node-fallback-evidence {
  padding: 0.5rem 0.625rem;
  border: 0.0625rem solid #fde7c7;
  border-left: 0.25rem solid #f59e0b;
  border-radius: 0.375rem;
  background: #fff7ed;
  color: #7c2d12;
  font-size: 0.75rem;
  line-height: 1.45;
}

.workflow-node-runtime-event-evidence {
  display: grid;
  gap: 0.25rem;
  padding: 0.5rem 0.625rem;
  border: 0.0625rem solid #c8d7f1;
  border-left: 0.25rem solid #3b82f6;
  border-radius: 0.375rem;
  background: #f6f9ff;
  color: #344054;
  font-size: 0.75rem;
  line-height: 1.45;
}

.workflow-node-runtime-event-evidence span {
  color: #2456a7;
  font-weight: 700;
}

.workflow-node-runtime-event-evidence p {
  margin: 0;
  overflow-wrap: anywhere;
}

.model-provider-tag {
  max-width: 8rem;
  flex: 0 0 auto;
  overflow: hidden;
  padding: 0.125rem 0.375rem;
  border-radius: 62.4375rem;
  background: #eef1ff;
  color: #5558e8;
  font-size: 0.6875rem;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-option-description {
  max-width: 100%;
  overflow: hidden;
  color: #778196;
  font-size: 0.8125rem;
  font-weight: 650;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-option-card.unavailable,
.resource-picker-group.disabled {
  opacity: 0.62;
}

.resource-picker-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-top: 0.5rem;
}

.resource-picker-group button {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1875rem;
  padding: 0.5rem;
  border: 1px solid #edf0f7;
  border-radius: 0.5rem;
  background: #f8f9fc;
  color: #30364a;
}

.resource-picker-group span {
  color: #8b93a7;
  font-size: 0.6875rem;
}

.resource-picker-group button.unavailable {
  opacity: 0.62;
}

.llm-skill-type-tabs {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.25rem;
  padding: 0.25rem;
  border-radius: 0.625rem;
  background: #f4f5fa;
}

.llm-skill-type-tabs button {
  min-width: 0;
  height: 2rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #687188;
  font-size: 0.75rem;
  font-weight: 800;
  cursor: pointer;
}

.llm-skill-type-tabs button.active {
  background: #fff;
  color: #565bf6;
  box-shadow: 0 0.1875rem 0.625rem rgba(34, 41, 63, 0.08);
}

.llm-skill-search {
  margin-top: 0.625rem;
}

.llm-skill-resource-list {
  max-height: 15rem;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-top: 0.625rem;
  overflow-y: auto;
  padding-right: 0.125rem;
}

.llm-skill-resource-list button {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1875rem;
  padding: 0.625rem;
  border: 1px solid #edf0f7;
  border-radius: 0.5rem;
  background: #f8f9fc;
  color: #30364a;
  cursor: pointer;
}

.llm-skill-resource-list button.unavailable {
  cursor: not-allowed;
  opacity: 0.58;
}

.llm-skill-resource-list small {
  color: #8b93a7;
  font-size: 0.6875rem;
}

.resource-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 4rem;
  border: 1px dashed #dce1ec;
  border-radius: 0.625rem;
  color: #8b93a7;
  font-size: 0.8125rem;
}

.llm-resource-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.llm-resource-card {
  padding: 0.625rem;
  border: 1px solid #e4e8f2;
  border-radius: 0.625rem;
  background: #f8f9fc;
}

.llm-resource-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.625rem;
}

.llm-resource-card-header div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.llm-resource-card-header strong {
  color: #30364a;
  font-size: 0.8125rem;
}

.llm-resource-card-header span {
  color: #7b8498;
  font-size: 0.6875rem;
  line-height: 1.35;
}

.llm-resource-card-header button {
  width: 1.5rem;
  height: 1.5rem;
  flex: 0 0 auto;
  border: 0;
  border-radius: 0.375rem;
  background: #eef1f8;
  color: #687189;
  cursor: pointer;
}

.llm-resource-fields {
  display: grid;
  gap: 0.5rem;
  margin-top: 0.625rem;
}

.llm-resource-fields label {
  display: grid;
  gap: 0.25rem;
  color: #7b8498;
  font-size: 0.75rem;
  font-weight: 700;
}

.variable-option {
  width: 100%;
  min-height: 2.75rem;
  display: flex;
  gap: 0.375rem;
  align-items: center;
  justify-content: flex-start;
  padding: 0.5rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #30364a;
  text-align: left;
  cursor: pointer;
}

.variable-option:hover {
  background: #f4f6fb;
}

.variable-option-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.variable-type-badge {
  padding: 0.125rem 0.375rem;
  border-radius: 0.375rem;
  background: #f1f3f8;
  color: #687287;
  font-size: 0.6875rem;
  font-weight: 800;
  white-space: nowrap;
}

.variable-empty {
  margin: auto;
  color: #9aa2b4;
  font-size: 0.75rem;
}

.readonly-values {
  min-height: 2rem;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.5rem;
  background: #f7f8fc;
}

.condition-branch-editor {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.condition-branch-card {
  padding: 0.875rem;
  border: 1px solid #dfe4f1;
  border-radius: 0.75rem;
  background: #fff;
}

.condition-branch-header {
  display: grid;
  grid-template-columns: 1rem auto auto minmax(0, 1fr) 2rem;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.625rem;
}

.condition-drag-handle {
  color: #a2aabd;
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: 0;
  transform: rotate(90deg);
}

.condition-branch-kind {
  color: #30364a;
  font-size: 0.9375rem;
  font-weight: 900;
  white-space: nowrap;
}

.condition-branch-priority {
  padding: 0.3125rem 0.625rem;
  border-radius: 0.5rem;
  background: #f2f4f8;
  color: #4c5367;
  font-size: 0.8125rem;
  font-weight: 800;
  white-space: nowrap;
}

.condition-branch-title {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  min-height: 2.25rem;
  padding: 0 0.625rem;
  border: 0.0625rem solid transparent;
  border-radius: 0.5rem;
  background: #f8f9fc;
  color: #30364a;
  text-align: left;
  cursor: pointer;
}

.condition-branch-title:hover {
  border-color: #d8def4;
  background: #f4f6ff;
}

.condition-branch-title strong {
  min-width: 0;
  overflow: hidden;
  font-size: 0.9375rem;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.condition-branch-name-input :deep(.ant-input),
.condition-default-row :deep(.ant-input) {
  background: #f8f9fc;
}

.condition-row {
  display: grid;
  grid-template-columns: 4.25rem minmax(0, 1fr) 2rem;
  gap: 0.5rem;
  align-items: start;
  margin-bottom: 0.5rem;
}

.condition-logic-toggle {
  grid-column: 1 / -1;
  width: fit-content;
  display: inline-flex;
  gap: 0.25rem;
  padding: 0.1875rem;
  border-radius: 0.5rem;
  background: #f1f3f8;
}

.condition-logic-toggle button {
  min-width: 2.25rem;
  height: 1.75rem;
  border: 0;
  border-radius: 0.375rem;
  background: transparent;
  color: #71798e;
  font-size: 0.75rem;
  font-weight: 800;
  cursor: pointer;
}

.condition-logic-toggle button.active {
  background: #fff;
  color: #565bf6;
  box-shadow: 0 0.125rem 0.375rem rgba(33, 40, 60, 0.08);
}

.condition-left-cell {
  grid-column: 2 / 3;
}

.condition-operator-select {
  grid-column: 1 / 2;
  grid-row: 1 / span 2;
}

.condition-right-cell {
  grid-column: 2 / 3;
}

.condition-delete-button {
  grid-column: 3;
  grid-row: 1 / span 2;
}

.condition-value-cell {
  min-width: 0;
  position: relative;
}

.condition-row :deep(.ant-select-selector) {
  min-height: 2.25rem;
}

.condition-operand-control :deep(.ant-input) {
  height: 100%;
  min-height: 0;
  padding: 0 0.625rem;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.condition-operand-control :deep(.ant-input) {
  color: #30364a;
  font-size: 0.8125rem;
  font-weight: 700;
}

.condition-variable-chip {
  min-height: 2.25rem;
}

.condition-variable-select {
  width: 100%;
  min-width: 0;
  height: 2.25rem;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  overflow: hidden;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.5rem;
  background: #fff;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.condition-variable-select:hover,
.condition-variable-select:focus-within {
  border-color: #cfd5e6;
  box-shadow: 0 0 0 0.0625rem rgba(86, 91, 246, 0.14);
}

.condition-variable-select-button {
  min-width: 0;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0 0.625rem;
  border: 0;
  background: transparent;
  color: #30364a;
  text-align: left;
  cursor: pointer;
}

.condition-variable-select-main {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.condition-variable-select-main strong {
  font-size: 0.8125rem;
  font-weight: 800;
}

.condition-variable-select-placeholder {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #b2b9c9;
  font-size: 0.8125rem;
  font-weight: 700;
}

.condition-variable-select-arrow {
  width: 0.875rem;
  height: 0.875rem;
  flex: 0 0 auto;
  color: #9aa2b5;
}

.condition-variable-select-clear {
  margin-right: 0.375rem;
  flex: 0 0 auto;
}

.condition-right-type-prefix {
  height: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-right: 0.0625rem solid #e5e8f1;
  background: #fff;
  color: #6f778a;
  font-size: 0.8125rem;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  user-select: none;
}

.condition-variable-popover {
  margin-top: 0;
}

.condition-add-button {
  width: fit-content;
  min-width: 7.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 0 0.75rem;
}

.condition-add-button svg {
  width: 0.875rem;
  height: 0.875rem;
  stroke-width: 1.8;
}

.condition-default-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.75rem;
  align-items: center;
  padding: 0.875rem;
  border: 1px solid #dfe4f1;
  border-radius: 0.75rem;
  background: #fff;
}

.condition-default-title {
  width: 100%;
}

.input-parameter-editor {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.start-variable-editor {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.start-variable-header,
.start-variable-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 5.5rem 3.5rem 2rem;
  gap: 0.5rem;
  align-items: center;
}

.start-variable-header {
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
}

.start-required-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.start-required-toggle input {
  width: 1rem;
  height: 1rem;
  accent-color: #565bf6;
}

.secondary-row-editor {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.secondary-row-header,
.secondary-row {
  display: grid;
  gap: 0.5rem;
  align-items: center;
}

.secondary-row-header {
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
}

.question-option-header,
.question-option-row {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 2rem;
}

.collection-field-header,
.collection-field-row {
  grid-template-columns: minmax(4.25rem, 0.8fr) 4.75rem 2.75rem minmax(5rem, 1fr) minmax(6.5rem, 1.15fr) 2rem;
}

.intent-row-header,
.intent-row {
  grid-template-columns: 1.5rem minmax(0, 1fr) minmax(0, 3fr) 2rem;
}

.intent-row-header span:first-child {
  grid-column: 2;
}

.intent-row-header span:nth-child(2),
.intent-row-header span:nth-child(3) {
  display: none;
}

.intent-row {
  grid-template-areas:
    'drag name description delete'
    'drag examples examples delete';
  align-items: start;
  padding: 0.625rem;
  border: 0.0625rem solid #e0e5f1;
  border-radius: 0.75rem;
  background: #fff;
}

.intent-drag-handle {
  grid-area: drag;
  align-self: center;
  width: 1.5rem;
  min-height: 4rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #a5adbd;
  font-size: 1rem;
  line-height: 1;
  letter-spacing: 0;
  cursor: grab;
}

.intent-drag-handle:active {
  cursor: grabbing;
}

.intent-row-fields {
  display: contents;
}

.intent-name-field {
  grid-area: name;
}

.intent-description-field {
  grid-area: description;
}

.intent-examples-field {
  grid-area: examples;
}

.intent-row > .output-row-icon {
  grid-area: delete;
  align-self: start;
}

.intent-examples-field :deep(.ant-input) {
  height: 4.75rem;
  resize: none;
  overflow-y: auto;
}

.collection-target-cell {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr);
  gap: 0.375rem;
}

.secondary-empty {
  margin: 0;
  padding: 0.625rem 0.75rem;
  border: 0.0625rem dashed #dce1ef;
  border-radius: 0.5rem;
  background: #f8f9fc;
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 700;
}

.resource-adapter-badge {
  min-height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0.625rem;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.5rem;
  background: #f8f9ff;
}

.resource-adapter-badge span {
  color: #565bf6;
  font-size: 0.8125rem;
  font-weight: 900;
}

.resource-adapter-badge small {
  min-width: 0;
  color: #7c8497;
  font-size: 0.75rem;
  font-weight: 700;
  overflow: hidden;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schema-input-mapping-editor {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.schema-input-mapping-header,
.schema-input-mapping-row {
  display: grid;
  grid-template-columns: minmax(4.5rem, 0.8fr) 4.25rem minmax(0, 1.4fr);
  gap: 0.5rem;
  align-items: center;
}

.schema-input-mapping-header {
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
}

.schema-param-name {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.schema-param-name strong {
  min-width: 0;
  color: #30364a;
  font-size: 0.8125rem;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schema-param-name small {
  flex: 0 0 auto;
  padding: 0.0625rem 0.3125rem;
  border-radius: 999rem;
  background: #fff1f0;
  color: #d94a3a;
  font-size: 0.625rem;
  font-weight: 800;
}

.legacy-resource-debug {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 0;
}

.legacy-resource-debug div {
  display: grid;
  grid-template-columns: 6.5rem minmax(0, 1fr);
  gap: 0.5rem;
  align-items: start;
  padding: 0.5rem 0.625rem;
  border: 0.0625rem solid #e5e8f1;
  border-radius: 0.5rem;
  background: #f8f9fc;
}

.legacy-resource-debug dt,
.legacy-resource-debug dd {
  margin: 0;
  min-width: 0;
  font-size: 0.75rem;
  line-height: 1.35;
}

.legacy-resource-debug dt {
  color: #7c8497;
  font-weight: 800;
}

.legacy-resource-debug dd {
  color: #30364a;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  overflow-wrap: anywhere;
}

.structured-row-editor {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.json-field-mapping-header,
.json-field-mapping-row {
  display: grid;
  grid-template-columns: minmax(4.75rem, 0.9fr) minmax(6rem, 1.2fr) 4.5rem 2rem;
  gap: 0.5rem;
  align-items: center;
}

.aggregation-source-header,
.aggregation-source-row {
  display: grid;
  grid-template-columns: minmax(5rem, 0.75fr) minmax(0, 1.5fr) 2rem;
  gap: 0.5rem;
  align-items: center;
}

.aggregation-group-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.aggregation-group-card {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0.75rem;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.625rem;
  background: #fff;
}

.aggregation-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  min-height: 2rem;
}

.aggregation-group-title {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  flex: 1;
}

.aggregation-group-name-display {
  max-width: 11rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: #30364a;
  font-size: 0.9375rem;
  font-weight: 900;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: text;
}

.aggregation-group-name-input {
  width: min(11rem, 100%);
  height: 1.875rem;
  padding: 0 0.5rem;
  border: 0.0625rem solid #cfd6e6;
  border-radius: 0.375rem;
  color: #30364a;
  font-size: 0.9375rem;
  font-weight: 900;
  outline: 0;
}

.aggregation-group-name-input:focus {
  border-color: #5158ff;
  box-shadow: 0 0 0 0.125rem rgba(81, 88, 255, 0.12);
}

.aggregation-group-type {
  flex: 0 0 auto;
}

.aggregation-group-info {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.0625rem solid #8991a5;
  border-radius: 999rem;
  color: #8991a5;
  font-size: 0.6875rem;
  font-weight: 900;
}

.aggregation-group-variable-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.aggregation-group-variable-row {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr) 2rem;
  gap: 0.375rem;
  align-items: center;
}

.aggregation-row-handle {
  color: #9aa3b8;
  font-size: 0.9375rem;
  line-height: 1;
  text-align: center;
}

.aggregation-add-group {
  min-height: 2.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border: 0;
  border-radius: 0.5rem;
  background: #e9ebff;
  color: #5158ff;
  font-size: 0.875rem;
  font-weight: 900;
  cursor: pointer;
}

.aggregation-add-group svg {
  width: 1rem;
  height: 1rem;
}

.aggregation-output-summary {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.aggregation-output-row {
  min-height: 2.25rem;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0 0.75rem;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.5rem;
  background: #fff;
}

.aggregation-output-row strong {
  color: #30364a;
  font-size: 0.875rem;
  font-weight: 800;
}

.human-input-schema-header,
.human-input-schema-row {
  display: grid;
  grid-template-columns: minmax(4.5rem, 0.85fr) 4.5rem 3.25rem minmax(5.5rem, 1fr) 2rem;
  gap: 0.5rem;
  align-items: center;
}

.json-field-mapping-header,
.aggregation-source-header,
.human-input-schema-header {
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
}

.variable-assignment-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.variable-assignment-header,
.variable-assignment-row {
  display: grid;
  grid-template-columns: minmax(8rem, 0.85fr) minmax(0, 1.4fr);
  gap: 0.5rem;
  align-items: center;
}

.variable-assignment-header {
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
}

.code-editor-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.code-editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  color: #687287;
  font-size: 0.75rem;
  font-weight: 800;
}

.soft-icon-button {
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.75rem;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.5rem;
  background: #f7f8fc;
  color: #565bf6;
  font-size: 0.75rem;
  font-weight: 800;
  cursor: pointer;
}

.soft-icon-button:hover {
  border-color: #cfd5e6;
  background: #eef1ff;
}

.code-editor-input :deep(.ant-input) {
  min-height: 12rem !important;
  resize: none;
  border-radius: 0.625rem;
  background: #111827;
  color: #e5e7eb;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.assignment-target-cell,
.variable-assignment-row > .input-value-cell {
  display: block;
}

.assignment-value-cell {
  display: block;
}

.input-parameter-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 3fr) 2rem;
  gap: 0.375rem;
  align-items: center;
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
}

.input-parameter-row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 3fr) 2rem;
  gap: 0.375rem;
  align-items: center;
}

.input-parameter-row > * {
  min-width: 0;
}

.input-parameter-row :deep(.ant-input),
.input-parameter-row :deep(.ant-select-selector),
.output-parameter-row :deep(.ant-input),
.output-parameter-row :deep(.ant-select-selector),
.schema-input-mapping-row :deep(.ant-input),
.schema-input-mapping-row :deep(.ant-select-selector),
.secondary-row :deep(.ant-input),
.secondary-row :deep(.ant-select-selector),
.structured-row-editor :deep(.ant-input),
.structured-row-editor :deep(.ant-select-selector) {
  min-height: 2.25rem;
}

.input-value-cell {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2.25rem;
  gap: 0.375rem;
  position: relative;
}

.input-parameter-row > .input-value-cell,
.output-parameter-row > .output-value-cell,
.aggregation-source-row > .input-value-cell {
  display: block;
}

.variable-value-combo {
  width: 100%;
  min-width: 0;
  height: 2.25rem;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2.25rem;
  align-items: stretch;
  overflow: hidden;
  border: 0.0625rem solid #dfe3ee;
  border-radius: 0.5rem;
  background: #fff;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.variable-value-combo.condition-comparison-value-control {
  grid-template-columns: 2.75rem minmax(0, 1fr) 2.25rem;
}

.variable-value-combo:focus-within,
.variable-value-combo:hover {
  border-color: #f59e0b;
  box-shadow: 0 0 0 0.0625rem rgba(245, 158, 11, 0.26);
}

.variable-value-main {
  min-width: 0;
  display: flex;
  align-items: center;
  background: #fff;
}

.variable-literal-input,
.variable-literal-select,
.variable-literal-textarea {
  width: 100%;
  min-width: 0;
  height: 100%;
  border: 0;
  background: transparent;
  color: #30364a;
  font-size: 0.8125rem;
  font-weight: 700;
  outline: 0;
}

.variable-literal-input,
.variable-literal-select {
  padding: 0 0.75rem;
}

.variable-literal-textarea {
  resize: none;
  padding: 0.5625rem 0.75rem;
  line-height: 1.15;
}

.variable-picker-trigger {
  width: 2.25rem;
  height: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-left: 0.0625rem solid #e5e8f1;
  background: #fff;
  color: #687287;
  cursor: pointer;
}

.variable-picker-trigger:hover,
.variable-picker-trigger:focus-visible {
  background: #f7f8fc;
  color: #5558e8;
  outline: 0;
}

.variable-picker-trigger svg {
  width: 1rem;
  height: 1rem;
}

.input-reference-control {
  min-width: 0;
  grid-column: 1 / -1;
  position: relative;
}

.input-reference-shortcut {
  width: 2.25rem;
  min-width: 2.25rem;
}

.input-variable-empty,
.input-variable-chip {
  position: relative;
  width: 100%;
  min-width: 0;
  height: 2.25rem;
  display: inline-flex;
  align-items: center;
  border: 1px solid #dfe3ee;
  border-radius: 0.5rem;
  background: #fff;
  color: #5f687d;
  cursor: pointer;
}

.input-variable-empty {
  justify-content: space-between;
  gap: 0.375rem;
  padding: 0 0.625rem;
  font-size: 0.75rem;
  font-weight: 800;
}

.input-variable-empty:hover,
.input-variable-chip:hover,
.input-variable-chip:focus-visible {
  border-color: #b9c0ff;
  background: #f8f9ff;
  outline: none;
}

.input-variable-chip {
  gap: 0.375rem;
  padding: 0.1875rem 0.25rem 0.1875rem 0.3125rem;
}

.variable-value-main .input-variable-chip {
  height: 100%;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.variable-value-main .input-variable-chip:hover,
.variable-value-main .input-variable-chip:focus-visible {
  background: #f8f9ff;
}

.input-variable-chip-main {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  text-align: left;
}

.input-variable-chip-main strong {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: #30364a;
  font-size: 0.75rem;
  line-height: 1;
}

.input-variable-chip .variable-type-badge {
  flex: 0 0 auto;
}

.input-variable-clear {
  width: 1.375rem;
  height: 1.375rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e3e6f0;
  border-radius: 0.375rem;
  background: #fff;
  color: #9aa2b5;
  font-size: 0.875rem;
  line-height: 1;
  cursor: pointer;
}

.input-variable-clear:hover {
  border-color: #ccd2e4;
  color: #596173;
}

.reference-value-proxy {
  position: absolute;
  width: 0.0625rem;
  height: 0.0625rem;
  opacity: 0;
  pointer-events: none;
}

.input-variable-popover {
  width: 33rem;
  max-width: calc(100% - 2rem);
}

.input-variable-popover.coze-variable-source-popover {
  width: var(--workflow-variable-picker-width, 16rem);
}

.input-add-button {
  height: 2rem;
  border: 1px dashed #b7bef4;
  border-radius: 0.5rem;
  background: #f7f8ff;
  color: #5558e8;
  font-size: 0.8125rem;
  font-weight: 800;
  cursor: pointer;
}

.output-parameter-editor {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.end-response-editor {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.end-return-mode {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.25rem;
  padding: 0.25rem;
  border: 0.0625rem solid #eceff6;
  border-radius: 0.625rem;
  background: #f4f5f9;
}

.end-return-mode button {
  min-height: 2rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #636b7f;
  font-size: 0.875rem;
  font-weight: 800;
  cursor: pointer;
}

.end-return-mode button.active {
  background: #fff;
  color: #565bf6;
  box-shadow: 0 0.25rem 0.75rem rgba(40, 47, 75, 0.08);
}

.end-output-format-row,
.end-response-heading {
  display: grid;
  grid-template-columns: 5.25rem minmax(0, 1fr);
  gap: 0.625rem;
  align-items: center;
}

.end-output-format-row label,
.end-response-heading label {
  margin: 0;
  color: #6f778a;
  font-size: 0.75rem;
  font-weight: 800;
}

.end-response-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.625rem;
  min-width: 0;
}

.end-stream-switch {
  display: inline-flex !important;
  align-items: center;
  gap: 0.5rem;
  color: #30364a !important;
  font-size: 0.8125rem !important;
  font-weight: 800 !important;
}

.end-response-textarea :deep(.ant-input) {
  resize: none;
}

.end-variable-popover {
  margin-top: 0;
}

.output-format-row,
.output-parameter-row {
  display: grid;
  gap: 0.5rem;
  align-items: center;
}

.output-format-row {
  grid-template-columns: 5.25rem minmax(0, 1fr);
}

.output-format-row label {
  margin: 0;
  color: #6f778a;
  font-size: 0.75rem;
  font-weight: 800;
}

.output-column-row {
  display: grid;
  grid-template-columns: minmax(6rem, 1fr) 7.75rem 2rem;
  gap: 0.5rem;
  align-items: center;
  color: #8b93a7;
  font-size: 0.75rem;
  font-weight: 800;
}

.output-column-row .output-row-icon {
  justify-self: end;
}

.end-output-column-row {
  grid-template-columns: minmax(5.25rem, 0.9fr) 5.75rem minmax(0, 1.35fr) 2rem;
}

.output-parameter-row {
  grid-template-columns: minmax(6rem, 1fr) 7.75rem 2rem;
}

.end-output-parameter-row {
  grid-template-columns: minmax(5.25rem, 0.9fr) 5.75rem minmax(0, 1.35fr) 2rem;
}

.output-value-cell {
  grid-template-columns: minmax(0, 1fr) 2.25rem;
}

.config-field .switch-field-row,
.switch-field-row {
  min-height: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.25rem 0;
}

.switch-field-row span {
  color: #687189;
  font-size: 0.8125rem;
  font-weight: 800;
}

.switch-field-row :deep(.ant-switch) {
  margin-left: auto;
}

.tool-resource-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
}

.tool-resource-option strong,
.tool-resource-option small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-resource-option small {
  color: #8a94a6;
}

.output-row-icon {
  width: 2rem;
  height: 2.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dfe3ee;
  border-radius: 0.5rem;
  background: #f7f8fc;
  color: #687287;
  cursor: pointer;
}

.output-row-icon:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.output-parameter-errors {
  margin: 0;
  padding-left: 1.125rem;
  color: #c23b3b;
  font-size: 0.75rem;
  line-height: 1.7;
}

.workflow-canvas-page :deep(.ant-input),
.workflow-canvas-page :deep(.ant-input),
.workflow-canvas-page :deep(.ant-select-selector) {
  border-radius: 0.5rem;
}

.workflow-canvas-page :deep(.ant-input),
.workflow-canvas-page textarea {
  resize: none;
}

.validation-title {
  color: #d94848;
}

.validation-list {
  margin: 0;
  padding-left: 1.125rem;
  color: #c23b3b;
  font-size: 0.8125rem;
  line-height: 1.8;
}

.run-summary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.625rem;
  color: #6b7487;
  font-size: 0.75rem;
  font-weight: 700;
}

.run-status {
  min-width: 4.875rem;
  padding: 0.1875rem 0.5rem;
  border-radius: 62.4375rem;
  background: #fee2e2;
  color: #b42318;
  font-size: 0.6875rem;
  font-weight: 900;
  line-height: 1.3;
  text-align: center;
}

.run-status.success {
  background: #dcfce7;
  color: #167a3a;
}

.workflow-result-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.workflow-result-row {
  display: grid;
  grid-template-columns: 5.5rem minmax(0, 1fr);
  gap: 0.625rem;
  padding: 0.625rem;
  border: 1px solid #e1e5ef;
  border-radius: 0.5625rem;
  background: #f8f9fc;
}

.workflow-result-row span {
  color: #7c8598;
  font-size: 0.75rem;
  font-weight: 800;
}

.workflow-result-row strong {
  color: #252b3d;
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.workflow-result-empty {
  padding: 0.625rem;
  border-radius: 0.5625rem;
  background: #f8f9fc;
  color: #8b94a8;
  font-size: 0.8125rem;
}

.chatflow-run-panel {
  overflow: hidden;
}

.chatflow-run-panel .config-header,
.chatflow-run-panel .config-section {
  flex: 0 0 auto;
}

.chatflow-run-header {
  position: sticky;
  overflow: visible;
}

.chatflow-run-header-title {
  min-width: 0;
  flex: 1 1 auto;
}

.chatflow-run-header-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.config-header.chatflow-run-header button {
  margin-left: 0;
}

.chatflow-run-header-button {
  width: auto !important;
  min-width: 5.5rem;
  gap: 0.25rem;
  padding: 0 0.625rem;
  background: #f7f8ff !important;
  color: #5558e8 !important;
  font-weight: 800;
}

.chatflow-run-header-button svg {
  transition: transform 0.16s ease;
}

.chatflow-run-header-button.active svg {
  transform: rotate(180deg);
}

.chatflow-run-header-icon:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.chatflow-run-settings-popover {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 1rem;
  z-index: 8;
  width: min(25rem, calc(100% - 2rem));
  display: grid;
  gap: 0.625rem;
  padding: 0.875rem;
  border: 0.0625rem solid #dfe5f2;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 1rem 2.25rem rgba(34, 41, 63, 0.16);
}

.chatflow-run-settings-summary {
  color: #8b94a8;
  font-size: 0.75rem;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chatflow-profile-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.5rem;
}

.chatflow-profile-grid :deep(.ant-input),
.chatflow-profile-grid :deep(.ant-select-selector) {
  height: 2.75rem;
  min-height: 2.75rem;
}

.chatflow-run-chat-window {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.875rem 1rem 1rem;
}

.chatflow-message-list {
  flex: 1 1 auto;
  min-height: 11rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-right: 0.25rem;
  overflow-y: auto;
}

.chatflow-empty-message {
  color: #8b94a8;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.chatflow-run-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #8b94a8;
  font-size: 0.75rem;
}

.chatflow-resume-card {
  display: grid;
  gap: 0.625rem;
  padding: 0.75rem;
  border: 0.0625rem solid #dbe2f0;
  border-radius: 0.75rem;
  background: #f7f9ff;
}

.chatflow-composer {
  padding-top: 0.75rem;
  border-top: 0.0625rem solid #edf0f6;
}

.chatflow-composer-shell {
  min-height: 6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
  border: 0.0625rem solid #cfd6e5;
  border-radius: 1rem;
  background: #fff;
}

.chatflow-composer-shell:focus-within {
  border-color: #5f61ff;
  box-shadow: 0 0 0 0.125rem rgba(95, 97, 255, 0.12);
}

.chatflow-composer-editor {
  width: 100%;
  min-width: 0;
}

.chatflow-composer-actions {
  min-height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.chatflow-upload-button,
.chatflow-send-button {
  width: 2.25rem;
  height: 2.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0.625rem;
  background: transparent;
  color: #596174;
  cursor: pointer;
}

.chatflow-upload-button:hover:not(:disabled),
.chatflow-send-button:hover:not(:disabled) {
  background: #f3f5fb;
  color: #4f46ff;
}

.chatflow-upload-button svg,
.chatflow-send-button svg {
  width: 1.125rem;
  height: 1.125rem;
}

.chatflow-composer-input {
  width: 100%;
  min-width: 0;
  min-height: 3rem !important;
  max-height: 9rem;
  padding: 0.25rem 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #252b3d;
  font-size: 1rem;
  line-height: 1.5;
  resize: none !important;
  overflow-y: auto !important;
  scrollbar-width: none;
}

.chatflow-composer-input :deep(.ant-input) {
  width: 100%;
  min-height: 3rem !important;
  max-height: 9rem;
  padding: 0.25rem 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #252b3d;
  font-size: 1rem;
  line-height: 1.5;
  resize: none !important;
  overflow-y: auto !important;
  scrollbar-width: none;
}

.chatflow-composer-input :deep(.ant-input::-webkit-scrollbar) {
  display: none;
}

.chatflow-send-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.chatflow-debug-grid {
  display: grid;
  gap: 0.625rem;
}

.run-input-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.run-input-field label {
  color: #6f778a;
  font-size: 0.75rem;
  font-weight: 800;
}

.run-input-field.compact label {
  font-size: 0.6875rem;
}

.chatflow-runtime-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #edf0f6;
}

.conversation-result {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.625rem;
}

.message-bubble {
  max-width: 88%;
  padding: 0.5625rem 0.6875rem;
  border-radius: 0.625rem;
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.message-bubble.user {
  align-self: flex-end;
  background: #eef0ff;
  color: #3438b8;
}

.message-bubble.assistant {
  align-self: flex-start;
  background: #f0f2f7;
  color: #2f3548;
}

.message-bubble.assistant.loading {
  min-width: 3.25rem;
}

.message-bubble.assistant.error {
  background: #fff0f0;
  color: #d93042;
}

.message-bubble.opening {
  background: #eefaf8;
  color: #0b6862;
}

.chatflow-loading-dots {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  min-height: 1rem;
}

.chatflow-loading-dots i {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 999rem;
  background: #8b94a8;
  animation: chatflow-loading-dot 0.9s ease-in-out infinite;
}

.chatflow-loading-dots i:nth-child(2) {
  animation-delay: 0.12s;
}

.chatflow-loading-dots i:nth-child(3) {
  animation-delay: 0.24s;
}

@keyframes chatflow-loading-dot {
  0%,
  80%,
  100% {
    opacity: 0.45;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-0.25rem);
  }
}

.typewriter-caret {
  display: inline-block;
  width: 0.0625rem;
  height: 0.875rem;
  margin-left: 0.125rem;
  vertical-align: -0.125rem;
  background: currentColor;
  animation: typewriter-caret-blink 0.9s steps(2, start) infinite;
}

@keyframes typewriter-caret-blink {
  0%,
  45% {
    opacity: 1;
  }
  46%,
  100% {
    opacity: 0;
  }
}

.chatflow-debug-stream-preview p {
  margin: 0.375rem 0 0;
  color: #2f3548;
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.chatflow-debug-stream-preview small {
  display: inline-flex;
  margin-top: 0.375rem;
  color: #8b94a8;
  font-size: 0.6875rem;
  font-weight: 700;
}

.chatflow-suggested-questions {
  align-self: flex-start;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.5rem 0 0.125rem;
}

.chatflow-suggested-title {
  color: #7c8598;
  font-size: 0.75rem;
  font-weight: 800;
}

.chatflow-guide-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.375rem;
}

.chatflow-guide-list button {
  width: fit-content;
  max-width: 100%;
  min-height: 1.75rem;
  padding: 0.25rem 0.5625rem;
  border: 1px solid #cdd3f7;
  border-radius: 62.4375rem;
  background: #f6f7ff;
  color: #4b50c8;
  font-size: 0.75rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  overflow-wrap: anywhere;
}

.chatflow-guide-list button:hover {
  background: #eef0ff;
}

.test-run-actions {
  margin-top: auto;
  padding: 0.875rem 1rem;
  border-top: 1px solid #edf0f6;
  text-align: right;
}

.save-input-check {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  margin-bottom: 0.625rem;
  color: #687189;
  font-size: 0.75rem;
  font-weight: 800;
}

.save-input-check input {
  accent-color: #22c55e;
}

.ops-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.375rem;
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid #edf0f6;
  background: #fafbff;
}

.ops-tabs button {
  height: 2rem;
  border: 0;
  border-radius: 0.4375rem;
  background: transparent;
  color: #6b7487;
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
}

.ops-tabs button.active {
  background: #eef0ff;
  color: #5d5ff6;
}

.ops-field-list {
  margin: 0;
}

.ops-field-list div {
  display: flex;
  justify-content: space-between;
  gap: 0.875rem;
  padding: 0.5625rem 0;
  border-bottom: 1px solid #f0f2f7;
}

.ops-field-list dt {
  color: #858ea2;
  font-size: 0.75rem;
  font-weight: 700;
}

.ops-field-list dd {
  margin: 0;
  max-width: 13.75rem;
  overflow-wrap: anywhere;
  color: #2f3548;
  font-size: 0.8125rem;
  font-weight: 700;
  text-align: right;
}

.ops-field-list code {
  color: #5d5ff6;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
}

.ops-code {
  max-height: 16.25rem;
  margin: 0.75rem 0 0;
  padding: 0.625rem;
  border-radius: 0.5rem;
  overflow: auto;
  background: #171a24;
  color: #d8def0;
  font-size: 0.75rem;
  line-height: 1.6;
}

.channel-shell-section {
  margin-top: 1rem;
}

.channel-shell-grid {
  display: grid;
  gap: 0.625rem;
}

.channel-shell-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.25rem 0.75rem;
  padding: 0.75rem;
  border: 1px solid #dbe3f0;
  border-radius: 0.5rem;
  background: #fff;
}

.channel-shell-card strong,
.channel-shell-card span,
.channel-shell-card p {
  display: block;
}

.channel-shell-card span,
.channel-shell-card p {
  color: #64748b;
}

.channel-shell-card em {
  font-style: normal;
  color: #2563eb;
}

.channel-shell-card.disabled {
  background: #f8fafc;
}

.channel-shell-card.disabled em {
  color: #94a3b8;
}

.channel-shell-card p {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 0.8125rem;
}

.channel-shell-card .channel-capabilities,
.channel-shell-card .channel-schema {
  color: #334155;
  font-weight: 700;
}

.channel-shell-card .channel-fields {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.publish-reasons {
  margin-top: 0.75rem;
}

.publish-actions {
  margin-top: 1rem;
  text-align: right;
}

.publish-dialog-body {
  display: grid;
  gap: 0.875rem;
}

.publish-version-field {
  display: grid;
  gap: 0.375rem;
  margin-top: 0.75rem;
}

.publish-version-field span {
  color: #788196;
  font-size: 0.75rem;
  font-weight: 800;
}

.publish-version-field input,
.publish-version-field textarea {
  width: 100%;
  border: 1px solid #d7deed;
  border-radius: 0.5rem;
  background: #fafbff;
  color: #303648;
  font-size: 0.8125rem;
}

.publish-version-field input {
  height: 2.25rem;
  padding: 0 0.625rem;
}

.publish-version-field textarea {
  min-height: 4.25rem;
  padding: 0.625rem;
  resize: none;
  line-height: 1.5;
}

.publish-dialog-body .publish-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.625rem;
  margin-top: 0;
}

.version-list {
  margin-top: 1rem;
}

.version-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto auto;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0;
  border-top: 0.0625rem solid #edf1f7;
}

.version-row strong,
.version-row span {
  display: block;
}

.version-row span {
  color: #94a3b8;
  font-size: 0.75rem;
}

.version-row em {
  font-style: normal;
  color: #2563eb;
  font-size: 0.8125rem;
}

.version-row button {
  border: 0;
  background: transparent;
  color: #5d5ff6;
  cursor: pointer;
}

.targeted-published-run-result,
.targeted-runtime-v2-run-result {
  margin: 0.5rem 0 0;
  padding: 0.5rem;
  border: 0.0625rem solid #dbe8ff;
  border-radius: 0.375rem;
  background: #f7fbff;
  color: #42526e;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.node-palette-group {
  margin-top: 0.5rem;
}

.node-palette-group strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #8b93a7;
  font-size: 0.75rem;
}

.node-palette-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.125rem 0.25rem;
}

.node-palette button {
  min-width: 0;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0 0.375rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #2f3648;
  font-size: 0.8125rem;
  font-weight: 650;
  text-align: left;
  cursor: pointer;
}

.node-palette button:hover {
  background: #f0f2fa;
}

.palette-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.0625rem solid transparent;
  border-radius: 0.375rem;
}

.palette-icon svg {
  width: 0.8125rem;
  height: 0.8125rem;
}

.canvas-toolbar {
  position: absolute;
  left: 50%;
  bottom: 1rem;
  z-index: 55;
  height: 2.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.75rem;
  border: 1px solid rgba(226, 232, 240, 0.96);
  border-radius: 0.875rem;
  background: rgba(255, 255, 255, 0.96);
  color: #2d3447;
  box-shadow: 0 0.625rem 1.875rem rgba(34, 41, 63, 0.12);
  transform: translateX(-50%);
}

.workflow-canvas-page.debug-dock-open .canvas-toolbar {
  bottom: calc(var(--debug-dock-height) + var(--debug-dock-gap) + 0.75rem);
}

.workflow-canvas-page.has-right-panel .canvas-toolbar {
  left: calc((100% - var(--workflow-right-panel-reserve)) / 2 - var(--workflow-resource-panel-width) / 2);
}

.workflow-canvas-page.has-node-test-drawer.has-right-panel .canvas-toolbar {
  left: calc((100% - var(--workflow-node-test-reserve)) / 2 - var(--workflow-resource-panel-width) / 2);
}

.workflow-canvas-page.has-right-panel .canvas-workbench.resource-collapsed .canvas-toolbar {
  left: calc((100% - var(--workflow-right-panel-reserve)) / 2);
}

.workflow-canvas-page.has-node-test-drawer.has-right-panel .canvas-workbench.resource-collapsed .canvas-toolbar {
  left: calc((100% - var(--workflow-node-test-reserve)) / 2);
}

.workflow-canvas-page.has-node-test-drawer:not(.has-right-panel) .canvas-toolbar {
  left: calc((100% - var(--workflow-node-test-panel-width) - var(--workflow-node-test-panel-gap) - var(--debug-dock-gap)) / 2 - var(--workflow-resource-panel-width) / 2);
}

.workflow-canvas-page.has-node-test-drawer:not(.has-right-panel) .canvas-workbench.resource-collapsed .canvas-toolbar {
  left: calc((100% - var(--workflow-node-test-panel-width) - var(--workflow-node-test-panel-gap) - var(--debug-dock-gap)) / 2);
}

.canvas-toolbar button {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0.0625rem solid #dfe5f2;
  border-radius: 0.5rem;
  background: #f6f8fc;
  color: #4b5568;
  cursor: pointer;
  box-shadow: 0 0.125rem 0.375rem rgba(34, 41, 63, 0.06);
  transition:
    background-color 0.16s ease,
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    color 0.16s ease,
    opacity 0.16s ease;
}

.canvas-toolbar button:hover:not(:disabled) {
  border-color: #cbd3e6;
  background: #fff;
  color: #242c3f;
  box-shadow: 0 0.25rem 0.75rem rgba(34, 41, 63, 0.1);
}

.canvas-toolbar button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.canvas-toolbar button svg {
  font-size: 1rem;
}

.canvas-toolbar button svg {
  width: 0.9375rem;
  height: 0.9375rem;
  stroke-width: 1.75;
}

.toolbar-zoom-wrap {
  position: relative;
  display: inline-flex;
}

.canvas-toolbar span {
  padding: 0 0.5rem;
  font-weight: 600;
}

.canvas-toolbar .toolbar-zoom {
  width: auto;
  min-width: 3.875rem;
  padding: 0 0.625rem;
  border: 1px solid rgba(226, 232, 240, 0.96);
  background: #f8fbff;
  font-weight: 800;
}

.canvas-zoom-menu {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 0.625rem);
  width: 5.75rem;
  padding: 0.375rem;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 0.625rem;
  background: #fff;
  box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.16);
  transform: translateX(-50%);
}

.canvas-zoom-menu button {
  width: 100%;
  height: 1.875rem;
  justify-content: flex-start;
  padding: 0 0.625rem;
  border-color: transparent;
  background: transparent;
  font-size: 0.8125rem;
  font-weight: 700;
}

.canvas-zoom-menu button.active {
  border-color: rgba(37, 99, 235, 0.18);
  background: #eff6ff;
  color: #2563eb;
}

.canvas-toolbar .toolbar-add-node {
  width: auto;
  min-width: 6.5rem;
  gap: 0.375rem;
  padding: 0 0.75rem;
  border-color: rgba(85, 88, 232, 0.16);
  border-radius: 0.5rem;
  background: #5558e8;
  color: #fff;
}

.canvas-toolbar .toolbar-add-node:hover:not(:disabled) {
  border-color: #5558e8;
  background: #474bd9;
  color: #fff;
}

.canvas-toolbar .toolbar-run {
  width: auto;
  min-width: 5.875rem;
  gap: 0.375rem;
  padding: 0 0.75rem;
  border-color: rgba(34, 197, 94, 0.18);
  border-radius: 0.5rem;
  background: #22c55e;
  color: #fff;
}

.canvas-toolbar .toolbar-run:hover:not(:disabled) {
  border-color: #16a34a;
  background: #16a34a;
  color: #fff;
}

.canvas-toolbar .toolbar-add-node span,
.canvas-toolbar .toolbar-run span {
  padding: 0;
  font-size: 0.8125rem;
  font-weight: 700;
}

@media (max-width: 980px) {
  .workflow-canvas-page {
    min-height: 40rem;
  }

  .canvas-mode-tabs,
  .canvas-actions {
    display: none;
  }

  .canvas-workbench {
    grid-template-columns: var(--workflow-resource-panel-width) minmax(0, 1fr);
  }

  .canvas-workbench.resource-collapsed {
    grid-template-columns: 0 minmax(0, 1fr);
  }

  .canvas-open-surface,
  .canvas-stage-shell {
    grid-column: 2;
  }

  .canvas-resource-panel {
    position: relative;
    z-index: 1;
    width: auto;
    max-width: none;
    box-shadow: none;
  }

  .resource-panel-toggle {
    display: inline-flex;
    left: var(--workflow-resource-panel-width);
  }

  .workflow-canvas-page.has-right-panel .canvas-toolbar,
  .workflow-canvas-page.has-node-test-drawer .canvas-toolbar {
    gap: 0.375rem;
    padding: 0 0.5rem;
  }

  .workflow-canvas-page.has-right-panel .canvas-toolbar .toolbar-add-node,
  .workflow-canvas-page.has-right-panel .canvas-toolbar .toolbar-run,
  .workflow-canvas-page.has-node-test-drawer .canvas-toolbar .toolbar-add-node,
  .workflow-canvas-page.has-node-test-drawer .canvas-toolbar .toolbar-run {
    width: 2rem;
    min-width: 2rem;
    gap: 0;
    padding: 0;
  }

  .workflow-canvas-page.has-right-panel .canvas-toolbar .toolbar-add-node span,
  .workflow-canvas-page.has-right-panel .canvas-toolbar .toolbar-run span,
  .workflow-canvas-page.has-node-test-drawer .canvas-toolbar .toolbar-add-node span,
  .workflow-canvas-page.has-node-test-drawer .canvas-toolbar .toolbar-run span {
    display: none;
  }

  .coze-node {
    width: 21.25rem;
  }
}
</style>
