import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { buildPageTitle, routePageTitle } from '@/utils/pageTitle'

const stub = { template: '<div />' }

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/projects', component: stub, meta: { title: 'Проекты' } },
    { path: '/bare', component: stub },
    {
      path: '/:companySlug/:projectCode',
      component: stub,
      children: [
        { path: 'shots', component: stub, meta: { title: 'Кадры' } },
        {
          path: 'shots/:shotName',
          component: stub,
          children: [{ path: 'versions', component: stub, meta: { title: 'Версии' } }],
        },
      ],
    },
  ],
})

describe('buildPageTitle', () => {
  it('joins the parts with a middle dot and ends with the app name', () => {
    expect(buildPageTitle(['SH010', 'Версии'])).toBe('SH010 · Версии · Паприка')
  })

  it('skips empty parts', () => {
    expect(buildPageTitle([undefined, '', null])).toBe('Паприка')
  })
})

describe('routePageTitle', () => {
  it('uses only the page title and the app name for plain pages', () => {
    expect(routePageTitle(router.resolve('/projects'))).toBe('Проекты · Паприка')
  })

  it('falls back to the app name when the route has no title', () => {
    expect(routePageTitle(router.resolve('/bare'))).toBe('Паприка')
  })

  it('adds the project code on project pages', () => {
    expect(routePageTitle(router.resolve('/acme/PRJ/shots'))).toBe('Кадры · PRJ · Паприка')
  })

  it('puts the shot name first and omits the project code on shot pages', () => {
    expect(routePageTitle(router.resolve('/acme/PRJ/shots/SH010/versions'))).toBe(
      'SH010 · Версии · Паприка',
    )
  })
})
