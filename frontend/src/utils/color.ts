import type { TagProps } from 'naive-ui'

/** Tag colors for an entity's `#rrggbb` color: tinted fill, solid border and text. */
export function tagColor(color: string): NonNullable<TagProps['color']> {
  return { color: `${color}26`, borderColor: color, textColor: color }
}
