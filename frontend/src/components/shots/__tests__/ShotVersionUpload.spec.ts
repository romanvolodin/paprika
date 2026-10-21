import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NMessageProvider } from 'naive-ui'
import ShotVersionUpload from '@/components/shots/ShotVersionUpload.vue'
import { useVersionsStore } from '@/stores/versions'
import * as chatApi from '@/api/chat'
import * as tasksApi from '@/api/tasks'
import * as versionsApi from '@/api/versions'
import ShotUploadTasks from '@/components/shots/ShotUploadTasks.vue'
import type { ShotTaskOut, TaskStatusOut, VersionOut } from '@/types/api'

vi.mock('@/api/versions')
vi.mock('@/api/chat')
vi.mock('@/api/tasks')

const created: VersionOut = {
  id: 20,
  project_id: 1,
  shot_id: 10,
  name: 'PRJ_0010_v02',
  type: 'video',
  source: 'http://localhost/media/a.mp4',
  converted: null,
  thumb: null,
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
}

function buildStatus(id: number, name: string, order: number | null): TaskStatusOut {
  return {
    id,
    company_id: 7,
    name,
    color: '#3366cc',
    order,
    is_default: id === 1,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

const taskStatuses = [
  buildStatus(1, 'Не начата', 1),
  buildStatus(2, 'В работе', 2),
  buildStatus(3, 'Готова', 3),
]

function buildShotTask(id: number, overrides: Partial<ShotTaskOut> = {}): ShotTaskOut {
  return {
    id,
    shot_id: 10,
    task: {
      id: id * 10,
      project_id: 1,
      code: `CLN${id}`,
      name: `Task ${id}`,
      description: '',
      type_id: 1,
      shot_ids: [10],
      created_by: null,
      updated_by: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    status_id: 1,
    assignee: null,
    estimated_hours: null,
    actual_hours: null,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function withTasks(...items: ShotTaskOut[]) {
  vi.mocked(tasksApi.listShotTasks).mockResolvedValue({ items } as never)
}

const received: VersionOut[] = []

const Host = defineComponent({
  setup() {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(ShotVersionUpload, {
            shotId: 10,
            projectId: 1,
            companyId: 7,
            onUploaded: (version: VersionOut) => received.push(version),
          }),
      })
  },
})

function chooseFile(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  return input.trigger('change')
}

function submitButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button').find((button) => button.text() === 'Отправить версию')!
}

const video = new File(['x'], 'PRJ_0010_v02.mp4', { type: 'video/mp4' })
const image = new File(['x'], 'frame.PNG', { type: 'image/png' })

describe('ShotVersionUpload', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    received.length = 0
    URL.createObjectURL = vi.fn(() => 'blob:preview')
    URL.revokeObjectURL = vi.fn()
    vi.mocked(tasksApi.listShotTasks).mockResolvedValue({ items: [] } as never)
    vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items: [] } as never)
    vi.mocked(tasksApi.listTaskStatuses).mockResolvedValue({ items: taskStatuses } as never)
    vi.mocked(tasksApi.updateShotTask).mockImplementation(
      async (id, input) => ({ ...buildShotTask(id), ...input }) as ShotTaskOut,
    )
    vi.mocked(versionsApi.listVersions).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })
  })

  it('asks for a file first, with nothing to send yet', () => {
    const wrapper = mount(Host)

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="preview"]').exists()).toBe(false)
    expect(submitButton(wrapper).attributes('disabled')).toBeDefined()
  })

  it('shows a live preview of a chosen video without uploading it', async () => {
    const wrapper = mount(Host)

    await chooseFile(wrapper, video)

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(false)
    expect(wrapper.find('video').attributes('src')).toBe('blob:preview')
    expect(wrapper.find('video').attributes('controls')).toBeDefined()
    expect(wrapper.text()).toContain('PRJ_0010_v02.mp4')
    expect(versionsApi.uploadVersion).not.toHaveBeenCalled()
    expect(submitButton(wrapper).attributes('disabled')).toBeUndefined()
  })

  it('shows a chosen image as a picture, whatever the case of its extension', async () => {
    const wrapper = mount(Host)

    await chooseFile(wrapper, image)

    expect(wrapper.find('video').exists()).toBe(false)
    expect(wrapper.find('img').attributes('src')).toBe('blob:preview')
  })

  it('takes a file dropped on the zone', async () => {
    const wrapper = mount(Host)

    await wrapper.find('[data-test="drop-zone"]').trigger('drop', {
      dataTransfer: { files: [video] },
    })

    expect(wrapper.find('video').exists()).toBe(true)
  })

  it('takes the first of several dropped files', async () => {
    const wrapper = mount(Host)

    await wrapper.find('[data-test="drop-zone"]').trigger('drop', {
      dataTransfer: { files: [image, video] },
    })

    expect(wrapper.find('img').exists()).toBe(true)
    expect(wrapper.find('video').exists()).toBe(false)
  })

  it('refuses a file with an unsupported extension and keeps asking for one', async () => {
    const wrapper = mount(Host)

    await chooseFile(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(true)
    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })

  it('goes back to the choice on a reset and frees the preview', async () => {
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await wrapper.find('button[aria-label="Сбросить файл"]').trigger('click')

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(true)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview')
  })

  it('frees the preview of the earlier file when another one is chosen', async () => {
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)
    await wrapper.find('button[aria-label="Сбросить файл"]').trigger('click')

    await chooseFile(wrapper, image)

    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1)
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2)
  })

  it('frees the preview when the page is left', async () => {
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    wrapper.unmount()

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview')
  })

  it('uploads the chosen file for the shot on send and reports the created version', async () => {
    vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await submitButton(wrapper).trigger('click')
    await flushPromises()

    expect(versionsApi.uploadVersion).toHaveBeenCalledWith(10, video, expect.any(Function))
    expect(received).toEqual([created])
  })

  it('keeps the chosen file when the upload fails, so it can be sent again', async () => {
    vi.mocked(versionsApi.uploadVersion).mockRejectedValue(new Error('boom'))
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await submitButton(wrapper).trigger('click')
    await flushPromises()

    expect(received).toEqual([])
    expect(useVersionsStore().uploadState).toBe('idle')
    expect(wrapper.find('video').exists()).toBe(true)
    expect(submitButton(wrapper).attributes('disabled')).toBeUndefined()
  })

  it('locks the reset and the send button while uploading and shows the processing note', async () => {
    let finish: (version: VersionOut) => void = () => {}
    vi.mocked(versionsApi.uploadVersion).mockImplementation(
      (_id, _file, onProgress) =>
        new Promise((resolve) => {
          onProgress?.(100, 100)
          finish = resolve
        }),
    )
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await submitButton(wrapper).trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('идёт обработка')
    expect(submitButton(wrapper).attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[aria-label="Сбросить файл"]').attributes('disabled')).toBeDefined()

    finish(created)
    await flushPromises()
    expect(wrapper.text()).not.toContain('идёт обработка')
  })

  describe('comment', () => {
    function commentField(wrapper: ReturnType<typeof mount>) {
      return wrapper.find('textarea')
    }

    async function send(wrapper: ReturnType<typeof mount>) {
      await submitButton(wrapper).trigger('click')
      await flushPromises()
    }

    function findButton(wrapper: ReturnType<typeof mount>, label: string) {
      return wrapper.findAll('button').find((button) => button.text() === label)
    }

    it('has a field for the comment', () => {
      const wrapper = mount(Host)

      expect(commentField(wrapper).exists()).toBe(true)
      expect(wrapper.text()).toContain('Комментарий')
    })

    it('sends the comment to the chat of the shot with a link to the new version', async () => {
      vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
      vi.mocked(chatApi.sendMessage).mockResolvedValue({} as never)
      const wrapper = mount(Host)
      await chooseFile(wrapper, video)
      await commentField(wrapper).setValue('  Поправил небо.  ')

      await send(wrapper)

      expect(chatApi.sendMessage).toHaveBeenCalledWith(10, {
        text: 'Поправил небо.',
        version_ids: [created.id],
      })
      expect(received).toEqual([created])
    })

    it('sends no message when there is no comment', async () => {
      vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
      const wrapper = mount(Host)
      await chooseFile(wrapper, video)
      await commentField(wrapper).setValue('   ')

      await send(wrapper)

      expect(chatApi.sendMessage).not.toHaveBeenCalled()
      expect(received).toEqual([created])
    })

    it('does not send the comment when the upload fails', async () => {
      vi.mocked(versionsApi.uploadVersion).mockRejectedValue(new Error('boom'))
      const wrapper = mount(Host)
      await chooseFile(wrapper, video)
      await commentField(wrapper).setValue('Поправил небо.')

      await send(wrapper)

      expect(chatApi.sendMessage).not.toHaveBeenCalled()
      expect((commentField(wrapper).element as HTMLTextAreaElement).value).toBe('Поправил небо.')
    })

    describe('when the comment cannot be sent', () => {
      async function failComment() {
        vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
        vi.mocked(chatApi.sendMessage).mockRejectedValue(new Error('offline'))
        const wrapper = mount(Host)
        await chooseFile(wrapper, video)
        await commentField(wrapper).setValue('Поправил небо.')
        await send(wrapper)
        return wrapper
      }

      it('stays on the page with an error and keeps the text', async () => {
        const wrapper = await failComment()

        expect(received).toEqual([])
        expect(wrapper.text()).toContain('Версия загружена, но комментарий не отправился.')
        expect((commentField(wrapper).element as HTMLTextAreaElement).value).toBe('Поправил небо.')
      })

      it('offers to send only the comment again, not the file', async () => {
        const wrapper = await failComment()

        expect(findButton(wrapper, 'Отправить версию')).toBeUndefined()
        expect(findButton(wrapper, 'Повторить отправку комментария')).toBeDefined()
        expect(
          wrapper.find('button[aria-label="Сбросить файл"]').attributes('disabled'),
        ).toBeDefined()
      })

      it('goes on once the retry succeeds, without uploading the file again', async () => {
        const wrapper = await failComment()
        vi.mocked(chatApi.sendMessage).mockResolvedValue({} as never)

        await findButton(wrapper, 'Повторить отправку комментария')!.trigger('click')
        await flushPromises()

        expect(versionsApi.uploadVersion).toHaveBeenCalledTimes(1)
        expect(chatApi.sendMessage).toHaveBeenCalledTimes(2)
        expect(received).toEqual([created])
      })

      it('sends the edited text on the retry', async () => {
        const wrapper = await failComment()
        vi.mocked(chatApi.sendMessage).mockResolvedValue({} as never)
        await commentField(wrapper).setValue('Поправил небо и тени.')

        await findButton(wrapper, 'Повторить отправку комментария')!.trigger('click')
        await flushPromises()

        expect(chatApi.sendMessage).toHaveBeenLastCalledWith(10, {
          text: 'Поправил небо и тени.',
          version_ids: [created.id],
        })
      })

      it('lets the user go on without the comment', async () => {
        const wrapper = await failComment()

        await findButton(wrapper, 'Перейти к версии без комментария')!.trigger('click')

        expect(received).toEqual([created])
      })
    })
  })

  describe('tasks', () => {
    async function mountWithFile() {
      const wrapper = mount(Host)
      await flushPromises()
      await chooseFile(wrapper, video)
      return wrapper
    }

    function tasksList(wrapper: ReturnType<typeof mount>) {
      return wrapper.findComponent(ShotUploadTasks)
    }

    async function send(wrapper: ReturnType<typeof mount>) {
      await submitButton(wrapper).trigger('click')
      await flushPromises()
    }

    function findButton(wrapper: ReturnType<typeof mount>, label: string) {
      return wrapper.findAll('button').find((button) => button.text() === label)
    }

    beforeEach(() => {
      vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
      vi.mocked(chatApi.sendMessage).mockResolvedValue({} as never)
    })

    it('lists the tasks of the shot with the code and the name', async () => {
      withTasks(buildShotTask(1), buildShotTask(2))
      const wrapper = await mountWithFile()

      const items = wrapper.findAll('.upload-tasks__item')
      expect(items.map((item) => item.find('.upload-tasks__code').text())).toEqual(['CLN1', 'CLN2'])
      expect(items[0].text()).toContain('Task 1')
      expect(items[1].text()).toContain('Task 2')
    })

    it('says so when the shot has no tasks', async () => {
      const wrapper = await mountWithFile()

      expect(wrapper.text()).toContain('На кадре нет задач.')
    })

    it('says so when the tasks cannot be loaded, and still lets the file be sent', async () => {
      vi.mocked(tasksApi.listShotTasks).mockRejectedValue(new Error('offline'))
      const wrapper = await mountWithFile()

      expect(wrapper.text()).toContain('Не удалось загрузить задачи.')
      await send(wrapper)
      expect(received).toEqual([created])
    })

    it('saves nothing while the changes are only made on the page', async () => {
      withTasks(buildShotTask(1))
      const wrapper = await mountWithFile()

      tasksList(wrapper).vm.$emit('status', 1, 3)
      tasksList(wrapper).vm.$emit('hours', 1, 2.5)
      await flushPromises()

      expect(tasksApi.updateShotTask).not.toHaveBeenCalled()
    })

    it('sends no task update when nothing was changed', async () => {
      withTasks(buildShotTask(1))
      const wrapper = await mountWithFile()

      await send(wrapper)

      expect(tasksApi.updateShotTask).not.toHaveBeenCalled()
      expect(received).toEqual([created])
    })

    it('saves only the changed tasks, and only the changed fields, after the upload', async () => {
      withTasks(buildShotTask(1, { actual_hours: 4 }), buildShotTask(2), buildShotTask(3))
      const wrapper = await mountWithFile()
      tasksList(wrapper).vm.$emit('status', 1, 3)
      tasksList(wrapper).vm.$emit('hours', 3, 2.5)
      await flushPromises()

      await send(wrapper)

      expect(tasksApi.updateShotTask).toHaveBeenCalledTimes(2)
      expect(tasksApi.updateShotTask).toHaveBeenCalledWith(1, { status_id: 3 })
      expect(tasksApi.updateShotTask).toHaveBeenCalledWith(3, { actual_hours: 2.5 })
      expect(received).toEqual([created])
    })

    it('sends a cleared hours field as no hours', async () => {
      withTasks(buildShotTask(1, { actual_hours: 4 }))
      const wrapper = await mountWithFile()
      tasksList(wrapper).vm.$emit('hours', 1, null)
      await flushPromises()

      await send(wrapper)

      expect(tasksApi.updateShotTask).toHaveBeenCalledWith(1, { actual_hours: null })
    })

    it('does not count a change that was put back as a change', async () => {
      withTasks(buildShotTask(1))
      const wrapper = await mountWithFile()
      tasksList(wrapper).vm.$emit('status', 1, 3)
      tasksList(wrapper).vm.$emit('status', 1, 1)
      await flushPromises()

      await send(wrapper)

      expect(tasksApi.updateShotTask).not.toHaveBeenCalled()
    })

    it('does not save the tasks when the upload fails', async () => {
      vi.mocked(versionsApi.uploadVersion).mockRejectedValue(new Error('boom'))
      withTasks(buildShotTask(1))
      const wrapper = await mountWithFile()
      tasksList(wrapper).vm.$emit('status', 1, 3)
      await flushPromises()

      await send(wrapper)

      expect(tasksApi.updateShotTask).not.toHaveBeenCalled()
      expect(chatApi.sendMessage).not.toHaveBeenCalled()
    })

    it('saves the tasks before the comment is sent', async () => {
      const order: string[] = []
      vi.mocked(tasksApi.updateShotTask).mockImplementation(async (id, input) => {
        order.push('task')
        return { ...buildShotTask(id), ...input } as ShotTaskOut
      })
      vi.mocked(chatApi.sendMessage).mockImplementation(async () => {
        order.push('comment')
        return {} as never
      })
      withTasks(buildShotTask(1))
      const wrapper = await mountWithFile()
      tasksList(wrapper).vm.$emit('status', 1, 3)
      await wrapper.find('textarea').setValue('Готово.')
      await flushPromises()

      await send(wrapper)

      expect(order).toEqual(['task', 'comment'])
    })

    describe('when a task cannot be saved', () => {
      async function failTask() {
        vi.mocked(tasksApi.updateShotTask).mockRejectedValue(new Error('offline'))
        withTasks(buildShotTask(1), buildShotTask(2))
        const wrapper = await mountWithFile()
        tasksList(wrapper).vm.$emit('status', 1, 3)
        tasksList(wrapper).vm.$emit('hours', 2, 1)
        await wrapper.find('textarea').setValue('Готово.')
        await flushPromises()
        await send(wrapper)
        return wrapper
      }

      it('stays on the page with an error, the version stays uploaded', async () => {
        const wrapper = await failTask()

        expect(received).toEqual([])
        expect(wrapper.text()).toContain('Версия загружена, но изменения задач не сохранились.')
        expect(findButton(wrapper, 'Отправить версию')).toBeUndefined()
        expect(findButton(wrapper, 'Повторить сохранение задач')).toBeDefined()
      })

      it('still sends the comment, which is not sent again on the retry', async () => {
        const wrapper = await failTask()
        vi.mocked(tasksApi.updateShotTask).mockImplementation(
          async (id, input) => ({ ...buildShotTask(id), ...input }) as ShotTaskOut,
        )

        await findButton(wrapper, 'Повторить сохранение задач')!.trigger('click')
        await flushPromises()

        expect(chatApi.sendMessage).toHaveBeenCalledTimes(1)
        expect(versionsApi.uploadVersion).toHaveBeenCalledTimes(1)
        expect(received).toEqual([created])
      })

      it('saves on the retry only the tasks that are still not saved', async () => {
        vi.mocked(tasksApi.updateShotTask)
          .mockResolvedValueOnce(buildShotTask(1, { status_id: 3 }))
          .mockRejectedValueOnce(new Error('offline'))
        withTasks(buildShotTask(1), buildShotTask(2))
        const wrapper = await mountWithFile()
        tasksList(wrapper).vm.$emit('status', 1, 3)
        tasksList(wrapper).vm.$emit('hours', 2, 1)
        await flushPromises()
        await send(wrapper)
        vi.mocked(tasksApi.updateShotTask).mockClear()

        await findButton(wrapper, 'Повторить сохранение задач')!.trigger('click')
        await flushPromises()

        expect(tasksApi.updateShotTask).toHaveBeenCalledTimes(1)
        expect(tasksApi.updateShotTask).toHaveBeenCalledWith(2, { actual_hours: 1 })
      })

      it('lets the user go on without saving the tasks', async () => {
        const wrapper = await failTask()

        await findButton(wrapper, 'Перейти к версии без сохранения задач')!.trigger('click')

        expect(received).toEqual([created])
      })

      it('asks to retry both when the comment fails as well', async () => {
        vi.mocked(chatApi.sendMessage).mockRejectedValue(new Error('offline'))
        const wrapper = await failTask()

        expect(wrapper.text()).toContain(
          'Версия загружена, но изменения задач не сохранились и комментарий не отправился.',
        )
        expect(findButton(wrapper, 'Повторить')).toBeDefined()
      })

      it('lets the changes be edited again and sends them on the retry', async () => {
        const wrapper = await failTask()
        vi.mocked(tasksApi.updateShotTask).mockImplementation(
          async (id, input) => ({ ...buildShotTask(id), ...input }) as ShotTaskOut,
        )
        tasksList(wrapper).vm.$emit('hours', 2, 3)
        await flushPromises()

        await findButton(wrapper, 'Повторить сохранение задач')!.trigger('click')
        await flushPromises()

        expect(tasksApi.updateShotTask).toHaveBeenLastCalledWith(2, { actual_hours: 3 })
      })
    })
  })
})
