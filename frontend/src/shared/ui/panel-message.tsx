interface PanelMessageProps {
  title: string
  description: string
  tone?: 'default' | 'error'
}

const toneClassName = {
  default: 'text-muted-foreground',
  error: 'text-destructive',
}

export function PanelMessage({ title, description, tone = 'default' }: PanelMessageProps) {
  return (
    <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border/70 bg-muted/10 px-6 py-10 text-center">
      <p className="text-base font-medium text-foreground">{title}</p>
      <p className={`max-w-md text-sm leading-6 ${toneClassName[tone]}`}>{description}</p>
    </div>
  )
}
