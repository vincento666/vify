import { describe, expect, it } from 'vitest'

import type { AiAssistantEvent } from '@/api/aiAssistant'
import { buildAiAssistantTimeline } from './aiAssistantTimeline'

describe('ai assistant execution timeline', () => {
  it('maps durable run events into visible Codex-style execution cards', () => {
    const events: AiAssistantEvent[] = [
      {
        id: 1,
        sessionId: 1,
        runId: 2,
        sequence: 1,
        type: 'run.started',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: 'Run started',
        visibleSummary: 'The assistant run started.',
        payload: {},
        createdAt: '2026-06-17T10:00:00',
      },
      {
        id: 2,
        sessionId: 1,
        runId: 2,
        sequence: 2,
        type: 'model.stream_chunk',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: '模型输出',
        visibleSummary: '我先读取文件。',
        payload: { chunk: '我先读取文件。', streaming: true },
        createdAt: '2026-06-17T10:00:01',
      },
      {
        id: 3,
        sessionId: 1,
        runId: 2,
        sequence: 3,
        type: 'tool.call_output',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: 'Tool output',
        visibleSummary: 'long output',
        payload: { output: { echo: 'hello' } },
        createdAt: '2026-06-17T10:00:02',
      },
      {
        id: 4,
        sessionId: 1,
        runId: 2,
        sequence: 4,
        type: 'approval.required',
        level: 'info',
        status: 'WAITING',
        visibleTitle: 'Approval required',
        visibleSummary: 'update_customer_profile requires approval.',
        payload: { approvalId: 9, riskLevel: 'BUSINESS_WRITE' },
        createdAt: '2026-06-17T10:00:03',
      },
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual(['model-output', 'tool'])
    expect(timeline[0].summary).toBe('我先读取文件。')
    expect(timeline[1].title).toBe('工具调用')
    expect(timeline[1].details).toEqual([])
    expect(timeline[1].toolInvocations?.[0].title).toBe('工具调用')
    expect(timeline[1].toolInvocations?.[0].outputRows).toContainEqual(
      expect.objectContaining({ label: '工具调用 · 已完成', value: '输出：hello' }),
    )
    expect(timeline.some((item) => item.approvalId === 9)).toBe(false)
  })

  it('assembles consecutive model stream chunks into one visible model output message', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'run.started', '运行开始', 'started', {}),
      event(2, 'model.stream_chunk', '流式输出', '我先', { chunk: '我先', streaming: true }),
      event(3, 'model.stream_chunk', '流式输出', '读取', { chunk: '读取', streaming: true }),
      event(4, 'model.stream_chunk', '流式输出', '文件。', { chunk: '文件。', streaming: true }),
      event(5, 'tool.call_output', '工具输出', 'AGENTS.md', { toolName: 'read_workspace_file', output: { path: 'AGENTS.md' } }),
      event(6, 'model.stream_chunk', '模型输出', '最终', {
        chunk: '最终',
        phase: 'final_answer',
        streaming: true,
      }),
      event(7, 'model.stream_chunk', '模型输出', '回答。', {
        chunk: '回答。',
        phase: 'final_answer',
        streaming: true,
      }),
      event(8, 'approval.required', '需要审批', '写入需要审批。', { approvalId: 9 }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual([
      'model-output',
      'file',
      'model-output',
    ])
    expect(timeline[0].summary).toBe('我先读取文件。')
    expect(timeline[0].phase).toBeUndefined()
    expect(timeline[0].payloadPreview).toContain('"chunkCount":3')
    expect(timeline[2].summary).toBe('最终回答。')
    expect(timeline[2].sequence).toBe(6)
    expect(timeline[2].phase).toBe('final_answer')
    expect(timeline.some((item) => item.approvalId === 9)).toBe(false)
  })

  it('carries stream phase and source metadata for final answer placement', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.stream_chunk', '模型输出', '最终', {
        chunk: '最终',
        phase: 'final_answer',
        source: 'harness_final_answer',
      }),
      event(2, 'model.stream_chunk', '模型输出', '回答', {
        chunk: '回答',
        phase: 'final_answer',
        source: 'harness_final_answer',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0]).toMatchObject({
      kind: 'model-output',
      summary: '最终回答',
      phase: 'final_answer',
      source: 'harness_final_answer',
    })
  })

  it('deduplicates thought summaries that repeat the visible model output', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.stream_chunk', '模型输出', '我会先读取文件。', { chunk: '我会先读取文件。' }),
      event(2, 'model.thought_summary', '思考摘要', '我会先读取文件。', {
        summary: '我会先读取文件。',
      }),
      event(3, 'model.thought_summary', '思考摘要', '需要比对配置和测试结果。', {
        summary: '需要比对配置和测试结果。',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual(['model-output', 'model-thought'])
    expect(timeline[1].title).toBe('思考过程')
    expect(timeline[1].summary).toBe('需要比对配置和测试结果。')
  })

  it('deduplicates thought summaries that arrive immediately before the same stream output', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.thought_summary', '思考摘要', '已根据请求规划工具调用。', {
        summary: '已根据请求规划工具调用。',
      }),
      event(2, 'model.stream_chunk', '模型输出', '已根据请求', { chunk: '已根据请求' }),
      event(3, 'model.stream_chunk', '模型输出', '规划工具调用。', { chunk: '规划工具调用。' }),
      event(4, 'model.tool_call_decision', '工具调用决策', '模型已选择工具调用。', {
        toolNames: ['read_workspace_file'],
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual(['model-output'])
    expect(timeline[0].summary).toBe('已根据请求规划工具调用。')
  })

  it('normalizes duplicated model stream fragments before rendering model text', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.stream_chunk', '模型输出', '用户用户要求我要求我', {
        chunk: '用户用户要求我要求我',
      }),
      event(2, 'model.stream_chunk', '模型输出', '执行一个复杂执行一个复杂验收任务验收任务。', {
        chunk: '执行一个复杂执行一个复杂验收任务验收任务。',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0].kind).toBe('model-output')
    expect(timeline[0].summary).toBe('用户要求我执行一个复杂验收任务。')
    expect(timeline[0].details[1].value).toBe('用户要求我执行一个复杂验收任务。')
  })

  it('keeps only one foldable tool result with readable input and output details', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'tool.call_started', '工具开始', '读取工作区文件 已开始执行。', {
        toolName: 'read_workspace_file',
        input: { path: 'AGENTS.md' },
      }),
      event(2, 'tool.call_output', '工具输出', 'project instructions', {
        toolName: 'read_workspace_file',
        output: { text: 'project instructions' },
      }),
      event(3, 'tool.call_completed', '工具完成', '读取工作区文件 已完成。', {
        toolName: 'read_workspace_file',
        status: 'OK',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0].kind).toBe('file')
    expect(timeline[0].title).toBe('已读取 1 个文件')
    expect(timeline[0].tone).toBe('success')
    expect(timeline[0].details).toContainEqual(
      expect.objectContaining({ label: '输入', value: expect.stringContaining('路径：AGENTS.md') }),
    )
    expect(timeline[0].details).toContainEqual(
      expect.objectContaining({ label: '结果', value: expect.stringContaining('内容预览：project instructions') }),
    )
    expect(timeline[0].toolInvocations).toBeUndefined()
  })

  it('summarizes multiple low-level tool calls into one foldable tool echo item', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.thought_summary', '思考摘要', '需要读取规范、检索知识库并写入校验文件。', {}),
      event(2, 'tool.call_started', '工具开始', '读取工作区文件 已开始。', {
        toolName: 'read_workspace_file',
        input: { path: 'specs/README.md' },
      }),
      event(3, 'tool.call_output', '工具输出', '规范索引', {
        toolName: 'read_workspace_file',
        output: { content: '规范索引' },
      }),
      event(4, 'tool.call_completed', '工具完成', '读取工作区文件 已完成。', {
        toolName: 'read_workspace_file',
        status: 'OK',
      }),
      event(5, 'tool.call_output', '工具输出', '知识库结果', {
        toolName: 'search_knowledge_base',
        input: { query: '退票规则 harness 规则' },
        output: { query: '退票规则 harness 规则', hits: [] },
      }),
      event(6, 'tool.call_output', '工具输出', '写入结果', {
        toolName: 'write_workspace_file',
        input: { path: 'tmp/ai-assistant-fuzzy-uat-2.md', content: '三段式中文校验记录' },
        output: { path: 'tmp/ai-assistant-fuzzy-uat-2.md', bytes: 36 },
      }),
      event(7, 'tool.call_output', '工具输出', '回读内容', {
        toolName: 'read_workspace_file',
        input: { path: 'tmp/ai-assistant-fuzzy-uat-2.md' },
        output: { content: '三段式中文校验记录' },
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.title)).toEqual([
      '思考过程',
      '已读取 1 个文件',
      '工具调用',
      '已编辑 1 个文件',
      '已读取 1 个文件',
    ])
    expect(timeline.filter((item) => item.title === '工具调用')).toHaveLength(1)
    expect(timeline[1]).toMatchObject({
      kind: 'file',
      title: '已读取 1 个文件',
      tone: 'success',
    })
    expect(timeline[1].details[1].value).toContain('内容预览：规范索引')
    expect(timeline[2].tone).toBe('success')
    expect(timeline[2].summary).toBe('已汇总 1 次工具调用')
    expect(timeline[2].details).toEqual([])
    expect(timeline[2].toolInvocations).toHaveLength(1)
    expect(timeline[2].toolInvocations?.[0]).toMatchObject({
      title: '知识库检索',
      subtitle: '退票规则 harness 规则',
      statusText: '已完成',
    })
    expect(timeline[2].toolInvocations?.[0].inputRows).toContainEqual(
      expect.objectContaining({
        label: '调用工具',
        value: expect.stringContaining('知识库检索：退票规则 harness 规则'),
      }),
    )
    expect(timeline[2].toolInvocations?.[0].inputRows).toContainEqual(
      expect.objectContaining({
        label: '知识库检索 · 退票规则 harness 规则',
        value: expect.stringContaining('查询：退票规则 harness 规则'),
      }),
    )
    expect(timeline[3]).toMatchObject({ kind: 'file', title: '已编辑 1 个文件' })
    expect(timeline[3].details).toContainEqual(
      expect.objectContaining({
        label: '结果',
        value: expect.stringContaining('结果：已写入 tmp/ai-assistant-fuzzy-uat-2.md（36 bytes）'),
      }),
    )
    expect(JSON.stringify(timeline)).not.toContain('skill=')
  })

  it('builds one product-grade summarized invocation instead of many raw tool blocks', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.thought_summary', '思考摘要', '需要读取规范、检索知识库、使用技能并写入校验文件。', {}),
      event(2, 'tool.call_output', '工具输出', '规范索引', {
        toolName: 'read_workspace_file',
        input: { path: 'specs/README.md' },
        output: { path: 'specs/README.md', content: '规范索引正文'.repeat(80), truncated: false },
      }),
      event(3, 'tool.call_output', '工具输出', '知识库结果', {
        toolName: 'search_knowledge_base',
        input: { query: '退票规则 harness 规则' },
        output: { query: '退票规则 harness 规则', hits: [] },
      }),
      event(4, 'tool.call_output', '工具输出', '技能结果', {
        toolName: 'invoke_skill',
        input: { skillName: 'tdd', instruction: '按红绿重构整理风险和证据' },
        output: { skillName: 'tdd', instruction: '按红绿重构整理风险和证据', status: 'RECORDED' },
      }),
      event(5, 'tool.call_output', '工具输出', '写入结果', {
        toolName: 'write_workspace_file',
        input: { path: 'tmp/ai-assistant-fuzzy-uat-2.md', content: '三段式中文校验记录' },
        output: { path: 'tmp/ai-assistant-fuzzy-uat-2.md', bytes: 36 },
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)
    const readItem = timeline[1]
    const toolItem = timeline[2]
    const writeItem = timeline[3]

    expect(timeline.map((item) => item.title)).toEqual([
      '思考过程',
      '已读取 1 个文件',
      '工具调用',
      '已编辑 1 个文件',
    ])
    expect(readItem.kind).toBe('file')
    expect(readItem.details[1].value).toContain('内容预览：规范索引正文')
    expect(readItem.details[0].value).toBe('路径：specs/README.md')
    expect(readItem.details[0].value).not.toContain('读取：specs/README.md')
    expect(readItem.details[1].value).not.toContain('读取：specs/README.md')
    expect(toolItem.details).toEqual([])
    expect(toolItem.toolInvocations).toHaveLength(1)
    expect(toolItem.toolInvocations?.[0]).toMatchObject({
      title: '知识库检索、使用技能',
      subtitle: '2 个工具',
      statusText: '已完成',
      tone: 'success',
    })
    expect(toolItem.toolInvocations?.[0].inputRows).toContainEqual({
      label: '调用工具',
      value: expect.stringContaining('使用技能：tdd'),
      monospace: true,
    })
    expect(toolItem.toolInvocations?.[0].inputRows).toContainEqual(
      expect.objectContaining({
        label: '使用技能 · tdd',
        value: '技能：tdd\n说明：按红绿重构整理风险和证据',
      }),
    )
    expect(toolItem.toolInvocations?.[0].outputRows).toContainEqual(
      expect.objectContaining({
        label: '知识库检索 · 退票规则 harness 规则',
        value: '结果：命中 0 条',
      }),
    )
    expect(toolItem.toolInvocations?.[0].outputRows).toContainEqual(
      expect.objectContaining({
        label: '使用技能 · tdd',
        value: '结果：已记录技能意图\n说明：按红绿重构整理风险和证据',
      }),
    )
    expect(writeItem.kind).toBe('file')
    expect(writeItem.details[0].value).toBe('路径：tmp/ai-assistant-fuzzy-uat-2.md\n内容预览：三段式中文校验记录')
    expect(writeItem.details[1].value).toContain('结果：已写入 tmp/ai-assistant-fuzzy-uat-2.md（36 bytes）')
    expect(writeItem.details[0].value).not.toContain('编辑：tmp/ai-assistant-fuzzy-uat-2.md')
    expect(writeItem.details[1].value).not.toContain('编辑：tmp/ai-assistant-fuzzy-uat-2.md')
    expect(JSON.stringify(toolItem.toolInvocations)).not.toContain('skill=tdd')
    expect(JSON.stringify(toolItem.toolInvocations)).not.toContain('技能调用')
  })

  it('keeps a single summarized tool echo item running while outputs are pending', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'tool.call_started', '工具开始', '读取工作区文件 已开始。', {
        toolName: 'read_workspace_file',
        input: { path: 'specs/README.md' },
      }),
      event(2, 'tool.call_started', '工具开始', '知识库检索 已开始。', {
        toolName: 'search_knowledge_base',
        input: { query: 'harness 规则' },
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(2)
    expect(timeline[0]).toMatchObject({
      kind: 'file',
      title: '已读取 1 个文件',
      tone: 'running',
    })
    expect(timeline[0].details[1].value).toContain('结果：等待结果')
    expect(timeline[1]).toMatchObject({
      kind: 'tool',
      title: '工具调用',
      tone: 'running',
      summary: '已汇总 1 次工具调用',
    })
    expect(timeline[1].toolInvocations).toHaveLength(1)
    expect(timeline[1].toolInvocations?.[0].statusText).toBe('运行中')
    expect(timeline[1].toolInvocations?.[0].outputRows).toContainEqual(
      expect.objectContaining({ label: '知识库检索 · harness 规则', value: '结果：等待结果' }),
    )
  })

  it('merges completed events back into the active tool group when only completion has a tool call id', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'tool.call_started', '工具开始', '写入工作区文件 已开始。', {
        toolName: 'write_workspace_file',
        input: { path: 'tmp/merged-tool.md', content: 'ok' },
      }),
      event(2, 'tool.call_output', '工具输出', '写入结果', {
        toolName: 'write_workspace_file',
        output: { path: 'tmp/merged-tool.md', bytes: 2 },
      }),
      {
        ...event(3, 'tool.call_completed', '工具完成', '写入工作区文件 已完成。', {
          toolName: 'write_workspace_file',
          status: 'COMPLETED',
        }),
        toolCallId: 99,
      },
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0]).toMatchObject({
      kind: 'file',
      title: '已编辑 1 个文件',
      summary: '已编辑 1 个文件',
    })
    expect(timeline[0].details).toContainEqual(
      expect.objectContaining({ label: '输入', value: expect.stringContaining('路径：tmp/merged-tool.md') }),
    )
    expect(timeline[0].details).toContainEqual(
      expect.objectContaining({ label: '结果', value: expect.stringContaining('结果：已写入 tmp/merged-tool.md（2 bytes）') }),
    )
    expect(JSON.stringify(timeline[0].details)).not.toContain('等待结果')
  })

  it('renders completed empty tool outputs from status instead of a pending placeholder', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'tool.call_started', '工具开始', '读取工作区文件 已开始。', {
        toolName: 'read_workspace_file',
        input: { path: 'tmp/missing.md' },
      }),
      event(2, 'tool.call_output', '工具输出', '', {
        toolName: 'read_workspace_file',
        output: { path: 'tmp/missing.md', content: '' },
      }),
      event(3, 'tool.call_completed', '工具完成', '读取工作区文件 未找到。', {
        toolName: 'read_workspace_file',
        status: 'NOT_FOUND',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline[0].tone).toBe('success')
    expect(timeline[0]).toMatchObject({ kind: 'file', title: '已读取 1 个文件' })
    expect(timeline[0].details[1].value).toContain('结果：未找到 tmp/missing.md')
    expect(JSON.stringify(timeline[0].details)).not.toContain('等待结果')
  })

  it('deduplicates repeated file detail rows when the same path is read more than once', () => {
    const events: AiAssistantEvent[] = [
      {
        ...event(1, 'tool.call_started', '工具开始', 'first read started', {
          toolName: 'read_workspace_file',
          input: { path: 'tmp/repeated.md' },
        }),
        toolCallId: 101,
      },
      {
        ...event(2, 'tool.call_output', '工具输出', 'first read', {
          toolName: 'read_workspace_file',
          input: { path: 'tmp/repeated.md' },
          output: { path: 'tmp/repeated.md', content: '重复内容' },
        }),
        toolCallId: 101,
      },
      {
        ...event(3, 'tool.call_completed', '工具完成', 'first read done', {
          toolName: 'read_workspace_file',
          status: 'COMPLETED',
        }),
        toolCallId: 101,
      },
      {
        ...event(4, 'tool.call_started', '工具开始', 'second read started', {
          toolName: 'read_workspace_file',
          input: { path: 'tmp/repeated.md' },
        }),
        toolCallId: 102,
      },
      {
        ...event(5, 'tool.call_output', '工具输出', 'second read', {
          toolName: 'read_workspace_file',
          input: { path: 'tmp/repeated.md' },
          output: { path: 'tmp/repeated.md', content: '重复内容' },
        }),
        toolCallId: 102,
      },
      {
        ...event(6, 'tool.call_completed', '工具完成', 'second read done', {
          toolName: 'read_workspace_file',
          status: 'COMPLETED',
        }),
        toolCallId: 102,
      },
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0]).toMatchObject({ kind: 'file', title: '已读取 1 个文件' })
    expect(timeline[0].details).toContainEqual({ label: '输入', value: '路径：tmp/repeated.md', monospace: true })
    expect(timeline[0].details).toContainEqual({
      label: '结果',
      value: '结果：已读取 tmp/repeated.md\n内容预览：重复内容',
      monospace: true,
    })
  })

  it('renders only supported execution echo event categories in processed groups', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'run.started', '运行开始', 'started', {}),
      event(2, 'task.updated', '任务规划', '低层事件不展示', { toolNames: ['read_workspace_file'] }),
      event(3, 'model.tool_call_decision', '工具决策', '低层事件不展示', { toolNames: ['read_workspace_file'] }),
      event(4, 'model.thought_summary', '思考摘要', '先读取再写入。', {}),
      event(5, 'tool.call_output', '工具输出', 'content', {
        toolName: 'read_workspace_file',
        output: { content: '文件正文' },
      }),
      event(6, 'approval.approved', '审批', 'operator-ui 已批准 写入工作区文件。', {
        approvalId: 11,
        toolName: 'write_workspace_file',
      }),
      event(7, 'run.completed', '完成', 'done', {}),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.title)).toEqual(['思考过程', '已读取 1 个文件', '审批通过'])
    expect(timeline.map((item) => item.kind)).toEqual(['model-thought', 'file', 'approval'])
    expect(timeline[1].details).toContainEqual(
      expect.objectContaining({ label: '结果', value: expect.stringContaining('内容预览：文件正文') }),
    )
    expect(timeline[2].details).toEqual([{ label: '内容', value: 'operator-ui 已批准 写入工作区文件。' }])
  })

  it('renders shell commands as command-titled fold items with a single shell result block', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'tool.call_started', '工具开始', 'start', {
        toolName: 'run_shell',
        input: { command: 'node tmp/demo.mjs' },
      }),
      event(2, 'tool.call_output', '工具输出', 'ok', {
        toolName: 'run_shell',
        input: { command: 'node tmp/demo.mjs' },
        output: { stdout: 'created tmp/demo.txt\nread tmp/demo.txt' },
      }),
      event(3, 'tool.call_completed', '工具完成', 'done', {
        toolName: 'run_shell',
        status: 'COMPLETED',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0].title).toBe('已运行 1 条命令')
    const invocation = timeline[0].toolInvocations?.[0]
    expect(invocation).toMatchObject({
      title: 'node tmp/demo.mjs',
      subtitle: '',
      statusText: '已完成',
      displayMode: 'shell',
      shellCommand: 'node tmp/demo.mjs',
      shellOutput: 'created tmp/demo.txt\nread tmp/demo.txt',
      shellCopyText: '$ node tmp/demo.mjs\n\ncreated tmp/demo.txt\nread tmp/demo.txt',
    })
    expect(invocation?.inputRows).toEqual([])
    expect(invocation?.outputRows).toEqual([])
    expect(JSON.stringify(timeline)).not.toContain('终端命令')
    expect(JSON.stringify(timeline)).not.toContain('调用工具')
  })
})

function event(
  sequence: number,
  type: string,
  visibleTitle: string,
  visibleSummary: string,
  payload: Record<string, unknown>,
): AiAssistantEvent {
  return {
    id: sequence,
    sessionId: 1,
    runId: 2,
    sequence,
    type,
    level: 'info',
    status: type === 'approval.required' ? 'WAITING' : 'COMPLETED',
    visibleTitle,
    visibleSummary,
    payload,
    createdAt: '2026-06-17T10:00:00',
  }
}
