// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import {
  describeEvalSetCard,
  describeEvalSetVersionState,
  displayEvalSetFieldLabel,
  normalizeCaseTags,
  normalizeFieldDrafts,
} from './evalSetViewModel'

describe('eval set view model', () => {
  it('describes case count and visible tags for manual regression cases', () => {
    expect(describeEvalSetCard({ caseCount: 0 })).toEqual({
      caseCountText: '0 条用例',
      tone: 'empty',
    })
    expect(describeEvalSetCard({ caseCount: 3 })).toEqual({
      caseCountText: '3 条用例',
      tone: 'ready',
    })
    expect(normalizeCaseTags([' refund ', '', 'policy', 'refund'])).toEqual(['refund', 'policy'])
  })

  it('keeps system field keys stable while showing Chinese labels', () => {
    expect(displayEvalSetFieldLabel({ key: 'input', label: 'Input' })).toBe('输入')
    expect(displayEvalSetFieldLabel({ key: 'expectedOutput', label: 'Expected output' })).toBe('期望输出')
    expect(displayEvalSetFieldLabel({ key: 'reference', label: 'Reference' })).toBe('Reference')
  })

  it('describes draft and submitted eval set version state', () => {
    expect(describeEvalSetVersionState({ latestVersion: '', draftChanged: true })).toEqual({
      label: '草稿',
      tone: 'draft',
      submitDisabled: false,
    })
    expect(describeEvalSetVersionState({ latestVersion: '0.0.1', draftChanged: false })).toEqual({
      label: 'v0.0.1',
      tone: 'version',
      submitDisabled: true,
    })
    expect(describeEvalSetVersionState({ latestVersion: '0.0.1', draftChanged: true })).toEqual({
      label: 'v0.0.1 后有草稿变更',
      tone: 'dirty',
      submitDisabled: false,
    })
  })

  it('normalizes editable eval set field drafts', () => {
    expect(normalizeFieldDrafts([
      { key: ' reference_output ', label: ' Reference ', contentType: 'text', required: true, displayOrder: 4 },
    ])).toEqual([
      { key: 'reference_output', label: 'Reference', contentType: 'TEXT', required: true, displayOrder: 1 },
    ])
  })
})
