export const authenticatedDesignSystemPrimitives = [
  'Button',
  'Modal',
  'PageHeader',
  'TableShell',
  'TextField',
  'SelectField',
  'AsyncPaginatedSelect',
  'StatusBadge',
  'SeverityBadge',
  'PageState',
  'EmptyState',
  'ErrorState',
  'PagePanel',
  'DataCard',
] as const

export type AuthenticatedDesignSystemPrimitive = (typeof authenticatedDesignSystemPrimitives)[number]
