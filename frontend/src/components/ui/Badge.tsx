import clsx from 'clsx'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'easy' | 'medium' | 'hard' | 'blue' | 'gray'
  className?: string
}

const variants = {
  default: 'bg-gray-700 text-gray-300',
  easy: 'bg-green-900/50 text-green-400 border border-green-800',
  medium: 'bg-yellow-900/50 text-yellow-400 border border-yellow-800',
  hard: 'bg-red-900/50 text-red-400 border border-red-800',
  blue: 'bg-blue-900/50 text-blue-400 border border-blue-800',
  gray: 'bg-gray-800 text-gray-400',
}

export default function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', variants[variant], className)}>
      {children}
    </span>
  )
}
