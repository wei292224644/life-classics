import { NavLink, useLocation } from 'react-router-dom'

interface TabNavProps {
  onClearChat?: () => void
}

export function TabNav({ onClearChat }: TabNavProps) {
  const location = useLocation()
  const isChat = location.pathname === '/chat'

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 text-sm border-b-2 transition-colors ${
      isActive
        ? 'border-purple-600 text-foreground font-medium'
        : 'border-transparent text-muted-foreground hover:text-foreground'
    }`

  return (
    <nav className="flex items-center border-b border-border shrink-0 bg-card px-2">
      <NavLink end to="/chunks" className={linkClass}>Chunks</NavLink>
      <NavLink end to="/upload" className={linkClass}>上传</NavLink>
      <NavLink end to="/chat" className={linkClass}>对话</NavLink>
      {isChat && onClearChat && (
        <button
          onClick={onClearChat}
          className="ml-auto mr-2 text-xs text-muted-foreground hover:text-foreground border border-border rounded px-2 py-1"
        >
          清空对话
        </button>
      )}
    </nav>
  )
}
