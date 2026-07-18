export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[]
export type JsonObject = { [key: string]: JsonValue }
export type Metadata = JsonObject

export interface PageInfo {
  limit: number
  offset: number
  total: number
  has_next: boolean
}
