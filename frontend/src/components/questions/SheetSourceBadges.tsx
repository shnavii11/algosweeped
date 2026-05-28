import Badge from '../ui/Badge'

interface Props {
  sourceSheets: string[]
}

const SHEET_LABELS: Record<string, string> = {
  neetcode_150: 'NC150',
  blind75: 'B75',
  grind_169: 'G169',
  lc_top_interview_150: 'TI150',
  striver_a2z: 'A2Z',
}

export default function SheetSourceBadges({ sourceSheets }: Props) {
  if (!sourceSheets.length) return null
  return (
    <div className="flex flex-wrap gap-1">
      {sourceSheets.map((s) => (
        <Badge key={s} variant="gray" className="text-[10px]">
          {SHEET_LABELS[s] || s}
        </Badge>
      ))}
    </div>
  )
}
