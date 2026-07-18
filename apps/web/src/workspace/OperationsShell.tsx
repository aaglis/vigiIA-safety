import { Outlet } from '@tanstack/react-router'
import { OperationsProvider, type OperationsContextValue } from '../pages/authenticated/operations/OperationsContext'

export function OperationsShell({ value }: { value: OperationsContextValue }) {
  return (
    <OperationsProvider value={value}>
      <Outlet />
    </OperationsProvider>
  )
}
