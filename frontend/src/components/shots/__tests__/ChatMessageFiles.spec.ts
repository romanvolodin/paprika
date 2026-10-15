import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessageFiles from '@/components/shots/ChatMessageFiles.vue'
import type { AttachmentOut, VersionOut } from '@/types/api'

function attachment(id: number, filename: string, contentType: string, size = 2048): AttachmentOut {
  return {
    id,
    url: `http://localhost/media/${filename}`,
    filename,
    size,
    content_type: contentType,
  }
}

function version(id: number, overrides: Partial<VersionOut> = {}): VersionOut {
  return {
    id,
    project_id: 1,
    shot_id: 10,
    name: `PRJ_0010_v0${id}`,
    type: 'video',
    source: `http://localhost/media/v${id}.mp4`,
    converted: null,
    thumb: `http://localhost/media/v${id}.jpg`,
    width: 1920,
    height: 1080,
    duration: 240,
    fps: 24,
    codec: 'h264',
    file_size: 1024,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('ChatMessageFiles', () => {
  it('renders nothing for a message without files or versions', () => {
    const wrapper = mount(ChatMessageFiles, { props: { attachments: [], versions: [] } })

    expect(wrapper.find('.chat-files').exists()).toBe(false)
  })

  it('shows an image attachment as a thumbnail that opens in a new tab', () => {
    const wrapper = mount(ChatMessageFiles, {
      props: { attachments: [attachment(1, 'shot.png', 'image/png')], versions: [] },
    })

    const link = wrapper.find('a.chat-files__image')
    expect(link.attributes('href')).toBe('http://localhost/media/shot.png')
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toContain('noopener')
    expect(link.find('img').attributes('src')).toBe('http://localhost/media/shot.png')
  })

  it('shows any other attachment as a link with its name and size', () => {
    const wrapper = mount(ChatMessageFiles, {
      props: {
        attachments: [attachment(2, 'notes.pdf', 'application/pdf', 5 * 1024 * 1024)],
        versions: [],
      },
    })

    const link = wrapper.find('a.chat-files__file')
    expect(link.attributes('href')).toBe('http://localhost/media/notes.pdf')
    expect(link.text().replace(/\s/g, ' ')).toBe('notes.pdf · 5 МБ')
    expect(wrapper.find('.chat-files__image').exists()).toBe(false)
  })

  it('keeps images and other files apart', () => {
    const wrapper = mount(ChatMessageFiles, {
      props: {
        attachments: [
          attachment(1, 'a.png', 'image/png'),
          attachment(2, 'b.zip', 'application/zip'),
          attachment(3, 'c.jpg', 'image/jpeg'),
        ],
        versions: [],
      },
    })

    expect(wrapper.findAll('.chat-files__image')).toHaveLength(2)
    expect(wrapper.findAll('.chat-files__file')).toHaveLength(1)
  })

  it('shows a linked version as a card with its thumbnail and name', () => {
    const wrapper = mount(ChatMessageFiles, { props: { attachments: [], versions: [version(2)] } })

    const card = wrapper.find('a.chat-files__version')
    expect(card.text()).toContain('PRJ_0010_v02')
    expect(card.find('img').attributes('src')).toBe('http://localhost/media/v2.jpg')
    expect(card.attributes('target')).toBe('_blank')
  })

  it('opens the converted file of a version when there is one, else the source', () => {
    const wrapper = mount(ChatMessageFiles, {
      props: {
        attachments: [],
        versions: [
          version(1, { converted: 'http://localhost/media/v1-proxy.mp4' }),
          version(2, { converted: null }),
        ],
      },
    })

    const hrefs = wrapper.findAll('a.chat-files__version').map((link) => link.attributes('href'))
    expect(hrefs).toEqual(['http://localhost/media/v1-proxy.mp4', 'http://localhost/media/v2.mp4'])
  })

  it('shows a placeholder when a version has no thumbnail', () => {
    const wrapper = mount(ChatMessageFiles, {
      props: { attachments: [], versions: [version(1, { thumb: null })] },
    })

    expect(wrapper.find('.chat-files__version img').exists()).toBe(false)
    expect(wrapper.find('.chat-files__version-thumb').exists()).toBe(true)
  })
})
