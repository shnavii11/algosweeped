import { describe, it, expect } from 'vitest'
import { computeOverall } from '../OverallProgress'

describe('computeOverall', () => {
  it('averages the platform sub-score and the sheet pct, then rounds', () => {
    expect(computeOverall(60, 40)).toBe(50)
    expect(computeOverall(75, 50)).toBe(63) // 62.5 → 63
    expect(computeOverall(0, 0)).toBe(0)
    expect(computeOverall(100, 100)).toBe(100)
  })

  it('clamps to [0, 100]', () => {
    expect(computeOverall(-20, 0)).toBe(0)
    expect(computeOverall(150, 150)).toBe(100)
  })
})
